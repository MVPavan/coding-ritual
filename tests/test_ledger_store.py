"""The run ledger's own guarantees: schema, identity, fence, export round trip.

The store CONTRACT (what every backend must do) lives in
`tests/test_store_contract.py`, which runs its read cases on a `ledger` lab.
What is here is what only the ledger has: a migration, a repository identity
pin, a `flock` two wrapper homes contend on, and an export whose round trip is
byte-identical.

Only the fence-contention case forks a process (`proc`); everything else is a
small test over `tmp_path`.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from collections.abc import Iterator
from contextlib import closing
from pathlib import Path
from typing import Final

import pytest

from tests._bdio import entry_request, load_definition, make_root
from tests._gates import ship_gate_request
from tests.conftest import branch_head
from workflow_interpreter.bdio.api import WorkflowStore
from workflow_interpreter.bdio.backend import PinnedBackendFactory
from workflow_interpreter.bdio.constants import BackendKind
from workflow_interpreter.bdio.rows import RowQuery
from workflow_interpreter.ledger import fence as fence_module
from workflow_interpreter.ledger.__main__ import main as ledger_main
from workflow_interpreter.ledger.constants import (
    EXPORT_KIND_HEADER,
    ROW_TABLES,
    ExportKey,
    LedgerTable,
    MetaKey,
)
from workflow_interpreter.ledger.database import (
    LedgerDatabase,
    connect,
    open_ledger,
    read_meta,
    schema_version,
)
from workflow_interpreter.ledger.errors import (
    LedgerFenceBusy,
    LedgerIdentityError,
    LedgerWriteUnsupported,
)
from workflow_interpreter.ledger.export import import_export, write_export
from workflow_interpreter.ledger.fence import LedgerFence, holders
from workflow_interpreter.ledger.paths import (
    ensure_fence_dir,
    export_path,
    fence_path,
    ledger_path,
    repo_hash,
)
from workflow_interpreter.ledger.schema import SCHEMA_VERSION
from workflow_interpreter.ledger.store import LedgerStore

TASK: Final[str] = "cr-3411.2"
ARTIFACT_REF: Final[str] = "refs/wf/artifacts/cr-3411.2"
ARTIFACT_OID: Final[str] = "c" * 40
ARTIFACT_DIGEST: Final[str] = "t" * 40
GIT_ENTRY: Final[str] = ".git"
HOLD_TIMEOUT_S: Final[float] = 20.0
HOLD_POLL_S: Final[float] = 0.05
READY: Final[str] = "held"
_SAME_DEVICE_PID: Final[int] = 424242
_OTHER_DEVICE_PID: Final[int] = 424243
_HOLDER_SCRIPT: Final[str] = """
import fcntl, os, sys
fd = os.open(sys.argv[1], os.O_RDWR | os.O_CREAT, 0o644)
fcntl.flock(fd, fcntl.LOCK_SH)
sys.stdout.write("held\\n")
sys.stdout.flush()
sys.stdin.readline()
"""
"""A second process holding the fence SHARED, exactly as a live driver does:
it reports when the lock is taken and holds it until its stdin is closed."""


def _repository(tmp_path: Path) -> tuple[Path, Path]:
    """A repository and a wrapper root, with the in-repo `.git` shape.

    `.git` as a DIRECTORY is its own git common directory (`sandbox._common_dir`),
    which is all the fence resolver reads — so these tests need no `git` binary.
    """
    repo_root = tmp_path / "repo"
    (repo_root / GIT_ENTRY).mkdir(parents=True)
    wrapper_root = tmp_path / "wrapper"
    wrapper_root.mkdir()
    return repo_root, wrapper_root


def _store(database: LedgerDatabase, task_id: str = TASK) -> WorkflowStore:
    """The public write path over one task's ledger rows."""
    backend = LedgerStore(database, task_id=task_id)
    return WorkflowStore(
        backend,
        backend_factory=PinnedBackendFactory(backend),
        branch_head_reader=branch_head,
    )


def _seeded(database: LedgerDatabase, task_id: str = TASK) -> str:
    """One root and one activation of `task_id`, through the public write path."""
    store = _store(database, task_id)
    root = make_root(store, load_definition())
    store.mint_activation(root.root_id, entry_request())
    return root.root_id


@pytest.fixture
def ledger(tmp_path: Path) -> Iterator[LedgerDatabase]:
    """An open ledger over a fresh repository, closed with the test."""
    repo_root, wrapper_root = _repository(tmp_path)
    with open_ledger(repo_root, wrapper_root) as database:
        yield database


# --- schema and migration --------------------------------------------------


def test_an_empty_database_is_migrated_to_the_known_schema(tmp_path: Path) -> None:
    """The first open creates every §3.3 table and pins the version it reached."""
    repo_root, wrapper_root = _repository(tmp_path)
    assert not ledger_path(repo_root).exists()

    with open_ledger(repo_root, wrapper_root) as database:
        assert schema_version(database.connection) == SCHEMA_VERSION
        tables = {
            row[0]
            for row in database.connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            ).fetchall()
        }
    assert {table.value for table in LedgerTable} <= tables


def test_a_second_open_migrates_nothing_and_keeps_the_creation_pin(
    tmp_path: Path,
) -> None:
    """Migration is forward-only, so an up-to-date ledger is opened untouched."""
    repo_root, wrapper_root = _repository(tmp_path)
    with open_ledger(repo_root, wrapper_root) as first:
        created = read_meta(first.connection, MetaKey.CREATED_AT)

    with open_ledger(repo_root, wrapper_root) as second:
        assert read_meta(second.connection, MetaKey.CREATED_AT) == created
        assert read_meta(second.connection, MetaKey.REPO_HASH) == repo_hash(repo_root)


def test_the_pragmas_the_concurrency_contract_names_are_applied(
    ledger: LedgerDatabase,
) -> None:
    """§3.4.1: WAL, a 5 s busy timeout and `synchronous = NORMAL`."""
    read = ledger.connection.execute
    assert str(read("PRAGMA journal_mode").fetchone()[0]).lower() == "wal"
    assert read("PRAGMA busy_timeout").fetchone()[0] == 5000
    assert read("PRAGMA synchronous").fetchone()[0] == 1


def test_every_row_carries_the_task_and_a_per_task_seq(ledger: LedgerDatabase) -> None:
    """§3.3: `task_id` and a `seq` from `tasks.next_seq` on every row."""
    _seeded(ledger)

    seqs = [
        (row["task_id"], row["seq"])
        for table in ROW_TABLES
        for row in ledger.connection.execute(f"SELECT * FROM {table.value}").fetchall()
    ]
    next_seq = ledger.connection.execute(
        "SELECT next_seq FROM tasks WHERE task_id = ?", (TASK,)
    ).fetchone()[0]
    assert {task for task, _ in seqs} == {TASK}
    assert sorted(seq for _, seq in seqs) == [1, 2]
    assert next_seq == 3


def test_a_bound_gate_projects_the_artifact_oid_beside_its_ref(
    ledger: LedgerDatabase,
) -> None:
    """§3.3: `artifact_ref` names the ref, `artifact_oid` the immutable object."""
    store = _store(ledger)
    root = make_root(store, load_definition())
    source = store.mint_activation(root.root_id, entry_request()).activation
    store.open_gate(
        root.root_id,
        ship_gate_request(
            source.activation_id,
            artifact_ref=ARTIFACT_REF,
            artifact_oid=ARTIFACT_OID,
            artifact_digest=ARTIFACT_DIGEST,
        ),
    )

    row = ledger.connection.execute(
        "SELECT artifact_ref, artifact_oid FROM gates"
    ).fetchone()
    assert row["artifact_ref"] == ARTIFACT_REF
    assert row["artifact_oid"] == ARTIFACT_OID


def test_the_probe_round_trips_a_value_and_reports_the_pinned_identity(
    ledger: LedgerDatabase,
) -> None:
    """§11: the ledger's canary is its schema, its wrapper root and a write."""
    result = LedgerStore(ledger, task_id=TASK).probe()

    assert result.kind is BackendKind.LEDGER
    assert result.attributes["schema_version"] == str(SCHEMA_VERSION)
    assert result.attributes["wrapper_root"] == str(ledger.wrapper_root)
    assert read_meta(ledger.connection, MetaKey.SCHEMA_VERSION) == str(SCHEMA_VERSION)


def test_the_write_surface_s1_does_not_implement_refuses_loudly(
    ledger: LedgerDatabase,
) -> None:
    """A half-written transition is worse than a refusal (S2 owns the writes)."""
    store = LedgerStore(ledger, task_id=TASK)
    root_id = _seeded(ledger)

    with pytest.raises(LedgerWriteUnsupported):
        store._merge_metadata(root_id, {"terminal": "done"})
    with pytest.raises(LedgerWriteUnsupported):
        store._close_row(root_id, "outcome=done")


# --- repository identity (§3.5) --------------------------------------------


def test_a_store_opened_under_another_wrapper_root_refuses_naming_the_pinned_one(
    tmp_path: Path,
) -> None:
    """The refusal has to say WHICH wrapper root owns the ledger, always."""
    repo_root, wrapper_root = _repository(tmp_path)
    with open_ledger(repo_root, wrapper_root):
        pass
    intruder = tmp_path / "other-wrapper"
    intruder.mkdir()

    with pytest.raises(LedgerIdentityError) as refusal:
        open_ledger(repo_root, intruder)

    assert str(wrapper_root.resolve()) in str(refusal.value)


def test_a_tree_that_is_not_a_repository_has_no_fence_to_take(
    tmp_path: Path,
) -> None:
    """No `.git` means no git common dir, and a fence nobody shares is none."""
    with pytest.raises(LedgerIdentityError):
        fence_path(tmp_path)
    assert ensure_fence_dir(tmp_path) is None


def test_the_fence_lives_in_the_git_common_directory(tmp_path: Path) -> None:
    """D4: outside `git clean`'s reach and shared by every worktree."""
    repo_root, _ = _repository(tmp_path)

    assert fence_path(repo_root) == repo_root / GIT_ENTRY / "wf" / "ledger.lock"
    assert ensure_fence_dir(repo_root) == fence_path(repo_root).parent


# --- export and import (§3.6) ----------------------------------------------


def test_an_export_round_trips_byte_identically(tmp_path: Path) -> None:
    """Rebuild from the export, export again, and the bytes are the same."""
    repo_root, wrapper_root = _repository(tmp_path)
    with open_ledger(repo_root, wrapper_root) as database:
        _seeded(database)
        first = write_export(database, TASK).read_bytes()

    import_export(
        export_path(repo_root, TASK),
        repo_root=repo_root,
        wrapper_root=wrapper_root,
        ledger=ledger_path(repo_root),
    )

    with open_ledger(repo_root, wrapper_root) as reopened:
        assert write_export(reopened, TASK).read_bytes() == first


def test_the_export_is_ordered_by_task_and_seq_with_an_identity_header(
    tmp_path: Path,
) -> None:
    """The header pins both identities, and the rows follow the durable order."""
    repo_root, wrapper_root = _repository(tmp_path)
    with open_ledger(repo_root, wrapper_root) as database:
        _seeded(database)
        lines = [
            json.loads(line)
            for line in write_export(database, TASK)
            .read_text(encoding="utf-8")
            .splitlines()
        ]

    header = lines[0]
    assert header[ExportKey.KIND.value] == EXPORT_KIND_HEADER
    assert header[ExportKey.REPO_HASH.value] == repo_hash(repo_root)
    assert header[ExportKey.WRAPPER_ROOT.value] == str(wrapper_root.resolve())
    assert [line[ExportKey.TABLE.value] for line in lines[1:]] == [
        LedgerTable.TASKS.value,
        LedgerTable.ROOTS.value,
        LedgerTable.ACTIVATIONS.value,
    ]
    assert [line[ExportKey.ROW.value]["seq"] for line in lines[2:]] == [1, 2]


def test_an_import_rebuilds_the_task_rather_than_merging_it(tmp_path: Path) -> None:
    """A restore leaves exactly what the export describes, and nothing else."""
    repo_root, wrapper_root = _repository(tmp_path)
    with open_ledger(repo_root, wrapper_root) as database:
        root_id = _seeded(database)
        write_export(database, TASK)

    ledger_file = ledger_path(repo_root)
    with closing(connect(ledger_file)) as raw:
        raw.execute("DELETE FROM activations")
        raw.execute("UPDATE roots SET status = 'closed'")
    import_export(
        export_path(repo_root, TASK),
        repo_root=repo_root,
        wrapper_root=wrapper_root,
        ledger=ledger_file,
    )

    with open_ledger(repo_root, wrapper_root) as reopened:
        store = LedgerStore(reopened, task_id=TASK)
        assert store.get_row(root_id).status == "open"
        assert len(store.find_rows(_activations_of(root_id))) == 1


def test_an_export_from_another_repository_is_refused(tmp_path: Path) -> None:
    """§3.5: the header is checked against BOTH pins before anything is written."""
    repo_root, wrapper_root = _repository(tmp_path)
    with open_ledger(repo_root, wrapper_root) as database:
        _seeded(database)
        export = write_export(database, TASK)
    elsewhere, _ = _repository(tmp_path / "elsewhere")

    with pytest.raises(LedgerIdentityError) as refusal:
        import_export(
            export,
            repo_root=elsewhere,
            wrapper_root=wrapper_root,
            ledger=ledger_path(elsewhere),
        )

    assert repo_hash(repo_root) in str(refusal.value)


# --- the fence (§3.4) ------------------------------------------------------


@pytest.mark.proc
def test_an_import_refuses_while_a_shared_fence_holder_lives(tmp_path: Path) -> None:
    """The bounded wait ends in a refusal that NAMES the holder's pid."""
    repo_root, wrapper_root = _repository(tmp_path)
    with open_ledger(repo_root, wrapper_root) as database:
        _seeded(database)
        export = write_export(database, TASK)

    with _holding(fence_path(repo_root)) as holder:
        assert holder.pid in holders(fence_path(repo_root))
        with pytest.raises(LedgerFenceBusy) as refusal:
            import_export(
                export,
                repo_root=repo_root,
                wrapper_root=wrapper_root,
                ledger=ledger_path(repo_root),
                fence=LedgerFence(fence_path(repo_root), wait_s=0.2),
            )

    assert refusal.value.holders == (holder.pid,)
    assert f"pid {holder.pid}" in str(refusal.value)


@pytest.mark.proc
def test_an_open_ledger_holds_the_fence_shared_for_the_life_of_its_connection(
    tmp_path: Path,
) -> None:
    """§3.4.4: the hold is the connection's, not one call's."""
    repo_root, wrapper_root = _repository(tmp_path)
    with open_ledger(repo_root, wrapper_root):
        assert os.getpid() in holders(fence_path(repo_root))
    assert os.getpid() not in holders(fence_path(repo_root))


def _activations_of(root_id: str) -> RowQuery:
    """The §4 activation selector for one instance."""
    return RowQuery(metadata_filters={"wf_root_id": root_id, "wf_kind": "activation"})


class _Holder:
    """A live process holding the fence, and the pid the refusal must name."""

    def __init__(self, process: subprocess.Popen[str]) -> None:
        self._process = process

    @property
    def pid(self) -> int:
        """The holder's pid."""
        return self._process.pid

    def stop(self) -> None:
        """Let the holder exit, and wait until it has."""
        if self._process.stdin is not None:
            self._process.stdin.close()
        self._process.wait(timeout=HOLD_TIMEOUT_S)


def _holding(path: Path) -> _HolderContext:
    """A second process holding `path` shared, for the body of a `with`."""
    return _HolderContext(path)


class _HolderContext:
    """Start the holder, wait until the lock is really taken, stop it after."""

    def __init__(self, path: Path) -> None:
        self._path = path

    def __enter__(self) -> _Holder:
        """Spawn the holder and block until it says the lock is held."""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        process = subprocess.Popen(
            (sys.executable, "-c", _HOLDER_SCRIPT, str(self._path)),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            text=True,
        )
        assert process.stdout is not None
        deadline = time.monotonic() + HOLD_TIMEOUT_S
        while time.monotonic() < deadline:
            if process.stdout.readline().strip() == READY:
                self._holder = _Holder(process)
                return self._holder
            time.sleep(HOLD_POLL_S)
        process.kill()
        raise AssertionError("the fence holder never reported that it held the lock")

    def __exit__(self, *_exception: object) -> None:
        """Release the holder however the body ended."""
        self._holder.stop()


# --- the CLI (§3.6) --------------------------------------------------------


def _config_file(tmp_path: Path) -> tuple[Path, Path, Path]:
    """A foreman config over a fresh repository, and the two roots it names."""
    repo_root, _ = _repository(tmp_path)
    home = tmp_path / "home"
    wrapper_root = home / repo_hash(repo_root)
    path = tmp_path / "foreman.toml"
    path.write_text(
        f'''repo_root = "{repo_root}"
wrapper_home = "{home}"
host = "host"
actor = "actor"

[bd]
workspace = "{tmp_path / "bd"}"
actor = "actor"

[supervisor]
repo_root = "{repo_root}"
wrapper_root = "{wrapper_root}"
host = "host"
''',
        encoding="utf-8",
    )
    return path, repo_root, wrapper_root


def test_the_cli_exports_a_task_and_imports_it_back(tmp_path: Path) -> None:
    """`wf ledger export <task>` then `wf ledger import`, over one config."""
    config, repo_root, wrapper_root = _config_file(tmp_path)
    with open_ledger(repo_root, wrapper_root) as database:
        _seeded(database)

    assert ledger_main(["--config", str(config), "export", TASK]) == 0
    assert export_path(repo_root, TASK).is_file()
    assert ledger_main(["--config", str(config), "import"]) == 0

    with open_ledger(repo_root, wrapper_root) as reopened:
        assert LedgerStore(reopened, task_id=TASK).find_rows(RowQuery())


def test_the_cli_refuses_a_task_the_ledger_does_not_hold(tmp_path: Path) -> None:
    """An export of an unknown task is a refusal, not an empty file."""
    config, repo_root, _ = _config_file(tmp_path)

    assert ledger_main(["--config", str(config), "export", TASK]) == 2
    assert not export_path(repo_root, TASK).exists()


def test_a_lock_on_another_device_with_the_same_inode_is_not_a_holder(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An inode number is unique per device, so the device is part of the key."""
    lock = tmp_path / "ledger.lock"
    lock.write_bytes(b"")
    stat = lock.stat()
    major, minor = os.major(stat.st_dev), os.minor(stat.st_dev)
    locks = tmp_path / "locks"
    locks.write_text(
        f"1: FLOCK  ADVISORY  WRITE {_SAME_DEVICE_PID} "
        f"{major:02x}:{minor:02x}:{stat.st_ino} 0 EOF\n"
        f"2: FLOCK  ADVISORY  READ {_OTHER_DEVICE_PID} "
        f"{major + 1:02x}:{minor:02x}:{stat.st_ino} 0 EOF\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(fence_module, "PROC_LOCKS", str(locks))

    assert holders(lock) == (_SAME_DEVICE_PID,)
