"""Closure is DERIVED and LATCHED, never stored (store-restructure §3.5, R6).

The highest-risk decision of the epic, so each property it rests on is one
test:

1. a crash between `write_export` and the ref pin leaves the task OPEN — no
   consumer reads it as closed, and the latch stays empty;
2. a shipped, exported, pinned task refuses `--retry`, which is the refusal a
   stored CLOSED used to carry;
3. a ledger deleted and rebuilt from the COMMITTED export in a fresh clone at
   another path derives `closed()` on first ask and latches it (archive is not
   clone-portable and never was — D19);
4. closure is MONOTONIC: neither a schema-version bump nor an attention write
   reopens a closed task, although either changes the bytes a re-export would
   produce;
5. an ABANDONED task is `retired()` — cleanup and archive proceed on what
   exists, succession does not;
6. nothing in the package writes `ContractorState.CLOSED` any more.

Real git throughout: every one of these is a statement about a blob, a ref or
a clone, and none of those can be faked.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path
from typing import Final

import pytest
from workflow_interpreter.ledger.closure import TaskClosure, closed, retired

from tests._fake_bd import FakeBd
from tests._gates import approval_payload, close
from tests._inspector import make_repo
from tests._ledger import TASK, ledger_store, seeded_task
from tests.conftest import Signer
from tests.test_ledger_writes import _open_gate
from workflow_interpreter.bdio import GateVerifier, SigningConfig
from workflow_interpreter.bdio.client import BdClient
from workflow_interpreter.bdio.constants import BackendKind
from workflow_interpreter.bdio.records import RootRecord
from workflow_interpreter.contractor import (
    ContractorAdapter,
    ContractorAdapterError,
    ContractorRecord,
)
from workflow_interpreter.contractor.journal import ExportPin
from workflow_interpreter.contractor.models import INSTANCE_KEY_TEMPLATE
from workflow_interpreter.contractor.verification import (
    CheckCommand,
    VerificationPolicy,
)
from workflow_interpreter.foreman.tick import cleanup_deferred
from workflow_interpreter.inspector.config import InspectorConfig
from workflow_interpreter.inspector.gitio import Git
from workflow_interpreter.inspector.sandbox import SandboxMode
from workflow_interpreter.ledger.archive import archive_task
from workflow_interpreter.ledger.constants import TaskState
from workflow_interpreter.ledger.database import LedgerDatabase, open_ledger
from workflow_interpreter.ledger.errors import LedgerExportError
from workflow_interpreter.ledger.export import export_task, import_export, write_export
from workflow_interpreter.ledger.paths import (
    export_path,
    ledger_path,
    repo_id_path,
)
from workflow_interpreter.ledger.reverify import (
    ExportAnchor,
    TrustAnchor,
    verify_export,
)
from workflow_interpreter.ledger.tasks import export_oid, record_task_state

EPIC_ID: Final[str] = "phase-1"
STAGE_ID: Final[str] = TASK
"""The contractor's stage IS the ledger's task: the closure probe is asked
about one id, and `adapter.close` pins the task named by the stage it closes."""
TARGET_REF: Final[str] = "refs/heads/main"
ROOT_ID: Final[str] = "contractor-root"
BASE_COMMIT: Final[str] = "a" * 40
ARTIFACT_OID: Final[str] = "b" * 40
TREE_OID: Final[str] = "c" * 40
GATE_RECEIPT: Final[str] = "gate-receipt"
LANDING_RECEIPT: Final[str] = "landing-receipt"
HOST: Final[str] = "derived-closed-test"
GIT_TIMEOUT_S: Final[float] = 30.0
_WRITES_CLOSED: Final[re.Pattern[str]] = re.compile(
    r"""["']?state["']?\s*[:=]\s*ContractorState\.CLOSED"""
)
"""A WRITE of the retired state: an assignment or a model update naming it.
Reads — `record.state is ContractorState.CLOSED` — stay legal, because a
record written before S2 still validates and still has to be recognised."""


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


def _landed_task(database: LedgerDatabase) -> str:
    """One task with rows, recorded as LANDED but not yet exported."""
    root_id = seeded_task(database)
    record_task_state(database, TASK, TaskState.LANDED)
    return root_id


def _contractor_root(database: LedgerDatabase, root_id: str) -> RootRecord:
    """The seeded root as a CONTRACTOR-owned one.

    Terminal cleanup reads the instance key off the root to learn whether the
    owning task closes through the contractor and therefore owes an export
    (§3.9); the seeded root is the same row with the other kind of key.
    """
    root = ledger_store(database).reads.load_root(root_id)
    return root.model_copy(
        update={
            "metadata": root.metadata.model_copy(
                update={
                    "instance_key": INSTANCE_KEY_TEMPLATE.format(
                        epic_id=EPIC_ID, stage_id=STAGE_ID, attempt=1
                    )
                }
            )
        }
    )


def _archivable(repo: Path, wrapper_root: Path, database: LedgerDatabase) -> str:
    """A settled root with one pinned ref and one run folder to lose."""
    root_id = f"{TASK}-a1"
    _git(
        repo,
        "update-ref",
        f"refs/wf/{root_id}/artifact/one",
        _git(repo, "rev-parse", "HEAD"),
    )
    (wrapper_root / root_id / "worktree").mkdir(parents=True, exist_ok=True)
    with database.transaction() as connection:
        connection.execute(
            "INSERT INTO roots (root_id, task_id, seq, attempt, backend, "
            "instance_key, terminal, status, metadata_json) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (root_id, TASK, 99, 1, "ledger", root_id, "shipped", "closed", "{}"),
        )
    return root_id


def _policy() -> VerificationPolicy:
    """One pinned check, so a record can carry a policy at all."""
    return VerificationPolicy.pin(
        (CheckCommand(name="source", argv=(sys.executable, "-c", "pass")),), Path.cwd()
    )


def _stored_record(fake_bd: FakeBd, state: str = "landed") -> ContractorRecord:
    """The stage's stored contractor record, at `state`, on the fake bead."""
    record = ContractorRecord.prepared(
        verification_policy=_policy(),
        epic_id=EPIC_ID,
        stage_id=STAGE_ID,
        attempt=1,
        target_ref=TARGET_REF,
        expected_base_commit=BASE_COMMIT,
    ).admitted(ROOT_ID)
    if state == "landed":
        record = record.landed(ARTIFACT_OID, TREE_OID, GATE_RECEIPT, LANDING_RECEIPT)
    fake_bd.rows[STAGE_ID] = {
        "id": STAGE_ID,
        "title": "stage",
        "status": "in_progress",
        "issue_type": "task",
        "parent": EPIC_ID,
        "metadata": {"contractor": record.model_dump(by_alias=True, mode="json")},
    }
    return record


def _succession(
    fake_client: BdClient, database: LedgerDatabase, git: Git, stored: ContractorRecord
) -> ContractorAdapter:
    """An adapter that can answer the closure question, ready for a retry."""
    adapter = ContractorAdapter(fake_client)
    adapter.closure = TaskClosure(database, git)
    return adapter


def test_a_crash_between_the_export_and_the_pin_leaves_the_task_open(
    tmp_path: Path, fake_bd: FakeBd, fake_client: BdClient
) -> None:
    """§3.5: nothing anchors those bytes, so nothing may read them as closed.

    The one window `ExportPin` cannot make atomic — the file is written and
    the process dies before `refs/wf/exports/<task>` names its blob. The task
    is LANDED and its export is sitting in the checkout, and that is not
    closure: succession, cleanup and archive must all behave as they would for
    a task that never exported at all, and the latch must stay empty so the
    next ask derives again.
    """
    repo, wrapper_root, git = _lab(tmp_path)
    stored = _stored_record(fake_bd)
    with open_ledger(repo, wrapper_root) as database:
        root_id = _landed_task(database)
        write_export(database, TASK)
        adapter = _succession(fake_client, database, git, stored)

        assert closed(database, git, TASK) is False
        assert retired(database, git, TASK) is False
        assert export_oid(database, TASK) is None
        assert cleanup_deferred(
            _contractor_root(database, root_id), ledger=database, git=git, task_id=TASK
        )
        with pytest.raises(ContractorAdapterError, match="landed"):
            adapter.prepare(STAGE_ID, stored.next_attempt())
        _archivable(repo, wrapper_root, database)
        with pytest.raises(LedgerExportError, match="not retired"):
            archive_task(
                git,
                database,
                TASK,
                bundle=tmp_path / "bundles" / f"{TASK}.bundle",
                repo_root=repo,
                wrapper_root=wrapper_root,
            )


def test_a_shipped_exported_and_pinned_task_refuses_a_retry(
    tmp_path: Path, fake_bd: FakeBd, fake_client: BdClient
) -> None:
    """The refusal a stored CLOSED used to carry, now carried by `closed()`.

    Nothing writes CLOSED after S2, so the succession guard that read it is
    dead vocabulary; the task's record being durable in git is what refuses a
    second attempt at work that already shipped.
    """
    repo, wrapper_root, git = _lab(tmp_path)
    stored = _stored_record(fake_bd)
    with open_ledger(repo, wrapper_root) as database:
        _landed_task(database)
        ExportPin(database, git, repo).pin(TASK, BackendKind.LEDGER)
        adapter = _succession(fake_client, database, git, stored)

        assert closed(database, git, TASK) is True
        with pytest.raises(ContractorAdapterError, match="closed"):
            adapter.prepare(STAGE_ID, stored.next_attempt())


def test_a_ledger_rebuilt_in_a_clone_derives_closed_on_first_ask_and_latches(
    tmp_path: Path, signing_config: SigningConfig, sign_payload: Signer
) -> None:
    """§3.5 and §3.9: the committed export is the whole record, in any clone.

    The ledger is per-checkout working state; a task that closed is rebuilt
    from the file the orchestrator committed, at a path the exporting checkout
    never saw. `closed()` cannot be read from a rebuilt row — the latch is
    elided from the export — so it is DERIVED, once, against the blob the
    landed history carries, and written back so no later read has to ask git
    again. Archive is deliberately not asserted: it bundles `refs/wf/<root>/*`,
    which a default clone does not fetch (D19).
    """
    origin, wrapper_root, _ = _lab(tmp_path, "origin")
    with open_ledger(origin, wrapper_root) as database:
        store = ledger_store(
            database, verifier=GateVerifier(signing_config, database.repo_root)
        )
        root_id, gate_id = _open_gate(store)
        gate = store.reads.load_gate(gate_id)
        close(store, root_id, gate, approval_payload(root_id, gate), sign_payload)
        record_task_state(database, TASK, TaskState.LANDED)
        write_export(database, TASK)
    _git(origin, "add", "--", str(export_path(origin, TASK)), str(repo_id_path(origin)))
    _git(origin, "commit", "--quiet", "-m", "land: the task and its export")

    clone = tmp_path / "clone"
    _git(tmp_path, "clone", "--quiet", str(origin), str(clone))
    clone_wrapper = tmp_path / "clone-wrapper"
    clone_wrapper.mkdir()
    clone_git = _seam(clone, clone_wrapper)
    with open_ledger(clone, clone_wrapper):
        pass
    import_export(
        export_path(clone, TASK),
        repo_root=clone,
        wrapper_root=clone_wrapper,
        ledger=ledger_path(clone),
    )

    verdict = verify_export(
        export_path(clone, TASK),
        TASK,
        TrustAnchor(
            repo_root=clone, allowed_signers=signing_config.allowed_signers_path
        ),
    )

    assert verdict.accepted, verdict.reasons
    assert verdict.anchor is ExportAnchor.COMMITTED
    with open_ledger(clone, clone_wrapper) as rebuilt:
        assert export_oid(rebuilt, TASK) is None, "the latch is not exported"

        assert closed(rebuilt, clone_git, TASK) is True

        assert export_oid(rebuilt, TASK) == verdict.pinned_oid
        assert not cleanup_deferred(
            _contractor_root(rebuilt, root_id),
            ledger=rebuilt,
            git=clone_git,
            task_id=TASK,
        )


def test_a_closed_task_stays_closed_under_a_schema_bump_and_an_attention_write(
    tmp_path: Path,
) -> None:
    """R6, the reason closure is a LATCH rather than a recomputation.

    A live re-export is a function of mutable state: the header carries the
    schema version and `projections` is exported. Recomputing closure from one
    would reopen every closed task the next migration or attention drain
    touched — which the first assertion below proves is not hypothetical, by
    showing the very bytes an anchor was taken over are no longer the bytes
    this ledger would produce.
    """
    repo, wrapper_root, git = _lab(tmp_path)
    with open_ledger(repo, wrapper_root) as database:
        _landed_task(database)
        anchored = ExportPin(database, git, repo).pin(TASK, BackendKind.LEDGER)
        as_pinned = export_task(database, TASK)
        assert closed(database, git, TASK) is True

        with database.transaction() as connection:
            connection.execute(
                "UPDATE meta SET value = ? WHERE key = 'schema_version'", ("99",)
            )
            connection.execute(
                "INSERT INTO projections (task_id, generation, created_at) "
                "VALUES (?, ?, ?)",
                (TASK, 1, "2026-09-19T00:00:00+00:00"),
            )

        assert export_task(database, TASK) != as_pinned
        assert closed(database, git, TASK) is True
        assert retired(database, git, TASK) is True
        assert export_oid(database, TASK) == anchored


def test_an_abandoned_task_is_retired_and_never_closed(
    tmp_path: Path, fake_bd: FakeBd, fake_client: BdClient
) -> None:
    """§3.5 and §3.8: cleanup and archive proceed on what exists; retry does not.

    An abandoned task never exports, so a cleanup gated on closure alone would
    defer its worktree forever and archive could never retire its refs. It is
    still not CLOSED: the work did not ship, and succession is refused for the
    same reason it is refused for a task that did.
    """
    repo, wrapper_root, git = _lab(tmp_path)
    stored = _stored_record(fake_bd, state="admitted")
    with open_ledger(repo, wrapper_root) as database:
        root_id = seeded_task(database)
        record_task_state(database, TASK, TaskState.ABANDONED)
        adapter = _succession(fake_client, database, git, stored)

        assert closed(database, git, TASK) is False
        assert retired(database, git, TASK) is True
        assert not cleanup_deferred(
            _contractor_root(database, root_id), ledger=database, git=git, task_id=TASK
        )
        with pytest.raises(ContractorAdapterError, match="retired"):
            adapter.prepare(STAGE_ID, stored.next_attempt())
        archived_root = _archivable(repo, wrapper_root, database)
        result = archive_task(
            git,
            database,
            TASK,
            bundle=tmp_path / "bundles" / f"{TASK}.bundle",
            repo_root=repo,
            wrapper_root=wrapper_root,
        )

    assert result.refs == (f"refs/wf/{archived_root}/artifact/one",)
    assert not (wrapper_root / archived_root).exists()


def test_no_producer_writes_the_closed_contractor_state() -> None:
    """§3.5: CLOSED is read-compatible vocabulary, and nothing may write it.

    The whole design rests on closure being derived; one surviving producer
    would put a stored CLOSED back in a record the export carries, which is
    exactly the conflict §1 names — either it violates D5 or it is lost on
    rebuild.
    """
    package = Path(__file__).resolve().parents[1] / "workflow_interpreter"

    writers = tuple(
        f"{path.relative_to(package)}:{number}"
        for path in sorted(package.rglob("*.py"))
        for number, line in enumerate(
            path.read_text(encoding="utf-8").splitlines(), start=1
        )
        if _WRITES_CLOSED.search(line)
    )

    assert writers == ()
