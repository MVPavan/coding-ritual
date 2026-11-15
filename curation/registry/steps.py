"""Playbooks and their steps: the frontmatter step lists (unit-kinds St1-St3).

A playbook is `<playbooks_dir>/<name>.md`; files in its subfolders are its
references, never playbooks. The frontmatter is the one source of the
playbook's trigger, its own traits and its ordered steps (St2).
"""

from __future__ import annotations

import posixpath
import re
import subprocess
from pathlib import Path
from typing import Literal

import yaml
from pydantic import Field, model_validator

from curation.registry.config import RegistryConfig
from curation.registry.loaders import _StrictYamlLoader
from curation.registry.models import StrictModel, _check_trait_ids
from curation.scan.catalog import folder_files, hash_files

# A call names a unit by kind and name (St1); a reference is a load, not a call.
CALL_KINDS = ("skill", "playbook")


class Action(StrictModel):
    """One own action of a step, described by a trait (T3)."""

    trait: str

    @model_validator(mode="after")
    def _check(self) -> Action:
        _check_trait_ids([self.trait], "trait")
        return self


class Call(StrictModel):
    """One call of a step: `to` a unit, the callee traits the step relies on (`needs`; absent means all), and a condition on this call
    only (`when`)."""

    to: str
    needs: list[str] = Field(default_factory=list)
    when: str | None = None

    @model_validator(mode="after")
    def _check(self) -> Call:
        _check_trait_ids(self.needs, "needs")
        return self

    def label(self) -> str:
        out = self.to
        if self.needs:
            out += f" needs [{', '.join(self.needs)}]"
        if self.when:
            out += f" (when: {self.when})"
        return out


class Load(StrictModel):
    """One reference a step reads, by path relative to the playbook file, and
    a condition on this load only. A load is not a call (St1: B3 does not
    apply)."""

    path: str
    when: str | None = None

    def label(self) -> str:
        return f"{self.path} (when: {self.when})" if self.when else self.path


class Step(StrictModel):
    """One position in a playbook's list (St1)."""

    id: str
    when: str
    actions: list[Action] = Field(default_factory=list)
    calls: list[Call] = Field(default_factory=list)
    loads: list[Load] = Field(default_factory=list)

    @model_validator(mode="after")
    def _check(self) -> Step:
        if not (self.actions or self.calls or self.loads):
            raise ValueError(f"{self.id}: a step has an action, a call or a load")
        return self

    @property
    def traits(self) -> list[str]:
        return [a.trait for a in self.actions]

    def signature(self) -> set[str]:
        """What the step does: its action traits, calls and loads."""
        return (
            {f"trait:{t}" for t in self.traits}
            | {f"call:{c.to}" for c in self.calls}
            | {f"load:{x.path}" for x in self.loads}
        )


class Playbook(StrictModel):
    """A playbook's frontmatter, plus its name and repository-relative path."""

    name: str
    path: str
    trigger: str
    traits: list[str] = Field(default_factory=list)
    steps: list[Step]

    @model_validator(mode="after")
    def _check(self) -> Playbook:
        _check_trait_ids(self.traits, "traits")
        if not self.steps:
            raise ValueError("a playbook has at least one step")
        return self

    @property
    def holder(self) -> str:
        """The `doc:` key under which the playbook holds traits; ledger adopts
        target the playbook file the same way (T3)."""
        return f"doc:{self.path}"

    @property
    def references_dir(self) -> str:
        """The playbook's own reference folder, `playbooks/<name>/` (F3)."""
        return posixpath.join(posixpath.dirname(self.path), self.name)

    def load_path(self, load: Load) -> str | None:
        """A load's repository path (the registry's `doc:` identity, St1), or
        None unless it lies under the playbook's own reference folder: a
        reference belongs to one playbook (F1, F3), and a file directly in
        the playbooks folder is a playbook, which a step calls."""
        if load.path.startswith("/"):
            return None
        folder = posixpath.dirname(self.path)
        resolved = posixpath.normpath(posixpath.join(folder, load.path))
        if not resolved.startswith(self.references_dir + "/"):
            return None
        return resolved

    def unit_traits(self) -> list[str]:
        """The traits the playbook holds: its own, then each step's actions,
        first occurrence kept (T3: never a callee's)."""
        out: list[str] = []
        for tid in self.traits + [t for s in self.steps for t in s.traits]:
            if tid not in out:
                out.append(tid)
        return out


_FRONTMATTER_RE = re.compile(r"\A---\n(.*?\n)---\n", re.DOTALL)
_PLAIN_WHEN_RE = re.compile(
    r"""^[ \t]*(?:-[ \t]+)?(?:when|"when"|'when'):[ \t]+(?![ \t"'|>]).* #""",
    re.MULTILINE,
)


def parse_playbook(name: str, path: str, text: str) -> Playbook:
    """Parse one playbook file; raises ValueError naming the problem."""
    match = _FRONTMATTER_RE.match(text)
    if match is None:
        raise ValueError("no frontmatter (`---` block at the top)")
    truncated = _PLAIN_WHEN_RE.search(match.group(1))
    if truncated is not None:
        raise ValueError(
            f"YAML cuts a plain `when:` at ' #': quote it or write full step IDs: "
            f"{truncated.group(0).strip()}"
        )
    try:
        raw = yaml.load(match.group(1), Loader=_StrictYamlLoader)
    except yaml.YAMLError as exc:
        raise ValueError(str(exc)) from exc
    if not isinstance(raw, dict):
        raise TypeError("frontmatter must be a mapping")
    if "name" in raw or "path" in raw:
        raise ValueError("`name` and `path` come from the file, not frontmatter")
    return Playbook.model_validate({"name": name, "path": path, **raw})


def playbook_files(cfg: RegistryConfig) -> list[Path]:
    """The playbook files: `*.md` directly in the playbooks folder."""
    folder = cfg.playbooks_dir
    return sorted(folder.glob("*.md")) if folder.is_dir() else []


def playbook_relpath(cfg: RegistryConfig, name: str) -> str:
    return str((cfg.playbooks_dir / f"{name}.md").relative_to(cfg.repo_root))


def playbook_tree_hash(cfg: RegistryConfig, rel: str) -> str:
    """A playbook's identity as a ledger target (`doc:<rel>`): its file and
    every file in its reference folder `playbooks/<name>/` (F3), so a
    reference edit changes it. Framed like `doc:` hashes, by repository path;
    with no reference folder it equals the file's own `doc:` hash."""
    file = cfg.repo_root / rel
    refs = file.with_suffix("")
    files = [file] + (folder_files(refs) if refs.is_dir() else [])
    return hash_files(cfg.repo_root, files)


def load_playbooks(cfg: RegistryConfig) -> tuple[dict[str, Playbook], list[str]]:
    """Every playbook by name; parse and schema errors, one per file."""
    out: dict[str, Playbook] = {}
    errors: list[str] = []
    for file in playbook_files(cfg):
        rel = str(file.relative_to(cfg.repo_root))
        try:
            out[file.stem] = parse_playbook(
                file.stem, rel, file.read_text(encoding="utf-8")
            )
        except Exception as exc:  # noqa: BLE001 - surfaced as a validation error
            errors.append(f"{rel}: {exc}")
    return out, errors


# --- per-step changes between two revisions (St3) ------------------------------

ChangeKind = Literal[
    "added",
    "removed",
    "moved",
    "condition",
    "traits",
    "calls",
    "loads",
    "trigger",
    "playbook-traits",
]


class StepChange(StrictModel):
    kind: ChangeKind
    step: str
    detail: str = ""


def _pair(old: list[Step], new: list[Step]) -> list[tuple[int, int]]:
    """(old index, new index) pairs, one to one. Steps pair by what they do,
    not by number, so renumbering is no change: first identical signatures,
    preferring the same condition, then the nearest position (so repeated
    signatures still pair by condition); then the most shared traits, calls
    and loads, then the same condition, then the nearest position. A step
    sharing nothing with any other stays unpaired, and a split pairs one part
    and adds the other."""
    pairs: list[tuple[int, int]] = []
    free_old = set(range(len(old)))
    free_new = set(range(len(new)))

    def take(candidates: list[tuple[int, ...]]) -> None:
        for *_, i, j in sorted(candidates):
            if i in free_old and j in free_new:
                pairs.append((i, j))
                free_old.discard(i)
                free_new.discard(j)

    take(
        [
            (-int(old[i].when == new[j].when), abs(i - j), i, j)
            for i in free_old
            for j in free_new
            if old[i].signature() == new[j].signature()
        ]
    )
    candidates: list[tuple[int, ...]] = []
    for i in free_old:
        for j in free_new:
            shared = len(old[i].signature() & new[j].signature())
            same_when = int(old[i].when == new[j].when)
            if shared or same_when:
                candidates.append((-shared, -same_when, abs(i - j), i, j))
    take(candidates)
    return sorted(pairs, key=lambda p: p[1])


def _kept_order(olds: list[int]) -> set[int]:
    """The longest increasing subsequence of old positions (taken in new
    order); ties keep earlier old positions. Old positions outside it moved."""
    n = len(olds)
    longest = [1] * n  # longest increasing run starting at each index
    for i in range(n - 1, -1, -1):
        for j in range(i + 1, n):
            if olds[j] > olds[i]:
                longest[i] = max(longest[i], longest[j] + 1)
    kept: set[int] = set()
    need = max(longest, default=0)
    last, start = -1, 0
    while need:
        options = [k for k in range(start, n) if longest[k] == need and olds[k] > last]
        k = min(options, key=lambda x: olds[x])
        kept.add(olds[k])
        last, start, need = olds[k], k + 1, need - 1
    return kept


def _diff_list(before: list[str], after: list[str]) -> str:
    gone = [f"-{x}" for x in before if x not in after]
    came = [f"+{x}" for x in after if x not in before]
    return " ".join(gone + came)


def step_changes(old: Playbook | None, new: Playbook | None) -> list[StepChange]:
    """Per-step changes from `old` to `new` (St3): added, removed, moved,
    condition, traits, calls and loads changed, plus the playbook's trigger and own
    traits. A wording edit outside these fields is no change."""
    if old is None and new is None:
        return []
    if old is None or new is None:
        kind: ChangeKind = "added" if old is None else "removed"
        book = new if old is None else old
        assert book is not None
        return [StepChange(kind=kind, step=s.id, detail=s.when) for s in book.steps]
    changes: list[StepChange] = []
    if old.trigger != new.trigger:
        changes.append(
            StepChange(kind="trigger", step=new.name, detail=f"{new.trigger}")
        )
    if set(old.traits) != set(new.traits):
        changes.append(
            StepChange(
                kind="playbook-traits",
                step=new.name,
                detail=_diff_list(old.traits, new.traits),
            )
        )
    pairs = _pair(old.steps, new.steps)
    kept = _kept_order([i for i, _ in pairs])
    paired_old = {i for i, _ in pairs}
    paired_new = {j for _, j in pairs}
    for i, step in enumerate(old.steps):
        if i not in paired_old:
            changes.append(StepChange(kind="removed", step=step.id, detail=step.when))
    for j, step in enumerate(new.steps):
        if j not in paired_new:
            changes.append(StepChange(kind="added", step=step.id, detail=step.when))
    for i, j in pairs:
        a, b = old.steps[i], new.steps[j]
        name = a.id if a.id == b.id else f"{a.id} → {b.id}"
        if i not in kept:
            changes.append(StepChange(kind="moved", step=name))
        if a.when != b.when:
            changes.append(
                StepChange(kind="condition", step=name, detail=f"{a.when} → {b.when}")
            )
        if set(a.traits) != set(b.traits):
            changes.append(
                StepChange(
                    kind="traits", step=name, detail=_diff_list(a.traits, b.traits)
                )
            )
        for kind, before, after in (
            ("calls", [c.label() for c in a.calls], [c.label() for c in b.calls]),
            ("loads", [x.label() for x in a.loads], [x.label() for x in b.loads]),
        ):
            if set(before) != set(after):
                changes.append(
                    StepChange(kind=kind, step=name, detail=_diff_list(before, after))
                )
    return changes


GIT_TIMEOUT = 15


def playbook_at(cfg: RegistryConfig, name: str, rev: str | None) -> Playbook | None:
    """The playbook at git revision `rev` (the working tree when None); None
    when the file is absent there. Raises SystemExit on a bad revision or an
    unparseable file."""
    rel = playbook_relpath(cfg, name)
    if rev is None:
        file = cfg.repo_root / rel
        if not file.is_file():
            return None
        text = file.read_text(encoding="utf-8")
    else:
        root = str(cfg.repo_root)
        try:
            check = subprocess.run(
                [
                    "git",
                    "-C",
                    root,
                    "rev-parse",
                    "--verify",
                    "--quiet",
                    f"{rev}^{{commit}}",
                ],
                capture_output=True,
                timeout=GIT_TIMEOUT,
                check=False,
            )
            if check.returncode != 0:
                raise SystemExit(f"{rev!r} is not a commit")
            shown = subprocess.run(
                ["git", "-C", root, "show", f"{rev}:{rel}"],
                capture_output=True,
                timeout=GIT_TIMEOUT,
                check=False,
            )
        except (OSError, subprocess.SubprocessError) as exc:
            raise SystemExit(f"git failed: {exc}") from exc
        if shown.returncode != 0:
            return None
        text = shown.stdout.decode("utf-8")
    try:
        return parse_playbook(name, rel, text)
    except Exception as exc:
        raise SystemExit(f"{rel} at {rev or 'the working tree'}: {exc}") from exc
