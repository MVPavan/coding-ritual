"""S4's contractor half: what the record moving into the ledger BUYS (§3.3, R4).

`test_contractor_record.py` proves the row — the version guard, the fold, the
export branch. This file proves the four behaviours that row exists for, each
through the production CLI on the lab's real wiring:

1. everything after §3.4's claim runs with the tracker unreachable;
2. `wf phase abandon` retires a task, cleans it up and frees its sibling;
3. a retry admits from the brief snapshot without reading the tracker;
4. prepare is where the ledger mints the task from its tracker ref (§3.7).

The close is deliberately absent from (1): it still writes the tracker mirror
directly (`adapter.close`), and S5's outbox is what moves it off the critical
path. Asserting it here would pin the defect rather than the design.
"""

from __future__ import annotations

import json
import sys
from collections.abc import Callable
from dataclasses import replace
from pathlib import Path
from typing import Final

import pytest

from tests._fake_bd import InjectedCrash
from tests._foreman import ForemanLab
from tests._inspector import ChildScript
from tests.test_contractor_cli import _entry
from tests.test_foreman_main import _contractor_adapter, _contractor_stage
from workflow_interpreter.bdio import GateVerifier, WorkflowStore
from workflow_interpreter.bdio.backend import SelectableBackendFactory
from workflow_interpreter.bdio.client import BdClient
from workflow_interpreter.bdio.constants import BackendKind
from workflow_interpreter.contractor import command as command_module
from workflow_interpreter.contractor import tracker_wiring
from workflow_interpreter.contractor.adapter import ContractorAdapter
from workflow_interpreter.contractor.landing import LandingHooks
from workflow_interpreter.contractor.models import ContractorRecord, ContractorState
from workflow_interpreter.contractor.verification import CheckCommand
from workflow_interpreter.foreman import __main__ as main_module
from workflow_interpreter.foreman.compose import Composition
from workflow_interpreter.foreman.locator import RootBackendLocator
from workflow_interpreter.foreman.tick import Foreman, RunReport
from workflow_interpreter.ledger.archive import archive_task
from workflow_interpreter.ledger.claims import LedgerClaims
from workflow_interpreter.ledger.closure import closed, retired
from workflow_interpreter.ledger.constants import TrackerKind
from workflow_interpreter.ledger.paths import export_path
from workflow_interpreter.ledger.store import LedgerStore
from workflow_interpreter.schema.models import Outcome
from workflow_interpreter.tracker.bd import BdTracker

EPIC: Final[str] = "phase"
"""The parent `_contractor_stage` writes, and therefore the CLI's epic id."""
STAGE: Final[str] = "a"
SIBLING: Final[str] = "b"
STAGE_BRIEF: Final[str] = "the stage brief, read once and snapshotted"
_CLAIM_WINDOW_COMMANDS: Final[int] = 7
"""What §3.4 costs on bd when the last attempt crashed inside the claim window:
the stranded claim is detected and RELEASED (read, read, `--assignee ""`,
read-back), then the fresh claim is taken (read, `--assignee`, read-back)."""
PROOF_SCRIPT: Final[str] = (
    "from pathlib import Path; assert Path('src/feature.py').is_file()"
)
"""The contractor check the landing runs in its detached verify tree."""
REASON: Final[str] = "the slice was superseded"


def _lab(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    signing_config: object,
    sign_payload: object,
    *stages: str,
) -> ForemanLab:
    """A ledger-backed lab wired to run `stages` through the real contract CLI.

    `store=LEDGER` is what makes the tracker assertions mean anything: on bd
    every store write is also a bd command, so "the tracker was not called"
    would be unanswerable. Here the only bd commands left ARE tracker traffic.
    """
    lab = ForemanLab(
        tmp_path,
        signing=signing_config,
        signer=sign_payload,
        store=BackendKind.LEDGER,
    )
    lab.composition = replace(
        lab.composition,
        config=lab.config.model_copy(
            update={
                "contractor_checks": (
                    CheckCommand(
                        name="source-proof",
                        argv=(sys.executable, "-c", PROOF_SCRIPT),
                    ),
                )
            }
        ),
    )
    for stage in stages:
        lab.fake_bd.rows[stage] = _contractor_stage(stage, description=STAGE_BRIEF)
    lab.halt_after_implement = False
    # Which PORT the contractor runs on (S5). The default is the bd adapter
    # over this lab's own fake TRANSPORT — production's wiring, minus the
    # subprocess — and a case about another tracker sets a port here before the
    # first entry point runs. `None` means "let the configuration decide", so a
    # case can exercise `tracker_for` itself.
    lab.tracker = BdTracker(BdClient(lab.config.bd, lab.fake_bd))
    verifier = GateVerifier(signing_config, lab.config.bd.workspace)
    monkeypatch.setattr(
        main_module, "_composition", lambda args: _scoped(lab, verifier, args.stage_id)
    )
    # The ADAPTER is built by production's own wiring (S5 fix): it reads
    # `config.tracker`, it always holds the ledger's outbox, and the only thing
    # the lab substitutes is which port object that wiring returns — a
    # `_Decorated` counter or a pre-populated file document cannot be spelled
    # in a config file.
    real_tracker_for = tracker_wiring.tracker_for
    monkeypatch.setattr(
        tracker_wiring,
        "tracker_for",
        lambda settings, config, client=None: (
            real_tracker_for(settings, config, client)
            if lab.tracker is None
            else lab.tracker
        ),
    )
    monkeypatch.setattr(Foreman, "run", _drive(lab))
    return lab


def _scoped(lab: ForemanLab, verifier: GateVerifier, stage: str) -> Composition:
    """The composition production builds per invocation: scoped to ONE task.

    The lab wires every root it creates to the one synthetic task its driver
    owns, which is enough while a single contractor stage runs. Two stages of
    one epic — and an abandon with a blocked sibling IS two — need what
    production has: `--task` decides the ledger rows, the minted root ids
    `<task>-a<n>` and the locator (§3.7, D16). Sharing one task instead makes
    the second stage's root collide with the first stage's, and files the
    first stage's roots where `wf phase abandon` cannot find them.
    """
    factory = SelectableBackendFactory(
        BdClient(lab.config.bd, lab.fake_bd),
        LedgerStore(lab.ledger, task_id=stage, epic_id=EPIC),
    )
    lab.store = WorkflowStore(
        factory(BackendKind.LEDGER),
        verifier,
        backend_factory=factory,
        claims=LedgerClaims(lab.ledger),
    )
    lab.composition = replace(
        lab.composition,
        store=lab.store,
        task_id=stage,
        epic_id=EPIC,
        locate_backend=RootBackendLocator(stage, ledger=lab.ledger),
    )
    # The inline spawner writes the activation's records through the
    # composition it was bound to, so it follows the task too.
    lab.spawner.bind(lab.composition)
    return lab.composition


def _drive(lab: ForemanLab) -> Callable[..., RunReport]:
    """The real tick loop, driven to `shipped` — or halted mid-run on request.

    `lab.halt_after_implement` is the orchestrator's ordinary hand-back: one
    round of work is on disk, the root is live and nothing will ever take it
    to a terminal. That is the only state `wf phase abandon` is FOR.
    """

    def run(
        self: Foreman,
        root_id: str,
        *,
        poll_s: float,
        max_wall_s: float,
        monitored: bool = False,
    ) -> RunReport:
        lab.root = lab.composition.reads_for_root(root_id).load_root(root_id)
        lab.profiles.next_script(
            ChildScript(
                marker='{"outcome":"done"}\n',
                effects='{"paths":["src/feature.py"]}',
                write_path="src/feature.py",
                write_body="value = 2\n",
                commit=True,
            )
        )
        assert self.tick(root_id).dispatched
        settled = self.tick(root_id)
        assert settled.settled
        if lab.halt_after_implement:
            return RunReport(ticks=2, report=settled)
        lab.profiles.next_script(
            ChildScript(marker='{"outcome":"accept"}\n', effects='{"paths":[]}')
        )
        assert self.tick(root_id).dispatched
        assert self.tick(root_id).settled
        ship = self.tick(root_id).opened_gate
        assert ship
        lab.approve(ship, Outcome.APPROVE)
        assert self.tick(root_id).closed_gates == (ship,)
        report = self.tick(root_id)
        assert report.terminal
        return RunReport(ticks=7, report=report)

    return run


def _prepare_only(lab: ForemanLab, stage: str) -> ContractorRecord:
    """Leave the task PREPARED with its root created, as a crash there does.

    §3.4's window: prepare has written the record and the tracker has been
    read for the last time, and the admit that follows never lands.
    """

    def die(self: ContractorAdapter, stage_id: str, record: object, *, root_id: str):
        raise InjectedCrash("the process died between prepare and admit")

    original = ContractorAdapter.admit
    ContractorAdapter.admit = die  # type: ignore[method-assign]
    try:
        assert _entry(lab, stage).exit_code == 1
    finally:
        ContractorAdapter.admit = original  # type: ignore[method-assign]
    prepared = _contractor_adapter(lab).record(stage)
    assert prepared.state is ContractorState.PREPARED
    return prepared


def _admit_only(lab: ForemanLab, stage: str, *extra: str) -> ContractorRecord:
    """Admit `stage` through the production command without running it."""
    driven: list[str] = []

    def refuse(composition, adapter, record, *, monitored=False):
        driven.append(record.stage_id)
        raise AssertionError("the stage must not run yet")

    original = command_module._run_record
    command_module._run_record = refuse
    try:
        _entry(lab, stage, *extra)
    except AssertionError:
        pass
    finally:
        command_module._run_record = original
    assert driven == [stage]
    return _contractor_adapter(lab).record(stage)


def _abandon(lab: ForemanLab, stage: str) -> tuple[int, dict[str, object]]:
    """`wf phase abandon <stage> --reason …` through the real entry point."""
    codes: list[int] = []
    _, output = lab.transcript(
        lambda: codes.append(
            main_module.main(
                [
                    "--config",
                    str(lab.repo / "foreman.toml"),
                    "phase",
                    "abandon",
                    stage,
                    "--reason",
                    REASON,
                ]
            )
        )
    )
    return codes[0], json.loads(output.splitlines()[0])


@pytest.mark.acceptance
def test_everything_after_prepare_runs_with_the_tracker_gone(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, signing_config, sign_payload
) -> None:
    """S4's headline (R4), as §3.4 leaves it: the CLAIM is the last contact.

    The tracker is killed on the PREPARED record — one window later than it
    used to be. bd declares `CLAIM` now, and R3 says an unanswered claim
    refuses admission, so the tracker HAS to answer the crash repair and the
    fresh claim; that is the price of `bd ready` being exact for a second
    session, and it is the only thing R4's "admission runs with the tracker
    unreachable" gives up.

    Everything after it is unchanged: the run, the landing, the export pin and
    the archive are answered from the ledger alone, and the only call attempted
    once the tracker died is the close mirror's read, which leaves an outbox
    row rather than a durable fact.
    """
    lab = _lab(tmp_path, monkeypatch, signing_config, sign_payload, STAGE)
    _prepare_only(lab, STAGE)
    served = len(lab.fake_bd.calls)
    lab.fake_bd.refuse_after(_CLAIM_WINDOW_COMMANDS)

    result = _entry(lab, STAGE)

    after = lab.fake_bd.calls[served + _CLAIM_WINDOW_COMMANDS :]
    assert lab.fake_bd.rows[STAGE]["assignee"] == lab.config.actor
    assert {name for name, _ in after} == {"show"}
    assert result.exit_code == 1
    assert "InjectedCrash" in result.report["diagnostic"]
    # Admitted, run and landed with nothing but the ledger and the checkout.
    record = _contractor_adapter(lab).record(STAGE)
    assert record.state is ContractorState.LANDED
    assert export_path(lab.repo, STAGE).is_file()
    assert closed(lab.ledger, lab.git, STAGE) is True
    assert lab.fake_bd.rows[STAGE]["status"] != "closed"
    archived = archive_task(
        lab.git,
        lab.ledger,
        STAGE,
        bundle=tmp_path / "archive" / f"{STAGE}.bundle",
        repo_root=lab.repo,
        wrapper_root=lab.inspector_config.wrapper_root,
    )
    assert archived.bundle.is_file()


@pytest.mark.acceptance
def test_abandon_retires_a_task_cleans_it_up_and_frees_its_sibling(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, signing_config, sign_payload
) -> None:
    """§3.8: the orchestrator's third verb, and everything that follows from it.

    An abandoned task is `retired()` without being `closed()` — the work never
    landed, so nothing may read it as finished — and that is precisely what
    unblocks the sibling `_refuse_other_admission` was holding, what lets
    cleanup delete a worktree no tick will ever reach, and what makes a second
    abandon a repeat of a decision rather than a refusal. A LANDED task is
    refused by name: its work is on the target ref.
    """
    lab = _lab(tmp_path, monkeypatch, signing_config, sign_payload, STAGE, SIBLING)
    lab.halt_after_implement = True
    assert _entry(lab, STAGE).exit_code == 0
    admitted = _contractor_adapter(lab).record(STAGE)
    assert admitted.state is ContractorState.ADMITTED
    worktree = lab.composition.for_root(admitted.root_id or "").paths.worktree
    assert worktree.exists()
    blocked = _entry(lab, SIBLING)
    assert blocked.report["state"] == "blocked"
    assert blocked.report["blocking_ids"] == [STAGE]

    exit_code, report = _abandon(lab, STAGE)

    assert (exit_code, report["state"]) == (0, "abandoned")
    assert report["roots_cleaned"] == [admitted.root_id]
    assert _contractor_adapter(lab).record(STAGE).state is ContractorState.ABANDONED
    assert retired(lab.ledger, lab.git, STAGE) is True
    assert closed(lab.ledger, lab.git, STAGE) is False
    assert not worktree.exists()
    # A decision, not an event: repeating it answers the same record.
    assert _abandon(lab, STAGE) == (exit_code, report)
    # The sibling the abandoned task was blocking now runs to a landing.
    lab.halt_after_implement = False
    assert _entry(lab, SIBLING).exit_code == 0
    assert _contractor_adapter(lab).record(SIBLING).state is ContractorState.LANDED

    refused, reason = _abandon(lab, SIBLING)

    assert refused == 2
    assert "has landed" in str(reason["reason"])


@pytest.mark.acceptance
def test_abandon_refuses_a_task_whose_landing_has_already_begun(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, signing_config, sign_payload
) -> None:
    """§3.8, D17: the landing window is not a window an abandon may close.

    The crash is after the fast-forward CAS, so the work IS on the target ref
    while the record still reads admitted. Abandoning there would clean the
    worktree away, pin no export and leave the commit orphaned, so abandon is
    refused by the one fact that outlives the process — the journalled landing
    intent — and the recovery `wf contract` already performs finishes the job.
    """
    lab = _lab(tmp_path, monkeypatch, signing_config, sign_payload, STAGE)
    armed = True

    def after_cas(self: LandingHooks) -> None:
        nonlocal armed
        if armed:
            armed = False
            raise InjectedCrash("the process died after the landing CAS")

    monkeypatch.setattr(LandingHooks, "after_cas", after_cas)
    crashed = _entry(lab, STAGE)
    assert crashed.exit_code == 1
    assert "InjectedCrash" in crashed.report["diagnostic"]

    refused, report = _abandon(lab, STAGE)

    assert refused == 2
    assert "landing" in str(report["reason"])
    assert _contractor_adapter(lab).record(STAGE).state is ContractorState.ADMITTED
    # What the task actually owes: the recovery the refusal named.
    assert _entry(lab, STAGE).exit_code == 0
    assert _contractor_adapter(lab).record(STAGE).state is ContractorState.LANDED
    assert closed(lab.ledger, lab.git, STAGE) is True


@pytest.mark.acceptance
def test_a_retry_admits_from_the_snapshot_without_reading_the_tracker(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, signing_config, sign_payload
) -> None:
    """§3.3, R4: the brief belongs to the task, so a retry owes no tracker read.

    The retry PREDICATE is stubbed out — `test_foreman_main` owns it — because
    what is under test is the admission it guards: attempt two is prepared and
    admitted from the snapshot the first prepare wrote, so no bd command over
    the whole retry reads anything the record already holds.

    The one command left is §3.4's claim, and it is a READ: the claim is a
    desired state, the bead is already held by this actor, so the adapter
    writes nothing. That is what makes re-admission cheap on bd now that bd
    declares `CLAIM`.
    """
    lab = _lab(tmp_path, monkeypatch, signing_config, sign_payload, STAGE)
    first = _admit_only(lab, STAGE)
    monkeypatch.setattr(command_module, "retry_refusal", lambda *_: None)
    served = len(lab.fake_bd.calls)

    retried = _admit_only(lab, STAGE, "--retry")

    assert [name for name, _ in lab.fake_bd.calls[served:]] == ["show"]
    assert (retried.attempt, retried.state) == (2, ContractorState.ADMITTED)
    assert retried.previous_attempts == (first.instance_key,)
    held = lab.records.read(STAGE)
    assert held is not None and held.brief == STAGE_BRIEF


@pytest.mark.acceptance
def test_prepare_mints_the_task_from_the_ref_its_tracker_knows_it_by(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, signing_config, sign_payload
) -> None:
    """§3.7, R8: prepare is the one moment both the ref and the epic are known.

    Nothing else writes the pair, so the row IS the evidence the mint ran. A
    bd id already satisfies the grammar, which is why nothing moves: the task
    the engine spends on refs, worktrees and paths is the id on the bead.
    """
    lab = _lab(tmp_path, monkeypatch, signing_config, sign_payload, STAGE)

    _prepare_only(lab, STAGE)

    row = lab.ledger.connection.execute(
        "SELECT task_id, epic_id, tracker_ref, tracker_kind FROM tasks "
        "WHERE task_id = ?",
        (STAGE,),
    ).fetchone()
    assert tuple(row) == (STAGE, EPIC, STAGE, TrackerKind.BD.value)
