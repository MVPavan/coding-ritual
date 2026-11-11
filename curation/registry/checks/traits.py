"""Trait checks: definitions, the traits/ folder, warnings and trait-level rulings."""

from __future__ import annotations

import json
from datetime import date as date_cls
from pathlib import Path
from typing import Any, Literal

from curation.registry.catalogs import _catalog_subjects
from curation.registry.config import RegistryConfig
from curation.registry.ledger import (
    _is_trait_level,
    _is_trait_subject,
    _same_sha,
    _trait_base,
    _trait_slug,
    effective_by_subject,
    effective_traits_for,
    is_carried,
    live_events,
    resolve_skill,
    retained_adoptions,
    withdrawn_destinations,
)
from curation.registry.loaders import _catalog_files, traits_file_for
from curation.registry.models import (
    Event,
    OursTraitEntry,
    RoundHeader,
    TraitDefinition,
    UpstreamTraitEntry,
)
from curation.registry.steps import Playbook
from curation.registry.traits import (
    _doc_tree_hash,
    _our_tree_hashes,
    _ours_traits,
    _trait_satisfied,
    _upstream_traits,
    doc_holders,
)
from curation.scan.models import Catalog


def _checkpoint_expectation(kinds: list[str]) -> tuple[str, bool]:
    """(expected capability kind, whether a target is required) for the trait
    rulings of one checkpoint (removed traits already excluded), per README §5b."""
    adopts = [k for k in kinds if k == "adopt"]
    if adopts and len(adopts) == len(kinds):
        return "adopt", True
    if adopts:
        return "adopt-merged", True
    if len(set(kinds)) == 1:
        return kinds[0], False
    return "reject", False


def _check_trait_definitions(
    definitions: dict[str, TraitDefinition],
) -> list[str]:
    """`distinct_from` and `replaced_by` resolve to defined traits (§1, §4)."""
    errors: list[str] = []
    for tid, d in definitions.items():
        for other in d.distinct_from:
            if other not in definitions:
                errors.append(
                    f"trait-definitions.yaml: {tid}: distinct_from {other!r} is undefined"
                )
        if d.retired:
            for repl in d.retired.replaced_by:
                if repl not in definitions:
                    errors.append(
                        f"trait-definitions.yaml: {tid}: replaced_by {repl!r} is undefined"
                    )
    return errors


DocHolderKind = Literal["agents", "project-document", "playbook"]


def doc_holder_kind(cfg: RegistryConfig, rel: str) -> DocHolderKind | None:
    """What a `doc:` holder's repository path names, or None when it may hold
    no traits: `AGENTS.md`, a flat `.repo-context/<file>` (stages-design 1.5)
    or a playbook file (T1, T3). Only the normalised spelling names one, so a
    file has one `doc:` subject."""
    parts = Path(rel).parts
    if ".." in parts or Path(rel).as_posix() != rel:
        return None
    if rel == "AGENTS.md":
        return "agents"
    if len(parts) == 2 and parts[0] == ".repo-context":
        return "project-document"
    playbooks = cfg.playbooks_dir.relative_to(cfg.repo_root).parts
    if parts[:-1] == playbooks and rel.endswith(".md"):
        return "playbook"
    return None


def _doc_key_errors(cfg: RegistryConfig, key: str, entry: OursTraitEntry) -> list[str]:
    """A `doc:` entry of traits/ours.yaml names `AGENTS.md` or a
    `.repo-context/<file>` that exists, and its `tree_hash` is current
    (stages-design 1.4-1.5, check item 5). A playbook is a `doc:` holder too,
    but its list is its frontmatter (St2), never an entry here."""
    rel = key[len("doc:") :]
    kind = doc_holder_kind(cfg, rel)
    if kind == "playbook":
        return [
            (
                f"traits/ours.yaml: {key}: a playbook's traits live in its "
                f"frontmatter, not here"
            )
        ]
    if kind is None:
        return [
            (
                f"traits/ours.yaml: {key}: a doc: key is AGENTS.md, "
                f".repo-context/<file> or a playbook"
            )
        ]
    path = cfg.repo_root / rel
    if not path.is_file():
        return [f"traits/ours.yaml: {key}: no such file"]
    if entry.tree_hash != _doc_tree_hash(rel, path.read_bytes()):
        return [f"traits/ours.yaml: {key}: tree_hash is stale"]
    return []


def _catalog_tree_hashes(cfg: RegistryConfig) -> dict[str, tuple[str | None, str]]:
    """`<repo>:<logical_id>` → (catalog source_commit, tree_hash) for every
    catalog capability that carries a tree hash."""
    out: dict[str, tuple[str | None, str]] = {}
    for cat_path in _catalog_files(cfg):
        try:
            catalog = Catalog.from_dict(
                json.loads(cat_path.read_text(encoding="utf-8"))
            )
        except Exception:  # noqa: BLE001, S112 - malformed catalogs ignored here
            continue
        for cap in catalog.capabilities:
            if cap.tree_hash:
                key = f"{catalog.repo}:{cap.logical_id}"
                out[key] = (catalog.source_commit, cap.tree_hash)
    return out


def _check_traits_yaml(
    cfg: RegistryConfig,
    traits: dict[str, OursTraitEntry | UpstreamTraitEntry],
    definitions: dict[str, TraitDefinition],
    records: set[str],
    ours: Any,
    events: list[Event],
) -> list[str]:
    """Each entry: a resolvable key, defined trait IDs, no repeats, metadata keys
    that are defined and belong to the entry, and — for an ours or doc entry — a
    tree_hash matching its folder or file today (§2).

    An upstream key is `<repo>:skill:<path>` and is in that repo's catalog or
    has ledger history (an event on the capability, which is then a
    removed-upstream subject) (review r1 #7). In each analysis, `added` and
    `changed` keys are listed, `removed` keys are not; the newest analysis's
    `tree_hash` matches the catalog while the pin is its sha (stages-design
    §Entries, 1.3)."""
    errors: list[str] = []
    tree_hashes = _our_tree_hashes(ours)
    catalog_subjects = _catalog_subjects(cfg)
    catalog_hashes = _catalog_tree_hashes(cfg)
    ruled = {e.subject for e in events if not _is_trait_subject(e.subject)}
    for key, entry in traits.items():
        where = f"traits/{traits_file_for(key)}: {key}"
        if isinstance(entry, OursTraitEntry):
            if key.startswith("doc:"):
                errors += _doc_key_errors(cfg, key, entry)
            else:
                skill = key[len("ours:") :]
                if skill not in records:
                    errors.append(f"{where}: no skills.yaml entry for {skill!r}")
                want = tree_hashes.get(skill)
                if want is not None and entry.tree_hash != want:
                    errors.append(f"{where}: tree_hash is stale")
            errors += _trait_list_errors(where, entry.traits, definitions)
            errors += _metadata_errors(
                where, {"notes": entry.notes}, set(entry.traits), definitions
            )
            continue
        repo, _, logical = key.partition(":")
        if not repo or not logical.startswith("skill:") or logical == "skill:":
            errors.append(f"{where}: an upstream key is <repo>:skill:<path>")
        elif key not in catalog_subjects and key not in ruled:
            errors.append(
                f"{where}: not in its catalog and has no "
                f"removed-upstream history in the ledger"
            )
        pinned = catalog_hashes.get(key)
        if (
            pinned is not None
            and _same_sha(pinned[0], entry.newest_sha)
            and entry.newest.tree_hash != pinned[1]
        ):
            errors.append(
                f"{where}: analysis {entry.newest_sha} tree_hash disagrees "
                f"with the catalog"
            )
        for sha, analysis in entry.analyses.items():
            at = f"{where}: analysis {sha}"
            for tid in analysis.removed:
                if tid in analysis.traits:
                    errors.append(f"{at}: removed trait {tid!r} is still listed")
            listed = set(analysis.traits)
            errors += _trait_list_errors(at, analysis.traits, definitions)
            errors += _metadata_errors(
                at,
                {"added": analysis.added, "changed": analysis.changed},
                listed,
                definitions,
            )
            errors += _metadata_errors(
                at,
                {"removed": analysis.removed, "notes": analysis.notes},
                listed | set(analysis.removed),
                definitions,
            )
    return errors


def _trait_list_errors(
    where: str, traits: list[str], definitions: dict[str, TraitDefinition]
) -> list[str]:
    errors: list[str] = []
    seen: set[str] = set()
    for tid in traits:
        if tid in seen:
            errors.append(f"{where}: trait {tid!r} is listed twice")
        seen.add(tid)
        if tid not in definitions:
            errors.append(f"{where}: trait {tid!r} is undefined")
    return errors


def _metadata_errors(
    where: str,
    fields: dict[str, dict[str, str]],
    allowed: set[str],
    definitions: dict[str, TraitDefinition],
) -> list[str]:
    errors: list[str] = []
    for name, keys in fields.items():
        for tid in keys:
            if tid not in definitions:
                errors.append(f"{where}: {name} trait {tid!r} is undefined")
            elif tid not in allowed:
                errors.append(f"{where}: {name} trait {tid!r} is not in the entry")
    return errors


def _retired_trait_warnings(
    traits: dict[str, OursTraitEntry | UpstreamTraitEntry],
    definitions: dict[str, TraitDefinition],
) -> list[str]:
    """While any entry lists a retired trait, warn and name the holders (§1)."""
    holders: dict[str, list[str]] = {}
    for key, entry in traits.items():
        listed = (
            entry.newest.traits
            if isinstance(entry, UpstreamTraitEntry)
            else entry.traits
        )
        for tid in listed:
            d = definitions.get(tid)
            if d and d.retired:
                holders.setdefault(tid, []).append(key)
    return [
        f"retired trait {tid!r} still listed by {', '.join(sorted(keys))}"
        for tid, keys in sorted(holders.items())
    ]


def _reference_analysis(entry: UpstreamTraitEntry) -> Any:
    """The analysis rulings are judged against: the accepted one, else the
    newest (a proposed-only entry)."""
    return entry.analyses[entry.accepted] if entry.accepted else entry.newest


def _check_trait_level(
    cfg: RegistryConfig,
    headers: list[RoundHeader],
    events: list[Event],
    ours: Any,
    forward: dict[str, str],
    retired: set[str],
    definitions: dict[str, TraitDefinition],
    traits: dict[str, OursTraitEntry | UpstreamTraitEntry],
    playbooks: dict[str, Playbook],
) -> list[str]:
    """Trait-level consistency, completeness, membership and coverage (§5).

    `events` is the RAW list: the current ruling and withdrawal state come from
    live events, but coverage obligations (C) read raw events so a superseded
    adopt still obliges the trait list until an ours-side `update` withdraws it
    (review r3)."""
    errors: list[str] = []
    live = live_events(events)
    current = effective_by_subject(live)
    upstream_traits = _upstream_traits(traits)
    ours_traits = _ours_traits(traits)
    tree_hashes = _our_tree_hashes(ours)
    trait_rounds = {h.round_id for h in headers if h.trait_level}
    withdrawn = withdrawn_destinations(events, forward)

    # (A) Consistency — whenever a capability has effective trait rulings, it
    # needs an effective checkpoint (review r1 #2), and that checkpoint (whatever
    # its kind) must agree with them (review #3).
    trait_bases = {_trait_base(s) for s in current if _is_trait_subject(s)}
    for base in sorted(trait_bases):
        checkpoint = current.get(base)
        if checkpoint is None:
            first_id = min(ev.id for ev in effective_traits_for(current, base).values())
            errors.append(
                f"{first_id}: trait rulings on {base!r} have no effective capability "
                f"checkpoint"
            )
            continue
        entry = upstream_traits.get(base)
        removed = set(_reference_analysis(entry).removed) if entry else set()
        active = {
            slug: ev
            for slug, ev in effective_traits_for(current, base).items()
            if slug not in removed
        }
        if not active:
            continue
        expected_kind, needs_target = _checkpoint_expectation(
            [ev.kind for ev in active.values()]
        )
        if checkpoint.kind != expected_kind:
            errors.append(
                f"{checkpoint.id}: checkpoint kind {checkpoint.kind!r} disagrees with "
                f"its traits (expected {expected_kind!r})"
            )
        if needs_target:
            targets = {ev.skill for ev in active.values() if ev.kind == "adopt"}
            if checkpoint.skill not in targets:
                errors.append(
                    f"{checkpoint.id}: checkpoint target {checkpoint.skill!r} is not one "
                    f"of its trait targets {sorted(t for t in targets if t)!r}"
                )

    # (B) Completeness against the ACCEPTED analysis (3.7) — every effective
    # trait-level checkpoint (see `_is_trait_level`), whatever its kind, and
    # every entry with an accepted analysis, checkpoint or not, needs its
    # entry, an effective checkpoint at the accepted analysis's sha and
    # tree_hash, a ruling at that sha for every trait it adds or changes
    # (every trait, for a first analysis) and a ruling at it or carried to it
    # (3.8) for every other listed trait. A grandfathered pre-trait checkpoint
    # (no accepted analysis yet) awaits a trait ruling (`gap` lists it); a
    # whole-skill defer/reject/out-of-scope needs nothing (3.6). A proposed
    # analysis changes nothing until promotion.
    for subject, upstream_entry in upstream_traits.items():
        if upstream_entry.accepted is not None and subject not in current:
            errors.append(
                f"{subject!r}: accepted analysis {upstream_entry.accepted} has no "
                f"effective checkpoint"
            )
    for subject, event in current.items():
        if subject.startswith("ours:") or _is_trait_subject(subject):
            continue
        if event.source is None or not event.source.logical_id.startswith("skill:"):
            continue
        entry = upstream_traits.get(subject)
        trait_rulings = effective_traits_for(current, subject)
        if not _is_trait_level(
            event, current, trait_rounds, upstream_traits, cfg.pre_trait_rounds
        ):
            continue  # checkpoint-only, or awaiting a trait ruling
        if entry is None:
            if not trait_rulings:
                errors.append(
                    f"{event.id}: {event.kind} checkpoint {subject!r} has no traits "
                    f"entry: a whole skill is never adopted without its traits"
                )
            else:
                errors.append(
                    f"{event.id}: trait-level checkpoint {subject!r} has no traits entry"
                )
            continue
        if entry.accepted is None:
            errors.append(
                f"{event.id}: trait-level checkpoint {subject!r} has no accepted "
                f"analysis (promote the proposed one)"
            )
            continue
        sha = entry.accepted
        analysis = entry.analyses[sha]
        if not trait_rulings:
            errors.append(
                f"{event.id}: {subject!r} has an accepted analysis: decide it per "
                f"trait (a whole-skill checkpoint needs trait rulings)"
            )
        if not event.source.sha:
            errors.append(f"{event.id}: trait-level checkpoint {subject!r} has no sha")
        elif not _same_sha(sha, event.source.sha):
            errors.append(
                f"{event.id}: accepted analysis sha {sha} disagrees with the checkpoint"
            )
        if not event.source.tree_hash:
            errors.append(
                f"{event.id}: trait-level checkpoint {subject!r} has no tree_hash"
            )
        elif analysis.tree_hash != event.source.tree_hash:
            errors.append(
                f"{event.id}: analysis tree_hash disagrees with the checkpoint"
            )
        first = not any(
            _same_sha(key, ev.source.sha)
            for ev in events
            if ev.source is not None
            and _trait_base(ev.subject) == subject
            and _is_trait_subject(ev.subject)
            for key in entry.analyses
            if key not in {sha, entry.proposed}
        )
        touched = (
            set(analysis.traits)
            if first
            else set(analysis.added) | set(analysis.changed)
        )
        for tid in analysis.traits:
            ruling = trait_rulings.get(tid)
            if ruling is None:
                errors.append(
                    f"{event.id}: trait {tid!r} in {subject!r} has no effective ruling"
                )
                continue
            at = ruling.source.sha if ruling.source else None
            if _same_sha(at, sha):
                continue
            if tid in touched:
                errors.append(
                    f"{event.id}: trait {tid!r} in {subject!r} has no effective "
                    f"ruling at {sha} (its ruling {ruling.id} is at {at})"
                )
            elif not is_carried(entry, tid, at, sha):
                errors.append(
                    f"{event.id}: trait {tid!r} in {subject!r}: ruling {ruling.id} "
                    f"at {at} does not carry to {sha}"
                )

    # Retirement — a subject introduced (its first event dated) on or after a
    # trait's retirement may not use it, in any of its events; a subject whose
    # first event predates retirement continues (§1, review r1 #9, r2 #2).
    first_event: dict[str, Event] = {}
    for event in events:
        first_event.setdefault(event.subject, event)
    for event in events:
        slug = _trait_slug(event.subject)
        d = definitions.get(slug) if slug else None
        if not (d and d.retired):
            continue
        introduced = first_event[event.subject].date
        if date_cls.fromisoformat(introduced) >= date_cls.fromisoformat(d.retired.date):
            errors.append(
                f"{event.id}: new subject {event.subject!r} (introduced "
                f"{introduced}) uses trait {slug!r}, retired {d.retired.date}"
            )

    # Effective trait rulings: an adopt targets a skill or `doc:`; a modified
    # adoption resolves its `distinct_from`; a fulfilled pending adopt errors
    # unless it pends a rewording (3.4a). Membership is by sha, for every
    # trait event (`checks.decisions`, 3.9).
    doc_traits = doc_holders(traits, playbooks)
    for subject, event in current.items():
        if not _is_trait_subject(subject):
            continue
        tid = _trait_slug(subject) or ""
        if (
            event.kind == "adopt"
            and event.skill
            and ":" in event.skill
            and not event.skill.startswith("doc:")
        ):
            errors.append(
                f"{event.id}: trait adopt targets {event.skill!r}; a trait lands in "
                f"a skill or a `doc:` file"
            )
        if event.kind == "adopt" and event.into and event.into != tid:
            into_def = definitions.get(event.into)
            if into_def is None or tid not in into_def.distinct_from:
                errors.append(
                    f"{event.id}: modified adoption into {event.into!r} must name "
                    f"{tid!r} in its distinct_from"
                )
        if event.kind == "adopt" and event.pending and event.skill:
            # A skill merged into a playbook resolves to its `doc:` holder.
            survivor = resolve_skill(event.skill, forward)
            listed: list[str] | None
            if ":" not in survivor:
                oentry = ours_traits.get(survivor)
                listed = oentry.traits if oentry else None
            else:
                listed = doc_traits.get(survivor)
            target_tid = event.into or tid
            if listed and target_tid in listed and event.rewording is None:
                errors.append(
                    f"{event.id}: pending adopt of {subject!r} but {survivor!r} "
                    f"already lists {target_tid!r} (fulfilled: record the "
                    f"completing adopt)"
                )

    # (C) Every adoption we still provide (last delivered adopt, not withdrawn)
    # must be listed by an active target skill in traits/ours.yaml — independently of
    # the trait's current upstream ruling (review #5, #6), per resolved target.
    # The resolved destination, so a skill merged into a playbook is checked
    # against that playbook's frontmatter (plan 40 §5a 3).
    for (subject, target), adopt in retained_adoptions(events, forward).items():
        if target and target.startswith("doc:"):
            # A `doc:` holder lists it too (Acceptance 4); a missing inventory
            # is an error, never a skip. A playbook may withdraw it (§4b).
            if (subject, target) in withdrawn:
                continue
            tid = adopt.into or _trait_slug(subject) or ""
            doc = doc_traits.get(target)
            if doc is None:
                errors.append(
                    f"{adopt.id}: {target!r} has no traits/ours.yaml entry or "
                    f"playbook; it keeps adopted trait {tid!r}"
                )
            elif not _trait_satisfied(tid, set(doc), definitions):
                errors.append(f"{adopt.id}: trait {tid!r} is not listed by {target!r}")
            continue
        if ":" in target:
            continue
        survivor = target
        if (subject, survivor) in withdrawn or survivor in retired:
            continue
        tid = adopt.into or _trait_slug(subject) or ""
        oentry = ours_traits.get(survivor)
        if oentry is None:
            errors.append(f"{adopt.id}: target skill {survivor!r} has no traits entry")
            continue
        if not _trait_satisfied(tid, set(oentry.traits), definitions):
            errors.append(
                f"{adopt.id}: trait {tid!r} is not listed by skill {survivor!r}"
            )
        want_hash = tree_hashes.get(survivor)
        if want_hash is not None and oentry.tree_hash != want_hash:
            errors.append(f"{adopt.id}: target skill {survivor!r} tree_hash is stale")
    return errors
