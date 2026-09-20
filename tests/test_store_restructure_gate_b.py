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

from pathlib import Path
from typing import Final

from tests._ledger import config_file
from workflow_interpreter.ledger.__main__ import COMMAND_RECONCILE
from workflow_interpreter.ledger.__main__ import main as ledger_main

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
