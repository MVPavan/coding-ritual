"""The supervisor wrapper — the deterministic machinery around one activation.

Phase 3 of the workflow interpreter (spec v0.3 §5, §6, §7, §8, §12). It sits
between the foreman's dispatch DECISION and the bd record of what happened, and
it owns everything about that stretch that must not depend on a model being
awake: the §5.2 fork barrier and exec ledger, the §5.4 worktree precondition,
the §8.2 monitoring loop, the §8.1 steer order, the §7 completion evidence and
the §5.6 recovery classification.

Two boundaries hold throughout:

- **Every bd write goes through `bdio`** (§0.1). Nothing here builds a bd
  invocation, and the only bd objects it constructs are the typed carriers
  `WorkflowStore` accepts.
- **Every git operation is local and confined** to a working tree the wrapper
  owns (`gitio`'s closed subcommand set has no `push`, `remote` or `fetch`).

`Supervisor` (`run.py`) is the composition root and the entry point a caller
wants: one process owning one activation from dispatch through `exit-recorded`,
alive for the child's lifetime (§5.3). The individual pieces stay public for
recovery, which drives them out of order by nature.

Linux-only: `/proc`, `boot_id`, process groups, `fork`/`setsid` and `flock`.

Not implemented here: runner PROFILES (phase 4 — this package declares the §6
Protocol only) and the foreman tick loop (phase 5).
"""

from workflow_interpreter.supervisor.band import BandLock
from workflow_interpreter.supervisor.channels import (
    pin_verifier_digests,
    pinned_verifier_digests,
    verifier_digest_key,
)
from workflow_interpreter.supervisor.clock import Clock, SystemClock, to_iso
from workflow_interpreter.supervisor.config import SupervisorConfig
from workflow_interpreter.supervisor.errors import (
    DirtyTreeRefused,
    ExecLedgerError,
    ForkBarrierError,
    GitCommandError,
    LockUnavailable,
    PreconditionRefused,
    SupervisorConfigError,
    SupervisorError,
    TerminationFailed,
    VerifyTreeError,
    WrapperDirError,
)
from workflow_interpreter.supervisor.exit import ExitObservation, ExitObserver
from workflow_interpreter.supervisor.gitio import Git
from workflow_interpreter.supervisor.launch import (
    Dispatcher,
    DispatchResult,
    ForkBarrierLauncher,
    Precondition,
    TaskBuilder,
)
from workflow_interpreter.supervisor.models import (
    EXIT_CODE_UNOBSERVED,
    AuditFlag,
    CollectedExit,
    CompletionEvidence,
    ConfirmedPath,
    DirtyEntry,
    DirtySnapshot,
    EffectsManifest,
    EntryKind,
    ExecLedgerEntry,
    ExitReason,
    HumanConfirmation,
    LaunchOutcome,
    LaunchReceipt,
    Liveness,
    LivenessProof,
    MonitorResult,
    MonitorVerdict,
    OutcomeMarker,
    PinOutcome,
    PinResult,
    PreconditionRecord,
    PreconditionResult,
    ReapResult,
    RecoveryCase,
    RecoveryClassification,
    ResetPlan,
    RunnerAttribution,
    StaleFlag,
    SteerIntent,
    TerminationProof,
    VerifyResult,
    WorkspaceRecord,
)
from workflow_interpreter.supervisor.monitor import Limits, Monitor
from workflow_interpreter.supervisor.paths import ExecLedger, WrapperPaths
from workflow_interpreter.supervisor.profile import (
    Capabilities,
    ChildLauncher,
    EventType,
    InspectResult,
    ProcessStatus,
    Profile,
    RunnerChannels,
    RunnerCommand,
    RunnerEvent,
    TaskSpec,
    TerminalEnvelope,
    channels_for,
)
from workflow_interpreter.supervisor.recover import (
    EVIDENCE_EXIT_UNOBSERVED,
    Recovery,
    RecoveryResolution,
)
from workflow_interpreter.supervisor.run import SupervisionResult, Supervisor
from workflow_interpreter.supervisor.steer import Steerer, SteerResult
from workflow_interpreter.supervisor.verify import VerifyTree, run_checks
from workflow_interpreter.supervisor.workspace import (
    Workspace,
    activation_ref,
    decode_dirty_state,
    encode_dirty_state,
    namespace_prefix,
    namespaced_ref,
)

__all__ = [
    "EVIDENCE_EXIT_UNOBSERVED",
    "EXIT_CODE_UNOBSERVED",
    "AuditFlag",
    "BandLock",
    "Capabilities",
    "ChildLauncher",
    "Clock",
    "CollectedExit",
    "CompletionEvidence",
    "ConfirmedPath",
    "DirtyEntry",
    "DirtySnapshot",
    "DirtyTreeRefused",
    "DispatchResult",
    "Dispatcher",
    "EffectsManifest",
    "EntryKind",
    "EventType",
    "ExecLedger",
    "ExecLedgerEntry",
    "ExecLedgerError",
    "ExitObservation",
    "ExitObserver",
    "ExitReason",
    "ForkBarrierError",
    "ForkBarrierLauncher",
    "Git",
    "GitCommandError",
    "HumanConfirmation",
    "InspectResult",
    "LaunchOutcome",
    "LaunchReceipt",
    "Limits",
    "Liveness",
    "LivenessProof",
    "LockUnavailable",
    "Monitor",
    "MonitorResult",
    "MonitorVerdict",
    "OutcomeMarker",
    "PinOutcome",
    "PinResult",
    "Precondition",
    "PreconditionRecord",
    "PreconditionRefused",
    "PreconditionResult",
    "ProcessStatus",
    "Profile",
    "ReapResult",
    "Recovery",
    "RecoveryCase",
    "RecoveryClassification",
    "RecoveryResolution",
    "ResetPlan",
    "RunnerAttribution",
    "RunnerChannels",
    "RunnerCommand",
    "RunnerEvent",
    "StaleFlag",
    "SteerIntent",
    "SteerResult",
    "Steerer",
    "SupervisionResult",
    "Supervisor",
    "SupervisorConfig",
    "SupervisorConfigError",
    "SupervisorError",
    "SystemClock",
    "TaskBuilder",
    "TaskSpec",
    "TerminalEnvelope",
    "TerminationFailed",
    "TerminationProof",
    "VerifyResult",
    "VerifyTree",
    "VerifyTreeError",
    "Workspace",
    "WorkspaceRecord",
    "WrapperDirError",
    "WrapperPaths",
    "activation_ref",
    "channels_for",
    "decode_dirty_state",
    "encode_dirty_state",
    "namespace_prefix",
    "namespaced_ref",
    "pin_verifier_digests",
    "pinned_verifier_digests",
    "run_checks",
    "to_iso",
    "verifier_digest_key",
]
