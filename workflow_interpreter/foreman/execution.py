"""The one execution view of a pinned node: graph body ⊕ resolved config (§3.1).

A root pins BOTH the graph and the resolution of every configurable field,
role bindings included. Everything that decides how a node RUNS — which
profile and model a mint asks for, what the wrapper is allowed to write, how
long it may run, where it runs — must read that pinned resolution and nothing
else, or an instance drifts the moment the project's `roles` map or config
changes underneath it.
"""

from __future__ import annotations

from typing import Final

from pydantic import BaseModel, ConfigDict, ValidationError

from workflow_interpreter.bdio.records import RootRecord
from workflow_interpreter.bdio.wire import NodeSetting, resolved_settings
from workflow_interpreter.foreman.errors import (
    UnresolvedRunnerError,
    UnusableResolutionError,
)
from workflow_interpreter.profiles.config import RUNNER_PREFIX
from workflow_interpreter.schema.models import Node

_MSG_UNRESOLVED_RUNNER: Final[str] = (
    "node {node!r} binds the runner role {role!r}, but the root's resolved "
    "config carries no usable {key!r} — the pinned resolution is incomplete "
    "and the instance cannot be executed from it (§3.1)"
)

_MSG_UNUSABLE_ROOT: Final[str] = (
    "the root's resolved config holds a value node {node!r} cannot execute "
    "under ({detail}) — the pinned resolution is corrupt (§3.1)"
)

_EFFECTIVE_FIELDS: Final[tuple[tuple[str, NodeSetting], ...]] = (
    ("model", NodeSetting.MODEL),
    ("isolation", NodeSetting.ISOLATION),
    ("writes", NodeSetting.WRITES),
    ("token_budget", NodeSetting.TOKEN_BUDGET),
    ("max_wall", NodeSetting.MAX_WALL),
    ("stale_after", NodeSetting.STALE_AFTER),
)
"""Node fields the execution path reads and `resolve()` can override.

`runner` is deliberately absent: the pinned node names a ROLE
(`profile:<role>`), while the resolved key holds the profile that role was
bound to, so the two cannot share one field. It is carried as
`ResolvedNode.runner_profile` instead. `allowed_paths` is a list, which
`resolve()` cannot express, so the pinned value stands.
"""


class ResolvedNode(BaseModel):
    """One task node as the execution path must read it.

    `node` is the pinned node overlaid with the root's resolved values, so a
    collaborator that already takes a `Node` (workspace isolation, wrapper
    limits, the task builder) needs no second accessor.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    node: Node
    runner_profile: str
    model: str


def resolved_node(root: RootRecord, node_name: str) -> ResolvedNode:
    """Read one node's effective execution settings off the root's pinned resolution.

    Raises `UnresolvedRunnerError` when a role-bound node has no resolved
    runner: the value would still be the `profile:<role>` reference, which no
    profile resolver can answer, and guessing it from the live role map is the
    drift this view exists to prevent.
    """
    pinned = root.index.nodes[node_name]
    settings = resolved_settings(root.metadata)
    updates = {
        field: settings[setting.at(node_name)]
        for field, setting in _EFFECTIVE_FIELDS
        if setting.at(node_name) in settings
    }
    # Re-validated rather than `model_copy`d: an override reaches here as a
    # bare scalar off the root's metadata, and `model_copy` skips the
    # validators that turn "worktree" into `IsolationMode` and refuse a
    # duration the pattern does not accept.
    try:
        effective = Node.model_validate(pinned.model_dump() | updates)
    except ValidationError as error:
        # `resolve()` refuses these before the root is written, so this is a
        # root nothing legitimate produced — it still leaves the tick loop as
        # a typed refusal naming the node, never a bare `ValidationError`.
        raise UnusableResolutionError(
            _MSG_UNUSABLE_ROOT.format(node=node_name, detail=error.errors()[0]["msg"])
        ) from error
    return ResolvedNode(
        node=effective,
        runner_profile=_runner_profile(
            pinned, settings.get(NodeSetting.RUNNER.at(node_name))
        ),
        model=effective.model or "",
    )


def _runner_profile(pinned: Node, resolved: str | int | bool | None) -> str:
    """The profile this node runs as, refusing an unresolved role reference."""
    runner = pinned.runner or ""
    if isinstance(resolved, str) and not resolved.startswith(RUNNER_PREFIX):
        return resolved
    if not runner.startswith(RUNNER_PREFIX):
        return runner
    raise UnresolvedRunnerError(
        _MSG_UNRESOLVED_RUNNER.format(
            node=pinned.name,
            role=runner.removeprefix(RUNNER_PREFIX),
            key=NodeSetting.RUNNER.at(pinned.name),
        )
    )
