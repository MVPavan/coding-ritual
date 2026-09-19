"""What an export IS: facts about the task, never about the file or the machine.

Five properties, and every one of them is a defect the store-restructure
roadmap §1 names:

1. the bytes a task re-exports are the bytes its pin names, so a rebuilt ledger
   can still be closed and archived (`cr-p7dg`);
2. a committed export imports into a fresh CLONE at another path, which is what
   "rebuild from the committed export" has to mean (§3.6);
3. the landing journal survives the round trip, so D17's fallback still has a
   row to read after a rebuild (`cr-ho9m`);
4. every table in the schema is either exported or explicitly NOT, with a
   reason — the completeness check that keeps the next table from being
   forgotten in silence;
5. and until §3.5's `closed()` exists in S2, `adapter.close` still refuses a
   record that names no export blob (D5).

`wf ledger pin-export` is here too, beside the first: it recovers the one
window the pin cannot make atomic, and it has to pin exactly the bytes that
property is about.

Real git rather than the `.git`-directory stand-in the other ledger tests use:
three of these are statements about a blob, a ref or a clone, and none of those
can be faked.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Final

import pytest

from tests._ledger import TASK, repository, seeded_task
from workflow_interpreter.bdio.client import BdClient
from workflow_interpreter.bdio.constants import BackendKind
from workflow_interpreter.contractor import (
    ContractorAdapter,
    ContractorAdapterError,
    ContractorRecord,
    ContractorState,
    LandingIntent,
)
from workflow_interpreter.contractor.journal import (
    ExportPin,
    LandingJournal,
    LandingPhase,
)
from workflow_interpreter.inspector import Git
from workflow_interpreter.inspector.config import InspectorConfig
from workflow_interpreter.inspector.sandbox import SandboxMode
from workflow_interpreter.ledger.__main__ import COMMAND_PIN_EXPORT
from workflow_interpreter.ledger.__main__ import main as ledger_main
from workflow_interpreter.ledger.constants import (
    EXPORT_REF_TEMPLATE,
    EXPORT_TABLES,
    NON_EXPORTED,
    LedgerTable,
)
from workflow_interpreter.ledger.database import open_ledger
from workflow_interpreter.ledger.export import import_export, write_export
from workflow_interpreter.ledger.paths import (
    export_path,
    ledger_path,
    repo_hash,
    repo_id_path,
)
from workflow_interpreter.ledger.schema import table_columns
from workflow_interpreter.ledger.tasks import export_oid

EPIC_ID: Final[str] = "phase-1"
STAGE_ID: Final[str] = "stage-a"
TARGET_REF: Final[str] = "refs/heads/main"
ROOT_ID: Final[str] = "contractor-root"
BASE_COMMIT: Final[str] = "a" * 40
ARTIFACT_OID: Final[str] = "b" * 40
TREE_OID: Final[str] = "c" * 40
GATE_RECEIPT: Final[str] = "gate-receipt"
LANDING_RECEIPT: Final[str] = "landing-receipt"
ATTEMPT: Final[int] = 1
POLICY_DIGEST: Final[str] = "d" * 64
HOST: Final[str] = "export-integrity-test"
OTHER_TASK: Final[str] = "cr-3411.3"
UNKNOWN_TASK: Final[str] = "cr-3411.404"
"""A task no ledger row describes, so a file named for it pins nothing."""


def _git_binary(*args: str, cwd: Path) -> str:
    """Run one git command in `cwd` and answer its stripped output."""
    return subprocess.run(
        ("git", *args), cwd=cwd, check=True, capture_output=True, text=True
    ).stdout.strip()


def _git_repository(tmp_path: Path, name: str = "repo") -> tuple[Path, Path]:
    """A real git checkout with one commit, and the wrapper root beside it."""
    repo_root = tmp_path / name
    repo_root.mkdir(parents=True)
    _git_binary("init", "--quiet", "--initial-branch=main", cwd=repo_root)
    _git_binary("config", "user.email", "tests@example.invalid", cwd=repo_root)
    _git_binary("config", "user.name", "ledger tests", cwd=repo_root)
    (repo_root / "README.md").write_text("repository\n", encoding="utf-8")
    _git_binary("add", "README.md", cwd=repo_root)
    _git_binary("commit", "--quiet", "-m", "first", cwd=repo_root)
    wrapper_root = tmp_path / f"{name}-wrapper"
    wrapper_root.mkdir()
    return repo_root, wrapper_root


def _git(repo_root: Path, wrapper_root: Path) -> Git:
    """The engine's git seam over one checkout, sandbox off."""
    return Git(
        InspectorConfig(
            repo_root=repo_root,
            wrapper_root=wrapper_root,
            host=HOST,
            sandbox=SandboxMode.OFF,
        )
    )


def _config_file(repo_root: Path, tmp_path: Path) -> tuple[Path, Path]:
    """A foreman config over `repo_root`, and the wrapper root it derives.

    `tests._ledger.config_file` builds its own `.git`-directory repository;
    the CLI cases here need the config to name a REAL checkout, because what
    they run reaches git.
    """
    home = tmp_path / "home"
    wrapper_root = home / repo_hash(repo_root)
    path = tmp_path / "foreman.toml"
    path.write_text(
        f'''repo_root = "{repo_root}"
wrapper_home = "{home}"
host = "{HOST}"
actor = "actor"

[bd]
workspace = "{tmp_path / "bd"}"
actor = "actor"

[inspector]
repo_root = "{repo_root}"
wrapper_root = "{wrapper_root}"
host = "{HOST}"
''',
        encoding="utf-8",
    )
    return path, wrapper_root


def _landing_intent() -> LandingIntent:
    """One journalled landing intent, the shape D17's fallback reads back."""
    return LandingIntent(
        ref=TARGET_REF,
        expected_base=BASE_COMMIT,
        artifact_oid=ARTIFACT_OID,
        tree=TREE_OID,
        gate_receipt_digest=GATE_RECEIPT,
        root_id=ROOT_ID,
        policy_digest=POLICY_DIGEST,
        stage=STAGE_ID,
        attempt=ATTEMPT,
    )


def test_a_closed_task_re_exports_the_very_bytes_its_pin_names(
    tmp_path: Path,
) -> None:
    """Export, close, export again: the same bytes, and the pinned blob (§3.6).

    The defect this closes (§1.1): the pin is recorded on the `tasks` row AFTER
    the bytes are written, so an export that carried `export_oid` could never
    hash to the blob it names. A ledger rebuilt from that file could never be
    closed or archived again.
    """
    repo_root, wrapper_root = _git_repository(tmp_path)
    git = _git(repo_root, wrapper_root)
    exported = export_path(repo_root, TASK)
    with open_ledger(repo_root, wrapper_root) as database:
        seeded_task(database)
        pinned_oid = ExportPin(database, git, repo_root).pin(TASK, BackendKind.LEDGER)
        as_pinned = exported.read_bytes()
        again = write_export(database, TASK).read_bytes()

    ref = EXPORT_REF_TEMPLATE.format(task_id=TASK)
    assert again == as_pinned
    assert _git_binary("hash-object", "--", str(exported), cwd=repo_root) == pinned_oid
    assert _git_binary("rev-parse", "--verify", ref, cwd=repo_root) == pinned_oid


def test_pin_export_recovers_a_crash_between_the_write_and_the_pin(
    tmp_path: Path,
) -> None:
    """`wf ledger pin-export` pins the bytes ON DISK and records their oid.

    The one window `ExportPin` cannot make atomic: the file is written and the
    process dies before the ref names its blob, so the task looks unexported
    while its whole record is sitting in the checkout. Recovery re-pins those
    bytes rather than exporting again — the operator's file is the one the
    oid must name.
    """
    repo_root, _ = _git_repository(tmp_path)
    config, wrapper_root = _config_file(repo_root, tmp_path)
    exported = export_path(repo_root, TASK)
    ref = EXPORT_REF_TEMPLATE.format(task_id=TASK)
    with open_ledger(repo_root, wrapper_root) as database:
        seeded_task(database)
        write_export(database, TASK)
    assert _git_binary("for-each-ref", "--format=%(refname)", ref, cwd=repo_root) == ""

    assert ledger_main(["--config", str(config), COMMAND_PIN_EXPORT, TASK]) == 0

    oid = _git_binary("hash-object", "--", str(exported), cwd=repo_root)
    assert _git_binary("rev-parse", "--verify", ref, cwd=repo_root) == oid
    with open_ledger(repo_root, wrapper_root) as reopened:
        assert export_oid(reopened, TASK) == oid


def test_pin_export_refuses_a_file_the_ledger_has_moved_past(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Stale bytes are not a pin: recovery re-pins, it does not resurrect.

    The crash `pin-export` recovers leaves a file the ledger still agrees
    with. A file written BEFORE more rows landed is a different claim: the oid
    would be recorded on a `tasks` row that can no longer produce those bytes,
    so the task's own record would contradict the blob it names (§3.6).
    """
    repo_root, _ = _git_repository(tmp_path)
    config, wrapper_root = _config_file(repo_root, tmp_path)
    ref = EXPORT_REF_TEMPLATE.format(task_id=TASK)
    with open_ledger(repo_root, wrapper_root) as database:
        seeded_task(database)
        write_export(database, TASK)
        # The ledger moves on: a second root of the same task, written after
        # the bytes were and before the interrupted pin could be retried.
        seeded_task(database)

    assert ledger_main(["--config", str(config), COMMAND_PIN_EXPORT, TASK]) == 2

    assert "exports now" in capsys.readouterr().err
    assert _git_binary("for-each-ref", "--format=%(refname)", ref, cwd=repo_root) == ""
    with open_ledger(repo_root, wrapper_root) as reopened:
        assert export_oid(reopened, TASK) is None


def test_pin_export_refuses_a_task_the_ledger_does_not_hold(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A pin is recorded ON a `tasks` row, so a task with no row cannot be pinned.

    Before this, the file was hashed, the ref was moved and the recording
    UPDATE matched nothing — the operator was told the export was pinned while
    the ledger went on saying the task owed one.
    """
    repo_root, _ = _git_repository(tmp_path)
    config, wrapper_root = _config_file(repo_root, tmp_path)
    with open_ledger(repo_root, wrapper_root) as database:
        seeded_task(database)
        exported = write_export(database, TASK)
    stray = export_path(repo_root, UNKNOWN_TASK)
    stray.write_bytes(exported.read_bytes())

    assert ledger_main(["--config", str(config), COMMAND_PIN_EXPORT, UNKNOWN_TASK]) == 2

    assert "no ledger rows exist" in capsys.readouterr().err
    unknown_ref = EXPORT_REF_TEMPLATE.format(task_id=UNKNOWN_TASK)
    assert (
        _git_binary("for-each-ref", "--format=%(refname)", unknown_ref, cwd=repo_root)
        == ""
    )


def test_pin_export_refuses_a_file_that_declares_another_task(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The header decides which task a file is an export OF, not the filename.

    A pin recorded from a file describing another task would point this task's
    row at a blob that rebuilds somebody else — found only when a restore did.
    """
    repo_root, _ = _git_repository(tmp_path)
    config, wrapper_root = _config_file(repo_root, tmp_path)
    ref = EXPORT_REF_TEMPLATE.format(task_id=TASK)
    with open_ledger(repo_root, wrapper_root) as database:
        seeded_task(database)
        seeded_task(database, OTHER_TASK)
        write_export(database, TASK)
        other = write_export(database, OTHER_TASK)
    export_path(repo_root, TASK).write_bytes(other.read_bytes())

    assert ledger_main(["--config", str(config), COMMAND_PIN_EXPORT, TASK]) == 2

    assert f"declares task {OTHER_TASK!r}" in capsys.readouterr().err
    assert _git_binary("for-each-ref", "--format=%(refname)", ref, cwd=repo_root) == ""
    with open_ledger(repo_root, wrapper_root) as reopened:
        assert export_oid(reopened, TASK) is None


def test_a_committed_export_imports_into_a_clone_at_another_path(
    tmp_path: Path,
) -> None:
    """§1.3: repository identity travels with the repository, not with its path.

    The clone is a different absolute path, so the old `repo_hash` header —
    `sha256` of that path — refused every committed export it was given. The
    `repo_id` in `.wf/repo-id` is committed with the export and answers the
    same question portably.
    """
    repo_root, wrapper_root = _git_repository(tmp_path)
    with open_ledger(repo_root, wrapper_root) as database:
        root_id = seeded_task(database)
        write_export(database, TASK)
    _git_binary(
        "add",
        "--",
        str(export_path(repo_root, TASK)),
        str(repo_id_path(repo_root)),
        cwd=repo_root,
    )
    _git_binary("commit", "--quiet", "-m", "export", cwd=repo_root)
    clone = tmp_path / "clone"
    _git_binary("clone", "--quiet", str(repo_root), str(clone), cwd=tmp_path)
    clone_wrapper = tmp_path / "clone-wrapper"
    clone_wrapper.mkdir()
    with open_ledger(clone, clone_wrapper):
        pass

    restored = import_export(
        export_path(clone, TASK),
        repo_root=clone,
        wrapper_root=clone_wrapper,
        ledger=ledger_path(clone),
    )

    assert restored == TASK
    with open_ledger(clone, clone_wrapper) as rebuilt:
        rows = rebuilt.connection.execute(
            "SELECT root_id FROM roots WHERE task_id = ?", (TASK,)
        ).fetchall()
    assert [str(row[0]) for row in rows] == [root_id]


def test_a_landed_task_round_trips_and_its_landing_rows_come_back(
    tmp_path: Path,
) -> None:
    """§1.2: the landing journal is exported, so a rebuild can read it again.

    The row is deleted before the import so that what the assertion proves is
    a RESTORE and not a survival: D17's fallback reads `landings` when the
    receipt file is gone, and a rebuild that dropped the row would leave the
    recovery path with nothing.
    """
    repo_root, wrapper_root = repository(tmp_path)
    intent = _landing_intent()
    with open_ledger(repo_root, wrapper_root) as database:
        seeded_task(database)
        journal = LandingJournal(database, TASK, BackendKind.LEDGER)
        journal.record(ATTEMPT, LandingPhase.INTENT, intent)
        export = write_export(database, TASK)
        as_exported = export.read_bytes()
        database.connection.execute("DELETE FROM landings")

    import_export(
        export,
        repo_root=repo_root,
        wrapper_root=wrapper_root,
        ledger=ledger_path(repo_root),
    )

    with open_ledger(repo_root, wrapper_root) as rebuilt:
        restored = LandingJournal(rebuilt, TASK, BackendKind.LEDGER).read(
            ATTEMPT, LandingPhase.INTENT, LandingIntent
        )
        again = write_export(rebuilt, TASK).read_bytes()
    assert restored == intent
    assert again == as_exported


def test_every_schema_table_is_exported_or_named_non_exported_with_a_reason() -> None:
    """A table in neither set is a defect this test refuses to let in silently.

    Derived from the schema the migrations actually create rather than from a
    hand-written list: §1's second defect was one table nobody listed, and a
    completeness check that restated the list would have missed it exactly as
    the two hand-lists did (R5).
    """
    exported = {table.value for table in EXPORT_TABLES}
    excluded = {table.value for table in NON_EXPORTED}

    assert exported.isdisjoint(excluded)
    assert set(table_columns()) == exported | excluded
    assert all(reason.strip() for reason in NON_EXPORTED.values())
    assert LedgerTable.LANDINGS.value in exported


def test_close_still_refuses_a_record_that_names_no_export_blob(
    fake_client: BdClient,
) -> None:
    """D5 stays until S2 derives `closed()` from the anchor instead (§3.6).

    The record's `export_oid` is the ONLY input to this refusal in S1, so
    eliding the column from the exported row must not touch it: a bead that
    closed on a record only `.wf/` held would close on bytes `git clean`
    deletes.
    """
    landed = (
        ContractorRecord.prepared(
            epic_id=EPIC_ID,
            stage_id=STAGE_ID,
            attempt=ATTEMPT,
            target_ref=TARGET_REF,
            expected_base_commit=BASE_COMMIT,
        )
        .admitted(ROOT_ID)
        .landed(ARTIFACT_OID, TREE_OID, GATE_RECEIPT, LANDING_RECEIPT)
    )
    unpinned = landed.model_copy(update={"state": ContractorState.CLOSED})

    with pytest.raises(ContractorAdapterError, match="export_oid"):
        ContractorAdapter(fake_client).close(STAGE_ID, unpinned, LANDING_RECEIPT)
