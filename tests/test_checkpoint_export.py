"""A deleted ledger is survivable mid-run (store-restructure §3.9, R10, S7).

Seven properties, one test each — the epic's last slice is small on purpose:

1. `.wf/ledger.db` deleted after an activation close, with the task still in
   flight, rebuilds from the CHECKPOINT anchor and the in-flight root comes
   back as it was: same root, same attempt, no retry minted — and the run then
   RESUMES from that close rather than replaying it;
2. a task anchored ONLY by checkpoints is never `closed()` or `retired()`, and
   the latch stays NULL through a rebuild — a checkpoint is not a close;
3. a task that closed rebuilds from its CLOSE anchor even when a stale
   checkpoint exists, and the re-export of the rebuilt ledger is byte-identical
   to the committed file (D3);
4. a checkpoint the git seam cannot write degrades — the activation still
   closes, because the run's facts are already in the ledger;
5. `wf ledger export` refuses a task that has not LANDED, which is what keeps
   the committed path a rebuild prefers from ever being the OLDER of the two
   anchors (S7 review, finding 1);
6. a rebuild REFUSES when git cannot answer whether checkpoints exist, rather
   than silently dropping every in-flight task (finding 2);
7. the staging write is a replace of a unique temporary file, and the task id
   it is keyed by goes through the one identifier grammar (finding 3).

Real git throughout: a blob, a ref and a rebuild cannot be faked.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Final

import pytest

from tests._bdio import REVIEW, entry_request, handle, load_definition, make_root
from tests._inspector import make_repo
from tests._ledger import EPIC, TASK, ledger_store, seed_contractor_record
from workflow_interpreter.bdio.carriers import MintReason
from workflow_interpreter.bdio.records import ActivationRecord
from workflow_interpreter.bdio.wire import ExitRecord
from workflow_interpreter.contracts.run_identity import InvalidIdentifier
from workflow_interpreter.inspector.config import InspectorConfig
from workflow_interpreter.inspector.errors import GitCommandError
from workflow_interpreter.inspector.gitio import Git
from workflow_interpreter.inspector.sandbox import SandboxMode
from workflow_interpreter.ledger import checkpoint as checkpoint_module
from workflow_interpreter.ledger.checkpoint import (
    TaskCheckpoint,
    checkpoint_ref,
    rebuild_sources,
    staging_path,
)
from workflow_interpreter.ledger.closure import closed, retired
from workflow_interpreter.ledger.constants import TaskState
from workflow_interpreter.ledger.database import LedgerDatabase, open_ledger
from workflow_interpreter.ledger.errors import LedgerExportError
from workflow_interpreter.ledger.export import (
    export_task,
    import_exports,
    pin_export,
    write_export,
    write_landed_export,
)
from workflow_interpreter.ledger.paths import (
    export_path,
    ledger_path,
    repo_id_path,
)
from workflow_interpreter.ledger.tasks import export_oid, record_task_state
from workflow_interpreter.schema.models import Outcome

HOST: Final[str] = "checkpoint-export-test"
GIT_TIMEOUT_S: Final[float] = 30.0
EXIT_RECORD: Final[ExitRecord] = ExitRecord(
    exit_code=0, ended_at="2026-09-20T00:01:00Z", reason="ok"
)
SQL_ROOT_COUNT: Final[str] = "SELECT COUNT(*) FROM roots WHERE task_id = ?"
STATUS_CLOSED: Final[str] = "closed"


def _git(repo: Path, *args: str) -> str:
    """One git command in `repo`, with an explicit timeout."""
    return subprocess.run(
        ("git", *args),
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
        timeout=GIT_TIMEOUT_S,
    ).stdout.strip()


def _seam(repo_root: Path, wrapper_root: Path) -> Git:
    """The engine's git seam over one checkout, sandbox off."""
    return Git(
        InspectorConfig(
            repo_root=repo_root,
            wrapper_root=wrapper_root,
            host=HOST,
            sandbox=SandboxMode.OFF,
        )
    )


def _lab(tmp_path: Path, name: str = "repo") -> tuple[Path, Path, Git]:
    """A real checkout, its wrapper root, and the git seam over both."""
    repo_root = make_repo(tmp_path, name)
    wrapper_root = tmp_path / f"{name}-wrapper"
    wrapper_root.mkdir(exist_ok=True)
    return repo_root, wrapper_root, _seam(repo_root, wrapper_root)


def _run_one_activation(
    database: LedgerDatabase, git: Git
) -> tuple[str, ActivationRecord]:
    """One root and one CLOSED activation, through the checkpointing path.

    The checkpoint sink is wired exactly as `foreman/__main__` wires it, so
    what these tests observe is the production hook and not a call they made
    themselves.
    """
    store = ledger_store(database, checkpoint=TaskCheckpoint(database, git))
    root = make_root(store, load_definition())
    activation = store.mint_activation(root.root_id, entry_request()).activation
    store.record_dispatch(activation.activation_id, handle())
    store.record_exit(activation.activation_id, EXIT_RECORD)
    return root.root_id, store.close_activation(activation.activation_id, Outcome.DONE)


def _rebuild(git: Git, repo_root: Path, wrapper_root: Path) -> tuple[str, ...]:
    """Rebuild the deleted ledger from whichever anchors git still carries."""
    with open_ledger(repo_root, wrapper_root):
        pass
    return import_exports(
        rebuild_sources(git, repo_root, ()),
        repo_root=repo_root,
        wrapper_root=wrapper_root,
        ledger=ledger_path(repo_root),
    )


def _landed(database: LedgerDatabase) -> None:
    """Record the task as LANDED, which is what closure's gate asks first."""
    seed_contractor_record(database, TASK, state="landed", epic_id=EPIC)
    record_task_state(database, TASK, TaskState.LANDED)


def test_a_ledger_deleted_mid_run_rebuilds_to_the_last_activation_close(
    tmp_path: Path,
) -> None:
    """§3.9 and R10: an in-flight task survives losing its database.

    Before S7 the rows of a task that had not closed existed only in
    `.wf/ledger.db`; deleting it lost the run, recovery refused the ownerless
    evidence in `refs/wf/*` and the orchestrator had to retry. The checkpoint
    written at every activation close is the anchor that makes the rebuild
    possible — and the point of resuming rather than retrying is that the
    ATTEMPT does not move: the same root comes back, and no second one is
    minted beside it.

    The rebuild is only half the acceptance, so the run is then driven ONE step
    further: the successor mint the foreman would make from the closed head
    (`cases.route_head` → an EDGE mint on the predecessor activation) has to
    succeed against the rebuilt ledger, on the same root, without the closed
    activation being replayed.
    """
    repo, wrapper_root, git = _lab(tmp_path)
    with open_ledger(repo, wrapper_root) as database:
        root_id, closure = _run_one_activation(database, git)

    assert git.ref_target(checkpoint_ref(TASK), cwd=repo) is not None
    ledger_path(repo).unlink()

    assert _rebuild(git, repo, wrapper_root) == (TASK,)
    with open_ledger(repo, wrapper_root) as rebuilt:
        store = ledger_store(rebuilt, checkpoint=TaskCheckpoint(rebuilt, git))
        reads = store.reads
        root = reads.load_root(root_id)
        again = reads.load_activation(closure.activation_id)
        resumed = store.mint_activation(
            root_id,
            entry_request(
                node=REVIEW,
                mint_reason=MintReason.EDGE,
                predecessor_activation_id=closure.activation_id,
            ),
        ).activation
        activations = tuple(
            record.activation_id for record in reads.list_activations(root_id)
        )
        with rebuilt.locked() as connection:
            roots = connection.execute(SQL_ROOT_COUNT, (TASK,)).fetchone()[0]

    assert root.root_id == root_id, "the in-flight root is resumed, not replaced"
    assert roots == 1, "no retry attempt was minted by the rebuild"
    assert again.status == STATUS_CLOSED
    assert again.metadata.outcome is closure.metadata.outcome
    assert resumed.metadata.wf_root_id == root_id, "the resume stays on the root"
    assert resumed.metadata.outcome_taken is closure.metadata.outcome, (
        "the resume continues from the LAST activation close"
    )
    assert activations == (closure.activation_id, resumed.activation_id), (
        "the closed activation is continued from, never replayed"
    )


def test_a_task_anchored_only_by_checkpoints_is_never_closed(
    tmp_path: Path,
) -> None:
    """A checkpoint anchor is not a close anchor, and never latches (§3.5).

    The two live in different ref namespaces on purpose, so the distinction is
    made by NAME rather than by a flag the wrong caller could set: `closed()`
    asks `anchor_oid`, which reads the committed blob and
    `refs/wf/exports/<task>` — never `refs/wf/checkpoints/<task>`. The task
    below is LANDED, so every other condition for closure holds, and the
    checkpoint still answers nothing. The latch is elided from the export
    bytes, so a rebuild cannot smuggle one back either.
    """
    repo, wrapper_root, git = _lab(tmp_path)
    with open_ledger(repo, wrapper_root) as database:
        _run_one_activation(database, git)
        _landed(database)
        TaskCheckpoint(database, git).checkpoint(TASK)

        assert closed(database, git, TASK) is False
        assert retired(database, git, TASK) is False
        assert export_oid(database, TASK) is None
    ledger_path(repo).unlink()

    _rebuild(git, repo, wrapper_root)

    with open_ledger(repo, wrapper_root) as rebuilt:
        assert export_oid(rebuilt, TASK) is None, "a checkpoint never latches"
        assert closed(rebuilt, git, TASK) is False
        assert retired(rebuilt, git, TASK) is False


def test_a_closed_task_rebuilds_from_the_close_anchor_byte_identically(
    tmp_path: Path,
) -> None:
    """The close anchor WINS, and the rebuilt ledger re-exports the same bytes.

    A close export is written at landing, after the last activation close, so
    it is always the newer of the two anchors — which is why "the newest of
    {close, checkpoint}" is decided by name here rather than by a timestamp
    nobody could trust. The stale checkpoint below is taken before the rows
    that landed the task, so restoring from it would be visible: the re-export
    would not be the committed file.
    """
    repo, wrapper_root, git = _lab(tmp_path)
    with open_ledger(repo, wrapper_root) as database:
        _run_one_activation(database, git)
        stale = git.ref_target(checkpoint_ref(TASK), cwd=repo)
        _landed(database)
        path = write_export(database, TASK)
        pin_export(git, database, TASK, repo)
        committed = path.read_bytes()
    _git(repo, "add", "--", str(path), str(repo_id_path(repo)))
    _git(repo, "commit", "--quiet", "-m", "land: the task and its export")
    ledger_path(repo).unlink()

    assert rebuild_sources(git, repo, ()) == (export_path(repo, TASK),)
    assert git.ref_target(checkpoint_ref(TASK), cwd=repo) == stale
    assert _rebuild(git, repo, wrapper_root) == (TASK,)

    with open_ledger(repo, wrapper_root) as rebuilt:
        assert export_task(rebuilt, TASK) == committed
        assert closed(rebuilt, git, TASK) is True


def test_a_checkpoint_the_seam_cannot_write_does_not_fail_the_activation(
    tmp_path: Path,
) -> None:
    """A checkpoint is an optimisation over losing the ledger, not a gate.

    The activation's facts are already committed when the checkpoint is taken,
    so a git seam that refuses must degrade to a log line: failing the close
    would trade a recoverable ledger loss for an unrecoverable run.
    """
    repo, wrapper_root, _ = _lab(tmp_path)

    class RefusingGit(Git):
        """A seam whose object write always fails, as a full disk would."""

        def write_blob(self, path: Path, *, cwd: Path) -> str:
            """Refuse, by the same error a real `hash-object` failure raises."""
            raise GitCommandError(f"git hash-object refused {path}")

    git = RefusingGit(
        InspectorConfig(
            repo_root=repo,
            wrapper_root=wrapper_root,
            host=HOST,
            sandbox=SandboxMode.OFF,
        )
    )
    with open_ledger(repo, wrapper_root) as database:
        _root_id, closure = _run_one_activation(database, git)

        assert closure.status == STATUS_CLOSED
        assert closure.metadata.outcome is Outcome.DONE
    assert _seam(repo, wrapper_root).ref_target(checkpoint_ref(TASK), cwd=repo) is None


def test_an_in_flight_export_cannot_outrank_a_newer_checkpoint(
    tmp_path: Path,
) -> None:
    """`wf ledger export` gates on LANDED, so the FILE is never the older anchor.

    A rebuild prefers the committed path by NAME, and that is only the newer
    answer while every file on it was written at landing. An operator export of
    a task still in flight broke exactly that: the file predated every later
    activation close, and the import — which CLEARS and refills — would have
    rebuilt the task backwards in time. The gate is the same one `pin-export`
    holds, so the crash-between-write-and-pin file it recovers still exists and
    is still preferred.
    """
    repo, wrapper_root, git = _lab(tmp_path)
    with open_ledger(repo, wrapper_root) as database:
        _run_one_activation(database, git)

        with pytest.raises(LedgerExportError, match="has not landed"):
            write_landed_export(database, TASK)

        assert not export_path(repo, TASK).exists()
        assert rebuild_sources(git, repo, ()) == (staging_path(repo, TASK),)

        _landed(database)

        assert write_landed_export(database, TASK) == export_path(repo, TASK)
    assert rebuild_sources(git, repo, ()) == (export_path(repo, TASK),)


def test_a_rebuild_refuses_when_git_cannot_say_which_tasks_are_checkpointed(
    tmp_path: Path,
) -> None:
    """A `show-ref` that FAILED is not the same fact as "there are no refs".

    Swallowing it made `import` rebuild from the committed exports alone, which
    clears every in-flight task's rows out of a live ledger and reports
    success. Git answering "no refs" (exit 1) still degrades to the empty set,
    because that answer is true.
    """
    repo, wrapper_root, _ = _lab(tmp_path)

    class BlindGit(Git):
        """A seam whose ref listing fails, as a timeout under load would."""

        def ref_names_under(self, prefix: str, *, cwd: Path) -> tuple[str, ...]:
            """Refuse, by the error a real `show-ref` failure raises."""
            raise GitCommandError(f"git show-ref failed (exit 128) for {prefix}")

    blind = BlindGit(
        InspectorConfig(
            repo_root=repo,
            wrapper_root=wrapper_root,
            host=HOST,
            sandbox=SandboxMode.OFF,
        )
    )

    with pytest.raises(LedgerExportError, match="checkpoint"):
        rebuild_sources(blind, repo, ())

    assert rebuild_sources(_seam(repo, wrapper_root), repo, ()) == ()


def test_a_checkpoint_stages_through_a_replace_of_a_unique_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The staging path is shared per task, so it may only ever be REPLACED.

    Two roots of one task close activations on two threads of one process
    (`database.py`, R8's `<task>-a<n>`), and a `write_bytes` interleaved with
    another's `hash-object` pins a ref to a byte-mix of two exports — which is
    unparseable, so the import refuses the whole rebuild at the one moment the
    checkpoint exists for. Either complete file is a valid export, so an
    `os.replace` of a unique temporary is enough; the id that names both files
    goes through the one grammar first.
    """
    repo, wrapper_root, git = _lab(tmp_path)
    replaced: list[tuple[str, str]] = []
    real_replace = os.replace

    def spy(source: object, destination: object) -> None:
        """Record every replace this checkpoint performs, then perform it."""
        replaced.append((str(source), str(destination)))
        real_replace(str(source), str(destination))

    monkeypatch.setattr(checkpoint_module.os, "replace", spy)
    with open_ledger(repo, wrapper_root) as database:
        _run_one_activation(database, git)

    staged = staging_path(repo, TASK)
    assert replaced, "the staging file was written in place"
    assert [destination for _, destination in replaced] == [str(staged)] * len(replaced)
    assert all(source != str(staged) for source, _ in replaced)
    assert [path.name for path in staged.parent.iterdir()] == [staged.name]
    with pytest.raises(InvalidIdentifier):
        staging_path(repo, "../../escape")
