"""The inspector wrapper — the deterministic machinery around one activation.

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

`Inspector` (`run.py`) is the composition root and the entry point a caller
wants: one process owning one activation from dispatch through `exit-recorded`,
alive for the child's lifetime (§5.3). The individual pieces stay public for
recovery, which drives them out of order by nature.

Linux-only: `/proc`, `boot_id`, process groups, `fork`/`setsid` and `flock`.

Not implemented here: crew PROFILES (phase 4 — this package declares the §6
Protocol only) and the foreman tick loop (phase 5).
"""

from workflow_interpreter.inspector.artifact import INSTANCE_BRANCH_REF
from workflow_interpreter.inspector.band import BandLock
from workflow_interpreter.inspector.branch import BranchAdvance, BranchAdvanceOutcome
from workflow_interpreter.inspector.channels import (
    pin_verifier_digests,
    pinned_verifier_digests,
    verifier_digest_key,
)
from workflow_interpreter.inspector.clock import Clock, SystemClock, to_iso
from workflow_interpreter.inspector.config import InspectorConfig
from workflow_interpreter.inspector.errors import (
    BandNotHeld,
    DirtyTreeRefused,
    ExecLedgerError,
    ForkBarrierAbortError,
    ForkBarrierError,
    GitCommandError,
    InspectorConfigError,
    InspectorError,
    LockUnavailable,
    PreconditionRefused,
    SnapshotFailed,
    TerminationFailed,
    VerifyTreeError,
    WrapperDirError,
)
from workflow_interpreter.inspector.exit import ExitObservation, ExitObserver
from workflow_interpreter.inspector.gitio import Git
from workflow_interpreter.inspector.launch import (
    Dispatcher,
    DispatchResult,
    ForkBarrierLauncher,
    Precondition,
    TaskBuilder,
)
from workflow_interpreter.inspector.models import (
    EXIT_CODE_UNOBSERVED,
    AuditFlag,
    CollectedExit,
    CompletionEvidence,
    ConfirmedPath,
    CrewAttribution,
    DirtyEntry,
    DirtySnapshot,
    EffectsManifest,
    EntryKind,
    ExecLedgerEntry,
    ExitReason,
    HumanConfirmation,
    LaunchOutcome,
    LaunchReceipt,
    LaunchReceiptState,
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
    StaleFlag,
    SteerIntent,
    TerminationProof,
    VerifyResult,
    WorkspaceRecord,
)
from workflow_interpreter.inspector.monitor import Limits, Monitor
from workflow_interpreter.inspector.paths import ExecLedger, WrapperPaths
from workflow_interpreter.inspector.profile import (
    ChildLauncher,
    CrewChannels,
    CrewCommand,
    CrewEvent,
    EventType,
    Profile,
    TaskSpec,
    TerminalEnvelope,
    channels_for,
)
from workflow_interpreter.inspector.recover import (
    EVIDENCE_EXIT_UNOBSERVED,
    Recovery,
    RecoveryResolution,
)
from workflow_interpreter.inspector.run import InspectionResult, Inspector
from workflow_interpreter.inspector.steer import Steerer, SteerResult
from workflow_interpreter.inspector.verify import VerifyTree, run_checks
from workflow_interpreter.inspector.workspace import (
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
    "INSTANCE_BRANCH_REF",
    "AuditFlag",
    "BandLock",
    "BandNotHeld",
    "BranchAdvance",
    "BranchAdvanceOutcome",
    "ChildLauncher",
    "Clock",
    "CollectedExit",
    "CompletionEvidence",
    "ConfirmedPath",
    "CrewAttribution",
    "CrewChannels",
    "CrewCommand",
    "CrewEvent",
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
    "ForkBarrierAbortError",
    "ForkBarrierError",
    "ForkBarrierLauncher",
    "Git",
    "GitCommandError",
    "HumanConfirmation",
    "InspectionResult",
    "Inspector",
    "InspectorConfig",
    "InspectorConfigError",
    "InspectorError",
    "LaunchOutcome",
    "LaunchReceipt",
    "LaunchReceiptState",
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
    "Profile",
    "ReapResult",
    "Recovery",
    "RecoveryCase",
    "RecoveryClassification",
    "RecoveryResolution",
    "ResetPlan",
    "SnapshotFailed",
    "StaleFlag",
    "SteerIntent",
    "SteerResult",
    "Steerer",
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
