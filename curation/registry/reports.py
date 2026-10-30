"""Report files (stages-design §Report file): context, scope, the current row,
`report draft`, `report seal` and the generated Markdown."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

from curation.registry.config import RegistryConfig
from curation.registry.ledger import (
    _same_sha,
    effective_by_subject,
    live_events,
    manifest_reports,
    seal_report_digest,
)
from curation.registry.loaders import (
    load_ledger,
    load_report,
    load_reports,
    load_skills,
    load_trait_definitions,
    load_trait_policy,
    load_traits,
    report_key,
)
from curation.registry.models import (
    Event,
    Pairing,
    PolicyEntry,
    Report,
    ReportAnalysis,
    ReportRow,
    SkillEntry,
    TraitDefinition,
    UpstreamTraitEntry,
)
from curation.registry.policy import live_policy
from curation.registry.traits import (
    _upstream_traits,
    compute_fact,
    compute_pairing,
    holders,
)

# The row fields a re-comparison compares with today's computation (2.6).
_COMPUTED = ("fact", "provider", "candidates", "also_in")


@dataclass(frozen=True)
class Context:
    """Everything facts, scope and the current row are computed from."""

    upstream: dict[str, UpstreamTraitEntry]
    held: dict[str, set[str]]
    definitions: dict[str, TraitDefinition]
    skills: dict[str, SkillEntry]
    events: list[Event]  # raw, in ledger order
    current: dict[str, Event]
    reports: dict[str, Report]
    sealed: dict[str, str]
    policies: dict[str, PolicyEntry]

    @property
    def live_policy(self) -> dict[str, PolicyEntry]:
        return live_policy(self.policies, self.definitions)


def load_context(cfg: RegistryConfig) -> Context:
    """Load the trait files, skills, ledger and reports; any error refuses."""
    definitions, def_errors = load_trait_definitions(cfg)
    traits, trait_errors = load_traits(cfg)
    skills, skill_errors = load_skills(cfg)
    _, events, ledger_errors = load_ledger(cfg)
    reports, report_errors = load_reports(cfg)
    policies, policy_errors = load_trait_policy(cfg)
    errors = (
        def_errors
        + trait_errors
        + skill_errors
        + ledger_errors
        + report_errors
        + policy_errors
    )
    if errors:
        raise SystemExit("registry has errors; run `check`:\n" + "\n".join(errors))
    return Context(
        upstream=_upstream_traits(traits),
        held=holders(traits),
        definitions=definitions,
        skills=skills,
        events=events,
        current=effective_by_subject(live_events(events)),
        reports=reports,
        sealed=manifest_reports(cfg),
        policies=policies,
    )


def supersede_closure(reports: dict[str, Report]) -> dict[str, set[str]]:
    """Report key → every report it supersedes, transitively."""
    direct = {k: set(r.supersedes or []) for k, r in reports.items()}
    out: dict[str, set[str]] = {}
    for key in reports:
        seen: set[str] = set()
        stack = list(direct[key])
        while stack:
            other = stack.pop()
            if other in seen:
                continue
            seen.add(other)
            stack.extend(direct.get(other, set()))
        out[key] = seen
    return out


def covering(
    reports: dict[str, Report],
    sealed: dict[str, str] | set[str],
    harness: str,
    logical_id: str,
    trait: str,
    sha: str,
) -> list[str]:
    """Sealed reports with a row for this trait of this skill's analysis."""
    return sorted(
        key
        for key, r in reports.items()
        if key in sealed
        and r.harness == harness
        and r.to_sha == sha
        and logical_id in r.skills
        and trait in r.skills[logical_id].traits
    )


def current_row(
    reports: dict[str, Report],
    sealed: dict[str, str] | set[str],
    harness: str,
    logical_id: str,
    trait: str,
    sha: str,
) -> tuple[str, ReportRow] | None:
    """The current row for (trait, analysis): the row in the sealed report for
    that analysis that no other sealed report covering it supersedes. A draft
    never counts. Raises `ValueError` when two covering reports are unrelated."""
    keys = covering(reports, sealed, harness, logical_id, trait, sha)
    # The closure runs over every sealed report, so a chain through a report
    # that does not cover the trait still supersedes (A <- B <- C).
    closure = supersede_closure({k: r for k, r in reports.items() if k in sealed})
    live = [k for k in keys if not any(k in closure[o] for o in keys if o != k)]
    if len(live) > 1:
        raise ValueError(
            f"{harness}:{logical_id}#{trait} at {sha}: unrelated sealed reports "
            + ", ".join(live)
        )
    if not live:
        return None
    return live[0], reports[live[0]].skills[logical_id].traits[trait]


def _compared(name: str) -> str | None:
    return None if name == "none" else name


def compute_scope(
    ctx: Context,
    harness: str,
    logical_id: str,
    compared_with: str,
    exclude: str | None = None,
) -> dict[str, str]:
    """2.6 without reconsideration: trait → `new`, `changed` or `recompare` for
    the entry's newest analysis. `exclude` leaves one report out of the current
    rows (the report being sealed is never its own history)."""
    entry = ctx.upstream[f"{harness}:{logical_id}"]
    sha = entry.newest_sha
    analysis = entry.newest
    scope: dict[str, str] = {}
    if entry.accepted is None:
        scope = {tid: "new" for tid in analysis.traits}
    elif entry.proposed is not None:
        touched = set(analysis.added) | set(analysis.changed)
        scope = {tid: "changed" for tid in analysis.traits if tid in touched}
    sealed = {k for k in ctx.sealed if k != exclude}
    for tid in analysis.traits:
        if tid in scope or _decided(ctx, harness, logical_id, tid, sha):
            continue
        found = current_row(ctx.reports, sealed, harness, logical_id, tid, sha)
        if found is None:
            continue
        if stale_fields(ctx, tid, compared_with, found[1]):
            scope[tid] = "recompare"
    return scope


def stale_fields(
    ctx: Context, tid: str, compared_with: str, row: ReportRow
) -> list[str]:
    """2.6: the row's computed fields that differ from today's computation,
    plus `via` when it is no longer a candidate."""
    today = compute_fact(tid, _compared(compared_with), ctx.held, ctx.definitions)
    stale = [f for f in _COMPUTED if getattr(row, f) != getattr(today, f)]
    if row.via is not None and row.via not in today.candidates:
        stale.append("via")
    return stale


def _decided(ctx: Context, harness: str, logical_id: str, tid: str, sha: str) -> bool:
    """An effective trait ruling at this analysis's sha."""
    event = ctx.current.get(f"{harness}:{logical_id}#{tid}")
    return (
        event is not None
        and event.source is not None
        and _same_sha(event.source.sha, sha)
    )


def _empty_row(scope: str) -> dict[str, Any]:
    return {
        "scope": scope,
        "change": [],
        "fact": "absent",
        "provider": None,
        "candidates": [],
        "via": None,
        "also_in": {},
        "ours": [],
        "recommendation": None,
        "delivery": None,
        "target": None,
        "modification": None,
        "rewording": None,
        "revisit_when": None,
        "policy": None,
        "guide": None,
        "reason": None,
    }


def draft(
    cfg: RegistryConfig,
    harness: str,
    logical_id: str,
    compared_with: str,
    report_path: Path | None = None,
    reconsider: list[str] | None = None,
    refresh: bool = False,
) -> Path:
    """`report draft`: create the report or add (with `refresh`, recompute) one
    skill. Computed fields are filled; judged ones stay null or kept."""
    ctx = load_context(cfg)
    subject = f"{harness}:{logical_id}"
    entry = ctx.upstream.get(subject)
    if entry is None:
        raise SystemExit(f"{subject}: no entry in traits/{harness}.yaml")
    if compared_with != "none":
        if compared_with.startswith("doc:") or compared_with not in ctx.skills:
            raise SystemExit(f"--with {compared_with!r}: not a skill in skills.yaml")
        if compared_with not in ctx.held:
            raise SystemExit(f"--with {compared_with!r}: no traits/ours.yaml entry")
    sha = entry.newest_sha
    analysis = entry.newest
    path = _report_path(cfg, ctx, harness, sha, report_path)
    key = report_key(cfg, path)
    if key in ctx.sealed:
        raise SystemExit(f"{key}: sealed; a later pass writes a new report")
    if path.exists():
        data = load_report(path).model_dump()
    else:
        data = {
            "harness": harness,
            "from_sha": None,
            "to_sha": sha,
            "supersedes": None,
            "analysis_critic": None,
            "comparison_critic": None,
            "themes": None,
            "skills": {},
        }
    if data["harness"] != harness:
        raise SystemExit(f"{key}: a report for {data['harness']!r}")
    if data["to_sha"] != sha:
        raise SystemExit(
            f"{subject}: newest analysis {sha} is not the report's to_sha "
            f"{data['to_sha']}"
        )
    old = data["skills"].get(logical_id)
    if old is not None and not refresh:
        raise SystemExit(f"{key}: {logical_id} is already in the report (--refresh)")
    for tid in reconsider or []:
        if tid not in analysis.traits:
            raise SystemExit(f"--reconsider {tid}: not a trait of {subject} at {sha}")

    scope = compute_scope(ctx, harness, logical_id, compared_with, exclude=key)
    for tid in reconsider or []:
        scope.setdefault(tid, "reconsider")
    old_rows: dict[str, Any] = old["traits"] if old else {}
    for tid, row in old_rows.items():  # a refresh keeps every row it had
        scope.setdefault(tid, row["scope"])
    compared = _compared(compared_with)
    rows: dict[str, Any] = {}
    for tid in [t for t in analysis.traits if t in scope]:
        row = dict(old_rows.get(tid) or _empty_row(scope[tid]))
        row["scope"] = scope[tid]
        row.update(compute_fact(tid, compared, ctx.held, ctx.definitions).model_dump())
        policy = ctx.live_policy.get(tid)
        row["policy"] = policy.prefill().model_dump() if policy else None
        rows[tid] = row
    overlap, placement, suggested = compute_pairing(
        analysis.traits,
        analysis.placement.domain,
        analysis.placement.substage,
        ctx.held,
        ctx.definitions,
        ctx.skills,
    )
    pairing = (
        dict(old["pairing"])
        if old
        else Pairing(
            overlap={},
            placement_match=[],
            suggested=None,
            purpose_match=None,
            purpose=None,
            flag=None,
            reason=None,
        ).model_dump()
    )
    pairing.update(overlap=overlap, placement_match=placement, suggested=suggested)
    data["skills"][logical_id] = {
        "upstream_tree_hash": analysis.tree_hash,
        "accepted": entry.accepted,
        "compared_with": compared_with,
        "pairing": pairing,
        "analysis": old["analysis"]
        if old
        else ReportAnalysis(blind=[], mapping=[]).model_dump(),
        "traits": rows,
    }
    report = Report.model_validate(data)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dump_report(report), encoding="utf-8")
    return path


def _report_path(
    cfg: RegistryConfig,
    ctx: Context,
    harness: str,
    sha: str,
    given: Path | None,
) -> Path:
    """`--report`, else the one draft for this harness and analysis, else a new
    `reviews/<today>-upstream-<harness>-<sha>.yaml`."""
    if given is not None:
        path = given if given.is_absolute() else cfg.repo_root / given
        if path.suffix != ".yaml" or path.resolve().parent != cfg.reviews_dir.resolve():
            raise SystemExit(f"--report {given}: must be a reviews/*.yaml file")
        return path
    drafts = sorted(
        k
        for k, r in ctx.reports.items()
        if k not in ctx.sealed and r.harness == harness and r.to_sha == sha
    )
    if len(drafts) > 1:
        raise SystemExit(
            "more than one draft: name one with --report\n" + "\n".join(drafts)
        )
    if drafts:
        return cfg.repo_root / drafts[0]
    today = datetime.now(tz=UTC).date().isoformat()
    return cfg.reviews_dir / f"{today}-upstream-{harness}-{sha}.yaml"


def dump_report(report: Report) -> str:
    return yaml.safe_dump(
        report.model_dump(), sort_keys=False, allow_unicode=True, width=88
    )


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def seal(cfg: RegistryConfig, path: Path) -> list[str]:
    """`report seal`: refuse (errors) or record the report's content hash. A
    report passes when its schema holds, both critics passed, its `supersedes`
    names sealed reports with no cycle, its evidence is complete (1.3, 2.1),
    every in-scope trait has exactly one row (2.7) and the check rules hold in
    full."""
    from curation.registry.checks.reports import (
        ambiguity_errors,
        evidence_errors,
        report_errors,
        supersession_errors,
    )

    if not path.is_absolute():
        path = cfg.repo_root / path
    if not path.is_file():
        return [f"{path}: no such report"]
    ctx = load_context(cfg)
    key = report_key(cfg, path)
    if key not in ctx.reports:
        return [f"{key}: not a reviews/*.yaml report"]
    if key in ctx.sealed:
        if ctx.sealed[key] == _sha256(path):
            return []
        return [f"{key}: already sealed and has CHANGED — refusing to re-seal"]
    report = ctx.reports[key]
    errors: list[str] = []
    for name in ("analysis_critic", "comparison_critic"):
        critic = getattr(report, name)
        if critic is None or critic.verdict != "pass":
            errors.append(f"{key}: {name} has not passed")
    closure = supersede_closure(ctx.reports)
    errors += supersession_errors(
        key, report, ctx.reports, ctx.sealed, closure, sealing=True
    )
    errors += report_errors(cfg, key, report, ctx.upstream, complete=True)
    errors += evidence_errors(key, report, ctx.upstream)
    errors += _scope_errors(ctx, key, report)
    after = {**ctx.sealed, key: ""}
    errors += [e for e in ambiguity_errors(ctx.reports, after, closure) if key in e]
    if not errors:
        seal_report_digest(cfg, key, _sha256(path))
    return errors


def _scope_errors(ctx: Context, key: str, report: Report) -> list[str]:
    """2.7: one row per in-scope trait, each with the scope it is in for."""
    errors: list[str] = []
    for logical_id, skill in report.skills.items():
        where = f"{key}: {logical_id}"
        entry = ctx.upstream.get(f"{report.harness}:{logical_id}")
        if entry is None or entry.newest_sha != report.to_sha:
            errors.append(f"{where}: newest analysis is not the report's to_sha")
            continue
        if skill.accepted != entry.accepted:
            errors.append(f"{where}: accepted {skill.accepted} is not the entry's")
        try:
            scope = compute_scope(
                ctx, report.harness, logical_id, skill.compared_with, exclude=key
            )
        except ValueError as exc:
            errors.append(f"{where}: {exc}")
            continue
        for tid, why in scope.items():
            row = skill.traits.get(tid)
            if row is None:
                errors.append(f"{where}: in-scope trait {tid} ({why}) has no row")
            elif row.scope != why:
                errors.append(f"{where}: {tid}: scope {row.scope}, in scope as {why}")
        for tid, row in skill.traits.items():
            if tid not in scope and row.scope != "reconsider":
                errors.append(f"{where}: {tid}: row is not in scope ({row.scope})")
    return errors


# --- generated Markdown ----------------------------------------------------------


def _critic(name: str, report: Report) -> str:
    critic = getattr(report, name)
    if critic is None:
        return f"{name.replace('_', ' ')}: none"
    return f"{name.replace('_', ' ')}: {critic.verdict} ({critic.by}, {critic.date})"


def render_report(name: str, report: Report) -> str:
    """The readable `<report>.md` beside each report file."""
    lines = [
        f"<!-- Generated by `registry.py build` from {name}; do not edit. -->",
        "",
        (
            f"# Upstream review: {report.harness} "
            f"{report.from_sha or '(new)'} → {report.to_sha}"
        ),
        "",
        f"- {_critic('analysis_critic', report)}",
        f"- {_critic('comparison_critic', report)}",
        "- supersedes: " + (", ".join(report.supersedes or []) or "none"),
        "",
        "## Themes",
        "",
        (report.themes or "(none yet)").rstrip(),
    ]
    for logical_id, skill in report.skills.items():
        p = skill.pairing
        lines += [
            "",
            f"## {logical_id}",
            "",
            (
                f"Compared with `{skill.compared_with}`; upstream tree hash "
                f"`{skill.upstream_tree_hash}`."
            ),
            "",
            "| Holder | Overlap | Placement match |",
            "|---|---|---|",
        ]
        for holder in sorted(set(p.overlap) | set(p.placement_match)):
            match = "yes" if holder in p.placement_match else ""
            lines.append(f"| {holder} | {p.overlap.get(holder, 0)} | {match} |")
        lines += [
            "",
            (
                f"Suggested: {p.suggested or 'none'} · purpose match: "
                f"{p.purpose_match or '(not judged)'} · flag: {p.flag or 'none'}"
            ),
        ]
        if p.purpose:
            lines.append(f"Purpose: {p.purpose}")
        if p.reason:
            lines.append(f"Reason: {p.reason}")
        lines += ["", "### Blind extraction", ""]
        lines += [f"{i}. {text}" for i, text in enumerate(skill.analysis.blind, 1)]
        lines += ["", "### Mapping", ""]
        lines += [
            f"- {m.line} → {', '.join(m.to)} ({m.mark})" for m in skill.analysis.mapping
        ]
        lines += ["", "### Traits", ""]
        lines += [_row_line(tid, row) for tid, row in skill.traits.items()]
    return "\n".join(lines) + "\n"


def _row_line(tid: str, row: ReportRow) -> str:
    fact: str = row.fact
    if row.provider:
        fact += f" via `{row.via}`" if row.via else f" in `{row.provider}`"
    parts = [f"- `{tid}` ({row.scope}): {fact}"]
    if row.recommendation:
        rec: str = row.recommendation
        if row.delivery:
            rec += f", {row.delivery}"
        if row.target:
            rec += f" → {row.target}"
        parts.append(rec)
    if row.guide:
        rules = f" [{', '.join(row.guide.rules)}]" if row.guide.rules else ""
        parts.append(f"guide {row.guide.verdict}{rules}")
    if row.also_in:
        parts.append(
            "also in " + ", ".join(f"{h} ({v})" for h, v in row.also_in.items())
        )
    for label in ("modification", "rewording", "revisit_when", "reason"):
        value = getattr(row, label)
        if value:
            parts.append(f"{label.replace('_', ' ')}: {value}")
    return "; ".join(parts)
