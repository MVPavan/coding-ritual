"""D2 inspection and steering drills at the public foreman seam."""

from __future__ import annotations

import json
import time
from collections.abc import Callable
from dataclasses import replace
from multiprocessing.process import BaseProcess
from pathlib import Path
from typing import Any, Final, cast

import pytest

from tests._bdio import entry_request, handle
from tests._foreman import ForemanLab, InlineSpawner, LockedPersistentBd, ProcSpawner
from tests._helpers import VALID_FIXTURE, mutate, write
from tests._supervisor import ChildScript
from workflow_interpreter.bdio import Lifecycle, MintReason, Outcome, bounds, mint
from workflow_interpreter.foreman import __main__ as main_module
from workflow_interpreter.foreman.constants import MAX_TRANSCRIPT_BYTES
from workflow_interpreter.foreman.tick import Foreman
from workflow_interpreter.supervisor.errors import ContinuationRefused
from workflow_interpreter.supervisor.models import StaleFlag
from workflow_interpreter.supervisor.paths import ExecLedger, read_record
from workflow_interpreter.supervisor.procfs import (
    COMM_CLOSE,
    STAT_FILE,
    ZOMBIE_STATE,
)
from workflow_interpreter.supervisor.steer import instructions_digest

# Every test in this file is a §5 drill row (INSPECT and STEER).
pytestmark = pytest.mark.acceptance

# The (a) `proc` sub-case shortens the entry node's real `stale_after` so the
# wrapper's own monitor loop (not `go_stale`) raises the flag inside the test's
# patience. The clock is still `FrozenClock` — `sleep()` advances virtual time
# for free — so left alone the loop would race straight through `stale_after`
# AND the node's real `max_wall` (45m) in a real-time eyeblink, killing the
# child before the test ever gets to steer it. `_PROC_REAL_SLEEP_S` throttles
# each poll to a real delay (the pattern `test_a_stale_child_raises_the_flag_
# on_disk_and_in_bd` in test_supervisor_run.py uses), so `stale_after` is
# reached almost at once while `max_wall` stays real-world minutes away;
# `_PROC_SLEEP_S` only has to outlast detection, not `max_wall`.
_PROC_STALE_AFTER: Final[str] = "2s"
_PROC_STALE_AFTER_S: Final[float] = 2.0
_PROC_REAL_SLEEP_S: Final[float] = 0.05
_PROC_SLEEP_S: Final[float] = 6.0
_PROC_INSTRUCTIONS: Final[str] = "finish the review with the recorded constraints"
_PROC_ANCHOR: Final[str] = (
    'max_wall      = "45m"                    '
    "# universal runaway ceiling (wrapper-enforced)\n"
    'stale_after   = "10m"'
)


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


def test_steer_preserves_session_round_and_its_bounded_tail(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """STEER catches a continuation that forks a session or loses its guidance."""
    instructions = "Finish the review with the recorded constraints."
    lab = ForemanLab(tmp_path)
    root = lab.instantiate()
    # Minted with no session of its own: `prepare()` is the only minter of ids
    # and the dispatch is what makes it durable, so a continuation that copies
    # `metadata.session_id` has one to copy only because of that write
    # (cr-o85.34.9).
    activation = (
        lab.wiring()
        .store.mint_activation(root.root_id, entry_request(session_id=""))
        .activation
    )
    activation = lab.wiring().store.record_dispatch(activation.activation_id, handle())
    lab.go_stale(activation.activation_id, tail_bytes=b"\xff" * 4096)
    region = activation.metadata.region
    assert region is not None
    rounds_before = bounds.distinct_rounds(
        mint.views_of(lab.store.reads.list_activations(root.root_id)), region
    )
    log_bytes_full = lab.wiring().paths.log(activation.activation_id).read_bytes()

    report = lab.steer(
        activation.activation_id,
        reason="silent past stale_after",
        instructions=instructions,
    )
    closed = lab.store.reads.load_activation(activation.activation_id)
    continuation = lab.store.reads.load_activation(report.continuation)
    before_repeat_creates = lab.count("create")
    repeated = lab.steer(
        activation.activation_id,
        reason="silent past stale_after",
        instructions=instructions,
    )

    assert report.tail_bytes == len(report.tail.encode("utf-8"))
    assert report.tail_bytes <= lab.supervisor_config.log_tail_bytes
    leniently_decoded = log_bytes_full.decode("utf-8", errors="replace")
    assert leniently_decoded.endswith(report.tail)
    assert report.tail != "" and report.tail[-1] == leniently_decoded[-1]
    limit = lab.supervisor_config.log_tail_bytes
    survivors = limit // len("�".encode())
    assert report.tail_bytes < limit
    assert report.tail == "�" * survivors
    assert closed.metadata.lifecycle is Lifecycle.CLOSED
    assert closed.metadata.outcome is Outcome.STEERED
    assert len(closed.metadata.deviations) == 1
    assert closed.metadata.deviations[0].kind == "steer"
    assert closed.metadata.deviations[0].instructions_digest == instructions_digest(
        instructions
    )
    assert continuation.metadata.mint_reason is MintReason.STEER_CONTINUATION
    assert (
        sum(
            1
            for record in lab.store.reads.list_activations(root.root_id)
            if record.metadata.mint_reason is MintReason.STEER_CONTINUATION
        )
        == 1
    )
    assert activation.metadata.handle is not None
    assert continuation.metadata.session_id == activation.metadata.handle.session_id
    # The continuation COPIES `metadata.session_id` (tick.py), so the steered
    # activation must already carry the id `prepare()` produced at dispatch —
    # the mint carries none of its own (cr-o85.34.9).
    assert activation.metadata.session_id == activation.metadata.handle.session_id
    assert continuation.metadata.round_no == activation.metadata.round_no
    rounds_after = bounds.distinct_rounds(
        mint.views_of(lab.store.reads.list_activations(root.root_id)), region
    )
    assert rounds_after == rounds_before
    assert repeated.continuation == continuation.activation_id
    assert lab.count("create") == before_repeat_creates
    assert len(lab.beads("activation")) == 2

    monkeypatch.setattr(main_module, "_composition", lambda _: lab.composition)
    instructions_file = tmp_path / "instructions.txt"
    instructions_file.write_text(instructions, encoding="utf-8")
    byte_count, transcript = lab.transcript(
        lambda: main_module.main(
            [
                "steer",
                root.root_id,
                activation.activation_id,
                "--reason",
                "silent past stale_after",
                "--instructions-file",
                str(instructions_file),
            ]
        )
    )
    assert byte_count <= MAX_TRANSCRIPT_BYTES + lab.supervisor_config.log_tail_bytes
    assert transcript.count("foreman-lab-sentinel") <= 1

    assert lab.tick().dispatched == continuation.activation_id
    assert (
        ExecLedger(lab.wiring().paths.ledger(continuation.activation_id)).count() == 1
    )


def test_steer_refuses_a_sessionless_continuation_before_the_intent(
    tmp_path: Path,
) -> None:
    """STEER sub-case (c) refuses before writing anything with no session to rejoin."""
    lab = ForemanLab(tmp_path)
    root = lab.instantiate()
    activation = (
        lab.wiring()
        .store.mint_activation(root.root_id, entry_request(session_id=""))
        .activation
    )
    activation = lab.wiring().store.record_dispatch(
        activation.activation_id, handle(session_id="")
    )
    before_updates = lab.count("update")

    with pytest.raises(ContinuationRefused):
        lab.steer(
            activation.activation_id,
            reason="no session to rejoin",
            instructions="go",
        )

    reloaded = lab.store.reads.load_activation(activation.activation_id)
    assert reloaded.metadata.lifecycle is Lifecycle.DISPATCHED
    assert lab.count("update") == before_updates
    assert not lab.wiring().paths.steer_intent(activation.activation_id).exists()


def test_a_carried_steer_with_no_intent_burns_the_infra_budget_then_falls_back(
    tmp_path: Path,
) -> None:
    """cr-o85.19: the retry that carries a steer is BOUNDED like any other.

    With the intent file gone there is nothing to continue, so the continuation
    and every retry behind it are refused at the launch and closed
    `error_transport` with a `continuation_refused` deviation. That deviation is
    deliberately NOT exempt from the §10.2 count (`bounds._RETRY_EXEMPT_DEVIATIONS`):
    exempt, the instance would re-dispatch the same refusal forever. Instead the
    node spends `1 + max_infra_retries` attempts and the fallback gate opens.
    """
    lab = ForemanLab(tmp_path)
    root = lab.instantiate()
    activation = (
        lab.wiring()
        .store.mint_activation(root.root_id, entry_request(session_id=""))
        .activation
    )
    activation = lab.wiring().store.record_dispatch(activation.activation_id, handle())
    lab.go_stale(activation.activation_id)
    lab.steer(
        activation.activation_id,
        reason="silent past stale_after",
        instructions="finish the review with the recorded constraints",
    )
    lab.wiring().paths.steer_intent(activation.activation_id).unlink()

    budget = lab.store.reads.load_root(root.root_id).index.nodes["implement"]
    assert budget.max_infra_retries is not None
    attempts = [lab.tick().dispatched for _ in range(1 + budget.max_infra_retries)]
    opened = lab.tick().opened_gate

    refused = [
        record
        for record in lab.store.reads.list_activations(root.root_id)
        if record.activation_id in attempts
    ]
    assert [record.activation_id for record in refused] == attempts
    assert [record.metadata.mint_reason for record in refused] == [
        MintReason.STEER_CONTINUATION,
        *[MintReason.INFRA_RETRY] * budget.max_infra_retries,
    ]
    for record in refused:
        assert record.metadata.outcome is Outcome.ERROR_TRANSPORT
        assert [deviation.kind for deviation in record.metadata.deviations] == [
            "continuation_refused"
        ]
    assert opened is not None
    gate = lab.store.reads.load_gate(opened)
    assert gate.metadata.gate_node == root.definition.document.fallback.to
    assert gate.metadata.opening_outcome is Outcome.ERROR_TRANSPORT


def _proc_steer_lab(tmp_path: Path) -> tuple[ForemanLab, ProcSpawner]:
    """A lab whose entry node goes stale in seconds and whose spawner forks a
    real wrapper, with bd durable enough for the fork to mirror into it."""
    state = tmp_path / "persistent-bd.json"

    def persistent(workspace: str) -> LockedPersistentBd:
        return LockedPersistentBd(workspace, state)

    fixture = write(
        tmp_path,
        mutate(
            VALID_FIXTURE.read_text(encoding="utf-8"),
            [(_PROC_ANCHOR, _PROC_ANCHOR.replace('"10m"', f'"{_PROC_STALE_AFTER}"'))],
        ),
    )
    lab = ForemanLab(tmp_path, toml=fixture, bd_factory=persistent)
    lab.clock.real_sleep_s = _PROC_REAL_SLEEP_S
    spawner = ProcSpawner()
    lab.spawner = cast(InlineSpawner, spawner)
    lab.composition = replace(lab.composition, spawner=spawner)
    spawner.bind(lab.composition)
    lab.foreman = Foreman(lab.composition)
    return lab, spawner


def _runner_alive(pid: int) -> bool:
    """Whether the real forked runner is still RUNNING, zombies excluded.

    A zombie is dead by `prove_liveness`'s own rule (procfs.py:137-141) — it has
    exited and only its unreaped status remains — but it keeps its `/proc` entry
    until the forked wrapper's next `Monitor` cycle waitpids it. Asking bare path
    existence therefore made this a race with that reap rather than a question
    about the kill, and it flaked under load (cr-us7 follow-up). `/proc` is read
    directly rather than through `prove_liveness`, which would need a
    `SupervisorConfig` and the handle's boot id and start time to answer the same
    question this pid alone can answer.
    """
    try:
        stat = Path(f"/proc/{pid}/{STAT_FILE}").read_text(encoding="utf-8")
    except OSError:
        return False
    state = stat.rpartition(COMM_CLOSE)[2].split()
    return bool(state) and state[0] != ZOMBIE_STATE


@pytest.mark.proc
def test_steer_proc_raises_its_own_flag_and_kills_a_genuinely_live_child(
    tmp_path: Path,
) -> None:
    """STEER sub-case (a): nothing is faked. A real forked wrapper's own §8.2
    monitor loop (monitor.py:152-154) raises and mirrors the stale flag while
    the test process — playing the foreman, per the row — never ticks; the
    real runner child is still alive at that moment. `steer()` is then called
    from that separate foreman-side process and must actually kill the live
    child through the real `procfs.terminate` path, which sub-case (b)'s
    `dead_pid()` handle never exercises at all.
    """
    lab, spawner = _proc_steer_lab(tmp_path)
    root = lab.instantiate()
    lab.profiles.next_script(
        ChildScript(emit="steer-lab-proc-event\n", sleep_s=_PROC_SLEEP_S)
    )

    dispatched = lab.tick()
    activation_id = dispatched.dispatched
    assert activation_id is not None

    try:
        deadline = time.monotonic() + 20.0
        activation = lab.store.reads.load_activation(activation_id)
        while activation.metadata.stale_flag is None:
            if time.monotonic() > deadline:
                raise AssertionError(
                    "the wrapper's own monitor never mirrored a stale flag "
                    "into bd before the deadline"
                )
            time.sleep(0.05)
            activation = lab.store.reads.load_activation(activation_id)

        # (a)'s own contract, row-derived: "the flag raised and mirrored
        # WHILE NO FOREMAN RUNS" — true here structurally, since no tick()
        # has run between dispatch and this read.
        assert activation.metadata.lifecycle is Lifecycle.DISPATCHED
        # "so the WRAPPER's own monitor raises the flag ... and mirrored":
        # bd metadata carries it without any `go_stale` call in this test.
        assert activation.metadata.stale_flag is not None
        # The flag's own numbers came from the real graph node's `stale_after`
        # (2s here), not from `go_stale`'s hardcoded 60.0 — proof this is the
        # wrapper's own computed limit, not an injected one.
        on_disk = read_record(lab.wiring().paths.stale_flag(activation_id), StaleFlag)
        assert on_disk is not None
        assert on_disk.stale_after_s == _PROC_STALE_AFTER_S
        # "and the child is genuinely alive when the foreman arrives":
        assert activation.metadata.handle is not None
        runner_pid = activation.metadata.handle.pid
        assert _runner_alive(runner_pid)

        report = lab.steer(
            activation_id,
            reason="silent past stale_after",
            instructions=_PROC_INSTRUCTIONS,
        )
        # Checked BEFORE the barrier, deliberately: the child sleeps
        # `_PROC_SLEEP_S` and the barrier waits longer than that, so a
        # post-barrier liveness check is satisfied by the child timing out on
        # its own and cannot tell a real kill from a natural exit (probed:
        # steering a bogus pid survives the post-barrier form and fails this
        # one). `steer()` terminates with proof before it returns.
        assert not _runner_alive(runner_pid)

        # The row's own post-conditions, reached through THIS live-child
        # injection rather than (b)'s dead_pid() one: (b)'s handle is already
        # dead when `steer()` runs, so its close+mint never has to survive a
        # real signal-and-prove termination first. That ordering is exactly
        # what (a) is for, so these are asserted here too, not skipped as a
        # duplicate of (b).
        closed = lab.store.reads.load_activation(activation_id)
        continuation = lab.store.reads.load_activation(report.continuation)
        assert closed.metadata.outcome is Outcome.STEERED
        assert closed.metadata.lifecycle is Lifecycle.CLOSED
        assert len(closed.metadata.deviations) == 1
        assert closed.metadata.deviations[0].kind == "steer"
        assert closed.metadata.deviations[0].instructions_digest == instructions_digest(
            _PROC_INSTRUCTIONS
        )
        assert continuation.metadata.mint_reason is MintReason.STEER_CONTINUATION
        assert (
            sum(
                1
                for record in lab.store.reads.list_activations(root.root_id)
                if record.metadata.mint_reason is MintReason.STEER_CONTINUATION
            )
            == 1
        )
        assert continuation.metadata.session_id == activation.metadata.handle.session_id
        assert continuation.metadata.round_no == activation.metadata.round_no

        spawner.await_barrier(lab.wiring(), activation_id, timeout_s=15.0)
        # The real child that was alive above is now genuinely dead: `steer()`
        # went through the real `procfs.terminate` signal-and-prove path, not
        # sub-case (b)'s already-dead handle.
        assert not _runner_alive(runner_pid)
    finally:
        for process in cast(list[BaseProcess], spawner.processes):
            if process.is_alive():
                process.kill()
                process.join(timeout=5)
