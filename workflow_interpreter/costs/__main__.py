"""Command-line entry point for read-only task cost reports."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from contextlib import ExitStack
from pathlib import Path

from pydantic import ValidationError

from workflow_interpreter.bdio.backend import SelectableBackendFactory
from workflow_interpreter.bdio.client import BdClient
from workflow_interpreter.costs.collection import collect_task
from workflow_interpreter.costs.pricing import PriceBook
from workflow_interpreter.costs.report import (
    CohortReport,
    TaskCostReport,
    build_task_report,
    cohort_report,
    cohort_text_report,
    text_report,
)
from workflow_interpreter.costs.supplement import UsageSupplement, apply_supplement
from workflow_interpreter.foreman.config import load_config
from workflow_interpreter.ledger.database import open_ledger
from workflow_interpreter.ledger.paths import ledger_path
from workflow_interpreter.ledger.store import LedgerStore


def _parser() -> argparse.ArgumentParser:
    """Build the finite task-cost CLI vocabulary."""
    parser = argparse.ArgumentParser(prog="python -m workflow_interpreter.costs")
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--prices", required=True, type=Path)
    commands = parser.add_subparsers(dest="command", required=True)
    task = commands.add_parser("task", help="report one explicit stage id")
    task.add_argument("stage_id")
    cohort = commands.add_parser("cohort", help="roll up explicit stage ids")
    cohort.add_argument("stage_ids", nargs="+")
    for command in (task, cohort):
        command.add_argument("--format", choices=("json", "text"), default="text")
        command.add_argument("--as-of")
        command.add_argument(
            "--normalize-standard",
            action="store_true",
            help="apply standard rates when the observed tier is unavailable",
        )
        command.add_argument("--supplement", type=Path)
        command.add_argument(
            "--runtime-root",
            action="append",
            default=[],
            metavar="ROOT_ID=PATH",
        )
    return parser


def _runtime_roots(values: Sequence[str]) -> dict[str, Path]:
    """Parse unique explicit root-to-wrapper-instance-directory mappings."""
    result: dict[str, Path] = {}
    for value in values:
        root_id, separator, raw_path = value.partition("=")
        if not separator or not root_id or not raw_path:
            raise ValueError("runtime roots must use ROOT_ID=PATH")
        if root_id in result:
            raise ValueError(f"duplicate runtime root mapping for {root_id!r}")
        path = Path(raw_path)
        if not path.is_absolute():
            raise ValueError("runtime root paths must be absolute")
        result[root_id] = path
    return result


def _emit_task(report: TaskCostReport, output_format: str) -> None:
    """Write one deterministic task report."""
    if output_format == "json":
        sys.stdout.write(report.model_dump_json(by_alias=True) + "\n")
    else:
        sys.stdout.write(text_report(report))


def _emit_cohort(report: CohortReport, output_format: str) -> None:
    """Write one deterministic cohort report."""
    if output_format == "json":
        sys.stdout.write(report.model_dump_json(by_alias=True) + "\n")
        return
    sys.stdout.write(cohort_text_report(report))


def main(argv: Sequence[str] | None = None) -> int:
    """Run a read-only task or explicit-cohort report command."""
    parser = _parser()
    args = parser.parse_args(argv)
    try:
        config = load_config(args.config)
        prices = PriceBook.load(args.prices)
        supplement = (
            None if args.supplement is None else UsageSupplement.load(args.supplement)
        )
        runtime_roots = _runtime_roots(args.runtime_root)
        client = BdClient(config.bd)
        stage_ids = (
            (args.stage_id,) if args.command == "task" else tuple(args.stage_ids)
        )
        if len(stage_ids) != len(set(stage_ids)):
            raise ValueError("stage ids must be unique")
        reports: list[TaskCostReport] = []
        # §3.4: costs is READ-ONLY, so it opens an existing ledger and never
        # creates one — `open_ledger` migrates, and migrating is a write. A
        # repository with no ledger has no ledger-backed root either, and a
        # bridge record that claims otherwise gets the factory's refusal.
        ledger_file = ledger_path(config.repo_root)
        with ExitStack() as resources:
            ledger = (
                resources.enter_context(
                    open_ledger(config.repo_root, config.wrapper_root)
                )
                if ledger_file.is_file()
                else None
            )
            for stage_id in stage_ids:
                # One factory per stage, because a `LedgerStore` is scoped to
                # the task whose rows it hold (§3.3): the stage IS that task.
                backends = SelectableBackendFactory(
                    client,
                    *(
                        ()
                        if ledger is None
                        else (LedgerStore(ledger, task_id=stage_id),)
                    ),
                )
                collection = collect_task(
                    client,
                    stage_id,
                    backends=backends,
                    runtime_roots=runtime_roots,
                )
                if supplement is not None:
                    collection = apply_supplement(collection, supplement)
                reports.append(
                    build_task_report(
                        collection,
                        prices,
                        as_of=args.as_of,
                        normalize_standard=args.normalize_standard,
                    )
                )
    except (OSError, ValueError, ValidationError) as exc:
        del exc
        sys.stderr.write("task-cost: invalid or unavailable local input\n")
        return 2
    if args.command == "task":
        _emit_task(reports[0], args.format)
    else:
        _emit_cohort(cohort_report(tuple(reports)), args.format)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
