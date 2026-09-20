"""The tracker port and its adapters (store-restructure §3.3, R2).

What humans read — title, brief, status, one attention flag, one closing
comment — behind four operations and a declared capability set. The ledger is
the truth; everything here is the mirror.

Only the CONTRACTOR imports this package. The foreman, the inspector and the
crew never do.
"""

from workflow_interpreter.tracker.bd import BdTracker
from workflow_interpreter.tracker.constants import (
    DEFAULT_CAPABILITIES,
    IntentKind,
    ResultKind,
    TrackerCapability,
    TrackerFlag,
    WorkItemStatus,
)
from workflow_interpreter.tracker.errors import TrackerRefused, TrackerUnavailable
from workflow_interpreter.tracker.file import FileTracker
from workflow_interpreter.tracker.intents import (
    Annotate,
    Applied,
    Claim,
    Close,
    Conflict,
    SetFlag,
    TrackerIntent,
    TrackerResult,
    Unknown,
)
from workflow_interpreter.tracker.models import Blocker, TrackerRef, WorkItem
from workflow_interpreter.tracker.null import NullTracker
from workflow_interpreter.tracker.port import TrackerPort

__all__ = [
    "DEFAULT_CAPABILITIES",
    "Annotate",
    "Applied",
    "BdTracker",
    "Blocker",
    "Claim",
    "Close",
    "Conflict",
    "FileTracker",
    "IntentKind",
    "NullTracker",
    "ResultKind",
    "SetFlag",
    "TrackerCapability",
    "TrackerFlag",
    "TrackerIntent",
    "TrackerPort",
    "TrackerRef",
    "TrackerRefused",
    "TrackerResult",
    "TrackerUnavailable",
    "Unknown",
    "WorkItem",
    "WorkItemStatus",
]
