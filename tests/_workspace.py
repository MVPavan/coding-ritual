"""Shared wiring for the two `Workspace` families (not a test module).

`Workspace` answers two different questions — may this working TREE be reset
(§5.4, §12), and may this COMMIT be claimed (§7.4) — and each has its own test
file. The fixture, the throwaway repo it wires up and the small builders both
families need live here, so neither file imports the other and the pair cannot
drift into two ideas of what an in-repo instance is.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from tests._supervisor import (
    IMPLEMENT,
    FrozenClock,
    entry_mint,
    head_of,
    make_config,
    make_git,
    make_paths,
    make_repo,
    make_root,
    make_store,
    make_workspace,
    node_of,
)
from workflow_interpreter.bdio import ActivationRecord, PreconditionRecord
from workflow_interpreter.schema.models import IsolationMode, Node
from workflow_interpreter.supervisor import (
    ConfirmedPath,
    DirtyEntry,
    DirtySnapshot,
    HumanConfirmation,
    RunnerAttribution,
    encode_dirty_state,
)

CONFIRMED_AT = "2026-08-25T12:00:00Z"
HUMAN_FILE = "src/human.py"
HUMAN_TEXT = "# a human was here\n"
HUMAN_COMMITTED = "docs/chapter.md"
RUNNER_FILE = "src/runner.py"
TRACKED_FILE = "src/feature.py"
TRACKED_ORIGINAL = "value = 1\n"
SCRATCH_FILE = "src/scratch.txt"
SCRATCH_TEXT = "hours of nobody's-sure-whose work\n"
STRANGER_ACTIVATION = "wf-999"
NESTED_DIR = "vendorwork"
NESTED_TEXT = "the human's own nested checkout\n"
CLEAN = encode_dirty_state(DirtySnapshot())


class Fixture:
    """One instance wired to a throwaway repo, bd workspace and wrapper dir."""

    def __init__(self, tmp_path: Path, isolation: IsolationMode) -> None:
        self.repo = make_repo(tmp_path)
        self.base = head_of(self.repo)
        self.config = make_config(self.repo, tmp_path, fake_proc=False)
        _, self.store = make_store(tmp_path, self.base)
        self.root = make_root(self.store, self.repo, "wt-instance")
        self.paths = make_paths(self.config, self.root.root_id)
        self.clock = FrozenClock()
        self.workspace = make_workspace(self.paths, make_git(self.config), self.clock)
        self.node = _with_isolation(
            node_of(self.root.definition.document, IMPLEMENT), isolation
        )
        minted = self.store.mint_activation(self.root.root_id, entry_mint()).activation
        # Production writes the §3.2 trio before the barrier releases a child
        # (§5.2); attribution refuses to guess without it, so the fixture
        # records a clean pre-attempt state exactly as `Supervisor.run` would.
        self.activation = self.store.record_precondition(
            minted.activation_id,
            PreconditionRecord(
                pre_attempt_commit=self.base,
                reset_verified_commit=self.base,
                pre_attempt_dirty_state=CLEAN,
            ),
        )


def _with_isolation(node: Node, isolation: IsolationMode) -> Node:
    """The fixture's node, forced into one isolation mode."""
    return node.model_copy(update={"isolation": isolation})


@pytest.fixture
def worktree(tmp_path: Path) -> Fixture:
    """A worktree-isolated instance (§5.4)."""
    return Fixture(tmp_path, IsolationMode.WORKTREE)


@pytest.fixture
def in_repo(tmp_path: Path) -> Fixture:
    """An in-repo instance (§12), with the execution band already held."""
    fixture = Fixture(tmp_path, IsolationMode.IN_REPO)
    fixture.workspace.band.acquire()
    return fixture


def entry_for(fixture: Fixture, path: str) -> DirtyEntry:
    """A `DirtyEntry` for a path currently dirty in the fixture's repo."""
    return DirtyEntry(
        path=path,
        digest=make_git(fixture.config).hash_working_file(path, cwd=fixture.repo),
        tracked=False,
    )


def confirmation_for(fixture: Fixture, path: str) -> HumanConfirmation:
    """A tier-2 release of `path` at the content currently on disk."""
    return HumanConfirmation(
        activation_id=fixture.activation.activation_id,
        confirmed=(
            ConfirmedPath(
                path=path,
                digest=make_git(fixture.config).hash_working_file(
                    path, cwd=fixture.repo
                ),
            ),
        ),
        reason="the human said so",
        actor="human",
        confirmed_at=CONFIRMED_AT,
    )


def attribute(fixture: Fixture, *declared: str) -> RunnerAttribution:
    """Record what the wrapper would have observed at this runner's exit."""
    record = fixture.workspace.record_attribution(
        fixture.activation, fixture.node, declared=frozenset(declared)
    )
    assert record is not None
    return record


def rebased(fixture: Fixture, base: str) -> ActivationRecord:
    """The fixture's activation with a different `intended_base_commit`."""
    return fixture.activation.model_copy(
        update={
            "metadata": fixture.activation.metadata.model_copy(
                update={"intended_base_commit": base}
            )
        }
    )


def nested_checkout(fixture: Fixture) -> Path:
    """A nested git repository inside the human's own tree, as they keep one."""
    nested = fixture.repo / NESTED_DIR
    nested.mkdir()
    subprocess.run(
        ["git", "init", "-q", str(nested)], check=True, capture_output=True, timeout=60
    )
    (nested / "a.txt").write_text(NESTED_TEXT, encoding="utf-8")
    return nested
