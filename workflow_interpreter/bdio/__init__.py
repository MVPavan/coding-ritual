"""The typed bd wrapper — the only path through which anything writes to bd.

Phase 2 of the workflow interpreter (spec v0.3 §0.1, §3, §4, §9, §10, §11).
`WorkflowStore` is the typed operations, `WorkflowReads` the read vocabulary,
`GateVerifier` the §9 human-gate check; `wire` holds the carriers, `mint` the
§3.2 fact derivation and `bounds` the pre-mint predicates.

`BdClient` is deliberately NOT exported. It is the transport, its write
methods are package-private, and a caller holding one could close a bead
without any of the §5.1/§9 rules that make this package worth having; a
`WorkflowStore` plus its `.reads` facade is the entire public surface.

`VerifiedApproval` is not exported either: it is the TOKEN saying "§9 already
verified this", and the only thing that should ever hold one is the code
between `GateVerifier.verify` and the write it authorizes (§0.3).

Everything a caller needs to CALL a write method is exported, though — every
request and value type in a public signature, plus `WorkflowStore.from_config`
so a sealed transport does not mean an unbuildable store (phase-2 r3). That
includes `Breaker`, which `Evidence` carries: a value type reachable only by
importing `bdio.wire` is a sealed boundary with a hole in it.
"""

from workflow_interpreter.bdio.api import WorkflowStore
from workflow_interpreter.bdio.bounds import BoundKind, BoundRefusal
from workflow_interpreter.bdio.capabilities import ArtifactReader, BranchHeadReader
from workflow_interpreter.bdio.config import BdConfig, SigningConfig
from workflow_interpreter.bdio.errors import (
    BdCommandError,
    BdConfigError,
    BdioError,
    BdOutputError,
    BdTimeoutError,
    BoundEvaluationError,
    BoundExceededError,
    CanaryFailedError,
    CarrierIntegrityError,
    ForbiddenInvocationError,
    GateVerificationError,
    LifecycleConflictError,
    LossyWriteError,
    NonceReplayError,
    PayloadMismatchError,
    PinnedGraphMismatchError,
    SignatureRefusedError,
    SignerNotAllowedError,
    StaleApprovalError,
)
from workflow_interpreter.bdio.mint import MintFacts
from workflow_interpreter.bdio.reads import WorkflowReads
from workflow_interpreter.bdio.records import (
    ActivationRecord,
    CanaryResult,
    GateRecord,
    MintResult,
    RootRecord,
)
from workflow_interpreter.bdio.signing import (
    AllowedSigner,
    BoundMutation,
    GateArtifact,
    GatePayload,
    GateVerifier,
    canonical_payload_bytes,
)
from workflow_interpreter.bdio.wire import (
    ArtifactIdentity,
    BindsMode,
    BoundSetting,
    Breaker,
    ConfigSource,
    Deviation,
    EventPayload,
    Evidence,
    ExitRecord,
    GateOpenRequest,
    GateReason,
    GateState,
    GateType,
    InputBinding,
    InstanceInput,
    Lifecycle,
    MintReason,
    MintRequest,
    NodeSetting,
    PreconditionRecord,
    ProcessHandle,
    ResolvedSetting,
    StaleFlagRecord,
    Usage,
    VerifyOutcome,
    WfKind,
    resolved_settings,
)
from workflow_interpreter.schema.models import Outcome

__all__ = [
    "ActivationRecord",
    "AllowedSigner",
    "ArtifactIdentity",
    "ArtifactReader",
    "BdCommandError",
    "BdConfig",
    "BdConfigError",
    "BdOutputError",
    "BdTimeoutError",
    "BdioError",
    "BindsMode",
    "BoundEvaluationError",
    "BoundExceededError",
    "BoundKind",
    "BoundMutation",
    "BoundRefusal",
    "BoundSetting",
    "BranchHeadReader",
    "Breaker",
    "CanaryFailedError",
    "CanaryResult",
    "CarrierIntegrityError",
    "ConfigSource",
    "Deviation",
    "EventPayload",
    "Evidence",
    "ExitRecord",
    "ForbiddenInvocationError",
    "GateArtifact",
    "GateOpenRequest",
    "GatePayload",
    "GateReason",
    "GateRecord",
    "GateState",
    "GateType",
    "GateVerificationError",
    "GateVerifier",
    "InputBinding",
    "InstanceInput",
    "Lifecycle",
    "LifecycleConflictError",
    "LossyWriteError",
    "MintFacts",
    "MintReason",
    "MintRequest",
    "MintResult",
    "NodeSetting",
    "NonceReplayError",
    "Outcome",
    "PayloadMismatchError",
    "PinnedGraphMismatchError",
    "PreconditionRecord",
    "ProcessHandle",
    "ResolvedSetting",
    "RootRecord",
    "SignatureRefusedError",
    "SignerNotAllowedError",
    "SigningConfig",
    "StaleApprovalError",
    "StaleFlagRecord",
    "Usage",
    "VerifyOutcome",
    "WfKind",
    "WorkflowReads",
    "WorkflowStore",
    "canonical_payload_bytes",
    "resolved_settings",
]
