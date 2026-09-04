"""§8.2 monitoring — supervisor-owned, and token-free by construction.

Everything here is `stat()`, `/proc` and `waitpid`. No model reads a byte of
the runner's log, and nothing in this loop can consume a token even in
principle, which is what makes drill 14's property ("the stale flag is written
while the foreman process is not running") true structurally rather than by
measurement: the loop belongs to the supervisor process, which is alive for the
child's lifetime, and the foreman under manual ticks usually is not.

Two enforcement powers, per §8.2's table:

- **Stale** — no new event for `stale_after`: raise the flag (file now, bd
  metadata when the foreman next ticks) and KEEP WATCHING. The flag is a hint
  for a tier-2 decision, not a verdict — but the watch is terminable: one
  further `stale_after` of silence and the wrapper TERMs the group exactly as
  a runaway is TERMed, with `stale` as the recorded reason. Any byte in
  between restarts the count, so only a runner that stays silent is ended.
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
    {
        MonitorVerdict.EXITED,
        MonitorVerdict.MAX_WALL_BREACH,
        MonitorVerdict.STALE_BREACH,
    }
)

STALE_WINDOWS_BEFORE_TERMINATION: Final[int] = 2
"""§8.2: one `stale_after` raises the flag, a SECOND one of unbroken silence
ends the child. Counted from the last activity, not from the flag, so a runner
that speaks again buys itself the whole policy back."""


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


class PendingTermination(BaseModel):
    """A kill this wrapper carried out but could not prove, and what it was.

    The verdict and reason travel with the proof because the death may only be
    confirmed cycles later, by a reap — and a status collected then is still
    the ceiling breach that caused it, not an ordinary signal death.
    """

    model_config = RECORD_MODEL

    proof: TerminationProof
    verdict: MonitorVerdict
    reason: ExitReason


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
        self._pending_termination: PendingTermination | None = None
        """An unconfirmed ceiling termination awaiting the child's reap."""

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
            pending = self._pending_termination
            if pending is not None:
                return self._result(
                    pending.verdict,
                    now,
                    size,
                    exit_code=reaped.exit_code,
                    reason=pending.reason,
                    termination=pending.proof,
                )
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

        silence_s = elapsed_seconds(self._last_activity, now)
        if silence_s > self._limits.stale_after_s > 0:
            flag = self._raise_stale_flag(now)
            if (
                silence_s
                > STALE_WINDOWS_BEFORE_TERMINATION * self._limits.stale_after_s
            ):
                return self._enforce_stale(now, size, stale=flag)
            return self._result(MonitorVerdict.STALE, now, size, stale=flag)
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
        """TERM the group on a runaway, and record `max_wall` only if it DIED."""
        _LOG.warning(
            "wf.child.max_wall",
            activation_id=self._activation_id,
            pid=self._handle.pid,
            max_wall_s=self._limits.max_wall_s,
        )
        return self._enforce_ceiling(
            now,
            size,
            verdict=MonitorVerdict.MAX_WALL_BREACH,
            reason=ExitReason.MAX_WALL,
            unconfirmed_event="wf.child.max_wall_unconfirmed",
        )

    def _enforce_stale(
        self, now: datetime, size: int, *, stale: StaleFlag
    ) -> MonitorResult:
        """TERM the group after a SECOND silent `stale_after` window (§8.2).

        The flag alone was only ever a hint, so a runner that went quiet and
        stayed quiet was watched forever: nothing but `max_wall` — often hours
        away, and unset on plenty of nodes — could end it. The second window is
        what makes the flag a watch: the first is the warning that reaches bd,
        and any byte written in it resets the count.

        One corner is deliberate: an ADOPTED (§5.2 REATTACHED) child whose
        `started_at` is already more than two windows old and whose log is
        empty is TERMed on this wrapper's FIRST observation, raising the flag
        and terminating in one cycle, so the foreman never gets its tier-2
        steer window. That is the honest reading of the evidence — a wrapper
        adopting a runner that has not written one byte in two full windows has
        nothing suggesting it ever spoke — and the flag is still written to
        disk and mirrored to bd, so the decision remains visible after the
        fact.
        """
        _LOG.warning(
            "wf.child.stale_terminated",
            activation_id=self._activation_id,
            pid=self._handle.pid,
            stale_after_s=self._limits.stale_after_s,
            last_activity_at=self._last_activity,
        )
        return self._enforce_ceiling(
            now,
            size,
            verdict=MonitorVerdict.STALE_BREACH,
            reason=ExitReason.STALE,
            unconfirmed_event="wf.child.stale_terminated_unconfirmed",
            stale=stale,
        )

    def _enforce_ceiling(
        self,
        now: datetime,
        size: int,
        *,
        verdict: MonitorVerdict,
        reason: ExitReason,
        unconfirmed_event: str,
        stale: StaleFlag | None = None,
    ) -> MonitorResult:
        """End the child on a breached ceiling, terminal only if it DIED.

        A termination that could not prove death is not a terminal observation.
        `TerminationProof.confirmed_dead = False` means the child survived TERM
        and KILL, or `/proc` could not be read at all — either way it may still
        be writing the working tree, and a breach verdict would end the watch,
        write an exit record and release §5.6 to reset that tree underneath it.
        The proof stays pending until a later reap confirms the child died, so
        the status is recorded as this breach rather than an ordinary
        termination. `terminate` remains idempotent and paces itself through
        its own grace periods (§8.1).
        """
        termination = procfs.terminate(self._config, self._handle, self._clock)
        if not termination.confirmed_dead:
            self._pending_termination = PendingTermination(
                proof=termination, verdict=verdict, reason=reason
            )
            self._last_proof_error = termination.proof.read_error
            _LOG.error(
                unconfirmed_event,
                activation_id=self._activation_id,
                pid=self._handle.pid,
                signals=termination.signals_sent,
            )
            return self._result(
                MonitorVerdict.INDETERMINATE,
                now,
                size,
                stale=stale,
                termination=termination,
            )
        return self._result(
            verdict,
            now,
            size,
            exit_code=termination.exit_code,
            reason=reason,
            stale=stale,
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
