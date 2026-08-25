"""§9 gate security — every refusal path, with real signatures.

A real `ssh-keygen` signs and verifies; the store runs against the in-memory
bd. That combination is what makes these paths testable at all: they need a
signed payload AND a controllable workspace, and none of them were covered
before (phase-2 review, finding 7).
"""

from __future__ import annotations

import hashlib

import pytest

from tests._bdio import (
    REGION,
    RESOLVED_CONFIG,
    SHIP,
    TRIAGE,
    entry_request,
    load_definition,
    make_root,
)
from tests._fake_bd import FakeBd, InjectedCrash
from tests._gates import (
    approval_payload,
    close,
    open_mutable_gate,
    open_ship_gate,
    open_triage_gate,
)
from tests.conftest import (
    APPROVED_TEXT,
    EDITED_TEXT,
    PLAN_REF,
    Documents,
    Signer,
    branch_head,
)
from workflow_interpreter import GraphDefinition
from workflow_interpreter.bdio import (
    BoundMutation,
    GateArtifact,
    GateVerificationError,
    GateVerifier,
    LifecycleConflictError,
    NonceReplayError,
    PayloadMismatchError,
    StaleApprovalError,
    canonical_payload_bytes,
)
from workflow_interpreter.bdio.api import WorkflowStore
from workflow_interpreter.bdio.client import BdClient
from workflow_interpreter.bdio.errors import BdConfigError
from workflow_interpreter.bdio.signing import payload_digest
from workflow_interpreter.bdio.wire import (
    BoundSetting,
    GateOpenRequest,
    GateState,
    metadata_dict,
)
from workflow_interpreter.schema.models import Outcome


@pytest.fixture(scope="session")
def definition() -> GraphDefinition:
    """The §2 canonical fixture, loaded and hashed once."""
    return load_definition()


# --- the happy path ------------------------------------------------------


def test_a_verified_approval_closes_the_gate(
    gate_store: WorkflowStore, definition: GraphDefinition, sign_payload: Signer
) -> None:
    root_id, gate = open_ship_gate(gate_store, definition)
    payload = approval_payload(root_id, gate)
    closed = close(gate_store, root_id, gate, payload, sign_payload)
    assert closed.metadata.state is GateState.CLOSED
    assert closed.metadata.outcome is Outcome.APPROVE
    assert closed.metadata.nonce == payload.nonce
    assert closed.metadata.verified_fingerprint is not None
    assert closed.bead.status == "closed"


# --- mutable artifacts: the wrapper re-hashes (§9 ruling) ---------------


def test_a_mutable_artifact_is_re_hashed_by_the_wrapper(
    gate_store: WorkflowStore, definition: GraphDefinition, sign_payload: Signer
) -> None:
    root_id, gate = open_mutable_gate(gate_store, definition)
    payload = approval_payload(
        root_id,
        gate,
        artifact=GateArtifact(sha256=hashlib.sha256(APPROVED_TEXT).hexdigest()),
    )
    closed = close(gate_store, root_id, gate, payload, sign_payload)
    assert closed.metadata.state is GateState.CLOSED


def test_an_edited_document_refuses_and_records_an_edit_receipt(
    gate_store: WorkflowStore,
    documents: Documents,
    definition: GraphDefinition,
    sign_payload: Signer,
) -> None:
    # The whole point of the ruling: the digest is computed from the bytes the
    # injected reader returns, so echoing the approved value cannot help.
    root_id, gate = open_mutable_gate(gate_store, definition)
    payload = approval_payload(
        root_id,
        gate,
        artifact=GateArtifact(sha256=hashlib.sha256(APPROVED_TEXT).hexdigest()),
    )
    documents.contents[PLAN_REF] = EDITED_TEXT
    with pytest.raises(StaleApprovalError, match="approved sha256"):
        close(gate_store, root_id, gate, payload, sign_payload)

    still_open = gate_store.reads.load_gate(gate.gate_id)
    assert still_open.metadata.state is GateState.OPEN
    assert still_open.bead.status == "open"
    assert len(still_open.metadata.stale_approval_receipts) == 1


def test_an_unreadable_artifact_refuses_and_still_writes_the_receipt(
    gate_store: WorkflowStore,
    documents: Documents,
    definition: GraphDefinition,
    sign_payload: Signer,
) -> None:
    # The path the review found raising WITHOUT the receipt it claimed.
    root_id, gate = open_mutable_gate(gate_store, definition)
    payload = approval_payload(
        root_id,
        gate,
        artifact=GateArtifact(sha256=hashlib.sha256(APPROVED_TEXT).hexdigest()),
    )
    del documents.contents[PLAN_REF]
    with pytest.raises(StaleApprovalError, match="could not be read"):
        close(gate_store, root_id, gate, payload, sign_payload)
    still_open = gate_store.reads.load_gate(gate.gate_id)
    assert still_open.metadata.state is GateState.OPEN
    assert len(still_open.metadata.stale_approval_receipts) == 1


def test_without_an_artifact_reader_a_mutable_gate_cannot_close(
    fake_client: BdClient,
    gate_verifier: GateVerifier,
    definition: GraphDefinition,
    sign_payload: Signer,
) -> None:
    # Fail closed: no reader means no re-hash, and the caller's word is not a
    # substitute (there is no parameter for it any more).
    store = WorkflowStore(fake_client, gate_verifier, branch_head_reader=branch_head)
    root_id, gate = open_mutable_gate(store, definition)
    payload = approval_payload(
        root_id,
        gate,
        artifact=GateArtifact(sha256=hashlib.sha256(APPROVED_TEXT).hexdigest()),
    )
    with pytest.raises(BdConfigError, match="artifact_reader"):
        close(store, root_id, gate, payload, sign_payload)


def test_an_approval_missing_the_artifact_shape_its_gate_binds_is_refused(
    gate_store: WorkflowStore, definition: GraphDefinition, sign_payload: Signer
) -> None:
    root_id, gate = open_ship_gate(gate_store, definition)
    payload = approval_payload(root_id, gate, artifact=GateArtifact(sha256="a" * 64))
    with pytest.raises(PayloadMismatchError, match="commit_oid, tree_oid"):
        close(gate_store, root_id, gate, payload, sign_payload)
    assert gate_store.reads.load_gate(gate.gate_id).metadata.state is GateState.OPEN


# --- gate ownership and nonce scope (§9 ruling) -------------------------


def test_a_gate_belonging_to_another_instance_is_refused(
    gate_store: WorkflowStore, definition: GraphDefinition, sign_payload: Signer
) -> None:
    # Ownership is what makes per-root nonce scope sufficient: a payload for
    # instance A applied to instance B's gate fails before the nonce matters.
    first_root, first_gate = open_ship_gate(gate_store, definition)
    second_root, _ = open_ship_gate(gate_store, definition)
    payload = approval_payload(first_root, first_gate)
    encoded = canonical_payload_bytes(payload)
    with pytest.raises(PayloadMismatchError, match="wf_root_id"):
        gate_store.close_gate_verified(
            second_root,
            first_gate.gate_id,
            payload_bytes=encoded,
            signature=sign_payload(encoded, None),
        )


def test_a_nonce_replayed_against_a_second_root_fails_on_identity_not_scope(
    gate_store: WorkflowStore, definition: GraphDefinition, sign_payload: Signer
) -> None:
    # §9 ruling: nonce uniqueness is scoped PER ROOT. A cross-root replay is
    # defeated by the root_id inside the SIGNED payload, so it never reaches
    # the nonce check — which is why a cross-instance scan is unnecessary.
    first_root, first_gate = open_ship_gate(gate_store, definition)
    payload = approval_payload(first_root, first_gate)
    close(gate_store, first_root, first_gate, payload, sign_payload)

    second_root, second_gate = open_ship_gate(gate_store, definition)
    replay = approval_payload(
        first_root,
        second_gate,
        nonce=payload.nonce,
        gate_key=first_gate.metadata.gate_key,
    )
    encoded = canonical_payload_bytes(replay)
    with pytest.raises(PayloadMismatchError, match="root_id"):
        gate_store.close_gate_verified(
            second_root,
            second_gate.gate_id,
            payload_bytes=encoded,
            signature=sign_payload(encoded, None),
        )
    assert gate_store.reads.load_gate(second_gate.gate_id).metadata.state is (
        GateState.OPEN
    )


def test_a_nonce_replayed_inside_one_root_is_refused(
    gate_store: WorkflowStore, definition: GraphDefinition, sign_payload: Signer
) -> None:
    root = make_root(gate_store, definition)
    source = gate_store.mint_activation(root.root_id, entry_request()).activation
    first = gate_store.open_gate(
        root.root_id,
        GateOpenRequest(
            gate_node=SHIP,
            outcomes=(Outcome.APPROVE, Outcome.ABANDON),
            source_activation_id=source.activation_id,
            opening_outcome=Outcome.ACCEPT,
        ),
    )
    payload = approval_payload(root.root_id, first)
    close(gate_store, root.root_id, first, payload, sign_payload)

    second = gate_store.open_gate(
        root.root_id,
        GateOpenRequest(
            gate_node=TRIAGE,
            outcomes=(Outcome.REBUDGET, Outcome.ABANDON),
            source_activation_id=source.activation_id,
            opening_outcome=Outcome.FAIL_PLAN,
        ),
    )
    replay = approval_payload(
        root.root_id,
        second,
        outcome=Outcome.REBUDGET,
        nonce=payload.nonce,
        bound_mutation=BoundMutation(key=BoundSetting.MAX_ENTRIES.at(REGION), value=9),
    )
    with pytest.raises(NonceReplayError):
        close(gate_store, root.root_id, second, replay, sign_payload)


def test_an_outcome_the_gate_does_not_declare_is_refused(
    gate_store: WorkflowStore, definition: GraphDefinition, sign_payload: Signer
) -> None:
    root_id, gate = open_ship_gate(gate_store, definition)
    payload = approval_payload(root_id, gate, outcome=Outcome.ACCEPT)
    with pytest.raises(PayloadMismatchError, match="is not declared by gate"):
        close(gate_store, root_id, gate, payload, sign_payload)


# --- §10.4 rebudget ------------------------------------------------------


def test_a_verified_rebudget_records_its_bound_on_the_gate_that_closed_it(
    gate_store: WorkflowStore, definition: GraphDefinition, sign_payload: Signer
) -> None:
    # §10.4: the raise is carried by the gate bead whose approval authorized
    # it, written in the same carrier update as the outcome and the signer.
    # Nothing is written to the root, so its resolution is still the one the
    # instance was created with.
    root_id, gate = open_triage_gate(gate_store, definition)
    payload = approval_payload(
        root_id,
        gate,
        outcome=Outcome.REBUDGET,
        bound_mutation=BoundMutation(key=BoundSetting.MAX_ENTRIES.at(REGION), value=9),
    )
    closed = close(gate_store, root_id, gate, payload, sign_payload)
    assert closed.metadata.state is GateState.CLOSED
    assert closed.metadata.bound_key == BoundSetting.MAX_ENTRIES.at(REGION)
    assert closed.metadata.bound_value == 9
    assert (
        gate_store.reads.effective_bound(root_id, BoundSetting.MAX_ENTRIES, REGION) == 9
    )
    root = gate_store.reads.load_root(root_id)
    assert [
        entry
        for entry in root.metadata.resolved_config
        if entry.key == BoundSetting.MAX_ENTRIES.at(REGION)
    ] == []


def test_a_crash_after_the_carrier_but_before_the_bd_close_is_repaired_forward(
    gate_store: WorkflowStore,
    fake_bd: FakeBd,
    definition: GraphDefinition,
    sign_payload: Signer,
) -> None:
    # The plain window: the human decision was recorded, the bead stayed open,
    # and every re-submission raised — with no raw bd write available to fix
    # it. (This test carries no bound; the rebudget window is the next one.)
    root_id, gate = open_ship_gate(gate_store, definition)
    payload = approval_payload(root_id, gate)
    encoded = canonical_payload_bytes(payload)
    signature = sign_payload(encoded, None)

    fake_bd.crash_on("close")
    with pytest.raises(InjectedCrash):
        gate_store.close_gate_verified(
            root_id, gate.gate_id, payload_bytes=encoded, signature=signature
        )
    wedged = gate_store.reads.load_gate(gate.gate_id)
    assert wedged.metadata.state is GateState.CLOSED
    assert wedged.bead.status == "open"

    repaired = gate_store.close_gate_verified(
        root_id, gate.gate_id, payload_bytes=encoded, signature=signature
    )
    assert repaired.bead.status == "closed"
    assert repaired.metadata.outcome is Outcome.APPROVE


def test_a_rebudget_bound_lands_atomically_with_the_gate_close(
    gate_store: WorkflowStore,
    fake_bd: FakeBd,
    definition: GraphDefinition,
    sign_payload: Signer,
) -> None:
    # There USED to be a window here: the bound was written to the root first,
    # so a crash before the gate carrier left a raised bound on an OPEN gate,
    # and the retry's raise-only arithmetic compared the mutation against
    # itself ("9 does not raise the effective bound 9") and refused (probed,
    # round-2 review). The window is gone by construction — the raise is a
    # field of the SAME carrier write that closes the gate, so there is only
    # one update, and it either happened or it did not.
    root_id, gate = open_triage_gate(gate_store, definition)
    payload = approval_payload(
        root_id,
        gate,
        outcome=Outcome.REBUDGET,
        bound_mutation=BoundMutation(key=BoundSetting.MAX_ENTRIES.at(REGION), value=9),
    )
    encoded = canonical_payload_bytes(payload)
    signature = sign_payload(encoded, None)

    before = fake_bd.command_count("update")
    fake_bd.crash_on("update")
    with pytest.raises(InjectedCrash):
        gate_store.close_gate_verified(
            root_id, gate.gate_id, payload_bytes=encoded, signature=signature
        )
    # The one update the close issues is the gate carrier: it died, so neither
    # the decision nor the bound exists, and the region is still on its pinned
    # `max_entries`.
    assert fake_bd.command_count("update") == before + 1
    assert gate_store.reads.load_gate(gate.gate_id).metadata.state is GateState.OPEN
    assert (
        gate_store.reads.effective_bound(root_id, BoundSetting.MAX_ENTRIES, REGION) == 3
    )

    repaired = gate_store.close_gate_verified(
        root_id, gate.gate_id, payload_bytes=encoded, signature=signature
    )
    assert repaired.metadata.state is GateState.CLOSED
    assert repaired.metadata.outcome is Outcome.REBUDGET
    assert repaired.metadata.bound_value == 9
    assert repaired.metadata.payload_digest == payload_digest(encoded)
    assert repaired.bead.status == "closed"
    # And the bound was raised exactly once, by exactly this approval.
    assert (
        gate_store.reads.effective_bound(root_id, BoundSetting.MAX_ENTRIES, REGION) == 9
    )


def test_a_second_rebudget_to_the_same_value_is_still_refused(
    gate_store: WorkflowStore, definition: GraphDefinition, sign_payload: Signer
) -> None:
    # Identity, not value: a DIFFERENT approval carrying the same number is a
    # second human decision that raises nothing, and §10.4 is raise-only.
    root_id, gate = open_triage_gate(gate_store, definition)
    mutation = BoundMutation(key=BoundSetting.MAX_ENTRIES.at(REGION), value=9)
    close(
        gate_store,
        root_id,
        gate,
        approval_payload(
            root_id, gate, outcome=Outcome.REBUDGET, bound_mutation=mutation
        ),
        sign_payload,
    )
    source = gate_store.reads.list_activations(root_id)[0]
    second = gate_store.open_gate(
        root_id,
        GateOpenRequest(
            gate_node=TRIAGE,
            outcomes=(Outcome.REBUDGET, Outcome.ABANDON),
            source_activation_id=source.activation_id,
            opening_outcome=Outcome.NO_DIFF,
        ),
    )
    with pytest.raises(PayloadMismatchError, match="raise-only"):
        close(
            gate_store,
            root_id,
            second,
            approval_payload(
                root_id, second, outcome=Outcome.REBUDGET, bound_mutation=mutation
            ),
            sign_payload,
        )


def test_a_rebudget_leaves_create_root_idempotent_on_its_instance_key(
    gate_store: WorkflowStore, definition: GraphDefinition, sign_payload: Signer
) -> None:
    # §3.1 identity is the resolution the instance was CREATED with — which is
    # now the only one it ever has, because a rebudget writes its raise to the
    # gate bead. Back when the raise was merged into the root's resolution, a
    # re-tick after a verified rebudget was a hard identity error for the
    # instance's life (probed, round-2 review).
    root_id, gate = open_triage_gate(gate_store, definition)
    close(
        gate_store,
        root_id,
        gate,
        approval_payload(
            root_id,
            gate,
            outcome=Outcome.REBUDGET,
            bound_mutation=BoundMutation(
                key=BoundSetting.MAX_ENTRIES.at(REGION), value=9
            ),
        ),
        sign_payload,
    )
    root = gate_store.reads.load_root(root_id)
    assert (
        gate_store.reads.effective_bound(root_id, BoundSetting.MAX_ENTRIES, REGION) == 9
    )

    re_ticked = gate_store.create_root(
        instance_key=root.metadata.instance_key,
        definition=definition,
        resolved_config=RESOLVED_CONFIG,
    )
    assert re_ticked.root_id == root_id


def test_the_repair_path_re_verifies_the_presented_signature(
    gate_store: WorkflowStore,
    fake_client: BdClient,
    definition: GraphDefinition,
) -> None:
    # Defence in depth (§0.3): the repair path holds the payload and the
    # signature, so it has no reason to trust mutable carrier fields about a
    # decision it can check itself. Carrier state saying "closed, approved by
    # SHA256:forged" must not turn garbage bytes into a finished gate.
    root_id, gate = open_ship_gate(gate_store, definition)
    forged = gate.metadata.model_copy(
        update={
            "state": GateState.CLOSED,
            "outcome": Outcome.APPROVE,
            "verified_fingerprint": "SHA256:forged",
            "payload_digest": "d" * 64,
        }
    )
    fake_client._merge_metadata(gate.gate_id, metadata_dict(forged))

    with pytest.raises(GateVerificationError):
        gate_store.close_gate_verified(
            root_id,
            gate.gate_id,
            payload_bytes=b"not-even-json",
            signature=b"garbage",
        )
    assert gate_store.reads.load_gate(gate.gate_id).bead.status == "open"


def test_a_different_payload_against_a_closed_gate_is_still_a_conflict(
    gate_store: WorkflowStore, definition: GraphDefinition, sign_payload: Signer
) -> None:
    # Repair-forward is keyed on the payload digest, so a SECOND, different
    # human decision cannot overwrite the first one.
    root_id, gate = open_ship_gate(gate_store, definition)
    close(gate_store, root_id, gate, approval_payload(root_id, gate), sign_payload)
    second = approval_payload(root_id, gate, outcome=Outcome.ABANDON)
    with pytest.raises(LifecycleConflictError, match="already closed"):
        close(gate_store, root_id, gate, second, sign_payload)


def test_a_rebudget_that_does_not_raise_the_bound_is_refused(
    gate_store: WorkflowStore, definition: GraphDefinition, sign_payload: Signer
) -> None:
    # §10.4: rebudgets are raise-only. Lowering a bound through a signed
    # payload would be a bound mutation the audit sweep cannot distinguish
    # from a legitimate raise.
    root_id, gate = open_triage_gate(gate_store, definition)
    payload = approval_payload(
        root_id,
        gate,
        outcome=Outcome.REBUDGET,
        bound_mutation=BoundMutation(key=BoundSetting.MAX_ENTRIES.at(REGION), value=2),
    )
    with pytest.raises(PayloadMismatchError, match="raise-only"):
        close(gate_store, root_id, gate, payload, sign_payload)


def test_a_rebudget_scoped_to_an_unknown_region_is_refused(
    gate_store: WorkflowStore, definition: GraphDefinition, sign_payload: Signer
) -> None:
    root_id, gate = open_triage_gate(gate_store, definition)
    payload = approval_payload(
        root_id,
        gate,
        outcome=Outcome.REBUDGET,
        bound_mutation=BoundMutation(
            key=BoundSetting.MAX_ENTRIES.at("no-such-region"), value=9
        ),
    )
    with pytest.raises(PayloadMismatchError, match="names no region"):
        close(gate_store, root_id, gate, payload, sign_payload)


# --- namespace separation ------------------------------------------------


def test_a_signature_made_in_another_namespace_does_not_verify(
    gate_store: WorkflowStore,
    definition: GraphDefinition,
    sign_payload: Signer,
    signing_key,
) -> None:
    # `ssh-keygen -Y sign -n git` over the same bytes: same key, same payload,
    # wrong namespace. §9's namespace separation is what stops a git-signing
    # key from doubling as a gate approval.
    import subprocess

    from tests.conftest import KEYGEN_TIMEOUT_S, SSH_KEYGEN

    root_id, gate = open_ship_gate(gate_store, definition)
    encoded = canonical_payload_bytes(approval_payload(root_id, gate))
    message = signing_key.parent / "cross-namespace.json"
    message.write_bytes(encoded)
    subprocess.run(
        [SSH_KEYGEN, "-Y", "sign", "-f", str(signing_key), "-n", "git", str(message)],
        check=True,
        capture_output=True,
        timeout=KEYGEN_TIMEOUT_S,
    )
    signature = message.with_suffix(".json.sig").read_bytes()
    with pytest.raises(Exception, match="does not verify|namespace"):
        gate_store.close_gate_verified(
            root_id, gate.gate_id, payload_bytes=encoded, signature=signature
        )
    assert gate_store.reads.load_gate(gate.gate_id).metadata.state is GateState.OPEN
