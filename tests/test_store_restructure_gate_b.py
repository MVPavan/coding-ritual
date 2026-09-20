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

from tests._ledger import EPIC, TASK, config_file
from workflow_interpreter.contractor.quiesce import NotQuiesced
from workflow_interpreter.foreman import __main__ as foreman_main
from workflow_interpreter.ledger.__main__ import COMMAND_RECONCILE
from workflow_interpreter.ledger.__main__ import main as ledger_main
from workflow_interpreter.tracker.bd import BdTracker
from workflow_interpreter.tracker.bd_transport import (
    BdClient,
    BdConfig,
    CompletedCommand,
)

EXIT_REFUSED: Final[int] = 2
ESCAPING_ID: Final[str] = "../x"
"""An operator-supplied id that leaves the directory its verb derives paths in."""


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
