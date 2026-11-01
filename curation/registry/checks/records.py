"""Record checks: adoption targets, generated block pairing, skill coverage."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from curation.registry.checks.traits import doc_holder_kind
from curation.registry.config import RegistryConfig, _rel
from curation.registry.ledger import (
    _trait_base,
    effective_by_subject,
    is_pending_adopt,
    resolve_skill,
)
from curation.registry.loaders import record_paths
from curation.registry.models import Event, Frontmatter, SkillEntry
from curation.registry.views.records import (
    DECLINED_CLOSE,
    DECLINED_OPEN,
    HISTORY_CLOSE,
    HISTORY_OPEN,
    LINEAGE_CLOSE,
    LINEAGE_OPEN,
    REVIEWS_CLOSE,
    REVIEWS_OPEN,
    SOURCES_CLOSE,
    SOURCES_OPEN,
    TRAITS_CLOSE,
    TRAITS_OPEN,
)
from curation.registry.vocab import IN_PROGRESS_DIR, STUB_SKILLS

# Non-skill target kinds a `kind:name` adoption target may name.
NONSKILL_KINDS = frozenset({"agent", "command", "hook", "rule", "mcp", "plugin"})


def _target_exists(
    target: str | None,
    existing: set[str],
    ours: Any,
    cfg: RegistryConfig | None = None,
) -> bool:
    """True when an adoption target resolves. A plain name must be a skill
    record, alias or stub. A `doc:<repo-relative path>` target (a method
    document, §2) resolves when the file exists. A `kind:name` target is valid
    only when kind is a real non-skill kind, name is non-empty, and that
    capability exists in our shipped surface — matched by full logical id or by
    exact (kind, name). The exact-name form covers the documented legacy prefix
    normalization (e.g. `agent:code-reviewer` ↔ `agent:agents/code-reviewer`,
    the legacy short form), since a capability's `name` is the bare leaf. A
    fabricated namespace such as `agent:does-not-exist/agents/code-reviewer`
    matches neither and is rejected."""
    if not target:
        return False
    if target.startswith("doc:"):
        rel = target[len("doc:") :]
        # Must be a repo-relative path that stays inside repo_root, even through
        # symlinks — `doc:/etc/passwd` and `doc:../x` are rejected (review #15).
        if not rel or rel.startswith("/") or ".." in Path(rel).parts:
            return False
        if cfg is None:
            return True
        root = cfg.repo_root.resolve()
        resolved = (cfg.repo_root / rel).resolve()
        if not resolved.is_relative_to(root):
            return False
        return resolved.is_file()
    if ":" not in target:
        return target in existing
    kind, _, name = target.partition(":")
    if kind not in NONSKILL_KINDS or not name:
        return False
    for cap in ours.capabilities:
        if cap.kind.value != kind:
            continue
        if cap.logical_id == target or cap.name == name:
            return True
    return False


def _can_be_planned(cfg: RegistryConfig, target: str) -> bool:
    """A target a delivering build may still create: a skill, or a playbook
    whose prospective path stays inside repo_root, even through symlinks."""
    if target.startswith("doc:"):
        rel = target[len("doc:") :]
        if doc_holder_kind(cfg, rel) != "playbook":
            return False
        return (cfg.repo_root / rel).resolve().is_relative_to(cfg.repo_root.resolve())
    return ":" not in target


def _check_effective_targets(
    cfg: RegistryConfig,
    events: list[Event],
    records: set[str],
    aliases: set[str],
    ours: Any,
    forward: dict[str, str],
    retired: set[str],
) -> list[str]:
    """Every live adoption carries a source and a target that resolves today.
    A target is resolved through our rename/merge lifecycle (§3); a target that
    was retired is "adopted, no longer provided", not an error. An unresolved,
    still-active target is an error. A pending trait adopt may name a skill or
    playbook its delivering build will create, and so may its skill's checkpoint
    (§5b); a delivered adopt needs the target to exist."""
    existing = records | aliases | STUB_SKILLS
    effective = effective_by_subject(events)
    planned: dict[str, set[str]] = {}
    for event in effective.values():
        if (
            is_pending_adopt(event)
            and event.skill
            and _can_be_planned(cfg, event.skill)
        ):
            planned.setdefault(_trait_base(event.subject), set()).add(event.skill)
    errors: list[str] = []
    for subject, event in effective.items():
        if event.kind not in {"adopt", "adopt-merged"}:
            continue
        if event.source is None:
            errors.append(f"{event.id}: live adoption of {subject} has no source")
        target = event.skill
        # Plain skill targets follow rename/merge; kind:name and doc: targets do not.
        resolved = target
        if target and ":" not in target:
            resolved = resolve_skill(target, forward)
        if resolved in retired:
            continue
        if _target_exists(resolved, existing, ours, cfg):
            continue
        if target in planned.get(_trait_base(subject), set()) and (
            is_pending_adopt(event) or "#" not in subject
        ):
            continue
        errors.append(
            f"{event.id}: live adoption of {subject} has an invalid "
            f"skill target {event.skill!r}"
        )
    return errors


_BLOCK_MARKERS = (
    (TRAITS_OPEN, TRAITS_CLOSE),
    (SOURCES_OPEN, SOURCES_CLOSE),
    (DECLINED_OPEN, DECLINED_CLOSE),
    (LINEAGE_OPEN, LINEAGE_CLOSE),
    (HISTORY_OPEN, HISTORY_CLOSE),
    (REVIEWS_OPEN, REVIEWS_CLOSE),
)


def _check_block_pairing(cfg: RegistryConfig) -> list[str]:
    """Each generated block that appears must be correctly paired and ordered:
    exactly one open and one close, with the close after the open (review #14)."""
    errors: list[str] = []
    for path in record_paths(cfg):
        text = path.read_text(encoding="utf-8")
        for open_tag, close_tag in _BLOCK_MARKERS:
            opens = text.count(open_tag)
            closes = text.count(close_tag)
            if opens == 0 and closes == 0:
                continue
            if opens != 1 or closes != 1 or text.find(open_tag) > text.find(close_tag):
                errors.append(
                    f"{_rel(cfg, path)}: malformed {open_tag!r} block (open/close pairing)"
                )
    return errors


def _check_skill_coverage(
    cfg: RegistryConfig, records: dict[str, Frontmatter]
) -> list[str]:
    """One `skills.yaml` entry per real skill folder: a folder with no entry
    (and not an alias, stub or in-progress) fails, and so does an entry with no
    folder (README §3 rule 5, check item 7). No skills folder at all fails
    every entry."""
    aliases = {alias for fm in records.values() for alias in fm.aliases}
    errors: list[str] = []
    folders = (
        {child.name for child in cfg.skills_dir.iterdir() if child.is_dir()}
        if cfg.skills_dir.is_dir()
        else set()
    )
    for name in sorted(folders):
        if (
            name == IN_PROGRESS_DIR
            or name in records
            or name in aliases
            or name in STUB_SKILLS
        ):
            continue
        errors.append(
            f".claude/skills/{name}: no skills.yaml entry, and not an alias, stub "
            f"or in-progress"
        )
    for name in sorted(set(records) - folders):
        errors.append(f"skills.yaml: {name}: no .claude/skills/{name} folder")
    return errors


def _check_boundaries(skills: dict[str, SkillEntry]) -> list[str]:
    """Two active skills in one domain · sub-stage each state a `boundary`
    (README §2 rule 3, check item 7)."""
    groups: dict[tuple[str, str], list[str]] = {}
    for name, entry in skills.items():
        if entry.status == "active":
            groups.setdefault((entry.domain, entry.substage), []).append(name)
    errors: list[str] = []
    for (domain, substage), names in sorted(groups.items()):
        if len(names) < 2:
            continue
        for name in sorted(names):
            if skills[name].boundary is None:
                others = ", ".join(n for n in sorted(names) if n != name)
                errors.append(
                    f"skills.yaml: {name}: shares {domain} · {substage} with "
                    f"{others} and has no boundary"
                )
    return errors
