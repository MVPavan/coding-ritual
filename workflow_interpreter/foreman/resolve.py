"""Pure configuration resolution and root instantiation helpers."""

import hashlib
import types
from collections.abc import Mapping
from enum import StrEnum
from pathlib import Path
from typing import Annotated, Union, get_args, get_origin

from workflow_interpreter.bdio import ConfigSource, InstanceInput, ResolvedSetting
from workflow_interpreter.bdio.records import RootRecord
from workflow_interpreter.bdio.roots import MAX_INSTANCE_INPUT_BYTES
from workflow_interpreter.foreman.compose import Composition
from workflow_interpreter.schema.graph_index import build_index
from workflow_interpreter.schema.loader import load_graph
from workflow_interpreter.schema.models import GraphDefinition, Node
from workflow_interpreter.supervisor import INSTANCE_BRANCH_REF
from workflow_interpreter.supervisor.channels import pin_verifier_digests


class ResolutionError(ValueError):
    """A caller supplied a setting that has no declared configuration home."""


def _scalar_setting_type(
    annotation: object,
) -> type[str] | type[int] | type[bool] | None:
    """Return the persisted scalar representation for one optional node field."""
    origin = get_origin(annotation)
    if origin is Annotated:
        return _scalar_setting_type(get_args(annotation)[0])
    if origin in {Union, types.UnionType}:
        members = [
            member for member in get_args(annotation) if member is not type(None)
        ]
        return _scalar_setting_type(members[0]) if len(members) == 1 else None
    if annotation in {str, int, bool}:
        return annotation
    if isinstance(annotation, type) and issubclass(annotation, StrEnum):
        return str
    return None


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
    for node in definition.document.node:
        for field, field_info in Node.model_fields.items():
            setting_type = _scalar_setting_type(field_info.annotation)
            if field_info.is_required() or setting_type is None:
                continue
            key = f"node.{node.name}.{field}"
            allowed[key] = setting_type
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
        values.append(ResolvedSetting(key=key, value=value, source=source))
    return tuple(values)


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


def instantiate(
    composition: Composition,
    toml_path: Path,
    *,
    instance_key: str,
    brief_path: Path,
    allow_test_flags: bool,
    overrides: Mapping[str, object],
) -> RootRecord:
    """Pin graph, brief, config and branch base into one idempotent root."""
    definition = load_graph(toml_path, allow_test_flags=allow_test_flags)
    body = brief_path.read_text(encoding="utf-8")
    if not body:
        raise ResolutionError("task brief must not be empty")
    if len(body.encode("utf-8")) > MAX_INSTANCE_INPUT_BYTES:
        raise ResolutionError("task brief exceeds the instance input byte cap")
    source = build_index(
        definition.document, allow_test_flags=allow_test_flags
    ).sources.get("task_brief")
    if source is None or source.producer != "instance":
        raise ResolutionError("task_brief must be declared with producer=instance")
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
        instance_inputs=(
            InstanceInput(
                name="task_brief",
                sha256=hashlib.sha256(body.encode("utf-8")).hexdigest(),
                body=body,
            ),
        ),
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
