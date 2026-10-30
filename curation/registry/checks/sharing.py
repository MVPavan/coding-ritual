"""`trait-sharing.yaml` against the computed shared set (stages-design §Shared
traits, check item 6)."""

from __future__ import annotations

from curation.registry.models import SharingEntry


def sharing_problems(
    shared: dict[str, list[str]], sharing: dict[str, SharingEntry]
) -> tuple[list[str], list[str]]:
    """(errors, warnings): a shared trait with no entry warns; an entry whose
    `skills` differ from the computed holders, or for an unshared trait,
    errors."""
    errors: list[str] = []
    warnings: list[str] = []
    for tid, holders in shared.items():
        entry = sharing.get(tid)
        if entry is None:
            warnings.append(
                f"shared trait {tid!r} ({', '.join(holders)}) has no "
                f"trait-sharing.yaml entry"
            )
        elif sorted(entry.skills) != holders:
            errors.append(
                f"trait-sharing.yaml: {tid}: skills {sorted(entry.skills)} are not "
                f"its holders {holders}"
            )
    for tid in sorted(set(sharing) - set(shared)):
        errors.append(f"trait-sharing.yaml: {tid}: not a shared trait")
    return errors, warnings
