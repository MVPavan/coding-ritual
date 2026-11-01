"""Playbook checks: step IDs, defined traits, resolvable calls and loads (St1,
B1, F1)."""

from __future__ import annotations

import re

from curation.registry.checks.records import _target_exists
from curation.registry.config import RegistryConfig
from curation.registry.models import TraitDefinition
from curation.registry.steps import CALL_KINDS, Playbook

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
        if "/" in name or not (cfg.skills_dir / name / "SKILL.md").is_file():
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
    list; every call resolves (`skill:<name>` to a skill folder,
    `playbook:<name>` to a playbook); every load is a file under the
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
