"""Tests for the skill + capability registry tool.

Each failure test starts from a passing baseline and then asserts the one
specific diagnostic the mutation should produce (so a test can never pass for an
unrelated reason). All state lives in a temporary directory; the real ledger is
never touched.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType

import pytest

HL = Path(__file__).resolve().parent.parent / "harness_lifecycle"


def _load_registry() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "registry", HL / "registry" / "registry.py"
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules["registry"] = module  # so pydantic can resolve the model's forward refs
    spec.loader.exec_module(module)
    return module


registry = _load_registry()
scan = registry.scan  # the scan module registry imported (for tree-hash helpers)


# --- helpers ------------------------------------------------------------------


def _make_cfg(tmp_path: Path) -> object:
    repo = tmp_path / "repo"
    reg = repo / "registry"
    (repo / ".claude" / "skills").mkdir(parents=True)
    (reg / "ledger").mkdir(parents=True)
    (reg / "skill-records").mkdir(parents=True)
    (reg / "references").mkdir(parents=True)
    (repo / "catalogs").mkdir(parents=True)
    return registry.RegistryConfig(
        repo_root=repo,
        registry_dir=reg,
        ledger_dir=reg / "ledger",
        manifest_path=reg / "ledger" / "MANIFEST.json",
        skill_records_dir=reg / "skill-records",
        references_dir=reg / "references",
        index_path=reg / "INDEX.md",
        trait_definitions_path=reg / "trait-definitions.yaml",
        traits_path=reg / "traits.yaml",
        traits_md_path=reg / "TRAITS.md",
        catalogs_dir=repo / "catalogs",
        skills_dir=repo / ".claude" / "skills",
        our_harness_root=repo / ".claude",
        codex_root=repo / ".codex",
        plugins_glob="plugins/*",
    )


def _write_skill(cfg: object, name: str, description: str = "A test skill.") -> None:
    skill_dir = cfg.skills_dir / name  # type: ignore[attr-defined]
    skill_dir.mkdir(parents=True, exist_ok=True)
    (skill_dir / "SKILL.md").write_text(
        f"---\nname: {name}\ndescription: {description}\n---\n# {name}\n",
        encoding="utf-8",
    )


def _write_record(
    cfg: object,
    skill: str,
    domain: str,
    stage: str,
    substage: str,
    aliases: list[str] | None = None,
) -> Path:
    aliases = aliases or []
    text = (
        f"---\nskill: {skill}\ndomain: {domain}\nstage: {stage}\nsubstage: {substage}\n"
        f"secondary: []\nfamily:\naliases: [{', '.join(aliases)}]\nstatus: active\n---\n"
        f"# {skill}\n\n## Capability\n\nseed.\n\n"
        f"{registry.LINEAGE_OPEN}\n{registry.LINEAGE_CLOSE}\n\n"
        f"{registry.HISTORY_OPEN}\n{registry.HISTORY_CLOSE}\n"
    )
    out = cfg.skill_records_dir / domain / f"{skill}.md"  # type: ignore[attr-defined]
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text, encoding="utf-8")
    return out


def _write_round(
    cfg: object,
    round_id: str,
    *events: dict,
    trait_level: bool = False,
    pins: dict[str, str] | None = None,
    date: str = "2026-10-14",
) -> Path:
    header: dict[str, object] = {
        "type": "round",
        "round_id": round_id,
        "date": date,
        "scope": "test",
    }
    if trait_level:
        header["trait_level"] = True
    if pins:
        header["pins"] = pins
    path = cfg.ledger_dir / f"{round_id}.jsonl"  # type: ignore[attr-defined]
    path.write_text(
        "\n".join([json.dumps(header)] + [json.dumps(e) for e in events]) + "\n",
        encoding="utf-8",
    )
    return path


def _ours_event(eid: str, kind: str, skill: str, **extra: object) -> dict:
    ev = {
        "type": "event",
        "id": eid,
        "date": "2026-10-14",
        "kind": kind,
        "subject": f"ours:{skill}",
        "why": "because",
        "evidence": ["x:1"],
        "skill": skill,
    }
    ev.update(extra)
    return ev


def _ref_event(
    eid: str,
    kind: str,
    repo: str,
    logical_id: str,
    content_hash: str = "h",
    **extra: object,
) -> dict:
    ev = {
        "type": "event",
        "id": eid,
        "date": "2026-10-14",
        "kind": kind,
        "subject": f"{repo}:{logical_id}",
        "why": "because",
        "evidence": ["x:1"],
        "source": {
            "repo": repo,
            "logical_id": logical_id,
            "content_hash": content_hash,
        },
    }
    ev.update(extra)
    return ev


def _cap(kind: str, name: str, logical_id: str, content_hash: str) -> dict:
    return {
        "kind": kind,
        "name": name,
        "category": "",
        "logical_id": logical_id,
        "canonical_path": f"{name}.md",
        "paths": [f"{name}.md"],
        "description": "d",
        "content_hash": content_hash,
        "signature_hash": "sig",
        "variant_hashes": [],
        "line_count": 1,
        "assets": [],
    }


def _catalog(cfg: object, repo: str, caps: list[dict]) -> None:
    data = {
        "schema": "harness-capability-catalog/v1",
        "repo": repo,
        "source": "working-tree",
        "source_commit": "deadbeef",
        "counts": {},
        "physical_scanned": len(caps),
        "excluded": 0,
        "capabilities": caps,
    }
    (cfg.catalogs_dir / f"{repo}.json").write_text(json.dumps(data), encoding="utf-8")  # type: ignore[attr-defined]


def _ns(**kw: object) -> argparse.Namespace:
    return argparse.Namespace(**kw)


def _rec_ns(**over: object) -> argparse.Namespace:
    base: dict[str, object] = {
        "id": None,
        "date": None,
        "kind": None,
        "subject": None,
        "why": None,
        "skill": None,
        "evidence": None,
        "json": None,
        "json_file": None,
        "stdin": False,
    }
    base.update(over)
    return argparse.Namespace(**base)


def _baseline(tmp_path: Path) -> object:
    """A registry that passes `check`."""
    cfg = _make_cfg(tmp_path)
    _write_skill(cfg, "planning")
    _write_record(cfg, "planning", "engineering", "Design", "Decomposition")
    _write_round(cfg, "2026-10-14-r", _ours_event("2026-10-14-r:1", "add", "planning"))
    assert registry.cmd_build(cfg, _ns()) == 0
    assert registry.cmd_check(cfg, _ns()) == 0
    return cfg


def _fails_with(cfg: object, capsys: pytest.CaptureFixture[str], needle: str) -> None:
    assert registry.cmd_check(cfg, _ns()) == 1
    assert needle in capsys.readouterr().err


# --- ours / template exclusion ------------------------------------------------


def test_ours_catalogs_our_skills(tmp_path: Path) -> None:
    cfg = _make_cfg(tmp_path)
    _write_skill(cfg, "planning")
    assert "skill:skills/planning" in registry.build_ours(cfg).by_logical_id()


def test_build_ours_excludes_plugin_template(tmp_path: Path) -> None:
    cfg = _make_cfg(tmp_path)
    plugin = cfg.repo_root / "plugins" / "p"  # type: ignore[attr-defined]
    (plugin / "skills" / "real").mkdir(parents=True)
    (plugin / "skills" / "real" / "SKILL.md").write_text(
        "---\nname: real\n---\n# real\n", encoding="utf-8"
    )
    (plugin / "template" / "skills" / "copy").mkdir(parents=True)
    (plugin / "template" / "skills" / "copy" / "SKILL.md").write_text(
        "---\nname: copy\n---\n# copy\n", encoding="utf-8"
    )
    ids = registry.build_ours(cfg).by_logical_id()
    assert "skill:skills/real" in ids
    assert not any("template/" in c.canonical_path for c in ids.values())


# --- round / record -----------------------------------------------------------


def test_round_record_seal_and_structured_json(tmp_path: Path) -> None:
    cfg = _make_cfg(tmp_path)
    assert (
        registry.cmd_round(
            cfg,
            _ns(
                round_command="open",
                slug="2026-10-14-x",
                date="2026-10-14",
                scope="s",
                json=None,
                json_file=None,
                stdin=False,
            ),
        )
        == 0
    )
    # record via structured JSON; id and date are auto-assigned
    payload = json.dumps(
        {
            "kind": "add",
            "subject": "ours:planning",
            "why": "new",
            "evidence": ["x:1"],
            "skill": "planning",
        }
    )
    assert registry.cmd_record(cfg, _rec_ns(json=payload)) == 0
    _, events, errors = registry.load_ledger(cfg)
    assert not errors and len(events) == 1
    assert events[0].id == "2026-10-14-x:001" and events[0].date  # auto id + date
    registry.seal(cfg, "2026-10-14-x")
    assert registry.open_round(cfg) is None


def test_round_open_prefixes_date_without_doubling(tmp_path: Path) -> None:
    cfg = _make_cfg(tmp_path)
    # a bare slug gets <date>- prepended (cr-alnr)
    assert (
        registry.cmd_round(
            cfg,
            _ns(
                round_command="open",
                slug="agent-skills",
                date="2026-10-14",
                scope="s",
                json=None,
                json_file=None,
                stdin=False,
            ),
        )
        == 0
    )
    path = cfg.ledger_dir / "2026-10-14-agent-skills.jsonl"  # type: ignore[attr-defined]
    assert path.exists()
    assert json.loads(path.read_text().splitlines()[0])["round_id"] == (
        "2026-10-14-agent-skills"
    )
    registry.seal(cfg, "2026-10-14-agent-skills")
    # a slug that already carries a date prefix is left alone (no doubling)
    assert (
        registry.cmd_round(
            cfg,
            _ns(
                round_command="open",
                slug="2026-10-14-other",
                date="2026-10-14",
                scope="s",
                json=None,
                json_file=None,
                stdin=False,
            ),
        )
        == 0
    )
    assert (cfg.ledger_dir / "2026-10-14-other.jsonl").exists()  # type: ignore[attr-defined]
    assert not (
        cfg.ledger_dir / "2026-10-14-2026-10-14-other.jsonl"  # type: ignore[attr-defined]
    ).exists()


def test_reviews_block_renders_both_citation_forms_and_empty(tmp_path: Path) -> None:
    cfg = _make_cfg(tmp_path)
    _write_skill(cfg, "planning")
    _write_record(cfg, "planning", "engineering", "Design", "Decomposition")
    _write_skill(cfg, "foo")
    _write_record(cfg, "foo", "engineering", "Building", "Diagnosis")
    _write_round(
        cfg,
        "2026-10-14-r",
        _ours_event(
            "2026-10-14-r:1",
            "add",
            "planning",
            evidence=[
                "harness_lifecycle/registry/reviews/2026-10-14-upstream-x-1.0.md"
            ],
        ),
        _ours_event(
            "2026-10-14-r:2",
            "update",
            "planning",
            why="rebuilt per skill-comparisons/debugging-loop/ analysis",
        ),
        _ours_event("2026-10-14-r:3", "add", "foo"),
    )
    assert registry.cmd_build(cfg, _ns()) == 0
    planning = (
        cfg.skill_records_dir / "engineering" / "planning.md"  # type: ignore[attr-defined]
    ).read_text()
    assert registry.REVIEWS_OPEN in planning and registry.REVIEWS_CLOSE in planning
    # review-file citation (prefix stripped) links into reviews/
    assert (
        "[2026-10-14-upstream-x-1.0.md](../../reviews/2026-10-14-upstream-x-1.0.md)"
        in planning
    )
    # old-prose comparison links into the archived folder
    assert (
        "[skill-comparisons/debugging-loop]"
        "(../../../archive/skill-comparisons/debugging-loop/)"
    ) in planning
    # a skill whose events cite no review gets the empty sentinel
    foo = (
        cfg.skill_records_dir / "engineering" / "foo.md"  # type: ignore[attr-defined]
    ).read_text()
    assert "None yet." in foo.split(registry.REVIEWS_OPEN)[1]


def test_record_autofills_reference_source(tmp_path: Path) -> None:
    cfg = _make_cfg(tmp_path)
    _catalog(cfg, "refrepo", [_cap("skill", "foo", "skill:skills/foo", "hcur")])
    registry.cmd_round(
        cfg,
        _ns(
            round_command="open",
            slug="2026-10-14-x",
            date="2026-10-14",
            scope="s",
            json=None,
            json_file=None,
            stdin=False,
        ),
    )
    assert (
        registry.cmd_record(
            cfg,
            _rec_ns(
                kind="reject", subject="refrepo:skill:skills/foo", why="no", skill=None
            ),
        )
        == 0
    )
    _, events, _ = registry.load_ledger(cfg)
    assert events[0].source is not None
    assert events[0].source.content_hash == "hcur"  # auto-filled from the catalog

    # completing a pending adopt copies the pending source, not the catalog (r1 #4)
    trait = "refrepo:skill:skills/foo#seams"
    old = {"repo": "refrepo", "logical_id": "skill:skills/foo", "sha": "old1234"}
    for extra in ({"pending": "cr-1", "source": old}, {}):
        payload = {"kind": "adopt", "subject": trait, "why": "w", "skill": "foo"}
        assert registry.cmd_record(cfg, _rec_ns(json=json.dumps(payload | extra))) == 0
    _, events, _ = registry.load_ledger(cfg)
    assert events[-1].source == events[-2].source


# --- check: baseline + one specific diagnostic each ---------------------------


def test_check_baseline_passes(tmp_path: Path) -> None:
    _baseline(tmp_path)  # asserts cmd_check == 0 internally


def test_check_rejects_duplicate_id(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    cfg = _baseline(tmp_path)
    _write_round(
        cfg,
        "2026-10-14-r",
        _ours_event("2026-10-14-r:1", "add", "planning"),
        _ours_event("2026-10-14-r:1", "add", "planning"),
    )
    registry.cmd_build(cfg, _ns())
    _fails_with(cfg, capsys, "duplicate event id")


def test_check_rejects_dangling_supersedes(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    cfg = _baseline(tmp_path)
    _write_round(
        cfg,
        "2026-10-14-r",
        _ours_event("2026-10-14-r:1", "add", "planning", supersedes=["ghost:9"]),
    )
    registry.cmd_build(cfg, _ns())
    _fails_with(cfg, capsys, "supersedes unknown event")


def test_check_rejects_bad_schema(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    cfg = _baseline(tmp_path)
    _write_round(
        cfg,
        "2026-10-14-r",
        {
            "type": "event",
            "id": "2026-10-14-r:1",
            "kind": "nonsense",
            "subject": "ours:planning",
            "date": "2026-10-14",
            "why": "x",
        },
    )
    _fails_with(cfg, capsys, "schema error")


def test_check_rejects_non_iso_date(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    cfg = _baseline(tmp_path)
    _write_round(
        cfg,
        "2026-10-14-r",
        _ours_event("2026-10-14-r:1", "add", "planning", date="last tuesday"),
    )
    _fails_with(cfg, capsys, "ISO 8601")


def test_check_rejects_adopt_without_source(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    cfg = _baseline(tmp_path)
    _write_round(
        cfg,
        "2026-10-14-r",
        {
            "type": "event",
            "id": "2026-10-14-r:1",
            "kind": "adopt",
            "subject": "refrepo:skill:skills/x",
            "date": "2026-10-14",
            "why": "y",
            "skill": "planning",
        },
    )
    _fails_with(cfg, capsys, "needs `source`")


def test_check_rejects_adopt_merged_without_adaptation(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    cfg = _baseline(tmp_path)
    _write_round(
        cfg,
        "2026-10-14-r",
        _ref_event(
            "2026-10-14-r:1",
            "adopt-merged",
            "refrepo",
            "skill:skills/x",
            skill="planning",
        ),
    )
    _fails_with(cfg, capsys, "needs `adaptation`")


def test_check_rejects_effective_adoption_without_skill(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    cfg = _baseline(tmp_path)
    _write_round(
        cfg,
        "2026-10-14-r",
        _ref_event("2026-10-14-r:1", "adopt", "refrepo", "skill:skills/x"),
    )
    registry.cmd_build(cfg, _ns())
    _fails_with(cfg, capsys, "invalid skill target")


def test_check_rejects_superseded_reject_then_adopt_with_bad_target(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A later adopt that overrides an earlier drop still needs a valid target;
    the old 'contested subject' tolerance no longer silently passes it."""
    cfg = _baseline(tmp_path)
    _write_round(
        cfg,
        "2026-10-14-r",
        _ref_event("2026-10-14-r:1", "reject", "refrepo", "skill:skills/x"),
        _ref_event(
            "2026-10-14-r:2",
            "adopt",
            "refrepo",
            "skill:skills/x",
            skill="ghost-skill",
            supersedes=["2026-10-14-r:1"],
        ),
    )
    registry.cmd_build(cfg, _ns())
    _fails_with(cfg, capsys, "invalid skill target")


def test_target_exists_accepts_only_real_kinds_and_shipped_caps(
    tmp_path: Path,
) -> None:
    cfg = _baseline(tmp_path)
    ours = registry.build_ours(cfg)
    existing = {"planning"}
    assert registry._target_exists("planning", existing, ours)
    assert registry._target_exists("skill:skills/planning", existing, ours) is False
    assert registry._target_exists("skill:never-existed", existing, ours) is False
    assert registry._target_exists("oops:", existing, ours) is False
    assert registry._target_exists("ghost", existing, ours) is False
    assert registry._target_exists("agent:code-reviewer", existing, ours) is False
    # A real non-skill capability resolves by (kind, name-leaf).
    (cfg.our_harness_root / "agents").mkdir(parents=True, exist_ok=True)  # type: ignore[attr-defined]
    (cfg.our_harness_root / "agents" / "code-reviewer.md").write_text(  # type: ignore[attr-defined]
        "---\nname: code-reviewer\ndescription: Reviews code.\n---\nBody.\n",
        encoding="utf-8",
    )
    ours2 = registry.build_ours(cfg)
    assert registry._target_exists("agent:code-reviewer", existing, ours2)
    assert registry._target_exists("agent:agents/code-reviewer", existing, ours2)
    # A fabricated namespace must not resolve via leaf-name matching.
    assert (
        registry._target_exists(
            "agent:does-not-exist/agents/code-reviewer", existing, ours2
        )
        is False
    )
    # doc: targets must stay inside repo_root (review #15).
    (cfg.repo_root / "docs").mkdir(parents=True, exist_ok=True)  # type: ignore[attr-defined]
    (cfg.repo_root / "docs" / "method.md").write_text("x", encoding="utf-8")  # type: ignore[attr-defined]
    assert registry._target_exists("doc:docs/method.md", existing, ours2, cfg)
    assert registry._target_exists("doc:/etc/passwd", existing, ours2, cfg) is False
    assert registry._target_exists("doc:../escape.md", existing, ours2, cfg) is False
    assert registry._target_exists("doc:docs/missing.md", existing, ours2, cfg) is False


def test_check_rejects_cross_subject_supersede(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    cfg = _baseline(tmp_path)
    _write_round(
        cfg,
        "2026-10-14-r",
        _ours_event("2026-10-14-r:1", "add", "alpha"),
        _ours_event("2026-10-14-r:2", "add", "beta", supersedes=["2026-10-14-r:1"]),
    )
    registry.cmd_build(cfg, _ns())
    _fails_with(cfg, capsys, "across subjects")


def test_check_rejects_supersession_cycle(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    cfg = _baseline(tmp_path)
    _write_round(
        cfg,
        "2026-10-14-r",
        _ours_event("2026-10-14-r:1", "add", "planning", supersedes=["2026-10-14-r:2"]),
        _ours_event("2026-10-14-r:2", "add", "planning", supersedes=["2026-10-14-r:1"]),
    )
    registry.cmd_build(cfg, _ns())
    _fails_with(cfg, capsys, "cyclic")


def test_check_rejects_cycle_on_non_first_edge(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    # A -> [leaf, B], B -> [leaf, A]; the cycle is on the second edge, which a
    # supersedes[0]-only traversal would miss.
    cfg = _baseline(tmp_path)
    _write_round(
        cfg,
        "2026-10-14-r",
        _ours_event("2026-10-14-r:3", "add", "planning"),
        _ours_event(
            "2026-10-14-r:1",
            "add",
            "planning",
            supersedes=["2026-10-14-r:3", "2026-10-14-r:2"],
        ),
        _ours_event(
            "2026-10-14-r:2",
            "add",
            "planning",
            supersedes=["2026-10-14-r:3", "2026-10-14-r:1"],
        ),
    )
    registry.cmd_build(cfg, _ns())
    _fails_with(cfg, capsys, "cyclic")


def test_check_rejects_blank_line_and_header_not_first(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    cfg = _baseline(tmp_path)
    path = cfg.ledger_dir / "2026-10-14-r.jsonl"  # type: ignore[attr-defined]
    path.write_text("\n" + path.read_text(), encoding="utf-8")  # leading blank line
    # a leading blank line both trips the no-blank-lines rule and pushes the header off line 1
    _fails_with(cfg, capsys, "blank line")


def test_check_rejects_header_not_physical_first(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    cfg = _baseline(tmp_path)
    path = cfg.ledger_dir / "2026-10-14-r.jsonl"  # type: ignore[attr-defined]
    lines = path.read_text().splitlines()
    path.write_text(
        "\n".join(lines[1:] + lines[:1]) + "\n", encoding="utf-8"
    )  # event first
    _fails_with(cfg, capsys, "physical first line must be a round header")


def test_record_rejects_foreign_id(tmp_path: Path) -> None:
    cfg = _make_cfg(tmp_path)
    registry.cmd_round(
        cfg,
        _ns(
            round_command="open",
            slug="2026-10-14-x",
            date="2026-10-14",
            scope="s",
            json=None,
            json_file=None,
            stdin=False,
        ),
    )
    with pytest.raises(SystemExit, match="does not belong"):
        registry.cmd_record(
            cfg,
            _rec_ns(
                id="wrong:1",
                kind="add",
                subject="ours:planning",
                why="w",
                skill="planning",
            ),
        )


def test_merge_contract(tmp_path: Path) -> None:
    # merge: subject names the old skill, skill names the survivor — a valid pair
    ok = {
        "type": "event",
        "id": "r:1",
        "date": "2026-10-14",
        "kind": "merge",
        "subject": "ours:old",
        "why": "folded in",
        "evidence": ["x:1"],
        "skill": "survivor",
    }
    assert registry.Event.model_validate(ok).skill == "survivor"
    with pytest.raises(ValueError, match="same"):
        registry.Event.model_validate({**ok, "subject": "ours:survivor"})
    with pytest.raises(ValueError, match="subject must be ours:"):
        registry.Event.model_validate({**ok, "kind": "add", "subject": "ours:other"})


def test_check_rejects_foreign_event_id(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    cfg = _baseline(tmp_path)
    _write_round(cfg, "2026-10-14-r", _ours_event("other-round:1", "add", "planning"))
    registry.cmd_build(cfg, _ns())
    _fails_with(cfg, capsys, "does not belong")


def test_check_rejects_edited_sealed_round(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    cfg = _baseline(tmp_path)
    registry.seal(cfg, "2026-10-14-r")
    path = cfg.ledger_dir / "2026-10-14-r.jsonl"  # type: ignore[attr-defined]
    path.write_text(path.read_text() + " \n", encoding="utf-8")
    _fails_with(cfg, capsys, "MODIFIED")


def test_seal_refuses_to_reseal_changed_round(tmp_path: Path) -> None:
    cfg = _baseline(tmp_path)
    registry.seal(cfg, "2026-10-14-r")
    path = cfg.ledger_dir / "2026-10-14-r.jsonl"  # type: ignore[attr-defined]
    path.write_text(path.read_text() + " \n", encoding="utf-8")
    with pytest.raises(SystemExit, match="refusing to re-seal"):
        registry.seal(cfg, "2026-10-14-r")


def test_more_than_one_open_round(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    cfg = _baseline(tmp_path)
    _write_round(cfg, "2026-10-14-s", _ours_event("2026-10-14-s:1", "add", "planning"))
    registry.cmd_build(cfg, _ns())
    _fails_with(cfg, capsys, "more than one open round")
    with pytest.raises(SystemExit, match="more than one open round"):
        registry.open_round(cfg)


def test_check_rejects_uncovered_skill_dir(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    cfg = _baseline(tmp_path)
    _write_skill(cfg, "orphan")
    _fails_with(cfg, capsys, "no record, and not an alias")


def test_check_accepts_alias_stub_and_in_progress(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    cfg = _baseline(tmp_path)
    _write_skill(cfg, "document-review")  # alias of review
    _write_skill(cfg, "cost-estimate")  # stub
    _write_skill(cfg, registry.IN_PROGRESS_DIR)
    _write_skill(cfg, "review")
    _write_record(
        cfg, "review", "core", "Verification", "Review", aliases=["document-review"]
    )
    assert registry.cmd_build(cfg, _ns()) == 0
    assert registry.cmd_check(cfg, _ns()) == 0
    # lazy records without a traits.yaml entry are reported as a count
    assert "without a traits.yaml entry" in capsys.readouterr().out


def test_check_rejects_duplicate_record(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    cfg = _baseline(tmp_path)
    # a second record for the same skill under a different (wrong) domain folder
    _write_record(cfg, "planning", "core", "Design", "Decomposition")
    registry.cmd_build(cfg, _ns())
    _fails_with(cfg, capsys, "duplicate skill record")


def test_check_rejects_record_path_mismatch(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    cfg = _make_cfg(tmp_path)
    _write_skill(cfg, "planning")
    # frontmatter says engineering, file lives under core/
    _write_record(cfg, "planning", "engineering", "Design", "Decomposition")
    wrong = cfg.skill_records_dir / "core" / "planning.md"  # type: ignore[attr-defined]
    wrong.parent.mkdir(parents=True)
    wrong.write_text(
        (cfg.skill_records_dir / "engineering" / "planning.md").read_text()
    )  # type: ignore[attr-defined]
    (cfg.skill_records_dir / "engineering" / "planning.md").unlink()  # type: ignore[attr-defined]
    _write_round(cfg, "2026-10-14-r", _ours_event("2026-10-14-r:1", "add", "planning"))
    _fails_with(cfg, capsys, "record path must be")


def test_check_rejects_bad_substage(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    cfg = _make_cfg(tmp_path)
    _write_skill(cfg, "planning")
    _write_record(cfg, "planning", "engineering", "Design", "NotAStage")
    _write_round(cfg, "2026-10-14-r", _ours_event("2026-10-14-r:1", "add", "planning"))
    _fails_with(cfg, capsys, "not a sub-stage")


def test_check_detects_stale_generated(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    cfg = _baseline(tmp_path)
    cfg.index_path.write_text("tampered\n", encoding="utf-8")  # type: ignore[attr-defined]
    _fails_with(cfg, capsys, "stale")


# --- gap / reference classification share one function ------------------------


def test_gap_and_reference_classify_identically(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    cfg = _make_cfg(tmp_path)
    _write_skill(cfg, "foo")  # ours has skill:skills/foo
    # baz carries a tree_hash that differs from its ruling's — the §4 cascade
    # (no content_hash fallback, review #1) flags it changed through tree_hash.
    baz = {**_cap("skill", "baz", "skill:skills/baz", "hnow"), "tree_hash": "tnew"}
    _catalog(
        cfg,
        "refrepo",
        [
            _cap("skill", "foo", "skill:skills/foo", "hnow"),  # present, unruled
            _cap("skill", "bar", "skill:skills/bar", "hnow"),  # not reviewed
            baz,  # ruled, tree hash changed
        ],
    )
    baz_event = _ref_event(
        "2026-10-14-r:1", "adopt", "refrepo", "skill:skills/baz", skill="foo"
    )
    baz_event["source"]["tree_hash"] = "told"  # type: ignore[index]
    _write_round(cfg, "2026-10-14-r", baz_event)
    # gap
    assert registry.cmd_gap(cfg, _ns(reference="refrepo", kind=None, beads=False)) == 0
    out = capsys.readouterr().out
    assert "not reviewed" in out and "skill:skills/bar" in out
    assert "present, unruled" in out and "skill:skills/foo" in out
    assert "changed since ruled" in out and "skill:skills/baz" in out
    # reference page shares the same classification, so statuses match
    assert registry.cmd_build(cfg, _ns()) == 0
    ref = (cfg.references_dir / "refrepo.md").read_text()  # type: ignore[attr-defined]
    assert "| `skill:skills/foo` | present, unruled |" in ref
    assert "| `skill:skills/bar` | not reviewed |" in ref
    assert "| `skill:skills/baz` | adopt |" in ref


def test_gap_truncates_long_descriptions(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    cfg = _make_cfg(tmp_path)
    long_desc = "x" * 400
    _catalog(
        cfg,
        "refrepo",
        [{**_cap("skill", "bar", "skill:skills/bar", "h"), "description": long_desc}],
    )
    assert registry.cmd_gap(cfg, _ns(reference="refrepo", kind=None, beads=False)) == 0
    line = next(
        ln for ln in capsys.readouterr().out.splitlines() if "skill:skills/bar" in ln
    )
    assert "…" in line and len(line) < 160


# --- traits (traits-design.md Acceptance 1-11) --------------------------------

SUBJECT = "refrepo:skill:skills/engineering/tdd"
LOGICAL = "skill:skills/engineering/tdd"
TREE = "treehashT"

_PLACEMENT = "{domain: engineering, stage: Design, substage: Specification}"


def _tree_hash_of(cfg: object, skill: str) -> str:
    return registry._our_tree_hashes(registry.build_ours(cfg))[skill]


def _write_defs(cfg: object, text: str) -> None:
    cfg.trait_definitions_path.write_text(text, encoding="utf-8")  # type: ignore[attr-defined]


def _write_traits(cfg: object, text: str) -> None:
    cfg.traits_path.write_text(text, encoding="utf-8")  # type: ignore[attr-defined]


def _defs(*traits: str) -> str:
    """A trait-definitions.yaml with one simple placement per trait id."""
    out = []
    for t in traits:
        out.append(f"{t}:\n  definition: Does {t}.\n  placement: {_PLACEMENT}\n")
    return "".join(out)


def _ours_entry(skill: str, tree_hash: str, traits: list[str]) -> str:
    return (
        f'ours:{skill}:\n  tree_hash: "{tree_hash}"\n  traits: [{", ".join(traits)}]\n'
    )


def _upstream_entry(
    subject: str,
    traits: list[str],
    tree_hash: str = TREE,
    reviewed_sha: str = "abc1234",
) -> str:
    return (
        f'{subject}:\n  reviewed_sha: "{reviewed_sha}"\n  tree_hash: "{tree_hash}"\n'
        f"  placement: {_PLACEMENT}\n  traits: [{', '.join(traits)}]\n"
    )


def _checkpoint(
    eid: str, kind: str, skill: str, tree_hash: str = TREE, **extra: object
) -> dict:
    ev = {
        "type": "event",
        "id": eid,
        "date": "2026-10-14",
        "kind": kind,
        "subject": SUBJECT,
        "why": "because",
        "evidence": ["x:1"],
        "skill": skill,
        "source": {
            "repo": "refrepo",
            "logical_id": LOGICAL,
            "content_hash": "h",
            "tree_hash": tree_hash,
            "sha": "abc1234",
        },
    }
    ev.update(extra)
    return ev


def _trait(eid: str, kind: str, slug: str, **extra: object) -> dict:
    ev = {
        "type": "event",
        "id": eid,
        "date": "2026-10-14",
        "kind": kind,
        "subject": f"{SUBJECT}#{slug}",
        "why": "because",
        "evidence": ["x:1"],
        "source": {
            "repo": "refrepo",
            "logical_id": LOGICAL,
            "content_hash": "h",
            "tree_hash": TREE,
            "sha": "abc1234",
        },
    }
    ev.update(extra)
    return ev


def _trait_cfg(base: Path) -> object:
    """A passing trait-level registry: one checkpoint, one adopted trait."""
    cfg = _make_cfg(base)
    _write_skill(cfg, "tdd")
    _write_record(cfg, "tdd", "engineering", "Design", "Specification")
    th = _tree_hash_of(cfg, "tdd")
    _write_defs(cfg, _defs("seams"))
    _write_traits(
        cfg, _ours_entry("tdd", th, ["seams"]) + _upstream_entry(SUBJECT, ["seams"])
    )
    _write_round(
        cfg,
        "2026-10-14-r",
        _checkpoint("2026-10-14-r:1", "adopt", "tdd"),
        _trait("2026-10-14-r:2", "adopt", "seams", skill="tdd"),
        trait_level=True,
    )
    return cfg


def test_trait_baseline_passes(tmp_path: Path) -> None:
    cfg = _trait_cfg(tmp_path)
    assert registry.cmd_build(cfg, _ns()) == 0
    assert registry.cmd_check(cfg, _ns()) == 0


# Acceptance 1: strict parsing of the two YAML files.
def test_strict_yaml_parsing_failures(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    # (a) duplicate YAML key
    a = _trait_cfg(tmp_path / "a")
    _write_defs(
        a, _defs("seams") + f"seams:\n  definition: dup.\n  placement: {_PLACEMENT}\n"
    )
    _fails_with(a, capsys, "duplicate key")

    # (b) unknown field
    b = _trait_cfg(tmp_path / "b")
    _write_defs(
        b,
        f"seams:\n  definition: x.\n  placement: {_PLACEMENT}\n  bogus: 1\n",
    )
    _fails_with(b, capsys, "seams")

    # (c) an unquoted all-digit sha reads as an int and fails strict parsing
    c = _trait_cfg(tmp_path / "c")
    th = _tree_hash_of(c, "tdd")
    _write_traits(
        c,
        _ours_entry("tdd", th, ["seams"])
        + f'{SUBJECT}:\n  reviewed_sha: 123456\n  tree_hash: "{TREE}"\n'
        f"  placement: {_PLACEMENT}\n  traits: [seams]\n",
    )
    _fails_with(c, capsys, SUBJECT)

    # (d) an undefined trait id
    d = _trait_cfg(tmp_path / "d")
    _write_defs(d, _defs("seams"))
    th = _tree_hash_of(d, "tdd")
    _write_traits(
        d,
        _ours_entry("tdd", th, ["seams", "ghost"])
        + _upstream_entry(SUBJECT, ["seams"]),
    )
    _fails_with(d, capsys, "trait 'ghost' is undefined")

    # (e) a repeated id in one skill
    e = _trait_cfg(tmp_path / "e")
    th = _tree_hash_of(e, "tdd")
    _write_traits(
        e,
        _ours_entry("tdd", th, ["seams", "seams"])
        + _upstream_entry(SUBJECT, ["seams"]),
    )
    _fails_with(e, capsys, "listed twice")

    # (f) distinct_from without a note
    f = _trait_cfg(tmp_path / "f")
    _write_defs(
        f,
        f"seams:\n  definition: x.\n  placement: {_PLACEMENT}\n"
        f"  distinct_from: [other]\n"
        f"other:\n  definition: y.\n  placement: {_PLACEMENT}\n",
    )
    _fails_with(f, capsys, "seams")

    # (g) review r1 #5: non-kebab IDs, YAML-typed keys and unknown coordinates
    bad = [
        (f"Bad_ID:\n  definition: x.\n  placement: {_PLACEMENT}\n", "kebab-case"),
        (f"no:\n  definition: x.\n  placement: {_PLACEMENT}\n", "False"),
        (
            (
                "seams:\n  definition: x.\n"
                "  placement: {domain: core, stage: Nowhere, substage: Implementation}\n"
            ),
            "unknown stage",
        ),
        (
            (
                "seams:\n  definition: x.\n"
                "  placement: {domain: core, stage: Design, substage: Diagnosis}\n"
            ),
            "not a sub-stage of Design",
        ),
        (
            (
                f"seams:\n  definition: x.\n  placement: {_PLACEMENT}\n"
                "  secondary: [Nowhere]\n"
            ),
            "is not a sub-stage",
        ),
    ]
    for i, (text, needle) in enumerate(bad):
        g = _trait_cfg(tmp_path / f"g{i}")
        _write_defs(g, _defs("seams") + text if "seams:" not in text else text)
        _fails_with(g, capsys, needle)


# Acceptance 2: a stale ours tree_hash fails check.
def test_stale_ours_tree_hash_fails(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    cfg = _trait_cfg(tmp_path)
    _write_traits(
        cfg,
        _ours_entry("tdd", "STALEHASH", ["seams"])
        + _upstream_entry(SUBJECT, ["seams"]),
    )
    _fails_with(cfg, capsys, "tree_hash is stale")


# Acceptance 3: trait-level round completeness and coverage.
def test_trait_level_round_failures(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    # (a) an unruled trait, under an adopt checkpoint
    a = _trait_cfg(tmp_path / "a")
    th = _tree_hash_of(a, "tdd")
    _write_traits(
        a,
        _ours_entry("tdd", th, ["seams"])
        + _upstream_entry(SUBJECT, ["seams", "extra"]),
    )
    _write_defs(a, _defs("seams", "extra"))
    _fails_with(a, capsys, "has no effective ruling")

    # (b) an unruled trait under a REJECT checkpoint too (review #8)
    b = _make_cfg(tmp_path / "b")
    _write_skill(b, "tdd")
    _write_record(b, "tdd", "engineering", "Design", "Specification")
    _write_defs(b, _defs("seams", "extra"))
    _write_traits(b, _upstream_entry(SUBJECT, ["seams", "extra"]))
    _write_round(
        b,
        "2026-10-14-r",
        _checkpoint("2026-10-14-r:1", "reject", "tdd"),
        _trait("2026-10-14-r:2", "reject", "seams"),
        trait_level=True,
    )
    _fails_with(b, capsys, "has no effective ruling")

    # (c) a reject checkpoint whose entry tree_hash differs from the checkpoint's
    c = _make_cfg(tmp_path / "c")
    _write_skill(c, "tdd")
    _write_record(c, "tdd", "engineering", "Design", "Specification")
    _write_defs(c, _defs("seams"))
    _write_traits(c, _upstream_entry(SUBJECT, ["seams"], tree_hash="DIFFERENT"))
    _write_round(
        c,
        "2026-10-14-r",
        _checkpoint("2026-10-14-r:1", "reject", "tdd"),
        _trait("2026-10-14-r:2", "reject", "seams"),
        trait_level=True,
    )
    _fails_with(c, capsys, "tree_hash disagrees with the checkpoint")

    # (d) an adopt into a skill that lacks the trait fails without pending …
    d = _make_cfg(tmp_path / "d")
    _write_skill(d, "tdd")
    _write_record(d, "tdd", "engineering", "Design", "Specification")
    th = _tree_hash_of(d, "tdd")
    _write_defs(d, _defs("seams"))
    _write_traits(d, _ours_entry("tdd", th, []) + _upstream_entry(SUBJECT, ["seams"]))
    _write_round(
        d,
        "2026-10-14-r",
        _checkpoint("2026-10-14-r:1", "adopt", "tdd"),
        _trait("2026-10-14-r:2", "adopt", "seams", skill="tdd"),
        trait_level=True,
    )
    _fails_with(d, capsys, "is not listed by skill 'tdd'")

    # … and passes with pending (intent, not delivery; no membership obligation)
    dp = _make_cfg(tmp_path / "dp")
    _write_skill(dp, "tdd")
    _write_record(dp, "tdd", "engineering", "Design", "Specification")
    th = _tree_hash_of(dp, "tdd")
    _write_defs(dp, _defs("seams"))
    _write_traits(dp, _ours_entry("tdd", th, []) + _upstream_entry(SUBJECT, ["seams"]))
    _write_round(
        dp,
        "2026-10-14-r",
        _checkpoint("2026-10-14-r:1", "adopt", "tdd"),
        _trait("2026-10-14-r:2", "adopt", "seams", skill="tdd", pending="cr-1"),
        trait_level=True,
    )
    assert registry.cmd_build(dp, _ns()) == 0
    assert registry.cmd_check(dp, _ns()) == 0

    # (e) a trait-level checkpoint whose entry reviewed_sha differs
    e = _trait_cfg(tmp_path / "e")
    th = _tree_hash_of(e, "tdd")
    _write_traits(
        e,
        _ours_entry("tdd", th, ["seams"])
        + _upstream_entry(SUBJECT, ["seams"], reviewed_sha="fff9999"),
    )
    _fails_with(e, capsys, "reviewed_sha disagrees with the checkpoint")

    # (f) review r1 #2: trait rulings without any capability checkpoint
    f = _make_cfg(tmp_path / "f")
    _write_skill(f, "tdd")
    _write_record(f, "tdd", "engineering", "Design", "Specification")
    _write_defs(f, _defs("seams", "extra"))
    _write_traits(
        f,
        _ours_entry("tdd", _tree_hash_of(f, "tdd"), ["seams"])
        + _upstream_entry(SUBJECT, ["seams", "extra"]),
    )
    _write_round(
        f,
        "2026-10-14-r",
        _trait("2026-10-14-r:1", "adopt", "seams", skill="tdd"),
        trait_level=True,
    )
    _fails_with(f, capsys, "have no effective capability checkpoint")

    # (g) review r1 #8: a trait adopt into a non-skill capability
    g = _trait_cfg(tmp_path / "g")
    _write_round(
        g,
        "2026-10-14-r",
        _checkpoint("2026-10-14-r:1", "adopt", "agent:reviewer"),
        _trait("2026-10-14-r:2", "adopt", "seams", skill="agent:reviewer"),
        trait_level=True,
    )
    _fails_with(g, capsys, "a trait lands in a skill or a `doc:` file")


def test_awaiting_trait_ruling(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Only a pre-trait round's checkpoint is grandfathered; every later one is
    judged by the trait-level predicate (§5, review r1 #3)."""

    def cfg_at(base: Path, round_id: str, sha: str, *traits: dict) -> object:
        cfg = _make_cfg(base)
        _write_skill(cfg, "tdd")
        _write_record(cfg, "tdd", "engineering", "Design", "Specification")
        _write_defs(cfg, _defs("seams"))
        _write_traits(cfg, _upstream_entry(SUBJECT, ["seams"], reviewed_sha=sha))
        _catalog(cfg, "refrepo", [_cap("skill", "tdd", LOGICAL, "h")])
        _write_round(
            cfg, round_id, _checkpoint(f"{round_id}:1", "reject", "tdd"), *traits
        )
        return cfg

    old = cfg_at(tmp_path / "old", "2026-10-14-migration", "5beb35b")
    assert registry.cmd_build(old, _ns()) == 0
    assert registry.cmd_check(old, _ns()) == 0
    capsys.readouterr()
    assert registry.cmd_gap(old, _ns(reference="refrepo", kind=None, beads=False)) == 0
    out = capsys.readouterr().out
    assert "awaiting trait ruling (1)" in out
    assert (
        f"{LOGICAL}  (checkpoint 2026-10-14-migration:1, traits listed at 5beb35b)"
        in out
    )

    # a newer whole-skill ruling over an older inventory is not grandfathered
    newer = cfg_at(tmp_path / "newer", "2026-10-20-later", "5beb35b")
    _fails_with(newer, capsys, "reviewed_sha disagrees with the checkpoint")

    # trait-level through its trait rulings, at the entry's sha, without the flag
    ruled = cfg_at(
        tmp_path / "ruled",
        "2026-10-20-later",
        "abc1234",
        _trait("2026-10-20-later:2", "reject", "seams"),
    )
    assert registry.cmd_build(ruled, _ns()) == 0
    assert registry.cmd_check(ruled, _ns()) == 0


# Acceptance 4: the pending lifecycle.
def _pending_cfg(base: Path, *events: dict, ours_traits: list[str]) -> object:
    cfg = _make_cfg(base)
    _write_skill(cfg, "tdd")
    _write_record(cfg, "tdd", "engineering", "Design", "Specification")
    th = _tree_hash_of(cfg, "tdd")
    _write_defs(cfg, _defs("seams"))
    _write_traits(
        cfg,
        _ours_entry("tdd", th, ours_traits) + _upstream_entry(SUBJECT, ["seams"]),
    )
    _write_round(
        cfg,
        "2026-10-14-r",
        _checkpoint("2026-10-14-r:1", "adopt", "tdd"),
        *events,
        trait_level=True,
    )
    return cfg


def test_pending_lifecycle(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    subj = f"{SUBJECT}#seams"
    adopt = _trait("2026-10-14-r:2", "adopt", "seams", skill="tdd")
    pending = _trait("2026-10-14-r:2", "adopt", "seams", skill="tdd", pending="cr-9")

    # (a) a pending adopt whose trait is now listed fails (fulfilled: record it)
    a = _pending_cfg(tmp_path / "a", pending, ours_traits=["seams"])
    _fails_with(a, capsys, "record the completing adopt")

    # (b) after the completing adopt lands, removing the trait from the list fails
    b = _pending_cfg(
        tmp_path / "b",
        _trait("2026-10-14-r:2", "adopt", "seams", skill="tdd", pending="cr-9"),
        _trait(
            "2026-10-14-r:3",
            "adopt",
            "seams",
            skill="tdd",
            supersedes=["2026-10-14-r:2"],
        ),
        ours_traits=[],
    )
    _fails_with(b, capsys, "is not listed by skill 'tdd'")

    # (c) a cancelled pending adopt (reject supersedes) leaves no obligation; the
    # effective ruling is reject, so the checkpoint is reject too.
    c = _make_cfg(tmp_path / "c")
    _write_skill(c, "tdd")
    _write_record(c, "tdd", "engineering", "Design", "Specification")
    _write_defs(c, _defs("seams"))
    _write_traits(
        c,
        _ours_entry("tdd", _tree_hash_of(c, "tdd"), [])
        + _upstream_entry(SUBJECT, ["seams"]),
    )
    _write_round(
        c,
        "2026-10-14-r",
        _checkpoint("2026-10-14-r:1", "reject", "tdd"),
        _trait("2026-10-14-r:2", "adopt", "seams", skill="tdd", pending="cr-9"),
        _trait("2026-10-14-r:3", "reject", "seams", supersedes=["2026-10-14-r:2"]),
        trait_level=True,
    )
    assert registry.cmd_build(c, _ns()) == 0
    assert registry.cmd_check(c, _ns()) == 0

    # (d) a delivered adopt then a pending revision keeps the delivered obligation
    d = _pending_cfg(
        tmp_path / "d",
        adopt,
        _trait(
            "2026-10-14-r:3",
            "adopt",
            "seams",
            skill="tdd",
            pending="cr-9",
            supersedes=["2026-10-14-r:2"],
        ),
        ours_traits=[],
    )
    _fails_with(d, capsys, "is not listed by skill 'tdd'")

    # (e) delivered → withdrawn → pending keeps the withdrawal; the completing
    # adopt revives the obligation.
    wd = _pending_cfg(
        tmp_path / "wd",
        adopt,
        _ours_event("2026-10-14-r:3", "update", "tdd", withdraws=[subj]),
        _trait(
            "2026-10-14-r:4",
            "adopt",
            "seams",
            skill="tdd",
            pending="cr-9",
            supersedes=["2026-10-14-r:2"],
        ),
        ours_traits=[],
    )
    fwd = registry.build_lifecycle(registry.load_ledger(wd)[1])[0]
    assert (subj, "tdd") in registry.withdrawn_destinations(
        registry.load_ledger(wd)[1], fwd
    )
    assert registry.cmd_build(wd, _ns()) == 0
    assert registry.cmd_check(wd, _ns()) == 0  # withdrawn: no obligation

    live = _pending_cfg(
        tmp_path / "live",
        adopt,
        _ours_event("2026-10-14-r:3", "update", "tdd", withdraws=[subj]),
        _trait(
            "2026-10-14-r:4",
            "adopt",
            "seams",
            skill="tdd",
            supersedes=["2026-10-14-r:2"],
        ),
        ours_traits=[],
    )
    fwd = registry.build_lifecycle(registry.load_ledger(live)[1])[0]
    assert (subj, "tdd") not in registry.withdrawn_destinations(
        registry.load_ledger(live)[1], fwd
    )
    _fails_with(live, capsys, "is not listed by skill 'tdd'")  # revived obligation

    # review r1 #1: delivered → withdrawn → delivered, then a reject supersedes the
    # second delivery: the withdrawal stays cleared, so the obligation holds.
    redo = _pending_cfg(
        tmp_path / "redo",
        adopt,
        _ours_event("2026-10-14-r:3", "update", "tdd", withdraws=[subj]),
        _trait(
            "2026-10-14-r:4",
            "adopt",
            "seams",
            skill="tdd",
            supersedes=["2026-10-14-r:2"],
        ),
        _trait("2026-10-14-r:5", "reject", "seams", supersedes=["2026-10-14-r:4"]),
        ours_traits=[],
    )
    _fails_with(redo, capsys, "is not listed by skill 'tdd'")

    # review r1 #4: a completing adopt must copy the pending event's source
    moved = _trait("2026-10-14-r:3", "adopt", "seams", skill="tdd")
    moved["source"] = {**moved["source"], "sha": "fff9999"}  # type: ignore[dict-item]
    changed = _pending_cfg(
        tmp_path / "changed",
        pending,
        moved | {"supersedes": ["2026-10-14-r:2"]},
        ours_traits=["seams"],
    )
    _fails_with(changed, capsys, "must copy `source` from pending 2026-10-14-r:2")

    # (f) a doc-targeted pending adopt passes with no membership check
    doc = _make_cfg(tmp_path / "doc")
    _write_skill(doc, "tdd")
    _write_record(doc, "tdd", "engineering", "Design", "Specification")
    (doc.repo_root / "docs").mkdir(parents=True)  # type: ignore[attr-defined]
    (doc.repo_root / "docs" / "m.md").write_text("m", encoding="utf-8")  # type: ignore[attr-defined]
    _write_defs(doc, _defs("seams"))
    _write_traits(doc, _upstream_entry(SUBJECT, ["seams"]))
    _write_round(
        doc,
        "2026-10-14-r",
        _checkpoint("2026-10-14-r:1", "adopt", "doc:docs/m.md"),
        _trait(
            "2026-10-14-r:2", "adopt", "seams", skill="doc:docs/m.md", pending="cr-9"
        ),
        trait_level=True,
    )
    assert registry.cmd_build(doc, _ns()) == 0
    assert registry.cmd_check(doc, _ns()) == 0


# Acceptance 5: a modified adoption into a different trait without modification.
def test_modified_adoption_requires_modification(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="modification"):
        registry.Event.model_validate(
            _trait("r:1", "adopt", "seams", skill="tdd", into="other")
        )


def test_modified_adoption_distinct_from(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    # `into` names a trait that does NOT list the upstream trait in distinct_from
    cfg = _make_cfg(tmp_path)
    _write_skill(cfg, "tdd")
    _write_record(cfg, "tdd", "engineering", "Design", "Specification")
    th = _tree_hash_of(cfg, "tdd")
    _write_defs(cfg, _defs("seams", "other"))  # other has no distinct_from
    _write_traits(
        cfg, _ours_entry("tdd", th, ["other"]) + _upstream_entry(SUBJECT, ["seams"])
    )
    _write_round(
        cfg,
        "2026-10-14-r",
        _checkpoint("2026-10-14-r:1", "adopt", "tdd"),
        _trait(
            "2026-10-14-r:2",
            "adopt",
            "seams",
            skill="tdd",
            into="other",
            modification="looser variant",
        ),
        trait_level=True,
    )
    _fails_with(cfg, capsys, "must name 'seams' in its distinct_from")


# Acceptance 6: an adoption into a merged skill resolves to the survivor.
def test_merge_resolves_to_survivor(tmp_path: Path) -> None:
    cfg = _make_cfg(tmp_path)
    _write_skill(cfg, "old")
    _write_skill(cfg, "survivor")
    _write_record(cfg, "old", "engineering", "Design", "Specification")
    _write_record(cfg, "survivor", "engineering", "Building", "Diagnosis")
    _write_defs(cfg, _defs("seams"))
    _write_traits(
        cfg,
        _ours_entry("survivor", _tree_hash_of(cfg, "survivor"), ["seams"])
        + _ours_entry("old", _tree_hash_of(cfg, "old"), [])
        + _upstream_entry(SUBJECT, ["seams"]),
    )
    _write_round(
        cfg,
        "2026-10-14-r",
        _checkpoint("2026-10-14-r:1", "adopt", "old"),
        _trait("2026-10-14-r:2", "adopt", "seams", skill="old"),
        _ours_event("2026-10-14-r:3", "merge", "survivor", subject="ours:old"),
        trait_level=True,
    )
    assert registry.cmd_build(cfg, _ns()) == 0
    assert registry.cmd_check(cfg, _ns()) == 0  # resolves old → survivor, lists seams


# Acceptance 7: withdrawal is per source.
SUBJECT2 = "refrepo:skill:skills/engineering/tdd2"


def _upstream_entry2(traits: list[str]) -> str:
    return (
        f'{SUBJECT2}:\n  reviewed_sha: "abc1234"\n  tree_hash: "T2"\n'
        f"  placement: {_PLACEMENT}\n  traits: [{', '.join(traits)}]\n"
    )


def test_withdrawal_is_per_source(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    subj1 = f"{SUBJECT}#seams"
    subj2 = f"{SUBJECT2}#seams"

    def ck2(eid: str, kind: str, skill: str) -> dict:
        return {
            "type": "event",
            "id": eid,
            "date": "2026-10-14",
            "kind": kind,
            "subject": SUBJECT2,
            "why": "because",
            "evidence": ["x:1"],
            "skill": skill,
            "source": {
                "repo": "refrepo",
                "logical_id": "skill:skills/engineering/tdd2",
                "content_hash": "h",
                "tree_hash": "T2",
                "sha": "abc1234",
            },
        }

    def tr2(eid: str, kind: str, **extra: object) -> dict:
        ev = {
            "type": "event",
            "id": eid,
            "date": "2026-10-14",
            "kind": kind,
            "subject": subj2,
            "why": "because",
            "evidence": ["x:1"],
            "source": {
                "repo": "refrepo",
                "logical_id": "skill:skills/engineering/tdd2",
                "tree_hash": "T2",
                "sha": "abc1234",
            },
        }
        ev.update(extra)
        return ev

    def setup(base: Path, ours_traits: list[str], *tail: dict) -> object:
        cfg = _make_cfg(base)
        _write_skill(cfg, "tdd")
        _write_record(cfg, "tdd", "engineering", "Design", "Specification")
        _write_defs(cfg, _defs("seams"))
        _write_traits(
            cfg,
            _ours_entry("tdd", _tree_hash_of(cfg, "tdd"), ours_traits)
            + _upstream_entry(SUBJECT, ["seams"])
            + _upstream_entry2(["seams"]),
        )
        _write_round(
            cfg,
            "2026-10-14-r",
            _checkpoint("2026-10-14-r:1", "adopt", "tdd"),
            ck2("2026-10-14-r:2", "adopt", "tdd"),
            _trait("2026-10-14-r:3", "adopt", "seams", skill="tdd"),
            tr2("2026-10-14-r:4", "adopt", skill="tdd"),
            *tail,
            trait_level=True,
        )
        return cfg

    # one source withdrawn, the trait still listed (the other source needs it): ok
    ok = setup(
        tmp_path / "ok",
        ["seams"],
        _ours_event("2026-10-14-r:5", "update", "tdd", withdraws=[subj1]),
    )
    assert registry.cmd_build(ok, _ns()) == 0
    assert registry.cmd_check(ok, _ns()) == 0

    # the trait removed while one adoption is still retained: fails
    bad = setup(tmp_path / "bad", [])
    _fails_with(bad, capsys, "is not listed by skill 'tdd'")


# Acceptance 8: retirement.
def test_retirement_rules(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    retired_defs = (
        f"seams:\n  definition: x.\n  placement: {_PLACEMENT}\n"
        f'  retired: {{date: "2026-10-01", replaced_by: [seam-a, seam-b]}}\n'
        f"seam-a:\n  definition: a.\n  placement: {_PLACEMENT}\n"
        f"seam-b:\n  definition: b.\n  placement: {_PLACEMENT}\n"
    )

    # (a) a retired trait still listed warns (not an error)
    warn = _make_cfg(tmp_path / "warn")
    _write_skill(warn, "tdd")
    _write_record(warn, "tdd", "engineering", "Design", "Specification")
    _write_defs(warn, retired_defs)
    _write_traits(warn, _ours_entry("tdd", _tree_hash_of(warn, "tdd"), ["seams"]))
    assert registry.cmd_build(warn, _ns()) == 0
    assert registry.cmd_check(warn, _ns()) == 0
    assert "retired trait 'seams' still listed" in capsys.readouterr().err

    # (b) a retained adoption into a retired trait passes when the holder lists
    # every replacement; the subject's first event predates retirement, so it
    # continues. Sources show the replacement mapping (review r1 #13).
    adopted = _make_cfg(tmp_path / "adopted")
    _write_skill(adopted, "tdd")
    _write_record(adopted, "tdd", "engineering", "Design", "Specification")
    _write_defs(adopted, retired_defs)
    _write_traits(
        adopted,
        _ours_entry("tdd", _tree_hash_of(adopted, "tdd"), ["seam-a", "seam-b"])
        + _upstream_entry(SUBJECT, ["seams"]),
    )
    _write_round(
        adopted,
        "2026-09-01-old",
        _trait("2026-09-01-old:1", "defer", "seams", date="2026-09-01"),
        date="2026-09-01",
    )
    registry.seal(adopted, "2026-09-01-old")
    _write_round(
        adopted,
        "2026-10-14-r",
        _checkpoint("2026-10-14-r:1", "adopt", "tdd"),
        _trait(
            "2026-10-14-r:2",
            "adopt",
            "seams",
            skill="tdd",
            supersedes=["2026-09-01-old:1"],
        ),
        trait_level=True,
    )
    assert registry.cmd_build(adopted, _ns()) == 0
    assert registry.cmd_check(adopted, _ns()) == 0
    record = (adopted.skill_records_dir / "engineering" / "tdd.md").read_text()  # type: ignore[attr-defined]
    assert "adopted as seams, now seam-a, seam-b" in record

    # (c) a NEW subject using a retired trait fails, even when its first event is
    # superseded by a later one (review r1 #9)
    for name, tail in (
        ("new", [_trait("2026-10-14-r:2", "adopt", "seams", skill="tdd")]),
        (
            "renewed",
            [
                _trait("2026-10-14-r:2", "defer", "seams"),
                _trait(
                    "2026-10-14-r:3",
                    "adopt",
                    "seams",
                    skill="tdd",
                    supersedes=["2026-10-14-r:2"],
                ),
            ],
        ),
    ):
        new = _make_cfg(tmp_path / name)
        _write_skill(new, "tdd")
        _write_record(new, "tdd", "engineering", "Design", "Specification")
        _write_defs(new, retired_defs)
        _write_traits(
            new,
            _ours_entry("tdd", _tree_hash_of(new, "tdd"), ["seam-a", "seam-b"])
            + _upstream_entry(SUBJECT, ["seams"]),
        )
        _write_round(
            new,
            "2026-10-14-r",
            _checkpoint("2026-10-14-r:1", "adopt", "tdd"),
            *tail,
            trait_level=True,
        )
        _fails_with(new, capsys, "new subject")


# Acceptance 9: upstream replaces trait A with B.
def test_upstream_replaces_a_with_b(tmp_path: Path) -> None:
    cfg = _make_cfg(tmp_path)
    _write_skill(cfg, "tdd")
    _write_record(cfg, "tdd", "engineering", "Design", "Specification")
    _write_defs(cfg, _defs("seams", "newmech"))
    # A (seams) moved to `removed`; B (newmech) is listed and rejected, carrying A.
    _write_traits(
        cfg,
        _ours_entry("tdd", _tree_hash_of(cfg, "tdd"), ["seams"])
        + f'{SUBJECT}:\n  reviewed_sha: "abc1234"\n  tree_hash: "{TREE}"\n'
        f"  placement: {_PLACEMENT}\n  traits: [newmech]\n"
        f'  removed: {{seams: "oldsha"}}\n',
    )
    _write_round(
        cfg,
        "2026-10-14-r",
        _checkpoint("2026-10-14-r:1", "reject", "tdd"),
        _trait("2026-10-14-r:2", "adopt", "seams", skill="tdd"),
        _trait(
            "2026-10-14-r:3",
            "reject",
            "newmech",
            carried_from=[f"{SUBJECT}#seams"],
        ),
        trait_level=True,
    )
    assert registry.cmd_build(cfg, _ns()) == 0
    assert registry.cmd_check(cfg, _ns()) == 0
    record = (cfg.skill_records_dir / "engineering" / "tdd.md").read_text()  # type: ignore[attr-defined]
    sources = record.split(registry.SOURCES_OPEN)[1].split(registry.SOURCES_CLOSE)[0]
    assert "upstream replaced it with newmech (reject)" in sources


# Acceptance 10: overlap warning.
def test_overlap_warning(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    cfg = _make_cfg(tmp_path)
    _write_skill(cfg, "tdd")
    _write_skill(cfg, "other")
    _write_record(cfg, "tdd", "engineering", "Design", "Specification")
    _write_record(cfg, "other", "engineering", "Building", "Diagnosis")
    _write_defs(cfg, _defs("seams"))
    _write_traits(
        cfg,
        _ours_entry("tdd", _tree_hash_of(cfg, "tdd"), ["seams"])
        + _ours_entry("other", _tree_hash_of(cfg, "other"), ["seams"]),
    )
    assert registry.cmd_build(cfg, _ns()) == 0
    assert registry.cmd_check(cfg, _ns()) == 0  # overlap is a warning, not an error
    err = capsys.readouterr().err
    assert "overlap" in err and "'seams'" in err and "other, tdd" in err


# Acceptance 11: TRAITS.md by-trait view lists ours and upstream holders.
def test_traits_md_by_trait_view(tmp_path: Path) -> None:
    cfg = _trait_cfg(tmp_path)
    assert registry.cmd_build(cfg, _ns()) == 0
    md = cfg.traits_md_path.read_text(encoding="utf-8")  # type: ignore[attr-defined]
    assert "## By skill" in md and "## By trait" in md
    by_trait = md.split("## By trait")[1]
    assert "### engineering · Design · Specification\n\n#### `seams`" in by_trait
    assert "- ours: `tdd`" in by_trait
    assert f"- `{SUBJECT}` — adopt → tdd#seams" in by_trait


def test_traits_md_pending_suffix(tmp_path: Path) -> None:
    cfg = _make_cfg(tmp_path)
    _write_skill(cfg, "tdd")
    _write_record(cfg, "tdd", "engineering", "Design", "Specification")
    _write_defs(cfg, _defs("seams"))
    _write_traits(
        cfg,
        _ours_entry("tdd", _tree_hash_of(cfg, "tdd"), [])
        + _upstream_entry(SUBJECT, ["seams"]),
    )
    _write_round(
        cfg,
        "2026-10-14-r",
        _checkpoint("2026-10-14-r:1", "adopt", "tdd"),
        _trait("2026-10-14-r:2", "adopt", "seams", skill="tdd", pending="cr-7"),
        trait_level=True,
    )
    assert registry.cmd_build(cfg, _ns()) == 0
    md = cfg.traits_md_path.read_text(encoding="utf-8")  # type: ignore[attr-defined]
    assert "adopt, pending cr-7 → tdd#seams" in md
    # review r1 #12: one lineage entry, labelled pending, no checkpoint duplicate
    record = (cfg.skill_records_dir / "engineering" / "tdd.md").read_text()  # type: ignore[attr-defined]
    lineage = record.split(registry.LINEAGE_OPEN)[1].split(registry.LINEAGE_CLOSE)[0]
    assert lineage.strip() == f"- **{SUBJECT}#seams** @ abc1234 (pending cr-7)"


def test_trait_identity_rules() -> None:
    # adopt-merged is not a valid trait kind
    with pytest.raises(ValueError, match="trait kinds"):
        registry.Event.model_validate(
            _trait("r:1", "adopt-merged", "seams", skill="tdd")
        )
    # a trait subject must name a skill logical id
    agent = _trait("r:1", "adopt", "seams", skill="tdd")
    agent["subject"] = "refrepo:agent:agents/x#seams"
    agent["source"] = {"repo": "refrepo", "logical_id": "agent:agents/x"}  # type: ignore[assignment]
    with pytest.raises(ValueError, match="skills only"):
        registry.Event.model_validate(agent)
    # slugs are validated
    with pytest.raises(ValueError, match="valid trait slug"):
        registry.Event.model_validate(_trait("r:1", "adopt", "bad slug", skill="tdd"))
    # review r1 #11: contextual fields only where §5 defines them
    for ev, needle in (
        (_trait("r:1", "reject", "seams", pending="cr-1"), "only for a trait adopt"),
        (_trait("r:1", "reject", "seams", withdraws=["x#y"]), "ours-side update"),
        (_trait("r:1", "adopt", "seams", skill="tdd", pending=" "), "is empty"),
    ):
        with pytest.raises(ValueError, match=needle):
            registry.Event.model_validate(ev)


def test_reference_page_traits_column(tmp_path: Path) -> None:
    cfg = _trait_cfg(tmp_path)
    _catalog(cfg, "refrepo", [_cap("skill", "tdd", LOGICAL, "hcur")])
    assert registry.cmd_build(cfg, _ns()) == 0
    page = (cfg.references_dir / "refrepo.md").read_text(encoding="utf-8")  # type: ignore[attr-defined]
    assert "Traits" in page.split("\n")[6]  # the header row carries a Traits column
    assert "1 adopt" in page


def test_build_refuses_invalid_trait_files(tmp_path: Path) -> None:
    """review r1 #10: a trait file that fails to load stops build before writing."""
    cfg = _trait_cfg(tmp_path)
    assert registry.cmd_build(cfg, _ns()) == 0
    before = cfg.traits_md_path.read_text(encoding="utf-8")  # type: ignore[attr-defined]
    _write_defs(
        cfg, f"seams:\n  definition: x.\n  placement: {_PLACEMENT}\n  bogus: 1\n"
    )
    with pytest.raises(SystemExit, match="trait files have errors"):
        registry.cmd_build(cfg, _ns())
    assert cfg.traits_md_path.read_text(encoding="utf-8") == before  # type: ignore[attr-defined]


def test_traits_yaml_keys_and_metadata(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """review r1 #6 and #7: metadata keys and upstream identities are checked."""
    cases = [
        # #6: an undefined removed trait, with an effective ruling on it
        (
            (
                f'{SUBJECT}:\n  reviewed_sha: "abc1234"\n  tree_hash: "{TREE}"\n'
                f"  placement: {_PLACEMENT}\n  traits: [seams]\n"
                f'  removed: {{ghost: "oldsha"}}\n'
            ),
            "removed trait 'ghost' is undefined",
            [_trait("2026-10-14-r:3", "reject", "ghost")],
        ),
        # #6: a note on a trait the entry does not hold
        (
            (
                f'{SUBJECT}:\n  reviewed_sha: "abc1234"\n  tree_hash: "{TREE}"\n'
                f"  placement: {_PLACEMENT}\n  traits: [seams]\n"
                f"  notes: {{other: n}}\n"
            ),
            "notes trait 'other' is not in the entry",
            [],
        ),
        # #7: a plausible key with no catalog entry and no ledger history
        (
            _upstream_entry(SUBJECT, ["seams"])
            + _upstream_entry("nonexistent:skill:skills/made-up", ["seams"]),
            "has no removed-upstream history",
            [],
        ),
        # #7: a non-skill capability key
        (
            _upstream_entry(SUBJECT, ["seams"])
            + _upstream_entry("refrepo:agent:agents/x", ["seams"]),
            "an upstream key is <repo>:skill:<path>",
            [],
        ),
    ]
    for i, (upstream, needle, extra) in enumerate(cases):
        cfg = _trait_cfg(tmp_path / str(i))
        _write_defs(cfg, _defs("seams", "other"))
        th = _tree_hash_of(cfg, "tdd")
        _write_traits(cfg, _ours_entry("tdd", th, ["seams"]) + upstream)
        if extra:
            _write_round(
                cfg,
                "2026-10-14-r",
                _checkpoint("2026-10-14-r:1", "adopt", "tdd"),
                _trait("2026-10-14-r:2", "adopt", "seams", skill="tdd"),
                *extra,
                trait_level=True,
            )
        _fails_with(cfg, capsys, needle)


def test_pending_completion_supersedes_effective_pending(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    # review r2 #1: reject → pending adopt → delivered adopt. The completion must
    # supersede the effective pending adopt (not the reject) and copy its source.
    reject = _trait("2026-10-14-r:2", "reject", "seams")
    pending = _trait(
        "2026-10-14-r:3",
        "adopt",
        "seams",
        skill="tdd",
        pending="cr-9",
    )
    moved = _trait("2026-10-14-r:4", "adopt", "seams", skill="tdd")
    moved["source"] = {**moved["source"], "sha": "fff9999"}  # type: ignore[dict-item]
    changed = _pending_cfg(
        tmp_path / "changed",
        reject,
        pending,
        moved | {"supersedes": ["2026-10-14-r:2"]},
        ours_traits=["seams"],
    )
    assert registry.cmd_build(changed, _ns()) == 0
    _fails_with(changed, capsys, "must supersede pending 2026-10-14-r:3")
    _fails_with(changed, capsys, "must copy `source` from pending 2026-10-14-r:3")

    skipped = _pending_cfg(
        tmp_path / "skipped",
        reject,
        pending,
        _trait("2026-10-14-r:4", "adopt", "seams", skill="tdd"),
        ours_traits=["seams"],
    )
    assert registry.cmd_build(skipped, _ns()) == 0
    _fails_with(skipped, capsys, "must supersede pending 2026-10-14-r:3")

    good = _pending_cfg(
        tmp_path / "good",
        reject,
        pending,
        _trait(
            "2026-10-14-r:4",
            "adopt",
            "seams",
            skill="tdd",
            supersedes=["2026-10-14-r:3"],
        ),
        ours_traits=["seams"],
    )
    assert registry.cmd_build(good, _ns()) == 0
    assert registry.cmd_check(good, _ns()) == 0


def test_retirement_uses_first_event_date(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    # review r2 #2: a round opened 2026-09-01 records the subject's first event on
    # 2026-10-14, after the trait retired on 2026-10-01: it is a new subject.
    cfg = _make_cfg(tmp_path)
    _write_skill(cfg, "tdd")
    _write_record(cfg, "tdd", "engineering", "Design", "Specification")
    _write_defs(
        cfg,
        f"seams:\n  definition: x.\n  placement: {_PLACEMENT}\n"
        f'  retired: {{date: "2026-10-01", replaced_by: [seam-a]}}\n'
        f"seam-a:\n  definition: a.\n  placement: {_PLACEMENT}\n",
    )
    _write_traits(
        cfg,
        _ours_entry("tdd", _tree_hash_of(cfg, "tdd"), ["seam-a"])
        + _upstream_entry(SUBJECT, ["seams"]),
    )
    _write_round(
        cfg,
        "2026-09-01-old",
        _checkpoint("2026-09-01-old:1", "adopt", "tdd"),
        _trait("2026-09-01-old:2", "adopt", "seams", skill="tdd"),
        date="2026-09-01",
        trait_level=True,
    )
    assert registry.cmd_build(cfg, _ns()) == 0
    _fails_with(cfg, capsys, "new subject")
