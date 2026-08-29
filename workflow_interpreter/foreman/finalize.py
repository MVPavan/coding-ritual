"""Pure conversion of wrapper evidence into an activation close decision."""

from pydantic import BaseModel, ConfigDict

from workflow_interpreter.bdio import ActivationRecord, Deviation
from workflow_interpreter.schema.models import Node, Outcome
from workflow_interpreter.supervisor.models import CompletionEvidence


class FinalDecision(BaseModel):
    """The facts a close operation must persist, with no I/O policy mixed in."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    outcome: Outcome
    claimed_outcome: Outcome | None
    blocked: bool
    deviations: tuple[Deviation, ...]


def decide(
    node: Node, activation: ActivationRecord, completion: CompletionEvidence
) -> FinalDecision:
    """Make the close decision from already-computed wrapper evidence."""
    blocked = bool(completion.evidence.undeclared_effects)
    return FinalDecision(
        outcome=completion.outcome,
        claimed_outcome=completion.claimed_outcome,
        blocked=blocked,
        deviations=activation.metadata.deviations,
    )
