"""Views of static root settings and one activation's invocation pins."""

from __future__ import annotations

from collections.abc import Mapping
from types import MappingProxyType
from typing import TYPE_CHECKING, Final

import structlog
from pydantic import BaseModel, ConfigDict, ValidationError

from workflow_interpreter.bdio.records import RootRecord
from workflow_interpreter.bdio.roots import static_root_config
from workflow_interpreter.bdio.wire import (
    ActivationMetadata,
    BoundSetting,
    NodeSetting,
    activation_binding_digest,
    is_legacy_activation,
    resolved_settings,
)
from workflow_interpreter.contracts.execution import (
    EXECUTION_POLICY_KEY,
    MSG_POLICY_MISMATCH,
    CrewName,
    ExecutionPolicy,
    ExecutionRegistry,
    policy_for,
    tool_network_for,
)
from workflow_interpreter.contracts.sessions import (
    SessionMode,
    activation_policy_digest,
    context_cap_key,
    session_mode_key,
)
from workflow_interpreter.foreman.config import BindingApply, ResolvedCrewBinding
from workflow_interpreter.foreman.errors import (
    UnresolvedCrewError,
    UnusableResolutionError,
)
from workflow_interpreter.inspector.models import LaunchReceipt
from workflow_interpreter.inspector.paths import read_record
from workflow_interpreter.profiles.config import CREW_PREFIX, MODEL_VENDOR_DEFAULT
from workflow_interpreter.schema.models import Node, NodeKind

if TYPE_CHECKING:
    from workflow_interpreter.inspector.paths import WrapperPaths

_LOG: Final[structlog.stdlib.BoundLogger] = structlog.get_logger(__name__)

_MSG_UNRESOLVED_CREW: Final[str] = (
    "node {node!r} binds the crew role {role!r}, but the root's resolved "
    "config carries no usable {key!r} — the pinned resolution is incomplete "
    "and the instance cannot be executed from it (§3.1)"
)

_MSG_UNUSABLE_ROOT: Final[str] = (
    "the root's resolved config holds a value node {node!r} cannot execute "
    "under ({detail}) — the pinned resolution is corrupt (§3.1)"
)
_MSG_UNUSABLE_ROLE_BOUND_SETTING: Final[str] = (
    "role-bound task node {node!r} has no usable {field} in the root's resolved "
    "config — the pinned resolution is incomplete and the instance cannot be "
    "executed from it (§3.1)"
)
_MSG_UNUSABLE_ACTIVATION_PIN: Final[str] = (
    "activation for task node {node!r} has no usable {field} invocation pin"
)

_EFFECTIVE_FIELDS: Final[tuple[tuple[str, NodeSetting | BoundSetting], ...]] = (
    ("model", NodeSetting.MODEL),
    ("isolation", NodeSetting.ISOLATION),
    ("writes", NodeSetting.WRITES),
    ("token_budget", NodeSetting.TOKEN_BUDGET),
    ("context_budget_bytes", NodeSetting.CONTEXT_BUDGET_BYTES),
    ("max_wall", NodeSetting.MAX_WALL),
    ("stale_after", NodeSetting.STALE_AFTER),
    ("max_infra_retries", BoundSetting.MAX_INFRA_RETRIES),
    ("max_steers", BoundSetting.MAX_STEERS),
)
"""Node fields the execution path reads and `resolve()` can override.

`crew` and `effort` are deliberately absent: the pinned node names a ROLE
(`profile:<role>`), while the resolved key holds the profile that role was
bound to, and the graph schema has no effort field. They are carried as
`ResolvedNode.crew_profile` and `ResolvedNode.effort` instead. `allowed_paths`
is a list, which `resolve()` cannot express, so the pinned value stands.
"""

EFFECTIVE_FIELD_SETTINGS: Final[Mapping[str, NodeSetting | BoundSetting]] = (
    MappingProxyType(dict(_EFFECTIVE_FIELDS))
)
"""The resolved setting that overlays each effective `Node` scalar field."""


def effective_node(
    pinned: Node,
    settings: Mapping[str, str | int | bool],
    *,
    activation: ActivationMetadata | None = None,
    static_only: bool = False,
) -> Node:
    """Overlay one node's resolvable scalar settings onto its pinned body."""
    values = pinned.model_dump()
    updates = {
        field: settings[setting.at(pinned.name)]
        for field, setting in _EFFECTIVE_FIELDS
        if setting.at(pinned.name) in settings
        and (not static_only or field != "model")
        and (activation is None or field != "model")
    }
    mode_key = session_mode_key(pinned.name)
    if activation is not None:
        updates["model"] = activation.model
        updates["session_mode"] = activation.session_mode
        values.pop("session_reuse", None)
    elif not static_only and mode_key in settings:
        updates["session_mode"] = settings[mode_key]
        # A legacy pin keeps its original bytes, but the effective execution
        # model has one canonical authority: the resolved session_mode pin.
        values.pop("session_reuse", None)
    if pinned.execution_profile is not None:
        if "writes" in updates and updates["writes"] != pinned.writes:
            raise UnusableResolutionError(MSG_POLICY_MISMATCH)
        updates.pop("writes", None)
    return Node.model_validate(values | updates)


def resolved_static_node(root: RootRecord, node_name: str) -> Node:
    """Read only root-pinned graph and safety settings for bookkeeping paths."""
    pinned = root.index.nodes[node_name]
    try:
        return effective_node(
            pinned, resolved_settings(root.metadata), static_only=True
        )
    except ValidationError as error:
        raise UnusableResolutionError(
            _MSG_UNUSABLE_ROOT.format(node=node_name, detail=error.errors()[0]["msg"])
        ) from error


class ResolvedNode(BaseModel):
    """One task node as the execution path must read it.

    `node` is the pinned node overlaid with the root's resolved values, so a
    collaborator that already takes a `Node` (workspace isolation, wrapper
    limits, the task builder) needs no second accessor.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    node: Node
    crew_profile: str
    model: str
    effort: str | None
    execution_policy: ExecutionPolicy | None = None
    context_cap_tokens: int | None = None
    """Claude's pinned `--autocompact` threshold; None leaves the vendor default."""
    binding_apply: BindingApply = BindingApply.NEXT_TASK


def resolved_node(
    root: RootRecord,
    node_name: str,
    *,
    activation: ActivationMetadata | None = None,
) -> ResolvedNode:
    """Read root settings for a new mint, or recorded pins for an activation."""
    if activation is not None and is_legacy_activation(activation):
        # Pre-S3 rows ran under the root resolution, which S4 has not removed.
        activation = None
    elif activation is not None and (
        activation.policy_digest
        != activation_policy_digest(activation.execution_policy)
    ):
        raise UnusableResolutionError(
            _MSG_UNUSABLE_ACTIVATION_PIN.format(node=node_name, field="policy digest")
        )
    elif activation is not None and (
        activation.binding_digest != activation_binding_digest(activation)
    ):
        raise UnusableResolutionError(
            _MSG_UNUSABLE_ACTIVATION_PIN.format(node=node_name, field="binding digest")
        )
    pinned = root.index.nodes[node_name]
    settings = resolved_settings(root.metadata)
    # Re-validated rather than `model_copy`d: an override reaches here as a
    # bare scalar off the root's metadata, and `model_copy` skips the
    # validators that turn "worktree" into `IsolationMode` and refuse a
    # duration the pattern does not accept.
    try:
        effective = effective_node(pinned, settings, activation=activation)
    except ValidationError as error:
        # `resolve()` refuses these before the root is written, so this is a
        # root nothing legitimate produced — it still leaves the tick loop as
        # a typed refusal naming the node, never a bare `ValidationError`.
        raise UnusableResolutionError(
            _MSG_UNUSABLE_ROOT.format(node=node_name, detail=error.errors()[0]["msg"])
        ) from error
    crew_profile = (
        activation.crew_profile
        if activation is not None
        else _crew_profile(pinned, settings.get(NodeSetting.CREW.at(node_name)))
    )
    model = effective.model or ""
    effort = (
        activation.effort
        if activation is not None
        else _effort(node_name, settings.get(NodeSetting.EFFORT.at(node_name)))
    )
    if (
        activation is None
        and pinned.kind is NodeKind.TASK
        and (pinned.crew or "").startswith(CREW_PREFIX)
    ):
        model = _required_role_text(
            node_name, "model", settings.get(NodeSetting.MODEL.at(node_name))
        )
        if model == MODEL_VENDOR_DEFAULT:
            raise UnusableResolutionError(
                _MSG_UNUSABLE_ROLE_BOUND_SETTING.format(node=node_name, field="model")
            )
        effort = _required_role_text(
            node_name, "effort", settings.get(NodeSetting.EFFORT.at(node_name))
        )
    if activation is not None and pinned.kind is NodeKind.TASK:
        for field, value in (
            ("crew", crew_profile),
            ("model", model),
            ("effort", effort),
        ):
            if not isinstance(value, str) or not value.strip():
                raise UnusableResolutionError(
                    _MSG_UNUSABLE_ACTIVATION_PIN.format(node=node_name, field=field)
                )
    policy = None
    if activation is not None:
        policy = activation.execution_policy
        if pinned.execution_profile is not None and (
            policy is None
            or policy.name != pinned.execution_profile
            or policy.writes != effective.writes
        ):
            raise UnusableResolutionError(MSG_POLICY_MISMATCH)
    elif pinned.execution_profile is not None:
        raw = settings.get(EXECUTION_POLICY_KEY.format(node=node_name))
        if not isinstance(raw, str):
            raise UnusableResolutionError(MSG_POLICY_MISMATCH)
        try:
            policy = ExecutionPolicy.model_validate_json(raw)
        except ValidationError as error:
            raise UnusableResolutionError(MSG_POLICY_MISMATCH) from error
        if policy.name != pinned.execution_profile or policy.writes != effective.writes:
            raise UnusableResolutionError(MSG_POLICY_MISMATCH)
    cap = (
        activation.context_cap_tokens
        if activation is not None
        else settings.get(context_cap_key(node_name))
    )
    if cap is not None and (type(cap) is not int or cap <= 0):
        raise UnusableResolutionError(
            _MSG_UNUSABLE_ROOT.format(
                node=node_name, detail="context_cap_tokens is not a positive int"
            )
        )
    return ResolvedNode(
        node=effective,
        crew_profile=crew_profile,
        model=model,
        effort=effort,
        execution_policy=policy,
        context_cap_tokens=cap,
    )


def resolved_invocation(
    root: RootRecord,
    node_name: str,
    profiles: ExecutionRegistry,
    *,
    binding: ResolvedCrewBinding | None = None,
) -> ResolvedNode:
    """Resolve a new activation using the selected crew's registered capability."""
    pinned = root.index.nodes[node_name]
    if binding is not None and pinned.crew and pinned.crew.startswith(CREW_PREFIX):
        static = {
            item.key: item.value
            for item in static_root_config(
                root.definition, root.metadata.resolved_config
            )
        }
        effective = effective_node(pinned, static, static_only=True)
        crew = static.get(NodeSetting.CREW.at(node_name), binding.profile)
        model = static.get(NodeSetting.MODEL.at(node_name), binding.model)
        effort = static.get(NodeSetting.EFFORT.at(node_name), binding.effort)
        mode = static.get(
            session_mode_key(node_name), binding.session_mode or SessionMode.RESUME
        )
        cap = static.get(context_cap_key(node_name))
        if binding.context_cap_tokens is not None:
            if crew != CrewName.CLAUDE:
                _LOG.warning(
                    "foreman.context_cap_dropped",
                    node=node_name,
                    crew=crew,
                    context_cap_tokens=binding.context_cap_tokens,
                )
            elif cap is None:
                cap = binding.context_cap_tokens
        crew = _required_role_text(node_name, "crew", crew)
        model = _required_role_text(node_name, "model", model)
        effort = _required_role_text(node_name, "effort", effort)
        if model == MODEL_VENDOR_DEFAULT:
            raise UnusableResolutionError(
                _MSG_UNUSABLE_ROLE_BOUND_SETTING.format(node=node_name, field="model")
            )
        if cap is not None and (type(cap) is not int or cap <= 0):
            raise UnusableResolutionError(
                _MSG_UNUSABLE_ROOT.format(
                    node=node_name, detail="context_cap_tokens is not a positive int"
                )
            )
        try:
            values = effective.model_dump()
            values.pop("session_reuse", None)
            node = Node.model_validate(values | {"model": model, "session_mode": mode})
        except ValidationError as error:
            raise UnusableResolutionError(
                _MSG_UNUSABLE_ROOT.format(
                    node=node_name, detail=error.errors()[0]["msg"]
                )
            ) from error
        view = ResolvedNode(
            node=node,
            crew_profile=crew,
            model=model,
            effort=effort,
            context_cap_tokens=cap,
        )
    else:
        view = resolved_node(root, node_name)
    if view.node.execution_profile is None:
        return view
    return view.model_copy(
        update={
            "execution_policy": policy_for(
                view.node.execution_profile,
                tool_network_for(view.crew_profile, profiles),
            )
        }
    )


def _crew_profile(pinned: Node, resolved: str | int | bool | None) -> str:
    """The profile this node runs as, refusing an unresolved role reference."""
    crew = pinned.crew or ""
    if isinstance(resolved, str) and not resolved.startswith(CREW_PREFIX):
        return resolved
    if not crew.startswith(CREW_PREFIX):
        return crew
    raise UnresolvedCrewError(
        _MSG_UNRESOLVED_CREW.format(
            node=pinned.name,
            role=crew.removeprefix(CREW_PREFIX),
            key=NodeSetting.CREW.at(pinned.name),
        )
    )


def _effort(node_name: str, resolved: str | int | bool | None) -> str | None:
    """Read an optional per-role effort from the pinned resolution."""
    if resolved is None:
        return None
    if isinstance(resolved, str):
        return resolved
    raise UnusableResolutionError(
        _MSG_UNUSABLE_ROOT.format(node=node_name, detail="effort is not a string")
    )


def _required_role_text(
    node_name: str, field: str, resolved: str | int | bool | None
) -> str:
    """Read a non-blank model or effort role bindings must pin."""
    if not isinstance(resolved, str) or not resolved.strip():
        raise UnusableResolutionError(
            _MSG_UNUSABLE_ROLE_BOUND_SETTING.format(node=node_name, field=field)
        )
    return resolved


def execution_status(
    paths: WrapperPaths, activation_ids: tuple[str, ...]
) -> dict[str, object]:
    """Expose recorded launch policy without inferring enforcement from live config."""

    result: dict[str, object] = {}
    for activation_id in activation_ids:
        receipt = read_record(paths.receipt(activation_id), LaunchReceipt)
        if receipt is not None and receipt.execution_grants is not None:
            result[activation_id] = receipt.execution_grants.policy.model_dump(
                mode="json"
            )
    return result
