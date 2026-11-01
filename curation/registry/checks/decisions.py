"""Decision checks (stages-design Stage 3; §What `check` adds, items 2-3 and
10-11): report citation, lifecycle inheritance, reconsideration, rewording,
each event's own `policy_basis`, membership by sha and analysis immutability.
Facts are never recomputed here: freshness is checked once, by `record` (3.3),
so a later delivery never invalidates history."""

from __future__ import annotations

from curation.registry.config import RegistryConfig
from curation.registry.ledger import (
    _is_trait_subject,
    _round_of,
    _same_sha,
    _trait_base,
    _trait_slug,
    analysis_at,
    analysis_digest,
    build_lifecycle,
    lifecycle_pending,
    live_events,
    manifest_analyses,
)
from curation.registry.models import (
    Event,
    Report,
    ReportRow,
    ReportSkill,
    UpstreamTraitEntry,
)

Cited = tuple[str, Report, ReportSkill, ReportRow]


def decision_errors(
    cfg: RegistryConfig,
    events: list[Event],
    upstream: dict[str, UpstreamTraitEntry],
    reports: dict[str, Report],
    sealed: dict[str, str],
) -> list[str]:
    """Every trait event, in ledger order: membership by sha (3.9); a
    completion or cancellation inherits its pending event's `report` and
    `source` (3.4); outside `pre_trait_rounds`, any other event cites a
    sealed report's row and its target (3.2), reconsiders through a
    `reconsider` row (3.4) and obeys a `reword` verdict (3.4a). Each event
    is classified with the rename/merge state preceding it, as `record` saw
    it, so a later merge never rewrites an earlier classification."""
    errors: list[str] = []
    dead: set[str] = set()
    history: dict[str, list[Event]] = {}
    for idx, event in enumerate(events):
        if _is_trait_subject(event.subject):
            forward, _ = build_lifecycle(live_events(events[:idx]))
            prior = next(
                (
                    e
                    for e in reversed(history.get(event.subject, []))
                    if e.id not in dead
                ),
                None,
            )
            errors += _event_errors(
                cfg, event, prior, forward, upstream, reports, sealed
            )
        dead.update(event.supersedes)
        history.setdefault(event.subject, []).append(event)
    return errors


def _event_errors(
    cfg: RegistryConfig,
    event: Event,
    prior: Event | None,
    forward: dict[str, str],
    upstream: dict[str, UpstreamTraitEntry],
    reports: dict[str, Report],
    sealed: dict[str, str],
) -> list[str]:
    errors = membership_errors(event, upstream)
    pending = lifecycle_pending(event, prior, forward)
    if pending is not None:
        errors += _inheritance_errors(event, pending, reports, sealed)
        if event.policy_basis != pending.policy_basis:
            errors.append(
                f"{event.id}: a lifecycle event must copy `policy_basis` from "
                f"pending {pending.id}"
            )
        return errors
    basis = event.policy_basis
    if (
        basis is not None
        and basis.stance == "avoid"
        and event.kind == "adopt"
        and event.override is None
    ):
        errors.append(
            f"{event.id}: adopting a trait whose policy is `avoid` needs `override`"
        )
    if _round_of(event) in cfg.pre_trait_rounds:
        return errors
    cite_errors, cited = cited_row(event, reports, sealed)
    errors += cite_errors
    if cited is None:
        return errors
    key, _, skill, row = cited
    if event.skill is not None and event.retarget is None:
        allowed = {row.provider, row.target}
        if skill.compared_with != "none":
            allowed.add(skill.compared_with)
        if event.skill not in allowed:
            errors.append(
                f"{event.id}: target {event.skill!r} is not the row's provider, "
                f"compared skill or adopt target "
                f"({sorted(a for a in allowed if a)}); set `retarget`"
            )
    assert event.source is not None
    if (
        prior is not None
        and prior.source is not None
        and _same_sha(prior.source.sha, event.source.sha)
        and row.scope != "reconsider"
    ):
        errors.append(
            f"{event.id}: reconsidering {prior.id} at {event.source.sha} needs a "
            f"`reconsider` row ({key} has {row.scope!r})"
        )
    if event.kind == "adopt":
        errors += _guide_errors(event, key, row)
    if basis is not None and basis.stance == "reword" and event.kind == "adopt":
        cited_rules = set(row.guide.rules) if row.guide else set()
        missing = sorted(set(basis.rules) - cited_rules)
        if missing:
            errors.append(
                f"{event.id}: the trait's policy is `reword` under rules "
                f"{sorted(basis.rules)}; row {key} omits {missing}"
            )
    if event.pending and event.rewording and event.target_tree_hash is None:
        errors.append(f"{event.id}: a pending rewording adopt needs `target_tree_hash`")
    return errors


def _guide_errors(event: Event, key: str, row: ReportRow) -> list[str]:
    """2.9, 3.4a: a new delivered adopt needs the row's verdict `ok`, or a
    `conflict` with an owner override; a new pending adopt needs a verdict and,
    unless one of those, `rewording`."""
    if row.guide is None:
        return [f"{event.id}: row {key} has no `guide`; it supports no new adopt"]
    verdict = row.guide.verdict
    if event.pending is None:
        if verdict == "reword":
            return [
                (
                    f"{event.id}: a new delivered adopt from a `reword` row "
                    f"(pend it with `rewording`)"
                )
            ]
        if not row.guide.supports_adopt:
            return [
                (
                    f"{event.id}: a new delivered adopt needs the row's guide "
                    f"verdict `ok`, or `conflict` with an owner override "
                    f"({key} has {verdict!r})"
                )
            ]
    elif not row.guide.supports_adopt and event.rewording is None:
        return [f"{event.id}: a pending adopt from a `{verdict}` row needs `rewording`"]
    return []


def defer_errors(cfg: RegistryConfig, events: list[Event]) -> list[str]:
    """3.5: every defer outside `pre_trait_rounds` (trait, whole-skill or a
    cancellation) says when to revisit it."""
    return [
        f"{event.id}: a defer needs `revisit_when` (3.5)"
        for event in events
        if event.kind == "defer"
        and event.revisit_when is None
        and _round_of(event) not in cfg.pre_trait_rounds
    ]


def membership_errors(
    event: Event, upstream: dict[str, UpstreamTraitEntry]
) -> list[str]:
    """3.9: the trait is listed in the analysis at the event's source sha."""
    base, tid = _trait_base(event.subject), _trait_slug(event.subject) or ""
    entry = upstream.get(base)
    if entry is None:
        return [f"{event.id}: trait ruling {event.subject!r} has no traits entry"]
    sha = event.source.sha if event.source else None
    found = analysis_at(entry, sha)
    if found is None:
        return [f"{event.id}: no analysis of {base!r} at {sha}"]
    if tid not in found[1].traits:
        return [
            (
                f"{event.id}: trait {tid!r} is not listed in the analysis of "
                f"{base!r} at {found[0]}"
            )
        ]
    return []


def cited_row(
    event: Event, reports: dict[str, Report], sealed: dict[str, str]
) -> tuple[list[str], Cited | None]:
    """3.2: the event's report exists, is sealed (so critic-passed), names the
    event's harness and source sha, and has a row for its trait."""
    key = event.report
    if key is None:
        return [
            f"{event.id}: a trait event outside pre_trait_rounds cites no `report`"
        ], None
    report = reports.get(key)
    if report is None:
        return [f"{event.id}: report {key} does not exist"], None
    if key not in sealed:
        return [f"{event.id}: report {key} is not sealed"], None
    assert event.source is not None
    errors: list[str] = []
    if report.harness != event.source.repo:
        errors.append(
            f"{event.id}: report {key} is for {report.harness}, not {event.source.repo}"
        )
    if not _same_sha(report.to_sha, event.source.sha):
        errors.append(
            f"{event.id}: report {key} is at {report.to_sha}, not the event's "
            f"{event.source.sha}"
        )
    skill = report.skills.get(event.source.logical_id)
    tid = _trait_slug(event.subject) or ""
    row = skill.traits.get(tid) if skill else None
    if skill is None or row is None:
        errors.append(f"{event.id}: report {key} has no row for {tid}")
    if errors or skill is None or row is None:
        return errors, None
    return [], (key, report, skill, row)


def _inheritance_errors(
    event: Event,
    pending: Event,
    reports: dict[str, Report],
    sealed: dict[str, str],
) -> list[str]:
    """3.4: exact inheritance of `report` and `source`; 3.4a: a rewording
    completion confirms the wording with the cited row's rules."""
    what = "completion" if event.kind == "adopt" else "cancellation"
    errors: list[str] = []
    if event.report != pending.report:
        errors.append(
            f"{event.id}: a {what} must inherit `report` from pending {pending.id}"
        )
    if event.source != pending.source:
        errors.append(
            f"{event.id}: completing adopt of {event.subject!r} must copy `source` "
            f"from pending {pending.id}"
            if what == "completion"
            else f"{event.id}: a {what} must inherit `source` from pending {pending.id}"
        )
    if what == "completion" and pending.rewording is not None:
        if event.guide is None or event.guide.verdict != "ok":
            errors.append(
                f"{event.id}: completing rewording {pending.id} needs "
                f"`guide: {{verdict: ok, rules: …}}`"
            )
        else:
            _, cited = cited_row(pending, reports, sealed)
            want = cited[3].guide.rules if cited and cited[3].guide else []
            if event.guide.rules != want:
                errors.append(
                    f"{event.id}: guide rules {event.guide.rules} are not the row's {want}"
                )
        if not event.evidence:
            errors.append(
                f"{event.id}: completing rewording {pending.id} cites the reworded lines"
            )
    return errors


def analysis_errors(
    cfg: RegistryConfig, upstream: dict[str, UpstreamTraitEntry]
) -> list[str]:
    """An analysis a sealed round cites never changes or vanishes (§Entries)."""
    errors: list[str] = []
    for key, digest in manifest_analyses(cfg).items():
        base, _, sha = key.rpartition("@")
        entry = upstream.get(base)
        analysis = entry.analyses.get(sha) if entry else None
        if analysis is None:
            errors.append(
                f"analysis {key} has VANISHED — a cited analysis is immutable"
            )
        elif analysis_digest(analysis) != digest:
            errors.append(f"analysis {key} has CHANGED — a cited analysis is immutable")
    return errors
