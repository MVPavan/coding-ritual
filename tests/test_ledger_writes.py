"""What the ledger's WRITE side guarantees: atomicity, concurrency, projections.

The store CONTRACT (what every backend must do) lives in
`tests/test_store_contract.py` and runs whole on a ledger lab. What is here is
what only the ledger can be asked: that a gate close lands its nonce, its
signature and its projection in ONE transaction; that the facts survive a
close and a reopen; that real concurrent processes neither lose a row nor
reuse a `seq`; that a writer which waits out `busy_timeout` REFUSES; and that
the attention label converges on what the ledger says, after a crash at either
logical fault point and under two roots racing one reconciler.

Only the multiprocess case forks (`proc`); everything else is a small test
over `tmp_path`.
"""

from __future__ import annotations

import json
import sqlite3
import subprocess
import sys
import time
from collections.abc import Callable, Iterator
from datetime import UTC, datetime
from pathlib import Path
from typing import Final

import pytest

from tests._bdio import entry_request, handle, load_definition, make_root
from tests._fake_bd import FakeBd
from tests._gates import approval_payload, close, ship_gate_request
from tests._ledger import (
    TASK,
    CrashingLedgerStore,
    FaultPoint,
    InjectedLedgerCrash,
    config_file,
    ledger_store,
    repository,
)
from tests.conftest import FAKE_WORKSPACE, TEST_ACTOR, Signer, branch_head
from workflow_interpreter.bdio import transitions
from workflow_interpreter.bdio.api import WorkflowStore
from workflow_interpreter.bdio.backend import PinnedBackendFactory
from workflow_interpreter.bdio.client import BdClient
from workflow_interpreter.bdio.config import BdConfig, SigningConfig
from workflow_interpreter.bdio.errors import (
    CarrierIntegrityError,
    LifecycleConflictError,
)
from workflow_interpreter.bdio.rows import RowGuard, StoreRow
from workflow_interpreter.bdio.signing import GateVerifier
from workflow_interpreter.bdio.wire import (
    EventPayload,
    Evidence,
    ExitRecord,
    GateState,
    Lifecycle,
    Metadata,
)
from workflow_interpreter.ledger.__main__ import main as ledger_main
from workflow_interpreter.ledger.constants import ExportKey, LedgerTable
from workflow_interpreter.ledger.database import LedgerDatabase, connect, open_ledger
from workflow_interpreter.ledger.errors import LedgerBusyRefusal, LedgerFenceBusy
from workflow_interpreter.ledger.export import import_export, write_export
from workflow_interpreter.ledger.fence import LedgerFence
from workflow_interpreter.ledger.paths import export_path, ledger_path
from workflow_interpreter.ledger.reconcile import (
    ATTENTION_LABEL,
    AttentionReconciler,
    task_lock_path,
)
from workflow_interpreter.ledger.store import LedgerStore
from workflow_interpreter.schema.models import Outcome

TERMINAL: Final[str] = "shipped"
ABANDONED: Final[str] = "abandoned"
STATUS_OPEN: Final[str] = "open"
STATUS_CLOSED: Final[str] = "closed"
BUSY_TIMEOUT_MS: Final[int] = 50
"""The production wait is 5000 ms (§3.4.1). The refusal is the same code path
at any bound, so the test shortens it rather than spending five seconds
proving that a bounded wait is bounded."""
BUSY_CEILING_S: Final[float] = 2.0
"""A silent retry loop would blow past this; one bounded wait cannot."""
LOCK_WAIT_S: Final[float] = 0.2
CHILDREN: Final[int] = 4
CHILD_TIMEOUT_S: Final[float] = 60.0
EXIT_RECORD: Final[ExitRecord] = ExitRecord(
    exit_code=0, ended_at="2026-09-16T00:01:00Z", reason="ok"
)

_CHILD_SCRIPT: Final[str] = """
import sys
from pathlib import Path

sys.path.insert(0, sys.argv[1])

from tests._ledger import ledger_store
from workflow_interpreter.bdio.wire import EventPayload
from workflow_interpreter.ledger.database import open_ledger
from workflow_interpreter.schema.models import Outcome

repo_root, wrapper_root, root_id, ordinal = sys.argv[2:6]
with open_ledger(Path(repo_root), Path(wrapper_root)) as database:
    store = ledger_store(database)
    store.append_event(
        root_id,
        EventPayload(
            **{"from": "implement"},
            outcome=Outcome.DONE,
            to="review-" + ordinal,
            activation_id=root_id + ".child." + ordinal,
            seq=int(ordinal),
            actor="child-" + ordinal,
            origin="activation",
        ),
    )
"""
"""One child writing one event of its own into the SHARED ledger, through the
same public path the driver uses — a real process, a real WAL, a real
`busy_timeout`."""

_CLOSE_SCRIPT: Final[str] = """
import sys
import time
from pathlib import Path

sys.path.insert(0, sys.argv[1])

from tests._ledger import ledger_backend
from workflow_interpreter.bdio.rows import GateClosure, GateSignature
from workflow_interpreter.ledger.database import open_ledger
from workflow_interpreter.ledger.errors import LedgerGateConflict

repo_root, wrapper_root, gate_id, ordinal, barrier = sys.argv[2:7]
mark = "-" + ordinal
closure = GateClosure(
    gate_id=gate_id,
    metadata={
        "state": "closed",
        "outcome": "approve",
        "nonce": "nonce" + mark,
        "payload_digest": "digest" + mark,
        "verified_fingerprint": "SHA256:fingerprint" + mark,
    },
    close_reason="outcome=approve",
    nonce="nonce" + mark,
    signature=GateSignature(
        payload_bytes=("payload" + mark).encode("utf-8"),
        signature_bytes=("signature" + mark).encode("utf-8"),
        signer_fingerprint="SHA256:fingerprint" + mark,
        allowed_signers_entry="entry" + mark,
        policy={"namespace": "wf"},
    ),
)
with open_ledger(Path(repo_root), Path(wrapper_root)) as database:
    backend = ledger_backend(database)
    while not Path(barrier).exists():
        time.sleep(0.01)
    try:
        backend._close_gate(closure)
    except LedgerGateConflict:
        raise SystemExit(3)
"""
"""One process taking one gate's decision, released by a shared barrier file.
Two of them race the SAME gate with two different approvals, which is the race
the §3.3 gate close has to decide inside its transaction."""


@pytest.fixture
def ledger(tmp_path: Path) -> Iterator[LedgerDatabase]:
    """An open ledger over a fresh repository, closed with the test."""
    repo_root, wrapper_root = repository(tmp_path)
    with open_ledger(repo_root, wrapper_root) as database:
        yield database


@pytest.fixture
def bd_labels() -> FakeBd:
    """An in-memory bd workspace the projection is written onto."""
    return FakeBd(str(FAKE_WORKSPACE))


@pytest.fixture
def label_client(bd_labels: FakeBd) -> BdClient:
    """The real bd transport, driving the in-memory workspace."""
    return BdClient(BdConfig(workspace=FAKE_WORKSPACE, actor=TEST_ACTOR), bd_labels)


def _task_bead(bd_labels: FakeBd, task_id: str = TASK) -> str:
    """The task bead a projection is reconciled onto."""
    bd_labels.rows[task_id] = {
        "id": task_id,
        "title": "task",
        "status": STATUS_OPEN,
        "issue_type": "task",
        "metadata": {},
        "payload": None,
        "close_reason": None,
        "labels": [],
    }
    return task_id


def _labels(bd_labels: FakeBd, task_id: str = TASK) -> list[str]:
    """The labels bd currently holds for the task bead."""
    return list(bd_labels.rows[task_id]["labels"])


def _open_gate(store: WorkflowStore) -> tuple[str, str]:
    """A fresh instance of the task with its `ship` gate OPEN."""
    root = make_root(store, load_definition())
    source = store.mint_activation(root.root_id, entry_request()).activation
    gate = store.open_gate(root.root_id, ship_gate_request(source.activation_id))
    return root.root_id, gate.gate_id


def _rows(
    database: LedgerDatabase, statement: str, *values: object
) -> list[sqlite3.Row]:
    """One bound query against the ledger, for the assertions below."""
    return list(database.connection.execute(statement, values).fetchall())


def _unacked(database: LedgerDatabase, task_id: str = TASK) -> list[int]:
    """Every generation this task still owes the reconciler."""
    return [
        int(row["generation"])
        for row in _rows(
            database,
            "SELECT generation FROM projections WHERE task_id = ? "
            "AND acked_at IS NULL ORDER BY generation",
            task_id,
        )
    ]


# --- durability across a reopen --------------------------------------------


def test_a_reopened_ledger_answers_exactly_what_the_closed_one_wrote(
    tmp_path: Path,
) -> None:
    """§3.5: the facts are the database's, not the process's.

    Written through the public path, read back through a SECOND connection
    after the first was closed — which is the only way to tell a committed
    transaction from a cached one.
    """
    repo_root, wrapper_root = repository(tmp_path)
    with open_ledger(repo_root, wrapper_root) as database:
        store = ledger_store(database)
        root = make_root(store, load_definition())
        activation = store.mint_activation(root.root_id, entry_request()).activation
        store.record_dispatch(activation.activation_id, handle())
        store.record_exit(activation.activation_id, EXIT_RECORD)
        closed = store.close_activation(activation.activation_id, Outcome.DONE)
        settled = store.settle_root(root.root_id, TERMINAL)

    with open_ledger(repo_root, wrapper_root) as reopened:
        reread = ledger_store(reopened).reads
        again = reread.load_activation(activation.activation_id)
        assert (again.status, again.close_reason) == (STATUS_CLOSED, "outcome=done")
        assert again.metadata.lifecycle is Lifecycle.CLOSED
        assert again.metadata.outcome is closed.metadata.outcome
        root_again = reread.load_root(root.root_id)
        assert root_again.metadata.terminal == settled.metadata.terminal
        assert root_again.status == STATUS_CLOSED
        assert (
            _rows(
                reopened,
                "SELECT terminal_at FROM roots WHERE root_id = ?",
                root.root_id,
            )[0]["terminal_at"]
            is not None
        )


# --- the atomic operations of §3.3 -----------------------------------------


def test_a_gate_close_lands_nonce_signature_and_projection_in_one_transaction(
    ledger: LedgerDatabase, signing_config: SigningConfig, sign_payload: Signer
) -> None:
    """§3.3: the decision is one write — every part of it, or none.

    The signature is verified OUTSIDE the transaction (it is a subprocess, and
    §3.4.2 forbids one inside), and what lands is the decision: the consumed
    nonce, the closed state and outcome, the historical trust §3.6 re-verifies
    from, and the projection that tells the reconciler to retire the label.
    """
    verifier = GateVerifier(signing_config, ledger.repo_root)
    store = ledger_store(ledger, verifier=verifier)
    root_id, gate_id = _open_gate(store)
    gate = store.reads.load_gate(gate_id)
    approval = approval_payload(root_id, gate)

    closed = close(store, root_id, gate, approval, sign_payload)

    assert closed.metadata.state is GateState.CLOSED
    assert closed.metadata.outcome is Outcome.APPROVE
    row = _rows(ledger, "SELECT * FROM gates WHERE gate_id = ?", gate_id)[0]
    assert (row["state"], row["outcome"]) == (GateState.CLOSED.value, "approve")
    assert (row["status"], row["version"]) == (STATUS_CLOSED, 2)
    assert row["nonce"] == approval.nonce
    nonce = _rows(ledger, "SELECT * FROM nonces WHERE nonce = ?", approval.nonce)[0]
    assert nonce["gate_id"] == gate_id
    signature = _rows(ledger, "SELECT * FROM signatures WHERE gate_id = ?", gate_id)[0]
    assert json.loads(signature["payload_bytes"])["nonce"] == approval.nonce
    assert signature["signature_bytes"]
    assert signature["signer_fingerprint"] == closed.metadata.verified_fingerprint
    assert signature["signer_fingerprint"] in signature["allowed_signers_entry"]
    assert json.loads(signature["policy_json"])["namespace"] == (
        signing_config.namespace
    )
    # One generation for the open, one for the close: both predicate changes.
    assert _unacked(ledger) == [
        int(row["generation"])
        for row in _rows(
            ledger, "SELECT generation FROM projections ORDER BY generation"
        )
    ]
    assert len(_unacked(ledger)) == 2


@pytest.mark.proc
def test_two_processes_closing_one_gate_leave_exactly_one_whole_decision(
    tmp_path: Path,
) -> None:
    """§3.3: the gate close DECIDES, inside the transaction that takes it.

    Two approvals reach one gate having both read it OPEN — the real shape,
    because verification happens outside the transaction. Whichever `BEGIN
    IMMEDIATE` commits first owns the gate; the loser writes nothing at all.
    Before this, the loser's carrier overwrote the winner's outcome while the
    nonce and signature inserts silently kept the winner's rows, leaving one
    gate whose decision and whose stored trust came from two approvals.
    """
    repo_root, wrapper_root = repository(tmp_path)
    with open_ledger(repo_root, wrapper_root) as database:
        _, gate_id = _open_gate(ledger_store(database))
    barrier = tmp_path / "start"

    project_root = str(Path(__file__).resolve().parents[1])
    racers = [
        subprocess.Popen(
            (
                sys.executable,
                "-c",
                _CLOSE_SCRIPT,
                project_root,
                str(repo_root),
                str(wrapper_root),
                gate_id,
                str(ordinal),
                str(barrier),
            ),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        for ordinal in (1, 2)
    ]
    barrier.write_text("go", encoding="utf-8")
    outcomes = []
    for racer in racers:
        _, stderr = racer.communicate(timeout=CHILD_TIMEOUT_S)
        outcomes.append((racer.returncode, stderr))

    codes = sorted(code for code, _ in outcomes)
    assert codes == [0, 3], outcomes
    with open_ledger(repo_root, wrapper_root) as reopened:
        gate = _rows(reopened, "SELECT * FROM gates WHERE gate_id = ?", gate_id)[0]
        winner = str(gate["nonce"])
        nonces = _rows(reopened, "SELECT * FROM nonces")
        signatures = _rows(reopened, "SELECT * FROM signatures")

    assert [str(row["nonce"]) for row in nonces] == [winner]
    assert len(signatures) == 1
    mark = winner.removeprefix("nonce")
    # One decision, whole: the carrier, the nonce and the stored trust are all
    # the winner's, and nothing of the loser's is anywhere.
    assert json.loads(gate["metadata_json"])["payload_digest"] == f"digest{mark}"
    assert signatures[0]["signer_fingerprint"] == f"SHA256:fingerprint{mark}"
    assert signatures[0]["allowed_signers_entry"] == f"entry{mark}"
    assert gate["state"] == GateState.CLOSED.value


def test_a_settlement_that_loses_the_race_never_rewrites_the_recorded_terminal(
    ledger: LedgerDatabase,
) -> None:
    """§3.1: the end an instance reached is routing truth, and it is written once.

    `settle_root` checks the recorded terminal against a read taken before its
    write, so two settlements that both saw it unset both passed that check and
    the later one rewrote the end of the instance. The guard runs INSIDE the
    writing transaction now, against the row being changed, so the settlement
    that lands second is refused and the first terminal stands.
    """
    store = ledger_store(ledger)
    root = make_root(store, load_definition())

    def rival() -> None:
        """Another process settles this root, on its own connection, first."""
        with open_ledger(ledger.repo_root, ledger.wrapper_root) as other:
            ledger_store(other).settle_root(root.root_id, ABANDONED)

    raced = WorkflowStore(
        _RacedLedgerStore(ledger, task_id=TASK, rival=rival),
        branch_head_reader=branch_head,
    )

    with pytest.raises(CarrierIntegrityError) as refusal:
        raced.settle_root(root.root_id, TERMINAL)

    assert ABANDONED in str(refusal.value)
    row = _rows(ledger, "SELECT * FROM roots WHERE root_id = ?", root.root_id)[0]
    assert row["terminal"] == ABANDONED
    assert store.reads.load_root(root.root_id).metadata.terminal == ABANDONED


class _RacedLedgerStore(LedgerStore):
    """A store whose rival settlement commits between the check and the write.

    The interleaving is the one `settle_root` cannot otherwise be asked for:
    its own guard read runs before the transaction, so the only way to prove
    the IN-transaction guard is to make another connection's settlement land in
    exactly that window. The rival commits on its own connection before this
    store's transaction begins, which is where a second process's settlement
    would land.
    """

    def __init__(
        self, database: LedgerDatabase, *, task_id: str, rival: Callable[[], None]
    ) -> None:
        super().__init__(database, task_id=task_id)
        self._rival: Callable[[], None] | None = rival

    def _merge_metadata(
        self, row_id: str, metadata: Metadata, *, guard: RowGuard | None = None
    ) -> StoreRow:
        """Let the rival settle once, then take this store's own transaction."""
        rival, self._rival = self._rival, None
        if rival is not None:
            rival()
        return super()._merge_metadata(row_id, metadata, guard=guard)


def test_a_settlement_stamps_the_terminal_and_enqueues_its_projection(
    ledger: LedgerDatabase,
) -> None:
    """§3.3: settlement is the write that can retire a task's attention."""
    store = ledger_store(ledger)
    root = make_root(store, load_definition())
    before = _unacked(ledger)

    store.settle_root(root.root_id, TERMINAL)

    row = _rows(ledger, "SELECT * FROM roots WHERE root_id = ?", root.root_id)[0]
    assert row["terminal"] == TERMINAL
    assert row["terminal_at"] is not None
    assert row["status"] == STATUS_CLOSED
    assert len(_unacked(ledger)) > len(before)


def test_a_late_supervisor_write_loses_to_the_steer_that_closed_the_activation(
    ledger: LedgerDatabase,
) -> None:
    """§3.3: the transition reads, checks and writes in ONE transaction.

    The interleaving is real and not hypothetical: the supervisor is resident
    and writes evidence concurrently with foreman ticks (`transitions.py`), so
    a steer can close the activation after the supervisor read it. Modelled by
    handing the transition a loader that answers the record as it stood BEFORE
    the steer — so every check outside the transaction passes, and only the
    guard that re-reads inside it can refuse.
    """
    backend = LedgerStore(ledger, task_id=TASK)
    store = ledger_store(ledger)
    root = make_root(store, load_definition())
    activation = store.mint_activation(root.root_id, entry_request()).activation
    store.record_dispatch(activation.activation_id, handle())
    stale = store.record_exit(activation.activation_id, EXIT_RECORD)
    steered = store.close_activation(activation.activation_id, Outcome.STEERED)
    version = _version(ledger, activation.activation_id)

    with pytest.raises(LifecycleConflictError):
        transitions.apply(
            backend,
            lambda _activation_id: stale,
            activation.activation_id,
            lifecycle=Lifecycle.EVIDENCE_RECORDED,
            allowed=frozenset({Lifecycle.EXIT_RECORDED}),
            evidence=Evidence(note="late"),
        )

    reread = store.reads.load_activation(activation.activation_id)
    assert reread.metadata.outcome is steered.metadata.outcome
    assert reread.metadata.lifecycle is Lifecycle.CLOSED
    assert reread.metadata.evidence is None
    assert _version(ledger, activation.activation_id) == version


def _version(database: LedgerDatabase, activation_id: str) -> int:
    """The row version §3.3 moves with every merge."""
    return int(
        _rows(
            database,
            "SELECT version FROM activations WHERE activation_id = ?",
            activation_id,
        )[0]["version"]
    )


# --- concurrency (§3.4) -----------------------------------------------------


@pytest.mark.proc
def test_concurrent_child_processes_neither_lose_a_row_nor_reuse_a_seq(
    tmp_path: Path,
) -> None:
    """§3.4.1: one connection per process, WAL, and a bounded wait per writer.

    Real subprocesses, because that is the only way the pragmas and the file
    lock are actually exercised: threads in one process share a connection and
    would prove nothing about two drivers.
    """
    repo_root, wrapper_root = repository(tmp_path)
    with open_ledger(repo_root, wrapper_root) as database:
        root = make_root(ledger_store(database), load_definition())

    project_root = str(Path(__file__).resolve().parents[1])
    children = [
        subprocess.Popen(
            (
                sys.executable,
                "-c",
                _CHILD_SCRIPT,
                project_root,
                str(repo_root),
                str(wrapper_root),
                root.root_id,
                str(ordinal),
            ),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        for ordinal in range(1, CHILDREN + 1)
    ]
    for child in children:
        _, stderr = child.communicate(timeout=CHILD_TIMEOUT_S)
        assert child.returncode == 0, stderr

    with open_ledger(repo_root, wrapper_root) as reopened:
        events = _rows(reopened, "SELECT event_id, seq FROM events ORDER BY seq")
        assert len(events) == CHILDREN
        seqs = [int(row["seq"]) for row in events]
        assert len(set(seqs)) == CHILDREN
        assert len({str(row["event_id"]) for row in events}) == CHILDREN


def test_a_writer_that_waits_out_the_busy_timeout_refuses_rather_than_retrying(
    ledger: LedgerDatabase,
) -> None:
    """§3.4.6: busy beyond the timeout is a RECORDED refusal, never a loop."""
    store = ledger_store(ledger)
    root = make_root(store, load_definition())
    ledger.connection.execute(f"PRAGMA busy_timeout={BUSY_TIMEOUT_MS}")
    blocker = connect(ledger_path(ledger.repo_root))
    blocker.execute(f"PRAGMA busy_timeout={BUSY_TIMEOUT_MS}")
    blocker.execute("BEGIN IMMEDIATE")
    started = time.monotonic()
    try:
        with pytest.raises(LedgerBusyRefusal) as refusal:
            store.settle_root(root.root_id, TERMINAL)
    finally:
        blocker.execute("ROLLBACK")
        blocker.close()

    assert time.monotonic() - started < BUSY_CEILING_S
    assert "§3.4.6" in str(refusal.value)
    assert refusal.value.operation
    assert store.reads.load_root(root.root_id).metadata.terminal is None


def test_a_second_drain_of_one_task_refuses_on_the_task_lock_naming_the_holder(
    ledger: LedgerDatabase, label_client: BdClient, bd_labels: FakeBd
) -> None:
    """§3.2.2: the reconcile lock is task-keyed, and its wait is bounded."""
    _task_bead(bd_labels)
    store = ledger_store(ledger)
    _open_gate(store)
    reconciler = AttentionReconciler(ledger, label_client, lock_wait_s=LOCK_WAIT_S)
    lock = task_lock_path(ledger.wrapper_root, TASK)

    with LedgerFence(lock).exclusive(), pytest.raises(LedgerFenceBusy) as refusal:
        reconciler.drain(TASK)

    assert str(lock) in str(refusal.value)
    # The drain that could not run acked nothing; the work is still owed.
    assert _unacked(ledger)
    assert _labels(bd_labels) == []


# --- the attention projection (§3.2) ---------------------------------------


def test_the_reconciler_writes_the_label_the_ledger_implies_and_then_acks(
    ledger: LedgerDatabase,
    label_client: BdClient,
    bd_labels: FakeBd,
    signing_config: SigningConfig,
    sign_payload: Signer,
) -> None:
    """The label is a function of ledger state, applied under the task lock."""
    _task_bead(bd_labels)
    verifier = GateVerifier(signing_config, ledger.repo_root)
    store = ledger_store(ledger, verifier=verifier)
    root_id, gate_id = _open_gate(store)
    reconciler = AttentionReconciler(ledger, label_client)

    opened = reconciler.drain(TASK)
    assert (opened.wanted, opened.written) == (True, True)
    assert _labels(bd_labels) == [ATTENTION_LABEL]
    assert _unacked(ledger) == []

    gate = store.reads.load_gate(gate_id)
    close(store, root_id, gate, approval_payload(root_id, gate), sign_payload)
    closed = reconciler.drain(TASK)

    assert closed.wanted is False
    assert _labels(bd_labels) == []
    assert _unacked(ledger) == []


def test_a_gate_under_a_settled_root_no_longer_asks_for_attention(
    ledger: LedgerDatabase, label_client: BdClient, bd_labels: FakeBd
) -> None:
    """§3.2: the predicate is over the task's NON-TERMINAL roots."""
    _task_bead(bd_labels)
    store = ledger_store(ledger)
    root_id, _ = _open_gate(store)
    reconciler = AttentionReconciler(ledger, label_client)
    reconciler.drain(TASK)
    assert _labels(bd_labels) == [ATTENTION_LABEL]

    store.settle_root(root_id, TERMINAL)
    reconciler.drain(TASK)

    assert _labels(bd_labels) == []


@pytest.mark.parametrize("point", list(FaultPoint))
def test_a_crash_at_a_fault_point_leaves_a_projection_the_next_drain_repairs(
    ledger: LedgerDatabase, label_client: BdClient, bd_labels: FakeBd, point: FaultPoint
) -> None:
    """§3.2.4: a crash anywhere leaves unacked rows, and replay is idempotent.

    Both points are armed against the SAME operation — opening a gate — so the
    difference tested is where the process died relative to the commit, which
    is the only thing the fault points name. Either way the state and its
    journal row landed together, so the next drain converges the label.
    """
    _task_bead(bd_labels)
    backend = CrashingLedgerStore(ledger, task_id=TASK)
    store = WorkflowStore(
        backend,
        backend_factory=PinnedBackendFactory(backend),
        branch_head_reader=branch_head,
    )
    root = make_root(store, load_definition())
    source = store.mint_activation(root.root_id, entry_request()).activation
    if point is FaultPoint.AFTER_STATE_COMMIT:
        gate = store.open_gate(root.root_id, ship_gate_request(source.activation_id))
        backend.arm(point)
        with pytest.raises(InjectedLedgerCrash):
            # The gate's state is committed; the process dies before the close
            # that would settle the row.
            backend._close_row(gate.gate_id, "outcome=approve")
    else:
        backend.arm(point)
        with pytest.raises(InjectedLedgerCrash):
            store.open_gate(root.root_id, ship_gate_request(source.activation_id))

    assert _unacked(ledger)
    assert _labels(bd_labels) == []

    result = AttentionReconciler(ledger, label_client).drain(TASK)

    assert result.wanted is True
    assert _labels(bd_labels) == [ATTENTION_LABEL]
    assert _unacked(ledger) == []


def test_two_roots_racing_one_reconciler_lose_no_update(
    ledger: LedgerDatabase, label_client: BdClient, bd_labels: FakeBd
) -> None:
    """D6: an ack covers only the generation whose state was actually read.

    The race, exactly: one root's gate opens while the OTHER root's drain is
    between its recompute and its ack. If the ack covered that later
    generation, the label would stay absent forever with nothing left to
    notice. Instead the new generation stays unacked, and the next drain
    writes what the ledger says.
    """
    _task_bead(bd_labels)
    store = ledger_store(ledger)
    first_root, _ = _open_gate(store)
    store.settle_root(first_root, TERMINAL)
    second = ledger_store(ledger)
    reconciler = AttentionReconciler(ledger, label_client)

    interleaved: list[str] = []
    original = label_client._remove_label

    def open_the_other_roots_gate(bead_id: str, label: str) -> object:
        """A second root opens a gate exactly during the first root's write."""
        label_client._remove_label = original
        interleaved.append(_open_gate(second)[1])
        return original(bead_id, label)

    label_client._remove_label = open_the_other_roots_gate  # type: ignore[method-assign]

    first = reconciler.drain(TASK)

    assert (first.wanted, _labels(bd_labels)) == (False, [])
    assert interleaved
    # The generation the second root enqueued was NOT acked by a drain that
    # never read it.
    assert _unacked(ledger)

    second_drain = reconciler.drain(TASK)

    assert second_drain.wanted is True
    assert _labels(bd_labels) == [ATTENTION_LABEL]
    assert _unacked(ledger) == []
    assert AttentionReconciler(ledger, label_client).wanted(TASK) is True


# --- what the export carries out of the write side (§3.6) -------------------


def test_the_export_carries_the_nonces_signatures_and_projections_a_task_owns(
    tmp_path: Path, signing_config: SigningConfig, sign_payload: Signer
) -> None:
    """§3.6: an approval is re-verifiable from the export ALONE (D21).

    The three task-owned auxiliary tables used to be left out, so a restored
    ledger had no signature to re-verify, no spent nonce to refuse a replay
    with, and no record that its attention was owed. They round trip with
    everything else, byte for byte.
    """
    repo_root, wrapper_root = repository(tmp_path)
    with open_ledger(repo_root, wrapper_root) as database:
        verifier = GateVerifier(signing_config, database.repo_root)
        store = ledger_store(database, verifier=verifier)
        root_id, gate_id = _open_gate(store)
        gate = store.reads.load_gate(gate_id)
        close(store, root_id, gate, approval_payload(root_id, gate), sign_payload)
        first = write_export(database, TASK).read_bytes()

    tables = [
        json.loads(line)[ExportKey.TABLE.value] for line in first.splitlines()[1:]
    ]
    assert {
        LedgerTable.NONCES.value,
        LedgerTable.SIGNATURES.value,
        LedgerTable.PROJECTIONS.value,
    } <= set(tables)

    import_export(
        export_path(repo_root, TASK),
        repo_root=repo_root,
        wrapper_root=wrapper_root,
        ledger=ledger_path(repo_root),
    )

    with open_ledger(repo_root, wrapper_root) as reopened:
        assert write_export(reopened, TASK).read_bytes() == first
        assert _rows(reopened, "SELECT * FROM signatures WHERE gate_id = ?", gate_id)


def test_an_imported_task_owes_exactly_one_new_attention_reconciliation(
    tmp_path: Path, label_client: BdClient, bd_labels: FakeBd
) -> None:
    """§3.2: a restored task's label was written from state that is now gone.

    The drain before the export left nothing owed, so the label on the bead
    agreed with the ledger. After a rebuild it agrees with nothing, and the
    import enqueues the one generation that makes the next drain re-derive it.
    """
    _task_bead(bd_labels)
    repo_root, wrapper_root = repository(tmp_path)
    with open_ledger(repo_root, wrapper_root) as database:
        _open_gate(ledger_store(database))
        AttentionReconciler(database, label_client).drain(TASK)
        assert _unacked(database) == []
        before = [
            int(row["generation"])
            for row in _rows(database, "SELECT generation FROM projections")
        ]
        write_export(database, TASK)

    import_export(
        export_path(repo_root, TASK),
        repo_root=repo_root,
        wrapper_root=wrapper_root,
        ledger=ledger_path(repo_root),
    )

    with open_ledger(repo_root, wrapper_root) as reopened:
        owed = _unacked(reopened)
        assert len(owed) == 1
        assert owed[0] not in before
        assert AttentionReconciler(reopened, label_client).drain(TASK).written is True


# --- the trace's own timestamps (§3.3) --------------------------------------


def test_an_appended_event_is_stamped_with_the_instant_it_was_written(
    ledger: LedgerDatabase,
) -> None:
    """§3.3: `events.at` is the moment the fact was appended, not NULL."""
    store = ledger_store(ledger)
    root = make_root(store, load_definition())

    store.append_event(root.root_id, _event_payload(root.root_id))

    stamps = [row["at"] for row in _rows(ledger, "SELECT at FROM events")]
    assert stamps and all(stamp is not None for stamp in stamps)
    assert all(datetime.fromisoformat(str(stamp)).tzinfo is UTC for stamp in stamps)


def _event_payload(root_id: str) -> EventPayload:
    """One routing event of this instance, as the driver appends it."""
    return EventPayload(
        **{"from": "implement"},
        outcome=Outcome.DONE,
        to="review",
        activation_id=f"{root_id}.implement.r1.1",
        seq=1,
        actor=TEST_ACTOR,
        origin="activation",
    )


# --- the CLI (§3.2.4) -------------------------------------------------------


@pytest.mark.bd
def test_the_reconcile_cli_drains_unacked_rows_onto_a_real_bead(
    tmp_path: Path, bd_workspace: Path
) -> None:
    """`wf ledger reconcile <task>` against REAL bd — the label ops included.

    The one addition to bd's closed subcommand argument set (§3.2.3) is
    exercised end to end here: the CLI builds the client, the reconciler
    writes `--add-label`, and the transport reads the bead back. A fake would
    not tell us whether bd accepts the flag.
    """
    config_path, repo_root, wrapper_root = config_file(tmp_path, bd_workspace)
    client = BdClient(BdConfig(workspace=bd_workspace, actor=TEST_ACTOR))
    task_id = client._create_bead(title="ledger task", metadata={}).id
    with open_ledger(repo_root, wrapper_root) as database:
        _open_gate(ledger_store(database, task_id))
        assert _unacked(database, task_id)

    assert ledger_main(["--config", str(config_path), "reconcile", task_id]) == 0

    assert ATTENTION_LABEL in client.show(task_id).labels
    with open_ledger(repo_root, wrapper_root) as reopened:
        assert _unacked(reopened, task_id) == []
