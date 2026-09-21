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
from workflow_interpreter.contracts.execution import EXECUTION_POLICY_KEY
from workflow_interpreter.contracts.sessions import (
    MSG_SESSION_SOURCE,
    SessionFreshReason,
    SessionReuse,
    execution_policy_digest,
)

_LOG = structlog.get_logger(__name__)
MSG_VERSION_FRESH: Final[str] = "wf.session.fresh.version_mismatch"


class SessionChoice(BaseModel):
    """Bind the selected source or explicit fresh reason together at mint."""

    model_config = ConfigDict(frozen=True, extra="forbid")
    source: SessionRegistration | None = None
    fresh_reason: SessionFreshReason | None = None


def choose_source(
    root: RootRecord, request: MintRequest, activations: Sequence[ActivationRecord]
) -> SessionChoice:
    """Select once at mint; fresh and ambiguous sessions never become implicit reuse."""
    node = root.index.nodes[request.node]
    continuation_ids = _continuation_sources(request, activations)
    continuation = bool(continuation_ids)
    if not continuation and node.session_reuse is not SessionReuse.SAME_NODE:
        return SessionChoice()
    settings = resolved_settings(root.metadata)
    policy = settings.get(EXECUTION_POLICY_KEY.format(node=node.name), "legacy")
    if not isinstance(policy, str):
        raise CarrierIntegrityError(MSG_SESSION_SOURCE)
    for source in sorted(activations, key=lambda item: item.metadata.seq, reverse=True):
        meta = source.metadata
        registration = meta.session_registration
        if (
            registration is None
            or not meta.is_completed
            or meta.wf_root_id != root.root_id
            or meta.node != request.node
            or registration.root_id != root.root_id
            or registration.activation_id != source.activation_id
            or registration.model != settings.get(NodeSetting.MODEL.at(node.name))
            or registration.effort != settings.get(NodeSetting.EFFORT.at(node.name))
            or registration.policy_digest != execution_policy_digest(policy)
        ):
            continue
        eligible = (
            (source.activation_id in continuation_ids)
            if continuation
            else (
                meta.session_completion is not None
                and meta.session_completion.registration == registration
            )
        )
        if not eligible:
            continue
        if registration.crew_version != CODEX_VERSION:
            _LOG.warning(
                MSG_VERSION_FRESH,
                source=source.activation_id,
                recorded=registration.crew_version,
                required=CODEX_VERSION,
            )
            return SessionChoice(fresh_reason=SessionFreshReason.VERSION_MISMATCH)
        return SessionChoice(source=registration)
    if continuation:
        raise CarrierIntegrityError(MSG_SESSION_SOURCE)
    return SessionChoice()


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
