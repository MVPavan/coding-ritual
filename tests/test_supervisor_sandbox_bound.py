"""The §2 mount bound WIRED: what a real dispatch does under it, end to end.

`tests/test_supervisor_sandbox.py` owns the plan and the raw `bwrap` argv. This
module owns the seams slice 3 added around them — the wrap site in
`ForkBarrierLauncher`, the `probe` gate in `Dispatcher._launch`, the receipt
field, the `sandbox = off` audit flag and the §3 refusal path — and it drives
each of them through the real launcher or the real foreman rather than through
`wrap` directly.

Skip policy (plan §6): only the tests that need a REAL `bwrap` skip, and they
skip loudly with `probe().reason`. The refusal-path test never skips — it forces
the probe red and uses no `bwrap` at all, which is exactly the host it is about.
"""

from __future__ import annotations

import json
import os
import time
import uuid
from pathlib import Path
from typing import Final

import pytest

from tests._foreman import ForemanLab
from tests._profiles import GRANDCHILD_PID_FILE, Lab
from tests._supervisor import ChildScript
from tests.conftest import Signer
from workflow_interpreter.bdio import Outcome, SigningConfig
from workflow_interpreter.bdio.bounds import consecutive_infra_closes
from workflow_interpreter.bdio.constants import DEVIATION_SANDBOX_UNAVAILABLE
from workflow_interpreter.bdio.mint import views_of
from workflow_interpreter.foreman.constants import HALT_SANDBOX_UNAVAILABLE
from workflow_interpreter.profiles import RunnerName
from workflow_interpreter.supervisor.launch import (
    EXIT_EXEC_FAILED,
    DispatchResult,
    _vendor_resolves,
)
from workflow_interpreter.supervisor.models import (
    AuditFlag,
    CompletionEvidence,
    LaunchReceipt,
    Liveness,
)
from workflow_interpreter.supervisor.paths import ARTIFACT_DIR, read_record
from workflow_interpreter.supervisor.procfs import prove_liveness, terminate
from workflow_interpreter.supervisor.sandbox import (
    BWRAP_BINARY,
    SandboxCapability,
    SandboxMode,
    probe,
)

MISSING_BINARY: Final[str] = "/nonexistent/vendor-cli"
GRANTED_FILE: Final[str] = "src/feature.py"
UNGRANTED_FILE: Final[str] = "outside.py"
REFUSED_TEXT: Final[str] = "Read-only file system"
IMPLEMENT: Final[str] = "implement"
FIRST_ROUND: Final[int] = 1
PROBE_REASON: Final[str] = "bwrap is not on PATH (forced red by the test)"


def handle_activation(result: DispatchResult) -> str:
    """The activation id one `dispatch()` acted on."""
    return result.activation.activation_id


def _skip_without_bwrap(lab: ForemanLab) -> None:
    """Skip loudly when this host cannot hold the bound (plan §6 skip policy)."""
    capability = probe(lab.supervisor_config)
    if not capability.available:
        pytest.skip(capability.reason)


def _completion(lab: ForemanLab, activation_id: str) -> CompletionEvidence:
    """The §7 verdict this activation closed on."""
    record = read_record(
        lab.wiring().paths.completion(activation_id), CompletionEvidence
    )
    assert record is not None
    return record


def _log(lab: ForemanLab, activation_id: str) -> str:
    """What the child said on the streams the launcher redirected."""
    return lab.wiring().paths.log(activation_id).read_text(encoding="utf-8")


# --- the bound, through a real dispatch ------------------------------------


def test_a_write_inside_the_grant_commits_and_is_pinned_as_the_artifact(
    tmp_path: Path,
) -> None:
    """The permissive half: a granted path is writable and the commit is the artifact.

    Without this the refusal tests below would pass on a box that refuses
    EVERYTHING, which is a broken bound rather than a working one.
    """
    lab = ForemanLab(tmp_path)
    _skip_without_bwrap(lab)
    lab.instantiate()

    activation_id = lab.tick().dispatched
    assert activation_id is not None
    assert lab.tick().settled == activation_id

    closed = lab.store.reads.load_activation(activation_id)
    assert closed.metadata.outcome is Outcome.DONE
    assert closed.metadata.evidence is not None
    assert closed.metadata.evidence.artifact is not None
    assert _log(lab, activation_id) == ""


def test_a_write_outside_the_grant_is_refused_and_grades_fail_code(
    tmp_path: Path,
) -> None:
    """The bound refuses it, and the refusal is GRADED rather than absorbed.

    Both halves matter: an EROFS the wrapper swallowed would leave a `done`
    claim standing on a node that produced nothing, which is precisely the
    silent-success shape §7.3 exists to refuse.
    """
    lab = ForemanLab(tmp_path)
    _skip_without_bwrap(lab)
    lab.instantiate()
    lab.profiles.next_script(
        ChildScript(
            marker='{"outcome":"done"}\n',
            effects='{"paths":[]}',
            write_path=UNGRANTED_FILE,
            write_body="escaped = True\n",
        )
    )

    activation_id = lab.tick().dispatched
    assert activation_id is not None
    assert lab.tick().settled == activation_id

    assert REFUSED_TEXT in _log(lab, activation_id)
    assert not (lab.wiring().paths.worktree / UNGRANTED_FILE).exists()
    closed = lab.store.reads.load_activation(activation_id)
    assert closed.metadata.outcome is Outcome.FAIL_CODE
    assert _completion(lab, activation_id).claimed_outcome is Outcome.DONE


def test_a_writes_false_node_cannot_write_anywhere_in_the_checkout(
    tmp_path: Path, signing_config: SigningConfig, sign_payload: Signer
) -> None:
    """`writes = false` gets the checkout read-only and `channels/` and nothing else."""
    lab = ForemanLab(tmp_path, signing=signing_config, signer=sign_payload)
    _skip_without_bwrap(lab)
    lab.instantiate()
    implement = lab.tick().dispatched
    assert implement is not None
    assert lab.tick().settled == implement

    lab.profiles.next_script(
        ChildScript(
            marker='{"outcome":"reject"}\n',
            effects='{"paths":[]}',
            write_path=GRANTED_FILE,
            write_body="the reviewer edits the code\n",
            artifact_path="review.md",
            artifact_body="rework this\n",
        )
    )
    review = lab.tick().dispatched
    assert review is not None
    assert lab.tick().settled == review

    # `src/**` is the IMPLEMENTER's grant; a `writes = false` node carries none
    # at all, so even that path is read-only for it.
    assert REFUSED_TEXT in _log(lab, review)


def test_the_receipt_records_the_wrapped_argv_and_the_mode(tmp_path: Path) -> None:
    """`handle.pid` names `bwrap`, so the receipt has to name what `bwrap` ran."""
    lab = ForemanLab(tmp_path)
    _skip_without_bwrap(lab)
    lab.instantiate()
    activation_id = lab.tick().dispatched
    assert activation_id is not None

    receipt = read_record(lab.wiring().paths.receipt(activation_id), LaunchReceipt)
    assert receipt is not None
    assert receipt.sandbox is SandboxMode.BWRAP
    assert receipt.argv[0] == probe(lab.supervisor_config).binary
    assert "--" in receipt.argv
    inner = receipt.argv[receipt.argv.index("--") + 1 :]
    assert inner[0] == "/bin/sh"


# --- `sandbox = off` is recorded, never silent (O5) -------------------------


def test_sandbox_off_closes_carrying_the_audit_flag(tmp_path: Path) -> None:
    """The escape hatch is legal and LOUD: the close names it."""
    lab = ForemanLab(tmp_path, sandbox=SandboxMode.OFF)
    lab.instantiate()
    activation_id = lab.tick().dispatched
    assert activation_id is not None
    assert lab.tick().settled == activation_id

    receipt = read_record(lab.wiring().paths.receipt(activation_id), LaunchReceipt)
    assert receipt is not None
    assert receipt.sandbox is SandboxMode.OFF
    assert BWRAP_BINARY not in receipt.argv[0]
    assert AuditFlag.SANDBOX_OFF in _completion(lab, activation_id).audit_flags


def test_the_bound_run_carries_no_sandbox_flag(tmp_path: Path) -> None:
    """The other side of the pair: a bounded close must NOT claim the escape."""
    lab = ForemanLab(tmp_path)
    _skip_without_bwrap(lab)
    lab.instantiate()
    activation_id = lab.tick().dispatched
    assert activation_id is not None
    assert lab.tick().settled == activation_id

    assert AuditFlag.SANDBOX_OFF not in _completion(lab, activation_id).audit_flags


# --- the §3 refusal path (never skipped) -----------------------------------


def test_a_host_that_cannot_hold_the_bound_halts_without_spending_a_retry(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """O1: refuse to dispatch, close as a dead end, open a halt gate.

    Never skipped — it forces the probe red and runs no `bwrap` at all, so it
    asserts the same thing on a host that has one and on a host that does not.
    The infra-retry count is the load-bearing assertion: a permanent refusal
    that consumed §10.2 budget would burn the instance's retries on a fact
    about the machine.
    """
    lab = ForemanLab(tmp_path)
    lab.instantiate()
    monkeypatch.setattr(
        "workflow_interpreter.supervisor.launch.probe",
        lambda config: SandboxCapability(available=False, reason=PROBE_REASON),
    )

    report = lab.tick()
    activation_id = report.dispatched
    assert activation_id is not None

    closed = lab.store.reads.load_activation(activation_id)
    assert closed.metadata.outcome is Outcome.ERROR_TRANSPORT
    assert [item.kind for item in closed.metadata.deviations] == [
        DEVIATION_SANDBOX_UNAVAILABLE
    ]
    assert PROBE_REASON in closed.metadata.deviations[0].reason

    activations = lab.store.reads.list_activations(closed.metadata.wf_root_id)
    assert consecutive_infra_closes(views_of(activations), IMPLEMENT, FIRST_ROUND) == 0

    gate_id = lab.tick().opened_gate
    assert gate_id is not None
    gate = lab.store.reads.load_gate(gate_id)
    assert gate.metadata.halt_reason == HALT_SANDBOX_UNAVAILABLE.format(
        node=IMPLEMENT, activation_id=activation_id
    )


# --- the exit-127 sentinel (drill 22 stays honest) --------------------------


@pytest.mark.proc
def test_a_vanished_vendor_binary_still_exits_127_inside_the_box(lab: Lab) -> None:
    """`bwrap` makes `argv[0]` exist, so the sentinel has to run BEFORE the wrap.

    Without it the child would exit whatever `bwrap` exits when its own inner
    program is missing, and drill 22's `1 + max_infra_retries` arithmetic — which
    is keyed on 127 — would silently stop describing anything.
    """
    capability = probe(lab.config)
    if not capability.available:
        pytest.skip(capability.reason)
    result = lab.run(RunnerName.CLAUDE, binary=MISSING_BINARY)

    assert result.observation is not None
    assert result.observation.exit_record.exit_code == EXIT_EXEC_FAILED
    activation_id = result.dispatch.activation.activation_id
    receipt = read_record(lab.paths.receipt(activation_id), LaunchReceipt)
    assert receipt is not None
    # Wrapped anyway: the receipt is the record of the bound this launch had,
    # and the sentinel fires in the child rather than by refusing to wrap.
    assert receipt.argv[0] == probe(lab.config).binary
    assert receipt.argv[-1] == MISSING_BINARY or MISSING_BINARY in receipt.argv


@pytest.mark.proc
def test_the_handle_still_owns_its_process_group_inside_the_box(lab: Lab) -> None:
    """§5.3 identity and §5.6 liveness are unaffected by the wrap (plan §2).

    `handle.pid` now names `bwrap`, not the vendor — but `setsid` runs BEFORE
    the exec, so bwrap's own fork stays in the group the handle records, and
    both group termination and `/proc` liveness keep working on it. A bound that
    cost the wrapper its handle would be worse than no bound.
    """
    capability = probe(lab.config)
    if not capability.available:
        pytest.skip(capability.reason)
    result = lab.dispatch(RunnerName.CLAUDE, session_id=str(uuid.uuid4()))

    handle = result.handle
    assert handle is not None
    assert handle.pgid == handle.pid
    assert prove_liveness(lab.config, handle).status is Liveness.ALIVE
    receipt = read_record(lab.paths.receipt(handle_activation(result)), LaunchReceipt)
    assert receipt is not None
    assert receipt.argv[0] == probe(lab.config).binary
    assert receipt.handle == handle


def test_a_receipt_without_the_field_is_read_as_unbounded(tmp_path: Path) -> None:
    """The default has to be the one that FLAGS, not the one that reassures.

    A receipt with no `sandbox` key can only have been written by a launcher
    that predates the field — that is, by a launch which ran with no mount bound
    at all. Defaulting it to `bwrap` would silently certify exactly the runs
    that were never bounded.
    """
    lab = ForemanLab(tmp_path, sandbox=SandboxMode.OFF)
    lab.instantiate()
    activation_id = lab.tick().dispatched
    assert activation_id is not None
    receipt_path = lab.wiring().paths.receipt(activation_id)
    body = json.loads(receipt_path.read_text(encoding="utf-8"))
    del body["sandbox"]
    receipt_path.write_text(json.dumps(body), encoding="utf-8")

    stripped = read_record(receipt_path, LaunchReceipt)
    assert stripped is not None
    assert stripped.sandbox is SandboxMode.OFF


def test_the_wrapped_argv_names_the_binary_the_probe_resolved(tmp_path: Path) -> None:
    """`probe` resolved an absolute `bwrap`; `wrap` must not re-resolve by name.

    Emitting a bare `bwrap` means the CHILD's `PATH` decides which binary holds
    the bound — and that `PATH` is a passthrough value the runner's environment
    carries. The probe already answered the question, so the answer travels on
    the plan instead of being asked again at exec time.
    """
    lab = ForemanLab(tmp_path)
    _skip_without_bwrap(lab)
    lab.instantiate()
    activation_id = lab.tick().dispatched
    assert activation_id is not None

    receipt = read_record(lab.wiring().paths.receipt(activation_id), LaunchReceipt)
    assert receipt is not None
    assert receipt.argv[0] == probe(lab.supervisor_config).binary
    assert Path(receipt.argv[0]).is_absolute()


def test_a_vendor_on_the_childs_path_only_is_not_called_missing(tmp_path: Path) -> None:
    """The sentinel judges `argv[0]` against the env the CHILD will exec under.

    `launch.py` execs with `dict(command.env)` and nothing else, so resolving
    against the WRAPPER's `os.environ` answers a different question — and gets
    it wrong in both directions for a vendor the profile put on a private
    `PATH`.
    """
    vendor_dir = tmp_path / "vendor bin"
    vendor_dir.mkdir()
    vendor = vendor_dir / "only-here"
    vendor.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    vendor.chmod(0o755)

    assert _vendor_resolves("only-here", {"PATH": str(vendor_dir)}) is True
    assert _vendor_resolves("only-here", {"PATH": "/nonexistent"}) is False
    assert _vendor_resolves(str(vendor), {}) is True


TERMINATE_TIMEOUT_S: Final[float] = 15.0


def _await_gone(pid: int, timeout_s: float = TERMINATE_TIMEOUT_S) -> bool:
    """Whether a pid stops answering `kill(0)` within the deadline."""
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        try:
            os.kill(pid, 0)
        except (ProcessLookupError, PermissionError):
            return True
        time.sleep(0.05)
    return False


def _await_pid(path: Path, timeout_s: float = TERMINATE_TIMEOUT_S) -> int:
    """Wait for the pid the sandboxed child wrote into its artifact channel."""
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        if path.exists() and path.read_text(encoding="utf-8").strip():
            return int(path.read_text(encoding="utf-8").strip())
        time.sleep(0.05)
    raise AssertionError(f"{path} never named a grandchild")


@pytest.mark.proc
def test_terminating_a_bound_child_ends_bwrap_and_its_grandchild(lab: Lab) -> None:
    """§8.1 termination has to reach THROUGH the box, not stop at `bwrap`.

    `handle.pid` names `bwrap`, and the runner plus everything it spawns live
    below it. `terminate` signals the process GROUP, which `setsid` gave the
    leader before the exec — so a grandchild that outlived the kill would mean
    the bound had cost the wrapper its only way to stop a run.
    """
    capability = probe(lab.config)
    if not capability.available:
        pytest.skip(capability.reason)
    result = lab.dispatch(
        RunnerName.CLAUDE, session_id=str(uuid.uuid4()), grandchild=True
    )
    handle = result.handle
    assert handle is not None
    activation_id = handle_activation(result)
    pid_file = (
        lab.paths.channels_dir(activation_id) / ARTIFACT_DIR / GRANDCHILD_PID_FILE
    )
    grandchild = _await_pid(pid_file)
    os.kill(grandchild, 0)

    proof = terminate(lab.config, handle, lab.clock)

    assert proof.confirmed_dead is True
    assert _await_gone(handle.pid) is True
    assert _await_gone(grandchild) is True
