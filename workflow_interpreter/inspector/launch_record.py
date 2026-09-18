"""Crash-atomic launch identity, including RPC ownership before vendor exec."""

from enum import StrEnum

from pydantic import BaseModel, ConfigDict

from workflow_interpreter.bdio import ProcessHandle
from workflow_interpreter.contracts.execution import ExecutionGrants, ToolNetwork
from workflow_interpreter.contracts.transport import RunnerTransport
from workflow_interpreter.supervisor.sandbox import SandboxMode
from workflow_interpreter.supervisor.toolchain_models import SeedReceipt

RECORD_MODEL = ConfigDict(frozen=True, extra="forbid", arbitrary_types_allowed=False)


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

    transport: RunnerTransport = RunnerTransport.EVENT_LOG
    owner: ProcessHandle | None = None
    vendor_state: str | None = None
    launch_id: str
    root_id: str
    activation_id: str
    argv: tuple[str, ...]
    """The WRAPPED argv under `sandbox = bwrap`: `handle.pid` names `bwrap`, not
    the vendor, so the inner argv would describe a process this receipt's handle
    does not name (plan §2)."""
    cwd: str
    handle: ProcessHandle
    seed_receipts: tuple[SeedReceipt, ...] = ()
    execution_grants: ExecutionGrants | None = None
    tool_network: ToolNetwork | None = None
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
