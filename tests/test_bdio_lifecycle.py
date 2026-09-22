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
    entry_request,
    handle,
    load_definition,
    make_root,
    run_to_close,
)
from tests._fake_bd import FakeBd
from workflow_interpreter import GraphDefinition
from workflow_interpreter.bdio import bounds
from workflow_interpreter.bdio.api import WorkflowStore
from workflow_interpreter.bdio.errors import (
    BoundExceededError,
    CarrierIntegrityError,
    LifecycleConflictError,
)
from workflow_interpreter.bdio.wire import (
    ConfigSource,
    GateOpenRequest,
    GateReason,
    Lifecycle,
    ResolvedSetting,
)
from workflow_interpreter.ledger.store import LedgerStore
from workflow_interpreter.schema.models import Outcome

LABEL_FLAGS: Final[frozenset[str]] = frozenset({"--add-label", "--remove-label"})
CLAIM_FLAGS: Final[frozenset[str]] = frozenset({"--assignee", "--status"})
"""Store-restructure §3.4's addition: who holds a bead, and the status bd's own
`--claim` would have set. Not `--claim` itself, which binds the row to bd's user
identity rather than to the engine's configured actor."""
PRE_LEDGER_FLAGS: Final[frozenset[str]] = frozenset(
    {
        "-C",
        "--actor",
        "--json",
        "--silent",
        "--title",
        "--type",
        "--no-inherit-labels",
        "--metadata",
        "--event-payload",
        "--ephemeral",
        "--wisp-type",
        "--limit",
        "--all",
        "--include-gates",
        "--metadata-field",
        "--parent",
        "--claim",
        "--reason",
    }
)
"""Every flag the transport could construct BEFORE the run ledger. Spelled out
rather than derived, so the assertion below measures a change against a
recorded baseline instead of against itself."""
PRE_LEDGER_SUBCOMMANDS: Final[frozenset[str]] = frozenset(
    {"create", "update", "close", "show", "list", "dep", "context"}
)

STATUS_CLOSED: Final[str] = "closed"
STATUS_OPEN: Final[str] = "open"
LOW_BEAD_ID: Final[str] = "wf-000"
"""A bead id below every id FakeBd hands out — real bd ids are not ordered by
creation time (probed), and this is how that looks deterministically."""

PUBLIC_STORE_SURFACE: Final[frozenset[str]] = frozenset(
    {
        "append_event",
        "append_wake_event",
        "assert_member",
        "claims",
        "queue_decision",
        "record_envelope",
        "coordination_store",
        "close_activation",
        "clear_unobserved_session",
        "close_gate_verified",
        "create_root",
        "for_root",
        "mint_activation",
        "open_gate",
        "reads",
        "record_dispatch",
        "register_session",
        "record_session_completion",
        "record_session_tree",
        "reserve_in_place_steer",
        "record_control_state",
        "record_evidence",
        "record_exit",
        "record_precondition",
        "record_stale_flag",
        "settle_root",
        "startup_canary",
        "supersede_activation",
    }
)
"""Every public name on `WorkflowStore`. Adding one is a design change; the
point of the set is that a generic write cannot quietly join it.

`for_root` derives a root-scoped reader without exposing the sealed client.
`record_precondition` and `record_stale_flag` joined it in phase 3, as the
narrowest typed writes for the two facts the inspector owns and §3.2/§8.2
require in bd: the carry-forward trio proven before the exec, and the stale
flag. Each takes one frozen carrier and touches only its own keys.

`settle_root` joined it in phase 8 (cr-o85.34.24): the one write that records
which terminal an instance reached and closes its root on that fact.

`append_wake_event` adds a frozen notification payload only; it cannot close
carriers, approve gates, change bounds, or route a transition.

`register_session` binds a correlated vendor thread to the dispatched launch;
it verifies root, activation, launch, and original process identity.

`clear_unobserved_session` is its inverse and its safety net: §5.6 recovery
drops a `prepare()`-preassigned id that no vendor event ever confirmed, so an
invented id can never become resume history. It writes one key, and only when
no registration exists.

`claims` joined it in S0 of the run ledger: the integration-target claim is a
shared row with no root and no lifecycle, and the contractor used to read and
write it through the transport itself. It is a read plus a create-or-merge of
one opaque payload — it can close nothing and approve nothing.

`record_session_tree` joined it in S3 of crew sessions: the §3 tree OID a
writing turn left, written once and only before settlement, so a resumed
writer can prove the shared checkout is still the one its session remembers.

S2 of the run ledger added NOTHING here. The one design change it records is
one level down, on the transport: `bd update --add-label|--remove-label`
(run-ledger §3.2.3), asserted below."""


@pytest.fixture(scope="session")
def definition() -> GraphDefinition:
    """The §2 canonical fixture, loaded and hashed once."""
    return load_definition()


# --- the sealed write surface (§0.1) ------------------------------------


def test_the_store_exposes_no_write_that_skips_verification(
    fake_store: WorkflowStore,
) -> None:
    public = {name for name in dir(fake_store) if not name.startswith("_")}
    assert public == PUBLIC_STORE_SURFACE
    # The two named escape hatches the review found, specifically:
    assert not hasattr(fake_store, "client")
    assert not hasattr(fake_store.coordination_store(), "client")
    assert not hasattr(fake_store.coordination_store(), "save")
    assert not hasattr(fake_store, "update_root_bounds")


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
    facade.instance_records(root.root_id)
    facade.list_activations(root.root_id)
    facade.list_gates(root.root_id)
    facade.list_wake_events(root.root_id)
    facade.find_by_idempotency_key(root.root_id, minted.idempotency_key)
    facade.find_gate(root.root_id, "nope")
    facade.find_event(root.root_id, "nope")
    writes_after = [
        name for name, _ in fake_bd.calls if name in {"create", "update", "close"}
    ]
    assert writes_after == writes_before


# --- repair-forward finalizers (§5.1) -----------------------------------


def test_a_close_that_landed_before_its_metadata_is_still_completed(
    fake_store: WorkflowStore, fake_client: LedgerStore, definition: GraphDefinition
) -> None:
    # The other order: the bead is closed with no routing truth recorded. The
    # next call must write the outcome and re-drive the close, not refuse.
    root = make_root(fake_store, definition)
    activation = fake_store.mint_activation(root.root_id, entry_request()).activation
    fake_store.record_dispatch(activation.activation_id, handle())
    fake_client._close_row(activation.activation_id, "outcome=stale")

    repaired = fake_store.close_activation(activation.activation_id, Outcome.DONE)
    assert repaired.metadata.outcome is Outcome.DONE
    assert repaired.close_reason == "outcome=done"


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


# --- terminal outcomes are not overwritable (§3.2, §3.3) ----------------


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


# --- interleaved mints (§3.2 race residue) ------------------------------


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
    assert bounds.ceiling_count(fake_store.reads.instance_records(root.root_id)) == 2


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
    assert bounds.ceiling_count(fake_store.reads.instance_records(root.root_id)) == 2
