"""The run ledger's own guarantees: schema, identity, fence, export round trip.

The store CONTRACT (what every backend must do) lives in
`tests/test_store_contract.py`, which runs its read cases on a `ledger` lab.
What is here is what only the ledger has: a migration, a repository identity
pin, a `flock` two wrapper homes contend on, and an export whose round trip
is byte-identical.

Only the fence-contention case forks a process (`proc`); everything else is a
small test over `tmp_path`.
"""

from __future__ import annotations

import json
import os
import sqlite3
import subprocess
import sys
import time
from collections.abc import Iterator
from contextlib import closing
from pathlib import Path
from typing import Any, Final

import pytest

from tests._bdio import entry_request, load_definition, make_root
from tests._gates import ship_gate_request
from tests._ledger import GIT_ENTRY, TASK, config_file, ledger_store, repository
from workflow_interpreter.bdio.constants import BackendKind
from workflow_interpreter.bdio.rows import RowQuery
from workflow_interpreter.ledger import fence as fence_module
from workflow_interpreter.ledger.__main__ import main as ledger_main
from workflow_interpreter.ledger.constants import (
    EXPORT_KIND_HEADER,
    LEDGER_FILE,
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
    LedgerClaimUnsupported,
    LedgerExportError,
    LedgerFenceBusy,
    LedgerIdentityError,
)
from workflow_interpreter.ledger.export import import_export, write_export
from workflow_interpreter.ledger.fence import LedgerFence, holders
from workflow_interpreter.ledger.paths import (
    ensure_fence_dir,
    export_path,
    fence_path,
    ledger_path,
    read_repo_id,
)
from workflow_interpreter.ledger.schema import SCHEMA_VERSION
from workflow_interpreter.ledger.store import LedgerStore

OTHER_TASK: Final[str] = "cr-3411.3"
ARTIFACT_REF: Final[str] = "refs/wf/artifacts/cr-3411.2"
ARTIFACT_OID: Final[str] = "c" * 40
ARTIFACT_DIGEST: Final[str] = "t" * 40
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


def _seeded(database: LedgerDatabase, task_id: str = TASK) -> str:
    """One root and one activation of `task_id`, through the public write path."""
    store = ledger_store(database, task_id)
    root = make_root(store, load_definition())
    store.mint_activation(root.root_id, entry_request())
    return root.root_id


@pytest.fixture
def ledger(tmp_path: Path) -> Iterator[LedgerDatabase]:
    """An open ledger over a fresh repository, closed with the test."""
    repo_root, wrapper_root = repository(tmp_path)
    with open_ledger(repo_root, wrapper_root) as database:
        yield database


# --- schema and migration --------------------------------------------------


def test_an_empty_database_is_migrated_to_the_known_schema(tmp_path: Path) -> None:
    """The first open creates every §3.3 table and pins the version it reached."""
    repo_root, wrapper_root = repository(tmp_path)
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
    repo_root, wrapper_root = repository(tmp_path)
    with open_ledger(repo_root, wrapper_root) as first:
        created = read_meta(first.connection, MetaKey.CREATED_AT)

    with open_ledger(repo_root, wrapper_root) as second:
        assert read_meta(second.connection, MetaKey.CREATED_AT) == created
        assert read_meta(second.connection, MetaKey.REPO_ID) == read_repo_id(repo_root)


def test_the_pre_fence_peek_never_creates_the_database_it_only_reads(
    tmp_path: Path,
) -> None:
    """§3.4: the version peek is a READ, so only the fenced branch may create.

    A peek that opened the file for writing would create it, pin its pragmas
    and leave it for a concurrent opener to read as an up-to-date ledger —
    outside the exclusive fence that exists to make creation single. The
    absent file is proved by refusing the fence: the peek is all that ran.
    """
    repo_root, wrapper_root = repository(tmp_path)
    database_path = ledger_path(repo_root)
    with LedgerFence(fence_path(repo_root)).exclusive():
        with pytest.raises(LedgerFenceBusy):
            open_ledger(
                repo_root,
                wrapper_root,
                fence=LedgerFence(fence_path(repo_root), wait_s=0.0),
            )
        assert not list(database_path.parent.glob(f"{database_path.name}*"))

    # And the absence is "behind", not an error: the first start still creates.
    with open_ledger(repo_root, wrapper_root) as database:
        assert schema_version(database.connection) == SCHEMA_VERSION
    assert database_path.is_file()


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
    store = ledger_store(ledger)
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


def test_a_claim_write_is_refused_rather_than_kept_in_a_second_store(
    ledger: LedgerDatabase,
) -> None:
    """D20: claims stay bd-backed, so the ledger refuses them by name.

    A ledger that answered claim writes itself would give a ledger-backed run
    a claim table no bd-backed run could see — two reservations, no shared
    serialisation, which is the one thing the claim row exists to provide.
    """
    store = LedgerStore(ledger, task_id=TASK)
    _seeded(ledger)

    with pytest.raises(LedgerClaimUnsupported, match="D20"):
        store._claim_and_merge_metadata(TASK, {"integration_target_key": "k"})


# --- repository identity (§3.5) --------------------------------------------


def test_a_store_opened_under_another_wrapper_root_refuses_naming_the_pinned_one(
    tmp_path: Path,
) -> None:
    """The refusal has to say WHICH wrapper root owns the ledger, always."""
    repo_root, wrapper_root = repository(tmp_path)
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
    repo_root, _ = repository(tmp_path)

    assert fence_path(repo_root) == repo_root / GIT_ENTRY / "wf" / "ledger.lock"
    assert ensure_fence_dir(repo_root) == fence_path(repo_root).parent


# --- export and import (§3.6) ----------------------------------------------


def test_an_export_round_trips_byte_identically(tmp_path: Path) -> None:
    """Rebuild from the export, export again: the same bytes, line for line.

    Nothing an import does may show in the next export — not the rows, not the
    `tasks` row, not `next_seq` (§3.6). The attention drain every restore owes
    (§3.2) is therefore recorded OUTSIDE the exportable state, in the
    non-exported `restore_pending` table, which is what keeps this property.
    """
    repo_root, wrapper_root = repository(tmp_path)
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
        second = write_export(reopened, TASK).read_bytes()

    assert second.splitlines() == first.splitlines()
    assert second == first


_HEADER_KEYS: Final[tuple[ExportKey, ...]] = (
    ExportKey.KIND,
    ExportKey.SCHEMA_VERSION,
    ExportKey.REPO_ID,
    ExportKey.TASK_ID,
)
"""Every key an export header carries — and, by equality, every key it does
not: `wrapper_root` named this machine's engine home, which no clone could
satisfy (§3.6)."""


def test_the_export_is_ordered_by_task_and_seq_with_an_identity_header(
    tmp_path: Path,
) -> None:
    """The header pins both identities, and the rows follow the durable order."""
    repo_root, wrapper_root = repository(tmp_path)
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
    assert header[ExportKey.REPO_ID.value] == read_repo_id(repo_root)
    # Nothing about this machine: a wrapper root in the header is what a
    # clone could not satisfy (§3.6).
    assert set(header) == {key.value for key in _HEADER_KEYS}
    assert [line[ExportKey.TABLE.value] for line in lines[1:]] == [
        LedgerTable.TASKS.value,
        LedgerTable.ROOTS.value,
        LedgerTable.ACTIVATIONS.value,
    ]
    assert [line[ExportKey.ROW.value]["seq"] for line in lines[2:]] == [1, 2]


def test_an_import_rebuilds_the_task_rather_than_merging_it(tmp_path: Path) -> None:
    """A restore leaves exactly what the export describes, and nothing else."""
    repo_root, wrapper_root = repository(tmp_path)
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
    """§3.6: the header is checked against the DESTINATION's own `repo_id`.

    Another repository, and not merely another path: the second checkout mints
    its own id, which is what makes this a refusal while a clone of the FIRST
    one — carrying the same committed `.wf/repo-id` — is an import.
    """
    repo_root, wrapper_root = repository(tmp_path)
    with open_ledger(repo_root, wrapper_root) as database:
        _seeded(database)
        export = write_export(database, TASK)
    elsewhere, elsewhere_wrapper = repository(tmp_path / "elsewhere")
    with open_ledger(elsewhere, elsewhere_wrapper):
        pass

    with pytest.raises(LedgerIdentityError) as refusal:
        import_export(
            export,
            repo_root=elsewhere,
            wrapper_root=elsewhere_wrapper,
            ledger=ledger_path(elsewhere),
        )

    assert str(read_repo_id(repo_root)) in str(refusal.value)


def test_an_export_row_naming_an_unknown_column_is_refused_whole(
    tmp_path: Path,
) -> None:
    """A column name reaches SQL as TEXT, so it is checked against the schema."""
    repo_root, wrapper_root = repository(tmp_path)
    with open_ledger(repo_root, wrapper_root) as database:
        _seeded(database)
        export = write_export(database, TASK)
    _rewrite(export, _with_column(_lines(export), "x) VALUES (1); DROP TABLE roots --"))

    with pytest.raises(LedgerExportError, match="column"):
        import_export(
            export,
            repo_root=repo_root,
            wrapper_root=wrapper_root,
            ledger=ledger_path(repo_root),
        )

    with open_ledger(repo_root, wrapper_root) as reopened:
        assert _count(reopened, LedgerTable.ROOTS) == 1


def test_an_export_row_naming_a_table_no_task_export_carries_is_refused(
    tmp_path: Path,
) -> None:
    """`meta` is a real table and not one an export may write into."""
    repo_root, wrapper_root = repository(tmp_path)
    with open_ledger(repo_root, wrapper_root) as database:
        _seeded(database)
        export = write_export(database, TASK)
    lines = _lines(export)
    lines[2][ExportKey.TABLE.value] = LedgerTable.META.value
    _rewrite(export, lines)

    with pytest.raises(LedgerExportError, match="meta"):
        import_export(
            export,
            repo_root=repo_root,
            wrapper_root=wrapper_root,
            ledger=ledger_path(repo_root),
        )

    with open_ledger(repo_root, wrapper_root) as reopened:
        assert _count(reopened, LedgerTable.ROOTS) == 1


def test_an_export_whose_rows_carry_another_task_is_refused(tmp_path: Path) -> None:
    """A file may only restore the task its header declares (§3.6)."""
    repo_root, wrapper_root = repository(tmp_path)
    with open_ledger(repo_root, wrapper_root) as database:
        _seeded(database)
        _seeded(database, OTHER_TASK)
        export = write_export(database, OTHER_TASK)
    lines = _lines(export)
    lines[0][ExportKey.TASK_ID.value] = TASK
    _rewrite(export, lines)

    with pytest.raises(LedgerExportError, match=OTHER_TASK):
        import_export(
            export,
            repo_root=repo_root,
            wrapper_root=wrapper_root,
            ledger=ledger_path(repo_root),
        )

    with open_ledger(repo_root, wrapper_root) as reopened:
        assert _count(reopened, LedgerTable.ROOTS) == 1


def test_an_export_carrying_no_tasks_row_is_refused(tmp_path: Path) -> None:
    """A header alone does not describe a task the rebuild can restore."""
    repo_root, wrapper_root = repository(tmp_path)
    with open_ledger(repo_root, wrapper_root) as database:
        _seeded(database)
        export = write_export(database, TASK)
    lines = _lines(export)
    _rewrite(export, [lines[0], *lines[2:]])

    with pytest.raises(LedgerExportError, match=LedgerTable.TASKS.value):
        import_export(
            export,
            repo_root=repo_root,
            wrapper_root=wrapper_root,
            ledger=ledger_path(repo_root),
        )


def test_an_export_carrying_two_tasks_rows_is_refused(tmp_path: Path) -> None:
    """Exactly one `tasks` row, so the file declares one task and carries it."""
    repo_root, wrapper_root = repository(tmp_path)
    with open_ledger(repo_root, wrapper_root) as database:
        _seeded(database)
        export = write_export(database, TASK)
    lines = _lines(export)
    _rewrite(export, [lines[0], lines[1], *lines[1:]])

    with pytest.raises(LedgerExportError, match=LedgerTable.TASKS.value):
        import_export(
            export,
            repo_root=repo_root,
            wrapper_root=wrapper_root,
            ledger=ledger_path(repo_root),
        )


def test_an_import_into_a_ledger_that_records_a_landing_rebuilds_it(
    tmp_path: Path,
) -> None:
    """A landed ledger is rebuilt, not refused (store-restructure §3.6).

    It was refused whole before: `landings` was outside `EXPORT_TABLES` and
    references `tasks` with no `ON DELETE`, so the rebuild's `DELETE FROM
    tasks` would have failed its own foreign key. Now the export carries the
    journal, `_clear` empties it in reverse order like every other exportable
    table, and the rebuild puts back exactly what the file describes — here, a
    row the destination did not have.

    The rows are written with SQL rather than through `LandingJournal` because
    what this keys on is a landed ledger, whatever wrote it.
    """
    repo_root, wrapper_root = repository(tmp_path)
    with open_ledger(repo_root, wrapper_root) as database:
        _seeded(database)
        _landing(database.connection, attempt=1)
        export = write_export(database, TASK)
    with closing(connect(ledger_path(repo_root))) as raw:
        raw.execute("DELETE FROM landings")
        _landing(raw, attempt=2)

    import_export(
        export,
        repo_root=repo_root,
        wrapper_root=wrapper_root,
        ledger=ledger_path(repo_root),
    )

    with open_ledger(repo_root, wrapper_root) as reopened:
        attempts = reopened.connection.execute(
            "SELECT attempt FROM landings WHERE task_id = ?", (TASK,)
        ).fetchall()
    # The export set IS the ledger after an import: attempt 2 was never in a
    # file, so it does not survive the rebuild that brought attempt 1 back.
    assert [int(row[0]) for row in attempts] == [1]


def _landing(connection: sqlite3.Connection, *, attempt: int) -> None:
    """One `landings` row of the fixture task, written straight to SQL."""
    connection.execute(
        "INSERT INTO landings (task_id, attempt, phase, record_json, written_at) "
        "VALUES (?, ?, 'intent', '{}', '2026-09-18T00:00:00Z')",
        (TASK, attempt),
    )


def test_an_import_leaves_no_task_the_export_set_does_not_describe(
    tmp_path: Path,
) -> None:
    """§3.6: a rebuild is the whole exportable state, not the files' tasks only."""
    config, repo_root, wrapper_root = config_file(tmp_path)
    with open_ledger(repo_root, wrapper_root) as database:
        _seeded(database)
        _seeded(database, OTHER_TASK)
        write_export(database, TASK)

    assert ledger_main(["--config", str(config), "import"]) == 0

    with open_ledger(repo_root, wrapper_root) as reopened:
        assert _count(reopened, LedgerTable.ROOTS, task_id=TASK) == 1
        assert _count(reopened, LedgerTable.ROOTS, task_id=OTHER_TASK) == 0
        assert _count(reopened, LedgerTable.TASKS, task_id=OTHER_TASK) == 0


def test_a_failing_file_leaves_every_earlier_file_unimported(tmp_path: Path) -> None:
    """One fence, one transaction: a rebuild half-applied is not a rebuild."""
    config, repo_root, wrapper_root = config_file(tmp_path)
    with open_ledger(repo_root, wrapper_root) as database:
        _seeded(database)
        _seeded(database, OTHER_TASK)
        write_export(database, TASK)
        second = write_export(database, OTHER_TASK)
    lines = _lines(second)
    lines[-1][ExportKey.ROW.value]["root_id"] = "no-such-root"
    _rewrite(second, lines)
    with closing(connect(ledger_path(repo_root))) as raw:
        raw.execute("DELETE FROM activations")

    assert ledger_main(["--config", str(config), "import"]) == 2

    with open_ledger(repo_root, wrapper_root) as reopened:
        assert _count(reopened, LedgerTable.ACTIVATIONS, task_id=TASK) == 0


def test_an_import_into_a_ledger_pinned_to_another_wrapper_root_is_refused(
    tmp_path: Path,
) -> None:
    """§3.5: the DESTINATION's pins are checked, under the exclusive fence."""
    repo_root, wrapper_root = repository(tmp_path)
    with open_ledger(repo_root, wrapper_root) as database:
        _seeded(database)
        export = write_export(database, TASK)
    for suffix in ("", "-wal", "-shm"):
        ledger_path(repo_root).with_name(f"{LEDGER_FILE}{suffix}").unlink(
            missing_ok=True
        )
    intruder = tmp_path / "other-wrapper"
    intruder.mkdir()
    with open_ledger(repo_root, intruder):
        pass

    with pytest.raises(LedgerIdentityError) as refusal:
        import_export(
            export,
            repo_root=repo_root,
            wrapper_root=wrapper_root,
            ledger=ledger_path(repo_root),
        )

    assert str(intruder.resolve()) in str(refusal.value)


def _lines(export: Path) -> list[dict[str, Any]]:
    """Every line of an export file as its parsed JSON object."""
    return [
        json.loads(line) for line in export.read_text(encoding="utf-8").splitlines()
    ]


def _rewrite(export: Path, lines: list[dict[str, Any]]) -> None:
    """Write a crafted export back, one JSON object per line."""
    export.write_text(
        "".join(f"{json.dumps(line)}\n" for line in lines), encoding="utf-8"
    )


def _with_column(lines: list[dict[str, Any]], column: str) -> list[dict[str, Any]]:
    """The same lines, with the roots row carrying one column name it must not."""
    lines[2][ExportKey.ROW.value][column] = "x"
    return lines


def _count(database: LedgerDatabase, table: LedgerTable, task_id: str = TASK) -> int:
    """How many rows of one task the table holds."""
    statement = f"SELECT COUNT(*) FROM {table.value} WHERE task_id = ?"
    return int(database.connection.execute(statement, (task_id,)).fetchone()[0])


# --- the fence (§3.4) ------------------------------------------------------


@pytest.mark.proc
def test_an_import_refuses_while_a_shared_fence_holder_lives(tmp_path: Path) -> None:
    """The bounded wait ends in a refusal that NAMES the holder's pid."""
    repo_root, wrapper_root = repository(tmp_path)
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
    repo_root, wrapper_root = repository(tmp_path)
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


def test_the_cli_exports_a_task_and_imports_it_back(tmp_path: Path) -> None:
    """`wf ledger export <task>` then `wf ledger import`, over one config."""
    config, repo_root, wrapper_root = config_file(tmp_path)
    with open_ledger(repo_root, wrapper_root) as database:
        _seeded(database)

    assert ledger_main(["--config", str(config), "export", TASK]) == 0
    assert export_path(repo_root, TASK).is_file()
    assert ledger_main(["--config", str(config), "import"]) == 0

    with open_ledger(repo_root, wrapper_root) as reopened:
        assert LedgerStore(reopened, task_id=TASK).find_rows(RowQuery())


def test_the_cli_refuses_a_task_the_ledger_does_not_hold(tmp_path: Path) -> None:
    """An export of an unknown task is a refusal, not an empty file."""
    config, repo_root, _ = config_file(tmp_path)

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
