"""Pure graph routing for completed activations and decided gates."""

from enum import StrEnum

from pydantic import BaseModel, ConfigDict

from workflow_interpreter.bdio import MintReason
from workflow_interpreter.schema.graph_index import GraphIndex
from workflow_interpreter.schema.models import BindsMode, Node, NodeKind, Outcome


class RouteKind(StrEnum):
    """The finite set of actions a tick may take after evaluating an outcome."""

    TASK = "task"
    GATE = "gate"
    TERMINAL = "terminal"
    FALLBACK = "fallback"
    EXHAUSTED = "exhausted"
    NO_PROGRESS = "no-progress"
    DEAD_END = "dead-end"
    FAIL_CLOSED = "fail-closed"


class RetryKind(StrEnum):
    """The only system-outcome continuation mechanisms."""

    INFRA = "infra"
    STEER = "steer"


class Route(BaseModel):
    """A routing result; target is absent only where no graph edge is taken."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    kind: RouteKind
    target: str | None = None
    reason: str | None = None


def abandon_target(index: GraphIndex) -> str | None:
    """Return the unique terminal target of declared ``abandon`` edges."""
    targets = {edge.to for edge in index.edges if edge.on is Outcome.ABANDON}
    if len(targets) != 1:
        return None
    return next(iter(targets))


def retry_kind(outcome: Outcome) -> MintReason | None:
    """Map a system outcome to its bounded re-mint reason, if any."""
    if outcome in {Outcome.ERROR_RUNNER, Outcome.ERROR_TRANSPORT}:
        return MintReason.INFRA_RETRY
    if outcome is Outcome.STEERED:
        return MintReason.STEER_CONTINUATION
    return None


def exhausted(index: GraphIndex, node: Node) -> Route:
    """Route a bounded-region exhaustion to its declared exit or fallback."""
    if node.region is not None:
        region = index.regions.get(node.region)
        if region is not None and region.on_exhausted is not None:
            return Route(kind=RouteKind.EXHAUSTED, target=region.on_exhausted)
    fallback = node.fallback or index.document.fallback
    return Route(kind=RouteKind.EXHAUSTED, target=fallback.to)


def route(
    index: GraphIndex,
    node: Node,
    outcome: Outcome,
    *,
    claimed_outcome: Outcome | None = None,
    no_progress: bool = False,
) -> Route:
    """Route one recorded outcome without reading or writing external state."""
    if no_progress:
        return Route(kind=RouteKind.NO_PROGRESS)
    if outcome is Outcome.FAIL_CODE and (
        claimed_outcome is not Outcome.FAIL_CODE
        or Outcome.FAIL_CODE not in (node.outcomes or ())
    ):
        return Route(kind=RouteKind.DEAD_END)
    target = next(
        (
            edge.to
            for edge in index.edges
            if edge.from_node == node.name and edge.on is outcome
        ),
        None,
    )
    if target is None:
        fallback = node.fallback or index.document.fallback
        return Route(kind=RouteKind.FALLBACK, target=fallback.to)
    target_node = index.nodes[target]
    if target_node.kind is NodeKind.TASK:
        return Route(kind=RouteKind.TASK, target=target)
    if target_node.kind is NodeKind.TERMINAL:
        return Route(kind=RouteKind.TERMINAL, target=target)
    if node.kind is NodeKind.GATE:
        return Route(kind=RouteKind.FAIL_CLOSED, reason="gate_to_gate_unsupported")
    if target_node.binds is BindsMode.MUTABLE:
        return Route(kind=RouteKind.FAIL_CLOSED, reason="mutable_gate_unbound")
    return Route(kind=RouteKind.GATE, target=target)
