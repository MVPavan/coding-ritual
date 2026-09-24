"""§3 tree-faithful resume: the three preconditions one shared checkout gets.

Every activation of a root works in the SAME checkout, so "reset it" is a
statement about somebody else's bytes. These tests pin the three answers §3
gives — a fresh writer resets, a resumed writer proves the tree is still the
one its session remembers and keeps it, and a non-writer touches nothing at
all — against a real git working tree rather than a stubbed status parser.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest

from tests._inspector import (
    IMPLEMENT,
    REVIEW,
    SESSION_ID,
    FakeProfile,
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
    observe_session,
    task_builder,
)
from workflow_interpreter.bdio import (
    ActivationRecord,
    ConfigSource,
    MintReason,
    MintRequest,
    Outcome,
    ResolvedSetting,
)
from workflow_interpreter.bdio.errors import BoundExceededError, CarrierIntegrityError
from workflow_interpreter.bdio.rpc_records import SessionRegistration
from workflow_interpreter.bdio.sessions import choose_source
from workflow_interpreter.bdio.wire import (
    is_legacy_activation,
    mint_request_from_activation,
)
from workflow_interpreter.contracts.execution import (
    ExecutionPolicy,
    ExecutionProfileName,
    ToolNetwork,
    policy_for,
)
from workflow_interpreter.contracts.sessions import (
    SessionFreshReason,
    SessionMode,
    session_mode_key,
)
from workflow_interpreter.inspector.errors import (
    ReadOnlyTreeMutation,
    ResumeMismatchReason,
    ResumeTreeMismatch,
    ReviewTreeMismatch,
    SnapshotFailed,
)
from workflow_interpreter.inspector.gitio import GitCommandError
from workflow_interpreter.inspector.launch import Dispatcher
from workflow_interpreter.inspector.models import (
    CrewAttribution,
    ObservedTree,
    PreconditionResult,
    WorkspaceRecord,
)
from workflow_interpreter.inspector.paths import read_record, write_record
from workflow_interpreter.inspector.profile import CrewChannels, TaskSpec
from workflow_interpreter.inspector.recover import Recovery
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
WRITER_POLICY = policy_for(ExecutionProfileName.WRITER, ToolNetwork.NOT_ENFORCED)
REVIEWER_POLICY = policy_for(ExecutionProfileName.REVIEWER, ToolNetwork.NOT_ENFORCED)


class Lab:
    """One instance whose activations share a checkout, as §3 has them do."""

    def __init__(
        self,
        tmp_path: Path,
        isolation: IsolationMode = IsolationMode.WORKTREE,
        *overrides: ResolvedSetting,
        real_proc: bool = False,
    ) -> None:
        self.repo = make_repo(tmp_path)
        self.base = head_of(self.repo)
        self.config = make_config(self.repo, tmp_path, fake_proc=not real_proc)
        _, self.store = make_store(tmp_path, self.base)
        self.root = make_root(self.store, self.repo, "tree-instance", *overrides)
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

    def mint(
        self,
        session_mode: SessionMode = SessionMode.FRESH,
        execution_policy: ExecutionPolicy | None = None,
    ) -> ActivationRecord:
        """The instance's first activation, as bd minted it."""
        minted = self.store.mint_activation(
            self.root.root_id,
            entry_mint(session_mode=session_mode, execution_policy=execution_policy),
        ).activation
        self.paths.ensure_activation_dir(minted.activation_id)
        return minted

    def successor(
        self, source: ActivationRecord, activation_id: str, **metadata: object
    ) -> ActivationRecord:
        """A later activation of the same node, durable session fields included."""
        self.paths.ensure_activation_dir(activation_id)
        # `id`, not `activation_id`: the latter is a read-only property, and
        # updating it left every "successor" still carrying its source's id.
        return source.model_copy(
            update={
                "id": activation_id,
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


def _resume_task(lab: Lab) -> Callable[[ActivationRecord, CrewChannels], TaskSpec]:
    """Build a bounded fake-crew task with a nonempty resume instruction."""
    base = task_builder(lab.tree, lab.node)

    def build(activation: ActivationRecord, channels: CrewChannels) -> TaskSpec:
        """Supply the resume delta the public dispatch contract requires."""
        return base(activation, channels).model_copy(
            update={"resume_brief": "continue from the recovered tree"}
        )

    return build


def _writer_mint(**overrides: object) -> MintRequest:
    """Use the S3 writer authority in a focused crash-retry request."""
    return entry_mint(execution_policy=WRITER_POLICY, **overrides)


@pytest.fixture
def lab(tmp_path: Path) -> Lab:
    """An instance with one shared worktree and nothing dispatched yet."""
    return Lab(tmp_path)


@pytest.fixture
def launch_lab(tmp_path: Path) -> Lab:
    """A tree lab whose public dispatcher can prove real child identity."""
    return Lab(tmp_path, real_proc=True)


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


def test_plain_loop_resumes_impl2_on_the_tree_impl1_pinned(tmp_path: Path) -> None:
    """S3 acceptance: impl#1 → review#1 → impl#2, through the real wiring.

    Nothing here computes the tree impl#2 is held to. impl#1's uncommitted
    sentinel is pinned at its exit, published from the ref as bd's
    `session_tree_oid`, selected by `choose_source` at impl#2's mint, and lands
    on impl#2 as `expected_tree_oid` — so equality passing proves the whole
    chain carried the same tree, and the sentinel surviving proves no reset.
    """
    lab = Lab(
        tmp_path,
        IsolationMode.WORKTREE,
        ResolvedSetting(
            key=session_mode_key(IMPLEMENT),
            value=SessionMode.RESUME.value,
            source=ConfigSource.GRAPH_DEFAULT,
        ),
    )
    minted = lab.mint(session_mode=SessionMode.RESUME)
    first = lab.run(minted, lab.node)
    assert minted.metadata.source_session_id is None
    assert first.reset_applied is False
    (lab.tree / SENTINEL).write_text(SENTINEL_TEXT, encoding="utf-8")
    dispatched = lab.store.record_dispatch(
        minted.activation_id,
        handle_for(dead_pid(), log_path=str(lab.paths.log(minted.activation_id))),
        launch_id="impl-1-launch",
    )
    impl1 = observe_session(lab.store, dispatched)
    pinned = lab.workspace.pin_session_tree(impl1, lab.node)
    published = lab.workspace.session_tree_oid(impl1.activation_id)
    assert pinned is not None and published == pinned
    lab.store.record_session_tree(impl1.activation_id, published)
    lab.store.close_activation(impl1.activation_id, Outcome.DONE)

    review = lab.store.mint_activation(
        lab.root.root_id,
        entry_mint(
            REVIEW,
            mint_reason=MintReason.EDGE,
            predecessor_activation_id=impl1.activation_id,
        ),
    ).activation
    lab.paths.ensure_activation_dir(review.activation_id)
    reviewer = node_of(lab.root.definition.document, REVIEW)
    observed = lab.run(review, reviewer)
    lab.workspace.verify_shared_tree(review, reviewer)
    assert observed.reset_applied is False
    seen = read_record(lab.paths.observed_tree(review.activation_id), ObservedTree)
    assert seen is not None and seen.tree_oid == published
    lab.store.record_dispatch(
        review.activation_id,
        handle_for(dead_pid(), log_path=str(lab.paths.log(review.activation_id))),
        launch_id="review-1-launch",
    )
    lab.store.close_activation(review.activation_id, Outcome.REJECT)

    impl2 = lab.store.mint_activation(
        lab.root.root_id,
        entry_mint(
            mint_reason=MintReason.EDGE,
            predecessor_activation_id=review.activation_id,
            session_mode=SessionMode.RESUME,
        ),
    ).activation
    assert impl2.metadata.session_source_activation_id == impl1.activation_id
    assert impl2.metadata.source_session_id == SESSION_ID
    assert impl2.metadata.expected_tree_oid == published

    resumed = lab.run(impl2, lab.node)

    assert resumed.reset_applied is False
    assert resumed.pre_reset_commit is None
    assert resumed.reset_verified_commit == head_of(lab.tree)
    assert (lab.tree / SENTINEL).read_text(encoding="utf-8") == SENTINEL_TEXT
    assert lab.git.status_paths(cwd=lab.tree) == ((SENTINEL, False),)
    owner = read_record(lab.paths.workspace_record, WorkspaceRecord)
    assert owner is not None
    assert owner.owner_activation_id == impl2.activation_id


def _crash_resumed_writer(
    lab: Lab,
    *,
    policy: ExecutionPolicy | None = WRITER_POLICY,
    registered: bool = True,
    edited: bool = True,
    lose_owner: bool = False,
    clean_after_snapshot: bool = False,
) -> ActivationRecord:
    """Drive one registered source and its resumed successor through recovery."""
    first = lab.mint(session_mode=SessionMode.RESUME, execution_policy=policy)
    lab.run(first, lab.node)
    (lab.tree / SENTINEL).write_text(SENTINEL_TEXT, encoding="utf-8")
    first = lab.store.record_dispatch(
        first.activation_id, handle_for(dead_pid()), launch_id="first-launch"
    )
    first = observe_session(lab.store, first)
    tree = lab.workspace.pin_session_tree(first, lab.node)
    assert tree is not None
    lab.store.record_session_tree(first.activation_id, tree)
    lab.store.close_activation(first.activation_id, Outcome.DONE)

    resumed = lab.store.mint_activation(
        lab.root.root_id,
        entry_mint(
            execution_policy=policy,
            session_mode=SessionMode.RESUME,
            mint_reason=MintReason.EDGE,
            predecessor_activation_id=first.activation_id,
        ),
    ).activation
    assert resumed.metadata.source_session_id == SESSION_ID
    lab.run(resumed, lab.node)
    resumed = lab.store.record_dispatch(
        resumed.activation_id, handle_for(dead_pid()), launch_id="resumed-launch"
    )
    if registered:
        meta = resumed.metadata
        assert meta.handle is not None
        assert meta.launch_id is not None
        assert meta.effort is not None
        assert meta.policy_digest is not None
        resumed = lab.store.register_session(
            resumed.activation_id,
            SessionRegistration(
                root_id=meta.wf_root_id,
                activation_id=resumed.activation_id,
                launch_id=meta.launch_id,
                handle=meta.handle,
                thread_id=SESSION_ID,
                crew_profile=meta.crew_profile,
                crew_version="old-cli-version",
                model=meta.model,
                effort=meta.effort,
                policy_digest=meta.policy_digest,
                state_path="",
            ),
        )
    if edited:
        (lab.tree / SENTINEL).write_text("partial resumed edits\n", encoding="utf-8")
    if clean_after_snapshot:
        snapshot = lab.workspace.preserve_interrupted(resumed, lab.node)
        assert snapshot is not None and snapshot.pinned
        (lab.tree / SENTINEL).unlink()
    if lose_owner:
        owner = read_record(lab.paths.workspace_record, WorkspaceRecord)
        assert owner is not None
        write_record(
            lab.paths.workspace_record,
            owner.model_copy(update={"owner_activation_id": "foreign-writer"}),
        )
    recovery = Recovery(lab.config, lab.paths, lab.store, lab.workspace, FrozenClock())
    result = recovery.resolve(resumed, lab.node)
    closed = result.closed
    assert closed is not None
    assert closed.metadata.session_tree_oid == (
        None if lose_owner else lab.workspace.working_tree_oid(lab.node)
    )
    snapshot = lab.workspace.read_recovery(resumed)
    if lose_owner:
        assert snapshot is not None and snapshot.unavailable is not None
    elif edited and not clean_after_snapshot:
        assert snapshot is not None and snapshot.pinned
        assert closed.metadata.session_tree_oid == snapshot.tree
    return closed


def test_crashed_resumed_writer_without_ownership_closes_without_tree(lab: Lab) -> None:
    """An unavailable owner proof closes the crash without claiming its tree."""
    closed = _crash_resumed_writer(lab, lose_owner=True)
    with pytest.raises(CarrierIntegrityError, match="crashed resumed writer source"):
        lab.store.mint_activation(
            lab.root.root_id,
            _writer_mint(
                session_mode=SessionMode.RESUME,
                mint_reason=MintReason.INFRA_RETRY,
                predecessor_activation_id=closed.activation_id,
            ),
        )
    assert (lab.tree / SENTINEL).read_text(encoding="utf-8") == (
        "partial resumed edits\n"
    )


def test_clean_crash_uses_current_tree_after_an_earlier_snapshot(lab: Lab) -> None:
    """A clean checkout supersedes a recovery snapshot of earlier dirty bytes."""
    closed = _crash_resumed_writer(lab, clean_after_snapshot=True)
    snapshot = lab.workspace.read_recovery(closed)
    assert snapshot is not None and snapshot.pinned
    assert snapshot.tree != closed.metadata.session_tree_oid
    assert closed.metadata.session_tree_oid == lab.workspace.working_tree_oid(lab.node)


def test_read_only_crash_retry_uses_the_prior_successful_source(lab: Lab) -> None:
    """A reviewer crash has no writer recovery tree and keeps its prior session."""
    writer = lab.mint()
    writer = lab.store.record_dispatch(
        writer.activation_id, handle_for(dead_pid()), launch_id="review-writer"
    )
    lab.store.close_activation(writer.activation_id, Outcome.DONE)
    first = lab.store.mint_activation(
        lab.root.root_id,
        entry_mint(
            REVIEW,
            execution_policy=REVIEWER_POLICY,
            session_mode=SessionMode.RESUME,
            mint_reason=MintReason.EDGE,
            predecessor_activation_id=writer.activation_id,
        ),
    ).activation
    first = lab.store.record_dispatch(
        first.activation_id, handle_for(dead_pid()), launch_id="review-first"
    )
    first = observe_session(lab.store, first)
    lab.store.close_activation(first.activation_id, Outcome.REJECT)
    resumed = lab.store.mint_activation(
        lab.root.root_id,
        entry_mint(
            REVIEW,
            execution_policy=REVIEWER_POLICY,
            session_mode=SessionMode.RESUME,
            mint_reason=MintReason.EDGE,
            predecessor_activation_id=first.activation_id,
        ),
    ).activation
    assert resumed.metadata.source_session_id == SESSION_ID
    crashed = lab.store.close_activation(resumed.activation_id, Outcome.ERROR_TRANSPORT)
    retry = lab.store.mint_activation(
        lab.root.root_id,
        entry_mint(
            REVIEW,
            execution_policy=REVIEWER_POLICY,
            session_mode=SessionMode.RESUME,
            mint_reason=MintReason.INFRA_RETRY,
            predecessor_activation_id=crashed.activation_id,
        ),
    ).activation
    assert retry.metadata.session_source_activation_id == first.activation_id
    assert retry.metadata.source_session_id == SESSION_ID


@pytest.mark.parametrize("legacy", [False, True])
def test_crashed_writer_without_usable_tree_refuses_unless_legacy(
    lab: Lab, legacy: bool
) -> None:
    """A modern failed writer needs its own tree; old pins use old selection."""
    closed = _crash_resumed_writer(lab)
    meta = closed.metadata.model_copy(update={"session_tree_oid": None})
    if legacy:
        meta = meta.model_copy(
            update={
                "role": None,
                "family": None,
                "effort": None,
                "context_cap_tokens": None,
                "execution_policy": None,
                "policy_digest": None,
                "catalog_digest": None,
                "binding_digest": None,
                "crew_version": None,
            }
        )
        assert is_legacy_activation(meta)
    crashed = closed.model_copy(update={"metadata": meta})
    records = [
        crashed if item.activation_id == closed.activation_id else item
        for item in lab.store.reads.list_activations(lab.root.root_id)
    ]
    request = mint_request_from_activation(closed.metadata).model_copy(
        update={
            "mint_reason": MintReason.INFRA_RETRY,
            "predecessor_activation_id": closed.activation_id,
        }
    )
    if legacy:
        choice = choose_source(lab.root, request, records)
        assert (
            choice.source_activation_id == closed.metadata.session_source_activation_id
        )
    else:
        with pytest.raises(
            CarrierIntegrityError, match="crashed resumed writer source"
        ):
            choose_source(lab.root, request, records)


def test_crashed_resumed_writer_retries_its_own_thread_and_recovery_tree(
    launch_lab: Lab,
) -> None:
    """An infra retry resumes the failed turn's registered thread and dirty tree."""
    lab = launch_lab
    closed = _crash_resumed_writer(lab)
    recovered_tree = closed.metadata.session_tree_oid

    retry = lab.store.mint_activation(
        lab.root.root_id,
        _writer_mint(
            session_mode=SessionMode.RESUME,
            mint_reason=MintReason.INFRA_RETRY,
            predecessor_activation_id=closed.activation_id,
        ),
    ).activation
    assert retry.metadata.session_source_activation_id == closed.activation_id
    assert retry.metadata.source_session_id == SESSION_ID
    assert retry.metadata.expected_tree_oid == recovered_tree
    assert retry.metadata.model == closed.metadata.model
    assert retry.metadata.effort == closed.metadata.effort
    assert retry.metadata.binding_digest == closed.metadata.binding_digest
    assert lab.run(retry, lab.node).reset_applied is False
    result = Dispatcher(lab.paths, lab.store, FrozenClock()).dispatch(
        mint_request_from_activation(retry.metadata),
        FakeProfile(),
        _resume_task(lab),
    )
    assert result.receipt is not None
    assert result.receipt.handle.session_id == SESSION_ID


def test_crashed_resumed_writer_without_policy_uses_declared_writes(lab: Lab) -> None:
    closed = _crash_resumed_writer(lab, policy=None)
    request = entry_mint(
        execution_policy=None,
        effort=closed.metadata.effort,
        session_mode=SessionMode.RESUME,
        mint_reason=MintReason.INFRA_RETRY,
        predecessor_activation_id=closed.activation_id,
    )

    writer = choose_source(
        lab.root, request, lab.store.reads.list_activations(lab.root.root_id)
    )
    assert writer.source_activation_id == closed.activation_id
    assert writer.source_session_id == SESSION_ID
    assert writer.source_tree_oid == closed.metadata.session_tree_oid

    # The graph's review node declares writes=false; the same policy-free
    # crashed record cannot enter the writer crash-resume branch there.
    assert not lab.root.index.nodes[REVIEW].writes
    review_closed = closed.model_copy(
        update={"metadata": closed.metadata.model_copy(update={"node": REVIEW})}
    )
    reviewer = choose_source(
        lab.root,
        request.model_copy(update={"node": REVIEW}),
        [review_closed],
    )
    assert reviewer.source_activation_id is None
    assert reviewer.fresh_reason is SessionFreshReason.NO_SOURCE


@pytest.mark.parametrize("pin_fails", [False, True])
def test_model_change_preserves_crash_tree_before_fresh_launch(
    launch_lab: Lab, monkeypatch: pytest.MonkeyPatch, pin_fails: bool
) -> None:
    """A changed binding launches fresh only behind a durable prereset ref."""
    lab = launch_lab
    closed = _crash_resumed_writer(lab)
    request = _writer_mint(
        model="changed-model",
        session_mode=SessionMode.RESUME,
        mint_reason=MintReason.INFRA_RETRY,
        predecessor_activation_id=closed.activation_id,
    )
    profile = FakeProfile()
    if pin_fails:
        original = lab.git.update_ref

        def refuse(ref: str, commit: str, *, cwd: Path) -> None:
            """Fail only the reset's preservation ref."""
            if "/prereset/" in ref:
                raise GitCommandError("injected prereset pin failure")
            original(ref, commit, cwd=cwd)

        monkeypatch.setattr(lab.git, "update_ref", refuse)
        with pytest.raises(SnapshotFailed, match="snapshot"):
            Dispatcher(lab.paths, lab.store, FrozenClock()).dispatch(
                request,
                profile,
                _resume_task(lab),
                lambda activation: lab.run(activation, lab.node),
            )
        retry = lab.store.reads.list_activations(lab.root.root_id)[-1]
        assert retry.metadata.session_fresh_reason.value == "model_changed"
        assert retry.metadata.handle is None
        assert not lab.paths.receipt(retry.activation_id).exists()
        assert profile.launched == []
        assert (lab.tree / SENTINEL).read_text(encoding="utf-8") == (
            "partial resumed edits\n"
        )
    else:
        result = Dispatcher(lab.paths, lab.store, FrozenClock()).dispatch(
            request,
            profile,
            _resume_task(lab),
            lambda activation: lab.run(activation, lab.node),
        )
        assert result.activation.metadata.session_fresh_reason.value == "model_changed"
        assert result.receipt is not None
        assert result.receipt.handle.session_id == SESSION_ID
        ref = namespaced_ref(
            lab.root.root_id, PRERESET_NAMESPACE, result.activation.activation_id
        )
        pinned = lab.git.ref_target(ref, cwd=lab.repo)
        assert pinned is not None
        assert lab.git.blob_text(f"{pinned}:{SENTINEL}", cwd=lab.repo) == (
            "partial resumed edits\n"
        )


def test_retry_crashes_exhaust_the_existing_infra_retry_bound(lab: Lab) -> None:
    """Each crash uses its own recovered tree until the fixture's cap ends it."""
    closed = _crash_resumed_writer(lab)
    for attempt in range(2):
        retry = lab.store.mint_activation(
            lab.root.root_id,
            _writer_mint(
                session_mode=SessionMode.RESUME,
                mint_reason=MintReason.INFRA_RETRY,
                predecessor_activation_id=closed.activation_id,
            ),
        ).activation
        assert retry.metadata.session_source_activation_id == closed.activation_id
        lab.run(retry, lab.node)
        retry = lab.store.record_dispatch(
            retry.activation_id,
            handle_for(dead_pid()),
            launch_id=f"retry-{attempt}-launch",
        )
        retry = observe_session(lab.store, retry)
        (lab.tree / SENTINEL).write_text(f"retry {attempt} crashed\n", encoding="utf-8")
        failed_retry = (
            Recovery(lab.config, lab.paths, lab.store, lab.workspace, FrozenClock())
            .resolve(retry, lab.node)
            .closed
        )
        assert failed_retry is not None
        assert failed_retry.metadata.session_tree_oid == lab.workspace.working_tree_oid(
            lab.node
        )
        closed = failed_retry
    with pytest.raises(BoundExceededError, match="infra"):
        lab.store.mint_activation(
            lab.root.root_id,
            _writer_mint(
                session_mode=SessionMode.RESUME,
                mint_reason=MintReason.INFRA_RETRY,
                predecessor_activation_id=closed.activation_id,
            ),
        )
    assert (lab.tree / SENTINEL).read_text(encoding="utf-8") == ("retry 1 crashed\n")


@pytest.mark.parametrize("edited", [False, True])
def test_unregistered_crashed_resume_uses_source_only_for_unchanged_tree(
    launch_lab: Lab, edited: bool
) -> None:
    """Without observed identity, a changed tree cannot be attached to the source."""
    lab = launch_lab
    closed = _crash_resumed_writer(lab, registered=False, edited=edited)
    request = _writer_mint(
        session_mode=SessionMode.RESUME,
        mint_reason=MintReason.INFRA_RETRY,
        predecessor_activation_id=closed.activation_id,
    )
    if edited:
        with pytest.raises(
            CarrierIntegrityError, match="crashed resumed writer source"
        ):
            lab.store.mint_activation(lab.root.root_id, request)
        assert (lab.tree / SENTINEL).read_text(encoding="utf-8") == (
            "partial resumed edits\n"
        )
    else:
        retry = lab.store.mint_activation(lab.root.root_id, request).activation
        assert retry.metadata.session_source_activation_id == closed.activation_id
        assert retry.metadata.source_session_id == SESSION_ID
        assert retry.metadata.expected_tree_oid == closed.metadata.expected_tree_oid
        assert lab.run(retry, lab.node).reset_applied is False
        result = Dispatcher(lab.paths, lab.store, FrozenClock()).dispatch(
            mint_request_from_activation(retry.metadata),
            FakeProfile(),
            _resume_task(lab),
        )
        assert result.receipt is not None
        assert result.receipt.handle.session_id == SESSION_ID


@pytest.mark.parametrize(
    ("override", "reason"),
    [
        ({"model": "changed-model"}, "model_changed"),
        ({"crew_version": "new-cli-version"}, "version_drift"),
    ],
)
def test_crashed_resume_binding_or_version_change_starts_fresh(
    lab: Lab, override: dict[str, str], reason: str
) -> None:
    """A changed binding or CLI version leaves the old thread behind."""
    closed = _crash_resumed_writer(lab)
    request = mint_request_from_activation(closed.metadata).model_copy(
        update={
            "mint_reason": MintReason.INFRA_RETRY,
            "predecessor_activation_id": closed.activation_id,
            **override,
        }
    )
    choice = choose_source(
        lab.root, request, lab.store.reads.list_activations(lab.root.root_id)
    )
    assert choice.source_session_id is None
    assert choice.fresh_reason is not None
    assert choice.fresh_reason.value == reason


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


def test_reviewer_refuses_a_tree_its_writer_did_not_leave(lab: Lab) -> None:
    """§3: a reviewer grades the tree its writer pinned, or refuses by name.

    Without the comparison a reviewer can grade bytes nobody produced; with no
    pinned predecessor tree there is nothing to prove, so it only records.
    """
    impl1 = lab.implement()
    pinned = lab.workspace.working_tree_oid(lab.node)
    review = lab.successor(impl1, "wf-review-1")
    (lab.tree / SENTINEL).write_text("an edit no activation made\n", encoding="utf-8")
    found = lab.workspace.working_tree_oid(lab.node)

    with pytest.raises(ReviewTreeMismatch) as refusal:
        choose_precondition(
            lab.workspace, lab.reviewer, None, None, reviewed_tree_oid=pinned
        )(review)

    assert refusal.value.expected == pinned
    assert refusal.value.observed == found
    assert (
        read_record(lab.paths.observed_tree(review.activation_id), ObservedTree) is None
    )
    unproven = choose_precondition(
        lab.workspace, lab.reviewer, None, None, reviewed_tree_oid=None
    )(review)
    assert unproven.reset_applied is False
