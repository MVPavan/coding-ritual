"""Liveness that PROVES identity, and the signalling built on it (§5.3, §5.6, §8.1).

A pid alone is not evidence. Between the dispatch and the tick that asks about
it the host may have rebooted, or the pid may have been reused by an unrelated
process — and "TERM the group" against a reused pid is the wrapper killing
someone else's work. So the §5.3 handle carries three facts and all three must
agree before a process counts as ours:

1. `/proc/<pid>` exists **and the process is not a zombie** — a reaped-but-not-
   waited child keeps its `/proc` entry, with a matching start time, forever.
2. `host_boot_id` equals the running kernel's — a reboot invalidates every pid.
3. `proc_start_time` equals field 22 of `/proc/<pid>/stat` — the boot-relative
   start of THIS process, which pid reuse cannot reproduce.

**Only ENOENT and ESRCH mean "gone".** Any other `/proc` failure — EACCES, EIO,
a container that lost its `/proc` mount — is `INDETERMINATE`, not DEAD.
Collapsing them was a live double-run: a transient read error on a healthy
child classified it §5.6 case 3, closed `error_transport`, and the retry ran
concurrently with the survivor.

Linux-only, by design (§5.3): `/proc`, `boot_id` and process groups have no
portable equivalent and no shim is provided.
"""

from __future__ import annotations

import os
import signal
from pathlib import Path
from typing import Final

import structlog
from pydantic import BaseModel, ConfigDict

from workflow_interpreter.bdio import ProcessHandle
from workflow_interpreter.supervisor.clock import Clock
from workflow_interpreter.supervisor.config import SupervisorConfig
from workflow_interpreter.supervisor.models import (
    Liveness,
    LivenessProof,
    ReapResult,
    TerminationProof,
)

_LOG: Final[structlog.stdlib.BoundLogger] = structlog.get_logger(__name__)

STAT_FILE: Final[str] = "stat"
ZOMBIE_STATE: Final[str] = "Z"
COMM_CLOSE: Final[str] = ")"
_STATE_INDEX: Final[int] = 0
_START_TIME_INDEX: Final[int] = 19
"""Field 22 of `/proc/<pid>/stat`, counted from the first field AFTER `comm`
(fields 1 and 2 are consumed by the `pid (comm)` prefix, which may itself
contain spaces and parentheses — hence the split on the LAST `)`)."""

_MSG_UNPARSEABLE: Final[str] = "{path} exists but does not parse as a stat line"
_MSG_NO_BOOT_ID: Final[str] = (
    "{path} could not be read ({error}); the boot id is half of the §5.3 handle "
    "identity, so liveness is unknown rather than dead"
)


def read_boot_id(config: SupervisorConfig) -> str | None:
    """The running kernel's boot id, or `None` when it cannot be read (§5.3).

    The one `/proc` read that used to sit outside the INDETERMINATE contract.
    A bare `read_text()` here raised `FileNotFoundError` straight out of
    `prove_liveness` — through `Monitor.observe`, `watch` and
    `Supervisor._supervise` — killing the resident supervisor with a live
    detached child, no exit record and nothing that would ever come back for
    it; the same read is also the one §5.6 recovery classifies on (probed,
    Opus#19). "A container that lost its /proc mount" is the module docstring's
    own example of an INDETERMINATE case, and this is how it becomes one.
    """
    try:
        return config.boot_id_path.read_text(encoding="utf-8").strip()
    except OSError as exc:
        _LOG.error(
            "wf.boot_id.unreadable",
            path=str(config.boot_id_path),
            error=str(exc),
        )
        return None


class _Stat(BaseModel):
    """One `/proc/<pid>/stat` read: the fields, or WHY there are none."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    state: str | None = None
    start_time: str | None = None
    read_error: str | None = None
    """Set only for a failure that is NOT "the process is gone"."""

    @property
    def absent(self) -> bool:
        """Whether `/proc` positively says there is no such process."""
        return self.state is None and self.read_error is None


_GONE: Final[tuple[type[OSError], ...]] = (
    FileNotFoundError,
    ProcessLookupError,
    NotADirectoryError,
)
"""ENOENT / ESRCH / ENOTDIR on the `/proc/<pid>` path — and nothing else. These
are the only errors that MEAN the process is not there."""


def _stat_fields(config: SupervisorConfig, pid: int) -> _Stat:
    """Read `/proc/<pid>/stat`, distinguishing "gone" from "could not read"."""
    path = Path(config.proc_root) / str(pid) / STAT_FILE
    try:
        raw = path.read_text(encoding="utf-8", errors="replace")
    except _GONE:
        return _Stat()
    except OSError as exc:
        return _Stat(read_error=str(exc))
    cut = raw.rfind(COMM_CLOSE)
    fields = raw[cut + 1 :].split() if cut >= 0 else []
    if cut < 0 or len(fields) <= _START_TIME_INDEX:
        # The entry exists but does not parse. Not "gone", and not readable
        # either — the honest answer is that liveness is unknown.
        return _Stat(read_error=_MSG_UNPARSEABLE.format(path=path))
    return _Stat(state=fields[_STATE_INDEX], start_time=fields[_START_TIME_INDEX])


def read_start_time(config: SupervisorConfig, pid: int) -> str | None:
    """Field 22 of `/proc/<pid>/stat`, or `None` if it could not be read."""
    return _stat_fields(config, pid).start_time


def prove_liveness(config: SupervisorConfig, handle: ProcessHandle) -> LivenessProof:
    """Answer "is the handle's process still running" with its evidence (§5.6).

    A zombie counts as DEAD: it has exited, its exit status is simply not
    reaped yet, and treating it as alive would hang every `max_wall` and
    steer wait behind a process that can never make progress again. It is
    recorded AS a zombie, though — that is the one observation proving the
    process group id has not been recycled (`terminate`).

    An unreadable `/proc` is INDETERMINATE, never DEAD: see the module note.
    That covers the boot id too — an unreadable one leaves the handle's identity
    half-answered, and "the pid is present but we cannot say whether this host
    rebooted" is not a proof of anything.
    """
    boot_id = read_boot_id(config)
    boot_id_matches = boot_id == handle.host_boot_id
    stat = _stat_fields(config, handle.pid)
    zombie = stat.state == ZOMBIE_STATE
    present = stat.state is not None and not zombie
    observed = stat.start_time
    start_time_matches = observed == handle.proc_start_time
    read_error = stat.read_error
    if boot_id is None:
        read_error = _MSG_NO_BOOT_ID.format(
            path=config.boot_id_path, error="unreadable"
        )
    if read_error is not None:
        status = Liveness.INDETERMINATE
    elif present and boot_id_matches and start_time_matches:
        status = Liveness.ALIVE
    elif present:
        status = Liveness.IDENTITY_MISMATCH
    else:
        status = Liveness.DEAD
    return LivenessProof(
        status=status,
        pid=handle.pid,
        pid_present=present,
        boot_id_matches=boot_id_matches,
        start_time_matches=start_time_matches,
        observed_start_time=observed,
        zombie=zombie,
        read_error=read_error,
    )


def collect(pid: int) -> ReapResult:
    """Wait-with-no-hang on `pid`, keeping the THREE answers `waitpid` gives.

    "Still running" and "never ours to wait for" both produced a bare `None`,
    and they are different facts. `ChildProcessError` is ECHILD: the kernel
    saying this process is not the pid's parent, which is what a REATTACHED
    child always is — another wrapper exec'd it and died, so init adopted it.
    Its status can never be collected here, and recording that as §5.6's
    `exit_unobserved` transport failure spent an infra retry on a run that had
    finished normally (probed, Opus#20).

    A UNIX-style exit code: negative signal number when the child was killed,
    so `max_wall` enforcement can be told from a clean exit 0.
    """
    try:
        waited_pid, status = os.waitpid(pid, os.WNOHANG)
    except ChildProcessError:
        return ReapResult(ours=False)
    if waited_pid == 0:
        return ReapResult()
    if os.WIFSIGNALED(status):
        return ReapResult(exit_code=-os.WTERMSIG(status))
    return ReapResult(exit_code=os.WEXITSTATUS(status))


def reap(pid: int) -> int | None:
    """The collected exit code alone, for callers that only want the status."""
    return collect(pid).exit_code


def _signal_group(pgid: int, sig: signal.Signals) -> bool:
    """Signal a whole process group; `False` when the group is already gone."""
    try:
        os.killpg(pgid, sig)
    except (ProcessLookupError, PermissionError):
        return False
    return True


def _await_death(
    config: SupervisorConfig, handle: ProcessHandle, clock: Clock, grace_s: float
) -> LivenessProof:
    """Poll the handle's identity until it stops being alive, or `grace_s` runs out.

    It deliberately does NOT reap. Reaping the leader here retires its `/proc`
    entry, which is the only thing proving `pgid` has not been recycled — and
    the KILL escalation still to come is aimed at that pgid. An unreaped leader
    is a zombie, which `prove_liveness` already counts as dead, so the loop
    still ends the moment the leader stops running (§8.1, `terminate`).
    """
    deadline = grace_s
    proof = prove_liveness(config, handle)
    while proof.alive and deadline > 0:
        slept = min(config.poll_interval_s, deadline)
        clock.sleep(slept)
        deadline -= slept
        proof = prove_liveness(config, handle)
    return proof


def _group_is_ours(proof: LivenessProof) -> bool:
    """Whether `pgid` provably still names OUR group, so `killpg` is safe.

    True while the leader occupies the pgid with matching identity — running,
    or a zombie of ours that nothing has reaped yet. False once the leader is
    fully gone: `pgid` is then a number the kernel may have handed to somebody
    else, and the wrapper does not kill groups it cannot show are its own. Also
    false on an identity mismatch, which is pid REUSE and somebody else's
    process by definition (§5.3).
    """
    return proof.identity_matches and (proof.pid_present or proof.zombie)


def terminate(
    config: SupervisorConfig, handle: ProcessHandle, clock: Clock
) -> TerminationProof:
    """§8.1 termination: TERM → bounded wait → KILL, with proof of death.

    Idempotent, and safe to call on an already-dead activation.

    - **indeterminate** → `confirmed_dead = False`, nothing signalled. `/proc`
      could not be read, so there is no proof of anything; a caller that treats
      this as death closes an activation whose child may still be running
      (§5.6).
    - **anything else** → TERM the group if the leader is running, wait, then
      ALWAYS escalate to KILL while the group is still provably ours, then reap
      only after death is confirmed.

    The escalation is unconditional on purpose, and the ORDER around the reap is
    the whole of it. §8.1's grace is owed to the process GROUP, and the leader's
    own death proves nothing about the rest of it: a descendant that ignores
    TERM keeps writing the working tree while §5.6 resets it underneath. The
    old sequence reaped the leader as soon as it died, which closed the only
    window in which `killpg` was demonstrably safe — after that, `pgid` is a
    number the kernel may have recycled. Holding the leader as an unreaped
    zombie keeps the group ours through the whole TERM → KILL sequence.
    """
    proof = prove_liveness(config, handle)
    if proof.status is Liveness.INDETERMINATE:
        _LOG.error(
            "wf.child.liveness_indeterminate",
            pid=handle.pid,
            error=proof.read_error,
        )
        return TerminationProof(
            pid=handle.pid, pgid=handle.pgid, confirmed_dead=False, proof=proof
        )
    signals: list[str] = []
    if proof.alive:
        if _signal_group(handle.pgid, signal.SIGTERM):
            signals.append(signal.SIGTERM.name)
        proof = _await_death(config, handle, clock, config.term_grace_s)
        if proof.alive:
            _LOG.warning("wf.child.term_resistant", pid=handle.pid, pgid=handle.pgid)
    if _group_is_ours(proof) and _signal_group(handle.pgid, signal.SIGKILL):
        signals.append(signal.SIGKILL.name)
    if proof.alive:
        proof = _await_death(config, handle, clock, config.kill_grace_s)
    confirmed_dead = proof.status is not Liveness.INDETERMINATE and not proof.alive
    return TerminationProof(
        pid=handle.pid,
        pgid=handle.pgid,
        signals_sent=tuple(signals),
        confirmed_dead=confirmed_dead,
        proof=proof,
        exit_code=reap(handle.pid) if confirmed_dead else None,
    )
