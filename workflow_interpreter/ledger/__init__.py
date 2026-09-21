"""The run ledger: one SQLite-format database per repository (run-ledger §3).

What a caller outside this package needs is here — open a ledger, build a store
over it, export and import a task, and the paths and fence those three agree
on. The schema, the row mapping and the SQL stay private to the package.
"""

from __future__ import annotations

from workflow_interpreter.ledger.database import LedgerDatabase, open_ledger
from workflow_interpreter.ledger.errors import (
    LedgerExportError,
    LedgerFenceBusy,
    LedgerIdentityError,
    LedgerSchemaError,
    LedgerWriteUnsupported,
)
from workflow_interpreter.ledger.export import (
    export_task,
    import_export,
    import_exports,
    write_export,
    write_landed_export,
)
from workflow_interpreter.ledger.fence import LedgerFence
from workflow_interpreter.ledger.paths import (
    ensure_fence_dir,
    export_path,
    fence_path,
    ledger_path,
)
from workflow_interpreter.ledger.reconcile import (
    ATTENTION_LABEL,
    AttentionReconciler,
    ReconcileResult,
    task_lock_path,
)
from workflow_interpreter.ledger.store import LedgerStore

__all__ = [
    "ATTENTION_LABEL",
    "AttentionReconciler",
    "LedgerDatabase",
    "LedgerExportError",
    "LedgerFence",
    "LedgerFenceBusy",
    "LedgerIdentityError",
    "LedgerSchemaError",
    "LedgerStore",
    "LedgerWriteUnsupported",
    "ReconcileResult",
    "ensure_fence_dir",
    "export_path",
    "export_task",
    "fence_path",
    "import_export",
    "import_exports",
    "ledger_path",
    "open_ledger",
    "task_lock_path",
    "write_export",
    "write_landed_export",
]
