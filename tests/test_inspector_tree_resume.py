"""§3 tree-faithful resume: the three preconditions one shared checkout gets.

Every activation of a root works in the SAME checkout, so "reset it" is a
statement about somebody else's bytes. These tests pin the three answers §3
gives — a fresh writer resets, a resumed writer proves the tree is still the
one its session remembers and keeps it, and a non-writer touches nothing at
all — against a real git working tree rather than a stubbed status parser.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tests._inspector import (
    IMPLEMENT,
    FrozenClock,
    dead_pid,
    entry_mint,
    handle_for,
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
from workflow_interpreter.bdio import ActivationRecord
from workflow_interpreter.contracts.sessions import SessionMode
from workflow_interpreter.inspector.errors import (
    ReadOnlyTreeMutation,
    ResumeMismatchReason,
    ResumeTreeMismatch,
)
from workflow_interpreter.inspector.models import (
    CrewAttribution,
    ObservedTree,
    PreconditionResult,
    WorkspaceRecord,
)
from workflow_interpreter.inspector.paths import read_record
from workflow_interpreter.inspector.run import choose_precondition
from workflow_interpreter.inspector.workspace import (
    PRERESET_NAMESPACE,
    namespaced_ref,
)
from workflow_interpreter.schema.models import IsolationMode, Node

SENTINEL = "src/sentinel.txt"
SENTINEL_TEXT = "impl#1 left this uncommitted\n"
REVIEWER_TEXT = "a reviewer wrote after all\n"
SOURCE_SESSION = "thread-1"


class Lab:
    """One instance whose activations share a checkout, as §3 has them do."""

    def __init__(
        self, tmp_path: Path, isolation: IsolationMode = IsolationMode.WORKTREE
    ) -> None:
        self.repo = make_repo(tmp_path)
        self.base = head_of(self.repo)
        self.config = make_config(self.repo, tmp_path)
        _, self.store = make_store(tmp_path, self.base)
        self.root = make_root(self.store, self.repo, "tree-instance")
        self.paths = make_paths(self.config, self.root.root_id)
        self.git = make_git(self.config)
        self.workspace = make_workspace(self.paths, self.git, FrozenClock())
        self.node = node_of(self.root.definition.document, IMPLEMENT).model_copy(
            update={"isolation": isolation}
        )
        self.reviewer = self.node.model_copy(update={"writes": False})

    @property
    def tree(self) -> Path:
        """The checkout every activation of this instance shares."""
        return self.workspace.path_for(self.node)

    def mint(self) -> ActivationRecord:
        """The instance's first activation, as bd minted it."""
        minted = self.store.mint_activation(self.root.root_id, entry_mint()).activation
        self.paths.ensure_activation_dir(minted.activation_id)
        return minted

    def successor(
        self, source: ActivationRecord, activation_id: str, **metadata: object
    ) -> ActivationRecord:
        """A later activation of the same node, durable session fields included."""
        self.paths.ensure_activation_dir(activation_id)
        return source.model_copy(
            update={
                "activation_id": activation_id,
                "metadata": source.metadata.model_copy(update=metadata),
            }
        )

    def resumed(
        self, source: ActivationRecord, expected: str | None, **metadata: object
    ) -> ActivationRecord:
        """The resumed writer §3 dispatches against impl#1's own tree."""
        return self.successor(
            source,
            "wf-impl-2",
            session_mode=SessionMode.RESUME,
            source_session_id=SOURCE_SESSION,
            expected_tree_oid=expected,
            **metadata,
        )

    def implement(self) -> ActivationRecord:
        """impl#1: a fresh writer that leaves an uncommitted sentinel at T1."""
        activation = self.mint()
        self.run(activation, self.node)
        (self.tree / SENTINEL).write_text(SENTINEL_TEXT, encoding="utf-8")
        return activation

    def run(self, activation: ActivationRecord, node: Node) -> PreconditionResult:
        """The precondition the §5.4 call site would choose for this activation."""
        return choose_precondition(self.workspace, node, None, None)(activation)

    def carried(
        self, activation: ActivationRecord, result: PreconditionResult
    ) -> ActivationRecord:
        """The activation as `Dispatcher._prepare` leaves it: the §3.2 trio durable."""
        return activation.model_copy(
            update={
                "metadata": activation.metadata.model_copy(
                    update=result.carry_forward().model_dump(mode="json")
                )
            }
        )


@pytest.fixture
def lab(tmp_path: Path) -> Lab:
    """An instance with one shared worktree and nothing dispatched yet."""
    return Lab(tmp_path)


@pytest.fixture
def in_repo_lab(tmp_path: Path) -> Lab:
    """An in-repo instance, where §12 attribution is what protects the human."""
    lab = Lab(tmp_path, isolation=IsolationMode.IN_REPO)
    lab.workspace.band.acquire()
    return lab


def test_resumed_writer_owns_and_records_trio(lab: Lab) -> None:
    """§3: equality proven → no reset, ownership taken, the §3.2 trio recorded."""
    impl1 = lab.implement()
    impl2 = lab.resumed(impl1, lab.workspace.working_tree_oid(lab.node))

    result = lab.run(impl2, lab.node)

    head = head_of(lab.tree)
    assert result.reset_applied is False
    assert result.pre_attempt_commit == head
    assert result.reset_verified_commit == head
    assert (lab.tree / SENTINEL).read_text(encoding="utf-8") == SENTINEL_TEXT
    record = read_record(lab.paths.workspace_record, WorkspaceRecord)
    assert record is not None
    assert record.owner_activation_id == impl2.activation_id
    assert record.read_only is False


def test_dead_resumed_writer_pins_tree(lab: Lab) -> None:
    """§5.6: a resumed writer owns the checkout, so its dead bytes are preserved."""
    impl1 = lab.implement()
    impl2 = lab.resumed(
        impl1,
        lab.workspace.working_tree_oid(lab.node),
        handle=handle_for(dead_pid(), log_path=str(lab.paths.log("wf-impl-2"))),
    )
    lab.run(impl2, lab.node)

    record = lab.workspace.preserve_interrupted(impl2, lab.node)

    assert record is not None
    assert record.pinned
    assert (
        lab.git.blob_text(f"{record.commit}:{SENTINEL}", cwd=lab.repo) == SENTINEL_TEXT
    )


def test_nonwriter_no_reset_oid_unchanged(lab: Lab) -> None:
    """§3: a reviewer observes the tree it was given and never transfers ownership."""
    impl1 = lab.implement()
    before = lab.workspace.working_tree_oid(lab.node)
    review = lab.successor(impl1, "wf-review-1")

    result = lab.run(review, lab.reviewer)
    lab.workspace.verify_shared_tree(review, lab.reviewer)

    assert result.reset_applied is False
    assert (lab.tree / SENTINEL).read_text(encoding="utf-8") == SENTINEL_TEXT
    assert lab.workspace.working_tree_oid(lab.reviewer) == before
    observed = read_record(lab.paths.observed_tree(review.activation_id), ObservedTree)
    assert observed is not None
    assert observed.tree_oid == before
    owner = read_record(lab.paths.workspace_record, WorkspaceRecord)
    assert owner is not None
    assert owner.owner_activation_id == impl1.activation_id

    (lab.tree / SENTINEL).write_text(REVIEWER_TEXT, encoding="utf-8")
    with pytest.raises(ReadOnlyTreeMutation, match=before):
        lab.workspace.verify_shared_tree(review, lab.reviewer)


def test_reviewer_bypass_checked_by_next_writer(lab: Lab) -> None:
    """A steered reviewer skips its own check; the next writer's probe catches it."""
    impl1 = lab.implement()
    expected = lab.workspace.working_tree_oid(lab.node)
    review = lab.successor(impl1, "wf-review-1")
    lab.run(review, lab.reviewer)
    # Steer-pending returns before `ExitObserver.observe`, so no after-exit
    # equality check ever runs over this mutation (§3).
    (lab.tree / SENTINEL).write_text(REVIEWER_TEXT, encoding="utf-8")

    with pytest.raises(ResumeTreeMismatch) as refusal:
        lab.run(lab.resumed(impl1, expected), lab.node)

    assert refusal.value.reason is ResumeMismatchReason.INTERVENING_WRITER
    assert expected in str(refusal.value)
    assert (lab.tree / SENTINEL).read_text(encoding="utf-8") == REVIEWER_TEXT


def test_intervening_writer_refuses(lab: Lab) -> None:
    """§3: impl#2 never resumes against a tree a different writer left behind."""
    impl1 = lab.implement()
    expected = lab.workspace.working_tree_oid(lab.node)
    other = lab.successor(impl1, "wf-other-writer")
    lab.run(other, lab.node)
    (lab.tree / SENTINEL).write_text("another writer's work\n", encoding="utf-8")
    observed = lab.workspace.working_tree_oid(lab.node)

    with pytest.raises(ResumeTreeMismatch) as refusal:
        lab.run(lab.resumed(impl1, expected), lab.node)

    assert refusal.value.reason is ResumeMismatchReason.INTERVENING_WRITER
    assert refusal.value.expected == expected
    assert refusal.value.observed == observed


def test_in_repo_reviewer_keeps_the_writer_attribution(in_repo_lab: Lab) -> None:
    """§12: a non-writer's exit must not erase what the writer before it left.

    In-repo, `ExitObserver` records attribution for EVERY activation, and an
    unknown pre-attempt state replaces the record with an empty one — so a
    reviewer that observed the tree would hand impl#1's own files to the next
    fresh writer's reset as the human's work. The observation therefore states
    the dirty state it found, exactly as the two writing branches do.
    """
    lab = in_repo_lab
    minted = lab.mint()
    impl1 = lab.carried(minted, lab.run(minted, lab.node))
    (lab.tree / SENTINEL).write_text(SENTINEL_TEXT, encoding="utf-8")
    written = lab.workspace.record_attribution(
        impl1, lab.node, declared=frozenset({SENTINEL})
    )
    assert written is not None
    assert [entry.path for entry in written.entries] == [SENTINEL]

    review = lab.successor(impl1, "wf-review-1")
    observed = lab.run(review, lab.reviewer)
    lab.workspace.record_attribution(
        lab.carried(review, observed), lab.reviewer, declared=frozenset()
    )

    assert observed.pre_attempt_dirty_state is not None
    record = read_record(lab.paths.attribution_record, CrewAttribution)
    assert record is not None
    assert [entry.path for entry in record.entries] == [SENTINEL]


def test_fresh_writer_resets(lab: Lab) -> None:
    """§3: a writer resolved as fresh keeps the existing precondition, snapshot first."""
    impl1 = lab.implement()
    fresh = lab.successor(impl1, "wf-impl-3")

    result = lab.run(fresh, lab.node)

    assert result.reset_applied is True
    assert not (lab.tree / SENTINEL).exists()
    assert head_of(lab.tree) == lab.base
    pinned = lab.git.ref_target(
        namespaced_ref(lab.root.root_id, PRERESET_NAMESPACE, fresh.activation_id),
        cwd=lab.repo,
    )
    assert pinned == result.pre_reset_commit
