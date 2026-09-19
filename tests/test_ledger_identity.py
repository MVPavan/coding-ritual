"""Identity: minted task ids, one grammar, epic as an input, attempt from the carrier.

The S3 acceptance family (store-restructure §3.7, R8). What is proved here is
that every boundary an id crosses — a git refname, a path component, the run
directory, `WF_TASK_ID` as `scripts/verify-debrief.sh` re-expands it — holds
the id the ledger minted, and that the two forms git refuses (`a..b`,
`foo.lock`) are refused BY NAME before any ref, path or row exists.

The shell side is exercised through the real script rather than a restatement
of its `case` glob: an identity bug there is a containment bug, so the test
that would catch one has to run what the wrapper runs.
"""

from __future__ import annotations

import os
import subprocess
from collections.abc import Iterator
from pathlib import Path
from typing import Final

import pytest
from pydantic import ValidationError

from tests._bdio import RESOLVED_CONFIG, load_definition
from tests._ledger import ledger_store, repository
from workflow_interpreter.bdio.api import WorkflowStore
from workflow_interpreter.contracts.run_identity import (
    InvalidIdentifier,
    RunIdentity,
    safe_component,
)
from workflow_interpreter.foreman.identifiers import validate_bead_id
from workflow_interpreter.ledger.constants import TrackerKind
from workflow_interpreter.ledger.database import LedgerDatabase, open_ledger
from workflow_interpreter.ledger.errors import LedgerEpicMissing
from workflow_interpreter.ledger.identity import mint_task

EPIC: Final[str] = "store-restructure"
TASK: Final[str] = "cr-nwy9.3"
EPIC_OF_TASK: Final[str] = "cr-nwy9"
GIT_TIMEOUT_S: Final[float] = 30.0
GIT_HOSTILE: Final[tuple[str, ...]] = ("a..b", "foo.lock")
"""Both pass a `[A-Za-z0-9][A-Za-z0-9._-]*` charset and both are refused by
`git check-ref-format` under `refs/wf/exports/<id>` — which is why the grammar
has to say so itself."""

_VERIFY_DEBRIEF: Final[Path] = (
    Path(__file__).resolve().parents[1] / "scripts" / "verify-debrief.sh"
)
_IDENTITY_FAILURE: Final[str] = "FAIL debrief-identity"
_PACKAGE: Final[Path] = Path(__file__).resolve().parents[1] / "workflow_interpreter"


@pytest.fixture
def ledger(tmp_path: Path) -> Iterator[LedgerDatabase]:
    """An open ledger over a fresh repository, closed with the test."""
    repo_root, wrapper_root = repository(tmp_path)
    with open_ledger(repo_root, wrapper_root) as database:
        yield database


def _git(repo: Path, *args: str) -> str:
    """One git command in a throwaway repository."""
    return (
        subprocess.check_output(
            ["git", *args], cwd=repo, timeout=GIT_TIMEOUT_S, stderr=subprocess.STDOUT
        )
        .decode()
        .strip()
    )


def _refname_accepted(candidate: str) -> bool:
    """Whether git itself would let this name be a ref."""
    return (
        subprocess.run(
            ["git", "check-ref-format", f"refs/wf/exports/{candidate}"],
            capture_output=True,
            timeout=GIT_TIMEOUT_S,
            check=False,
        ).returncode
        == 0
    )


@pytest.fixture
def identity_repo(tmp_path: Path) -> tuple[Path, str]:
    """A repository with one commit, for running the real debrief check in."""
    repo = tmp_path / "shell-repo"
    repo.mkdir()
    _git(repo, "init", "--quiet")
    _git(repo, "config", "user.email", "lab@example.com")
    _git(repo, "config", "user.name", "lab")
    (repo / "README.md").write_text("lab\n", encoding="utf-8")
    _git(repo, "add", "README.md")
    _git(repo, "commit", "--quiet", "-m", "base")
    return repo, _git(repo, "rev-parse", "HEAD")


def _debrief_identity(
    repo: Path, base: str, *, task_id: str, epic_id: str
) -> subprocess.CompletedProcess[str]:
    """Run the real verifier with one identity and nothing else staged."""
    return subprocess.run(
        [str(_VERIFY_DEBRIEF)],
        cwd=repo,
        capture_output=True,
        text=True,
        timeout=GIT_TIMEOUT_S,
        check=False,
        env={
            **os.environ,
            "WF_BASE_COMMIT": base,
            "WF_EPIC_SEGMENT": epic_id,
            "WF_TASK_ID": task_id,
            "WF_ATTEMPT": "1",
            "WF_RENDER_OID": "",
            "WF_RENDER_DIGEST": "",
        },
    )


def _tasks(database: LedgerDatabase) -> tuple[tuple[str, str, str, str], ...]:
    """Every `tasks` row as (task_id, epic_id, tracker_ref, tracker_kind)."""
    with database.locked() as connection:
        rows = connection.execute(
            "SELECT task_id, epic_id, tracker_ref, tracker_kind FROM tasks"
        ).fetchall()
    return tuple((str(row[0]), str(row[1]), str(row[2]), str(row[3])) for row in rows)


def _roots(database: LedgerDatabase) -> dict[str, tuple[int, str | None]]:
    """Every root of this ledger as id -> (attempt, parent_root_id)."""
    with database.locked() as connection:
        rows = connection.execute(
            "SELECT root_id, attempt, parent_root_id FROM roots"
        ).fetchall()
    return {
        str(row[0]): (int(row[1]), None if row[2] is None else str(row[2]))
        for row in rows
    }


# --- 1. minting ------------------------------------------------------------


@pytest.mark.parametrize(
    ("tracker_ref", "tracker_kind"),
    [("PROJ-12", TrackerKind.JIRA), ("gh#123", TrackerKind.GITHUB)],
)
def test_a_tracker_ref_mints_an_id_every_boundary_can_hold(
    ledger: LedgerDatabase,
    identity_repo: tuple[Path, str],
    tmp_path: Path,
    tracker_ref: str,
    tracker_kind: TrackerKind,
) -> None:
    """`gh#123` is not path-safe; what the ledger mints for it must be."""
    repo, base = identity_repo

    task_id = mint_task(
        ledger, tracker_ref=tracker_ref, tracker_kind=tracker_kind, epic_id=EPIC
    )

    assert safe_component(task_id) == task_id
    assert _refname_accepted(task_id)
    worktree = tmp_path / "worktrees" / task_id
    assert worktree.parent == tmp_path / "worktrees"
    identity = RunIdentity(task_id=task_id, attempt=1, epic_id=EPIC)
    assert identity.run_directory == f"docs/workstreams/{EPIC}/runs/{task_id}/a1"
    shell = _debrief_identity(repo, base, task_id=task_id, epic_id=EPIC)
    assert _IDENTITY_FAILURE not in shell.stdout


@pytest.mark.parametrize(
    ("tracker_ref", "tracker_kind"),
    [("PROJ-12", TrackerKind.JIRA), ("gh#123", TrackerKind.GITHUB)],
)
def test_the_minted_row_holds_the_foreign_id_uniquely(
    ledger: LedgerDatabase, tracker_ref: str, tracker_kind: TrackerKind
) -> None:
    """The tracker's id is a column, not the key — and minting twice is once."""
    task_id = mint_task(
        ledger, tracker_ref=tracker_ref, tracker_kind=tracker_kind, epic_id=EPIC
    )

    again = mint_task(
        ledger, tracker_ref=tracker_ref, tracker_kind=tracker_kind, epic_id=EPIC
    )

    assert again == task_id
    assert _tasks(ledger) == ((task_id, EPIC, tracker_ref, tracker_kind.value),)


def test_two_tracker_refs_that_sanitise_alike_get_distinct_ids(
    ledger: LedgerDatabase,
) -> None:
    """A suffix inside the minting transaction, never a silent collision."""
    first = mint_task(
        ledger, tracker_ref="gh#123", tracker_kind=TrackerKind.GITHUB, epic_id=EPIC
    )

    second = mint_task(
        ledger, tracker_ref="gh!123", tracker_kind=TrackerKind.GITHUB, epic_id=EPIC
    )

    assert first != second
    assert safe_component(second) == second
    assert _refname_accepted(second)


def test_a_bead_id_is_minted_as_itself(ledger: LedgerDatabase) -> None:
    """For bd, `task_id == tracker_ref`: no existing id, ref or `WF_*` moves."""
    task_id = mint_task(
        ledger, tracker_ref=TASK, tracker_kind=TrackerKind.BD, epic_id=EPIC_OF_TASK
    )

    assert task_id == TASK


# --- 2. one grammar --------------------------------------------------------


@pytest.mark.parametrize("value", GIT_HOSTILE)
def test_git_refuses_what_the_charset_alone_would_allow(value: str) -> None:
    """The premise: both forms are refused by git under an export ref."""
    assert not _refname_accepted(value)


@pytest.mark.parametrize("value", GIT_HOSTILE)
def test_a_git_hostile_component_is_refused_by_name(value: str) -> None:
    """One grammar, so the refusal is the same wherever the id is stated."""
    with pytest.raises(InvalidIdentifier) as refusal:
        safe_component(value)
    assert value in str(refusal.value)

    with pytest.raises(InvalidIdentifier):
        validate_bead_id(value)


@pytest.mark.parametrize("value", GIT_HOSTILE)
def test_the_record_refuses_a_hostile_task_or_epic(value: str) -> None:
    """Both path components are under the same grammar (§3.7)."""
    with pytest.raises(ValidationError):
        RunIdentity(task_id=value, attempt=1, epic_id=EPIC)

    with pytest.raises(ValidationError):
        RunIdentity(task_id=TASK, attempt=1, epic_id=value)


@pytest.mark.parametrize("value", GIT_HOSTILE)
def test_a_hostile_epic_is_refused_before_a_row_exists(
    ledger: LedgerDatabase, value: str
) -> None:
    """Refused by name at mint, with nothing written to roll back."""
    with pytest.raises(InvalidIdentifier):
        mint_task(ledger, tracker_ref=TASK, tracker_kind=TrackerKind.BD, epic_id=value)

    assert _tasks(ledger) == ()


@pytest.mark.parametrize("value", GIT_HOSTILE)
def test_the_shell_side_refuses_the_same_two_forms(
    identity_repo: tuple[Path, str], value: str
) -> None:
    """`verify-debrief.sh` re-applies the rule to the task AND the epic."""
    repo, base = identity_repo

    as_task = _debrief_identity(repo, base, task_id=value, epic_id=EPIC)
    as_epic = _debrief_identity(repo, base, task_id=TASK, epic_id=value)

    assert as_task.returncode != 0
    assert _IDENTITY_FAILURE in as_task.stdout
    assert as_epic.returncode != 0
    assert _IDENTITY_FAILURE in as_epic.stdout


def test_an_existing_bead_shaped_id_still_passes(
    identity_repo: tuple[Path, str],
) -> None:
    """Tightening the grammar moves no id that exists today."""
    repo, base = identity_repo

    assert safe_component(TASK) == TASK
    assert validate_bead_id(TASK) == TASK
    assert _refname_accepted(TASK)
    shell = _debrief_identity(repo, base, task_id=TASK, epic_id=EPIC_OF_TASK)
    assert _IDENTITY_FAILURE not in shell.stdout


# --- 3. epic is an input ---------------------------------------------------


def test_the_epic_written_is_the_epic_given(ledger: LedgerDatabase) -> None:
    """`tasks.epic_id` is the mint input, never a parse of the task id."""
    task_id = mint_task(
        ledger, tracker_ref=TASK, tracker_kind=TrackerKind.BD, epic_id=EPIC
    )

    assert _tasks(ledger) == ((task_id, EPIC, TASK, TrackerKind.BD.value),)


def test_an_undotted_task_gets_the_epic_it_was_given(
    ledger: LedgerDatabase,
) -> None:
    """A task id with no dot is not its own epic unless it was named as one."""
    task_id = mint_task(
        ledger, tracker_ref="PROJ-12", tracker_kind=TrackerKind.JIRA, epic_id=EPIC
    )

    assert _tasks(ledger) == ((task_id, EPIC, "PROJ-12", TrackerKind.JIRA.value),)
    assert (
        RunIdentity(task_id=task_id, attempt=2, epic_id=EPIC).run_directory
        == f"docs/workstreams/{EPIC}/runs/{task_id}/a2"
    )


def test_nothing_derives_an_epic_from_an_id_any_more() -> None:
    """The probe R8 names: `epic_segment` is gone from the engine."""
    holders = [
        path
        for path in _PACKAGE.rglob("*.py")
        if "epic_segment" in path.read_text(encoding="utf-8")
    ]

    assert holders == []


# --- 4. the lazy path ------------------------------------------------------


def test_the_lazy_task_row_refuses_without_an_epic(
    ledger: LedgerDatabase,
) -> None:
    """A run that never went through prepare has no epic to write, and says so."""
    store = ledger_store(ledger, TASK, epic_id=None)

    with pytest.raises(LedgerEpicMissing) as refusal:
        store.create_root(
            instance_key="lazy-1",
            definition=load_definition(),
            resolved_config=RESOLVED_CONFIG,
        )

    assert TASK in str(refusal.value)
    assert _tasks(ledger) == ()


def test_a_prepared_task_needs_no_epic_on_the_lazy_path(
    ledger: LedgerDatabase,
) -> None:
    """The refusal is about minting a row, not about every later write."""
    mint_task(ledger, tracker_ref=TASK, tracker_kind=TrackerKind.BD, epic_id=EPIC)
    store = ledger_store(ledger, TASK, epic_id=None)

    root = store.create_root(
        instance_key="prepared-1",
        definition=load_definition(),
        resolved_config=RESOLVED_CONFIG,
        run_identity=RunIdentity(task_id=TASK, attempt=1, epic_id=EPIC),
    )

    assert root.root_id == f"{TASK}-a1"
    assert _tasks(ledger) == ((TASK, EPIC, TASK, TrackerKind.BD.value),)


# --- 5. attempt from the carrier -------------------------------------------


def _root(
    store: WorkflowStore, instance_key: str, identity: RunIdentity | None = None
) -> str:
    """One root of the lab task under `instance_key`, pinned or not."""
    return store.create_root(
        instance_key=instance_key,
        definition=load_definition(),
        resolved_config=RESOLVED_CONFIG,
        run_identity=identity,
    ).root_id


def test_attempt_roots_take_their_number_from_the_carrier(
    ledger: LedgerDatabase,
) -> None:
    """The count of roots is no longer what names an attempt (§3.7)."""
    store = ledger_store(ledger, TASK, epic_id=EPIC)
    first = _root(store, "a1", RunIdentity(task_id=TASK, attempt=1, epic_id=EPIC))

    decision = _root(store, "decision-1")
    replacement = _root(store, "replacement-1")
    second = _root(store, "a2", RunIdentity(task_id=TASK, attempt=2, epic_id=EPIC))

    assert first == f"{TASK}-a1"
    assert decision == f"{TASK}-a1-c1"
    assert replacement == f"{TASK}-a1-c2"
    assert second == f"{TASK}-a2"


def test_a_child_root_records_the_attempt_root_it_hangs_off(
    ledger: LedgerDatabase,
) -> None:
    """`parent_root_id` is what makes two roots of one task readable."""
    store = ledger_store(ledger, TASK, epic_id=EPIC)
    _root(store, "a1", RunIdentity(task_id=TASK, attempt=1, epic_id=EPIC))

    _root(store, "decision-1")
    _root(store, "replacement-1")

    assert _roots(ledger) == {
        f"{TASK}-a1": (1, None),
        f"{TASK}-a1-c1": (1, f"{TASK}-a1"),
        f"{TASK}-a1-c2": (1, f"{TASK}-a1"),
    }


def test_the_natural_key_neither_collides_nor_resolves_to_the_first(
    ledger: LedgerDatabase,
) -> None:
    """A second child is its own root; a re-create of one IS the same root."""
    store = ledger_store(ledger, TASK, epic_id=EPIC)
    _root(store, "a1", RunIdentity(task_id=TASK, attempt=1, epic_id=EPIC))
    first_child = _root(store, "decision-1")
    second_child = _root(store, "replacement-1")

    again = _root(store, "decision-1")

    assert first_child != second_child
    assert again == first_child
    assert set(_roots(ledger)) == {
        f"{TASK}-a1",
        first_child,
        second_child,
    }


def test_children_of_a_later_attempt_start_from_one(
    ledger: LedgerDatabase,
) -> None:
    """`m` is minted per attempt, so attempt two's first child is `-a2-c1`."""
    store = ledger_store(ledger, TASK, epic_id=EPIC)
    _root(store, "a1", RunIdentity(task_id=TASK, attempt=1, epic_id=EPIC))
    _root(store, "decision-1")
    _root(store, "a2", RunIdentity(task_id=TASK, attempt=2, epic_id=EPIC))

    child = _root(store, "decision-2")

    assert child == f"{TASK}-a2-c1"
