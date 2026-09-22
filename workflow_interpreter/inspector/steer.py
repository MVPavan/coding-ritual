"""§8.1 steer (tier 2) — the order of these four steps is the whole design.

```
persist steer intent (durable)  →  terminate(handle)  →  close `steered`  →  mint ONE continuation
```

Read backwards, every step is there to make a crash survivable:

- **Intent first, and RESUMABLE.** A crash after the kill but before the close
  leaves an activation that is dead with no recorded reason; the durable intent
  file is what tells the next tick that the death was deliberate rather than a
  §5.6 case-3 transport failure. It therefore carries the continuation REQUEST
  **and the instructions text**, not just a reason and a digest: recovery has to
  be able to FINISH the steer, and the three steps after the intent are all
  idempotent, so `resume` runs them again from wherever the crash landed. An
  intent recovery could recognise but not act on would still cost the human
  their continuation and spend an infra retry naming the deliberate kill a
  transport failure — and a digest is not something `build_resume_command` can
  resume with, so the text is what `Dispatcher` reads back off this file.
- **Refused before anything is destroyed.** Both refusals — no handle to prove
  death against, and no session the continuation could rejoin — are checked
  ahead of the intent write and therefore ahead of the kill. `build_resume_command`
  refuses an unknown session too, but that refusal lands after the crew is
  dead and the activation is closed `steered`: the round is spent and the
  continuation cannot be made. Order is the difference between fail-closed and
  fail-destructive.
- **Terminate before close.** Closing `steered` while the child still runs
  would let the continuation's crew and the steered crew write the same
  worktree at once. Death is PROVEN through the handle's identity, never
  assumed from a signal's exit status (§5.3), and a child that survives KILL
  refuses the steer outright — there is no honest way to continue.
- **Close before mint.** `mint_activation` derives `outcome_taken` from the
  predecessor's recorded close (§3.2); with no close there is no edge for the
  continuation to have taken.
- **Exactly one continuation.** Its `max_steers` cap lives in `bdio`'s pre-mint
  predicates, and its idempotency key makes a re-run re-find rather than
  re-mint (drill 14).

Guidance is not infrastructure failure: steers are capped separately from infra
retries and never consume review rounds (§8.1, §10.2).
"""

from __future__ import annotations

import hashlib
from typing import Final

import structlog
from pydantic import BaseModel

from workflow_interpreter.bdio import (
    ActivationRecord,
    Deviation,
    ExitRecord,
    MintRequest,
    MintResult,
    NodeSetting,
    Outcome,
    StoreError,
    WorkflowStore,
    pinned_execution_setting,
)
from workflow_interpreter.bdio.rpc_records import ControlRegistration
from workflow_interpreter.bdio.wire import resolved_settings
from workflow_interpreter.inspector.band import BandLock
from workflow_interpreter.inspector.clock import Clock, to_iso
from workflow_interpreter.inspector.config import InspectorConfig
from workflow_interpreter.inspector.errors import (
    ContinuationRefused,
    InspectorError,
    TerminationFailed,
)
from workflow_interpreter.inspector.gitio import Git
from workflow_interpreter.inspector.models import (
    RECORD_MODEL,
    ExitReason,
    RecoverySnapshot,
    SteerIntent,
    TerminationProof,
)
from workflow_interpreter.inspector.paths import WrapperPaths, write_record
from workflow_interpreter.inspector.procfs import terminate
from workflow_interpreter.inspector.rpc_control import enqueue, request_interrupt
from workflow_interpreter.inspector.workspace import Workspace
from workflow_interpreter.schema.models import Node

_LOG: Final[structlog.stdlib.BoundLogger] = structlog.get_logger(__name__)

DEVIATION_KIND_STEER: Final[str] = "steer"
STEER_EXIT_CODE: Final[int] = -15
"""The child is TERMed; a signalled death is recorded as `-signum` (§5.3)."""

_MSG_SURVIVED: Final[str] = (
    "activation {activation_id} survived TERM and KILL; refusing to close it "
    "`steered` while its process group may still be writing (§8.1)"
)
_MSG_NO_HANDLE: Final[str] = (
    "activation {activation_id} has no recorded handle; there is nothing to "
    "steer and no proof of death to record (§5.3)"
)
_MSG_NO_SESSION: Final[str] = (
    "activation {activation_id} has no session a continuation could rejoin; "
    "refusing to kill a crew whose §8.1 continuation could only be dispatched "
    "as a fresh session carrying the node's original brief"
)


def instructions_digest(instructions: str) -> str:
    """The sha256 of the steer instructions — the form a bd record may carry."""
    return hashlib.sha256(instructions.encode("utf-8")).hexdigest()


def _resumable_session(activation: ActivationRecord) -> str:
    """The session a continuation of this activation would rejoin.

    Raises rather than returning `""`, and the CALLER's position matters more
    than the check: an empty id means the vendor never named a session (codex
    assigns its thread id in its first event and there is nothing to resume
    until it does, §5.2), so `build_resume_command` would refuse — after the
    kill, with the activation already closed `steered`.

    A handle or metadata id may have been preassigned before the vendor emitted
    an identity event.  Only the durable registration proves that the session
    exists and can be resumed (§5.2, §5.3).
    """
    registration = activation.metadata.session_registration
    if registration is None:
        raise ContinuationRefused(
            _MSG_NO_SESSION.format(activation_id=activation.activation_id)
        )
    return registration.thread_id


def _continue_session(
    activation_id: str, session_id: str, continuation: MintRequest
) -> MintRequest:
    """Force the continuation onto the session the steered child actually ran.

    §8.1 continues a session; a continuation minted with some other id would be
    dispatched through `build_resume_command` naming a session the vendor has
    never heard of, and both CLIs answer that with a transport failure. The
    caller supplying the id was the weak link — it is derivable here.

    `session_id` is not part of the §3.2 idempotency key, so rewriting it cannot
    make a re-run mint a second continuation (drill 14).
    """
    if continuation.session_id == session_id:
        return continuation
    _LOG.info(
        "wf.steer.session_pinned",
        activation_id=activation_id,
        requested=continuation.session_id,
        pinned=session_id,
    )
    return continuation.model_copy(update={"session_id": session_id})


class SteerResult(BaseModel):
    """The evidence one steer produced, in the order §8.1 produced it."""

    model_config = RECORD_MODEL

    intent: SteerIntent
    termination: TerminationProof
    closed: ActivationRecord
    continuation: MintResult


class Steerer:
    """Tier-2 steering for one instance (§8.1)."""

    def __init__(
        self,
        config: InspectorConfig,
        paths: WrapperPaths,
        store: WorkflowStore,
        clock: Clock,
        *,
        workspace: Workspace | None = None,
    ) -> None:
        self._config = config
        self._paths = paths
        self._store = store
        self._clock = clock
        self._workspace = workspace or Workspace(
            paths, Git(config), clock, BandLock(paths.band_lock)
        )

    def in_place(
        self, activation: ActivationRecord, *, reason: str, instructions: str
    ) -> ControlRegistration:
        """Experimental app-server-only control; no close or continuation is minted."""
        root = self._store.reads.load_root(self._paths.root_id)
        coordinator = self._store.coordination_store()
        coordinator.validate_member(root)
        coordinator.assert_child_progress(root)
        return enqueue(
            self._paths,
            self._store,
            activation,
            reason=reason,
            instructions=instructions,
        )

    def steer(
        self,
        activation: ActivationRecord,
        *,
        reason: str,
        instructions: str,
        continuation: MintRequest,
    ) -> SteerResult:
        """Persist, terminate with proof, close `steered`, mint one continuation.

        Both refusals are checked BEFORE the intent is written, because a
        persisted intent is an INSTRUCTION to §5.6 recovery: one recovery could
        never carry out would wedge the activation on every later tick, and one
        written after the kill would have spent the round to learn that.
        """
        coordinator = self._store.coordination_store()
        root = self._store.reads.load_root(self._paths.root_id)
        coordinator.validate_member(root)
        coordinator.assert_child_progress(root)
        activation_id = activation.activation_id
        if activation.metadata.handle is None:
            raise TerminationFailed(_MSG_NO_HANDLE.format(activation_id=activation_id))
        session_id = _resumable_session(activation)
        continuation = self._pinned_continuation(continuation)
        self._store._preflight_steer_continuation(
            self._paths.root_id, activation, continuation
        )
        intent = SteerIntent(
            activation_id=activation_id,
            reason=reason,
            instructions=instructions,
            instructions_digest=instructions_digest(instructions),
            requested_at=to_iso(self._clock.now()),
            continuation=_continue_session(activation_id, session_id, continuation),
        )
        write_record(self._paths.steer_intent(activation_id), intent)
        return self.resume(activation, intent)

    def resume(self, activation: ActivationRecord, intent: SteerIntent) -> SteerResult:
        """Carry a PERSISTED steer to its end: kill, close, mint one continuation.

        Every step is idempotent, which is what lets §5.6 recovery call this on
        an intent it found on disk without knowing where the crash landed:
        `terminate` is a no-op on a dead handle, the exit file is a rewrite of
        the same record, `close_activation` repairs a half-finished close
        forward, and the continuation's idempotency key re-finds rather than
        re-mints (drill 14).
        """
        coordinator = self._store.coordination_store()
        root = self._store.reads.load_root(self._paths.root_id)
        coordinator.validate_member(root)
        coordinator.assert_child_progress(root)
        activation_id = activation.activation_id
        handle = activation.metadata.handle
        if handle is None:
            raise TerminationFailed(_MSG_NO_HANDLE.format(activation_id=activation_id))

        request_interrupt(self._paths, activation)
        proof = terminate(self._config, handle, self._clock)
        if not proof.confirmed_dead:
            raise TerminationFailed(_MSG_SURVIVED.format(activation_id=activation_id))
        self._write_exit_file(activation_id)
        pinned = root.index.nodes[activation.metadata.node]
        settings = resolved_settings(root.metadata)
        recovery_node = Node.model_validate(
            pinned.model_dump()
            | {
                field: settings[setting.at(pinned.name)]
                for field, setting in (
                    ("writes", NodeSetting.WRITES),
                    ("isolation", NodeSetting.ISOLATION),
                )
                if setting.at(pinned.name) in settings
            }
        )
        preserved = self._workspace.preserve_interrupted(activation, recovery_node)
        self._record_session_tree(activation, recovery_node, preserved)

        closed = self._store.close_activation(
            activation_id,
            Outcome.STEERED,
            deviations=(
                Deviation(
                    kind=DEVIATION_KIND_STEER,
                    reason=intent.reason,
                    recorded_at=intent.requested_at,
                    instructions_digest=intent.instructions_digest,
                ),
            ),
        )
        from workflow_interpreter.inspector.toolchain_cleanup import cleanup_toolchain

        cleanup_toolchain(self._paths, closed)
        intent = intent.model_copy(
            update={"continuation": self._pinned_continuation(intent.continuation)}
        )
        minted = self._store.mint_activation(self._paths.root_id, intent.continuation)
        _LOG.info(
            "wf.activation.steered",
            activation_id=activation_id,
            continuation_id=minted.activation.activation_id,
            signals=proof.signals_sent,
        )
        return SteerResult(
            intent=intent, termination=proof, closed=closed, continuation=minted
        )

    def _record_session_tree(
        self,
        activation: ActivationRecord,
        node: Node,
        preserved: RecoverySnapshot | None,
    ) -> None:
        """Carry the killed turn's own tree into §3, from the pin recovery made.

        A steered source feeds the SAME launch contract a normal turn does —
        there is no second resume mechanism — and its tree proof is the
        recovery snapshot just pinned, taken while this frame held the proof of
        death. Where recovery pinned nothing there was nothing dirty to pin,
        and the current full-tree OID states that same tree exactly. Recorded
        before the close, because a settled activation no longer accepts it; a
        failure here only costs the continuation its tree-faithful resume,
        which then refuses by name rather than resetting.
        """
        if not node.writes:
            return
        try:
            tree = (
                preserved.tree
                if preserved is not None and preserved.tree is not None
                else self._workspace.resumable_tree_oid(activation, node)
            )
            self._store.record_session_tree(activation.activation_id, tree)
        except (StoreError, InspectorError, OSError) as exc:
            _LOG.warning(
                "wf.session.tree_unpinned",
                activation_id=activation.activation_id,
                error=str(exc),
            )

    def _pinned_continuation(self, continuation: MintRequest) -> MintRequest:
        """Normalize execution bindings against the immutable root pins."""
        root = self._store.reads.load_root(self._paths.root_id)
        return continuation.model_copy(
            update={
                "crew_profile": pinned_execution_setting(
                    root, continuation.node, NodeSetting.CREW
                ),
                "model": pinned_execution_setting(
                    root, continuation.node, NodeSetting.MODEL
                ),
            }
        )

    def _write_exit_file(self, activation_id: str) -> None:
        """Record the deliberate death in the wrapper dir (crash-window fallback).

        Not mirrored into bd: §5.1 has no `exit-recorded` → `steered` path, and
        the close that follows IS the routing truth. The file exists so a tick
        that crashes between the kill and the close can tell a steer from a
        §5.6 case-3 disappearance.
        """
        write_record(
            self._paths.exit_file(activation_id),
            ExitRecord(
                exit_code=STEER_EXIT_CODE,
                ended_at=to_iso(self._clock.now()),
                reason=ExitReason.STEERED.value,
            ),
        )
