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


def _write_round(cfg: object, round_id: str, *events: dict) -> Path:
    header = {
        "type": "round",
        "round_id": round_id,
        "date": "2026-10-14",
        "scope": "test",
    }
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


def test_check_warns_for_listed_owner_review_event(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
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
    monkeypatch.setattr(
        registry, "OWNER_REVIEW_EVENTS", {"2026-10-14-r:2": "owner must decide"}
    )
    assert registry.cmd_check(cfg, _ns()) == 0
    assert "owner-review" in capsys.readouterr().err


def test_check_fails_when_owner_review_list_rots(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cfg = _baseline(tmp_path)
    monkeypatch.setattr(
        registry, "OWNER_REVIEW_EVENTS", {"2026-10-14-r:999": "stale entry"}
    )
    _fails_with(cfg, capsys, "no longer an effective adoption")


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


def test_check_accepts_alias_stub_and_in_progress(tmp_path: Path) -> None:
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
    _catalog(
        cfg,
        "refrepo",
        [
            _cap("skill", "foo", "skill:skills/foo", "hnow"),  # present, unruled
            _cap("skill", "bar", "skill:skills/bar", "hnow"),  # not reviewed
            _cap("skill", "baz", "skill:skills/baz", "hnow"),  # ruled, hash changed
        ],
    )
    _write_round(
        cfg,
        "2026-10-14-r",
        _ref_event(
            "2026-10-14-r:1",
            "adopt",
            "refrepo",
            "skill:skills/baz",
            content_hash="hold",
            skill="foo",
        ),
    )
    # gap
    assert registry.cmd_gap(cfg, _ns(reference="refrepo", kind=None, beads=False)) == 0
    out = capsys.readouterr().out
    assert "not reviewed" in out and "skill:skills/bar" in out
    assert "present, unruled" in out and "skill:skills/foo" in out
    assert "changed since ruled" in out and "skill:skills/baz" in out
    # reference page uses the same classify_capability, so statuses match
    assert registry.cmd_build(cfg, _ns()) == 0
    ref = (cfg.references_dir / "refrepo.md").read_text()  # type: ignore[attr-defined]
    assert "| `skill:skills/foo` | present, unruled |" in ref
    assert "| `skill:skills/bar` | not reviewed |" in ref
    assert "| `skill:skills/baz` | adopt |" in ref and "| yes |" in ref


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
