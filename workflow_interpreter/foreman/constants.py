"""Names and immutable vocabulary owned by the foreman."""

from typing import Final

from workflow_interpreter.bdio.constants import (
    DEVIATION_INSTANCE_BRANCH_DIVERGED,
    DEVIATION_PRECONDITION_REFUSED,
    DEVIATION_UNDECLARED_EFFECTS_ACCEPTED,
    DEVIATION_UNDECLARED_EFFECTS_DISCARDED,
)
from workflow_interpreter.supervisor import INSTANCE_BRANCH_REF

__all__ = [
    "DEVIATION_INSTANCE_BRANCH_DIVERGED",
    "DEVIATION_PRECONDITION_REFUSED",
    "DEVIATION_UNDECLARED_EFFECTS_ACCEPTED",
    "DEVIATION_UNDECLARED_EFFECTS_DISCARDED",
    "DISPATCH_REQUEST",
    "EFFECTS_NODE",
    "FORCED_FIRST_REJECT",
    "GATES_DIR",
    "HALT_AUDIT",
    "HALT_BRANCH_DIVERGED",
    "HALT_CEILING",
    "HALT_FAIL_CLOSED",
    "HALT_FAIL_CODE",
    "HALT_INDETERMINATE",
    "HALT_MISSING_COMMIT",
    "HALT_NODE",
    "HALT_PRECONDITION_REFUSED",
    "INSTANCE_BRANCH",
    "MAX_TRANSCRIPT_BYTES",
    "NO_ARTIFACT_OID",
    "WRAPPER_HANDLE",
    "WRAPPER_LOCK",
]

EFFECTS_NODE: Final[str] = "effects"
HALT_NODE: Final[str] = "halt"
NO_ARTIFACT_OID: Final[str] = "0" * 40
WRAPPER_LOCK: Final[str] = "wrapper.lock"
DISPATCH_REQUEST: Final[str] = "dispatch-request.json"
WRAPPER_HANDLE: Final[str] = "wrapper.json"
FORCED_FIRST_REJECT: Final[str] = (
    "§13 test switch: this is the first review round of the instance — return "
    "the outcome `reject` with findings, whatever the artifact looks like"
)
GATES_DIR: Final[str] = "gates"
MAX_TRANSCRIPT_BYTES: Final[int] = 4096
INSTANCE_BRANCH: Final[str] = INSTANCE_BRANCH_REF
HALT_AUDIT: Final[str] = "audit:{reason}"
HALT_MISSING_COMMIT: Final[str] = "missing_commit intended_base_commit {commit}"
HALT_CEILING: Final[str] = "ceiling:{detail}"
HALT_INDETERMINATE: Final[str] = "indeterminate:{detail}"
HALT_FAIL_CLOSED: Final[str] = "fail_closed:{reason}"
HALT_FAIL_CODE: Final[str] = "fail_code:{node}:{activation_id}"
HALT_BRANCH_DIVERGED: Final[str] = "instance_branch_diverged:{node}:{activation_id}"
HALT_PRECONDITION_REFUSED: Final[str] = "precondition_refused:{node}:{activation_id}"
