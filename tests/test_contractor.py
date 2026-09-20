"""Focused proof for contract admission and recovery."""

from __future__ import annotations

import hashlib
import subprocess
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace
from typing import Final

import pytest

from tests._fake_bd import FakeBd, InjectedCrash
from tests._helpers import (
    TASK_BRIEF,
    VALID_FIXTURE,
    CrashingContractorRecords,
    InjectedRecordCrash,
    MemoryContractorRecords,
    seeded_records,
)
from tests._workspace import Fixture
from tests.conftest import Signer
from workflow_interpreter.bdio import (
    GateArtifact,
    GatePayload,
    GateState,
    GateVerifier,
    canonical_payload_bytes,
)
from workflow_interpreter.bdio.client import BdClient
from workflow_interpreter.bdio.constants import BackendKind
from workflow_interpreter.bdio.records import GateRecord, parse_gate
from workflow_interpreter.bdio.signing import payload_digest
from workflow_interpreter.bdio.wire import BeadRecord, GateMetadata
from workflow_interpreter.contractor import (
    AdmissionRefused,
    ContractorAdapter,
    ContractorAdapterError,
    ContractorRecord,
    ContractorRoot,
    ContractorState,
    DetachedRepositoryGate,
    GateEvidence,
    LandingDisposition,
    LandingHooks,
    LandingIntent,
    LandingReceipt,
    PhaseAdmission,
    PhaseLanding,
    RepositoryGateResult,
)
from workflow_interpreter.contractor.adapter import MSG_CLOSE_REASON
from workflow_interpreter.contractor.authority import BeadGateAuthority
from workflow_interpreter.contractor.journal import ExportPin
from workflow_interpreter.contractor.landing import LANDING_RECEIPT_FILE, T1_MESSAGE
from workflow_interpreter.contractor.models import INSTANCE_KEY_TEMPLATE
from workflow_interpreter.contractor.records import LedgerContractorRecords
from workflow_interpreter.contractor.retry import RetryRefusal, retry_refusal
from workflow_interpreter.contractor.verification import (
    CheckCommand,
    CheckResult,
    VerificationPolicy,
)
from workflow_interpreter.foreman.frontier import Frontier
from workflow_interpreter.inspector import Git
from workflow_interpreter.inspector.config import InspectorConfig
from workflow_interpreter.inspector.paths import (
    WrapperPaths,
    read_record,
    record_bytes,
    write_record,
)
from workflow_interpreter.inspector.sandbox import SandboxMode
from workflow_interpreter.ledger import records as ledger_records
from workflow_interpreter.ledger.closure import NoLedgerClosure
from workflow_interpreter.ledger.database import open_ledger
from workflow_interpreter.ledger.tasks import pin_task_backend
from workflow_interpreter.schema.graph_index import build_index
from workflow_interpreter.schema.loader import load_graph
from workflow_interpreter.schema.models import IsolationMode, Outcome

EPIC_ID = "phase-1"
STAGE_ID = "stage-a"
TARGET_REF = "refs/heads/main"
BASE_COMMIT = "a" * 40

ROOT_ID: Final[str] = "contractor-root"
FUTURE_CONTRACTOR_SCHEMA: Final[str] = "future-schema/99"
WRONG_INSTANCE_KEY: Final[str] = "not-the-derived-key"
REPEATED_PREVIOUS_ATTEMPT: Final[str] = "x"


def _policy():
    return VerificationPolicy.pin(
        (CheckCommand(name="source", argv=(sys.executable, "-c", "pass")),), Path.cwd()
    )


class _DurableRecord:
    """A closure probe that says this task's record is already in git (§3.5).

    A stand-in rather than a ledger: what these tests are about is the bead
    surface, and `tests/test_derived_closed.py` is where the derivation itself
    is proved against real git.
    """

    def closed(self, task_id: str) -> bool:
        """Yes: the export is pinned and the task derives closed."""
        return True

    def retired(self, task_id: str) -> bool:
        """A closed task is retired."""
        return True


def _admission(adapter, roots, head_commit):
    # A first prepare snapshots the task brief beside the record (§3.3, R4),
    # so an admission rig that could not state one could never prepare.
    return PhaseAdmission(
        adapter,
        roots,
        head_commit,
        verification_policy=_policy(),
        task_brief=TASK_BRIEF,
    )


def _stage_row(status: str = "open") -> dict[str, object]:
    """Build the direct-child stage the contractor is allowed to admit.

    `status` is the TRACKER's label, and since S4 nothing in the contractor
    writes it: the claim is the tracker port's, placed by the caller before
    the ledger transition (§3.4), and it arrives in S5. A case about "this
    recovery must not close the bead" therefore states the in-progress label
    as part of its world instead of expecting admission to have set it.
    """
    return {
        "id": STAGE_ID,
        "title": "one stage",
        "status": status,
        "issue_type": "task",
        "metadata": {"unrelated": {"preserved": True}},
        "parent": EPIC_ID,
    }


def _gate(
    state: GateState,
    *,
    gate_node: str,
    outcome: Outcome = Outcome.APPROVE,
) -> GateRecord:
    """Build one valid gate record for a retry-frontier observation."""
    metadata = GateMetadata(
        wf_root_id=ROOT_ID,
        gate_key=f"gate-{gate_node}",
        gate_node=gate_node,
        outcomes=(Outcome.APPROVE, Outcome.REJECT),
        seq=1,
        state=state,
        outcome=outcome if state is GateState.CLOSED else None,
        verified_fingerprint="fingerprint" if state is GateState.CLOSED else None,
        payload_digest="digest" if state is GateState.CLOSED else None,
    )
    return parse_gate(
        BeadRecord(
            id=f"gate-{gate_node}",
            title=gate_node,
            status="open",
            issue_type="task",
            metadata=metadata.model_dump(mode="json", exclude_none=True),
        )
    )


def test_attempt_key_is_stable_and_distinct_per_attempt() -> None:
    """Keep a recovered attempt on its recorded root identity."""
    first = ContractorRecord.prepared(
        verification_policy=_policy(),
        epic_id=EPIC_ID,
        stage_id=STAGE_ID,
        attempt=1,
        target_ref=TARGET_REF,
        expected_base_commit=BASE_COMMIT,
    )
    retry = first.next_attempt()

    assert first.instance_key == "contract:phase-1:stage-a:attempt:1"
    assert retry.instance_key == "contract:phase-1:stage-a:attempt:2"
    assert retry.previous_attempts == (first.instance_key,)


def test_contractor_record_rejects_an_unknown_schema() -> None:
    """A journal must declare the pinned schema instead of accepting future records."""
    record = ContractorRecord.prepared(
        verification_policy=_policy(),
        epic_id=EPIC_ID,
        stage_id=STAGE_ID,
        attempt=1,
        target_ref=TARGET_REF,
        expected_base_commit=BASE_COMMIT,
    )
    raw = record.model_dump(by_alias=True)
    raw["schema"] = FUTURE_CONTRACTOR_SCHEMA

    with pytest.raises(ValueError, match="schema"):
        ContractorRecord.model_validate(raw)


def test_contractor_record_rejects_an_underived_instance_key() -> None:
    """A journal key must identify its epic, stage, and attempt exactly."""
    record = ContractorRecord.prepared(
        verification_policy=_policy(),
        epic_id=EPIC_ID,
        stage_id=STAGE_ID,
        attempt=1,
        target_ref=TARGET_REF,
        expected_base_commit=BASE_COMMIT,
    )
    raw = record.model_dump(by_alias=True)
    raw["instance_key"] = WRONG_INSTANCE_KEY

    with pytest.raises(ValueError, match="instance_key"):
        ContractorRecord.model_validate(raw)


def test_contractor_record_rejects_invalid_previous_attempt_history() -> None:
    """A retry journal must retain each earlier attempt once and only once."""
    record = ContractorRecord.prepared(
        verification_policy=_policy(),
        epic_id=EPIC_ID,
        stage_id=STAGE_ID,
        attempt=1,
        target_ref=TARGET_REF,
        expected_base_commit=BASE_COMMIT,
    )
    raw = record.model_dump(by_alias=True)
    raw.update(
        {
            "attempt": 3,
            "instance_key": INSTANCE_KEY_TEMPLATE.format(
                epic_id=EPIC_ID, stage_id=STAGE_ID, attempt=3
            ),
            "previous_attempts": (
                REPEATED_PREVIOUS_ATTEMPT,
                REPEATED_PREVIOUS_ATTEMPT,
            ),
        }
    )

    with pytest.raises(ValueError, match="previous_attempts"):
        ContractorRecord.model_validate(raw)


@pytest.mark.parametrize("field", ("schema", "previous_attempts"))
def test_contractor_record_rejects_truncated_journal_fields(field: str) -> None:
    """A nested metadata replacement cannot silently re-default identity fields."""
    record = ContractorRecord.prepared(
        verification_policy=_policy(),
        epic_id=EPIC_ID,
        stage_id=STAGE_ID,
        attempt=1,
        target_ref=TARGET_REF,
        expected_base_commit=BASE_COMMIT,
    )
    raw = record.model_dump(by_alias=True)
    del raw[field]

    with pytest.raises(ValueError, match=field):
        ContractorRecord.model_validate(raw)


def test_contractor_next_attempt_round_trips_through_validation() -> None:
    """The normal retry constructor remains a valid complete journal record."""
    retry = ContractorRecord.prepared(
        verification_policy=_policy(),
        epic_id=EPIC_ID,
        stage_id=STAGE_ID,
        attempt=1,
        target_ref=TARGET_REF,
        expected_base_commit=BASE_COMMIT,
    ).next_attempt()

    assert ContractorRecord.model_validate(retry.model_dump(by_alias=True)) == retry


def test_contractor_prepared_refuses_a_nonfirst_attempt() -> None:
    """Only next_attempt may attach genuine prior-attempt history."""
    with pytest.raises(ValueError, match="first attempt"):
        ContractorRecord.prepared(
            verification_policy=_policy(),
            epic_id=EPIC_ID,
            stage_id=STAGE_ID,
            attempt=3,
            target_ref=TARGET_REF,
            expected_base_commit=BASE_COMMIT,
        )


def test_retry_refusal_allows_a_declared_terminal() -> None:
    """A listed terminal may mint the contractor's next root."""
    frontier = Frontier(terminal=True, terminal_node="abandoned")

    assert retry_refusal(ContractorState.ADMITTED, ("abandoned",), frontier) is None


def test_retry_refusal_refuses_an_unlisted_terminal() -> None:
    """A terminal outside the retry declaration cannot mint another root."""
    frontier = Frontier(terminal=True, terminal_node="failed")

    assert (
        retry_refusal(ContractorState.ADMITTED, ("abandoned",), frontier)
        is RetryRefusal.UNLISTED_TERMINAL
    )


def test_retry_refusal_refuses_a_root_without_a_terminal() -> None:
    """A root still in flight has no terminal eligible for retry."""
    frontier = Frontier()

    assert (
        retry_refusal(ContractorState.ADMITTED, ("abandoned",), frontier)
        is RetryRefusal.NO_TERMINAL
    )


def test_retry_refusal_open_halt_outranks_a_declared_terminal() -> None:
    """An unresolved halt prevents retry even after a listed terminal."""
    frontier = Frontier(
        terminal=True,
        terminal_node="abandoned",
        open_halt=_gate(GateState.OPEN, gate_node="halt"),
    )

    assert (
        retry_refusal(ContractorState.ADMITTED, ("abandoned",), frontier)
        is RetryRefusal.OPEN_HALT
    )


def test_retry_refusal_refuses_the_realistic_open_halt_frontier() -> None:
    """A live halt has no terminal until the foreman settles the root."""
    frontier = Frontier(open_halt=_gate(GateState.OPEN, gate_node="halt"))

    assert (
        retry_refusal(ContractorState.ADMITTED, ("abandoned",), frontier)
        is RetryRefusal.OPEN_HALT
    )


def test_retry_refusal_gate_red_requires_an_approved_shipped_terminal() -> None:
    """A gate-red retry cannot bypass the prior root's ship approval."""
    frontier = Frontier(terminal=True, terminal_node="shipped")

    assert (
        retry_refusal(ContractorState.GATE_RED, ("shipped", "abandoned"), frontier)
        is RetryRefusal.GATE_RED_NOT_APPROVED_SHIPPED
    )


def test_retry_refusal_allows_gate_red_after_approved_shipped_terminal() -> None:
    """A gate-red retry follows the prior root's accepted immutable ship gate."""
    frontier = Frontier(
        terminal=True,
        terminal_node="shipped",
        decided_gates=(_gate(GateState.CLOSED, gate_node="ship"),),
    )

    assert (
        retry_refusal(ContractorState.GATE_RED, ("shipped", "abandoned"), frontier)
        is None
    )


@pytest.mark.parametrize(
    ("gate_node", "outcome"),
    (("ship", Outcome.REJECT), ("review", Outcome.APPROVE)),
)
def test_retry_refusal_refuses_gate_red_without_an_approved_ship_gate(
    gate_node: str, outcome: Outcome
) -> None:
    """A gate-red root needs an approving decision at the declared ship gate."""
    frontier = Frontier(
        terminal=True,
        terminal_node="shipped",
        decided_gates=(_gate(GateState.CLOSED, gate_node=gate_node, outcome=outcome),),
    )

    assert (
        retry_refusal(ContractorState.GATE_RED, ("shipped",), frontier)
        is RetryRefusal.GATE_RED_NOT_APPROVED_SHIPPED
    )


def test_retry_refusal_refuses_gate_red_without_the_shipped_terminal() -> None:
    """An approved ship gate cannot qualify a different declared terminal."""
    frontier = Frontier(
        terminal=True,
        terminal_node="abandoned",
        decided_gates=(_gate(GateState.CLOSED, gate_node="ship"),),
    )

    assert (
        retry_refusal(ContractorState.GATE_RED, ("abandoned",), frontier)
        is RetryRefusal.GATE_RED_NOT_APPROVED_SHIPPED
    )


def test_adapter_writes_the_whole_record_across_the_admit_boundary(
    fake_bd: FakeBd, fake_client: BdClient
) -> None:
    """Keep the stage record complete across the prepare-to-admit boundary.

    And keep it entirely in the record store: since S4 both transitions are
    ledger writes (§3.2, R4), and the S4 acceptance is that admit succeeds
    with `.beads/` deleted — so a tracker write here would be the defect, not
    the claim this case used to assert. The tracker claim returns in S5, on
    the tracker port, placed by the caller before the transaction (§3.4).
    """
    fake_bd.rows[STAGE_ID] = _stage_row()
    records = MemoryContractorRecords()
    adapter = ContractorAdapter(fake_client, closure=NoLedgerClosure(), records=records)
    prepared = ContractorRecord.prepared(
        verification_policy=_policy(),
        epic_id=EPIC_ID,
        stage_id=STAGE_ID,
        attempt=1,
        target_ref=TARGET_REF,
        expected_base_commit=BASE_COMMIT,
    )

    adapter.prepare(STAGE_ID, prepared, brief=TASK_BRIEF)
    writes_after_prepare = len(fake_bd.metadata_writes)
    admitted = adapter.admit(STAGE_ID, prepared, root_id="wf-1")

    assert admitted.state is ContractorState.ADMITTED
    held = records.read(STAGE_ID)
    assert held is not None
    assert held.record == admitted
    assert held.brief == TASK_BRIEF
    # The first write created the record, the second moved it: the version is
    # the evidence a transition states, so it has to have advanced.
    assert held.version == 2
    assert fake_bd.rows[STAGE_ID]["metadata"] == {"unrelated": {"preserved": True}}
    assert len(fake_bd.metadata_writes) == writes_after_prepare
    assert adapter.dependencies(STAGE_ID) == ()


@pytest.mark.parametrize(
    "stored_state", (ContractorState.ADMITTED, ContractorState.LANDED)
)
def test_prepare_refuses_a_non_successor_over_a_later_stored_journal(
    fake_bd: FakeBd, fake_client: BdClient, stored_state: ContractorState
) -> None:
    """A same-attempt write cannot replace admitted or landed stage evidence."""
    stored = ContractorRecord.prepared(
        verification_policy=_policy(),
        epic_id=EPIC_ID,
        stage_id=STAGE_ID,
        attempt=1,
        target_ref=TARGET_REF,
        expected_base_commit=BASE_COMMIT,
    ).admitted(ROOT_ID)
    stored = stored.model_copy(update={"state": stored_state})
    fake_bd.rows[STAGE_ID] = _stage_row()

    incoming = stored.model_copy(update={"state": ContractorState.PREPARED})

    with pytest.raises(ContractorAdapterError, match="requires stored state prepared"):
        ContractorAdapter(
            fake_client, closure=NoLedgerClosure(), records=seeded_records(stored)
        ).prepare(STAGE_ID, incoming)


@pytest.mark.parametrize(
    "stored_state", (ContractorState.ADMITTED, ContractorState.GATE_RED)
)
def test_prepare_accepts_a_valid_successor_over_an_unsettled_journal(
    fake_bd: FakeBd, fake_client: BdClient, stored_state: ContractorState
) -> None:
    """A retry advances a settled-not-closed stage journal by one attempt."""
    stored = ContractorRecord.prepared(
        verification_policy=_policy(),
        epic_id=EPIC_ID,
        stage_id=STAGE_ID,
        attempt=1,
        target_ref=TARGET_REF,
        expected_base_commit=BASE_COMMIT,
    ).admitted(ROOT_ID)
    stored = stored.model_copy(update={"state": stored_state})
    fake_bd.rows[STAGE_ID] = _stage_row()

    successor = ContractorAdapter(
        fake_client, closure=NoLedgerClosure(), records=seeded_records(stored)
    ).prepare(STAGE_ID, stored.next_attempt())

    assert successor == stored.next_attempt()


def test_prepare_refuses_a_structural_successor_over_a_landed_journal(
    fake_bd: FakeBd, fake_client: BdClient
) -> None:
    """No retry structure can reopen evidence for a stage that landed.

    The record stops at LANDED since S2 — closure is derived from the ledger
    and its git anchor (store-restructure §3.5) — so the stored state alone
    refuses the successor, and a task that also derives `closed()` is refused
    by the probe before this (`tests/test_derived_closed.py`).
    """
    stored = (
        ContractorRecord.prepared(
            verification_policy=_policy(),
            epic_id=EPIC_ID,
            stage_id=STAGE_ID,
            attempt=1,
            target_ref=TARGET_REF,
            expected_base_commit=BASE_COMMIT,
        )
        .admitted(ROOT_ID)
        .landed("b" * 40, "c" * 40, "gate-receipt", "landing-receipt")
    )
    fake_bd.rows[STAGE_ID] = _stage_row()

    with pytest.raises(ContractorAdapterError, match="refuses a landed stored record"):
        ContractorAdapter(
            fake_client, closure=NoLedgerClosure(), records=seeded_records(stored)
        ).prepare(STAGE_ID, stored.next_attempt())


def test_prepare_refuses_a_nonprepared_incoming_journal(
    fake_bd: FakeBd, fake_client: BdClient
) -> None:
    """The supplied record is named when it is not a prepare intent."""
    fake_bd.rows[STAGE_ID] = _stage_row()
    incoming = ContractorRecord.prepared(
        verification_policy=_policy(),
        epic_id=EPIC_ID,
        stage_id=STAGE_ID,
        attempt=1,
        target_ref=TARGET_REF,
        expected_base_commit=BASE_COMMIT,
    ).admitted(ROOT_ID)

    with pytest.raises(
        ContractorAdapterError, match="incoming contractor record expected state"
    ):
        ContractorAdapter(
            fake_client, closure=NoLedgerClosure(), records=MemoryContractorRecords()
        ).prepare(STAGE_ID, incoming)


def test_prepare_wraps_unreadable_stored_journal(
    fake_bd: FakeBd, fake_client: BdClient, tmp_path: Path
) -> None:
    """A corrupt stored record stays behind the adapter's error boundary.

    The record is a ledger row since S4 (§3.2, R4), so the corruption is a
    `record_json` that will not validate — written straight to the table,
    because no public path can produce one. A real ledger rather than a stub:
    what is under test is that the seam the record actually crosses names its
    own refusal instead of letting a validation error escape.
    """
    repo, _base = _temporary_repo(tmp_path)
    fake_bd.rows[STAGE_ID] = _stage_row()
    database = open_ledger(repo, tmp_path / "unreadable-wrapper")
    pin_task_backend(database, STAGE_ID, BackendKind.LEDGER, EPIC_ID)
    ledger_records.create(
        database,
        STAGE_ID,
        state=ContractorState.PREPARED.value,
        attempt=1,
        root_id=None,
        brief=TASK_BRIEF,
        record_json='{"state": "not-a-contractor-state"}',
    )
    incoming = ContractorRecord.prepared(
        verification_policy=_policy(),
        epic_id=EPIC_ID,
        stage_id=STAGE_ID,
        attempt=1,
        target_ref=TARGET_REF,
        expected_base_commit=BASE_COMMIT,
    )

    with pytest.raises(
        ContractorAdapterError, match="stored contractor record is unreadable"
    ):
        ContractorAdapter(
            fake_client,
            closure=NoLedgerClosure(),
            records=LedgerContractorRecords(database, backend=BackendKind.LEDGER),
        ).prepare(STAGE_ID, incoming)


class _Roots:
    """Script the root and branch seams around a real temporary Git history."""

    def __init__(self, fake_client: BdClient, repo: Path, base: str) -> None:
        self._client = fake_client
        self._repo = repo
        self._base = base
        self._roots: dict[str, ContractorRoot] = {}
        self._branches: set[str] = set()
        self.backends: list[BackendKind] = []
        self.fail_branch = False

    def find(
        self,
        instance_key: str,
        backend: BackendKind = BackendKind.BD,
        attempt: int = 1,
    ) -> ContractorRoot | None:
        """Find the root already created for an admission identity."""
        self.backends.append(backend)
        found = self._roots.get(instance_key)
        if found is not None:
            return found
        for row in self._client.list_beads(
            metadata_filters={"instance_key": instance_key}
        ):
            self._client._merge_metadata(row.id, {"root_id": row.id})
            recovered = ContractorRoot(
                root_id=row.id,
                instance_key=instance_key,
                instance_base_commit=str(row.metadata["base"]),
            )
            self._roots[instance_key] = recovered
            return recovered
        return None

    def create(
        self,
        instance_key: str,
        backend: BackendKind = BackendKind.BD,
        attempt: int = 1,
    ) -> ContractorRoot:
        """Create one fake root on the backend and attempt the record pins."""
        self.backends.append(backend)
        root = self._client._create_bead(
            title="phase root",
            metadata={"instance_key": instance_key, "base": self._base},
        )
        self._client._merge_metadata(root.id, {"root_id": root.id})
        created = ContractorRoot(
            root_id=root.id,
            instance_key=instance_key,
            instance_base_commit=self._base,
        )
        self._roots[instance_key] = created
        return created

    def ensure_branch(self, root: ContractorRoot) -> None:
        """Recreate an instance branch from the persisted root base."""
        if self.fail_branch:
            self.fail_branch = False
            raise InjectedCrash("branch creation died")
        if root.root_id not in self._branches:
            subprocess.run(
                ["git", "update-ref", f"refs/wf/{root.root_id}", self._base],
                cwd=self._repo,
                check=True,
                capture_output=True,
            )
            self._branches.add(root.root_id)


def _temporary_repo(tmp_path: Path) -> tuple[Path, str]:
    """Create the real Git history admission recovery must not reinterpret."""
    fixture = Fixture(tmp_path, IsolationMode.WORKTREE)
    return fixture.repo, fixture.base


def test_admission_recovers_after_root_creation_crash(
    fake_bd: FakeBd, fake_client: BdClient, tmp_path: Path
) -> None:
    """Resume one prepared intent instead of creating a second root."""
    fake_bd.rows[STAGE_ID] = _stage_row()
    repo, base = _temporary_repo(tmp_path)
    roots = _Roots(fake_client, repo, base)
    records = MemoryContractorRecords()
    admission = _admission(
        ContractorAdapter(fake_client, closure=NoLedgerClosure(), records=records),
        roots,
        lambda: base,
    )
    fake_bd.crash_on("create")

    with pytest.raises(InjectedCrash, match="bd create died"):
        admission.admit(EPIC_ID, STAGE_ID, TARGET_REF, base)

    recovered = admission.admit(EPIC_ID, STAGE_ID, TARGET_REF, base)

    assert recovered.state is ContractorState.ADMITTED
    assert fake_bd.command_count("create") == 2
    assert len(roots._roots) == 1
    held = records.read(STAGE_ID)
    assert held is not None
    assert held.record == recovered


def test_admission_repairs_a_root_interrupted_before_its_self_link(
    fake_bd: FakeBd, fake_client: BdClient, tmp_path: Path
) -> None:
    """Reuse the one raw root left between create and self-link."""
    fake_bd.rows[STAGE_ID] = _stage_row()
    repo, base = _temporary_repo(tmp_path)
    roots = _Roots(fake_client, repo, base)
    admission = _admission(
        ContractorAdapter(
            fake_client, closure=NoLedgerClosure(), records=MemoryContractorRecords()
        ),
        roots,
        lambda: base,
    )
    # The self-link is the FIRST bd update of an admission now: prepare writes
    # the record to the ledger rather than to the stage bead (§3.2, R4).
    fake_bd.crash_on("update", occurrence=1)

    with pytest.raises(InjectedCrash, match="bd update died"):
        admission.admit(EPIC_ID, STAGE_ID, TARGET_REF, base)

    recovered = admission.admit(EPIC_ID, STAGE_ID, TARGET_REF, base)

    found = roots.find(recovered.instance_key)
    assert found is not None
    assert recovered.root_id == found.root_id
    assert fake_bd.command_count("create") == 1


def test_admission_reuses_a_root_when_branch_creation_is_interrupted(
    fake_bd: FakeBd, fake_client: BdClient, tmp_path: Path
) -> None:
    """Restore the branch from the root base without rereading coordinator HEAD."""
    fake_bd.rows[STAGE_ID] = _stage_row()
    repo, base = _temporary_repo(tmp_path)
    roots = _Roots(fake_client, repo, base)
    roots.fail_branch = True
    head = [base]
    admission = _admission(
        ContractorAdapter(
            fake_client, closure=NoLedgerClosure(), records=MemoryContractorRecords()
        ),
        roots,
        lambda: head[0],
    )

    with pytest.raises(InjectedCrash, match="branch creation died"):
        admission.admit(EPIC_ID, STAGE_ID, TARGET_REF, base)
    head[0] = "b" * 40

    recovered = admission.admit(EPIC_ID, STAGE_ID, TARGET_REF, base)

    assert recovered.state is ContractorState.ADMITTED
    assert fake_bd.command_count("create") == 1
    assert f"refs/wf/{recovered.root_id}" in {
        line.strip()
        for line in subprocess.run(
            ["git", "for-each-ref", "--format=%(refname)"],
            cwd=repo,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.splitlines()
    }


def test_admission_recovers_after_the_relation_write_is_interrupted(
    fake_bd: FakeBd, fake_client: BdClient, tmp_path: Path
) -> None:
    """Finish the stage relation without manufacturing another root."""
    fake_bd.rows[STAGE_ID] = _stage_row()
    repo, base = _temporary_repo(tmp_path)
    roots = _Roots(fake_client, repo, base)
    prepared_root = roots.create("contract:phase-1:stage-a:attempt:1")
    # The relation write is the ledger transition to ADMITTED since S4 (§3.2,
    # R4), so that is where this case's interruption has to be injected.
    admission = _admission(
        ContractorAdapter(
            fake_client,
            closure=NoLedgerClosure(),
            records=CrashingContractorRecords(MemoryContractorRecords(), armed=True),
        ),
        roots,
        lambda: base,
    )

    with pytest.raises(InjectedRecordCrash, match="record update died"):
        admission.admit(EPIC_ID, STAGE_ID, TARGET_REF, base)

    recovered = admission.admit(EPIC_ID, STAGE_ID, TARGET_REF, base)

    assert recovered.root_id == prepared_root.root_id
    assert fake_bd.command_count("create") == 1


def test_admission_refuses_an_open_stage_with_a_landed_relation(
    fake_bd: FakeBd, fake_client: BdClient, tmp_path: Path
) -> None:
    """A landed relation remains unfinished until its stage bead is closed."""
    other_stage_id = "stage-b"
    fake_bd.rows[STAGE_ID] = _stage_row()
    other_stage = _stage_row()
    other_stage["id"] = other_stage_id
    fake_bd.rows[other_stage_id] = other_stage
    repo, base = _temporary_repo(tmp_path)
    roots = _Roots(fake_client, repo, base)
    adapter = ContractorAdapter(
        fake_client, closure=NoLedgerClosure(), records=MemoryContractorRecords()
    )
    admission = _admission(adapter, roots, lambda: base)

    admitted = admission.admit(EPIC_ID, STAGE_ID, TARGET_REF, base)
    landed = admitted.landed(base, "b" * 40, "gate-receipt", "landing-receipt")
    adapter.land(STAGE_ID, landed)

    with pytest.raises(AdmissionRefused, match="unfinished contractor admission"):
        admission.admit(EPIC_ID, other_stage_id, TARGET_REF, base)

    adapter.closure = _DurableRecord()
    adapter.close(STAGE_ID, landed, "landing-receipt")
    other = admission.admit(EPIC_ID, other_stage_id, TARGET_REF, base)

    assert other.state is ContractorState.ADMITTED


def test_conflicting_record_refuses_without_creating_a_root(
    fake_bd: FakeBd, fake_client: BdClient, tmp_path: Path
) -> None:
    """Leave ambiguous identity for a human instead of opening another journal."""
    conflicting = ContractorRecord.prepared(
        verification_policy=_policy(),
        epic_id=EPIC_ID,
        stage_id=STAGE_ID,
        attempt=1,
        target_ref=TARGET_REF,
        expected_base_commit="c" * 40,
    )
    fake_bd.rows[STAGE_ID] = _stage_row()
    repo, base = _temporary_repo(tmp_path)
    roots = _Roots(fake_client, repo, base)
    admission = _admission(
        ContractorAdapter(
            fake_client, closure=NoLedgerClosure(), records=seeded_records(conflicting)
        ),
        roots,
        lambda: base,
    )

    with pytest.raises(AdmissionRefused, match="identity conflicts"):
        admission.admit(EPIC_ID, STAGE_ID, TARGET_REF, base)

    assert fake_bd.command_count("create") == 0


class _GateAuthority:
    """Return one already signature-verified immutable ship-gate observation."""

    def __init__(
        self,
        artifact_oid: str,
        tree: str,
        verifier: GateVerifier,
        signer: Signer,
    ) -> None:
        self._artifact_oid = artifact_oid
        self._tree = tree
        self._verifier = verifier
        self._signer = signer
        self.calls = 0

    def verify(self, root_id: str) -> GateEvidence:
        """Describe the closed acceptance whose payload was re-verified upstream."""
        self.calls += 1
        payload = GatePayload(
            graph_id="contract",
            root_id=root_id,
            gate_key="ship",
            outcome=Outcome.APPROVE,
            artifact=GateArtifact(commit_oid=self._artifact_oid, tree_oid=self._tree),
            nonce="reverified-ship-gate",
        )
        encoded = canonical_payload_bytes(payload)
        with tempfile.TemporaryDirectory() as directory:
            approval = self._verifier.verify(
                payload_bytes=encoded,
                signature=self._signer(encoded, None),
                work_dir=Path(directory),
            )
        metadata = GateMetadata(
            wf_root_id=root_id,
            gate_key="ship",
            gate_node="ship",
            outcomes=(Outcome.APPROVE, Outcome.ABANDON),
            seq=1,
            state=GateState.CLOSED,
            outcome=Outcome.APPROVE,
            verified_fingerprint=approval.fingerprint,
            payload_digest=payload_digest(encoded),
            artifact_ref=self._artifact_oid,
            artifact_digest=self._tree,
        )
        gate = parse_gate(
            BeadRecord(
                id="signed-ship",
                title="ship",
                status="closed",
                issue_type="task",
                metadata=metadata.model_dump(mode="json"),
            )
        )
        reads = SimpleNamespace(
            list_gates=lambda _: (gate,),
            load_root=lambda _: SimpleNamespace(
                root_id=root_id,
                index=build_index(
                    load_graph(VALID_FIXTURE).document, allow_test_flags=False
                ),
            ),
        )
        return BeadGateAuthority(reads).verify(root_id)


class _RepositoryGate:
    """Record the real detached tree the injected gate was asked to grade."""

    def __init__(
        self,
        artifact_oid: str,
        tree: str,
        results: tuple[str, ...] = ("repository gate green",),
    ) -> None:
        self._artifact_oid = artifact_oid
        self._tree = tree
        self._results = results
        self.calls = 0

    def verify(self, artifact_oid: str, tree: str) -> RepositoryGateResult:
        """Return a complete green receipt for the artifact's real Git identity."""
        self.calls += 1
        assert artifact_oid == self._artifact_oid
        assert tree == self._tree
        return RepositoryGateResult(
            artifact_oid=artifact_oid,
            tree=tree,
            complete=True,
            green=True,
            policy_digest=_policy().digest,
            results=(
                CheckResult(
                    name="source",
                    command=_policy().checks[0].command,
                    executable_digest=_policy().checks[0].executable_digest,
                    exit_code=0,
                    source_unchanged=True,
                ),
            ),
        )


class _CrashAfterCas(LandingHooks):
    """Open the post-CAS crash window without exposing a production fault flag."""

    def after_cas(self) -> None:
        """Interrupt before the landing receipt exists."""
        raise InjectedCrash("post-CAS interruption")


def _commit_artifact(repo: Path) -> tuple[str, str]:
    """Commit an artifact on the temporary repository's real mainline history."""
    subprocess.run(
        ["git", "checkout", "--quiet", "-b", "artifact"], cwd=repo, check=True
    )
    (repo / "artifact.txt").write_text("signed artifact\n", encoding="utf-8")
    subprocess.run(["git", "add", "artifact.txt"], cwd=repo, check=True)
    subprocess.run(
        ["git", "commit", "--quiet", "-m", "signed artifact"],
        cwd=repo,
        check=True,
    )
    artifact_oid = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    tree = subprocess.run(
        ["git", "rev-parse", f"{artifact_oid}^{{tree}}"],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    subprocess.run(["git", "checkout", "--quiet", "main"], cwd=repo, check=True)
    return artifact_oid, tree


def _landing_context(repo: Path, tmp_path: Path) -> tuple[Git, WrapperPaths, ExportPin]:
    """The real Git, wrapper paths and export pin for one temporary history.

    The export pin is part of the context rather than an option because §3.6
    makes it a precondition of CLOSED: a landing composed without one cannot
    close at all, so a test that omitted it would be testing the refusal.
    The ledger lives outside the checkout, as it does in `ForemanLab`.
    """
    config = InspectorConfig(
        repo_root=repo,
        wrapper_root=tmp_path / "contractor-wrapper",
        host="contractor-test",
        sandbox=SandboxMode.OFF,
    )
    git = Git(config)
    database = open_ledger(
        repo, config.wrapper_root, path=tmp_path / "contractor-ledger.db"
    )
    return git, WrapperPaths(config, ROOT_ID), ExportPin(database, git, repo, EPIC_ID)


def test_landing_refuses_a_prepared_stage_without_cas_or_close(
    fake_bd: FakeBd,
    fake_client: BdClient,
    gate_verifier: GateVerifier,
    sign_payload: Signer,
    tmp_path: Path,
) -> None:
    """Only an admitted stage may enter the one-shot landing path."""
    repo, base = _temporary_repo(tmp_path)
    fake_bd.rows[STAGE_ID] = _stage_row()
    git, paths, export = _landing_context(repo, tmp_path)
    adapter = ContractorAdapter(
        fake_client, closure=export.closure, records=export.records
    )
    prepared = ContractorRecord.prepared(
        verification_policy=_policy(),
        epic_id=EPIC_ID,
        stage_id=STAGE_ID,
        attempt=1,
        target_ref=TARGET_REF,
        expected_base_commit=base,
    )
    adapter.prepare(STAGE_ID, prepared)
    landing = PhaseLanding(
        adapter,
        git,
        repo,
        paths,
        _GateAuthority(base, "b" * 40, gate_verifier, sign_payload),
        _RepositoryGate(base, "b" * 40),
        export=export,
    )
    before_reflog = _reflog(repo)

    result = landing.land(STAGE_ID)

    assert result.disposition is LandingDisposition.HUMAN_ATTENTION
    assert _ref_target(repo) == base
    assert _reflog(repo) == before_reflog
    assert fake_bd.command_count("close") == 0


def test_post_cas_recovery_closes_only_the_signed_artifact(
    fake_bd: FakeBd,
    fake_client: BdClient,
    gate_verifier: GateVerifier,
    sign_payload: Signer,
    tmp_path: Path,
) -> None:
    """A real-Git post-CAS interruption recovers closure without another ref move."""
    repo, base = _temporary_repo(tmp_path)
    artifact_oid, tree = _commit_artifact(repo)
    fake_bd.rows[STAGE_ID] = _stage_row()
    admitted = ContractorRecord.prepared(
        verification_policy=_policy(),
        epic_id=EPIC_ID,
        stage_id=STAGE_ID,
        attempt=1,
        target_ref=TARGET_REF,
        expected_base_commit=base,
    ).admitted(ROOT_ID)
    git, paths, export = _landing_context(repo, tmp_path)
    ContractorAdapter(
        fake_client, closure=export.closure, records=export.records
    ).prepare(STAGE_ID, admitted.model_copy(update={"state": ContractorState.PREPARED}))
    ContractorAdapter(
        fake_client, closure=export.closure, records=export.records
    ).admit(
        STAGE_ID,
        admitted.model_copy(update={"state": ContractorState.PREPARED}),
        root_id=ROOT_ID,
    )
    gate = _GateAuthority(artifact_oid, tree, gate_verifier, sign_payload)
    repository_gate = _RepositoryGate(artifact_oid, tree)
    landing = PhaseLanding(
        ContractorAdapter(fake_client, closure=export.closure, records=export.records),
        git,
        repo,
        paths,
        gate,
        repository_gate,
        hooks=_CrashAfterCas(),
        export=export,
    )

    with pytest.raises(InjectedCrash, match="post-CAS interruption"):
        landing.land(STAGE_ID)

    assert _ref_target(repo) == artifact_oid
    assert git.ref_target(TARGET_REF, cwd=repo) == artifact_oid
    recovered = PhaseLanding(
        ContractorAdapter(fake_client, closure=export.closure, records=export.records),
        git,
        repo,
        paths,
        gate,
        repository_gate,
        export=export,
    ).recover(STAGE_ID)

    assert recovered.disposition is LandingDisposition.CLOSED
    assert _ref_target(repo) == artifact_oid
    assert fake_bd.rows[STAGE_ID]["status"] == "closed"
    assert gate.calls == 2
    assert repository_gate.calls == 2


def test_closed_recovery_uses_the_disk_receipt_digest_without_redriving_close(
    fake_bd: FakeBd,
    fake_client: BdClient,
    gate_verifier: GateVerifier,
    sign_payload: Signer,
    tmp_path: Path,
) -> None:
    """A closed stage keeps the close reason named by its durable receipt."""
    repo, base = _temporary_repo(tmp_path)
    artifact_oid, tree = _commit_artifact(repo)
    fake_bd.rows[STAGE_ID] = _stage_row()
    git, paths, export = _landing_context(repo, tmp_path)
    adapter = ContractorAdapter(
        fake_client, closure=export.closure, records=export.records
    )
    prepared = ContractorRecord.prepared(
        verification_policy=_policy(),
        epic_id=EPIC_ID,
        stage_id=STAGE_ID,
        attempt=1,
        target_ref=TARGET_REF,
        expected_base_commit=base,
    )
    adapter.prepare(STAGE_ID, prepared)
    adapter.admit(STAGE_ID, prepared, root_id=ROOT_ID)
    gate = _GateAuthority(artifact_oid, tree, gate_verifier, sign_payload)

    landed = PhaseLanding(
        adapter,
        git,
        repo,
        paths,
        gate,
        _RepositoryGate(artifact_oid, tree, ("receipt written to disk",)),
        export=export,
    ).land(STAGE_ID)
    receipt = read_record(paths.instance_dir / LANDING_RECEIPT_FILE, LandingReceipt)
    assert receipt is not None
    receipt_digest = hashlib.sha256(record_bytes(receipt)).hexdigest()
    before_closes = fake_bd.command_count("close")

    recovered = PhaseLanding(
        adapter,
        git,
        repo,
        paths,
        gate,
        _RepositoryGate(artifact_oid, tree, ("rebuilt green diagnostic",)),
        export=export,
    ).recover(STAGE_ID)

    assert landed.disposition is LandingDisposition.CLOSED
    assert recovered.disposition is LandingDisposition.CLOSED
    assert fake_bd.rows[STAGE_ID]["close_reason"] == MSG_CLOSE_REASON.format(
        digest=receipt_digest
    )
    assert fake_bd.command_count("close") == before_closes


def test_recovery_after_receipt_write_persists_the_disk_receipt_digest(
    fake_bd: FakeBd,
    fake_client: BdClient,
    gate_verifier: GateVerifier,
    sign_payload: Signer,
    tmp_path: Path,
) -> None:
    """A pre-relation crash records the receipt digest read back during recovery."""
    repo, base = _temporary_repo(tmp_path)
    artifact_oid, tree = _commit_artifact(repo)
    fake_bd.rows[STAGE_ID] = _stage_row()
    git, paths, export = _landing_context(repo, tmp_path)
    # The relation write is a ledger transition since S4 (§3.2, R4): the crash
    # this case is about is armed on the record store, not on bd.
    records = CrashingContractorRecords(export.records)
    adapter = ContractorAdapter(fake_client, closure=export.closure, records=records)
    prepared = ContractorRecord.prepared(
        verification_policy=_policy(),
        epic_id=EPIC_ID,
        stage_id=STAGE_ID,
        attempt=1,
        target_ref=TARGET_REF,
        expected_base_commit=base,
    )
    adapter.prepare(STAGE_ID, prepared)
    adapter.admit(STAGE_ID, prepared, root_id=ROOT_ID)
    gate = _GateAuthority(artifact_oid, tree, gate_verifier, sign_payload)
    records.arm()

    with pytest.raises(InjectedRecordCrash, match="record update died"):
        PhaseLanding(
            adapter,
            git,
            repo,
            paths,
            gate,
            _RepositoryGate(artifact_oid, tree, ("receipt written to disk",)),
            export=export,
        ).land(STAGE_ID)

    receipt = read_record(paths.instance_dir / LANDING_RECEIPT_FILE, LandingReceipt)
    assert receipt is not None
    receipt_digest = hashlib.sha256(record_bytes(receipt)).hexdigest()
    before_closes = fake_bd.command_count("close")

    recovered = PhaseLanding(
        adapter,
        git,
        repo,
        paths,
        gate,
        _RepositoryGate(artifact_oid, tree, ("rebuilt green diagnostic",)),
        export=export,
    ).recover(STAGE_ID)

    assert recovered.disposition is LandingDisposition.CLOSED
    assert adapter.record(STAGE_ID).landing_receipt_digest == receipt_digest
    assert fake_bd.rows[STAGE_ID]["close_reason"] == MSG_CLOSE_REASON.format(
        digest=receipt_digest
    )
    assert fake_bd.command_count("close") == before_closes + 1


@pytest.mark.parametrize("field", ("signed_oid", "landed_oid"))
def test_recovery_returns_human_attention_for_mismatched_receipt_identity(
    fake_bd: FakeBd,
    fake_client: BdClient,
    gate_verifier: GateVerifier,
    sign_payload: Signer,
    tmp_path: Path,
    field: str,
) -> None:
    """A receipt bound to another artifact remains for an operator to reconcile."""
    repo, base = _temporary_repo(tmp_path)
    artifact_oid, tree = _commit_artifact(repo)
    fake_bd.rows[STAGE_ID] = _stage_row(status="in_progress")
    git, paths, export = _landing_context(repo, tmp_path)
    adapter = ContractorAdapter(
        fake_client, closure=export.closure, records=export.records
    )
    prepared = ContractorRecord.prepared(
        verification_policy=_policy(),
        epic_id=EPIC_ID,
        stage_id=STAGE_ID,
        attempt=1,
        target_ref=TARGET_REF,
        expected_base_commit=base,
    )
    adapter.prepare(STAGE_ID, prepared)
    adapter.admit(STAGE_ID, prepared, root_id=ROOT_ID)
    gate = _GateAuthority(artifact_oid, tree, gate_verifier, sign_payload)
    repository_gate = _RepositoryGate(artifact_oid, tree)
    fake_bd.crash_on("close")

    with pytest.raises(InjectedCrash, match="bd close died"):
        PhaseLanding(
            adapter, git, repo, paths, gate, repository_gate, export=export
        ).land(STAGE_ID)

    receipt_path = paths.instance_dir / LANDING_RECEIPT_FILE
    receipt = read_record(receipt_path, LandingReceipt)
    assert receipt is not None
    write_record(receipt_path, receipt.model_copy(update={field: base}))

    recovered = PhaseLanding(
        adapter, git, repo, paths, gate, repository_gate, export=export
    ).recover(STAGE_ID)

    assert recovered.disposition is LandingDisposition.HUMAN_ATTENTION
    assert fake_bd.rows[STAGE_ID]["status"] == "in_progress"


def test_landing_closed_stage_routes_to_recovery_without_a_second_cas(
    fake_bd: FakeBd,
    fake_client: BdClient,
    gate_verifier: GateVerifier,
    sign_payload: Signer,
    tmp_path: Path,
) -> None:
    """A human restore of H cannot make a completed stage land its old artifact again."""
    repo, base = _temporary_repo(tmp_path)
    artifact_oid, tree = _commit_artifact(repo)
    fake_bd.rows[STAGE_ID] = _stage_row()
    git, paths, export = _landing_context(repo, tmp_path)
    adapter = ContractorAdapter(
        fake_client, closure=export.closure, records=export.records
    )
    prepared = ContractorRecord.prepared(
        verification_policy=_policy(),
        epic_id=EPIC_ID,
        stage_id=STAGE_ID,
        attempt=1,
        target_ref=TARGET_REF,
        expected_base_commit=base,
    )
    adapter.prepare(STAGE_ID, prepared)
    adapter.admit(STAGE_ID, prepared, root_id=ROOT_ID)
    gate = _GateAuthority(artifact_oid, tree, gate_verifier, sign_payload)
    repository_gate = _RepositoryGate(artifact_oid, tree)
    landing = PhaseLanding(
        adapter, git, repo, paths, gate, repository_gate, export=export
    )

    assert landing.land(STAGE_ID).disposition is LandingDisposition.CLOSED
    subprocess.run(["git", "update-ref", TARGET_REF, base], cwd=repo, check=True)
    before_reflog = _reflog(repo)
    before_closes = fake_bd.command_count("close")

    repeated = landing.land(STAGE_ID)

    assert repeated.disposition is LandingDisposition.CLOSED
    assert repeated.reason == "validated historical completion"
    assert _ref_target(repo) == base
    assert _reflog(repo) == before_reflog
    assert fake_bd.command_count("close") == before_closes


def _ref_target(repo: Path) -> str:
    """Read the actual target ref so recovery tests never mock ref motion."""
    return subprocess.run(
        ["git", "rev-parse", TARGET_REF],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _reflog(repo: Path) -> tuple[str, ...]:
    """Capture the target's real ref-motion evidence before recovery runs."""
    return tuple(
        subprocess.run(
            ["git", "reflog", "show", "--format=%H", TARGET_REF],
            cwd=repo,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.splitlines()
    )


def test_recovery_refuses_unrelated_history_without_closing_or_moving_a_ref(
    fake_bd: FakeBd,
    fake_client: BdClient,
    gate_verifier: GateVerifier,
    sign_payload: Signer,
    tmp_path: Path,
) -> None:
    """An interrupted landing cannot turn unrelated post-CAS history into closure."""
    repo, base = _temporary_repo(tmp_path)
    artifact_oid, tree = _commit_artifact(repo)
    fake_bd.rows[STAGE_ID] = _stage_row(status="in_progress")
    git, paths, export = _landing_context(repo, tmp_path)
    adapter = ContractorAdapter(
        fake_client, closure=export.closure, records=export.records
    )
    prepared = ContractorRecord.prepared(
        verification_policy=_policy(),
        epic_id=EPIC_ID,
        stage_id=STAGE_ID,
        attempt=1,
        target_ref=TARGET_REF,
        expected_base_commit=base,
    )
    adapter.prepare(STAGE_ID, prepared)
    adapter.admit(STAGE_ID, prepared, root_id=ROOT_ID)
    gate = _GateAuthority(artifact_oid, tree, gate_verifier, sign_payload)
    repository_gate = _RepositoryGate(artifact_oid, tree)
    with pytest.raises(InjectedCrash):
        PhaseLanding(
            adapter,
            git,
            repo,
            paths,
            gate,
            repository_gate,
            hooks=_CrashAfterCas(),
            export=export,
        ).land(STAGE_ID)
    unrelated = subprocess.run(
        ["git", "commit-tree", f"{base}^{{tree}}", "-m", "unrelated"],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    subprocess.run(["git", "update-ref", TARGET_REF, unrelated], cwd=repo, check=True)
    before_recovery = _reflog(repo)

    result = PhaseLanding(
        adapter, git, repo, paths, gate, repository_gate, export=export
    ).recover(STAGE_ID)

    assert result.disposition is LandingDisposition.HUMAN_ATTENTION
    assert _ref_target(repo) == unrelated
    assert _reflog(repo) == before_recovery
    assert fake_bd.rows[STAGE_ID]["status"] == "in_progress"


def test_recovery_closes_when_a_descendant_contains_the_signed_artifact(
    fake_bd: FakeBd,
    fake_client: BdClient,
    gate_verifier: GateVerifier,
    sign_payload: Signer,
    tmp_path: Path,
) -> None:
    """A target descendant may finish closure but recovery still cannot move it."""
    repo, base = _temporary_repo(tmp_path)
    artifact_oid, tree = _commit_artifact(repo)
    fake_bd.rows[STAGE_ID] = _stage_row()
    git, paths, export = _landing_context(repo, tmp_path)
    adapter = ContractorAdapter(
        fake_client, closure=export.closure, records=export.records
    )
    prepared = ContractorRecord.prepared(
        verification_policy=_policy(),
        epic_id=EPIC_ID,
        stage_id=STAGE_ID,
        attempt=1,
        target_ref=TARGET_REF,
        expected_base_commit=base,
    )
    adapter.prepare(STAGE_ID, prepared)
    adapter.admit(STAGE_ID, prepared, root_id=ROOT_ID)
    gate = _GateAuthority(artifact_oid, tree, gate_verifier, sign_payload)
    repository_gate = _RepositoryGate(artifact_oid, tree)
    with pytest.raises(InjectedCrash):
        PhaseLanding(
            adapter,
            git,
            repo,
            paths,
            gate,
            repository_gate,
            hooks=_CrashAfterCas(),
            export=export,
        ).land(STAGE_ID)
    subprocess.run(["git", "checkout", "--quiet", "main"], cwd=repo, check=True)
    (repo / "descendant.txt").write_text("descendant\n", encoding="utf-8")
    subprocess.run(["git", "add", "descendant.txt"], cwd=repo, check=True)
    subprocess.run(
        ["git", "commit", "--quiet", "-m", "post-CAS descendant"],
        cwd=repo,
        check=True,
    )
    descendant = _ref_target(repo)
    before_recovery = _reflog(repo)

    result = PhaseLanding(
        adapter, git, repo, paths, gate, repository_gate, export=export
    ).recover(STAGE_ID)

    assert result.disposition is LandingDisposition.CLOSED
    assert _ref_target(repo) == descendant
    assert _reflog(repo) == before_recovery
    assert fake_bd.rows[STAGE_ID]["status"] == "closed"


def test_blocking_dependencies_tolerate_the_open_bd_relation_vocabulary(
    fake_bd: FakeBd, fake_client: BdClient
) -> None:
    """Only unfinished blocks rows prevent admission as bd adds relation types."""
    stage = _stage_row()
    stage["dependencies"] = [
        {
            "id": "epic",
            "status": "open",
            "dependency_type": "parent-child",
        },
        {
            "id": "closed-blocker",
            "status": "closed",
            "dependency_type": "blocks",
        },
        {
            "id": "tracks",
            "status": "open",
            "dependency_type": "tracks",
        },
        {
            "id": "related",
            "status": "open",
            "dependency_type": "related",
        },
        {
            "id": "discovered-from",
            "status": "open",
            "dependency_type": "discovered-from",
        },
        {
            "id": "until",
            "status": "open",
            "dependency_type": "until",
        },
        {
            "id": "caused-by",
            "status": "open",
            "dependency_type": "caused-by",
        },
        {
            "id": "validates",
            "status": "open",
            "dependency_type": "validates",
        },
        {
            "id": "relates-to",
            "status": "open",
            "dependency_type": "relates-to",
        },
        {
            "id": "supersedes",
            "status": "open",
            "dependency_type": "supersedes",
        },
        {
            "id": "future-dependency",
            "status": "open",
            "dependency_type": "future-dependency",
        },
        {
            "id": "open-blocker",
            "status": "open",
            "dependency_type": "blocks",
        },
    ]
    fake_bd.rows[STAGE_ID] = stage

    dependencies = ContractorAdapter(
        fake_client, closure=NoLedgerClosure(), records=MemoryContractorRecords()
    ).blocking_dependencies(STAGE_ID)

    assert tuple(dependency.id for dependency in dependencies) == ("open-blocker",)


def test_intent_before_cas_refuses_without_restarting_the_landing(
    fake_bd: FakeBd,
    fake_client: BdClient,
    gate_verifier: GateVerifier,
    sign_payload: Signer,
    tmp_path: Path,
) -> None:
    """An intact intent at H is operator work, never an automatic second CAS."""
    repo, base = _temporary_repo(tmp_path)
    artifact_oid, tree = _commit_artifact(repo)
    fake_bd.rows[STAGE_ID] = _stage_row(status="in_progress")
    git, paths, export = _landing_context(repo, tmp_path)
    adapter = ContractorAdapter(
        fake_client, closure=export.closure, records=export.records
    )
    prepared = ContractorRecord.prepared(
        verification_policy=_policy(),
        epic_id=EPIC_ID,
        stage_id=STAGE_ID,
        attempt=1,
        target_ref=TARGET_REF,
        expected_base_commit=base,
    )
    adapter.prepare(STAGE_ID, prepared)
    adapter.admit(STAGE_ID, prepared, root_id=ROOT_ID)
    gate = _GateAuthority(artifact_oid, tree, gate_verifier, sign_payload)
    repository_gate = _RepositoryGate(artifact_oid, tree)
    intent = LandingIntent(
        root_id=ROOT_ID,
        policy_digest=_policy().digest,
        ref=TARGET_REF,
        expected_base=base,
        artifact_oid=artifact_oid,
        tree=tree,
        gate_receipt_digest=gate.verify(ROOT_ID).digest,
        stage=STAGE_ID,
        attempt=1,
    )
    write_record(paths.instance_dir / "contract-landing.json", intent)
    before_recovery = _reflog(repo)

    result = PhaseLanding(
        adapter, git, repo, paths, gate, repository_gate, export=export
    ).recover(STAGE_ID)

    assert result.disposition is LandingDisposition.PENDING
    assert result.observed_target == base
    assert _ref_target(repo) == base
    assert _reflog(repo) == before_recovery
    assert fake_bd.rows[STAGE_ID]["status"] == "in_progress"


def test_repository_gate_discloses_t1_before_running_the_detached_checkout(
    tmp_path: Path,
) -> None:
    """Operator output names the trusted-code boundary before the gate can execute."""
    repo, _ = _temporary_repo(tmp_path)
    artifact_oid, tree = _commit_artifact(repo)
    git, paths, _export = _landing_context(repo, tmp_path)
    events: list[str] = []

    result = DetachedRepositoryGate(git, paths, _policy(), events.append).verify(
        artifact_oid, tree
    )
    assert events == [T1_MESSAGE]
    assert result.green
    assert result.results[0].exit_code == 0


def test_admitted_shipped_attempt_cannot_skip_landing_by_retry() -> None:
    assert (
        retry_refusal(
            ContractorState.ADMITTED, ("shipped",), Frontier(terminal_node="shipped")
        )
        is not None
    )


def test_landing_refuses_wrong_root_directory(
    fake_bd, fake_client, gate_verifier, sign_payload, tmp_path
):
    repo, base = _temporary_repo(tmp_path)
    oid, tree = _commit_artifact(repo)
    fake_bd.rows[STAGE_ID] = _stage_row()
    record = ContractorRecord.prepared(
        epic_id=EPIC_ID,
        stage_id=STAGE_ID,
        attempt=1,
        target_ref=TARGET_REF,
        expected_base_commit=base,
        verification_policy=_policy(),
    ).admitted(ROOT_ID)
    git, paths, export = _landing_context(repo, tmp_path)
    seeded_records(record, into=export.records)
    landing = PhaseLanding(
        ContractorAdapter(fake_client, closure=export.closure, records=export.records),
        git,
        repo,
        WrapperPaths(paths.config, "other-root"),
        _GateAuthority(oid, tree, gate_verifier, sign_payload),
        _RepositoryGate(oid, tree),
        export=export,
    )
    with pytest.raises(ValueError, match="ambiguous"):
        landing.land(STAGE_ID)
    assert _ref_target(repo) == base


def test_gate_view_refuses_a_different_root_with_same_key(
    fake_bd, fake_client, monkeypatch
):
    from workflow_interpreter.bdio.reads import WorkflowReads
    from workflow_interpreter.contractor.gate_view import contractor_gate_view

    record = ContractorRecord.prepared(
        epic_id=EPIC_ID,
        stage_id=STAGE_ID,
        attempt=1,
        target_ref=TARGET_REF,
        expected_base_commit=BASE_COMMIT,
    ).admitted(ROOT_ID)
    fake_bd.rows[STAGE_ID] = _stage_row()
    records = seeded_records(record)
    monkeypatch.setattr(
        ContractorAdapter,
        "from_config",
        classmethod(
            lambda *_, **kwargs: ContractorAdapter(
                fake_client,
                closure=NoLedgerClosure(),
                records=kwargs["records"],
            )
        ),
    )
    with pytest.raises(ContractorAdapterError, match="does not own"):
        contractor_gate_view(
            record.instance_key,
            fake_client.config,
            root_id="impostor",
            reads=WorkflowReads(fake_client),
            records=records,
        )


@pytest.mark.parametrize(
    "corruption",
    (
        "wrong-policy",
        "wrong-artifact",
        "missing",
        "duplicate",
        "failed",
        "wrong-command",
        "legacy",
        "target-moved",
    ),
)
def test_policy_correspondence_refuses_before_cas(
    fake_bd, fake_client, gate_verifier, sign_payload, tmp_path, monkeypatch, corruption
):
    repo, base = _temporary_repo(tmp_path)
    oid, tree = _commit_artifact(repo)
    fake_bd.rows[STAGE_ID] = _stage_row()
    git, paths, export = _landing_context(repo, tmp_path)
    record = ContractorRecord.prepared(
        epic_id=EPIC_ID,
        stage_id=STAGE_ID,
        attempt=1,
        target_ref=TARGET_REF,
        expected_base_commit=base,
        verification_policy=None if corruption == "legacy" else _policy(),
    ).admitted(ROOT_ID)
    seeded_records(record, into=export.records)
    repository = _RepositoryGate(oid, tree)
    observed = repository.verify(oid, tree)
    if corruption == "wrong-policy":
        observed = observed.model_copy(update={"policy_digest": "other"})
    if corruption == "wrong-artifact":
        observed = observed.model_copy(update={"artifact_oid": base})
    if corruption == "missing":
        observed = observed.model_copy(update={"results": ()})
    if corruption == "duplicate":
        observed = observed.model_copy(update={"results": observed.results * 2})
    if corruption in ("failed", "wrong-command"):
        item = observed.results[0].model_copy(
            update={"exit_code": 1} if corruption == "failed" else {"name": "different"}
        )
        observed = observed.model_copy(update={"results": (item,)})
    monkeypatch.setattr(repository, "verify", lambda *_: observed)
    if corruption == "target-moved":
        git.update_ref(TARGET_REF, oid, cwd=repo)
    before = _ref_target(repo)
    landing = PhaseLanding(
        ContractorAdapter(fake_client, closure=export.closure, records=export.records),
        git,
        repo,
        paths,
        _GateAuthority(oid, tree, gate_verifier, sign_payload),
        repository,
        export=export,
    )
    if corruption == "legacy":
        with pytest.raises(ValueError, match="policy"):
            landing.land(STAGE_ID)
    else:
        assert landing.land(STAGE_ID).disposition is not LandingDisposition.CLOSED
    assert _ref_target(repo) == before
    assert fake_bd.command_count("close") == 0
    assert not (paths.instance_dir / LANDING_RECEIPT_FILE).exists()
