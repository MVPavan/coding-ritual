"""Generated blocks of a skill record (lineage, history, reviews, traits, sources)."""

from __future__ import annotations

import re

from curation.registry.ledger import (
    _carried_replacements,
    _is_trait_subject,
    _trait_base,
    _trait_slug,
    build_lifecycle,
    effective_by_subject,
    live_events,
    resolve_skill,
    retained_adoptions,
    withdrawn_destinations,
)
from curation.registry.models import Event, OursTraitEntry, SkillEntry, TraitDefinition
from curation.registry.text import _one_line

TRAITS_OPEN = "<!-- registry:generated traits -->"


TRAITS_CLOSE = "<!-- /registry:generated traits -->"


SOURCES_OPEN = "<!-- registry:generated sources -->"


SOURCES_CLOSE = "<!-- /registry:generated sources -->"


DECLINED_OPEN = "<!-- registry:generated declined -->"


DECLINED_CLOSE = "<!-- /registry:generated declined -->"


LINEAGE_OPEN = "<!-- registry:generated lineage -->"


LINEAGE_CLOSE = "<!-- /registry:generated lineage -->"


HISTORY_OPEN = "<!-- registry:generated history -->"


HISTORY_CLOSE = "<!-- /registry:generated history -->"


REVIEWS_OPEN = "<!-- registry:generated reviews -->"


REVIEWS_CLOSE = "<!-- /registry:generated reviews -->"


# Citation forms recognised in an event's `evidence` entries and `why` text.
# A registry review file (with or without a `harness_lifecycle/registry/`
# prefix) and an old-prose comparison folder, now under archive/.
_REVIEW_RE = re.compile(r"reviews/(\d{4}-\d{2}-\d{2}-[a-z]+-[A-Za-z0-9._-]+?\.md)")


_COMPARISON_RE = re.compile(r"skill-comparisons/([A-Za-z0-9._-]+)")


def _names(skill: str, name: str | None, forward: dict[str, str]) -> bool:
    """Whether `name` is `skill` itself or an earlier name `rename`/`merge`
    carried into it, so a renamed record keeps its lineage and history. The
    chain may run past `skill`: one merged into a playbook keeps its own."""
    seen: set[str] = set()
    while name is not None and name not in seen:
        if name == skill:
            return True
        seen.add(name)
        name = forward.get(name)
    return False


def _concerns(skill: str, event: Event, forward: dict[str, str]) -> bool:
    """Whether the event belongs in `skill`'s history: it targets the skill
    or is about it, under any name the skill has had."""
    ours = event.subject[len("ours:") :] if event.subject.startswith("ours:") else None
    return _names(skill, event.skill, forward) or _names(skill, ours, forward)


def _lineage_block(skill: str, events: list[Event], forward: dict[str, str]) -> str:
    """Adopted lineage: one entry per adopted trait (the last delivered adopt,
    else the pending one, labelled), and a capability checkpoint only when no
    trait adopt into this skill stands for it (review r1 #12)."""
    adopts = [
        e
        for e in events
        if _names(skill, e.skill, forward)
        and e.kind in {"adopt", "adopt-merged"}
        and e.source is not None
    ]
    by_trait: dict[str, Event] = {}
    for e in adopts:
        if _is_trait_subject(e.subject):
            held = by_trait.get(e.subject)
            if held is None or held.pending or not e.pending:
                by_trait[e.subject] = e
    trait_bases = {_trait_base(subject) for subject in by_trait}
    rows: list[Event] = []
    for e in adopts:
        if _is_trait_subject(e.subject):
            if by_trait.get(e.subject) is e:
                rows.append(e)
        elif e.subject not in trait_bases:
            rows.append(e)
    if not rows:
        return "No adopted lineage recorded."
    lines: list[str] = []
    for event in rows:
        src = event.source
        assert src is not None
        sha = f" @ {src.sha}" if src.sha else ""
        path = f" `{src.path}`" if src.path else ""
        pending = f" (pending {event.pending})" if event.pending else ""
        lines.append(f"- **{event.subject}**{path}{sha}{pending}")
        adapt = event.adaptation
        if adapt and adapt.merged_from:
            for merged in adapt.merged_from:
                lines.append(f"  - merged from: {merged}")
        if adapt and adapt.modifications:
            for mod in adapt.modifications:
                lines.append(f"  - modified: {mod}")
        if adapt and adapt.deliberately_dropped:
            for drop in adapt.deliberately_dropped:
                lines.append(f"  - dropped: {drop}")
    return "\n".join(lines)


def _history_block(
    skill: str, events: list[Event], dead: set[str], forward: dict[str, str]
) -> str:
    rows = [e for e in events if _concerns(skill, e, forward)]
    if not rows:
        return "No ledger history recorded."
    lines: list[str] = []
    for event in reversed(rows):  # newest first: `events` is in recording order
        mark = " *(superseded)*" if event.id in dead else ""
        lines.append(
            f"- `{event.date}` **{event.kind}** ({event.id}){mark}: {_one_line(event.why, 160)}"
        )
    return "\n".join(lines)


def _reviews_block(skill: str, events: list[Event], forward: dict[str, str]) -> str:
    """Every review cited by the same events the history block lists. Registry
    reviews first (newest file name first), then archived comparisons
    (alphabetical). Deduplicated; empty renders a single sentinel line."""
    rows = [e for e in events if _concerns(skill, e, forward)]
    review_files: set[str] = set()
    comparisons: set[str] = set()
    for event in rows:
        for text in [*event.evidence, event.why]:
            review_files.update(m.group(1) for m in _REVIEW_RE.finditer(text))
            comparisons.update(m.group(1) for m in _COMPARISON_RE.finditer(text))
    lines = [
        f"- [{name}](../../reviews/{name})"
        for name in sorted(review_files, reverse=True)
    ]
    lines += [
        f"- [skill-comparisons/{family}](../../../archive/skill-comparisons/{family}/)"
        for family in sorted(comparisons)
    ]
    return "\n".join(lines) if lines else "None yet."


def _traits_record_block(
    skill: str,
    ours_traits: dict[str, OursTraitEntry],
    definitions: dict[str, TraitDefinition],
) -> str:
    """The skill's traits from `traits/ours.yaml`, with their definitions (§7)."""
    entry = ours_traits.get(skill)
    if entry is None or not entry.traits:
        return "No traits recorded."
    lines: list[str] = []
    for tid in entry.traits:
        d = definitions.get(tid)
        text = d.definition if d else ""
        note = entry.notes.get(tid)
        suffix = f" ({note})" if note else ""
        lines.append(f"- `{tid}`: {text}{suffix}")
    return "\n".join(lines)


def _sources_block(
    skill: str,
    events: list[Event],
    current: dict[str, Event],
    forward: dict[str, str],
    withdrawn: dict[tuple[str, str], str],
    retired: set[str],
    ours_traits: dict[str, OursTraitEntry],
    definitions: dict[str, TraitDefinition],
) -> str:
    """Per trait id, the upstream traits adopted into it — the last delivered
    adopt even when later superseded, withdrawn or replaced upstream (§5, §7).
    `skill` is the current survivor name; adoptions are matched through the
    lifecycle.

    Reads the same `retained_adoptions` that the coverage check (C) reads, so the
    listed sources and the enforced obligations can never disagree (review r3)."""
    adopts: dict[str, Event] = {
        subject: adopt
        for (subject, dest), adopt in retained_adoptions(events, forward).items()
        if dest == skill
    }
    if not adopts:
        return "No adopted traits recorded."
    replaced = _carried_replacements(current)
    listed = set(ours_traits[skill].traits) if skill in ours_traits else set()
    grouped: dict[str, list[str]] = {}
    for subject, event in adopts.items():
        assert event.subject is not None
        tid = event.into or _trait_slug(subject)
        sha = event.source.sha if event.source else None
        label = f"adopted at {sha}" if sha else "adopted"
        d = definitions.get(tid or "")
        if d and d.retired and tid not in listed:
            label += f"; adopted as {tid}, now {', '.join(d.retired.replaced_by)}"
        if (subject, skill) in withdrawn:
            label += f"; withdrawn {withdrawn[(subject, skill)]}"
        elif skill in retired:
            label += "; no longer provided"
        elif subject in replaced:
            b = replaced[subject]
            bid = _trait_slug(b.subject)
            label += f"; upstream replaced it with {bid} ({b.kind})"
        else:
            cur = current.get(subject)
            if cur is not None and cur.kind != "adopt":
                label += f"; current upstream revision {cur.kind}"
        grouped.setdefault(tid or "(unmapped)", []).append(f"  - `{subject}` ({label})")
    lines: list[str] = []
    for tid in sorted(grouped):
        lines.append(f"- `{tid}`:")
        lines.extend(sorted(grouped[tid]))
    return "\n".join(lines)


def _declined_block(
    skill: str, current: dict[str, Event], forward: dict[str, str]
) -> str:
    """Upstream traits whose effective ruling is reject/defer, considered for this
    skill, with the reason (§7). A `doc:` survivor has no record, so a skill
    merged into a playbook keeps the ones considered under its names."""
    lines: list[str] = []
    for subject, event in sorted(current.items()):
        if not event.skill or ":" in event.skill:
            continue
        survivor = resolve_skill(event.skill, forward)
        if (
            _is_trait_subject(subject)
            and event.kind in {"reject", "defer"}
            and (
                survivor == skill
                or (survivor.startswith("doc:") and _names(skill, event.skill, forward))
            )
        ):
            lines.append(f"- `{subject}` ({event.kind}): {_one_line(event.why, 160)}")
    return "\n".join(lines) if lines else "No declined traits recorded."


def _frontmatter_text(skill: str, entry: SkillEntry) -> str:
    """The record frontmatter: today's keys and order (README §3)."""
    family = f" {entry.family}" if entry.family else ""  # none: a bare `family:` (YAML null)
    return (
        f"---\nskill: {skill}\ndomain: {entry.domain}\nstage: {entry.stage}\n"
        f"substage: {entry.substage}\nsecondary: [{', '.join(entry.secondary)}]\n"
        f"family:{family}\naliases: [{', '.join(entry.aliases)}]\n"
        f"status: {entry.status}\n---\n"
    )


def render_record(
    skill: str,
    entry: SkillEntry,
    description: str,
    events: list[Event],
    dead: set[str],
    ours_traits: dict[str, OursTraitEntry],
    definitions: dict[str, TraitDefinition],
) -> str:
    """The whole record (stages-design §Skills file): frontmatter from
    `skills.yaml`, the title, the description (`skill_description`), the boundary when set,
    then every generated block."""
    live = live_events(events)
    current = effective_by_subject(live)
    forward, retired = build_lifecycle(live)
    withdrawn = withdrawn_destinations(events, forward)
    blocks = [
        (
            TRAITS_OPEN,
            _traits_record_block(skill, ours_traits, definitions),
            TRAITS_CLOSE,
        ),
        (LINEAGE_OPEN, _lineage_block(skill, events, forward), LINEAGE_CLOSE),
        (HISTORY_OPEN, _history_block(skill, events, dead, forward), HISTORY_CLOSE),
        (REVIEWS_OPEN, _reviews_block(skill, events, forward), REVIEWS_CLOSE),
        (
            SOURCES_OPEN,
            _sources_block(
                skill,
                events,
                current,
                forward,
                withdrawn,
                retired,
                ours_traits,
                definitions,
            ),
            SOURCES_CLOSE,
        ),
        (DECLINED_OPEN, _declined_block(skill, current, forward), DECLINED_CLOSE),
    ]
    parts = [f"# {skill}", description or "No description."]
    if entry.boundary:
        parts.append(f"**Boundary:** {entry.boundary.strip()}")
    parts += [
        f"{open_tag}\n{body}\n{close_tag}" for open_tag, body, close_tag in blocks
    ]
    return _frontmatter_text(skill, entry) + "\n\n".join(parts) + "\n"
