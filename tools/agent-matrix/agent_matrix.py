#!/usr/bin/env python3
"""Deterministic Agent Matrix catalog validation and Codex evidence tooling."""

import argparse
from collections.abc import Mapping, Sequence
from datetime import datetime
import json
import os
from pathlib import Path
import re
import subprocess
import sys

import yaml


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CATALOG_PATH = (
    REPO_ROOT
    / "docs/research/codebases/subagent-runtimes/agent-matrix-values.yaml"
)


class CatalogError(ValueError):
    """Raised when the Agent Matrix catalog or a selection is invalid."""


class InventoryError(ValueError):
    """Raised when the live Codex model inventory is malformed."""


class CoverageError(ValueError):
    """Raised when results do not cover a plan exactly once."""


class _UniqueKeyLoader(yaml.SafeLoader):
    pass


def _construct_unique_mapping(loader, node, deep=False):
    mapping = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in mapping:
            raise CatalogError(f"duplicate key: {key!r}")
        mapping[key] = loader.construct_object(value_node, deep=deep)
    return mapping


_UniqueKeyLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
    _construct_unique_mapping,
)


def load_catalog(path):
    """Load a YAML catalog while rejecting duplicate mapping keys."""
    try:
        with Path(path).open(encoding="utf-8") as stream:
            catalog = yaml.load(stream, Loader=_UniqueKeyLoader)
    except yaml.YAMLError as exc:
        raise CatalogError(f"invalid YAML: {exc}") from exc
    if not isinstance(catalog, dict):
        raise CatalogError("catalog root must be a mapping")
    return catalog


def _require_mapping(value, label):
    if not isinstance(value, Mapping):
        raise CatalogError(f"{label} must be a mapping")
    return value


def _require_unique_strings(values, label):
    if not isinstance(values, Sequence) or isinstance(values, (str, bytes)):
        raise CatalogError(f"{label} must be a list")
    if any(not isinstance(value, str) or not value for value in values):
        raise CatalogError(f"{label} must contain non-empty strings")
    if len(values) != len(set(values)):
        raise CatalogError(f"{label} contains duplicate values")
    return list(values)


def validate_catalog(catalog):
    """Validate the compact catalog shape needed by the shared CLI."""
    catalog = _require_mapping(catalog, "catalog")
    if catalog.get("version") != 2:
        raise CatalogError("catalog version must be 2")
    models = _require_mapping(catalog.get("models"), "models")
    if not {"claude", "codex"} <= set(models):
        raise CatalogError("models must declare claude and codex providers")
    for provider, values in models.items():
        if not isinstance(provider, str) or not provider:
            raise CatalogError("provider names must be non-empty strings")
        _require_unique_strings(values, f"models.{provider}")

    effort_levels = _require_mapping(
        catalog.get("effort_levels"), "effort_levels"
    )
    contexts = _require_mapping(catalog.get("context_modes"), "context_modes")
    capabilities = _require_mapping(catalog.get("capabilities"), "capabilities")
    skills = _require_mapping(catalog.get("skills"), "skills")
    for name, value in effort_levels.items():
        if not isinstance(name, str) or not name:
            raise CatalogError("effort level names must be non-empty strings")
        if isinstance(value, list):
            _require_unique_strings(value, f"effort_levels.{name}")
        elif not isinstance(value, Mapping):
            raise CatalogError(f"effort_levels.{name} must be a mapping or list")
    if not contexts:
        raise CatalogError("context_modes must not be empty")
    for name, context in contexts.items():
        context = _require_mapping(context, f"context_modes.{name}")
        codex = _require_mapping(
            context.get("codex"), f"context_modes.{name}.codex"
        )
        if codex.get("field") != "fork_turns":
            raise CatalogError(
                f"context_modes.{name}.codex.field must be 'fork_turns'"
            )
        if "value" not in codex and not (
            codex.get("value_type") == "positive_integer_string"
            and isinstance(codex.get("example"), str)
            and re.fullmatch(r"[1-9][0-9]*", codex["example"])
        ):
            raise CatalogError(
                f"context_modes.{name}.codex must declare a value or positive example"
            )

    for name in ("skills", "mcp_servers", "codex"):
        _require_mapping(capabilities.get(name), f"capabilities.{name}")
    for name, spec in capabilities["codex"].items():
        spec = _require_mapping(spec, f"capabilities.codex.{name}")
        if "values" in spec:
            _require_unique_strings(
                spec["values"], f"capabilities.codex.{name}.values"
            )
        if "named_values" in spec:
            _require_unique_strings(
                spec["named_values"],
                f"capabilities.codex.{name}.named_values",
            )
    approval = _require_mapping(
        capabilities["codex"].get("approval_policy"),
        "capabilities.codex.approval_policy",
    )
    _require_unique_strings(
        approval.get("named_values"),
        "capabilities.codex.approval_policy.named_values",
    )
    structured = _require_mapping(
        approval.get("structured_value"),
        "capabilities.codex.approval_policy.structured_value",
    )
    granular = _require_mapping(
        structured.get("granular"),
        "capabilities.codex.approval_policy.structured_value.granular",
    )
    if set(granular) != set(GRANULAR_APPROVAL_FIELDS) or any(
        value != "boolean" for value in granular.values()
    ):
        raise CatalogError("granular approval shape must declare all boolean fields")

    common_skills = [
        name for name, value in skills.items() if isinstance(value, Mapping)
    ]
    for provider in models:
        provider_skills = skills.get(provider, [])
        _require_unique_strings(provider_skills, f"skills.{provider}")
        duplicates = set(common_skills) & set(provider_skills)
        if duplicates:
            raise CatalogError(
                f"skills.{provider} duplicates common skills: {sorted(duplicates)}"
            )
    codex_skill_spec = _require_mapping(
        capabilities["skills"].get("codex"),
        "capabilities.skills.codex",
    )
    if codex_skill_spec.get("values_from") != "skills":
        raise CatalogError("capabilities.skills.codex must use the skills registry")
    codex_mcp_spec = _require_mapping(
        capabilities["mcp_servers"].get("codex"),
        "capabilities.mcp_servers.codex",
    )
    _require_unique_strings(
        codex_mcp_spec.get("values"),
        "capabilities.mcp_servers.codex.values",
    )
    return catalog


def _allowed_efforts(catalog, provider):
    efforts = []
    for name, value in catalog["effort_levels"].items():
        if isinstance(value, Mapping):
            efforts.append(name)
    provider_values = catalog["effort_levels"].get(provider, [])
    if isinstance(provider_values, list):
        efforts.extend(provider_values)
    return efforts


def _allowed_skills(catalog, provider):
    skills = []
    for name, value in catalog["skills"].items():
        if isinstance(value, Mapping):
            skills.append(name)
    provider_values = catalog["skills"].get(provider, [])
    if isinstance(provider_values, list):
        skills.extend(provider_values)
    return skills


def _capability_spec(catalog, provider, name):
    capabilities = catalog["capabilities"]
    shared = capabilities.get(name)
    if isinstance(shared, Mapping) and provider in shared:
        return shared[provider]
    provider_capabilities = capabilities.get(provider, {})
    if isinstance(provider_capabilities, Mapping) and name in provider_capabilities:
        return provider_capabilities[name]
    raise CatalogError(f"unknown {provider} capability: {name!r}")


def _validate_structured_capability(name, value, shape):
    if not isinstance(value, Mapping):
        raise CatalogError(f"capability {name!r} must be a mapping")
    unknown_outer = set(value) - set(shape)
    if unknown_outer:
        raise CatalogError(
            f"capability {name!r} has unknown fields: {sorted(unknown_outer)}"
        )
    if not value:
        raise CatalogError(f"capability {name!r} must not be empty")
    for section, section_value in value.items():
        fields = _require_mapping(shape[section], f"{name}.{section} shape")
        selected = _require_mapping(section_value, f"{name}.{section}")
        if not selected:
            raise CatalogError(f"capability {name!r} must not be empty")
        unknown = set(selected) - set(fields)
        if unknown:
            raise CatalogError(
                f"capability {name!r} has unknown fields: {sorted(unknown)}"
            )
        for field, field_value in selected.items():
            if fields[field] == "boolean" and type(field_value) is not bool:
                raise CatalogError(f"{name}.{section}.{field} must be boolean")


def _validate_capability_value(catalog, provider, name, value):
    spec = _require_mapping(
        _capability_spec(catalog, provider, name),
        f"capability {name!r}",
    )
    structured = spec.get("structured_value")
    if structured is not None and isinstance(value, Mapping):
        _validate_structured_capability(name, value, structured)
        return

    allowed = spec.get("values")
    if allowed is None:
        allowed = spec.get("named_values")
    if allowed is None and spec.get("values_from") == "skills":
        allowed = _allowed_skills(catalog, provider)
    if allowed is None:
        raise CatalogError(f"capability {name!r} has no selectable scalar values")

    if isinstance(value, list) and name not in {"skills", "mcp_servers"}:
        raise CatalogError(f"capability {name!r} is scalar, not list-valued")
    selected_values = value if isinstance(value, list) else [value]
    if not selected_values:
        raise CatalogError(f"capability {name!r} selection must not be empty")
    if len(selected_values) != len(set(selected_values)):
        raise CatalogError(f"capability {name!r} contains duplicate selections")
    for selected in selected_values:
        if selected not in allowed:
            raise CatalogError(
                f"unknown value for {provider} capability {name!r}: {selected!r}"
            )


def validate_selection(
    catalog,
    *,
    provider,
    model=None,
    effort=None,
    context=None,
    capabilities=None,
    skills=None,
):
    """Reject any matrix selection that is not declared by the catalog."""
    validate_catalog(catalog)
    if provider not in catalog["models"]:
        raise CatalogError(f"unknown provider: {provider!r}")
    if model is not None and model not in catalog["models"][provider]:
        raise CatalogError(f"unknown {provider} model: {model!r}")
    if effort is not None and effort not in _allowed_efforts(catalog, provider):
        raise CatalogError(f"unknown {provider} effort: {effort!r}")
    if context is not None:
        context_spec = catalog["context_modes"].get(context)
        if not isinstance(context_spec, Mapping) or provider not in context_spec:
            raise CatalogError(f"unknown {provider} context: {context!r}")
    for name, value in (capabilities or {}).items():
        _validate_capability_value(catalog, provider, name, value)
    allowed_skills = _allowed_skills(catalog, provider)
    selected_skills = skills or []
    if len(selected_skills) != len(set(selected_skills)):
        raise CatalogError("skills selection contains duplicates")
    for skill in selected_skills:
        if skill not in allowed_skills:
            raise CatalogError(f"unknown {provider} skill: {skill!r}")


def parse_codex_models(text):
    """Parse stdout from ``codex debug models`` as strict JSON."""
    try:
        payload = json.loads(text)
    except (json.JSONDecodeError, TypeError) as exc:
        raise InventoryError(
            "codex debug models stdout must contain strict JSON only"
        ) from exc
    if not isinstance(payload, Mapping) or not isinstance(
        payload.get("models"), list
    ):
        raise InventoryError("model inventory must contain a models list")

    models = []
    seen_models = set()
    for index, raw_model in enumerate(payload["models"]):
        if not isinstance(raw_model, Mapping):
            raise InventoryError(f"models[{index}] must be a mapping")
        slug = raw_model.get("slug")
        if not isinstance(slug, str) or not slug:
            raise InventoryError(f"models[{index}].slug must be a non-empty string")
        if slug in seen_models:
            raise InventoryError(f"duplicate model slug: {slug!r}")
        seen_models.add(slug)

        raw_efforts = raw_model.get("supported_reasoning_levels")
        if raw_efforts is None:
            raw_efforts = raw_model.get("supported_reasoning_efforts")
        if not isinstance(raw_efforts, list):
            raise InventoryError(
                f"model {slug!r} must advertise supported reasoning levels"
            )
        efforts = []
        for raw_effort in raw_efforts:
            effort = (
                raw_effort.get("effort")
                if isinstance(raw_effort, Mapping)
                else raw_effort
            )
            if not isinstance(effort, str) or not effort:
                raise InventoryError(
                    f"model {slug!r} has an invalid reasoning effort"
                )
            if effort in efforts:
                raise InventoryError(
                    f"model {slug!r} advertises duplicate effort {effort!r}"
                )
            efforts.append(effort)

        if "visibility" in raw_model:
            visible = raw_model["visibility"] == "list"
        else:
            visible = raw_model.get("visible", True) is True
        if visible and not efforts:
            raise InventoryError(
                f"visible model {slug!r} advertises no reasoning efforts"
            )
        models.append({"slug": slug, "visible": visible, "efforts": efforts})
    return models


TERMINAL_STATUSES = (
    "pass",
    "fail",
    "unsupported",
    "untestable",
    "infra_error",
)

GRANULAR_APPROVAL_FIELDS = (
    "sandbox_approval",
    "rules",
    "skill_approval",
    "request_permissions",
    "mcp_elicitations",
)

OBSERVATION_FIELDS = frozenset(
    {
        "case_id",
        "status",
        "reason",
        "tool_accepted",
        "backend_accepted",
        "parse_only",
        "evidence",
        "stderr",
        "returncode",
        "command",
        "config_override",
        "catalog_visible",
        "tool_exposed",
    }
)

OBSERVATION_RESERVED_FIELDS = frozenset(
    {
        "rollout",
        "observed",
        "evidence_source",
    }
)


def _identifier(value):
    identifier = re.sub(r"[^a-z0-9]+", "_", str(value).lower()).strip("_")
    return identifier or "empty"


def _new_case(kind, dimension, requested, expected, *, visible=None, exposed=None):
    case_id = "_".join(
        [
            "codex",
            _identifier(kind),
            _identifier(dimension),
            _identifier(requested.get("model", "")),
            _identifier(requested.get("reasoning_effort", "")),
            _identifier(requested.get("field", "")),
            _identifier(requested.get("value", "")),
        ]
    )
    case_id = re.sub(r"_+", "_", case_id).rstrip("_")
    requested_task_name = requested.get("task_name")
    task_name = (
        requested_task_name
        if isinstance(requested_task_name, str)
        and re.fullmatch(r"[a-z0-9_]+", requested_task_name)
        else case_id
    )
    return {
        "case_id": case_id,
        "task_name": task_name,
        "agent_path": f"/root/{task_name}",
        "kind": kind,
        "dimension": dimension,
        "requested": requested,
        "expected": expected,
        "catalog_visible": visible,
        "tool_exposed": exposed,
        "tool_accepted": None,
        "backend_accepted": None,
    }


def _append_case(cases, *args, **kwargs):
    case = _new_case(*args, **kwargs)
    existing = {item["case_id"] for item in cases}
    if case["case_id"] in existing:
        suffix = 2
        base = case["case_id"]
        while f"{base}_{suffix}" in existing:
            suffix += 1
        case["case_id"] = f"{base}_{suffix}"
        if case["task_name"] == base:
            case["task_name"] = case["case_id"]
            case["agent_path"] = f"/root/{case['case_id']}"
    cases.append(case)


def _add_model_effort_cases(cases, catalog, models, tool_models):
    visible_models = sorted(
        (model for model in models if model["visible"]),
        key=lambda model: model["slug"],
    )
    if not visible_models:
        raise InventoryError("model inventory contains no visible models")
    effort_order = {
        effort: index
        for index, effort in enumerate(_allowed_efforts(catalog, "codex"))
    }
    for model in visible_models:
        if not model.get("efforts"):
            raise InventoryError(
                f"visible model {model.get('slug')!r} advertises no reasoning efforts"
            )
        validate_selection(catalog, provider="codex", model=model["slug"])
        efforts = sorted(
            model["efforts"],
            key=lambda effort: (effort_order.get(effort, len(effort_order)), effort),
        )
        for effort in efforts:
            validate_selection(catalog, provider="codex", effort=effort)
            requested = {
                "message": "Reply with exactly: agent_matrix_ok",
                "fork_turns": "none",
                "model": model["slug"],
                "reasoning_effort": effort,
            }
            dimension = f"{model['slug']}_{effort}"
            _append_case(
                cases,
                "model_effort",
                dimension,
                requested,
                {"outcome": "accept", "evidence": "first_turn_context"},
                visible=True,
                exposed=model["slug"] in tool_models,
            )
    return [model["slug"] for model in visible_models]


def _add_tracer_case(cases):
    candidates = [
        case
        for case in cases
        if case["kind"] == "model_effort" and case["tool_exposed"]
    ]
    if not candidates:
        return
    tracer_source = next(
        (
            case
            for case in candidates
            if case["requested"]["model"] == "gpt-5.6-terra"
            and case["requested"]["reasoning_effort"] == "low"
        ),
        candidates[0],
    )
    requested = dict(tracer_source["requested"])
    _append_case(
        cases,
        "tracer",
        "effective_model_effort",
        requested,
        {"outcome": "accept", "evidence": "first_turn_context"},
        visible=True,
        exposed=True,
    )
    tracer = cases[-1]
    model_name = requested["model"].removeprefix("gpt-5.6-")
    tracer["task_name"] = (
        f"am_tracer_{_identifier(model_name)}_"
        f"{_identifier(requested['reasoning_effort'])}"
    )
    tracer["agent_path"] = f"/root/{tracer['task_name']}"


def _codex_scalar_capabilities(catalog):
    capabilities = catalog["capabilities"]
    for name, shared_spec in capabilities.items():
        if name == "codex" or not isinstance(shared_spec, Mapping):
            continue
        spec = shared_spec.get("codex")
        if not isinstance(spec, Mapping):
            continue
        if spec.get("values_from") == "skills":
            values = _allowed_skills(catalog, "codex")
        else:
            values = spec.get("values", [])
        for value in values:
            yield name, value

    for name, spec in capabilities.get("codex", {}).items():
        if not isinstance(spec, Mapping):
            continue
        for value in spec.get("values", []):
            yield name, value
        for value in spec.get("named_values", []):
            yield name, value


def _add_config_cases(cases, catalog):
    for name, value in _codex_scalar_capabilities(catalog):
        _append_case(
            cases,
            "config",
            name,
            {"field": name, "value": value},
            {"outcome": "parse_accept", "execution": "parse_only"},
        )

    approval = catalog["capabilities"]["codex"]["approval_policy"]
    granular = approval["structured_value"]["granular"]
    for field in sorted(granular):
        for value in (False, True):
            _append_case(
                cases,
                "config",
                "approval_policy.granular",
                {"field": field, "value": value},
                {"outcome": "parse_accept", "execution": "parse_only"},
            )


def _add_context_cases(cases, catalog):
    for name in sorted(catalog["context_modes"]):
        spec = catalog["context_modes"][name].get("codex")
        if not isinstance(spec, Mapping):
            continue
        requested = {"message": "Reply with exactly: agent_matrix_ok"}
        if "value" in spec:
            requested[spec["field"]] = spec["value"]
        else:
            requested[spec["field"]] = spec.get("example", "1")
        _append_case(
            cases,
            "context",
            name,
            requested,
            {"outcome": "accept", "evidence": "runtime"},
        )


def _add_spawn_contract_cases(
    cases,
    reference_model,
    reference_effort,
    full_history_model,
):
    valid_message = "Reply with exactly: agent_matrix_ok"
    contract_cases = [
        (
            "spawn_contract",
            "task_name_valid",
            {"task_name": "valid_task_1", "message": valid_message},
            "accept",
        ),
        (
            "negative",
            "task_name_blank",
            {"task_name": "", "message": valid_message},
            "reject",
        ),
        (
            "negative",
            "task_name_reserved",
            {"task_name": "root", "message": valid_message},
            "reject",
        ),
        (
            "negative",
            "task_name_invalid_characters",
            {"task_name": "bad-name", "message": valid_message},
            "reject",
        ),
        (
            "spawn_contract",
            "message_valid",
            {"task_name": "message_valid", "message": valid_message},
            "accept",
        ),
        (
            "negative",
            "message_blank",
            {"task_name": "message_blank", "message": ""},
            "reject",
        ),
        (
            "spawn_contract",
            "agent_type_default",
            {"message": valid_message, "fork_turns": "none"},
            "accept",
        ),
        (
            "spawn_contract",
            "agent_type_configured",
            {
                "message": valid_message,
                "fork_turns": "none",
                "agent_type": "code-reviewer",
            },
            "accept",
        ),
        (
            "negative",
            "agent_type_unknown",
            {
                "message": valid_message,
                "fork_turns": "none",
                "agent_type": "unknown_role",
            },
            "reject",
        ),
        (
            "spawn_contract",
            "agent_type_role_pinning",
            {
                "message": valid_message,
                "fork_turns": "none",
                "agent_type": "code-reviewer",
                "model": reference_model,
            },
            "untestable",
        ),
        (
            "spawn_contract",
            "service_tier_per_spawn",
            {"field": "service_tier"},
            "unsupported",
            False,
        ),
        (
            "negative",
            "invalid_model",
            {
                "message": valid_message,
                "fork_turns": "none",
                "model": "not_in_catalog",
            },
            "reject",
        ),
        (
            "negative",
            "invalid_effort",
            {
                "message": valid_message,
                "fork_turns": "none",
                "model": reference_model,
                "reasoning_effort": "not_an_effort",
            },
            "reject",
        ),
        (
            "negative",
            "invalid_context",
            {"message": valid_message, "fork_turns": "0"},
            "reject",
        ),
    ]
    for contract_case in contract_cases:
        kind, dimension, requested, outcome, *exposure = contract_case
        _append_case(
            cases,
            kind,
            dimension,
            requested,
            {"outcome": outcome},
            exposed=exposure[0] if exposure else None,
        )

    forbidden_overrides = [
        ("agent_type", "code-reviewer", None),
        (
            "model",
            full_history_model,
            "am_full_model_override_"
            + _identifier(full_history_model.removeprefix("gpt-5.6-")),
        ),
        ("reasoning_effort", reference_effort, None),
    ]
    for field, value, task_name in forbidden_overrides:
        requested = {
            "message": valid_message,
            "fork_turns": "all",
            field: value,
        }
        if task_name is not None:
            requested["task_name"] = task_name
        _append_case(
            cases,
            "negative",
            f"full_history_{field}",
            requested,
            {"outcome": "reject"},
        )


def generate_codex_plan(catalog, models, tool_models=()):
    """Generate the deterministic, non-Cartesian Codex validation plan."""
    validate_catalog(catalog)
    tool_models = set(tool_models)
    if not tool_models:
        raise CatalogError(
            "at least one --tool-model from the active spawn schema is required"
        )
    if any(not isinstance(model, str) or not model for model in tool_models):
        raise CatalogError("tool-exposed models must be non-empty strings")
    cases = []
    visible_models = _add_model_effort_cases(
        cases, catalog, models, tool_models
    )
    unknown_tool_models = sorted(tool_models - set(visible_models))
    if unknown_tool_models:
        raise CatalogError(
            f"tool-exposed models are absent from the live catalog: "
            f"{unknown_tool_models}"
        )
    first_model_case = next(
        (
            case
            for case in cases
            if case["kind"] == "model_effort" and case["tool_exposed"]
        ),
        next(case for case in cases if case["kind"] == "model_effort"),
    )
    reference_model = first_model_case["requested"]["model"]
    reference_effort = first_model_case["requested"]["reasoning_effort"]
    tool_exposed_models = sorted(
        {
            case["requested"]["model"]
            for case in cases
            if case["kind"] == "model_effort" and case["tool_exposed"]
        }
    )
    full_history_model = next(
        (
            model
            for model in tool_exposed_models
            if model != reference_model
        ),
        reference_model,
    )
    _add_tracer_case(cases)
    _add_config_cases(cases, catalog)
    _add_context_cases(cases, catalog)
    _add_spawn_contract_cases(
        cases,
        reference_model,
        reference_effort,
        full_history_model,
    )
    return {
        "schema_version": 1,
        "provider": "codex",
        "status_values": list(TERMINAL_STATUSES),
        "catalog_visible_models": visible_models,
        "tool_exposed_models": sorted(tool_models),
        "tool_contract_provenance": {
            "source": "caller_supplied_active_spawn_schema",
            "cli_flag": "--tool-model",
            "introspected": False,
        },
        "cases": cases,
    }


def _agent_path_from_session_meta(payload):
    agent_path = payload.get("agent_path")
    if isinstance(agent_path, str):
        return agent_path
    source = payload.get("source")
    if not isinstance(source, Mapping):
        return None
    subagent = source.get("subagent")
    if not isinstance(subagent, Mapping):
        return None
    spawn = subagent.get("thread_spawn")
    if not isinstance(spawn, Mapping):
        return None
    agent_path = spawn.get("agent_path")
    return agent_path if isinstance(agent_path, str) else None


def _read_rollout(path, sessions_root):
    session_meta = None
    turn_context = None
    try:
        with path.open(encoding="utf-8") as stream:
            for line_number, line in enumerate(stream, start=1):
                if not line.strip():
                    continue
                try:
                    event = json.loads(line)
                except json.JSONDecodeError as exc:
                    return {
                        "error": f"invalid JSONL at line {line_number}: {exc.msg}",
                        "rollout": path.relative_to(sessions_root).as_posix(),
                    }
                if not isinstance(event, Mapping):
                    continue
                if event.get("type") == "session_meta" and session_meta is None:
                    session_meta = event
                elif event.get("type") == "turn_context" and turn_context is None:
                    turn_context = event
                if session_meta is not None and turn_context is not None:
                    break
    except OSError as exc:
        return {
            "error": f"could not read rollout: {exc}",
            "rollout": path.relative_to(sessions_root).as_posix(),
        }

    meta_payload = (
        session_meta.get("payload", {})
        if isinstance(session_meta, Mapping)
        else {}
    )
    context_payload = (
        turn_context.get("payload", {})
        if isinstance(turn_context, Mapping)
        else {}
    )
    agent_path = (
        _agent_path_from_session_meta(meta_payload)
        if isinstance(meta_payload, Mapping)
        else None
    )
    task_name = (
        meta_payload.get("task_name")
        if isinstance(meta_payload, Mapping)
        else None
    )
    if not isinstance(task_name, str) and isinstance(agent_path, str):
        task_name = agent_path.rstrip("/").rsplit("/", 1)[-1]
    return {
        "agent_path": agent_path,
        "task_name": task_name,
        "timestamp": (
            session_meta.get("timestamp", "")
            if isinstance(session_meta, Mapping)
            else ""
        ),
        "model": (
            context_payload.get("model")
            if isinstance(context_payload, Mapping)
            else None
        ),
        "effort": (
            context_payload.get("effort")
            if isinstance(context_payload, Mapping)
            else None
        ),
        "has_turn_context": turn_context is not None,
        "rollout": path.relative_to(sessions_root).as_posix(),
    }


def _parse_iso8601(value, label="timestamp"):
    if not isinstance(value, str) or not value:
        raise CoverageError(f"{label} must be an ISO8601 timestamp")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise CoverageError(f"{label} must be an ISO8601 timestamp") from exc
    if parsed.tzinfo is None:
        raise CoverageError(f"{label} must include an ISO8601 timezone")
    return parsed


def _scan_child_rollouts(sessions_root, not_before=None):
    sessions_root = Path(sessions_root).expanduser()
    if not sessions_root.is_dir():
        raise InventoryError(f"Codex sessions directory not found: {sessions_root}")
    cutoff = (
        _parse_iso8601(not_before, "--not-before")
        if not_before is not None
        else None
    )
    rollouts = []
    for path in sorted(sessions_root.rglob("*.jsonl")):
        rollout = _read_rollout(path, sessions_root)
        if cutoff is not None:
            try:
                timestamp = _parse_iso8601(
                    rollout.get("timestamp"), "rollout timestamp"
                )
            except CoverageError:
                continue
            if timestamp < cutoff:
                continue
        if rollout.get("agent_path") or rollout.get("task_name"):
            rollouts.append(rollout)
    return rollouts


def _matching_rollout(case, rollouts):
    agent_path = case.get("agent_path")
    task_name = case.get("task_name")
    exact_matches = [
        rollout
        for rollout in rollouts
        if isinstance(agent_path, str)
        and rollout.get("agent_path") == agent_path
    ]
    matches = exact_matches
    if not matches:
        matches = [
            rollout
            for rollout in rollouts
            if isinstance(task_name, str)
            and rollout.get("task_name") == task_name
        ]
    if not matches:
        return None
    return max(
        matches,
        key=lambda rollout: (
            str(rollout.get("timestamp", "")),
            str(rollout.get("rollout", "")),
        ),
    )


def _collect_case_result(case, rollout):
    result = {
        "case_id": case.get("case_id"),
        "status": "untestable",
        "catalog_visible": case.get("catalog_visible"),
        "tool_exposed": case.get("tool_exposed"),
        "tool_accepted": case.get("tool_accepted"),
        "backend_accepted": case.get("backend_accepted"),
        "observed": None,
    }
    if rollout is None:
        result["reason"] = "no matching child rollout found"
        return result
    result["rollout"] = rollout["rollout"]
    if rollout.get("error"):
        result["status"] = "infra_error"
        result["reason"] = rollout["error"]
        return result

    result["tool_accepted"] = True
    result["backend_accepted"] = True
    result["evidence_source"] = "child_rollout"
    if not rollout.get("has_turn_context"):
        result["reason"] = "matching child rollout has no turn_context"
        return result

    if case.get("kind") not in {"model_effort", "tracer"}:
        expected = case.get("expected", {}).get("outcome")
        if expected == "reject":
            result["status"] = "fail"
            result["reason"] = "a child rollout exists for a rejection case"
        else:
            result["reason"] = (
                "turn_context does not expose evidence for this case dimension"
            )
        return result

    requested = case.get("requested", {})
    observed = {
        "model": rollout.get("model"),
        "reasoning_effort": rollout.get("effort"),
    }
    result["observed"] = observed
    if observed["model"] is None or observed["reasoning_effort"] is None:
        result["reason"] = "first turn_context omits model or effort"
        return result
    expected = {
        "model": requested.get("model"),
        "reasoning_effort": requested.get("reasoning_effort"),
    }
    if observed == expected:
        result["status"] = "pass"
        result["reason"] = "first turn_context matches requested model and effort"
    else:
        result["status"] = "fail"
        result["reason"] = "first turn_context contradicts requested model or effort"
    return result


def _validated_observations(plan, observations):
    planned_cases = {
        case.get("case_id"): case
        for case in plan["cases"]
        if isinstance(case.get("case_id"), str)
    }
    validated = {}
    for observation in observations or []:
        if not isinstance(observation, Mapping):
            raise CoverageError("every observation must be a mapping")
        reserved = set(observation) & OBSERVATION_RESERVED_FIELDS
        if reserved:
            raise CoverageError(
                f"observation cannot set reserved fields: {sorted(reserved)}"
            )
        unknown = set(observation) - OBSERVATION_FIELDS
        if unknown:
            raise CoverageError(
                f"observation has unknown fields: {sorted(unknown)}"
            )
        case_id = observation.get("case_id")
        if not isinstance(case_id, str) or not case_id:
            raise CoverageError("every observation must have a non-empty case_id")
        if case_id in validated:
            raise CoverageError(f"duplicate observation for case: {case_id!r}")
        if case_id not in planned_cases:
            raise CoverageError(f"observation references unknown case: {case_id!r}")
        status = observation.get("status")
        if status not in TERMINAL_STATUSES:
            raise CoverageError(
                f"observation for {case_id!r} has invalid status: {status!r}"
            )
        tool_accepted = observation.get("tool_accepted")
        if tool_accepted is not None and type(tool_accepted) is not bool:
            raise CoverageError(
                f"observation for {case_id!r} has non-boolean tool_accepted"
            )
        backend_accepted = observation.get("backend_accepted")
        if backend_accepted is not None and type(backend_accepted) is not bool:
            raise CoverageError(
                f"observation for {case_id!r} has non-boolean backend_accepted"
            )
        if "parse_only" in observation and type(
            observation["parse_only"]
        ) is not bool:
            raise CoverageError(
                f"observation for {case_id!r} has non-boolean parse_only"
            )

        case = planned_cases[case_id]
        for support_field in ("catalog_visible", "tool_exposed"):
            if (
                support_field in observation
                and observation[support_field] != case.get(support_field)
            ):
                raise CoverageError(
                    f"observation for {case_id!r} contradicts planned "
                    f"{support_field}"
                )
        kind = case.get("kind")
        expected = case.get("expected", {}).get("outcome")
        if (
            backend_accepted is not None
            and tool_accepted is not True
        ):
            raise CoverageError(
                f"observation for {case_id!r} cannot report a backend outcome "
                "without tool_accepted=true"
            )
        if status == "unsupported" and not (
            (tool_accepted is False and backend_accepted is None)
            or (tool_accepted is True and backend_accepted is False)
            or (
                kind == "config"
                and observation.get("parse_only") is True
                and tool_accepted is None
                and backend_accepted is None
            )
        ):
            raise CoverageError(
                f"unsupported observation for {case_id!r} must identify either "
                "tool rejection or backend rejection"
            )
        if status == "fail" and backend_accepted is False:
            raise CoverageError(
                f"fail observation for {case_id!r} cannot use backend rejection"
            )
        if tool_accepted is False and (
            backend_accepted is not None
            or not (
                status == "unsupported"
                or (status == "pass" and expected == "reject")
            )
        ):
            raise CoverageError(
                f"tool-schema rejection for {case_id!r} must leave "
                "backend_accepted null and be unsupported, or pass only when "
                "rejection was expected"
            )
        if status == "pass":
            if kind in {"model_effort", "tracer"}:
                raise CoverageError(
                    f"{kind} pass for {case_id!r} requires child rollout evidence"
                )
            if kind == "config":
                if observation.get("parse_only") is not True:
                    raise CoverageError(
                        f"config pass for {case_id!r} requires parse_only=true"
                    )
            elif expected == "reject" and (
                tool_accepted is not False or backend_accepted is not None
            ):
                raise CoverageError(
                    f"rejection pass for {case_id!r} requires "
                    "tool_accepted=false and backend_accepted=null"
                )
            elif expected == "accept" and backend_accepted is not True:
                raise CoverageError(
                    f"acceptance pass for {case_id!r} requires "
                    "backend_accepted=true"
                )
            if kind == "context":
                evidence = observation.get("evidence")
                if not isinstance(evidence, str) or not evidence.strip():
                    raise CoverageError(
                        f"context pass for {case_id!r} requires runtime evidence"
                    )
        validated[case_id] = dict(observation)
    return validated


def collect_codex_results(
    plan,
    sessions_root,
    observations=None,
    not_before=None,
):
    """Collect rollout-backed results and overlay explicit tool observations."""
    if not isinstance(plan, Mapping) or not isinstance(plan.get("cases"), list):
        raise CatalogError("plan must contain a cases list")
    rollouts = _scan_child_rollouts(sessions_root, not_before=not_before)
    results = [
        _collect_case_result(case, _matching_rollout(case, rollouts))
        for case in plan["cases"]
    ]
    by_case = _validated_observations(plan, observations)
    for result in results:
        observation = by_case.get(result["case_id"])
        if observation is None:
            continue
        if observation.get("backend_accepted") is True and not (
            result.get("backend_accepted") is True
            and result.get("evidence_source") == "child_rollout"
        ):
            raise CoverageError(
                f"observation for {result['case_id']!r} cannot claim backend "
                "acceptance without a matching child rollout"
            )
        for field in OBSERVATION_FIELDS - {"case_id"}:
            if field in observation:
                result[field] = observation[field]
        result["evidence_source"] = "tool_observation"
    return results


def check_tracer(plan, results):
    """Fail closed unless one rollout-backed tracer proves model and effort."""
    if not isinstance(plan, Mapping) or not isinstance(plan.get("cases"), list):
        raise CoverageError("plan must contain a cases list")
    tracers = [case for case in plan["cases"] if case.get("kind") == "tracer"]
    if len(tracers) != 1:
        raise CoverageError(
            f"plan must contain exactly one tracer case, found {len(tracers)}"
        )
    tracer = tracers[0]
    case_id = tracer.get("case_id")
    matches = [
        result
        for result in results
        if isinstance(result, Mapping) and result.get("case_id") == case_id
    ]
    if len(matches) != 1:
        raise CoverageError(
            f"tracer must have exactly one result, found {len(matches)}"
        )
    result = matches[0]
    requested = tracer.get("requested", {})
    expected_observed = {
        "model": requested.get("model"),
        "reasoning_effort": requested.get("reasoning_effort"),
    }
    if (
        result.get("status") != "pass"
        or result.get("tool_accepted") is not True
        or result.get("backend_accepted") is not True
        or result.get("evidence_source") != "child_rollout"
        or result.get("observed") != expected_observed
    ):
        raise CoverageError(
            "tracer did not produce one rollout-backed pass with the requested "
            "model and reasoning effort"
        )
    return {
        "case_id": case_id,
        "status": "pass",
        "observed": expected_observed,
    }


def check_coverage(plan, results):
    """Require exactly one terminal result for every planned case."""
    if not isinstance(plan, Mapping) or not isinstance(plan.get("cases"), list):
        raise CoverageError("plan must contain a cases list")
    results = list(results)
    planned_ids = [case.get("case_id") for case in plan["cases"]]
    if any(not isinstance(case_id, str) or not case_id for case_id in planned_ids):
        raise CoverageError("every planned case must have a non-empty case_id")
    if len(planned_ids) != len(set(planned_ids)):
        raise CoverageError("plan contains duplicate case IDs")

    result_ids = []
    invalid_statuses = []
    for result in results:
        if not isinstance(result, Mapping):
            raise CoverageError("every result must be a mapping")
        case_id = result.get("case_id")
        if not isinstance(case_id, str) or not case_id:
            raise CoverageError("every result must have a non-empty case_id")
        result_ids.append(case_id)
        if result.get("status") not in TERMINAL_STATUSES:
            invalid_statuses.append((case_id, result.get("status")))

    duplicates = sorted(
        case_id for case_id in set(result_ids) if result_ids.count(case_id) > 1
    )
    missing = sorted(set(planned_ids) - set(result_ids))
    unexpected = sorted(set(result_ids) - set(planned_ids))
    problems = []
    if duplicates:
        problems.append(f"duplicate results: {duplicates}")
    if missing:
        problems.append(f"missing results: {missing}")
    if unexpected:
        problems.append(f"unexpected results: {unexpected}")
    if invalid_statuses:
        problems.append(f"invalid terminal statuses: {invalid_statuses}")
    if problems:
        raise CoverageError("; ".join(problems))

    status_counts = {
        status: sum(result.get("status") == status for result in results)
        for status in TERMINAL_STATUSES
    }
    return {
        "planned": len(planned_ids),
        "results": len(results),
        "missing": [],
        "duplicates": [],
        "unexpected": [],
        "status_counts": status_counts,
    }


def _toml_value(value):
    if type(value) is bool:
        return "true" if value else "false"
    if isinstance(value, str):
        return json.dumps(value)
    raise CatalogError(f"unsupported TOML probe value: {value!r}")


def _granular_approval_override(field, value):
    if field not in GRANULAR_APPROVAL_FIELDS or type(value) is not bool:
        raise CatalogError(f"invalid granular approval probe: {field}={value!r}")
    values = {
        name: (value if name == field else False)
        for name in GRANULAR_APPROVAL_FIELDS
    }
    body = ", ".join(
        f"{name} = {_toml_value(values[name])}"
        for name in GRANULAR_APPROVAL_FIELDS
    )
    return f"approval_policy={{ granular = {{ {body} }} }}"


def _config_override(case):
    dimension = case.get("dimension")
    requested = case.get("requested", {})
    field = requested.get("field")
    value = requested.get("value")
    scalar_keys = {
        "sandbox_mode": "sandbox_mode",
        "approval_policy": "approval_policy",
        "permission_profile": "default_permissions",
        "web_search": "web_search",
        "service_tier": "service_tier",
    }
    if dimension == "approval_policy.granular":
        return _granular_approval_override(field, value)
    if dimension == "mcp_servers":
        if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9_-]+", value):
            raise CatalogError(f"invalid MCP server id for config probe: {value!r}")
        return f"mcp_servers.{value}.enabled=true"
    key = scalar_keys.get(dimension)
    if key is None:
        return None
    return f"{key}={_toml_value(value)}"


def _config_failure_status(stderr):
    lower = stderr.lower()
    infrastructure_markers = (
        "authentication",
        "capacity",
        "could not connect",
        "no such file",
        "permission denied",
        "rate limit",
        "read-only file system",
        "timed out",
    )
    return (
        "infra_error"
        if any(marker in lower for marker in infrastructure_markers)
        else "unsupported"
    )


def _result_support_layers(case):
    return {
        "catalog_visible": case.get("catalog_visible"),
        "tool_exposed": case.get("tool_exposed"),
        "tool_accepted": case.get("tool_accepted"),
        "backend_accepted": case.get("backend_accepted"),
    }


def _rendered_skill_names(value):
    strings = []

    def visit(item):
        if isinstance(item, str):
            strings.append(item)
        elif isinstance(item, Mapping):
            for nested in item.values():
                visit(nested)
        elif isinstance(item, Sequence) and not isinstance(item, (str, bytes)):
            for nested in item:
                visit(nested)

    visit(value)
    names = set()
    for text in strings:
        for block in re.findall(
            r"<skills_instructions>(.*?)</skills_instructions>",
            text,
            flags=re.DOTALL,
        ):
            names.update(
                re.findall(
                    r"(?m)^- ([A-Za-z0-9][A-Za-z0-9:_-]*):(?:\s|$)",
                    block,
                )
            )
    return names


def _is_valid_explicit_only_skill(repo_root, skill):
    skill_root = Path(repo_root) / ".codex/skills" / skill
    skill_path = skill_root / "SKILL.md"
    policy_path = skill_root / "agents/openai.yaml"
    if not skill_path.is_file() or not policy_path.is_file():
        return False
    try:
        frontmatter = _skill_frontmatter(skill_path)
        with policy_path.open(encoding="utf-8") as stream:
            policy_document = yaml.load(stream, Loader=_UniqueKeyLoader)
    except (CatalogError, OSError, yaml.YAMLError):
        return False
    if frontmatter.get("name") != skill or not isinstance(
        policy_document, Mapping
    ):
        return False
    policy = policy_document.get("policy")
    return (
        isinstance(policy, Mapping)
        and policy.get("allow_implicit_invocation") is False
    )


def _run_prompt_input(case, repo_root=REPO_ROOT):
    dimension = case.get("dimension")
    support_layers = _result_support_layers(case)
    if dimension == "tool_access":
        return {
            "case_id": case.get("case_id"),
            "status": "untestable",
            "reason": (
                "tool_access is inherited from the parent/tool schema and is "
                "not a Codex config field"
            ),
            "evidence": "parent_or_tool_schema_required",
            "parse_only": True,
            "stderr": "",
            **support_layers,
        }

    if dimension == "skills":
        command = [
            "codex",
            "debug",
            "prompt-input",
            "verify configured skill discovery",
        ]
        override = None
    else:
        override = _config_override(case)
        if override is None:
            return {
                "case_id": case.get("case_id"),
                "status": "unsupported",
                "reason": f"{dimension!r} is not mapped to a Codex config field",
                "parse_only": True,
                "stderr": "",
                **support_layers,
            }
        command = [
            "codex",
            "debug",
            "prompt-input",
            "-c",
            override,
            "agent matrix config parse probe",
        ]

    completed = subprocess.run(
        command,
        capture_output=True,
        text=True,
        check=False,
    )
    result = {
        "case_id": case.get("case_id"),
        "status": "pass",
        "reason": "Codex parsed the config override without running inference",
        "parse_only": True,
        "stderr": completed.stderr,
        "returncode": completed.returncode,
        "command": command,
        **support_layers,
    }
    if override is not None:
        result["config_override"] = override
    if completed.returncode != 0:
        result["status"] = _config_failure_status(completed.stderr)
        result["reason"] = "codex debug prompt-input rejected or could not render"
        return result
    try:
        rendered = json.loads(completed.stdout)
    except json.JSONDecodeError:
        result["status"] = "infra_error"
        result["reason"] = "codex debug prompt-input returned non-JSON stdout"
        return result
    if dimension == "skills":
        skill = str(case.get("requested", {}).get("value", ""))
        if skill in _rendered_skill_names(rendered):
            result["reason"] = f"rendered prompt discovered skill {skill!r}"
        elif _is_valid_explicit_only_skill(repo_root, skill):
            result["status"] = "untestable"
            result["reason"] = (
                f"skill {skill!r} is valid on disk but explicitly excluded "
                "from implicit prompt rendering"
            )
            result["evidence"] = (
                "valid_skill_frontmatter_and_explicit_only_policy"
            )
        else:
            result["status"] = "fail"
            result["reason"] = f"rendered prompt did not discover skill {skill!r}"
    return result


def probe_codex_config(plan, repo_root=REPO_ROOT):
    """Run render-only Codex config probes for every planned config case."""
    if not isinstance(plan, Mapping) or not isinstance(plan.get("cases"), list):
        raise CatalogError("plan must contain a cases list")
    return [
        _run_prompt_input(case, repo_root=repo_root)
        for case in plan["cases"]
        if case.get("kind") == "config"
    ]


def _read_json(path, label):
    try:
        with Path(path).open(encoding="utf-8") as stream:
            value = json.load(stream)
    except (OSError, json.JSONDecodeError) as exc:
        raise CatalogError(f"could not read {label}: {exc}") from exc
    if not isinstance(value, Mapping):
        raise CatalogError(f"{label} must be a JSON object")
    return value


def _read_jsonl(path):
    results = []
    try:
        with Path(path).open(encoding="utf-8") as stream:
            for line_number, line in enumerate(stream, start=1):
                if not line.strip():
                    continue
                try:
                    value = json.loads(line)
                except json.JSONDecodeError as exc:
                    raise CoverageError(
                        f"invalid results JSONL at line {line_number}: {exc.msg}"
                    ) from exc
                if not isinstance(value, Mapping):
                    raise CoverageError(
                        f"result at line {line_number} must be a JSON object"
                    )
                results.append(value)
    except OSError as exc:
        raise CoverageError(f"could not read results: {exc}") from exc
    return results


def _write_text(path, text):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _write_json(path, value):
    _write_text(path, json.dumps(value, indent=2, sort_keys=True) + "\n")


def _write_jsonl(path, values):
    text = "".join(
        json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n"
        for value in values
    )
    _write_text(path, text)


def _markdown_report(report, results, plan=None, not_before=None):
    lines = [
        "# Codex Agent Matrix Results",
        "",
        f"Planned cases: {report['planned']}",
        "",
    ]
    provenance = (
        plan.get("tool_contract_provenance")
        if isinstance(plan, Mapping)
        else None
    )
    if isinstance(provenance, Mapping):
        lines.extend(
            [
                "Tool contract provenance: "
                f"{provenance.get('source', 'unknown')} "
                f"(introspected={str(provenance.get('introspected')).lower()})",
                "",
            ]
        )
    model_provenance = (
        plan.get("model_catalog_provenance")
        if isinstance(plan, Mapping)
        else None
    )
    if isinstance(model_provenance, Mapping):
        lines.extend(
            [
                "Model catalog provenance: "
                f"{model_provenance.get('source', 'unknown')} "
                f"(captured={str(model_provenance.get('captured')).lower()})",
                "",
            ]
        )
    if not_before is not None:
        lines.extend([f"Rollout cutoff: {not_before}", ""])
    lines.extend(
        [
        "| Status | Count |",
        "|---|---:|",
        ]
    )
    for status in TERMINAL_STATUSES:
        lines.append(f"| {status} | {report['status_counts'][status]} |")
    lines.extend(["", "| Case | Status | Reason |", "|---|---|---|"])
    for result in results:
        reason = str(result.get("reason", "")).replace("|", r"\|").replace(
            "\n", " "
        )
        lines.append(
            f"| {result['case_id']} | {result['status']} | {reason} |"
        )
    return "\n".join(lines) + "\n"


def _parse_capabilities(values):
    capabilities = {}
    for item in values:
        if "=" not in item:
            raise CatalogError(
                f"capability must use NAME=VALUE syntax: {item!r}"
            )
        name, raw_value = item.split("=", 1)
        if not name:
            raise CatalogError("capability name must not be empty")
        if name in capabilities:
            raise CatalogError(f"duplicate capability selection: {name!r}")
        try:
            value = json.loads(raw_value)
        except json.JSONDecodeError:
            value = raw_value
        capabilities[name] = value
    return capabilities


def _skill_frontmatter(path):
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise CatalogError(f"missing Agent Matrix skill: {path}") from exc
    lines = text.splitlines()
    if not lines or lines[0] != "---":
        raise CatalogError(f"skill has no YAML frontmatter: {path}")
    try:
        closing = lines.index("---", 1)
    except ValueError as exc:
        raise CatalogError(f"skill frontmatter is not closed: {path}") from exc
    try:
        frontmatter = yaml.load(
            "\n".join(lines[1:closing]), Loader=_UniqueKeyLoader
        )
    except yaml.YAMLError as exc:
        raise CatalogError(f"invalid skill frontmatter in {path}: {exc}") from exc
    if not isinstance(frontmatter, Mapping):
        raise CatalogError(f"skill frontmatter must be a mapping: {path}")
    return frontmatter


def validate_skills(repo_root=REPO_ROOT):
    """Validate that both runtime-specific Agent Matrix skills are discoverable."""
    repo_root = Path(repo_root)
    paths = [
        repo_root / ".codex/skills/agent-matrix/SKILL.md",
        repo_root / ".claude/skills/agent-matrix/SKILL.md",
    ]
    for path in paths:
        frontmatter = _skill_frontmatter(path)
        if frontmatter.get("name") != "agent-matrix":
            raise CatalogError(
                f"skill name must be 'agent-matrix': {path}"
            )
    return paths


def _run_codex_model_inventory():
    completed = subprocess.run(
        ["codex", "debug", "models"],
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        detail = completed.stderr.strip() or "no stderr"
        raise InventoryError(
            f"codex debug models failed with exit {completed.returncode}: {detail}"
        )
    models = parse_codex_models(completed.stdout)
    if completed.stderr.strip():
        print(completed.stderr.rstrip(), file=sys.stderr)
    return models


def _add_catalog_argument(parser):
    parser.add_argument(
        "--catalog",
        type=Path,
        default=DEFAULT_CATALOG_PATH,
        help="Path to the compact Agent Matrix YAML catalog.",
    )


def _build_parser():
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate_catalog_parser = subparsers.add_parser("validate-catalog")
    _add_catalog_argument(validate_catalog_parser)

    plan_parser = subparsers.add_parser("plan-codex")
    _add_catalog_argument(plan_parser)
    plan_parser.add_argument("--output", type=Path, required=True)
    plan_parser.add_argument(
        "--models-json",
        type=Path,
        help="Captured strict JSON from `codex debug models` for reproducible planning.",
    )
    plan_parser.add_argument(
        "--tool-model",
        action="append",
        required=True,
        help="Model advertised by the active spawn_agent schema; repeat as needed.",
    )

    selection_parser = subparsers.add_parser("validate-selection")
    _add_catalog_argument(selection_parser)
    selection_parser.add_argument("--provider", required=True)
    selection_parser.add_argument("--model")
    selection_parser.add_argument("--effort")
    selection_parser.add_argument("--context")
    selection_parser.add_argument("--capability", action="append", default=[])
    selection_parser.add_argument("--skill", action="append", default=[])

    probe_parser = subparsers.add_parser("probe-codex-config")
    probe_parser.add_argument("--plan", type=Path, required=True)
    probe_parser.add_argument("--output-jsonl", type=Path, required=True)

    collect_parser = subparsers.add_parser("collect-codex")
    collect_parser.add_argument("--plan", type=Path, required=True)
    collect_parser.add_argument(
        "--observations",
        type=Path,
        action="append",
        default=[],
        help="JSONL observations to overlay; repeat for multiple evidence files.",
    )
    collect_parser.add_argument("--output-jsonl", type=Path, required=True)
    collect_parser.add_argument("--output-markdown", type=Path, required=True)
    collect_parser.add_argument(
        "--not-before",
        required=True,
        help="Ignore child rollouts older than this ISO8601 timestamp.",
    )

    coverage_parser = subparsers.add_parser("check-coverage")
    coverage_parser.add_argument("--plan", type=Path, required=True)
    coverage_parser.add_argument("--results", type=Path, required=True)

    tracer_parser = subparsers.add_parser("check-tracer")
    tracer_parser.add_argument("--plan", type=Path, required=True)
    tracer_parser.add_argument("--results", type=Path, required=True)

    skills_parser = subparsers.add_parser("validate-skills")
    skills_parser.add_argument("--repo-root", type=Path, default=REPO_ROOT)
    return parser


def _run_command(args):
    if args.command == "validate-catalog":
        catalog = load_catalog(args.catalog)
        validate_catalog(catalog)
        print(f"valid catalog: {args.catalog}")
        return 0
    if args.command == "plan-codex":
        catalog = load_catalog(args.catalog)
        if args.models_json is not None:
            try:
                models_text = args.models_json.read_text(encoding="utf-8")
            except OSError as exc:
                raise InventoryError(
                    f"could not read captured model inventory: {exc}"
                ) from exc
            models = parse_codex_models(models_text)
            inventory_source = args.models_json.as_posix()
        else:
            models = _run_codex_model_inventory()
            inventory_source = "live:codex debug models"
        plan = generate_codex_plan(catalog, models, args.tool_model)
        plan["model_catalog_provenance"] = {
            "source": inventory_source,
            "captured": args.models_json is not None,
        }
        _write_json(args.output, plan)
        print(f"wrote {len(plan['cases'])} cases: {args.output}")
        return 0
    if args.command == "validate-selection":
        catalog = load_catalog(args.catalog)
        validate_selection(
            catalog,
            provider=args.provider,
            model=args.model,
            effort=args.effort,
            context=args.context,
            capabilities=_parse_capabilities(args.capability),
            skills=args.skill,
        )
        print("valid selection")
        return 0
    if args.command == "probe-codex-config":
        plan = _read_json(args.plan, "plan")
        results = probe_codex_config(plan)
        config_plan = {
            "cases": [
                case for case in plan["cases"] if case.get("kind") == "config"
            ]
        }
        check_coverage(config_plan, results)
        _write_jsonl(args.output_jsonl, results)
        print(f"probed {len(results)} config cases")
        return 0
    if args.command == "collect-codex":
        plan = _read_json(args.plan, "plan")
        codex_home = Path(
            os.environ.get("CODEX_HOME", str(Path.home() / ".codex"))
        ).expanduser()
        observations = []
        for observations_path in args.observations:
            observations.extend(_read_jsonl(observations_path))
        results = collect_codex_results(
            plan,
            codex_home / "sessions",
            observations=observations or None,
            not_before=args.not_before,
        )
        for result in results:
            result["collection_not_before"] = args.not_before
        report = check_coverage(plan, results)
        if plan.get("provider") == "codex":
            check_tracer(plan, results)
        _write_jsonl(args.output_jsonl, results)
        _write_text(
            args.output_markdown,
            _markdown_report(
                report,
                results,
                plan=plan,
                not_before=args.not_before,
            ),
        )
        print(f"collected {len(results)} results")
        return 0
    if args.command == "check-coverage":
        plan = _read_json(args.plan, "plan")
        results = _read_jsonl(args.results)
        report = check_coverage(plan, results)
        print(json.dumps(report, sort_keys=True))
        return 0
    if args.command == "check-tracer":
        plan = _read_json(args.plan, "plan")
        results = _read_jsonl(args.results)
        report = check_tracer(plan, results)
        print(json.dumps(report, sort_keys=True))
        return 0
    if args.command == "validate-skills":
        paths = validate_skills(args.repo_root)
        print(f"valid skills: {len(paths)}")
        return 0
    raise AssertionError(f"unhandled command: {args.command}")


def main(argv=None):
    parser = _build_parser()
    args = parser.parse_args(argv)
    try:
        return _run_command(args)
    except (CatalogError, InventoryError, CoverageError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
