"""Shared ledger lab builders for the two ledger test families (not a test module).

It also owns the logical fault points, because two families arm them: the
store contract (which runs them on every backend that can produce one) and the
ledger's own projection tests (which prove a crash at each point reconciles at
the next drain).

`test_ledger_store` covers what only the ledger HAS — schema, identity pin,
fence, export round trip — and `test_ledger_writes` covers what it DOES under
concurrency. Both need the same "a repository with a ledger in it" and "the
public write path over one task" shapes, so there is one definition of each.
"""

from __future__ import annotations

import json
import time
from collections.abc import Callable
from enum import StrEnum
from pathlib import Path
from typing import Final

from tests._bdio import entry_request, load_definition, make_root
from tests.conftest import branch_head
from workflow_interpreter.bdio.api import WorkflowStore
from workflow_interpreter.bdio.backend import PinnedBackendFactory, StoreBackend
from workflow_interpreter.bdio.rows import NewRow, StoreRow
from workflow_interpreter.bdio.signing import GateVerifier
from workflow_interpreter.bdio.wire import BeadRecord
from workflow_interpreter.ledger.database import LedgerDatabase
from workflow_interpreter.ledger.paths import repo_hash
from workflow_interpreter.ledger.store import LedgerStore

TASK: Final[str] = "cr-3411.2"
GIT_ENTRY: Final[str] = ".git"
STATUS_OPEN: Final[str] = "open"
SIGNAL_TIMEOUT_S: Final[float] = 30.0
"""How long one process waits for another's file signal before failing. A race
test that hangs teaches nothing; one that fails names which signal never came."""
SIGNAL_POLL_S: Final[float] = 0.01


def _nothing() -> None:
    """The default hook: a label write with nothing to interleave."""


def repository(tmp_path: Path) -> tuple[Path, Path]:
    """A repository and a wrapper root, with the in-repo `.git` shape.

    `.git` as a DIRECTORY is its own git common directory (`sandbox._common_dir`),
    which is all the fence resolver reads — so these tests need no `git` binary.
    """
    repo_root = tmp_path / "repo"
    (repo_root / GIT_ENTRY).mkdir(parents=True)
    wrapper_root = tmp_path / "wrapper"
    wrapper_root.mkdir(exist_ok=True)
    return repo_root, wrapper_root


def ledger_store(
    database: LedgerDatabase,
    task_id: str = TASK,
    *,
    verifier: GateVerifier | None = None,
    claims_backend: StoreBackend | None = None,
) -> WorkflowStore:
    """The public write path over one task's ledger rows.

    Built through the factory, the way production builds one: the backend a
    root is served by is the factory's answer, never a borrowed handle (§3.2).
    """
    backend = LedgerStore(database, task_id=task_id)
    return WorkflowStore(
        backend,
        verifier,
        backend_factory=PinnedBackendFactory(backend),
        branch_head_reader=branch_head,
        claims_backend=claims_backend,
    )


def seeded_task(database: LedgerDatabase, task_id: str = TASK) -> str:
    """One root and one activation of `task_id`, through the public write path.

    Here rather than in one test module because both export families need the
    same "a task with rows in it" shape before they can say anything about the
    bytes it exports.
    """
    store = ledger_store(database, task_id)
    root = make_root(store, load_definition())
    store.mint_activation(root.root_id, entry_request())
    return root.root_id


def ledger_backend(database: LedgerDatabase, task_id: str = TASK) -> LedgerStore:
    """The backend itself, for the tests that ask it what only IT decides.

    The public path (`ledger_store`) goes through `WorkflowStore`, which
    verifies a signature before it hands a gate closure down. A test about the
    closing TRANSACTION — which decision owns the gate when two arrive — states
    its closures directly, so it can state two of them.
    """
    return LedgerStore(database, task_id=task_id)


def config_file(
    tmp_path: Path, bd_workspace: Path | None = None
) -> tuple[Path, Path, Path]:
    """A foreman config over a fresh repository, and the two roots it names.

    `bd_workspace` names a REAL bd workspace for the commands that reach bd;
    the export and import paths never do, so they take the placeholder.
    """
    repo_root, _ = repository(tmp_path)
    home = tmp_path / "home"
    wrapper_root = home / repo_hash(repo_root)
    path = tmp_path / "foreman.toml"
    path.write_text(
        f'''repo_root = "{repo_root}"
wrapper_home = "{home}"
host = "host"
actor = "actor"

[bd]
workspace = "{bd_workspace or tmp_path / "bd"}"
actor = "actor"

[inspector]
repo_root = "{repo_root}"
wrapper_root = "{wrapper_root}"
host = "host"
''',
        encoding="utf-8",
    )
    return path, repo_root, wrapper_root


class FileLabelWriter:
    """An `AttentionWriter` whose bead is a JSON file, shared across processes.

    The in-memory `FakeBd` cannot be the bead of a REAL race: two processes do
    not share it. A file can be, and the label write stays what the reconciler
    treats it as — one write followed by a read-back — so what is under test is
    the ordering, not a substitute for it.
    """

    def __init__(
        self, path: Path, task_id: str = TASK, *, before: Callable[[], None] = _nothing
    ) -> None:
        self._path = path
        self._task_id = task_id
        self._before = before

    def labels(self) -> tuple[str, ...]:
        """The labels the bead currently carries."""
        if not self._path.exists():
            return ()
        loaded = json.loads(self._path.read_text(encoding="utf-8"))
        return tuple(str(label) for label in loaded)

    def _add_label(self, bead_id: str, label: str) -> BeadRecord:
        """Add one label and read the bead back."""
        return self._write(bead_id, (*self.labels(), label))

    def _remove_label(self, bead_id: str, label: str) -> BeadRecord:
        """Remove one label and read the bead back."""
        return self._write(
            bead_id, tuple(held for held in self.labels() if held != label)
        )

    def _write(self, bead_id: str, labels: tuple[str, ...]) -> BeadRecord:
        """Set the bead's labels, after whatever must happen first has."""
        self._before()
        self._path.write_text(json.dumps(sorted(set(labels))), encoding="utf-8")
        return BeadRecord(
            id=bead_id,
            title="task",
            status=STATUS_OPEN,
            issue_type="task",
            labels=self.labels(),
        )


def wait_for(path: Path, *, timeout_s: float = SIGNAL_TIMEOUT_S) -> None:
    """Block until another process raises `path`, or fail loudly (not silently)."""
    deadline = time.monotonic() + timeout_s
    while not path.exists():
        if time.monotonic() > deadline:
            raise TimeoutError(f"{path} was never raised")
        time.sleep(SIGNAL_POLL_S)


class FaultPoint(StrEnum):
    """Where a backend is made to fail, named by meaning rather than command."""

    AFTER_STATE_COMMIT = "after-state-commit"
    """The routing state landed; the process dies before the follow-up write
    that finishes the transition."""

    BEFORE_READBACK = "before-readback"
    """The write landed durably; its verifying read never returned, so the
    caller never learned the row exists."""


class InjectedLedgerCrash(Exception):
    """A ledger writer that died where the fault point says it did."""


class CrashingLedgerStore(LedgerStore):
    """A ledger store that dies at one logical fault point, once.

    Subclassed rather than hooked into production code: the fault points are
    real call boundaries, so a test-only override IS the crash — the
    transaction either committed before it or it did not, and that is exactly
    what the two points name.
    """

    def __init__(self, database: LedgerDatabase, *, task_id: str) -> None:
        super().__init__(database, task_id=task_id)
        self._armed: FaultPoint | None = None

    def arm(self, point: FaultPoint) -> None:
        """Arm the next occurrence of `point`."""
        self._armed = point

    def _disarm(self, point: FaultPoint) -> bool:
        """Whether this call is the armed one, clearing the arming if it is."""
        if self._armed is not point:
            return False
        self._armed = None
        return True

    def _create_row(self, new: NewRow) -> StoreRow:
        """Commit the row, then die before the caller can learn it exists."""
        written = super()._create_row(new)
        if self._disarm(FaultPoint.BEFORE_READBACK):
            raise InjectedLedgerCrash(written.id)
        return written

    def _close_row(self, row_id: str, reason: str) -> StoreRow:
        """Die before the close that follows an already-committed state."""
        if self._disarm(FaultPoint.AFTER_STATE_COMMIT):
            raise InjectedLedgerCrash(row_id)
        return super()._close_row(row_id, reason)
