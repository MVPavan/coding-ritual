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

from enum import StrEnum
from pathlib import Path
from typing import Final

from tests.conftest import branch_head
from workflow_interpreter.bdio.api import WorkflowStore
from workflow_interpreter.bdio.backend import PinnedBackendFactory, StoreBackend
from workflow_interpreter.bdio.rows import NewRow, StoreRow
from workflow_interpreter.bdio.signing import GateVerifier
from workflow_interpreter.ledger.database import LedgerDatabase
from workflow_interpreter.ledger.paths import repo_hash
from workflow_interpreter.ledger.store import LedgerStore

TASK: Final[str] = "cr-3411.2"
GIT_ENTRY: Final[str] = ".git"


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

[supervisor]
repo_root = "{repo_root}"
wrapper_root = "{wrapper_root}"
host = "host"
''',
        encoding="utf-8",
    )
    return path, repo_root, wrapper_root


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
