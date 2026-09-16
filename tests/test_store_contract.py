"""The store contract — what every backend must do, whichever one is pinned.

Parameterised by a BACKEND FACTORY rather than by a transport: each case runs
against the in-memory transport and against a real bd workspace, and neither
variant names a bd command. Faults are named by what they mean — the state
committed and the process died before its follow-up write; the write landed
and its read-back never returned — so the same case will run against the
ledger backend in S1/S2 without being rewritten.

A backend that cannot inject a fault skips those cases loudly rather than
passing them vacuously: real bd has no crash hook, and a green fault case on a
store that could not have crashed would prove nothing.
"""

from __future__ import annotations

from collections.abc import Iterator
from enum import StrEnum
from typing import Final

import pytest

from tests._bdio import (
    entry_request,
    handle,
    instance_key,
    load_definition,
    make_root,
)
from tests._fake_bd import FakeBd, InjectedCrash
from tests.conftest import FAKE_WORKSPACE, TEST_ACTOR, branch_head
from workflow_interpreter.bdio.api import WorkflowStore
from workflow_interpreter.bdio.backend import (
    PinnedBackendFactory,
    StoreBackend,
    StoreBackendFactory,
)
from workflow_interpreter.bdio.bounds import ceiling_count
from workflow_interpreter.bdio.client import BdClient
from workflow_interpreter.bdio.config import BdConfig
from workflow_interpreter.bdio.constants import BackendKind
from workflow_interpreter.bdio.reads import activations_of, next_seq
from workflow_interpreter.bdio.records import ActivationRecord, RowRecord
from workflow_interpreter.bdio.wire import EventPayload, ExitRecord, Lifecycle, Metadata
from workflow_interpreter.schema.models import Outcome

STATUS_CLOSED: Final[str] = "closed"
STATUS_OPEN: Final[str] = "open"
CLAIM_PAYLOAD: Final[str] = "contract_claim"
_NO_FAULTS: Final[str] = (
    "the {backend} backend has no fault hook: a crash between two durable "
    "writes cannot be produced, so this case would pass vacuously"
)


class FaultPoint(StrEnum):
    """Where a backend is made to fail, named by meaning rather than command."""

    AFTER_STATE_COMMIT = "after-state-commit"
    """The routing state landed; the process dies before the follow-up write
    that finishes the transition."""

    BEFORE_READBACK = "before-readback"
    """The write landed durably; its verifying read never returned, so the
    caller never learned the row exists."""


class ContractLab:
    """One backend under the contract, plus whatever faults it can produce."""

    def __init__(
        self,
        name: str,
        backend_factory: StoreBackendFactory,
        faults: FakeBd | None = None,
    ) -> None:
        self.name = name
        self.backend_factory = backend_factory
        self._faults = faults

    def store(self) -> WorkflowStore:
        """A store built the way production builds one: through the factory."""
        return WorkflowStore(
            self.backend_factory(BackendKind.BD),
            backend_factory=self.backend_factory,
            branch_head_reader=branch_head,
        )

    def arm(self, point: FaultPoint) -> None:
        """Arm the next occurrence of `point`, or skip a test that needs one."""
        if self._faults is None:
            pytest.skip(_NO_FAULTS.format(backend=self.name))
        if point is FaultPoint.AFTER_STATE_COMMIT:
            # The carrier is written first and the row closed second (§5.1),
            # so "state committed, transition unfinished" is a dead close.
            self._faults.crash_on("close")
            return
        self._faults.lose_response_on("create")


@pytest.fixture(
    params=[
        pytest.param("fake", id="fake-transport"),
        pytest.param("bd", id="real-bd", marks=pytest.mark.bd),
    ]
)
def lab(request: pytest.FixtureRequest) -> Iterator[ContractLab]:
    """The contract's backend, built from a factory like production's."""
    if request.param == "fake":
        fake = FakeBd(str(FAKE_WORKSPACE))
        client = BdClient(
            BdConfig(workspace=FAKE_WORKSPACE, actor=TEST_ACTOR), runner=fake
        )
        yield ContractLab("fake", PinnedBackendFactory(client), fake)
        return
    workspace = request.getfixturevalue("bd_workspace")
    client = BdClient(BdConfig(workspace=workspace, actor=TEST_ACTOR))
    yield ContractLab("bd", PinnedBackendFactory(client))


def _entry(store: WorkflowStore, root_id: str) -> ActivationRecord:
    """Mint the fixture's entry activation and take it up to its close."""
    activation = store.mint_activation(root_id, entry_request()).activation
    store.record_dispatch(activation.activation_id, handle())
    store.record_exit(
        activation.activation_id,
        ExitRecord(exit_code=0, ended_at="2026-09-16T00:01:00Z", reason="ok"),
    )
    return activation


def test_a_root_reads_back_by_its_id_and_by_its_instance_key(
    lab: ContractLab,
) -> None:
    """Both root lookups answer from the same durable fact."""
    store = lab.store()
    root = make_root(store, load_definition())

    reread = store.reads.load_root(root.root_id)
    assert (reread.root_id, reread.status) == (root.root_id, STATUS_OPEN)
    assert reread.metadata.instance_key == root.metadata.instance_key

    found = store.reads.roots_by_instance_key(root.metadata.instance_key)
    assert tuple(row.id for row in found) == (root.root_id,)


def test_a_mint_is_idempotent_under_its_natural_key(lab: ContractLab) -> None:
    """A re-mint re-finds the activation rather than creating a second one."""
    store = lab.store()
    root = make_root(store, load_definition())

    first = store.mint_activation(root.root_id, entry_request())
    second = store.mint_activation(root.root_id, entry_request())

    assert first.created is True
    assert second.created is False
    assert second.activation.activation_id == first.activation.activation_id


def test_instance_records_are_typed_and_exclude_the_root_from_the_count(
    lab: ContractLab,
) -> None:
    """The instance reads hand out records, and §10.3 counts only its work."""
    store = lab.store()
    root = make_root(store, load_definition())
    activation = store.mint_activation(root.root_id, entry_request()).activation

    records = store.reads.instance_records(root.root_id)
    assert {record.id for record in records} == {root.root_id, activation.activation_id}
    assert tuple(item.activation_id for item in activations_of(records)) == (
        activation.activation_id,
    )
    assert [record.kind for record in records if isinstance(record, RowRecord)] == [
        "root"
    ]
    assert ceiling_count(records) == 1
    assert next_seq(records) == activation.metadata.seq + 1


def test_a_close_records_its_outcome_and_settles_the_row(lab: ContractLab) -> None:
    """A closed activation carries its outcome AND a settled durable row."""
    store = lab.store()
    root = make_root(store, load_definition())
    activation = _entry(store, root.root_id)

    closed = store.close_activation(activation.activation_id, Outcome.DONE)

    assert closed.metadata.lifecycle is Lifecycle.CLOSED
    assert closed.metadata.outcome is Outcome.DONE
    assert (closed.status, closed.close_reason) == (STATUS_CLOSED, "outcome=done")
    assert store.reads.load_activation(activation.activation_id) == closed


def test_an_event_appends_once_per_event_key(lab: ContractLab) -> None:
    """The second append of one transition re-finds the first (§3.3)."""
    store = lab.store()
    root = make_root(store, load_definition())
    activation = _entry(store, root.root_id)
    store.close_activation(activation.activation_id, Outcome.DONE)
    payload = EventPayload(
        **{"from": "implement"},
        outcome=Outcome.DONE,
        to="review",
        activation_id=activation.activation_id,
        seq=9,
        actor=TEST_ACTOR,
        origin="activation",
    )

    first = store.append_event(root.root_id, payload)
    second = store.append_event(root.root_id, payload)

    assert first.id == second.id
    assert store.reads.find_event(root.root_id, str(first.metadata["event_key"])) == (
        first
    )


def test_a_claim_is_found_by_key_and_merged_rather_than_duplicated(
    lab: ContractLab,
) -> None:
    """Two writes of one target key contend on one row, not two (§3.2)."""
    store = lab.store()
    key = instance_key()
    payload: Metadata = {CLAIM_PAYLOAD: {"holder": "first"}}

    store.claims.write(key, payload)
    written = store.claims.find(key)
    assert len(written) == 1
    assert written[0].payload[CLAIM_PAYLOAD] == {"holder": "first"}

    store.claims.write(key, {CLAIM_PAYLOAD: {"holder": "second"}}, written[0].id)
    merged = store.claims.find(key)
    assert [row.id for row in merged] == [written[0].id]
    assert merged[0].payload[CLAIM_PAYLOAD] == {"holder": "second"}


def test_a_root_scoped_store_is_built_through_the_backend_factory(
    lab: ContractLab,
) -> None:
    """A root gets its backend from the factory, not from a borrowed handle.

    The pin is per root (§3.2), so the derivation has to ASK; a `for_root`
    that reused whatever transport it held could not serve two roots on two
    backends during the cutover.
    """
    asked: list[BackendKind] = []

    def recording(backend: BackendKind) -> StoreBackend:
        asked.append(backend)
        return lab.backend_factory(backend)

    store = WorkflowStore(
        recording(BackendKind.BD),
        backend_factory=recording,
        branch_head_reader=branch_head,
    )
    root = make_root(store, load_definition())
    asked.clear()

    scoped = store.for_root(branch_head_reader=branch_head)

    assert asked == [BackendKind.BD]
    assert scoped.reads.load_root(root.root_id).root_id == root.root_id


def test_a_crash_after_the_state_commit_is_repaired_forward(
    lab: ContractLab,
) -> None:
    """The transition finishes on the next call, rather than wedging (§5.1)."""
    store = lab.store()
    root = make_root(store, load_definition())
    activation = _entry(store, root.root_id)
    lab.arm(FaultPoint.AFTER_STATE_COMMIT)

    with pytest.raises(InjectedCrash):
        store.close_activation(activation.activation_id, Outcome.DONE)

    wedged = store.reads.load_activation(activation.activation_id)
    assert wedged.metadata.lifecycle is Lifecycle.CLOSED
    assert wedged.status == STATUS_OPEN

    repaired = store.close_activation(activation.activation_id, Outcome.DONE)
    assert (repaired.status, repaired.metadata.outcome) == (
        STATUS_CLOSED,
        Outcome.DONE,
    )


def test_a_write_whose_readback_is_lost_mints_nothing_twice(
    lab: ContractLab,
) -> None:
    """A durable write nobody saw is re-FOUND by its natural key, not repeated."""
    store = lab.store()
    root = make_root(store, load_definition())
    lab.arm(FaultPoint.BEFORE_READBACK)

    with pytest.raises(InjectedCrash):
        store.mint_activation(root.root_id, entry_request())

    recovered = store.mint_activation(root.root_id, entry_request())
    assert recovered.created is False
    assert len(activations_of(store.reads.instance_records(root.root_id))) == 1
