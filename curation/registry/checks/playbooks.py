"""Playbook checks: step IDs, defined traits, resolvable calls and loads (St1,
B1, F1); each playbook's hash against its ledger event (README §4b)."""

from __future__ import annotations

import re

from curation.registry.checks.records import _target_exists
from curation.registry.checks.traits import doc_holder_kind
from curation.registry.config import RegistryConfig
from curation.registry.ledger import (
    build_lifecycle,
    effective_by_subject,
    live_events,
    resolve_skill,
)
from curation.registry.loaders import unit_file
from curation.registry.models import Event, TraitDefinition
from curation.registry.steps import (
    CALL_KINDS,
    Playbook,
    playbook_files,
    playbook_tree_hash,
)
from curation.registry.vocab import PLAYBOOK_KINDS

_NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")


def _undefined(
    where: str, ids: list[str], definitions: dict[str, TraitDefinition]
) -> list[str]:
    return [
        f"{where}: trait {tid!r} is undefined" for tid in ids if tid not in definitions
    ]


def _call_errors(
    cfg: RegistryConfig, where: str, to: str, playbooks: dict[str, Playbook]
) -> list[str]:
    kind, sep, name = to.partition(":")
    if not sep or kind not in CALL_KINDS or not name:
        kinds = ", ".join(f"{k}:<name>" for k in CALL_KINDS)
        return [f"{where}: call {to!r} is not {kinds}; a reference is a load"]
    if kind == "skill":
        if "/" in name or not unit_file(cfg, name).is_file():
            return [f"{where}: call {to!r}: no skill folder {name!r}"]
    elif name not in playbooks:
        return [f"{where}: call {to!r}: no playbook {name!r}"]
    return []


def playbook_errors(
    cfg: RegistryConfig,
    playbooks: dict[str, Playbook],
    definitions: dict[str, TraitDefinition],
) -> list[str]:
    """Each step's ID is `<playbook>#<position>`; every trait (the playbook's,
    each action's and each call's `needs`) is defined and listed once per
    list; every call resolves (`skill:<name>` to a skill folder or principle
    file, `playbook:<name>` to a playbook); every load is a file under the
    playbook's own `playbooks/<name>/` folder, so a reference has one owner
    (F1, F3; a second consumer promotes it, F2)."""
    errors: list[str] = []
    for name, book in sorted(playbooks.items()):
        where = book.path
        if not _NAME_RE.fullmatch(name):
            errors.append(f"{where}: the name {name!r} is not kebab case (B1)")
        errors += _undefined(where, book.traits, definitions)
        if len(set(book.traits)) != len(book.traits):
            errors.append(f"{where}: a playbook trait is listed twice")
        for n, step in enumerate(book.steps, start=1):
            at = f"{where}: {step.id}"
            if step.id != f"{name}#{n}":
                errors.append(
                    f"{at}: step {n} has ID {step.id!r}; IDs are {name}#<position>"
                )
            errors += _undefined(at, step.traits, definitions)
            if len(set(step.traits)) != len(step.traits):
                errors.append(f"{at}: an action trait is listed twice")
            for call in step.calls:
                errors += _call_errors(cfg, at, call.to, playbooks)
                errors += _undefined(f"{at}: call {call.to}", call.needs, definitions)
                if len(set(call.needs)) != len(call.needs):
                    errors.append(
                        f"{at}: call {call.to}: a needs trait is listed twice"
                    )
            for load in step.loads:
                rel = book.load_path(load)
                if rel is None or not _target_exists(f"doc:{rel}", set(), None, cfg):
                    errors.append(
                        f"{at}: load {load.path!r}: no such reference (a file "
                        f"under {book.references_dir}/; a reference has one "
                        f"owner, F1, F3)"
                    )
    return errors


def playbook_ledger_errors(cfg: RegistryConfig, events: list[Event]) -> list[str]:
    """Each playbook's hash lives on its effective event (§4b): that event names
    a playbook file that exists and carries `target_tree_hash`, and every
    playbook file has such an event, at its current hash. A renamed-away path's
    effective event is its `rename`, whose survivor must have such an event.
    Only effective events are read, so a sealed event is corrected by
    superseding it."""
    live = live_events(events)
    current = effective_by_subject(live)
    effective = {
        subject: event
        for subject, event in current.items()
        if subject.startswith("doc:") and event.kind in PLAYBOOK_KINDS
    }
    errors: list[str] = []
    forward, _ = build_lifecycle(live)
    for subject, event in sorted(current.items()):
        if not (subject.startswith("doc:") and event.kind == "rename"):
            continue
        survivor = resolve_skill(subject, forward)
        if doc_holder_kind(cfg, subject[len("doc:") :]) != "playbook":
            errors.append(f"{event.id}: {subject} names no playbook file")
        elif survivor not in effective:
            errors.append(
                f"{event.id}: {subject} is renamed to {survivor}, which has no "
                f"effective `add` or `update` (README §4b)"
            )
    for subject, event in sorted(effective.items()):
        rel = subject[len("doc:") :]
        if doc_holder_kind(cfg, rel) != "playbook":
            errors.append(f"{event.id}: {subject} names no playbook file")
        elif not (cfg.repo_root / rel).is_file():
            errors.append(
                f"{rel}: no such playbook, but {event.id} is its effective event; "
                f"removing a playbook has no event yet (README §4b)"
            )
        elif event.target_tree_hash is None:
            errors.append(f"{event.id}: {subject} has no `target_tree_hash`")
    for file in playbook_files(cfg):
        rel = str(file.relative_to(cfg.repo_root))
        found = effective.get(f"doc:{rel}")
        if found is None:
            errors.append(f"{rel}: no ledger event; `record` an `add` (README §4b)")
        elif found.target_tree_hash not in (None, playbook_tree_hash(cfg, rel)):
            errors.append(
                f"{rel}: changed since {found.id}; `record` an `update` (README §4b)"
            )
    return errors
