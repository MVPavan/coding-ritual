#!/usr/bin/env python3
"""Check or repair the Codex view of this repository's harness.

`--check` writes nothing and exits 1 when anything has drifted, printing one
line per drift. `--write` repairs what it can, then checks again and exits 1
only if drift remains (each remaining line says why it needs a hand).

What it keeps:

- Hooks copied byte-identical from `.claude/hooks/` to `.codex/hooks/`
  (`IDENTICAL_HOOKS`; the Claude copy is the source).
- Declared pairs that differ by design (`PAIRS`): both halves exist. A pending
  pair (its Codex half not built yet) only needs the Claude half.
- `.codex/hooks.json` parses, holds every registration in `WIRING` (plus each
  active pair's), and every `.codex/hooks/<script>` it names exists.
- Root-only files (`ROOT_ONLY`) never appear under `.codex/hooks/`; the Codex
  session hook calls `.claude/hooks/bead-mirror.py` by path, by design.
- `.codex/skills` does not exist; Codex reads `.agents/skills` directly.
- `.agents/skills` is a real directory holding at least one `<n>/SKILL.md`, and
  the Claude skill view matches the layout in `SKILL_LAYOUT`: `dir`
  (`.claude/skills` links to `.agents/skills`) or `per-skill` (one link
  `.claude/skills/<n>` per `.agents/skills/<n>` with a `SKILL.md`).

`--write` only copies hooks and makes or retires skill links. It writes through
real paths inside the repository (never through a symlink), replaces files
atomically, and deletes only a skill link in exactly the form it creates. Wiring,
root-only files and anything else unexpected are reported for a hand.

Stdlib only. `--repo` points it at another tree (tests use fixtures).
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

IDENTICAL_HOOKS = (
    "block-dangerous-commands.sh",
    "bd-prime.sh",
    "bead-mirror-session.sh",
)


@dataclass(frozen=True)
class Pair:
    """A Claude hook and its Codex twin, which differ by design."""

    claude: str
    codex: str
    pending: bool = False  # Codex half not built yet; flip when it lands.
    wiring: tuple[str, str] | None = None  # (event, matcher) once active


@dataclass(frozen=True)
class Wiring:
    """A `.codex/hooks.json` registration: `event` -> `matcher` -> script."""

    event: str
    matcher: str
    script: str


SESSION = "startup|resume|clear|compact"
WIRING = (
    Wiring("SessionStart", SESSION, "bd-prime.sh"),
    Wiring("SessionStart", SESSION, "bead-mirror-session.sh"),
    Wiring("PreToolUse", "Bash", "block-dangerous-commands.sh"),
)


PAIRS = (
    Pair(
        ".claude/hooks/block-generated-edits.sh",
        ".codex/hooks/block-generated-edits.py",
        wiring=("PreToolUse", "apply_patch|Edit|Write"),
    ),
    Pair(
        ".claude/hooks/autopilot-branch-guard.sh",
        ".codex/hooks/autopilot-branch-guard.py",
        pending=True,  # U5: set wiring=(event, matcher) when this flips
    ),
)

ROOT_ONLY = ("harness-staleness-nudge.sh", "bead-mirror.py")
ROOT_ONLY_PREFIX = "harness-"

SKILL_LAYOUT = Path("mvp-harness/plugins/mvp-plugin/scripts/skill-layout.txt")
HOOK_REF = re.compile(r"\.codex/hooks/([A-Za-z0-9_.-]+)")


class Sync:
    """Collects drift lines and, in write mode, repairs what it can."""

    def __init__(self, repo: Path, write: bool) -> None:
        self.repo = repo
        self.write = write
        self.drift: list[str] = []
        self.fixed: list[str] = []

    def report(self, message: str) -> None:
        self.drift.append(message)

    def repaired(self, message: str) -> None:
        self.fixed.append(message)

    def real_dirs(self, *rels: str) -> bool:
        """Report and return False when a repo directory is a link or not a dir."""
        for rel in rels:
            path = self.repo / rel
            if path.is_symlink() or (path.exists() and not path.is_dir()):
                self.report(f"{rel}: symlink or not a directory; fix it by hand")
                return False
        return True

    def run(self) -> None:
        self.identical_hooks()
        self.pairs()
        self.hooks_json()
        self.root_only()
        self.codex_skills()
        self.skill_view()

    # Hooks -----------------------------------------------------------------

    def identical_hooks(self) -> None:
        if not self.real_dirs(".codex", ".codex/hooks"):
            return
        for name in IDENTICAL_HOOKS:
            source = self.repo / ".claude" / "hooks" / name
            target = self.repo / ".codex" / "hooks" / name
            rel = f".codex/hooks/{name}"
            if not source.is_file():
                self.report(f".claude/hooks/{name}: source hook missing")
                continue
            if target.is_symlink() or (target.exists() and not target.is_file()):
                self.report(f"{rel}: symlink or not a regular file; replace it by hand")
                continue
            if target.is_file() and target.read_bytes() == source.read_bytes():
                continue
            if self.write:
                replace_file(source, target)
                self.repaired(f"{rel}: copied from .claude/hooks/{name}")
            else:
                state = "differs from" if target.exists() else "missing, copy of"
                self.report(f"{rel}: {state} .claude/hooks/{name}")

    def pairs(self) -> None:
        for pair in PAIRS:
            if not (self.repo / pair.claude).is_file():
                self.report(f"{pair.claude}: Claude half of a declared pair missing")
            if pair.pending:
                continue
            if not (self.repo / pair.codex).is_file():
                self.report(f"{pair.codex}: Codex half of {pair.claude} missing")

    def hooks_json(self) -> None:
        path = self.repo / ".codex" / "hooks.json"
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as error:
            self.report(f".codex/hooks.json: does not parse ({error})")
            return
        for name in sorted(set(HOOK_REF.findall(json.dumps(data)))):
            if not (self.repo / ".codex" / "hooks" / name).is_file():
                self.report(f".codex/hooks.json: names missing .codex/hooks/{name}")
        wanted = list(WIRING) + [
            Wiring(*pair.wiring, Path(pair.codex).name)
            for pair in PAIRS
            if pair.wiring and not pair.pending
        ]
        for need in wanted:
            if not registered(data, need):
                self.report(
                    f".codex/hooks.json: no {need.event} [{need.matcher}] entry runs "
                    f".codex/hooks/{need.script}; add it by hand"
                )

    def root_only(self) -> None:
        hooks = self.repo / ".codex" / "hooks"
        if not hooks.is_dir():
            return
        for entry in sorted(hooks.iterdir()):
            if entry.name not in ROOT_ONLY and not entry.name.startswith(
                ROOT_ONLY_PREFIX
            ):
                continue
            self.report(f".codex/hooks/{entry.name}: root-only; remove it by hand")

    # Skills ----------------------------------------------------------------

    def codex_skills(self) -> None:
        path = self.repo / ".codex" / "skills"
        if path.exists() or path.is_symlink():
            self.report(
                ".codex/skills: must not exist (Codex reads .agents/skills; remove it by hand)"
            )

    def skill_view(self) -> None:
        layout_file = self.repo / SKILL_LAYOUT
        try:
            layout = layout_file.read_text(encoding="utf-8").strip()
        except OSError:
            self.report(f"{SKILL_LAYOUT}: layout file missing")
            return
        source = self.repo / ".agents" / "skills"
        if (
            (self.repo / ".agents").is_symlink()
            or source.is_symlink()
            or not self.skill_names()
        ):
            self.report(
                ".agents/skills: not a real directory holding <n>/SKILL.md; "
                "skill view left alone"
            )
            return
        if not self.real_dirs(".claude"):
            return
        if layout == "dir":
            self.dir_view()
        elif layout == "per-skill":
            self.per_skill_view()
        else:
            self.report(
                f"{SKILL_LAYOUT}: unknown layout {layout!r} (want dir or per-skill)"
            )

    def skill_names(self) -> set[str]:
        source = self.repo / ".agents" / "skills"
        if not source.is_dir():
            return set()
        return {e.name for e in source.iterdir() if (e / "SKILL.md").is_file()}

    def _link(self, link: Path, target: str, rel: str) -> None:
        """Make `link` a symlink to `target` at a vacant path; report any occupant.

        A link pointing elsewhere may be the user's own skill, so it is never
        replaced."""
        if link.is_symlink():
            self.report(
                f"{rel}: links to {os.readlink(link)}, want {target}; fix it by hand"
            )
            return
        if link.exists():
            self.report(
                f"{rel}: real file or directory where a link belongs; replace it by hand"
            )
            return
        if not self.write:
            self.report(f"{rel}: should link to {target}")
            return
        link.parent.mkdir(parents=True, exist_ok=True)
        link.symlink_to(target)
        self.repaired(f"{rel}: linked to {target}")

    def dir_view(self) -> None:
        view = self.repo / ".claude" / "skills"
        source = self.repo / ".agents" / "skills"
        if view.is_symlink() and view.is_dir() and view.resolve() == source.resolve():
            return
        self._link(view, "../.agents/skills", ".claude/skills")

    def per_skill_view(self) -> None:
        view = self.repo / ".claude" / "skills"
        source = self.repo / ".agents" / "skills"
        if view.is_symlink() or (view.exists() and not view.is_dir()):
            self.report(
                ".claude/skills: per-skill layout wants a real directory; replace it by hand"
            )
            return
        wanted = self.skill_names()
        if self.write:
            view.mkdir(parents=True, exist_ok=True)
        present = (
            {entry.name: entry for entry in view.iterdir()} if view.is_dir() else {}
        )
        for name in sorted(wanted):
            link = view / name
            if link.is_symlink() and link.resolve() == (source / name).resolve():
                continue
            self._link(link, made_link(name), f".claude/skills/{name}")
        for name in sorted(set(present) - wanted):
            entry = present[name]
            rel = f".claude/skills/{name}"
            ours = entry.is_symlink() and os.readlink(entry) == made_link(name)
            if not ours:
                self.report(f"{rel}: not a link this script made; remove it by hand")
            elif self.write:
                entry.unlink()
                self.repaired(f"{rel}: stale link removed")
            else:
                self.report(f"{rel}: no skill .agents/skills/{name}; link should go")


def made_link(name: str) -> str:
    """The link text `per-skill` writes for `.claude/skills/<name>`."""
    return f"../../.agents/skills/{name}"


def registered(data: object, need: Wiring) -> bool:
    """True when `need.event` has a `need.matcher` entry running `need.script`."""
    hooks = data.get("hooks") if isinstance(data, dict) else None
    entries = hooks.get(need.event) if isinstance(hooks, dict) else None
    for entry in entries if isinstance(entries, list) else ():
        if not isinstance(entry, dict) or entry.get("matcher") != need.matcher:
            continue
        group = entry.get("hooks")
        for hook in group if isinstance(group, list) else ():
            if not isinstance(hook, dict) or hook.get("type") != "command":
                continue
            command = hook.get("command")
            if isinstance(command, str) and need.script in HOOK_REF.findall(command):
                return True
    return False


def replace_file(source: Path, target: Path) -> None:
    """Copy `source` over `target` atomically: temp file beside it, then rename."""
    target.parent.mkdir(parents=True, exist_ok=True)
    handle, temp = tempfile.mkstemp(dir=target.parent, prefix=f".{target.name}.")
    os.close(handle)
    try:
        shutil.copyfile(source, temp)
        shutil.copymode(source, temp)
        os.replace(temp, target)
    except BaseException:
        os.unlink(temp)
        raise


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument(
        "--check", action="store_true", help="report drift, write nothing"
    )
    mode.add_argument("--write", action="store_true", help="repair drift, then recheck")
    parser.add_argument(
        "--repo",
        type=Path,
        default=Path(__file__).resolve().parents[2],
        help="repository root (default: this script's repository)",
    )
    args = parser.parse_args(argv)
    repo = Path(os.path.abspath(args.repo))

    if args.write:
        repair = Sync(repo, write=True)
        repair.run()
        for line in repair.fixed:
            print(f"fixed: {line}")
    final = Sync(repo, write=False)
    final.run()
    for line in final.drift:
        print(f"drift: {line}")
    return 1 if final.drift else 0


if __name__ == "__main__":
    sys.exit(main())
