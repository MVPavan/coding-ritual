"""Git-backed pre-routing reconciliation for a pinned workflow root."""

from collections.abc import Iterable
from pathlib import Path

from pydantic import BaseModel, ConfigDict

from workflow_interpreter.bdio import ActivationRecord, RootRecord
from workflow_interpreter.foreman.constants import INSTANCE_BRANCH
from workflow_interpreter.supervisor.gitio import Git


class Reconciliation(BaseModel):
    """A read-only answer that either permits routing or names its stop."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    stalled: str | None = None
    missing_commit: str | None = None


def reconcile(
    root: RootRecord,
    activations: Iterable[ActivationRecord],
    git: Git,
    *,
    repo_root: Path,
) -> Reconciliation:
    """Ensure every pinned commit and the instance branch still exists."""
    base = root.metadata.instance_base_commit
    if base is None or not git.commit_exists(base, cwd=repo_root):
        return Reconciliation(
            stalled="instance base commit is missing", missing_commit=base
        )
    if (
        git.ref_target(INSTANCE_BRANCH.format(root_id=root.root_id), cwd=repo_root)
        is None
    ):
        return Reconciliation(stalled="instance branch missing")
    for activation in activations:
        commit = activation.metadata.intended_base_commit
        if not git.commit_exists(commit, cwd=repo_root):
            return Reconciliation(
                stalled=f"missing_commit intended_base_commit {commit}",
                missing_commit=commit,
            )
    return Reconciliation()
