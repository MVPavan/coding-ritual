"""Rounds, effective rulings, lifecycle, adoptions and withdrawals."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from curation.registry.config import RegistryConfig
from curation.registry.loaders import (
    _round_files,
    load_ledger,
    load_traits,
    read_manifest,
)
from curation.registry.models import (
    Analysis,
    Event,
    RoundHeader,
    UpstreamTraitEntry,
)


def superseded_ids(events: list[Event]) -> set[str]:
    return {target for event in events for target in event.supersedes}


def live_events(events: list[Event]) -> list[Event]:
    """Events still operative — those not superseded by a later event, in ledger
    order. Every lifecycle, merge, withdrawal and coverage consumer reads this
    single list, so a correction (supersede a bad event with a good one) takes
    effect everywhere at once instead of each check re-deciding supersession
    (review #8, N2/N3). History and provenance consumers keep raw events."""
    dead = superseded_ids(events)
    return [event for event in events if event.id not in dead]


def effective_by_subject(events: list[Event]) -> dict[str, Event]:
    """The latest event per subject, in ledger order. Callers pass `live_events`,
    so superseded events are already excluded (review #8)."""
    current: dict[str, Event] = {}
    for event in events:
        current[event.subject] = event
    return current


def round_header_by_id(headers: list[RoundHeader]) -> dict[str, RoundHeader]:
    return {h.round_id: h for h in headers}


def _is_trait_subject(subject: str) -> bool:
    """A trait event's subject carries a trailing ``#<trait_id>``."""
    return "#" in subject


def _trait_base(subject: str) -> str:
    """The capability subject (<repo>:<logical_id>) of a trait subject."""
    return subject.split("#", 1)[0]


def _trait_slug(subject: str) -> str | None:
    return subject.split("#", 1)[1] if "#" in subject else None


def effective_traits_for(current: dict[str, Event], base: str) -> dict[str, Event]:
    """Effective trait events whose subject is ``<base>#<trait_id>``, keyed by
    trait id."""
    out: dict[str, Event] = {}
    for subject, event in current.items():
        if _is_trait_subject(subject) and _trait_base(subject) == base:
            slug = _trait_slug(subject)
            if slug is not None:
                out[slug] = event
    return out


def _same_sha(a: str | None, b: str | None) -> bool:
    """Two commit shas name the same commit when one is a prefix of the other,
    so a short sha matches its full form."""
    if not a or not b:
        return False
    a, b = a.lower(), b.lower()
    return a.startswith(b) or b.startswith(a)


def analysis_at(
    entry: UpstreamTraitEntry, sha: str | None
) -> tuple[str, Analysis] | None:
    """The entry's analysis at a commit sha (prefixes match), with its key."""
    for key, analysis in entry.analyses.items():
        if _same_sha(key, sha):
            return key, analysis
    return None


def is_carried(
    entry: UpstreamTraitEntry, trait: str, from_sha: str | None, to_sha: str | None
) -> bool:
    """3.8: a ruling recorded at analysis `from_sha` carries to the later
    analysis `to_sha` when the trait is listed in both and the later one
    neither adds nor changes it. Never true for one analysis with itself."""
    earlier, later = analysis_at(entry, from_sha), analysis_at(entry, to_sha)
    if earlier is None or later is None or earlier[0] == later[0]:
        return False
    after = later[1]
    return (
        trait in earlier[1].traits
        and trait in after.traits
        and trait not in after.added
        and trait not in after.changed
    )


def is_pending_adopt(event: Event) -> bool:
    return event.kind == "adopt" and event.pending is not None and "#" in event.subject


def lifecycle_of(
    kind: str | None,
    subject: str,
    supersedes: list[str],
    skill: str | None,
    into: str | None,
    pending: str | None,
    prior: Event | None,
    forward: dict[str, str],
) -> Event | None:
    """3.4: the pending adopt a request completes or cancels, or None when it
    is a new decision. It must explicitly supersede the subject's *effective*
    event `prior`, a pending adopt; a completion (a delivered adopt) keeps
    that event's resolved target and adopted trait, a cancellation is a reject
    or defer. `record` and `check` both decide through here."""
    if prior is None or not is_pending_adopt(prior) or prior.subject != subject:
        return None
    if prior.id not in supersedes:
        return None
    if kind in {"reject", "defer"}:
        return prior
    if kind != "adopt" or pending is not None or skill is None:
        return None
    assert prior.skill is not None
    tid = _trait_slug(subject)
    same_target = resolve_skill(skill, forward) == resolve_skill(prior.skill, forward)
    return prior if same_target and (into or tid) == (prior.into or tid) else None


def lifecycle_pending(
    event: Event, prior: Event | None, forward: dict[str, str]
) -> Event | None:
    """`lifecycle_of` for a recorded event."""
    return lifecycle_of(
        event.kind,
        event.subject,
        event.supersedes,
        event.skill,
        event.into,
        event.pending,
        prior,
        forward,
    )


def _is_grandfathered(
    event: Event,
    current: dict[str, Event],
    upstream_traits: dict[str, UpstreamTraitEntry],
    pre_trait_rounds: frozenset[str],
) -> bool:
    """A checkpoint sealed before traits existed, whose subject now has an
    upstream entry but no trait ruling: awaiting a trait ruling (§5). It ends
    once the entry has an accepted analysis (3.7)."""
    entry = upstream_traits.get(event.subject)
    return (
        _round_of(event) in pre_trait_rounds
        and entry is not None
        and entry.accepted is None
        and not effective_traits_for(current, event.subject)
    )


# Kinds a checkpoint with neither an entry nor trait rulings may take in a
# trait-level round: it stays a whole-skill ruling (§5b).
WHOLE_SKILL_KINDS = frozenset({"defer", "reject", "out-of-scope"})


def _is_trait_level(
    event: Event,
    current: dict[str, Event],
    trait_rounds: set[str],
    upstream_traits: dict[str, UpstreamTraitEntry],
    pre_trait_rounds: frozenset[str],
) -> bool:
    """A capability checkpoint not grandfathered is trait-level when its subject
    has an accepted analysis or any effective trait ruling, or it is not a
    whole-skill defer, reject or out-of-scope and its round is trait-level or
    outside `pre_trait_rounds`, whatever the round's flag (3.6). A
    proposed-only entry changes nothing (stages-design §Entries)."""
    if _is_grandfathered(event, current, upstream_traits, pre_trait_rounds):
        return False
    entry = upstream_traits.get(event.subject)
    if (entry is not None and entry.accepted is not None) or effective_traits_for(
        current, event.subject
    ):
        return True
    round_id = _round_of(event)
    return (
        round_id in trait_rounds or round_id not in pre_trait_rounds
    ) and event.kind not in WHOLE_SKILL_KINDS


def build_lifecycle(events: list[Event]) -> tuple[dict[str, str], set[str]]:
    """Our skill lifecycle, read in ledger order (§3, §5).

    Returns ``(forward, retired)``: a one-step ``old -> new`` map across
    ``rename``/``merge`` and the set of retired skill names. A skill is keyed by
    its plain name, a renamed playbook by its full ``doc:<path>`` (README §4b).
    Trait IDs are global, so a merge needs no slug map (§5). Callers pass
    `live_events`, so superseded lifecycle events are already excluded (review #8).
    """
    forward: dict[str, str] = {}
    retired: set[str] = set()
    for event in events:
        if event.kind in {"rename", "merge"} and event.subject.startswith("ours:"):
            old = event.subject[len("ours:") :]
            if event.skill:
                forward[old] = event.skill
        elif event.kind == "rename" and event.subject.startswith("doc:"):
            if event.skill:
                forward[event.subject] = event.skill
        elif event.kind == "retire" and event.skill:
            retired.add(event.skill)
    return forward, retired


def resolve_skill(name: str, forward: dict[str, str]) -> str:
    """Follow rename/merge until the current survivor."""
    seen: set[str] = set()
    while name in forward and name not in seen:
        seen.add(name)
        name = forward[name]
    return name


def tracks_adoption(target: str) -> bool:
    """Whether an adoption into `target` is an obligation the target keeps: a
    skill or a `doc:` holder, never a `kind:name` capability. Only a playbook
    has an `update` to withdraw one with (§4b)."""
    return ":" not in target or target.startswith("doc:")


def withdrawn_destinations(
    events: list[Event], forward: dict[str, str]
) -> dict[tuple[str, str], str]:
    """(trait subject, resolved destination skill) pairs currently withdrawn,
    mapped to the withdrawal date. Keyed per destination so withdrawing a trait
    from one skill never touches the same trait adopted into another (review #7).
    Ordered by ledger position: a *delivered* (non-pending) `adopt` into that
    same destination after the withdrawing `update` makes it live again; a
    pending adopt is intent, not delivery, so it never clears a withdrawal (§5).

    `events` is the RAW list, like `retained_adoptions`: a delivered adopt keeps
    reviving the obligation even when later superseded, while a superseded
    withdrawing `update` never operates (review r1 #1)."""
    dead = superseded_ids(events)
    withdrawn: dict[tuple[str, str], str] = {}
    for event in events:
        if (
            event.kind == "update"
            and event.withdraws
            and event.skill
            and event.id not in dead
        ):
            dest = resolve_skill(event.skill, forward)
            for subject in event.withdraws:
                withdrawn[(subject, dest)] = event.date
        elif (
            event.kind == "adopt"
            and not event.pending
            and _is_trait_subject(event.subject)
            and event.skill
            and tracks_adoption(event.skill)
        ):
            withdrawn.pop((event.subject, resolve_skill(event.skill, forward)), None)
    return withdrawn


def retained_adoptions(
    events: list[Event], forward: dict[str, str]
) -> dict[tuple[str, str], Event]:
    """The last delivered `adopt` event per (trait subject, resolved destination
    skill), in ledger order — the adoption we still provide even after a later
    upstream revision is declined (§5). Keyed per destination so adopting one
    trait into A and then into B keeps A's coverage obligation until A withdraws
    it, rather than B silently replacing A (review #6, N1).

    A `doc:` target is kept verbatim (its holder lists the trait too,
    Acceptance 4). Reads only non-pending `adopt` events: a pending adopt is intent, not
    delivery, so it never enters the fold and never replaces a delivered
    obligation (§5, round-2 #1). Computed from RAW events, including a superseded
    `adopt`: per §5 only an ours-side `update` with `withdraws` removes an
    adoption obligation; an upstream `reject`/`defer` that supersedes the adopt
    never does (review r3). `forward` and the withdrawal state come from live
    events, so the coverage check and the sources block — which both read this
    function — can never disagree."""
    out: dict[tuple[str, str], Event] = {}
    for event in events:
        if (
            event.kind == "adopt"
            and not event.pending
            and _is_trait_subject(event.subject)
            and event.skill
            and tracks_adoption(event.skill)
        ):
            dest = resolve_skill(event.skill, forward)
            out[(event.subject, dest)] = event
    return out


def open_rounds(cfg: RegistryConfig) -> list[Path]:
    """Every unsealed round file (not yet in the manifest)."""
    recorded = _manifest_rounds(cfg)
    return [p for p in _round_files(cfg) if p.name not in recorded]


def open_round(cfg: RegistryConfig) -> Path | None:
    """The single unsealed round file; fails if more than one is open."""
    unsealed = open_rounds(cfg)
    if len(unsealed) > 1:
        names = ", ".join(p.name for p in unsealed)
        raise SystemExit(
            f"more than one open round ({names}) — seal one before recording"
        )
    return unsealed[0] if unsealed else None


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


_MANIFEST_KEYS = ("rounds", "reports", "analyses")


def _manifest(cfg: RegistryConfig) -> dict[str, Any]:
    data = read_manifest(cfg)
    manifest: dict[str, Any] = {key: dict(data.get(key, {})) for key in _MANIFEST_KEYS}
    manifest["round_order"] = data.get("round_order", [])
    return manifest


def _manifest_rounds(cfg: RegistryConfig) -> dict[str, str]:
    rounds: dict[str, str] = _manifest(cfg)["rounds"]
    return rounds


def round_order_errors(cfg: RegistryConfig) -> list[str]:
    """`round_order` names exactly the sealed rounds, each once."""
    order = read_manifest(cfg).get("round_order", [])
    if not isinstance(order, list):
        return ["MANIFEST.json: round_order must be a list"]
    recorded = _manifest_rounds(cfg)
    names = [str(name) for name in order]
    errors = [
        f"MANIFEST.json: round_order: {name}: listed more than once"
        for name in sorted({n for n in names if names.count(n) > 1})
    ]
    errors += [
        f"MANIFEST.json: round_order: {name}: listed but not sealed"
        for name in sorted(set(names) - set(recorded))
    ]
    errors += [
        f"MANIFEST.json: round_order: {name}: not listed"
        for name in sorted(set(recorded) - set(names))
    ]
    return errors


def require_round_order(cfg: RegistryConfig) -> None:
    """Refuse a write that depends on chronology while the order is invalid: with
    a bad list the events load in an order `check` will not accept."""
    errors = round_order_errors(cfg)
    if errors:
        raise SystemExit(
            "; ".join(errors) + " — repair round_order in recording order first"
        )


def manifest_reports(cfg: RegistryConfig) -> dict[str, str]:
    """Sealed reports: repo-relative path → sha256 of the file."""
    reports: dict[str, str] = _manifest(cfg)["reports"]
    return reports


def manifest_analyses(cfg: RegistryConfig) -> dict[str, str]:
    """Analyses cited by a sealed round: `<entry key>@<sha>` → content hash."""
    analyses: dict[str, str] = _manifest(cfg)["analyses"]
    return analyses


def analysis_digest(analysis: Analysis) -> str:
    """sha256 of an analysis's canonical JSON form."""
    text = json.dumps(analysis.model_dump(), sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _write_manifest(cfg: RegistryConfig, manifest: dict[str, Any]) -> None:
    """The manifest keeps sealed rounds under `rounds` and their recording order
    under `round_order`; once any is recorded, sealed reports under `reports` and
    cited analyses under `analyses`."""
    data: dict[str, Any] = {
        "_comment": "sha256 of every sealed round file, and in round_order the "
        "sealed rounds in recording order. registry.py check fails if a sealed "
        "file is modified or deleted. Never edit by hand.",
        "rounds": dict(sorted(manifest["rounds"].items())),
        "round_order": manifest["round_order"],
    }
    if manifest["reports"] or manifest["analyses"]:
        data["_comment"] = (
            "sha256 of every sealed round file and report, and of every analysis "
            "a sealed round cites; in round_order, the sealed rounds in recording "
            "order. registry.py check fails if one is modified or deleted. Never "
            "edit by hand."
        )
    for key in _MANIFEST_KEYS[1:]:
        if manifest[key]:
            data[key] = dict(sorted(manifest[key].items()))
    cfg.manifest_path.parent.mkdir(parents=True, exist_ok=True)
    cfg.manifest_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def seal(cfg: RegistryConfig, round_id: str) -> None:
    """Record the sha256 of a round file and append it to `round_order`. A sealed
    round is never re-digested; a sealed round that has since changed is refused
    rather than overwritten, and so is a round citing an analysis whose recorded
    digest it would replace."""
    path = cfg.ledger_dir / f"{round_id}.jsonl"
    if not path.is_file():
        raise SystemExit(f"no round file to seal: {path}")
    require_round_order(cfg)
    manifest = _manifest(cfg)
    recorded = manifest["rounds"]
    current = _sha256(path)
    if path.name in recorded:
        if recorded[path.name] != current:
            raise SystemExit(
                f"{path.name}: already sealed and has CHANGED — refusing to re-seal"
            )
        return  # already sealed with the same digest; nothing to do
    cited = _cited_analyses(cfg, round_id)
    changed = sorted(
        key
        for key, digest in cited.items()
        if manifest["analyses"].get(key, digest) != digest
    )
    if changed:
        raise SystemExit(
            f"{path.name}: cites analysis {', '.join(changed)}, which has CHANGED "
            f"since a sealed round cited it — refusing to seal"
        )
    recorded[path.name] = current
    manifest["round_order"].append(path.name)
    manifest["analyses"].update(cited)
    _write_manifest(cfg, manifest)


def _cited_analyses(cfg: RegistryConfig, round_id: str) -> dict[str, str]:
    """`<entry key>@<sha>` → digest of each analysis the round's trait events
    cite (stages-design §Entries: immutable once cited)."""
    _, events, _ = load_ledger(cfg)
    traits, _ = load_traits(cfg)
    out: dict[str, str] = {}
    for event in events:
        if _round_of(event) != round_id or not _is_trait_subject(event.subject):
            continue
        entry = traits.get(_trait_base(event.subject))
        if not isinstance(entry, UpstreamTraitEntry) or event.source is None:
            continue
        found = analysis_at(entry, event.source.sha)
        if found is not None:
            out[f"{_trait_base(event.subject)}@{found[0]}"] = analysis_digest(found[1])
    return out


def seal_report_digest(cfg: RegistryConfig, key: str, digest: str) -> None:
    """Record a passed report's content hash (the caller validated it)."""
    manifest = _manifest(cfg)
    manifest["reports"][key] = digest
    _write_manifest(cfg, manifest)


def _adopt_target(ruling: Event, forward: dict[str, str]) -> str:
    """The rendered adoption target of a trait `adopt` ruling: a `kind:` target
    verbatim, a `doc:` target as the path it was renamed to, otherwise the
    survivor skill and the adopted trait id."""
    assert ruling.skill is not None
    if ruling.skill.startswith("doc:"):  # a playbook may be renamed; no trait id
        return resolve_skill(ruling.skill, forward)
    if ":" in ruling.skill:  # kind: target, no trait id, no lifecycle
        return ruling.skill
    survivor = resolve_skill(ruling.skill, forward)
    tid = ruling.into or _trait_slug(ruling.subject)
    return f"{survivor}#{tid}" if tid else survivor


def _round_of(event: Event) -> str:
    return event.id.rsplit(":", 1)[0]


def _next_event_id(path: Path, round_id: str) -> str:
    """The next `<round_id>:<n>` for the open round, from the ids already present."""
    highest = 0
    prefix = f"{round_id}:"
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        rec = json.loads(line)
        rid = str(rec.get("id", ""))
        if rid.startswith(prefix):
            suffix = rid[len(prefix) :]
            if suffix.isdigit():
                highest = max(highest, int(suffix))
    return f"{round_id}:{highest + 1:03d}"


def _event_dict(event: Event) -> dict[str, Any]:
    """The event as written: unset fields omitted, but a trait event's
    `policy_basis` kept even when null (recorded under no policy)."""
    data = event.model_dump(exclude_none=True)
    if "policy_basis" in event.model_fields_set and event.policy_basis is None:
        data["policy_basis"] = None
    return data


def _dump(data: dict[str, Any]) -> str:
    return json.dumps(data, ensure_ascii=False)


def _carried_replacements(current: dict[str, Event]) -> dict[str, Event]:
    """Earlier trait subject -> the effective event that carries it (§5): used to
    render ``upstream replaced it with B`` on an adoption of A."""
    out: dict[str, Event] = {}
    for event in current.values():
        for carried in event.carried_from:
            out[carried] = event
    return out
