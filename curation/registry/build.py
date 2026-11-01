"""Every generated file's content, computed without writing."""

from __future__ import annotations

import json
from pathlib import Path

from curation.registry.catalogs import _normalized_index, build_ours
from curation.registry.config import RegistryConfig
from curation.registry.ledger import (
    build_lifecycle,
    effective_by_subject,
    live_events,
    round_header_by_id,
    superseded_ids,
)
from curation.registry.loaders import (
    _catalog_files,
    load_ledger,
    load_records,
    load_reports,
    load_skills,
    load_trait_definitions,
    load_trait_sharing,
    load_traits,
    record_path,
    skill_description,
)
from curation.registry.reports import load_context, render_report
from curation.registry.status import skill_statuses
from curation.registry.steps import load_playbooks
from curation.registry.traits import _ours_traits, _upstream_traits, shared_traits
from curation.registry.views.index import render_index
from curation.registry.views.records import render_record
from curation.registry.views.references import render_reference
from curation.registry.views.steps_md import render_steps
from curation.registry.views.traits_md import render_traits
from curation.scan.models import Catalog


def build_outputs(cfg: RegistryConfig) -> dict[Path, str]:
    """Every generated file's path → its current content (no writes)."""
    _, events, errors = load_ledger(cfg)
    if errors:
        raise SystemExit("ledger has errors; run `check`:\n" + "\n".join(errors))
    headers = load_ledger(cfg)[0]
    headers_by_id = round_header_by_id(headers)
    live = live_events(events)
    current = effective_by_subject(live)
    dead = superseded_ids(events)  # history: render_record marks superseded events
    forward, _ = build_lifecycle(live)
    definitions, def_errors = load_trait_definitions(cfg)
    traits, trait_errors = load_traits(cfg)
    if def_errors or trait_errors:
        raise SystemExit(
            "trait files have errors; run `check`:\n"
            + "\n".join(def_errors + trait_errors)
        )
    skills, skill_errors = load_skills(cfg)
    if skill_errors:
        raise SystemExit(
            "skills.yaml has errors; run `check`:\n" + "\n".join(skill_errors)
        )
    sharing, sharing_errors = load_trait_sharing(cfg)
    if sharing_errors:
        raise SystemExit(
            "trait-sharing.yaml has errors; run `check`:\n" + "\n".join(sharing_errors)
        )
    playbooks, playbook_errors = load_playbooks(cfg)
    if playbook_errors:
        raise SystemExit(
            "playbooks have errors; run `check`:\n" + "\n".join(playbook_errors)
        )
    ours_traits = _ours_traits(traits)
    upstream_traits = _upstream_traits(traits)
    outputs: dict[Path, str] = {}
    for skill, entry in skills.items():
        path = record_path(cfg, skill, entry.domain)
        outputs[path] = render_record(
            skill,
            entry,
            skill_description(cfg, skill),
            events,
            dead,
            ours_traits,
            definitions,
        )
    records = load_records(cfg)
    outputs[cfg.index_path] = render_index(cfg, records)
    outputs[cfg.traits_md_path] = render_traits(
        cfg,
        current,
        forward,
        definitions,
        traits,
        shared_traits(traits, skills, playbooks),
        sharing,
        playbooks,
    )
    outputs[cfg.steps_md_path] = render_steps(playbooks)
    ours = build_ours(cfg)
    our_ids = ours.by_logical_id()
    normalized = _normalized_index(ours)
    ctx = load_context(cfg)
    for cat_path in _catalog_files(cfg):
        catalog = Catalog.from_dict(json.loads(cat_path.read_text(encoding="utf-8")))
        stages = {s.logical_id: s.stage for s in skill_statuses(ctx, catalog)}
        outputs[cfg.references_dir / f"{cat_path.stem}.md"] = render_reference(
            catalog,
            current,
            our_ids,
            normalized,
            upstream_traits,
            cfg=cfg,
            headers_by_id=headers_by_id,
            forward=forward,
            stages=stages,
        )
    reports, report_errors = load_reports(cfg)
    if report_errors:
        raise SystemExit(
            "reports have errors; run `check`:\n" + "\n".join(report_errors)
        )
    for key, report in reports.items():
        path = cfg.repo_root / key
        outputs[path.with_suffix(".md")] = render_report(path.name, report)
    return outputs
