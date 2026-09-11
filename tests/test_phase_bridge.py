"""Focused proof for phase-bridge admission and recovery."""

from __future__ import annotations

import hashlib
import subprocess
import tempfile
from pathlib import Path
from typing import Final

import pytest

from tests._fake_bd import FakeBd, InjectedCrash
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
from workflow_interpreter.bdio.records import GateRecord, parse_gate
from workflow_interpreter.bdio.signing import payload_digest
from workflow_interpreter.bdio.wire import BeadRecord, GateMetadata
from workflow_interpreter.bridge import (
    AdmissionRefused,
    BridgeRoot,
    DetachedRepositoryGate,
    GateEvidence,
    LandingDisposition,
    LandingHooks,
    LandingIntent,
    LandingReceipt,
    PhaseAdapter,
    PhaseAdapterError,
    PhaseAdmission,
    PhaseBridgeRecord,
    PhaseBridgeState,
    PhaseLanding,
    RepositoryGateResult,
)
from workflow_interpreter.bridge.adapter import MSG_CLOSE_REASON
from workflow_interpreter.bridge.landing import LANDING_RECEIPT_FILE, T1_MESSAGE
from workflow_interpreter.bridge.models import INSTANCE_KEY_TEMPLATE
from workflow_interpreter.bridge.retry import RetryRefusal, retry_refusal
from workflow_interpreter.foreman.frontier import Frontier
from workflow_interpreter.schema.models import IsolationMode, Outcome
from workflow_interpreter.supervisor import Git
from workflow_interpreter.supervisor.config import SupervisorConfig
from workflow_interpreter.supervisor.paths import (
    WrapperPaths,
    read_record,
    record_bytes,
    write_record,
)
from workflow_interpreter.supervisor.sandbox import SandboxMode

EPIC_ID = "phase-1"
STAGE_ID = "stage-a"
TARGET_REF = "refs/heads/main"
BASE_COMMIT = "a" * 40
ROOT_ID: Final[str] = "bridge-root"
FUTURE_PHASE_BRIDGE_SCHEMA: Final[str] = "future-schema/99"
WRONG_INSTANCE_KEY: Final[str] = "not-the-derived-key"
REPEATED_PREVIOUS_ATTEMPT: Final[str] = "x"


def _stage_row() -> dict[str, object]:
    """Build the direct-child stage the bridge is allowed to admit."""
    return {
        "id": STAGE_ID,
        "title": "one stage",
        "status": "open",
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
    first = PhaseBridgeRecord.prepared(
        epic_id=EPIC_ID,
        stage_id=STAGE_ID,
        attempt=1,
        target_ref=TARGET_REF,
        expected_base_commit=BASE_COMMIT,
    )
    retry = first.next_attempt()

    assert first.instance_key == "phase-bridge:phase-1:stage-a:attempt:1"
    assert retry.instance_key == "phase-bridge:phase-1:stage-a:attempt:2"
    assert retry.previous_attempts == (first.instance_key,)


def test_phase_bridge_record_rejects_an_unknown_schema() -> None:
    """A journal must declare the pinned schema instead of accepting future records."""
    record = PhaseBridgeRecord.prepared(
        epic_id=EPIC_ID,
        stage_id=STAGE_ID,
        attempt=1,
        target_ref=TARGET_REF,
        expected_base_commit=BASE_COMMIT,
    )
    raw = record.model_dump(by_alias=True)
    raw["schema"] = FUTURE_PHASE_BRIDGE_SCHEMA

    with pytest.raises(ValueError, match="schema"):
        PhaseBridgeRecord.model_validate(raw)


def test_phase_bridge_record_rejects_an_underived_instance_key() -> None:
    """A journal key must identify its epic, stage, and attempt exactly."""
    record = PhaseBridgeRecord.prepared(
        epic_id=EPIC_ID,
        stage_id=STAGE_ID,
        attempt=1,
        target_ref=TARGET_REF,
        expected_base_commit=BASE_COMMIT,
    )
    raw = record.model_dump(by_alias=True)
    raw["instance_key"] = WRONG_INSTANCE_KEY

    with pytest.raises(ValueError, match="instance_key"):
        PhaseBridgeRecord.model_validate(raw)


def test_phase_bridge_record_rejects_invalid_previous_attempt_history() -> None:
    """A retry journal must retain each earlier attempt once and only once."""
    record = PhaseBridgeRecord.prepared(
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
        PhaseBridgeRecord.model_validate(raw)


@pytest.mark.parametrize("field", ("schema", "previous_attempts"))
def test_phase_bridge_record_rejects_truncated_journal_fields(field: str) -> None:
    """A nested metadata replacement cannot silently re-default identity fields."""
    record = PhaseBridgeRecord.prepared(
        epic_id=EPIC_ID,
        stage_id=STAGE_ID,
        attempt=1,
        target_ref=TARGET_REF,
        expected_base_commit=BASE_COMMIT,
    )
    raw = record.model_dump(by_alias=True)
    del raw[field]

    with pytest.raises(ValueError, match=field):
        PhaseBridgeRecord.model_validate(raw)


def test_phase_bridge_next_attempt_round_trips_through_validation() -> None:
    """The normal retry constructor remains a valid complete journal record."""
    retry = PhaseBridgeRecord.prepared(
        epic_id=EPIC_ID,
        stage_id=STAGE_ID,
        attempt=1,
        target_ref=TARGET_REF,
        expected_base_commit=BASE_COMMIT,
    ).next_attempt()

    assert PhaseBridgeRecord.model_validate(retry.model_dump(by_alias=True)) == retry


def test_phase_bridge_prepared_refuses_a_nonfirst_attempt() -> None:
    """Only next_attempt may attach genuine prior-attempt history."""
    with pytest.raises(ValueError, match="first attempt"):
        PhaseBridgeRecord.prepared(
            epic_id=EPIC_ID,
            stage_id=STAGE_ID,
            attempt=3,
            target_ref=TARGET_REF,
            expected_base_commit=BASE_COMMIT,
        )


def test_retry_refusal_allows_a_declared_terminal() -> None:
    """A listed terminal may mint the bridge's next root."""
    frontier = Frontier(terminal=True, terminal_node="abandoned")

    assert retry_refusal(PhaseBridgeState.CLOSED, ("abandoned",), frontier) is None


def test_retry_refusal_refuses_an_unlisted_terminal() -> None:
    """A terminal outside the retry declaration cannot mint another root."""
    frontier = Frontier(terminal=True, terminal_node="failed")

    assert (
        retry_refusal(PhaseBridgeState.CLOSED, ("abandoned",), frontier)
        is RetryRefusal.UNLISTED_TERMINAL
    )


def test_retry_refusal_refuses_a_root_without_a_terminal() -> None:
    """A root still in flight has no terminal eligible for retry."""
    frontier = Frontier()

    assert (
        retry_refusal(PhaseBridgeState.CLOSED, ("abandoned",), frontier)
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
        retry_refusal(PhaseBridgeState.CLOSED, ("abandoned",), frontier)
        is RetryRefusal.OPEN_HALT
    )


def test_retry_refusal_refuses_the_realistic_open_halt_frontier() -> None:
    """A live halt has no terminal until the foreman settles the root."""
    frontier = Frontier(open_halt=_gate(GateState.OPEN, gate_node="halt"))

    assert (
        retry_refusal(PhaseBridgeState.CLOSED, ("abandoned",), frontier)
        is RetryRefusal.OPEN_HALT
    )


def test_retry_refusal_gate_red_requires_an_approved_shipped_terminal() -> None:
    """A gate-red retry cannot bypass the prior root's ship approval."""
    frontier = Frontier(terminal=True, terminal_node="shipped")

    assert (
        retry_refusal(PhaseBridgeState.GATE_RED, ("shipped", "abandoned"), frontier)
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
        retry_refusal(PhaseBridgeState.GATE_RED, ("shipped", "abandoned"), frontier)
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
        retry_refusal(PhaseBridgeState.GATE_RED, ("shipped",), frontier)
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
        retry_refusal(PhaseBridgeState.GATE_RED, ("abandoned",), frontier)
        is RetryRefusal.GATE_RED_NOT_APPROVED_SHIPPED
    )


def test_adapter_writes_the_whole_record_then_claims_with_admission(
    fake_bd: FakeBd, fake_client: BdClient
) -> None:
    """Keep the stage journal complete across the prepare-to-admit boundary."""
    fake_bd.rows[STAGE_ID] = _stage_row()
    adapter = PhaseAdapter(fake_client)
    prepared = PhaseBridgeRecord.prepared(
        epic_id=EPIC_ID,
        stage_id=STAGE_ID,
        attempt=1,
        target_ref=TARGET_REF,
        expected_base_commit=BASE_COMMIT,
    )

    adapter.prepare(STAGE_ID, prepared)
    admitted = adapter.admit(STAGE_ID, prepared, root_id="wf-1")

    assert admitted.state is PhaseBridgeState.ADMITTED
    assert fake_bd.rows[STAGE_ID]["status"] == "in_progress"
    assert fake_bd.rows[STAGE_ID]["metadata"] == {
        "unrelated": {"preserved": True},
        "phase_bridge": admitted.model_dump(by_alias=True, mode="json"),
    }
    assert "--claim" in fake_bd.calls[-2][1]
    assert fake_bd.metadata_writes[-2]["phase_bridge"] == admitted.model_dump(
        by_alias=True, mode="json"
    )
    assert adapter.dependencies(STAGE_ID) == ()


@pytest.mark.parametrize(
    "stored_state", (PhaseBridgeState.ADMITTED, PhaseBridgeState.CLOSED)
)
def test_prepare_refuses_a_non_successor_over_a_later_stored_journal(
    fake_bd: FakeBd, fake_client: BdClient, stored_state: PhaseBridgeState
) -> None:
    """A same-attempt write cannot replace admitted or closed stage evidence."""
    stored = PhaseBridgeRecord.prepared(
        epic_id=EPIC_ID,
        stage_id=STAGE_ID,
        attempt=1,
        target_ref=TARGET_REF,
        expected_base_commit=BASE_COMMIT,
    ).admitted(ROOT_ID)
    if stored_state is PhaseBridgeState.CLOSED:
        stored = stored.closed()
    stage = _stage_row()
    stage["metadata"] = {"phase_bridge": stored.model_dump(by_alias=True, mode="json")}
    fake_bd.rows[STAGE_ID] = stage

    incoming = stored.model_copy(update={"state": PhaseBridgeState.PREPARED})

    with pytest.raises(PhaseAdapterError, match="requires stored state prepared"):
        PhaseAdapter(fake_client).prepare(STAGE_ID, incoming)


@pytest.mark.parametrize(
    "stored_state", (PhaseBridgeState.ADMITTED, PhaseBridgeState.GATE_RED)
)
def test_prepare_accepts_a_valid_successor_over_an_unsettled_journal(
    fake_bd: FakeBd, fake_client: BdClient, stored_state: PhaseBridgeState
) -> None:
    """A retry advances a settled-not-closed stage journal by one attempt."""
    stored = PhaseBridgeRecord.prepared(
        epic_id=EPIC_ID,
        stage_id=STAGE_ID,
        attempt=1,
        target_ref=TARGET_REF,
        expected_base_commit=BASE_COMMIT,
    ).admitted(ROOT_ID)
    stored = stored.model_copy(update={"state": stored_state})
    stage = _stage_row()
    stage["metadata"] = {"phase_bridge": stored.model_dump(by_alias=True, mode="json")}
    fake_bd.rows[STAGE_ID] = stage

    successor = PhaseAdapter(fake_client).prepare(STAGE_ID, stored.next_attempt())

    assert successor == stored.next_attempt()


def test_prepare_refuses_a_structural_successor_over_a_closed_journal(
    fake_bd: FakeBd, fake_client: BdClient
) -> None:
    """No retry structure can reopen evidence for a stage that landed and closed."""
    stored = (
        PhaseBridgeRecord.prepared(
            epic_id=EPIC_ID,
            stage_id=STAGE_ID,
            attempt=1,
            target_ref=TARGET_REF,
            expected_base_commit=BASE_COMMIT,
        )
        .admitted(ROOT_ID)
        .closed()
    )
    stage = _stage_row()
    stage["metadata"] = {"phase_bridge": stored.model_dump(by_alias=True, mode="json")}
    fake_bd.rows[STAGE_ID] = stage

    with pytest.raises(PhaseAdapterError, match="refuses a closed stored record"):
        PhaseAdapter(fake_client).prepare(STAGE_ID, stored.next_attempt())


def test_prepare_refuses_a_nonprepared_incoming_journal(
    fake_bd: FakeBd, fake_client: BdClient
) -> None:
    """The supplied record is named when it is not a prepare intent."""
    fake_bd.rows[STAGE_ID] = _stage_row()
    incoming = PhaseBridgeRecord.prepared(
        epic_id=EPIC_ID,
        stage_id=STAGE_ID,
        attempt=1,
        target_ref=TARGET_REF,
        expected_base_commit=BASE_COMMIT,
    ).admitted(ROOT_ID)

    with pytest.raises(
        PhaseAdapterError, match="incoming phase bridge record expected state"
    ):
        PhaseAdapter(fake_client).prepare(STAGE_ID, incoming)


def test_prepare_wraps_unreadable_stored_journal(
    fake_bd: FakeBd, fake_client: BdClient
) -> None:
    """Corrupt stored bridge metadata stays behind the adapter error boundary."""
    stage = _stage_row()
    stage["metadata"] = {"phase_bridge": {"state": "not-a-bridge-state"}}
    fake_bd.rows[STAGE_ID] = stage
    incoming = PhaseBridgeRecord.prepared(
        epic_id=EPIC_ID,
        stage_id=STAGE_ID,
        attempt=1,
        target_ref=TARGET_REF,
        expected_base_commit=BASE_COMMIT,
    )

    with pytest.raises(
        PhaseAdapterError, match="stored phase bridge record is unreadable"
    ):
        PhaseAdapter(fake_client).prepare(STAGE_ID, incoming)


class _Roots:
    """Script the root and branch seams around a real temporary Git history."""

    def __init__(self, fake_client: BdClient, repo: Path, base: str) -> None:
        self._client = fake_client
        self._repo = repo
        self._base = base
        self._roots: dict[str, BridgeRoot] = {}
        self._branches: set[str] = set()
        self.fail_branch = False

    def find(self, instance_key: str) -> BridgeRoot | None:
        """Find the root already created for an admission identity."""
        found = self._roots.get(instance_key)
        if found is not None:
            return found
        for row in self._client.list_beads(
            metadata_filters={"instance_key": instance_key}
        ):
            self._client._merge_metadata(row.id, {"root_id": row.id})
            recovered = BridgeRoot(
                root_id=row.id,
                instance_key=instance_key,
                instance_base_commit=str(row.metadata["base"]),
            )
            self._roots[instance_key] = recovered
            return recovered
        return None

    def create(self, instance_key: str) -> BridgeRoot:
        """Create one fake root through the real bd transport seam."""
        root = self._client._create_bead(
            title="phase root",
            metadata={"instance_key": instance_key, "base": self._base},
        )
        self._client._merge_metadata(root.id, {"root_id": root.id})
        created = BridgeRoot(
            root_id=root.id,
            instance_key=instance_key,
            instance_base_commit=self._base,
        )
        self._roots[instance_key] = created
        return created

    def ensure_branch(self, root: BridgeRoot) -> None:
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
    admission = PhaseAdmission(PhaseAdapter(fake_client), roots, lambda: base)
    fake_bd.crash_on("create")

    with pytest.raises(InjectedCrash, match="bd create died"):
        admission.admit(EPIC_ID, STAGE_ID, TARGET_REF, base)

    recovered = admission.admit(EPIC_ID, STAGE_ID, TARGET_REF, base)

    assert recovered.state is PhaseBridgeState.ADMITTED
    assert fake_bd.command_count("create") == 2
    assert len(roots._roots) == 1
    assert fake_bd.rows[STAGE_ID]["metadata"]["phase_bridge"] == recovered.model_dump(
        by_alias=True, mode="json"
    )


def test_admission_repairs_a_root_interrupted_before_its_self_link(
    fake_bd: FakeBd, fake_client: BdClient, tmp_path: Path
) -> None:
    """Reuse the one raw root left between create and self-link."""
    fake_bd.rows[STAGE_ID] = _stage_row()
    repo, base = _temporary_repo(tmp_path)
    roots = _Roots(fake_client, repo, base)
    admission = PhaseAdmission(PhaseAdapter(fake_client), roots, lambda: base)
    fake_bd.crash_on("update", occurrence=2)

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
    admission = PhaseAdmission(PhaseAdapter(fake_client), roots, lambda: head[0])

    with pytest.raises(InjectedCrash, match="branch creation died"):
        admission.admit(EPIC_ID, STAGE_ID, TARGET_REF, base)
    head[0] = "b" * 40

    recovered = admission.admit(EPIC_ID, STAGE_ID, TARGET_REF, base)

    assert recovered.state is PhaseBridgeState.ADMITTED
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
    prepared_root = roots.create("phase-bridge:phase-1:stage-a:attempt:1")
    admission = PhaseAdmission(PhaseAdapter(fake_client), roots, lambda: base)
    fake_bd.crash_on("update", occurrence=2)

    with pytest.raises(InjectedCrash, match="bd update died"):
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
    adapter = PhaseAdapter(fake_client)
    admission = PhaseAdmission(adapter, roots, lambda: base)

    admitted = admission.admit(EPIC_ID, STAGE_ID, TARGET_REF, base)
    landed = admitted.landed(base, "b" * 40, "gate-receipt", "landing-receipt")
    adapter.land(STAGE_ID, landed)

    with pytest.raises(AdmissionRefused, match="unfinished bridge admission"):
        admission.admit(EPIC_ID, other_stage_id, TARGET_REF, base)

    adapter.close(STAGE_ID, landed.closed(), "landing-receipt")
    other = admission.admit(EPIC_ID, other_stage_id, TARGET_REF, base)

    assert other.state is PhaseBridgeState.ADMITTED


def test_conflicting_record_refuses_without_creating_a_root(
    fake_bd: FakeBd, fake_client: BdClient, tmp_path: Path
) -> None:
    """Leave ambiguous identity for a human instead of opening another journal."""
    conflicting = PhaseBridgeRecord.prepared(
        epic_id=EPIC_ID,
        stage_id=STAGE_ID,
        attempt=1,
        target_ref=TARGET_REF,
        expected_base_commit="c" * 40,
    )
    stage = _stage_row()
    stage["metadata"] = {"phase_bridge": conflicting.model_dump(by_alias=True)}
    fake_bd.rows[STAGE_ID] = stage
    repo, base = _temporary_repo(tmp_path)
    roots = _Roots(fake_client, repo, base)
    admission = PhaseAdmission(PhaseAdapter(fake_client), roots, lambda: base)

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
            graph_id="phase-bridge",
            root_id=root_id,
            gate_key="ship",
            outcome=Outcome.ACCEPT,
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
        return GateEvidence(
            root_id=root_id,
            gate_node="ship",
            closed=True,
            immutable=True,
            accepted=True,
            artifact_oid=self._artifact_oid,
            tree=self._tree,
            fingerprint=approval.fingerprint,
            digest=payload_digest(encoded),
            artifact_ref=self._artifact_oid,
        )


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
            results=self._results,
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


def _landing_context(repo: Path, tmp_path: Path) -> tuple[Git, WrapperPaths]:
    """Build the real Git and wrapper-path services for one temporary history."""
    config = SupervisorConfig(
        repo_root=repo,
        wrapper_root=tmp_path / "bridge-wrapper",
        host="bridge-test",
        sandbox=SandboxMode.OFF,
    )
    return Git(config), WrapperPaths(config, ROOT_ID)


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
    adapter = PhaseAdapter(fake_client)
    prepared = PhaseBridgeRecord.prepared(
        epic_id=EPIC_ID,
        stage_id=STAGE_ID,
        attempt=1,
        target_ref=TARGET_REF,
        expected_base_commit=base,
    )
    adapter.prepare(STAGE_ID, prepared)
    git, paths = _landing_context(repo, tmp_path)
    landing = PhaseLanding(
        adapter,
        git,
        repo,
        paths,
        _GateAuthority(base, "b" * 40, gate_verifier, sign_payload),
        _RepositoryGate(base, "b" * 40),
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
    admitted = PhaseBridgeRecord.prepared(
        epic_id=EPIC_ID,
        stage_id=STAGE_ID,
        attempt=1,
        target_ref=TARGET_REF,
        expected_base_commit=base,
    ).admitted(ROOT_ID)
    PhaseAdapter(fake_client).prepare(
        STAGE_ID, admitted.model_copy(update={"state": PhaseBridgeState.PREPARED})
    )
    PhaseAdapter(fake_client).admit(
        STAGE_ID,
        admitted.model_copy(update={"state": PhaseBridgeState.PREPARED}),
        root_id=ROOT_ID,
    )
    gate = _GateAuthority(artifact_oid, tree, gate_verifier, sign_payload)
    repository_gate = _RepositoryGate(artifact_oid, tree)
    git, paths = _landing_context(repo, tmp_path)
    landing = PhaseLanding(
        PhaseAdapter(fake_client),
        git,
        repo,
        paths,
        gate,
        repository_gate,
        hooks=_CrashAfterCas(),
    )

    with pytest.raises(InjectedCrash, match="post-CAS interruption"):
        landing.land(STAGE_ID)

    assert _ref_target(repo) == artifact_oid
    assert git.ref_target(TARGET_REF, cwd=repo) == artifact_oid
    recovered = PhaseLanding(
        PhaseAdapter(fake_client),
        git,
        repo,
        paths,
        gate,
        repository_gate,
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
    adapter = PhaseAdapter(fake_client)
    prepared = PhaseBridgeRecord.prepared(
        epic_id=EPIC_ID,
        stage_id=STAGE_ID,
        attempt=1,
        target_ref=TARGET_REF,
        expected_base_commit=base,
    )
    adapter.prepare(STAGE_ID, prepared)
    adapter.admit(STAGE_ID, prepared, root_id=ROOT_ID)
    gate = _GateAuthority(artifact_oid, tree, gate_verifier, sign_payload)
    git, paths = _landing_context(repo, tmp_path)

    landed = PhaseLanding(
        adapter,
        git,
        repo,
        paths,
        gate,
        _RepositoryGate(artifact_oid, tree, ("receipt written to disk",)),
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
    adapter = PhaseAdapter(fake_client)
    prepared = PhaseBridgeRecord.prepared(
        epic_id=EPIC_ID,
        stage_id=STAGE_ID,
        attempt=1,
        target_ref=TARGET_REF,
        expected_base_commit=base,
    )
    adapter.prepare(STAGE_ID, prepared)
    adapter.admit(STAGE_ID, prepared, root_id=ROOT_ID)
    gate = _GateAuthority(artifact_oid, tree, gate_verifier, sign_payload)
    git, paths = _landing_context(repo, tmp_path)
    fake_bd.crash_on("update")

    with pytest.raises(InjectedCrash, match="bd update died"):
        PhaseLanding(
            adapter,
            git,
            repo,
            paths,
            gate,
            _RepositoryGate(artifact_oid, tree, ("receipt written to disk",)),
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
    fake_bd.rows[STAGE_ID] = _stage_row()
    adapter = PhaseAdapter(fake_client)
    prepared = PhaseBridgeRecord.prepared(
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
    git, paths = _landing_context(repo, tmp_path)
    fake_bd.crash_on("close")

    with pytest.raises(InjectedCrash, match="bd close died"):
        PhaseLanding(adapter, git, repo, paths, gate, repository_gate).land(STAGE_ID)

    receipt_path = paths.instance_dir / LANDING_RECEIPT_FILE
    receipt = read_record(receipt_path, LandingReceipt)
    assert receipt is not None
    write_record(receipt_path, receipt.model_copy(update={field: base}))

    recovered = PhaseLanding(adapter, git, repo, paths, gate, repository_gate).recover(
        STAGE_ID
    )

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
    adapter = PhaseAdapter(fake_client)
    prepared = PhaseBridgeRecord.prepared(
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
    git, paths = _landing_context(repo, tmp_path)
    landing = PhaseLanding(adapter, git, repo, paths, gate, repository_gate)

    assert landing.land(STAGE_ID).disposition is LandingDisposition.CLOSED
    subprocess.run(["git", "update-ref", TARGET_REF, base], cwd=repo, check=True)
    before_reflog = _reflog(repo)
    before_closes = fake_bd.command_count("close")

    repeated = landing.land(STAGE_ID)

    assert repeated.disposition is LandingDisposition.HUMAN_ATTENTION
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
    fake_bd.rows[STAGE_ID] = _stage_row()
    adapter = PhaseAdapter(fake_client)
    prepared = PhaseBridgeRecord.prepared(
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
    git, paths = _landing_context(repo, tmp_path)
    with pytest.raises(InjectedCrash):
        PhaseLanding(
            adapter,
            git,
            repo,
            paths,
            gate,
            repository_gate,
            hooks=_CrashAfterCas(),
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

    result = PhaseLanding(adapter, git, repo, paths, gate, repository_gate).recover(
        STAGE_ID
    )

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
    adapter = PhaseAdapter(fake_client)
    prepared = PhaseBridgeRecord.prepared(
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
    git, paths = _landing_context(repo, tmp_path)
    with pytest.raises(InjectedCrash):
        PhaseLanding(
            adapter,
            git,
            repo,
            paths,
            gate,
            repository_gate,
            hooks=_CrashAfterCas(),
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

    result = PhaseLanding(adapter, git, repo, paths, gate, repository_gate).recover(
        STAGE_ID
    )

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

    dependencies = PhaseAdapter(fake_client).blocking_dependencies(STAGE_ID)

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
    fake_bd.rows[STAGE_ID] = _stage_row()
    adapter = PhaseAdapter(fake_client)
    prepared = PhaseBridgeRecord.prepared(
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
    git, paths = _landing_context(repo, tmp_path)
    intent = LandingIntent(
        ref=TARGET_REF,
        expected_base=base,
        artifact_oid=artifact_oid,
        tree=tree,
        gate_receipt_digest=gate.verify(ROOT_ID).digest,
        stage=STAGE_ID,
        attempt=1,
    )
    write_record(paths.instance_dir / "phase-bridge-landing.json", intent)
    before_recovery = _reflog(repo)

    result = PhaseLanding(adapter, git, repo, paths, gate, repository_gate).recover(
        STAGE_ID
    )

    assert result.disposition is LandingDisposition.HUMAN_ATTENTION
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
    git, paths = _landing_context(repo, tmp_path)
    events: list[str] = []

    def checks(checkout: Path, candidate: str) -> tuple[str, ...]:
        """Prove the production gate receives a clean detached candidate tree."""
        assert candidate == artifact_oid
        assert (
            subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=checkout,
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip()
            == artifact_oid
        )
        assert events == [T1_MESSAGE]
        return ("five numbered items / six commands green",)

    result = DetachedRepositoryGate(git, paths, checks, events.append).verify(
        artifact_oid, tree
    )

    assert result.results == ("five numbered items / six commands green",)
