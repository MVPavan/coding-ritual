"""§3.4/§10.3/§10.4 gate LIFECYCLE — re-find, halt ordinals, rebudget races.

The refusal paths live in `test_bdio_gate_security`; this family is about what
happens to a gate that already exists: which requests re-find it, when a new
halt gate may be minted, and what two rebudgets landing in one window do to the
instance's bounds. Real `ssh-keygen` signatures over the in-memory bd, whose
scheduling hooks are what make the interleavings deterministic.
"""

from __future__ import annotations

import hashlib

import pytest

from tests._bdio import (
    IMPLEMENT,
    REGION,
    RESOLVED_CONFIG,
    REVIEW,
    TRIAGE,
    entry_request,
    load_definition,
    make_root,
    run_to_close,
)
from tests._fake_bd import FakeBd
from tests._gates import (
    approval_payload,
    close,
    open_ship_gate,
    open_triage_gate,
    ship_gate_request,
)
from tests.conftest import APPROVED_TEXT, PLAN_REF, Signer
from workflow_interpreter import GraphDefinition
from workflow_interpreter.bdio import (
    BoundExceededError,
    BoundMutation,
    CarrierIntegrityError,
    LifecycleConflictError,
    MintReason,
    MintRequest,
    PayloadMismatchError,
    canonical_payload_bytes,
)
from workflow_interpreter.bdio.api import WorkflowStore
from workflow_interpreter.bdio.client import BdClient
from workflow_interpreter.bdio.records import GateRecord
from workflow_interpreter.bdio.signing import payload_digest
from workflow_interpreter.bdio.wire import (
    BindsMode,
    BoundSetting,
    ConfigSource,
    GateOpenRequest,
    GateReason,
    GateState,
    ResolvedSetting,
    metadata_dict,
)
from workflow_interpreter.schema.models import Outcome


@pytest.fixture(scope="session")
def definition() -> GraphDefinition:
    """The §2 canonical fixture, loaded and hashed once."""
    return load_definition()


# --- gate re-find: OPEN gates only, and only the gate asked for (§3.4, §10.3)


def test_a_closed_gate_is_never_re_found_as_a_freshly_opened_one(
    gate_store: WorkflowStore, definition: GraphDefinition, sign_payload: Signer
) -> None:
    # `open_gate` re-found by key without looking at state, so a decision
    # already taken came back as an open gate: the foreman would wait on a
    # gate that carries someone else's recorded outcome (probed, round 3).
    root_id, gate = open_ship_gate(gate_store, definition)
    request = ship_gate_request(str(gate.metadata.source_activation_id))
    close(gate_store, root_id, gate, approval_payload(root_id, gate), sign_payload)

    with pytest.raises(LifecycleConflictError, match="already CLOSED"):
        gate_store.open_gate(root_id, request)


def test_a_re_find_that_contradicts_the_recorded_gate_is_refused(
    gate_store: WorkflowStore, definition: GraphDefinition
) -> None:
    # The caller asked for a MUTABLE gate over a document and silently got the
    # IMMUTABLE gate already at that key — no refusal, no signal, and a §9
    # freshness check that would never run (probed, round 3).
    root_id, gate = open_ship_gate(gate_store, definition)

    with pytest.raises(CarrierIntegrityError, match="binds"):
        gate_store.open_gate(
            root_id,
            ship_gate_request(
                str(gate.metadata.source_activation_id),
                binds=BindsMode.MUTABLE,
                artifact_ref=PLAN_REF,
                artifact_digest=hashlib.sha256(APPROVED_TEXT).hexdigest(),
            ),
        )
    assert (
        gate_store.reads.load_gate(gate.gate_id).metadata.binds is BindsMode.IMMUTABLE
    )


def test_re_finding_an_open_gate_with_the_same_request_is_idempotent(
    gate_store: WorkflowStore, definition: GraphDefinition
) -> None:
    root_id, gate = open_ship_gate(gate_store, definition)
    again = gate_store.open_gate(
        root_id, ship_gate_request(str(gate.metadata.source_activation_id))
    )
    assert again.gate_id == gate.gate_id


def test_a_gate_key_with_race_residue_re_finds_the_same_bead_every_tick(
    gate_store: WorkflowStore, fake_client: BdClient, definition: GraphDefinition
) -> None:
    # Two beads under one gate key is residue; whichever bd lists first is not
    # a rule. Lowest id is, exactly as for roots and activations.
    root_id, gate = open_ship_gate(gate_store, definition)
    duplicate = fake_client._create_bead(
        title="wf gate residue",
        metadata=metadata_dict(gate.metadata.model_copy(update={"seq": 99})),
    )

    found = gate_store.reads.find_gate(root_id, gate.metadata.gate_key)

    assert found is not None
    assert found.gate_id == min(gate.gate_id, duplicate.id)


# --- §10.3 halt gates: one open at a time, never one per instance --------


def test_a_closed_halt_gate_does_not_wedge_the_next_halt(
    gate_store: WorkflowStore, definition: GraphDefinition, sign_payload: Signer
) -> None:
    # Keyed on the root ALONE, the halt gate was one-shot: after the first
    # halt closed, every later ceiling breach re-found the closed bead with
    # its old outcome, so §10.6's audit-sweep halt could never fire again
    # (probed, round 3). The key gains an ordinal instead.
    root = make_root(
        gate_store,
        definition,
        ResolvedSetting(
            key="instance.max_total_activations",
            value=3,
            source=ConfigSource.INSTANCE_OVERRIDE,
        ),
    )
    gate_store.mint_activation(root.root_id, entry_request())

    def halt(reason: str) -> GateRecord:
        return gate_store.open_gate(
            root.root_id,
            GateOpenRequest(
                gate_node=TRIAGE,
                outcomes=(Outcome.REBUDGET, Outcome.ABANDON),
                gate_reason=GateReason.HALT,
                halt_reason=reason,
            ),
        )

    first = halt("ceiling breach #1")
    # One open halt at a time: a second breach re-finds it, whatever it says.
    assert halt("ceiling breach #1 again").gate_id == first.gate_id

    close(
        gate_store,
        root.root_id,
        first,
        approval_payload(
            root.root_id,
            first,
            outcome=Outcome.REBUDGET,
            bound_mutation=BoundMutation(
                key=BoundSetting.MAX_TOTAL_ACTIVATIONS.at(), value=40
            ),
        ),
        sign_payload,
    )

    second = halt("ceiling breach #2")

    assert second.gate_id != first.gate_id
    assert second.metadata.state is GateState.OPEN
    assert second.metadata.outcome is None
    assert second.metadata.halt_reason == "ceiling breach #2"
    assert second.metadata.gate_key != first.metadata.gate_key
    # And it is resolvable on its own terms.
    resolved = close(
        gate_store,
        root.root_id,
        second,
        approval_payload(root.root_id, second, outcome=Outcome.ABANDON),
        sign_payload,
    )
    assert resolved.metadata.outcome is Outcome.ABANDON


def test_the_halt_exemption_still_costs_a_human_verified_close(
    gate_store: WorkflowStore, definition: GraphDefinition
) -> None:
    # The ordinal must not turn the ceiling-exempt mint back into an unbounded
    # one: a new halt bead exists only when every prior halt is CLOSED.
    root = make_root(
        gate_store,
        definition,
        ResolvedSetting(
            key="instance.max_total_activations",
            value=2,
            source=ConfigSource.INSTANCE_OVERRIDE,
        ),
    )
    gate_store.mint_activation(root.root_id, entry_request())
    opened = [
        gate_store.open_gate(
            root.root_id,
            GateOpenRequest(
                gate_node=TRIAGE,
                outcomes=(Outcome.ABANDON,),
                gate_reason=GateReason.HALT,
                halt_reason="ceiling",
            ),
        )
        for _ in range(5)
    ]

    assert len({gate.gate_id for gate in opened}) == 1
    assert len(gate_store.reads.list_gates(root.root_id)) == 1


# --- §10.4 rebudget scope: the setting decides what a scope may name -----


def test_a_rebudget_scoped_to_the_wrong_KIND_of_thing_is_refused(
    gate_store: WorkflowStore, definition: GraphDefinition, sign_payload: Signer
) -> None:
    # A region-scoped key naming a NODE (and the reverse) passed the "is it a
    # region or a node" check, landed in resolved_config, matched no real
    # bound — and the gate took its `rebudget` edge on a signed approval that
    # changed nothing (probed, round 3).
    root_id, gate = open_triage_gate(gate_store, definition)
    region_key_naming_a_node = approval_payload(
        root_id,
        gate,
        outcome=Outcome.REBUDGET,
        bound_mutation=BoundMutation(
            key=BoundSetting.MAX_ENTRIES.at(IMPLEMENT), value=9
        ),
    )
    with pytest.raises(PayloadMismatchError, match="names no region"):
        close(gate_store, root_id, gate, region_key_naming_a_node, sign_payload)

    node_key_naming_a_region = approval_payload(
        root_id,
        gate,
        outcome=Outcome.REBUDGET,
        bound_mutation=BoundMutation(
            key=BoundSetting.MAX_INFRA_RETRIES.at(REGION), value=9
        ),
    )
    with pytest.raises(PayloadMismatchError, match="names no node"):
        close(gate_store, root_id, gate, node_key_naming_a_region, sign_payload)

    assert gate_store.reads.load_gate(gate.gate_id).metadata.state is GateState.OPEN
    root = gate_store.reads.load_root(root_id)
    assert [
        entry
        for entry in root.metadata.resolved_config
        if entry.key.endswith(("max_entries", "max_infra_retries"))
    ] == []


def test_a_mis_scoped_approval_does_not_wedge_the_exhaustion_gate(
    gate_store: WorkflowStore, definition: GraphDefinition, sign_payload: Signer
) -> None:
    # The compound defect: a mis-scoped rebudget was ACCEPTED, closed the
    # exhaustion gate, changed no bound — and the re-opened gate re-found the
    # closed bead, so the corrected approval could never be applied (probed,
    # round 3). Both halves are fixed; the corrected approval lands.
    root = make_root(gate_store, definition)
    gate_store.mint_activation(root.root_id, entry_request())
    request = GateOpenRequest(
        gate_node=TRIAGE,
        outcomes=(Outcome.REBUDGET, Outcome.ABANDON),
        gate_reason=GateReason.EXHAUSTION,
        region=REGION,
        round_no=1,
    )
    gate = gate_store.open_gate(root.root_id, request)

    mis_scoped = approval_payload(
        root.root_id,
        gate,
        outcome=Outcome.REBUDGET,
        bound_mutation=BoundMutation(
            key=BoundSetting.MAX_ENTRIES.at(IMPLEMENT), value=9
        ),
    )
    with pytest.raises(PayloadMismatchError):
        close(gate_store, root.root_id, gate, mis_scoped, sign_payload)

    # The gate stayed open, so the SAME gate takes the corrected approval.
    reopened = gate_store.open_gate(root.root_id, request)
    assert reopened.gate_id == gate.gate_id
    corrected = approval_payload(
        root.root_id,
        gate,
        outcome=Outcome.REBUDGET,
        bound_mutation=BoundMutation(key=BoundSetting.MAX_ENTRIES.at(REGION), value=9),
    )
    closed = close(gate_store, root.root_id, reopened, corrected, sign_payload)

    assert closed.metadata.outcome is Outcome.REBUDGET
    assert (
        gate_store.reads.effective_bound(root.root_id, BoundSetting.MAX_ENTRIES, REGION)
        == 9
    )


# --- §10.3/§10.4 a ceiling rebudget re-opens the instance ---------------


def test_a_ceiling_rebudget_on_a_halt_gate_lets_the_instance_run_again(
    gate_store: WorkflowStore, definition: GraphDefinition, sign_payload: Signer
) -> None:
    # `max_total_activations` is one of the §10.4 bound keys, so the raise it
    # takes lives on the halt gate that carried the approval — and BOTH §10.3
    # predicate sites (the gate-open ceiling and the pre-mint ceiling) have to
    # read it from there. A reader that answered from the root bead alone
    # would enforce the pre-rebudget ceiling and refuse the very work the
    # human just re-budgeted for.
    root = make_root(
        gate_store,
        definition,
        ResolvedSetting(
            key="instance.max_total_activations",
            value=1,
            source=ConfigSource.INSTANCE_OVERRIDE,
        ),
    )
    entry = gate_store.mint_activation(root.root_id, entry_request()).activation
    ship = ship_gate_request(entry.activation_id)
    with pytest.raises(BoundExceededError):
        gate_store.open_gate(root.root_id, ship)
    run_to_close(gate_store, entry.activation_id, Outcome.DONE)
    successor = MintRequest(
        node=REVIEW,
        mint_reason=MintReason.EDGE,
        predecessor_activation_id=entry.activation_id,
        runner_profile="profile:reviewer",
        model="default",
        session_id="sess-1",
    )
    with pytest.raises(BoundExceededError):
        gate_store.mint_activation(root.root_id, successor)

    halt = gate_store.open_gate(
        root.root_id,
        GateOpenRequest(
            gate_node=TRIAGE,
            outcomes=(Outcome.REBUDGET, Outcome.ABANDON),
            gate_reason=GateReason.HALT,
            halt_reason="ceiling",
        ),
    )
    close(
        gate_store,
        root.root_id,
        halt,
        approval_payload(
            root.root_id,
            halt,
            outcome=Outcome.REBUDGET,
            bound_mutation=BoundMutation(
                key=BoundSetting.MAX_TOTAL_ACTIVATIONS.at(), value=10
            ),
        ),
        sign_payload,
    )

    assert (
        gate_store.reads.effective_bound(
            root.root_id, BoundSetting.MAX_TOTAL_ACTIVATIONS
        )
        == 10
    )
    # Both refusals lift, from the raise recorded on the gate bead.
    assert gate_store.mint_activation(root.root_id, successor).created
    assert gate_store.open_gate(root.root_id, ship).metadata.state is GateState.OPEN


# --- §10.4 two rebudgets in flight: both signed bounds survive -----------


def test_two_concurrent_rebudgets_both_stay_in_effect(
    gate_store: WorkflowStore,
    fake_bd: FakeBd,
    definition: GraphDefinition,
    sign_payload: Signer,
) -> None:
    # The r3/r4 defect: the root was one object written wholesale, so the
    # second rebudget's read happened BEFORE the first one's write and its
    # merge dropped a bound it had never seen. Both gates ended CLOSED with a
    # verified fingerprint while one signed raise was silently not in effect,
    # and the writer's own read-back could not see it — content comparison
    # cannot detect data the writer never held, so no retry loop could fix it
    # (probed, `probe_rebudget_race.py`).
    #
    # Bound authority is now the creation config PLUS the closed rebudget
    # gates, max per key. Two closes are two different bead writes: neither
    # can clobber the other, and no recovery re-submission is needed.
    root_id, first_gate, second_gate = two_open_triage_gates(gate_store, definition)
    first = approval_payload(
        root_id,
        first_gate,
        outcome=Outcome.REBUDGET,
        bound_mutation=BoundMutation(key=BoundSetting.MAX_ENTRIES.at(REGION), value=9),
    )
    second = approval_payload(
        root_id,
        second_gate,
        outcome=Outcome.REBUDGET,
        bound_mutation=BoundMutation(
            key=BoundSetting.MAX_TOTAL_ACTIVATIONS.at(), value=50
        ),
    )

    def interleave() -> None:
        close(gate_store, root_id, second_gate, second, sign_payload)

    # The second tick runs to completion inside the first one's write window:
    # it reads, decides and closes before the first one's carrier update lands.
    fake_bd.pause_before("update", interleave)
    close(gate_store, root_id, first_gate, first, sign_payload)

    assert (
        gate_store.reads.effective_bound(root_id, BoundSetting.MAX_ENTRIES, REGION) == 9
    )
    assert (
        gate_store.reads.effective_bound(root_id, BoundSetting.MAX_TOTAL_ACTIVATIONS)
        == 50
    )
    # Both decisions are auditable: each gate carries its own raise and its own
    # payload digest, and the root's resolution never moved.
    closed = {
        gate.gate_id: gate
        for gate in gate_store.reads.list_gates(root_id)
        if gate.metadata.state is GateState.CLOSED
    }
    assert {
        (gate.metadata.bound_key, gate.metadata.bound_value) for gate in closed.values()
    } == {
        (BoundSetting.MAX_ENTRIES.at(REGION), 9),
        (BoundSetting.MAX_TOTAL_ACTIVATIONS.at(), 50),
    }
    assert {gate.metadata.payload_digest for gate in closed.values()} == {
        payload_digest(canonical_payload_bytes(first)),
        payload_digest(canonical_payload_bytes(second)),
    }
    assert (
        gate_store.reads.load_root(root_id).metadata.resolved_config == RESOLVED_CONFIG
    )


def two_open_triage_gates(
    store: WorkflowStore, definition: GraphDefinition
) -> tuple[str, GateRecord, GateRecord]:
    """One instance with two open `triage` gates — two ticks, two decisions."""
    root = make_root(store, definition)
    source = store.mint_activation(root.root_id, entry_request()).activation
    gates = tuple(
        store.open_gate(
            root.root_id,
            GateOpenRequest(
                gate_node=TRIAGE,
                outcomes=(Outcome.REBUDGET, Outcome.ABANDON),
                source_activation_id=source.activation_id,
                opening_outcome=opening,
            ),
        )
        for opening in (Outcome.FAIL_PLAN, Outcome.FAIL_CODE)
    )
    return root.root_id, gates[0], gates[1]


def test_a_tampered_bound_without_signature_evidence_raises_nothing(
    fake_bd: FakeBd, gate_store: WorkflowStore, definition: GraphDefinition
) -> None:
    """A closed gate carrying bound fields but no verified fingerprint or
    payload digest was never written by `close_gate_verified` (which records
    them in one write); its bound must not fold into the effective bound
    (§0.3 hardening, phase-2 micro-confirm)."""
    root_id, gate = open_triage_gate(gate_store, definition)
    before = gate_store.reads.effective_bound(
        root_id, BoundSetting.MAX_ENTRIES, scope="build-review"
    )
    fake_bd.rows[gate.bead.id]["status"] = "closed"
    fake_bd.rows[gate.bead.id]["metadata"].update(
        {
            "state": "closed",
            "outcome": "rebudget",
            "bound_key": "region.build-review.max_entries",
            "bound_value": 999,
        }
    )
    after = gate_store.reads.effective_bound(
        root_id, BoundSetting.MAX_ENTRIES, scope="build-review"
    )
    assert after == before
