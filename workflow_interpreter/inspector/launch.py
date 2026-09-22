"""§5.2 two-phase activation — the crash-atomic core of the wrapper.

Phase A is `bdio`'s idempotent mint. Phase B is here, and it exists to make one
sentence true under an arbitrarily-timed kill: **a launch either left no child
at all, or left a durable receipt naming the child it started.**

The mechanism is a fork barrier with a positive release:

```
parent                                   child
------                                   -----
pipe(ready), pipe(go)
fork ─────────────────────────────────▶  setsid()               (own process group)
                                         write "R" ────────────▶
read "R" (bounded)
read /proc/<pid>/stat  (start time)
write receipt: temp → fsync → rename → fsync(dir)
write GO = the exec-ledger line ───────▶ read GO (EOF ⇒ exit, never exec)
                                         assert the receipt exists
                                         append line, fsync   (O_APPEND)
                        ◀───────────────  write "A"
read "A" (bounded)                       execve
verify receipt + ledger
record_dispatch(handle)
```

Why each piece is load-bearing:

- **The release is a positive message, not a closed pipe.** If the parent dies
  before releasing, the child's `read` returns EOF, and EOF means EXIT — it
  must never be mistaken for "go". A barrier that opened on parent death would
  exec a child whose receipt was never written (drill 2).
- **The ledger line travels ON the release.** The parent knows the pid, so it
  renders the line; the child appends it. The append therefore happens only
  in a child that got past the barrier, and never in a parent that merely
  intended to start one — which is what makes `wc -l` count EXECS.
- **The ack closes the window before the parent's own verification.** Without
  it the parent would race the child's append and could not check the ledger
  at all.
- **The receipt is written before the release and read back after it.** A
  profile that ignored the injected launcher would be caught by that check,
  because it could not produce a receipt with this launch's id (§6).

The one window that remains is between the child's exec and `record_dispatch`:
bd still says `minted` while a process runs. The receipt closes it — a redispatch
that finds a receipt with a matching ledger line REATTACHES instead of exec'ing
a second time. The reverse residue (a ledger line the receipt cannot explain)
refuses loudly rather than risk a second child.

**The §5.4 precondition runs INSIDE this sequence**, between the mint and the
launch, and its §3.2 carry-forward trio is written to bd before `profile.launch`
is even called. That ordering is the point: `pre_attempt_commit` is what a later
rework's `intended_base_commit` is derived from, and an activation that ran
without it recorded silently reworks on top of the branch head — which after a
reject IS the rejected artifact (§3.2). It is skipped on the REATTACH and
already-dispatched paths for the same reason it exists: a child is running, and
resetting its tree is the last thing to do.

Linux-only: `os.fork`, `os.setsid` and process groups.
"""

from __future__ import annotations

import uuid
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Final, Protocol

import structlog
from pydantic import BaseModel

from workflow_interpreter.bdio import (
    ActivationRecord,
    Lifecycle,
    MintReason,
    MintRequest,
    ProcessHandle,
    StoreError,
    WorkflowStore,
)
from workflow_interpreter.bdio.preflight import steer_ancestor_of
from workflow_interpreter.contracts.execution import (
    MSG_NAMED_SANDBOX,
    MSG_PINNED_POLICY,
    CrewName,
)
from workflow_interpreter.contracts.sessions import SessionFreshReason, SessionMode
from workflow_interpreter.contracts.transport import CrewTransport
from workflow_interpreter.inspector.clock import Clock
from workflow_interpreter.inspector.errors import (
    ContinuationRefused,
    ExecLedgerError,
    ForkBarrierAbortError,
    ForkBarrierError,
    SandboxUnavailable,
    WrapperDirError,
)
from workflow_interpreter.inspector.execution import resolve_grants
from workflow_interpreter.inspector.fork_launcher import (
    EXIT_EXEC_FAILED,
    MSG_NO_ACK,
    ForkBarrierLauncher,
    _vendor_resolves,
)
from workflow_interpreter.inspector.models import (
    RECORD_MODEL,
    LaunchOutcome,
    LaunchReceipt,
    LaunchReceiptState,
    PreconditionResult,
    SteerIntent,
)
from workflow_interpreter.inspector.paths import (
    ExecLedger,
    WrapperPaths,
    read_record,
)
from workflow_interpreter.inspector.profile import (
    CrewChannels,
    Profile,
    TaskSpec,
    WorkingDirectoryProfile,
    channels_for,
)
from workflow_interpreter.inspector.rpc_pipes import RpcPipes
from workflow_interpreter.inspector.rpc_state import state_for
from workflow_interpreter.inspector.sandbox import (
    SandboxMode,
    SandboxPlan,
    plan_for,
    probe,
    toolchain_cache_for,
)
from workflow_interpreter.inspector.toolchain import ToolchainSeeder
from workflow_interpreter.profiles.errors import TaskRefused
from workflow_interpreter.schema.models import ArtifactInputMode

__all__ = ["EXIT_EXEC_FAILED", "ForkBarrierLauncher", "_vendor_resolves"]

_LOG: Final[structlog.stdlib.BoundLogger] = structlog.get_logger(__name__)

_MSG_NO_RECEIPT: Final[str] = (
    "no durable launch receipt for launch {launch_id} after launch; the profile "
    "did not exec through the inspector's launcher (§5.2, §6)"
)
_MSG_HANDLE_DRIFT: Final[str] = (
    "the durable receipt for launch {launch_id} names a different process than "
    "the handle returned; the fork barrier was bypassed"
)
_MSG_LEDGER_COUNT: Final[str] = (
    "exec ledger for {activation_id} moved from {before} to {after} lines across "
    "one launch; exactly one exec must be appended (§5.2)"
)
_MSG_UNEXPLAINED: Final[str] = (
    "exec ledger for {activation_id} holds {count} line(s) that no durable "
    "receipt explains; refusing to exec a second child (§5.2)"
)
_MSG_NO_SESSION: Final[str] = (
    "activation {activation_id} was minted as {reason!r} but carries no session "
    "to rejoin; §8.1 resumes a session, and a launch here would mint a fresh "
    "one and resume something the crew never ran"
)
_MSG_NO_INSTRUCTIONS: Final[str] = (
    "activation {activation_id} was minted as {reason!r} but dispatch was given "
    "no steer instructions; §8.1 continues a session via build_resume_command, "
    "and launching it fresh would discard the guidance the steer was for"
)
_MSG_SANDBOX_UNAVAILABLE: Final[str] = (
    "this host cannot hold the §2 mount bound ({reason}); refusing to dispatch "
    "activation {activation_id} rather than run a node unbounded (O1)"
)
_MSG_REFERENCE_REVIEW_NEEDS_BOUND: Final[str] = (
    "reference-mode task {node!r} requires sandbox = bwrap; exported evidence "
    "must remain protected by the wrapper-root read-only mount"
)
_MSG_NOT_A_CONTINUATION: Final[str] = (
    "dispatch was given steer instructions for activation {activation_id}, whose "
    "mint reason is {reason}; only a {expected} may resume another session (§8.1)"
)
MSG_RESUME_SOURCE_CONTRACT: Final[str] = (
    "resume source contract mismatch for activation {activation_id}: selected "
    "source {source!r} must carry observed session {session!r}"
)
MSG_CLI_VERSION_UNAVAILABLE: Final[str] = (
    "CLI version unavailable for resume activation {activation_id} ({crew}): {reason}"
)
MSG_CLI_VERSION_MISMATCH: Final[str] = (
    "CLI version mismatch for resume activation {activation_id}: source "
    "registered {source!r}, current process probed {current!r}"
)


class DispatchResult(BaseModel):
    """What one `dispatch()` did, and the evidence for it."""

    model_config = RECORD_MODEL

    activation: ActivationRecord
    outcome: LaunchOutcome
    idempotency_key: str
    minted: bool
    exec_count: int
    session_id: str = ""
    """What `Profile.prepare` pre-assigned for this launch (§5.2).

    Reported because it is not always what the mint carried: `prepare` is
    idempotent but may MINT the id for a vendor that can pre-assign one, and the
    caller that later steers this activation needs the id the child actually
    ran under. It is durable through `handle.session_id`, which
    `record_dispatch` writes to bd."""
    handle: ProcessHandle | None = None
    receipt: LaunchReceipt | None = None
    precondition: PreconditionResult | None = None
    """What §5.4 proved before this child was allowed to exec. `None` on the
    REATTACH and already-dispatched paths, where a child is already running and
    its tree is the last thing to touch."""


class TaskBuilder(Protocol):
    """Builds the §6 task for a freshly minted activation (foreman-owned)."""

    def __call__(
        self, activation: ActivationRecord, channels: CrewChannels
    ) -> TaskSpec: ...  # pragma: no cover - protocol


class EnvelopeTaskBuilder:
    """Foreman composer that accounts for the exact initial or resumed payload.

    Plain two-argument builders remain supported for low-level profile callers.
    """

    def __init__(
        self,
        build: Callable[[ActivationRecord, CrewChannels, str | None], TaskSpec],
    ) -> None:
        self._build = build

    def __call__(
        self, activation: ActivationRecord, channels: CrewChannels
    ) -> TaskSpec:
        return self._build(activation, channels, None)

    def continuation(
        self, activation: ActivationRecord, channels: CrewChannels, instructions: str
    ) -> TaskSpec:
        """Compose raw, already-validated steer advice before recording bytes."""
        return self._build(activation, channels, instructions)


class Precondition(Protocol):
    """Proves the §5.4 worktree precondition for a freshly minted activation."""

    def __call__(
        self, activation: ActivationRecord
    ) -> PreconditionResult: ...  # pragma: no cover - protocol


MSG_RPC_CWD: Final[str] = "app-server command cwd disagrees with its planned cwd"


class Dispatcher:
    """§5.2 phase A + phase B for one instance: mint, then launch behind the barrier."""

    def __init__(
        self,
        paths: WrapperPaths,
        store: WorkflowStore,
        clock: Clock,
        *,
        host_env: Mapping[str, str] | None = None,
    ) -> None:
        self._paths = paths
        self._store = store
        self._clock = clock
        self._rpc: tuple[RpcPipes, TaskSpec] | None = None
        self._host_env = dict(host_env or {})

    def take_rpc(self) -> tuple[RpcPipes, TaskSpec] | None:
        """Transfer live transport only to the resident owner; never reconstruct it."""
        rpc, self._rpc = self._rpc, None
        return rpc

    def dispatch(
        self,
        request: MintRequest,
        profile: Profile,
        build_task: TaskBuilder,
        precondition: Precondition | None = None,
        *,
        instructions: str | None = None,
    ) -> DispatchResult:
        """Mint (idempotent), prove the precondition, then exec at most once.

        `instructions` turns the launch into a §8.1 CONTINUATION: the invocation
        comes from `build_resume_command`, so the child rejoins the session its
        predecessor was steered out of instead of starting a new one. It is
        required for a `steer-continuation` mint and refused for any other, so
        neither half of §8.1's "exactly one continuation, via
        `build_resume_command`" can be lost by a caller forgetting an argument.

        A caller that does not hold the text does not have to: for a
        `steer-continuation` it is READ from the predecessor's persisted steer
        intent (`_steer_instructions`). That is what makes the continuation
        dispatchable through `Inspector.run` — the only entry point that also
        watches the child and records its exit — without threading a human's
        prose through every foreman signature, and it is the same file §5.6
        recovery resumes a crashed steer from. bd never sees the prose at all.
        """
        minted = self._store.mint_activation(self._paths.root_id, request)
        activation = minted.activation
        activation_id = activation.activation_id
        ledger = ExecLedger(self._paths.ledger(activation_id))
        if activation.metadata.lifecycle is not Lifecycle.MINTED:
            return DispatchResult(
                activation=activation,
                outcome=LaunchOutcome.ALREADY_DISPATCHED,
                idempotency_key=minted.idempotency_key,
                minted=minted.created,
                exec_count=ledger.count(),
                handle=activation.metadata.handle,
            )
        self._paths.ensure_activation_dir(activation_id)
        reattached = self._reattach(activation_id, ledger)
        if reattached is not None:
            record = self._store.record_dispatch(
                activation_id, reattached.handle, launch_id=reattached.launch_id
            )
            _LOG.warning(
                "wf.dispatch.reattached",
                activation_id=activation_id,
                launch_id=reattached.launch_id,
            )
            return DispatchResult(
                activation=record,
                outcome=LaunchOutcome.REATTACHED,
                idempotency_key=minted.idempotency_key,
                minted=minted.created,
                exec_count=ledger.count(),
                handle=reattached.handle,
                receipt=reattached,
            )
        source = self._steer_source(activation)
        instructions = self._steer_instructions(activation, instructions, source)
        request = request.model_copy(
            update={
                "session_mode": activation.metadata.session_mode,
                "session_source_activation_id": activation.metadata.session_source_activation_id,
                "source_session_id": activation.metadata.source_session_id,
                "expected_tree_oid": activation.metadata.expected_tree_oid,
            }
        )
        self._assert_continuation(
            request,
            activation,
            profile,
            instructions,
            carries_steer=source is not None
            or activation.metadata.mint_reason is MintReason.STEER_CONTINUATION,
        )
        activation, prepared = self._prepare(activation, precondition)
        return self._launch(
            request,
            activation,
            minted.idempotency_key,
            minted.created,
            profile,
            build_task,
            ledger,
            prepared,
            instructions,
        )

    def _steer_source(self, activation: ActivationRecord) -> str | None:
        """The activation whose persisted steer intent this launch must read.

        For a `steer-continuation` that is its predecessor — the activation
        `Steerer.steer` killed, which wrote `steer-intent.json` before it did.
        For an INFRA RETRY the intent is one hop further back: the ancestry
        `R(→R…)→C→S` is walked to the continuation `C` (a retry may itself fail
        in transport, so a one-hop check is not enough), and the intent belongs
        to the activation `C` continued (§8.1, §10.2 — cr-o85.19).
        """
        metadata = activation.metadata
        if metadata.mint_reason is MintReason.STEER_CONTINUATION:
            return metadata.predecessor_activation_id
        continuation = steer_ancestor_of(self._store.reads, activation)
        if continuation is None:
            return None
        return self._store.reads.load_activation(
            continuation
        ).metadata.predecessor_activation_id

    def _steer_instructions(
        self,
        activation: ActivationRecord,
        instructions: str | None,
        source: str | None,
    ) -> str | None:
        """Recover the steer text from the steered activation's intent file.

        The caller's value always wins; this only fills the gap. `source` is
        what `_steer_source` resolved — the activation whose own
        `steer-intent.json` `Steerer.steer` wrote durably before it killed
        anything. Nothing else can reach `build_resume_command` this way.

        A malformed intent classifies as ABSENT rather than raising, for the
        reason `_reattach` gives: the refusal that follows is deterministic and
        recoverable, while a parse error out of `dispatch` wedges the activation
        on every subsequent tick (drill 18).
        """
        if instructions is not None:
            return instructions
        if not source:
            return None
        try:
            intent = read_record(self._paths.steer_intent(source), SteerIntent)
        except WrapperDirError as exc:
            _LOG.warning(
                "wf.dispatch.steer_intent_malformed",
                activation_id=activation.activation_id,
                predecessor_activation_id=source,
                error=str(exc),
            )
            return None
        return None if intent is None else intent.instructions

    def _assert_continuation(
        self,
        request: MintRequest,
        activation: ActivationRecord,
        profile: Profile,
        instructions: str | None,
        carries_steer: bool,
    ) -> None:
        """Refuse a mismatch between durable resume intent and steer payload.

        `carries_steer` covers both activations §8.1 continues a session for:
        the continuation itself and an infra retry descended from one, which
        re-attempts the same steered work and must resume it with the same text
        (cr-o85.19). Either with no instructions is refused rather than launched
        fresh — including a retry whose intent file has gone.

        The session is checked BEFORE `Profile.prepare` runs, and for the same
        reason `Steerer` checks it before the kill (`steer.py`): a profile that
        mints its own id would answer an empty session with a FRESH uuid, and
        the child would then "resume" a session no vendor has ever heard of.
        """
        version_fresh = (
            activation.metadata.crew_profile.removeprefix("profile:")
            == CrewName.CODEX_APPSERVER.value
            and activation.metadata.session_fresh_reason
            is SessionFreshReason.VERSION_MISMATCH
        )
        resume = (
            request.session_mode is SessionMode.RESUME
            and request.source_session_id is not None
        )
        source_id = request.session_source_activation_id
        selected = source_id is not None or request.source_session_id is not None
        # A resume-mode node with NO source selected has no history yet (its
        # first activation, or every candidate was ineligible): fresh is the
        # honest launch. The refusal below is for a source that WAS selected and
        # whose durable identity does not back it (finding 2) — that is the case
        # that used to fall through to a silent fresh launch.
        if request.session_mode is SessionMode.RESUME and selected:
            registration = None
            if source_id is not None:
                try:
                    registration = self._store.reads.load_activation(
                        source_id
                    ).metadata.session_registration
                except StoreError:
                    registration = None
            if (
                source_id is None
                or request.source_session_id is None
                or registration is None
                or registration.activation_id != source_id
                or registration.thread_id != request.source_session_id
            ):
                raise ContinuationRefused(
                    MSG_RESUME_SOURCE_CONTRACT.format(
                        activation_id=activation.activation_id,
                        source=source_id,
                        session=request.source_session_id,
                    )
                )
            crew = profile.name().removeprefix("profile:")
            if crew in (CrewName.CLAUDE.value, CrewName.CODEX.value):
                version_reader = getattr(profile, "cli_version", None)
                error_reader = getattr(profile, "cli_version_error", None)
                version = version_reader() if callable(version_reader) else None
                error = error_reader() if callable(error_reader) else None
                if version is None:
                    raise ContinuationRefused(
                        MSG_CLI_VERSION_UNAVAILABLE.format(
                            activation_id=activation.activation_id,
                            crew=crew,
                            reason=error or "profile was not qualified",
                        )
                    )
                if (
                    registration.crew_version is not None
                    and registration.crew_version != version
                ):
                    raise ContinuationRefused(
                        MSG_CLI_VERSION_MISMATCH.format(
                            activation_id=activation.activation_id,
                            source=registration.crew_version,
                            current=version,
                        )
                    )
        if carries_steer and not resume and not version_fresh:
            raise ContinuationRefused(
                _MSG_NO_SESSION.format(
                    activation_id=activation.activation_id,
                    reason=activation.metadata.mint_reason.value,
                )
            )
        if carries_steer and instructions is None:
            raise ContinuationRefused(
                _MSG_NO_INSTRUCTIONS.format(
                    activation_id=activation.activation_id,
                    reason=activation.metadata.mint_reason.value,
                )
            )
        if not carries_steer and instructions is not None:
            raise ContinuationRefused(
                _MSG_NOT_A_CONTINUATION.format(
                    activation_id=activation.activation_id,
                    reason=activation.metadata.mint_reason.value,
                    expected=MintReason.STEER_CONTINUATION.value,
                )
            )

    def _prepare(
        self, activation: ActivationRecord, precondition: Precondition | None
    ) -> tuple[ActivationRecord, PreconditionResult | None]:
        """Prove §5.4 and make its §3.2 carry-forward durable, before any exec.

        The bd write happens here rather than after the launch on purpose: it
        is the one fact about this attempt that a LATER activation reads, so a
        crash between the exec and it would leave a rework deriving its base
        from the branch head instead of from what this attempt started on
        (§3.2, §5.4).
        """
        if precondition is None:
            return activation, None
        prepared = precondition(activation)
        record = self._store.record_precondition(
            activation.activation_id, prepared.carry_forward()
        )
        return record, prepared

    def _reattach(self, activation_id: str, ledger: ExecLedger) -> LaunchReceipt | None:
        """Decide whether an exec already happened for this activation (§5.2).

        Fail-closed in both directions: a receipt whose launch never reached the
        ledger means no child ran (relaunch); a ledger line no receipt explains
        means a child DID run and cannot be identified — refuse rather than
        start a second one.

        A receipt that does not PARSE is treated as absent, and the ledger then
        decides. It used to raise `WrapperDirError` straight out of `dispatch`,
        so a receipt torn by a crash wedged the activation on every subsequent
        tick — even in the case where the ledger is empty and therefore no
        child can possibly have run. Malformed input classifies here for the
        same reason it does in §5.6: a crash loop is strictly worse than a
        deterministic answer (drill 18).
        """
        receipt = self._read_receipt(activation_id)
        if receipt is not None and receipt.state is not LaunchReceiptState.STARTED:
            raise ForkBarrierAbortError(MSG_NO_ACK.format(pid=receipt.handle.pid))
        if receipt is not None and ledger.has_launch(receipt.launch_id):
            return receipt
        count = ledger.count()
        if count:
            raise ExecLedgerError(
                _MSG_UNEXPLAINED.format(activation_id=activation_id, count=count)
            )
        return None

    def _read_receipt(self, activation_id: str) -> LaunchReceipt | None:
        """The durable receipt, or `None` when there is none the wrapper can read."""
        try:
            return read_record(self._paths.receipt(activation_id), LaunchReceipt)
        except WrapperDirError as exc:
            _LOG.warning(
                "wf.dispatch.receipt_malformed",
                activation_id=activation_id,
                error=str(exc),
            )
            return None

    def _launch(
        self,
        request: MintRequest,
        activation: ActivationRecord,
        idempotency_key: str,
        created: bool,
        profile: Profile,
        build_task: TaskBuilder,
        ledger: ExecLedger,
        prepared: PreconditionResult | None = None,
        instructions: str | None = None,
    ) -> DispatchResult:
        """Build the command, exec behind the barrier, verify, record the handle."""
        activation_id = activation.activation_id
        channels = channels_for(
            self._paths.activation_dir(activation_id),
            self._paths.log(activation_id),
            activation_id,
        )
        task = (
            build_task.continuation(activation, channels, instructions)
            if isinstance(build_task, EnvelopeTaskBuilder) and instructions is not None
            else build_task(activation, channels)
        )
        if profile.name() == CrewName.CODEX_APPSERVER:
            if not isinstance(profile, WorkingDirectoryProfile):
                raise TaskRefused(MSG_RPC_CWD)
            task = task.model_copy(
                update={
                    "checkout_read_root": task.checkout_read_root or task.cwd,
                    "cwd": profile.working_directory(task),
                }
            )
        if task.execution_profile is not None:
            if task.execution_policy is None:
                raise TaskRefused(MSG_PINNED_POLICY)
            task = task.model_copy(
                update={
                    "checkout_read_root": task.checkout_read_root or task.cwd,
                }
            )
        plan, mode = self._sandbox(activation_id, task)
        task = task.model_copy(update={"toolchain_cache": str(plan.toolchain_cache[0])})
        root = self._store.reads.load_root(self._paths.root_id)
        seed = ToolchainSeeder(self._paths.config, self._host_env).prepare(
            Path(task.checkout_read_root or task.cwd),
            root.metadata.instance_base_commit,
            self._paths.activation_dir(activation_id),
        )
        plan = plan.model_copy(
            update={"ro_pins": (*plan.ro_pins, *seed.protected_roots)}
        )
        if task.execution_profile is not None:
            grants = resolve_grants(task, plan, profile)
            task = task.model_copy(
                update={"execution_grants": grants, "cwd": grants.process_cwd}
            )
            plan = plan_for(
                task,
                repo_root=self._paths.config.repo_root,
                wrapper_root=self._paths.config.wrapper_root,
                channels_dir=Path(grants.channels),
                binary=plan.binary,
                protected_roots=seed.protected_roots,
            )
        # The S1 request contract is pinned onto activation metadata at mint.
        # S2 consumes it here: plain resume and steer resume share this branch;
        # steer text changes the prompt, never the decision to resume.
        if profile.name() == CrewName.CODEX_APPSERVER:
            state = state_for(self._paths, root, activation)
            task = task.model_copy(update={"vendor_state": str(state)})
            plan = plan.model_copy(update={"vendor_state": (state,)})
        resume = (
            request.session_mode is SessionMode.RESUME
            and request.source_session_id is not None
        )
        session_id = (
            request.source_session_id if resume else profile.prepare(activation)
        )
        assert session_id is not None
        command = (
            profile.build_resume_command(
                session_id,
                (
                    task.brief
                    if profile.name() == CrewName.CODEX_APPSERVER
                    else task.resume_brief or ""
                )
                if instructions is None
                else instructions,
                task,
            )
            if resume
            else profile.build_command(task, session_id)
        )
        if command.transport is CrewTransport.STDIO_RPC:
            if command.cwd != task.cwd:
                raise TaskRefused(MSG_RPC_CWD)
            if instructions is not None:
                task = task.model_copy(update={"brief": instructions})
        launcher = ForkBarrierLauncher(
            self._paths.config,
            self._paths,
            self._clock,
            activation_id=activation_id,
            launch_id=uuid.uuid4().hex,
            plan=plan,
            sandbox=mode,
            seed_receipts=seed.receipts,
            execution_grants=task.execution_grants,
        )
        before = ledger.count()
        from contextlib import nullcontext

        from workflow_interpreter.inspector.band import BandLock

        coordinator = self._store.coordination_store()
        guard = (
            BandLock(coordinator.member_lock_path(root.root_id, "launch"))
            if root.metadata.coordination is not None
            else nullcontext()
        )
        with guard:
            self._store.assert_member(root.root_id)
            handle = profile.launch(command, launcher)
            self._assert_barrier_held(activation_id, launcher, handle, ledger, before)
            try:
                record = self._store.record_dispatch(
                    activation_id, handle, launch_id=launcher.launch_id
                )
            except BaseException:
                pipes = launcher.take_rpc_pipes()
                if pipes is not None:
                    pipes.close()
                raise
            pipes = launcher.take_rpc_pipes()
            if pipes is not None:
                self._rpc = (pipes, task)
        return DispatchResult(
            activation=record,
            outcome=LaunchOutcome.LAUNCHED,
            idempotency_key=idempotency_key,
            minted=created,
            exec_count=ledger.count(),
            session_id=session_id,
            handle=handle,
            receipt=self._read_receipt(activation_id),
            precondition=prepared,
        )

    def _sandbox(
        self, activation_id: str, task: TaskSpec
    ) -> tuple[SandboxPlan, SandboxMode]:
        """Prove this host can hold the §2 bound, then compute this task's mounts.

        BEFORE `Profile.prepare`, so no vendor session is minted for a launch
        that may not happen (O1). A missing or non-enforcing `bwrap` is
        permanent, so it raises rather than degrades: `foreman/inspector.py`
        turns it into a typed close and the frontier into a halt gate.

        `sandbox = off` builds only the private toolchain-cache plan. It avoids
        `plan_for`'s mount-source side effects while keeping uv's state the same
        as a bounded launch; `wrap` still discards the bind in this mode.
        """
        config = self._paths.config
        if task.execution_profile is not None and config.sandbox is SandboxMode.OFF:
            raise SandboxUnavailable(MSG_NAMED_SANDBOX)
        capability = probe(config)
        if not capability.available:
            raise SandboxUnavailable(
                _MSG_SANDBOX_UNAVAILABLE.format(
                    reason=capability.reason, activation_id=activation_id
                )
            )
        if config.sandbox is SandboxMode.OFF:
            if task.artifact_input_mode is ArtifactInputMode.REFERENCES:
                raise SandboxUnavailable(
                    _MSG_REFERENCE_REVIEW_NEEDS_BOUND.format(node=task.node)
                )
            _LOG.warning(
                "wf.dispatch.sandbox_off",
                activation_id=activation_id,
                node=task.node,
            )
            return (
                SandboxPlan(
                    toolchain_cache=toolchain_cache_for(
                        self._paths.activation_dir(activation_id)
                    )
                ),
                SandboxMode.OFF,
            )
        plan = plan_for(
            task,
            repo_root=config.repo_root,
            wrapper_root=config.wrapper_root,
            channels_dir=self._paths.channels_dir(activation_id),
            binary=capability.binary,
        )
        return plan, SandboxMode.BWRAP

    def _assert_barrier_held(
        self,
        activation_id: str,
        launcher: ForkBarrierLauncher,
        handle: ProcessHandle,
        ledger: ExecLedger,
        before: int,
    ) -> None:
        """Verify the launch went through the barrier — never assume it did (§6)."""
        receipt = self._read_receipt(activation_id)
        if receipt is None or receipt.launch_id != launcher.launch_id:
            raise ForkBarrierError(_MSG_NO_RECEIPT.format(launch_id=launcher.launch_id))
        if receipt.handle != handle:
            raise ForkBarrierError(
                _MSG_HANDLE_DRIFT.format(launch_id=launcher.launch_id)
            )
        after = ledger.count()
        if after != before + 1 or not ledger.has_launch(launcher.launch_id):
            raise ExecLedgerError(
                _MSG_LEDGER_COUNT.format(
                    activation_id=activation_id, before=before, after=after
                )
            )
