"""The stateless foreman tick and bounded stale-runner control surface."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from workflow_interpreter.bdio import (
    ActivationRecord,
    Lifecycle,
    MintReason,
    MintRequest,
    Outcome,
    RootRecord,
)
from workflow_interpreter.bdio.client import STATUS_CLOSED
from workflow_interpreter.bdio.errors import (
    BoundExceededError,
    CanaryFailedError,
    GateVerificationError,
    PinnedGraphMismatchError,
)
from workflow_interpreter.bdio.reads import activations_of, gates_of, next_seq
from workflow_interpreter.foreman.audit import audit
from workflow_interpreter.foreman.cases import (
    advance_lifecycle,
    halt_dead_end,
    intake_all,
    mint_entry,
    route_head,
)
from workflow_interpreter.foreman.compose import (
    Composition,
    InstanceBranchMissing,
    InstanceWiring,
)
from workflow_interpreter.foreman.constants import (
    HALT_AUDIT,
    HALT_MISSING_COMMIT,
    RUN_MAX_WALL,
)
from workflow_interpreter.foreman.events import backfill, expected_intents
from workflow_interpreter.foreman.frontier import build_frontier
from workflow_interpreter.foreman.gates import halt_gate
from workflow_interpreter.foreman.identifiers import validate_bead_id
from workflow_interpreter.foreman.owner import ensure_owner
from workflow_interpreter.foreman.reconcile import reconcile
from workflow_interpreter.foreman.transcript import bounded_tail
from workflow_interpreter.supervisor.errors import (
    ContinuationRefused,
    GitCommandError,
    LockUnavailable,
)
from workflow_interpreter.supervisor.models import SteerIntent
from workflow_interpreter.supervisor.paths import read_record, read_tail
from workflow_interpreter.supervisor.steer import Steerer


class TickReport(BaseModel):
    """The bounded durable work one tick performed.

    Three fields say "this tick did nothing", and they are not the same thing:
    `stalled` is a condition a human has to clear, `contended` is a band-lock
    miss that the next tick may well win, and `waiting_gate` names the open
    gate whose approval is the only thing that can move the instance. Without
    the last two, an automatic loop (`Foreman.run`) could neither poll past a
    lock nor tell a wait from the all-default report it used to spin on.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    blocked: bool = False
    halted: bool = False
    stalled: str | None = None
    contended: bool = False
    dispatched: str | None = None
    settled: str | None = None
    opened_gate: str | None = None
    waiting_gate: str | None = None
    closed_gates: tuple[str, ...] = ()
    refusals: tuple[str, ...] = ()
    events_backfilled: int = 0
    terminal: bool = False


class RunReport(BaseModel):
    """One `Foreman.run` loop: how many ticks it took and how it ended."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    ticks: int
    report: TickReport


class Inspection(BaseModel):
    """The read-only stale-tail view a human or model sees before steering."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    activation_id: str
    lifecycle: Lifecycle
    node: str
    round_no: int
    stale_flag: str | None
    tail: str
    tail_bytes: int


class SteerReport(BaseModel):
    """The one tail acted upon and the durable steer results."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    tail: str
    tail_bytes: int
    closed: str
    continuation: str


def _stale_tail(
    wiring: InstanceWiring, limit: int, activation: ActivationRecord
) -> str:
    """Read the one licensed log tail only when bd already says it is stale."""
    if activation.metadata.stale_flag is None:
        return ""
    return bounded_tail(
        read_tail(wiring.paths.log(activation.activation_id), limit), limit
    )


class Foreman:
    """Coordinates durable workflow work while retaining no tick-local state."""

    def __init__(self, composition: Composition) -> None:
        self._composition = composition

    def inspect(self, root_id: str, activation_id: str) -> Inspection:
        """Read the stale-gated tail without acquiring a band or writing state."""
        validate_bead_id(root_id)
        validate_bead_id(activation_id)
        wiring = self._composition.for_root(root_id)
        activation = wiring.store.reads.load_activation(activation_id)
        if activation.metadata.wf_root_id != root_id:
            raise ValueError("activation does not belong to root")
        tail = _stale_tail(
            wiring, self._composition.supervisor_config.log_tail_bytes, activation
        )
        flag = activation.metadata.stale_flag
        return Inspection(
            activation_id=activation_id,
            lifecycle=activation.metadata.lifecycle,
            node=activation.metadata.node,
            round_no=activation.metadata.round_no,
            stale_flag=None if flag is None else flag.raised_at,
            tail=tail,
            tail_bytes=len(tail.encode("utf-8")),
        )

    def steer(
        self, root_id: str, activation_id: str, *, reason: str, instructions: str
    ) -> SteerReport:
        """Read the stale tail then perform exactly one supervisor steer."""
        validate_bead_id(root_id)
        validate_bead_id(activation_id)
        wiring = self._composition.for_root(root_id)
        wiring.band.acquire()
        try:
            activation = wiring.store.reads.load_activation(activation_id)
            if activation.metadata.wf_root_id != root_id:
                raise ValueError("activation does not belong to root")
            tail = _stale_tail(
                wiring, self._composition.supervisor_config.log_tail_bytes, activation
            )
            continuation = MintRequest(
                node=activation.metadata.node,
                mint_reason=MintReason.STEER_CONTINUATION,
                runner_profile=activation.metadata.runner_profile,
                model=activation.metadata.model,
                session_id=activation.metadata.session_id,
                predecessor_activation_id=activation.activation_id,
                inputs=activation.metadata.inputs,
            )
            steerer = Steerer(
                self._composition.supervisor_config,
                wiring.paths,
                wiring.store,
                self._composition.clock,
            )
            if activation.metadata.is_settled:
                intent = read_record(
                    wiring.paths.steer_intent(activation_id), SteerIntent
                )
                if activation.metadata.outcome is not Outcome.STEERED:
                    raise ValueError("cannot steer a settled activation")
                if intent is None:
                    raise ValueError("cannot resume a steer without its intent")
                result = steerer.resume(activation, intent)
            else:
                result = steerer.steer(
                    activation,
                    reason=reason,
                    instructions=instructions,
                    continuation=continuation,
                )
            return SteerReport(
                tail=tail,
                tail_bytes=len(tail.encode("utf-8")),
                closed=result.closed.activation_id,
                continuation=result.continuation.activation.activation_id,
            )
        finally:
            wiring.band.release()

    def tick(self, root_id: str) -> TickReport:
        """Advance at most one lifecycle action after auditing fresh durable state."""
        validate_bead_id(root_id)
        wiring = self._composition.for_root(root_id)
        try:
            wiring.band.acquire()
        except LockUnavailable:
            return TickReport(contended=True)
        try:
            wiring.store.startup_canary()
            root = wiring.store.reads.load_root(root_id)
            ensure_owner(self._composition.config)
            beads = wiring.store.reads.instance_beads(root_id)
            checked = audit(root, beads)
            if checked.violation is not None:
                gate = wiring.store.open_gate(
                    root.root_id,
                    halt_gate(HALT_AUDIT.format(reason=checked.violation)),
                )
                return TickReport(halted=True, opened_gate=gate.gate_id)
            state = reconcile(
                root,
                activations_of(beads),
                self._composition.git,
                repo_root=wiring.repo_root,
            )
            if state.stalled is not None:
                if state.missing_commit is not None:
                    gate = wiring.store.open_gate(
                        root.root_id,
                        halt_gate(
                            HALT_MISSING_COMMIT.format(commit=state.missing_commit)
                        ),
                    )
                    return TickReport(halted=True, opened_gate=gate.gate_id)
                return TickReport(stalled=state.stalled)
            for activation in activations_of(beads):
                if (
                    activation.metadata.is_completed
                    and activation.bead.status != STATUS_CLOSED
                    and activation.metadata.outcome is not None
                ):
                    repaired = wiring.store.close_activation(
                        activation.activation_id,
                        activation.metadata.outcome,
                        evidence=activation.metadata.evidence,
                        usage=activation.metadata.usage,
                        deviations=activation.metadata.deviations,
                    )
                    return TickReport(settled=repaired.activation_id)
            frontier = build_frontier(root, beads)
            intake = intake_all(wiring, root, gates_of(beads))
            if intake.closed or intake.refusals:
                return TickReport(
                    halted=not intake.closed and frontier.open_halt is not None,
                    closed_gates=tuple(gate.gate_id for gate in intake.closed),
                    refusals=intake.refusals,
                )
            if frontier.open_halt is not None:
                return TickReport(halted=True)
            for activation in (
                *frontier.minted,
                *frontier.dispatched,
                *frontier.exit_recorded,
                *frontier.evidence_recorded,
            ):
                result = advance_lifecycle(self._composition, wiring, root, activation)
                return TickReport(
                    blocked=result.blocked,
                    dispatched=result.dispatched,
                    settled=result.settled,
                    stalled=result.stalled,
                )
            if frontier.dead_end is not None:
                result = halt_dead_end(
                    wiring,
                    root,
                    frontier.dead_end.kind,
                    frontier.dead_end.activation,
                )
                return TickReport(opened_gate=result.opened_gates[0])
            if frontier.abandoned_halt is not None:
                backfilled = self._backfill(wiring, root)
                self._cleanup_terminal_worktree(wiring, root)
                return TickReport(events_backfilled=backfilled, terminal=True)
            if frontier.head is not None:
                result = route_head(self._composition, wiring, root, frontier.head)
                backfilled = self._backfill(wiring, root)
                terminal = result.terminal
                if terminal:
                    self._cleanup_terminal_worktree(wiring, root)
                return TickReport(
                    dispatched=result.dispatched,
                    settled=result.settled,
                    stalled=result.stalled,
                    opened_gate=(
                        result.opened_gates[0] if result.opened_gates else None
                    ),
                    events_backfilled=backfilled,
                    terminal=terminal,
                )
            if frontier.empty:
                result = mint_entry(self._composition, wiring, root)
                return TickReport(
                    dispatched=result.dispatched,
                    stalled=result.stalled,
                )
            if frontier.terminal:
                self._cleanup_terminal_worktree(wiring, root)
                return TickReport(terminal=True)
            if frontier.open_gates:
                # Nothing else advanced and an OPEN gate exists, so the next
                # actor is a human: an open gate is never a routing head
                # (`frontier.candidates_g` requires a decided one), which makes
                # every later tick a repeat of this one. The LOWEST gate id is
                # named for determinism — the report says "a human is needed",
                # not "here is the list".
                return TickReport(
                    waiting_gate=min(gate.gate_id for gate in frontier.open_gates)
                )
            return TickReport()
        except LockUnavailable:
            # Same transient as the band miss above, met deeper in the tick.
            return TickReport(contended=True)
        except (
            BoundExceededError,
            CanaryFailedError,
            ContinuationRefused,
            GateVerificationError,
            PinnedGraphMismatchError,
            InstanceBranchMissing,
            GitCommandError,
        ) as exc:
            return TickReport(
                stalled=f"git: {exc}" if isinstance(exc, GitCommandError) else str(exc)
            )
        finally:
            wiring.band.release()

    def run(self, root_id: str, *, poll_s: float, max_wall_s: float) -> RunReport:
        """Tick until a human, a terminal, a stall, or the wall ends the loop.

        The clock is the injected one, so a drill neither sleeps nor waits:
        `Clock.sleep` is the same capability `SystemClock` implements with
        `time.sleep` and `FrozenClock` implements as "advance `now()`".

        `tick()` is unchanged by this loop — the startup canary still runs per
        tick — because a run is exactly repeated ticks and nothing else.
        """
        clock = self._composition.clock
        started = clock.now()
        ticks = 0
        while True:
            report = self.tick(root_id)
            ticks += 1
            if (
                report.halted
                or report.terminal
                or report.opened_gate
                or report.waiting_gate
                or report.stalled
            ):
                return RunReport(ticks=ticks, report=report)
            if (clock.now() - started).total_seconds() > max_wall_s:
                # The run's own verdict, not a tick's: rendered as a stall so
                # one field answers "why did this stop" for every caller.
                return RunReport(ticks=ticks, report=TickReport(stalled=RUN_MAX_WALL))
            if report.blocked or report.contended:
                clock.sleep(poll_s)

    def _backfill(self, wiring: InstanceWiring, root: RootRecord) -> int:
        """Append every newly implied trace event after its source is durable."""
        beads = wiring.store.reads.instance_beads(root.root_id)
        existing = {
            str(bead.metadata["event_key"])
            for bead in beads
            if bead.metadata.get("wf_kind") == "event" and "event_key" in bead.metadata
        }
        return backfill(
            wiring.store,
            root.root_id,
            expected_intents(root, activations_of(beads), gates_of(beads)),
            actor=self._composition.config.actor,
            existing=existing,
            first_seq=next_seq(beads),
        )

    def _cleanup_terminal_worktree(
        self, wiring: InstanceWiring, root: RootRecord
    ) -> None:
        """D-T1: remove only a clean worktree whose writing outputs are pinned."""
        worktree = wiring.paths.worktree
        if not worktree.exists():
            return
        activations = wiring.store.reads.list_activations(root.root_id)
        if any(
            root.index.nodes[activation.metadata.node].writes
            and (
                activation.metadata.evidence is None
                or activation.metadata.evidence.artifact is None
            )
            for activation in activations
        ):
            return
        if self._composition.git.status_paths(cwd=worktree):
            return
        wiring.workspace.remove_worktree()
