"""The composition root: one activation, dispatch through `exit-recorded`.

Everything else in this package is a piece of the §5 lifecycle. This is the
piece that OWNS it, in one process, for the whole of a child's life:

```
prepare (§5.4) → record_precondition (§3.2) → exec behind the barrier (§5.2)
      → watch  (§8.2, stale + max_wall)      → observe the exit (§7)
      → record_exit (§5.3, the final act)
```

Why it has to exist as a thing rather than as a sequence somebody writes at the
call site: §5.3 gives runtime enforcement to "one wrapper process per
activation, ALIVE FOR THE CHILD'S LIFETIME", and drill 14's property is that
the stale flag is raised while the foreman is not running. Without a resident
owner the pieces were individually correct and collectively inert — nothing
tied dispatch to the watch loop or the watch loop to `record_exit`, so in
production shape `max_wall` was never enforced and no exit was ever mirrored
unless a human happened to tick at the right moment.

**It survives its parent.** Nothing here consults the parent process, and the
child is `setsid`-detached into its own group, so a foreman killed mid-run
leaves this loop running and the exit still gets recorded (§5.6 exists for the
case where THIS process dies, not the one above it).

**The stale flag is mirrored here, not in the loop.** §8.2 wants it in the
wrapper dir AND in bd; `Monitor` writes the file and is structurally unable to
reach bd, and this is the caller that closes the gap — without ever being able
to END the loop, because a failed hint must not cost an exit record.

**In-repo, the whole run holds the §12 band.** Not just the precondition: the
band is what makes "one active crew per repo path" true for the child's
lifetime, and `ExitObserver` still needs it when it records what that crew
left dirty.

**A §8.1 continuation comes through here like any other activation.** It used
to be undispatchable in production: `Dispatcher` requires the steer
instructions for a `steer-continuation` mint and this composition has no
argument for them, so every continuation — including the one §5.6 recovery
mints from a crashed steer — was refused at the launch. It is not a signature
problem, and adding a `instructions` parameter here would only move the
forgetting one frame up: the dispatcher reads the text off the predecessor's
own durable steer intent (`Dispatcher._steer_instructions`), so a caller that
holds nothing but the `MintRequest` `Steerer` produced can still run the
continuation to `exit-recorded`.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Final

import structlog
from pydantic import BaseModel

from workflow_interpreter.bdio import (
    ActivationRecord,
    LifecycleConflictError,
    MintRequest,
    StaleFlagRecord,
    StoreError,
    WorkflowStore,
)
from workflow_interpreter.contracts.run_identity import RunIdentity
from workflow_interpreter.contracts.transport import CrewTransport
from workflow_interpreter.inspector import procfs
from workflow_interpreter.inspector.clock import Clock
from workflow_interpreter.inspector.config import InspectorConfig
from workflow_interpreter.inspector.errors import WrapperDirError
from workflow_interpreter.inspector.exit import ExitObservation, ExitObserver
from workflow_interpreter.inspector.gitio import Git
from workflow_interpreter.inspector.launch import (
    Dispatcher,
    DispatchResult,
    Precondition,
    TaskBuilder,
)
from workflow_interpreter.inspector.models import (
    EXIT_CODE_UNOBSERVED,
    HOST_ENDED_EXIT_REASONS,
    RECORD_MODEL,
    ExitReason,
    HumanConfirmation,
    LaunchOutcome,
    MonitorResult,
    MonitorVerdict,
    PreconditionResult,
    SteerIntent,
    TerminationProof,
)
from workflow_interpreter.inspector.monitor import Limits, Monitor
from workflow_interpreter.inspector.paths import WrapperPaths, read_record
from workflow_interpreter.inspector.profile import Profile
from workflow_interpreter.inspector.rpc_session import RpcSession
from workflow_interpreter.inspector.workspace import Workspace
from workflow_interpreter.schema.models import IsolationMode, Node

_LOG: Final[structlog.stdlib.BoundLogger] = structlog.get_logger(__name__)


class InspectionResult(BaseModel):
    """Everything one inspected activation produced, in the order it happened."""

    model_config = RECORD_MODEL

    dispatch: DispatchResult
    monitor: MonitorResult | None = None
    observation: ExitObservation | None = None
    stale_recorded: bool = False
    """Whether the §8.2 stale flag reached bd as well as the wrapper dir."""


class Inspector:
    """One activation's whole §5 lifecycle, owned by one resident process."""

    def __init__(
        self,
        config: InspectorConfig,
        paths: WrapperPaths,
        git: Git,
        store: WorkflowStore,
        workspace: Workspace,
        clock: Clock,
        *,
        host_env: Mapping[str, str] | None = None,
    ) -> None:
        self._config = config
        self._paths = paths
        self._store = store
        self._clock = clock
        self._workspace = workspace
        self._dispatcher = Dispatcher(paths, store, clock, host_env=host_env)
        self._observer = ExitObserver(config, paths, git, store, workspace, clock)

    def run(
        self,
        request: MintRequest,
        node: Node,
        profile: Profile,
        build_task: TaskBuilder,
        *,
        pinned_digests: dict[str, str],
        previous_tree_oid: str | None = None,
        prior_dirty_state: str | None = None,
        confirmation: HumanConfirmation | None = None,
        run_identity: RunIdentity | None = None,
    ) -> InspectionResult:
        """Dispatch, watch until the child is gone, then record what it did.

        In-repo, the whole of that happens inside the §12 execution band — one
        active crew per repo path, ever. Acquiring it around the composition
        rather than around `prepare` alone is what makes the claim true: the
        band has to still be held when `ExitObserver` records what this crew
        left dirty, and an in-repo node whose caller forgot to take it simply
        could not run at all (§12).
        """

        def inspect() -> InspectionResult:
            return self._inspect(
                request,
                node,
                profile,
                build_task,
                pinned_digests=pinned_digests,
                previous_tree_oid=previous_tree_oid,
                prior_dirty_state=prior_dirty_state,
                confirmation=confirmation,
                run_identity=run_identity,
            )

        band = self._workspace.band
        if node.isolation is not IsolationMode.IN_REPO or band.held:
            # `band.held` means a caller above already took it and owns its
            # release; taking it here would end with this frame releasing
            # somebody else's band on the way out.
            return inspect()
        with band:
            return inspect()

    def _inspect(
        self,
        request: MintRequest,
        node: Node,
        profile: Profile,
        build_task: TaskBuilder,
        *,
        pinned_digests: dict[str, str],
        previous_tree_oid: str | None = None,
        prior_dirty_state: str | None = None,
        confirmation: HumanConfirmation | None = None,
        run_identity: RunIdentity | None = None,
    ) -> InspectionResult:
        """One activation, dispatch through `exit-recorded`, band already held.

        Returns without observing an exit only where the child is not this
        wrapper's to watch: `ALREADY_DISPATCHED` means bd already records a
        handle, so another wrapper may be alive on it and adopting it here would
        put two watchers on one child (§5.6 answers that question instead) — and
        where a durable §8.1 steer intent already claims the death, which the
        steerer or §5.6 closes itself (see `_steer_pending`).

        A REATTACHED child IS adopted. It is the §5.2 crash window — our own
        receipt and ledger line exist while bd still said `minted`, which can
        only mean the wrapper that exec'd it died before recording the dispatch,
        so nobody is watching. Returning there left a live child with no
        `max_wall` enforcement and no exit record at all, and its eventual
        normal exit became §5.6's `error_transport`.

        Adoption cannot make the child ours to `waitpid`, though: it is
        reparented to init, so its exit STATUS is unknowable rather than
        unobserved. The monitor learns that from the kernel rather than from
        here — `waitpid` answers ECHILD — and records it as
        `EXIT_STATUS_UNOBSERVABLE_REATTACHED` (§5.2, §5.6). Except where THIS
        frame ended it: an adopted STDIO-RPC child is killed rather than
        watched, because its pipes died with the launcher, and `_host_ended`
        keeps that kill in the recorded reason.
        """
        # A §8.1 continuation runs the same §5.4 precondition as any other
        # activation, so a writing node's continuation is reset to the steered
        # attempt's pre_attempt_commit BEFORE the resumed session's first turn
        # — the killed crew's edits are pinned under prereset/ first, but the
        # session rejoins a tree that no longer matches its context. §5.4 as
        # written is what this obeys; whether §8.1 should exempt continuations
        # is the open ruling in bead cr-o85.18.
        dispatch = self._dispatcher.dispatch(
            request,
            profile,
            build_task,
            self._precondition(node, prior_dirty_state, confirmation),
        )
        handle = dispatch.handle
        if handle is None or dispatch.outcome is LaunchOutcome.ALREADY_DISPATCHED:
            _LOG.info(
                "wf.inspector.no_child",
                activation_id=dispatch.activation.activation_id,
                outcome=dispatch.outcome.value,
            )
            return InspectionResult(dispatch=dispatch)
        if dispatch.outcome is LaunchOutcome.REATTACHED:
            proof = procfs.prove_liveness(self._config, handle)
            _LOG.warning(
                "wf.inspector.adopted",
                activation_id=dispatch.activation.activation_id,
                pid=handle.pid,
                liveness=proof.status.value,
            )

        activation = dispatch.activation
        monitor = Monitor(
            self._config,
            self._paths,
            self._clock,
            activation_id=activation.activation_id,
            handle=handle,
            limits=Limits.from_node(node),
        )
        mirror = _StaleMirror(self._store, activation.activation_id)
        rpc = self._dispatcher.take_rpc()
        if rpc is not None and dispatch.receipt is not None:
            pipes, task = rpc
            result = RpcSession(
                self._config,
                self._paths,
                self._store,
                self._clock,
                dispatch.receipt,
                task,
                pipes,
            ).watch(monitor, mirror)
        else:
            killed = (
                procfs.terminate(self._config, handle, self._clock)
                if dispatch.receipt is not None
                and dispatch.receipt.transport is CrewTransport.STDIO_RPC
                else None
            )
            result = monitor.watch(mirror)
            if killed is not None:
                result = _host_ended(result, killed)
        if self._steer_pending(activation.activation_id):
            # §8.1 writes the intent DURABLY before the kill, so a child that
            # dies with one on disk died BECAUSE of the steer — the same rule
            # §5.6 recovery applies when it lets the intent outrank the exit
            # record. Grading that death here would name it `exit_unobserved` →
            # `error_transport`: an infra retry spent on a deliberate kill, and
            # a close racing the steerer's own `steered` close (cr-us7). The
            # steerer that wrote the intent — or recovery's STEER_PENDING case
            # on the next tick — owns the close; both are idempotent.
            _LOG.info(
                "wf.inspector.steer_pending",
                activation_id=activation.activation_id,
                verdict=result.verdict.value,
            )
            return InspectionResult(
                dispatch=dispatch, monitor=result, stale_recorded=mirror.recorded
            )
        observation = self._observer.observe(
            activation,
            node,
            profile,
            exit_code=_exit_code(result),
            reason=_exit_reason(result),
            pinned_digests=pinned_digests,
            previous_tree_oid=previous_tree_oid,
            run_identity=run_identity,
        )
        return InspectionResult(
            dispatch=dispatch,
            monitor=result,
            observation=observation,
            stale_recorded=mirror.recorded,
        )

    def _steer_pending(self, activation_id: str) -> bool:
        """Whether a durable §8.1 intent claims this activation's death.

        A malformed intent is treated as absent: an unreadable file is §5.6's
        to report (`MALFORMED_STEER_INTENT`), and letting it suppress the exit
        record here would lose the observation to a corrupt byte.
        """
        try:
            intent = read_record(self._paths.steer_intent(activation_id), SteerIntent)
        except WrapperDirError as exc:
            _LOG.warning(
                "wf.inspector.steer_intent_unreadable",
                activation_id=activation_id,
                error=str(exc),
            )
            return False
        return intent is not None

    def _precondition(
        self,
        node: Node,
        prior_dirty_state: str | None,
        confirmation: HumanConfirmation | None,
    ) -> Precondition:
        """The §5.4 hook `Dispatcher` runs between the mint and the exec."""

        def prepare(activation: ActivationRecord) -> PreconditionResult:
            return self._workspace.prepare(
                activation,
                node,
                prior_dirty_state=prior_dirty_state,
                confirmation=confirmation,
            )

        return prepare


class _StaleMirror:
    """Mirrors the first §8.2 stale flag of a watch into bd, and only the first.

    A callable rather than a closure so `recorded` can be read back afterwards,
    and stateful on purpose: §8.2 keeps the FIRST timestamp, so a loop that
    stays stale for an hour writes to bd once.

    **It can never end the watch.** The flag is a HINT for a tier-2 decision;
    the watch is what enforces `max_wall` and what eventually records the exit.
    An exception escaping this callback aborted `Monitor.watch` and left a live
    detached child with neither — a bd hiccup costing an exit record. So every
    bd failure is caught:

    - a transport failure is transient, so the next cycle retries (the flag is
      still on disk, and it is still stale — the loop IS the outbox);
    - a `LifecycleConflictError` means the activation is no longer `dispatched`,
      usually because a foreman tick closed it first (a §8.1 steer is exactly
      what a stale flag is supposed to provoke). The §5.1 lifecycle only ever
      moves forward, so that can never become writable again: stop trying,
      rather than spending a bd read on every remaining poll.
    """

    def __init__(self, store: WorkflowStore, activation_id: str) -> None:
        self._store = store
        self._activation_id = activation_id
        self.recorded = False
        self.abandoned: str | None = None
        """Why the mirror gave up, when it did. The flag stays on disk (§P1)."""

    def __call__(self, result: MonitorResult) -> None:
        """Record a newly raised stale flag; every other cycle is a no-op."""
        if self.recorded or self.abandoned is not None or result.stale is None:
            return
        try:
            self._store.record_stale_flag(
                self._activation_id,
                StaleFlagRecord(
                    raised_at=result.stale.raised_at,
                    last_activity_at=result.stale.last_activity_at,
                ),
            )
        except LifecycleConflictError as exc:
            self.abandoned = str(exc)
            _LOG.warning(
                "wf.stale.mirror_abandoned",
                activation_id=self._activation_id,
                error=str(exc),
            )
            return
        except StoreError as exc:
            _LOG.warning(
                "wf.stale.mirror_deferred",
                activation_id=self._activation_id,
                error=str(exc),
            )
            return
        self.recorded = True


def _exit_code(result: MonitorResult) -> int:
    """The child's exit code, or the sentinel when its status was never seen.

    Never a fabricated `0`: a `MonitorResult` with no code means the process
    vanished without this wrapper reaping it, which is exactly the observation
    that must not be recordable as a success.
    """
    return EXIT_CODE_UNOBSERVED if result.exit_code is None else result.exit_code


def _host_ended(result: MonitorResult, killed: TerminationProof) -> MonitorResult:
    """Keep a kill this wrapper carried out visible in the reason it records.

    An adopted child is reparented to init, so `waitpid` here answers ECHILD
    and the watch reads its death as `EXIT_STATUS_UNOBSERVABLE_REATTACHED` — a
    child that ran to its OWN end, which `foreman/decisions` then accepts as a
    finished run (`HOST_ENDED_EXIT_REASONS`). Over a child this frame killed
    that is a host-kill bypass: the status is genuinely unknowable, but the
    CAUSE is not, and the termination proof is the evidence for it. A watch
    that ended on a ceiling breach already names a host-ended reason and keeps
    the more specific one.
    """
    if _exit_reason(result) in HOST_ENDED_EXIT_REASONS:
        return result
    return result.model_copy(
        update={
            "exit_reason": ExitReason.TERMINATED,
            "exit_code": killed.exit_code
            if result.exit_code is None
            else result.exit_code,
            "termination": killed if result.termination is None else result.termination,
        }
    )


def _exit_reason(result: MonitorResult) -> ExitReason:
    """Why the child stopped, per the §8.2 verdict that ended the watch."""
    if result.verdict is MonitorVerdict.MAX_WALL_BREACH:
        return ExitReason.MAX_WALL
    if result.verdict is MonitorVerdict.STALE_BREACH:
        return ExitReason.STALE
    if result.exit_reason is not None:
        return result.exit_reason
    return ExitReason.EXIT_UNOBSERVED


__all__ = ["InspectionResult", "Inspector"]
