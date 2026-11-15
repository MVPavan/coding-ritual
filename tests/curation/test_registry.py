"""Tests for the skill + capability registry tool.

Each failure test starts from a passing baseline and then asserts the one
specific diagnostic the mutation should produce (so a test can never pass for an
unrelated reason). All state lives in a temporary directory; the real ledger is
never touched.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

import pytest
import yaml

from curation.registry import (
    catalogs,
    cli,
    config,
    ledger,
    loaders,
    models,
    vocab,
)
from curation.registry import traits as trait_facts
from curation.registry.checks import ledger as checks_ledger
from curation.registry.checks import records as record_checks
from curation.registry.record import _target_hash
from curation.registry.views import records as record_views
from curation.scan import catalog as scan

# --- helpers ------------------------------------------------------------------


def _make_cfg(tmp_path: Path) -> object:
    repo = tmp_path / "repo"
    reg = repo / "registry"
    (repo / ".claude" / "skills").mkdir(parents=True)
    (reg / "ledger").mkdir(parents=True)
    (reg / "skill-records").mkdir(parents=True)
    (reg / "references").mkdir(parents=True)
    (repo / "catalogs").mkdir(parents=True)
    return config.RegistryConfig(
        repo_root=repo,
        registry_dir=reg,
        ledger_dir=reg / "ledger",
        manifest_path=reg / "ledger" / "MANIFEST.json",
        skill_records_dir=reg / "skill-records",
        references_dir=reg / "references",
        index_path=reg / "INDEX.md",
        trait_definitions_path=reg / "trait-definitions.yaml",
        traits_dir=reg / "traits",
        skills_path=reg / "skills.yaml",
        traits_md_path=reg / "TRAITS.md",
        catalogs_dir=repo / "catalogs",
        skills_dir=repo / ".claude" / "skills",
        our_harness_root=repo / ".claude",
        codex_root=repo / ".codex",
        plugins_glob="plugins/*",
        # The legacy fixture round predates reports (stages-design 3.2): its
        # trait events cite none. Decision-rule tests use later rounds.
        pre_trait_rounds=frozenset(
            {
                "2026-10-14-migration",
                "2026-10-14-owner-review",
                "2026-10-14-r",
                "2026-09-01-old",
            }
        ),
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
    boundary: str | None = None,
) -> Path:
    """Add the skill's `skills.yaml` entry; `build` writes the record, whose
    path is returned."""
    path = cfg.skills_path  # type: ignore[attr-defined]
    skills = yaml.safe_load(path.read_text(encoding="utf-8")) if path.is_file() else {}
    skills[skill] = {
        "domain": domain,
        "stage": stage,
        "substage": substage,
        "secondary": [],
        "family": None,
        "aliases": aliases or [],
        "status": "active",
        "boundary": boundary,
    }
    path.write_text(yaml.safe_dump(skills, sort_keys=False), encoding="utf-8")
    return cfg.skill_records_dir / domain / f"{skill}.md"  # type: ignore[attr-defined,no-any-return]


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
    assert cli.cmd_build(cfg, _ns()) == 0
    assert cli.cmd_check(cfg, _ns()) == 0
    return cfg


def _fails_with(cfg: object, capsys: pytest.CaptureFixture[str], needle: str) -> None:
    assert cli.cmd_check(cfg, _ns()) == 1
    assert needle in capsys.readouterr().err


# --- ours / template exclusion ------------------------------------------------


def test_ours_catalogs_our_skills(tmp_path: Path) -> None:
    cfg = _make_cfg(tmp_path)
    _write_skill(cfg, "planning")
    assert "skill:skills/planning" in catalogs.build_ours(cfg).by_logical_id()


def test_principle_is_a_routed_file_not_a_skill_folder(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    cfg = _baseline(tmp_path)
    name = "principle-example"
    _write_record(cfg, name, "engineering", "Design", "Architecture")
    playbook = cfg.playbooks_dir / "route.md"  # type: ignore[attr-defined]
    playbook.parent.mkdir(parents=True)
    playbook.write_text(
        "---\ntrigger: Route it.\nsteps:\n  - id: route#1\n    when: always\n"
        f'    calls: [{{to: "skill:{name}"}}]\n---\n# Route\n',
        encoding="utf-8",
    )

    def check_output() -> str:
        cli.cmd_check(cfg, _ns())
        return capsys.readouterr().err

    no_file = f"skills.yaml: {name}: no file"
    unresolved = f"call 'skill:{name}'"
    output = check_output()
    assert no_file in output
    assert unresolved in output

    cfg.principles_dir.mkdir()  # type: ignore[attr-defined]
    file = cfg.principles_dir / "example.md"  # type: ignore[attr-defined]
    file.write_text("# Example\n", encoding="utf-8")
    cfg.router_path.write_text(  # type: ignore[attr-defined]
        "## Principles\n\n- `principles/example.md`: the example situation holds.\n",
        encoding="utf-8",
    )
    output = check_output()
    assert no_file not in output
    assert unresolved not in output
    assert loaders.skill_description(cfg, name) == "the example situation holds."

    # A principle file with no entry.
    (cfg.principles_dir / "unlisted.md").write_text("# Unlisted\n", encoding="utf-8")  # type: ignore[attr-defined]
    assert "principle-unlisted: no skills.yaml entry" in check_output()

    def tree_hash() -> str:
        item = catalogs.build_ours(cfg).by_logical_id()[f"skill:skills/{name}"]
        return item.tree_hash  # type: ignore[no-any-return]

    before = tree_hash()
    file.write_text("# Edited\n", encoding="utf-8")
    assert tree_hash() != before


LIVE_LINE = "- `principles/example.md`: live situation.\n"
EXAMPLE_LINE = "- `principles/example.md`: example only.\n"


@pytest.mark.parametrize(
    "example",
    [
        f"<!--\n{EXAMPLE_LINE}-->\n",
        f"```\n{EXAMPLE_LINE}```\n",
        f"````markdown\n```\n{EXAMPLE_LINE}````\n",
        f"~~~~\n~~~\n{EXAMPLE_LINE}~~~~\n",
    ],
    ids=["comment", "fence", "backticks-inside-longer", "tildes-inside-longer"],
)
def test_principle_situation_skips_examples(tmp_path: Path, example: str) -> None:
    cfg = _make_cfg(tmp_path)
    cfg.router_path.parent.mkdir(parents=True)  # type: ignore[attr-defined]
    cfg.router_path.write_text(  # type: ignore[attr-defined]
        f"## Principles\n\n{example}{LIVE_LINE}", encoding="utf-8"
    )
    assert loaders.skill_description(cfg, "principle-example") == "live situation."


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
    ids = catalogs.build_ours(cfg).by_logical_id()
    assert "skill:skills/real" in ids
    assert not any("template/" in c.canonical_path for c in ids.values())


# --- round / record -----------------------------------------------------------


def test_round_record_seal_and_structured_json(tmp_path: Path) -> None:
    cfg = _make_cfg(tmp_path)
    assert (
        cli.cmd_round(
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
    assert cli.cmd_record(cfg, _rec_ns(json=payload)) == 0
    _, events, errors = loaders.load_ledger(cfg)
    assert not errors and len(events) == 1
    assert events[0].id == "2026-10-14-x:001" and events[0].date  # auto id + date
    ledger.seal(cfg, "2026-10-14-x")
    assert ledger.open_round(cfg) is None


def test_round_open_prefixes_date_without_doubling(tmp_path: Path) -> None:
    cfg = _make_cfg(tmp_path)
    # a bare slug gets <date>- prepended (cr-alnr)
    assert (
        cli.cmd_round(
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
    ledger.seal(cfg, "2026-10-14-agent-skills")
    # a slug that already carries a date prefix is left alone (no doubling)
    assert (
        cli.cmd_round(
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
    assert cli.cmd_build(cfg, _ns()) == 0
    planning = (
        cfg.skill_records_dir / "engineering" / "planning.md"  # type: ignore[attr-defined]
    ).read_text()
    assert (
        record_views.REVIEWS_OPEN in planning and record_views.REVIEWS_CLOSE in planning
    )
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
    assert "None yet." in foo.split(record_views.REVIEWS_OPEN)[1]


def test_renamed_skill_record_keeps_lineage_history_and_reviews(
    tmp_path: Path,
) -> None:
    """A rename moves a record's lineage, history and reviews to the survivor;
    an unrelated skill's record gains none of them."""
    cfg = _make_cfg(tmp_path)
    for name in ("slicing", "foo"):
        _write_skill(cfg, name)
    _write_record(cfg, "slicing", "engineering", "Design", "Decomposition")
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
        _ref_event(
            "2026-10-14-r:2", "adopt", "refrepo", "skill:skills/x", skill="planning"
        ),
        {
            **_ours_event("2026-10-14-r:3", "rename", "planning"),
            "skill": "slicing",
            "why": "renamed planning to slicing",
        },
        _ours_event("2026-10-14-r:4", "add", "foo"),
    )
    assert cli.cmd_build(cfg, _ns()) == 0

    def blocks(skill: str) -> tuple[str, str, str]:
        text = (
            cfg.skill_records_dir / "engineering" / f"{skill}.md"  # type: ignore[attr-defined]
        ).read_text()

        def block(open_tag: str, close_tag: str) -> str:
            return text.split(open_tag)[1].split(close_tag)[0]

        return (
            block(record_views.LINEAGE_OPEN, record_views.LINEAGE_CLOSE),
            block(record_views.HISTORY_OPEN, record_views.HISTORY_CLOSE),
            block(record_views.REVIEWS_OPEN, record_views.REVIEWS_CLOSE),
        )

    lineage, history, reviews = blocks("slicing")
    assert "**refrepo:skill:skills/x**" in lineage
    for eid in ("2026-10-14-r:1", "2026-10-14-r:2", "2026-10-14-r:3"):
        assert f"({eid})" in history
    assert "2026-10-14-r:4" not in history
    assert "2026-10-14-upstream-x-1.0.md" in reviews

    foo_lineage, foo_history, foo_reviews = blocks("foo")
    assert "No adopted lineage recorded." in foo_lineage
    assert "(2026-10-14-r:4)" in foo_history
    assert "2026-10-14-r:1" not in foo_history
    assert "None yet." in foo_reviews


def test_reusing_a_renamed_name_is_refused(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Adding a name a live rename forwards would leak the new skill's events
    into the survivor's record, so `record` and `check` refuse it; once the
    rename is superseded, the name is free again."""
    cfg = _make_cfg(tmp_path)
    _write_skill(cfg, "slicing")
    _write_record(cfg, "slicing", "engineering", "Design", "Decomposition")
    retiring = [
        _ours_event("2026-10-14-r:1", "add", "planning"),
        _ref_event(
            "2026-10-14-r:2", "adopt", "refrepo", "skill:skills/x", skill="planning"
        ),
        {
            **_ours_event("2026-10-14-r:3", "rename", "planning"),
            "skill": "slicing",
            "why": "renamed planning to slicing",
        },
    ]
    readd = _ours_event("2026-10-14-r:4", "add", "planning")
    _write_round(cfg, "2026-10-14-r", *retiring, readd)
    with pytest.raises(SystemExit, match="retired by rename 2026-10-14-r:3"):
        cli.cmd_build(cfg, _ns())
    _fails_with(
        cfg,
        capsys,
        "2026-10-14-r:4: add reintroduces 'planning', retired by rename 2026-10-14-r:3",
    )

    # `record` refuses the same add before writing it.
    path = _write_round(cfg, "2026-10-14-r", *retiring)
    before = path.read_text()
    with pytest.raises(SystemExit, match="retired by rename 2026-10-14-r:3"):
        cli.cmd_record(
            cfg, _rec_ns(kind="add", subject="ours:planning", why="w", skill="planning")
        )
    assert path.read_text() == before

    # A superseded rename retires nothing.
    undo = {
        **_ours_event("2026-10-14-r:4", "update", "planning"),
        "supersedes": ["2026-10-14-r:3"],
    }
    _write_round(cfg, "2026-10-14-r", *retiring, undo)
    assert (
        cli.cmd_record(
            cfg, _rec_ns(kind="add", subject="ours:planning", why="w", skill="planning")
        )
        == 0
    )


def test_record_autofills_reference_source(tmp_path: Path) -> None:
    cfg = _make_cfg(tmp_path)
    _catalog(cfg, "refrepo", [_cap("skill", "foo", "skill:skills/foo", "hcur")])
    # `record` checks membership by sha (3.9), so the trait needs its analysis.
    _write_defs(cfg, _defs("seams"))
    _write_traits(
        cfg,
        'refrepo:skill:skills/foo:\n  accepted: null\n  proposed: "old1234"\n'
        '  analyses:\n    "old1234":\n' + _analysis(["seams"]),
    )
    cli.cmd_round(
        cfg,
        _ns(
            round_command="open",
            slug="2026-10-14-r",
            date="2026-10-14",
            scope="s",
            json=None,
            json_file=None,
            stdin=False,
        ),
    )
    assert (
        cli.cmd_record(
            cfg,
            _rec_ns(
                kind="reject", subject="refrepo:skill:skills/foo", why="no", skill=None
            ),
        )
        == 0
    )
    _, events, _ = loaders.load_ledger(cfg)
    assert events[0].source is not None
    assert events[0].source.content_hash == "hcur"  # auto-filled from the catalog

    # completing a pending adopt copies the pending source, not the catalog (r1 #4)
    trait = "refrepo:skill:skills/foo#seams"
    old = {"repo": "refrepo", "logical_id": "skill:skills/foo", "sha": "old1234"}
    payload = {"kind": "adopt", "subject": trait, "why": "w", "skill": "foo"}
    for extra in ({"pending": "cr-1", "source": old}, {"supersedes": None}):
        if "supersedes" in extra:  # a completion supersedes its pending adopt
            extra = {"supersedes": [loaders.load_ledger(cfg)[1][-1].id]}
        assert cli.cmd_record(cfg, _rec_ns(json=json.dumps(payload | extra))) == 0
    _, events, _ = loaders.load_ledger(cfg)
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
    cli.cmd_build(cfg, _ns())
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
    cli.cmd_build(cfg, _ns())
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


@pytest.mark.parametrize(
    ("field", "value", "diagnostic"),
    [
        # Lax pydantic read "yes" as True and "3" as 3; the strict base refuses.
        ("trait_level", "yes", "trait_level\n  Input should be a valid boolean"),
        (
            "excluded",
            [{"rule": "r", "why": "w", "count": "3"}],
            "excluded.0.count\n  Input should be a valid integer",
        ),
    ],
)
def test_check_rejects_coercible_round_header(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    field: str,
    value: object,
    diagnostic: str,
) -> None:
    cfg = _baseline(tmp_path)
    path = cfg.ledger_dir / "2026-10-14-r.jsonl"  # type: ignore[attr-defined]
    header, *rest = path.read_text(encoding="utf-8").splitlines()
    bad = json.dumps({**json.loads(header), field: value})
    path.write_text("\n".join([bad, *rest]) + "\n", encoding="utf-8")
    assert cli.cmd_check(cfg, _ns()) == 1
    err = capsys.readouterr().err
    assert "2026-10-14-r.jsonl:1: schema error" in err
    assert diagnostic in err


def test_change_info_and_config_are_strict(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="extra\n  Extra inputs are not permitted"):
        models.ChangeInfo.model_validate({"changed": "no", "extra": 1})
    cfg = _make_cfg(tmp_path)
    data = {**cfg.model_dump(), "repo_root": str(tmp_path)}  # type: ignore[attr-defined]
    with pytest.raises(
        ValueError, match="repo_root\n  Input should be an instance of Path"
    ):
        config.RegistryConfig.model_validate(data)


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
    cli.cmd_build(cfg, _ns())
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
    cli.cmd_build(cfg, _ns())
    _fails_with(cfg, capsys, "invalid skill target")


UNBUILT_PLAYBOOK = "doc:.claude/skills/mvp-mode/playbooks/feature.md"


def test_check_accepts_pending_adopt_into_unbuilt_playbook(tmp_path: Path) -> None:
    """The checkpoint may name it too, as it may a skill not yet built (§5b)."""
    cfg = _pending_cfg(
        tmp_path,
        _trait(
            "2026-10-14-r:2", "adopt", "seams", skill=UNBUILT_PLAYBOOK, pending="cr-9"
        ),
        ours_traits=[],
        checkpoint_skill=UNBUILT_PLAYBOOK,
    )
    assert cli.cmd_build(cfg, _ns()) == 0
    assert cli.cmd_check(cfg, _ns()) == 0


@pytest.mark.parametrize(
    ("target", "pending"),
    [
        ("doc:docs/unbuilt.md", "cr-9"),
        ("doc:.claude/skills/mvp-mode/playbooks/feature/reference.md", "cr-9"),
        (UNBUILT_PLAYBOOK, None),
    ],
    ids=["pending-outside-folder", "pending-playbook-reference", "delivered-playbook"],
)
def test_check_rejects_missing_doc_target_a_build_cannot_excuse(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], target: str, pending: str | None
) -> None:
    """Both the trait adopt and the checkpoint naming the same target fail."""
    extra = {"pending": pending} if pending else {}
    cfg = _pending_cfg(
        tmp_path,
        _trait("2026-10-14-r:2", "adopt", "seams", skill=target, **extra),
        ours_traits=[],
        checkpoint_skill=target,
    )
    cli.cmd_build(cfg, _ns())
    assert cli.cmd_check(cfg, _ns()) == 1
    err = capsys.readouterr().err
    for eid in ("2026-10-14-r:1", "2026-10-14-r:2"):
        assert f"{eid}: live adoption" in err and "invalid skill target" in err


def test_check_rejects_pending_playbook_through_symlink_out_of_repo(
    tmp_path: Path,
    tmp_path_factory: pytest.TempPathFactory,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A missing target may be excused; one that escapes the repository may not."""
    cfg = _pending_cfg(
        tmp_path,
        _trait(
            "2026-10-14-r:2", "adopt", "seams", skill=UNBUILT_PLAYBOOK, pending="cr-9"
        ),
        ours_traits=[],
        checkpoint_skill=UNBUILT_PLAYBOOK,
    )
    playbooks = cfg.repo_root / UNBUILT_PLAYBOOK[len("doc:") :].rsplit("/", 1)[0]
    playbooks.parent.mkdir(parents=True, exist_ok=True)
    playbooks.symlink_to(tmp_path_factory.mktemp("outside"), target_is_directory=True)
    cli.cmd_build(cfg, _ns())
    assert cli.cmd_check(cfg, _ns()) == 1
    err = capsys.readouterr().err
    for eid in ("2026-10-14-r:1", "2026-10-14-r:2"):
        assert f"{eid}: live adoption" in err and "invalid skill target" in err


def test_target_exists_accepts_only_real_kinds_and_shipped_caps(
    tmp_path: Path,
) -> None:
    cfg = _baseline(tmp_path)
    ours = catalogs.build_ours(cfg)
    existing = {"planning"}
    assert record_checks._target_exists("planning", existing, ours)
    assert (
        record_checks._target_exists("skill:skills/planning", existing, ours) is False
    )
    assert record_checks._target_exists("skill:never-existed", existing, ours) is False
    assert record_checks._target_exists("oops:", existing, ours) is False
    assert record_checks._target_exists("ghost", existing, ours) is False
    assert record_checks._target_exists("agent:code-reviewer", existing, ours) is False
    # A real non-skill capability resolves by (kind, name-leaf).
    (cfg.our_harness_root / "agents").mkdir(parents=True, exist_ok=True)  # type: ignore[attr-defined]
    (cfg.our_harness_root / "agents" / "code-reviewer.md").write_text(  # type: ignore[attr-defined]
        "---\nname: code-reviewer\ndescription: Reviews code.\n---\nBody.\n",
        encoding="utf-8",
    )
    ours2 = catalogs.build_ours(cfg)
    assert record_checks._target_exists("agent:code-reviewer", existing, ours2)
    assert record_checks._target_exists("agent:agents/code-reviewer", existing, ours2)
    # A fabricated namespace must not resolve via leaf-name matching.
    assert (
        record_checks._target_exists(
            "agent:does-not-exist/agents/code-reviewer", existing, ours2
        )
        is False
    )
    # doc: targets must stay inside repo_root (review #15).
    (cfg.repo_root / "docs").mkdir(parents=True, exist_ok=True)  # type: ignore[attr-defined]
    (cfg.repo_root / "docs" / "method.md").write_text("x", encoding="utf-8")  # type: ignore[attr-defined]
    assert record_checks._target_exists("doc:docs/method.md", existing, ours2, cfg)
    assert (
        record_checks._target_exists("doc:/etc/passwd", existing, ours2, cfg) is False
    )
    assert (
        record_checks._target_exists("doc:../escape.md", existing, ours2, cfg) is False
    )
    assert (
        record_checks._target_exists("doc:docs/missing.md", existing, ours2, cfg)
        is False
    )


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
    cli.cmd_build(cfg, _ns())
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
    cli.cmd_build(cfg, _ns())
    _fails_with(cfg, capsys, "cyclic")


def test_check_rejects_a_supersedes_edge_pointing_forward(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    cfg = _baseline(tmp_path)
    _write_round(
        cfg,
        "2026-10-14-r",
        _ours_event("2026-10-14-r:1", "add", "planning", supersedes=["2026-10-14-r:2"]),
        _ours_event("2026-10-14-r:2", "add", "planning"),
    )
    cli.cmd_build(cfg, _ns())
    _fails_with(cfg, capsys, "which comes later in ledger order")


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
    cli.cmd_build(cfg, _ns())
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
    cli.cmd_round(
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
        cli.cmd_record(
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
    assert models.Event.model_validate(ok).skill == "survivor"
    with pytest.raises(ValueError, match="same"):
        models.Event.model_validate({**ok, "subject": "ours:survivor"})
    with pytest.raises(ValueError, match="subject must be ours:"):
        models.Event.model_validate({**ok, "kind": "add", "subject": "ours:other"})


def test_check_rejects_foreign_event_id(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    cfg = _baseline(tmp_path)
    _write_round(cfg, "2026-10-14-r", _ours_event("other-round:1", "add", "planning"))
    cli.cmd_build(cfg, _ns())
    _fails_with(cfg, capsys, "does not belong")


def test_check_rejects_edited_sealed_round(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    cfg = _baseline(tmp_path)
    ledger.seal(cfg, "2026-10-14-r")
    path = cfg.ledger_dir / "2026-10-14-r.jsonl"  # type: ignore[attr-defined]
    path.write_text(path.read_text() + " \n", encoding="utf-8")
    _fails_with(cfg, capsys, "MODIFIED")


def test_seal_refuses_to_reseal_changed_round(tmp_path: Path) -> None:
    cfg = _baseline(tmp_path)
    ledger.seal(cfg, "2026-10-14-r")
    path = cfg.ledger_dir / "2026-10-14-r.jsonl"  # type: ignore[attr-defined]
    path.write_text(path.read_text() + " \n", encoding="utf-8")
    with pytest.raises(SystemExit, match="refusing to re-seal"):
        ledger.seal(cfg, "2026-10-14-r")


def _two_sealed_against_filename_order(cfg: object) -> None:
    """z is sealed before a, so recording order is not filename order."""
    ledger.seal(cfg, "2026-10-14-r")
    for round_id in ("2026-10-15-z", "2026-10-15-a"):
        event = _ours_event(f"{round_id}:1", "add", "planning")
        _write_round(cfg, round_id, event)
        ledger.seal(cfg, round_id)
    assert cli.cmd_build(cfg, _ns()) == 0


def test_seal_appends_recording_order_and_the_loader_reads_it(tmp_path: Path) -> None:
    cfg = _baseline(tmp_path)
    _two_sealed_against_filename_order(cfg)
    order = ["2026-10-14-r.jsonl", "2026-10-15-z.jsonl", "2026-10-15-a.jsonl"]
    ledger.seal(cfg, "2026-10-15-z")  # already sealed: not listed twice
    ledger.seal_report_digest(cfg, "reviews/x.yaml", "digest")  # keeps the list
    manifest = json.loads(cfg.manifest_path.read_text())  # type: ignore[attr-defined]
    assert manifest["round_order"] == order
    _write_round(cfg, "2026-10-13-open", _ours_event("2026-10-13-open:1", "add", "x"))
    names = [p.name for p in loaders._round_files(cfg)]  # type: ignore[arg-type]
    assert names == [*order, "2026-10-13-open.jsonl"]
    current = ledger.effective_by_subject(loaders.load_ledger(cfg)[1])
    assert current["ours:planning"].id == "2026-10-15-a:1"
    record = cfg.skill_records_dir / "engineering" / "planning.md"  # type: ignore[attr-defined]
    text = record.read_text()
    assert text.index("(2026-10-15-a:1)") < text.index(
        "(2026-10-15-z:1)"
    )  # newest first


@pytest.mark.parametrize(
    ("order", "needle"),
    [
        (
            ["2026-10-15-z.jsonl", "2026-10-15-a.jsonl"],
            "2026-10-14-r.jsonl: not listed",
        ),
        (
            ["2026-10-14-r.jsonl", "2026-10-15-z.jsonl", "2026-10-15-a.jsonl"] * 2,
            "2026-10-14-r.jsonl: listed more than once",
        ),
        (
            [
                "2026-10-14-r.jsonl",
                "2026-10-15-z.jsonl",
                "2026-10-15-a.jsonl",
                "2026-10-16-gone.jsonl",
            ],
            "2026-10-16-gone.jsonl: listed but not sealed",
        ),
        ("2026-10-14-r.jsonl", "round_order must be a list"),
        (None, "round_order must be a list"),
    ],
    ids=["missing", "duplicate", "unsealed", "string", "null"],
)
def test_check_refuses_a_bad_round_order(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], order: object, needle: str
) -> None:
    cfg = _baseline(tmp_path)
    _two_sealed_against_filename_order(cfg)
    path = cfg.manifest_path  # type: ignore[attr-defined]
    manifest = json.loads(path.read_text())
    manifest["round_order"] = order
    path.write_text(json.dumps(manifest))
    _fails_with(cfg, capsys, needle)


@pytest.mark.parametrize(
    "order",
    [None, ["2026-10-14-r.jsonl", "2026-10-15-z.jsonl"]],
    ids=["absent", "missing-a-sealed-round"],
)
def test_bad_round_order_refuses_record_build_and_seal(
    tmp_path: Path, order: object
) -> None:
    cfg = _baseline(tmp_path)
    _two_sealed_against_filename_order(cfg)
    path = cfg.manifest_path  # type: ignore[attr-defined]
    manifest = json.loads(path.read_text())
    if order is None:
        del manifest["round_order"]
    else:
        manifest["round_order"] = order
    path.write_text(json.dumps(manifest))
    _write_round(cfg, "2026-10-16-o", _ours_event("2026-10-16-o:1", "add", "x"))
    tree = cfg.ledger_dir.parent  # type: ignore[attr-defined]
    before = {p: p.read_bytes() for p in tree.rglob("*") if p.is_file()}

    payload = json.dumps(_ours_event("2026-10-16-o:2", "add", "planning"))
    for call in (
        lambda: cli.cmd_record(cfg, _rec_ns(json=payload)),
        lambda: cli.cmd_build(cfg, _ns()),
        lambda: ledger.seal(cfg, "2026-10-16-o"),
    ):
        with pytest.raises(SystemExit, match="repair round_order"):
            call()

    assert {p: p.read_bytes() for p in tree.rglob("*") if p.is_file()} == before


def test_more_than_one_open_round(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    cfg = _baseline(tmp_path)
    _write_round(cfg, "2026-10-14-s", _ours_event("2026-10-14-s:1", "add", "planning"))
    cli.cmd_build(cfg, _ns())
    _fails_with(cfg, capsys, "more than one open round")
    with pytest.raises(SystemExit, match="more than one open round"):
        ledger.open_round(cfg)


def test_check_rejects_uncovered_skill_dir(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    cfg = _baseline(tmp_path)
    _write_skill(cfg, "orphan")
    _fails_with(cfg, capsys, "no skills.yaml entry, and not an alias")
    # review 2 #11: no .claude/skills/ at all fails every skills.yaml entry.
    shutil.rmtree(cfg.skills_dir)  # type: ignore[attr-defined]
    _fails_with(cfg, capsys, "skills.yaml: planning: no .claude/skills/planning folder")


def test_check_accepts_alias_stub_and_in_progress(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    cfg = _baseline(tmp_path)
    _write_skill(cfg, "document-review")  # alias of review
    _write_skill(cfg, "cost-estimate")  # stub
    _write_skill(cfg, vocab.IN_PROGRESS_DIR)
    _write_skill(cfg, "review")
    _write_record(
        cfg, "review", "core", "Verification", "Review", aliases=["document-review"]
    )
    assert cli.cmd_build(cfg, _ns()) == 0
    assert cli.cmd_check(cfg, _ns()) == 0
    # lazy records without a traits/ours.yaml entry are reported as a count
    assert "without a traits/ours.yaml entry" in capsys.readouterr().out


# Acceptance 14: skills.yaml and fully generated records.
def test_skills_yaml_and_generated_records(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    cfg = _baseline(tmp_path)
    record = cfg.skill_records_dir / "engineering" / "planning.md"  # type: ignore[attr-defined]
    text = record.read_text(encoding="utf-8")
    # The whole record comes from skills.yaml and SKILL.md: no Capability section.
    assert text.startswith("---\nskill: planning\ndomain: engineering\n")
    assert "\n# planning\n\nA test skill.\n\n<!-- registry:generated traits -->" in text
    assert "## Capability" not in text
    # A skill with no family renders a bare `family:` key, with no trailing space.
    assert "\nfamily:\n" in text
    assert [line for line in text.splitlines() if line != line.rstrip()] == []

    # (a) a hand edit to a record fails until `build`
    record.write_text(text.replace("A test skill.", "Edited."), encoding="utf-8")
    _fails_with(cfg, capsys, "planning.md: generated file is stale")
    assert cli.cmd_build(cfg, _ns()) == 0
    assert cli.cmd_check(cfg, _ns()) == 0

    # (b) an entry with no folder fails; a record no entry generates fails
    _write_record(cfg, "ghost", "core", "U", "Tooling")
    _fails_with(cfg, capsys, "skills.yaml: ghost: no .claude/skills/ghost folder")
    stray = _baseline(tmp_path / "stray")
    (stray.skill_records_dir / "core").mkdir()  # type: ignore[attr-defined]
    (stray.skill_records_dir / "core" / "planning.md").write_text(text)  # type: ignore[attr-defined]
    _fails_with(stray, capsys, "core/planning.md: no skills.yaml entry generates")

    # (c) two active skills in one domain · sub-stage each need a boundary
    two = _baseline(tmp_path / "two")
    _write_skill(two, "slicing")
    _write_record(two, "slicing", "engineering", "Design", "Decomposition")
    assert cli.cmd_build(two, _ns()) == 0
    _fails_with(
        two, capsys, "planning: shares engineering · Decomposition with slicing"
    )
    _write_record(
        two, "planning", "engineering", "Design", "Decomposition", boundary="P."
    )
    _write_record(
        two, "slicing", "engineering", "Design", "Decomposition", boundary="S."
    )
    assert cli.cmd_build(two, _ns()) == 0
    assert cli.cmd_check(two, _ns()) == 0
    slicing = two.skill_records_dir / "engineering" / "slicing.md"  # type: ignore[attr-defined]
    assert "A test skill.\n\n**Boundary:** S.\n\n<!--" in slicing.read_text()

    # (d) strict schema, duplicate-key-safe
    bad = _baseline(tmp_path / "bad")
    path = bad.skills_path  # type: ignore[attr-defined]
    path.write_text(path.read_text() + "planning:\n  domain: core\n")
    _fails_with(bad, capsys, "duplicate key")


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
    assert cli.cmd_gap(cfg, _ns(reference="refrepo", kind=None, beads=False)) == 0
    out = capsys.readouterr().out
    assert "not reviewed" in out and "skill:skills/bar" in out
    assert "present, unruled" in out and "skill:skills/foo" in out
    assert "changed since ruled" in out and "skill:skills/baz" in out
    # reference page shares the same classification, so statuses match
    assert cli.cmd_build(cfg, _ns()) == 0
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
    assert cli.cmd_gap(cfg, _ns(reference="refrepo", kind=None, beads=False)) == 0
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
    return trait_facts._our_tree_hashes(catalogs.build_ours(cfg))[skill]


@pytest.mark.parametrize("in_git", [True, False])
def test_tree_hash_skips_only_git_ignored_files(tmp_path: Path, in_git: bool) -> None:
    root = tmp_path / "harness"
    skill = root / "skills" / "tdd"
    skill.mkdir(parents=True)
    (skill / "SKILL.md").write_text("---\nname: tdd\n---\n", encoding="utf-8")
    if in_git:
        subprocess.run(["git", "init", "-q", str(root)], check=True)
        (root / ".gitignore").write_text("__pycache__/\n", encoding="utf-8")
    before = scan._skill_tree_hash(skill)
    (skill / "__pycache__").mkdir()
    (skill / "__pycache__" / "x.pyc").write_bytes(b"\0cache")
    # Ignored inside a work tree; hashed like any file outside one.
    assert (scan._skill_tree_hash(skill) == before) is in_git
    with_cache = scan._skill_tree_hash(skill)
    (skill / "notes.md").write_text("untracked, not ignored\n", encoding="utf-8")
    assert scan._skill_tree_hash(skill) != with_cache
    if in_git:  # review 2 #14: a wholly ignored folder hashes as empty
        (root / ".gitignore").write_text("skills/\n", encoding="utf-8")
        assert scan._skill_tree_hash(skill) == hashlib.sha256().hexdigest()


@pytest.mark.parametrize("in_git", [True, False])
def test_scan_counts_skip_git_ignored_files(tmp_path: Path, in_git: bool) -> None:
    root = tmp_path / "harness"
    (root / "skills" / "tdd" / "__pycache__").mkdir(parents=True)
    (root / "skills" / "tdd" / "SKILL.md").write_text("---\nname: tdd\n---\n")
    (root / "skills" / "tdd" / "__pycache__" / "x.pyc").write_bytes(b"\0")
    (root / "node_modules").mkdir()
    (root / "node_modules" / "x.js").write_text("x\n")
    (root / "local.json").write_text("{}\n")
    if in_git:
        subprocess.run(["git", "init", "-q", str(root)], check=True)
        (root / ".gitignore").write_text("__pycache__/\nlocal.json\n")
    cat = scan.scan_repo(root, "h", source="working-tree", source_commit=None)
    # In a work tree: ignored files (and .git/) count nowhere; node_modules/ is
    # excluded by rule. Outside one, every file counts.
    if in_git:
        assert (cat.excluded, cat.physical_scanned) == (1, 2)  # SKILL.md, .gitignore
    else:
        assert (cat.excluded, cat.physical_scanned) == (2, 2)  # SKILL.md, local.json
    if in_git:  # review 2 #14: an empty listing stays empty, never falls back
        (root / ".gitignore").write_text("*\n")
        cat = scan.scan_repo(root, "h", source="working-tree", source_commit=None)
        assert (cat.excluded, cat.physical_scanned) == (0, 0)


def _write_defs(cfg: object, text: str) -> None:
    cfg.trait_definitions_path.write_text(text, encoding="utf-8")  # type: ignore[attr-defined]


def _write_traits(cfg: object, text: str) -> None:
    """Route each top-level entry of `text` to its `traits/` file, creating an
    empty catalog for a harness that has none (a harness file needs one)."""
    folder = cfg.traits_dir  # type: ignore[attr-defined]
    if folder.is_dir():
        for old in folder.glob("*.yaml"):
            old.unlink()
    folder.mkdir(exist_ok=True)
    files: dict[str, str] = {}
    name = ""
    for line in text.splitlines(keepends=True):
        if line.strip() and not line.startswith(" "):
            name = loaders.traits_file_for(line.strip().strip('"'))
        files[name] = files.get(name, "") + line
    for name, body in files.items():
        (folder / name).write_text(body, encoding="utf-8")
        repo = name.removesuffix(".yaml")
        if (
            name != loaders.OURS_TRAITS_FILE
            and not (
                cfg.catalogs_dir / f"{repo}.json"  # type: ignore[attr-defined]
            ).exists()
        ):
            _catalog(cfg, repo, [])


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


def _analysis(
    traits: list[str], tree_hash: str = TREE, extra: str = "", indent: str = "      "
) -> str:
    return (
        f'{indent}tree_hash: "{tree_hash}"\n{indent}placement: {_PLACEMENT}\n'
        f"{indent}traits: [{', '.join(traits)}]\n{extra}"
    )


def _upstream_entry(
    subject: str,
    traits: list[str],
    tree_hash: str = TREE,
    reviewed_sha: str = "abc1234",
    extra: str = "",
) -> str:
    """An entry with one accepted analysis at `reviewed_sha`; `extra` holds
    further analysis fields, indented six spaces."""
    return (
        f'{subject}:\n  accepted: "{reviewed_sha}"\n  proposed: null\n'
        f'  analyses:\n    "{reviewed_sha}":\n' + _analysis(traits, tree_hash, extra)
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
    assert cli.cmd_build(cfg, _ns()) == 0
    assert cli.cmd_check(cfg, _ns()) == 0


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
        + f"{SUBJECT}:\n  accepted: 123456\n  proposed: null\n"
        f"  analyses:\n    123456:\n" + _analysis(["seams"]),
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
    assert cli.cmd_build(dp, _ns()) == 0
    assert cli.cmd_check(dp, _ns()) == 0

    # (e) a trait-level checkpoint whose entry reviewed_sha differs
    e = _trait_cfg(tmp_path / "e")
    th = _tree_hash_of(e, "tdd")
    _write_traits(
        e,
        _ours_entry("tdd", th, ["seams"])
        + _upstream_entry(SUBJECT, ["seams"], reviewed_sha="fff9999"),
    )
    _fails_with(e, capsys, "analysis sha fff9999 disagrees with the checkpoint")

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


def test_whole_skill_checkpoint_in_trait_level_round(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """With neither an entry nor trait rulings, a checkpoint stays whole-skill
    in a trait-level round, but only as defer, reject or out-of-scope (3.6)."""

    def cfg_with(
        base: Path, kind: str, round_id: str = "2026-10-14-r", flagged: bool = True
    ) -> object:
        cfg = _make_cfg(base)
        _write_skill(cfg, "tdd")
        _write_record(cfg, "tdd", "engineering", "Design", "Specification")
        _write_defs(cfg, _defs("seams"))
        _write_traits(cfg, _ours_entry("tdd", _tree_hash_of(cfg, "tdd"), ["seams"]))
        extra = {"adaptation": {"merged_from": [], "modifications": ["m"]}}
        _write_round(
            cfg,
            round_id,
            _checkpoint(f"{round_id}:1", kind, "tdd", **extra),
            trait_level=flagged,
        )
        assert cli.cmd_build(cfg, _ns()) == 0
        return cfg

    ok = cfg_with(tmp_path / "reject", "reject")
    assert cli.cmd_build(ok, _ns()) == 0
    assert cli.cmd_check(ok, _ns()) == 0
    _fails_with(
        cfg_with(tmp_path / "adopt", "adopt"),
        capsys,
        "a whole skill is never adopted without its traits",
    )
    # review 2 #5: outside pre_trait_rounds, whatever the round's flag.
    for kind in ("adopt", "adopt-merged"):
        _fails_with(
            cfg_with(tmp_path / f"later-{kind}", kind, "2026-10-20-r", flagged=False),
            capsys,
            "a whole skill is never adopted without its traits",
        )
    later = cfg_with(tmp_path / "later-reject", "reject", "2026-10-20-r", False)
    assert cli.cmd_check(later, _ns()) == 0


def test_awaiting_trait_ruling(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Only a pre-trait round's checkpoint is grandfathered; every later one is
    judged by the trait-level predicate (§5, review r1 #3)."""

    def cfg_at(
        base: Path, round_id: str, sha: str, *traits: dict, accepted: bool = True
    ) -> object:
        cfg = _make_cfg(base)
        _write_skill(cfg, "tdd")
        _write_record(cfg, "tdd", "engineering", "Design", "Specification")
        _write_defs(cfg, _defs("seams"))
        entry = _upstream_entry(SUBJECT, ["seams"], reviewed_sha=sha)
        if not accepted:  # proposed only, as migrated
            entry = entry.replace(
                f'accepted: "{sha}"\n  proposed: null',
                f'accepted: null\n  proposed: "{sha}"',
            )
        _write_traits(cfg, entry)
        _catalog(cfg, "refrepo", [_cap("skill", "tdd", LOGICAL, "h")])
        _write_round(
            cfg, round_id, _checkpoint(f"{round_id}:1", "reject", "tdd"), *traits
        )
        return cfg

    old = cfg_at(tmp_path / "old", "2026-10-14-migration", "5beb35b", accepted=False)
    assert cli.cmd_build(old, _ns()) == 0
    assert cli.cmd_check(old, _ns()) == 0
    capsys.readouterr()
    assert cli.cmd_gap(old, _ns(reference="refrepo", kind=None, beads=False)) == 0
    out = capsys.readouterr().out
    assert "awaiting trait ruling (1)" in out
    assert (
        f"{LOGICAL}  (checkpoint 2026-10-14-migration:1, traits listed at 5beb35b)"
        in out
    )

    # review 2 #4: grandfathering ends once the skill has an accepted analysis
    promoted = cfg_at(tmp_path / "promoted", "2026-10-14-migration", "5beb35b")
    assert cli.cmd_build(promoted, _ns()) == 0
    _fails_with(promoted, capsys, f"trait 'seams' in {SUBJECT!r} has no effective")
    # … and an accepted analysis needs an effective checkpoint at all
    bare = cfg_at(tmp_path / "bare", "2026-10-14-migration", "5beb35b")
    _write_round(bare, "2026-10-14-migration")
    assert cli.cmd_build(bare, _ns()) == 0
    _fails_with(
        bare, capsys, f"{SUBJECT!r}: accepted analysis 5beb35b has no effective"
    )

    # a newer whole-skill ruling over an older inventory is not grandfathered
    newer = cfg_at(tmp_path / "newer", "2026-10-20-later", "5beb35b")
    _fails_with(newer, capsys, "analysis sha 5beb35b disagrees with the checkpoint")

    # trait-level through its trait rulings, at the entry's sha, without the flag
    ruled = cfg_at(
        tmp_path / "ruled",
        "2026-10-14-r",
        "abc1234",
        _trait("2026-10-14-r:2", "reject", "seams"),
    )
    assert cli.cmd_build(ruled, _ns()) == 0
    assert cli.cmd_check(ruled, _ns()) == 0


# Acceptance 4: the pending lifecycle.
def _pending_cfg(
    base: Path, *events: dict, ours_traits: list[str], checkpoint_skill: str = "tdd"
) -> object:
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
        _checkpoint("2026-10-14-r:1", "adopt", checkpoint_skill),
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
    assert cli.cmd_build(c, _ns()) == 0
    assert cli.cmd_check(c, _ns()) == 0

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
    fwd = ledger.build_lifecycle(loaders.load_ledger(wd)[1])[0]
    assert (subj, "tdd") in ledger.withdrawn_destinations(
        loaders.load_ledger(wd)[1], fwd
    )
    assert cli.cmd_build(wd, _ns()) == 0
    assert cli.cmd_check(wd, _ns()) == 0  # withdrawn: no obligation

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
    fwd = ledger.build_lifecycle(loaders.load_ledger(live)[1])[0]
    assert (subj, "tdd") not in ledger.withdrawn_destinations(
        loaders.load_ledger(live)[1], fwd
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
    assert cli.cmd_build(doc, _ns()) == 0
    assert cli.cmd_check(doc, _ns()) == 0


# Acceptance 5: a modified adoption into a different trait without modification.
def test_modified_adoption_requires_modification(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="modification"):
        models.Event.model_validate(
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
    assert cli.cmd_build(cfg, _ns()) == 0
    assert cli.cmd_check(cfg, _ns()) == 0  # resolves old → survivor, lists seams


# Acceptance 7: withdrawal is per source.
SUBJECT2 = "refrepo:skill:skills/engineering/tdd2"


def _upstream_entry2(traits: list[str]) -> str:
    return (
        f'{SUBJECT2}:\n  accepted: "abc1234"\n  proposed: null\n'
        f'  analyses:\n    "abc1234":\n' + _analysis(traits, "T2")
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
    assert cli.cmd_build(ok, _ns()) == 0
    assert cli.cmd_check(ok, _ns()) == 0

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
    assert cli.cmd_build(warn, _ns()) == 0
    assert cli.cmd_check(warn, _ns()) == 0
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
    ledger.seal(adopted, "2026-09-01-old")
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
    assert cli.cmd_build(adopted, _ns()) == 0
    assert cli.cmd_check(adopted, _ns()) == 0
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
    # A (seams), adopted at oldsha, moved to `removed` at abc1234; B (newmech)
    # is added there and rejected, carrying A. Membership is by sha (3.9).
    _write_traits(
        cfg,
        _ours_entry("tdd", _tree_hash_of(cfg, "tdd"), ["seams"])
        + _upstream_entry(
            SUBJECT,
            ["newmech"],
            extra='      added: {newmech: "x"}\n      removed: {seams: "x"}\n',
        )
        + '    "0ddba11":\n'
        + _analysis(["seams"]),
    )
    adopt_a = _trait("2026-10-14-r:2", "adopt", "seams", skill="tdd")
    adopt_a["source"] = {**adopt_a["source"], "sha": "0ddba11"}  # type: ignore[dict-item]
    _write_round(
        cfg,
        "2026-10-14-r",
        _checkpoint("2026-10-14-r:1", "reject", "tdd"),
        adopt_a,
        _trait(
            "2026-10-14-r:3",
            "reject",
            "newmech",
            carried_from=[f"{SUBJECT}#seams"],
        ),
        trait_level=True,
    )
    assert cli.cmd_build(cfg, _ns()) == 0
    assert cli.cmd_check(cfg, _ns()) == 0
    record = (cfg.skill_records_dir / "engineering" / "tdd.md").read_text()  # type: ignore[attr-defined]
    sources = record.split(record_views.SOURCES_OPEN)[1].split(
        record_views.SOURCES_CLOSE
    )[0]
    assert "upstream replaced it with newmech (reject)" in sources


# Acceptance 11: TRAITS.md by-trait view lists ours and upstream holders.
def test_traits_md_by_trait_view(tmp_path: Path) -> None:
    cfg = _trait_cfg(tmp_path)
    assert cli.cmd_build(cfg, _ns()) == 0
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
    assert cli.cmd_build(cfg, _ns()) == 0
    md = cfg.traits_md_path.read_text(encoding="utf-8")  # type: ignore[attr-defined]
    assert "adopt, pending cr-7 → tdd#seams" in md
    # review r1 #12: one lineage entry, labelled pending, no checkpoint duplicate
    record = (cfg.skill_records_dir / "engineering" / "tdd.md").read_text()  # type: ignore[attr-defined]
    lineage = record.split(record_views.LINEAGE_OPEN)[1].split(
        record_views.LINEAGE_CLOSE
    )[0]
    assert lineage.strip() == f"- **{SUBJECT}#seams** @ abc1234 (pending cr-7)"


def test_trait_identity_rules() -> None:
    # adopt-merged is not a valid trait kind
    with pytest.raises(ValueError, match="trait kinds"):
        models.Event.model_validate(_trait("r:1", "adopt-merged", "seams", skill="tdd"))
    # a trait subject must name a skill logical id
    agent = _trait("r:1", "adopt", "seams", skill="tdd")
    agent["subject"] = "refrepo:agent:agents/x#seams"
    agent["source"] = {"repo": "refrepo", "logical_id": "agent:agents/x"}  # type: ignore[assignment]
    with pytest.raises(ValueError, match="skills only"):
        models.Event.model_validate(agent)
    # slugs are validated
    with pytest.raises(ValueError, match="valid trait slug"):
        models.Event.model_validate(_trait("r:1", "adopt", "bad slug", skill="tdd"))
    # review r1 #11: contextual fields only where §5 defines them
    for ev, needle in (
        (_trait("r:1", "reject", "seams", pending="cr-1"), "only for a trait adopt"),
        (_trait("r:1", "reject", "seams", withdraws=["x#y"]), "ours-side update"),
        (_trait("r:1", "adopt", "seams", skill="tdd", pending=" "), "is empty"),
    ):
        with pytest.raises(ValueError, match=needle):
            models.Event.model_validate(ev)


def test_reference_page_traits_column(tmp_path: Path) -> None:
    cfg = _trait_cfg(tmp_path)
    _catalog(cfg, "refrepo", [_cap("skill", "tdd", LOGICAL, "hcur")])
    assert cli.cmd_build(cfg, _ns()) == 0
    page = (cfg.references_dir / "refrepo.md").read_text(encoding="utf-8")  # type: ignore[attr-defined]
    assert "Traits" in page.split("\n")[6]  # the header row carries a Traits column
    assert "1 adopt" in page


@pytest.mark.parametrize("with_traits", [False, True])
def test_reference_page_names_the_renamed_skill(
    tmp_path: Path, with_traits: bool
) -> None:
    """A whole-skill adoption into a skill we later renamed shows the survivor
    under Into ours, whether or not the reference has trait analysis."""
    cfg = _trait_cfg(tmp_path) if with_traits else _make_cfg(tmp_path)
    _write_skill(cfg, "slicing")
    _write_record(cfg, "slicing", "engineering", "Design", "Decomposition")
    caps = [_cap("skill", "x", "skill:skills/x", "h")]
    if with_traits:
        caps.append(_cap("skill", "tdd", LOGICAL, "hcur"))
    _catalog(cfg, "refrepo", caps)
    _write_round(
        cfg,
        "2026-10-14-migration",
        _ours_event("2026-10-14-migration:1", "add", "planning"),
        _ref_event(
            "2026-10-14-migration:2",
            "adopt",
            "refrepo",
            "skill:skills/x",
            skill="planning",
        ),
        {
            **_ours_event("2026-10-14-migration:3", "rename", "planning"),
            "skill": "slicing",
            "why": "renamed planning to slicing",
        },
    )
    assert cli.cmd_build(cfg, _ns()) == 0
    page = (cfg.references_dir / "refrepo.md").read_text(encoding="utf-8")  # type: ignore[attr-defined]
    row = next(line for line in page.splitlines() if "`skill:skills/x`" in line)
    assert row.split(" | ")[3] == "slicing"
    assert ("Traits" in page) is with_traits


def test_build_refuses_invalid_trait_files(tmp_path: Path) -> None:
    """review r1 #10: a trait file that fails to load stops build before writing."""
    cfg = _trait_cfg(tmp_path)
    assert cli.cmd_build(cfg, _ns()) == 0
    before = cfg.traits_md_path.read_text(encoding="utf-8")  # type: ignore[attr-defined]
    _write_defs(
        cfg, f"seams:\n  definition: x.\n  placement: {_PLACEMENT}\n  bogus: 1\n"
    )
    with pytest.raises(SystemExit, match="trait files have errors"):
        cli.cmd_build(cfg, _ns())
    assert cfg.traits_md_path.read_text(encoding="utf-8") == before  # type: ignore[attr-defined]


def test_traits_yaml_keys_and_metadata(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """review r1 #6 and #7: metadata keys and upstream identities are checked."""
    cases = [
        # #6: an undefined removed trait, with an effective ruling on it
        (
            _upstream_entry(
                SUBJECT, ["seams"], extra='      removed: {ghost: "oldsha"}\n'
            ),
            "removed trait 'ghost' is undefined",
            [_trait("2026-10-14-r:3", "reject", "ghost")],
        ),
        # #6: a note on a trait the entry does not hold
        (
            _upstream_entry(SUBJECT, ["seams"], extra="      notes: {other: n}\n"),
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
    # supersede the effective pending adopt (not the reject); one that does not
    # is a new decision, with no source to copy (review 2 #2): at another sha
    # it needs that analysis; in this pre-trait round it needs no citation.
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
    assert cli.cmd_build(changed, _ns()) == 0
    _fails_with(changed, capsys, "2026-10-14-r:4: no analysis of")

    skipped = _pending_cfg(
        tmp_path / "skipped",
        reject,
        pending,
        _trait("2026-10-14-r:4", "adopt", "seams", skill="tdd"),
        ours_traits=["seams"],
    )
    assert cli.cmd_build(skipped, _ns()) == 0
    assert cli.cmd_check(skipped, _ns()) == 0, capsys.readouterr().err

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
    assert cli.cmd_build(good, _ns()) == 0
    assert cli.cmd_check(good, _ns()) == 0


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
    assert cli.cmd_build(cfg, _ns()) == 0
    _fails_with(cfg, capsys, "new subject")


# --- slice 3: traits/ folder, entries, doc: entries ------------------------------


# Acceptance 15: a traits/ key in the wrong file, or in two files, fails.
def test_traits_folder_placement(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    cfg = _trait_cfg(tmp_path / "wrong")
    folder = cfg.traits_dir  # type: ignore[attr-defined]
    ours = folder / "ours.yaml"
    up = folder / "refrepo.yaml"
    ours.write_text(ours.read_text() + up.read_text())
    up.unlink()
    _fails_with(
        cfg, capsys, f"traits/ours.yaml: {SUBJECT}: belongs in traits/refrepo.yaml"
    )

    two = _trait_cfg(tmp_path / "two")
    folder = two.traits_dir  # type: ignore[attr-defined]
    (folder / "ours.yaml").write_text(
        (folder / "ours.yaml").read_text() + (folder / "refrepo.yaml").read_text()
    )
    _fails_with(
        two, capsys, f"traits/refrepo.yaml: {SUBJECT}: also in traits/ours.yaml"
    )

    nocat = _trait_cfg(tmp_path / "nocat")
    (nocat.catalogs_dir / "refrepo.json").unlink()  # type: ignore[attr-defined]
    _fails_with(nocat, capsys, "traits/refrepo.yaml: no catalog for harness 'refrepo'")


def test_entry_pointers_and_analysis_keys(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    head = f"{SUBJECT}:\n"
    one = '  analyses:\n    "abc1234":\n' + _analysis(["seams"])
    cases = [
        (head + "  accepted: null\n  proposed: null\n" + one, "must be set"),
        (
            head + '  accepted: "abc1234"\n  proposed: "abc1234"\n' + one,
            "same analysis",
        ),
        (
            head + '  accepted: "abc1234"\n  proposed: "zzz"\n' + one,
            "'zzz' names no analysis",
        ),
        (
            _upstream_entry(
                SUBJECT, ["seams"], extra='      changed: {other: "abc1234"}\n'
            ),
            "changed trait 'other' is not in the entry",
        ),
        (
            _upstream_entry(
                SUBJECT, ["seams"], extra='      added: {ghost: "abc1234"}\n'
            ),
            "added trait 'ghost' is undefined",
        ),
    ]
    for i, (entry, needle) in enumerate(cases):
        cfg = _trait_cfg(tmp_path / str(i))
        _write_defs(cfg, _defs("seams", "other"))
        th = _tree_hash_of(cfg, "tdd")
        _write_traits(cfg, _ours_entry("tdd", th, ["seams"]) + entry)
        _fails_with(cfg, capsys, needle)


def test_trait_level_needs_an_accepted_analysis(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A proposed-only entry leaves a whole-skill checkpoint valid; the same
    entry with `accepted` set makes the checkpoint trait-level."""

    def setup(base: Path, accepted: bool) -> object:
        cfg = _make_cfg(base)
        _write_skill(cfg, "tdd")
        _write_record(cfg, "tdd", "engineering", "Design", "Specification")
        _write_defs(cfg, _defs("seams"))
        pointers = (
            '  accepted: "abc1234"\n  proposed: null\n'
            if accepted
            else '  accepted: null\n  proposed: "abc1234"\n'
        )
        _write_traits(
            cfg,
            f"{SUBJECT}:\n{pointers}"
            + '  analyses:\n    "abc1234":\n'
            + _analysis(["seams"]),
        )
        # A later round: a pre-trait one would grandfather the checkpoint.
        defer = _checkpoint("2026-10-20-r:1", "defer", "tdd", revisit_when="later")
        _write_round(cfg, "2026-10-20-r", defer)
        assert cli.cmd_build(cfg, _ns()) == 0
        return cfg

    assert cli.cmd_check(setup(tmp_path / "proposed", False), _ns()) == 0
    _fails_with(
        setup(tmp_path / "accepted", True),
        capsys,
        f"trait 'seams' in {SUBJECT!r} has no effective ruling",
    )


def test_catalog_tree_hash_matches_newest_analysis_while_pinned(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    def setup(base: Path, cap_hash: str, pin: str) -> object:
        cfg = _trait_cfg(base)
        cap = _cap("skill", "tdd", LOGICAL, "h") | {"tree_hash": cap_hash}
        _catalog(cfg, "refrepo", [cap])
        data = json.loads((cfg.catalogs_dir / "refrepo.json").read_text())  # type: ignore[attr-defined]
        data["source_commit"] = pin
        (cfg.catalogs_dir / "refrepo.json").write_text(json.dumps(data))  # type: ignore[attr-defined]
        assert cli.cmd_build(cfg, _ns()) == 0
        return cfg

    assert cli.cmd_check(setup(tmp_path / "ok", TREE, "abc1234def"), _ns()) == 0
    assert cli.cmd_check(setup(tmp_path / "moved", "other", "fff0000"), _ns()) == 0
    _fails_with(
        setup(tmp_path / "bad", "other", "abc1234def"),
        capsys,
        "analysis abc1234 tree_hash disagrees with the catalog",
    )


def _doc_cfg(base: Path, key: str = "doc:AGENTS.md") -> object:
    cfg = _trait_cfg(base)
    rel = key[len("doc:") :]
    path = cfg.repo_root / rel  # type: ignore[attr-defined]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("Run the checks before claiming done.\n", encoding="utf-8")
    th = trait_facts._doc_tree_hash(rel, path.read_bytes())
    folder = cfg.traits_dir  # type: ignore[attr-defined]
    (folder / "ours.yaml").write_text(
        (folder / "ours.yaml").read_text()
        + f'{key}:\n  tree_hash: "{th}"\n  traits: [seams]\n'
    )
    assert cli.cmd_build(cfg, _ns()) == 0
    return cfg


def test_doc_entries(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    cfg = _doc_cfg(tmp_path / "ok")
    assert cli.cmd_check(cfg, _ns()) == 0
    md = cfg.traits_md_path.read_text(encoding="utf-8")  # type: ignore[attr-defined]
    assert "### Docs\n\n#### doc:AGENTS.md\n- `seams`: Does seams.\n" in md
    assert "- ours: `tdd`\n- `doc:AGENTS.md`\n" in md
    assert (
        cli.cmd_check(_doc_cfg(tmp_path / "rc", "doc:.repo-context/style.md"), _ns())
        == 0
    )

    (cfg.repo_root / "AGENTS.md").write_text("Edited.\n")  # type: ignore[attr-defined]
    _fails_with(cfg, capsys, "doc:AGENTS.md: tree_hash is stale")
    (cfg.repo_root / "AGENTS.md").unlink()  # type: ignore[attr-defined]
    _fails_with(cfg, capsys, "doc:AGENTS.md: no such file")
    deep = _doc_cfg(tmp_path / "deep", "doc:docs/x.md")
    _fails_with(
        deep, capsys, "a doc: key is AGENTS.md, .repo-context/<file> or a playbook"
    )


def test_retained_adoption_may_target_doc_agents_md(tmp_path: Path) -> None:
    cfg = _doc_cfg(tmp_path)
    _write_round(
        cfg,
        "2026-10-14-r",
        _checkpoint("2026-10-14-r:1", "adopt", "doc:AGENTS.md"),
        _trait("2026-10-14-r:2", "adopt", "seams", skill="doc:AGENTS.md"),
        trait_level=True,
    )
    assert cli.cmd_build(cfg, _ns()) == 0
    assert cli.cmd_check(cfg, _ns()) == 0


# --- a playbook renamed (plan 45 §5b, P2 U0) ----------------------------------

MEND_PATH = ".claude/skills/mvp-mode/playbooks/mend.md"


def _steps() -> Any:
    """The playbook fixtures live in `test_steps`, which imports this module,
    so it is imported when a test runs."""
    from tests.curation import test_steps

    return test_steps


def _rename(cfg: object, old: str, new: str) -> int:
    fields = {"kind": "rename", "subject": old, "skill": new, "why": "renamed"}
    return cli.cmd_record(cfg, _rec_ns(json=json.dumps(fields)))  # type: ignore[arg-type]


def _renamed_playbook(base: Path, *, rename: bool = True) -> object:
    """`fix` holds a whole-capability `adopt-merged` (shaped like
    `2026-11-02-pilot-2:013`) and the adopted trait `gate`. Its file and
    reference folder move to `mend`; `record` adds `mend`, then renames
    `fix` into it."""
    st = _steps()
    old, new = f"doc:{st.FIX_PATH}", f"doc:{MEND_PATH}"
    cfg = st._playbook_cfg(base)
    caps = [_cap("skill", "tdd", LOGICAL, "hcur"), _cap("skill", "x", "skill:x", "h")]
    _catalog(cfg, "refrepo", caps)
    merged = _ref_event(
        "2026-10-14-owner-review:1",
        "adopt-merged",
        "refrepo",
        "skill:x",
        skill=old,
        adaptation={"merged_from": ["x"]},
    )
    _write_round(cfg, "2026-10-14-owner-review", merged)
    ledger.seal(cfg, "2026-10-14-owner-review")  # type: ignore[arg-type]
    _write_round(
        cfg,
        "2026-10-14-r",
        _checkpoint("2026-10-14-r:1", "adopt", "tdd"),
        _trait("2026-10-14-r:2", "adopt", "seams", skill="tdd"),
        _trait("2026-10-14-r:3", "adopt", "gate", skill=old),
        *st._baselines(cfg),
        trait_level=True,
    )
    analysis = cfg.traits_dir / "refrepo.yaml"  # type: ignore[attr-defined]
    analysis.write_text(analysis.read_text().replace("[seams]", "[seams, gate]"))
    folder = cfg.playbooks_dir  # type: ignore[attr-defined]
    (folder / "fix").rename(folder / "mend")
    (folder / "fix.md").unlink()
    mend = st.FIX.replace("fix#", "mend#").replace("fix/notes", "mend/notes")
    st._write_playbook(cfg, "mend", mend)
    assert st._record(cfg, "add", new) == 0
    if rename:
        assert _rename(cfg, old, new) == 0
    assert cli.cmd_build(cfg, _ns()) == 0  # type: ignore[arg-type]
    return cfg


def test_a_renamed_playbook_keeps_its_adoptions(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Without the rename, the moved playbook's old event and adoptions fail;
    with it, they follow the new path: the lifecycle, the target check, the
    target hash and the reference page's current destination."""
    st = _steps()
    old, new = f"doc:{st.FIX_PATH}", f"doc:{MEND_PATH}"
    stuck = _renamed_playbook(tmp_path / "stuck", rename=False)
    assert cli.cmd_check(stuck, _ns()) == 1  # type: ignore[arg-type]
    err = capsys.readouterr().err
    assert f"{st.FIX_PATH}: no such playbook, but 2026-10-14-r:100" in err
    assert f"has an invalid skill target {old!r}" in err

    cfg = _renamed_playbook(tmp_path / "moved")
    assert cli.cmd_check(cfg, _ns()) == 0, capsys.readouterr().err  # type: ignore[arg-type]
    events = loaders.load_ledger(cfg)[1]  # type: ignore[arg-type]
    forward, _ = ledger.build_lifecycle(ledger.live_events(events))
    assert ledger.resolve_skill(old, forward) == new
    want = st.steps.playbook_tree_hash(cfg, MEND_PATH)
    assert _target_hash(cfg, old, events) == want  # type: ignore[arg-type]
    page = (cfg.references_dir / "refrepo.md").read_text(encoding="utf-8")  # type: ignore[attr-defined]
    row = next(line for line in page.splitlines() if "`skill:x`" in line)
    assert row.split(" | ")[3] == new

    # Status and a withdrawal under the new path see the adoption made under
    # the old one.
    gate = f"{SUBJECT}#gate"

    def label() -> str:
        context = st.reports.load_context(cfg)
        return str(st.status.provisions(context)[gate])

    assert label() == "delivered"
    mend = (cfg.playbooks_dir / "mend.md").read_text()  # type: ignore[attr-defined]
    st._write_playbook(cfg, "mend", mend.replace("[gate]", "[]"))
    assert st._record(cfg, "update", new, withdraws=[gate]) == 0
    assert cli.cmd_build(cfg, _ns()) == 0  # type: ignore[arg-type]
    assert cli.cmd_check(cfg, _ns()) == 0, capsys.readouterr().err  # type: ignore[arg-type]
    assert label() == "withdrawn"


@pytest.mark.parametrize(
    "new",
    [
        "doc:.claude/skills/mvp-mode/playbooks/gone.md",
        "doc:.claude/skills/mvp-mode/playbooks/fix/notes.md",
        "doc:AGENTS.md",
        "tdd",
    ],
)
def test_record_refuses_a_rename_onto_no_playbook(tmp_path: Path, new: str) -> None:
    st = _steps()
    cfg = st._playbook_cfg(tmp_path)
    (cfg.repo_root / "AGENTS.md").write_text("x\n")  # type: ignore[attr-defined]
    with pytest.raises(SystemExit, match="is not a playbook file"):
        _rename(cfg, f"doc:{st.FIX_PATH}", new)


def test_a_playbook_renames_only_onto_another_playbook_path() -> None:
    """A hand-written rename cannot move a playbook onto a skill or itself."""
    st = _steps()
    old = f"doc:{st.FIX_PATH}"
    base = {"type": "event", "id": "r:1", "date": "2026-10-14", "kind": "rename"}
    for new in ("tdd", "ours:tdd", old):
        with pytest.raises(ValueError, match="renamed only to another `doc:`"):
            models.Event.model_validate(
                base | {"subject": old, "skill": new, "why": "w"}
            )


def test_a_renamed_away_playbook_needs_its_survivor_add(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A rename whose survivor has no `add` or `update` leaves no hashed
    playbook behind, and one whose old path is no playbook would forward that
    file's adoptions, so `check` fails."""
    st = _steps()
    cfg = st._playbook_cfg(tmp_path)
    gone = "doc:.claude/skills/mvp-mode/playbooks/gone.md"
    rename = st._baselines(cfg)[1] | {"id": "2026-10-14-r:102", "kind": "rename"}
    (cfg.playbooks_dir / "ship.md").unlink()  # type: ignore[attr-defined]
    del rename["target_tree_hash"]
    path = cfg.ledger_dir / "2026-10-14-r.jsonl"  # type: ignore[attr-defined]
    agents = rename | {"id": "2026-10-14-r:103", "subject": "doc:AGENTS.md"}
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(rename | {"skill": gone}) + "\n")
        handle.write(json.dumps(agents | {"skill": f"doc:{st.FIX_PATH}"}) + "\n")
    assert cli.cmd_build(cfg, _ns()) == 0  # type: ignore[arg-type]
    assert cli.cmd_check(cfg, _ns()) == 1  # type: ignore[arg-type]
    err = capsys.readouterr().err
    assert (
        f"2026-10-14-r:102: doc:{st.SHIP_PATH} is renamed to {gone}, which has "
        f"no effective `add` or `update`"
    ) in err
    assert "2026-10-14-r:103: doc:AGENTS.md names no playbook file" in err


def test_adopt_target_follows_a_playbook_rename() -> None:
    """A trait adopted into a renamed playbook renders under the new `doc:`
    label; a `kind:name` target stays verbatim."""
    st = _steps()
    old, new = f"doc:{st.FIX_PATH}", f"doc:{MEND_PATH}"
    forward = {old: new, "command:x": "command:y"}
    for target, want in ((old, new), ("command:x", "command:x")):
        adopt = models.Event.model_validate(
            _trait("r:1", "adopt", "gate", skill=target)
        )
        assert ledger._adopt_target(adopt, forward) == want


@pytest.mark.parametrize("kind", ["add", "update"])
def test_a_renamed_away_playbook_path_is_not_reused(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], kind: str
) -> None:
    """`add` or `update` of a path a live rename forwards is refused by
    `record` and `check`; once that rename is superseded, the path is free
    again."""
    st = _steps()
    old = f"doc:{st.FIX_PATH}"
    cfg = _renamed_playbook(tmp_path)
    renamed = st._last_event(cfg)["id"]
    st._write_playbook(cfg, "fix", st.FIX)
    (cfg.playbooks_dir / "fix").mkdir()  # type: ignore[attr-defined]
    (cfg.playbooks_dir / "fix" / "notes.md").write_text("Notes.\n")  # type: ignore[attr-defined]
    with pytest.raises(SystemExit, match=f"retired by rename {renamed}"):
        st._record(cfg, kind, old)
    path = cfg.ledger_dir / "2026-10-14-r.jsonl"  # type: ignore[attr-defined]
    before = path.read_text(encoding="utf-8")
    readd = st._baselines(cfg)[0] | {"id": "2026-10-14-r:900", "kind": kind}
    path.write_text(before + json.dumps(readd) + "\n", encoding="utf-8")
    _fails_with(
        cfg, capsys, f"2026-10-14-r:900: {kind} reintroduces {old!r}, retired by rename"
    )
    path.write_text(before, encoding="utf-8")
    assert st._record(cfg, kind, old, supersedes=[renamed]) == 0
    assert cli.cmd_build(cfg, _ns()) == 0  # type: ignore[arg-type]
    assert cli.cmd_check(cfg, _ns()) == 0, capsys.readouterr().err  # type: ignore[arg-type]


def test_plain_name_lifecycle_is_unchanged() -> None:
    """Regression (unchanged code): a skill renamed, then merged into a
    playbook, resolves to it under its plain names, renders with its trait
    id, and its old name still cannot come back."""
    st = _steps()
    playbook = f"doc:{st.FIX_PATH}"
    events = [
        models.Event.model_validate(e)
        for e in (
            _ours_event("r:1", "add", "old"),
            _ours_event("r:2", "rename", "mid", subject="ours:old"),
            _ours_event("r:3", "merge", playbook, subject="ours:mid"),
            _ours_event("r:4", "add", "old"),
        )
    ]
    forward, _ = ledger.build_lifecycle(events)
    assert forward == {"old": "mid", "mid": playbook}
    adopt = models.Event.model_validate(_trait("r:5", "adopt", "seams", skill="old"))
    assert ledger._adopt_target(adopt, forward) == f"{playbook}#seams"
    assert checks_ledger.reuse_errors(events) == [
        "r:4: add reintroduces 'old', retired by rename r:2"
    ]
