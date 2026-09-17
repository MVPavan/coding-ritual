"""S3 cutover: the store switch, the locator, and what a close now owes.

The premise every test here shares is that a run must work IDENTICALLY on both
backends and that which backend it is on is decided once, before the root
exists, and never again (run-ledger §3.2, D18). So the end-to-end drill is
parameterised by the switch rather than duplicated, and the rest are the
refusals that make "never again" true.
"""

from __future__ import annotations

import sys
from dataclasses import replace
from pathlib import Path
from typing import Final

import pytest

from tests._foreman import LAB_TASK, ForemanLab
from tests._supervisor import ChildScript
from tests.test_foreman_main import _bridge_adapter, _bridge_stage
from tests.test_phase_bridge_cli import _entry
from workflow_interpreter.bdio.constants import BackendKind
from workflow_interpreter.bdio.errors import StoreConfigError
from workflow_interpreter.bridge import PhaseAdapter, PhaseAdapterError
from workflow_interpreter.bridge.journal import EXPORT_REF_TEMPLATE, LandingPhase
from workflow_interpreter.bridge.landing import (
    LANDING_INTENT_FILE,
    LANDING_RECEIPT_FILE,
    LandingIntent,
    LandingReceipt,
)
from workflow_interpreter.bridge.models import PhaseBridgeRecord
from workflow_interpreter.bridge.verification import CheckCommand
from workflow_interpreter.foreman import __main__ as main_module
from workflow_interpreter.foreman.locator import RootBackendLocator
from workflow_interpreter.foreman.tick import Foreman, RunReport
from workflow_interpreter.ledger.paths import export_path
from workflow_interpreter.ledger.tasks import export_oid, task_backend
from workflow_interpreter.schema.models import Outcome

STAGE: Final[str] = "a"
PROOF_SCRIPT: Final[str] = (
    "from pathlib import Path; assert Path('src/feature.py').is_file()"
)
"""The bridge check the landing runs in its detached verify tree."""
LEDGER_ROOT_PREFIX: Final[str] = f"{LAB_TASK}-a"
"""D8: a ledger root is `<task>-a<n>`, so the id itself names its backend."""


def _bridge_lab(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    signing_config: object,
    sign_payload: object,
    store: BackendKind,
) -> ForemanLab:
    """A lab wired to run one bridge stage end to end on `store`."""
    lab = ForemanLab(tmp_path, signing=signing_config, signer=sign_payload, store=store)
    config = lab.config.model_copy(
        update={
            "bridge_checks": (
                CheckCommand(
                    name="source-proof",
                    argv=(
                        sys.executable,
                        "-c",
                        PROOF_SCRIPT,
                    ),
                ),
            )
        }
    )
    lab.composition = replace(lab.composition, config=config)
    lab.fake_bd.rows[STAGE] = _bridge_stage(STAGE, description="the only stage")
    monkeypatch.setattr(main_module, "_composition", lambda _: lab.composition)
    monkeypatch.setattr(
        PhaseAdapter, "from_config", classmethod(lambda *_: _bridge_adapter(lab))
    )

    def drive(self, root_id, *, poll_s, max_wall_s, monitored=False):
        """Run the graph to its terminal through the REAL tick loop."""
        lab.root = lab.store.reads.load_root(root_id)
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
        assert self.tick(root_id).settled
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

    monkeypatch.setattr(Foreman, "run", drive)
    return lab


@pytest.mark.acceptance
@pytest.mark.parametrize("store", (BackendKind.BD, BackendKind.LEDGER))
def test_a_stage_lands_end_to_end_on_each_switch_value(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    signing_config,
    sign_payload,
    store: BackendKind,
) -> None:
    """S3's headline: prepare, admit, run, sign, land, close — on either store.

    Every assertion below is backend-agnostic except the root id, which is
    exactly the point of D8: the ledger mints `<task>-a<n>` and bd keeps its
    own minted id, and nothing else in the run can tell the difference.
    """
    lab = _bridge_lab(tmp_path, monkeypatch, signing_config, sign_payload, store)

    result = _entry(lab, STAGE)

    assert result.exit_code == 0, result.report
    record = _bridge_adapter(lab).record(STAGE)
    assert record.root_backend is store
    assert lab.fake_bd.rows[STAGE]["status"] == "closed"
    assert (record.root_id or "").startswith(LEDGER_ROOT_PREFIX) is (
        store is BackendKind.LEDGER
    )
    # §3.6: the record is in git, and the bead names the blob it is in.
    assert record.export_oid is not None
    assert export_path(lab.repo, STAGE).is_file()
    assert (
        lab.git.ref_target(EXPORT_REF_TEMPLATE.format(task_id=STAGE), cwd=lab.repo)
        == record.export_oid
    )
    assert export_oid(lab.ledger, STAGE) == record.export_oid
    # D17: the landing is journalled, both halves, under the stage's task.
    assert (
        lab.ledger.connection.execute(
            "SELECT COUNT(*) FROM landings WHERE task_id = ?", (STAGE,)
        ).fetchone()[0]
        == 2
    )


@pytest.mark.acceptance
def test_a_ledger_root_resumes_after_the_switch_goes_back_to_bd(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, signing_config, sign_payload
) -> None:
    """D18: the switch is for NEW roots; an old one keeps the pin it was made with.

    The whole reason the backend is recorded rather than read from config: a
    root created under `store = "ledger"` has to stay loadable after an
    operator flips the switch back, and "loadable" means the store is chosen
    from the pin before the root is read.
    """
    lab = _bridge_lab(
        tmp_path, monkeypatch, signing_config, sign_payload, BackendKind.LEDGER
    )
    lab.fake_bd.rows[STAGE]["metadata"] = {}
    admitted = _admit_only(lab)
    assert admitted.root_backend is BackendKind.LEDGER

    # The operator flips the switch back. Nothing about the live root moves.
    lab.composition = replace(
        lab.composition,
        config=lab.composition.config.model_copy(update={"store": BackendKind.BD}),
    )
    locator = RootBackendLocator(LAB_TASK, ledger=lab.ledger)

    assert locator(admitted.root_id or "") is BackendKind.LEDGER
    resumed = _entry(lab, STAGE)
    assert resumed.exit_code == 0, resumed.report
    assert _bridge_adapter(lab).record(STAGE).root_id == admitted.root_id


def _admit_only(lab: ForemanLab) -> PhaseBridgeRecord:
    """Admit the stage without running it, by refusing to drive the root."""
    from workflow_interpreter.bridge import command as command_module

    driven: list[str] = []

    def refuse(composition, adapter, record, *, monitored=False):
        driven.append(record.stage_id)
        raise AssertionError("the stage must not run yet")

    original = command_module._run_record
    command_module._run_record = refuse
    try:
        _entry(lab, STAGE)
    except AssertionError:
        pass
    finally:
        command_module._run_record = original
    assert driven == [STAGE]
    return _bridge_adapter(lab).record(STAGE)


def test_the_locator_refuses_a_root_nothing_pinned(tmp_path: Path) -> None:
    """§3.2: no bridge record, no ledger row — a named refusal, never a guess.

    Falling back to bd would be worse than failing: a ledger-backed root read
    through bd reports as MISSING, and a missing root is how the engine
    decides a run never happened.
    """
    with pytest.raises(StoreConfigError, match="no backend is pinned"):
        RootBackendLocator("cr-unknown.9")("cr-unknown.9-a1")


def test_a_ledger_task_row_locates_every_root_of_a_run_with_no_bridge(
    tmp_path: Path,
) -> None:
    """D16: `--task` is required so that the `tasks` row can be the locator."""
    lab = ForemanLab(tmp_path, store=BackendKind.LEDGER)
    locator = RootBackendLocator(LAB_TASK, ledger=lab.ledger)

    assert task_backend(lab.ledger, LAB_TASK) is BackendKind.LEDGER
    # A root that does not exist yet still resolves, because the TASK is pinned.
    assert locator(f"{LAB_TASK}-a7") is BackendKind.LEDGER


def test_re_preparing_one_attempt_cannot_move_its_backend(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, signing_config, sign_payload
) -> None:
    """§3.2: the pin is immutable for the attempt, because its root may exist."""
    lab = _bridge_lab(
        tmp_path, monkeypatch, signing_config, sign_payload, BackendKind.LEDGER
    )
    adapter = _bridge_adapter(lab)
    prepared = PhaseBridgeRecord.prepared(
        epic_id="phase",
        stage_id=STAGE,
        attempt=1,
        target_ref="refs/heads/main",
        expected_base_commit=lab.head,
        root_backend=BackendKind.LEDGER,
    )
    adapter.prepare(STAGE, prepared)

    with pytest.raises(PhaseAdapterError, match="root_backend is pinned at prepare"):
        adapter.prepare(
            STAGE, prepared.model_copy(update={"root_backend": BackendKind.BD})
        )


def test_a_close_is_refused_when_the_export_cannot_be_pinned(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, signing_config, sign_payload
) -> None:
    """§3.6: no pinned export, no CLOSED — the bead never closes on a lost record.

    The pin is broken the only way it can be broken without lying about
    anything else: the ref write lands nowhere, so the read-back disagrees
    with the blob that was just written.
    """
    from workflow_interpreter.supervisor.gitio import Git

    lab = _bridge_lab(
        tmp_path, monkeypatch, signing_config, sign_payload, BackendKind.LEDGER
    )
    real_update_ref = Git.update_ref

    def swallow_export_ref(self, ref: str, commit: str, *, cwd: Path) -> None:
        """Lose only the export pin; every other ref this run writes must land."""
        if not ref.startswith("refs/wf/exports/"):
            real_update_ref(self, ref, commit, cwd=cwd)

    monkeypatch.setattr(Git, "update_ref", swallow_export_ref)

    result = _entry(lab, STAGE)

    assert result.exit_code == 2, result.report
    assert "could not be pinned" in str(result.report["reason"])
    assert lab.fake_bd.rows[STAGE]["status"] != "closed"
    assert _bridge_adapter(lab).record(STAGE).export_oid is None


@pytest.mark.parametrize("phase", (LandingPhase.INTENT, LandingPhase.RECEIPT))
def test_landing_recovery_falls_back_to_the_journalled_row(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    signing_config,
    sign_payload,
    phase: LandingPhase,
) -> None:
    """D17: a deleted wrapper file leaves the row, and the row is enough.

    The file is what recovery prefers, so proving the fallback means taking
    the file away — which is exactly the failure the row exists for.
    """
    lab = _bridge_lab(
        tmp_path, monkeypatch, signing_config, sign_payload, BackendKind.LEDGER
    )
    assert _entry(lab, STAGE).exit_code == 0
    record = _bridge_adapter(lab).record(STAGE)
    instance = lab.composition.for_root(record.root_id or "").paths.instance_dir
    name = LANDING_INTENT_FILE if phase is LandingPhase.INTENT else LANDING_RECEIPT_FILE
    model = LandingIntent if phase is LandingPhase.INTENT else LandingReceipt
    (instance / name).unlink()

    from workflow_interpreter.bridge.journal import LandingJournal

    journal = LandingJournal(lab.ledger, STAGE, BackendKind.LEDGER)
    assert journal.read(record.attempt, phase, model) is not None
    # Recovery of the already-closed stage still validates, from the row.
    assert _entry(lab, STAGE).exit_code == 0


def test_a_bd_root_and_a_ledger_root_contend_on_one_bd_claim(
    tmp_path: Path,
) -> None:
    """D20: claims stay in bd, so the two backends see each other's reservation.

    The whole risk the decision names: if a ledger-backed run kept its claims
    in the ledger, two attempts aiming at one integration target would each
    find an EMPTY claim set and both believe they had reserved it. So the
    ledger-backed store is built with the bd transport injected as its claims
    backend, and what is asserted is that the reservation one wrote is the
    reservation the other reads — on the same row, not a copy of it.
    """
    from tests._fake_bd import FakeBd
    from tests._ledger import ledger_store, repository
    from workflow_interpreter.bdio import BdConfig, WorkflowStore
    from workflow_interpreter.bdio.backend import PinnedBackendFactory
    from workflow_interpreter.bdio.client import BdClient
    from workflow_interpreter.ledger.database import open_ledger

    target = "refs/heads/main"
    repo_root, wrapper_root = repository(tmp_path)
    bd = BdClient(
        BdConfig(workspace=tmp_path / "bd", actor="test"), FakeBd(str(tmp_path / "bd"))
    )
    on_bd = WorkflowStore(bd, backend_factory=PinnedBackendFactory(bd))
    with open_ledger(repo_root, wrapper_root, path=tmp_path / "ledger.db") as database:
        on_ledger = ledger_store(database, claims_backend=bd)

        on_bd.claims.write(target, {"owner": "attempt-one"})

        held = on_ledger.claims.find(target)
        assert [claim.payload["owner"] for claim in held] == ["attempt-one"]
        # And the second run's write lands on the SAME row rather than a rival.
        on_ledger.claims.write(target, {"owner": "attempt-two"}, held[0].id)
        assert [claim.payload["owner"] for claim in on_bd.claims.find(target)] == [
            "attempt-two"
        ]


@pytest.mark.acceptance
@pytest.mark.parametrize(
    ("first", "second"),
    ((BackendKind.BD, BackendKind.LEDGER), (BackendKind.LEDGER, BackendKind.BD)),
)
def test_a_retry_creates_its_root_on_the_backend_its_record_names(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    signing_config,
    sign_payload,
    first: BackendKind,
    second: BackendKind,
) -> None:
    """D18: the switch applies to a NEW attempt root — and to its creation too.

    A retry admitted after the switch flipped prepares a record pinned to the
    new backend, so the root that record names has to be CREATED there. Created
    through the process-wide store instead, it would land on whichever
    transport this process started on and contradict its own record — and for a
    bd root of a ledger-pinned task nothing durable would ever say so, because
    the ledger holds no row for it and the `tasks` row still names attempt one.
    """
    lab = _bridge_lab(tmp_path, monkeypatch, signing_config, sign_payload, first)
    adapter = _bridge_adapter(lab)
    admitted = _admit_only(lab)
    assert admitted.root_backend is first

    # The operator flips the switch, and the next attempt is prepared on it.
    flipped = lab.composition.config.model_copy(update={"store": second})
    lab.composition = replace(lab.composition, config=flipped)
    retried = _admit_successor(lab, adapter, admitted.next_attempt(second))

    assert retried.root_backend is second
    assert retried.root_id != admitted.root_id
    locator = lab.composition.locate_backend
    # The new root is on the backend its record names…
    assert locator(retried.root_id or "") is second
    assert (
        lab.composition.store_for_root(retried.root_id or "")
        .reads.load_root(retried.root_id or "")
        .root_id
        == retried.root_id
    )
    # …and the first attempt still resolves through its own, unmoved pin.
    assert locator(admitted.root_id or "") is first
    assert (
        lab.composition.store_for_root(admitted.root_id or "")
        .reads.load_root(admitted.root_id or "")
        .root_id
        == admitted.root_id
    )


def _admit_successor(
    lab: ForemanLab, adapter: PhaseAdapter, successor: PhaseBridgeRecord
) -> PhaseBridgeRecord:
    """Admit one declared successor through the production admission path."""
    from workflow_interpreter.bridge.admission import (
        PhaseAdmission,
        WorkflowRootProvisioner,
    )
    from workflow_interpreter.foreman.resolve import instantiate

    brief = lab.repo.parent / "successor-brief.md"
    brief.write_text("the only stage", encoding="utf-8")
    roots = WorkflowRootProvisioner(
        adapter,
        lambda instance_key, backend: instantiate(
            lab.composition,
            lab.config.bridge_graph,
            instance_key=instance_key,
            instance_inputs={"task_brief": brief},
            allow_test_flags=False,
            overrides={},
            backend=backend,
        ),
        lab.git,
        lab.repo,
    )
    return PhaseAdmission(
        adapter,
        roots,
        lambda: lab.git.head_commit(cwd=lab.repo),
        verification_policy=successor.verification_policy,
        root_backend=lab.composition.config.store,
    ).admit_successor(
        successor.epic_id,
        successor.stage_id,
        successor.target_ref,
        successor.expected_base_commit,
        successor,
    )
