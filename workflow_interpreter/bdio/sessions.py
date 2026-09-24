"""Choose intentional history from settled same-node records, never caller text."""

from collections.abc import Sequence
from typing import Final

import structlog
from pydantic import BaseModel, ConfigDict

from workflow_interpreter.bdio.bounds import INFRA_OUTCOMES
from workflow_interpreter.bdio.errors import CarrierIntegrityError
from workflow_interpreter.bdio.records import ActivationRecord, RootRecord
from workflow_interpreter.bdio.rpc_records import SessionCompletion, SessionRegistration
from workflow_interpreter.bdio.wire import (
    MintReason,
    MintRequest,
    activation_binding_digest,
    is_legacy_activation,
    resolved_settings,
)
from workflow_interpreter.contracts.codex import CODEX_VERSION
from workflow_interpreter.contracts.execution import CrewName, ExecutionPolicy
from workflow_interpreter.contracts.sessions import (
    MSG_SESSION_SOURCE,
    SessionFreshReason,
    SessionMode,
    SessionReuse,
    activation_policy_digest,
    session_mode_key,
)
from workflow_interpreter.schema.models import Outcome

_LOG = structlog.get_logger(__name__)
MSG_VERSION_FRESH: Final[str] = "wf.session.fresh.version_mismatch"
MSG_CRASH_SOURCE: Final[str] = "crashed resumed writer source is unproved"
RESUMABLE_SESSION_OUTCOMES: Final[frozenset[Outcome]] = frozenset(
    {
        Outcome.DONE,
        Outcome.NO_DIFF,
        Outcome.ACCEPT,
        Outcome.REJECT,
        Outcome.FAIL_CODE,
        Outcome.FAIL_PLAN,
        Outcome.DOUBT,
    }
)
"""Successful task turns whose vendor history may seed a later plain resume."""
_VERSIONED_CREWS: Final[frozenset[str]] = frozenset(
    {CrewName.CLAUDE.value, CrewName.CODEX.value}
)
"""Crews whose registration carries a probed CLI version reuse is gated on."""


class SessionChoice(BaseModel):
    """Bind the selected source or explicit fresh reason together at mint."""

    model_config = ConfigDict(frozen=True, extra="forbid")
    source: SessionRegistration | None = None
    source_activation_id: str | None = None
    source_session_id: str | None = None
    source_tree_oid: str | None = None
    """§3: the tree the selected source left. `None` where the source never
    pinned one, which makes a writing resume refuse rather than reset."""
    fresh_reason: SessionFreshReason | None = None


def choose_source(
    root: RootRecord, request: MintRequest, activations: Sequence[ActivationRecord]
) -> SessionChoice:
    """Select once at mint; fresh and ambiguous sessions never become implicit reuse."""
    if request.fresh_reason_override is not None:
        return SessionChoice(fresh_reason=request.fresh_reason_override)
    continuation_ids = _continuation_sources(request, activations)
    continuation = bool(continuation_ids)
    appserver = (
        request.crew_profile.removeprefix("profile:") == CrewName.CODEX_APPSERVER.value
    )
    if (
        not continuation
        and request.session_mode is not SessionMode.RESUME
        and not (
            appserver
            and resolved_session_mode(root, request.node) is SessionMode.RESUME
        )
    ):
        return SessionChoice()
    if request.execution_policy is not None and not isinstance(
        request.execution_policy, ExecutionPolicy
    ):
        raise CarrierIntegrityError(MSG_SESSION_SOURCE)
    policy_digest = activation_policy_digest(request.execution_policy)
    crew_profile = request.crew_profile.removeprefix("profile:")
    crashed = (
        None if appserver else _crashed_resumed_predecessor(root, request, activations)
    )
    if crashed is not None and not (
        continuation and crashed.metadata.session_tree_oid is None
    ):
        return _choose_crashed_source(crashed, request, activations, policy_digest)
    # The first explanation in scan order (newest candidate first) is the one
    # the record keeps: a fresh launch on a RESUME node must say WHY, and the
    # most recent near-miss is the answer an operator is looking for.
    rejected: SessionFreshReason | None = None
    for source in sorted(activations, key=lambda item: item.metadata.seq, reverse=True):
        meta = source.metadata
        registration = meta.session_registration
        if (
            not meta.is_completed
            or meta.wf_root_id != root.root_id
            or meta.node != request.node
        ):
            continue
        legacy = is_legacy_activation(meta)
        if not legacy and (
            meta.policy_digest != activation_policy_digest(meta.execution_policy)
            or meta.binding_digest != activation_binding_digest(meta)
        ):
            raise CarrierIntegrityError(
                f"session source activation {source.activation_id!r} has unusable "
                "invocation pins"
            )
        if (
            crew_profile != CrewName.CODEX_APPSERVER.value
            and not legacy
            and (
                meta.model != request.model
                or meta.effort != request.effort
                or meta.crew_profile.removeprefix("profile:") != crew_profile
            )
        ):
            if continuation:
                raise CarrierIntegrityError(MSG_SESSION_SOURCE)
            return SessionChoice(fresh_reason=SessionFreshReason.MODEL_CHANGED)
        if not _source_outcome_eligible(source, crew_profile, continuation_ids):
            continue
        # §5.2 (finding 3): only an OBSERVED vendor identity is registrable, so
        # an unregistered activation carries no session a resume could rejoin —
        # whatever `prepare()` preassigned into `session_id` is not evidence.
        if registration is None:
            rejected = rejected or SessionFreshReason.UNREGISTERED_SOURCE
            continue
        if (
            registration.root_id != root.root_id
            or registration.activation_id != source.activation_id
            or registration.model != request.model
            or registration.effort != request.effort
            or registration.policy_digest != policy_digest
            or (
                registration.crew_profile is not None
                and registration.crew_profile.removeprefix("profile:") != crew_profile
            )
            or (
                registration.crew_profile is None
                and crew_profile != CrewName.CODEX_APPSERVER.value
            )
        ):
            continue
        eligible = (
            (source.activation_id in continuation_ids)
            if continuation
            else (
                crew_profile != CrewName.CODEX_APPSERVER.value
                or (
                    meta.session_completion is not None
                    and meta.session_completion.registration == registration
                )
            )
        )
        if not eligible:
            continue
        if (
            crew_profile == CrewName.CODEX_APPSERVER.value
            and registration.crew_version != CODEX_VERSION
        ):
            _LOG.warning(
                MSG_VERSION_FRESH,
                source=source.activation_id,
                recorded=registration.crew_version,
                required=CODEX_VERSION,
            )
            return SessionChoice(fresh_reason=SessionFreshReason.VERSION_MISMATCH)
        # Design §6: an unqualified version refuses reuse. A claude/codex source
        # that registered no CLI version cannot be compared with anything, so
        # skipping the guard for it would resume across an unknown upgrade.
        if crew_profile in _VERSIONED_CREWS and registration.crew_version is None:
            rejected = rejected or SessionFreshReason.UNQUALIFIED_SOURCE
            continue
        # Finding 4: eligibility compares what the SOURCE ran under against what
        # this process probed, never a root pin — a pin is historical once the
        # CLI is upgraded under a long-lived root.
        current_version = request.crew_version
        if (
            registration.crew_version is not None
            and current_version is not None
            and registration.crew_version != current_version
        ):
            _LOG.warning(
                MSG_VERSION_FRESH,
                source=source.activation_id,
                recorded=registration.crew_version,
                required=current_version,
            )
            rejected = rejected or SessionFreshReason.VERSION_DRIFT
            continue
        return SessionChoice(
            source=registration,
            source_activation_id=source.activation_id,
            source_session_id=registration.thread_id,
            source_tree_oid=meta.session_tree_oid,
        )
    if continuation:
        raise CarrierIntegrityError(MSG_SESSION_SOURCE)
    return SessionChoice(fresh_reason=rejected or SessionFreshReason.NO_SOURCE)


def _crashed_resumed_predecessor(
    root: RootRecord, request: MintRequest, activations: Sequence[ActivationRecord]
) -> ActivationRecord | None:
    """Find only the immediately failed resumed turn of this infra retry."""
    if request.mint_reason is not MintReason.INFRA_RETRY:
        return None
    return next(
        (
            item
            for item in activations
            if item.activation_id == request.predecessor_activation_id
            and item.metadata.wf_root_id == root.root_id
            and item.metadata.node == request.node
            and item.metadata.is_completed
            and item.metadata.outcome in INFRA_OUTCOMES
            and item.metadata.session_mode is SessionMode.RESUME
            and item.metadata.source_session_id is not None
            and not is_legacy_activation(item.metadata)
            and item.metadata.execution_policy is not None
            and item.metadata.execution_policy.writes
        ),
        None,
    )


def _choose_crashed_source(
    crashed: ActivationRecord,
    request: MintRequest,
    activations: Sequence[ActivationRecord],
    policy_digest: str,
) -> SessionChoice:
    """Use the failed turn's own proof, never an older successful near-match."""
    meta = crashed.metadata
    if meta.binding_digest != activation_binding_digest(
        meta
    ) or meta.policy_digest != activation_policy_digest(meta.execution_policy):
        raise CarrierIntegrityError(MSG_CRASH_SOURCE)
    if (
        meta.crew_profile != request.crew_profile
        or meta.model != request.model
        or meta.effort != request.effort
        or meta.policy_digest != policy_digest
    ):
        return SessionChoice(fresh_reason=SessionFreshReason.MODEL_CHANGED)
    if meta.session_tree_oid is None:
        raise CarrierIntegrityError(MSG_CRASH_SOURCE)
    registration = meta.session_registration
    if registration is None:
        registration = next(
            (
                item.metadata.session_registration
                for item in activations
                if item.activation_id == meta.session_source_activation_id
            ),
            None,
        )
        if (
            meta.expected_tree_oid is None
            or meta.session_tree_oid != meta.expected_tree_oid
            or registration is None
            or registration.thread_id != meta.source_session_id
        ):
            raise CarrierIntegrityError(MSG_CRASH_SOURCE)
    if (
        registration.root_id != meta.wf_root_id
        or registration.activation_id
        != (
            crashed.activation_id
            if meta.session_registration is not None
            else meta.session_source_activation_id
        )
        or registration.model != request.model
        or registration.effort != request.effort
        or registration.policy_digest != policy_digest
        or registration.crew_profile is None
        or registration.crew_profile.removeprefix("profile:")
        != request.crew_profile.removeprefix("profile:")
        or registration.thread_id != meta.source_session_id
    ):
        raise CarrierIntegrityError(MSG_CRASH_SOURCE)
    if (
        request.crew_profile.removeprefix("profile:") in _VERSIONED_CREWS
        and registration.crew_version is None
    ):
        return SessionChoice(fresh_reason=SessionFreshReason.UNQUALIFIED_SOURCE)
    if (
        registration.crew_version is not None
        and request.crew_version is not None
        and registration.crew_version != request.crew_version
    ):
        return SessionChoice(fresh_reason=SessionFreshReason.VERSION_DRIFT)
    return SessionChoice(
        source=registration,
        source_activation_id=crashed.activation_id,
        source_session_id=registration.thread_id,
        source_tree_oid=meta.session_tree_oid,
    )


def _source_outcome_eligible(
    source: ActivationRecord, crew_profile: str, continuation_ids: frozenset[str]
) -> bool:
    """Admit successful turns, plus the exact deliberate steer ancestor.

    The frozen app-server crew keeps its pre-epic rule exactly: its recorded
    `session_completion` is what qualifies a source, whatever the close was,
    so the outcome filter never applies to it.
    """
    if crew_profile == CrewName.CODEX_APPSERVER.value:
        return True
    if source.metadata.outcome in RESUMABLE_SESSION_OUTCOMES:
        return True
    return (
        source.activation_id in continuation_ids
        and source.metadata.outcome is Outcome.STEERED
    )


def resolved_session_mode(root: RootRecord, node_name: str) -> SessionMode:
    """Read the immutable pin, with a compatibility fallback for old roots."""
    value = resolved_settings(root.metadata).get(session_mode_key(node_name))
    if isinstance(value, str):
        try:
            return SessionMode(value)
        except ValueError as error:
            raise CarrierIntegrityError(MSG_SESSION_SOURCE) from error
    legacy = root.index.nodes[node_name].session_reuse
    if legacy is SessionReuse.SAME_NODE:
        return SessionMode.RESUME
    if legacy is SessionReuse.FRESH or value is None:
        return SessionMode.FRESH
    raise CarrierIntegrityError(MSG_SESSION_SOURCE)


def _continuation_sources(
    request: MintRequest, activations: Sequence[ActivationRecord]
) -> frozenset[str]:
    """Trace only deliberate steer ancestry; ordinary retries stay fresh by default."""
    if request.mint_reason not in (
        MintReason.STEER_CONTINUATION,
        MintReason.INFRA_RETRY,
    ):
        return frozenset()
    records = {item.activation_id: item for item in activations}
    predecessor = request.predecessor_activation_id
    found: set[str] = set()
    visited: set[str] = set()
    deliberate = request.mint_reason is MintReason.STEER_CONTINUATION
    while predecessor is not None and predecessor not in visited:
        visited.add(predecessor)
        source = records.get(predecessor)
        if source is None or source.metadata.node != request.node:
            break
        found.add(predecessor)
        if source.metadata.session_reuse_source is not None:
            found.add(source.metadata.session_reuse_source.activation_id)
        if source.metadata.session_source_activation_id is not None:
            found.add(source.metadata.session_source_activation_id)
        if deliberate or source.metadata.mint_reason is MintReason.STEER_CONTINUATION:
            return frozenset(found)
        if source.metadata.mint_reason is not MintReason.INFRA_RETRY:
            break
        predecessor = source.metadata.predecessor_activation_id
    return frozenset()


def validate_completion(
    activation: ActivationRecord, completion: SessionCompletion
) -> None:
    """A completion cannot attach a new identity or replace the one completed turn."""
    if activation.metadata.session_registration != completion.registration:
        raise CarrierIntegrityError(MSG_SESSION_SOURCE)
    previous = activation.metadata.session_completion
    if previous is not None and previous != completion:
        raise CarrierIntegrityError(MSG_SESSION_SOURCE)
