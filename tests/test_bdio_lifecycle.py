"""Crash windows, interleavings, root identity and the sealed write surface.

Every test here needs something a live bd cannot give deterministically — a
process death at a chosen instruction, or two mints scheduled against each
other — so they run through the in-memory bd (`tests/_fake_bd.py`) behind the
real transport. No bd binary is involved.
"""

from __future__ import annotations

from typing import Final

import pytest

from tests._bdio import (
    IMPLEMENT,
    REVIEW,
    entry_request,
    handle,
    load_definition,
    make_root,
    race_residue,
    run_to_close,
)
from tests._fake_bd import FakeBd, InjectedCrash
from workflow_interpreter import GraphDefinition
from workflow_interpreter.bdio import bounds
from workflow_interpreter.bdio.api import WorkflowStore
from workflow_interpreter.bdio.client import BdClient
from workflow_interpreter.bdio.errors import (
    BoundExceededError,
    CarrierIntegrityError,
    LifecycleConflictError,
)
from workflow_interpreter.bdio.records import MintResult
from workflow_interpreter.bdio.wire import (
    ConfigSource,
    Deviation,
    Evidence,
    GateOpenRequest,
    GateReason,
    Lifecycle,
    MintReason,
    ResolvedSetting,
    Usage,
    WfKind,
)
from workflow_interpreter.schema.models import Outcome

STATUS_CLOSED: Final[str] = "closed"
STATUS_OPEN: Final[str] = "open"
LOW_BEAD_ID: Final[str] = "wf-000"
"""A bead id below every id FakeBd hands out — real bd ids are not ordered by
creation time (probed), and this is how that looks deterministically."""

PUBLIC_STORE_SURFACE: Final[frozenset[str]] = frozenset(
    {
        "append_event",
        "close_activation",
        "close_gate_verified",
        "create_root",
        "for_root",
        "from_config",
        "mint_activation",
        "open_gate",
        "reads",
        "record_dispatch",
        "record_evidence",
        "record_exit",
        "record_precondition",
        "record_stale_flag",
        "startup_canary",
        "supersede_activation",
    }
)
"""Every public name on `WorkflowStore`. Adding one is a design change; the
point of the set is that a generic write cannot quietly join it.

`for_root` derives a root-scoped reader without exposing the sealed client.
`record_precondition` and `record_stale_flag` joined it in phase 3, as the
narrowest typed writes for the two facts the supervisor owns and §3.2/§8.2
require in bd: the carry-forward trio proven before the exec, and the stale
flag. Each takes one frozen carrier and touches only its own keys."""


@pytest.fixture(scope="session")
def definition() -> GraphDefinition:
    """The §2 canonical fixture, loaded and hashed once."""
    return load_definition()


# --- the sealed write surface (§0.1) ------------------------------------


def test_the_public_package_exports_no_transport() -> None:
    # A caller holding a BdClient can close a bead in one line, skipping every
    # §5.1 and §9 rule this package exists to enforce.
    import workflow_interpreter.bdio as package

    assert "BdClient" not in package.__all__
    assert not hasattr(package, "BdClient")


def test_the_store_exposes_no_write_that_skips_verification(
    fake_store: WorkflowStore,
) -> None:
    public = {name for name in dir(fake_store) if not name.startswith("_")}
    assert public == PUBLIC_STORE_SURFACE
    # The two named escape hatches the review found, specifically:
    assert not hasattr(fake_store, "client")
    assert not hasattr(fake_store, "update_root_bounds")


def test_the_transports_write_methods_are_package_private() -> None:
    assert not hasattr(BdClient, "create_bead")
    assert not hasattr(BdClient, "merge_metadata")
    assert not hasattr(BdClient, "close_bead")


def test_the_read_facade_issues_no_write_command(
    fake_store: WorkflowStore, fake_bd: FakeBd, definition: GraphDefinition
) -> None:
    root = make_root(fake_store, definition)
    minted = fake_store.mint_activation(root.root_id, entry_request())
    writes_before = [
        name for name, _ in fake_bd.calls if name in {"create", "update", "close"}
    ]
    facade = fake_store.reads
    facade.load_root(root.root_id)
    facade.load_activation(minted.activation.activation_id)
    facade.instance_beads(root.root_id)
    facade.list_activations(root.root_id)
    facade.list_gates(root.root_id)
    facade.find_by_idempotency_key(root.root_id, minted.idempotency_key)
    facade.find_gate(root.root_id, "nope")
    facade.find_event(root.root_id, "nope")
    writes_after = [
        name for name, _ in fake_bd.calls if name in {"create", "update", "close"}
    ]
    assert writes_after == writes_before


# --- repair-forward finalizers (§5.1) -----------------------------------


def test_a_crash_between_the_outcome_and_the_close_is_repaired_forward(
    fake_store: WorkflowStore, fake_bd: FakeBd, definition: GraphDefinition
) -> None:
    # The recorded window: metadata says closed, bd says open. Returning early
    # leaves an open bead the frontier re-picks forever.
    root = make_root(fake_store, definition)
    activation = fake_store.mint_activation(root.root_id, entry_request()).activation
    fake_store.record_dispatch(activation.activation_id, handle())
    fake_bd.crash_on("close")
    with pytest.raises(InjectedCrash):
        fake_store.close_activation(activation.activation_id, Outcome.DONE)

    wedged = fake_store.reads.load_activation(activation.activation_id)
    assert wedged.metadata.lifecycle is Lifecycle.CLOSED
    assert wedged.bead.status == STATUS_OPEN

    repaired = fake_store.close_activation(activation.activation_id, Outcome.DONE)
    assert repaired.bead.status == STATUS_CLOSED
    assert repaired.bead.close_reason == "outcome=done"
    assert repaired.metadata.outcome is Outcome.DONE


def test_a_close_that_landed_before_its_metadata_is_still_completed(
    fake_store: WorkflowStore, fake_client: BdClient, definition: GraphDefinition
) -> None:
    # The other order: the bead is closed with no routing truth recorded. The
    # next call must write the outcome and re-drive the close, not refuse.
    root = make_root(fake_store, definition)
    activation = fake_store.mint_activation(root.root_id, entry_request()).activation
    fake_store.record_dispatch(activation.activation_id, handle())
    fake_client._close_bead(activation.activation_id, "outcome=stale")

    repaired = fake_store.close_activation(activation.activation_id, Outcome.DONE)
    assert repaired.metadata.outcome is Outcome.DONE
    assert repaired.bead.close_reason == "outcome=done"


def test_a_contradicting_close_is_still_refused(
    fake_store: WorkflowStore, definition: GraphDefinition
) -> None:
    # Repair-forward is not "accept anything": a DIFFERENT outcome against a
    # recorded one is a real conflict (§5.1).
    root = make_root(fake_store, definition)
    activation = fake_store.mint_activation(root.root_id, entry_request()).activation
    run_to_close(fake_store, activation.activation_id, Outcome.DONE)
    with pytest.raises(LifecycleConflictError, match="already closed"):
        fake_store.close_activation(activation.activation_id, Outcome.NO_DIFF)


def test_re_closing_with_a_different_payload_is_refused_not_dropped(
    fake_store: WorkflowStore, definition: GraphDefinition
) -> None:
    # The recorded close wins (§5.1), so a second close carrying NEW evidence,
    # usage or deviations reported success while writing none of them — the
    # caller believed its late evidence was recorded (probed, round 3).
    root = make_root(fake_store, definition)
    activation = fake_store.mint_activation(root.root_id, entry_request()).activation
    run_to_close(fake_store, activation.activation_id, Outcome.DONE)

    # Re-closing with the SAME (absent) payload stays idempotent.
    assert (
        fake_store.close_activation(
            activation.activation_id, Outcome.DONE
        ).metadata.outcome
        is Outcome.DONE
    )

    for kwargs in (
        {"evidence": Evidence(note="late evidence")},
        {"usage": Usage(known=True, input_tokens=5)},
        {
            "deviations": (
                Deviation(
                    kind="salvage", reason="r", recorded_at="2026-08-25T00:00:00Z"
                ),
            )
        },
    ):
        with pytest.raises(CarrierIntegrityError, match="already closed"):
            fake_store.close_activation(
                activation.activation_id,
                Outcome.DONE,
                **kwargs,  # type: ignore[arg-type]
            )
    recorded = fake_store.reads.load_activation(activation.activation_id).metadata
    assert recorded.evidence is None
    assert recorded.usage is None
    assert recorded.deviations == ()


def test_a_crashed_supersede_is_repaired_forward(
    fake_store: WorkflowStore,
    fake_client: BdClient,
    fake_bd: FakeBd,
    definition: GraphDefinition,
) -> None:
    root = make_root(fake_store, definition)
    winner = fake_store.mint_activation(root.root_id, entry_request()).activation
    loser = race_residue(fake_client, winner)

    fake_bd.crash_on("close")
    with pytest.raises(InjectedCrash):
        fake_store.supersede_activation(loser.activation_id, winner.activation_id)
    wedged = fake_store.reads.load_activation(loser.activation_id)
    assert wedged.metadata.superseded_by == winner.activation_id
    assert wedged.bead.status == STATUS_OPEN

    repaired = fake_store.supersede_activation(
        loser.activation_id, winner.activation_id
    )
    assert repaired.bead.status == STATUS_CLOSED
    assert repaired.metadata.outcome is Outcome.SUPERSEDED


def test_a_contradicting_supersede_is_still_refused(
    fake_store: WorkflowStore, fake_client: BdClient, definition: GraphDefinition
) -> None:
    root = make_root(fake_store, definition)
    winner = fake_store.mint_activation(root.root_id, entry_request()).activation
    loser = race_residue(fake_client, winner, seq_delta=2)
    other = race_residue(fake_client, winner, seq_delta=1)
    fake_store.supersede_activation(loser.activation_id, winner.activation_id)
    with pytest.raises(LifecycleConflictError, match="already superseded"):
        fake_store.supersede_activation(loser.activation_id, other.activation_id)


def test_a_supersede_naming_a_winner_that_does_not_exist_is_refused(
    fake_store: WorkflowStore, definition: GraphDefinition
) -> None:
    # Live probe, round 3: superseding the sole entry activation onto
    # "wf-does-not-exist" succeeded, closed it `superseded`, and the next
    # identical mint then refused — the instance had destroyed its own only
    # activation to settle a race nobody could show existed.
    root = make_root(fake_store, definition)
    only = fake_store.mint_activation(root.root_id, entry_request()).activation

    with pytest.raises(CarrierIntegrityError, match="not a live activation"):
        fake_store.supersede_activation(only.activation_id, "wf-does-not-exist")

    assert (
        fake_store.reads.load_activation(only.activation_id).metadata.lifecycle
        is Lifecycle.MINTED
    )
    assert (
        fake_store.mint_activation(
            root.root_id, entry_request()
        ).activation.activation_id
        == only.activation_id
    )


def test_a_supersede_naming_a_winner_of_another_key_is_refused(
    fake_store: WorkflowStore, definition: GraphDefinition
) -> None:
    # A real bead, a real root — but not a party to this key's race. Closing
    # the loser onto it would leave the key with nothing live under it.
    root = make_root(fake_store, definition)
    first = fake_store.mint_activation(root.root_id, entry_request()).activation
    run_to_close(fake_store, first.activation_id, Outcome.DONE)
    successor = fake_store.mint_activation(
        root.root_id,
        entry_request(
            node=REVIEW,
            mint_reason=MintReason.EDGE,
            predecessor_activation_id=first.activation_id,
        ),
    ).activation

    with pytest.raises(CarrierIntegrityError, match="not a live activation"):
        fake_store.supersede_activation(successor.activation_id, first.activation_id)


def test_a_supersede_naming_the_loser_of_the_tie_break_is_refused(
    fake_store: WorkflowStore, fake_client: BdClient, definition: GraphDefinition
) -> None:
    # Both beads are genuine race residue for one key, so "exists, same root,
    # same key" all hold — and the §3.2 rule still says which one survives.
    root = make_root(fake_store, definition)
    winner = fake_store.mint_activation(root.root_id, entry_request()).activation
    residue = race_residue(fake_client, winner)

    with pytest.raises(CarrierIntegrityError, match="tie-break"):
        fake_store.supersede_activation(winner.activation_id, residue.activation_id)


# --- terminal outcomes are not overwritable (§3.2, §3.3) ----------------


def test_a_superseded_loser_cannot_be_closed_back_into_routing_truth(
    fake_store: WorkflowStore, fake_client: BdClient, definition: GraphDefinition
) -> None:
    # Two typed calls, no signature anywhere: supersede then close(ACCEPT) used
    # to resurrect a lost race into an edge a successor could be minted from
    # (probed, round-2 review). `supersede` is terminal too.
    root = make_root(fake_store, definition)
    first = fake_store.mint_activation(root.root_id, entry_request()).activation
    loser = race_residue(fake_client, first)
    fake_store.supersede_activation(loser.activation_id, first.activation_id)

    with pytest.raises(CarrierIntegrityError, match="superseded"):
        fake_store.close_activation(loser.activation_id, Outcome.ACCEPT)
    still_lost = fake_store.reads.load_activation(loser.activation_id)
    assert still_lost.metadata.outcome is Outcome.SUPERSEDED
    assert still_lost.metadata.superseded_by == first.activation_id
    # And nothing can be routed off it: `outcome_taken` is read from the close.
    with pytest.raises(CarrierIntegrityError):
        fake_store.mint_activation(
            root.root_id,
            entry_request(
                mint_reason=MintReason.EDGE,
                predecessor_activation_id=loser.activation_id,
            ),
        )


def test_a_completed_activation_is_never_superseded(
    fake_store: WorkflowStore, definition: GraphDefinition
) -> None:
    root = make_root(fake_store, definition)
    activation = fake_store.mint_activation(root.root_id, entry_request()).activation
    run_to_close(fake_store, activation.activation_id, Outcome.DONE)
    with pytest.raises(CarrierIntegrityError, match="COMPLETED"):
        fake_store.supersede_activation(activation.activation_id, "wf-998")
    assert (
        fake_store.reads.load_activation(activation.activation_id).metadata.outcome
        is Outcome.DONE
    )


def test_race_residue_never_destroys_a_completed_activation(
    fake_store: WorkflowStore, fake_client: BdClient, definition: GraphDefinition
) -> None:
    # The §3.2 tie-break is `seq`, and residue with a LOWER seq used to win it
    # — superseding an activation that had already run, recorded its evidence
    # and produced the outcome the frontier routed on (probed, round-2 review).
    # A completed activation is routing truth; it wins the race outright.
    root = make_root(fake_store, definition)
    first = fake_store.mint_activation(root.root_id, entry_request()).activation
    run_to_close(fake_store, first.activation_id, Outcome.DONE)
    completed = fake_store.reads.load_activation(first.activation_id)
    residue = completed.metadata.model_copy(
        update={
            "seq": completed.metadata.seq - 1,
            "lifecycle": Lifecycle.MINTED,
            "outcome": None,
            "evidence": None,
            "exit_record": None,
            "handle": None,
        }
    )
    duplicate = fake_client._create_bead(
        title="wf race residue",
        metadata=residue.model_dump(mode="json", exclude_none=True),
    )

    resolved = fake_store.mint_activation(root.root_id, entry_request())
    assert resolved.activation.activation_id == first.activation_id
    survivor = fake_store.reads.load_activation(first.activation_id)
    assert survivor.metadata.outcome is Outcome.DONE
    assert survivor.metadata.exit_record is not None
    assert survivor.bead.close_reason == "outcome=done"
    assert fake_client.show(duplicate.id).status == STATUS_CLOSED


# --- interleaved mints (§3.2 race residue) ------------------------------


def test_a_minter_told_created_but_later_superseded_cannot_dispatch(
    fake_store: WorkflowStore,
    fake_client: BdClient,
    fake_bd: FakeBd,
    definition: GraphDefinition,
) -> None:
    # The scheduled window: a second minter re-checks and returns created=True
    # BEFORE the first minter's create lands, and then loses the §3.2 tie-break
    # (lowest seq). Its `created=True` is stale by the time it is read — the
    # refusal has to be structural, at the next state write.
    root = make_root(fake_store, definition)
    stale: list[MintResult] = []

    def interleave() -> None:
        # Beads appear between the two minters' reads, so the later creator
        # holds the LOWER seq and wins the tie-break.
        for index in range(3):
            fake_client._create_bead(
                title=f"wf filler {index}",
                metadata={
                    "wf_kind": WfKind.EVENT.value,
                    "wf_root_id": root.root_id,
                    "seq": 100 + index,
                },
            )
        stale.append(fake_store.mint_activation(root.root_id, entry_request()))

    fake_bd.pause_before("create", interleave)
    winner = fake_store.mint_activation(root.root_id, entry_request())

    (loser,) = stale
    assert loser.created is True
    assert winner.created is True
    assert loser.activation.activation_id != winner.activation.activation_id

    resolved = fake_store.reads.load_activation(loser.activation.activation_id)
    assert resolved.metadata.superseded_by == winner.activation.activation_id
    with pytest.raises(LifecycleConflictError, match="superseded"):
        fake_store.record_dispatch(resolved.activation_id, handle())


def test_race_residue_leaves_exactly_one_live_head(
    fake_store: WorkflowStore, fake_client: BdClient, definition: GraphDefinition
) -> None:
    root = make_root(fake_store, definition)
    minted = fake_store.mint_activation(root.root_id, entry_request())
    duplicate_metadata = minted.activation.metadata.model_copy(
        update={"seq": minted.activation.metadata.seq + 1}
    )
    duplicate = fake_client._create_bead(
        title="wf race residue",
        metadata=duplicate_metadata.model_dump(mode="json", exclude_none=True),
    )

    resolved = fake_store.mint_activation(root.root_id, entry_request())
    assert resolved.created is False
    assert resolved.activation.activation_id == minted.activation.activation_id
    live = [
        record
        for record in fake_store.reads.list_activations(root.root_id)
        if not record.metadata.is_superseded
    ]
    assert [record.activation_id for record in live] == [
        minted.activation.activation_id
    ]
    assert fake_client.show(duplicate.id).status == STATUS_CLOSED


# --- §10.3 ceiling and the halt gate ------------------------------------


def test_the_halt_gate_is_mintable_at_the_ceiling_and_still_counted(
    fake_store: WorkflowStore, definition: GraphDefinition
) -> None:
    # §10.3 ruling: exempt from the PREDICATE, never from the COUNT.
    root = make_root(
        fake_store,
        definition,
        ResolvedSetting(
            key="instance.max_total_activations",
            value=1,
            source=ConfigSource.INSTANCE_OVERRIDE,
        ),
    )
    fake_store.mint_activation(root.root_id, entry_request())
    with pytest.raises(BoundExceededError):
        fake_store.open_gate(
            root.root_id,
            GateOpenRequest(
                gate_node="ship",
                outcomes=(Outcome.APPROVE, Outcome.ABANDON),
                source_activation_id="wf-2",
                opening_outcome=Outcome.ACCEPT,
            ),
        )
    halt = fake_store.open_gate(
        root.root_id,
        GateOpenRequest(
            gate_node=IMPLEMENT,
            outcomes=(Outcome.ABANDON,),
            gate_reason=GateReason.HALT,
            halt_reason="ceiling",
        ),
    )
    assert halt.metadata.gate_reason is GateReason.HALT
    # And it counts: the instance is now 2 beads over a limit of 1.
    assert bounds.ceiling_count(fake_store.reads.instance_beads(root.root_id)) == 2


def test_the_halt_gate_exemption_is_bounded_at_one_gate_per_instance(
    fake_store: WorkflowStore, definition: GraphDefinition
) -> None:
    # The exemption used to be keyed on the caller's free-text reason, so every
    # distinct string bought another ceiling-exempt bead — five of them past a
    # limit of two (probed, round-2 review). Keyed on the ROOT, the second call
    # re-finds the first gate and the reason is just metadata.
    root = make_root(
        fake_store,
        definition,
        ResolvedSetting(
            key="instance.max_total_activations",
            value=2,
            source=ConfigSource.INSTANCE_OVERRIDE,
        ),
    )
    fake_store.mint_activation(root.root_id, entry_request())
    opened = [
        fake_store.open_gate(
            root.root_id,
            GateOpenRequest(
                gate_node=IMPLEMENT,
                outcomes=(Outcome.ABANDON,),
                gate_reason=GateReason.HALT,
                halt_reason=f"ceiling-{index}",
            ),
        )
        for index in range(5)
    ]
    assert len({gate.gate_id for gate in opened}) == 1
    assert opened[0].metadata.halt_reason == "ceiling-0"
    assert len(fake_store.reads.list_gates(root.root_id)) == 1
    assert bounds.ceiling_count(fake_store.reads.instance_beads(root.root_id)) == 2
