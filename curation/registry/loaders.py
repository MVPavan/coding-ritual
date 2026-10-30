"""Duplicate-key-safe YAML, JSONL round files and record frontmatter → models."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

from curation.registry.config import RegistryConfig
from curation.registry.models import (
    Event,
    Frontmatter,
    OursTraitEntry,
    PolicyEntry,
    Report,
    RoundHeader,
    SharingEntry,
    SkillEntry,
    TraitDefinition,
    UpstreamTraitEntry,
)
from curation.registry.vocab import _SLUG_RE, _TRAIT_ID_RE


class _StrictYamlLoader(yaml.SafeLoader):
    """`yaml.safe_load` that errors on a duplicate mapping key (§3): PyYAML keeps
    the last silently, which would drop a trait definition or list."""


def _no_duplicate_keys(loader: _StrictYamlLoader, node: Any) -> dict[Any, Any]:
    mapping: dict[Any, Any] = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=True)
        if key in mapping:
            raise yaml.constructor.ConstructorError(
                "while constructing a mapping",
                node.start_mark,
                f"found duplicate key {key!r}",
                key_node.start_mark,
            )
        mapping[key] = loader.construct_object(value_node, deep=True)
    return mapping


_StrictYamlLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _no_duplicate_keys
)


def load_trait_definitions(
    cfg: RegistryConfig,
) -> tuple[dict[str, TraitDefinition], list[str]]:
    """Parse `trait-definitions.yaml`; absent means empty (§1)."""
    path = cfg.trait_definitions_path
    if not path.is_file():
        return {}, []
    try:
        raw = yaml.load(path.read_text(encoding="utf-8"), Loader=_StrictYamlLoader)
    except yaml.YAMLError as exc:
        return {}, [f"trait-definitions.yaml: {exc}"]
    if raw is None:
        return {}, []
    if not isinstance(raw, dict):
        return {}, ["trait-definitions.yaml: top level must be a mapping"]
    out: dict[str, TraitDefinition] = {}
    errors: list[str] = []
    for tid, body in raw.items():
        if not isinstance(tid, str) or not _TRAIT_ID_RE.fullmatch(tid):
            errors.append(
                f"trait-definitions.yaml: {tid!r} is not a kebab-case trait ID"
            )
            continue
        try:
            out[tid] = TraitDefinition.model_validate(body)
        except Exception as exc:  # noqa: BLE001 - surfaced as a validation error
            errors.append(f"trait-definitions.yaml: {tid}: {exc}")
    return out, errors


OURS_TRAITS_FILE = "ours.yaml"


def traits_file_for(key: str) -> str:
    """The `traits/` file a key belongs in: `ours:` and `doc:` keys in
    `ours.yaml`, an upstream key in `<repo>.yaml` (stages-design §Files)."""
    if key.startswith(("ours:", "doc:")):
        return OURS_TRAITS_FILE
    return f"{key.partition(':')[0]}.yaml"


TraitEntry = OursTraitEntry | UpstreamTraitEntry


def load_traits(cfg: RegistryConfig) -> tuple[dict[str, TraitEntry], list[str]]:
    """Parse every `traits/*.yaml`; an absent folder means empty (§2). `ours:`
    and `doc:` keys are ours entries, every other key an upstream entry. Each key
    sits in exactly one file, the one matching its source; a harness file needs
    the harness's catalog (check item 8). Files are read in name order, so
    `out` keeps every file's key order."""
    folder = cfg.traits_dir
    if not folder.is_dir():
        return {}, []
    catalogs = {p.stem for p in _catalog_files(cfg)}
    out: dict[str, TraitEntry] = {}
    where: dict[str, str] = {}
    errors: list[str] = []
    for path in sorted(folder.glob("*.yaml")):
        name = f"traits/{path.name}"
        if path.name != OURS_TRAITS_FILE and path.stem not in catalogs:
            errors.append(f"{name}: no catalog for harness {path.stem!r}")
        try:
            raw = yaml.load(path.read_text(encoding="utf-8"), Loader=_StrictYamlLoader)
        except yaml.YAMLError as exc:
            errors.append(f"{name}: {exc}")
            continue
        if raw is None:
            continue
        if not isinstance(raw, dict):
            errors.append(f"{name}: top level must be a mapping")
            continue
        for key, body in raw.items():
            if not isinstance(key, str):
                errors.append(f"{name}: key {key!r} is not a string")
                continue
            if key in where:
                errors.append(f"{name}: {key}: also in {where[key]}")
                continue
            where[key] = name
            if traits_file_for(key) != path.name:
                errors.append(
                    f"{name}: {key}: belongs in traits/{traits_file_for(key)}"
                )
            ours = key.startswith(("ours:", "doc:"))
            model: type[TraitEntry] = OursTraitEntry if ours else UpstreamTraitEntry
            try:
                out[key] = model.model_validate(body)
            except Exception as exc:  # noqa: BLE001 - surfaced as a validation error
                errors.append(f"{name}: {key}: {exc}")
    return out, errors


def load_skills(cfg: RegistryConfig) -> tuple[dict[str, SkillEntry], list[str]]:
    """Parse `skills.yaml`; absent means empty (stages-design §Skills file)."""
    path = cfg.skills_path
    if not path.is_file():
        return {}, []
    try:
        raw = yaml.load(path.read_text(encoding="utf-8"), Loader=_StrictYamlLoader)
    except yaml.YAMLError as exc:
        return {}, [f"skills.yaml: {exc}"]
    if raw is None:
        return {}, []
    if not isinstance(raw, dict):
        return {}, ["skills.yaml: top level must be a mapping"]
    out: dict[str, SkillEntry] = {}
    errors: list[str] = []
    for name, body in raw.items():
        if not isinstance(name, str) or not _SLUG_RE.fullmatch(name):
            errors.append(f"skills.yaml: {name!r} is not a skill folder name")
            continue
        try:
            out[name] = SkillEntry.model_validate(body)
        except Exception as exc:  # noqa: BLE001 - surfaced as a validation error
            errors.append(f"skills.yaml: {name}: {exc}")
    return out, errors


def _load_trait_keyed[M: (PolicyEntry, SharingEntry)](
    path: Path, model: type[M]
) -> tuple[dict[str, M], list[str]]:
    """A YAML mapping of trait ID → `model`; absent or `{}` means empty."""
    name = path.name
    if not path.is_file():
        return {}, []
    try:
        raw = yaml.load(path.read_text(encoding="utf-8"), Loader=_StrictYamlLoader)
    except yaml.YAMLError as exc:
        return {}, [f"{name}: {exc}"]
    if raw is None:
        return {}, []
    if not isinstance(raw, dict):
        return {}, [f"{name}: top level must be a mapping"]
    out: dict[str, M] = {}
    errors: list[str] = []
    for tid, body in raw.items():
        if not isinstance(tid, str) or not _TRAIT_ID_RE.fullmatch(tid):
            errors.append(f"{name}: {tid!r} is not a kebab-case trait ID")
            continue
        try:
            out[tid] = model.model_validate(body)
        except Exception as exc:  # noqa: BLE001 - surfaced as a validation error
            errors.append(f"{name}: {tid}: {exc}")
    return out, errors


def load_trait_policy(
    cfg: RegistryConfig,
) -> tuple[dict[str, PolicyEntry], list[str]]:
    """Parse `trait-policy.yaml` (stages-design §Trait policy)."""
    return _load_trait_keyed(cfg.trait_policy_path, PolicyEntry)


def load_trait_sharing(
    cfg: RegistryConfig,
) -> tuple[dict[str, SharingEntry], list[str]]:
    """Parse `trait-sharing.yaml` (stages-design §Shared traits)."""
    return _load_trait_keyed(cfg.trait_sharing_path, SharingEntry)


def skill_description(cfg: RegistryConfig, skill: str) -> str:
    """The `description` from `.claude/skills/<skill>/SKILL.md` frontmatter,
    whitespace-collapsed; empty when absent or unreadable."""
    path = cfg.skills_dir / skill / "SKILL.md"
    if not path.is_file():
        return ""
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        return ""
    block, sep, _ = text[4:].partition("\n---")
    if not sep:
        return ""
    try:
        data = yaml.safe_load(block)
    except yaml.YAMLError:
        return ""
    desc = data.get("description") if isinstance(data, dict) else None
    return " ".join(desc.split()) if isinstance(desc, str) else ""


def _round_files(cfg: RegistryConfig) -> list[Path]:
    if not cfg.ledger_dir.is_dir():
        return []
    return sorted(p for p in cfg.ledger_dir.glob("*.jsonl"))


def load_ledger(
    cfg: RegistryConfig,
) -> tuple[list[RoundHeader], list[Event], list[str]]:
    """Read every round file into validated headers and events, in order."""
    headers: list[RoundHeader] = []
    events: list[Event] = []
    errors: list[str] = []
    for path in _round_files(cfg):
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if not line.strip():
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError as exc:
                errors.append(f"{path.name}:{lineno}: unparseable JSON ({exc})")
                continue
            kind = record.get("type")
            try:
                if kind == "round":
                    headers.append(RoundHeader.model_validate(record))
                elif kind == "event":
                    events.append(Event.model_validate(record))
                else:
                    errors.append(f"{path.name}:{lineno}: unknown record type {kind!r}")
            except Exception as exc:  # noqa: BLE001 - surfaced as a validation error
                errors.append(f"{path.name}:{lineno}: schema error ({exc})")
    return headers, events, errors


def parse_record(text: str) -> tuple[Frontmatter, str]:
    """Split a record into validated frontmatter and the body after it."""
    if not text.startswith("---\n"):
        raise ValueError("record has no frontmatter")
    _, _, rest = text.partition("---\n")
    block, sep, body = rest.partition("\n---\n")
    if not sep:
        raise ValueError("record frontmatter is not closed")
    fm = _parse_frontmatter_block(block)
    return Frontmatter.model_validate(fm), body


def _parse_frontmatter_block(block: str) -> dict[str, Any]:
    fm: dict[str, Any] = {}
    for line in block.splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        key, _, raw = line.partition(":")
        key = key.strip()
        value = raw.strip()
        if value.startswith("[") and value.endswith("]"):
            inner = value[1:-1].strip()
            fm[key] = [item.strip() for item in inner.split(",") if item.strip()]
        elif value == "":
            fm[key] = None
        else:
            fm[key] = value.strip("\"'")
    return fm


def record_paths(cfg: RegistryConfig) -> list[Path]:
    if not cfg.skill_records_dir.is_dir():
        return []
    return sorted(cfg.skill_records_dir.rglob("*.md"))


def record_path(cfg: RegistryConfig, skill: str, domain: str) -> Path:
    return cfg.skill_records_dir / domain / f"{skill}.md"


def load_records(cfg: RegistryConfig) -> dict[str, Frontmatter]:
    """Every skill's record frontmatter, from `skills.yaml` (records are
    generated from it)."""
    skills, _ = load_skills(cfg)
    return {name: entry.frontmatter(name) for name, entry in skills.items()}


def _catalog_files(cfg: RegistryConfig) -> list[Path]:
    if not cfg.catalogs_dir.is_dir():
        return []
    return sorted(p for p in cfg.catalogs_dir.glob("*.json") if p.stem != "ours")


def report_key(cfg: RegistryConfig, path: Path) -> str:
    """A report's repo-relative path: its name in `supersedes` and the manifest."""
    return path.resolve().relative_to(cfg.repo_root.resolve()).as_posix()


def report_files(cfg: RegistryConfig) -> list[Path]:
    """Every `reviews/*.yaml`; older Markdown-only reviews are history."""
    if not cfg.reviews_dir.is_dir():
        return []
    return sorted(cfg.reviews_dir.glob("*.yaml"))


def load_report(path: Path) -> Report:
    """One report file, strictly; raises on a YAML or schema error."""
    raw = yaml.load(path.read_text(encoding="utf-8"), Loader=_StrictYamlLoader)
    return Report.model_validate(raw)


def load_reports(cfg: RegistryConfig) -> tuple[dict[str, Report], list[str]]:
    """Every report, keyed by `report_key`."""
    out: dict[str, Report] = {}
    errors: list[str] = []
    for path in report_files(cfg):
        key = report_key(cfg, path)
        try:
            out[key] = load_report(path)
        except Exception as exc:  # noqa: BLE001 - surfaced as a validation error
            errors.append(f"{key}: {exc}")
    return out, errors
