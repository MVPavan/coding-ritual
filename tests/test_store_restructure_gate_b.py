"""The five seams gate B found unheld (store-restructure, epic cr-nwy9).

One test per finding, each stating the failure it refuses rather than the code
it covers:

1. a `Close` lost with the outbox — the ledger deleted and rebuilt — is
   re-derived from the restored `closed()` by `wf ledger reconcile`, once;
2. a contractor transition survives a rebuild, because the checkpoint anchors
   the CONTRACTOR's facts and not only the foreman's — and an abandon after
   such a rebuild still refuses mid-landing, on the wrapper intent file;
3. R12's quiesce probe is a cost of CREATING and ADMITTING, never of a tick or
   an inspector spawn: the run loop stays tracker-free (R4, ADR 0006);
4. an abandoned mid-run task settles its roots, so `wf ledger archive` can
   reclaim its refs;
5. every `wf ledger` verb puts the id it is given through the ONE identifier
   grammar, at the CLI boundary, before a path or a lock is built (invariant G).
"""

from __future__ import annotations

import argparse
import subprocess
from collections.abc import Sequence
from pathlib import Path
from typing import Final

import pytest

from tests._inspector import make_repo
from tests._ledger import EPIC, TASK, config_file, seeded_task
from tests.test_derived_closed import _record, _seed_record
from workflow_interpreter.contractor import tracker_wiring
from workflow_interpreter.contractor.quiesce import NotQuiesced
from workflow_interpreter.contractor.tracker_wiring import repair_mirror
from workflow_interpreter.foreman import __main__ as foreman_main
from workflow_interpreter.foreman.config import (
    ForemanConfig,
    load_config,
    wrapper_root_for,
)
from workflow_interpreter.inspector.config import InspectorConfig
from workflow_interpreter.inspector.gitio import Git
from workflow_interpreter.inspector.sandbox import SandboxMode
from workflow_interpreter.ledger.__main__ import COMMAND_RECONCILE
from workflow_interpreter.ledger.__main__ import main as ledger_main
from workflow_interpreter.ledger.checkpoint import rebuild_sources
from workflow_interpreter.ledger.closure import closed
from workflow_interpreter.ledger.constants import TaskState
from workflow_interpreter.ledger.database import open_ledger
from workflow_interpreter.ledger.export import import_exports, pin_export, write_export
from workflow_interpreter.ledger.paths import ledger_path, repo_id_path
from workflow_interpreter.ledger.tasks import record_task_state
from workflow_interpreter.tracker.bd import BdTracker
from workflow_interpreter.tracker.bd_transport import (
    BdClient,
    BdConfig,
    CompletedCommand,
)
from workflow_interpreter.tracker.constants import WorkItemStatus
from workflow_interpreter.tracker.file import FileTracker
from workflow_interpreter.tracker.intents import Close, TrackerIntent, TrackerResult
from workflow_interpreter.tracker.models import TrackerRef, WorkItem
from workflow_interpreter.tracker.outbox import TrackerOutbox

EXIT_REFUSED: Final[int] = 2
ESCAPING_ID: Final[str] = "../x"
"""An operator-supplied id that leaves the directory its verb derives paths in."""
HOST: Final[str] = "gate-b-test"
GIT_TIMEOUT_S: Final[float] = 60.0


def test_a_ledger_verb_refuses_an_escaping_task_id_before_it_builds_a_path(
    tmp_path: Path,
) -> None:
    """Invariant G: the grammar is applied where the id ENTERS, not downstream.

    `wf ledger reconcile ../x` used to reach `task_lock_path`, and the fence
    then created `<wrapper_root>/tasks/../x.lock` — a lock file outside the
    wrapper root, made by an operator typo. The foreman CLI has always
    validated its ids; the ledger CLI validated nothing.
    """
    config, _repo_root, wrapper_root = config_file(tmp_path)

    assert ledger_main(["--config", str(config), COMMAND_RECONCILE, ESCAPING_ID]) == (
        EXIT_REFUSED
    )
    assert not (wrapper_root.parent / "x.lock").exists()
    assert not (wrapper_root / "tasks").exists(), "no path was built at all"


class _CountingTransport:
    """The bd TRANSPORT, counted: every subprocess this composition would run.

    On the transport rather than on the port (gate B, finding 3): the existing
    "no tracker call inside a tick" test decorates the PORT, and the R12
    quiesce probe reaches past it — `legacy_metadata` is a transport read no
    port method names — so a port counter could not see it.

    It never answers. A probe that runs at all therefore refuses by name, which
    is what makes "did it run?" a fact rather than an absence.
    """

    def __init__(self) -> None:
        self.calls: list[tuple[str, ...]] = []

    def __call__(self, argv: Sequence[str], timeout_s: float) -> CompletedCommand:
        """Record the command, then time out as an unreachable bd would."""
        self.calls.append(tuple(argv))
        raise subprocess.TimeoutExpired(list(argv), timeout_s)


def _args(config: Path, command: str, **extra: object) -> argparse.Namespace:
    """The parsed arguments one foreman invocation composes from."""
    return argparse.Namespace(
        config=config, task=TASK, epic=EPIC, command=command, **extra
    )


def test_the_quiesce_probe_is_a_cost_of_admitting_not_of_running(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """R4 and ADR 0006: nothing past admission touches the tracker.

    `assert_quiesced` ran in `_composition`, which every command composes
    through — so each detached inspector spawn and each tick did one `bd show`
    on the activation's critical path, and an unreachable bd failed the
    activation before `run_wrapper` was ever reached. The probe belongs to the
    commands that CREATE or ADMIT a root; `wf contract` still pays it (and
    `contractor.command` asks it again over the adapter's own port).
    """
    config, _repo_root, _wrapper_root = config_file(tmp_path)
    transport = _CountingTransport()
    tracker = BdTracker(BdClient(BdConfig(workspace=tmp_path, actor="test"), transport))
    monkeypatch.setattr(foreman_main, "tracker_for", lambda _settings: tracker)

    for command, extra in (
        ("inspector", {"root_id": "r", "activation_id": "a"}),
        ("tick", {"root_id": "r"}),
    ):
        composition = foreman_main._composition(_args(config, command, **extra))
        assert composition.ledger is not None
        composition.ledger.close()

    assert transport.calls == [], "a run-loop command contacted the tracker"

    with pytest.raises(NotQuiesced):
        foreman_main._composition(
            _args(config, "contract", epic_id=EPIC, stage_id=TASK)
        )

    assert transport.calls, "an admitting command still pays for the probe"


class _CountingFileTracker(FileTracker):
    """A file tracker that counts the closes it is ASKED for.

    A repaired mirror must close the item once, so "how many `Close` intents
    reached the tracker" is the question — a second one would be a mirror
    write for a state the mirror is already in.
    """

    def __init__(self, path: Path) -> None:
        super().__init__(path)
        self.closes = 0

    def apply(self, intent: TrackerIntent) -> TrackerResult:
        """Count a close, then let the real document answer it."""
        if isinstance(intent, Close):
            self.closes += 1
        return super().apply(intent)


def _git(repo: Path, *args: str) -> None:
    """One git command in `repo`, with an explicit timeout."""
    subprocess.run(
        ("git", *args),
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
        timeout=GIT_TIMEOUT_S,
    )


def _file_tracker_config(tmp_path: Path, repo: Path, document: Path) -> ForemanConfig:
    """A foreman config whose tracker is one JSON document, loaded from TOML.

    Loaded rather than constructed, because `repair_mirror` is reached from
    `wf ledger reconcile`, which reads exactly this file.
    """
    path = tmp_path / "foreman.toml"
    home = tmp_path / "home"
    path.write_text(
        f'''repo_root = "{repo}"
wrapper_home = "{home}"
host = "{HOST}"
actor = "actor"

[tracker]
backend = "file"
path = "{document}"

[inspector]
repo_root = "{repo}"
wrapper_root = "{wrapper_root_for(home, repo)}"
host = "{HOST}"
sandbox = "off"
''',
        encoding="utf-8",
    )
    return load_config(path)


def test_a_close_lost_with_the_outbox_is_re_derived_by_reconcile(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """§3.4 and §3.9: the documented remedy has to actually re-derive the Close.

    `tracker_outbox` is not exported, so a rebuild from a checkpoint or a
    committed export loses every pending mirror row. `closed()` comes back
    true, the item is still open, and `wf ledger reconcile` used to print
    "nothing due" — leaving the bead open forever from the one command the
    guide names as the repair. The re-derivation is idempotent against the
    item's own state, so repairing twice closes once.
    """
    repo = make_repo(tmp_path, "repo")
    wrapper_root = wrapper_root_for(tmp_path / "home", repo)
    wrapper_root.mkdir(parents=True, exist_ok=True)
    git = Git(
        InspectorConfig(
            repo_root=repo,
            wrapper_root=wrapper_root,
            host=HOST,
            sandbox=SandboxMode.OFF,
        )
    )
    with open_ledger(repo, wrapper_root) as database:
        seeded_task(database)
        _seed_record(database, _record())
        record_task_state(database, TASK, TaskState.LANDED)
        export = write_export(database, TASK)
        pin_export(git, database, TASK, repo)
    _git(repo, "add", "--", str(export), str(repo_id_path(repo)))
    _git(repo, "commit", "--quiet", "-m", "land: the task and its export")

    # The loss: the ledger, and with it the pending `Close`, is gone.
    ledger_path(repo).unlink()
    with open_ledger(repo, wrapper_root):
        pass
    import_exports(
        rebuild_sources(git, repo, ()),
        repo_root=repo,
        wrapper_root=wrapper_root,
        ledger=ledger_path(repo),
    )

    document = tmp_path / "tracker.json"
    tracker = _CountingFileTracker(document)
    tracker.upsert(
        WorkItem(ref=TASK, title="the task", brief=None, status=WorkItemStatus.OPEN)
    )
    monkeypatch.setattr(
        tracker_wiring, "tracker_for", lambda _settings, client=None: tracker
    )
    config = _file_tracker_config(tmp_path, repo, document)
    ref = TrackerRef(kind=tracker.kind, ref=TASK)

    with open_ledger(repo, wrapper_root) as rebuilt:
        assert closed(rebuilt, git, TASK) is True
        assert TrackerOutbox(rebuilt).pending() == (), "the rebuild lost the row"

        repair_mirror(config, rebuilt, git, TASK)
        item = tracker.get(ref)
        assert item is not None and item.status is WorkItemStatus.CLOSED

        repair_mirror(config, rebuilt, git, TASK)

        assert tracker.closes == 1, "a repaired mirror closes the item once"
        assert TrackerOutbox(rebuilt).pending() == ()
