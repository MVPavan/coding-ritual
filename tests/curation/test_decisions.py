"""Decision rules and lifecycle (stages-design Stage 3; Acceptance 2-4, 6-10,
21): report citation, record-time freshness, completion, cancellation,
reconsideration, rewording, whole-skill mode, promotion, carry-over,
membership and analysis immutability."""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
import yaml

from curation.registry import cli, ledger, reports
from curation.registry.loaders import load_traits, report_key
from curation.registry.models import Event, MappingLine
from tests.curation.test_registry import (
    _PLACEMENT,
    LOGICAL,
    SUBJECT,
    _ns,
    _rec_ns,
    _tree_hash_of,
    _write_round,
    _write_skill,
)
from tests.curation.test_reports import UPSTREAM, _cfg, _draft, _edit, _judge

ROUND = "2026-10-20-d"
LATER = "2026-10-21-p"
SHA = "abc1234"
NEW = "def5678"
ADAPTATION = {"merged_from": [], "modifications": ["m"], "deliberately_dropped": []}


def _source(sha: str = SHA) -> dict[str, str]:
    return {
        "repo": "refrepo",
        "logical_id": LOGICAL,
        "content_hash": "h",
        "tree_hash": f"T-{sha}",
        "sha": sha,
    }


def _ev(
    eid: str, kind: str, tid: str | None = None, sha: str = SHA, **extra: Any
) -> dict[str, Any]:
    ev: dict[str, Any] = {
        "type": "event",
        "id": eid,
        "date": "2026-10-20",
        "kind": kind,
        "subject": SUBJECT + (f"#{tid}" if tid else ""),
        "why": "because",
        "evidence": ["x:1"],
        "source": _source(sha),
    }
    ev.update(extra)
    return ev


def _first_round(key: str) -> list[dict[str, Any]]:
    """The decision of every trait at SHA: three delivered adopts (one into
    AGENTS.md), two defers and a pending adopt of `novel`."""
    rep = {"report": key}
    return [
        _ev(f"{ROUND}:1", "adopt-merged", skill="tdd", adaptation=ADAPTATION),
        _ev(f"{ROUND}:2", "adopt", "red-green", skill="tdd", **rep),
        _ev(f"{ROUND}:3", "adopt", "seams", skill="tdd", **rep),
        _ev(f"{ROUND}:4", "defer", "mocks", revisit_when="when needed", **rep),
        _ev(f"{ROUND}:5", "adopt", "agents-rule", skill="doc:AGENTS.md", **rep),
        _ev(f"{ROUND}:6", "defer", "style-rule", revisit_when="when needed", **rep),
        _ev(f"{ROUND}:7", "adopt", "novel", skill="tdd", pending="cr-1", **rep),
    ]


def _judge_pending(data: dict[str, Any]) -> None:
    _judge(data)
    data["skills"][LOGICAL]["traits"]["novel"].update(
        recommendation="adopt",
        delivery="pending",
        guide={"verdict": "ok", "rules": ["U-01"]},
    )


def _seal(
    cfg: Any, path: Path, change: Callable[[dict[str, Any]], None] = _judge_pending
) -> str:
    _edit(path, change)
    assert reports.seal(cfg, path) == []
    return report_key(cfg, path)


def _point(
    cfg: Any,
    accepted: str | None,
    proposed: str | None,
    shas: tuple[str, ...] = (SHA,),
    listed: dict[str, list[str]] | None = None,
) -> None:
    """Rewrite the upstream entry; the NEW analysis changes `seams`."""
    out = f"refrepo:{LOGICAL}:\n"
    out += f"  accepted: {json.dumps(accepted)}\n  proposed: {json.dumps(proposed)}\n"
    out += "  analyses:\n"
    for sha in shas:
        traits = (listed or {}).get(sha, UPSTREAM)
        out += (
            f'    "{sha}":\n      tree_hash: "T-{sha}"\n      placement: {_PLACEMENT}\n'
            f"      traits: [{', '.join(traits)}]\n"
        )
        if sha == NEW:
            out += '      changed: {seams: "Reworded upstream."}\n'
    (cfg.traits_dir / "refrepo.yaml").write_text(out, encoding="utf-8")


def _decided(
    tmp: Path, trait_level: bool = True, events: list[dict[str, Any]] | None = None
) -> tuple[Any, str]:
    """A sealed report, the round deciding every trait at SHA, promoted."""
    cfg = _cfg(tmp)
    ledger.seal(cfg, "2026-10-14-r")
    key = _seal(cfg, _draft(cfg))
    _write_round(
        cfg,
        ROUND,
        *(events if events is not None else _first_round(key)),
        trait_level=trait_level,
        date="2026-10-20",
    )
    _point(cfg, SHA, None)
    assert cli.cmd_build(cfg, _ns()) == 0
    return cfg, key


def _ok(cfg: Any, capsys: pytest.CaptureFixture[str]) -> None:
    assert cli.cmd_build(cfg, _ns()) == 0
    rc = cli.cmd_check(cfg, _ns())
    assert rc == 0, capsys.readouterr().err


def _fails(cfg: Any, capsys: pytest.CaptureFixture[str], needle: str) -> None:
    assert cli.cmd_build(cfg, _ns()) == 0
    assert cli.cmd_check(cfg, _ns()) == 1
    err = capsys.readouterr().err
    assert needle in err, err


def _record(cfg: Any, data: dict[str, Any], **kw: Any) -> int:
    return cli.cmd_record(cfg, _rec_ns(json=json.dumps(data), **kw))


def _last(cfg: Any, round_id: str = ROUND) -> dict[str, Any]:
    lines = (cfg.ledger_dir / f"{round_id}.jsonl").read_text().splitlines()
    return json.loads(lines[-1])  # type: ignore[no-any-return]


def _lists(cfg: Any, old: str, new: str) -> None:
    path = cfg.traits_dir / "ours.yaml"
    text = path.read_text(encoding="utf-8")
    assert old in text
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def _new(data: dict[str, Any]) -> dict[str, Any]:
    """A record request: the event without `type` and `id`."""
    return {k: v for k, v in data.items() if k not in {"type", "id"}}


# --- slice-4 follow-ups ---------------------------------------------------------


def test_report_accepted_and_split(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="at least two"):
        MappingLine(line=1, to=["seams"], mark="split")
    cfg = _cfg(tmp_path)
    data = yaml.safe_load(_draft(cfg).read_text())
    assert data["from_sha"] is None
    assert data["skills"][LOGICAL]["accepted"] is None


# --- 2.6 / Acceptance 6: report citation -------------------------------------------


@pytest.mark.parametrize("flagged", [True, False])
def test_report_citation(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], flagged: bool
) -> None:
    cfg, key = _decided(tmp_path, trait_level=flagged)
    _ok(cfg, capsys)
    draft = _draft(cfg, report_path=Path("registry/reviews/draft.yaml"))
    draft_key = report_key(cfg, draft)

    def with_seams(change: Callable[[dict[str, Any]], None]) -> None:
        events = _first_round(key)
        change(events[2])
        _write_round(cfg, ROUND, *events, trait_level=flagged, date="2026-10-20")

    with_seams(lambda e: e.pop("report"))
    _fails(cfg, capsys, f"{ROUND}:3: a trait event outside pre_trait_rounds cites no")
    with_seams(lambda e: e.update(report=draft_key))
    _fails(cfg, capsys, f"{ROUND}:3: report {draft_key} is not sealed")
    _point(cfg, SHA, NEW, shas=(SHA, NEW))
    with_seams(lambda e: e.update(source=_source(NEW)))
    _fails(cfg, capsys, f"{ROUND}:3: report {key} is at {SHA}, not the event's {NEW}")
    _point(cfg, SHA, None)
    with_seams(lambda e: e.update(skill="debug"))
    _fails(cfg, capsys, f"{ROUND}:3: target 'debug' is not the row's provider")
    with_seams(lambda e: e.update(skill="debug", retarget="debug owns seams now"))
    _ok(cfg, capsys)


# --- Acceptance 3, 7: record-time freshness ------------------------------------------


def test_record_freshness(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    cfg = _cfg(tmp_path)
    ledger.seal(cfg, "2026-10-14-r")
    key = _seal(cfg, _draft(cfg), _judge)  # novel: defer
    first = _first_round(key)
    first[6] = _ev(f"{ROUND}:7", "defer", "novel", report=key)
    _write_round(cfg, ROUND, first[0], trait_level=True, date="2026-10-20")

    # 3: seams is now listed only by a non-compared skill; the row says present.
    _lists(cfg, "traits: [red-green, seams]", "traits: [red-green]")
    with pytest.raises(SystemExit, match="stale row"):
        _record(cfg, _new(first[2]))
    _lists(cfg, "traits: [red-green]", "traits: [red-green, seams]")
    for event in first[1:]:
        assert _record(cfg, _new(event)) == 0
    _point(cfg, SHA, None)
    _ok(cfg, capsys)
    # 7: a later absent → present delivery never invalidates history.
    _lists(cfg, "traits: [red-green, seams]", "traits: [red-green, seams, novel]")
    _ok(cfg, capsys)


def test_defer_needs_revisit_when(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    # review 2 #10: `revisit_when` only on a defer, required outside
    # pre_trait_rounds; `record` copies the row's.
    with pytest.raises(ValueError, match="only for a defer"):
        Event.model_validate(_ev("r:1", "reject", "mocks", revisit_when="later"))
    with pytest.raises(ValueError, match="empty"):
        Event.model_validate(_ev("r:1", "defer", "mocks", revisit_when=" "))
    cfg, key = _decided(tmp_path)
    events = _first_round(key)
    events[3].pop("revisit_when")
    _write_round(cfg, ROUND, *events, trait_level=True, date="2026-10-20")
    _fails(cfg, capsys, f"{ROUND}:4: a defer needs `revisit_when`")
    _write_round(
        cfg, ROUND, *events[:3], *events[4:], trait_level=True, date="2026-10-20"
    )
    assert _record(cfg, _new(events[3])) == 0
    assert _last(cfg)["revisit_when"] == "when needed"  # the row's
    _ok(cfg, capsys)


def test_new_adopt_needs_guide_ok(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    # review 2 #9: a delivered adopt needs an `ok` row; a pending one a guide
    # and, unless `ok`, `rewording`; a row without `guide` supports neither.
    def conflict(data: dict[str, Any]) -> None:
        _judge_pending(data)
        data["skills"][LOGICAL]["traits"]["mocks"].update(
            recommendation="reject",
            revisit_when=None,
            guide={"verdict": "conflict", "rules": ["U-01"]},
        )

    cfg = _cfg(tmp_path)
    ledger.seal(cfg, "2026-10-14-r")
    key = _seal(cfg, _draft(cfg), conflict)
    first = _first_round(key)
    _write_round(cfg, ROUND, *first[:3], *first[4:], trait_level=True)
    adopt = _new(_ev("x", "adopt", "mocks", skill="tdd", report=key))
    with pytest.raises(SystemExit, match="guide verdict `ok`"):
        _record(cfg, adopt)
    with pytest.raises(SystemExit, match="`conflict` row needs `rewording`"):
        _record(cfg, adopt | {"pending": "cr-4"})
    style = _new(_ev("x", "adopt", "style-rule", skill="tdd", report=key))
    with pytest.raises(SystemExit, match="has no `guide`"):
        _record(cfg, style | {"pending": "cr-5"})
    bad = _ev(f"{ROUND}:4", "adopt", "mocks", skill="tdd", report=key)
    _write_round(cfg, ROUND, *first[:3], bad, *first[4:], trait_level=True)
    _fails(cfg, capsys, f"{ROUND}:4: a new delivered adopt needs the row's guide")


def test_owner_override_supports_a_conflict_adopt(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    # critic-1b-build finding 4: an adopt rests on a `conflict` row only with
    # an owner override citing the ruling and its date.
    override = {"ruling": "owner ruling R15", "date": "2026-11-01"}

    def overridden(data: dict[str, Any]) -> None:
        _judge_pending(data)
        data["skills"][LOGICAL]["traits"]["seams"]["guide"] = {
            "verdict": "conflict",
            "rules": ["U-01"],
            "override": override,
        }

    cfg = _cfg(tmp_path)
    ledger.seal(cfg, "2026-10-14-r")
    key = _seal(cfg, _draft(cfg), overridden)
    first = _first_round(key)
    _write_round(cfg, ROUND, *first[:2], *first[3:], trait_level=True)
    assert _record(cfg, _new(_ev("x", "adopt", "seams", skill="tdd", report=key))) == 0
    _point(cfg, SHA, None)
    _ok(cfg, capsys)


# --- Acceptance 8: completion, cancellation, reconsideration ----------------------------


def test_completion(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    cfg, key = _decided(tmp_path)
    _lists(cfg, "traits: [red-green, seams]", "traits: [red-green, seams, novel]")
    done = {
        "kind": "adopt",
        "subject": f"{SUBJECT}#novel",
        "why": "landed",
        "evidence": ["x:1"],
        "skill": "tdd",
        "supersedes": [f"{ROUND}:7"],
    }
    with pytest.raises(SystemExit, match="inherit `report`"):
        _record(cfg, done | {"report": "registry/reviews/other.yaml"})
    # The fact changed (absent → present) and there is no new row: record passes.
    assert _record(cfg, done) == 0
    assert _last(cfg)["report"] == key and _last(cfg)["source"] == _source()
    _ok(cfg, capsys)

    events = _first_round(key)
    bad = _ev(f"{ROUND}:8", "adopt", "novel", skill="tdd", supersedes=[f"{ROUND}:7"])
    _write_round(cfg, ROUND, *events, bad | {"report": "x.yaml"}, trait_level=True)
    _fails(cfg, capsys, f"{ROUND}:8: a completion must inherit `report`")
    moved = bad | {"report": key, "source": _source() | {"content_hash": "h2"}}
    _write_round(cfg, ROUND, *events, moved, trait_level=True)
    _fails(cfg, capsys, f"{ROUND}:8: completing adopt of")


def test_completion_in_round_sorting_before_its_pending_passes_check(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Filename order is not chronology within a date, so a completion from a
    `reword` row is judged against the pending event it supersedes."""

    def reword(data: dict) -> None:
        _judge(data)
        data["supersedes"] = [key]
        data["skills"][LOGICAL]["traits"]["mocks"].update(
            recommendation="adopt",
            delivery="pending",
            rewording="Mock only at the boundary.",
            guide={"verdict": "reword", "rules": ["U-01"]},
        )

    cfg, key = _decided(tmp_path)
    ledger.seal(cfg, ROUND)
    path = _draft(
        cfg, report_path=Path("registry/reviews/re.yaml"), reconsider=["mocks"]
    )
    again = _seal(cfg, path, reword)
    pending_round, completing_round = "2026-10-21-z", "2026-10-21-a"
    pending = _ev(
        f"{pending_round}:1",
        "adopt",
        "mocks",
        skill="tdd",
        report=again,
        supersedes=[f"{ROUND}:4"],
        pending="cr-2",
        rewording="Mock only at the boundary.",
        target_tree_hash=_tree_hash_of(cfg, "tdd"),
    )
    _write_round(cfg, pending_round, pending, trait_level=True, date="2026-10-21")
    ledger.seal(cfg, pending_round)
    done = _ev(
        f"{completing_round}:1",
        "adopt",
        "mocks",
        skill="tdd",
        report=again,
        supersedes=[pending["id"]],
        guide={"verdict": "ok", "rules": ["U-01"]},
    )
    _write_round(cfg, completing_round, done, trait_level=True, date="2026-10-21")
    _lists(cfg, "traits: [red-green, seams]", "traits: [red-green, seams, mocks]")
    _ok(cfg, capsys)


def _two_pending_and_completion(
    base: Path, order: tuple[int, int], chained: bool
) -> object:
    """Rounds z and a sort a before z. z holds a pending adopt into tdd, then one
    retargeted into debug's variant; a completes the first, superseding both."""

    def reword(data: dict) -> None:
        _judge(data)
        data["supersedes"] = [key]
        data["skills"][LOGICAL]["traits"]["mocks"].update(
            recommendation="adopt",
            delivery="pending",
            rewording="Mock only at the boundary.",
            guide={"verdict": "reword", "rules": ["U-01"]},
        )

    cfg, key = _decided(base)
    ledger.seal(cfg, ROUND)
    path = _draft(
        cfg, report_path=Path("registry/reviews/re.yaml"), reconsider=["mocks"]
    )
    again = _seal(cfg, path, reword)
    pending_round, completing_round = "2026-10-21-z", "2026-10-21-a"
    first = _ev(
        f"{pending_round}:1",
        "adopt",
        "mocks",
        skill="tdd",
        report=again,
        supersedes=[f"{ROUND}:4"],
        pending="cr-2",
        rewording="Mock only at the boundary.",
        target_tree_hash=_tree_hash_of(cfg, "tdd"),
    )
    second = _ev(
        f"{pending_round}:2",
        "adopt",
        "mocks",
        skill="debug",
        report=again,
        supersedes=[first["id"]] if chained else [],
        pending="cr-3",
        rewording="Mock only at the boundary.",
        target_tree_hash=_tree_hash_of(cfg, "debug"),
        into="mocks-strict",
        modification="Use the strict-mock variant.",
        retarget="The later pending ruling chooses the debugging holder.",
    )
    _write_round(cfg, pending_round, first, second, trait_level=True, date="2026-10-21")
    ledger.seal(cfg, pending_round)
    ids = (first["id"], second["id"])
    done = _ev(
        f"{completing_round}:1",
        "adopt",
        "mocks",
        skill="tdd",
        report=again,
        supersedes=[ids[i] for i in order],
        guide={"verdict": "ok", "rules": ["U-01"]},
    )
    _write_round(cfg, completing_round, done, trait_level=True, date="2026-10-21")
    _lists(cfg, "traits: [red-green, seams]", "traits: [red-green, seams, mocks]")
    return cfg


@pytest.mark.parametrize("order", [(0, 1), (1, 0)], ids=["first-last", "last-first"])
def test_two_unrelated_later_predecessors_are_refused_in_either_order(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], order: tuple[int, int]
) -> None:
    cfg = _two_pending_and_completion(tmp_path, order, chained=False)
    _fails(cfg, capsys, "2026-10-21-a:1: supersedes several later events")


@pytest.mark.parametrize("order", [(0, 1), (1, 0)], ids=["first-last", "last-first"])
def test_superseded_predecessor_cannot_be_completed_in_either_order(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], order: tuple[int, int]
) -> None:
    """The later pending ruling replaced the first, so superseding both is refused."""
    cfg = _two_pending_and_completion(tmp_path, order, chained=True)
    _fails(cfg, capsys, "2026-10-21-z:1: superseded twice")


def test_cancellation_and_reconsideration(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    cfg, key = _decided(tmp_path)
    cancel = {
        "kind": "defer",
        "subject": f"{SUBJECT}#novel",
        "why": "not now",
        "evidence": ["x:1"],
        "supersedes": [f"{ROUND}:7"],
    }
    with pytest.raises(SystemExit, match="needs `revisit_when`"):
        _record(cfg, cancel)  # review 2 #10: a cancellation into defer too
    assert _record(cfg, cancel | {"revisit_when": "next release"}) == 0
    assert _last(cfg)["report"] == key and _last(cfg)["source"] == _source()
    _ok(cfg, capsys)
    events = _first_round(key)
    bad = _ev(f"{ROUND}:8", "reject", "novel", supersedes=[f"{ROUND}:7"])
    _write_round(cfg, ROUND, *events, bad | {"report": "x.yaml"}, trait_level=True)
    _fails(cfg, capsys, f"{ROUND}:8: a cancellation must inherit `report`")

    # Reopening the deferred `mocks` without a `reconsider` row fails …
    reopen = _ev(
        f"{ROUND}:8",
        "adopt",
        "mocks",
        skill="tdd",
        pending="cr-2",
        report=key,
        supersedes=[f"{ROUND}:4"],
    )
    _write_round(cfg, ROUND, *events, reopen, trait_level=True)
    _fails(cfg, capsys, f"{ROUND}:8: reconsidering {ROUND}:4 at {SHA} needs a")
    _write_round(cfg, ROUND, *events, trait_level=True, date="2026-10-20")
    with pytest.raises(SystemExit, match="reconsider"):
        _record(cfg, _new(reopen))

    # … and passes once a superseding report has one.
    def reconsider(data: dict[str, Any]) -> None:
        _judge(data)
        data["supersedes"] = [key]
        data["skills"][LOGICAL]["traits"]["mocks"].update(
            recommendation="adopt",
            delivery="pending",
            guide={"verdict": "ok", "rules": ["U-01"]},
        )

    path = _draft(
        cfg, report_path=Path("registry/reviews/re.yaml"), reconsider=["mocks"]
    )
    again = _seal(cfg, path, reconsider)
    assert _record(cfg, _new(reopen) | {"report": again}) == 0
    _ok(cfg, capsys)


def test_lifecycle_needs_explicit_supersession(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    # review 2 #2: without `supersedes` of the effective pending adopt, a
    # completion or cancellation is a new decision, in `record` and `check`.
    cfg, key = _decided(tmp_path)
    _lists(cfg, "traits: [red-green, seams]", "traits: [red-green, seams, novel]")
    novel = {"subject": f"{SUBJECT}#novel", "why": "w", "evidence": ["x:1"]}
    with pytest.raises(SystemExit, match="cites no `report`"):
        _record(cfg, novel | {"kind": "adopt", "skill": "tdd"})
    with pytest.raises(SystemExit, match="cites no `report`"):
        _record(cfg, novel | {"kind": "defer", "revisit_when": "later"})
    # Sol's sequence: an unsuperseding cancellation, then an adopt superseding
    # the old pending event to inherit its basis.
    cancel = _ev(f"{ROUND}:8", "defer", "novel", report=key, revisit_when="later")
    adopt = _ev(
        f"{ROUND}:9",
        "adopt",
        "novel",
        skill="tdd",
        report=key,
        supersedes=[f"{ROUND}:7"],
    )
    _write_round(cfg, ROUND, *_first_round(key), cancel, adopt, trait_level=True)
    _fails(cfg, capsys, f"{ROUND}:8: reconsidering {ROUND}:7 at {SHA} needs a")
    _fails(cfg, capsys, f"{ROUND}:9: reconsidering {ROUND}:8 at {SHA} needs a")


# --- Acceptance 2, 10: promotion and carry-over -------------------------------------------


def test_promotion_and_carry_over(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    cfg, _ = _decided(tmp_path)
    ledger.seal(cfg, ROUND)
    # A proposed analysis changes nothing while the accepted checkpoint stands.
    _point(cfg, SHA, NEW, shas=(SHA, NEW))
    _ok(cfg, capsys)
    later = _draft(cfg)
    assert yaml.safe_load(later.read_text())["skills"][LOGICAL]["accepted"] == SHA
    assert list(yaml.safe_load(later.read_text())["skills"][LOGICAL]["traits"]) == [
        "seams"
    ]
    later_key = _seal(cfg, later, _judge)

    checkpoint = _ev(
        f"{LATER}:1",
        "adopt-merged",
        sha=NEW,
        skill="tdd",
        supersedes=[f"{ROUND}:1"],
    )
    _write_round(cfg, LATER, checkpoint, trait_level=True, date="2026-10-21")
    _point(cfg, NEW, None, shas=(SHA, NEW))
    _fails(
        cfg, capsys, f"trait 'seams' in {SUBJECT!r} has no effective ruling at {NEW}"
    )

    seams = _ev(
        f"{LATER}:2",
        "adopt",
        "seams",
        sha=NEW,
        skill="tdd",
        report=later_key,
        supersedes=[f"{ROUND}:3"],
    )
    _write_round(cfg, LATER, checkpoint, seams, trait_level=True, date="2026-10-21")
    _ok(cfg, capsys)  # every untouched trait carries its SHA ruling
    entry = load_traits(cfg)[0][f"refrepo:{LOGICAL}"]
    assert ledger.is_carried(entry, "red-green", SHA, NEW)  # type: ignore[arg-type]
    assert not ledger.is_carried(entry, "seams", SHA, NEW)  # type: ignore[arg-type]

    # A pending adopt from the earlier sha still completes after promotion.
    _lists(cfg, "traits: [red-green, seams]", "traits: [red-green, seams, novel]")
    done = {
        "kind": "adopt",
        "subject": f"{SUBJECT}#novel",
        "why": "landed",
        "evidence": ["x:1"],
        "skill": "tdd",
        "supersedes": [f"{ROUND}:7"],
    }
    assert _record(cfg, done) == 0
    assert _last(cfg, LATER)["source"]["sha"] == SHA
    _ok(cfg, capsys)


# --- 3.9 and §Entries: membership and immutability ------------------------------------------


def test_membership_and_analysis_immutability(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    cfg, key = _decided(tmp_path)
    events = _first_round(key)
    _write_round(
        cfg,
        ROUND,
        *events[:2],
        _ev(f"{ROUND}:3", "adopt", "seams", sha="fff0000", skill="tdd", report=key),
        *events[3:],
        trait_level=True,
    )
    _fails(cfg, capsys, f"{ROUND}:3: no analysis of {SUBJECT!r} at fff0000")
    listed = {NEW: [t for t in UPSTREAM if t != "seams"]}
    _point(cfg, SHA, NEW, shas=(SHA, NEW), listed=listed)
    _write_round(
        cfg,
        ROUND,
        *events[:2],
        _ev(f"{ROUND}:3", "adopt", "seams", sha=NEW, skill="tdd", report=key),
        *events[3:],
        trait_level=True,
    )
    _fails(cfg, capsys, f"{ROUND}:3: trait 'seams' is not listed in the analysis")

    _point(cfg, SHA, None)
    _write_round(cfg, ROUND, *events, trait_level=True, date="2026-10-20")
    ledger.seal(cfg, ROUND)
    manifest = json.loads(cfg.manifest_path.read_text())
    assert list(manifest["analyses"]) == [f"refrepo:{LOGICAL}@{SHA}"]
    assert set(manifest["reports"]) == {key} and ROUND + ".jsonl" in manifest["rounds"]
    _ok(cfg, capsys)
    path = cfg.traits_dir / "refrepo.yaml"
    path.write_text(path.read_text() + '      notes: {seams: "edited"}\n')
    _fails(cfg, capsys, f"analysis refrepo:{LOGICAL}@{SHA} has CHANGED")
    _point(cfg, NEW, None, shas=(NEW,))
    _fails(cfg, capsys, f"analysis refrepo:{LOGICAL}@{SHA} has VANISHED")


def test_seal_keeps_analysis_digests(tmp_path: Path) -> None:
    # review 2 #1: a later round citing an edited analysis is never sealed.
    cfg, key = _decided(tmp_path)
    ledger.seal(cfg, ROUND)
    before = cfg.manifest_path.read_text()
    path = cfg.traits_dir / "refrepo.yaml"
    path.write_text(path.read_text() + '      notes: {seams: "edited"}\n')
    cite = _ev(f"{LATER}:1", "reject", "mocks", report=key, supersedes=[f"{ROUND}:4"])
    _write_round(cfg, LATER, cite, trait_level=True, date="2026-10-21")
    with pytest.raises(SystemExit, match=f"refrepo:{LOGICAL}@{SHA}.*CHANGED"):
        ledger.seal(cfg, LATER)
    assert cfg.manifest_path.read_text() == before


# --- Acceptance 4: a doc:AGENTS.md target ----------------------------------------------------


def test_doc_agents_target(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    cfg, _ = _decided(tmp_path)  # agents-rule → doc:AGENTS.md, no retarget
    _ok(cfg, capsys)
    _lists(cfg, "traits: [agents-rule]", "traits: []")
    _fails(cfg, capsys, "trait 'agents-rule' is not listed by 'doc:AGENTS.md'")
    # review 2 #6: deleting the document's inventory never drops retention.
    path = cfg.traits_dir / "ours.yaml"
    text = path.read_text(encoding="utf-8")
    start = text.index("doc:AGENTS.md:")
    end = text.index("\n", text.index("traits: []", start)) + 1
    path.write_text(text[:start] + text[end:], encoding="utf-8")
    _fails(cfg, capsys, f"{ROUND}:5: 'doc:AGENTS.md' has no traits/ours.yaml entry")


def test_pending_adopt_into_planned_skill(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A pending adopt and its checkpoint may name a skill not yet built; a
    delivered adopt may not."""

    def judge(data: dict[str, Any]) -> None:
        _judge_pending(data)
        data["skills"][LOGICAL]["traits"]["novel"]["target"] = "planned"

    cfg = _cfg(tmp_path)
    ledger.seal(cfg, "2026-10-14-r")
    key = _seal(cfg, _draft(cfg), judge)
    events = _first_round(key)
    events[0]["skill"] = "planned"
    events[-1]["skill"] = "planned"
    _write_round(cfg, ROUND, *events, trait_level=True, date="2026-10-20")
    _point(cfg, SHA, None)
    _ok(cfg, capsys)
    done = _ev(
        f"{ROUND}:8",
        "adopt",
        "novel",
        skill="planned",
        report=key,
        supersedes=[f"{ROUND}:7"],
    )
    _write_round(cfg, ROUND, *events, done, trait_level=True, date="2026-10-20")
    _fails(cfg, capsys, f"{ROUND}:8: live adoption of {SUBJECT}#novel has an invalid")


# --- Acceptance 9: whole-skill mode ------------------------------------------------------------


def test_whole_skill_mode(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    def setup(base: Path) -> Any:
        cfg = _cfg(base)
        ledger.seal(cfg, "2026-10-14-r")
        _write_round(cfg, ROUND, trait_level=True, date="2026-10-20")
        return cfg

    # No entry at all, then a proposed-only entry: a whole-skill defer stands.
    bare = setup(tmp_path / "bare")
    (bare.traits_dir / "refrepo.yaml").unlink()
    with pytest.raises(SystemExit, match="needs `revisit_when`"):
        _record(bare, _new(_ev("x", "defer")), whole_skill="defer")
    later = {"revisit_when": "when it ships"}
    assert _record(bare, _new(_ev("x", "defer", **later)), whole_skill="defer") == 0
    assert _last(bare)["kind"] == "defer" and _last(bare)["subject"] == SUBJECT
    _ok(bare, capsys)
    _point(bare, None, SHA)
    _ok(bare, capsys)
    _point(bare, SHA, None)
    _fails(bare, capsys, "has an accepted analysis: decide it per trait")

    # With an accepted analysis, one verdict expands per trait; earlier
    # adoptions stay retained after the whole-skill reject.
    cfg, key = _decided(tmp_path / "decided")
    ledger.seal(cfg, ROUND)

    def reject_all(data: dict[str, Any]) -> None:
        _judge(data)
        data["supersedes"] = [key]
        # Reconsider rows only: no analysis evidence needed (review 2 #13).
        data["skills"][LOGICAL]["analysis"] = {"blind": [], "mapping": []}
        for row in data["skills"][LOGICAL]["traits"].values():
            row.update(recommendation="reject", delivery=None, guide=None)

    path = _draft(
        cfg, report_path=Path("registry/reviews/all.yaml"), reconsider=list(UPSTREAM)
    )
    again = _seal(cfg, path, reject_all)
    _write_round(cfg, LATER, trait_level=True, date="2026-10-21")
    request = {
        "subject": SUBJECT,
        "why": "not ours",
        "report": again,
        "evidence": ["x:1"],
    }
    assert _record(cfg, request, whole_skill="reject") == 0
    lines = (cfg.ledger_dir / f"{LATER}.jsonl").read_text().splitlines()[1:]
    got = {
        json.loads(line)["subject"].split("#")[1]: json.loads(line) for line in lines
    }
    assert set(got) == set(UPSTREAM)
    assert {e["kind"] for e in got.values()} == {"reject"}
    assert got["seams"]["report"] == again
    assert got["novel"]["report"] == key  # cancels the pending adopt: inherits
    assert got["seams"]["supersedes"] == [f"{ROUND}:3"]
    checkpoint = _new(_ev("x", "reject", supersedes=[f"{ROUND}:1"]))
    assert _record(cfg, checkpoint) == 0
    _ok(cfg, capsys)
    _lists(cfg, "traits: [red-green, seams]", "traits: [red-green]")
    _fails(cfg, capsys, "trait 'seams' is not listed by skill 'tdd'")


# --- Acceptance 21: rewording ------------------------------------------------------------------


def test_rewording(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    def reword(data: dict[str, Any]) -> None:
        _judge_pending(data)
        data["skills"][LOGICAL]["traits"]["seams"].update(
            delivery="pending",
            rewording="Name the seam before the test.",
            guide={"verdict": "reword", "rules": ["U-01"]},
        )

    cfg = _cfg(tmp_path)
    ledger.seal(cfg, "2026-10-14-r")
    key = _seal(cfg, _draft(cfg), reword)
    first = _first_round(key)
    _write_round(
        cfg, ROUND, *first[:2], *first[3:], trait_level=True, date="2026-10-20"
    )
    with pytest.raises(SystemExit, match="reword"):
        _record(cfg, _new(first[2]))  # a new delivered adopt
    pending = _new(first[2]) | {"pending": "cr-3"}
    with pytest.raises(SystemExit, match="needs `rewording`"):
        _record(cfg, pending)
    assert _record(cfg, pending | {"rewording": "Name the seam first."}) == 0
    recorded = _last(cfg)
    assert recorded["target_tree_hash"] == _tree_hash_of(cfg, "tdd")
    _point(cfg, SHA, None)
    _ok(cfg, capsys)  # tdd already lists seams: wording-only, still pending

    done = {
        "kind": "adopt",
        "subject": f"{SUBJECT}#seams",
        "why": "reworded",
        "evidence": ["tdd/SKILL.md:5"],
        "skill": "tdd",
        "supersedes": [recorded["id"]],
        "guide": {"verdict": "ok", "rules": ["U-01"]},
    }
    with pytest.raises(SystemExit, match="unchanged"):
        _record(cfg, done)
    old = _tree_hash_of(cfg, "tdd")
    _write_skill(cfg, "tdd", "Names the seam before the test.")
    _lists(cfg, old, _tree_hash_of(cfg, "tdd"))
    assert _record(cfg, done) == 0
    _ok(cfg, capsys)

    lines = (cfg.ledger_dir / f"{ROUND}.jsonl").read_text().splitlines()
    wrong = json.loads(lines[-1])
    wrong["guide"]["rules"] = []
    (cfg.ledger_dir / f"{ROUND}.jsonl").write_text(
        "\n".join([*lines[:-1], json.dumps(wrong)]) + "\n"
    )
    _fails(cfg, capsys, "guide rules [] are not the row's ['U-01']")
    delivered = json.loads(lines[-2]) | {"id": f"{ROUND}:9"}
    delivered = {
        k: v
        for k, v in delivered.items()
        if k not in {"pending", "rewording", "target_tree_hash"}
    }
    (cfg.ledger_dir / f"{ROUND}.jsonl").write_text(
        "\n".join([lines[0], *lines[1:-2], json.dumps(delivered)]) + "\n"
    )
    _fails(cfg, capsys, f"{ROUND}:9: a new delivered adopt from a `reword` row")


def test_completion_keeps_target_and_trait(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    # review 2 #3: completing a rewording into another skill or another trait
    # is a new decision, so the `reword` row refuses it.
    def reword(data: dict[str, Any]) -> None:
        _judge_pending(data)
        data["skills"][LOGICAL]["traits"]["seams"].update(
            delivery="pending",
            rewording="Name the seam first.",
            guide={"verdict": "reword", "rules": ["U-01"]},
        )

    cfg = _cfg(tmp_path)
    ledger.seal(cfg, "2026-10-14-r")
    key = _seal(cfg, _draft(cfg), reword)
    first = _first_round(key)
    pend = first[2] | {"pending": "cr-3", "rewording": "Name the seam first."}
    pend["target_tree_hash"] = _tree_hash_of(cfg, "tdd")
    _write_round(cfg, ROUND, *first[:2], pend, *first[3:], trait_level=True)
    done = {
        "kind": "adopt",
        "subject": f"{SUBJECT}#seams",
        "why": "reworded",
        "evidence": ["debug/SKILL.md:5"],
        "skill": "debug",
        "supersedes": [f"{ROUND}:3"],
        "guide": {"verdict": "ok", "rules": ["U-01"]},
        "report": key,
        "source": _source(),
    }
    with pytest.raises(SystemExit, match="new delivered adopt from a `reword` row"):
        _record(cfg, done)
    into = done | {"skill": "tdd", "into": "mocks-strict", "modification": "m"}
    with pytest.raises(SystemExit, match="new delivered adopt from a `reword` row"):
        _record(cfg, into)
    moved = _ev(f"{ROUND}:8", "adopt", "seams", report=key) | {
        k: done[k] for k in ("evidence", "skill", "supersedes", "guide")
    }
    _write_round(cfg, ROUND, *first[:2], pend, *first[3:], moved, trait_level=True)
    _fails(cfg, capsys, f"{ROUND}:8: a new delivered adopt from a `reword` row")


def _reconsider_novel(cfg: Any, key: str, name: str, target: str = "tdd") -> str:
    """A sealed report superseding `key` with a `reconsider` row adopting
    `novel` delivered into `target`, guide `ok`."""

    def change(data: dict[str, Any]) -> None:
        _judge(data)
        data["supersedes"] = [key]
        data["skills"][LOGICAL]["traits"]["novel"].update(
            recommendation="adopt",
            delivery="delivered",
            guide={"verdict": "ok", "rules": ["U-01"]},
        )

    path = _draft(
        cfg,
        target,
        report_path=Path(f"registry/reviews/{name}.yaml"),
        reconsider=["novel"],
    )
    return _seal(cfg, path, change)


def test_new_adopt_beside_pending_is_a_new_decision(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    # Sol re-review #1: a delivered adopt that does not supersede the pending
    # adopt is a new decision; `record` and `check` agree it is valid.
    cfg, key = _decided(tmp_path)
    _lists(cfg, "traits: [red-green, seams]", "traits: [red-green, seams, novel]")
    again = _reconsider_novel(cfg, key, "re")
    adopt = {
        "kind": "adopt",
        "subject": f"{SUBJECT}#novel",
        "why": "decided afresh",
        "evidence": ["x:1"],
        "skill": "tdd",
        "report": again,
        "source": _source(),
    }
    assert _record(cfg, adopt) == 0
    assert _last(cfg)["report"] == again
    _ok(cfg, capsys)


def test_later_merge_keeps_earlier_classification(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    # Sol re-review #2: a merge recorded later never turns an earlier new
    # decision into a completion; a completion after the merge still is one.
    merge = {
        "kind": "merge",
        "subject": "ours:tdd",
        "why": "folded in",
        "evidence": ["x:1"],
        "skill": "debug",
    }
    cfg, key = _decided(tmp_path / "new")
    _lists(cfg, "mocks-strict]", "mocks-strict, novel]")
    again = _reconsider_novel(cfg, key, "re", target="debug")
    moved = {
        "kind": "adopt",
        "subject": f"{SUBJECT}#novel",
        "why": "into debug instead",
        "evidence": ["x:1"],
        "skill": "debug",
        "report": again,
        "source": _source(),
        "supersedes": [f"{ROUND}:7"],
    }
    assert _record(cfg, moved) == 0
    assert _last(cfg)["report"] == again
    _ok(cfg, capsys)
    assert _record(cfg, merge) == 0
    _ok(cfg, capsys)

    cfg, key = _decided(tmp_path / "done")
    _lists(cfg, "mocks-strict]", "mocks-strict, novel]")
    assert _record(cfg, merge) == 0
    done = moved | {"why": "landed in the survivor"}
    del done["report"], done["source"]
    assert _record(cfg, done) == 0
    assert _last(cfg)["report"] == key and _last(cfg)["source"] == _source()
    _ok(cfg, capsys)
