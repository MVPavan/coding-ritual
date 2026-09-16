"""Command-line entry point for ledger export, import and reconcile (§3.2, §3.6).

`wf ledger export <task>` and `wf ledger import` in the plan's vocabulary; this
repository spells its entry points `python -m workflow_interpreter.<package>`
(see `workflow_interpreter/costs/__main__.py`), and authority arrives the same
way it does there — as an explicit `--config` file, never from the environment.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Final

from pydantic import ValidationError

from workflow_interpreter.bdio.client import BdClient
from workflow_interpreter.bdio.errors import StoreError
from workflow_interpreter.foreman.config import ForemanConfig, load_config
from workflow_interpreter.ledger.constants import EXPORT_SUFFIX
from workflow_interpreter.ledger.database import open_ledger
from workflow_interpreter.ledger.export import import_exports, write_export
from workflow_interpreter.ledger.paths import export_dir, ledger_path
from workflow_interpreter.ledger.reconcile import ATTENTION_LABEL, AttentionReconciler

PROG: Final[str] = "python -m workflow_interpreter.ledger"
COMMAND_EXPORT: Final[str] = "export"
COMMAND_IMPORT: Final[str] = "import"
COMMAND_RECONCILE: Final[str] = "reconcile"
EXIT_OK: Final[int] = 0
EXIT_REFUSED: Final[int] = 2

_MSG_NO_EXPORTS: Final[str] = "ledger: no export files under {directory}\n"
_MSG_REFUSED: Final[str] = "ledger: {reason}\n"
_MSG_EXPORTED: Final[str] = "exported {task_id} to {path}\n"
_MSG_IMPORTED: Final[str] = "imported {task_id} from {path}\n"
_MSG_RECONCILED: Final[str] = (
    "reconciled {task_id}: {label} {presence}, generation {generation}, "
    "{acked} row(s) acked\n"
)
_MSG_NOTHING_DUE: Final[str] = "reconciled {task_id}: nothing due\n"
_PRESENT: Final[str] = "present"
_ABSENT: Final[str] = "absent"


def _parser() -> argparse.ArgumentParser:
    """Build the finite ledger CLI vocabulary."""
    parser = argparse.ArgumentParser(prog=PROG)
    parser.add_argument("--config", required=True, type=Path)
    commands = parser.add_subparsers(dest="command", required=True)
    export = commands.add_parser(
        COMMAND_EXPORT, help="write one task's rows to .wf/export/<task>.jsonl"
    )
    export.add_argument("task_id")
    restore = commands.add_parser(
        COMMAND_IMPORT, help="rebuild tasks from .wf/export/, under the exclusive fence"
    )
    restore.add_argument(
        "task_ids",
        nargs="*",
        help=(
            "the export files the ledger is rebuilt from; every export file "
            "when none is named. An import REPLACES the exportable state, so "
            "a task no named file describes does not survive it"
        ),
    )
    reconcile = commands.add_parser(
        COMMAND_RECONCILE,
        help="drain one task's unacked attention projections onto its bead",
    )
    reconcile.add_argument("task_id")
    return parser


def _exports(repo_root: Path, task_ids: Sequence[str]) -> tuple[Path, ...]:
    """The export files a rebuild reads, named or discovered in `(task)` order."""
    directory = export_dir(repo_root)
    if task_ids:
        return tuple(directory / f"{task_id}{EXPORT_SUFFIX}" for task_id in task_ids)
    return tuple(sorted(directory.glob(f"*{EXPORT_SUFFIX}")))


def _reconcile(config: ForemanConfig, task_id: str) -> int:
    """Drain the unacked attention projections of one task (§3.2.4).

    The bd client is built HERE and injected: a CLI is a composition root, and
    the reconciler must not construct its own transport.
    """
    with open_ledger(config.repo_root, config.wrapper_root) as database:
        result = AttentionReconciler(database, BdClient(config.bd)).drain(task_id)
    if not result.written:
        sys.stdout.write(_MSG_NOTHING_DUE.format(task_id=task_id))
        return EXIT_OK
    sys.stdout.write(
        _MSG_RECONCILED.format(
            task_id=task_id,
            label=ATTENTION_LABEL,
            presence=_PRESENT if result.wanted else _ABSENT,
            generation=result.generation,
            acked=result.acked,
        )
    )
    return EXIT_OK


def main(argv: Sequence[str] | None = None) -> int:
    """Export one task, or rebuild tasks from their exports."""
    args = _parser().parse_args(argv)
    try:
        config = load_config(args.config)
        repo_root = config.repo_root
        wrapper_root = config.wrapper_root
        if args.command == COMMAND_EXPORT:
            with open_ledger(repo_root, wrapper_root) as database:
                path = write_export(database, args.task_id)
            sys.stdout.write(_MSG_EXPORTED.format(task_id=args.task_id, path=path))
            return EXIT_OK
        if args.command == COMMAND_RECONCILE:
            return _reconcile(config, args.task_id)
        paths = _exports(repo_root, args.task_ids)
        if not paths:
            sys.stderr.write(_MSG_NO_EXPORTS.format(directory=export_dir(repo_root)))
            return EXIT_REFUSED
        # The schema has to exist before an import can fill it, and creating it
        # takes the exclusive fence — so the ledger is opened and CLOSED first,
        # rather than held while the import asks for the same fence (§3.4).
        with open_ledger(repo_root, wrapper_root):
            pass
        # ONE call, so the whole set lands under ONE fence and ONE transaction
        # (§3.6): a per-file loop would let a reader in between two files and
        # would leave the first files applied when a later one failed.
        task_ids = import_exports(
            paths,
            repo_root=repo_root,
            wrapper_root=wrapper_root,
            ledger=ledger_path(repo_root),
        )
        for task_id, path in zip(task_ids, paths, strict=True):
            sys.stdout.write(_MSG_IMPORTED.format(task_id=task_id, path=path))
    except (OSError, ValueError, ValidationError, StoreError) as exc:
        sys.stderr.write(_MSG_REFUSED.format(reason=exc))
        return EXIT_REFUSED
    return EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())
