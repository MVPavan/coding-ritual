"""Delete disposable private tools only after durable close and death proof."""

import shutil
from enum import StrEnum

import structlog
from pydantic import BaseModel, ConfigDict

from workflow_interpreter.bdio import ActivationRecord
from workflow_interpreter.bdio.rows import STATUS_CLOSED
from workflow_interpreter.inspector import procfs
from workflow_interpreter.inspector import toolchain_constants as tc
from workflow_interpreter.inspector.errors import InspectorError
from workflow_interpreter.inspector.models import LaunchReceipt, Liveness
from workflow_interpreter.inspector.paths import (
    WrapperPaths,
    fsync_dir,
    read_record,
    write_record,
)


class CleanupStatus(StrEnum):
    """State retained until disposable activation files can be removed."""

    PENDING = "pending"


class CleanupPending(BaseModel):
    """Durable activation-local reason for a deferred disposal attempt."""

    model_config = ConfigDict(frozen=True, extra="forbid")
    status: CleanupStatus = CleanupStatus.PENDING
    reason: str


def _pending(paths: WrapperPaths, activation: ActivationRecord, reason: str) -> None:
    """Retain a retry marker without changing the closed activation outcome."""
    write_record(
        paths.activation_dir(activation.activation_id) / tc.CLEANUP_PENDING,
        CleanupPending(reason=reason),
    )


def death_refusal(paths: WrapperPaths, activation: ActivationRecord) -> str | None:
    """Why this activation's bytes may NOT be deleted yet, or `None` if they may.

    The one liveness question every disposal asks: a receipt can hold the
    handle missing from the store after a dispatch crash, and missing or
    malformed identity with a nonempty ledger cannot establish crew death.

    PUBLIC because the terminal cleanup in `foreman/tick.py` must ask the same
    question about every activation of a root before it removes the worktree,
    the verify tree or any scratch — one decision, one implementation, rather
    than a second liveness rule that could drift from this one (§3.9).
    """
    try:
        receipt = read_record(paths.receipt(activation.activation_id), LaunchReceipt)
    except InspectorError as exc:
        return str(exc)
    handles = [activation.metadata.handle]
    if receipt is not None:
        handles.append(receipt.handle)
    identified = [handle for handle in handles if handle is not None]
    ledger = paths.ledger(activation.activation_id)
    if not identified and ledger.exists() and ledger.stat().st_size:
        return tc.MSG_NO_IDENTITY
    for handle in identified:
        proof = procfs.prove_liveness(paths.config, handle)
        if proof.status not in (Liveness.DEAD, Liveness.IDENTITY_MISMATCH):
            return tc.MSG_NOT_DEAD
    return None


def cleanup_scratch(paths: WrapperPaths, activation: ActivationRecord) -> None:
    """Delete one activation's `channels/scratch` at TERMINAL (run-ledger §3.9).

    Over 99 % of a run folder is scratch, and it is the crew's `TMPDIR`: it
    holds nothing the record needs once the outcome, findings and evidence are
    stored. Deleted here rather than at activation close because §3.9 makes
    every run-folder deletion wait for the durable record — for a contractor task,
    for its export — and under the same proven-death guard the toolchain
    disposal uses, because the bytes belong to a process that may still exist.

    Idempotent and best effort: a refusal leaves the directory and the retry
    marker for the next tick, which is why nothing here raises.
    """
    if not activation.metadata.is_completed or activation.status != STATUS_CLOSED:
        return
    scratch = paths.scratch(activation.activation_id)
    try:
        if not scratch.exists() and not scratch.is_symlink():
            return
        if scratch.is_symlink() or scratch.resolve() != scratch:
            raise OSError(tc.MSG_CLEANUP_LINK)
        refusal = death_refusal(paths, activation)
        if refusal is not None:
            _pending(paths, activation, refusal)
            return
        shutil.rmtree(scratch)
        fsync_dir(scratch.parent)
    except (OSError, InspectorError) as exc:
        structlog.get_logger(__name__).warning(
            tc.LOG_CLEANUP,
            activation_id=activation.activation_id,
            error=tc.MSG_CLEANUP.format(error=exc),
        )


def cleanup_toolchain(paths: WrapperPaths, activation: ActivationRecord) -> None:
    """Retry close-time cleanup; report failures while keeping provenance intact.

    A receipt can hold the handle missing from bd after a dispatch crash. Missing
    or malformed identity with a nonempty ledger cannot establish crew death.
    No cache bytes or symlink targets are executed or followed during deletion.
    """
    if not activation.metadata.is_completed or activation.status != STATUS_CLOSED:
        return
    directory = paths.activation_dir(activation.activation_id)
    private = directory / tc.TOOLCHAIN
    try:
        if directory.resolve() != directory:
            raise OSError(tc.MSG_CLEANUP_LINK)
        targets = tuple(
            path
            for path in (private, *directory.glob(tc.STAGING_PREFIX + "*"))
            if path.exists() or path.is_symlink()
        )
        if not targets:
            (directory / tc.CLEANUP_PENDING).unlink(missing_ok=True)
            return
        if any(path.is_symlink() for path in targets):
            raise OSError(tc.MSG_CLEANUP_LINK)
        refusal = death_refusal(paths, activation)
        if refusal is not None:
            _pending(paths, activation, refusal)
            return
        for target in targets:
            shutil.rmtree(target)
        (directory / tc.CLEANUP_PENDING).unlink(missing_ok=True)
        fsync_dir(directory)
    except (OSError, InspectorError) as exc:
        error = tc.MSG_CLEANUP.format(error=exc)
        structlog.get_logger(__name__).warning(
            tc.LOG_CLEANUP,
            activation_id=activation.activation_id,
            error=error,
        )
