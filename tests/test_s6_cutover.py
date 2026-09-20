"""S6's two acceptance lines: the whole cycle, and the quiesce that precedes it.

Everything else S6 does is deletion, and a deletion is asserted by the suite
that survives it. What is NOT asserted anywhere else is the cycle end to end —
prepare, admit, land, close, the orchestrator's commit, then `wf ledger
reconcile` — closing the tracker item exactly ONCE. Every earlier slice proves
one leg of that; the mirror is idempotent by construction (R2) and the drain is
on the ref anchor (R7), so the count is the only thing that can tell a second
close from a repaired one.

And R12's clean break: no read shim, so an in-flight record in the old home —
bead metadata, retired in S4 — is a refusal by name with the remedy in it,
rather than a task this build silently treats as unprepared.
"""

from __future__ import annotations

import subprocess
from collections.abc import Sequence
from pathlib import Path
from typing import Final

import pytest

from tests.test_contractor_cli import _entry
from tests.test_contractor_in_ledger import STAGE, _lab
from tests.test_tracker_port import _Decorated, _file_tracker, _outbox
from workflow_interpreter.contractor.quiesce import (
    LEGACY_RECORD_KEYS,
    MSG_REMEDY,
    NotQuiesced,
    assert_quiesced,
)
from workflow_interpreter.contractor.tracker_wiring import repair_mirror
from workflow_interpreter.ledger.closure import closed
from workflow_interpreter.ledger.paths import export_path, repo_id_path
from workflow_interpreter.tracker.bd import BdTracker
from workflow_interpreter.tracker.bd_transport import (
    BdClient,
    BdConfig,
    CompletedCommand,
)
from workflow_interpreter.tracker.constants import WorkItemStatus
from workflow_interpreter.tracker.models import TrackerRef

GIT_TIMEOUT_S: Final[float] = 60.0
CLOSE_CALL: Final[str] = "apply:close"


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


@pytest.mark.acceptance
def test_the_full_cycle_closes_the_tracker_item_exactly_once(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, signing_config, sign_payload
) -> None:
    """S6's acceptance: one cycle, one close (§3.1, R7).

    The close drains at the REF anchor, so by the time the orchestrator commits
    the export the item is already closed. `wf ledger reconcile` then runs over
    a task with nothing owed — and because a `Close` is a desired state rather
    than an operation, repairing the mirror must not write a second one.
    """
    lab = _lab(tmp_path, monkeypatch, signing_config, sign_payload, STAGE)
    tracker = _Decorated(_file_tracker(lab, STAGE))
    lab.tracker = tracker

    result = _entry(lab, STAGE)

    assert result.exit_code == 0, result.report
    assert closed(lab.ledger, lab.git, STAGE) is True
    assert tracker.calls.count(CLOSE_CALL) == 1

    _git(
        lab.repo,
        "add",
        "--",
        str(export_path(lab.repo, STAGE)),
        str(repo_id_path(lab.repo)),
    )
    _git(lab.repo, "commit", "--quiet", "-m", "land: the task and its export")

    repair_mirror(lab.composition.config, lab.ledger, lab.git, STAGE)

    assert tracker.calls.count(CLOSE_CALL) == 1
    assert _outbox(lab).pending() == ()
    item = tracker.get(TrackerRef(kind=tracker.kind, ref=STAGE))
    assert item is not None and item.status is WorkItemStatus.CLOSED


@pytest.mark.acceptance
@pytest.mark.parametrize("state", ["prepared", "admitted"])
@pytest.mark.parametrize("key", sorted(LEGACY_RECORD_KEYS))
def test_an_in_flight_record_in_the_old_home_refuses_by_name(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    signing_config,
    sign_payload,
    state: str,
    key: str,
) -> None:
    """R12: a clean break refuses what it cannot read, and says what to do.

    The record lived in bead metadata until S4. There is no shim — reading one
    would be the compatibility layer R12 refuses — so a task still in flight
    there must not be treated as a task that never prepared, which is what
    every later step would otherwise do: mint a second id, claim, admit, and
    run the work twice.
    """
    lab = _lab(tmp_path, monkeypatch, signing_config, sign_payload, STAGE)
    lab.fake_bd.rows[STAGE]["metadata"] = {
        key: {"stage_id": STAGE, "epic_id": "phase", "state": state}
    }

    result = _entry(lab, STAGE)

    assert result.exit_code == 2
    reason = str(result.report["reason"])
    assert STAGE in reason
    assert state in reason
    assert MSG_REMEDY in reason


@pytest.mark.acceptance
def test_a_quiesce_probe_that_cannot_answer_refuses(tmp_path: Path) -> None:
    """R12 fails CLOSED: one `bd show` timeout may not skip the guard.

    The probe used to read every transport failure as "carries nothing", so a
    single timeout on a stage whose old-home record says `admitted` let the
    command mint a second id for work already running — the exact shape R12
    exists to refuse. A probe that cannot answer refuses by name instead.
    """

    def times_out(argv: Sequence[str], timeout_s: float) -> CompletedCommand:
        raise subprocess.TimeoutExpired(list(argv), timeout_s)

    tracker = BdTracker(BdClient(BdConfig(workspace=tmp_path, actor="test"), times_out))

    with pytest.raises(NotQuiesced) as refusal:
        assert_quiesced(tracker, STAGE)

    assert STAGE in str(refusal.value)
    assert MSG_REMEDY in str(refusal.value)
