"""Playbooks and steps in the registry (unit-kinds T1, T3, St1-St4): parsing
and validation, playbooks as trait holders, the STEPS.md index and per-step
changes between revisions."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest
import yaml

from curation.registry import cli, reports, status, steps
from curation.registry.loaders import load_ledger
from curation.registry.models import Event
from curation.registry.record import _target_hash
from curation.registry.traits import _doc_tree_hash
from curation.registry.views import records as record_views
from tests.curation.test_registry import (
    SUBJECT,
    _checkpoint,
    _defs,
    _fails_with,
    _ns,
    _ours_event,
    _rec_ns,
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
SHIP_PATH = ".claude/skills/mvp-mode/playbooks/ship.md"


def _write_playbook(cfg: object, name: str, text: str) -> Path:
    path = cfg.playbooks_dir / f"{name}.md"  # type: ignore[attr-defined]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _baselines(cfg: object) -> list[dict]:
    """Today's `add` event for each fixture playbook (README §4b)."""
    return [
        {
            "type": "event",
            "id": f"2026-10-14-r:{n}",
            "date": "2026-10-14",
            "kind": "add",
            "subject": f"doc:{rel}",
            "why": "baseline",
            "skill": f"doc:{rel}",
            "target_tree_hash": steps.playbook_tree_hash(cfg, rel),  # type: ignore[arg-type]
        }
        for n, rel in enumerate((FIX_PATH, SHIP_PATH), start=100)
    ]


def _record(cfg: object, kind: str, target: str, **extra: object) -> int:
    """`record` on a playbook subject, through the CLI command."""
    fields = {"kind": kind, "subject": target, "skill": target, "why": "because"}
    return cli.cmd_record(cfg, _rec_ns(json=json.dumps(fields | extra)))


def _last_event(cfg: object) -> dict:
    path = cfg.ledger_dir / "2026-10-14-r.jsonl"  # type: ignore[attr-defined]
    return json.loads(path.read_text(encoding="utf-8").splitlines()[-1])  # type: ignore[no-any-return]


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
    _write_round(
        cfg,
        "2026-10-14-r",
        _checkpoint("2026-10-14-r:1", "adopt", "tdd"),
        _trait("2026-10-14-r:2", "adopt", "seams", skill="tdd"),
        *_baselines(cfg),
        trait_level=True,
    )
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
    assert _record(cfg, "update", f"doc:{FIX_PATH}") == 0
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
    adopted = (
        _checkpoint("2026-10-14-r:1", "adopt", target),
        _trait("2026-10-14-r:2", "adopt", "seams", skill=target),
    )
    _write_round(cfg, "2026-10-14-r", *adopted, *_baselines(cfg), trait_level=True)
    _fails_with(cfg, capsys, f"trait 'seams' is not listed by {target!r}")
    _write_playbook(cfg, "fix", FIX.replace("traits: [gate]", "traits: [gate, seams]"))
    _write_round(cfg, "2026-10-14-r", *adopted, *_baselines(cfg), trait_level=True)
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


@pytest.mark.parametrize(
    "edited", [FIX_PATH, ".claude/skills/mvp-mode/playbooks/fix/notes.md"]
)
def test_playbook_edit_needs_an_update(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], edited: str
) -> None:
    """An edit to a playbook or its reference fails `check`, naming the event
    and the remedy, until `record update` stores the new hash; recording again
    is refused, and a restatement of that update is not."""
    target = f"doc:{FIX_PATH}"
    cfg = _playbook_cfg(tmp_path)
    assert cli.cmd_check(cfg, _ns()) == 0
    with (cfg.repo_root / edited).open("a") as handle:  # type: ignore[attr-defined]
        handle.write("Edited.\n")
    _fails_with(
        cfg,
        capsys,
        f"{FIX_PATH}: changed since 2026-10-14-r:100; `record` an `update`",
    )
    with pytest.raises(SystemExit, match="`target_tree_hash` is computed"):
        _record(cfg, "update", target, target_tree_hash="wrong")
    assert _record(cfg, "update", target) == 0
    update = _last_event(cfg)
    assert update["target_tree_hash"] == steps.playbook_tree_hash(cfg, FIX_PATH)  # type: ignore[arg-type]
    assert "source" not in update
    assert cli.cmd_check(cfg, _ns()) == 0
    with pytest.raises(SystemExit, match="unchanged since 2026-10-14-r:102"):
        _record(cfg, "update", target)
    assert _record(cfg, "update", target, supersedes=[update["id"]]) == 0
    assert cli.cmd_check(cfg, _ns()) == 0


def test_a_correction_of_a_reverted_edit_records(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """An edit is recorded, then undone: the update it superseded held the wrong
    hash, so correcting it records although the file matches the baseline."""
    target = f"doc:{FIX_PATH}"
    cfg = _playbook_cfg(tmp_path)
    _write_playbook(cfg, "fix", FIX + "Edited.\n")
    assert _record(cfg, "update", target) == 0
    wrong = _last_event(cfg)["id"]
    _write_playbook(cfg, "fix", FIX)
    _fails_with(cfg, capsys, f"{FIX_PATH}: changed since {wrong}")
    assert _record(cfg, "update", target, supersedes=[wrong]) == 0
    assert cli.cmd_check(cfg, _ns()) == 0


def test_a_correction_of_a_wrong_hash_records(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A hand-appended event's wrong hash is corrected by superseding it, the
    file unchanged; `record` still computes the hash and `check` verifies it."""
    target = f"doc:{FIX_PATH}"
    cfg = _playbook_cfg(tmp_path)
    wrong = "2026-10-14-r:102"
    event = _baselines(cfg)[0] | {
        "id": wrong,
        "kind": "update",
        "target_tree_hash": "x",
    }
    path = cfg.ledger_dir / "2026-10-14-r.jsonl"  # type: ignore[attr-defined]
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event) + "\n")
    _fails_with(cfg, capsys, f"{FIX_PATH}: changed since {wrong}")
    assert _record(cfg, "update", target, supersedes=[wrong]) == 0
    now = steps.playbook_tree_hash(cfg, FIX_PATH)  # type: ignore[arg-type]
    assert _last_event(cfg)["target_tree_hash"] == now
    assert cli.cmd_check(cfg, _ns()) == 0


@pytest.mark.parametrize(
    "rel",
    [
        "AGENTS.md",
        ".claude/skills/mvp-mode/playbooks/fix/notes.md",
        ".claude/skills/mvp-mode/playbooks/gone.md",
        ".claude/skills/mvp-mode/playbooks//fix.md",
    ],
)
def test_record_refuses_a_subject_that_is_no_playbook(tmp_path: Path, rel: str) -> None:
    cfg = _playbook_cfg(tmp_path)
    (cfg.repo_root / "AGENTS.md").write_text("x\n")  # type: ignore[attr-defined]
    with pytest.raises(SystemExit, match="is not a playbook file"):
        _record(cfg, "update", f"doc:{rel}")


def test_check_ties_playbook_files_to_events(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A playbook with no event, an event with no hash, an event naming no
    playbook, and a removed playbook all fail."""
    cfg = _playbook_cfg(tmp_path)
    _write_playbook(cfg, "new", SHIP.replace("ship#1", "new#1"))
    assert cli.cmd_build(cfg, _ns()) == 0
    new = ".claude/skills/mvp-mode/playbooks/new.md"
    _fails_with(cfg, capsys, f"{new}: no ledger event; `record` an `add`")
    (cfg.playbooks_dir / "new.md").unlink()  # type: ignore[attr-defined]
    assert cli.cmd_build(cfg, _ns()) == 0

    bare, ship = _baselines(cfg)
    del bare["target_tree_hash"]
    agents = bare | {
        "id": "2026-10-14-r:102",
        "subject": "doc:AGENTS.md",
        "skill": "doc:AGENTS.md",
    }
    _write_round(cfg, "2026-10-14-r", bare, ship, agents, trait_level=True)
    assert cli.cmd_check(cfg, _ns()) == 1
    err = capsys.readouterr().err
    assert f"2026-10-14-r:100: doc:{FIX_PATH} has no `target_tree_hash`" in err
    assert "2026-10-14-r:102: doc:AGENTS.md names no playbook file" in err

    (cfg.playbooks_dir / "ship.md").unlink()  # type: ignore[attr-defined]
    _fails_with(cfg, capsys, f"{SHIP_PATH}: no such playbook, but 2026-10-14-r:101")


def _adopted_into_fix(cfg: object) -> None:
    """`fix` lists `seams`, adopted into it, at today's hashes."""
    target = f"doc:{FIX_PATH}"
    _write_playbook(cfg, "fix", FIX.replace("traits: [gate]", "traits: [gate, seams]"))
    _write_round(
        cfg,
        "2026-10-14-r",
        _checkpoint("2026-10-14-r:1", "adopt", target),
        _trait("2026-10-14-r:2", "adopt", "seams", skill=target),
        *_baselines(cfg),
        trait_level=True,
    )
    assert cli.cmd_build(cfg, _ns()) == 0
    assert cli.cmd_check(cfg, _ns()) == 0


def test_withdraws_on_a_playbook_update(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A trait adopted into a playbook may leave its frontmatter through the
    playbook's `update`; a later delivered adopt makes it live again."""
    target = f"doc:{FIX_PATH}"
    cfg = _playbook_cfg(tmp_path)
    _adopted_into_fix(cfg)
    _write_playbook(cfg, "fix", FIX)
    assert cli.cmd_build(cfg, _ns()) == 0
    _fails_with(cfg, capsys, f"trait 'seams' is not listed by {target!r}")

    assert _record(cfg, "update", target, withdraws=[f"{SUBJECT}#seams"]) == 0
    assert cli.cmd_check(cfg, _ns()) == 0

    readopt = _trait("x", "adopt", "seams", skill=target)
    del readopt["id"]
    assert cli.cmd_record(cfg, _rec_ns(json=json.dumps(readopt))) == 0
    _fails_with(cfg, capsys, f"trait 'seams' is not listed by {target!r}")


def test_withdraws_is_per_destination(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """`ship` never adopted the trait `fix` holds, so it cannot withdraw it."""
    cfg = _playbook_cfg(tmp_path)
    _adopted_into_fix(cfg)
    _write_playbook(cfg, "ship", SHIP + "Edited.\n")
    trait = f"{SUBJECT}#seams"
    assert _record(cfg, "update", f"doc:{SHIP_PATH}", withdraws=[trait]) == 0
    _fails_with(cfg, capsys, f"withdraws {trait!r} but no adopt event targets")
    mistaken = _last_event(cfg)["id"]
    assert _record(cfg, "update", f"doc:{SHIP_PATH}", supersedes=[mistaken]) == 0
    assert cli.cmd_check(cfg, _ns()) == 0


@pytest.mark.parametrize("kind", ["merge", "rename", "split", "retire"])
def test_playbook_subject_has_only_add_and_update(tmp_path: Path, kind: str) -> None:
    cfg = _playbook_cfg(tmp_path)
    target = f"doc:{FIX_PATH}"
    with pytest.raises(ValueError, match="on a playbook subject"):
        _record(cfg, kind, target)


def test_a_reference_ruling_cannot_forget_a_playbook(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A `doc:` subject is a playbook's whatever the kind or source, so a made-up
    `reject` cannot supersede the baseline of a deleted file."""
    cfg = _playbook_cfg(tmp_path)
    (cfg.playbooks_dir / "fix.md").unlink()  # type: ignore[attr-defined]
    ruling = {
        "kind": "reject",
        "subject": f"doc:{FIX_PATH}",
        "why": "gone",
        "source": {"repo": "doc", "logical_id": FIX_PATH, "content_hash": "x"},
        "supersedes": ["2026-10-14-r:100"],
    }
    with pytest.raises(ValueError, match="reject on a playbook subject"):
        cli.cmd_record(cfg, _rec_ns(json=json.dumps(ruling)))
    _fails_with(cfg, capsys, f"{FIX_PATH}: no such playbook")


def test_plain_when_cut_by_a_yaml_comment_is_refused() -> None:
    head = "---\ntrigger: A defect to fix.\nsteps:\n  - id: fix#1\n"
    action = "    actions: [{trait: act}]   # new\n---\n"
    with pytest.raises(ValueError, match="quote it or write full step IDs"):
        steps.parse_playbook(
            "fix", "fix.md", f"{head}    when: from fix#3, #5\n{action}"
        )
    quoted = f'{head}    when: "from fix#3, #5"\n{action}'
    assert (
        steps.parse_playbook("fix", "fix.md", quoted).steps[0].when == "from fix#3, #5"
    )
    plain = f"{head}    when: from fix#3\n{action}"
    assert steps.parse_playbook("fix", "fix.md", plain).steps[0].when == "from fix#3"


@pytest.mark.parametrize("gap", [" ", "  ", "    ", "\t", " \t "])
@pytest.mark.parametrize("key", ["when", '"when"', "'when'"])
def test_when_guard_reads_past_any_spacing_and_key_spelling(gap: str, key: str) -> None:
    head = "---\ntrigger: A defect to fix.\nsteps:\n  - id: fix#1\n"
    action = "    actions: [{trait: act}]   # new\n---\n"
    cut = f"{head}    {key}:{gap}from fix#3, #5\n{action}"
    with pytest.raises(ValueError, match="quote it or write full step IDs"):
        steps.parse_playbook("fix", "fix.md", cut)
    if "\t" not in gap:
        quoted = f'{head}    {key}:{gap}"from fix#3, #5"\n{action}'
        parsed = steps.parse_playbook("fix", "fix.md", quoted)
        assert parsed.steps[0].when == "from fix#3, #5"


# --- a skill merged into a playbook (plan 40 §5a 3, U0) -----------------------

MERGED = f"doc:{FIX_PATH}"


def _merged_into_fix(base: Path, *extra: dict[str, object]) -> object:
    """`tdd-old` adopted `seams`, was renamed `tdd` and then merged into the
    `fix` playbook, which lists `seams`: the adoption follows the merge."""
    cfg = _playbook_cfg(base, FIX.replace("traits: [gate]", "traits: [gate, seams]"))
    _write_round(
        cfg,
        "2026-10-14-r",
        _checkpoint("2026-10-14-r:1", "adopt", "tdd-old"),
        _trait("2026-10-14-r:2", "adopt", "seams", skill="tdd-old"),
        {**_ours_event("2026-10-14-r:3", "rename", "tdd-old"), "skill": "tdd"},
        *_baselines(cfg),
        {**_ours_event("2026-10-14-r:102", "merge", "tdd"), "skill": MERGED},
        *extra,
        trait_level=True,
    )
    ours = cfg.traits_dir / "ours.yaml"  # type: ignore[attr-defined]
    entry = yaml.safe_load(ours.read_text(encoding="utf-8"))
    del entry["ours:tdd"]
    ours.write_text(yaml.safe_dump(entry), encoding="utf-8")
    if extra:  # each extra event rules on `gate`, so the analysis lists it
        analysis = cfg.traits_dir / "refrepo.yaml"  # type: ignore[attr-defined]
        analysis.write_text(analysis.read_text().replace("[seams]", "[seams, gate]"))
    assert cli.cmd_build(cfg, _ns()) == 0  # type: ignore[arg-type]
    return cfg


def _events(cfg: object) -> list[Event]:
    return load_ledger(cfg)[1]  # type: ignore[arg-type]


def test_merged_skill_adoption_follows_into_the_playbook(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Coverage (C) reads the playbook's frontmatter for an adoption whose
    skill merged into it, and `record` hashes that playbook for the old name."""
    cfg = _merged_into_fix(tmp_path)
    want = steps.playbook_tree_hash(cfg, FIX_PATH)  # type: ignore[arg-type]
    assert _target_hash(cfg, "tdd-old", _events(cfg)) == want  # type: ignore[arg-type]
    assert cli.cmd_check(cfg, _ns()) == 0, capsys.readouterr().err  # type: ignore[arg-type]

    _write_playbook(cfg, "fix", FIX)
    assert _record(cfg, "update", MERGED) == 0
    _fails_with(cfg, capsys, f"trait 'seams' is not listed by {MERGED!r}")


def test_pending_adopt_into_a_merged_skill_sees_the_playbook(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A pending adopt into the old name is fulfilled once the playbook lists
    the trait, as it would be for a skill survivor."""
    pending = _trait("2026-10-14-r:103", "adopt", "gate", skill="tdd", pending="cr-1")
    _fails_with(
        _merged_into_fix(tmp_path, pending),
        capsys,
        f"pending adopt of '{SUBJECT}#gate' but {MERGED!r} already lists 'gate'",
    )


def test_merged_adoption_status_labels(tmp_path: Path) -> None:
    """Regression (critic-40b F4, unchanged code): `status` labels the merged
    adoption delivered, a withdrawn one withdrawn, an unlisted one no longer
    provided."""
    seams = f"{SUBJECT}#seams"

    def label(cfg: object) -> str:
        return str(status.provisions(reports.load_context(cfg))[seams])  # type: ignore[arg-type]

    cfg = _merged_into_fix(tmp_path)
    assert label(cfg) == "delivered"
    _write_playbook(cfg, "fix", FIX)
    assert label(cfg) == "no longer provided"
    assert _record(cfg, "update", MERGED, withdraws=[seams]) == 0
    assert label(cfg) == "withdrawn"


def test_merged_skill_record_keeps_its_lineage_and_history(tmp_path: Path) -> None:
    """The merged skill's record keeps what it had under every earlier name,
    as a rename's survivor does, and the traits declined there: a playbook has
    no record to carry them."""
    defer = _trait(
        "2026-10-14-r:103", "defer", "gate", skill="tdd-old", revisit_when="later"
    )
    cfg = _merged_into_fix(tmp_path, defer)
    text: str = (cfg.skill_records_dir / "engineering" / "tdd.md").read_text()  # type: ignore[attr-defined]

    def block(open_tag: str, close_tag: str) -> str:
        return text.split(open_tag)[1].split(close_tag)[0]

    lineage = block(record_views.LINEAGE_OPEN, record_views.LINEAGE_CLOSE)
    history = block(record_views.HISTORY_OPEN, record_views.HISTORY_CLOSE)
    assert f"**{SUBJECT}#seams**" in lineage
    for n in (1, 2, 3, 102, 103):
        assert f"(2026-10-14-r:{n})" in history
    declined = block(record_views.DECLINED_OPEN, record_views.DECLINED_CLOSE)
    assert f"`{SUBJECT}#gate` (defer): because" in declined
