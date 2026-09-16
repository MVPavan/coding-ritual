"""Command-line entry point for ledger export and import (§3.6).

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

from workflow_interpreter.bdio.errors import StoreError
from workflow_interpreter.foreman.config import load_config
from workflow_interpreter.ledger.constants import EXPORT_SUFFIX
from workflow_interpreter.ledger.database import open_ledger
from workflow_interpreter.ledger.export import import_export, write_export
from workflow_interpreter.ledger.paths import export_dir, ledger_path

PROG: Final[str] = "python -m workflow_interpreter.ledger"
COMMAND_EXPORT: Final[str] = "export"
COMMAND_IMPORT: Final[str] = "import"
EXIT_OK: Final[int] = 0
EXIT_REFUSED: Final[int] = 2

_MSG_NO_EXPORTS: Final[str] = "ledger: no export files under {directory}\n"
_MSG_REFUSED: Final[str] = "ledger: {reason}\n"
_MSG_EXPORTED: Final[str] = "exported {task_id} to {path}\n"
_MSG_IMPORTED: Final[str] = "imported {task_id} from {path}\n"


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
        help="tasks to rebuild; every export file when none is named",
    )
    return parser


def _exports(repo_root: Path, task_ids: Sequence[str]) -> tuple[Path, ...]:
    """The export files a rebuild reads, named or discovered in `(task)` order."""
    directory = export_dir(repo_root)
    if task_ids:
        return tuple(directory / f"{task_id}{EXPORT_SUFFIX}" for task_id in task_ids)
    return tuple(sorted(directory.glob(f"*{EXPORT_SUFFIX}")))


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
        paths = _exports(repo_root, args.task_ids)
        if not paths:
            sys.stderr.write(_MSG_NO_EXPORTS.format(directory=export_dir(repo_root)))
            return EXIT_REFUSED
        # The schema has to exist before an import can fill it, and creating it
        # takes the exclusive fence — so the ledger is opened and CLOSED first,
        # rather than held while the import asks for the same fence (§3.4).
        with open_ledger(repo_root, wrapper_root):
            pass
        for path in paths:
            task_id = import_export(
                path,
                repo_root=repo_root,
                wrapper_root=wrapper_root,
                ledger=ledger_path(repo_root),
            )
            sys.stdout.write(_MSG_IMPORTED.format(task_id=task_id, path=path))
    except (OSError, ValueError, ValidationError, StoreError) as exc:
        sys.stderr.write(_MSG_REFUSED.format(reason=exc))
        return EXIT_REFUSED
    return EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())
