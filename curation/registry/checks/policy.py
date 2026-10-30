"""`trait-policy.yaml` checks (stages-design §Trait policy, check item 10):
keys, retirement reconciliation, `ledger`, the ours-side and guide warnings.
Each event's own `policy_basis` is checked in `checks.decisions`."""

from __future__ import annotations

from curation.registry.models import (
    OursTraitEntry,
    PolicyEntry,
    SkillEntry,
    TraitDefinition,
)
from curation.registry.policy import guide_changes, live_policy


def policy_problems(
    policies: dict[str, PolicyEntry],
    definitions: dict[str, TraitDefinition],
    event_ids: set[str],
    ours: dict[str, OursTraitEntry],
    skills: dict[str, SkillEntry],
    rules: dict[str, tuple[str, str, bool]],
) -> tuple[list[str], list[str]]:
    """(errors, warnings) of the policy file against the vocabulary, the
    ledger, our skills and the GUIDE."""
    errors: list[str] = []
    for tid, entry in policies.items():
        where = f"trait-policy.yaml: {tid}"
        d = definitions.get(tid)
        if d is None:
            errors.append(f"{where}: trait is undefined")
        elif d.retired is None:
            if entry.reconciled is not None:
                errors.append(f"{where}: `reconciled` is only for a retired trait")
        else:
            want = set(d.retired.replaced_by)
            got = set(entry.reconciled or {})
            if got != want:
                errors.append(
                    f"{where}: retired; `reconciled` must cover exactly its "
                    f"replaced_by {sorted(want)} (has {sorted(got)})"
                )
            for repl, how in sorted((entry.reconciled or {}).items()):
                if how != "carried":
                    continue
                other = policies.get(repl)
                if other is None or tid not in other.from_:
                    errors.append(
                        f"{where}: carried to {repl!r}, whose entry must list "
                        f"{tid!r} in `from`"
                    )
        if entry.ledger not in event_ids:
            errors.append(f"{where}: ledger {entry.ledger!r} names no event")
        for old in entry.from_:
            od = definitions.get(old)
            if od is None or od.retired is None:
                errors.append(f"{where}: from {old!r} is not a retired trait")
    live = live_policy(policies, definitions)
    warnings: list[str] = []
    for name, oentry in sorted(ours.items()):
        skill = skills.get(name)
        if skill is None or skill.status != "active":
            continue
        for tid in oentry.traits:
            if tid in live and live[tid].stance == "avoid":
                warnings.append(
                    f"skill {name!r} lists {tid!r}, whose policy is `avoid` "
                    f"(clean it out with an ours-side update)"
                )
    for tid, notes in guide_changes(live, rules).items():
        warnings.append(f"trait-policy.yaml: {tid}: guide changed ({'; '.join(notes)})")
    return errors, warnings
