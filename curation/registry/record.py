"""`registry.py record`: build, validate and refuse events (stages-design
3.2-3.4a, 3.6). Freshness is checked here, once (3.3); `check` re-runs the
structural decision rules on the whole ledger."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from curation.registry import reports as report_files
from curation.registry.catalogs import _autofill_source, build_ours
from curation.registry.checks.decisions import (
    cited_row,
    decision_errors,
    defer_errors,
)
from curation.registry.config import RegistryConfig
from curation.registry.ledger import (
    _next_event_id,
    analysis_at,
    build_lifecycle,
    effective_by_subject,
    is_pending_adopt,
    lifecycle_of,
    live_events,
    resolve_skill,
)
from curation.registry.loaders import load_ledger
from curation.registry.models import Event, Source
from curation.registry.traits import _doc_tree_hash, _our_tree_hashes

WHOLE_SKILL_VERDICTS = ("defer", "reject", "out-of-scope")


def prepare(
    cfg: RegistryConfig,
    path: Path,
    data: dict[str, Any],
    whole_skill: str | None = None,
) -> list[Event]:
    """The events one `record` call appends, all validated; any refusal
    raises `SystemExit` before anything is written."""
    _, events, _ = load_ledger(cfg)
    if whole_skill is not None:
        return _expand(cfg, path, data, whole_skill, events)
    data.setdefault("id", _next_event_id(path, path.stem))
    return [_single(cfg, data, events)]


def _single(cfg: RegistryConfig, data: dict[str, Any], events: list[Event]) -> Event:
    subject = str(data.get("subject", ""))
    round_id = str(data["id"]).rsplit(":", 1)[0]
    live = live_events(events)
    prior = effective_by_subject(live).get(subject)
    pending = lifecycle_of(
        data.get("kind"),
        subject,
        [str(t) for t in data.get("supersedes") or []],
        data.get("skill"),
        data.get("into"),
        data.get("pending"),
        prior,
        build_lifecycle(live)[0],
    )
    if pending is not None:
        _inherit(data, pending)
    elif "source" not in data and ":" in subject and not subject.startswith("ours:"):
        # A trait subject carries a trailing #<slug>; the catalog is keyed by the
        # bare logical id, so strip it before autofilling the source.
        repo, _, logical = subject.partition(":")
        source = _autofill_source(cfg, repo, logical.split("#", 1)[0])
        if source is not None:
            data["source"] = source
    if (
        "#" in subject
        and data.get("kind") == "adopt"
        and data.get("pending")
        and data.get("rewording")
        and data.get("skill")
    ):
        data["target_tree_hash"] = _target_hash(cfg, str(data["skill"]), events)
    ctx = report_files.load_context(cfg) if "#" in subject else None
    if ctx is not None:
        _set_policy_basis(data, subject, pending, ctx)
        if pending is None and data.get("kind") == "defer":
            _copy_revisit_when(data, subject, ctx)
    event = Event.model_validate(data)
    late = defer_errors(cfg, [event])
    if late:
        raise SystemExit("refused:\n" + "\n".join(late))
    if ctx is None:
        return event
    errors = [
        e
        for e in decision_errors(
            cfg, [*events, event], ctx.upstream, ctx.reports, ctx.sealed
        )
        if e.startswith(f"{event.id}:")
    ]
    if not errors and pending is None and round_id not in cfg.pre_trait_rounds:
        errors += _freshness_errors(event, ctx)
    if not errors and pending is not None and pending.rewording is not None:
        target = pending.skill  # a completion keeps it (3.4)
        if event.kind == "adopt" and target:
            now = _target_hash(cfg, target, events)
            if now == pending.target_tree_hash:
                errors.append(
                    f"{event.id}: target {target!r} is unchanged since rewording "
                    f"{pending.id} was pended; edit it first"
                )
    if errors:
        raise SystemExit("refused:\n" + "\n".join(errors))
    return event


def _inherit(data: dict[str, Any], pending: Event) -> None:
    """Fill `report` and `source` from the pending event; refuse a mismatch."""
    what = "completion" if data.get("kind") == "adopt" else "cancellation"
    assert pending.source is not None
    if "source" in data and Source.model_validate(data["source"]) != pending.source:
        raise SystemExit(f"a {what} must inherit `source` from pending {pending.id}")
    if "report" in data and data["report"] != pending.report:
        raise SystemExit(f"a {what} must inherit `report` from pending {pending.id}")
    data["source"] = pending.source.model_dump(exclude_none=True)
    if pending.report is not None:
        data["report"] = pending.report


def _set_policy_basis(
    data: dict[str, Any],
    subject: str,
    pending: Event | None,
    ctx: report_files.Context,
) -> None:
    """Every new trait event stores the policy it is recorded under: the
    trait's live entry now, or `null`; a lifecycle event copies its pending
    event's exactly (stages-design §Trait policy)."""
    if pending is not None:
        basis = pending.policy_basis
    else:
        entry = ctx.live_policy.get(subject.split("#", 1)[1])
        basis = entry.basis() if entry else None
    want = basis.model_dump() if basis else None
    if "policy_basis" in data and data["policy_basis"] != want:
        raise SystemExit(f"`policy_basis` is computed by `record`; it is {want}")
    data["policy_basis"] = want


def _copy_revisit_when(
    data: dict[str, Any], subject: str, ctx: report_files.Context
) -> None:
    """A new trait defer takes its cited row's `revisit_when` unless given."""
    report = ctx.reports.get(str(data.get("report")))
    source = data.get("source")
    if "revisit_when" in data or report is None or not isinstance(source, dict):
        return
    skill = report.skills.get(str(source.get("logical_id")))
    row = skill.traits.get(subject.split("#", 1)[1]) if skill else None
    if row is not None and row.revisit_when:
        data["revisit_when"] = row.revisit_when


def _freshness_errors(event: Event, ctx: report_files.Context) -> list[str]:
    """3.3: the cited row is the current one and its computed fields equal
    today's computation; its `via` is still a candidate."""
    _, cited = cited_row(event, ctx.reports, ctx.sealed)
    if cited is None:
        return []
    key, report, skill, row = cited
    assert event.source is not None
    tid = event.subject.split("#", 1)[1]
    try:
        current = report_files.current_row(
            ctx.reports,
            ctx.sealed,
            report.harness,
            event.source.logical_id,
            tid,
            report.to_sha,
        )
    except ValueError as exc:
        return [f"{event.id}: {exc}"]
    if current is not None and current[0] != key:
        return [f"{event.id}: {key} is not the current row for {tid} ({current[0]} is)"]
    stale = report_files.stale_fields(ctx, tid, skill.compared_with, row)
    if stale:
        return [
            (
                f"{event.id}: stale row {key}#{tid}: {', '.join(stale)} differ "
                f"from today's computation; re-compare in a new report"
            )
        ]
    return []


def _target_hash(cfg: RegistryConfig, target: str, events: list[Event]) -> str:
    """The target's current tree hash: a skill folder's, or a `doc:` file's."""
    if target.startswith("doc:"):
        rel = target[len("doc:") :]
        file = cfg.repo_root / rel
        if not file.is_file():
            raise SystemExit(f"{target}: no such file to hash")
        return _doc_tree_hash(rel, file.read_bytes())
    forward, _ = build_lifecycle(live_events(events))
    survivor = resolve_skill(target, forward)
    found = _our_tree_hashes(build_ours(cfg)).get(survivor)
    if found is None:
        raise SystemExit(f"{target}: no skill folder to hash")
    return found


def _expand(
    cfg: RegistryConfig,
    path: Path,
    data: dict[str, Any],
    kind: str,
    events: list[Event],
) -> list[Event]:
    """`record --whole-skill <kind>` (3.6): without an accepted analysis, the
    one whole-skill checkpoint; with one, an event per trait listed in the
    analysis at the cited report's sha, all citing it. A trait whose pending
    adopt this verdict cancels inherits that event's report instead (3.4)."""
    if kind not in WHOLE_SKILL_VERDICTS:
        raise SystemExit(
            f"--whole-skill {kind}: one of {', '.join(WHOLE_SKILL_VERDICTS)}"
        )
    if data.get("kind") not in (None, kind):
        raise SystemExit(f"--whole-skill {kind} disagrees with kind {data['kind']!r}")
    subject = str(data.get("subject", ""))
    if "#" in subject or ":" not in subject or subject.startswith("ours:"):
        raise SystemExit(
            f"--whole-skill needs an upstream skill subject, not {subject!r}"
        )
    data["kind"] = kind
    ctx = report_files.load_context(cfg)
    entry = ctx.upstream.get(subject)
    if entry is None or entry.accepted is None:
        data.setdefault("id", _next_event_id(path, path.stem))
        return [_single(cfg, data, events)]
    key = data.pop("report", None)
    report = ctx.reports.get(str(key)) if key else None
    if report is None:
        raise SystemExit(
            f"{subject} has an accepted analysis: cite the report (`report`)"
        )
    found = analysis_at(entry, report.to_sha)
    if found is None:
        raise SystemExit(
            f"{subject}: no analysis at the report's to_sha {report.to_sha}"
        )
    repo, _, logical = subject.partition(":")
    base = (
        data.pop("source", None)
        or _autofill_source(cfg, repo, logical)
        or {
            "repo": repo,
            "logical_id": logical,
        }
    )
    source = {**base, "sha": report.to_sha, "tree_hash": found[1].tree_hash}
    first = int(_next_event_id(path, path.stem).rsplit(":", 1)[1])
    so_far = list(events)
    out: list[Event] = []
    for n, tid in enumerate(found[1].traits):
        item = dict(data, subject=f"{subject}#{tid}", id=f"{path.stem}:{first + n:03d}")
        prior = effective_by_subject(live_events(so_far)).get(item["subject"])
        item["supersedes"] = [prior.id] if prior else []
        if not (
            prior is not None and is_pending_adopt(prior) and kind != "out-of-scope"
        ):
            item.update(source=dict(source), report=key)
        event = _single(cfg, item, so_far)
        so_far.append(event)
        out.append(event)
    return out
