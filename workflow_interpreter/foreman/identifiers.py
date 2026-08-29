"""Validation for bead identifiers that are also used as path components."""

import re
from pathlib import Path

from workflow_interpreter.supervisor.paths import WrapperPaths

_BEAD_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*\Z")


def validate_bead_id(value: str) -> str:
    """Return one safe single-component bead id or refuse it before path use."""
    if not _BEAD_ID.fullmatch(value):
        raise ValueError(f"invalid bead id: {value!r}")
    return value


def activation_dir(paths: WrapperPaths, activation_id: str) -> Path:
    """Derive an activation directory only after proving wrapper-root containment."""
    root = paths.instance_dir.resolve()
    candidate = (root / validate_bead_id(activation_id)).resolve()
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise ValueError(
            f"activation path escapes wrapper root: {activation_id!r}"
        ) from exc
    return candidate
