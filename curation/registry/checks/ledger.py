"""Ledger checks: immutability, supersession, structure, carry-over, withdrawals."""

from __future__ import annotations

import json

from curation.registry.config import RegistryConfig
from curation.registry.ledger import (
    _is_trait_subject,
    _manifest_rounds,
    _round_of,
    _sha256,
    resolve_skill,
    superseded_ids,
    tracks_adoption,
)
from curation.registry.loaders import _round_files
from curation.registry.models import Event, RoundHeader


def check_immutable(cfg: RegistryConfig) -> list[str]:
    recorded = _manifest_rounds(cfg)
    present = {p.name: _sha256(p) for p in _round_files(cfg)}
    errors: list[str] = []
    for name, digest in recorded.items():
        if name not in present:
            errors.append(
                f"{name}: sealed round file has been DELETED — the ledger is append-only"
            )
        elif present[name] != digest:
            errors.append(
                f"{name}: sealed round file has been MODIFIED — the ledger is append-only"
            )
    return errors


def _check_supersession(events: list[Event], seen: set[str]) -> list[str]:
    """Targets exist, belong to the same subject, superseded at most once, and
    chains are acyclic within a subject."""
    errors: list[str] = []
    by_id = {e.id: e for e in events}
    superseded_by: dict[str, str] = {}
    for event in events:
        for target in event.supersedes:
            if target not in seen:
                errors.append(f"{event.id}: supersedes unknown event {target!r}")
                continue
            if target == event.id:
                errors.append(f"{event.id}: supersedes itself")
            tgt = by_id[target]
            if tgt.subject != event.subject:
                errors.append(
                    f"{event.id}: supersedes {target} across subjects "
                    f"({event.subject} vs {tgt.subject})"
                )
            if target in superseded_by:
                errors.append(
                    f"{target}: superseded twice ({superseded_by[target]} and {event.id})"
                )
            superseded_by[target] = event.id
    # Acyclicity over the full supersedes graph (every edge, not just the first).
    WHITE, GREY, BLACK = 0, 1, 2
    color: dict[str, int] = {}
    cyclic: set[str] = set()

    def visit(node: str, stack: list[str]) -> None:
        color[node] = GREY
        stack.append(node)
        for nxt in by_id.get(node).supersedes if node in by_id else []:  # type: ignore[union-attr]
            if nxt not in by_id:
                continue
            if color.get(nxt, WHITE) == GREY:
                cyclic.update(stack[stack.index(nxt) :] + [nxt])
            elif color.get(nxt, WHITE) == WHITE:
                visit(nxt, stack)
        stack.pop()
        color[node] = BLACK

    for node in by_id:
        if color.get(node, WHITE) == WHITE:
            visit(node, [])
    for node in sorted(cyclic):
        errors.append(f"{node}: supersession chain is cyclic")
    return errors


def _check_structure(cfg: RegistryConfig) -> list[str]:
    """Each round file: exactly one header on line 1, round_id == filename stem,
    every event id belongs to that round."""
    errors: list[str] = []
    for path in _round_files(cfg):
        stem = path.stem
        lines = path.read_text(encoding="utf-8").splitlines()
        if not lines:
            errors.append(f"{path.name}: empty round file")
            continue
        # Physical lines: the header must be line 1, with no blank lines anywhere.
        for lineno, line in enumerate(lines, 1):
            if not line.strip():
                errors.append(
                    f"{path.name}:{lineno}: blank line (one JSON record per line)"
                )
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            is_header = rec.get("type") == "round"
            if lineno == 1:
                if not is_header:
                    errors.append(
                        f"{path.name}: physical first line must be a round header"
                    )
                elif rec.get("round_id") != stem:
                    errors.append(
                        f"{path.name}: header round_id {rec.get('round_id')!r} != filename"
                    )
            elif is_header:
                errors.append(f"{path.name}:{lineno}: a second round header")
            elif not str(rec.get("id", "")).startswith(f"{stem}:"):
                errors.append(
                    f"{path.name}:{lineno}: event {rec.get('id')!r} does not belong to {stem}"
                )
    return errors


def _check_carried_from(events: list[Event]) -> list[str]:
    """Each carried_from must name an *earlier* trait subject — not itself, not a
    capability subject, and not one introduced only later (§5, review #18)."""
    errors: list[str] = []
    seen_before: set[str] = set()
    for event in events:
        for carried in event.carried_from:
            if carried == event.subject:
                errors.append(f"{event.id}: carried_from {carried!r} is itself")
            elif not _is_trait_subject(carried):
                errors.append(
                    f"{event.id}: carried_from {carried!r} is not a trait subject"
                )
            elif carried not in seen_before:
                errors.append(
                    f"{event.id}: carried_from {carried!r} is not an earlier trait subject"
                )
        seen_before.add(event.subject)
    return errors


def _check_withdraws(events: list[Event], forward: dict[str, str]) -> list[str]:
    """An ours-side `update` withdraws only traits adopted into this skill or
    playbook (§5). A superseded `update` has no effect (§5b), so it is skipped.
    Reads raw adoptions: one superseded by an upstream reject is still a live
    obligation and remains withdrawable (review r3)."""
    errors: list[str] = []
    dead = superseded_ids(events)
    for event in events:
        if event.kind != "update" or not event.withdraws or event.id in dead:
            continue
        skill = resolve_skill(event.skill or "", forward)
        for subject in event.withdraws:
            adopted_here = any(
                e.kind == "adopt"
                and e.subject == subject
                and e.skill
                and tracks_adoption(e.skill)
                and resolve_skill(e.skill, forward) == skill
                for e in events
            )
            if not adopted_here:
                errors.append(
                    f"{event.id}: withdraws {subject!r} but no adopt event targets "
                    f"{event.skill!r}"
                )
    return errors


def _check_adopt_merged_adaptation(
    headers: list[RoundHeader], events: list[Event]
) -> list[str]:
    """An `adopt-merged` capability event outside a trait-level round must carry
    `adaptation` (README §5, review #4); inside one it is optional."""
    trait_rounds = {h.round_id for h in headers if h.trait_level}
    errors: list[str] = []
    for event in events:
        if (
            event.kind == "adopt-merged"
            and not _is_trait_subject(event.subject)
            and event.adaptation is None
            and _round_of(event) not in trait_rounds
        ):
            errors.append(
                f"{event.id}: adopt-merged needs `adaptation` outside a trait-level round"
            )
    return errors
