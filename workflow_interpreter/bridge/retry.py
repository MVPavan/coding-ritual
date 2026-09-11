"""Pure retry eligibility for a previously admitted phase-bridge root."""

from __future__ import annotations

from enum import StrEnum
from typing import Final

from workflow_interpreter.bridge.landing import SHIP_GATE
from workflow_interpreter.bridge.models import PhaseBridgeState
from workflow_interpreter.foreman.frontier import Frontier
from workflow_interpreter.schema.models import Outcome

SHIPPED_TERMINAL: Final[str] = "shipped"


class RetryRefusal(StrEnum):
    """Reasons a phase-bridge retry must not create another root."""

    OPEN_HALT = "open-halt"
    NO_TERMINAL = "no-terminal"
    UNLISTED_TERMINAL = "unlisted-terminal"
    GATE_RED_NOT_APPROVED_SHIPPED = "gate-red-not-approved-shipped"


def retry_refusal(
    prior_state: PhaseBridgeState,
    retry_terminals: tuple[str, ...],
    frontier: Frontier,
) -> RetryRefusal | None:
    """Return why retry is refused, or ``None`` when the root may be retried."""
    if frontier.open_halt is not None:
        return RetryRefusal.OPEN_HALT
    if frontier.terminal_node is None:
        return RetryRefusal.NO_TERMINAL
    if prior_state is PhaseBridgeState.GATE_RED:
        if (
            frontier.terminal_node == SHIPPED_TERMINAL
            and SHIPPED_TERMINAL in retry_terminals
            and any(
                gate.metadata.gate_node == SHIP_GATE
                and gate.metadata.outcome is Outcome.APPROVE
                for gate in frontier.decided_gates
            )
        ):
            return None
        return RetryRefusal.GATE_RED_NOT_APPROVED_SHIPPED
    if frontier.terminal_node in retry_terminals:
        return None
    return RetryRefusal.UNLISTED_TERMINAL
