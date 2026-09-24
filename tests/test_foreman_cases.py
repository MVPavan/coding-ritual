"""C2b lifecycle case contracts using the shared real-collaborator lab."""

import subprocess
from dataclasses import replace
from pathlib import Path
from typing import cast
from unittest.mock import Mock

import pytest

from tests._bdio import handle
from tests._foreman import (
    DEFAULT_LAB_ROLES,
    FAKE_PROFILE,
    ForemanLab,
    entry_request,
    lab_catalog,
)
from tests._helpers import VALID_FIXTURE
from tests._inspector import SESSION_ID, ChildScript
from workflow_interpreter.bdio import (
    ArtifactIdentity,
    CarrierIntegrityError,
    Evidence,
    ExitRecord,
    Lifecycle,
)
from workflow_interpreter.bdio.wire import (
    activation_binding_digest,
    mint_request_from_activation,
)
from workflow_interpreter.contracts.execution import CrewName
from workflow_interpreter.contracts.sessions import SessionFreshReason, SessionMode
from workflow_interpreter.foreman import cases as cases_module
from workflow_interpreter.foreman.cases import (
    advance_lifecycle,
    mint_entry,
    route_head,
    startup_invocation,
)
from workflow_interpreter.foreman.compose import WrapperLaunch
from workflow_interpreter.foreman.config import CrewBinding
from workflow_interpreter.foreman.constants import DISPATCH_REQUEST
from workflow_interpreter.foreman.model_catalog import (
    CatalogModel,
    CatalogProvenance,
    CatalogSnapshot,
    FamilySnapshot,
    VerificationStatus,
)
from workflow_interpreter.inspector import Recovery
from workflow_interpreter.inspector.band import BandLock
from workflow_interpreter.inspector.models import CompletionEvidence, RecoveryCase
from workflow_interpreter.inspector.paths import read_record
from workflow_interpreter.schema.models import Outcome


def _bd_writes(lab: ForemanLab) -> int:
    """Count every durable bd mutation, excluding reads and process-local files."""
    return sum(lab.count(command) for command in ("create", "update", "close"))


_LEGACY_S3_PINS: dict[str, None] = {
    "binding_digest": None,
    "role": None,
    "family": None,
    "effort": None,
    "context_cap_tokens": None,
    "execution_policy": None,
    "policy_digest": None,
    "catalog_digest": None,
    "crew_version": None,
}


def test_empty_lifecycle_mints_and_runs_one_real_wrapper(tmp_path: Path) -> None:
    """Entry mint reaches the wrapper's dispatch and exit-recorded lifecycle."""
    lab = ForemanLab(tmp_path)
    root = lab.instantiate()
    before = _bd_writes(lab)

    report = mint_entry(lab.composition, lab.wiring(), root)

    activation = lab.store.reads.list_activations(root.root_id)[0]
    assert report.dispatched == activation.activation_id
    assert activation.metadata.lifecycle is Lifecycle.EXIT_RECORDED
    assert _bd_writes(lab) - before == 5  # includes the immutable envelope record
    assert [launch.activation_id for launch in lab.spawner.launches] == [
        activation.activation_id
    ]


def _live_role_lab(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, *, toml: Path = VALID_FIXTURE
) -> tuple[ForemanLab, Path]:
    """Wire real foreman mints to a local catalog and an inert launch boundary."""
    lab = ForemanLab(tmp_path, toml=toml)
    role_path = tmp_path / "roles.toml"
    role_path.write_text(
        '[roles.implementer]\nmodel = "model-a"\neffort = "medium"\n',
        encoding="utf-8",
    )
    snapshot = CatalogSnapshot(
        generated_at="2026-09-23T00:00:00Z",
        digest="test",
        families={
            CrewName.CODEX: FamilySnapshot(
                source="bundled-cli",
                available=True,
                models=(
                    CatalogModel(
                        id="model-a", efforts=("medium",), context_window=200000
                    ),
                    CatalogModel(
                        id="model-b", efforts=("medium",), context_window=200000
                    ),
                ),
            )
        },
    )
    lab.profiles.accepted = lab.profiles.accepted | {"codex"}
    lab.config = lab.config.model_copy(update={"role_bindings_path": role_path})
    lab.composition = replace(
        lab.composition,
        config=lab.config,
        catalog=snapshot,
        catalog_provenance=CatalogProvenance.REFRESHED,
    )
    monkeypatch.setattr(lab.spawner, "launch", lambda *_args, **_kwargs: None)
    return lab, role_path


def test_foreman_replays_entry_before_reading_malformed_live_roles(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A duplicate key keeps its pin even if the operator file is broken."""
    lab, role_path = _live_role_lab(tmp_path, monkeypatch)
    root = lab.instantiate()
    first = mint_entry(lab.composition, lab.wiring(), root)
    assert first.dispatched is not None
    role_path.write_text("[roles.implementer\n", encoding="utf-8")

    replay = mint_entry(lab.composition, lab.wiring(), root)

    assert replay.dispatched == first.dispatched
    assert len(lab.store.reads.list_activations(root.root_id)) == 1


def test_foreman_replays_retry_before_reading_malformed_live_roles(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A routed duplicate keeps the first retry pin after a broken edit."""
    lab, role_path = _live_role_lab(tmp_path, monkeypatch)
    root = lab.instantiate()
    first = mint_entry(lab.composition, lab.wiring(), root)
    assert first.dispatched is not None
    dispatched = lab.store.record_dispatch(first.dispatched, handle())
    closed = lab.store.close_activation(
        dispatched.activation_id, Outcome.ERROR_TRANSPORT
    )
    retry = route_head(lab.composition, lab.wiring(), root, closed)
    assert retry.dispatched is not None
    role_path.write_text("[roles.implementer\n", encoding="utf-8")

    replay = route_head(lab.composition, lab.wiring(), root, closed)

    assert replay.dispatched == retry.dispatched
    assert len(lab.store.reads.list_activations(root.root_id)) == 2


def test_foreman_replays_edge_before_reading_malformed_live_roles(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A completed head's already minted edge is independent of later edits."""
    lab, role_path = _live_role_lab(tmp_path, monkeypatch)
    role_path.write_text(
        '[roles.implementer]\nmodel = "model-a"\neffort = "medium"\n'
        '[roles.critic]\nmodel = "model-b"\neffort = "medium"\n',
        encoding="utf-8",
    )
    root = lab.instantiate()
    first = mint_entry(lab.composition, lab.wiring(), root)
    assert first.dispatched is not None
    dispatched = lab.store.record_dispatch(first.dispatched, handle())
    commit = lab.git.head_commit(cwd=lab.repo)
    closed = lab.store.close_activation(
        dispatched.activation_id,
        Outcome.DONE,
        evidence=Evidence(
            artifact=ArtifactIdentity(
                commit_oid=commit, tree_oid=lab.git.tree_oid(commit, cwd=lab.repo)
            )
        ),
    )
    edge = route_head(lab.composition, lab.wiring(), root, closed)
    assert edge.dispatched is not None
    role_path.write_text("[roles.critic\n", encoding="utf-8")

    replay = route_head(lab.composition, lab.wiring(), root, closed)

    assert replay.dispatched == edge.dispatched
    assert len(lab.store.reads.list_activations(root.root_id)) == 2


@pytest.mark.parametrize(
    ("apply", "expected"),
    [("next-task", "model-a"), ("now", "model-b")],
)
def test_live_role_edit_applies_at_selected_mint(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, apply: str, expected: str
) -> None:
    """A retry pins either the task's binding or the current edit."""
    lab, role_path = _live_role_lab(tmp_path, monkeypatch)
    root = lab.instantiate()
    first = mint_entry(lab.composition, lab.wiring(), root)
    assert first.dispatched is not None
    dispatched = lab.store.record_dispatch(first.dispatched, handle())
    closed = lab.store.close_activation(
        dispatched.activation_id, Outcome.ERROR_TRANSPORT
    )
    role_path.write_text(
        '[roles.implementer]\nmodel = "model-b"\neffort = "medium"\n'
        f'apply = "{apply}"\n',
        encoding="utf-8",
    )
    assert startup_invocation(lab.composition, root, "implement").model == "model-b"

    result = route_head(lab.composition, lab.wiring(), root, closed)

    assert result.dispatched is not None
    metadata = lab.store.reads.load_activation(result.dispatched).metadata
    assert metadata.model == expected
    assert metadata.session_fresh_reason is (
        SessionFreshReason.MODEL_CHANGED
        if apply == "now"
        else SessionFreshReason.NO_SOURCE
    )
    if apply == "next-task":
        assert metadata.binding_digest == closed.metadata.binding_digest


def test_apply_now_mode_only_edit_keeps_current_task_pin(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    lab, role_path = _live_role_lab(tmp_path, monkeypatch)
    role_path.write_text(
        '[roles.implementer]\nmodel = "model-a"\neffort = "medium"\n'
        'session_mode = "fresh"\n',
        encoding="utf-8",
    )
    root = lab.instantiate()
    first = mint_entry(lab.composition, lab.wiring(), root)
    assert first.dispatched is not None
    dispatched = lab.store.record_dispatch(first.dispatched, handle())
    closed = lab.store.close_activation(
        dispatched.activation_id, Outcome.ERROR_TRANSPORT
    )
    role_path.write_text(
        '[roles.implementer]\nmodel = "model-a"\neffort = "medium"\napply = "now"\n',
        encoding="utf-8",
    )

    result = route_head(lab.composition, lab.wiring(), root, closed)

    assert result.dispatched is not None
    retried = lab.store.reads.load_activation(result.dispatched).metadata
    assert retried.session_mode is SessionMode.FRESH
    assert retried.session_fresh_reason is None
    assert retried.binding_digest == closed.metadata.binding_digest


def test_apply_now_does_not_copy_another_nodes_mode_to_new_mint(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    graph = tmp_path / "shared-role.toml"
    graph.write_text(
        VALID_FIXTURE.read_text()
        .replace(
            'crew        = "profile:critic"', 'crew        = "profile:implementer"'
        )
        .replace(
            'name          = "implement"',
            'name          = "implement"\nsession_mode = "fresh"',
        ),
        encoding="utf-8",
    )
    lab, role_path = _live_role_lab(tmp_path, monkeypatch, toml=graph)
    role_path.write_text(
        '[roles.implementer]\nmodel = "model-a"\neffort = "medium"\napply = "now"\n',
        encoding="utf-8",
    )
    root = lab.instantiate()
    first = mint_entry(lab.composition, lab.wiring(), root)
    assert first.dispatched is not None
    dispatched = lab.store.record_dispatch(first.dispatched, handle())
    commit = lab.git.head_commit(cwd=lab.repo)
    closed = lab.store.close_activation(
        dispatched.activation_id,
        Outcome.DONE,
        evidence=Evidence(
            artifact=ArtifactIdentity(
                commit_oid=commit, tree_oid=lab.git.tree_oid(commit, cwd=lab.repo)
            )
        ),
    )
    edge = route_head(lab.composition, lab.wiring(), root, closed)
    assert edge.dispatched is not None
    minted = lab.store.reads.load_activation(edge.dispatched).metadata
    assert minted.node == "review"
    assert minted.session_mode is SessionMode.RESUME


def test_next_task_edit_keeps_role_pin_on_edge_round(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A later graph edge in the same root retains the role's first pin."""
    lab, role_path = _live_role_lab(tmp_path, monkeypatch)
    role_path.write_text(
        '[roles.implementer]\nmodel = "model-a"\neffort = "medium"\n'
        '[roles.critic]\nmodel = "model-b"\neffort = "medium"\n',
        encoding="utf-8",
    )
    root = lab.instantiate()
    first = mint_entry(lab.composition, lab.wiring(), root)
    assert first.dispatched is not None
    implemented = lab.store.record_dispatch(first.dispatched, handle())
    commit = lab.git.head_commit(cwd=lab.repo)
    implemented = lab.store.close_activation(
        implemented.activation_id,
        Outcome.DONE,
        evidence=Evidence(
            artifact=ArtifactIdentity(
                commit_oid=commit, tree_oid=lab.git.tree_oid(commit, cwd=lab.repo)
            )
        ),
    )
    review = route_head(lab.composition, lab.wiring(), root, implemented)
    assert review.dispatched is not None
    reviewed = lab.store.record_dispatch(review.dispatched, handle())
    reviewed = lab.store.close_activation(
        reviewed.activation_id,
        Outcome.REJECT,
        evidence=Evidence(
            outputs_ref="wf-output://review",
            outputs_tree_oid=lab.git.tree_oid(commit, cwd=lab.repo),
            artifact=ArtifactIdentity(
                commit_oid=commit, tree_oid=lab.git.tree_oid(commit, cwd=lab.repo)
            ),
        ),
    )
    role_path.write_text(
        '[roles.implementer]\nmodel = "model-b"\neffort = "medium"\n'
        '[roles.critic]\nmodel = "model-b"\neffort = "medium"\n',
        encoding="utf-8",
    )

    second = route_head(lab.composition, lab.wiring(), root, reviewed)

    assert second.dispatched is not None
    metadata = lab.store.reads.load_activation(second.dispatched).metadata
    assert metadata.round_no == 2
    assert metadata.model == "model-a"


def test_malformed_live_roles_keep_pin_on_new_retry(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An existing task can retry without parsing a broken operator edit."""
    lab, role_path = _live_role_lab(tmp_path, monkeypatch)
    root = lab.instantiate()
    first = mint_entry(lab.composition, lab.wiring(), root)
    assert first.dispatched is not None
    dispatched = lab.store.record_dispatch(first.dispatched, handle())
    closed = lab.store.close_activation(
        dispatched.activation_id, Outcome.ERROR_TRANSPORT
    )
    role_path.write_text("[roles.implementer\n", encoding="utf-8")

    retry = route_head(lab.composition, lab.wiring(), root, closed)

    assert retry.dispatched is not None
    assert lab.store.reads.load_activation(retry.dispatched).metadata.model == "model-a"


def test_invalid_now_edit_warns_once_and_keeps_pin(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A bad immediate edit names the refused model while retaining this task's pin."""
    lab, role_path = _live_role_lab(tmp_path, monkeypatch)
    root = lab.instantiate()
    first = mint_entry(lab.composition, lab.wiring(), root)
    assert first.dispatched is not None
    dispatched = lab.store.record_dispatch(first.dispatched, handle())
    closed = lab.store.close_activation(
        dispatched.activation_id, Outcome.ERROR_TRANSPORT
    )
    role_path.write_text(
        '[roles.implementer]\nmodel = "no-such-model"\neffort = "medium"\n'
        'apply = "now"\n',
        encoding="utf-8",
    )
    logger = Mock()
    monkeypatch.setattr(cases_module, "_LOG", logger)

    retry = route_head(lab.composition, lab.wiring(), root, closed)

    assert retry.dispatched is not None
    assert lab.store.reads.load_activation(retry.dispatched).metadata.model == "model-a"
    logger.warning.assert_called_once()
    (event,) = logger.warning.call_args.args
    assert event == cases_module.MSG_ROLE_EDIT_IGNORED
    assert logger.warning.call_args.kwargs["role"] == "implementer"
    assert "no-such-model" in logger.warning.call_args.kwargs["reason"]


def test_new_claude_binding_is_probed_outside_the_band(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A seed-only selection gets paid admission before the durable mint."""
    lab, role_path = _live_role_lab(tmp_path, monkeypatch)
    role_path.write_text(
        '[roles.implementer]\nmodel = "claude-a"\neffort = "medium"\n',
        encoding="utf-8",
    )
    catalog = CatalogSnapshot(
        generated_at="2026-09-23T00:00:00Z",
        digest="claude-test",
        families={
            CrewName.CLAUDE: FamilySnapshot(
                source="checked-seed-and-probe",
                available=True,
                models=(
                    CatalogModel(
                        id="claude-a",
                        efforts=("medium",),
                        context_window=500000,
                        verification=VerificationStatus.SEED_UNPROBED,
                    ),
                ),
            ),
        },
    )
    calls: list[tuple[str, ...]] = []

    def run(argv: list[str], timeout: float) -> subprocess.CompletedProcess[str]:
        band = BandLock(lab.wiring().paths.band_lock)
        band.acquire()
        band.release()
        calls.append(tuple(argv))
        return subprocess.CompletedProcess(argv, 0, '{"is_error":false}', "")

    lab.profiles.accepted = lab.profiles.accepted | {"claude"}
    lab.composition = replace(lab.composition, catalog=catalog, catalog_runner=run)
    root = lab.instantiate()

    report = lab.foreman.__class__(lab.composition).tick(root.root_id)

    assert report.dispatched is not None
    assert len(calls) == 1
    metadata = lab.store.reads.load_activation(report.dispatched).metadata
    assert metadata.model == "claude-a"
    assert lab.composition.active_catalog is not None
    assert metadata.catalog_digest == lab.composition.active_catalog.digest
    assert metadata.catalog_digest != catalog.digest


def test_minted_lifecycle_dispatches_and_records_its_exit(tmp_path: Path) -> None:
    """A real launch owns precondition, dispatch, and exit writes."""
    lab = ForemanLab(tmp_path)
    root = lab.instantiate()
    minted = (
        lab.wiring().store.mint_activation(root.root_id, entry_request()).activation
    )
    before = _bd_writes(lab)

    result = advance_lifecycle(lab.composition, lab.wiring(), root, minted)

    assert result.dispatched == minted.activation_id
    assert lab.store.reads.load_activation(minted.activation_id).metadata.lifecycle is (
        Lifecycle.EXIT_RECORDED
    )
    assert _bd_writes(lab) - before == 4  # precondition, envelope, dispatch, exit
    assert [launch.activation_id for launch in lab.spawner.launches] == [
        minted.activation_id,
    ]


def test_unlaunched_version_repin_updates_the_ledger_request(tmp_path: Path) -> None:
    """A prelaunch CLI update persists before the durable request is rebuilt."""
    lab = ForemanLab(tmp_path)
    root = lab.instantiate()
    minted = (
        lab.wiring()
        .store.mint_activation(
            root.root_id,
            entry_request(
                crew_version="codex-cli 0.156.1",
                fresh_reason_override=SessionFreshReason.MODEL_CHANGED,
            ),
        )
        .activation
    )

    updated = lab.wiring().store.repin_unlaunched_version(minted, "codex-cli 0.156.2")

    assert updated.metadata.crew_version == "codex-cli 0.156.2"
    assert updated.metadata.session_fresh_reason is SessionFreshReason.MODEL_CHANGED
    assert (
        mint_request_from_activation(updated.metadata).crew_version
        == "codex-cli 0.156.2"
    )
    assert lab.store.reads.load_activation(minted.activation_id) == updated


def test_minted_dispatch_refuses_a_corrupted_activation_binding(
    tmp_path: Path,
) -> None:
    """A mutated model cannot become the vendor task of a minted row."""
    lab = ForemanLab(tmp_path)
    root = lab.instantiate()
    minted = (
        lab.wiring().store.mint_activation(root.root_id, entry_request()).activation
    )
    lab.backend._merge_metadata(minted.activation_id, {"model": "legacy-model"})
    activation = lab.store.reads.load_activation(minted.activation_id)

    advance_lifecycle(lab.composition, lab.wiring(), root, activation)

    closed = lab.store.reads.load_activation(minted.activation_id)
    assert closed.metadata.lifecycle is Lifecycle.CLOSED
    assert closed.metadata.outcome is Outcome.ERROR_TRANSPORT
    assert lab.profiles.profile.tasks == []


def test_durable_launch_request_carries_the_resolved_session_contract(
    tmp_path: Path,
) -> None:
    """The S1 session fields survive mint and the durable pre-spawn record."""
    lab = ForemanLab(
        tmp_path,
        roles={
            "implementer": CrewBinding(
                model="fake",
                effort="medium",
                session_mode=SessionMode.RESUME,
            ),
            "critic": CrewBinding(model="fake", effort="medium"),
            "scribe": CrewBinding(model="fake", effort="medium"),
        },
    )
    root = lab.instantiate()

    mint_entry(lab.composition, lab.wiring(), root)

    activation = lab.store.reads.list_activations(root.root_id)[0]
    launch = read_record(
        lab.wiring().paths.activation_dir(activation.activation_id) / DISPATCH_REQUEST,
        WrapperLaunch,
    )
    assert launch is not None
    values = launch.request.model_dump()
    assert {
        "session_mode",
        "session_source_activation_id",
        "source_session_id",
    } <= values.keys()
    assert launch.request.session_mode is SessionMode.RESUME
    assert launch.request.session_source_activation_id is None
    assert launch.request.source_session_id is None


def test_dispatched_lifecycle_recovers_without_a_second_bd_write(
    tmp_path: Path,
) -> None:
    """A dead dispatched activation takes recovery and does not launch again."""
    lab = ForemanLab(tmp_path)
    root = lab.instantiate()
    minted = (
        lab.wiring().store.mint_activation(root.root_id, entry_request()).activation
    )
    activation = lab.store.record_dispatch(minted.activation_id, handle())
    before = _bd_writes(lab)

    result = advance_lifecycle(lab.composition, lab.wiring(), root, activation)

    assert result.stalled is not None
    assert _bd_writes(lab) == before
    assert lab.spawner.launches == []


def test_dispatched_lifecycle_counts_the_two_writes_of_a_closing_recovery(
    tmp_path: Path,
) -> None:
    """A recovery that closes an already-recorded outcome performs update then close."""
    lab = ForemanLab(tmp_path)
    root = lab.instantiate()
    activation = (
        lab.wiring().store.mint_activation(root.root_id, entry_request()).activation
    )
    activation = lab.wiring().store.record_dispatch(activation.activation_id, handle())

    class ClosingRecovery:
        def resolve(self, *_args: object) -> object:
            closed = lab.wiring().store.close_activation(
                activation.activation_id, Outcome.ERROR_TRANSPORT
            )
            return type("Resolution", (), {"closed": closed, "halted": None})()

    wiring = replace(lab.wiring(), recovery=cast(Recovery, ClosingRecovery()))
    before = _bd_writes(lab)

    result = advance_lifecycle(lab.composition, wiring, root, activation)

    assert result.settled == activation.activation_id
    assert _bd_writes(lab) - before == 2


def test_infra_retry_waits_for_pending_barrier_abort_cleanup(tmp_path: Path) -> None:
    """A closed transport retry cannot bypass the receipt's pending kill."""
    lab = ForemanLab(tmp_path)
    root = lab.instantiate()
    minted = (
        lab.wiring().store.mint_activation(root.root_id, entry_request()).activation
    )
    dispatched = lab.wiring().store.record_dispatch(minted.activation_id, handle())
    closed = lab.wiring().store.close_activation(
        dispatched.activation_id, Outcome.ERROR_TRANSPORT
    )

    class PendingAbortRecovery:
        def classify(self, *_args: object) -> object:
            return type("Classification", (), {"case": RecoveryCase.ABORT_PENDING})()

        def resolve(self, *_args: object) -> object:
            termination = type("Termination", (), {"confirmed_dead": False})()
            return type("Resolution", (), {"termination": termination})()

    wiring = replace(lab.wiring(), recovery=cast(Recovery, PendingAbortRecovery()))

    result = route_head(lab.composition, wiring, root, closed)

    assert result.stalled == "barrier abort cleanup is still pending"
    assert len(lab.store.reads.list_activations(root.root_id)) == 1


def test_infra_retry_rebuilds_its_request_from_the_root_pin(tmp_path: Path) -> None:
    """A legacy retry request cannot trip the mint boundary guard."""
    # Explicit fresh isolates the legacy request guard from resume-source
    # integrity: this test deliberately corrupts the predecessor's binding.
    lab = ForemanLab(
        tmp_path,
        roles={
            **DEFAULT_LAB_ROLES,
            "implementer": DEFAULT_LAB_ROLES["implementer"].model_copy(
                update={"session_mode": SessionMode.FRESH}
            ),
        },
    )
    root = lab.instantiate()
    minted = (
        lab.wiring().store.mint_activation(root.root_id, entry_request()).activation
    )
    dispatched = lab.wiring().store.record_dispatch(minted.activation_id, handle())
    closed = lab.wiring().store.close_activation(
        dispatched.activation_id, Outcome.ERROR_TRANSPORT
    )
    lab.backend._merge_metadata(
        closed.activation_id, {"crew_profile": "legacy-crew", "model": "legacy-model"}
    )
    legacy = lab.store.reads.load_activation(closed.activation_id)

    result = route_head(lab.composition, lab.wiring(), root, legacy)

    assert result.dispatched is not None
    retried = lab.store.reads.load_activation(result.dispatched)
    assert retried.metadata.crew_profile == "codex"
    assert retried.metadata.model == "fake"


def test_infra_retry_with_resume_default_keeps_valid_binding_pin(
    tmp_path: Path,
) -> None:
    """A real prior pin can be scanned by the default resume retry."""
    lab = ForemanLab(tmp_path)
    root = lab.instantiate()
    first = (
        lab.wiring()
        .store.mint_activation(
            root.root_id,
            entry_request(crew_profile="codex", session_mode=SessionMode.RESUME),
        )
        .activation
    )
    dispatched = lab.store.record_dispatch(first.activation_id, handle())
    closed = lab.store.close_activation(
        dispatched.activation_id, Outcome.ERROR_TRANSPORT
    )

    result = route_head(lab.composition, lab.wiring(), root, closed)

    assert result.dispatched is not None
    retried = lab.store.reads.load_activation(result.dispatched).metadata
    assert retried.session_mode is SessionMode.RESUME
    assert retried.session_fresh_reason is SessionFreshReason.NO_SOURCE
    assert retried.model == closed.metadata.model
    assert retried.binding_digest == activation_binding_digest(retried)


def test_exit_recorded_lifecycle_records_evidence_then_closes(tmp_path: Path) -> None:
    """Settlement owns one evidence update plus the close update and close command."""
    lab = ForemanLab(tmp_path)
    root = lab.instantiate()
    activation_id = lab.tick().dispatched
    assert activation_id is not None
    activation = lab.store.reads.load_activation(activation_id)
    before = _bd_writes(lab)

    result = advance_lifecycle(lab.composition, lab.wiring(), root, activation)

    assert result.settled == activation_id
    # evidence, the §3 session tree, the close update and the close command
    assert _bd_writes(lab) - before == 4


def test_completed_pre_s3_activation_does_not_block_later_ticks(tmp_path: Path) -> None:
    """A completed root-pinned row remains usable after activation pins arrive."""
    lab = ForemanLab(tmp_path)
    lab.instantiate()
    first = lab.tick().dispatched
    assert first is not None
    lab.tick()
    closed = lab.store.reads.load_activation(first)
    assert closed.metadata.lifecycle is Lifecycle.CLOSED
    lab.backend._merge_metadata(
        first,
        _LEGACY_S3_PINS,
    )

    report = lab.tick()

    assert report.dispatched is not None
    successor = lab.store.reads.load_activation(report.dispatched)
    assert successor.metadata.node == "review"
    lab.tick()


@pytest.mark.parametrize("missing_digest", ["binding_digest", "policy_digest"])
def test_partial_activation_pin_halts_by_name(
    tmp_path: Path, missing_digest: str
) -> None:
    """A damaged S3 row cannot settle through the legacy root fallback."""
    lab = ForemanLab(tmp_path)
    lab.instantiate()
    activation_id = lab.tick().dispatched
    assert activation_id is not None
    lab.backend._merge_metadata(
        activation_id,
        {missing_digest: None, "model": "tampered-model"},
    )

    report = lab.tick()

    assert report.opened_gate is not None
    gate = lab.store.reads.load_gate(report.opened_gate)
    assert gate.metadata.halt_reason == (
        f"unusable_resolution:implement:{activation_id}"
    )
    assert lab.tick().halted


def test_exit_recorded_legacy_settlement_uses_the_root_pinned_profile(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A pre-S3 exit remains attached to its root-pinned vendor."""
    lab = ForemanLab(
        tmp_path,
        overrides={
            "node.implement.crew": FAKE_PROFILE,
            "node.implement.model": "fake",
            "node.implement.effort": "medium",
            "node.implement.session_mode": "fresh",
        },
    )
    root = lab.instantiate()
    minted = (
        lab.wiring().store.mint_activation(root.root_id, entry_request()).activation
    )
    dispatched = lab.wiring().store.record_dispatch(minted.activation_id, handle())
    activation = lab.wiring().store.record_exit(
        dispatched.activation_id,
        ExitRecord(exit_code=0, ended_at="2026-09-08T00:00:00Z", reason="ok"),
    )
    lab.backend._merge_metadata(
        activation.activation_id,
        {"crew_profile": "legacy-crew", **_LEGACY_S3_PINS},
    )
    activation = lab.store.reads.load_activation(activation.activation_id)
    profiles: list[str] = []

    monkeypatch.setattr(
        lab.composition.profiles,
        "profile_for",
        lambda name: profiles.append(name) or lab.profiles.profile,
    )
    monkeypatch.setattr(
        cases_module,
        "settle",
        lambda *_args: type(
            "Settlement",
            (),
            {"activation": activation, "stalled": None},
        )(),
    )

    advance_lifecycle(lab.composition, lab.wiring(), root, activation)

    assert profiles == [FAKE_PROFILE]


def test_dispatched_legacy_settlement_uses_the_root_pinned_profile(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A pre-S3 dispatched row recovers with the root-pinned vendor."""
    lab = ForemanLab(
        tmp_path,
        overrides={
            "node.implement.crew": FAKE_PROFILE,
            "node.implement.model": "fake",
            "node.implement.effort": "medium",
            "node.implement.session_mode": "fresh",
        },
    )
    root = lab.instantiate()
    minted = (
        lab.wiring().store.mint_activation(root.root_id, entry_request()).activation
    )
    activation = lab.wiring().store.record_dispatch(minted.activation_id, handle())
    lab.backend._merge_metadata(
        activation.activation_id,
        {"crew_profile": "legacy-crew", **_LEGACY_S3_PINS},
    )
    activation = lab.store.reads.load_activation(activation.activation_id)
    profiles: list[str] = []

    class ExitRecordedRecovery:
        def resolve(self, *_args: object) -> object:
            return type(
                "Resolution",
                (),
                {
                    "classification": type(
                        "Classification",
                        (),
                        {
                            "exit_record": ExitRecord(
                                exit_code=0,
                                ended_at="2026-09-08T00:00:00Z",
                                reason="ok",
                            )
                        },
                    )(),
                    "closed": None,
                    "halted": None,
                },
            )()

    wiring = replace(lab.wiring(), recovery=cast(Recovery, ExitRecordedRecovery()))
    monkeypatch.setattr(
        lab.composition.profiles,
        "profile_for",
        lambda name: profiles.append(name) or lab.profiles.profile,
    )
    monkeypatch.setattr(
        cases_module,
        "settle",
        lambda *_args: type(
            "Settlement",
            (),
            {"activation": activation, "stalled": None},
        )(),
    )

    advance_lifecycle(lab.composition, wiring, root, activation)

    assert profiles == [FAKE_PROFILE]


def test_evidence_recorded_lifecycle_closes_from_the_saved_completion(
    tmp_path: Path,
) -> None:
    """A replay-free close writes its outcome and then finishes the bead."""
    lab = ForemanLab(tmp_path)
    root = lab.instantiate()
    activation_id = lab.tick().dispatched
    assert activation_id is not None
    completion = read_record(
        lab.wiring().paths.completion(activation_id), CompletionEvidence
    )
    assert completion is not None
    activation = lab.store.record_evidence(activation_id, completion.evidence)
    before = _bd_writes(lab)

    result = advance_lifecycle(lab.composition, lab.wiring(), root, activation)

    assert result.settled == activation_id
    # the §3 session tree, then the close — the evidence is already recorded
    assert _bd_writes(lab) - before == 3


def test_the_mint_carries_no_session_and_the_dispatch_records_the_prepared_one(
    tmp_path: Path,
) -> None:
    """§5.2: `prepare()` is the only minter of session ids (cr-o85.34.9).

    The mint used to pre-assign a UUID whenever the bound profile happened to
    be named `claude`, which made the id a property of a string comparison in
    the foreman rather than of the profile that owns the session. The durable
    request the wrapper reads carries none, and the id the child actually ran
    under is written back by the dispatch that recorded the handle.
    """
    lab = ForemanLab(tmp_path)
    root = lab.instantiate()

    mint_entry(lab.composition, lab.wiring(), root)

    activation = lab.store.reads.list_activations(root.root_id)[0]
    launch = read_record(
        lab.wiring().paths.activation_dir(activation.activation_id) / DISPATCH_REQUEST,
        WrapperLaunch,
    )
    assert launch is not None
    assert launch.request.session_id == ""
    assert activation.metadata.session_id == SESSION_ID
    assert activation.metadata.handle is not None
    assert activation.metadata.handle.session_id == SESSION_ID


def test_entry_mint_and_task_construction_read_the_roots_resolution(
    tmp_path: Path,
) -> None:
    """§3.1: an instance override reaches the mint AND the built task (cr-7h8).

    Both were recorded with provenance and then ignored — the mint re-read the
    live role map, and the task builder read the raw pinned node.
    """
    lab = ForemanLab(
        tmp_path,
        overrides={
            "node.implement.model": "override-model",
            "node.implement.token_budget": 1234,
        },
    )
    root = lab.instantiate()

    mint_entry(lab.composition, lab.wiring(), root)

    activation = lab.store.reads.list_activations(root.root_id)[0]
    assert activation.metadata.model == "override-model"
    task = lab.profiles.profile.tasks[-1]
    assert task.model == "override-model"
    assert task.token_budget == 1234


def test_a_role_rebinding_after_instantiation_reaches_a_new_mint(
    tmp_path: Path,
) -> None:
    """New mints use the owner's startup bindings, not historical root pins."""
    lab = ForemanLab(tmp_path)
    root = lab.instantiate()
    lab.composition.config.roles["implementer"] = CrewBinding(
        model="drifted-model", effort="high"
    )
    lab.composition = replace(lab.composition, catalog=lab_catalog(lab.config.roles))

    mint_entry(lab.composition, lab.wiring(), root)

    activation = lab.store.reads.list_activations(root.root_id)[0]
    assert activation.metadata.crew_profile == "codex"
    assert activation.metadata.model == "drifted-model"
    assert activation.metadata.effort == "high"


def test_duplicate_mint_replays_before_new_binding_validation(tmp_path: Path) -> None:
    """A re-tick returns the ledger pin even if its request binding drifted."""
    lab = ForemanLab(tmp_path)
    root = lab.instantiate()
    first = lab.wiring().store.mint_activation(root.root_id, entry_request())

    replay = lab.wiring().store.mint_activation(
        root.root_id, entry_request(model="invalid-new-model", effort="high")
    )

    assert replay.created is False
    assert replay.activation.metadata.model == first.activation.metadata.model
    assert replay.activation.metadata.effort == first.activation.metadata.effort


@pytest.mark.parametrize(
    "overrides",
    ({"effort": ""}, {"context_cap_tokens": 0}, {"context_cap_tokens": -1}),
)
def test_new_mint_refuses_unusable_effort_or_cap(
    tmp_path: Path, overrides: dict[str, object]
) -> None:
    lab = ForemanLab(tmp_path)
    root = lab.instantiate()

    with pytest.raises(CarrierIntegrityError, match="effort|context cap"):
        lab.wiring().store.mint_activation(root.root_id, entry_request(**overrides))


def test_task_uses_activation_effort_and_context_cap(tmp_path: Path) -> None:
    """A direct mint's invocation stays intact when the root has older values."""
    lab = ForemanLab(tmp_path)
    root = lab.instantiate()
    minted = (
        lab.wiring()
        .store.mint_activation(
            root.root_id,
            entry_request(effort="high", context_cap_tokens=120000),
        )
        .activation
    )

    advance_lifecycle(lab.composition, lab.wiring(), root, minted)

    recorded = lab.store.reads.load_activation(minted.activation_id)
    task = lab.profiles.profile.tasks[-1]
    assert recorded.metadata.effort == "high"
    assert recorded.metadata.context_cap_tokens == 120000
    assert task.effort == "high"
    assert task.context_cap_tokens == 120000


def test_a_real_override_reaches_the_brief_the_task_and_the_workspace(
    tmp_path: Path,
) -> None:
    """An in-repo writer reaches every execution reader without becoming a non-writer.

    `writes` and `isolation` are resolved once and then read by everything:
    the brief the crew is given, the task it is launched with, and the
    directory it runs in. Driven through `resolve()`'s own checks, not a
    hand-built resolution.
    """
    lab = ForemanLab(tmp_path)
    lab.instantiate_resolved(
        {"node.implement.writes": True, "node.implement.isolation": "in-repo"}
    )
    lab.profiles.next_script(ChildScript(marker='{"outcome":"done"}\n'))

    report = lab.tick()

    assert report.dispatched is not None
    task = lab.profiles.profile.tasks[-1]
    assert task.writes is True
    assert task.cwd == str(lab.repo)
    assert "repository writes: yes" in task.brief
