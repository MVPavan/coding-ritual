"""Audit flags that must survive malformed runner channels."""

from __future__ import annotations

import json
from pathlib import Path

from tests.test_supervisor_exit import DONE_MARKER, FEATURE_FILE, Lab
from workflow_interpreter.supervisor import AuditFlag


def test_invalid_marker_does_not_hide_unsafe_outputs(tmp_path: Path) -> None:
    """Unsafe output evidence is recorded before the marker's early verdict."""
    lab = Lab(tmp_path)
    outside = tmp_path / "outside"
    outside.write_text("secret\n", encoding="utf-8")
    (lab.paths.artifacts(lab.activation.activation_id) / "unsafe").symlink_to(outside)

    completion = lab.observe().completion

    flags = completion.audit_flags
    assert AuditFlag.MARKER_INVALID in flags
    assert AuditFlag.OUTPUTS_UNSAFE in flags
    assert "unsafe output unsafe (symlink)" in completion.reasons


def test_completion_reuse_returns_empty_collection_and_unknown_usage(
    tmp_path: Path,
) -> None:
    """Completion reuse currently reconstructs neither channels nor usage."""
    lab = Lab(tmp_path)
    lab.commit_work()
    lab.marker(json.dumps(DONE_MARKER))
    lab.effects(FEATURE_FILE)
    first = lab.observe()

    replayed = lab.observer.replay(
        lab.reload(),
        lab.node,
        lab.profile,
        first.exit_record,
        pinned_digests=lab.pins(),
    )

    assert replayed.collected.marker is None
    assert replayed.usage.known is False
