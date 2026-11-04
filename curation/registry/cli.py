"""Skill + capability registry: the curation tool described in README.md.

Replaces gap.py, ledger.json, aliases.json, export_csv.py and casebook.py with a
single append-only ledger (one JSONL file per round), hand-authored skill
records, and generated reference pages and INDEX. It imports curation.scan
for catalogs.

Commands (see README.md §6):
  gap <harness> [--kind K] [--beads]   capabilities never ruled on, or changed
                                       upstream since ruled, or present-unruled
  ours                                 catalog our own capabilities
  round open <slug> / round seal <id>  start / seal a round file
  record ...                           append one validated event to the open round
  report draft|seal ...                draft a review report / seal a passed one
  status <harness> [--skill X] [--traits]  where each upstream skill stands
  build                                regenerate INDEX.md, references/*.md, records
  check                                validate the ledger, records and generated files
"""

from __future__ import annotations

import argparse
import json
import re
import shlex
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from curation.registry import record as record_events
from curation.registry import reports as report_files
from curation.registry import status as status_view
from curation.registry.build import build_outputs
from curation.registry.catalogs import (
    _normalized_index,
    _removed_upstream,
    build_ours,
    match_to_ours,
    resolve_reference,
)
from curation.registry.changes import _change_info
from curation.registry.checks.decisions import (
    analysis_errors,
    decision_errors,
    defer_errors,
)
from curation.registry.checks.ledger import (
    _check_adopt_merged_adaptation,
    _check_carried_from,
    _check_structure,
    _check_supersession,
    _check_withdraws,
    check_immutable,
)
from curation.registry.checks.playbooks import playbook_errors, playbook_ledger_errors
from curation.registry.checks.policy import policy_problems
from curation.registry.checks.records import (
    _check_block_pairing,
    _check_boundaries,
    _check_effective_targets,
    _check_skill_coverage,
)
from curation.registry.checks.reports import check_reports
from curation.registry.checks.sharing import sharing_problems
from curation.registry.checks.traits import (
    _check_trait_definitions,
    _check_trait_level,
    _check_traits_yaml,
    _retired_trait_warnings,
)
from curation.registry.config import RegistryConfig, _rel
from curation.registry.ledger import (
    _adopt_target,
    _dump,
    _event_dict,
    _is_grandfathered,
    _round_of,
    build_lifecycle,
    effective_by_subject,
    effective_traits_for,
    live_events,
    manifest_reports,
    open_round,
    open_rounds,
    require_round_order,
    round_header_by_id,
    round_order_errors,
    seal,
)
from curation.registry.loaders import (
    load_ledger,
    load_reports,
    load_skills,
    load_trait_definitions,
    load_trait_policy,
    load_trait_sharing,
    load_traits,
    record_path,
    record_paths,
)
from curation.registry.models import (
    ChangeInfo,
    Event,
    Frontmatter,
    RoundHeader,
    UpstreamTraitEntry,
)
from curation.registry.policy import guide_changes, guide_rules
from curation.registry.status import skill_statuses
from curation.registry.steps import load_playbooks, playbook_at, step_changes
from curation.registry.text import _one_line
from curation.registry.traits import _ours_traits, _upstream_traits, shared_traits
from curation.registry.vocab import EVENT_KINDS
from curation.scan.catalog import render_catalog_summary
from curation.scan.models import Catalog


def _today_iso() -> str:
    return datetime.now(tz=UTC).date().isoformat()


_DATE_PREFIX_RE = re.compile(r"^\d{4}-\d{2}-\d{2}-")


def _traits_line(
    subject: str,
    event: Event,
    current: dict[str, Event],
    upstream_traits: dict[str, UpstreamTraitEntry],
    forward: dict[str, str],
) -> str:
    """The per-trait ruling summary for a changed capability (§5). Adopt targets
    are resolved through the lifecycle so renamed/merged skills read true (#10)."""
    entry = upstream_traits.get(subject)
    trait_events = effective_traits_for(current, subject)
    parts: list[str] = []
    if entry:
        for tid in entry.newest.traits:
            ruling = trait_events.get(tid)
            if ruling is None:
                continue
            if ruling.kind == "adopt" and ruling.skill:
                suffix = ", pending" if ruling.pending else ""
                parts.append(f"{tid} adopt→{_adopt_target(ruling, forward)}{suffix}")
            else:
                parts.append(f"{tid} {ruling.kind}")
    if parts:
        return " · ".join(parts)
    if event.adaptation and event.adaptation.modifications:
        return "; ".join(event.adaptation.modifications)
    return _one_line(event.why, 100)


def cmd_gap(cfg: RegistryConfig, args: argparse.Namespace) -> int:
    ref = resolve_reference(cfg, args.reference)
    ours = build_ours(cfg)
    headers, events, errors = load_ledger(cfg)
    if errors:
        for line in errors:
            print(f"error: {line}", file=sys.stderr)
        return 1
    live = live_events(events)
    current = effective_by_subject(live)
    headers_by_id = round_header_by_id(headers)
    traits, _ = load_traits(cfg)
    upstream_traits = _upstream_traits(traits)
    forward, _ = build_lifecycle(live)
    our_ids = ours.by_logical_id()
    normalized = _normalized_index(ours)

    not_reviewed: list[Any] = []
    present_unruled: list[Any] = []
    changed: list[tuple[Any, Event, ChangeInfo]] = []
    hash_unknown: list[tuple[Any, Event, ChangeInfo]] = []
    for cap in ref.capabilities:
        if args.kind and cap.kind.value != args.kind:
            continue
        event = current.get(f"{ref.repo}:{cap.logical_id}")
        if event is None:
            if match_to_ours(cap, our_ids, normalized) is not None:
                present_unruled.append(cap)
            else:
                not_reviewed.append(cap)
            continue
        info = _change_info(cfg, ref, cap, event, headers_by_id.get(_round_of(event)))
        if info.changed == "yes":
            changed.append((cap, event, info))
        elif info.changed == "unknown":
            hash_unknown.append((cap, event, info))

    # Removed upstream: ruled subjects with no catalog entry any more (§5),
    # generated independently of reference records and honoring --kind (review #13).
    removed_upstream = [
        (subject, event)
        for subject, event in _removed_upstream(
            ref.repo, current, set(ref.by_logical_id())
        )
        if not args.kind
        or event.source is None
        or event.source.logical_id.startswith(f"{args.kind}:")
    ]

    # Awaiting trait ruling: a grandfathered pre-trait checkpoint whose subject
    # now has an upstream entry but no trait ruling (§5).
    awaiting = [
        (event, upstream_traits[subject])
        for subject, event in current.items()
        if subject.startswith(f"{ref.repo}:")
        and _is_grandfathered(event, current, upstream_traits, cfg.pre_trait_rounds)
        and (
            not args.kind
            or event.source is None
            or event.source.logical_id.startswith(f"{args.kind}:")
        )
    ]

    lines = [f"## gap: {ref.repo}  ({ref.source})"]
    if not_reviewed:
        lines.append(f"\n### not reviewed ({len(not_reviewed)})")
        for cap in sorted(not_reviewed, key=lambda c: c.logical_id):
            desc = f" — {_one_line(cap.description)}" if cap.description else ""
            lines.append(f"  + {cap.logical_id}{desc}")
    if present_unruled:
        lines.append(f"\n### present, unruled ({len(present_unruled)})")
        for cap in sorted(present_unruled, key=lambda c: c.logical_id):
            lines.append(
                f"  = {cap.logical_id}  (we have the same capability but never ruled)"
            )
    if changed:
        lines.append(f"\n### changed since ruled ({len(changed)})")
        for cap, event, info in sorted(changed, key=lambda t: t[0].logical_id):
            lines.append(
                f"  ~ {cap.logical_id}  (ruled {event.kind} in {_round_of(event)})"
            )
            if info.diff_cmd:
                suffix = f"  [{info.label}]" if info.label else ""
                lines.append(f"    diff: {info.diff_cmd}{suffix}")
            lines.append(
                "    traits: "
                + _traits_line(
                    f"{ref.repo}:{cap.logical_id}",
                    event,
                    current,
                    upstream_traits,
                    forward,
                )
            )
    if hash_unknown:
        lines.append(f"\n### baseline unknown — review ({len(hash_unknown)})")
        for cap, event, info in sorted(hash_unknown, key=lambda t: t[0].logical_id):
            lines.append(
                f"  ? {cap.logical_id}  (ruled {event.kind}, no usable baseline)"
            )
    if removed_upstream:
        lines.append(f"\n### removed upstream ({len(removed_upstream)})")
        for subject, event in sorted(removed_upstream, key=lambda t: t[0]):
            dest = f" → {event.skill}" if event.skill else ""
            lines.append(f"  - {subject}  (last ruled {event.kind}{dest})")
    if awaiting:
        lines.append(f"\n### awaiting trait ruling ({len(awaiting)})")
        for event, entry in sorted(awaiting, key=lambda t: t[0].subject):
            lines.append(
                f"  * {event.subject.split(':', 1)[1]}  (checkpoint {event.id}, "
                f"traits listed at {entry.newest_sha})"
            )
    if not (
        not_reviewed
        or present_unruled
        or changed
        or hash_unknown
        or removed_upstream
        or awaiting
    ):
        lines.append("\nNo gaps — everything they ship is ruled and current.")
    if args.beads:
        lines.append("\n### bd create lines (review before running)")
        for cap in sorted(not_reviewed, key=lambda c: c.logical_id):
            title = f"Evaluate {cap.kind.value} {cap.name} from {ref.repo}"
            desc = f"Gap candidate {cap.logical_id} ({cap.canonical_path}). Rule via harness-evaluate."
            lines.append(
                f"bd create --title={shlex.quote(title)} "
                f"--description={shlex.quote(desc)} --type=task --priority=3"
            )
    print("\n".join(lines))
    return 0


def cmd_ours(cfg: RegistryConfig, args: argparse.Namespace) -> int:
    ours = build_ours(cfg)
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(
            json.dumps(ours.to_dict(), indent=2) + "\n", encoding="utf-8"
        )
        print(f"wrote {args.out}", file=sys.stderr)
    print(render_catalog_summary(ours))
    return 0


def cmd_round(cfg: RegistryConfig, args: argparse.Namespace) -> int:
    if args.round_command == "open":
        if open_rounds(cfg):
            names = ", ".join(p.name for p in open_rounds(cfg))
            raise SystemExit(f"a round is already open ({names}) — seal it first")
        date = args.date or _today_iso()
        # round_id is <yyyy-mm-dd>-<slug>; a slug that already carries a date
        # prefix is used as-is so the date is never doubled (cr-alnr).
        round_id = (
            args.slug if _DATE_PREFIX_RE.match(args.slug) else f"{date}-{args.slug}"
        )
        path = cfg.ledger_dir / f"{round_id}.jsonl"
        if path.exists():
            raise SystemExit(f"round file already exists: {path}")
        data = _json_arg(args)
        data["type"] = "round"
        data["round_id"] = round_id
        data.setdefault("date", date)
        if args.scope is not None:
            data["scope"] = args.scope
        data.setdefault("scope", "")
        header = RoundHeader.model_validate(data)
        cfg.ledger_dir.mkdir(parents=True, exist_ok=True)
        path.write_text(
            _dump(header.model_dump(exclude_defaults=False)) + "\n", encoding="utf-8"
        )
        print(f"opened {path}")
        return 0
    # seal
    seal(cfg, args.round_id)
    print(f"sealed {args.round_id}")
    return 0


def cmd_record(cfg: RegistryConfig, args: argparse.Namespace) -> int:
    require_round_order(cfg)
    path = open_round(cfg)
    if path is None:
        raise SystemExit("no open round — run `round open <slug>` first")
    round_id = path.stem
    data = _json_arg(args)
    for field in ("id", "date", "kind", "subject", "why", "skill"):
        value = getattr(args, field, None)
        if value is not None:
            data[field] = value
    if getattr(args, "evidence", None):
        data["evidence"] = list(args.evidence)
    if getattr(args, "supersedes", None):
        data["supersedes"] = list(args.supersedes)
    data["type"] = "event"
    data.setdefault("date", _today_iso())
    if "id" in data and not str(data["id"]).startswith(f"{round_id}:"):
        raise SystemExit(
            f"id {data['id']!r} does not belong to the open round {round_id!r}"
        )
    events = record_events.prepare(cfg, path, data, getattr(args, "whole_skill", None))
    with path.open("a", encoding="utf-8") as handle:
        for event in events:
            handle.write(_dump(_event_dict(event)) + "\n")
    for event in events:
        print(f"recorded {event.id} in {path.name}")
    return 0


def _json_arg(args: argparse.Namespace) -> dict[str, Any]:
    """Structured input for `record`/`round open`: --json, --json-file or stdin."""
    raw: str | None = getattr(args, "json", None)
    if raw is None and getattr(args, "json_file", None):
        raw = Path(args.json_file).read_text(encoding="utf-8")
    if raw is None and getattr(args, "stdin", False):
        raw = sys.stdin.read()
    if not raw:
        return {}
    parsed = json.loads(raw)
    if not isinstance(parsed, dict):
        raise SystemExit("structured input must be a JSON object")
    return dict(parsed)


def cmd_build(cfg: RegistryConfig, args: argparse.Namespace) -> int:
    require_round_order(cfg)
    outputs = build_outputs(cfg)
    cfg.references_dir.mkdir(parents=True, exist_ok=True)
    for path, content in outputs.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    print(f"built: {len(outputs)} generated file(s)")
    return 0


def cmd_check(cfg: RegistryConfig, args: argparse.Namespace) -> int:
    errors: list[str] = []
    headers, events, load_errors = load_ledger(cfg)
    errors += load_errors

    seen: set[str] = set()
    known_rounds = {h.round_id for h in headers}
    for event in events:
        if event.id in seen:
            errors.append(f"{event.id}: duplicate event id")
        seen.add(event.id)
        if not event.why.strip():
            errors.append(f"{event.id}: why is empty")
        if _round_of(event) not in known_rounds:
            errors.append(f"{event.id}: round {_round_of(event)!r} has no header")
    errors += _check_supersession(events, seen)
    errors += _check_structure(cfg)
    open_now = open_rounds(cfg)
    if len(open_now) > 1:
        errors.append(
            "more than one open round: " + ", ".join(p.name for p in open_now)
        )
    errors += check_immutable(cfg)
    errors += round_order_errors(cfg)

    skills, skill_errors = load_skills(cfg)
    errors += skill_errors
    records: dict[str, Frontmatter] = {
        name: entry.frontmatter(name) for name, entry in skills.items()
    }
    errors += _check_boundaries(skills)
    expected = {record_path(cfg, name, fm.domain) for name, fm in records.items()}
    for path in record_paths(cfg):
        if path not in expected:
            errors.append(
                f"{_rel(cfg, path)}: no skills.yaml entry generates this record"
            )

    errors += _check_skill_coverage(cfg, records)
    aliases = {alias for fm in records.values() for alias in fm.aliases}
    ours = build_ours(cfg)
    definitions, def_errors = load_trait_definitions(cfg)
    traits, trait_errors = load_traits(cfg)
    errors += def_errors + trait_errors
    playbooks, playbook_load_errors = load_playbooks(cfg)
    errors += playbook_load_errors
    errors += playbook_errors(cfg, playbooks, definitions)
    errors += playbook_ledger_errors(cfg, events)
    # One live (non-superseded) event list feeds every lifecycle/withdrawal
    # consumer, so a correction takes effect everywhere at once (N2/N3). Coverage
    # obligations instead read raw events (an upstream reject never withdraws an
    # adoption — only an ours-side `update` does), so `_check_trait_level` gets
    # the raw list (review r3).
    live = live_events(events)
    forward, retired = build_lifecycle(live)
    warnings: list[str] = []
    errors += _check_effective_targets(
        cfg, live, set(records), aliases, ours, forward, retired
    )
    errors += _check_carried_from(
        events
    )  # history: carried_from names an earlier subject
    errors += _check_withdraws(
        events, forward
    )  # raw: superseded adopt still withdrawable
    errors += _check_adopt_merged_adaptation(headers, live)
    errors += _check_block_pairing(cfg)
    errors += _check_trait_definitions(definitions)
    errors += _check_traits_yaml(cfg, traits, definitions, set(records), ours, events)
    warnings += _retired_trait_warnings(traits, definitions)
    sharing, sharing_load_errors = load_trait_sharing(cfg)
    errors += sharing_load_errors
    sharing_errors, sharing_warnings = sharing_problems(
        shared_traits(traits, skills, playbooks), sharing
    )
    errors += sharing_errors
    warnings += sharing_warnings
    policies, policy_load_errors = load_trait_policy(cfg)
    errors += policy_load_errors
    policy_errors, policy_warnings = policy_problems(
        policies,
        definitions,
        seen,
        _ours_traits(traits),
        skills,
        guide_rules(cfg.guide_path),
    )
    errors += policy_errors
    warnings += policy_warnings
    errors += _check_trait_level(
        cfg, headers, events, ours, forward, retired, definitions, traits, playbooks
    )

    reports, report_errors = load_reports(cfg)
    errors += report_errors
    upstream = _upstream_traits(traits)
    errors += check_reports(cfg, reports, upstream)
    errors += decision_errors(cfg, events, upstream, reports, manifest_reports(cfg))
    errors += defer_errors(cfg, events)
    errors += analysis_errors(cfg, upstream)

    # Records with no traits/ours.yaml entry stay lazy; report how many.
    ours_traits = _ours_traits(traits)
    lazy = sum(
        1
        for skill, fm in records.items()
        if fm.status == "active" and skill not in ours_traits
    )

    if not errors:
        try:
            outputs = build_outputs(cfg)
        except SystemExit as exc:
            errors.append(str(exc))
            outputs = {}
        for path, content in outputs.items():
            on_disk = path.read_text(encoding="utf-8") if path.exists() else None
            if on_disk != content:
                errors.append(
                    f"{_rel(cfg, path)}: generated file is stale — run `build`"
                )

    for line in warnings:
        print(f"warning: {line}", file=sys.stderr)
    if errors:
        for line in errors:
            print(f"error: {line}", file=sys.stderr)
        print(f"\n{len(errors)} problem(s)", file=sys.stderr)
        return 1
    print(
        f"ok: {len(headers)} round(s), {len(events)} event(s), "
        f"{len(records)} skill record(s); "
        f"{lazy} record(s) without a traits/ours.yaml entry (lazy)"
    )
    return 0


def _status_table(rows: list[list[str]], indent: str = "  ") -> list[str]:
    widths = [max(len(r[i]) for r in rows) for i in range(len(rows[0]))]
    return [
        indent + "  ".join(c.ljust(w) for c, w in zip(r, widths, strict=True)).rstrip()
        for r in rows
    ]


def cmd_status(cfg: RegistryConfig, args: argparse.Namespace) -> int:
    """Stage 4: each upstream skill's stage (its least advanced trait's), with
    `--traits` each trait's stage, ruling and provision; the harness's other
    capabilities; trait-policy entries whose GUIDE rules changed."""
    path = cfg.catalogs_dir / f"{args.harness}.json"
    if not path.is_file():
        raise SystemExit(f"no catalog for {args.harness!r}: {_rel(cfg, path)}")
    catalog = Catalog.from_dict(json.loads(path.read_text(encoding="utf-8")))
    ctx = report_files.load_context(cfg)
    skills = skill_statuses(ctx, catalog)
    if args.skill:
        want = args.skill
        skills = [
            s for s in skills if want in (s.logical_id, s.logical_id.rsplit("/", 1)[-1])
        ]
        if not skills:
            raise SystemExit(f"--skill {want}: no upstream skill of {args.harness}")
    lines = [
        f"## status: {catalog.repo}  (catalog {catalog.source_commit or catalog.source})",
        "",
    ]
    rows = [["skill", "stage", "traits"]]
    for st in skills:
        counts: dict[str, int] = {}
        for t in st.traits:
            counts[t.stage] = counts.get(t.stage, 0) + 1
        summary = " · ".join(
            f"{counts[s]} {s}" for s in sorted(counts, key=status_view.stage_rank)
        )
        rows.append([st.logical_id, st.stage, summary or "—"])
    lines += _status_table(rows)
    if args.traits:
        for st in skills:
            if not st.traits:
                continue
            lines += ["", f"### {st.logical_id}"]
            trows = [["trait", "stage", "ruling", "provision"]]
            trows += [
                [t.trait, t.stage, t.ruling or "—", t.provision or "—"]
                for t in st.traits
            ]
            lines += _status_table(trows)
    if not args.skill:
        headers, _, _ = load_ledger(cfg)
        headers_by_id = round_header_by_id(headers)
        others: list[list[str]] = []
        for cap in catalog.capabilities:
            if cap.kind.value == "skill":
                continue
            event = ctx.current.get(f"{catalog.repo}:{cap.logical_id}")
            changed = (
                _change_info(
                    cfg, catalog, cap, event, headers_by_id.get(_round_of(event))
                ).changed
                if event is not None
                else ""
            )
            others.append(
                [cap.logical_id, status_view.capability_state(event, changed)]
            )
        for subject, _event in _removed_upstream(
            catalog.repo, ctx.current, set(catalog.by_logical_id())
        ):
            logical = subject.split(":", 1)[1]
            if not logical.startswith("skill:"):
                others.append([logical, "removed"])
        if others:
            lines += ["", "### other capabilities"]
            lines += _status_table([["capability", "state"], *sorted(others)])
    changes = guide_changes(ctx.live_policy, guide_rules(cfg.guide_path))
    lines += ["", f"### guide changed (trait-policy.yaml): {len(changes)}"]
    for tid, notes in changes.items():
        lines.append(f"  {tid}: {'; '.join(notes)}")
    print("\n".join(lines))
    return 0


def cmd_report(cfg: RegistryConfig, args: argparse.Namespace) -> int:
    if args.report_command == "draft":
        path = report_files.draft(
            cfg,
            args.harness,
            args.skill,
            args.compared_with,
            Path(args.report) if args.report else None,
            list(args.reconsider or []),
            refresh=args.refresh,
        )
        print(f"drafted {args.skill} in {path} — fill the judged fields, then `build`")
        return 0
    errors = report_files.seal(cfg, Path(args.path))
    if errors:
        for line in errors:
            print(f"error: {line}", file=sys.stderr)
        print(f"\nnot sealed: {len(errors)} problem(s)", file=sys.stderr)
        return 1
    print(f"sealed {args.path}")
    return 0


def cmd_steps(cfg: RegistryConfig, args: argparse.Namespace) -> int:
    """Per-step changes of one playbook between two revisions (St3)."""
    old = playbook_at(cfg, args.playbook, args.base)
    new = playbook_at(cfg, args.playbook, args.head)
    if old is None and new is None:
        print(f"error: no playbook {args.playbook!r} at either side", file=sys.stderr)
        return 1
    span = f"{args.base} → {args.head or 'working tree'}"
    changes = step_changes(old, new)
    if not changes:
        print(f"{args.playbook} ({span}): no step changes")
        return 0
    print(f"{args.playbook} ({span}): {len(changes)} step change(s)")
    width = max(len(c.kind) for c in changes)
    for change in changes:
        detail = f": {change.detail}" if change.detail else ""
        print(f"  {change.kind.ljust(width)}  {change.step}{detail}")
    return 0


def _add_json_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--json", help="a JSON object with the full/partial record")
    parser.add_argument(
        "--json-file", dest="json_file", help="path to that JSON object"
    )
    parser.add_argument(
        "--stdin", action="store_true", help="read the JSON object from stdin"
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Skill + capability registry.")
    sub = parser.add_subparsers(dest="command", required=True)

    p_gap = sub.add_parser("gap", help="capabilities never ruled on, or changed since")
    p_gap.add_argument("reference")
    p_gap.add_argument("--kind")
    p_gap.add_argument("--beads", action="store_true")
    p_gap.set_defaults(func=cmd_gap)

    p_ours = sub.add_parser("ours", help="catalog our own capabilities")
    p_ours.add_argument("--out")
    p_ours.set_defaults(func=cmd_ours)

    p_round = sub.add_parser("round", help="open or seal a round file")
    round_sub = p_round.add_subparsers(dest="round_command", required=True)
    p_open = round_sub.add_parser("open")
    p_open.add_argument("slug")
    p_open.add_argument("--date")
    p_open.add_argument("--scope")
    _add_json_args(p_open)
    p_seal = round_sub.add_parser("seal")
    p_seal.add_argument("round_id")
    p_round.set_defaults(func=cmd_round)

    p_rec = sub.add_parser("record", help="append one event to the open round")
    p_rec.add_argument("--id", help="default: the next <round_id>:<n>")
    p_rec.add_argument("--date", help="default: today")
    p_rec.add_argument("--kind", choices=sorted(EVENT_KINDS))
    p_rec.add_argument("--subject")
    p_rec.add_argument("--why")
    p_rec.add_argument("--evidence", action="append")
    p_rec.add_argument("--skill")
    p_rec.add_argument("--supersedes", action="append", help="an event id it replaces")
    p_rec.add_argument(
        "--whole-skill",
        dest="whole_skill",
        choices=record_events.WHOLE_SKILL_VERDICTS,
        help="one verdict on an upstream skill (one event per trait once accepted)",
    )
    _add_json_args(p_rec)
    p_rec.set_defaults(func=cmd_record)

    p_report = sub.add_parser("report", help="draft or seal a report file")
    report_sub = p_report.add_subparsers(dest="report_command", required=True)
    p_draft = report_sub.add_parser("draft", help="create a report or add a skill")
    p_draft.add_argument("harness")
    p_draft.add_argument("--skill", required=True, help="upstream logical id")
    p_draft.add_argument(
        "--with", dest="compared_with", required=True, help="our skill, or none"
    )
    p_draft.add_argument("--report", help="reviews/<name>.yaml (default: the draft)")
    p_draft.add_argument("--reconsider", nargs="+", metavar="TRAIT")
    p_draft.add_argument(
        "--refresh", action="store_true", help="recompute a skill already drafted"
    )
    p_seal_report = report_sub.add_parser("seal", help="seal a passed report")
    p_seal_report.add_argument("path")
    p_report.set_defaults(func=cmd_report)

    p_status = sub.add_parser("status", help="where each upstream skill stands")
    p_status.add_argument("harness")
    p_status.add_argument("--skill", help="one upstream skill (logical id or name)")
    p_status.add_argument("--traits", action="store_true", help="per trait")
    p_status.set_defaults(func=cmd_status)

    p_steps = sub.add_parser("steps", help="a playbook's step changes")
    steps_sub = p_steps.add_subparsers(dest="steps_command", required=True)
    p_steps_diff = steps_sub.add_parser(
        "diff", help="per-step changes between two revisions"
    )
    p_steps_diff.add_argument("playbook", help="playbook name, e.g. bug-fix")
    p_steps_diff.add_argument("base", nargs="?", default="HEAD", help="default HEAD")
    p_steps_diff.add_argument(
        "head", nargs="?", default=None, help="default: the working tree"
    )
    p_steps.set_defaults(func=cmd_steps)

    sub.add_parser(
        "build", help="regenerate INDEX.md, TRAITS.md, STEPS.md, references, records"
    ).set_defaults(func=cmd_build)
    sub.add_parser(
        "check", help="validate the ledger, records and generated files"
    ).set_defaults(func=cmd_check)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    cfg = RegistryConfig.default()
    return int(args.func(cfg, args))
