"""Bounded command-line entrypoints for manual foreman operation."""

from __future__ import annotations

import argparse
import io
import json
import os
import sys
import traceback
from collections.abc import Callable, Sequence
from pathlib import Path

from workflow_interpreter.bdio import WorkflowStore
from workflow_interpreter.foreman.compose import Composition, DetachedSpawner
from workflow_interpreter.foreman.config import load_config
from workflow_interpreter.foreman.constants import (
    GATES_DIR,
    INSTANCE_BRANCH,
    MAX_TRANSCRIPT_BYTES,
)
from workflow_interpreter.foreman.frontier import build_frontier
from workflow_interpreter.foreman.gates import payload_template
from workflow_interpreter.foreman.identifiers import validate_bead_id
from workflow_interpreter.foreman.supervise import run_wrapper
from workflow_interpreter.foreman.tick import Foreman
from workflow_interpreter.foreman.transcript import bounded_tail
from workflow_interpreter.profiles.registry import ProfileRegistry
from workflow_interpreter.supervisor.clock import SystemClock
from workflow_interpreter.supervisor.gitio import Git


def _composition(path: Path | None) -> Composition:
    """Build production collaborators from the explicitly supplied TOML file."""
    if path is None:
        raise ValueError("foreman configuration path is required")
    config = load_config(path)
    clock = SystemClock()
    return Composition(
        config=config,
        store=WorkflowStore.from_config(config.bd, config.signing),
        supervisor_config=config.supervisor,
        git=Git(config.supervisor),
        clock=clock,
        profiles=ProfileRegistry(config.profiles, config.supervisor, clock, os.environ),
        spawner=DetachedSpawner(config.supervisor, path),
    )


def _parser() -> argparse.ArgumentParser:
    """Create the five public, deliberately small command forms."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path)
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("tick", "status"):
        child = commands.add_parser(name)
        child.add_argument("root_id")
    supervise = commands.add_parser("supervise")
    supervise.add_argument("root_id")
    supervise.add_argument("activation_id")
    supervise.add_argument("--config", type=Path, required=True)
    inspect = commands.add_parser("inspect")
    inspect.add_argument("root_id")
    inspect.add_argument("activation_id")
    steer = commands.add_parser("steer")
    steer.add_argument("root_id")
    steer.add_argument("activation_id")
    steer.add_argument("--reason", required=True)
    steer.add_argument("--instructions-file", type=Path, required=True)
    return parser


def _emit(value: str, *, limit: int = MAX_TRANSCRIPT_BYTES) -> None:
    """Write one JSON report, truncating only its tail to fit the byte budget."""
    report = json.loads(value)
    if not isinstance(report, dict):
        raise TypeError("foreman reports must be JSON objects")

    def render() -> str:
        return json.dumps(report, ensure_ascii=False, separators=(",", ":"))

    rendered = render()
    for field in ("tail", "stalled"):
        report_value = report.get(field)
        if len((rendered + "\n").encode("utf-8")) <= limit or not isinstance(
            report_value, str
        ):
            continue
        encoded_value = report_value.encode("utf-8")
        low, high = 0, len(encoded_value)
        while low <= high:
            middle = (low + high) // 2
            report[field] = bounded_tail(report_value, middle)
            candidate = render()
            if len((candidate + "\n").encode("utf-8")) <= limit:
                rendered = candidate
                low = middle + 1
            else:
                high = middle - 1
        report[field] = bounded_tail(report_value, high)
        rendered = render()
    if len((rendered + "\n").encode("utf-8")) > limit:
        rendered = '{"truncated":true}'
    sys.stdout.write(rendered + "\n")


def _is_supervise(argv: Sequence[str] | None) -> bool:
    """Recognize the subcommand without moving non-wrapper parser errors."""
    arguments = tuple(sys.argv[1:] if argv is None else argv)
    index = 0
    while index < len(arguments):
        argument = arguments[index]
        if argument == "--config":
            index += 2
            continue
        if argument.startswith(("--config=", "-")):
            index += 1
            continue
        return argument == "supervise"
    return False


def main(argv: Sequence[str] | None = None) -> int:
    """Run one command, exempting the redirected wrapper log from the transcript cap."""
    if _is_supervise(argv):
        try:
            return _run(argv, lambda value, limit: _emit(value, limit=limit))
        except SystemExit:
            raise
        except Exception:  # noqa: BLE001 -- wrapper diagnostics belong in its log.
            traceback.print_exc()
            return 1
    original_stdout, original_stderr = sys.stdout, sys.stderr
    captured_stdout_bytes = io.BytesIO()
    captured_stderr_bytes = io.BytesIO()
    captured_stdout = io.TextIOWrapper(
        captured_stdout_bytes, encoding="utf-8", write_through=True
    )
    captured_stderr = io.TextIOWrapper(
        captured_stderr_bytes, encoding="utf-8", write_through=True
    )
    sys.stdout = captured_stdout
    sys.stderr = captured_stderr
    limit = MAX_TRANSCRIPT_BYTES
    raised: SystemExit | None = None

    def emit(value: str, emitted_limit: int) -> None:
        nonlocal limit
        limit = emitted_limit
        _emit(value, limit=limit)

    try:
        return _run(argv, emit)
    except SystemExit as exc:
        raised = exc
        return_code = exc.code if isinstance(exc.code, int) else 1
    except Exception:  # noqa: BLE001 -- the CLI must bound every runtime traceback.
        traceback.print_exc()
        return_code = 1
    finally:
        captured_stdout.flush()
        captured_stderr.flush()
        stdout_text = captured_stdout_bytes.getvalue().decode("utf-8", errors="replace")
        stderr_text = captured_stderr_bytes.getvalue().decode("utf-8", errors="replace")
        sys.stdout = original_stdout
        sys.stderr = original_stderr
        stdout = bounded_tail(stdout_text, limit)
        remaining = max(limit - len(stdout.encode("utf-8")), 0)
        original_stdout.write(stdout)
        original_stdout.flush()
        original_stderr.write(bounded_tail(stderr_text, remaining))
        original_stderr.flush()
    if raised is not None:
        raise raised
    return return_code


def _run(
    argv: Sequence[str] | None,
    emit: Callable[[str, int], None],
) -> int:
    """Execute one command while its caller owns the transcript renderer."""
    args = _parser().parse_args(argv)
    validate_bead_id(args.root_id)
    if hasattr(args, "activation_id"):
        validate_bead_id(args.activation_id)
    composition = _composition(args.config)
    foreman = Foreman(composition)
    if args.command == "supervise":
        return (
            0
            if run_wrapper(composition, args.root_id, args.activation_id).value
            in {"done", "stale", "locked"}
            else 1
        )
    if args.command == "tick":
        emit(foreman.tick(args.root_id).model_dump_json(), MAX_TRANSCRIPT_BYTES)
        return 0
    if args.command == "inspect":
        limit = MAX_TRANSCRIPT_BYTES + composition.supervisor_config.log_tail_bytes
        emit(foreman.inspect(args.root_id, args.activation_id).model_dump_json(), limit)
        return 0
    if args.command == "steer":
        limit = MAX_TRANSCRIPT_BYTES + composition.supervisor_config.log_tail_bytes
        emit(
            foreman.steer(
                args.root_id,
                args.activation_id,
                reason=args.reason,
                instructions=args.instructions_file.read_text(encoding="utf-8"),
            ).model_dump_json(),
            limit,
        )
        return 0
    wiring = composition.for_root(args.root_id)
    root = wiring.store.reads.load_root(args.root_id)
    frontier = build_frontier(root, wiring.store.reads.instance_beads(args.root_id))
    status: dict[str, object] = {
        "root_id": args.root_id,
        "activations": len(wiring.store.reads.list_activations(args.root_id)),
        "instance_base_commit": root.metadata.instance_base_commit,
        "instance_branch_head": composition.git.ref_target(
            INSTANCE_BRANCH.format(root_id=args.root_id),
            cwd=composition.config.repo_root,
        ),
        "stale": tuple(
            f"stale {activation.activation_id} since "
            f"{activation.metadata.stale_flag.raised_at}; inspect for the tail"
            for activation in wiring.store.reads.list_activations(args.root_id)
            if activation.metadata.stale_flag is not None
        ),
    }
    if frontier.open_halt is not None:
        gate = frontier.open_halt
        status["open_halt"] = {
            "inbox": str(
                wiring.paths.instance_dir / GATES_DIR / gate.metadata.gate_key
            ),
            "template": payload_template(root, gate),
        }
    emit(json.dumps(status, sort_keys=True), MAX_TRANSCRIPT_BYTES)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
