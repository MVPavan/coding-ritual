"""Report files: computed facts, pairing, draft, seal, immutability and the
current row (stages-design §Report file; Acceptance 3-5, 17-19)."""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
import yaml

from curation.registry import cli, ledger, reports
from curation.registry import traits as trait_facts
from curation.registry.loaders import load_skills
from curation.registry.models import Report
from tests.curation.test_registry import (
    _PLACEMENT,
    LOGICAL,
    _cap,
    _catalog,
    _make_cfg,
    _ns,
    _ours_event,
    _trait,
    _tree_hash_of,
    _write_defs,
    _write_record,
    _write_round,
    _write_skill,
    _write_traits,
)

UPSTREAM = ["red-green", "seams", "mocks", "agents-rule", "style-rule", "novel"]
STYLE = "doc:.repo-context/style.md"
SHA = "abc1234"


def _defs() -> str:
    out = ""
    for t in [*UPSTREAM, "mocks-strict"]:
        out += f"{t}:\n  definition: Does {t}.\n  placement: {_PLACEMENT}\n"
    return out + "  distinct_from: [mocks]\n  note: Stricter.\n"


def _entry(accepted: str | None, proposed: str | None, extra: str = "") -> str:
    """The upstream entry; every named sha gets one analysis of UPSTREAM."""
    out = f"refrepo:{LOGICAL}:\n"
    out += f"  accepted: {json.dumps(accepted)}\n  proposed: {json.dumps(proposed)}\n"
    out += "  analyses:\n"
    for sha in [s for s in (accepted, proposed) if s]:
        out += (
            f'    "{sha}":\n      tree_hash: "T-{sha}"\n      placement: {_PLACEMENT}\n'
            f"      traits: [{', '.join(UPSTREAM)}]\n"
        )
        if sha == proposed and accepted:
            out += extra
    return out


def _cfg(
    tmp: Path,
    accepted: str | None = None,
    proposed: str | None = "abc1234",
    debug: tuple[str, ...] = ("red-green", "seams", "mocks-strict"),
    extra: str = "",
    check: bool = True,
) -> Any:
    """tdd (placement match) lists red-green and seams; debug lists three,
    one a variant of `mocks`; AGENTS.md and a .repo-context doc one each.
    `check=False` skips the closing `check` (an accepted analysis with no
    checkpoint fails it, 3.7)."""
    cfg: Any = _make_cfg(tmp)
    _write_skill(cfg, "tdd")
    _write_skill(cfg, "debug")
    _write_record(cfg, "tdd", "engineering", "Design", "Specification")
    _write_record(cfg, "debug", "engineering", "Building", "Diagnosis")
    _write_defs(cfg, _defs())
    docs = ""
    for key, trait in (("doc:AGENTS.md", "agents-rule"), (STYLE, "style-rule")):
        rel = key[len("doc:") :]
        path = cfg.repo_root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"{trait}\n", encoding="utf-8")
        th = trait_facts._doc_tree_hash(rel, path.read_bytes())
        docs += f'{key}:\n  tree_hash: "{th}"\n  traits: [{trait}]\n'
    ours = ""
    for skill, listed in (("tdd", ("red-green", "seams")), ("debug", debug)):
        ours += f'ours:{skill}:\n  tree_hash: "{_tree_hash_of(cfg, skill)}"\n'
        ours += f"  traits: [{', '.join(listed)}]\n"
    _write_traits(cfg, ours + docs + _entry(accepted, proposed, extra))
    _catalog(cfg, "refrepo", [_cap("skill", "tdd", LOGICAL, "h")])
    guide = cfg.repo_root / "harness_lifecycle" / "prompting-guides" / "GUIDE.md"
    guide.parent.mkdir(parents=True)
    guide.write_text("# Guide\n\n- **U-01** State the outcome.\n", encoding="utf-8")
    _write_round(cfg, "2026-10-14-r", _ours_event("2026-10-14-r:1", "add", "tdd"))
    assert cli.cmd_build(cfg, _ns()) == 0
    assert not check or cli.cmd_check(cfg, _ns()) == 0
    return cfg


def _draft(cfg: Any, with_: str = "tdd", **kw: Any) -> Path:
    return reports.draft(cfg, "refrepo", LOGICAL, with_, **kw)


def _edit(path: Path, change: Callable[[dict[str, Any]], None]) -> None:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    change(data)
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")


def _judge(data: dict[str, Any]) -> None:
    """Fill every judged field so the report can pass."""
    critic = {"by": "critic", "date": "2026-10-30", "verdict": "pass"}
    data["analysis_critic"] = dict(critic)
    data["comparison_critic"] = dict(critic)
    data["themes"] = "Test release."
    skill = data["skills"][LOGICAL]
    skill["analysis"] = {
        "blind": ["Writes a failing test first."],
        "mapping": [{"line": 1, "to": ["red-green"], "mark": "match"}],
    }
    pairing = skill["pairing"]
    pairing["purpose_match"] = "tdd"
    pairing["purpose"] = "Both write the test first."
    if {skill["compared_with"], pairing["suggested"]} != {"tdd"}:
        pairing["flag"] = "picks differ"
        pairing["reason"] = "Purpose beats overlap here."
    for row in skill["traits"].values():
        if row["fact"] == "absent":
            row.update(recommendation="defer", revisit_when="when needed")
        else:
            row.update(
                recommendation="adopt",
                delivery="delivered",
                ours=["AGENTS.md:1"],
                guide={"verdict": "ok", "rules": ["U-01"]},
            )
            if row["fact"] == "variant":
                row.update(via=row["candidates"][0], modification="Stricter.")
        row["reason"] = "One sentence."


def _sealed(cfg: Any, **kw: Any) -> Path:
    path = _draft(cfg, **kw)
    _edit(path, _judge)
    assert reports.seal(cfg, path) == []
    assert cli.cmd_build(cfg, _ns()) == 0
    return path


def _rows(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return data["skills"][LOGICAL]["traits"]  # type: ignore[no-any-return]


def _fails(cfg: Any, capsys: pytest.CaptureFixture[str], needle: str) -> None:
    assert cli.cmd_check(cfg, _ns()) == 1
    assert needle in capsys.readouterr().err


# --- facts (Acceptance 3, 4, 17, 18) ---------------------------------------------


def test_facts_and_pairing(tmp_path: Path) -> None:
    cfg = _cfg(tmp_path)
    path = _draft(cfg)
    rows = _rows(path)
    assert list(rows) == UPSTREAM  # new skill: every trait, in analysis order
    assert {r["scope"] for r in rows.values()} == {"new"}
    got = {t: (r["fact"], r["provider"], r["also_in"]) for t, r in rows.items()}
    assert got == {
        "red-green": ("present", "tdd", {"debug": "present"}),
        "seams": ("present", "tdd", {"debug": "present"}),
        # 3: only in a non-compared skill (as a variant there): absent
        "mocks": ("absent", None, {"debug": "variant"}),
        # 4, 17: AGENTS.md makes it present for any compared skill
        "agents-rule": ("present", "doc:AGENTS.md", {}),
        # 17: a .repo-context doc is never coverage
        "style-rule": ("absent", None, {STYLE: "present"}),
        "novel": ("absent", None, {}),
    }
    pairing = yaml.safe_load(path.read_text())["skills"][LOGICAL]["pairing"]
    # 18: the skill covering the most traits, with the overlap table
    assert pairing["overlap"] == {
        "debug": 3,
        STYLE: 1,
        "doc:AGENTS.md": 1,
        "tdd": 2,
    }
    assert pairing["placement_match"] == ["tdd"]
    assert pairing["suggested"] == "debug"
    assert pairing["purpose_match"] is None

    other = _draft(cfg, "debug", report_path=Path("registry/reviews/b.yaml"))
    mocks = _rows(other)["mocks"]
    assert (mocks["fact"], mocks["provider"], mocks["candidates"]) == (
        "variant",
        "debug",
        ["mocks-strict"],
    )
    none = _draft(cfg, "none", report_path=Path("registry/reviews/c.yaml"))
    assert _rows(none)["agents-rule"]["provider"] == "doc:AGENTS.md"
    assert _rows(none)["red-green"]["fact"] == "absent"
    assert _rows(none)["mocks"]["fact"] == "absent"

    # A tie in overlap goes to the placement match.
    held = {"a": {"x"}, "tdd": {"x"}}
    _, _, suggested = trait_facts.compute_pairing(
        ["x"], "engineering", "Specification", held, {}, load_skills(cfg)[0]
    )
    assert suggested == "tdd"


# --- draft ------------------------------------------------------------------------


def test_draft_refusals_and_refresh(tmp_path: Path) -> None:
    cfg = _cfg(tmp_path)
    path = _draft(cfg)
    with pytest.raises(SystemExit, match="already in the report"):
        _draft(cfg)
    with pytest.raises(SystemExit, match="not a skill"):
        _draft(cfg, "doc:AGENTS.md", report_path=Path("registry/reviews/x.yaml"))
    with pytest.raises(SystemExit, match="not a trait"):
        _draft(cfg, refresh=True, reconsider=["nope"])

    def judged(data: dict[str, Any]) -> None:
        data["skills"][LOGICAL]["traits"]["novel"]["reason"] = "kept"
        data["skills"][LOGICAL]["pairing"]["purpose"] = "kept too"

    _edit(path, judged)
    assert _draft(cfg, "debug", refresh=True) == path
    data = yaml.safe_load(path.read_text())["skills"][LOGICAL]
    assert data["compared_with"] == "debug"
    assert data["traits"]["novel"]["reason"] == "kept"
    assert data["pairing"]["purpose"] == "kept too"
    assert data["traits"]["mocks"]["fact"] == "variant"

    _edit(path, lambda d: d.update(to_sha="other99"))
    with pytest.raises(SystemExit, match="not the report's to_sha"):
        _draft(cfg, refresh=True)


# --- check rules (Acceptance 19) -----------------------------------------------------


def test_pairing_flag_and_adopt_guide(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    cfg = _cfg(tmp_path)
    path = _draft(cfg)
    assert cli.cmd_build(cfg, _ns()) == 0
    assert cli.cmd_check(cfg, _ns()) == 0  # a fresh draft passes check
    _edit(path, _judge)

    def unflag(data: dict[str, Any]) -> None:
        data["skills"][LOGICAL]["pairing"]["flag"] = None

    _edit(path, unflag)
    errors = reports.seal(cfg, path)
    assert any("differ without pairing.flag" in e for e in errors)

    _edit(path, _judge)
    _edit(path, lambda d: d["skills"][LOGICAL]["traits"]["seams"].update(guide=None))
    errors = reports.seal(cfg, path)
    assert any("seams: an adopt row needs `guide`" in e for e in errors)
    assert cli.cmd_build(cfg, _ns()) == 0
    _fails(cfg, capsys, "seams: an adopt row needs `guide`")  # judged in a draft

    def bad(data: dict[str, Any]) -> None:
        rows = data["skills"][LOGICAL]["traits"]
        rows["seams"]["guide"] = {"verdict": "reword", "rules": ["Z-99"]}
        rows["novel"].update(recommendation="adopt", delivery="delivered")
        rows["novel"]["guide"] = {"verdict": "conflict", "rules": []}
        rows["red-green"]["ours"] = []

    _edit(path, bad)
    errors = "\n".join(reports.seal(cfg, path))
    for needle in (
        "guide rule Z-99 is not in GUIDE.md",
        "seams: a reword verdict is an adopt, pending",
        "seams: a reword verdict needs `rewording`",
        "novel: a conflict verdict is never an adopt",
        "novel: a delivered adopt needs fact present",
        "red-green: a present row cites `ours`",
    ):
        assert needle in errors
    assert not cfg.manifest_path.exists()  # nothing was sealed


def test_seal_needs_evidence(tmp_path: Path) -> None:
    # review 2 #13: new rows need the blind list, a full mapping into the
    # analysis's traits, and a purpose.
    cfg = _cfg(tmp_path)
    path = _draft(cfg)

    def gaps(data: dict[str, Any]) -> None:
        _judge(data)
        skill = data["skills"][LOGICAL]
        skill["pairing"]["purpose"] = None
        skill["analysis"] = {
            "blind": ["One.", "Two."],
            "mapping": [{"line": 1, "to": ["mocks-strict"], "mark": "match"}],
        }

    _edit(path, gaps)
    errors = "\n".join(reports.seal(cfg, path))
    for needle in (
        "pairing.purpose is empty",
        "blind line 2 is not mapped",
        "mapping line 1: mocks-strict is not a trait of the analysis",
    ):
        assert needle in errors, errors
    _edit(
        path,
        lambda d: d["skills"][LOGICAL].update(analysis={"blind": [], "mapping": []}),
    )
    errors = "\n".join(reports.seal(cfg, path))
    assert "new or changed rows need `analysis.blind` and `mapping`" in errors
    assert not cfg.manifest_path.exists()


# --- seal, immutability, currency (Acceptance 5) --------------------------------------


def test_seal_immutability_and_current_row(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    cfg = _cfg(tmp_path)
    path = _draft(cfg)
    _edit(path, _judge)
    _edit(path, lambda d: d["skills"][LOGICAL]["traits"].pop("novel"))
    assert cli.cmd_build(cfg, _ns()) == 0
    _fails(cfg, capsys, "both critics passed but it is not sealed")
    assert any(
        "in-scope trait novel (new) has no row" in e for e in reports.seal(cfg, path)
    )
    key = "registry/reviews/" + path.name
    # A draft never becomes current.
    ctx = reports.load_context(cfg)
    assert (
        reports.current_row(
            ctx.reports, ctx.sealed, "refrepo", LOGICAL, "seams", "abc1234"
        )
        is None
    )

    path.unlink()
    path = _sealed(cfg)
    manifest = json.loads(cfg.manifest_path.read_text())
    assert manifest["reports"] == {key: reports._sha256(path)}
    assert "2026-10-14-r.jsonl" not in manifest["rounds"]  # round still open
    assert cli.cmd_check(cfg, _ns()) == 0
    md = path.with_suffix(".md").read_text()
    assert "| debug | 3 |  |" in md and "- `mocks` (new): absent" in md
    with pytest.raises(SystemExit, match="sealed"):
        _draft(cfg, refresh=True)
    ctx = reports.load_context(cfg)
    assert (
        reports.current_row(
            ctx.reports, ctx.sealed, "refrepo", LOGICAL, "seams", "abc1234"
        )[0]
        == key
    )  # type: ignore[index]

    # A superseding sealed report becomes current.
    later = _draft(cfg, report_path=Path("registry/reviews/later.yaml"))
    _edit(later, _judge)
    _edit(later, lambda d: d.update(supersedes=[key]))
    assert reports.seal(cfg, later) == []
    assert cli.cmd_build(cfg, _ns()) == 0
    assert cli.cmd_check(cfg, _ns()) == 0
    ctx = reports.load_context(cfg)
    found = reports.current_row(
        ctx.reports, ctx.sealed, "refrepo", LOGICAL, "seams", "abc1234"
    )
    assert found is not None and found[0] == "registry/reviews/later.yaml"

    # Two unrelated sealed reports on one trait: seal refuses, check fails.
    third = _draft(cfg, report_path=Path("registry/reviews/third.yaml"))
    _edit(third, _judge)
    assert any("neither supersedes" in e for e in reports.seal(cfg, third))
    manifest = json.loads(cfg.manifest_path.read_text())
    manifest["reports"]["registry/reviews/third.yaml"] = reports._sha256(third)
    cfg.manifest_path.write_text(json.dumps(manifest))
    assert cli.cmd_build(cfg, _ns()) == 0
    _fails(cfg, capsys, "neither supersedes the other")
    with pytest.raises(ValueError, match="unrelated sealed reports"):
        reports.current_row(*_ctx_args(cfg), "refrepo", LOGICAL, "seams", "abc1234")
    third.unlink()
    third.with_suffix(".md").unlink()
    _fails(cfg, capsys, "third.yaml: sealed report has been DELETED")
    del manifest["reports"]["registry/reviews/third.yaml"]
    cfg.manifest_path.write_text(json.dumps(manifest))

    # Editing a sealed report fails check; a missing supersedes target fails.
    _edit(later, lambda d: d.update(supersedes=[key, "registry/reviews/gone.yaml"]))
    assert cli.cmd_build(cfg, _ns()) == 0
    _fails(cfg, capsys, "later.yaml: sealed report has been MODIFIED")
    _fails(cfg, capsys, "supersedes 'registry/reviews/gone.yaml', no such report")

    # Sealing a round keeps the sealed reports in the manifest.
    ledger.seal(cfg, "2026-10-14-r")
    assert set(json.loads(cfg.manifest_path.read_text())["reports"]) == {
        key,
        "registry/reviews/later.yaml",
    }


def test_current_row_is_transitive(tmp_path: Path) -> None:
    # review 2 #8: A <- B <- C where B does not cover `seams`: C is current.
    cfg = _cfg(tmp_path)
    a = "registry/reviews/" + _sealed(cfg).name
    base = reports.load_context(cfg).reports[a].model_dump()

    def report(supersedes: str, drop: bool) -> Report:
        data = json.loads(json.dumps(base))
        data["supersedes"] = [supersedes]
        if drop:
            data["skills"][LOGICAL]["traits"].pop("seams")
        return Report.model_validate(data)

    b, c = "registry/reviews/b.yaml", "registry/reviews/c.yaml"
    all_ = {a: reports.load_context(cfg).reports[a], b: report(a, True)}
    all_[c] = report(b, False)
    found = reports.current_row(all_, set(all_), "refrepo", LOGICAL, "seams", SHA)
    assert found is not None and found[0] == c


def test_seal_validates_supersedes(tmp_path: Path) -> None:
    # review 2 #7: seal refuses a missing, unsealed or self target.
    cfg = _cfg(tmp_path)
    draft = _draft(cfg, report_path=Path("registry/reviews/d.yaml"))
    path = _draft(cfg, report_path=Path("registry/reviews/s.yaml"))
    _edit(path, _judge)
    for target, needle in (
        (
            "registry/reviews/gone.yaml",
            "supersedes 'registry/reviews/gone.yaml', no such report",
        ),
        ("registry/reviews/d.yaml", "supersedes 'registry/reviews/d.yaml', not sealed"),
        ("registry/reviews/s.yaml", "supersedes itself"),
    ):
        _edit(path, lambda d, t=target: d.update(supersedes=[t]))
        assert any(needle in e for e in reports.seal(cfg, path)), target
    assert draft.is_file() and not cfg.manifest_path.exists()


def _ctx_args(cfg: Any) -> tuple[Any, Any]:
    ctx = reports.load_context(cfg)
    return ctx.reports, ctx.sealed


# --- scope (2.6) ------------------------------------------------------------------------


def test_scope(tmp_path: Path) -> None:
    # accepted + proposed: only `added` and `changed`.
    extra = '      added: {novel: "def5678"}\n      changed: {seams: "def5678"}\n'
    cfg = _cfg(
        tmp_path / "changed",
        accepted="abc1234",
        proposed="def5678",
        extra=extra,
        check=False,
    )
    rows = _rows(_draft(cfg, reconsider=["mocks"]))
    assert {t: r["scope"] for t, r in rows.items()} == {
        "seams": "changed",
        "mocks": "reconsider",
        "novel": "changed",
    }

    # A stale current row of an undecided trait is re-compared.
    cfg = _cfg(tmp_path / "stale")
    _sealed(cfg)
    entry = _entry("abc1234", None)
    text = (cfg.traits_dir / "refrepo.yaml").read_text()
    (cfg.traits_dir / "refrepo.yaml").write_text(text.split("refrepo:")[0] + entry)
    ours = (cfg.traits_dir / "ours.yaml").read_text()
    (cfg.traits_dir / "ours.yaml").write_text(
        ours.replace("[red-green, seams, mocks-strict]", "[red-green, mocks-strict]")
    )
    later = _draft(cfg, report_path=Path("registry/reviews/later.yaml"))
    assert {t: r["scope"] for t, r in _rows(later).items()} == {"seams": "recompare"}
    assert _rows(later)["seams"]["also_in"] == {}

    # A trait ruled at that sha is decided: no re-comparison.
    later.unlink()
    _write_round(
        cfg,
        "2026-10-15-r",
        _trait("2026-10-15-r:1", "defer", "seams"),
        trait_level=True,
    )
    assert _rows(_draft(cfg, report_path=Path("registry/reviews/later.yaml"))) == {}
