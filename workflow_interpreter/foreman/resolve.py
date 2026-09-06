"""Pure configuration resolution and root instantiation helpers."""

import hashlib
from collections.abc import Mapping
from pathlib import Path
from typing import Final

from pydantic import ValidationError

from workflow_interpreter.bdio import (
    BoundSetting,
    ConfigSource,
    InstanceInput,
    NodeSetting,
    ResolvedSetting,
)
from workflow_interpreter.bdio.records import RootRecord
from workflow_interpreter.bdio.roots import MAX_INSTANCE_INPUT_BYTES
from workflow_interpreter.foreman.compose import Composition
from workflow_interpreter.foreman.errors import ResolutionError
from workflow_interpreter.profiles.config import RUNNER_PREFIX
from workflow_interpreter.schema.graph_index import build_index
from workflow_interpreter.schema.loader import load_graph
from workflow_interpreter.schema.models import (
    PRODUCER_INSTANCE,
    GraphDefinition,
    Node,
    NodeKind,
)
from workflow_interpreter.supervisor import INSTANCE_BRANCH_REF
from workflow_interpreter.supervisor.channels import pin_verifier_digests

RUNNER_FIELD: Final[str] = "runner"

MSG_UNUSABLE: Final[str] = (
    "unusable value for {key!r}: {value!r} is not something the node's own "
    "field accepts ({detail})"
)
MSG_ROLE_REFERENCE: Final[str] = (
    "{key!r} from {source} is a `profile:<role>` reference; only the foreman "
    "config's roles map resolves those, so state the profile itself"
)
MSG_RUNNER_WITHOUT_MODEL: Final[str] = (
    "{key!r} from {source} chooses a runner without {model!r} from the same "
    "source — the model would stay the graph role's, a pairing nobody stated"
)

TASK_SETTING_TYPES: Final[
    Mapping[NodeSetting | BoundSetting, type[str | int | bool]]
] = {
    NodeSetting.RUNNER: str,
    NodeSetting.MODEL: str,
    NodeSetting.ISOLATION: str,
    NodeSetting.MAX_WALL: str,
    NodeSetting.STALE_AFTER: str,
    NodeSetting.WRITES: bool,
    NodeSetting.TOKEN_BUDGET: int,
    BoundSetting.MAX_INFRA_RETRIES: int,
    BoundSetting.MAX_STEERS: int,
}
"""The closed task-resolution vocabulary.

`instructions`, `region`, `gate_type`, and `binds` are never configurable:
they change what the graph MEANS under one content hash (ADR 0002), and an
ignored `gate_type` would look like a removed approval (§9).
"""


def resolve(
    definition: GraphDefinition,
    config: Mapping[str, object],
    overrides: Mapping[str, object],
) -> tuple[ResolvedSetting, ...]:
    """Resolve graph defaults, project settings and explicit instance overrides."""
    defaults: dict[str, str | int | bool | None] = {
        "instance.max_total_activations": definition.document.instance.max_total_activations
    }
    allowed: dict[str, type[str | int | bool]] = {"instance.max_total_activations": int}
    owners: dict[str, tuple[Node, str]] = {}
    for node in definition.document.node:
        if node.kind is not NodeKind.TASK:
            continue
        for setting, setting_type in TASK_SETTING_TYPES.items():
            key = setting.at(node.name)
            field = setting.value.rsplit(".", maxsplit=1)[-1]
            allowed[key] = setting_type
            owners[key] = (node, field)
            value = getattr(node, field)
            if value is not None:
                defaults[key] = value.value if hasattr(value, "value") else value
    for region in definition.document.region:
        key = f"region.{region.name}.max_entries"
        allowed[key] = int
        if region.max_entries is not None:
            defaults[key] = region.max_entries
    unknown_project = set(config) - set(allowed)
    if unknown_project:
        raise ResolutionError(
            f"unknown project config keys: {', '.join(sorted(unknown_project))}"
        )
    unknown_override = set(overrides) - set(allowed)
    if unknown_override:
        raise ResolutionError(
            f"unknown override keys: {', '.join(sorted(unknown_override))}"
        )
    values: list[ResolvedSetting] = []
    for key in sorted(allowed):
        if key in overrides:
            value = overrides[key]
            source = ConfigSource.INSTANCE_OVERRIDE
        elif key in config:
            value = config[key]
            source = ConfigSource.PROJECT_CONFIG
        else:
            value = defaults.get(key)
            source = ConfigSource.GRAPH_DEFAULT
        if value is None:
            continue
        if type(value) is not allowed[key]:
            raise ResolutionError(f"unsupported value for {key!r}")
        owner = owners.get(key)
        if owner is not None and source is not ConfigSource.GRAPH_DEFAULT:
            owner_node, owner_field = owner
            _refuse_unusable(owner_node, owner_field, key, value)
            if owner_field == RUNNER_FIELD:
                _refuse_half_bound_runner(
                    owner_node.name,
                    value,
                    source,
                    overrides if source is ConfigSource.INSTANCE_OVERRIDE else config,
                )
        values.append(ResolvedSetting(key=key, value=value, source=source))
    return tuple(values)


def _refuse_unusable(node: Node, field: str, key: str, value: str | int | bool) -> None:
    """Refuse a value the node's OWN field cannot hold, before the root exists.

    The scalar type check above accepts `max_wall = "banana"` and
    `isolation = "sandbox"`: both are `str`. A root is immutable, so a value
    only the execution view would reject makes an instance permanently
    un-tickable — the refusal has to happen here (cr-7h8 review).
    """
    try:
        Node.model_validate(node.model_dump() | {field: value})
    except ValidationError as error:
        raise ResolutionError(
            MSG_UNUSABLE.format(key=key, value=value, detail=error.errors()[0]["msg"])
        ) from error


def _refuse_half_bound_runner(
    node_name: str,
    value: str | int | bool,
    source: ConfigSource,
    supplied: Mapping[str, object],
) -> None:
    """Keep a configured runner a COMPLETE, already-resolved binding (§3.1).

    A `profile:<role>` value is a role reference, and only `_resolved_config`
    resolves those — accepting one here pins a root whose execution view has
    no runner to read. A runner without its model is the other half: the
    profile would come from config while the model stayed the graph role's,
    a pairing nobody stated (cr-7h8 review).
    """
    if isinstance(value, str) and value.startswith(RUNNER_PREFIX):
        raise ResolutionError(
            MSG_ROLE_REFERENCE.format(
                key=NodeSetting.RUNNER.at(node_name), source=source.value
            )
        )
    if NodeSetting.MODEL.at(node_name) not in supplied:
        raise ResolutionError(
            MSG_RUNNER_WITHOUT_MODEL.format(
                key=NodeSetting.RUNNER.at(node_name),
                model=NodeSetting.MODEL.at(node_name),
                source=source.value,
            )
        )


def ensure_instance_branch(composition: Composition, root: RootRecord) -> None:
    """Create the root's branch once, after proving its base commit exists."""
    base = root.metadata.instance_base_commit
    if base is None or not composition.git.commit_exists(
        base, cwd=composition.config.repo_root
    ):
        raise ResolutionError("instance base commit is missing")
    branch = INSTANCE_BRANCH_REF.format(root_id=root.root_id)
    if composition.git.ref_target(branch, cwd=composition.config.repo_root) is None:
        composition.git.update_ref(branch, base, cwd=composition.config.repo_root)


def _pinned_instance_inputs(
    definition: GraphDefinition,
    instance_inputs: Mapping[str, Path],
    *,
    allow_test_flags: bool,
) -> tuple[InstanceInput, ...]:
    """Read and pin every named instance input the graph declares.

    Every refusal is raised here, before `instantiate` reaches bd: a root is
    immutable once written (§3.1), so an input the graph never declared or a
    body `create_root` would reject must cost nothing but an error.
    """
    sources = build_index(
        definition.document, allow_test_flags=allow_test_flags
    ).sources
    declared = {
        name for name, source in sources.items() if source.producer == PRODUCER_INSTANCE
    }
    undeclared = sorted(set(instance_inputs) - declared)
    if undeclared:
        raise ResolutionError(
            "inputs not declared with producer=instance: " + ", ".join(undeclared)
        )
    absent = sorted(
        name
        for name in declared
        if not sources[name].optional and name not in instance_inputs
    )
    if absent:
        raise ResolutionError("missing required instance inputs: " + ", ".join(absent))
    pinned: list[InstanceInput] = []
    # Sorted, so the pinned tuple — and the root identity it feeds — does not
    # depend on the order the caller happened to name its inputs in.
    for name in sorted(instance_inputs):
        body = instance_inputs[name].read_text(encoding="utf-8")
        size = len(body.encode("utf-8"))
        if not body:
            raise ResolutionError(f"instance input {name} must not be empty")
        if size > MAX_INSTANCE_INPUT_BYTES:
            raise ResolutionError(
                f"instance input {name} exceeds the {MAX_INSTANCE_INPUT_BYTES}-byte cap"
            )
        pinned.append(
            InstanceInput(
                name=name,
                sha256=hashlib.sha256(body.encode("utf-8")).hexdigest(),
                body=body,
            )
        )
    total = sum(len(item.body.encode("utf-8")) for item in pinned)
    if total > MAX_INSTANCE_INPUT_BYTES:
        raise ResolutionError(
            f"instance inputs are {total} bytes, over the aggregate "
            f"{MAX_INSTANCE_INPUT_BYTES}-byte cap `create_root` enforces"
        )
    return tuple(pinned)


def instantiate(
    composition: Composition,
    toml_path: Path,
    *,
    instance_key: str,
    instance_inputs: Mapping[str, Path],
    allow_test_flags: bool,
    overrides: Mapping[str, object],
) -> RootRecord:
    """Pin graph, inputs, config and branch base into one idempotent root."""
    definition = load_graph(toml_path, allow_test_flags=allow_test_flags)
    pinned = _pinned_instance_inputs(
        definition, instance_inputs, allow_test_flags=allow_test_flags
    )
    roles = {
        node.name: node.runner.removeprefix("profile:")
        for node in definition.document.node
        if node.runner is not None and node.runner.startswith("profile:")
    }
    missing = sorted(set(roles.values()) - set(composition.config.roles))
    if missing:
        raise ResolutionError(f"unknown runner roles: {', '.join(missing)}")
    base = composition.git.head_commit(cwd=composition.config.repo_root)
    root = composition.store.create_root(
        instance_key=instance_key,
        definition=definition,
        resolved_config=_resolved_config(composition, definition, overrides),
        instance_inputs=pinned,
        allow_test_flags=allow_test_flags,
        instance_base_commit=base,
    )
    ensure_instance_branch(composition, root)
    return root


def _resolved_config(
    composition: Composition,
    definition: GraphDefinition,
    overrides: Mapping[str, object],
) -> tuple[ResolvedSetting, ...]:
    """Apply role bindings and verifier pins before the immutable root write."""
    settings = {
        item.key: item
        for item in resolve(definition, composition.config.project_config, overrides)
    }
    for node in definition.document.node:
        if node.runner is None or not node.runner.startswith("profile:"):
            continue
        binding = composition.config.roles[node.runner.removeprefix("profile:")]
        runner_key = f"node.{node.name}.runner"
        model_key = f"node.{node.name}.model"
        if settings.get(runner_key) is None or (
            settings[runner_key].source is ConfigSource.GRAPH_DEFAULT
        ):
            settings[runner_key] = ResolvedSetting(
                key=runner_key,
                value=binding.profile,
                source=ConfigSource.ROLE_BINDING,
            )
        if settings.get(model_key) is None or (
            settings[model_key].source is ConfigSource.GRAPH_DEFAULT
        ):
            settings[model_key] = ResolvedSetting(
                key=model_key,
                value=binding.model,
                source=ConfigSource.ROLE_BINDING,
            )
    settings.update(
        {
            item.key: item
            for item in pin_verifier_digests(
                definition.document, composition.config.repo_root
            )
        }
    )
    return tuple(settings[key] for key in sorted(settings))
