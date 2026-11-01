"""Playbooks and steps in the registry (unit-kinds T1, T3, St1-St4): parsing
and validation, playbooks as trait holders, the STEPS.md index and per-step
changes between revisions."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from curation.registry import cli, steps
from curation.registry.traits import _doc_tree_hash
from tests.curation.test_registry import (
    _checkpoint,
    _defs,
    _fails_with,
    _ns,
    _trait,
    _trait_cfg,
    _write_defs,
    _write_record,
    _write_round,
    _write_skill,
)

FIX = """\
---
trigger: A defect to fix.
traits: [gate]
steps:
  - id: fix#1
    when: always
    actions: [{trait: act}]
    calls: [{to: "skill:tdd", needs: [seams]}]
  - id: fix#2
    when: the cause is confirmed
    actions: [{trait: log}]
    calls: [{to: "playbook:ship"}]
    loads: [{path: fix/notes.md, when: a flake}]
---
# Fix
"""

SHIP = """\
---
trigger: Ship it.
steps:
  - id: ship#1
    when: always
    actions: [{trait: log}]
    calls: [{to: "skill:tdd"}]
---
# Ship
"""

FIX_PATH = ".claude/skills/mvp-mode/playbooks/fix.md"


def _write_playbook(cfg: object, name: str, text: str) -> Path:
    path = cfg.playbooks_dir / f"{name}.md"  # type: ignore[attr-defined]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _playbook_cfg(base: Path, fix: str = FIX) -> object:
    """A passing registry with two playbooks; `fix` has a reference file and
    a subfolder file that is not a playbook."""
    cfg = _trait_cfg(base)
    _write_skill(cfg, "mvp-mode")
    _write_record(cfg, "mvp-mode", "core", "X", "Coordination")
    _write_defs(cfg, _defs("seams", "gate", "act", "log"))
    _write_playbook(cfg, "fix", fix)
    _write_playbook(cfg, "ship", SHIP)
    refs = cfg.playbooks_dir / "fix"  # type: ignore[attr-defined]
    refs.mkdir()
    (refs / "notes.md").write_text("Notes.\n", encoding="utf-8")
    (refs / "not-a-playbook.md").write_text("no frontmatter\n", encoding="utf-8")
    assert cli.cmd_build(cfg, _ns()) == 0
    return cfg


def test_playbooks_build_index_and_holders(tmp_path: Path) -> None:
    cfg = _playbook_cfg(tmp_path)
    assert cli.cmd_check(cfg, _ns()) == 0
    md = cfg.steps_md_path.read_text(encoding="utf-8")  # type: ignore[attr-defined]
    assert "## fix\n\n`.claude/skills/mvp-mode/playbooks/fix.md`" in md
    assert "Playbook traits: `gate`" in md
    assert "| `fix#1` | always | `act` | `skill:tdd` needs `seams` |  |" in md
    assert (
        "| `playbook:ship` | `.claude/skills/mvp-mode/playbooks/fix/notes.md` "
        "(when: a flake) |"
    ) in md
    recurrence = md.split("## Recurrence")[1]
    assert "| `log` | fix: `fix#2`; ship: `ship#1` |" in recurrence
    assert "| `skill:tdd` | fix: `fix#1`; ship: `ship#1` |" in recurrence
    traits_md = cfg.traits_md_path.read_text(encoding="utf-8")  # type: ignore[attr-defined]
    assert f"#### fix — `doc:{FIX_PATH}`\n- `gate`: Does gate.\n- `act`" in traits_md
    assert f"- playbook: `doc:{FIX_PATH}`" in traits_md


def test_check_fails_when_steps_md_is_stale(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    cfg = _playbook_cfg(tmp_path)
    _write_playbook(cfg, "fix", FIX.replace("when: always", "when: first"))
    _fails_with(cfg, capsys, "STEPS.md: generated file is stale")


@pytest.mark.parametrize(
    ("old", "new", "needle"),
    [
        ("id: fix#2", "id: fix#3", "step 2 has ID 'fix#3'; IDs are fix#<position>"),
        ("traits: [gate]", "traits: [gone]", "fix.md: trait 'gone' is undefined"),
        ("{trait: act}", "{trait: nope}", "fix#1: trait 'nope' is undefined"),
        ("needs: [seams]", "needs: [nope]", "call skill:tdd: trait 'nope'"),
        (
            "needs: [seams]",
            "needs: [seams, seams]",
            "fix#1: call skill:tdd: a needs trait is listed twice",
        ),
        ('"skill:tdd"', '"skill:none"', "no skill folder 'none'"),
        ('"playbook:ship"', '"playbook:none"', "no playbook 'none'"),
        ("fix/notes.md", "fix/gone.md", "load 'fix/gone.md': no such reference"),
        ("fix/notes.md", "ship.md", "load 'ship.md': no such reference"),
        ('"playbook:ship"', '"doc:AGENTS.md"', "; a reference is a load"),
        ("trigger:", "rules: []\ntrigger:", "Extra inputs are not permitted"),
        (
            '    actions: [{trait: act}]\n    calls: [{to: "skill:tdd", needs: [seams]}]\n',
            "",
            "fix#1: a step has an action, a call or a load",
        ),
    ],
)
def test_playbook_validation(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    old: str,
    new: str,
    needle: str,
) -> None:
    cfg = _playbook_cfg(tmp_path)
    assert old in FIX
    _write_playbook(cfg, "fix", FIX.replace(old, new, 1))
    _fails_with(cfg, capsys, needle)


def test_reference_has_one_owner(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A playbook loads only files under its own `playbooks/<name>/` (F1, F3),
    even an existing file in another playbook's folder that nothing else
    loads."""
    cfg = _playbook_cfg(tmp_path)
    _write_playbook(cfg, "fix", FIX.replace("fix/notes.md", "ship/notes.md"))
    (cfg.playbooks_dir / "ship").mkdir()  # type: ignore[attr-defined]
    (cfg.playbooks_dir / "ship" / "notes.md").write_text("x\n")  # type: ignore[attr-defined]
    _fails_with(cfg, capsys, "load 'ship/notes.md': no such reference")
    _write_playbook(cfg, "fix", FIX)
    _write_playbook(
        cfg,
        "ship",
        SHIP.replace("# Ship", "").replace(
            '[{to: "skill:tdd"}]',
            '[{to: "skill:tdd"}]\n    loads: [{path: fix/notes.md}]',
        ),
    )
    _fails_with(
        cfg,
        capsys,
        "load 'fix/notes.md': no such reference (a file under "
        ".claude/skills/mvp-mode/playbooks/ship/",
    )


def test_playbook_holds_adopted_traits(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A ledger adopt may target a playbook file; the playbook's frontmatter,
    never a traits/ours.yaml entry, is its trait list (T3)."""
    target = f"doc:{FIX_PATH}"
    cfg = _playbook_cfg(tmp_path)
    _write_round(
        cfg,
        "2026-10-14-r",
        _checkpoint("2026-10-14-r:1", "adopt", target),
        _trait("2026-10-14-r:2", "adopt", "seams", skill=target),
        trait_level=True,
    )
    _fails_with(cfg, capsys, f"trait 'seams' is not listed by {target!r}")
    _write_playbook(cfg, "fix", FIX.replace("traits: [gate]", "traits: [gate, seams]"))
    assert cli.cmd_build(cfg, _ns()) == 0
    assert cli.cmd_check(cfg, _ns()) == 0

    ours = cfg.traits_dir / "ours.yaml"  # type: ignore[attr-defined]
    ours.write_text(ours.read_text() + f'{target}:\n  tree_hash: "x"\n  traits: []\n')
    _fails_with(cfg, capsys, "a playbook's traits live in its frontmatter")


def test_build_lists_an_undefined_playbook_trait(tmp_path: Path) -> None:
    """`build` still runs while a playbook names an undefined trait; `check`
    reports it (TRAITS.md sorts it under `(undefined)`, last)."""
    cfg = _playbook_cfg(tmp_path)
    _write_playbook(cfg, "fix", FIX.replace("traits: [gate]", "traits: [later]"))
    assert cli.cmd_build(cfg, _ns()) == 0
    md = cfg.traits_md_path.read_text(encoding="utf-8")  # type: ignore[attr-defined]
    assert (
        md.split("## By trait")[1]
        .split("## Shared")[0]
        .rstrip()
        .endswith(f"### (undefined)\n\n#### `later`\n- playbook: `doc:{FIX_PATH}`")
    )


def _book(*rows: tuple[str, list[str], list[str]]) -> steps.Playbook:
    """A playbook `p` from (when, action traits, call targets) per step."""
    return steps.Playbook(
        name="p",
        path="p.md",
        trigger="t",
        steps=[
            steps.Step(
                id=f"p#{n}",
                when=when,
                actions=[steps.Action(trait=t) for t in acts],
                calls=[steps.Call(to=c) for c in calls],
            )
            for n, (when, acts, calls) in enumerate(rows, start=1)
        ],
    )


A = ("a", ["ta"], [])
B = ("b", ["tb"], ["skill:x"])
C = ("c", [], ["skill:y"])


def _kinds(old: steps.Playbook, new: steps.Playbook) -> list[tuple[str, str]]:
    return [(c.kind, c.step) for c in steps.step_changes(old, new)]


def test_step_changes() -> None:
    # An insertion renumbers the later steps but changes nothing else.
    assert _kinds(_book(A, C), _book(A, B, C)) == [("added", "p#2")]
    assert _kinds(_book(A, B, C), _book(A, C)) == [("removed", "p#2")]
    # One step moved to the front: only it is moved, not the two it passed.
    assert _kinds(_book(A, B, C), _book(C, A, B)) == [("moved", "p#3 → p#1")]
    # A swap marks the later upstream step moved (ties keep earlier ones).
    assert _kinds(_book(A, B), _book(B, A)) == [("moved", "p#2 → p#1")]
    changed = _book(("a2", ["ta", "tz"], []), ("b", ["tb"], ["skill:w"]), C)
    assert [
        (c.kind, c.step, c.detail) for c in steps.step_changes(_book(A, B, C), changed)
    ] == [
        ("condition", "p#1", "a → a2"),
        ("traits", "p#1", "+tz"),
        ("calls", "p#2", "-skill:x +skill:w"),
    ]
    assert steps.step_changes(_book(A, B), _book(A, B)) == []


def test_step_changes_with_repeated_signatures() -> None:
    """Steps that do the same thing pair by condition before position; a
    split pairs one part and adds the other (pairing is one to one)."""
    fail, ok = ("on failure", ["log"], []), ("on success", ["log"], [])
    start = ("on start", ["log"], [])
    assert _kinds(_book(fail, ok), _book(start, fail, ok)) == [("added", "p#1")]
    assert _kinds(_book(fail, ok), _book(ok, fail)) == [("moved", "p#2 → p#1")]
    both = ("a", ["ta", "tb"], [])
    split = _book(("a", ["ta"], []), ("a", ["tb"], []))
    assert _kinds(_book(both), split) == [("added", "p#2"), ("traits", "p#1")]


def test_playbook_target_hash_covers_its_references(tmp_path: Path) -> None:
    """A playbook's `doc:` target hash covers its reference folder (F3); with
    none, it is the file's own `doc:` hash."""
    cfg = _playbook_cfg(tmp_path)
    ship = ".claude/skills/mvp-mode/playbooks/ship.md"
    raw = (cfg.repo_root / ship).read_bytes()  # type: ignore[attr-defined]
    assert steps.playbook_tree_hash(cfg, ship) == _doc_tree_hash(ship, raw)  # type: ignore[arg-type]
    before = steps.playbook_tree_hash(cfg, FIX_PATH)  # type: ignore[arg-type]
    (cfg.playbooks_dir / "fix" / "notes.md").write_text("Edited.\n")  # type: ignore[attr-defined]
    assert steps.playbook_tree_hash(cfg, FIX_PATH) != before  # type: ignore[arg-type]


def test_steps_diff_between_revisions(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    cfg = _playbook_cfg(tmp_path)
    root = str(cfg.repo_root)  # type: ignore[attr-defined]

    def git(*args: str) -> None:
        subprocess.run(
            ["git", "-C", root, "-c", "user.name=t", "-c", "user.email=t@t", *args],
            check=True,
            capture_output=True,
        )

    git("init", "-q")
    git("add", "-A")
    git("commit", "-qm", "base")
    _write_playbook(cfg, "fix", FIX.replace("when: always", "when: first"))
    args = _ns(playbook="fix", base="HEAD", head=None)
    assert cli.cmd_steps(cfg, args) == 0
    out = capsys.readouterr().out
    assert "fix (HEAD → working tree): 1 step change(s)" in out
    assert "condition  fix#1: always → first" in out
    with pytest.raises(SystemExit, match="'nope' is not a commit"):
        cli.cmd_steps(cfg, _ns(playbook="fix", base="nope", head=None))
