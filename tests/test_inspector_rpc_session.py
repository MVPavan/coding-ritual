"""What an RPC session records about a child IT killed after a protocol failure."""

import pytest

from tests._appserver import AppServerLab
from workflow_interpreter.inspector.models import (
    HOST_ENDED_EXIT_REASONS,
    ExitReason,
)


@pytest.mark.proc
def test_a_protocol_failure_kill_is_recorded_as_host_ended(tmp_path) -> None:
    """Sol: the confirmed kill wrote its reason into a field that does not exist.

    An RPC session that fails mid-protocol terminates the crew itself and
    proves the death. `terminate` reaped the status, so the session's own
    `monitor.observe()` afterwards sees ECHILD and calls the death
    `exit_status_unobservable_reattached` — "it ended on its own", which
    `foreman/decisions` accepts as a finished run. The session already meant to
    overwrite that with `terminated`; it named the wrong field, so the bypass
    stayed open on the one path where the kill is confirmed.
    """
    lab = AppServerLab(tmp_path, "wrong-thread")

    result = lab.run()

    assert result.monitor is not None
    assert result.monitor.exit_reason is ExitReason.TERMINATED
    assert result.monitor.exit_reason in HOST_ENDED_EXIT_REASONS
