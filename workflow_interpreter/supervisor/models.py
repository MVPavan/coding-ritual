"""Frozen carriers for everything the wrapper directory holds (§5.2, §5.3, §12).

These are the **observation cache's** shapes (§P1): the launch receipt, the
exec-ledger line, the worktree/in-repo lifecycle record, the stale flag, the
steer intent, the exit file. Losing them costs telemetry, never correctness —
every durable fact they carry is also mirrored into bd through `bdio`.

The bd-side carriers are imported, never re-declared: `ProcessHandle`,
`ExitRecord`, `Evidence` and `ArtifactIdentity` have exactly one definition
each, in `bdio.wire`, and the wrapper writes the same objects to both stores.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Final

from pydantic import BaseModel, ConfigDict

from workflow_interpreter.bdio import (
    ArtifactIdentity,
    Evidence,
    ExitRecord,
    MintRequest,
    PreconditionRecord,
    ProcessHandle,
)
from workflow_interpreter.schema.models import IsolationMode, Outcome
from workflow_interpreter.supervisor.branch import BranchAdvance, BranchAdvanceOutcome
from workflow_interpreter.supervisor.outputs import OutputsWalk, UnsafeEntry, UnsafeKind
from workflow_interpreter.supervisor.sandbox import SandboxMode

RECORD_MODEL: Final[ConfigDict] = ConfigDict(
    frozen=True, extra="forbid", arbitrary_types_allowed=False
)

EXIT_CODE_UNOBSERVED: Final[int] = -256
"""The exit code of a child whose status was never observed (§5.6 case 3).

Never a fabricated `0`: a success the wrapper did not witness is the one
value this record must not be able to state. A real exit code is 0–255 and a
signalled death is recorded as `-signum` (≥ -64), so -256 cannot collide with
either.
"""

__all__ = [
    "EXIT_CODE_UNOBSERVED",
    "ArtifactIdentity",
    "AuditFlag",
    "BranchAdvance",
    "BranchAdvanceOutcome",
    "CollectedExit",
    "CompletionEvidence",
    "ConfirmedPath",
    "DirtyEntry",
    "DirtySnapshot",
    "EffectsManifest",
    "EntryKind",
    "Evidence",
    "ExecLedgerEntry",
    "ExitReason",
    "ExitRecord",
    "HumanConfirmation",
    "IsolationMode",
    "LaunchOutcome",
    "LaunchReceipt",
    "LaunchReceiptState",
    "Liveness",
    "LivenessProof",
    "MonitorResult",
    "MonitorVerdict",
    "OutcomeMarker",
    "OutputsWalk",
    "PinOutcome",
    "PinResult",
    "PreconditionRecord",
    "PreconditionResult",
    "ProcessHandle",
    "ReapResult",
    "RecoveryCase",
    "RecoveryClassification",
    "ResetPlan",
    "RunnerAttribution",
    "StaleFlag",
    "SteerIntent",
    "TerminationProof",
    "UnsafeEntry",
    "UnsafeKind",
    "VerifyResult",
    "WorkspaceRecord",
]


class ExitReason(StrEnum):
    """Why the child stopped — the `reason` of the §5.3 exit record."""

    EXITED = "exited"
    MAX_WALL = "max_wall"
    STALE = "stale"
    """The child was silent through a SECOND `stale_after` window and the
    wrapper ended it (§8.2). The kill is the `max_wall` one — same proof, same
    `error_runner` close costing one infra retry — and only this reason says
    which ceiling was breached."""
    STEERED = "steered"
    TERMINATED = "terminated"
    EXIT_UNOBSERVED = "exit_unobserved"
    """The process vanished and nothing collected its status — §5.6's transport
    failure. A wrapper that COULD have reaped it and did not."""
    EXIT_STATUS_UNOBSERVABLE_REATTACHED = "exit_status_unobservable_reattached"
    """An ADOPTED child died, and its status was never ours to collect.

    `REATTACHED` means, by §5.2's own definition, that another wrapper process
    exec'd the child and died before `record_dispatch`; the child is reparented
    to init, so `waitpid` from here raises `ChildProcessError` forever and the
    code is UNKNOWABLE rather than unobserved (probed, Opus#20). Recording it as
    `exit_unobserved` claimed a transport failure for a run that finished
    normally — and adoption exists precisely to stop that. Death is still
    PROVEN, through `/proc` and the handle's identity; §7's marker, verify
    results and effects decide the outcome, none of which read the exit code.
    """


class LaunchOutcome(StrEnum):
    """What one `dispatch()` call actually did (§5.2 crash windows)."""

    LAUNCHED = "launched"
    """A child crossed the fork barrier and appended one exec-ledger line."""
    REATTACHED = "reattached"
    """A durable receipt and a matching ledger line already existed: the crash
    landed between the exec and `record_dispatch`, so the dispatch is repaired
    forward from the receipt rather than exec'd a second time."""
    ALREADY_DISPATCHED = "already-dispatched"
    """bd already records the handle; nothing to do (§5.1 idempotence)."""


class Liveness(StrEnum):
    """The §5.6 liveness question, answered with proof rather than a pid check."""

    ALIVE = "alive"
    DEAD = "dead"
    IDENTITY_MISMATCH = "identity-mismatch"
    """A process holds the pid, but its boot id or start time is not ours — PID
    reuse or a reboot. Treated exactly as DEAD, and never signalled."""
    INDETERMINATE = "indeterminate"
    """`/proc` could not be read for a reason that is not "the process is gone"
    (EACCES, EIO, a container losing its `/proc` mount). Absence of evidence is
    not evidence of death: calling this DEAD closes the activation and lets a
    retry run concurrently with a survivor, so recovery HALTS on it instead."""


class MonitorVerdict(StrEnum):
    """§8.2 monitoring outcomes; all five are file/proc inspection only."""

    RUNNING = "running"
    STALE = "stale"
    EXITED = "exited"
    MAX_WALL_BREACH = "max-wall-breach"
    STALE_BREACH = "stale-breach"
    """A second `stale_after` window of silence, ended by the wrapper (§8.2).
    Terminal for the same reason `MAX_WALL_BREACH` is: the child is PROVEN
    dead, and the exit that gets recorded is this termination."""
    INDETERMINATE = "indeterminate"
    """Liveness could not be answered, or a `max_wall` termination could not be
    PROVEN. Deliberately non-terminal: the loop holds position and keeps
    watching, because recording an exit for a process that may still be writing
    is what lets §10.2 retry a second child beside a survivor (§5.6)."""


class RecoveryCase(StrEnum):
    """The three §5.6 cases, in the order the spec evaluates them.

    Plus two the spec's three cannot express and that both fail CLOSED — they
    never close an activation, they hand it back for another tick or a human:

    - `STEER_PENDING`: a durable §8.1 steer intent before its continuation is
      durably found. The death was deliberate; classifying it case 3 would
      spend an infra retry on it and drop the continuation the human asked for.
    - `INDETERMINATE`: liveness could not be answered at all (§5.6's question
      needs an answer, not a guess).
    """

    NOT_LAUNCHED = "not-launched"
    ABORT_PENDING = "abort-pending"
    EXIT_RECORDED = "exit-recorded"
    RUNNING = "running"
    DEAD_WITHOUT_EXIT = "dead-without-exit"
    STEER_PENDING = "steer-pending"
    INDETERMINATE = "indeterminate"


class EntryKind(StrEnum):
    """What a §12 dirty entry IS — the question a content digest cannot answer.

    `git status -uall` reports a nested checkout as `?? vendorwork/` and a dirty
    submodule as ` M vendored`: single entries that name a DIRECTORY. They have
    no blob, so they have no digest, so the digest comparison `_is_runner_output`
    rests on degenerates to `"" == ""` — which would make every directory the
    wrapper ever recorded resettable forever. The kind is recorded so the
    comparison is never reached for one (§12).

    A directory is only the shape this repository met first. A FIFO, a socket,
    a device node — or the far likelier symlink to one, which `git status`
    reports as an ordinary entry and `git hash-object` FOLLOWS — has no blob
    either, and blocks git instead of failing it (probed, r4). `NON_REGULAR` is
    that class, and it gets a directory's treatment: never hashed, never
    attributable, never releasable.

    `FILE` covers an absent path too: a deleted tracked file has no blob either,
    but its content is in the object store, so it is legitimately restorable
    (`DirtyEntry.digest`).
    """

    FILE = "file"
    DIRECTORY = "directory"
    NON_REGULAR = "non-regular"


class AuditFlag(StrEnum):
    """§10.6 sweep flags the wrapper raises while computing §7 evidence."""

    VERIFIER_PROVENANCE = "verifier_provenance"
    VERIFY_UNRUNNABLE = "verify_unrunnable"
    """The check's provenance held but the process could not be started at all
    (permissions, a missing interpreter). Recorded, never raised: an escaping
    `OSError` means no exit record is ever written and the activation repeats
    as `error_transport` until the §10.2 infra cap burns."""
    MARKER_INVALID = "marker_invalid"
    UNDECLARED_EFFECT = "undeclared_effect"
    EFFECT_OUTSIDE_ALLOWED_PATHS = "effect_outside_allowed_paths"
    """A path was modified outside the node's `allowed_paths`, whether or not
    the runner declared it. §7.5 subtracts `declared UNION allowed`, so a
    declared path outside the set reconciles the transition and is graded
    `done`; as a REPORTING rule `allowed_paths` is an exemption, never a bound
    (ADR 0001). Recorded, never raised: this flags scope for an operator and
    changes no outcome.

    Containment itself is the §2 mount bound (`supervisor/sandbox.py`), which
    makes the grants the node's writable mounts — so under `sandbox = bwrap`
    this flag is a should-never-fire signal rather than the only line of
    defence, and it is joined there by `BOUND_VIOLATED`. It still fires
    honestly, and alone, under `sandbox = off`."""
    BOUND_VIOLATED = "bound_violated"
    """A child the RECEIPT says ran under the §2 mount bound left an
    out-of-grant path whose WORKING-TREE state differs from the intended base
    commit's (cr-n2z.4). That write was physically impossible under the bound,
    so this is not a runner outcome at all: the bound did not hold. The flag
    needs the physical difference and not just
    `EFFECT_OUTSIDE_ALLOWED_PATHS` — `.git` is writable under the bound, so an
    index-only or commit-only forgery puts an out-of-grant path in the
    observation without any write outside the grant (`exit.py`).

    Unlike every other flag it CHANGES the verdict — `error_transport`, which
    `foreman/finalize.decide` turns into the retry-exempt `bound_violated`
    deviation that halts. That halt is a STOP and not a rollback: §7.4 has
    already pinned the artifact ref and the instance branch may already have
    been advanced. What it buys is that nothing further is dispatched into a
    bound the wrapper cannot vouch for."""
    SANDBOX_OFF = "sandbox_off"
    """This activation's child ran WITHOUT the §2 mount bound (O5). Evidence
    side, so it renders to the operator and blocks nothing: `sandbox = off` is a
    legitimate operator escape hatch, and the only requirement is that it is
    never silent."""
    ANTI_DRIFT = "anti_drift"
    EFFECTS_MANIFEST_MISSING = "effects_manifest_missing"
    OUTPUTS_UNSAFE = "outputs_unsafe"
    INSTANCE_BRANCH_DIVERGED = "instance_branch_diverged"


# --- wrapper-dir records -------------------------------------------------


class LaunchReceiptState(StrEnum):
    """Whether a receipt's child launched normally or was aborted at the barrier."""

    STARTED = "started"
    ABORTED = "aborted"
    ABORT_PENDING = "abort-pending"


class LaunchReceipt(BaseModel):
    """The §5.2 fork barrier's durable artifact — written BEFORE the child execs.

    Its existence is the barrier condition, and its `launch_id` is what ties an
    exec-ledger line to this launch. A receipt with no matching ledger line
    means the child never crossed; a receipt WITH one means an exec happened
    even if bd never learned of it (the `REATTACHED` window).
    """

    model_config = RECORD_MODEL

    launch_id: str
    root_id: str
    activation_id: str
    argv: tuple[str, ...]
    """The WRAPPED argv under `sandbox = bwrap`: `handle.pid` names `bwrap`, not
    the vendor, so the inner argv would describe a process this receipt's handle
    does not name (plan §2)."""
    cwd: str
    handle: ProcessHandle
    sandbox: SandboxMode = SandboxMode.OFF
    """Which bound this child ran under.

    Defaulted to `off`, which is the FLAGGING value and the only honest one: a
    receipt carrying no `sandbox` key can only have been written by a launcher
    that predates the field, and such a launch ran with no mount bound at all.
    Defaulting to `bwrap` would have silently certified precisely the runs that
    were never bounded. Every launcher-written receipt states the mode
    explicitly, so the default is only ever reached by such a record."""
    state: LaunchReceiptState = LaunchReceiptState.STARTED
    """The abort result, when the parent gave up waiting for the barrier ACK."""
    abort_exit_code: int | None = None
    """The `TerminationProof` status when a barrier abort proved the child dead."""


class ExecLedgerEntry(BaseModel):
    """One appended line of the §5.2 exec ledger — one per REAL exec.

    Appended by the CHILD, after the barrier and immediately before `execve`,
    so `wc -l` counts execs rather than intentions (drills 1, 2, 10, 22).
    """

    model_config = RECORD_MODEL

    launch_id: str
    activation_id: str
    pid: int
    at: str


class WorkspaceRecord(BaseModel):
    """The §5.4 worktree record / §12 in-repo band record for one instance."""

    model_config = RECORD_MODEL

    isolation: IsolationMode
    path: str
    branch: str | None
    owner_activation_id: str
    expected_head: str
    read_only: bool = False
    """A `writes = false` node gets a checkout at the reviewed commit; its
    outputs go to `$WF_ARTIFACT_DIR` (§5.4)."""
    created_at: str


class DirtyEntry(BaseModel):
    """One dirty path of a §12 snapshot, identified by content, not by mtime."""

    model_config = RECORD_MODEL

    path: str
    digest: str
    """The blob OID of the working-tree content, or `""` where there is no blob
    to hash: a deleted path, a DIRECTORY, and anything else that is not a
    regular file. `kind` is what tells those apart — a deleted tracked file is
    legitimately restorable from the object store, while the other two are
    protected outright."""
    tracked: bool
    kind: EntryKind = EntryKind.FILE
    """Defaulted so a snapshot recorded before this field existed still decodes;
    everything the wrapper writes now states it."""


class DirtySnapshot(BaseModel):
    """§12 `pre_attempt_dirty_state`: what was dirty BEFORE the runner ran.

    `stash_commit` is `git stash create`'s commit (empty when the tree was
    clean); the per-path digests are what a later reset actually compares
    against, because a stash commit alone cannot answer "is this file still
    exactly the human's".
    """

    model_config = RECORD_MODEL

    stash_commit: str | None = None
    entries: tuple[DirtyEntry, ...] = ()

    @property
    def paths(self) -> frozenset[str]:
        """The dirty paths this snapshot covers."""
        return frozenset(entry.path for entry in self.entries)

    def digest_of(self, path: str) -> str | None:
        """The recorded content digest for `path`, or `None` if unrecorded."""
        return next(
            (entry.digest for entry in self.entries if entry.path == path), None
        )


class RunnerAttribution(BaseModel):
    """What the wrapper itself WATCHED a runner produce (§12 positive attribution).

    The §12 reset authority. Every entry survived three independent tests at
    the moment the runner died and the wrapper still held the band:

    1. the wrapper's own `git status` saw the path dirty (observed);
    2. the runner's `$WF_EFFECTS_FILE` declared it (claimed);
    3. it was not already dirty when that attempt STARTED (so it cannot be
       pre-existing human work the runner merely overwrote).

    A path is resettable later only if its content is STILL byte-identical to
    the digest recorded here — anything that touched it since (a human, an
    editor, another tool) breaks the match and returns it to protected.

    Instance-scoped and single-writer: only `ExitObserver` writes it, and only
    one runner is ever active per repo path (§12 execution band). Entries
    accumulate across activations so a file the implementer left is still
    attributable after a reviewer has run; a superseded path is overwritten and
    a changed one simply stops matching.

    Losing it (a wiped `.wf/`) costs no correctness: with nothing attributable,
    every dirty path is protected and the reset refuses to tier-2 (§P1).
    """

    model_config = RECORD_MODEL

    activation_id: str
    observed_at: str
    head_commit: str
    entries: tuple[DirtyEntry, ...] = ()

    def digest_of(self, path: str) -> str | None:
        """The content digest the wrapper attributed to a runner, if any."""
        return next(
            (entry.digest for entry in self.entries if entry.path == path), None
        )


class ConfirmedPath(BaseModel):
    """One path a human released for reset, bound to the content they saw."""

    model_config = RECORD_MODEL

    path: str
    digest: str
    """The blob OID the human looked at; `""` for a path they confirmed as
    deleted. A confirmation that named the path alone would still authorize the
    destruction of whatever was written there afterwards."""


class HumanConfirmation(BaseModel):
    """Tier-2 confirmation naming the exact paths a human released (§12).

    Path-scoped on purpose: a blanket "yes" would let one confirmation authorize
    every future reset, which is the same as no confirmation at all. Scoped to
    ONE activation and to the exact CONTENT of each path for the same reason in
    the time dimension — a confirmation kept from an earlier attempt would
    otherwise release work that did not exist when it was given.
    """

    model_config = RECORD_MODEL

    activation_id: str
    confirmed: tuple[ConfirmedPath, ...]
    reason: str
    actor: str
    confirmed_at: str

    def releases(self, activation_id: str, path: str, digest: str) -> bool:
        """Whether this confirmation released this path, at this content, HERE.

        All three must match. The activation is the time dimension: a
        confirmation kept from an earlier attempt would otherwise authorize a
        reset in an attempt the human never looked at, which is the same
        blanket "yes" the path and digest scoping exist to prevent.
        """
        return activation_id == self.activation_id and any(
            entry.path == path and entry.digest == digest for entry in self.confirmed
        )

    @property
    def confirmed_paths(self) -> tuple[str, ...]:
        """The released paths, for logging and refusal messages."""
        return tuple(entry.path for entry in self.confirmed)


class ResetPlan(BaseModel):
    """What a §5.4/§12 reset would do, computed before anything is destroyed."""

    model_config = RECORD_MODEL

    resettable: tuple[str, ...] = ()
    protected: tuple[str, ...] = ()
    """Dirty paths the wrapper cannot ATTRIBUTE to the runner — treated as
    human work (§12). Ambiguity lands here; it never lands in `resettable`."""
    head_move_required: bool = False
    head_protected: bool = False
    """HEAD is off `intended_base_commit` and the commit it sits on is not
    wrapper-pinned lineage — someone else committed, and `reset --hard` would
    discard it with nothing referencing it (§12)."""
    protected_head: str | None = None

    @property
    def refused(self) -> bool:
        """Whether this plan may not be applied without tier-2 confirmation."""
        return bool(self.protected) or self.head_protected


class PinOutcome(StrEnum):
    """What `Workspace.pin_artifact` did with the commit it found (§7.4).

    Four answers rather than an `ArtifactIdentity | None`, because `None` was
    two different facts — "there is no commit" and "there is one this attempt
    cannot claim" — and §5.6 recovery closed on both. Closing is what authorizes
    the next reset, so it is only safe where the commit is PRESERVED.
    """

    NO_COMMIT = "no-commit"
    """HEAD is still `intended_base_commit`: nothing was produced (§7.4 `no_diff`)."""
    PINNED = "pinned"
    """Attributed to this attempt and pinned as its artifact — and therefore
    also the §12 authority for a later reset to move HEAD off it."""
    QUARANTINED = "quarantined"
    """Not attributable, but PRESERVED under the quarantine namespace so it can
    neither be garbage-collected nor mistaken for this attempt's artifact. Never
    reset authority; a later precondition still refuses to move HEAD off it."""
    REFUSED = "refused"
    """Not attributable and not preserved. The caller has an unreferenced commit
    on its hands and must not act as though the attempt settled."""


class PinResult(BaseModel):
    """The §7.4 pin decision, with the ref and the reason it went that way."""

    model_config = RECORD_MODEL

    outcome: PinOutcome
    identity: ArtifactIdentity | None = None
    """Set only for `PINNED`: the honest statement that THIS activation produced
    THIS commit. A quarantined commit deliberately has none (§7.4)."""
    commit: str | None = None
    """The commit the decision was about, whatever the outcome."""
    ref: str | None = None
    reason: str | None = None
    branch: BranchAdvance | None = None

    @property
    def settled(self) -> bool:
        """Whether the commit question is closed — nothing is left unreferenced."""
        return self.outcome is not PinOutcome.REFUSED


class PreconditionResult(BaseModel):
    """The §5.4 precondition, proven — and the §3.2 carry-forward it produces.

    The trio is persisted through `WorkflowStore.record_precondition` between
    the mint and the exec (`Dispatcher.dispatch`'s `precondition` hook), so a
    crash after the exec cannot leave a dispatched activation whose
    `pre_attempt_commit` was never recorded — `bdio.mint` derives a rework's
    `intended_base_commit` from it and otherwise falls through to the branch
    head, which after a reject IS the rejected artifact (§3.2).
    """

    model_config = RECORD_MODEL

    intended_base_commit: str
    pre_attempt_commit: str
    reset_verified_commit: str
    pre_attempt_dirty_state: str | None = None
    """Canonical JSON of the §12 `DirtySnapshot`; `None` in worktree mode."""
    plan: ResetPlan = ResetPlan()
    reset_applied: bool = False
    pre_reset_commit: str | None = None
    """The §12 pre-destruction snapshot this reset was allowed to proceed
    behind, pinned under `refs/wf/<root_id>/prereset/<activation_id>` BEFORE the
    first destructive command ran. `None` when no reset was applied. It is what
    makes every reset recoverable even where attribution erred — including the
    untracked content `stash create` cannot capture at all."""

    def carry_forward(self) -> PreconditionRecord:
        """The §3.2 trio as the bd carrier `record_precondition` writes."""
        return PreconditionRecord(
            pre_attempt_commit=self.pre_attempt_commit,
            reset_verified_commit=self.reset_verified_commit,
            pre_attempt_dirty_state=self.pre_attempt_dirty_state,
        )


class StaleFlag(BaseModel):
    """§8.2 stale flag: raised by the WRAPPER, with no model in the loop."""

    model_config = RECORD_MODEL

    activation_id: str
    raised_at: str
    last_activity_at: str
    stale_after_s: float


class SteerIntent(BaseModel):
    """§8.1 steer intent — persisted DURABLY before the child is signalled.

    Carries the continuation REQUEST and the instructions TEXT, not just the
    reason: a tick that finds this file has to be able to FINISH the steer, and
    a continuation it cannot reconstruct is a steer the human asked for that
    silently never happened. With the digest alone it could not be
    reconstructed — `Dispatcher` refuses a continuation with no instructions,
    so a §5.6 recovery that re-dispatched one had nothing to resume with.

    The prose lives HERE and nowhere else. The wrapper directory is the
    observation cache §P1 already allows to hold a runner's own bytes, while bd
    is durable project state a human reads; `instructions_digest` is the form
    §8.1 records where the prose must not go, and the only form that may ever be
    written there. Nothing writes even the digest to bd today — the `steered`
    close carries the steer's REASON, which is a sentence about the run, not the
    guidance itself.
    """

    model_config = RECORD_MODEL

    activation_id: str
    reason: str
    instructions: str
    instructions_digest: str
    requested_at: str
    continuation: MintRequest


# --- computed results ----------------------------------------------------


class LivenessProof(BaseModel):
    """Why the wrapper believes a process is (or is not) still ours (§5.3)."""

    model_config = RECORD_MODEL

    status: Liveness
    pid: int
    pid_present: bool
    boot_id_matches: bool
    start_time_matches: bool
    observed_start_time: str | None = None
    zombie: bool = False
    """`/proc` holds the pid in state `Z`: exited, not yet reaped. Recorded
    separately from `pid_present` because it is the one state that PROVES the
    process group id has not been recycled — the leader still occupies it."""
    read_error: str | None = None
    """Why `/proc` could not be read, when the answer is INDETERMINATE."""

    @property
    def alive(self) -> bool:
        """Alive AND provably the process the handle names."""
        return self.status is Liveness.ALIVE

    @property
    def identity_matches(self) -> bool:
        """Whether the pid the handle names is provably still the same process."""
        return self.boot_id_matches and self.start_time_matches


class ReapResult(BaseModel):
    """What `waitpid(WNOHANG)` could say about one pid — three answers, not two.

    "Still running" and "never ours to wait for" were both a bare `None`, and
    the second is a statement the KERNEL makes: ECHILD means this process is not
    the pid's parent, so its status is unknowable here rather than merely
    unobserved. §5.2's REATTACHED child is exactly that shape (§5.6).
    """

    model_config = RECORD_MODEL

    exit_code: int | None = None
    """The collected status, or `None` when there was none to collect."""
    ours: bool = True
    """False on ECHILD: this process cannot ever collect this pid's status."""


class TerminationProof(BaseModel):
    """§8.1: TERM → bounded wait → KILL, with death proven by handle identity."""

    model_config = RECORD_MODEL

    pid: int
    pgid: int
    signals_sent: tuple[str, ...] = ()
    confirmed_dead: bool = False
    proof: LivenessProof
    exit_code: int | None = None
    """The status `terminate` REAPED, since `terminate` is the one call that
    could. A status can be collected exactly once: the caller that reaped again
    for it always got `None`, and `None` is recorded as `EXIT_CODE_UNOBSERVED`
    (-256) — the one value the record is documented never to state for a death
    the wrapper itself carried out (§8.1, probed)."""


class MonitorResult(BaseModel):
    """One §8.2 observation cycle — file and proc inspection, zero tokens."""

    model_config = RECORD_MODEL

    verdict: MonitorVerdict
    observed_at: str
    last_activity_at: str
    log_size: int
    exit_code: int | None = None
    exit_reason: ExitReason | None = None
    stale: StaleFlag | None = None
    termination: TerminationProof | None = None


class OutcomeMarker(BaseModel):
    """The one schema-validated marker of `$WF_OUTCOME_FILE` (§6)."""

    model_config = RECORD_MODEL

    outcome: Outcome
    note: str | None = None


class EffectsManifest(BaseModel):
    """The declared-paths manifest of `$WF_EFFECTS_FILE` (§6, §7.5)."""

    model_config = RECORD_MODEL

    paths: tuple[str, ...] = ()


class VerifyResult(BaseModel):
    """One executed `verify` entry plus its §7.3 provenance decision."""

    model_config = RECORD_MODEL

    cmd: str
    exit_code: int
    script_digest: str
    pinned_digest: str | None
    provenance_ok: bool
    timed_out: bool = False
    program: str = ""
    """The absolute path that was hashed and executed — ONE resolution, so the
    digest and the exec cannot name different files (§7.3)."""
    error: str | None = None
    """Why the check could not be executed at all, when it could not."""
    attempts: int = 1
    """How many times the program ran; 2 means the first run was red and the
    rerun's exit code is the one recorded (cr-o85.34.14)."""
    output_tails: tuple[str, ...] = ()
    """One bounded tail of combined stdout+stderr per attempt, in attempt order.

    `len(output_tails) == attempts` whenever the program actually ran, and it is
    empty for a check that never ran at all — refused on provenance, or unable
    to start. A `fail_code` used to name an exit code and nothing else, so the
    cause had to be inferred from outside the record (cr-o85.34.12)."""


class CollectedExit(BaseModel):
    """The three §6 runner channels, read once, after the child exited."""

    model_config = RECORD_MODEL

    marker: OutcomeMarker | None
    marker_error: str | None = None
    effects: EffectsManifest | None = None
    effects_error: str | None = None
    artifact_paths: tuple[str, ...] = ()
    outputs_unsafe: tuple[UnsafeEntry, ...] = ()
    outputs_truncated: bool = False
    session_id: str | None = None
    duration_s: float | None = None


class CompletionEvidence(BaseModel):
    """The §7 verdict: computed evidence plus the outcome it actually supports.

    `outcome` is what the wrapper concluded, which is NOT the marker's claim
    whenever a clause fails — `fail_code` is fail-closed and never routed
    through a fallback (§2 'Outcome vocabulary').
    """

    model_config = RECORD_MODEL

    outcome: Outcome
    claimed_outcome: Outcome | None
    evidence: Evidence
    verify_results: tuple[VerifyResult, ...] = ()
    audit_flags: tuple[AuditFlag, ...] = ()
    reasons: tuple[str, ...] = ()
    branch: BranchAdvance | None = None


class RecoveryClassification(BaseModel):
    """The §5.6 classification of a dispatched-not-closed activation."""

    model_config = RECORD_MODEL

    case: RecoveryCase
    activation_id: str
    proof: LivenessProof | None = None
    exit_record: ExitRecord | None = None
    exit_from_file: bool = False
    evidence_complete: bool = False
    """Whether the §7 computation finished and left its evidence durably. An
    exit record with `evidence_complete = False` is "exited, evidence
    incomplete" — the crash landed inside the §7 computation, and §7 is
    recomputable, so it is re-run rather than treated as a case-3 loss."""
    steer_intent: SteerIntent | None = None
    log_tail: str = ""
    malformed: tuple[str, ...] = ()
    """Wrapper-dir artifacts that did not parse. Recorded, never raised: a
    truncated exit file must classify toward case 3, not crash-loop (drill 18)."""
