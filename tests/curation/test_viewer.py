"""The registry viewer (`registry.py viewer`), mostly built from this
repository's own registry: it is deterministic, its kinds match the unit
folders, it links playbooks and skills both ways, adoptions follow renames,
provenance follows retained adoptions, an unknown change baseline stays
unknown, and no text can break out of the embedded data."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from curation.registry.config import RegistryConfig
from curation.registry.ledger import build_lifecycle, live_events, resolve_skill
from curation.registry.models import ChangeInfo, Event
from curation.registry.reports import load_context
from curation.registry.views import viewer

PLAN = "doc:.claude/skills/mvp-mode/playbooks/plan.md"


@pytest.fixture(scope="module")
def cfg() -> RegistryConfig:
    return RegistryConfig.default()


@pytest.fixture(scope="module")
def built(cfg: RegistryConfig) -> viewer.Built:
    return viewer.build(cfg)


def test_two_builds_render_the_same_bytes(
    cfg: RegistryConfig, built: viewer.Built
) -> None:
    assert viewer.render(cfg, built) == viewer.render(cfg, viewer.build(cfg))


def test_playbook_kind_holds_every_playbook_file(
    cfg: RegistryConfig, built: viewer.Built
) -> None:
    shown = sorted(
        u["name"] for u in viewer.page_data(built)["ours"] if u["kind"] == "playbook"
    )
    assert shown == sorted(p.stem for p in cfg.playbooks_dir.glob("*.md"))


def test_plan_and_the_skill_it_calls_link_both_ways(built: viewer.Built) -> None:
    assert "settle-open-questions" in built.ours[PLAN]["links"]
    assert PLAN in built.ours["settle-open-questions"]["links"]


def test_adoptions_into_a_renamed_skill_land_on_its_current_name(
    cfg: RegistryConfig, built: viewer.Built
) -> None:
    ctx = load_context(cfg)
    forward, _ = build_lifecycle(live_events(ctx.events))
    renamed = [
        e
        for e in ctx.current.values()
        if e.kind in ("adopt", "adopt-merged") and e.skill in forward
    ]
    assert renamed, "the ledger has adoptions into an old name to resolve"
    targets = {k for t in built.tiles.values() for k in t["targets"]}
    targets |= {
        x["to"] for t in built.tiles.values() for x in t["traits"] if x.get("to")
    }
    assert all(resolve_skill(k, forward) == k for k in targets)
    assert "discovery" not in built.ours
    fed_by = set(built.ours["settle-open-questions"]["fed"])
    assert any(e.subject.split("#", 1)[0] in fed_by for e in renamed)


def test_provenance_keeps_each_destination_until_its_own_withdrawal() -> None:
    from tests.curation.test_registry import SUBJECT, _ours_event, _trait

    events = [
        Event.model_validate(e)
        for e in (
            _trait("r:1", "adopt", "x", skill="alpha"),
            _trait("r:2", "adopt", "x", skill="beta", supersedes=["r:1"]),
            _ours_event("r:3", "update", "alpha", withdraws=[f"{SUBJECT}#x"]),
        )
    ]
    prov = viewer.provenance(events, {}, set())
    assert prov["alpha"] == [(f"{SUBJECT}#x", "withdrawn")]
    assert prov["beta"] == [(f"{SUBJECT}#x", "delivered")]


def _withdrawal_registry(tmp_path: Path, *extra: dict) -> RegistryConfig:
    """A fixture registry: an adopt checkpoint into `tdd`, its one trait
    delivered there, then an ours-side update withdrawing it; `extra` events
    follow in the same round."""
    from tests.curation.test_registry import (
        SUBJECT,
        _checkpoint,
        _ours_entry,
        _ours_event,
        _trait,
        _trait_cfg,
        _tree_hash_of,
        _upstream_entry,
        _write_record,
        _write_round,
        _write_traits,
    )

    fx = _trait_cfg(tmp_path)
    fx.router_path.parent.mkdir(parents=True, exist_ok=True)
    fx.router_path.write_text(
        "---\nname: mvp-mode\ndescription: Routes work.\n---\n# MVP mode\n",
        encoding="utf-8",
    )
    _write_record(fx, "mvp-mode", "engineering", "X", "Coordination")
    _write_traits(
        fx,
        _ours_entry("tdd", _tree_hash_of(fx, "tdd"), [])
        + _upstream_entry(SUBJECT, ["seams"]),
    )
    _write_round(
        fx,
        "2026-10-14-r",
        _checkpoint("2026-10-14-r:1", "adopt", "tdd"),
        _trait("2026-10-14-r:2", "adopt", "seams", skill="tdd"),
        _ours_event("2026-10-14-r:3", "update", "tdd", withdraws=[f"{SUBJECT}#seams"]),
        *extra,
        trait_level=True,
    )
    return fx


def test_a_withdrawn_only_trait_leaves_no_target_feeder_or_whole_row(
    tmp_path: Path,
) -> None:
    from tests.curation.test_registry import SUBJECT

    b = viewer.build(_withdrawal_registry(tmp_path))
    assert b.tiles[SUBJECT]["targets"] == {}
    assert b.ours["tdd"]["fed"] == {}
    assert b.ours["tdd"]["prov"] == [
        {"tile": SUBJECT, "trait": "seams", "state": "withdrawn"}
    ]


def test_a_pending_readoption_shows_beside_the_withdrawal(tmp_path: Path) -> None:
    from tests.curation.test_registry import SUBJECT, _trait

    pending = _trait(
        "2026-10-14-r:4",
        "adopt",
        "seams",
        skill="tdd",
        pending="cr-test",
        supersedes=["2026-10-14-r:2"],
    )
    b = viewer.build(_withdrawal_registry(tmp_path, pending))
    states = [r["state"] for r in b.ours["tdd"]["prov"]]
    assert sorted(states) == ["pending", "withdrawn"]
    assert b.tiles[SUBJECT]["targets"] == {"tdd": 1}


def test_an_unknown_change_baseline_reads_unknown_review(
    cfg: RegistryConfig, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        viewer, "_change_info", lambda *a: ChangeInfo(changed="unknown")
    )
    built = viewer.build(cfg)
    ruled = [t for t in built.tiles.values() if t["checkpoint"] and not t["removed"]]
    assert ruled and all(t["change"] == "unknown" and not t["stale"] for t in ruled)
    plugin = built.tiles["cursor_plugins:plugin:harness/pstack/claude-code/pstack"]
    assert plugin["stage_status"] == "unknown, review"


def test_embedded_data_has_no_raw_less_than(
    cfg: RegistryConfig, built: viewer.Built
) -> None:
    sentinel = "A </script> B <!--<script> C"
    built.ours["unslop"]["desc"], before = sentinel, built.ours["unslop"]["desc"]
    try:
        page = viewer.render(cfg, built)
    finally:
        built.ours["unslop"]["desc"] = before
    data = page.split('type="application/json">', 1)[1].split("</script>", 1)[0]
    assert "<" not in data
    ours = {u["id"]: u for u in json.loads(data)["ours"]}
    assert ours["unslop"]["desc"] == sentinel
