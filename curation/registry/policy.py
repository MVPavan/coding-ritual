"""Trait policy (stages-design 3.5a, §Trait policy): GUIDE rule digests, live
entries and the basis a decision is recorded under."""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

from curation.registry.models import PolicyEntry, TraitDefinition

_RULE_LINE_RE = re.compile(r"^- \*\*([A-Z]+-\d+)\*\*(.*)$", re.MULTILINE)
_CITATIONS_RE = re.compile(r"(\s*\[[^\]]*\])+\s*$")
_RETIRED_RE = re.compile(r"^Retired \d{4}-\d{2}-\d{2}; see [A-Z]+-\d+\.$")


def rule_digest(text: str) -> str:
    """First 12 hex chars of the sha256 of a rule's text."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]


def guide_rules(path: Path) -> dict[str, tuple[str, str, bool]]:
    """GUIDE.md rule ID → (text, digest, retired). The text follows `**ID**`,
    trailing bracketed citations removed and whitespace collapsed; a rule
    reading `Retired <date>; see <ID>.` is retired. A missing file has none."""
    if not path.is_file():
        return {}
    out: dict[str, tuple[str, str, bool]] = {}
    for rule, rest in _RULE_LINE_RE.findall(path.read_text(encoding="utf-8")):
        text = " ".join(_CITATIONS_RE.sub("", rest).split())
        out[rule] = (text, rule_digest(text), bool(_RETIRED_RE.fullmatch(text)))
    return out


def live_policy(
    policies: dict[str, PolicyEntry], definitions: dict[str, TraitDefinition]
) -> dict[str, PolicyEntry]:
    """Entries of defined, non-retired traits; a retired key is history."""
    return {
        tid: entry
        for tid, entry in policies.items()
        if tid in definitions and definitions[tid].retired is None
    }


def guide_changes(
    policies: dict[str, PolicyEntry],
    rules: dict[str, tuple[str, str, bool]],
) -> dict[str, list[str]]:
    """Trait → a note per cited rule whose stored digest differs from the
    current one (`ID <old> → <new>`), or that is missing or retired."""
    out: dict[str, list[str]] = {}
    for tid, entry in sorted(policies.items()):
        notes: list[str] = []
        for rule, stored in sorted(entry.rules.items()):
            found = rules.get(rule)
            if found is None:
                notes.append(f"{rule} missing")
            elif found[2]:
                notes.append(f"{rule} retired")
            elif found[1] != stored:
                notes.append(f"{rule} {stored} → {found[1]}")
        if notes:
            out[tid] = notes
    return out
