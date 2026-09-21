"""Validation for bead identifiers that are also used as path components.

The grammar itself lives in `contracts/run_identity.py` — ONE expression, so
that a component this module accepts is one the record model, the ledger's
mint and `scripts/verify-debrief.sh` accept too (§3.7, R8). `InvalidIdentifier`
is re-exported rather than redefined for the same reason: callers catch one
class however the refusal was reached.
"""

from pathlib import Path

from workflow_interpreter.contracts.run_identity import (
    ComponentKind,
    InvalidIdentifier,
    safe_component,
)
from workflow_interpreter.inspector.paths import WrapperPaths

__all__ = ["InvalidIdentifier", "activation_dir", "validate_bead_id"]


def validate_bead_id(value: str) -> str:
    """Return one safe single-component bead id or refuse it before path use."""
    return safe_component(value, kind=ComponentKind.BEAD)


def activation_dir(paths: WrapperPaths, activation_id: str) -> Path:
    """Derive an activation directory only after proving wrapper-root containment."""
    root = paths.instance_dir.resolve()
    candidate = (root / validate_bead_id(activation_id)).resolve()
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise InvalidIdentifier(
            f"activation path escapes wrapper root: {activation_id!r}"
        ) from exc
    return candidate
