"""Status, shared traits and trait policy (stages-design Stage 4, §Shared
traits, §Trait policy; Acceptance 1, 11, 12, 20, 22, 23)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
import yaml

from curation.registry import cli, ledger, reports, status
from curation.registry.policy import guide_rules, rule_digest
from curation.scan import catalog as scan
from curation.scan.models import Catalog
from tests.curation.test_decisions import (
    LATER,
    NEW,
    ROUND,
    SHA,
    _decided,
    _ev,
    _fails,
    _first_round,
    _last,
    _lists,
    _new,
    _ok,
    _point,
    _record,
    _seal,
)
from tests.curation.test_registry import (
    _PLACEMENT,
    LOGICAL,
    SUBJECT,
    _cap,
    _catalog,
    _ns,
    _ours_event,
    _write_round,
)
from tests.curation.test_reports import UPSTREAM, _cfg, _draft, _edit, _judge

D1 = rule_digest("State the outcome.")
OTHER = "skill:skills/other"
WHOLE = "skill:skills/whole"
EMPTY = "skill:skills/empty"


def _caps(tree_hash: str | None = f"T-{SHA}", tdd: bool = True) -> list[dict[str, Any]]:
    caps = [
        _cap("skill", "other", OTHER, "h"),
        _cap("skill", "whole", WHOLE, "h"),
        {**_cap("skill", "empty", EMPTY, "h"), "tree_hash": "T-e"},
        _cap("agent", "x", "agent:agents/x", "h"),
    ]
    if tdd:
        caps.append({**_cap("skill", "tdd", LOGICAL, "h"), "tree_hash": tree_hash})
    return caps


def _upstream(
    cfg: Any,
    accepted: str | None,
    proposed: str | None,
    removed: tuple[str, ...] = (),
    whole: bool = False,
) -> None:
    """The tdd entry (NEW changes seams and mocks), an empty analysis and,
    with `whole`, a proposed analysis of the whole-skill-deferred skill."""

    def analysis(sha: str, traits: list[str], extra: str = "") -> str:
        return (
            f'    "{sha}":\n      tree_hash: "T-{sha}"\n      placement: {_PLACEMENT}\n'
            f"      traits: [{', '.join(traits)}]\n{extra}"
        )

    out = f"refrepo:{LOGICAL}:\n"
    out += f"  accepted: {json.dumps(accepted)}\n  proposed: {json.dumps(proposed)}\n"
    out += "  analyses:\n" + analysis(SHA, UPSTREAM)
    if NEW in (accepted, proposed):
        extra = '      changed: {seams: "x", mocks: "x"}\n'
        if removed:
            extra += (
                "      removed: {" + ", ".join(f'{t}: "x"' for t in removed) + "}\n"
            )
        out += analysis(NEW, [t for t in UPSTREAM if t not in removed], extra)
    out += f'refrepo:{EMPTY}:\n  accepted: null\n  proposed: "e"\n  analyses:\n'
    out += analysis("e", [])
    if whole:
        out += f'refrepo:{WHOLE}:\n  accepted: null\n  proposed: "w"\n  analyses:\n'
        out += analysis("w", ["red-green"])
    (cfg.traits_dir / "refrepo.yaml").write_text(out, encoding="utf-8")


def _status(cfg: Any) -> dict[str, status.SkillStatus]:
    path = cfg.catalogs_dir / "refrepo.json"
    catalog = Catalog.from_dict(json.loads(path.read_text(encoding="utf-8")))
    ctx = reports.load_context(cfg)
    return {s.logical_id: s for s in status.skill_statuses(ctx, catalog)}


def _stages(cfg: Any) -> dict[str, str]:
    return {t.trait: t.stage for t in _status(cfg)[LOGICAL].traits}


def _provisions(cfg: Any) -> dict[str, str | None]:
    return {t.trait: t.provision for t in _status(cfg)[LOGICAL].traits}


def _status_out(cfg: Any, capsys: pytest.CaptureFixture[str], **kw: Any) -> str:
    args = {"harness": "refrepo", "skill": None, "traits": False} | kw
    assert cli.cmd_status(cfg, _ns(**args)) == 0
    return capsys.readouterr().out


def _whole_defer() -> dict[str, Any]:
    return {
        "type": "event",
        "id": f"{ROUND}:8",
        "date": "2026-10-20",
        "kind": "defer",
        "subject": f"refrepo:{WHOLE}",
        "why": "later",
        "evidence": ["x:1"],
        "revisit_when": "when analysed",
        "source": {"repo": "refrepo", "logical_id": WHOLE},
    }


# --- Acceptance 1: pin moves, tree hashes ------------------------------------------


def test_stage_follows_tree_hash_not_pin(tmp_path: Path) -> None:
    cfg = _cfg(tmp_path)
    harness = tmp_path / "upstream"
    folder = harness / "skills" / "engineering" / "tdd"
    folder.mkdir(parents=True)
    (folder / "SKILL.md").write_text("---\nname: tdd\n---\n# tdd\n", encoding="utf-8")

    def rescan(pin: str) -> str:
        cat = scan.scan_repo(harness, "refrepo", source="x", source_commit=pin)
        path = cfg.catalogs_dir / "refrepo.json"
        path.write_text(json.dumps(cat.to_dict()), encoding="utf-8")
        found = cat.by_logical_id()[LOGICAL].tree_hash
        assert found is not None
        return found

    tree = rescan("pin1")
    path = cfg.traits_dir / "refrepo.yaml"
    path.write_text(path.read_text().replace(f"T-{SHA}", tree), encoding="utf-8")
    assert _status(cfg)[LOGICAL].stage == "analysed"
    (folder / "SKILL.md").chmod(0o755)  # an executable bit only
    assert rescan("pin2") == tree
    assert _status(cfg)[LOGICAL].stage == "analysed"
    (folder / "SKILL.md").write_text("---\nname: tdd\n---\n# changed\n")
    assert rescan("pin3") != tree
    assert _status(cfg)[LOGICAL].stage == "needs re-analysis"
    assert set(_stages(cfg).values()) == {"needs re-analysis"}


# --- Acceptance 11: every stage and provision ---------------------------------------


def test_status_stages_and_provisions(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    cfg, key = _decided(tmp_path)
    first = _first_round(key)
    _write_round(cfg, ROUND, *first, _whole_defer(), trait_level=True)
    _catalog(cfg, "refrepo", _caps())
    _upstream(cfg, SHA, None)
    got = _status(cfg)
    assert got[LOGICAL].stage == "decided"
    assert {t.trait: (t.stage, t.ruling, t.provision) for t in got[LOGICAL].traits} == {
        "red-green": ("decided", "adopt", "delivered"),
        "seams": ("decided", "adopt", "delivered"),
        "mocks": ("decided", "defer", None),
        "agents-rule": ("decided", "adopt", "delivered"),
        "style-rule": ("decided", "defer", None),
        "novel": ("decided", "adopt", "pending"),
    }
    assert got[OTHER].stage == "not analysed"
    assert got[WHOLE].stage == "decided (whole skill)"
    assert got[EMPTY].stage == "analysed, no traits"
    out = _status_out(cfg, capsys, traits=True)
    assert "agent:agents/x  not reviewed" in out and "novel" in out
    _upstream(cfg, SHA, None, whole=True)
    assert _status(cfg)[WHOLE].stage == "decided (whole skill) + analysed"

    # Provision: withdrawn, target dropped, target retired without replacement.
    withdraw = _ours_event(
        f"{ROUND}:9", "update", "tdd", withdraws=[f"{SUBJECT}#red-green"]
    )
    _write_round(cfg, ROUND, *first, withdraw, trait_level=True)
    _lists(cfg, "traits: [red-green, seams]", "traits: [red-green]")
    assert _provisions(cfg) == {
        "red-green": "withdrawn",
        "seams": "no longer provided",
        "mocks": None,
        "agents-rule": "delivered",
        "style-rule": None,
        "novel": "pending",
    }
    _lists(cfg, "traits: [red-green]", "traits: [red-green, seams]")
    retire = _ours_event(f"{ROUND}:9", "retire", "tdd")
    _write_round(cfg, ROUND, *first, retire, trait_level=True)
    assert _provisions(cfg)["seams"] == "no longer provided"
    _write_round(cfg, ROUND, *first, trait_level=True)

    # A newer analysis: the old tree hash needs re-analysis; once current, an
    # untouched ruling carries and a changed deferred trait is `analysed`.
    _upstream(cfg, SHA, NEW)
    assert set(_stages(cfg).values()) == {"needs re-analysis"}
    _catalog(cfg, "refrepo", _caps(f"T-{NEW}"))
    assert _stages(cfg) == {
        "red-green": "decided",
        "seams": "analysed",
        "mocks": "analysed",
        "agents-rule": "decided",
        "style-rule": "decided",
        "novel": "decided",
    }
    assert _status(cfg)[LOGICAL].stage == "analysed"

    draft = _draft(cfg)
    assert {_stages(cfg)[t] for t in ("seams", "mocks")} == {"in review"}
    _edit(draft, _judge)
    assert reports.seal(cfg, draft) == []
    assert {_stages(cfg)[t] for t in ("seams", "mocks")} == {"reported"}
    _draft(cfg, report_path=Path("registry/reviews/second.yaml"))
    assert _stages(cfg)["seams"] == "reported"  # a draft never displaces it
    _lists(cfg, "traits: [red-green, seams]", "traits: [red-green]")
    assert _stages(cfg)["seams"] == "needs re-comparison"
    # review 2 #12: the skill shows its least advanced trait by progress rank;
    # seams (needs re-comparison) is behind mocks (reported).
    assert _status(cfg)[LOGICAL].stage == "needs re-comparison"
    _lists(cfg, "traits: [red-green]", "traits: [red-green, seams]")

    _upstream(cfg, SHA, NEW, removed=("novel",))
    novel = next(t for t in _status(cfg)[LOGICAL].traits if t.trait == "novel")
    assert (novel.stage, novel.ruling, novel.provision) == (
        "removed upstream",
        "adopt",
        "pending",
    )
    _catalog(cfg, "refrepo", _caps(tdd=False))
    assert _status(cfg)[LOGICAL].stage == "removed upstream"


def test_variant_with_two_candidates_is_one_row(tmp_path: Path) -> None:
    cfg = _cfg(tmp_path)
    defs = yaml.safe_load(cfg.trait_definitions_path.read_text())
    defs["mocks-loose"] = dict(defs["mocks-strict"], definition="Looser.")
    cfg.trait_definitions_path.write_text(yaml.safe_dump(defs))
    _lists(cfg, "mocks-strict]", "mocks-strict, mocks-loose]")
    path = _draft(cfg, "debug")
    row = yaml.safe_load(path.read_text())["skills"][LOGICAL]["traits"]["mocks"]
    assert (row["fact"], row["candidates"]) == (
        "variant",
        ["mocks-loose", "mocks-strict"],
    )
    _edit(path, _judge)  # selects one `via`
    assert reports.seal(cfg, path) == []
    mocks = [t for t in _status(cfg)[LOGICAL].traits if t.trait == "mocks"]
    assert [t.stage for t in mocks] == ["reported"]


# --- Acceptance 12: shared traits ---------------------------------------------------


def _sharing(cfg: Any, **entries: list[str]) -> None:
    body = {
        tid: {"skills": skills, "why": "One format.", "reviewed": "2026-10-30"}
        for tid, skills in entries.items()
    }
    cfg.trait_sharing_path.write_text(yaml.safe_dump(body), encoding="utf-8")


def test_shared_traits(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    cfg = _cfg(tmp_path)  # tdd and debug both list red-green and seams
    assert cli.cmd_check(cfg, _ns()) == 0
    err = capsys.readouterr().err
    assert "shared trait 'seams' (debug, tdd) has no trait-sharing.yaml entry" in err
    assert "overlap" not in err
    _sharing(cfg, seams=["tdd", "debug"])
    _ok(cfg, capsys)
    md = cfg.traits_md_path.read_text()
    assert "| `seams` | debug, tdd | One format. |" in md
    assert "| `red-green` | debug, tdd | not yet justified |" in md
    _sharing(cfg, seams=["tdd"])
    _fails(cfg, capsys, "trait-sharing.yaml: seams: skills ['tdd'] are not its")
    _sharing(cfg, seams=["tdd", "debug"], mocks=["debug"])
    _fails(cfg, capsys, "trait-sharing.yaml: mocks: not a shared trait")
    # doc:AGENTS.md counts as a holder
    _sharing(cfg, seams=["tdd", "debug"])
    _lists(cfg, "traits: [red-green, seams]", "traits: [red-green, seams, agents-rule]")
    assert cli.cmd_build(cfg, _ns()) == 0
    assert cli.cmd_check(cfg, _ns()) == 0
    assert "'agents-rule' (doc:AGENTS.md, tdd) has no" in capsys.readouterr().err


# --- Acceptance 20: policy at record time and in check ------------------------------


def _pol(stance: str, ledger_id: str, **extra: Any) -> dict[str, Any]:
    return {
        "stance": stance,
        "rules": {"U-01": D1},
        "why": "A guide rule.",
        "decided": "2026-10-20",
        "reviewed": "2026-10-20",
        "ledger": ledger_id,
        "from": [],
        **extra,
    }


def _policy(cfg: Any, **entries: dict[str, Any]) -> None:
    cfg.trait_policy_path.write_text(yaml.safe_dump(entries), encoding="utf-8")


def _guide(cfg: Any, text: str) -> None:
    path = cfg.repo_root / "harness_lifecycle" / "prompting-guides" / "GUIDE.md"
    path.write_text("# Guide\n\n" + text, encoding="utf-8")


def _open(tmp: Path, checkpoint: bool = True) -> tuple[Any, str]:
    """A sealed report and an open round holding only the checkpoint."""
    cfg = _cfg(tmp)
    ledger.seal(cfg, "2026-10-14-r")
    key = _seal(cfg, _draft(cfg))
    events = _first_round(key)[:1] if checkpoint else []
    _write_round(cfg, ROUND, *events, trait_level=True, date="2026-10-20")
    return cfg, key


def test_policy_enforced_at_record_time(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    cfg, key = _open(tmp_path / "avoid")
    first = _first_round(key)
    _policy(cfg, seams=_pol("avoid", "2026-10-14-r:1"))
    assert _record(cfg, _new(first[1])) == 0
    assert "policy_basis" in _last(cfg) and _last(cfg)["policy_basis"] is None
    with pytest.raises(SystemExit, match="needs `override`"):
        _record(cfg, _new(first[2]))
    assert _record(cfg, _new(first[2]) | {"override": "Our seam rule differs."}) == 0
    assert _last(cfg)["policy_basis"] == {"stance": "avoid", "rules": {"U-01": D1}}
    for event in first[3:]:
        assert _record(cfg, _new(event)) == 0
    _point(cfg, SHA, None)
    assert cli.cmd_build(cfg, _ns()) == 0
    assert cli.cmd_check(cfg, _ns()) == 0
    err = capsys.readouterr().err
    assert "skill 'tdd' lists 'seams', whose policy is `avoid`" in err
    path = cfg.ledger_dir / f"{ROUND}.jsonl"
    lines = path.read_text().splitlines()
    seams = json.loads(lines[3])
    assert seams["subject"].endswith("#seams")
    del seams["override"]
    path.write_text("\n".join([*lines[:3], json.dumps(seams), *lines[4:]]) + "\n")
    _fails(cfg, capsys, f"{seams['id']}: adopting a trait whose policy is `avoid`")

    # `report draft` pre-fills the stance for the same trait in another harness;
    # `--refresh` updates it.
    (cfg.traits_dir / "otherrepo.yaml").write_text(
        'otherrepo:skill:skills/x:\n  accepted: null\n  proposed: "abc1234"\n'
        f'  analyses:\n    "abc1234":\n      tree_hash: "T"\n'
        f"      placement: {_PLACEMENT}\n      traits: [seams]\n"
    )
    _catalog(cfg, "otherrepo", [_cap("skill", "x", "skill:skills/x", "h")])
    other = reports.draft(cfg, "otherrepo", "skill:skills/x", "tdd")
    row = yaml.safe_load(other.read_text())["skills"]["skill:skills/x"]["traits"]
    assert row["seams"]["policy"] == {"stance": "avoid", "rules": ["U-01"]}
    _policy(cfg, seams=_pol("reword", "2026-10-14-r:1"))
    reports.draft(cfg, "otherrepo", "skill:skills/x", "tdd", refresh=True)
    row = yaml.safe_load(other.read_text())["skills"]["skill:skills/x"]["traits"]
    assert row["seams"]["policy"] == {"stance": "reword", "rules": ["U-01"]}

    # A `reword` trait's adopt must cite a row whose guide rules include the
    # entry's rules.
    cfg, key = _open(tmp_path / "reword")
    _guide(cfg, "- **U-01** State the outcome.\n- **U-02** Name the scope.\n")
    rules = {"U-01": D1, "U-02": rule_digest("Name the scope.")}
    _policy(cfg, seams=_pol("reword", "2026-10-14-r:1", rules=rules))
    with pytest.raises(SystemExit, match=r"omits \['U-02'\]"):
        _record(cfg, _new(_first_round(key)[2]))
    _policy(cfg, seams=_pol("reword", "2026-10-14-r:1"))
    assert _record(cfg, _new(_first_round(key)[2])) == 0


def test_history_keeps_its_basis(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    cfg, _ = _decided(tmp_path)
    ledger.seal(cfg, ROUND)
    # Adopted traits become `avoid` later: earlier decisions keep their basis.
    _policy(
        cfg,
        **{
            "red-green": _pol("avoid", f"{ROUND}:2"),
            "novel": _pol("avoid", f"{ROUND}:7"),
            "seams": _pol("reword", f"{ROUND}:3"),
        },
    )
    _ok(cfg, capsys)
    _point(cfg, SHA, NEW, shas=(SHA, NEW))
    later_key = _seal(cfg, _draft(cfg), _judge)
    checkpoint = _ev(
        f"{LATER}:1", "adopt-merged", sha=NEW, skill="tdd", supersedes=[f"{ROUND}:1"]
    )
    _write_round(cfg, LATER, checkpoint, trait_level=True, date="2026-10-21")
    seams = _ev(
        f"{LATER}:2",
        "adopt",
        "seams",
        sha=NEW,
        skill="tdd",
        report=later_key,
        supersedes=[f"{ROUND}:3"],
    )
    assert _record(cfg, _new(seams)) == 0
    assert _last(cfg, LATER)["policy_basis"] == {
        "stance": "reword",
        "rules": {"U-01": D1},
    }
    _point(cfg, NEW, None, shas=(SHA, NEW))
    # Completing the pending `novel` (now `avoid`) copies its null basis.
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
    assert _last(cfg, LATER)["policy_basis"] is None
    _ok(cfg, capsys)  # red-green carried; seams and novel at their bases

    # The cited rule is replaced and the entry re-reviewed: history stands.
    _guide(cfg, "- **U-01** Retired 2026-10-30; see U-02.\n- **U-02** Say it.\n")
    rules = {"U-02": rule_digest("Say it.")}
    _policy(
        cfg,
        **{
            "red-green": _pol("avoid", f"{ROUND}:2"),
            "novel": _pol("avoid", f"{ROUND}:7"),
            "seams": _pol("reword", f"{ROUND}:3", rules=rules, reviewed="2026-10-30"),
        },
    )
    _ok(cfg, capsys)

    path = cfg.ledger_dir / f"{LATER}.jsonl"
    lines = path.read_text().splitlines()
    wrong = json.loads(lines[-1]) | {"policy_basis": {"stance": "avoid", "rules": {}}}
    path.write_text("\n".join([*lines[:-1], json.dumps(wrong)]) + "\n")
    _fails(cfg, capsys, "must copy `policy_basis` from pending")


# --- Acceptance 22: retirement reconciliation ---------------------------------------


def test_policy_retirement(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    cfg, key = _open(tmp_path / "retire", checkpoint=False)
    _policy(cfg, seams=_pol("avoid", "2026-10-14-r:1"))
    _ok(cfg, capsys)
    defs = yaml.safe_load(cfg.trait_definitions_path.read_text())
    defs["seams"]["retired"] = {"date": "2026-10-25", "replaced_by": ["novel"]}
    cfg.trait_definitions_path.write_text(yaml.safe_dump(defs))
    _fails(cfg, capsys, "seams: retired; `reconciled` must cover exactly")
    reconciled = {"reconciled": {"novel": "carried"}}
    _policy(cfg, seams=_pol("avoid", "2026-10-14-r:1", **reconciled))
    _fails(cfg, capsys, "carried to 'novel', whose entry must list 'seams'")
    _policy(
        cfg,
        seams=_pol("avoid", "2026-10-14-r:1", **reconciled),
        novel=_pol("avoid", "2026-10-14-r:1", **{"from": ["seams"]}),
    )
    _ok(cfg, capsys)
    novel = _new(_first_round(key)[6])
    with pytest.raises(SystemExit, match="needs `override`"):
        _record(cfg, novel)
    assert _record(cfg, novel | {"override": "Needed here."}) == 0

    # Upstream A→B (a new mechanism) leaves B without A's stance.
    cfg = _cfg(tmp_path / "ab")
    _policy(cfg, mocks=_pol("avoid", "2026-10-14-r:1"))
    b_traits = [t if t != "mocks" else "mocks-strict" for t in UPSTREAM]
    (cfg.traits_dir / "refrepo.yaml").write_text(
        f"refrepo:{LOGICAL}:\n  accepted: null\n  proposed: {json.dumps(NEW)}\n"
        f'  analyses:\n    "{NEW}":\n      tree_hash: "T-{NEW}"\n'
        f"      placement: {_PLACEMENT}\n      traits: [{', '.join(b_traits)}]\n"
        '      added: {mocks-strict: "x"}\n      removed: {mocks: "x"}\n'
    )
    rows = yaml.safe_load(_draft(cfg).read_text())["skills"][LOGICAL]["traits"]
    assert rows["mocks-strict"]["policy"] is None
    _ok(cfg, capsys)  # A's entry stays on A


# --- Acceptance 23: guide changes ---------------------------------------------------


def test_guide_changed(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    cfg = _cfg(tmp_path)
    _policy(cfg, seams=_pol("reword", "2026-10-14-r:1"))
    assert "guide changed (trait-policy.yaml): 0" in _status_out(cfg, capsys)
    _guide(cfg, "- **U-01** State  the outcome and scope. [a.md:1-2] [b.md:3]\n")
    now = rule_digest("State the outcome and scope.")
    assert guide_rules(cfg.guide_path)["U-01"] == (
        "State the outcome and scope.",
        now,
        False,
    )
    out = _status_out(cfg, capsys)
    assert f"seams: U-01 {D1} → {now}" in out
    assert cli.cmd_check(cfg, _ns()) == 0
    assert "trait-policy.yaml: seams: guide changed" in capsys.readouterr().err
    _policy(cfg, seams=_pol("reword", "2026-10-14-r:1", rules={"U-01": now}))
    assert "guide changed (trait-policy.yaml): 0" in _status_out(cfg, capsys)
    _guide(cfg, "- **U-01** Retired 2026-10-30; see U-02.\n")
    assert "seams: U-01 retired" in _status_out(cfg, capsys)
    _policy(cfg, seams=_pol("reword", "2026-10-14-r:1", rules={"U-09": now}))
    assert "seams: U-09 missing" in _status_out(cfg, capsys)
