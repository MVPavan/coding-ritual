"""§8.2 monitoring — supervisor-owned, and token-free by construction.

Everything here is `stat()`, `/proc` and `waitpid`. No model reads a byte of
the runner's log, and nothing in this loop can consume a token even in
principle, which is what makes drill 14's property ("the stale flag is written
while the foreman process is not running") true structurally rather than by
measurement: the loop belongs to the supervisor process, which is alive for the
child's lifetime, and the foreman under manual ticks usually is not.

Two enforcement powers, per §8.2's table:

- **Stale** — no new event for `stale_after`: raise the flag (file now, bd
  metadata when the foreman next ticks) and KEEP WATCHING. Staleness is a hint
  for a tier-2 decision, not a verdict.
- **Runaway** — `max_wall` breached: TERM the group and record the exit reason.
  This one is a ceiling, and it is the universal one; the token ceiling is
  best-effort and only where the profile reports live usage (§6).

**Nothing terminal is ever recorded without proof.** Two observations end a
cycle in `INDETERMINATE` and keep the loop polling: a `/proc` that cannot be
read (liveness unknown) and a `max_wall` termination that could not prove
death. Both used to end the watch and hand `run.py` an exit to record, which
released §5.6 to retry beside a child that was still alive and still writing.
Absence of evidence is not evidence of death, and the honest answer here is to
hold position.

Activity is byte growth plus mtime, and §8.2 is explicit that this is activity,
not proof of progress — a runner in a tight retry loop looks busy here, and the
§10.5 no-progress breaker (artifact identity) is what actually catches it.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from typing import Final

import structlog
from pydantic import BaseModel

from workflow_interpreter.bdio import ProcessHandle
from workflow_interpreter.schema.graph_index import duration_seconds
from workflow_interpreter.schema.models import Node
from workflow_interpreter.supervisor import procfs
from workflow_interpreter.supervisor.clock import Clock, elapsed_seconds, to_iso
from workflow_interpreter.supervisor.config import SupervisorConfig
from workflow_interpreter.supervisor.models import (
    RECORD_MODEL,
    ExitReason,
    Liveness,
    MonitorResult,
    MonitorVerdict,
    ReapResult,
    StaleFlag,
    TerminationProof,
)
from workflow_interpreter.supervisor.paths import (
    WrapperPaths,
    read_record,
    write_record,
)

_LOG: Final[structlog.stdlib.BoundLogger] = structlog.get_logger(__name__)

TERMINAL_VERDICTS: Final[frozenset[MonitorVerdict]] = frozenset(
    {MonitorVerdict.EXITED, MonitorVerdict.MAX_WALL_BREACH}
)


class Limits(BaseModel):
    """The node's two runtime ceilings, in seconds (§2 durations, §8.2)."""

    model_config = RECORD_MODEL

    stale_after_s: float
    max_wall_s: float

    @classmethod
    def from_node(cls, node: Node) -> Limits:
        """Read `stale_after` and `max_wall` off a validated task node."""
        return cls(
            stale_after_s=duration_seconds(node.stale_after or "0s"),
            max_wall_s=duration_seconds(node.max_wall or "0s"),
        )


class Monitor:
    """One activation's §8.2 watch loop, owned by the supervisor process."""

    def __init__(
        self,
        config: SupervisorConfig,
        paths: WrapperPaths,
        clock: Clock,
        *,
        activation_id: str,
        handle: ProcessHandle,
        limits: Limits,
    ) -> None:
        self._config = config
        self._paths = paths
        self._clock = clock
        self._activation_id = activation_id
        self._handle = handle
        self._limits = limits
        self._last_size = 0
        self._last_activity = handle.started_at
        """Seeded from the dispatch, not from the first poll: a runner that
        never writes a single event must still go stale `stale_after` after it
        STARTED, not `stale_after` after somebody happened to look (§8.2)."""
        self._last_proof_error: str | None = None
        """Why the last liveness question could not be answered, for the log."""

    def observe(self) -> MonitorResult:
        """One cycle: reaped status, then unknown, then exit, runaway, staleness.

        Order matters. A reaped status is definitive whatever `/proc` says next.
        An UNANSWERABLE liveness question comes second and stops the cycle
        there: a child that may still be alive must not be signalled (the pid
        is unproven) and must not be recorded as exited (§5.6 would spend an
        infra retry and run a second child beside the survivor — probed). A
        child that has already exited is not stale and did not run away, and
        signalling a `max_wall` breach at a dead pid would be a signal aimed at
        whatever holds that pid now.
        """
        now = self._clock.now()
        size = self._log_size()
        if size != self._last_size:
            self._last_size = size
            self._last_activity = to_iso(now)

        status, reaped = self._exited()
        if reaped.exit_code is not None:
            code = reaped.exit_code
            reason = ExitReason.TERMINATED if code < 0 else ExitReason.EXITED
            return self._result(
                MonitorVerdict.EXITED, now, size, exit_code=code, reason=reason
            )
        if status is Liveness.INDETERMINATE:
            return self._hold(now, size)
        if status is not Liveness.ALIVE:
            return self._result(
                MonitorVerdict.EXITED,
                now,
                size,
                reason=self._unreapable_reason(reaped),
            )

        if elapsed_seconds(self._handle.started_at, now) > self._limits.max_wall_s > 0:
            return self._enforce_max_wall(now, size)

        if elapsed_seconds(self._last_activity, now) > self._limits.stale_after_s > 0:
            return self._result(
                MonitorVerdict.STALE, now, size, stale=self._raise_stale_flag(now)
            )
        return self._result(MonitorVerdict.RUNNING, now, size)

    def watch(
        self, on_cycle: Callable[[MonitorResult], None] | None = None
    ) -> MonitorResult:
        """Poll until the child is gone or the wrapper ends it (§5.3, §8.2).

        `on_cycle` is how a non-terminal observation reaches anything outside
        this loop — §8.2 requires the stale flag in bd as well as on disk, and
        the loop itself is deliberately incapable of writing to bd. The
        supervisor process that owns this loop does the mirroring; nothing in
        here gains a store, a model, or a way to spend a token (drill 14).
        """
        while True:
            result = self.observe()
            if on_cycle is not None:
                on_cycle(result)
            if result.verdict in TERMINAL_VERDICTS:
                return result
            self._clock.sleep(self._config.poll_interval_s)

    # -- internals -------------------------------------------------------

    def _exited(self) -> tuple[Liveness, ReapResult]:
        """`(what liveness can be PROVEN, what `waitpid` could say)`.

        Three answers, not two. `INDETERMINATE` is the one the boolean could
        not express: `Liveness.INDETERMINATE` has `alive == False`, so asking
        `.alive` alone turned an unreadable `/proc` on a healthy child into
        "gone" — verdict `exited`, no code, recorded as §5.6's `exit_unobserved`
        transport failure, and a retry launched beside the survivor (probed).

        `waitpid` and `/proc` are two reads, and a child can die between them.
        Concluding "gone, code unknown" from that ordering DISCARDED the status
        of every child short-lived enough to exit inside the window, so a
        `/proc` that says dead is followed by one more reap: the status is
        still there to collect.
        """
        reaped = procfs.collect(self._handle.pid)
        if reaped.exit_code is not None:
            return Liveness.DEAD, reaped
        proof = procfs.prove_liveness(self._config, self._handle)
        if proof.status is not Liveness.ALIVE:
            self._last_proof_error = proof.read_error
        if proof.alive or proof.status is Liveness.INDETERMINATE:
            return proof.status, reaped
        return proof.status, procfs.collect(self._handle.pid)

    @staticmethod
    def _unreapable_reason(reaped: ReapResult) -> ExitReason | None:
        """Why a proven-dead child left no status here (§5.2, §5.6).

        `None` lets `run.py` fall through to `exit_unobserved` — a wrapper that
        COULD have collected this status and did not, which is §5.6's transport
        failure. `ours = False` is the other case entirely, and it is the kernel
        that says so: `waitpid` answered ECHILD, so this process is not the
        pid's parent and the status was never collectable here. That is what a
        REATTACHED child always is — another wrapper exec'd it and died, so it
        was reparented to init — and calling its normal exit a transport failure
        spent an infra retry on a finished run (probed, Opus#20).
        """
        if reaped.ours:
            return None
        return ExitReason.EXIT_STATUS_UNOBSERVABLE_REATTACHED

    def _hold(self, now: datetime, size: int) -> MonitorResult:
        """Keep watching a child whose liveness cannot be answered (§5.6, §8.2).

        Non-terminal by construction, so `watch` polls again rather than
        returning: there is no honest terminal answer here. Recording an exit
        would authorize a retry beside a child that may still be writing, and
        signalling would aim at a pid this wrapper can no longer prove is its
        own. The loop holds until `/proc` answers or a human ends the wrapper.
        """
        _LOG.error(
            "wf.child.liveness_indeterminate",
            activation_id=self._activation_id,
            pid=self._handle.pid,
            error=self._last_proof_error,
        )
        return self._result(MonitorVerdict.INDETERMINATE, now, size)

    def _log_size(self) -> int:
        """The runner log's byte count — the whole of the activity signal."""
        try:
            return self._paths.log(self._activation_id).stat().st_size
        except (FileNotFoundError, NotADirectoryError):
            return 0

    def _enforce_max_wall(self, now: datetime, size: int) -> MonitorResult:
        """TERM the group on a runaway, and record `max_wall` only if it DIED.

        A termination that could not prove death is not a terminal observation.
        `TerminationProof.confirmed_dead = False` means the child survived TERM
        and KILL, or `/proc` could not be read at all — either way it may still
        be writing the working tree, and `MAX_WALL_BREACH` would end the watch,
        write an exit record and release §5.6 to reset that tree underneath it.
        So the breach is re-enforced on the next cycle instead; `terminate` is
        idempotent and paces itself through its own grace periods (§8.1).

        The exit code comes off the TERMINATION PROOF, never from a second
        `reap`. `terminate` reaps as its last act, a status can be collected
        exactly once, and asking again always answered `None` — recorded as
        `EXIT_CODE_UNOBSERVED`, which claims the wrapper never saw the death it
        had just carried out (Opus#23, Sol#18). The real value is `-9`.
        """
        _LOG.warning(
            "wf.child.max_wall",
            activation_id=self._activation_id,
            pid=self._handle.pid,
            max_wall_s=self._limits.max_wall_s,
        )
        termination = procfs.terminate(self._config, self._handle, self._clock)
        if not termination.confirmed_dead:
            self._last_proof_error = termination.proof.read_error
            _LOG.error(
                "wf.child.max_wall_unconfirmed",
                activation_id=self._activation_id,
                pid=self._handle.pid,
                signals=termination.signals_sent,
            )
            return self._result(
                MonitorVerdict.INDETERMINATE, now, size, termination=termination
            )
        return self._result(
            MonitorVerdict.MAX_WALL_BREACH,
            now,
            size,
            exit_code=termination.exit_code,
            reason=ExitReason.MAX_WALL,
            termination=termination,
        )

    def _raise_stale_flag(self, now: datetime) -> StaleFlag:
        """Write the §8.2 stale flag once; a re-raise keeps the first timestamp."""
        path = self._paths.stale_flag(self._activation_id)
        existing = read_record(path, StaleFlag)
        if existing is not None:
            return existing
        flag = StaleFlag(
            activation_id=self._activation_id,
            raised_at=to_iso(now),
            last_activity_at=self._last_activity,
            stale_after_s=self._limits.stale_after_s,
        )
        write_record(path, flag)
        _LOG.warning(
            "wf.child.stale",
            activation_id=self._activation_id,
            last_activity_at=self._last_activity,
        )
        return flag

    def _result(
        self,
        verdict: MonitorVerdict,
        now: datetime,
        size: int,
        *,
        exit_code: int | None = None,
        reason: ExitReason | None = None,
        stale: StaleFlag | None = None,
        termination: TerminationProof | None = None,
    ) -> MonitorResult:
        """Assemble one observation, always carrying the activity evidence."""
        return MonitorResult(
            verdict=verdict,
            observed_at=to_iso(now),
            last_activity_at=self._last_activity,
            log_size=size,
            exit_code=exit_code,
            exit_reason=reason,
            stale=stale,
            termination=termination,
        )
