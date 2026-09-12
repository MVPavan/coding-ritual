"""Controlled crash and publication races at storage/process boundaries."""

import json
import multiprocessing
import os
import signal
from pathlib import Path

import pytest

from tests._bdio import entry_request, handle, load_definition, make_root
from workflow_interpreter.bdio import Evidence, ExitRecord, Lifecycle
from workflow_interpreter.bdio.errors import LifecycleConflictError


@pytest.mark.parametrize("conflicting", [False, True])
def test_concurrent_evidence_publication_reconciles_only_identical_payload(
    fake_store, fake_bd, conflicting
):
    root = make_root(fake_store, load_definition())
    activation = fake_store.mint_activation(root.root_id, entry_request()).activation
    activation_id = activation.activation_id
    fake_store.record_dispatch(activation_id, handle())
    fake_store.record_exit(
        activation_id,
        ExitRecord(exit_code=0, ended_at="2026-08-25T00:01:00Z", reason="ok"),
    )
    evidence = Evidence(note="late completion")
    winner = Evidence(note="different completion") if conflicting else evidence
    # First guard sees EXIT_RECORDED; a second publisher wins before the fresh guard.
    fake_bd.pause_before(
        "show",
        lambda: fake_bd.pause_before(
            "show", lambda: fake_store.record_evidence(activation_id, winner)
        ),
    )
    if conflicting:
        with pytest.raises(LifecycleConflictError):
            fake_store.record_evidence(activation_id, evidence)
    else:
        result = fake_store.record_evidence(activation_id, evidence)
        assert result.metadata.lifecycle is Lifecycle.EVIDENCE_RECORDED
    assert fake_store.reads.load_activation(activation_id).metadata.evidence == winner


def _die_during_snapshot(fake, entered):
    from workflow_interpreter.supervisor import paths

    original = Path.write_text

    def in_place(path, text, *args, **kwargs):
        if path == fake._state:
            with path.open("w") as stream:
                stream.write(text[: len(text) // 2])
                stream.flush()
                entered.set()
                signal.pause()
        return original(path, text, *args, **kwargs)

    def partial_write(descriptor, data):
        os.write(descriptor, data[: len(data) // 2])
        entered.set()
        signal.pause()

    # Interrupt the actual file write, whether in-place or temp-file publication.
    Path.write_text = in_place
    paths.write_all = partial_write
    fake(["bd", "--db", fake.workspace, "--actor", "test", "show", "wf-1"], 5)


@pytest.mark.proc
def test_killed_fake_writer_preserves_previous_complete_snapshot(tmp_path):
    from tests._foreman import LockedPersistentBd

    state = tmp_path / "bd.json"
    old = {
        "rows": {
            "wf-1": {
                "id": "wf-1",
                "title": "old",
                "status": "open",
                "issue_type": "task",
                "metadata": {},
            }
        },
        "next_id": 2,
        "calls": [],
    }
    state.write_text(json.dumps(old))
    fake = LockedPersistentBd(str(tmp_path), state)
    context = multiprocessing.get_context("fork")
    entered = context.Event()
    writer = context.Process(target=_die_during_snapshot, args=(fake, entered))
    writer.start()
    try:
        assert entered.wait(5), "writer did not reach the controlled partial write"
        writer.kill()
        writer.join(5)
        assert writer.exitcode == -9
        assert json.loads(state.read_text()) == old
        restored = LockedPersistentBd(str(tmp_path), state)
        assert restored.rows == old["rows"]
    finally:
        if writer.is_alive():
            writer.kill()
            writer.join(5)


@pytest.mark.parametrize("conflicting", [False, True])
def test_concurrent_dispatch_publication_reconciles_only_same_handle(
    fake_store, fake_bd, conflicting
):
    root = make_root(fake_store, load_definition())
    activation_id = fake_store.mint_activation(
        root.root_id, entry_request()
    ).activation.activation_id
    launched = handle()
    winner = (
        launched.model_copy(update={"pid": launched.pid + 1})
        if conflicting
        else launched
    )
    fake_bd.pause_before(
        "show",
        lambda: fake_bd.pause_before(
            "show", lambda: fake_store.record_dispatch(activation_id, winner)
        ),
    )
    if conflicting:
        with pytest.raises(LifecycleConflictError):
            fake_store.record_dispatch(activation_id, launched)
    else:
        result = fake_store.record_dispatch(activation_id, launched)
        assert result.metadata.lifecycle is Lifecycle.DISPATCHED
    assert fake_store.reads.load_activation(activation_id).metadata.handle == winner
