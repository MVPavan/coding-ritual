"""Integration tests against a real bd 1.1.0 workspace.

Marked `bd` and skipped when the binary is absent. The workspace is a
throwaway created under `tmp_path_factory` (never this repo's `.beads`), and
EVERY assertion selects by `wf_root_id` — a nested bd workspace leaks the
outer project's beads into read paths (probed), so "all rows" would be a lie.

What lives here is what only a real bd can prove: that the §3 carriers survive
its storage layer, that its lossy surfaces are still lossy, and that the
wrapper's read-back guard catches them. Crash windows and interleavings live
in the fake-bd families, where they are deterministic.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import uuid
from pathlib import Path
from typing import Final

import pytest

from tests._bdio import (
    IMPLEMENT,
    REGION,
    RESOLVED_CONFIG,
    REVIEW,
    SHIP,
    TRIAGE,
    entry_request,
    handle,
    instance_key,
    load_definition,
    make_root,
    race_residue,
    run_to_close,
)
from tests.conftest import BRANCH_HEAD, Signer, branch_head
from workflow_interpreter import GraphDefinition, canonical_bytes
from workflow_interpreter.bdio import (
    BoundExceededError,
    BoundMutation,
    CanaryFailedError,
    GateArtifact,
    GatePayload,
    GateVerifier,
    LossyWriteError,
    NonceReplayError,
    PayloadMismatchError,
    StaleApprovalError,
    canonical_payload_bytes,
)
from workflow_interpreter.bdio.api import WorkflowStore
from workflow_interpreter.bdio.bounds import BoundKind
from workflow_interpreter.bdio.client import BdClient
from workflow_interpreter.bdio.config import BdConfig
from workflow_interpreter.bdio.wire import (
    BindsMode,
    BoundSetting,
    ConfigSource,
    EventPayload,
    Evidence,
    ExitRecord,
    GateOpenRequest,
    GateState,
    Lifecycle,
    MintReason,
    ResolvedSetting,
    WfKind,
)
from workflow_interpreter.schema.models import Outcome

pytestmark = pytest.mark.bd

BD_TIMEOUT_S: Final[float] = 60.0


@pytest.fixture(scope="session")
def definition() -> GraphDefinition:
    """The §2 canonical fixture, loaded and hashed once."""
    return load_definition()


# --- §11 canary ----------------------------------------------------------


def test_startup_canary_asserts_the_backend_and_round_trips_a_wisp(
    store: WorkflowStore,
) -> None:
    result = store.startup_canary()
    assert result.backend == "dolt"
    assert result.dolt_mode == "embedded"
    assert result.bd_version == "1.1.0"
    assert result.wisp_id


def test_the_canary_refuses_a_store_that_is_not_the_injected_workspace(
    bd_config: BdConfig, bd_workspace: Path
) -> None:
    # Backend identity alone would pass against ANY dolt store; §11 has to
    # assert WHICH workspace bd actually resolved. `-C <workspace>/sub`
    # succeeds — bd walks up to the project — but resolves a `repo_root` that
    # is NOT the injected path (probed 2026-08-25), which is exactly the
    # silent-redirect shape the canary must catch.
    nested = bd_workspace / "sub"
    nested.mkdir(exist_ok=True)
    elsewhere = bd_config.model_copy(update={"workspace": nested})
    with pytest.raises(CanaryFailedError, match="repo_root"):
        WorkflowStore(BdClient(elsewhere)).startup_canary()


def test_the_canary_names_the_cwd_requirement_when_bd_cannot_resolve_context(
    bd_config: BdConfig, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # `bd context` resolves against the PROCESS cwd as well as `-C`: outside a
    # git repository it exits 1 while every other read still works (probed
    # 2026-08-25). That surfaced as a raw BdCommandError, which routes nowhere
    # useful — the canary is where "refuse dispatch, and say why" belongs.
    monkeypatch.chdir(tmp_path)
    with pytest.raises(CanaryFailedError, match="git repository"):
        WorkflowStore(BdClient(bd_config)).startup_canary()


# --- §3.1 root -----------------------------------------------------------


def test_root_pins_the_canonical_body_byte_identically(
    store: WorkflowStore, definition: GraphDefinition
) -> None:
    root = make_root(store, definition)
    assert root.metadata.wf_root_id == root.root_id
    # The pinned body read back out of bd is byte-identical to what was pinned.
    assert root.metadata.graph_body.encode("utf-8") == canonical_bytes(
        definition.document
    )
    reloaded = store.reads.load_root(root.root_id)
    assert reloaded.definition.content_hash == definition.content_hash
    assert reloaded.metadata.graph_content_hash == definition.content_hash


def test_create_root_is_idempotent_on_its_instance_key(
    store: WorkflowStore, definition: GraphDefinition
) -> None:
    key = instance_key()
    first = store.create_root(
        instance_key=key, definition=definition, resolved_config=RESOLVED_CONFIG
    )
    second = store.create_root(
        instance_key=key, definition=definition, resolved_config=RESOLVED_CONFIG
    )
    assert first.root_id == second.root_id


# --- §3.2 mint idempotency ----------------------------------------------


def test_double_mint_of_one_key_produces_exactly_one_bead(
    store: WorkflowStore, definition: GraphDefinition
) -> None:
    # Drill 1's non-dispatch half: a crash after mint, then a re-tick.
    root = make_root(store, definition)
    first = store.mint_activation(root.root_id, entry_request())
    second = store.mint_activation(root.root_id, entry_request())

    assert first.created is True
    assert second.created is False
    assert first.activation.activation_id == second.activation.activation_id
    assert first.idempotency_key == second.idempotency_key
    found = store.reads.find_by_idempotency_key(root.root_id, first.idempotency_key)
    assert len(found) == 1
    assert len(store.reads.list_activations(root.root_id)) == 1


def test_the_derived_mint_facts_survive_a_bd_round_trip(
    store: WorkflowStore, definition: GraphDefinition
) -> None:
    root = make_root(store, definition)
    minted = store.mint_activation(root.root_id, entry_request()).activation
    reloaded = store.reads.load_activation(minted.activation_id)
    assert reloaded.metadata.region == REGION
    assert reloaded.metadata.round_no == 1
    assert reloaded.metadata.intended_base_commit == BRANCH_HEAD
    assert reloaded.metadata.mint_reason is MintReason.ENTRY


def test_the_activation_lifecycle_is_recorded_and_idempotent(
    store: WorkflowStore, definition: GraphDefinition
) -> None:
    root = make_root(store, definition)
    activation_id = store.mint_activation(
        root.root_id, entry_request()
    ).activation.activation_id
    assert store.record_dispatch(activation_id, handle()).metadata.lifecycle is (
        Lifecycle.DISPATCHED
    )
    # Re-applying a recorded state is a no-op (§5.1).
    assert store.record_dispatch(activation_id, handle()).metadata.handle == handle()

    store.record_exit(
        activation_id,
        ExitRecord(exit_code=0, ended_at="2026-08-25T00:01:00Z", reason="ok"),
    )
    recorded = store.record_evidence(activation_id, Evidence(note="verified"))
    assert recorded.metadata.evidence is not None

    closed = store.close_activation(activation_id, Outcome.DONE)
    assert closed.metadata.outcome is Outcome.DONE
    assert closed.bead.status == "closed"
    assert closed.bead.close_reason == "outcome=done"
    # A closed activation stays findable by its key — or a re-tick re-mints.
    assert (
        len(
            store.reads.find_by_idempotency_key(
                root.root_id, closed.metadata.idempotency_key
            )
        )
        == 1
    )
    assert store.close_activation(activation_id, Outcome.DONE).metadata.outcome is (
        Outcome.DONE
    )


def test_supersede_is_append_only(
    store: WorkflowStore, bd_client: BdClient, definition: GraphDefinition
) -> None:
    # A genuine race pair: two live beads under ONE idempotency key. §3.2
    # supersede now proves that relationship before closing anything.
    root = make_root(store, definition)
    winner = store.mint_activation(root.root_id, entry_request()).activation
    loser = race_residue(bd_client, winner)

    superseded = store.supersede_activation(loser.activation_id, winner.activation_id)
    assert superseded.metadata.superseded_by == winner.activation_id
    assert superseded.metadata.outcome is Outcome.SUPERSEDED
    assert superseded.bead.status == "closed"
    # The bead is still there — supersede never deletes.
    still_listed = {
        record.activation_id for record in store.reads.list_activations(root.root_id)
    }
    assert still_listed == {winner.activation_id, loser.activation_id}
    # Re-applying the same supersede is a no-op.
    assert store.supersede_activation(
        loser.activation_id, winner.activation_id
    ).metadata.outcome is (Outcome.SUPERSEDED)


# --- §3.3 events ---------------------------------------------------------


def test_event_payload_round_trips_inline_and_never_duplicates(
    store: WorkflowStore, definition: GraphDefinition
) -> None:
    root = make_root(store, definition)
    activation = store.mint_activation(root.root_id, entry_request()).activation
    payload = EventPayload(
        from_node=IMPLEMENT,
        outcome=Outcome.DONE,
        to_node=REVIEW,
        activation_id=activation.activation_id,
        seq=2,
        actor="wf-test-foreman",
    )
    first = store.append_event(root.root_id, payload)
    second = store.append_event(root.root_id, payload)

    assert first.id == second.id
    assert first.issue_type == WfKind.EVENT.value
    assert first.payload is not None
    stored = json.loads(first.payload)
    assert stored["from"] == IMPLEMENT
    assert stored["to"] == REVIEW
    assert stored["outcome"] == Outcome.DONE.value


# --- §10 bounds ----------------------------------------------------------


def test_the_instance_ceiling_refuses_the_next_mint(
    store: WorkflowStore, definition: GraphDefinition
) -> None:
    root = make_root(
        store,
        definition,
        ResolvedSetting(
            key=BoundSetting.MAX_TOTAL_ACTIVATIONS.at(),
            value=1,
            source=ConfigSource.INSTANCE_OVERRIDE,
        ),
    )
    first = store.mint_activation(root.root_id, entry_request()).activation
    run_to_close(store, first.activation_id, Outcome.DONE)
    with pytest.raises(BoundExceededError) as caught:
        store.mint_activation(
            root.root_id,
            entry_request(
                node=REVIEW,
                mint_reason=MintReason.EDGE,
                predecessor_activation_id=first.activation_id,
            ),
        )
    assert caught.value.refusal.bound is BoundKind.INSTANCE_CEILING


def test_an_exhausted_region_refuses_a_new_round(
    store: WorkflowStore, definition: GraphDefinition
) -> None:
    # `max_entries = 1`: round 1 executes, and the first back-edge arrival —
    # whose round the wrapper DERIVES as 2 — exhausts (§10.1).
    root = make_root(
        store,
        definition,
        ResolvedSetting(
            key=BoundSetting.MAX_ENTRIES.at(REGION),
            value=1,
            source=ConfigSource.INSTANCE_OVERRIDE,
        ),
    )
    first = store.mint_activation(root.root_id, entry_request()).activation
    run_to_close(store, first.activation_id, Outcome.DONE)
    review = store.mint_activation(
        root.root_id,
        entry_request(
            node=REVIEW,
            mint_reason=MintReason.EDGE,
            predecessor_activation_id=first.activation_id,
        ),
    ).activation
    run_to_close(store, review.activation_id, Outcome.REJECT)
    with pytest.raises(BoundExceededError) as caught:
        store.mint_activation(
            root.root_id,
            entry_request(
                mint_reason=MintReason.EDGE,
                predecessor_activation_id=review.activation_id,
            ),
        )
    assert caught.value.refusal.bound is BoundKind.REGION_ROUNDS


# --- §3.4 / §9 gates -----------------------------------------------------


def _ship_gate(source_id: str) -> GateOpenRequest:
    """The `ship` gate's opening transition."""
    return GateOpenRequest(
        gate_node=SHIP,
        outcomes=(Outcome.APPROVE, Outcome.ABANDON),
        source_activation_id=source_id,
        opening_outcome=Outcome.ACCEPT,
    )


def test_reopening_a_gate_re_finds_the_same_bead(
    store: WorkflowStore, definition: GraphDefinition
) -> None:
    # Drill 6: a re-tick converges, no duplicate gate.
    root = make_root(store, definition)
    source = store.mint_activation(root.root_id, entry_request()).activation
    request = _ship_gate(source.activation_id)
    first = store.open_gate(root.root_id, request)
    second = store.open_gate(root.root_id, request)
    assert first.gate_id == second.gate_id
    assert len(store.reads.list_gates(root.root_id)) == 1


def test_a_verified_payload_closes_the_gate_and_a_replayed_nonce_does_not(
    store: WorkflowStore, definition: GraphDefinition, sign_payload: Signer
) -> None:
    root = make_root(store, definition)
    source = store.mint_activation(root.root_id, entry_request()).activation
    gate = store.open_gate(root.root_id, _ship_gate(source.activation_id))

    nonce = uuid.uuid4().hex
    payload = GatePayload(
        graph_id=definition.document.graph.id,
        root_id=root.root_id,
        gate_key=gate.metadata.gate_key,
        outcome=Outcome.APPROVE,
        artifact=GateArtifact(commit_oid="c" * 40, tree_oid="t" * 40),
        nonce=nonce,
    )
    encoded = canonical_payload_bytes(payload)
    signature = sign_payload(encoded, None)

    closed = store.close_gate_verified(
        root.root_id, gate.gate_id, payload_bytes=encoded, signature=signature
    )
    assert closed.metadata.state is GateState.CLOSED
    assert closed.metadata.outcome is Outcome.APPROVE
    assert closed.metadata.verified_fingerprint is not None
    assert closed.metadata.nonce == nonce
    assert closed.bead.status == "closed"

    # Same nonce, a different gate of the same instance: refused (§9).
    second_gate = store.open_gate(
        root.root_id,
        GateOpenRequest(
            gate_node=TRIAGE,
            outcomes=(Outcome.REBUDGET, Outcome.ABANDON),
            source_activation_id=source.activation_id,
            opening_outcome=Outcome.FAIL_PLAN,
        ),
    )
    replay = GatePayload(
        graph_id=definition.document.graph.id,
        root_id=root.root_id,
        gate_key=second_gate.metadata.gate_key,
        outcome=Outcome.REBUDGET,
        artifact=GateArtifact(commit_oid="c" * 40, tree_oid="t" * 40),
        nonce=nonce,
        bound_mutation=BoundMutation(key=BoundSetting.MAX_ENTRIES.at(REGION), value=9),
    )
    replay_bytes = canonical_payload_bytes(replay)
    with pytest.raises(NonceReplayError):
        store.close_gate_verified(
            root.root_id,
            second_gate.gate_id,
            payload_bytes=replay_bytes,
            signature=sign_payload(replay_bytes, None),
        )
    assert store.reads.list_gates(root.root_id)[1].metadata.state is GateState.OPEN


def test_a_payload_for_another_gate_is_refused(
    store: WorkflowStore, definition: GraphDefinition, sign_payload: Signer
) -> None:
    root = make_root(store, definition)
    source = store.mint_activation(root.root_id, entry_request()).activation
    gate = store.open_gate(root.root_id, _ship_gate(source.activation_id))
    payload = GatePayload(
        graph_id=definition.document.graph.id,
        root_id=root.root_id,
        gate_key="a-different-gate",
        outcome=Outcome.APPROVE,
        artifact=GateArtifact(commit_oid="c" * 40, tree_oid="t" * 40),
        nonce=uuid.uuid4().hex,
    )
    encoded = canonical_payload_bytes(payload)
    with pytest.raises(PayloadMismatchError, match="gate_key"):
        store.close_gate_verified(
            root.root_id,
            gate.gate_id,
            payload_bytes=encoded,
            signature=sign_payload(encoded, None),
        )
    assert store.reads.list_gates(root.root_id)[0].metadata.state is GateState.OPEN


def test_a_verified_rebudget_persists_the_raised_bound_in_bd(
    store: WorkflowStore, definition: GraphDefinition, sign_payload: Signer
) -> None:
    # §10.4 through the only path that exists: a signed rebudget payload.
    # There is no longer an API by which a caller can write a bound directly.
    # Against a REAL bd, so the bound's home on the gate bead is exercised
    # through bd's own metadata merge and read-back, not the fake's.
    root = make_root(store, definition)
    source = store.mint_activation(root.root_id, entry_request()).activation
    gate = store.open_gate(
        root.root_id,
        GateOpenRequest(
            gate_node=TRIAGE,
            outcomes=(Outcome.REBUDGET, Outcome.ABANDON),
            source_activation_id=source.activation_id,
            opening_outcome=Outcome.FAIL_PLAN,
        ),
    )
    payload = GatePayload(
        graph_id=definition.document.graph.id,
        root_id=root.root_id,
        gate_key=gate.metadata.gate_key,
        outcome=Outcome.REBUDGET,
        artifact=GateArtifact(commit_oid="c" * 40, tree_oid="t" * 40),
        nonce=uuid.uuid4().hex,
        bound_mutation=BoundMutation(key=BoundSetting.MAX_ENTRIES.at(REGION), value=7),
    )
    encoded = canonical_payload_bytes(payload)
    closed = store.close_gate_verified(
        root.root_id,
        gate.gate_id,
        payload_bytes=encoded,
        signature=sign_payload(encoded, None),
    )
    assert closed.metadata.bound_key == BoundSetting.MAX_ENTRIES.at(REGION)
    assert closed.metadata.bound_value == 7
    assert (
        store.reads.effective_bound(root.root_id, BoundSetting.MAX_ENTRIES, REGION) == 7
    )


def test_a_mutable_gate_is_re_hashed_from_the_workspace_at_close(
    bd_client: BdClient,
    gate_verifier: GateVerifier,
    definition: GraphDefinition,
    sign_payload: Signer,
    tmp_path: Path,
) -> None:
    # End to end on real bd: the digest comes from the injected reader, and an
    # edit between approval and close leaves the gate open with a receipt.
    document = tmp_path / "plan.md"
    document.write_bytes(b"approved plan\n")
    store = WorkflowStore(
        bd_client,
        gate_verifier,
        artifact_reader=lambda ref: (tmp_path / ref).read_bytes(),
        branch_head_reader=branch_head,
    )
    approved_digest = hashlib.sha256(document.read_bytes()).hexdigest()
    root = make_root(store, definition)
    source = store.mint_activation(root.root_id, entry_request()).activation
    gate = store.open_gate(
        root.root_id,
        GateOpenRequest(
            gate_node=SHIP,
            outcomes=(Outcome.APPROVE, Outcome.ABANDON),
            source_activation_id=source.activation_id,
            opening_outcome=Outcome.ACCEPT,
            binds=BindsMode.MUTABLE,
            artifact_ref="plan.md",
            artifact_digest=approved_digest,
        ),
    )
    payload = GatePayload(
        graph_id=definition.document.graph.id,
        root_id=root.root_id,
        gate_key=gate.metadata.gate_key,
        outcome=Outcome.APPROVE,
        artifact=GateArtifact(sha256=approved_digest),
        nonce=uuid.uuid4().hex,
    )
    encoded = canonical_payload_bytes(payload)
    signature = sign_payload(encoded, None)

    document.write_bytes(b"quietly edited plan\n")
    with pytest.raises(StaleApprovalError):
        store.close_gate_verified(
            root.root_id, gate.gate_id, payload_bytes=encoded, signature=signature
        )
    still_open = store.reads.load_gate(gate.gate_id)
    assert still_open.metadata.state is GateState.OPEN
    assert still_open.metadata.stale_approval_receipts

    # Restore the approved bytes and the same approval now closes the gate.
    document.write_bytes(b"approved plan\n")
    closed = store.close_gate_verified(
        root.root_id, gate.gate_id, payload_bytes=encoded, signature=signature
    )
    assert closed.metadata.state is GateState.CLOSED


# --- lossy-write detection ----------------------------------------------


def test_a_value_bd_cannot_store_exactly_raises_instead_of_passing(
    bd_client: BdClient,
) -> None:
    # bd's JSON path rounds integers past float64 precision — silently, exit 0.
    with pytest.raises(LossyWriteError, match="read back as"):
        bd_client._create_bead(
            title="wf lossy probe",
            metadata={"wf_kind": "probe", "big": 12345678901234567890},
        )


def test_the_at_file_event_payload_trap_is_still_real_and_would_be_caught(
    bd_client: BdClient, bd_workspace: Path, tmp_path: Path
) -> None:
    # Re-confirms the §3.3 probe on this bd build: `--event-payload @file`
    # stores the LITERAL string and exits 0. The client cannot construct that
    # form, and its read-back guard would reject it if it ever could.
    payload_file = tmp_path / "evt.json"
    payload_file.write_text('{"from":"a"}', encoding="utf-8")
    created = subprocess.run(
        [
            "bd",
            "-C",
            str(bd_workspace),
            "create",
            "--title",
            "wf at-file trap probe",
            "--type",
            "event",
            "--event-payload",
            f"@{payload_file}",
            "--silent",
        ],
        check=True,
        capture_output=True,
        text=True,
        timeout=BD_TIMEOUT_S,
    )
    record = bd_client.show(created.stdout.strip())
    assert record.payload == f"@{payload_file}"
    with pytest.raises(LossyWriteError, match="unparseable"):
        BdClient._assert_event_payload(record, {"from": "a"})
