"""Choose intentional history from settled same-node records, never caller text."""

from collections.abc import Sequence
from typing import Final

import structlog
from pydantic import BaseModel, ConfigDict

from workflow_interpreter.bdio.errors import CarrierIntegrityError
from workflow_interpreter.bdio.records import ActivationRecord, RootRecord
from workflow_interpreter.bdio.rpc_records import SessionCompletion, SessionRegistration
from workflow_interpreter.bdio.wire import (
    MintReason,
    MintRequest,
    NodeSetting,
    resolved_settings,
)
from workflow_interpreter.contracts.codex import CODEX_VERSION
from workflow_interpreter.contracts.execution import EXECUTION_POLICY_KEY, CrewName
from workflow_interpreter.contracts.sessions import (
    MSG_SESSION_SOURCE,
    SessionFreshReason,
    SessionMode,
    SessionReuse,
    execution_policy_digest,
    session_mode_key,
)
from workflow_interpreter.schema.models import Outcome

_LOG = structlog.get_logger(__name__)
MSG_VERSION_FRESH: Final[str] = "wf.session.fresh.version_mismatch"
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
    continuation_ids = _continuation_sources(request, activations)
    continuation = bool(continuation_ids)
    if (
        not continuation
        and resolved_session_mode(root, request.node) is not SessionMode.RESUME
    ):
        return SessionChoice()
    settings = resolved_settings(root.metadata)
    policy = settings.get(EXECUTION_POLICY_KEY.format(node=request.node), "legacy")
    if not isinstance(policy, str):
        raise CarrierIntegrityError(MSG_SESSION_SOURCE)
    crew_profile = request.crew_profile.removeprefix("profile:")
    # The first explanation in scan order (newest candidate first) is the one
    # the record keeps: a fresh launch on a RESUME node must say WHY, and the
    # most recent near-miss is the answer an operator is looking for.
    rejected: SessionFreshReason | None = None
    for source in sorted(activations, key=lambda item: item.metadata.seq, reverse=True):
        meta = source.metadata
        registration = meta.session_registration
        if (
            not meta.is_completed
            or not _source_outcome_eligible(source, continuation_ids)
            or meta.wf_root_id != root.root_id
            or meta.node != request.node
            or meta.model != settings.get(NodeSetting.MODEL.at(request.node))
            or meta.crew_profile.removeprefix("profile:") != crew_profile
        ):
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
            or registration.model != settings.get(NodeSetting.MODEL.at(request.node))
            or registration.effort != settings.get(NodeSetting.EFFORT.at(request.node))
            or registration.policy_digest != execution_policy_digest(policy)
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


def _source_outcome_eligible(
    source: ActivationRecord, continuation_ids: frozenset[str]
) -> bool:
    """Admit successful turns, plus the exact deliberate steer ancestor."""
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
