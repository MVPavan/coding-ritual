"""Foreman-facing aliases for the pure §10 bound predicates."""

from workflow_interpreter.bdio.bounds import (
    ActivationView,
    BoundKind,
    BoundRefusal,
    consecutive_infra_closes,
    infra_retry_refusal,
    instance_ceiling_refusal,
    region_round_refusal,
    steer_closes,
    steer_refusal,
)
from workflow_interpreter.foreman.routing import Route, RouteKind, exhausted
from workflow_interpreter.schema.graph_index import GraphIndex
from workflow_interpreter.schema.models import Node

__all__ = [
    "ActivationView",
    "BoundKind",
    "BoundRefusal",
    "consecutive_infra_closes",
    "infra_retry_refusal",
    "instance_ceiling_refusal",
    "refusal_route",
    "region_round_refusal",
    "steer_closes",
    "steer_refusal",
]


def refusal_route(index: GraphIndex, node: Node, refusal: BoundRefusal) -> Route:
    """Map each §10 refusal to its declared human or graph recovery path."""
    if refusal.bound is BoundKind.REGION_ROUNDS:
        return exhausted(index, node)
    if refusal.bound in {BoundKind.INFRA_RETRIES, BoundKind.STEERS}:
        fallback = node.fallback or index.document.fallback
        return Route(kind=RouteKind.FALLBACK, target=fallback.to)
    return Route(kind=RouteKind.FAIL_CLOSED, reason=refusal.detail)
