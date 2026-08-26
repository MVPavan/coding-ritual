"""The two phase-3 writes: the §3.2 carry-forward trio and the §8.2 stale flag.

Both are the narrowest typed surface for a fact the supervisor owns and bd has
to carry, and both are here for the same two questions every other write in
this package answers: is a repeat a no-op, and does a CONTRADICTION fail loud
rather than silently overwrite?

The trio has a third: it must be frozen once the child has run. bd merges
metadata wholesale per key with no compare-and-set, so nothing would stop a
late write from rewriting the base a later rework derives from (§3.2).

And both have a fourth, which is what this family is really for now.
`FakeBd.pause_before` runs a callback immediately before a chosen command, so
"another writer landed between the read and the write" is expressible as
ordinary single-threaded code. That is how the whole-carrier merge was caught:
the supervisor is a RESIDENT process (B5), so it is not serialised by the §4
tick, and a stale carrier re-emitted `lifecycle` and `handle` from read time —
dragging a closed activation back to `dispatched` under a bd row already marked
closed. Every write here is now delta-only over a freshly read record, and the
interleaving tests below are the proof.
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from pathlib import Path
from typing import Final

import pytest
from pydantic import ValidationError

from tests._bdio import entry_request, handle, load_definition, make_root, race_residue
from tests._fake_bd import FakeBd, InjectedCrash
from workflow_interpreter import GraphDefinition
from workflow_interpreter.bdio import (
    CarrierIntegrityError,
    Deviation,
    Evidence,
    ExitRecord,
    Lifecycle,
    LifecycleConflictError,
    Outcome,
    PreconditionRecord,
    StaleFlagRecord,
    WorkflowStore,
    transitions,
)
from workflow_interpreter.bdio.client import STATUS_CLOSED, BdClient
from workflow_interpreter.bdio.config import BdConfig
from workflow_interpreter.bdio.wire import KEY_LIFECYCLE

ACTOR: Final[str] = "wf-test-precondition"
HEAD: Final[str] = "a" * 40
ATTEMPT: Final[str] = "b" * 40
OTHER: Final[str] = "c" * 40
DIRTY: Final[str] = '{"entries":[],"stash_commit":null}'
RAISED_AT: Final[str] = "2026-08-25T12:10:00Z"
LAST_ACTIVITY: Final[str] = "2026-08-25T12:00:00Z"
STEER_REASON: Final[str] = "the runner has been quiet for an hour"
UPDATE: Final[str] = "update"
FLAG_METADATA: Final[str] = "--metadata"


@pytest.fixture(scope="session")
def definition() -> GraphDefinition:
    """The §2 canonical fixture, loaded and hashed once."""
    return load_definition()


@pytest.fixture
def bd(tmp_path: Path) -> FakeBd:
    """The in-memory bd workspace, exposed so a test can schedule against it."""
    workspace = tmp_path / "ws"
    workspace.mkdir()
    return FakeBd(str(workspace))


@pytest.fixture
def client(bd: FakeBd) -> BdClient:
    """The typed client the store writes through, exposed so a test can plant
    genuine §3.2 race residue (a second bead under one idempotency key)."""
    return BdClient(BdConfig(workspace=Path(bd.workspace), actor=ACTOR), bd)


@pytest.fixture
def store(client: BdClient) -> Iterator[WorkflowStore]:
    """A typed store over an in-memory bd workspace."""
    yield WorkflowStore(client, branch_head_reader=lambda: HEAD)


def _minted(store: WorkflowStore, definition: GraphDefinition) -> str:
    """One freshly minted activation of a fresh instance."""
    root = make_root(store, definition)
    return store.mint_activation(root.root_id, entry_request()).activation.activation_id


def _record(**overrides: object) -> PreconditionRecord:
    """The §3.2 trio a §5.4 precondition would have proven."""
    values: dict[str, object] = {
        "pre_attempt_commit": ATTEMPT,
        "reset_verified_commit": ATTEMPT,
        "pre_attempt_dirty_state": DIRTY,
    }
    return PreconditionRecord.model_validate(values | overrides)


def test_the_trio_lands_on_the_activation(
    store: WorkflowStore, definition: GraphDefinition
) -> None:
    """§3.2: `bdio.mint` READS `pre_attempt_commit`; something has to write it."""
    activation_id = _minted(store, definition)

    recorded = store.record_precondition(activation_id, _record())

    assert recorded.metadata.pre_attempt_commit == ATTEMPT
    assert recorded.metadata.reset_verified_commit == ATTEMPT
    assert recorded.metadata.pre_attempt_dirty_state == DIRTY


def test_recording_the_same_trio_twice_writes_once(
    store: WorkflowStore, bd: FakeBd, definition: GraphDefinition
) -> None:
    """A crashed dispatch re-proves the precondition; that is not a second write.

    Counted rather than inferred (Opus#31): comparing the metadata before and
    after cannot tell a skipped write from a write that landed identical
    values, and only the first is idempotence.
    """
    activation_id = _minted(store, definition)
    store.record_precondition(activation_id, _record())
    before = store.reads.load_activation(activation_id)
    writes = bd.command_count(UPDATE)

    again = store.record_precondition(activation_id, _record())

    assert again.metadata == before.metadata
    assert bd.command_count(UPDATE) == writes


def test_an_activation_with_no_trio_is_not_treated_as_already_recorded(
    store: WorkflowStore, bd: FakeBd, definition: GraphDefinition
) -> None:
    """Sol#26: the all-empty sentinel satisfied idempotence and skipped the write.

    The recorded trio was read back as `commit or ""`, so an activation that had
    NOTHING recorded compared equal to a carrier of two empty strings — and a
    caller handing in an empty record got "already recorded" with no write at
    all. `None` and "recorded as empty" are now different answers, and an empty
    string is no longer a value a `PreconditionRecord` can hold.
    """
    activation_id = _minted(store, definition)
    writes = bd.command_count(UPDATE)

    store.record_precondition(activation_id, _record())

    assert bd.command_count(UPDATE) == writes + 1
    with pytest.raises(ValidationError):
        _record(pre_attempt_commit="", reset_verified_commit="")


def test_the_trio_may_be_re_proven_while_the_activation_is_still_minted(
    store: WorkflowStore, definition: GraphDefinition
) -> None:
    """Before the exec the tree can still move; the record follows it."""
    activation_id = _minted(store, definition)
    store.record_precondition(activation_id, _record())

    updated = store.record_precondition(
        activation_id, _record(pre_attempt_commit=OTHER, reset_verified_commit=OTHER)
    )

    assert updated.metadata.pre_attempt_commit == OTHER


def test_the_trio_is_frozen_once_the_child_has_run(
    store: WorkflowStore, definition: GraphDefinition
) -> None:
    """After dispatch it describes a tree the runner ALREADY worked in (§3.2)."""
    activation_id = _minted(store, definition)
    store.record_precondition(activation_id, _record())
    store.record_dispatch(activation_id, handle())

    with pytest.raises(LifecycleConflictError, match="ALREADY ran against"):
        store.record_precondition(activation_id, _record(pre_attempt_commit=OTHER))


def test_re_asserting_the_recorded_trio_after_dispatch_is_a_no_op(
    store: WorkflowStore, definition: GraphDefinition
) -> None:
    """Repair-forward: the same values are idempotent, not a conflict."""
    activation_id = _minted(store, definition)
    store.record_precondition(activation_id, _record())
    store.record_dispatch(activation_id, handle())

    assert (
        store.record_precondition(activation_id, _record()).metadata.handle is not None
    )


def test_the_stale_flag_reaches_bd(
    store: WorkflowStore, definition: GraphDefinition
) -> None:
    """§8.2: the flag is a file AND bd metadata; the file alone dies with `.wf/`."""
    activation_id = _minted(store, definition)
    store.record_dispatch(activation_id, handle())

    recorded = store.record_stale_flag(
        activation_id,
        StaleFlagRecord(raised_at=RAISED_AT, last_activity_at=LAST_ACTIVITY),
    )

    assert recorded.metadata.stale_flag is not None
    assert recorded.metadata.stale_flag.raised_at == RAISED_AT


def test_a_re_raised_stale_flag_keeps_its_first_timestamp(
    store: WorkflowStore, definition: GraphDefinition
) -> None:
    """§8.2: staleness is a hint, and rewriting WHEN it started destroys it."""
    activation_id = _minted(store, definition)
    store.record_dispatch(activation_id, handle())
    store.record_stale_flag(
        activation_id,
        StaleFlagRecord(raised_at=RAISED_AT, last_activity_at=LAST_ACTIVITY),
    )

    again = store.record_stale_flag(
        activation_id,
        StaleFlagRecord(raised_at="2026-08-25T13:00:00Z", last_activity_at=RAISED_AT),
    )

    assert again.metadata.stale_flag is not None
    assert again.metadata.stale_flag.raised_at == RAISED_AT


def test_a_stale_flag_on_a_finished_child_is_refused(
    store: WorkflowStore, definition: GraphDefinition
) -> None:
    """A stale flag is a statement about a RUNNING child (§8.2)."""
    activation_id = _minted(store, definition)
    store.record_dispatch(activation_id, handle())
    store.record_exit(
        activation_id,
        ExitRecord(exit_code=0, ended_at=RAISED_AT, reason="exited"),
    )

    with pytest.raises(LifecycleConflictError, match="not dispatched"):
        store.record_stale_flag(
            activation_id,
            StaleFlagRecord(raised_at=RAISED_AT, last_activity_at=LAST_ACTIVITY),
        )


def test_re_raising_a_recorded_flag_after_the_child_finished_is_refused(
    store: WorkflowStore, definition: GraphDefinition
) -> None:
    """Sol#28: the first-raise short-circuit ran BEFORE the lifecycle guard.

    So the documented "dispatched only" refusal was steppable simply by asking
    twice: the first raise recorded the flag, and every later assertion — on an
    exited, closed, superseded activation — returned that flag and reported
    success. The guard now runs first, so the refusal is about the activation's
    STATE and not about whether a value happens to be there already.
    """
    activation_id = _minted(store, definition)
    store.record_dispatch(activation_id, handle())
    store.record_stale_flag(
        activation_id,
        StaleFlagRecord(raised_at=RAISED_AT, last_activity_at=LAST_ACTIVITY),
    )
    store.record_exit(
        activation_id, ExitRecord(exit_code=0, ended_at=RAISED_AT, reason="exited")
    )

    with pytest.raises(LifecycleConflictError, match="not dispatched"):
        store.record_stale_flag(
            activation_id,
            StaleFlagRecord(raised_at=RAISED_AT, last_activity_at=LAST_ACTIVITY),
        )


# --- carrier validation (Sol#26) -----------------------------------------


@pytest.mark.parametrize(
    "overrides",
    [
        {"pre_attempt_commit": ""},
        {"reset_verified_commit": "not-a-commit"},
        {"pre_attempt_commit": "A" * 40},
        {"pre_attempt_commit": "a" * 39},
        {"pre_attempt_dirty_state": "not json at all"},
        {"pre_attempt_dirty_state": "[]"},
        {"pre_attempt_dirty_state": '{"stash_commit": null, "entries": []}'},
    ],
    ids=[
        "empty-commit",
        "not-a-commit",
        "uppercase-oid",
        "short-oid",
        "dirty-state-not-json",
        "dirty-state-not-an-object",
        "dirty-state-not-canonical",
    ],
)
def test_the_trio_refuses_a_value_that_is_not_what_it_claims(
    overrides: dict[str, object],
) -> None:
    """Sol#26: bd cannot help here, so the carrier has to check itself.

    The write is a key-scoped merge with no compare-and-set and no schema on
    bd's side, so a malformed trio simply lands — and a LATER activation
    derives its `intended_base_commit` from it (§3.2). The non-canonical case
    is not pedantry: idempotence is a string comparison, so two spellings of
    one snapshot compare unequal forever and re-write on every dispatch.
    """
    with pytest.raises(ValidationError):
        _record(**overrides)


# --- interleaving: the resident supervisor vs. the foreman tick ----------


def test_a_precondition_write_cannot_drag_a_dispatch_backwards(
    store: WorkflowStore, bd: FakeBd, definition: GraphDefinition
) -> None:
    """Sol#7: the whole-carrier merge re-emitted state read BEFORE the dispatch.

    Two writers both read `minted`; the second's merge then wrote `lifecycle`
    and `handle` back as they stood at ITS read, reverting a recorded dispatch
    and losing the handle §5.6 needs to prove liveness. The write is now
    delta-only — the three trio keys and nothing else — so the keys it does not
    own cannot travel with it.
    """
    activation_id = _minted(store, definition)
    bd.pause_before(UPDATE, lambda: store.record_dispatch(activation_id, handle()))

    store.record_precondition(activation_id, _record())

    metadata = store.reads.load_activation(activation_id).metadata
    assert metadata.lifecycle is Lifecycle.DISPATCHED
    assert metadata.handle == handle()
    assert metadata.pre_attempt_commit == ATTEMPT


def test_a_stale_mirror_cannot_reopen_an_activation_the_foreman_closed(
    store: WorkflowStore, bd: FakeBd, definition: GraphDefinition
) -> None:
    """Blocker 4 (probed): `status=closed` with `lifecycle=dispatched`.

    The stale mirror runs in the RESIDENT supervisor process, which by B5's own
    design outlives the foreman tick — so it is not serialised by the §4
    single-flight lock the docstring used to claim. A foreman that closes the
    same activation between the mirror's read and its write (a §8.1 steer,
    which is exactly what a stale flag is meant to provoke) had `lifecycle`
    dragged back to `dispatched` under a bd row already marked closed. §5.6
    then read that as recoverable and `record_exit` became legal again.

    Delta-only fixes it structurally: `lifecycle` is not in the payload, so no
    interleaving can move it. The residual race costs one `stale_flag` key on a
    closed activation, which nothing routes on.
    """
    activation_id = _minted(store, definition)
    store.record_dispatch(activation_id, handle())

    def foreman_steers() -> None:
        store.close_activation(
            activation_id,
            Outcome.STEERED,
            deviations=(
                Deviation(kind="steer", reason=STEER_REASON, recorded_at=RAISED_AT),
            ),
        )

    bd.pause_before(UPDATE, foreman_steers)

    store.record_stale_flag(
        activation_id,
        StaleFlagRecord(raised_at=RAISED_AT, last_activity_at=LAST_ACTIVITY),
    )

    row = bd.rows[activation_id]
    metadata = store.reads.load_activation(activation_id).metadata
    assert row["status"] == STATUS_CLOSED
    assert metadata.lifecycle is Lifecycle.CLOSED
    assert metadata.outcome is Outcome.STEERED
    assert metadata.stale_flag is not None


# --- the §5.1 transitions: delta-only, and terminal-outcome-safe ---------


def _last_metadata_keys(bd: FakeBd) -> frozenset[str]:
    """The metadata keys of the most recent `bd update` this workspace served.

    Read off the argv rather than off the row, because the row cannot tell a
    key that was WRITTEN from one that was merely already there — and "which
    keys did this transition emit" is the whole question.
    """
    argv = next(argv for name, argv in reversed(bd.calls) if name == UPDATE)
    return frozenset(json.loads(argv[argv.index(FLAG_METADATA) + 1]))


def _clobber_lifecycle(bd: FakeBd, activation_id: str, lifecycle: Lifecycle) -> None:
    """Leave the row a losing race leaves when nothing repairs it.

    `status=closed` with a recorded outcome under a NON-terminal `lifecycle`.
    `transitions.apply` repairs that forward inside the call that caused it, so
    reaching the state through the API alone would need the wrapper to die in
    the one instruction between the merge and the repair. It is still reachable
    — an older build, a hand-edited bead, a bd write from outside this package
    — and the guards below are what make it harmless, so the test states it
    directly instead of choreographing a second crash.
    """
    bd.rows[activation_id]["metadata"][KEY_LIFECYCLE] = lifecycle.value


def _steer(store: WorkflowStore, activation_id: str) -> None:
    """What a foreman tick does to an activation the supervisor still owns."""
    store.close_activation(
        activation_id,
        Outcome.STEERED,
        deviations=(
            Deviation(kind="steer", reason=STEER_REASON, recorded_at=RAISED_AT),
        ),
    )


def test_a_transition_writes_only_the_keys_it_owns(
    store: WorkflowStore, bd: FakeBd, definition: GraphDefinition
) -> None:
    """Opus#17: `_apply` re-emitted the WHOLE carrier from the opening read.

    Which meant every key the transition does not own travelled with it, at the
    value it had before any interleaved writer touched it — so a `record_exit`
    issued by the resident supervisor rolled the foreman's `deviations`,
    `evidence` and `usage` back to their pre-close values. A transition owns
    `lifecycle` and its own record; this asserts it emits nothing else.
    """
    activation_id = _minted(store, definition)
    store.record_dispatch(activation_id, handle())
    assert _last_metadata_keys(bd) == frozenset({KEY_LIFECYCLE, "handle"})

    store.record_exit(
        activation_id, ExitRecord(exit_code=0, ended_at=RAISED_AT, reason="exited")
    )
    assert _last_metadata_keys(bd) == frozenset({KEY_LIFECYCLE, "exit_record"})

    store.record_evidence(activation_id, Evidence(note="verified"))
    assert _last_metadata_keys(bd) == frozenset({KEY_LIFECYCLE, "evidence"})


def test_a_dispatch_landing_after_a_close_does_not_survive_it(
    store: WorkflowStore, bd: FakeBd, definition: GraphDefinition
) -> None:
    """Opus#17 case C: the foreman closes between the guard and the merge."""
    activation_id = _minted(store, definition)
    bd.pause_before(
        UPDATE, lambda: store.close_activation(activation_id, Outcome.ERROR_TRANSPORT)
    )

    store.record_dispatch(activation_id, handle())

    metadata = store.reads.load_activation(activation_id).metadata
    assert bd.rows[activation_id]["status"] == STATUS_CLOSED
    assert metadata.outcome is Outcome.ERROR_TRANSPORT
    assert metadata.lifecycle is Lifecycle.CLOSED
    assert metadata.is_completed


def test_an_exit_landing_after_a_close_does_not_survive_it(
    store: WorkflowStore, bd: FakeBd, definition: GraphDefinition
) -> None:
    """Opus#17 case B, the blocker shape: `status=closed lifecycle=exit-recorded`.

    The exit record itself is kept — it is a true observation of a child that
    really did exit, and bd cannot clear a key anyway — but the §3.3 routing
    truth and the §5.1 terminal both stand.
    """
    activation_id = _minted(store, definition)
    store.record_dispatch(activation_id, handle())
    bd.pause_before(UPDATE, lambda: _steer(store, activation_id))

    store.record_exit(
        activation_id, ExitRecord(exit_code=0, ended_at=RAISED_AT, reason="exited")
    )

    metadata = store.reads.load_activation(activation_id).metadata
    assert metadata.outcome is Outcome.STEERED
    assert metadata.lifecycle is Lifecycle.CLOSED
    assert metadata.is_completed
    assert metadata.exit_record is not None
    # The steer deviation is the key a whole-carrier merge silently rolled back.
    assert [deviation.kind for deviation in metadata.deviations] == ["steer"]


def test_evidence_landing_after_a_close_does_not_survive_it(
    store: WorkflowStore, bd: FakeBd, definition: GraphDefinition
) -> None:
    """Opus#17 case D: the same race one transition later."""
    activation_id = _minted(store, definition)
    store.record_dispatch(activation_id, handle())
    store.record_exit(
        activation_id, ExitRecord(exit_code=0, ended_at=RAISED_AT, reason="exited")
    )
    bd.pause_before(UPDATE, lambda: _steer(store, activation_id))

    store.record_evidence(activation_id, Evidence(note="recomputed §7"))

    metadata = store.reads.load_activation(activation_id).metadata
    assert metadata.outcome is Outcome.STEERED
    assert metadata.lifecycle is Lifecycle.CLOSED
    assert metadata.is_completed


def test_a_recorded_outcome_refuses_every_later_state_write(
    store: WorkflowStore, bd: FakeBd, definition: GraphDefinition
) -> None:
    """Opus#17's chain: `record_evidence` was LEGAL on the clobbered row.

    `status=closed lifecycle=exit-recorded outcome=steered` passed the
    lifecycle guard of every transition whose `expected` state it happened to
    be sitting in, so §7 evidence could be recomputed onto an activation a
    continuation had already been minted from. The refusal keys on the recorded
    OUTCOME now, which no later `lifecycle` write can move.
    """
    activation_id = _minted(store, definition)
    store.record_dispatch(activation_id, handle())
    store.record_exit(
        activation_id, ExitRecord(exit_code=0, ended_at=RAISED_AT, reason="exited")
    )
    _steer(store, activation_id)
    _clobber_lifecycle(bd, activation_id, Lifecycle.EXIT_RECORDED)

    with pytest.raises(LifecycleConflictError, match="already recorded outcome"):
        store.record_evidence(activation_id, Evidence(note="recomputed §7"))

    _clobber_lifecycle(bd, activation_id, Lifecycle.DISPATCHED)
    with pytest.raises(LifecycleConflictError, match="already recorded outcome"):
        store.record_exit(
            activation_id,
            ExitRecord(exit_code=0, ended_at=RAISED_AT, reason="exited"),
        )
    with pytest.raises(LifecycleConflictError, match="already recorded outcome"):
        store.record_dispatch(activation_id, handle())


def test_a_close_cannot_overwrite_the_outcome_a_clobbered_row_still_records(
    store: WorkflowStore, bd: FakeBd, definition: GraphDefinition
) -> None:
    """Opus#17's end: `close_activation(DONE)` over a recorded `STEERED`.

    The close's conflict guard used to require `lifecycle == closed`, which the
    losing race had already moved — so the guard was skipped and the second
    close overwrote the outcome §3.3 routes on. It keys on the recorded outcome
    now. A bd row closed with NO recorded outcome is a different state (the
    §5.1 crash window) and is still repaired forward, which is what
    `test_a_close_that_landed_before_its_metadata_is_still_completed` holds.
    """
    activation_id = _minted(store, definition)
    store.record_dispatch(activation_id, handle())
    _steer(store, activation_id)
    _clobber_lifecycle(bd, activation_id, Lifecycle.EXIT_RECORDED)

    with pytest.raises(LifecycleConflictError, match="already closed"):
        store.close_activation(
            activation_id, Outcome.DONE, evidence=Evidence(note="done")
        )

    metadata = store.reads.load_activation(activation_id).metadata
    assert metadata.outcome is Outcome.STEERED
    assert bd.rows[activation_id]["close_reason"] == "outcome=steered"


def test_a_supersede_cannot_overwrite_the_outcome_a_clobbered_row_records(
    store: WorkflowStore, client: BdClient, bd: FakeBd, definition: GraphDefinition
) -> None:
    """The last typed call that walked through a recorded outcome (r4).

    `supersede_activation` guarded on `is_completed`, which REQUIRES
    `lifecycle == closed` — exactly the key a losing merge moves. The clobbered
    row is built here the way a SIGKILL builds it rather than by editing the
    row: the foreman's steer lands from inside our `bd update`, and the wrapper
    dies in the one window `repair_forward` occupies, leaving
    `status=closed lifecycle=exit-recorded outcome=steered` behind. Superseding
    that would turn the outcome a continuation was already minted from into
    `superseded` — forged §3.3 routing truth with no signature anywhere.
    """
    root = make_root(store, definition)
    winner = store.mint_activation(root.root_id, entry_request()).activation
    loser_id = race_residue(client, winner).activation_id
    store.record_dispatch(loser_id, handle())
    bd.pause_before(UPDATE, lambda: _steer(store, loser_id))
    bd.crash_on(UPDATE, 3)
    with pytest.raises(InjectedCrash):
        store.record_exit(
            loser_id, ExitRecord(exit_code=0, ended_at=RAISED_AT, reason="exited")
        )
    clobbered = store.reads.load_activation(loser_id).metadata
    assert clobbered.lifecycle is Lifecycle.EXIT_RECORDED
    assert clobbered.is_settled and not clobbered.is_completed

    with pytest.raises(CarrierIntegrityError, match="COMPLETED"):
        store.supersede_activation(loser_id, winner.activation_id)

    metadata = store.reads.load_activation(loser_id).metadata
    assert metadata.outcome is Outcome.STEERED
    assert metadata.superseded_by is None
    assert bd.rows[loser_id]["close_reason"] == "outcome=steered"


def test_the_transition_writer_itself_refuses_past_a_recorded_outcome(
    store: WorkflowStore, client: BdClient, bd: FakeBd, definition: GraphDefinition
) -> None:
    """The backstop under all four transitions, asserted where it lives.

    `apply` re-reads the activation immediately before the merge and used to
    re-assert only the LIFECYCLE — and `allowed` is a set of lifecycles, so the
    clobbered row (`outcome=steered` under a lifecycle a losing merge dragged
    back) sits inside it and the write went through. Each caller's own
    `assert_not_settled` runs against ITS read, one bd round-trip earlier, so it
    cannot see a row that settles in between; this guard can.
    """
    activation_id = _minted(store, definition)
    store.record_dispatch(activation_id, handle())
    _steer(store, activation_id)
    _clobber_lifecycle(bd, activation_id, Lifecycle.DISPATCHED)

    with pytest.raises(LifecycleConflictError, match="already recorded outcome"):
        transitions.apply(
            client,
            store.reads.load_activation,
            activation_id,
            lifecycle=Lifecycle.EXIT_RECORDED,
            allowed=transitions.OPEN_LIFECYCLES,
            exit_record=ExitRecord(exit_code=0, ended_at=RAISED_AT, reason="exited"),
        )

    metadata = store.reads.load_activation(activation_id).metadata
    assert metadata.outcome is Outcome.STEERED
    assert metadata.exit_record is None
