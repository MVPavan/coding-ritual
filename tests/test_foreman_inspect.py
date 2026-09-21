"""C2b wrapper error-mapping contracts at the public wrapper seam."""

from collections.abc import Callable
from pathlib import Path
from types import SimpleNamespace
from typing import NoReturn, cast

import pytest

from tests._foreman import ForemanLab, LockedPersistentBd, entry_request
from workflow_interpreter.bdio import (
    Evidence,
    Lifecycle,
    LifecycleConflictError,
    LossyWriteError,
    MintRequest,
    Outcome,
)
from workflow_interpreter.bdio.constants import (
    DEVIATION_FORK_BARRIER_ABORT,
    DEVIATION_PRECONDITION_REFUSED,
    DEVIATION_UNUSABLE_RESOLUTION,
)
from workflow_interpreter.bdio.wire import config_signature
from workflow_interpreter.foreman.compose import InstanceWiring
from workflow_interpreter.foreman.inspector import (
    WrapperExit,
    _close_error,
    _precondition_reason,
    run_wrapper,
)
from workflow_interpreter.inspector.errors import (
    BandNotHeld,
    ContinuationRefused,
    DirtyTreeRefused,
    ExecLedgerError,
    ForkBarrierAbortError,
    ForkBarrierError,
    PreconditionRefused,
    SnapshotFailed,
)
from workflow_interpreter.inspector.models import LaunchOutcome
from workflow_interpreter.inspector.profile import Profile
from workflow_interpreter.profiles.errors import TaskRefused, UnsupportedOptionError

FailureFactory = Callable[[], Exception]


def _wrapper_with_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, failure: Exception
) -> tuple[ForemanLab, str, str, InstanceWiring]:
    """Build one real minted activation whose inspector raises the given fault."""
    lab = ForemanLab(tmp_path)
    root = lab.instantiate()
    wiring = lab.wiring()
    activation = wiring.store.mint_activation(root.root_id, entry_request()).activation
    monkeypatch.setattr(
        lab.composition.profiles,
        "profile_for",
        lambda _name: cast(Profile, object()),
    )

    def refuse(*_args: object, **_kwargs: object) -> NoReturn:
        raise failure

    monkeypatch.setattr(wiring.inspector, "run", refuse)
    return lab, root.root_id, activation.activation_id, wiring


def test_dirty_tree_reason_names_the_protected_path() -> None:
    assert (
        _precondition_reason(DirtyTreeRefused("dirty", ("src/human.py",)))
        == "src/human.py"
    )


def test_plain_precondition_reason_preserves_its_message() -> None:
    assert (
        _precondition_reason(PreconditionRefused("not a git worktree"))
        == "not a git worktree"
    )


def test_wrapper_fallback_request_rebuilds_the_root_execution_pin(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A missing dispatch file cannot revive stale activation vendor metadata."""
    lab = ForemanLab(tmp_path)
    root = lab.instantiate()
    wiring = lab.wiring()
    activation = wiring.store.mint_activation(root.root_id, entry_request()).activation
    lab.backend._merge_metadata(
        activation.activation_id,
        {"crew_profile": "legacy-crew", "model": "legacy-model"},
    )
    received: list[MintRequest] = []

    def capture(request: MintRequest, *_args: object, **_kwargs: object) -> object:
        received.append(request)
        return SimpleNamespace(dispatch=SimpleNamespace(outcome=LaunchOutcome.LAUNCHED))

    monkeypatch.setattr(wiring.inspector, "run", capture)

    assert (
        run_wrapper(
            lab.composition, root.root_id, activation.activation_id, wiring=wiring
        )
        is WrapperExit.DONE
    )
    request = received[0]
    assert request.crew_profile == "fake"
    assert request.model == "fake"


def test_wrapper_error_close_records_transport_evidence(tmp_path: Path) -> None:
    """Preparation failure closes durably and deletes its unlaunched private copy."""
    lab = ForemanLab(tmp_path)
    root = lab.instantiate()
    wiring = lab.wiring()
    activation = wiring.store.mint_activation(root.root_id, entry_request()).activation
    private = wiring.paths.activation_dir(activation.activation_id) / "toolchain"
    private.mkdir(parents=True)
    (private / "partial").write_text("not evidence")
    result = _close_error(
        wiring,
        activation.activation_id,
        Outcome.ERROR_TRANSPORT,
        OSError("disk"),
    )
    assert result is WrapperExit.DONE
    closed = wiring.store.reads.load_activation(activation.activation_id)
    assert closed.metadata.outcome is Outcome.ERROR_TRANSPORT
    assert closed.metadata.evidence == Evidence(note="disk")
    assert not private.exists()


@pytest.mark.parametrize("field", ("model", "effort"))
def test_unusable_role_resolution_closes_and_the_next_tick_does_not_redispatch(
    tmp_path: Path, field: str
) -> None:
    """A legacy incomplete role resolution halts instead of wedging MINTED."""
    lab = ForemanLab(tmp_path)
    root = lab.instantiate()
    activation = (
        lab.wiring().store.mint_activation(root.root_id, entry_request()).activation
    )
    resolved_config = tuple(
        item
        for item in root.metadata.resolved_config
        if item.key != f"node.implement.{field}"
    )
    lab.backend._merge_metadata(
        root.root_id,
        {
            "resolved_config": [
                item.model_dump(mode="json") for item in resolved_config
            ],
            "config_signature": config_signature(resolved_config),
        },
    )
    assert (
        run_wrapper(lab.composition, root.root_id, activation.activation_id)
        is WrapperExit.DONE
    )
    closed = lab.store.reads.load_activation(activation.activation_id)
    assert closed.metadata.lifecycle is Lifecycle.CLOSED
    assert closed.metadata.outcome is Outcome.ERROR_TRANSPORT
    assert [item.kind for item in closed.metadata.deviations] == [
        DEVIATION_UNUSABLE_RESOLUTION
    ]

    launches = len(lab.spawner.launches)
    report = lab.tick()

    assert report.dispatched is None
    assert report.opened_gate is not None
    assert len(lab.spawner.launches) == launches
    assert len(lab.beads("activation")) == 1


@pytest.mark.parametrize(
    ("failure", "outcome"),
    (
        pytest.param(
            lambda: ForkBarrierError("barrier"),
            Outcome.ERROR_CREW,
            id="fork-barrier-error",
        ),
        pytest.param(
            lambda: ExecLedgerError("ledger"),
            Outcome.ERROR_CREW,
            id="exec-ledger-error",
        ),
        pytest.param(
            lambda: TaskRefused("task"),
            Outcome.ERROR_CREW,
            id="task-refused",
        ),
        pytest.param(
            lambda: UnsupportedOptionError("option"),
            Outcome.ERROR_CREW,
            id="unsupported-option-error",
        ),
    ),
)
def test_crew_faults_close_as_error_crew_with_evidence(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    failure: FailureFactory,
    outcome: Outcome,
) -> None:
    """Each crew-side failure has one durable error-crew mapping."""
    error = failure()
    lab, root_id, activation_id, wiring = _wrapper_with_failure(
        tmp_path, monkeypatch, error
    )

    assert (
        run_wrapper(lab.composition, root_id, activation_id, wiring=wiring)
        is WrapperExit.DONE
    )
    closed = lab.store.reads.load_activation(activation_id)
    assert closed.metadata.outcome is outcome
    assert closed.metadata.evidence == Evidence(note=str(error))
    assert closed.metadata.deviations == ()


def test_continuation_refusal_records_a_transport_deviation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A failed continuation is transport failure, not a taken steer."""
    error = ContinuationRefused("no resumable session")
    lab, root_id, activation_id, wiring = _wrapper_with_failure(
        tmp_path, monkeypatch, error
    )

    assert (
        run_wrapper(lab.composition, root_id, activation_id, wiring=wiring)
        is WrapperExit.DONE
    )
    closed = lab.store.reads.load_activation(activation_id)
    assert closed.metadata.outcome is Outcome.ERROR_TRANSPORT
    assert closed.metadata.evidence == Evidence(note="no resumable session")
    assert closed.metadata.deviations[0].kind == "continuation_refused"


def test_barrier_abort_is_a_retry_counting_transport_deviation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An unacknowledged child is infrastructure failure, never crew failure."""
    error = ForkBarrierAbortError("child 42 never acknowledged")
    lab, root_id, activation_id, wiring = _wrapper_with_failure(
        tmp_path, monkeypatch, error
    )

    assert (
        run_wrapper(lab.composition, root_id, activation_id, wiring=wiring)
        is WrapperExit.DONE
    )
    closed = lab.store.reads.load_activation(activation_id)
    assert closed.metadata.outcome is Outcome.ERROR_TRANSPORT
    assert closed.metadata.deviations[0].kind == DEVIATION_FORK_BARRIER_ABORT


@pytest.mark.parametrize(
    ("failure", "reason"),
    (
        pytest.param(
            lambda: PreconditionRefused("not a git worktree"),
            "not a git worktree",
            id="base-precondition-refused",
        ),
        pytest.param(
            lambda: DirtyTreeRefused("dirty", ("src/human.py", "notes.txt")),
            "src/human.py, notes.txt",
            id="dirty-tree-refused-paths",
        ),
        pytest.param(
            lambda: DirtyTreeRefused("dirty head", (), protected_head="abc123"),
            "abc123",
            id="dirty-tree-refused-head",
        ),
    ),
)
def test_precondition_refusal_preserves_its_type_specific_reason(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    failure: FailureFactory,
    reason: str,
) -> None:
    """Only DirtyTreeRefused has protected paths or a protected head."""
    error = failure()
    lab, root_id, activation_id, wiring = _wrapper_with_failure(
        tmp_path, monkeypatch, error
    )

    assert (
        run_wrapper(lab.composition, root_id, activation_id, wiring=wiring)
        is WrapperExit.DONE
    )
    closed = lab.store.reads.load_activation(activation_id)
    assert closed.metadata.outcome is Outcome.ERROR_TRANSPORT
    assert closed.metadata.evidence == Evidence(note=str(error))
    assert closed.metadata.deviations[0].kind == DEVIATION_PRECONDITION_REFUSED
    assert closed.metadata.deviations[0].reason == reason


def test_band_not_held_does_not_fall_through_to_precondition_deviation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The specialized precondition routes before the generic branch."""
    error = BandNotHeld("band missing")
    lab, root_id, activation_id, wiring = _wrapper_with_failure(
        tmp_path, monkeypatch, error
    )

    assert (
        run_wrapper(lab.composition, root_id, activation_id, wiring=wiring)
        is WrapperExit.DONE
    )
    closed = lab.store.reads.load_activation(activation_id)
    assert closed.metadata.outcome is Outcome.ERROR_TRANSPORT
    assert closed.metadata.evidence == Evidence(note="band missing")
    assert closed.metadata.deviations == ()


def test_snapshot_failure_is_retryable_transport_without_a_deviation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Q26 leaves an infra close eligible for the later retry decision."""
    error = SnapshotFailed("snapshot ref update failed")
    lab, root_id, activation_id, wiring = _wrapper_with_failure(
        tmp_path, monkeypatch, error
    )

    assert (
        run_wrapper(lab.composition, root_id, activation_id, wiring=wiring)
        is WrapperExit.DONE
    )
    closed = lab.store.reads.load_activation(activation_id)
    assert closed.metadata.outcome is Outcome.ERROR_TRANSPORT
    assert closed.metadata.evidence == Evidence(note=str(error))
    assert closed.metadata.deviations == ()


@pytest.mark.parametrize(
    "failure",
    (
        pytest.param(LifecycleConflictError("close raced"), id="lifecycle-conflict"),
        pytest.param(LossyWriteError("wf-1", "metadata", "dropped"), id="lossy-write"),
    ),
)
def test_settled_write_conflicts_are_owned_by_the_tick(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, failure: Exception
) -> None:
    """A conflicting wrapper write is harmless when the tick already settled it."""
    lab, root_id, activation_id, wiring = _wrapper_with_failure(
        tmp_path, monkeypatch, failure
    )

    def settle_then_refuse(*_args: object, **_kwargs: object) -> NoReturn:
        lab.store.close_activation(activation_id, Outcome.DONE)
        raise failure

    monkeypatch.setattr(wiring.inspector, "run", settle_then_refuse)
    assert (
        run_wrapper(lab.composition, root_id, activation_id, wiring=wiring)
        is WrapperExit.CLOSED_BY_TICK
    )


@pytest.mark.parametrize(
    "failure",
    (
        pytest.param(LifecycleConflictError("close raced"), id="lifecycle-conflict"),
        pytest.param(LossyWriteError("wf-1", "metadata", "dropped"), id="lossy-write"),
    ),
)
def test_unsettled_write_conflicts_escape_as_failed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, failure: Exception
) -> None:
    """A conflict without a settled activation remains a visible wrapper failure."""
    lab, root_id, activation_id, wiring = _wrapper_with_failure(
        tmp_path, monkeypatch, failure
    )

    assert (
        run_wrapper(lab.composition, root_id, activation_id, wiring=wiring)
        is WrapperExit.FAILED
    )


def test_locked_wrapper_does_not_read_or_write_the_store(tmp_path: Path) -> None:
    """A real wrapper flock refuses before even the first activation read."""
    lab = ForemanLab(tmp_path)
    root = lab.instantiate()
    activation = (
        lab.wiring().store.mint_activation(root.root_id, entry_request()).activation
    )
    lock = lab.hold_wrapper_lock(activation.activation_id)
    before = list(lab.fake_bd.calls)
    try:
        result = run_wrapper(lab.composition, root.root_id, activation.activation_id)
    finally:
        lock.release()

    assert result is WrapperExit.LOCKED
    assert lab.fake_bd.calls == before
    assert not lab.wiring().paths.ledger(activation.activation_id).exists()


def test_stale_wrapper_does_not_write_or_append_a_ledger(tmp_path: Path) -> None:
    """A non-minted activation is returned untouched after its one durable read."""
    lab = ForemanLab(tmp_path)
    root = lab.instantiate()
    activation = (
        lab.wiring().store.mint_activation(root.root_id, entry_request()).activation
    )
    lab.backend._merge_metadata(
        activation.activation_id, {"lifecycle": (Lifecycle.DISPATCHED.value)}
    )
    before_updates = lab.count("update")
    before_closes = lab.count("close")

    assert (
        run_wrapper(lab.composition, root.root_id, activation.activation_id)
        is WrapperExit.STALE
    )
    assert lab.count("update") == before_updates
    assert lab.count("close") == before_closes
    assert not lab.wiring().paths.ledger(activation.activation_id).exists()


def test_rebuild_reconstructs_new_foreman_collaborators_from_persistent_state(
    tmp_path: Path,
) -> None:
    """A crash restart retains only durable state, never the prior composition."""
    state = tmp_path / "persistent-bd.json"

    def persistent(workspace: str) -> LockedPersistentBd:
        return LockedPersistentBd(workspace, state)

    lab = ForemanLab(tmp_path, bd_factory=persistent)
    root = lab.instantiate()
    old_composition = lab.composition
    old_foreman = lab.foreman
    old_store = lab.store

    lab.rebuild()

    assert lab.composition is not old_composition
    assert lab.foreman is not old_foreman
    assert lab.store is not old_store
    assert lab.root is not None
    assert lab.root.root_id == root.root_id
    assert lab.store.reads.load_root(root.root_id).root_id == root.root_id


def test_rebuild_refuses_an_in_memory_bd(tmp_path: Path) -> None:
    """A crash drill never silently resumes from an empty in-memory fake."""
    lab = ForemanLab(tmp_path)
    lab.instantiate()

    with pytest.raises(AssertionError, match="durable bd_factory"):
        lab.rebuild()


@pytest.mark.proc
@pytest.mark.parametrize("phase", ["pre_reset", "interrupted"])
def test_snapshot_pin_failure_at_wrapper_lifecycle_seam(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, phase: str
) -> None:
    """Reset refusal closes for infra retry; producer recovery blocks settlement."""
    from tests._inspector import ChildScript
    from workflow_interpreter.inspector import Git, GitCommandError

    lab = ForemanLab(tmp_path)
    root = lab.instantiate()
    wiring = lab.wiring()
    activation = wiring.store.mint_activation(root.root_id, entry_request()).activation
    node = root.index.nodes["implement"]
    path = wiring.paths.worktree / "src/feature.py"
    if phase == "pre_reset":
        wiring.workspace.prepare(activation, node)
        path.write_text("unfinished\n")
    else:
        lab.profiles.next_script(
            ChildScript(write_path="src/feature.py", write_body="unfinished\n")
        )
    original = Git.update_ref

    def refuse(self: Git, ref: str, commit: str, *, cwd: Path) -> None:
        if ("/recovery/" in ref) == (phase == "interrupted"):
            raise GitCommandError("injected snapshot pin failure")
        original(self, ref, commit, cwd=cwd)

    monkeypatch.setattr(Git, "update_ref", refuse)
    result = run_wrapper(
        lab.composition, root.root_id, activation.activation_id, wiring=wiring
    )
    current = lab.store.reads.load_activation(activation.activation_id)
    assert path.read_text() == "unfinished\n"
    assert current.metadata.deviations == ()
    if phase == "pre_reset":
        assert result is WrapperExit.DONE
        assert current.metadata.lifecycle is Lifecycle.CLOSED
        assert current.metadata.outcome is Outcome.ERROR_TRANSPORT
        assert current.metadata.handle is None
        assert lab.profiles.profile.tasks == []
    else:
        assert result is WrapperExit.FAILED
        assert current.metadata.lifecycle is Lifecycle.DISPATCHED
        assert wiring.paths.exit_file(activation.activation_id).exists()
        assert current.metadata.outcome is None
        assert current.metadata.evidence is None
        assert not wiring.paths.completion(activation.activation_id).exists()
        assert lab.tick().settled is None
        assert path.read_text() == "unfinished\n"
        monkeypatch.setattr(Git, "update_ref", original)
        assert lab.tick().settled == activation.activation_id
        recovery = wiring.workspace.read_recovery(current)
        assert recovery is not None and recovery.pinned
        assert (
            lab.git.blob_text(f"{recovery.commit}:src/feature.py", cwd=lab.repo)
            == "unfinished\n"
        )
