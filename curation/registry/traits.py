"""Trait holders and facts drawn from the traits/ folder."""

from __future__ import annotations

import hashlib
from collections.abc import Mapping
from typing import Any, Literal

from curation.registry.models import (
    Holding,
    OursTraitEntry,
    SkillEntry,
    StrictModel,
    TraitDefinition,
    UpstreamTraitEntry,
)
from curation.registry.steps import Playbook

AGENTS_DOC = "doc:AGENTS.md"


def _ours_traits(
    traits: dict[str, OursTraitEntry | UpstreamTraitEntry],
) -> dict[str, OursTraitEntry]:
    """Our skills' entries, keyed by bare skill name."""
    return {
        k[len("ours:") :]: v
        for k, v in traits.items()
        if isinstance(v, OursTraitEntry) and k.startswith("ours:")
    }


def _doc_traits(
    traits: dict[str, OursTraitEntry | UpstreamTraitEntry],
) -> dict[str, OursTraitEntry]:
    """`doc:<path>` entries, keyed by the full `doc:` key (stages-design 1.5)."""
    return {
        k: v
        for k, v in traits.items()
        if isinstance(v, OursTraitEntry) and k.startswith("doc:")
    }


def doc_holders(
    traits: dict[str, OursTraitEntry | UpstreamTraitEntry],
    playbooks: Mapping[str, Playbook],
) -> dict[str, list[str]]:
    """Every `doc:` holder's trait list by its full key: the `doc:` entries of
    traits/ours.yaml, and each playbook, whose list is its frontmatter (T1,
    T3; a ledger adopt into a playbook targets the same key)."""
    out = {k: list(e.traits) for k, e in _doc_traits(traits).items()}
    out.update({book.holder: book.unit_traits() for book in playbooks.values()})
    return out


def _doc_tree_hash(name: str, raw: bytes) -> str:
    """sha256 over one file framed like a skill folder's tree hash, with the
    repo-relative path as the name (stages-design 1.4)."""
    digest = hashlib.sha256()
    digest.update(name.encode("utf-8"))
    digest.update(b"\0")
    digest.update(str(len(raw)).encode("ascii"))
    digest.update(b"\0")
    digest.update(raw)
    return digest.hexdigest()


def _upstream_traits(
    traits: dict[str, OursTraitEntry | UpstreamTraitEntry],
) -> dict[str, UpstreamTraitEntry]:
    return {k: v for k, v in traits.items() if isinstance(v, UpstreamTraitEntry)}


def _our_tree_hashes(ours: Any) -> dict[str, str]:
    """Current tree hash of each of our skills, keyed by bare skill name."""
    out: dict[str, str] = {}
    for cap in ours.capabilities:
        if cap.kind.value == "skill":
            out[cap.name] = cap.tree_hash
    return out


def _trait_satisfied(
    trait_id: str, listed: set[str], definitions: dict[str, TraitDefinition]
) -> bool:
    """A holder lists the trait, or — when it is retired — every `replaced_by`
    trait (traits-design §1)."""
    if trait_id in listed:
        return True
    d = definitions.get(trait_id)
    if d and d.retired and d.retired.replaced_by:
        return all(r in listed for r in d.retired.replaced_by)
    return False


# --- facts and pairing (stages-design 2.1-2.2) -----------------------------------


class Fact(StrictModel):
    """The computed part of a report row for one upstream trait."""

    fact: Literal["present", "variant", "absent"]
    provider: str | None
    candidates: list[str]
    also_in: dict[str, Holding]


def holders(
    traits: dict[str, OursTraitEntry | UpstreamTraitEntry],
    playbooks: Mapping[str, Playbook],
) -> dict[str, set[str]]:
    """Every holder's trait list: our skills by bare name, `doc:` holders
    (playbooks included) by their full key."""
    out = {name: set(e.traits) for name, e in _ours_traits(traits).items()}
    out.update({key: set(ids) for key, ids in doc_holders(traits, playbooks).items()})
    return out


def variant_candidates(
    trait_id: str, listed: set[str], definitions: dict[str, TraitDefinition]
) -> list[str]:
    """The listed traits whose definition's `distinct_from` names `trait_id`."""
    return sorted(
        tid
        for tid in listed
        if tid in definitions and trait_id in definitions[tid].distinct_from
    )


def holding(
    trait_id: str, listed: set[str], definitions: dict[str, TraitDefinition]
) -> Holding | None:
    if _trait_satisfied(trait_id, listed, definitions):
        return "present"
    if variant_candidates(trait_id, listed, definitions):
        return "variant"
    return None


def compute_fact(
    trait_id: str,
    compared: str | None,
    held: dict[str, set[str]],
    definitions: dict[str, TraitDefinition],
) -> Fact:
    """2.2: only the compared skill (`None` for `none`) or `doc:AGENTS.md`
    makes a trait present, the compared skill winning; only the compared skill
    makes it a variant. Every other holder goes to `also_in`, never coverage."""
    ours = held.get(compared, set()) if compared is not None else set()
    candidates = variant_candidates(trait_id, ours, definitions)
    fact: Literal["present", "variant", "absent"]
    provider: str | None
    if compared is not None and _trait_satisfied(trait_id, ours, definitions):
        fact, provider = "present", compared
    elif _trait_satisfied(trait_id, held.get(AGENTS_DOC, set()), definitions):
        fact, provider = "present", AGENTS_DOC
    elif candidates:
        fact, provider = "variant", compared
    else:
        fact, provider = "absent", None
    also_in: dict[str, Holding] = {}
    for name in sorted(held):
        if name == provider:
            continue
        found = holding(trait_id, held[name], definitions)
        if found is not None:
            also_in[name] = found
    return Fact(fact=fact, provider=provider, candidates=candidates, also_in=also_in)


def compute_pairing(
    upstream: list[str],
    domain: str,
    substage: str,
    held: dict[str, set[str]],
    definitions: dict[str, TraitDefinition],
    skills: dict[str, SkillEntry],
) -> tuple[dict[str, int], list[str], str | None]:
    """2.1, the computed signals: `overlap` (holders with a nonzero count of the
    upstream traits present or as variant), `placement_match` (our active skills
    at the same domain · sub-stage) and `suggested` (the skill, never a `doc:`,
    with the most overlap, ties by placement match, then name; `None` when no
    skill overlaps or matches placement)."""
    overlap: dict[str, int] = {}
    for name in sorted(held):
        count = sum(
            1 for tid in upstream if holding(tid, held[name], definitions) is not None
        )
        if count:
            overlap[name] = count
    active = {n for n, e in skills.items() if e.status == "active"}
    placement = sorted(
        n
        for n in active
        if skills[n].domain == domain and skills[n].substage == substage
    )
    pool = {
        n
        for n in overlap
        if not n.startswith("doc:") and (n in active or n not in skills)
    } | set(placement)
    ranked = sorted(pool, key=lambda n: (-overlap.get(n, 0), n not in placement, n))
    return overlap, placement, ranked[0] if ranked else None


# --- sharing (stages-design §Shared traits) ----------------------------------------


def shared_traits(
    traits: dict[str, OursTraitEntry | UpstreamTraitEntry],
    skills: dict[str, SkillEntry],
    playbooks: Mapping[str, Playbook],
) -> dict[str, list[str]]:
    """Trait → its holders, for every trait listed by two or more of our
    active skills, `doc:AGENTS.md` and each playbook counted as holders (T1,
    T2: the same check in a skill and a playbook is the same trait)."""
    listed: dict[str, list[str]] = {}
    for name, entry in sorted(_ours_traits(traits).items()):
        if name in skills and skills[name].status == "active":
            for tid in entry.traits:
                listed.setdefault(tid, []).append(name)
    agents = _doc_traits(traits).get(AGENTS_DOC)
    for tid in agents.traits if agents else []:
        listed.setdefault(tid, []).append(AGENTS_DOC)
    for book in playbooks.values():
        for tid in book.unit_traits():
            listed.setdefault(tid, []).append(book.holder)
    return {
        tid: sorted(names) for tid, names in sorted(listed.items()) if len(names) > 1
    }
