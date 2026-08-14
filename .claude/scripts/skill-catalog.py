#!/usr/bin/env python3
"""Skill-catalog generator + slash-pointer linter for the skill-router skill.

The router (.claude/skills/skill-router/SKILL.md) is hand-owned above the
marker line and generated below it. Hand-maintained catalogs rot — a previous
router shipped dead pointers undetected until an audit — so this script
generates the mechanical part and lints the rest.

  --check (default)
      Exit 1 if the generated section is stale, or any /name reference in a
      skill or command body resolves to no installed skill, no installed
      command, and no ALLOWED_SLASHES entry.
  --write
      Regenerate everything below the marker line. Refuses if the marker is
      missing. Deterministic (sorted) and idempotent.

Warnings (reported, never exit-code failures): a quoted trigger phrase claimed
by two or more model-invocable skill descriptions; an ALLOWED_SLASHES entry no
longer referenced anywhere; a commented-out disable-model-invocation key the
loader ignores.

Pure standard library; mirrors harness_lifecycle/gap.py conventions.
"""

from __future__ import annotations

import argparse
import difflib
import re
from dataclasses import dataclass
from pathlib import Path

MARKER = "<!-- generated:skill-catalog -->"
ROUTER_REL = Path("skills/skill-router/SKILL.md")
WRITE_CMD = "python3 .claude/scripts/skill-catalog.py --write"

# Slash tokens that legitimately resolve outside .claude/skills and
# .claude/commands. One-word reason each; --check warns when an entry stops
# being referenced so the list stays minimal.
ALLOWED_SLASHES: dict[str, str] = {
    "/code-intel:index-repo": "plugin",
    "/code-intel:setup": "plugin",
    "/codex": "plugin",
    "/codex-check": "plugin",
    "/codex-critique": "plugin",
    "/codex-diagnose": "plugin",
    "/codex-implement": "plugin",
    "/codex-research": "plugin",
    "/codex-review": "plugin",
    "/goal": "prompt-syntax",  # teach-session prompt directive, not a command
    "/login": "url-path",  # i-have-adhd example: open `/login`
    "/subtask": "builtin",  # Claude Code built-in, agent-matrix docs it
    "/tmp": "path",  # improve-codebase-architecture temp-dir fallback
}

# A slash reference: /name preceded by line start, whitespace, an opening
# paren/bracket/asterisk/quote, or an OPENING backtick (a backtick preceded by
# one of those, or at line start — a closing backtick as in `eval`/`exec` does
# not open a ref). Not a path segment (next char `/`), not a filename
# (`.ext`), not a compound word (next char `-`). Colon admits plugin /ns:cmd.
SLASH_REF = re.compile(
    r"(?:^|(?<=[\s(*\[\"])|(?<=^`)|(?<=[\s(*\[\"]`))"
    r"(/[a-z](?:[a-z0-9:-]*[a-z0-9])?)"
    r"(?!\.\w|[\w/-])"
)

# A backticked bare skill/command name, as the hand-owned router table uses.
BARE_NAME = re.compile(r"`([a-z][a-z0-9-]*)`")

# A quoted trigger phrase inside a description: 'like this' or "like this",
# opened after whitespace/punctuation so apostrophes ("project's") don't pair.
QUOTED_PHRASE = re.compile(
    r"(?:(?<=[\s(/:—-])|^)(?:'([^']{2,80}?)'|\"([^\"]{2,80}?)\")(?=[\s,.;:)!?]|$)"
)

FRONTMATTER_KEY = re.compile(r"^([A-Za-z][\w-]*):\s*(.*)$")
SENTENCE_END = re.compile(r"(.*?[.!?])(?:\s|$)")


@dataclass(frozen=True)
class Surface:
    """One user- or model-reachable unit: a skill or a command."""

    name: str
    kind: str  # "skill" | "command"
    slash_only: bool
    description: str
    path: Path
    commented_disable: bool = False  # disable-model-invocation present but commented out


# --- Parsing ------------------------------------------------------------------


def parse_frontmatter(text: str) -> dict[str, str]:
    """Parse the YAML-subset frontmatter this harness uses: plain scalars,
    quoted scalars, and '>' / '|' block scalars. Unknown lines are skipped."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}
    fields: dict[str, str] = {}
    i = 1
    while i < len(lines):
        line = lines[i]
        if line.strip() == "---":
            break
        match = FRONTMATTER_KEY.match(line)
        if not match:
            i += 1
            continue
        key, value = match.group(1), match.group(2).strip()
        if value in {">", "|", ">-", "|-"}:
            block: list[str] = []
            i += 1
            while i < len(lines) and (lines[i].startswith((" ", "\t")) or not lines[i].strip()):
                block.append(lines[i].strip())
                i += 1
            fields[key] = " ".join(part for part in block if part)
            continue
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        fields[key] = value
        i += 1
    return fields


def _frontmatter_block(text: str) -> str:
    """The raw lines between the opening and closing frontmatter fences."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return ""
    block: list[str] = []
    for line in lines[1:]:
        if line.strip() == "---":
            break
        block.append(line)
    return "\n".join(block)


def load_skills(claude_dir: Path) -> list[Surface]:
    """Every .claude/skills/*/SKILL.md, classified by invocation mode. Only an
    uncommented `disable-model-invocation: true` key blocks model invocation —
    matching the loader's observed behaviour; a commented-out key is flagged
    (warning) but never changes classification."""
    surfaces: list[Surface] = []
    for skill_md in sorted(claude_dir.glob("skills/*/SKILL.md")):
        raw = skill_md.read_text(encoding="utf-8")
        fields = parse_frontmatter(raw)
        block = _frontmatter_block(raw)
        surfaces.append(
            Surface(
                name=fields.get("name", skill_md.parent.name),
                kind="skill",
                slash_only=fields.get("disable-model-invocation") == "true",
                description=fields.get("description", ""),
                path=skill_md,
                commented_disable=(
                    "disable-model-invocation" in block
                    and "disable-model-invocation" not in fields
                ),
            )
        )
    return surfaces


def load_commands(claude_dir: Path) -> list[Surface]:
    """Every .claude/commands/*.md — always user-launched."""
    surfaces: list[Surface] = []
    for command_md in sorted(claude_dir.glob("commands/*.md")):
        fields = parse_frontmatter(command_md.read_text(encoding="utf-8"))
        surfaces.append(
            Surface(
                name=command_md.stem,
                kind="command",
                slash_only=True,
                description=fields.get("description", ""),
                path=command_md,
            )
        )
    return surfaces


def first_sentence(text: str) -> str:
    """First sentence of a description, whitespace-collapsed."""
    collapsed = " ".join(text.split())
    match = SENTENCE_END.match(collapsed)
    return match.group(1) if match else collapsed


# --- Rendering ----------------------------------------------------------------


def _cell(text: str) -> str:
    return text.replace("|", "\\|") if text else "(no description)"


def render_catalog(skills: list[Surface], commands: list[Surface]) -> str:
    """The generated section: everything below the marker line. Model-invocable
    skills are names only — the model holds their descriptions natively; the
    slash table carries gists because the model never sees those descriptions."""
    model = sorted((s for s in skills if not s.slash_only), key=lambda s: s.name)
    slash = sorted([s for s in skills if s.slash_only] + commands, key=lambda s: s.name)
    lines = [
        "",
        f"<!-- Generated by `{WRITE_CMD}` — edit above the marker only. -->",
        "",
        "## Model-invocable skills",
        "",
        ", ".join(f"`{s.name}`" for s in model),
        "",
        "## Slash-only workflows and commands",
        "",
        "| Surface | Use |",
        "|---|---|",
    ]
    lines += [f"| `/{s.name}` | {_cell(first_sentence(s.description))} |" for s in slash]
    return "\n".join(lines) + "\n"


def split_at_marker(text: str) -> tuple[str, str] | None:
    """(hand-owned part incl. marker line, generated part), or None if the
    marker is missing."""
    lines = text.splitlines(keepends=True)
    for idx, line in enumerate(lines):
        if line.strip() == MARKER:
            return "".join(lines[: idx + 1]), "".join(lines[idx + 1 :])
    return None


# --- Linting ------------------------------------------------------------------


def slash_refs(path: Path) -> list[tuple[int, str]]:
    """(line number, token) for every slash reference in the file."""
    refs: list[tuple[int, str]] = []
    for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        refs.extend((lineno, match.group(1)) for match in SLASH_REF.finditer(line))
    return refs


NEGATION_MARKERS = ("Never trigger", "Do NOT")


def _positive_span(description: str) -> str:
    """Description text up to the first negation marker. Phrases quoted after
    one ('Never trigger on X') are negative examples, not claims; positives
    after a negation clause are missed — acceptable for a warning-only check."""
    cut = len(description)
    for marker in NEGATION_MARKERS:
        idx = description.find(marker)
        if idx != -1:
            cut = min(cut, idx)
    return description[:cut]


def trigger_phrase_warnings(skills: list[Surface]) -> list[str]:
    """Quoted trigger phrases claimed by 2+ model-invocable descriptions."""
    claims: dict[str, set[str]] = {}
    for skill in skills:
        if skill.slash_only:
            continue
        for match in QUOTED_PHRASE.finditer(_positive_span(skill.description)):
            phrase = (match.group(1) or match.group(2)).lower()
            claims.setdefault(phrase, set()).add(skill.name)
    return [
        f"trigger phrase '{phrase}' claimed by {', '.join(sorted(names))}"
        for phrase, names in sorted(claims.items())
        if len(names) >= 2
    ]


def frontmatter_warnings(skills: list[Surface]) -> list[str]:
    """Skills whose frontmatter carries a commented-out disable-model-invocation."""
    return [
        f"{skill.name}: commented-out disable-model-invocation in frontmatter"
        " — the loader ignores it; uncomment or delete"
        for skill in sorted(skills, key=lambda s: s.name)
        if skill.commented_disable
    ]


# --- Commands -----------------------------------------------------------------


def _rel(path: Path, root: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def cmd_check(root: Path) -> int:
    claude_dir = root / ".claude"
    skills = load_skills(claude_dir)
    commands = load_commands(claude_dir)
    failures: list[str] = []
    warnings: list[str] = []

    known = {s.name for s in skills} | {c.name for c in commands}
    router = claude_dir / ROUTER_REL
    if not router.is_file():
        failures.append(f"missing {_rel(router, root)} — create it with the marker, then run --write")
    else:
        parts = split_at_marker(router.read_text(encoding="utf-8"))
        if parts is None:
            failures.append(f"marker {MARKER} missing from {_rel(router, root)}")
        else:
            # The hand-owned half names skills bare (`grilling`); a rename
            # would leave those stale while the generated tables stay green.
            for lineno, line in enumerate(parts[0].splitlines(), start=1):
                failures.extend(
                    f"unresolved skill name `{name}` at {_rel(router, root)}:{lineno}"
                    " (hand-owned section) — no installed skill or command"
                    for name in (m.group(1) for m in BARE_NAME.finditer(line))
                    if name not in known
                )
        if parts is not None and parts[1] != render_catalog(skills, commands):
            diff = list(
                difflib.unified_diff(
                    parts[1].splitlines(),
                    render_catalog(skills, commands).splitlines(),
                    fromfile="on-disk",
                    tofile="regenerated",
                    lineterm="",
                )
            )
            excerpt = "\n".join("    " + line for line in diff[:15])
            failures.append(f"stale generated section — run `{WRITE_CMD}`\n{excerpt}")

    used_allowlist: set[str] = set()
    resolved = 0
    for surface in skills + commands:
        for lineno, token in slash_refs(surface.path):
            if token[1:] in known:
                resolved += 1
            elif token in ALLOWED_SLASHES:
                used_allowlist.add(token)
                resolved += 1
            else:
                failures.append(
                    f"dead slash pointer {token} at {_rel(surface.path, root)}:{lineno}"
                    " — no installed skill, command, or allowlist entry"
                )
    warnings.extend(
        f"allowlist entry {token} ({ALLOWED_SLASHES[token]}) is no longer referenced — remove it"
        for token in sorted(set(ALLOWED_SLASHES) - used_allowlist)
    )
    warnings.extend(trigger_phrase_warnings(skills))
    warnings.extend(frontmatter_warnings(skills))

    model_count = sum(1 for s in skills if not s.slash_only)
    print(f"## skill-catalog check: {root}")
    print(
        f"{len(skills)} skills ({model_count} model-invocable,"
        f" {len(skills) - model_count} slash-only), {len(commands)} commands"
    )
    if not failures:
        print("OK   generated section is current")
        print(f"OK   {resolved} slash references resolve ({len(used_allowlist)} allowlisted)")
    for warning in warnings:
        print(f"WARN {warning}")
    for failure in failures:
        print(f"FAIL {failure}")
    return 1 if failures else 0


def cmd_write(root: Path) -> int:
    claude_dir = root / ".claude"
    router = claude_dir / ROUTER_REL
    if not router.is_file():
        raise SystemExit(f"refusing: {_rel(router, root)} does not exist")
    parts = split_at_marker(router.read_text(encoding="utf-8"))
    if parts is None:
        raise SystemExit(
            f"refusing: marker {MARKER} missing from {_rel(router, root)}"
            " — everything above it is hand-owned; add the marker where the generated section starts"
        )
    skills = load_skills(claude_dir)
    commands = load_commands(claude_dir)
    updated = parts[0] + render_catalog(skills, commands)
    if updated == parts[0] + parts[1]:
        print(f"already current: {_rel(router, root)}")
    else:
        router.write_text(updated, encoding="utf-8")
        print(f"regenerated: {_rel(router, root)}")
    for warning in trigger_phrase_warnings(skills) + frontmatter_warnings(skills):
        print(f"WARN {warning}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate/lint the skill-router catalog.")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--check", action="store_true", help="verify catalog + slash pointers (default)")
    mode.add_argument("--write", action="store_true", help="regenerate the section below the marker")
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).resolve().parents[2],
        help="repo root containing .claude/ (default: derived from script location)",
    )
    args = parser.parse_args(argv)
    root = args.root.resolve()
    if not (root / ".claude").is_dir():
        raise SystemExit(f"no .claude/ under {root} — pass --root")
    return cmd_write(root) if args.write else cmd_check(root)


if __name__ == "__main__":
    raise SystemExit(main())
