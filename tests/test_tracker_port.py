"""S5's tracker port: what the contractor's tracker touches become (§3.3, R2).

One conformance suite — the SAME landing rig, run against `NullTracker`,
`FileTracker` and the bd adapter — plus one case per acceptance line of the
slice. The rig is `test_contractor_in_ledger`'s, reused rather than rebuilt:
what changes between the three runs is the port and nothing else, which is the
whole claim the port makes.

The forced results (`Unknown`, `Conflict`) come from a thin decorator over a
real tracker rather than from a hand-built double: a fake that answered every
call would prove only that the caller reads its own stub.
"""

from __future__ import annotations

import threading
from collections.abc import Callable
from dataclasses import replace
from pathlib import Path
from typing import Final

import pytest

from tests._fake_bd import FakeBd, InjectedCrash
from tests._foreman import LAB_TASK, ForemanLab
from tests.test_contractor_cli import _entry
from tests.test_contractor_in_ledger import (
    EPIC,
    STAGE,
    STAGE_BRIEF,
    _abandon,
    _lab,
    _prepare_only,
)
from workflow_interpreter.bdio.client import BdClient
from workflow_interpreter.contractor.adapter import (
    ContractorAdapter,
    ContractorAdapterError,
)
from workflow_interpreter.contractor.models import ContractorRecord, ContractorState
from workflow_interpreter.contractor.tracker_config import (
    TrackerBackend,
    TrackerSettings,
)
from workflow_interpreter.contractor.tracker_wiring import (
    adapter_of,
    attention_writer,
    repair_mirror,
)
from workflow_interpreter.foreman import __main__ as main_module
from workflow_interpreter.foreman.tick import Foreman
from workflow_interpreter.ledger.closure import closed
from workflow_interpreter.ledger.constants import TrackerKind
from workflow_interpreter.ledger.reconcile import RootAttentionDrain
from workflow_interpreter.ledger.reverify import ExportAnchor, anchor_oid
from workflow_interpreter.tracker import (
    Applied,
    Blocker,
    Claim,
    Conflict,
    FileTracker,
    IntentKind,
    NullTracker,
    SetFlag,
    TrackerCapability,
    TrackerFlag,
    TrackerIntent,
    TrackerPort,
    TrackerRef,
    TrackerResult,
    Unknown,
    WorkItem,
    WorkItemStatus,
)
from workflow_interpreter.tracker.bd import BdTracker
from workflow_interpreter.tracker.outbox import TrackerOutbox

ACTOR: Final[str] = "test"
"""`ForemanLab`'s configured actor — the identity a claim is held by."""
BRIEF_FILE: Final[str] = "task-brief.md"


class _Decorated:
    """A real tracker with one intent kind forced to a declared result.

    The whole port, delegated: only `apply` is intercepted, and only for the
    kind under test, so every other call in the rig still goes to the tracker
    it is wrapping. `calls` is the counting half — acceptance 6 asks how many
    tracker calls a foreman tick makes, and the honest answer needs a counter
    on the port itself rather than on one implementation of it.
    """

    def __init__(
        self,
        inner: TrackerPort,
        *,
        forced: TrackerResult | None = None,
        kind: IntentKind | None = None,
    ) -> None:
        self._inner = inner
        self._forced = forced
        self._kind = kind
        self.calls: list[str] = []

    @property
    def kind(self) -> TrackerKind:
        return self._inner.kind

    @property
    def capabilities(self) -> frozenset[TrackerCapability]:
        return self._inner.capabilities

    def release(self) -> None:
        """Stop forcing, so the next contact answers from the real tracker."""
        self._forced = None

    def get(self, ref: TrackerRef) -> WorkItem | None:
        self.calls.append("get")
        return self._inner.get(ref)

    def children(self, ref: TrackerRef) -> tuple[WorkItem, ...]:
        self.calls.append("children")
        return self._inner.children(ref)

    def blockers(self, ref: TrackerRef) -> tuple[Blocker, ...]:
        self.calls.append("blockers")
        return self._inner.blockers(ref)

    def apply(self, intent: TrackerIntent) -> TrackerResult:
        self.calls.append(f"apply:{intent.kind.value}")
        if self._forced is not None and intent.kind is self._kind:
            return self._forced
        return self._inner.apply(intent)


def _file_tracker(
    lab: ForemanLab,
    *stages: str,
    capabilities: frozenset[TrackerCapability] | None = None,
) -> FileTracker:
    """A file tracker holding the same epic and stages the bd rig holds."""
    tracker = FileTracker(lab.repo.parent / "tracker.json", capabilities=capabilities)
    tracker.upsert(
        WorkItem(ref=EPIC, title="phase", brief=None, status=WorkItemStatus.OPEN)
    )
    for stage in stages:
        tracker.upsert(
            WorkItem(
                ref=stage,
                title="summary only",
                brief=STAGE_BRIEF,
                status=WorkItemStatus.OPEN,
                parent=EPIC,
            )
        )
    return tracker


def _brief_path(lab: ForemanLab) -> Path:
    """The `--brief` a run under `NullTracker` has to be given (§3.3)."""
    path = lab.repo.parent / BRIEF_FILE
    path.write_text(STAGE_BRIEF, encoding="utf-8")
    return path


def _outbox(lab: ForemanLab) -> TrackerOutbox:
    """This lab's outbox, as the contractor composes one."""
    assert lab.ledger is not None
    return TrackerOutbox(lab.ledger)


def _record(lab: ForemanLab, stage: str = STAGE) -> ContractorRecord:
    held = lab.records.read(stage)
    assert held is not None
    return held.record


@pytest.mark.acceptance
@pytest.mark.parametrize("tracker_kind", ["null", "file", "bd"])
def test_the_same_rig_lands_against_null_file_and_bd(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    signing_config,
    sign_payload,
    tracker_kind: str,
) -> None:
    """R2's whole claim: the contractor runs on any tracker, or on none.

    One rig, three ports. `NullTracker` declares no capabilities, so it is
    given the brief the tracker would otherwise have held (§3.3) and neither
    children nor blockers are consulted; the other two answer both. All three
    land, export and derive `closed()`.
    """
    lab = _lab(tmp_path, monkeypatch, signing_config, sign_payload, STAGE)
    extra: tuple[str, ...] = ()
    if tracker_kind == "null":
        lab.tracker = NullTracker()
        extra = ("--brief", str(_brief_path(lab)))
    elif tracker_kind == "file":
        lab.tracker = _file_tracker(lab, STAGE)
    else:
        lab.tracker = BdTracker(BdClient(lab.config.bd, lab.fake_bd))

    result = _entry(lab, STAGE, *extra)

    assert result.exit_code == 0, result.report
    assert _record(lab).state is ContractorState.LANDED
    assert closed(lab.ledger, lab.git, STAGE) is True
    assert _outbox(lab).pending() == ()
    if tracker_kind != "null":
        item = lab.tracker.get(TrackerRef(kind=lab.tracker.kind, ref=STAGE))
        assert item is not None and item.status is WorkItemStatus.CLOSED


@pytest.mark.acceptance
def test_unknown_on_close_leaves_the_landing_intact_and_one_pending_row(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, signing_config, sign_payload
) -> None:
    """§3.1, R7: the ledger is the truth and the tracker is a copy of it.

    The close mirror cannot fail a close that has already happened, so an
    `Unknown` leaves exactly one pending outbox row and nothing else — and the
    intent is a desired state, so the next drain simply applies it. The anchor
    that let the close run at all is the REF one (R7): nothing is committed
    here, and the sibling-blocking `closed()` still answers yes.
    """
    lab = _lab(tmp_path, monkeypatch, signing_config, sign_payload, STAGE)
    tracker = _Decorated(
        _file_tracker(lab, STAGE),
        forced=Unknown(reason="the tracker is unreachable"),
        kind=IntentKind.CLOSE,
    )
    lab.tracker = tracker

    result = _entry(lab, STAGE)

    assert result.exit_code == 0, result.report
    assert _record(lab).state is ContractorState.LANDED
    assert closed(lab.ledger, lab.git, STAGE) is True
    assert anchor_oid(lab.repo, STAGE)[0] is ExportAnchor.REF
    pending = _outbox(lab).pending()
    assert tuple(intent.kind for intent in pending) == (IntentKind.CLOSE,)

    tracker.release()
    drained = _outbox(lab).drain(tracker)

    assert (drained.applied, _outbox(lab).pending()) == (1, ())
    item = tracker.get(TrackerRef(kind=tracker.kind, ref=STAGE))
    assert item is not None and item.status is WorkItemStatus.CLOSED


@pytest.mark.acceptance
@pytest.mark.parametrize(
    "forced",
    [Unknown(reason="the tracker did not answer"), Conflict(reason="already held")],
    ids=["unknown", "conflict"],
)
def test_an_unanswered_claim_refuses_admission(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    signing_config,
    sign_payload,
    forced: TrackerResult,
) -> None:
    """§3.4, R3: ambiguity refuses, and the refusal is before the transition.

    The claim is the last thing before `BEGIN IMMEDIATE`, so a claim that was
    not applied leaves the record exactly where prepare left it: PREPARED,
    with no root and no admitted relation written.
    """
    lab = _lab(tmp_path, monkeypatch, signing_config, sign_payload, STAGE)
    lab.tracker = _Decorated(
        _file_tracker(lab, STAGE), forced=forced, kind=IntentKind.CLAIM
    )

    result = _entry(lab, STAGE)

    assert result.exit_code == 2
    record = _record(lab)
    assert (record.state, record.root_id) == (ContractorState.PREPARED, None)


@pytest.mark.acceptance
def test_a_refusal_or_a_crash_after_the_claim_releases_it(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, signing_config, sign_payload
) -> None:
    """§3.4: the only failures left inside the claim window, and their repair.

    A ledger refusal after the claim releases it on the spot. A CRASH cannot,
    so the same shape — a PREPARED row plus an item claimed by us — is detected
    per task on the next invocation and released before the fresh claim, which
    is why the port never needs a `list`.
    """
    lab = _lab(tmp_path, monkeypatch, signing_config, sign_payload, STAGE)
    tracker = _file_tracker(lab, STAGE)
    lab.tracker = tracker
    ref = TrackerRef(kind=tracker.kind, ref=STAGE)
    admit = ContractorAdapter.admit
    refused = _fail_admit(ContractorAdapterError("the ledger refused the transition"))

    monkeypatch.setattr(ContractorAdapter, "admit", refused)
    assert _entry(lab, STAGE).exit_code == 2

    held = tracker.get(ref)
    assert held is not None and held.claimed_by is None

    crashed = _fail_admit(InjectedCrash("the process died after the claim"))
    monkeypatch.setattr(ContractorAdapter, "admit", crashed)
    assert _entry(lab, STAGE).exit_code == 1
    stranded = tracker.get(ref)
    assert stranded is not None and stranded.claimed_by == ACTOR
    assert _record(lab).state is ContractorState.PREPARED

    monkeypatch.setattr(ContractorAdapter, "admit", admit)
    assert _entry(lab, STAGE).exit_code == 0

    assert _record(lab).state is ContractorState.LANDED
    assert not hasattr(TrackerPort, "list")


def _fail_admit(error: Exception) -> Callable[..., ContractorRecord]:
    """An admit that refuses, standing in for the ledger's own refusal."""

    def admit(
        self: ContractorAdapter, stage_id: str, record: object, *, root_id: str
    ) -> ContractorRecord:
        raise error

    return admit


@pytest.mark.acceptance
def test_an_externally_closed_item_marks_the_record_abandoned_external(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, signing_config, sign_payload
) -> None:
    """§3.8: a task somebody else ended is never guessed at, only observed.

    The claim is the next tracker contact after prepare, and an item already
    closed answers it with a `Conflict` naming that status. The record is
    retired as ABANDONED_EXTERNAL rather than admitted or silently re-opened.
    """
    lab = _lab(tmp_path, monkeypatch, signing_config, sign_payload, STAGE)
    tracker = _file_tracker(lab, STAGE)
    lab.tracker = tracker
    _prepare_only(lab, STAGE)
    ref = TrackerRef(kind=tracker.kind, ref=STAGE)
    tracker.upsert(
        tracker.get(ref).model_copy(update={"status": WorkItemStatus.CLOSED})
    )

    result = _entry(lab, STAGE)

    assert result.exit_code == 2
    assert _record(lab).state is ContractorState.ABANDONED_EXTERNAL


@pytest.mark.acceptance
def test_no_tracker_call_inside_a_tick_and_the_outbox_drains_at_exit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, signing_config, sign_payload
) -> None:
    """D6, §3.1: the tracker is never on the run loop's critical path.

    The foreman's attention projection goes through `SetFlag` on the outbox
    now, so a whole run's worth of ticks makes ZERO tracker calls; the outbox
    is drained once, as the driver exits, and nothing is left owed.
    """
    lab = _lab(tmp_path, monkeypatch, signing_config, sign_payload, STAGE)
    tracker = _Decorated(_file_tracker(lab, STAGE))
    lab.tracker = tracker
    # The production wiring of the projection (§3.3): the reconciler enqueues,
    # nothing in a tick contacts the tracker, and the drain happens at exit.
    lab.composition = replace(
        lab.composition,
        drain_attention=RootAttentionDrain(
            lab.ledger, attention_writer(lab.ledger, tracker)
        ),
    )
    inside: list[int] = []
    driven = Foreman.run

    def run(self: Foreman, root_id: str, **kwargs: object):
        before = len(tracker.calls)
        report = driven(self, root_id, **kwargs)
        inside.append(len(tracker.calls) - before)
        return report

    monkeypatch.setattr(Foreman, "run", run)

    assert _entry(lab, STAGE).exit_code == 0

    assert inside == [0]
    assert "apply:set_flag" in tracker.calls
    assert _outbox(lab).pending() == ()


@pytest.mark.acceptance
@pytest.mark.parametrize("required", [False, True], ids=["proceeds", "refuses"])
def test_a_tracker_without_blockers_records_the_gap_or_refuses(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    signing_config,
    sign_payload,
    required: bool,
) -> None:
    """R9: an absent capability is not liveness ambiguity — unless configured.

    Either way the record says which policy applied, so the trace can answer
    whether this task's blockers were ever looked at.
    """
    lab = _lab(tmp_path, monkeypatch, signing_config, sign_payload, STAGE)
    lab.tracker = _file_tracker(
        lab,
        STAGE,
        capabilities=frozenset(TrackerCapability) - {TrackerCapability.BLOCKERS},
    )
    lab.composition = replace(
        lab.composition,
        config=lab.composition.config.model_copy(
            update={"tracker": TrackerSettings(blockers_required=required)}
        ),
    )

    result = _entry(lab, STAGE)

    if required:
        assert result.exit_code == 2
        assert lab.records.read(STAGE) is None
        return
    assert result.exit_code == 0, result.report
    assert _record(lab).blockers_checked is False


@pytest.mark.acceptance
@pytest.mark.parametrize("command", ["run", "tick"])
def test_every_driver_exit_drains_the_outbox(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    signing_config,
    sign_payload,
    command: str,
) -> None:
    """D6: `wf contract` is not the only driver, so it is not the only drain.

    `wf run` and `wf tick` build the same composition, tick the foreman, let
    the reconciler enqueue a `SetFlag` and used to exit with the row still
    pending — so an operator driving a root with `wf run` never saw
    `wf:attention` until somebody happened to run `wf contract` or
    `wf ledger reconcile`. One drain, at every driver exit.
    """
    lab = ForemanLab(tmp_path, signing=signing_config, signer=sign_payload)
    # The null port, so the drain proves the DRAIN rather than a bd subprocess.
    lab.composition = replace(
        lab.composition,
        config=lab.config.model_copy(
            update={"tracker": TrackerSettings(backend=TrackerBackend.NULL)}
        ),
    )
    root = lab.instantiate()
    monkeypatch.setattr(main_module, "_composition", lambda _: lab.composition)
    assert lab.ledger is not None
    outbox = TrackerOutbox(lab.ledger)
    outbox.enqueue(
        LAB_TASK,
        SetFlag(
            ref=TrackerRef(kind=TrackerKind.NONE, ref=LAB_TASK),
            flag=TrackerFlag.ATTENTION.value,
            on=True,
        ),
    )
    assert len(outbox.pending()) == 1

    lab.transcript(lambda: main_module.main([command, root.root_id]))

    assert outbox.pending() == ()


@pytest.mark.acceptance
def test_the_abandon_fact_and_its_mirror_row_commit_or_roll_back_together(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, signing_config, sign_payload
) -> None:
    """§3.3: the crash between a fact and its outbox row is gone by construction.

    `enqueue` used to open a transaction of its own, so a crash after the
    transition and before the row lost the `Close` forever — a drain only
    applies rows that exist, and nothing re-derives one from a retired record.
    The row is written INSIDE the transition now, so there is no window to
    inject a crash into: the only thing left to assert is the atomicity, by
    failing the enqueue and finding the retirement gone with it.
    """
    lab = _lab(tmp_path, monkeypatch, signing_config, sign_payload, STAGE)
    lab.tracker = _file_tracker(lab, STAGE)
    lab.halt_after_implement = True
    assert _entry(lab, STAGE).exit_code == 0
    assert _record(lab).state is ContractorState.ADMITTED
    monkeypatch.setattr(
        TrackerOutbox,
        "enqueue",
        _fails("the process died between the fact and its mirror row"),
    )

    with pytest.raises(InjectedCrash):
        adapter_of(lab.composition).abandon(STAGE)

    # Neither half happened: the record is where it was, and nothing is owed.
    assert _record(lab).state is ContractorState.ADMITTED
    assert _outbox(lab).pending() == ()


def _fails(reason: str) -> Callable[..., None]:
    """An enqueue that dies, standing in for the crash the window allowed."""

    def enqueue(*_: object, **__: object) -> None:
        raise InjectedCrash(reason)

    return enqueue


@pytest.mark.acceptance
def test_ledger_reconcile_releases_the_claim_a_crash_stranded(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, signing_config, sign_payload
) -> None:
    """§3.4: `wf ledger reconcile <task>` is the OTHER repair path, so it repairs.

    A crash inside the claim window leaves a PREPARED record and an item this
    actor holds. `wf contract` detects that shape on its next invocation — but
    §3.4 also names this command, and it only drained the outbox, so on a
    machine where the next `wf contract` is days away the documented remedy
    did nothing and `bd ready` stayed wrong.
    """
    lab = _lab(tmp_path, monkeypatch, signing_config, sign_payload, STAGE)
    tracker = _file_tracker(lab, STAGE)
    lab.tracker = tracker
    ref = TrackerRef(kind=tracker.kind, ref=STAGE)
    _prepare_only(lab, STAGE)
    stranded = tracker.get(ref)
    assert stranded is not None and stranded.claimed_by == ACTOR

    repair_mirror(lab.composition.config, lab.ledger, lab.git, STAGE)

    released = tracker.get(ref)
    assert released is not None and released.claimed_by is None
    assert _record(lab).state is ContractorState.PREPARED
    assert _outbox(lab).pending() == ()


@pytest.mark.acceptance
def test_abandon_closes_the_tracker_the_configuration_names(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, signing_config, sign_payload
) -> None:
    """§3.3: the mirror goes where `tracker.backend` says, through the outbox.

    The whole command runs on production's own wiring — no adapter is
    substituted, and `tracker_for` builds the port from the configuration —
    because that wiring was the defect: eight of nine construction sites
    defaulted to a bd tracker and to no outbox, so `wf phase abandon` in a
    repository whose tasks live in a FILE closed a bd bead instead, with no
    pending row to say the real item was never touched.
    """
    lab = _lab(tmp_path, monkeypatch, signing_config, sign_payload, STAGE)
    _file_tracker(lab, STAGE)
    document = lab.repo.parent / "tracker.json"
    # Nothing injected: `tracker_for` reads this and builds the port itself.
    lab.tracker = None
    lab.composition = replace(
        lab.composition,
        config=lab.composition.config.model_copy(
            update={
                "tracker": TrackerSettings(backend=TrackerBackend.FILE, path=document)
            }
        ),
    )
    lab.halt_after_implement = True
    assert _entry(lab, STAGE).exit_code == 0
    served = len(lab.fake_bd.calls)

    exit_code, report = _abandon(lab, STAGE)

    assert (exit_code, report["state"]) == (0, "abandoned")
    item = FileTracker(document).get(TrackerRef(kind=TrackerKind.FILE, ref=STAGE))
    assert item is not None and item.status is WorkItemStatus.CLOSED
    assert lab.fake_bd.rows[STAGE]["status"] != "closed"
    assert lab.fake_bd.calls[served:] == []
    assert _outbox(lab).pending() == ()


def test_the_adapter_keeps_no_bd_read_beside_the_port() -> None:
    """R2, §3.3: ONE tracker surface, or the port is decoration.

    `show`, `direct_children`, `dependencies` and `blocking_dependencies` were
    the contractor's own bd reads. Each asked the TRANSPORT while `self.tracker`
    held the configured port, so a repository on the file tracker asked bd about
    its own stage — and `landing.recover` decided on that answer whether a close
    had completed. Their ABSENCE is the assertion: a method that still exists is
    one a call site drifts back to.
    """
    absent = [
        name
        for name in ("show", "direct_children", "dependencies", "blocking_dependencies")
        if hasattr(ContractorAdapter, name)
    ]

    assert absent == []


@pytest.mark.acceptance
def test_the_bd_adapter_holds_one_claim_at_a_time(
    fake_bd: FakeBd, fake_client: BdClient
) -> None:
    """§3.4, R3 on the tracker every checkout actually runs.

    bd has `assignee`, so the claim is a desired state there like anywhere
    else: claimed by us is `Applied` however often it is re-applied, claimed by
    somebody else is a `Conflict` that carries what was observed — which is
    what `_refuse_conflicted_claim` reads — and the release hands it back.
    Without this, claim-first, `_release_stranded` and external-close detection
    were all dead code on bd.
    """
    fake_bd.rows[STAGE] = {
        "id": STAGE,
        "title": "stage",
        "status": "open",
        "issue_type": "task",
        "metadata": {},
        "labels": [],
    }
    tracker = BdTracker(fake_client)
    ref = TrackerRef(kind=TrackerKind.BD, ref=STAGE)

    assert TrackerCapability.CLAIM in tracker.capabilities
    for _ in range(2):
        assert isinstance(tracker.apply(Claim(ref=ref, actor=ACTOR)), Applied)
    assert fake_bd.rows[STAGE]["assignee"] == ACTOR
    assert fake_bd.rows[STAGE]["status"] == "in_progress"

    disputed = tracker.apply(Claim(ref=ref, actor="somebody-else"))

    assert isinstance(disputed, Conflict)
    assert disputed.observed is not None and disputed.observed.claimed_by == ACTOR
    assert fake_bd.rows[STAGE]["assignee"] == ACTOR

    released = tracker.apply(Claim(ref=ref, actor=ACTOR, held=False))

    assert isinstance(released, Applied)
    assert not fake_bd.rows[STAGE]["assignee"]
    assert fake_bd.rows[STAGE]["status"] == "open"


class _RacingTracker(FileTracker):
    """A file tracker that holds the read open until its rival has read too.

    The window under test is read-whole → mutate → write-whole, and two plain
    threads hit it only by luck. So the window is FORCED: `_read` waits on a
    barrier, and the barrier is what makes both outcomes deterministic. With
    an exclusive lock the rival cannot reach `_read` at all, the barrier times
    out, and the two claims are serialised — which is the assertion.
    """

    def __init__(self, path: Path, *, barrier: threading.Barrier) -> None:
        super().__init__(path)
        self._barrier = barrier

    def _read(self) -> dict[str, object]:
        document = super()._read()
        try:
            self._barrier.wait(timeout=_RACE_TIMEOUT_S)
        except threading.BrokenBarrierError:
            pass
        return document


_RACE_TIMEOUT_S: Final[float] = 0.5


def test_two_racing_claims_on_one_item_leave_one_holder(tmp_path: Path) -> None:
    """§3.4 on the file tracker: a claim excludes across processes, or it lies.

    Two trackers over ONE document, each its own instance with its own file
    handle, claim the same item at the same moment. Exactly one may be
    `Applied`; the other has to see the first holder and conflict, and the
    document has to still parse afterwards — an interleaved write would leave
    a mixture no tracker can read again.
    """
    path = tmp_path / "tracker.json"
    FileTracker(path).upsert(
        WorkItem(ref=STAGE, title="stage", brief=None, status=WorkItemStatus.OPEN)
    )
    ref = TrackerRef(kind=TrackerKind.FILE, ref=STAGE)
    barrier = threading.Barrier(2)
    results: dict[str, TrackerResult] = {}

    def claim(actor: str) -> None:
        tracker = _RacingTracker(path, barrier=barrier)
        results[actor] = tracker.apply(Claim(ref=ref, actor=actor))

    racers = [threading.Thread(target=claim, args=(actor,)) for actor in ("one", "two")]
    for racer in racers:
        racer.start()
    for racer in racers:
        racer.join(timeout=10.0)

    kinds = sorted(result.result.value for result in results.values())
    assert kinds == ["applied", "conflict"]
    held = FileTracker(path).get(ref)
    assert held is not None and held.status is WorkItemStatus.IN_PROGRESS
    applied = next(
        actor for actor, result in results.items() if isinstance(result, Applied)
    )
    assert held.claimed_by == applied


def test_the_null_tracker_applies_every_intent_without_a_capability() -> None:
    """§3.3: no capabilities, and still every run completes.

    A `Claim` against nothing is `Applied` with nothing observed rather than a
    refusal: the whole point of the null port is that a run under no tracker is
    not a degraded run, it is a run with no mirror.
    """
    tracker = NullTracker()

    result = tracker.apply(
        Claim(ref=TrackerRef(kind=tracker.kind, ref=STAGE), actor=ACTOR)
    )

    assert isinstance(result, Applied) and result.observed is None
    assert tracker.capabilities == frozenset()
