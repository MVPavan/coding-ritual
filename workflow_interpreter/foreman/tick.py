"""The stateless foreman tick and bounded stale-runner control surface."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Final

import structlog
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
    HALT_INPUTS,
    HALT_MISSING_COMMIT,
    RUN_MAX_WALL,
    TERMINAL_SKIP_AMBIGUOUS_ABANDON,
    TERMINAL_SKIP_NOT_A_TERMINAL,
)
from workflow_interpreter.foreman.events import EventIntent, backfill, expected_intents
from workflow_interpreter.foreman.execution import resolved_node
from workflow_interpreter.foreman.frontier import build_frontier
from workflow_interpreter.foreman.gates import ensure_inbox, halt_gate
from workflow_interpreter.foreman.identifiers import validate_bead_id
from workflow_interpreter.foreman.inputs import InputsUnavailable
from workflow_interpreter.foreman.owner import ensure_owner
from workflow_interpreter.foreman.reconcile import reconcile
from workflow_interpreter.foreman.routing import abandon_target
from workflow_interpreter.foreman.transcript import bounded_tail
from workflow_interpreter.schema.models import NodeKind
from workflow_interpreter.supervisor.errors import (
    ContinuationRefused,
    GitCommandError,
    LockUnavailable,
    WrapperDirError,
)
from workflow_interpreter.supervisor.models import (
    CompletionEvidence,
    SteerIntent,
    VerifyResult,
)
from workflow_interpreter.supervisor.paths import read_record, read_tail
from workflow_interpreter.supervisor.steer import Steerer

_LOG: Final[structlog.stdlib.BoundLogger] = structlog.get_logger(__name__)


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
    terminal_node: str | None = None
    """The terminal this instance reached, as recorded on the root (§3.1).
    `terminal` alone said an instance was over without saying where, which
    left an operator reading tick logs to find out (cr-o85.34.24)."""


class RunReport(BaseModel):
    """One `Foreman.run` loop: how many ticks it took and how it ended."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    ticks: int
    report: TickReport


class VerifyInspection(BaseModel):
    """One §7.3 check of a settled activation, as a human reads it back.

    `red_tails` carries only the output of the attempts that came back
    non-zero: a green attempt's chatter is noise in a report whose whole
    purpose is explaining a `fail_code` (cr-o85.34.12).
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    cmd: str
    exit_code: int
    attempts: int
    timed_out: bool
    provenance_ok: bool
    red_tails: tuple[str, ...]


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
    verify: tuple[VerifyInspection, ...] = ()


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


def _red_tails(result: VerifyResult, limit: int) -> tuple[str, ...]:
    """The output of the attempts that came back non-zero, re-bounded.

    Which attempts were red is derived rather than recorded: the rerun policy
    only re-runs a RED attempt, so every attempt before the last was red by
    construction and the last is red exactly when the recorded exit code is.
    """
    tails = result.output_tails if result.exit_code != 0 else result.output_tails[:-1]
    return tuple(bounded_tail(tail, limit) for tail in tails)


def _verify_inspections(
    wiring: InstanceWiring, activation_id: str, limit: int
) -> tuple[VerifyInspection, ...]:
    """The §7.3 results of a settled activation, or nothing at all.

    `inspect` is a read-only view, so an activation that has not been graded
    yet and a `completion.json` a crash left half-written are the same answer:
    no verify section, never an exception out of a report.
    """
    try:
        completion = read_record(
            wiring.paths.completion(activation_id), CompletionEvidence
        )
    except WrapperDirError:
        return ()
    if completion is None:
        return ()
    return tuple(
        VerifyInspection(
            cmd=result.cmd,
            exit_code=result.exit_code,
            attempts=result.attempts,
            timed_out=result.timed_out,
            provenance_ok=result.provenance_ok,
            red_tails=_red_tails(result, limit),
        )
        for result in completion.verify_results
    )


def _abandon_terminal(root: RootRecord) -> str | None:
    """The terminal an approved abandon halt reaches, when the graph names one.

    Nothing in §2 makes an `abandon` edge target a terminal, and the validator
    does not either, so the kind is CHECKED here: settling the root on a task
    or gate target would raise out of the tick (`settle_root` refuses a
    non-terminal), and that exception routes nowhere — every later tick would
    raise before the worktree cleanup. Both unnameable ends are logged and left
    unsettled instead.
    """
    target = abandon_target(root.index)
    if target is None:
        _LOG.warning(
            "wf.root.terminal_skipped",
            root_id=root.root_id,
            reason=TERMINAL_SKIP_AMBIGUOUS_ABANDON,
        )
        return None
    node = root.index.nodes.get(target)
    if node is None or node.kind is not NodeKind.TERMINAL:
        _LOG.warning(
            "wf.root.terminal_skipped",
            root_id=root.root_id,
            reason=TERMINAL_SKIP_NOT_A_TERMINAL.format(node=target),
        )
        return None
    return target


def _opened_gate(wiring: InstanceWiring, gate_id: str | None) -> str | None:
    """Create a just-opened gate's inbox, and pass its id through to the report.

    Every `opened_gate` a tick reports is a gate a human must now approve by
    dropping a signed payload into that directory, and `scripts/approve-gate.sh`
    refuses a missing inbox — so the directory is made where the gate is made,
    not by hand between `status` and the signature.
    """
    if gate_id is None:
        return None
    ensure_inbox(wiring.paths, wiring.store.reads.load_gate(gate_id))
    return gate_id


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
        limit = self._composition.supervisor_config.log_tail_bytes
        tail = _stale_tail(wiring, limit, activation)
        flag = activation.metadata.stale_flag
        return Inspection(
            activation_id=activation_id,
            lifecycle=activation.metadata.lifecycle,
            node=activation.metadata.node,
            round_no=activation.metadata.round_no,
            stale_flag=None if flag is None else flag.raised_at,
            tail=tail,
            tail_bytes=len(tail.encode("utf-8")),
            verify=_verify_inspections(wiring, activation_id, limit),
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
            root = wiring.store.reads.load_root(root_id)
            activation = wiring.store.reads.load_activation(activation_id)
            if activation.metadata.wf_root_id != root_id:
                raise ValueError("activation does not belong to root")
            tail = _stale_tail(
                wiring, self._composition.supervisor_config.log_tail_bytes, activation
            )
            view = resolved_node(root, activation.metadata.node)
            continuation = MintRequest(
                node=activation.metadata.node,
                mint_reason=MintReason.STEER_CONTINUATION,
                runner_profile=view.runner_profile,
                model=view.model,
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
        """Advance the owner through ordinary member execution and decision intents."""
        from workflow_interpreter.foreman.decisions import advance_decision

        return advance_decision(self._composition, root_id, self._tick_local)

    def _tick_local(self, root_id: str) -> TickReport:
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
            wiring.store.assert_member(root_id)
            ensure_owner(self._composition.config)
            beads = wiring.store.reads.instance_beads(root_id)
            checked = audit(root, beads)
            if checked.violation is not None:
                gate = wiring.store.open_gate(
                    root.root_id,
                    halt_gate(HALT_AUDIT.format(reason=checked.violation)),
                )
                return TickReport(
                    halted=True, opened_gate=_opened_gate(wiring, gate.gate_id)
                )
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
                    return TickReport(
                        halted=True, opened_gate=_opened_gate(wiring, gate.gate_id)
                    )
                return TickReport(stalled=state.stalled)
            for activation in activations_of(beads):
                if (
                    activation.metadata.is_completed
                    and activation.bead.status != STATUS_CLOSED
                    and activation.metadata.outcome is not None
                ):
                    # The one close that re-passes the record's OWN deviations
                    # and is not the cr-n2z.9 duplication: an activation with a
                    # recorded outcome is `is_settled`, so `close_activation`
                    # takes its repair-forward branch — it asserts this payload
                    # agrees with the recorded one and merges nothing. This
                    # close adds no deviation; it re-states the recorded ones so
                    # `assert_close_payload` can check them.
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
                source = frontier.dead_end.activation
                if any(
                    "envelope requires" in d.reason for d in source.metadata.deviations
                ):
                    from workflow_interpreter.foreman.decisions import queue_boundary

                    if queue_boundary(
                        self._composition, wiring, root, source, "input_oversize"
                    ):
                        return TickReport(blocked=True)
                result = halt_dead_end(
                    wiring,
                    root,
                    frontier.dead_end.kind,
                    frontier.dead_end.activation,
                )
                return TickReport(
                    opened_gate=_opened_gate(wiring, result.opened_gates[0])
                )
            if frontier.abandoned_halt is not None:
                backfilled = self._backfill(wiring, root)
                return TickReport(
                    events_backfilled=backfilled,
                    terminal=True,
                    terminal_node=self._settle_terminal(
                        wiring, root, _abandon_terminal(root)
                    ),
                )
            if frontier.head is not None:
                result = route_head(self._composition, wiring, root, frontier.head)
                backfilled = self._backfill(wiring, root, result.event_intents)
                terminal = result.terminal
                return TickReport(
                    dispatched=result.dispatched,
                    settled=result.settled,
                    stalled=result.stalled,
                    opened_gate=_opened_gate(
                        wiring,
                        result.opened_gates[0] if result.opened_gates else None,
                    ),
                    events_backfilled=backfilled,
                    terminal=terminal,
                    terminal_node=self._settle_terminal(
                        wiring, root, result.terminal_node
                    )
                    if terminal
                    else None,
                )
            if frontier.empty:
                result = mint_entry(self._composition, wiring, root)
                return TickReport(
                    dispatched=result.dispatched,
                    stalled=result.stalled,
                )
            if frontier.terminal:
                return TickReport(
                    terminal=True,
                    terminal_node=self._settle_terminal(
                        wiring, root, frontier.terminal_node
                    ),
                )
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
        except InputsUnavailable as exc:
            # On a validated graph a bound input is unprovable only when the
            # durable trace contradicts itself (§10.6), so this is the audit
            # violation's sibling, not a stall a later tick could clear. It sits
            # before the stall tuple below — no member of that tuple is a
            # superclass of `InputsUnavailable` today, and this ordering keeps
            # the halt correct whatever the tuple grows to catch.
            gate = wiring.store.open_gate(
                root_id, halt_gate(HALT_INPUTS.format(reason=str(exc)))
            )
            return TickReport(
                halted=True, opened_gate=_opened_gate(wiring, gate.gate_id)
            )
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

    def _backfill(
        self,
        wiring: InstanceWiring,
        root: RootRecord,
        intents: Iterable[EventIntent] = (),
    ) -> int:
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
            (*expected_intents(root, activations_of(beads), gates_of(beads)), *intents),
            actor=self._composition.config.actor,
            existing=existing,
            first_seq=next_seq(beads),
        )

    def _settle_terminal(
        self, wiring: InstanceWiring, root: RootRecord, terminal: str | None
    ) -> str | None:
        """Record the reached terminal on the root, then clean the worktree.

        The root is settled FIRST: it is the durable statement that the
        instance is over, and it must land even if the worktree cleanup below
        cannot (a later tick re-tries the cleanup, because a settled root
        still reports terminal). `settle_root` is idempotent, so every tick
        after the first writes nothing.

        A terminal the graph cannot name — an `abandon` halt in a graph with no
        unique abandon edge, where no terminal event is written either — settles
        nothing: the root must not close on a guess.
        """
        recorded = (
            None
            if terminal is None
            else wiring.store.settle_root(root.root_id, terminal).metadata.terminal
        )
        self._cleanup_terminal_worktree(wiring, root)
        return recorded

    def _cleanup_terminal_worktree(
        self, wiring: InstanceWiring, root: RootRecord
    ) -> None:
        """D-T1: remove only a clean worktree whose writing outputs are pinned."""
        worktree = wiring.paths.worktree
        if not worktree.exists():
            return
        activations = wiring.store.reads.list_activations(root.root_id)
        if any(
            resolved_node(root, activation.metadata.node).node.writes
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
