"""Bounded command-line entrypoints for manual foreman operation."""

from __future__ import annotations

import argparse
import io
import json
import logging
import os
import sys
import traceback
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Final

import structlog

from workflow_interpreter.bdio import ActivationRecord, GateRecord, WorkflowStore
from workflow_interpreter.bdio.reads import activations_of
from workflow_interpreter.bdio.records import RootRecord
from workflow_interpreter.bridge.command import execute_phase_bridge
from workflow_interpreter.bridge.gate_view import phase_bridge_gate_view
from workflow_interpreter.foreman.compose import (
    Composition,
    DetachedSpawner,
    InstanceWiring,
)
from workflow_interpreter.foreman.config import ForemanConfig, load_config
from workflow_interpreter.foreman.constants import (
    INSTANCE_BRANCH,
    MAX_GATE_DIFF_BYTES,
    MAX_TRANSCRIPT_BYTES,
    NO_ARTIFACT,
    NO_ARTIFACT_OID,
    RUN_DEFAULT_MAX_WALL_S,
    RUN_DEFAULT_POLL_S,
)
from workflow_interpreter.foreman.errors import ResolutionError
from workflow_interpreter.foreman.frontier import Frontier, build_frontier
from workflow_interpreter.foreman.gates import inbox_dir, payload_template
from workflow_interpreter.foreman.identifiers import InvalidIdentifier, validate_bead_id
from workflow_interpreter.foreman.resolve import instantiate
from workflow_interpreter.foreman.supervise import run_wrapper
from workflow_interpreter.foreman.tick import Foreman
from workflow_interpreter.foreman.transcript import bounded_tail
from workflow_interpreter.profiles.registry import ProfileRegistry
from workflow_interpreter.supervisor.clock import SystemClock
from workflow_interpreter.supervisor.gitio import Git

# The per-subprocess `debug` chatter every git and bd call emits is worthless in
# an operator transcript, while `wf.verify.rerun` and every error must stay
# visible — INFO is the line between the two.
LOG_LEVEL: Final[int] = logging.INFO

MSG_NO_SIGNING: Final[str] = (
    "refusing to create a root this config cannot approve: no [signing] "
    "allowed_signers_path, so every gate close raises BdConfigError — render a "
    "config with scripts/make-foreman-config.sh, or pass --allow-unsigned-gates "
    "for a lab instance that will never be approved"
)
MSG_ALLOW_LIST_UNREADABLE: Final[str] = (
    "refusing to create a root this config cannot approve: gate allow-list "
    "{path} is unreadable ({reason}); scripts/make-foreman-config.sh generates it"
)
MSG_ALLOW_LIST_EMPTY: Final[str] = (
    "refusing to create a root this config cannot approve: gate allow-list "
    "{path} is empty, so no signer exists; scripts/make-foreman-config.sh "
    "generates a key and lists it"
)


def _stderr_logger(*_args: object) -> structlog.PrintLogger:
    """Build a logger bound to whatever `sys.stderr` is at the moment of the call."""
    return structlog.PrintLogger(file=sys.stderr)


def _configure_logging() -> None:
    """Send every log line to stderr so stdout carries the one JSON report alone.

    The sink is resolved per call, not captured here: `main` swaps `sys.stderr`
    for a capturing wrapper and the `supervise` branch runs under the wrapper's
    own redirected streams, so a factory holding today's stderr object would
    write to a stream nobody is reading. That also forbids
    `cache_logger_on_first_use`.
    """
    structlog.configure(
        processors=[
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.KeyValueRenderer(key_order=["event"]),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(LOG_LEVEL),
        logger_factory=_stderr_logger,
        cache_logger_on_first_use=False,
    )


def _composition(path: Path | None) -> Composition:
    """Build production collaborators from the explicitly supplied TOML file."""
    if path is None:
        raise InvalidIdentifier("foreman configuration path is required: pass --config")
    config = load_config(path)
    clock = SystemClock()
    return Composition(
        config=config,
        store=WorkflowStore.from_config(config.bd, config.signing),
        supervisor_config=config.supervisor,
        git=Git(config.supervisor),
        clock=clock,
        profiles=ProfileRegistry(config.profiles, clock, os.environ),
        spawner=DetachedSpawner(config.supervisor, path),
    )


def _parser() -> argparse.ArgumentParser:
    """Create the eight public, deliberately small command forms.

    `--config` is a top-level option for every command, `supervise` included:
    the detached wrapper spawn passes it in that one position too, so there is
    a single spelling to keep in step with `DetachedSpawner`.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path)
    commands = parser.add_subparsers(dest="command", required=True)
    create = commands.add_parser("create")
    create.add_argument("graph", type=Path)
    create.add_argument("--instance-key", required=True)
    create.add_argument("--input", action="append", default=[], metavar="NAME=PATH")
    create.add_argument("--allow-test-flags", action="store_true")
    create.add_argument("--allow-unsigned-gates", action="store_true")
    for name in ("tick", "status"):
        child = commands.add_parser(name)
        child.add_argument("root_id")
    run = commands.add_parser("run")
    run.add_argument("root_id")
    run.add_argument("--poll", type=float, default=RUN_DEFAULT_POLL_S)
    run.add_argument("--max-wall", type=float, default=RUN_DEFAULT_MAX_WALL_S)
    phase_bridge = commands.add_parser("phase-bridge")
    phase_bridge.add_argument("epic_id")
    phase_bridge.add_argument("stage_id")
    phase_bridge.add_argument("--retry", action="store_true")
    phase_bridge.add_argument("--retry-landing", action="store_true")
    phase_bridge.add_argument("--trace", action="store_true")
    supervise = commands.add_parser("supervise")
    supervise.add_argument("root_id")
    supervise.add_argument("activation_id")
    inspect = commands.add_parser("inspect")
    inspect.add_argument("root_id")
    inspect.add_argument("activation_id")
    steer = commands.add_parser("steer")
    steer.add_argument("root_id")
    steer.add_argument("activation_id")
    steer.add_argument("--reason", required=True)
    steer.add_argument("--instructions-file", type=Path, required=True)
    integration = commands.add_parser("integration").add_subparsers(
        dest="integration_command", required=True
    )
    prepare = integration.add_parser("prepare")
    prepare.add_argument("--request", type=Path, required=True)
    for name in ("status", "retry"):
        operation = integration.add_parser(name)
        operation.add_argument("epic_id")
        operation.add_argument("stage_id")
    children = commands.add_parser("children").add_subparsers(
        dest="child_command", required=True
    )
    replacement = children.add_parser("replace")
    replacement.add_argument("owner_id")
    replacement.add_argument("--slot", required=True)
    replacement.add_argument("--generation", required=True, type=int)
    replacement.add_argument("--request", required=True, type=Path)
    for name in ("admit", "start", "status", "collect", "cancel", "recover", "drive"):
        child = children.add_parser(name)
        child.add_argument("owner_id")
        if name in ("admit", "start", "collect", "cancel", "recover"):
            child.add_argument("slot")
        if name in ("collect", "cancel", "recover"):
            child.add_argument("generation", type=int)
        if name == "admit":
            child.add_argument("--graph", type=Path, required=True)
            child.add_argument(
                "--input", action="append", default=[], metavar="NAME=FILE"
            )
        if name == "start":
            child.add_argument("--admission", type=Path, required=True)
        if name == "cancel":
            child.add_argument("--request-key", required=True)
            child.add_argument("--reason", required=True)
        if name == "drive":
            child.add_argument("--max-concurrent", type=int, required=True)
            child.add_argument("--max-wall", type=float, required=True)
    return parser


def _instance_inputs(pairs: Sequence[str]) -> dict[str, Path]:
    """Parse the repeated `--input NAME=PATH` pairs into one named mapping."""
    inputs: dict[str, Path] = {}
    for pair in pairs:
        name, separator, path = pair.partition("=")
        if not separator or not name or not path:
            raise ResolutionError(f"--input must be NAME=PATH, got {pair}")
        if name in inputs:
            raise ResolutionError(f"--input {name} was given twice")
        inputs[name] = Path(path)
    return inputs


def _signing_preflight(config: ForemanConfig, *, allow_unsigned: bool) -> str | None:
    """Refuse, in one line, a root whose gates nobody would be able to close.

    `close_gate_verified` raises `BdConfigError` when no verifier is configured
    (`bdio/api.py`) and `GateVerifier` needs a readable allow-list, so an
    unsigned or empty-allow-list config fails first at the `ship` gate — after
    a whole run, with a human already waiting. Both are decidable at `create`,
    which is the last moment before anything durable exists.
    """
    if config.signing is None:
        return None if allow_unsigned else MSG_NO_SIGNING
    path = config.signing.allowed_signers_path
    try:
        empty = not path.read_text(encoding="utf-8").strip()
    except OSError as unreadable:
        return MSG_ALLOW_LIST_UNREADABLE.format(path=path, reason=unreadable)
    return MSG_ALLOW_LIST_EMPTY.format(path=path) if empty else None


def _create(args: argparse.Namespace) -> int:
    """Pin one new instance root and print nothing but its id.

    The root id is the only thing a caller needs to reach every other command,
    so it is written as a bare line rather than through the JSON report
    renderer the root-scoped commands share.
    """
    composition = _composition(args.config)
    refusal = _signing_preflight(
        composition.config, allow_unsigned=args.allow_unsigned_gates
    )
    if refusal is not None:
        sys.stderr.write(f"{refusal}\n")
        return 1
    try:
        root = instantiate(
            composition,
            args.graph,
            instance_key=args.instance_key,
            instance_inputs=_instance_inputs(args.input),
            allow_test_flags=args.allow_test_flags,
            overrides={},
        )
    except ResolutionError as refused:
        sys.stderr.write(f"{refused}\n")
        return 1
    sys.stdout.write(f"{root.root_id}\n")
    return 0


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


@dataclass(frozen=True)
class _InstanceView:
    """The durable reads every root-scoped report shares, taken once."""

    wiring: InstanceWiring
    root: RootRecord
    frontier: Frontier
    activations: Mapping[str, ActivationRecord]


def _coordination_report(
    composition: Composition, root: RootRecord
) -> dict[str, object]:
    """Reserved capacity is separate from actual activation/provider usage."""
    link = root.metadata.coordination
    if link is None:
        return {}
    return {
        "coordination": composition.store.coordination_store()
        .coordination_view(link.owner_id)
        .model_dump(mode="json")
    }


def _view(composition: Composition, root_id: str) -> _InstanceView:
    """Load one instance's beads a single time for a whole rendered report."""
    requested = composition.store.reads.load_root(root_id)
    if requested.metadata.coordination_state is not None:
        root_id = requested.metadata.coordination_state.active.get("work") or root_id
    wiring = composition.for_root(root_id)
    root = wiring.store.reads.load_root(root_id)
    beads = wiring.store.reads.instance_beads(root_id)
    return _InstanceView(
        wiring=wiring,
        root=root,
        frontier=build_frontier(root, beads),
        activations={item.activation_id: item for item in activations_of(tuple(beads))},
    )


def _diff_stat(composition: Composition, root: RootRecord, gate: GateRecord) -> str:
    """The cumulative diff a §9 approver signs off on, base to artifact."""
    artifact = gate.metadata.artifact_ref
    base = root.metadata.instance_base_commit
    # A halt gate pins no artifact, and a root with no pinned base never
    # dispatched anything: both leave the approver nothing to diff.
    if artifact is None or artifact == NO_ARTIFACT_OID or base is None:
        return NO_ARTIFACT
    return bounded_tail(
        composition.git.diff_stat(
            base,
            artifact,
            cwd=composition.config.repo_root,
        ),
        MAX_GATE_DIFF_BYTES,
    )


def _findings(
    composition: Composition, view: _InstanceView, gate: GateRecord
) -> tuple[str, ...]:
    """The paths of the findings the gate's source activation produced.

    Evidence pins outputs as a git tree rather than as a path list
    (`outputs_tree_oid`), so the paths are read from the object store. A source
    that pinned nothing renders its `$WF_ARTIFACT_DIR` instead — the directory
    where those bytes would have been.
    """
    source = gate.metadata.source_activation_id
    if source is None:
        return ()
    activation = view.activations.get(source)
    evidence = None if activation is None else activation.metadata.evidence
    tree = None if evidence is None else evidence.outputs_tree_oid
    if tree is None:
        return (str(view.wiring.paths.artifacts(source)),)
    return composition.git.tree_entries(tree, cwd=composition.config.repo_root)


def _gate_entry(
    composition: Composition,
    view: _InstanceView,
    gate: GateRecord,
    bridge_view: Mapping[str, object],
) -> dict[str, object]:
    """Render the four things a §9 approver cannot derive by hand."""
    return {
        "inbox": str(inbox_dir(view.wiring.paths, gate)),
        "template": payload_template(view.root, gate),
        "diff_stat": _diff_stat(composition, view.root, gate),
        "findings": _findings(composition, view, gate),
        **bridge_view,
    }


def _open_gates(
    composition: Composition, view: _InstanceView, bridge_view: Mapping[str, object]
) -> tuple[dict[str, object], ...]:
    """EVERY open gate, halt and transition alike.

    `status` and `run` are the only commands that render a gate's inbox path
    and unsigned payload template, and §9 approval is exactly "drop
    payload.json and payload.json.sig into that inbox" — so reporting halt
    gates only left a human waiting on `ship` or `triage` (both
    `gate_type = "human"` in the shipped feature-delivery graph) with no way to
    learn either without recomputing the gate key. A gate whose payload has
    already been submitted still appears: the inbox is the truth, and the next
    tick consumes what is in it.
    """
    return tuple(
        {
            "gate_id": gate.gate_id,
            "node": gate.metadata.gate_node,
            "reason": gate.metadata.gate_reason.value,
            **_gate_entry(composition, view, gate, bridge_view),
        }
        for gate in sorted(view.frontier.open_gates, key=lambda item: item.gate_id)
    )


def _usage_summary(
    activations: Mapping[str, ActivationRecord],
) -> dict[str, int | None]:
    """Sum reported usage fields while keeping absent input telemetry unknown."""
    usages = [
        activation.metadata.usage
        for activation in activations.values()
        if activation.metadata.usage is not None
    ]

    def total(values: list[int | None]) -> int | None:
        """Sum one optional token field unless every activation omitted it."""
        return (
            None
            if not any(value is not None for value in values)
            else sum(value or 0 for value in values)
        )

    return {
        "input_tokens": total([usage.input_tokens for usage in usages]),
        "cache_read_input_tokens": total(
            [usage.cache_read_input_tokens for usage in usages]
        ),
        "cache_creation_input_tokens": total(
            [usage.cache_creation_input_tokens for usage in usages]
        ),
        "total_input_tokens": total([usage.total_input_tokens for usage in usages]),
    }


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
    _configure_logging()
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
    if args.command in ("children", "integration"):
        from tomllib import TOMLDecodeError

        from pydantic import ValidationError

        from workflow_interpreter.bdio.errors import BdioError
        from workflow_interpreter.bridge.adapter import PhaseAdapterError
        from workflow_interpreter.bridge.errors import BridgeRefusal
        from workflow_interpreter.foreman.children import command
        from workflow_interpreter.schema.decisions import CoordinationError
        from workflow_interpreter.schema.loader import GraphValidationError
        from workflow_interpreter.supervisor.errors import SupervisorError

        try:
            if args.command == "children":
                validate_bead_id(args.owner_id)
                value = command(_composition(args.config), args)
            else:
                from workflow_interpreter.bridge.integration import (
                    command as integration_command,
                )

                value = integration_command(_composition(args.config), args)
        except (
            InvalidIdentifier,
            BridgeRefusal,
            PhaseAdapterError,
            GraphValidationError,
            CoordinationError,
            ResolutionError,
            ValidationError,
            TOMLDecodeError,
            OSError,
            BdioError,
            SupervisorError,
        ) as exc:
            emit(
                json.dumps({"state": "refused", "reason": str(exc)[:2048]}),
                MAX_TRANSCRIPT_BYTES,
            )
            return 2
        emit(value, MAX_TRANSCRIPT_BYTES)
        return 0
    if args.command == "create":
        return _create(args)
    if args.command == "phase-bridge":
        validate_bead_id(args.epic_id)
        validate_bead_id(args.stage_id)
        composition = _composition(args.config)
        outcome = execute_phase_bridge(
            composition,
            epic_id=args.epic_id,
            stage_id=args.stage_id,
            retry=args.retry,
            retry_landing=args.retry_landing,
            trace=args.trace,
        )
        emit(json.dumps(outcome.report, sort_keys=True), MAX_TRANSCRIPT_BYTES)
        return outcome.exit_code
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
        inspection = foreman.inspect(args.root_id, args.activation_id)
        # Each red §7.3 tail is bounded by `log_tail_bytes` in its own right, so
        # the budget grows by exactly one such tail per red attempt in the
        # report — otherwise a verdict with output collapses to `truncated`.
        red_tails = sum(len(check.red_tails) for check in inspection.verify)
        limit = MAX_TRANSCRIPT_BYTES + composition.supervisor_config.log_tail_bytes * (
            1 + red_tails
        )
        emit(inspection.model_dump_json(), limit)
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
    if args.command == "run":
        result = foreman.run(args.root_id, poll_s=args.poll, max_wall_s=args.max_wall)
        view = _view(composition, args.root_id)
        bridge_view = phase_bridge_gate_view(
            view.root.metadata.instance_key,
            composition.config.bd,
            root_id=view.root.root_id,
        )
        emit(
            json.dumps(
                {
                    **result.model_dump(mode="json"),
                    "open_gates": _open_gates(composition, view, bridge_view),
                    **_coordination_report(composition, view.root),
                },
                sort_keys=True,
            ),
            MAX_TRANSCRIPT_BYTES,
        )
        return 1 if result.report.stalled is not None else 0
    view = _view(composition, args.root_id)
    root, frontier = view.root, view.frontier
    status: dict[str, object] = {
        "root_id": root.root_id,
        **_coordination_report(composition, root),
        "activations": len(view.activations),
        "instance_base_commit": root.metadata.instance_base_commit,
        # The two fields that say an instance is OVER: which terminal it
        # reached and whether its root bead is closed on that fact (§3.1).
        "terminal": frontier.terminal_node,
        "root_state": root.bead.status,
        "instance_branch_head": composition.git.ref_target(
            INSTANCE_BRANCH.format(root_id=root.root_id),
            cwd=composition.config.repo_root,
        ),
        "stale": tuple(
            f"stale {activation.activation_id} since "
            f"{activation.metadata.stale_flag.raised_at}; inspect for the tail"
            for activation in view.activations.values()
            if activation.metadata.stale_flag is not None
        ),
        "usage": _usage_summary(view.activations),
        "input_envelopes": {
            a.activation_id: a.metadata.envelope
            for a in view.activations.values()
            if a.metadata.envelope is not None
        },
    }
    bridge_view = phase_bridge_gate_view(
        root.metadata.instance_key, composition.config.bd, root_id=root.root_id
    )
    status["open_gates"] = _open_gates(composition, view, bridge_view)
    if frontier.open_halt is not None:
        status["open_halt"] = _gate_entry(
            composition, view, frontier.open_halt, bridge_view
        )
    emit(json.dumps(status, sort_keys=True), MAX_TRANSCRIPT_BYTES)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
