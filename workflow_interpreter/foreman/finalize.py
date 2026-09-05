"""Pure conversion of wrapper evidence into an activation close decision."""

from typing import Final

from pydantic import BaseModel, ConfigDict

from workflow_interpreter.bdio import ActivationRecord, Deviation
from workflow_interpreter.bdio.constants import DEVIATION_BOUND_VIOLATED
from workflow_interpreter.schema.models import Node, Outcome
from workflow_interpreter.supervisor.models import AuditFlag, CompletionEvidence

REASON_BOUND_VIOLATED: Final[str] = (
    "an effect landed outside allowed_paths under the §2 mount bound"
)
"""Deliberately path-free: the paths are in `completion.json` and in the
evidence, and this reason has to say the one thing the deviation MEANS."""


class FinalDecision(BaseModel):
    """The facts a close operation must persist, with no I/O policy mixed in."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    outcome: Outcome
    claimed_outcome: Outcome | None
    blocked: bool
    deviations: tuple[Deviation, ...]
    """ONLY what this close ADDS. `WorkflowStore.close_activation` stores
    `(*record.metadata.deviations, *deviations)`, so it is the single owner of
    the merge; returning the activation's existing deviations here recorded
    every carried one two or three times (cr-n2z.9)."""


def bound_violated(completion: CompletionEvidence) -> Deviation | None:
    """The wrapper-recorded fact that the §2 mount bound did not hold, if so.

    One definition, because the fresh-observation close and the crash-window
    replay close (`close._completion_deviations`) must record the same fact the
    same way — it is what `frontier._dead_end` routes on and what
    `bounds._RETRY_EXEMPT_DEVIATIONS` exempts.
    """
    if AuditFlag.BOUND_VIOLATED not in completion.audit_flags:
        return None
    return Deviation(
        kind=DEVIATION_BOUND_VIOLATED,
        reason=REASON_BOUND_VIOLATED,
        recorded_at="wrapper",
    )


def decide(
    node: Node, activation: ActivationRecord, completion: CompletionEvidence
) -> FinalDecision:
    """Make the close decision from already-computed wrapper evidence.

    What it returns about deviations is what THIS close ADDS — the activation's
    own are already on the record, and the store appends these after them. So
    `activation` is now, like `node`, part of the call's shape rather than
    something the decision reads (cr-n2z.9).
    """
    violation = bound_violated(completion)
    if violation is not None:
        # Never `blocked`: the §7.5 effects gate asks a human to accept or
        # discard what the runner did, and a bound that failed is not something
        # the runner did. The deviation dead-ends this at a halt instead, and
        # the outcome stays the wrapper's own `error_transport` verdict.
        return FinalDecision(
            outcome=completion.outcome,
            claimed_outcome=completion.claimed_outcome,
            blocked=False,
            deviations=(violation,),
        )
    blocked = bool(completion.evidence.undeclared_effects)
    return FinalDecision(
        outcome=completion.outcome,
        claimed_outcome=completion.claimed_outcome,
        blocked=blocked,
        deviations=(),
    )
