"""C2b lifecycle case contracts using the shared real-collaborator lab."""

from dataclasses import replace
from pathlib import Path
from typing import cast

from tests._bdio import entry_request, handle
from tests._foreman import ForemanLab
from workflow_interpreter.bdio import Lifecycle
from workflow_interpreter.foreman.cases import advance_lifecycle, mint_entry
from workflow_interpreter.schema.models import Outcome
from workflow_interpreter.supervisor import Recovery
from workflow_interpreter.supervisor.models import CompletionEvidence
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
    assert _bd_writes(lab) - before == 4
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
    assert _bd_writes(lab) - before == 3
    assert [launch.activation_id for launch in lab.spawner.launches] == [
        minted.activation_id,
    ]


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
