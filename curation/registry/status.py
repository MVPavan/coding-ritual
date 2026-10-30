"""`registry.py status` (stages-design Stage 4): where every upstream skill,
trait and capability stands. Computed from the catalog, the trait files, the
reports and the ledger; nothing stores it (4.2)."""

from __future__ import annotations

from dataclasses import dataclass

from curation.registry.ledger import (
    WHOLE_SKILL_KINDS,
    _is_trait_subject,
    _same_sha,
    _trait_slug,
    build_lifecycle,
    effective_traits_for,
    is_carried,
    live_events,
    retained_adoptions,
    withdrawn_destinations,
)
from curation.registry.models import Event, UpstreamTraitEntry
from curation.registry.reports import Context, current_row, stale_fields
from curation.registry.traits import _trait_satisfied
from curation.scan.models import Catalog

# 4.3, first match wins; a later stage is less advanced.
STAGES = (
    "removed upstream",
    "needs re-analysis",
    "decided",
    "needs re-comparison",
    "reported",
    "in review",
    "analysed",
    "not analysed",
)
NO_TRAITS = "analysed, no traits"
WHOLE_SKILL = "decided (whole skill)"
AMBIGUOUS = "ambiguous rows (see check)"


# A skill's least advanced trait (4.3), by progress: first is least advanced.
# Separate from the first-match precedence above, which is per trait.
PROGRESS = (
    "not analysed",
    "needs re-analysis",
    "analysed",
    "in review",
    "needs re-comparison",
    "reported",
    "decided",
    "removed upstream",
)


def stage_rank(stage: str) -> int:
    """Display order (4.3 precedence): a higher rank is less advanced."""
    return STAGES.index(stage) if stage in STAGES else len(STAGES)


def progress_rank(stage: str) -> int:
    """Progress order: a lower rank is less advanced; an ambiguous trait,
    which `check` fails on, is least advanced of all."""
    return PROGRESS.index(stage) if stage in PROGRESS else -1


@dataclass(frozen=True)
class TraitStatus:
    trait: str
    stage: str
    ruling: str | None  # the effective event kind
    provision: str | None  # adopts: delivered, pending, withdrawn, no longer provided


@dataclass(frozen=True)
class SkillStatus:
    logical_id: str
    stage: str
    traits: list[TraitStatus]


def provisions(ctx: Context) -> dict[str, str]:
    """Trait subject → whether we provide it now (4.3): *pending* while its
    effective event is a pending adopt; otherwise, per retained adoption,
    *withdrawn*, *no longer provided* (the target retired without replacement
    or no longer lists it) or *delivered*. Several destinations are joined."""
    live = live_events(ctx.events)
    forward, retired = build_lifecycle(live)
    withdrawn = withdrawn_destinations(ctx.events, forward)
    states: dict[str, list[tuple[str, str]]] = {}
    for (subject, dest), adopt in retained_adoptions(ctx.events, forward).items():
        tid = adopt.into or _trait_slug(subject) or ""
        listed = ctx.held.get(dest)
        if (subject, dest) in withdrawn:
            state = "withdrawn"
        elif (
            dest in retired
            or listed is None
            or not _trait_satisfied(tid, listed, ctx.definitions)
        ):
            state = "no longer provided"
        else:
            state = "delivered"
        states.setdefault(subject, []).append((dest, state))
    out: dict[str, str] = {}
    for subject, found in states.items():
        if len(found) == 1:
            out[subject] = found[0][1]
        else:
            out[subject] = ", ".join(f"{s} ({d})" for d, s in sorted(found))
    for subject, event in ctx.current.items():
        if _is_trait_subject(subject) and event.kind == "adopt" and event.pending:
            out[subject] = "pending"
    return out


def _decided(entry: UpstreamTraitEntry, sha: str, tid: str, event: Event) -> bool:
    """An effective ruling recorded at the analysis, or carried to it (3.8)."""
    at = event.source.sha if event.source else None
    return _same_sha(at, sha) or is_carried(entry, tid, at, sha)


def _trait_stage(
    ctx: Context,
    harness: str,
    logical_id: str,
    entry: UpstreamTraitEntry,
    tid: str,
    event: Event | None,
) -> str:
    """4.3 for one listed trait of a skill still in the catalog and analysed
    at its current tree hash."""
    sha = entry.newest_sha
    if event is not None and _decided(entry, sha, tid, event):
        return "decided"
    try:
        found = current_row(ctx.reports, ctx.sealed, harness, logical_id, tid, sha)
    except ValueError:  # two unrelated sealed reports: `check` fails on it
        return AMBIGUOUS
    if found is not None:
        compared = ctx.reports[found[0]].skills[logical_id].compared_with
        if stale_fields(ctx, tid, compared, found[1]):
            return "needs re-comparison"
        return "reported"
    drafted = any(
        key not in ctx.sealed
        and r.harness == harness
        and r.to_sha == sha
        and logical_id in r.skills
        and tid in r.skills[logical_id].traits
        for key, r in ctx.reports.items()
    )
    return "in review" if drafted else "analysed"


def skill_status(
    ctx: Context,
    harness: str,
    logical_id: str,
    catalog_tree_hash: str | None,
    in_catalog: bool,
    provided: dict[str, str],
) -> SkillStatus:
    """A skill's stage is its least advanced trait's (4.3), with the special
    cases: *analysed, no traits*, and *decided (whole skill)* for a
    whole-skill ruling without an accepted analysis."""
    subject = f"{harness}:{logical_id}"
    entry = ctx.upstream.get(subject)
    rulings = effective_traits_for(ctx.current, subject)
    checkpoint = ctx.current.get(subject)
    whole = (
        checkpoint is not None
        and checkpoint.kind in WHOLE_SKILL_KINDS
        and not rulings
        and (entry is None or entry.accepted is None)
    )
    if entry is None:
        if not in_catalog:
            return SkillStatus(logical_id, "removed upstream", [])
        return SkillStatus(logical_id, WHOLE_SKILL if whole else "not analysed", [])
    analysis = entry.newest
    reanalyse = catalog_tree_hash is not None and catalog_tree_hash != (
        analysis.tree_hash
    )
    traits: list[TraitStatus] = []
    for tid in [*analysis.traits, *analysis.removed]:
        event = rulings.get(tid)
        if tid in analysis.removed or not in_catalog:
            stage = "removed upstream"
        elif reanalyse:
            stage = "needs re-analysis"
        else:
            stage = _trait_stage(ctx, harness, logical_id, entry, tid, event)
        traits.append(
            TraitStatus(
                tid,
                stage,
                event.kind if event else None,
                provided.get(f"{subject}#{tid}"),
            )
        )
    if not in_catalog:
        stage = "removed upstream"
    elif reanalyse:
        stage = "needs re-analysis"
    elif not analysis.traits:
        stage = NO_TRAITS
    else:
        stage = min((t.stage for t in traits), key=progress_rank)
    if whole:
        stage = f"{WHOLE_SKILL} + {stage}"
    return SkillStatus(logical_id, stage, traits)


def capability_state(event: Event | None, changed: str) -> str:
    """4.4, a capability that is not a skill: not reviewed, decided or
    changed since (`gap`'s change detection); *removed* is listed apart."""
    if event is None:
        return "not reviewed"
    return "changed since" if changed == "yes" else "decided"


def skill_statuses(ctx: Context, catalog: Catalog) -> list[SkillStatus]:
    """Every upstream skill of the harness: in its catalog, or with an entry
    or a ruling though it left the catalog."""
    harness = catalog.repo
    provided = provisions(ctx)
    present = {
        c.logical_id: c.tree_hash
        for c in catalog.capabilities
        if c.kind.value == "skill"
    }
    known = set(present)
    for subject in ctx.upstream:
        if subject.startswith(f"{harness}:"):
            known.add(subject.split(":", 1)[1])
    for subject, event in ctx.current.items():
        if (
            not _is_trait_subject(subject)
            and event.source is not None
            and event.source.repo == harness
            and event.source.logical_id.startswith("skill:")
        ):
            known.add(event.source.logical_id)
    return [
        skill_status(
            ctx, harness, lid, present.get(lid) or None, lid in present, provided
        )
        for lid in sorted(known)
    ]
