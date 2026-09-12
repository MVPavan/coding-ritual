"""C2b lifecycle case contracts using the shared real-collaborator lab."""

from dataclasses import replace
from pathlib import Path
from typing import cast

import pytest

from tests._bdio import handle
from tests._foreman import FAKE_PROFILE, ForemanLab, entry_request
from tests._supervisor import SESSION_ID, ChildScript
from workflow_interpreter.bdio import ExitRecord, Lifecycle
from workflow_interpreter.foreman import cases as cases_module
from workflow_interpreter.foreman.cases import advance_lifecycle, mint_entry, route_head
from workflow_interpreter.foreman.compose import WrapperLaunch
from workflow_interpreter.foreman.config import RunnerBinding
from workflow_interpreter.foreman.constants import DISPATCH_REQUEST
from workflow_interpreter.schema.models import Outcome
from workflow_interpreter.supervisor import Recovery
from workflow_interpreter.supervisor.models import CompletionEvidence, RecoveryCase
from workflow_interpreter.supervisor.paths import read_record


def _bd_writes(lab: ForemanLab) -> int:
    """Count every durable bd mutation, excluding reads and process-local files."""
    return sum(lab.count(command) for command in ("create", "update", "close"))


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


def test_minted_dispatch_rebuilds_its_request_from_the_root_pin(tmp_path: Path) -> None:
    """A legacy activation cannot select a different launch vendor."""
    lab = ForemanLab(tmp_path)
    root = lab.instantiate()
    minted = (
        lab.wiring().store.mint_activation(root.root_id, entry_request()).activation
    )
    lab.fake_bd.rows[minted.activation_id]["metadata"].update(
        {"runner_profile": "legacy-runner", "model": "legacy-model"}
    )
    activation = lab.store.reads.load_activation(minted.activation_id)

    advance_lifecycle(lab.composition, lab.wiring(), root, activation)

    request = lab.spawner.launches[-1].request
    assert request.runner_profile == FAKE_PROFILE
    assert request.model == "fake"


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
    lab = ForemanLab(tmp_path)
    root = lab.instantiate()
    minted = (
        lab.wiring().store.mint_activation(root.root_id, entry_request()).activation
    )
    dispatched = lab.wiring().store.record_dispatch(minted.activation_id, handle())
    closed = lab.wiring().store.close_activation(
        dispatched.activation_id, Outcome.ERROR_TRANSPORT
    )
    lab.fake_bd.rows[closed.activation_id]["metadata"].update(
        {"runner_profile": "legacy-runner", "model": "legacy-model"}
    )
    legacy = lab.store.reads.load_activation(closed.activation_id)

    result = route_head(lab.composition, lab.wiring(), root, legacy)

    assert result.dispatched is not None
    retried = lab.store.reads.load_activation(result.dispatched)
    assert retried.metadata.runner_profile == FAKE_PROFILE
    assert retried.metadata.model == "fake"


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
    assert _bd_writes(lab) - before == 3


def test_exit_recorded_settlement_uses_the_root_pinned_profile(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A replayed exit is parsed by the vendor the root says ran."""
    lab = ForemanLab(tmp_path)
    root = lab.instantiate()
    minted = (
        lab.wiring().store.mint_activation(root.root_id, entry_request()).activation
    )
    dispatched = lab.wiring().store.record_dispatch(minted.activation_id, handle())
    activation = lab.wiring().store.record_exit(
        dispatched.activation_id,
        ExitRecord(exit_code=0, ended_at="2026-09-08T00:00:00Z", reason="ok"),
    )
    lab.fake_bd.rows[activation.activation_id]["metadata"]["runner_profile"] = (
        "legacy-runner"
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


def test_dispatched_settlement_uses_the_root_pinned_profile(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A recovered exit is parsed by the vendor the root says ran."""
    lab = ForemanLab(tmp_path)
    root = lab.instantiate()
    minted = (
        lab.wiring().store.mint_activation(root.root_id, entry_request()).activation
    )
    activation = lab.wiring().store.record_dispatch(minted.activation_id, handle())
    lab.fake_bd.rows[activation.activation_id]["metadata"]["runner_profile"] = (
        "legacy-runner"
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
    assert _bd_writes(lab) - before == 2


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


def test_a_role_rebinding_after_instantiation_never_reaches_a_mint(
    tmp_path: Path,
) -> None:
    """§3.1: the live roles map is consulted at instantiation only (cr-7h8)."""
    lab = ForemanLab(tmp_path)
    root = lab.instantiate()
    lab.composition.config.roles["implementer"] = RunnerBinding(
        profile=FAKE_PROFILE, model="drifted-model", effort="high"
    )

    mint_entry(lab.composition, lab.wiring(), root)

    activation = lab.store.reads.list_activations(root.root_id)[0]
    assert activation.metadata.runner_profile == FAKE_PROFILE
    assert activation.metadata.model == "fake"


def test_a_real_override_reaches_the_brief_the_task_and_the_workspace(
    tmp_path: Path,
) -> None:
    """An in-repo writer reaches every execution reader without becoming a non-writer.

    `writes` and `isolation` are resolved once and then read by everything:
    the brief the runner is given, the task it is launched with, and the
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
