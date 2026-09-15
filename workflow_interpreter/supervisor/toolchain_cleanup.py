"""Delete disposable private tools only after durable close and death proof."""

import shutil

import structlog

from workflow_interpreter.bdio import ActivationRecord
from workflow_interpreter.bdio.client import STATUS_CLOSED
from workflow_interpreter.supervisor import procfs
from workflow_interpreter.supervisor import toolchain_constants as tc
from workflow_interpreter.supervisor.errors import SupervisorError
from workflow_interpreter.supervisor.models import LaunchReceipt, Liveness
from workflow_interpreter.supervisor.paths import WrapperPaths, fsync_dir, read_record


def cleanup_toolchain(paths: WrapperPaths, activation: ActivationRecord) -> str | None:
    """Retry close-time cleanup; report failures while keeping provenance intact.

    A receipt can hold the handle missing from bd after a dispatch crash. Missing
    or malformed identity with a nonempty ledger cannot establish runner death.
    No cache bytes or symlink targets are executed or followed during deletion.
    """
    if not activation.metadata.is_completed or activation.bead.status != STATUS_CLOSED:
        return None
    directory = paths.activation_dir(activation.activation_id)
    private = directory / tc.TOOLCHAIN
    try:
        targets = tuple(
            path
            for path in (private, *directory.glob(tc.STAGING_PREFIX + "*"))
            if path.exists() or path.is_symlink()
        )
        if not targets:
            return None
        if directory.resolve() != directory or any(
            path.is_symlink() for path in targets
        ):
            raise OSError(tc.MSG_CLEANUP_LINK)
        receipt = read_record(paths.receipt(activation.activation_id), LaunchReceipt)
        handles = [activation.metadata.handle]
        if receipt is not None:
            handles.append(receipt.handle)
        identified = [handle for handle in handles if handle is not None]
        ledger = paths.ledger(activation.activation_id)
        if not identified and ledger.exists() and ledger.stat().st_size:
            raise OSError(tc.MSG_NO_IDENTITY)
        for handle in identified:
            proof = procfs.prove_liveness(paths.config, handle)
            if proof.status not in (Liveness.DEAD, Liveness.IDENTITY_MISMATCH):
                raise OSError(tc.MSG_NOT_DEAD)
        for target in targets:
            shutil.rmtree(target)
        fsync_dir(directory)
    except (OSError, SupervisorError) as exc:
        error = tc.MSG_CLEANUP.format(error=exc)
        structlog.get_logger(__name__).warning(
            tc.LOG_CLEANUP,
            activation_id=activation.activation_id,
            error=error,
        )
        return error
    return None
