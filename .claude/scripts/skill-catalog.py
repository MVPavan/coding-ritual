#!/usr/bin/env python3
"""Skill-catalog generator + slash-pointer linter for the mvp-mode router.

The router's always-loaded part (.claude/skills/mvp-mode/SKILL.md) is
hand-owned. Its full skill catalog (.claude/skills/mvp-mode/references/catalog.md)
is hand-owned above the marker line and generated below it. Hand-maintained
catalogs rot — a previous router shipped dead pointers undetected until an
audit — so this script generates the mechanical part and lints the rest.

  --check (default)
      Exit 1 if the generated section is stale; if a backticked skill name in
      the router's hand-owned text names no installed skill; if a backticked
      `principle-<name>` citation in any shipped text file under a skill folder
      resolves to no mvp-mode/principles/<name>.md; if a principle file
      (mvp-mode/principles/*.md) or a playbook file (mvp-mode/playbooks/*.md)
      has no `target`: situation entry in the router's Playbooks or Principles
      section, if an entry names nothing installed, if a skill folder is named
      principle-*, or if the router does not point at its catalog — comments
      and fenced examples excluded (unit-kinds R3); if any /name reference in any
      shipped text file under a skill folder (*.md, *.sh, *.py, *.yaml —
      references, scripts, assets included) resolves to no installed skill and
      no ALLOWED_SLASHES entry; if any `.claude/`, `.agents/` or
      `.repo-context/` path token in those same files names nothing
      (placeholder/glob tokens and a token followed by `(if present)` are
      skipped), or any backticked `playbooks/...` or `principles/...` path
      (relative to the router's folder, wherever it is written) names nothing;
      if a backticked path in the router's `routes.md` names nothing, or a
      `Replaces` line there (baseline a 64-hex sha256) names no installed skill
      entry point or playbook or principle file; or if any skill's
      `agents/openai.yaml` is missing or its `policy.allow_implicit_invocation`
      disagrees with the SKILL.md `disable-model-invocation` flag (the Codex
      twin of that flag). `routes.md` route lines count as router entries.
      Tokens under `.agents/skills/` or `.claude/skills/` resolve against
      --skills-dir; other tokens against --root, or with `--inventory <file>`
      (one installed repo path per line) against that list only, where a
      directory token exists when it is a parent of some listed path.
  --pointers-only
      Only the slash, path and principle references and `routes.md` (no
      generated-section, router-entry or sidecar checks), for a repo whose own
      skills make the shipped catalog stale. A reference to a `Replaces` old
      name resolves only when its new name does, a file beneath the old unit
      only when the corresponding file beneath the new one exists, and each
      `/old` call or old path in a repo-owned file (`repo-owned` in
      `.repo-context/harness-settings.txt`) is listed for local migration.
  --write
      Regenerate everything below the marker line and every skill's
      `agents/openai.yaml` policy block (an existing `interface:` block is
      kept verbatim). Refuses if the marker is missing. Deterministic (sorted)
      and idempotent.

Slash commands were folded into slash-only skills (2026-08-19): there is no
.claude/commands directory; a user-run workflow is a skill with
`disable-model-invocation: true`.

Principles are not skills (owner ruling 2026-11-05; unit-kinds P7): the router
lists them and the catalog does not, and a /principle-<name> reference is dead.

Warnings (reported, never exit-code failures): a quoted trigger phrase claimed
by two or more model-invocable skill descriptions; an ALLOWED_SLASHES entry no
longer referenced anywhere; a commented-out disable-model-invocation key the
loader ignores.

Every skill's frontmatter must parse as YAML (PyYAML) with string `name` and
`description`, a string `argument-hint` and a boolean `disable-model-invocation`
when present: both modes refuse to build entries otherwise, because a skill a
YAML consumer cannot load must not appear in a green catalog. Entries and
sidecar expectations are built from those YAML values. Run it with the project
environment, which declares PyYAML (`uv run python .claude/scripts/...`);
otherwise standard library, mirroring harness_lifecycle/scan.py conventions.
"""

from __future__ import annotations

import argparse
import difflib
import re
from dataclasses import dataclass, field
from pathlib import Path

MARKER = "<!-- generated:skill-catalog -->"
ROUTER_DIR = Path("mvp-mode")  # relative to the skills dir
ROUTER_REL = ROUTER_DIR / "SKILL.md"  # always loaded; hand-owned
CATALOG_REL = ROUTER_DIR / "references" / "catalog.md"  # generated below MARKER
PLAYBOOKS_REL = ROUTER_DIR / "playbooks"
PRINCIPLES_REL = ROUTER_DIR / "principles"
PRINCIPLE_PREFIX = "principle-"
ROUTES_REL = ROUTER_DIR / "routes.md"  # repo-owned, never shipped; optional
SETTINGS_REL = Path(".repo-context") / "harness-settings.txt"
SKILL_TREE_PREFIXES = (".agents/skills/", ".claude/skills/")
WRITE_CMD = "uv run python .claude/scripts/skill-catalog.py --write"

# Slash tokens that legitimately resolve outside .claude/skills. One-word
# reason each; --check warns when an entry stops
# being referenced so the list stays minimal.
ALLOWED_SLASHES: dict[str, str] = {}

# `.claude/...` path tokens that legitimately name nothing on disk (an
# illustrative example, a path that exists only in an adopted repo). One-word
# reason each; --check warns when an entry stops being referenced.
ALLOWED_PATHS: dict[str, str] = {
    # Regression fixture proves foreign legacy overlays are preserved by migration.
    ".claude/project": "foreign-repo",
    # migrate-claude-to-codex converts OTHER repos' command dirs; this repo has none.
    ".claude/commands": "foreign-repo",
    ".claude/commands/": "foreign-repo",
    # Migration handles OTHER repos' rule dirs; local guidance is in .repo-context/.
    ".claude/rules": "foreign-repo",
    ".claude/rules/": "foreign-repo",
    # Migration maps OTHER repos' agent definitions; this repo uses delegation roles.
    ".claude/agents": "foreign-repo",
    ".claude/agents/": "foreign-repo",
}

# Text files under a skill folder whose slash and path references are linted.
# Everything else (images, fixtures, binaries) is skipped by suffix.
SHIPPED_TEXT_SUFFIXES = frozenset({".md", ".sh", ".py", ".yaml", ".yml"})

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

# A repo-relative harness path token, backticked or bare: `.claude/...`,
# `.repo-context/...` or the canonical skill tree `.agents/skills/...`, not
# preceded by `/`, `~`, or a word char — so `~/.claude/...` (home dir) and
# `<repo>/.claude/...` (another checkout) are out of scope. Captures
# placeholder characters too, so a glob-ish token is recognised whole and
# skipped rather than half-matched; `:NN` line suffixes and `#fragments` end
# the token naturally. Trailing sentence periods are stripped afterwards.
CLAUDE_PATH = re.compile(
    r"(?<![\w/~])((?:\.claude|\.repo-context|\.agents)/[\w./\-<>*{}…]*)"
)
PLACEHOLDER_MARKS = ("<", ">", "*", "{", "}", "…", "...")
# A token followed by this, after its closing backtick or quote, or by a
# trailing `#` comment that is exactly this, is an intentionally conditional
# reference; a comment that only starts with it conditions something else.
IF_PRESENT = re.compile(r"[`\"']?\s*(?:\(if present\)|#\s*\(if present\)\s*$)")

# A backticked bare skill/command name, as the hand-owned router table uses.
BARE_NAME = re.compile(r"`([a-z][a-z0-9-]*)`")
PRINCIPLE_CITATION = re.compile(r"`(principle-[a-z0-9][a-z0-9-]*)`")

# A quoted trigger phrase inside a description: 'like this' or "like this",
# opened after whitespace/punctuation so apostrophes ("project's") don't pair.
QUOTED_PHRASE = re.compile(
    r"(?:(?<=[\s(/:—-])|^)(?:'([^']{2,80}?)'|\"([^\"]{2,80}?)\")(?=[\s,.;:)!?]|$)"
)

SENTENCE_END = re.compile(r"(.*?[.!?])(?:\s|$)")


@dataclass(frozen=True)
class Surface:
    """One user- or model-reachable unit: a skill."""

    name: str
    kind: str  # "skill"
    slash_only: bool
    description: str
    path: Path
    commented_disable: bool = (
        False  # disable-model-invocation present but commented out
    )


# --- Parsing ------------------------------------------------------------------


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


FRONTMATTER_TYPES: dict[str, tuple[type, str]] = {
    "name": (str, "a string"),
    "description": (str, "a string"),
    "argument-hint": (str, "a string"),
    "disable-model-invocation": (bool, "a boolean"),
}
REQUIRED_FRONTMATTER = ("name", "description")


def _yaml_frontmatter(raw: str) -> tuple[dict[str, object] | None, str | None]:
    """The frontmatter parsed as YAML, or None and why it cannot be."""
    import yaml  # PyYAML: the project environment declares it

    if not raw.startswith("---"):
        return None, "no frontmatter"
    try:
        fields = yaml.safe_load(_frontmatter_block(raw))
    except yaml.YAMLError as error:
        return None, "frontmatter is not valid YAML — " + " ".join(str(error).split())
    if not isinstance(fields, dict):
        return None, "frontmatter is not a mapping"
    return fields, None


def frontmatter_failures(root: Path, skills_dir: Path) -> list[str]:
    """Skills whose frontmatter is not valid YAML or whose known fields have the
    wrong type. Both modes refuse before building any entry."""
    try:
        import yaml  # noqa: F401
    except ImportError:
        need = "PyYAML is required to validate skill frontmatter"
        return [f"{need} — run this script with `uv run python`"]
    failures: list[str] = []
    for skill_md in sorted(skills_dir.glob("*/SKILL.md")):
        where = _rel(skill_md, root)
        fields, error = _yaml_frontmatter(skill_md.read_text(encoding="utf-8"))
        if fields is None:
            failures.append(f"{where}: {error}")
            continue
        for key in REQUIRED_FRONTMATTER:
            if key not in fields:
                failures.append(f"{where}: frontmatter lacks `{key}`")
        for key, (kind, label) in FRONTMATTER_TYPES.items():
            if key in fields and not isinstance(fields[key], kind):
                failures.append(f"{where}: frontmatter `{key}` must be {label}")
    return failures


def load_skills(skills_dir: Path) -> list[Surface]:
    """Every .claude/skills/*/SKILL.md, classified by invocation mode from the
    validated YAML values (`frontmatter_failures` runs first). Only a YAML
    `disable-model-invocation: true` blocks model invocation; a commented-out
    key is flagged (warning) but never changes classification."""
    surfaces: list[Surface] = []
    for skill_md in sorted(skills_dir.glob("*/SKILL.md")):
        raw = skill_md.read_text(encoding="utf-8")
        fields = _yaml_frontmatter(raw)[0] or {}
        name = fields.get("name")
        description = fields.get("description")
        block = _frontmatter_block(raw)
        surfaces.append(
            Surface(
                name=name if isinstance(name, str) else skill_md.parent.name,
                kind="skill",
                slash_only=fields.get("disable-model-invocation") is True,
                description=description if isinstance(description, str) else "",
                path=skill_md,
                commented_disable=(
                    "disable-model-invocation" in block
                    and "disable-model-invocation" not in fields
                ),
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


def render_catalog(skills: list[Surface]) -> str:
    """The generated section: everything below the marker line. Model-invocable
    skills are names only — the model holds their descriptions natively; the
    slash table carries gists because the model never sees those descriptions."""
    model = sorted((s for s in skills if not s.slash_only), key=lambda s: s.name)
    slash = sorted((s for s in skills if s.slash_only), key=lambda s: s.name)
    lines = [
        "",
        (
            "<!-- Generated by the harness's skill-catalog.py --write (source harness only;"
            " plugin copies are regenerated at publish) — edit above the marker only. -->"
        ),
        "",
        "## Model-invocable skills",
        "",
        ", ".join(f"`{s.name}`" for s in model),
        "",
        "## Slash-only workflows",
        "",
        "| Surface | Use |",
        "|---|---|",
    ]
    lines += [
        f"| `/{s.name}` | {_cell(first_sentence(s.description))} |" for s in slash
    ]
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


def shipped_text_files(surface: Surface) -> list[Path]:
    """Files linted for slash and `.claude/...` path references: every text
    file under a skill's folder (SKILL.md, references, scripts, assets)."""
    return sorted(
        candidate
        for candidate in surface.path.parent.rglob("*")
        if candidate.is_file() and candidate.suffix in SHIPPED_TEXT_SUFFIXES
    )


def slash_refs(path: Path) -> list[tuple[int, str]]:
    """(line number, token) for every slash reference in the file."""
    refs: list[tuple[int, str]] = []
    for lineno, line in enumerate(
        path.read_text(encoding="utf-8").splitlines(), start=1
    ):
        refs.extend((lineno, match.group(1)) for match in SLASH_REF.finditer(line))
    return refs


def claude_path_refs(path: Path) -> list[tuple[int, str]]:
    """(line number, token) for every checkable `.claude/`, `.repo-context/` or
    `.agents/` token in the file. Placeholder/glob tokens (`<name>`, `*`,
    `{a,b}`, `…`, `...`) are not checkable and a token followed by
    `(if present)` is conditional; both are omitted."""
    refs: list[tuple[int, str]] = []
    for lineno, line in enumerate(
        path.read_text(encoding="utf-8").splitlines(), start=1
    ):
        for match in CLAUDE_PATH.finditer(line):
            token = match.group(1).rstrip(".")
            if any(mark in token for mark in PLACEHOLDER_MARKS):
                continue
            if IF_PRESENT.match(line, match.end()):
                continue
            refs.append((lineno, token))
    return refs


@dataclass(frozen=True)
class Resolver:
    """Where a path token must exist: skill-tree tokens in the selected skills
    directory, others under the repo root or, given one, in an inventory of
    installed repo paths."""

    root: Path
    skills_dir: Path
    inventory: frozenset[str] | None = None

    def exists(self, token: str) -> bool:
        for prefix in SKILL_TREE_PREFIXES:
            if token.startswith(prefix) or token == prefix.rstrip("/"):
                return (self.skills_dir / token[len(prefix) :]).exists()
        if self.inventory is None:
            return (self.root / token).exists()
        want = token.rstrip("/")
        return want in self.inventory or any(
            listed.startswith(want + "/") for listed in self.inventory
        )

    def where(self) -> str:
        if self.inventory is None:
            return "nothing on disk under the repo root or the skills directory"
        return "not in the inventory or the skills directory"


def read_inventory(path: Path) -> frozenset[str]:
    """One installed repo path per line, normalized (no `./`, no trailing `/`)."""
    return frozenset(
        line.strip().removeprefix("./").rstrip("/")
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    )


def read_settings(root: Path) -> dict[str, list[str]]:
    """`.repo-context/harness-settings.txt` as {key: [value, ...]}; each line is
    `key<TAB>value`. Absent means empty."""
    path = root / SETTINGS_REL
    settings: dict[str, list[str]] = {}
    if path.is_file():
        for line in path.read_text(encoding="utf-8").splitlines():
            key, sep, value = line.partition("\t")
            if sep and key.strip() and not key.startswith("#"):
                settings.setdefault(key.strip(), []).append(value.strip())
    return settings


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


# --- Codex twin of disable-model-invocation -----------------------------------

OPENAI_YAML_REL = Path("agents/openai.yaml")
POLICY_LINE = re.compile(
    r"^\s*allow_implicit_invocation:\s*(true|false)\s*$", re.MULTILINE
)


def expected_policy(surface: Surface) -> str:
    """Codex reads `policy.allow_implicit_invocation` from agents/openai.yaml,
    never Claude's frontmatter, so the value mirrors `disable-model-invocation`:
    a slash-only skill must not be auto-invoked on either tool."""
    return "false" if surface.slash_only else "true"


def render_openai_yaml(existing: str | None, policy: str) -> str:
    """The sidecar text: any existing `interface:` block kept verbatim (it is
    cosmetic, hand-owned), followed by the generated policy block."""
    interface_lines: list[str] = []
    if existing:
        in_interface = False
        for line in existing.splitlines():
            if line.startswith("interface:"):
                in_interface = True
            elif line and not line[0].isspace():
                in_interface = False
            if in_interface:
                interface_lines.append(line)
    body = "\n".join(
        interface_lines + ["policy:", f"  allow_implicit_invocation: {policy}"]
    )
    return body + "\n"


def openai_yaml_failures(skills: list[Surface]) -> list[str]:
    """Missing sidecar, or a policy that disagrees with the frontmatter flag."""
    failures: list[str] = []
    for surface in skills:
        sidecar = surface.path.parent / OPENAI_YAML_REL
        want = expected_policy(surface)
        if not sidecar.is_file():
            failures.append(
                f"missing {sidecar.parent.parent.name}/{OPENAI_YAML_REL} — run `{WRITE_CMD}`"
            )
            continue
        match = POLICY_LINE.search(sidecar.read_text(encoding="utf-8"))
        got = match.group(1) if match else None
        if got != want:
            failures.append(
                f"{surface.name}/{OPENAI_YAML_REL}: allow_implicit_invocation is {got},"
                f" frontmatter says {want} — run `{WRITE_CMD}`"
            )
    return failures


def write_openai_yamls(skills: list[Surface]) -> int:
    """Write/refresh every skill's sidecar; returns how many files changed."""
    changed = 0
    for surface in skills:
        sidecar = surface.path.parent / OPENAI_YAML_REL
        existing = sidecar.read_text(encoding="utf-8") if sidecar.is_file() else None
        rendered = render_openai_yaml(existing, expected_policy(surface))
        if rendered != existing:
            sidecar.parent.mkdir(parents=True, exist_ok=True)
            sidecar.write_text(rendered, encoding="utf-8")
            changed += 1
    return changed


# --- Commands -----------------------------------------------------------------


def _rel(path: Path, root: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def unresolved_names(path: Path, text: str, known: set[str], root: Path) -> list[str]:
    """Hand-owned router text names skills bare (`grilling`); a rename would
    leave those stale while the generated catalog stays green."""
    return [
        f"unresolved skill name `{name}` at {_rel(path, root)}:{lineno}"
        " (hand-owned) — no installed skill"
        for lineno, line in enumerate(text.splitlines(), start=1)
        for name in (m.group(1) for m in BARE_NAME.finditer(line))
        # PointerCheck lints these, in every shipped file.
        if name not in known and not name.startswith(PRINCIPLE_PREFIX)
    ]


def installed_principles(skills_dir: Path) -> set[str]:
    """Each principle's file name; `principle-<stem>` is the unit's name."""
    return {p.name for p in (skills_dir / PRINCIPLES_REL).glob("*.md")}


# The router's Playbooks and Principles sections hold one list item per unit:
#   - `playbooks/<name>.md`: <the request it fits>
#   - `principles/<name>.md`: <the situation it applies in>
# Comments and fenced examples are stripped before parsing, so a mention there
# routes nothing (unit-kinds R3).
HTML_COMMENT = re.compile(r"<!--.*?-->", re.DOTALL)
# A fence opens with three or more backticks or tildes after at most three
# spaces; it closes at the same character, at least as long, with nothing after
# it, or at the end of the text. A backtick fence's info string has no backtick.
FENCE_OPEN = re.compile(r"^ {0,3}(`{3,}(?=[^`]*$)|~{3,})")
CODE_SPAN = re.compile(r"`([^`\n]+)`")
SECTION_HEADING = re.compile(r"^## (.+?)\s*$", re.MULTILINE)
ROUTE_ENTRY = re.compile(r"^- `([^`]+)`:\s*(.*?)\s*$")
ROUTE_SECTIONS = {
    "Playbooks": re.compile(r"playbooks/[a-z0-9][a-z0-9-]*\.md"),
    "Principles": re.compile(r"principles/[a-z0-9][a-z0-9-]*\.md"),
}


def routed_text(router_text: str) -> str:
    """Router text with comments and fenced examples removed."""
    return "\n".join(masked_lines(router_text)) + "\n"


def route_entries(router_text: str) -> tuple[dict[str, list[str]], list[str]]:
    """({section: [target, ...]}, failures) for the Playbooks and Principles
    sections. A list item that is not `target`: situation, or whose target
    does not fit its section, is a failure."""
    text = routed_text(router_text)
    headings = list(SECTION_HEADING.finditer(text))
    entries: dict[str, list[str]] = {name: [] for name in ROUTE_SECTIONS}
    failures: list[str] = []
    for name, target_form in ROUTE_SECTIONS.items():
        found = [h for h in headings if h.group(1) == name]
        if not found:
            failures.append(f"router has no `## {name}` section")
            continue
        start = found[0].end()
        later = [h.start() for h in headings if h.start() > start]
        body = text[start : later[0] if later else len(text)]
        for line in body.splitlines():
            if not line.startswith("- "):
                continue
            match = ROUTE_ENTRY.match(line)
            if not match:
                failures.append(f"{name} entry is not `target`: situation — {line!r}")
            elif not target_form.fullmatch(match.group(1)):
                failures.append(f"{name} entry target `{match.group(1)}` is malformed")
            elif not match.group(2):
                failures.append(f"{name} entry `{match.group(1)}` names no situation")
            else:
                entries[name].append(match.group(1))
    return entries, failures


# --- routes.md: the repo's own route lines and replacement mapping ----------
#   - `playbooks/<name>.md`: <the request it fits>     (also principles/)
#   - Replaces `<old unit or path>` with `<new unit or path>` (baseline <sha256>)
REPLACES_LINE = re.compile(
    r"^- Replaces `([^`]+)` with `([^`]+)` \(baseline [0-9a-f]{64}\)\s*$"
)
UNIT_FILE = re.compile(r"mvp-mode/(?:playbooks|principles)/[a-z0-9][a-z0-9-]*\.md")
# A path relative to a skill's folder or, failing that, the router's, as the
# router and its callers write a playbook or principle: `playbooks/<name>.md`,
# `principles/<name>/...`; a `:18` or `:18-20` citation suffix is not part of it.
ROUTER_RELATIVE = re.compile(r"((?:playbooks|principles)/\S*?)(?::\d+(?:-\d+)?)?")


@dataclass(frozen=True)
class Unit:
    """A `Replaces` operand: its path relative to the skills directory (a
    skill's folder, or a playbook or principle file) and, for a skill, the
    declared name a slash call uses."""

    rel: str
    name: str | None = None


def parse_unit(operand: str, skills: list[Surface]) -> Unit:
    """An operand as one identity, whichever way it is written: a skill by its
    declared name, folder or entry point (`<skill>/SKILL.md`, bare or under a
    skill tree); a principle as `principle-<name>`, `principles/<name>.md` or
    its skill-tree path; a playbook by either path."""
    if "/" not in operand and operand.startswith(PRINCIPLE_PREFIX):
        stem = operand.removeprefix(PRINCIPLE_PREFIX)
        return Unit(str(PRINCIPLES_REL / f"{stem}.md"))
    if "/" not in operand:
        folder = next(
            (s.path.parent.name for s in skills if s.name == operand), operand
        )
        return Unit(folder, operand)
    rel = operand.rstrip("/")
    for prefix in SKILL_TREE_PREFIXES:
        if rel.startswith(prefix):
            rel = rel[len(prefix) :]
            break
    else:
        if rel.startswith(("playbooks/", "principles/")):
            rel = str(ROUTER_DIR / rel)
    parts = rel.split("/")
    if len(parts) == 2 and parts[1] == "SKILL.md":
        rel = parts[0]
    if "/" in rel:
        return Unit(rel)
    declared = {s.path.parent.name: s.name for s in skills}
    return Unit(rel, declared.get(rel, rel))


def unit_installed(unit: Unit, skills_dir: Path, skills: list[Surface]) -> bool:
    """An installed unit's entry point: a loaded skill declaring the name, in
    that folder, or a regular playbook or principle file."""
    if unit.name is not None:
        return any(
            s.name == unit.name and s.path.parent.name == unit.rel for s in skills
        )
    return bool(UNIT_FILE.fullmatch(unit.rel)) and (skills_dir / unit.rel).is_file()


@dataclass(frozen=True)
class Replacement:
    old: str
    new: str
    old_unit: Unit
    new_unit: Unit
    new_resolves: bool
    lineno: int  # in `routes.md`; its operands are not ordinary references

    @staticmethod
    def _base(rel: str) -> str:
        """The folder a unit's own files sit in: a skill's folder, or a
        playbook's or principle's companion folder (its path without `.md`)."""
        return rel.removesuffix(".md") if UNIT_FILE.fullmatch(rel) else rel

    def covers(self, rel: str) -> bool:
        old = self.old_unit.rel
        return rel == old or rel.startswith(self._base(old) + "/")

    def resolves(self, rel: str, skills_dir: Path) -> bool:
        """The old unit resolves when its replacement does; a file beneath it
        only when the corresponding file beneath the new unit exists."""
        if not self.new_resolves:
            return False
        if rel == self.old_unit.rel:
            return True
        old, new = self._base(self.old_unit.rel), self._base(self.new_unit.rel)
        return (skills_dir / (new + rel[len(old) :])).exists()

    def call_resolves(self) -> bool:
        """A `/old` call resolves only to a skill the slash check knows."""
        return self.new_resolves and self.new_unit.name is not None


def read_routes(
    skills_dir: Path, root: Path, skills: list[Surface]
) -> tuple[dict[str, list[str]], list[Replacement], list[str]]:
    """({section: [target, ...]}, replacements, failures) from `routes.md`.
    Every backticked path there must resolve, except the operands of a
    `Replaces` line and router-relative paths, which `cmd_check` resolves
    through the mapping."""
    entries: dict[str, list[str]] = {name: [] for name in ROUTE_SECTIONS}
    replacements: list[Replacement] = []
    failures: list[str] = []
    path = skills_dir / ROUTES_REL
    if not path.is_file():
        return entries, replacements, failures
    where = _rel(path, root)
    lines = masked_lines(path.read_text(encoding="utf-8"))
    for lineno, line in enumerate(lines, start=1):
        spans = [m.group(1) for m in CODE_SPAN.finditer(line)]
        if line.startswith("- Replaces"):
            match = REPLACES_LINE.match(line)
            if not match:
                failures.append(
                    f"{where}: not `- Replaces `<old>` with `<new>` (baseline <sha256>)` — {line!r}"
                )
                continue
            old, new = match.groups()
            new_unit = parse_unit(new, skills)
            ok = unit_installed(new_unit, skills_dir, skills)
            if not ok:
                failures.append(
                    f"{where}: Replaces `{old}` with `{new}` — `{new}` names nothing installed"
                )
            replacements.append(
                Replacement(old, new, parse_unit(old, skills), new_unit, ok, lineno)
            )
            continue
        if (entry := ROUTE_ENTRY.match(line)) and entry.group(2):
            for name, form in ROUTE_SECTIONS.items():
                if form.fullmatch(entry.group(1)):
                    entries[name].append(entry.group(1))
        for span in spans:
            if (
                "/" not in span
                or any(c.isspace() for c in span)
                or any(mark in span for mark in PLACEHOLDER_MARKS)
                or CLAUDE_PATH.fullmatch(span)  # linted with every shipped file
                or ROUTER_RELATIVE.fullmatch(span)  # likewise, through the mapping
            ):
                continue
            if not (
                (skills_dir / ROUTER_DIR / span).exists()
                or (skills_dir / span).exists()
            ):
                failures.append(
                    f"dead path {span} at {where} — nothing in the skills directory"
                )
    return entries, replacements, failures


def replacement_for(rel: str, replacements: list[Replacement]) -> Replacement | None:
    return next((item for item in replacements if item.covers(rel)), None)


def masked_lines(text: str) -> list[str]:
    """The text's lines with comments and fenced examples blanked, numbering
    kept."""
    text = HTML_COMMENT.sub(lambda m: "\n" * m.group(0).count("\n"), text)
    kept: list[str] = []
    fence = ""
    for line in text.splitlines():
        if fence:
            stripped = line.strip()
            if (
                len(line) - len(line.lstrip(" ")) <= 3
                and stripped.startswith(fence)
                and not stripped.strip(fence[0])
            ):
                fence = ""
            kept.append("")
        elif opened := FENCE_OPEN.match(line):
            fence = opened.group(1)
            kept.append("")
        else:
            kept.append(line)
    return kept


def router_path_refs(path: Path) -> list[tuple[int, str]]:
    """(line number, path) for every backticked router-relative path outside
    comments and fenced examples, citation suffix removed; placeholder spans
    and spans followed by `(if present)` are omitted."""
    refs: list[tuple[int, str]] = []
    for lineno, line in enumerate(
        masked_lines(path.read_text(encoding="utf-8")), start=1
    ):
        for match in CODE_SPAN.finditer(line):
            ref = ROUTER_RELATIVE.fullmatch(match.group(1))
            if (
                ref
                and not any(mark in ref.group(1) for mark in PLACEHOLDER_MARKS)
                and not IF_PRESENT.match(line, match.end())
            ):
                refs.append((lineno, ref.group(1)))
    return refs


@dataclass(frozen=True)
class Ref:
    """One reference in a shipped file, resolved: `head` and `why` make its
    failure message."""

    lineno: int
    token: str
    kind: str  # "slash", "path" or "principle"
    ok: bool
    swap: Replacement | None
    head: str
    why: str


@dataclass
class PointerCheck:
    """Resolves every reference in shipped files one way: a skill-tree path
    through the `Replaces` mapping when one covers it, else on disk; a slash
    call through the mapping, else by declared name."""

    skills_dir: Path
    resolver: Resolver
    known: set[str]
    swaps: list[Replacement]
    used_slashes: set[str] = field(default_factory=set)
    used_paths: set[str] = field(default_factory=set)

    def tree_path(self, rel: str) -> tuple[bool, Replacement | None]:
        swap = replacement_for(rel, self.swaps)
        if swap is not None:
            return swap.resolves(rel, self.skills_dir), swap
        return (self.skills_dir / rel).exists(), None

    def slash(self, token: str) -> tuple[bool, Replacement | None]:
        # `/mvp-plugin:adopt` is the plugin-namespaced form of `/adopt`:
        # resolve by the bare name so shipped skills may use either.
        bare = token[1:].split(":", 1)[-1]
        swap = next((r for r in self.swaps if r.old_unit.name == bare), None)
        if swap is not None:
            return swap.call_resolves(), swap
        if bare in self.known:
            return True, None
        if token in ALLOWED_SLASHES:
            self.used_slashes.add(token)
            return True, None
        return False, None

    def shared_path(self, token: str) -> tuple[bool, Replacement | None]:
        for prefix in SKILL_TREE_PREFIXES:
            if token.startswith(prefix):
                return self.tree_path(token[len(prefix) :].rstrip("/"))
        if self.resolver.exists(token):
            return True, None
        if token in ALLOWED_PATHS:
            self.used_paths.add(token)
            return True, None
        return False, None

    def router_relative(self, span: str, home: str) -> tuple[bool, Replacement | None]:
        """A skill's own companion first, then the router's folder."""
        rel = span.rstrip("/")
        if home != str(ROUTER_DIR) and (self.skills_dir / home / rel).exists():
            return True, None
        return self.tree_path(str(ROUTER_DIR / rel))

    def refs(self, shipped: Path, home: str, skip: set[int]) -> list[Ref]:
        """Every reference in the file, except on the `skip` lines."""
        refs: list[Ref] = []
        for lineno, token in slash_refs(shipped):
            refs.append(
                Ref(
                    lineno,
                    token,
                    "slash",
                    *self.slash(token),
                    f"dead slash pointer {token}",
                    "no installed skill or allowlist entry",
                )
            )
        for lineno, token in claude_path_refs(shipped):
            refs.append(
                Ref(
                    lineno,
                    token,
                    "path",
                    *self.shared_path(token),
                    f"dead path {token}",
                    f"{self.resolver.where()}, and no allowlist entry",
                )
            )
        for lineno, span in router_path_refs(shipped):
            refs.append(
                Ref(
                    lineno,
                    span,
                    "path",
                    *self.router_relative(span, home),
                    f"dead path {span}",
                    f"nothing under {home} or {ROUTER_DIR}",
                )
            )
        text = shipped.read_text(encoding="utf-8")
        for lineno, line in enumerate(text.splitlines(), start=1):
            for match in PRINCIPLE_CITATION.finditer(line):
                name = match.group(1)
                rel = str(PRINCIPLES_REL / f"{name.removeprefix(PRINCIPLE_PREFIX)}.md")
                refs.append(
                    Ref(
                        lineno,
                        name,
                        "principle",
                        *self.tree_path(rel),
                        f"unresolved principle `{name}`",
                        f"no {rel.removeprefix(str(ROUTER_DIR) + '/')}",
                    )
                )
        return [ref for ref in refs if ref.lineno not in skip]


def unreachable_units(
    skills: list[Surface],
    skills_dir: Path,
    router_text: str,
    root: Path,
    extra: dict[str, list[str]] | None = None,
) -> list[str]:
    """Principles, playbooks and the full catalog are reached only through the
    router's always-loaded part (unit-kinds R3) and `routes.md`: each installed
    principle and playbook needs an entry, each entry a target that exists, and
    the router must point at its catalog — all outside comments and fenced
    examples."""
    router = _rel(skills_dir / ROUTER_REL, root)
    entries, failures = route_entries(router_text)
    for name, targets in (extra or {}).items():
        entries[name].extend(targets)
    # The pointer is a whole code span that resolves, from the router's folder,
    # to the catalog — not any text that merely contains its path.
    catalog = (skills_dir / CATALOG_REL).resolve()
    router_dir = skills_dir / ROUTER_DIR
    if not any(
        (router_dir / span.group(1)).resolve() == catalog
        for span in CODE_SPAN.finditer(routed_text(router_text))
    ):
        catalog_link = CATALOG_REL.relative_to(ROUTER_DIR)
        failures.append(f"{router} does not point at {catalog_link}")

    # The folder's own name and the name it declares: a leftover may hold only a
    # sidecar, or declare another name, and neither is what discovery reports.
    stray = {
        child.name
        for child in skills_dir.iterdir()
        if child.is_dir() and child.name.startswith(PRINCIPLE_PREFIX)
    } | {s.name for s in skills if s.name.startswith(PRINCIPLE_PREFIX)}
    failures.extend(
        f"skill folder {name}: a principle is a file under {PRINCIPLES_REL}, not a skill"
        for name in sorted(stray)
    )
    principles = {f"principles/{name}" for name in installed_principles(skills_dir)}
    playbooks_dir = skills_dir / PLAYBOOKS_REL
    playbooks = (
        {f"playbooks/{p.name}" for p in playbooks_dir.glob("*.md")}
        if playbooks_dir.is_dir()
        else set()
    )
    for kind, installed, routed in (
        ("principle", principles, set(entries["Principles"])),
        ("playbook", playbooks, set(entries["Playbooks"])),
    ):
        failures.extend(
            f"{kind} {name} has no entry in {router}"
            for name in sorted(installed - routed)
        )
        failures.extend(
            f"{kind} entry `{name}` in {router} names nothing installed"
            for name in sorted(routed - installed)
        )
    return failures


def repo_owned(path: Path, skills_dir: Path, owned: list[str]) -> bool:
    rel = _rel(path, skills_dir)
    return any(
        rel == entry.rstrip("/") or rel.startswith(entry.rstrip("/") + "/")
        for entry in owned
    )


def catalog_failures(
    skills: list[Surface],
    skills_dir: Path,
    root: Path,
    route_extra: dict[str, list[str]],
) -> list[str]:
    """The router's names and entries and the generated catalog section."""
    failures: list[str] = []
    known = {s.name for s in skills}
    router = skills_dir / ROUTER_REL
    catalog = skills_dir / CATALOG_REL
    if router.is_file():
        router_text = router.read_text(encoding="utf-8")
        failures.extend(unresolved_names(router, router_text, known, root))
        failures.extend(
            unreachable_units(skills, skills_dir, router_text, root, route_extra)
        )
    else:
        failures.append(f"missing {_rel(router, root)}")
    if not catalog.is_file():
        failures.append(
            f"missing {_rel(catalog, root)} — create it with the marker, then run --write"
        )
    else:
        parts = split_at_marker(catalog.read_text(encoding="utf-8"))
        if parts is None:
            failures.append(f"marker {MARKER} missing from {_rel(catalog, root)}")
        else:
            failures.extend(unresolved_names(catalog, parts[0], known, root))
        if parts is not None and parts[1] != render_catalog(skills):
            diff = list(
                difflib.unified_diff(
                    parts[1].splitlines(),
                    render_catalog(skills).splitlines(),
                    fromfile="on-disk",
                    tofile="regenerated",
                    lineterm="",
                )
            )
            excerpt = "\n".join("    " + line for line in diff[:15])
            failures.append(f"stale generated section — run `{WRITE_CMD}`\n{excerpt}")

    return failures


def cmd_check(
    root: Path,
    skills_dir: Path,
    inventory: frozenset[str] | None = None,
    pointers_only: bool = False,
) -> int:
    malformed = frontmatter_failures(root, skills_dir)
    if malformed:
        print(f"## skill-catalog check: {skills_dir}")
        for failure in malformed:
            print(f"FAIL {failure}")
        return 1
    skills = load_skills(skills_dir)
    failures: list[str] = []
    warnings: list[str] = []
    migrations: list[str] = []
    resolver = Resolver(root, skills_dir, inventory)

    route_extra, replacements, route_failures = read_routes(skills_dir, root, skills)
    failures.extend(route_failures)
    # Old names resolve through their replacement only in pointers-only mode,
    # which is how an adopted repo checks its own tree.
    swaps = replacements if pointers_only else []
    owned = read_settings(root).get("repo-owned", []) if pointers_only else []
    if not pointers_only:
        failures.extend(catalog_failures(skills, skills_dir, root, route_extra))

    check = PointerCheck(skills_dir, resolver, {s.name for s in skills}, swaps)
    resolved = {"slash": 0, "path": 0, "principle": 0}
    routes_file = skills_dir / ROUTES_REL
    mapping = {item.lineno for item in replacements}
    for surface in skills:
        home = _rel(surface.path.parent, skills_dir)
        for shipped in shipped_text_files(surface):
            is_routes = shipped == routes_file
            migrate = not is_routes and repo_owned(shipped, skills_dir, owned)
            for ref in check.refs(shipped, home, mapping if is_routes else set()):
                if ref.swap is not None and migrate:
                    migrations.append(
                        f"{_rel(shipped, skills_dir)}:{ref.lineno} {ref.token}"
                        f" — `{ref.swap.old}` is replaced by `{ref.swap.new}`"
                    )
                if ref.ok:
                    resolved[ref.kind] += 1
                else:
                    failures.append(
                        f"{ref.head} at {_rel(shipped, root)}:{ref.lineno} — {ref.why}"
                    )
    used_allowlist, used_path_allowlist = check.used_slashes, check.used_paths
    resolved_paths, resolved_citations = resolved["path"], resolved["principle"]
    warnings.extend(
        f"allowlist entry {token} ({ALLOWED_SLASHES[token]}) is no longer referenced — remove it"
        for token in sorted(set(ALLOWED_SLASHES) - used_allowlist)
    )
    warnings.extend(
        f"path allowlist entry {token} ({ALLOWED_PATHS[token]}) is no longer referenced — remove it"
        for token in sorted(set(ALLOWED_PATHS) - used_path_allowlist)
    )
    if not pointers_only:
        failures.extend(openai_yaml_failures(skills))
        warnings.extend(trigger_phrase_warnings(skills))
        warnings.extend(frontmatter_warnings(skills))

    model_count = sum(1 for s in skills if not s.slash_only)
    print(f"## skill-catalog check: {skills_dir}")
    print(
        f"{len(skills)} skills ({model_count} model-invocable, {len(skills) - model_count} slash-only)"
    )
    if not failures:
        if not pointers_only:
            print("OK   generated section is current")
        print(
            f"OK   {resolved['slash']} slash references resolve ({len(used_allowlist)} allowlisted)"
        )
        print(
            f"OK   {resolved_paths} shared path references resolve"
            f" ({len(used_path_allowlist)} allowlisted)"
        )
        print(f"OK   {resolved_citations} principle citations resolve")
        if not pointers_only:
            print(
                f"OK   {len(skills)} agents/openai.yaml sidecars match their frontmatter"
            )
    for migration in migrations:
        print(f"MIGRATE {migration}")
    for warning in warnings:
        print(f"WARN {warning}")
    for failure in failures:
        print(f"FAIL {failure}")
    return 1 if failures else 0


def cmd_write(root: Path, skills_dir: Path) -> int:
    catalog = skills_dir / CATALOG_REL
    if not catalog.is_file():
        raise SystemExit(f"refusing: {_rel(catalog, root)} does not exist")
    parts = split_at_marker(catalog.read_text(encoding="utf-8"))
    if parts is None:
        raise SystemExit(
            f"refusing: marker {MARKER} missing from {_rel(catalog, root)}"
            " — everything above it is hand-owned; add the marker where the generated section starts"
        )
    malformed = frontmatter_failures(root, skills_dir)
    if malformed:
        raise SystemExit("refusing: " + "; ".join(malformed))
    skills = load_skills(skills_dir)
    updated = parts[0] + render_catalog(skills)
    if updated == parts[0] + parts[1]:
        print(f"already current: {_rel(catalog, root)}")
    else:
        catalog.write_text(updated, encoding="utf-8")
        print(f"regenerated: {_rel(catalog, root)}")
    changed = write_openai_yamls(skills)
    print(
        f"agents/openai.yaml sidecars: {changed} written, {len(skills) - changed} already current"
    )
    for warning in trigger_phrase_warnings(skills) + frontmatter_warnings(skills):
        print(f"WARN {warning}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Generate/lint the mvp-mode skill catalog."
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--check", action="store_true", help="verify catalog + slash pointers (default)"
    )
    mode.add_argument(
        "--write", action="store_true", help="regenerate the section below the marker"
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).resolve().parents[2],
        help="repo root containing .claude/ (default: derived from script location)",
    )
    parser.add_argument(
        "--skills-dir",
        type=Path,
        default=None,
        help="skills directory to catalog/lint (default: <root>/.agents/skills, the real copy that"
        " .claude/skills links to). The publish"
        " step points this at a plugin's skills/ so its shipped router lists only shipped skills;"
        " `.agents/skills/` and `.claude/skills/` tokens resolve against it, others against --root",
    )
    parser.add_argument(
        "--inventory",
        type=Path,
        default=None,
        help="file of installed repo paths, one per line: tokens outside the skill tree"
        " resolve against this list instead of --root",
    )
    parser.add_argument(
        "--pointers-only",
        action="store_true",
        help="check only slash, path and principle references and routes.md",
    )
    args = parser.parse_args(argv)
    if args.write and (args.pointers_only or args.inventory):
        parser.error("--pointers-only and --inventory apply to --check only")
    root = args.root.resolve()
    skills_dir = (args.skills_dir or root / ".agents" / "skills").resolve()
    if not skills_dir.is_dir():
        raise SystemExit(
            f"no skills directory at {skills_dir} — pass --root or --skills-dir"
        )
    if args.write:
        return cmd_write(root, skills_dir)
    inventory = read_inventory(args.inventory) if args.inventory else None
    return cmd_check(root, skills_dir, inventory, args.pointers_only)


if __name__ == "__main__":
    raise SystemExit(main())
