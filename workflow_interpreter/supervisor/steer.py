"""§8.1 steer (tier 2) — the order of these four steps is the whole design.

```
persist steer intent (durable)  →  terminate(handle)  →  close `steered`  →  mint ONE continuation
```

Read backwards, every step is there to make a crash survivable:

- **Intent first, and RESUMABLE.** A crash after the kill but before the close
  leaves an activation that is dead with no recorded reason; the durable intent
  file is what tells the next tick that the death was deliberate rather than a
  §5.6 case-3 transport failure. It therefore carries the continuation REQUEST,
  not just a reason and a digest: recovery has to be able to FINISH the steer,
  and the three steps after the intent are all idempotent, so `resume` runs
  them again from wherever the crash landed. An intent recovery could recognise
  but not act on would still cost the human their continuation and spend an
  infra retry naming the deliberate kill a transport failure.
- **Terminate before close.** Closing `steered` while the child still runs
  would let the continuation's runner and the steered runner write the same
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
    Outcome,
    WorkflowStore,
)
from workflow_interpreter.supervisor.clock import Clock, to_iso
from workflow_interpreter.supervisor.config import SupervisorConfig
from workflow_interpreter.supervisor.errors import TerminationFailed
from workflow_interpreter.supervisor.models import (
    RECORD_MODEL,
    ExitReason,
    SteerIntent,
    TerminationProof,
)
from workflow_interpreter.supervisor.paths import WrapperPaths, write_record
from workflow_interpreter.supervisor.procfs import terminate

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


def instructions_digest(instructions: str) -> str:
    """The sha256 of the steer instructions — recorded, never the text itself."""
    return hashlib.sha256(instructions.encode("utf-8")).hexdigest()


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
        config: SupervisorConfig,
        paths: WrapperPaths,
        store: WorkflowStore,
        clock: Clock,
    ) -> None:
        self._config = config
        self._paths = paths
        self._store = store
        self._clock = clock

    def steer(
        self,
        activation: ActivationRecord,
        *,
        reason: str,
        instructions: str,
        continuation: MintRequest,
    ) -> SteerResult:
        """Persist, terminate with proof, close `steered`, mint one continuation."""
        activation_id = activation.activation_id
        if activation.metadata.handle is None:
            # Checked BEFORE the intent is written: a persisted intent is an
            # instruction to recovery, and one it could never carry out would
            # wedge the activation on every later tick.
            raise TerminationFailed(_MSG_NO_HANDLE.format(activation_id=activation_id))
        intent = SteerIntent(
            activation_id=activation_id,
            reason=reason,
            instructions_digest=instructions_digest(instructions),
            requested_at=to_iso(self._clock.now()),
            continuation=continuation,
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
        activation_id = activation.activation_id
        handle = activation.metadata.handle
        if handle is None:
            raise TerminationFailed(_MSG_NO_HANDLE.format(activation_id=activation_id))

        proof = terminate(self._config, handle, self._clock)
        if not proof.confirmed_dead:
            raise TerminationFailed(_MSG_SURVIVED.format(activation_id=activation_id))
        self._write_exit_file(activation_id)

        closed = self._store.close_activation(
            activation_id,
            Outcome.STEERED,
            deviations=(
                Deviation(
                    kind=DEVIATION_KIND_STEER,
                    reason=intent.reason,
                    recorded_at=intent.requested_at,
                ),
            ),
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
