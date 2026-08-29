"""D2 inspection and steering drills at the public foreman seam."""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

from tests._bdio import entry_request, handle
from tests._foreman import ForemanLab
from workflow_interpreter.bdio import Lifecycle, MintReason, Outcome
from workflow_interpreter.foreman import __main__ as main_module
from workflow_interpreter.foreman.constants import MAX_TRANSCRIPT_BYTES
from workflow_interpreter.supervisor.paths import ExecLedger
from workflow_interpreter.supervisor.steer import instructions_digest


def test_inspect_reads_only_a_stale_activation_tail_without_writing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """INSPECT catches an unconditional runner-log read or lifecycle write."""
    lab = ForemanLab(tmp_path)
    root = lab.instantiate()
    activation = (
        lab.wiring().store.mint_activation(root.root_id, entry_request()).activation
    )
    activation = lab.wiring().store.record_dispatch(activation.activation_id, handle())
    lab.go_stale(activation.activation_id)
    monkeypatch.setattr(main_module, "_composition", lambda _: lab.composition)
    before_updates, before_closes = lab.count("update"), lab.count("close")

    byte_count, transcript = lab.transcript(
        lambda: main_module.main(["inspect", root.root_id, activation.activation_id])
    )
    report = json.loads(transcript)

    assert byte_count <= MAX_TRANSCRIPT_BYTES + lab.supervisor_config.log_tail_bytes
    assert "foreman-lab-sentinel" in report["tail"]
    assert report["tail_bytes"] <= lab.supervisor_config.log_tail_bytes
    assert lab.count("update") == before_updates
    assert lab.count("close") == before_closes
    assert (
        lab.store.reads.load_activation(activation.activation_id).metadata.lifecycle
        is Lifecycle.DISPATCHED
    )


def test_inspect_never_opens_a_healthy_runner_log(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """INSPECT preserves AUDIT-20's zero-log-byte premise for healthy work."""
    lab = ForemanLab(tmp_path)
    root = lab.instantiate()
    activation = (
        lab.wiring().store.mint_activation(root.root_id, entry_request()).activation
    )
    activation = lab.wiring().store.record_dispatch(activation.activation_id, handle())
    lab.wiring().paths.ensure_activation_dir(activation.activation_id)
    log_path = lab.wiring().paths.log(activation.activation_id)
    log_path.write_text("foreman-lab-sentinel", encoding="utf-8")
    monkeypatch.setattr(main_module, "_composition", lambda _: lab.composition)
    calls = 0
    path_type = type(log_path)
    original_open: Callable[..., Any] = path_type.open

    def track_open(path: Path, *args: object, **kwargs: object) -> Any:
        nonlocal calls
        if path == log_path:
            calls += 1
        return original_open(path, *args, **kwargs)

    monkeypatch.setattr(path_type, "open", track_open)
    _, transcript = lab.transcript(
        lambda: main_module.main(["inspect", root.root_id, activation.activation_id])
    )

    report = json.loads(transcript)
    assert report["tail"] == ""
    assert report["tail_bytes"] == 0
    assert "foreman-lab-sentinel" not in transcript
    assert calls == 0


def test_steer_preserves_session_round_and_its_bounded_tail(tmp_path: Path) -> None:
    """STEER catches a continuation that forks a session or loses its guidance."""
    instructions = "Finish the review with the recorded constraints."
    lab = ForemanLab(tmp_path)
    root = lab.instantiate()
    activation = (
        lab.wiring().store.mint_activation(root.root_id, entry_request()).activation
    )
    activation = lab.wiring().store.record_dispatch(activation.activation_id, handle())
    lab.go_stale(activation.activation_id, tail_bytes=b"\xff" * 4096)

    report = lab.steer(
        activation.activation_id,
        reason="silent past stale_after",
        instructions=instructions,
    )
    closed = lab.store.reads.load_activation(activation.activation_id)
    continuation = lab.store.reads.load_activation(report.continuation)
    repeated = lab.steer(
        activation.activation_id,
        reason="silent past stale_after",
        instructions=instructions,
    )

    assert report.tail_bytes == len(report.tail.encode("utf-8"))
    assert report.tail_bytes <= lab.supervisor_config.log_tail_bytes
    assert closed.metadata.lifecycle is Lifecycle.CLOSED
    assert closed.metadata.outcome is Outcome.STEERED
    assert len(closed.metadata.deviations) == 1
    assert closed.metadata.deviations[0].kind == "steer"
    assert closed.metadata.deviations[0].instructions_digest == instructions_digest(
        instructions
    )
    assert continuation.metadata.mint_reason is MintReason.STEER_CONTINUATION
    assert activation.metadata.handle is not None
    assert continuation.metadata.session_id == activation.metadata.handle.session_id
    assert continuation.metadata.round_no == activation.metadata.round_no
    assert repeated.continuation == continuation.activation_id
    assert len(lab.beads("activation")) == 2
    assert lab.tick().dispatched == continuation.activation_id
    assert (
        ExecLedger(lab.wiring().paths.ledger(continuation.activation_id)).count() == 1
    )
