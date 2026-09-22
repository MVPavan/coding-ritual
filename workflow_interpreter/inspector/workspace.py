"""Isolation and the §5.4 precondition — the two modes of §12.

**Worktree mode.** One worktree per instance at `.wf/<root_id>/worktree` on
branch `wf/<root_id>`, created at first dispatch and removed at terminal. The
tree belongs to the wrapper, so a dirty tree there is always the previous
crew's and is always resettable.

**In-repo mode.** The human's own checkout. Every invariant of worktree mode
holds except physical isolation, and two things replace it: the §12 execution
band (a single-flight `flock` scoped to the repo path — one active crew,
ever) and recorded provenance. `git stash create` snapshots the dirty tree at
dispatch, preserving it as a dangling commit no reset can lose.

**Whose file is it? POSITIVE ATTRIBUTION, and nothing weaker.** In-repo, a path
is resettable only where the wrapper can PROVE the crew produced it. Nothing
is inferred from a path being new, or absent from a set, or otherwise
unaccounted for: the destructive operation requires evidence FOR the crew,
so every gap in the evidence lands on the protected side.

- **Untracked files are never auto-deleted, whatever the evidence says.**
  Attribution rests in part on the crew's own `$WF_EFFECTS_FILE`, which the
  crew controls: a crew that builds its manifest from `git status` names
  the human's mid-run file with no malice at all, and for never-committed
  content the mistake is unrecoverable — there is no blob, no commit, no reflog
  to go back to. So creation always refuses to tier-2 (probed).
- **Tracked files** — `CrewAttribution`, written by `ExitObserver` while the
  crew's activation still held the band. An entry exists only where the
  wrapper's own `git status` saw the path dirty AND the crew declared it AND
  it was not already dirty when that attempt started. A path is resettable now
  only if its content still hashes to the digest recorded then — anything that
  has touched it since breaks the match and protects it again.
- **Commits** — wrapper-pinned lineage. HEAD may be moved off
  `intended_base_commit` only when the commit it sits on is one the WRAPPER
  pinned as an ARTIFACT under `refs/wf/<root_id>/artifact/…` and
  `intended_base_commit` is an ancestor of it. A commit nothing of ours
  references is somebody else's work, and `reset --hard` would leave it
  unreachable. The sibling namespaces (`orphan/`, `prereset/`) preserve commits
  WITHOUT blessing them, and `_is_crew_lineage` reads neither.
- **Everything else** — protected. No prior snapshot, no attribution record, a
  wiped `.wf/`, a digest that no longer matches, an unpinned HEAD: each refuses
  to tier-2. §12 is explicit that an unresolvable dirty tree blocks the
  instance on a human, by design.

**And every reset is recoverable anyway.** Before the first destructive command
of ANY reset, in either mode, the wrapper commits the whole dirty state —
untracked content included — and pins it under
`refs/wf/<root_id>/prereset/<activation_id>`. A snapshot that cannot be pinned
ABORTS the reset rather than proceeding unpinned: attribution is a judgement,
and a judgement that destroys work has to have an undo behind it.

*Flagged reading (§12 sentence "files matching the snapshot are the crew's"):
taken literally that inverts the ownership test, because the `stash create`
snapshot is taken BEFORE the crew runs and can only ever contain what
preceded it. Read as set membership it is worse than inverted — it made every
file that APPEARED during a run the crew's, so a human's untracked notes
written mid-run were auto-`git clean`ed at the next dispatch (probed). What the
same paragraph actually requires — "anything else is human work → tier-2
confirmation required, never auto-reset" — is what is implemented above, with
the snapshot in its real role: proof of what pre-existed the attempt.*

The precondition is asserted BEFORE exec and is idempotent: a precondition
survives crashes, a trailing cleanup does not (§5.4, drills 4, 5, 26).
"""

from __future__ import annotations

import shutil
from contextlib import nullcontext
from pathlib import Path
from typing import Final

import structlog

from workflow_interpreter.bdio import ActivationRecord, ArtifactIdentity
from workflow_interpreter.inspector.artifact import (
    ARTIFACT_NAMESPACE,
    BRANCH_TEMPLATE,
    INSTANCE_BRANCH_REF,
    ORPHAN_NAMESPACE,
    PRERESET_NAMESPACE,
    REF_TEMPLATE,
    ArtifactManager,
    activation_ref,
    namespace_prefix,
    namespaced_ref,
)
from workflow_interpreter.inspector.attribution import (
    AttributionManager,
    decode_dirty_state,
    encode_dirty_state,
)
from workflow_interpreter.inspector.band import BandLock
from workflow_interpreter.inspector.branch import BranchAdvance, BranchAdvanceOutcome
from workflow_interpreter.inspector.clock import Clock, to_iso
from workflow_interpreter.inspector.errors import (
    BandNotHeld,
    DirtyTreeRefused,
    GitCommandError,
    InterruptedWorkPreservationFailed,
    PreconditionRefused,
    ReadOnlyTreeMutation,
    ResumeMismatchReason,
    ResumeTreeMismatch,
    ReviewTreeMismatch,
    SnapshotFailed,
    WrapperDirError,
)
from workflow_interpreter.inspector.gitio import Git
from workflow_interpreter.inspector.models import (
    CrewAttribution,
    DirtyEntry,
    DirtySnapshot,
    HumanConfirmation,
    Liveness,
    ObservedTree,
    PinOutcome,
    PinResult,
    PreconditionResult,
    RecoverySnapshot,
    ResetPlan,
    WorkspaceRecord,
)
from workflow_interpreter.inspector.paths import (
    WrapperPaths,
    read_record,
    write_record,
)
from workflow_interpreter.inspector.procfs import prove_liveness
from workflow_interpreter.ledger.constants import REPO_ID_RELPATH
from workflow_interpreter.schema.models import IsolationMode, Node

_LOG: Final[structlog.stdlib.BoundLogger] = structlog.get_logger(__name__)

__all__ = [
    "ARTIFACT_NAMESPACE",
    "BRANCH_TEMPLATE",
    "INSTANCE_BRANCH_REF",
    "ORPHAN_NAMESPACE",
    "PRERESET_NAMESPACE",
    "REF_TEMPLATE",
    "Workspace",
    "activation_ref",
    "decode_dirty_state",
    "encode_dirty_state",
    "namespace_prefix",
    "namespaced_ref",
]

_SNAPSHOT_MESSAGE: Final[str] = (
    "wf pre-reset snapshot of {activation_id} at {head} (§12): the full dirty "
    "state, untracked content included, as it stood before the reset"
)
_OUTPUTS_MESSAGE: Final[str] = "wf pinned outputs for {activation_id}"
_OUTPUTS_NAMESPACE: Final[str] = "outputs"
_SESSION_NAMESPACE: Final[str] = "session"
_SESSION_MESSAGE: Final[str] = (
    "wf session tree of {activation_id} at {head} (§3): the working tree a "
    "resumed successor of this vendor session must observe"
)

_MSG_MISSING_COMMIT: Final[str] = (
    "intended_base_commit {commit} does not exist in {repo}; a bd record naming "
    "a missing commit halts the instance (§7.4)"
)
_MSG_NOT_RESET: Final[str] = (
    "worktree {path} is at {head} with {dirty} dirty path(s) after the reset; "
    "the §5.4 precondition (HEAD == {intended}, clean tree) does not hold"
)
_MSG_HUMAN_WORK: Final[str] = (
    "refusing to reset {count} path(s) the wrapper cannot attribute to the "
    "crew: {paths}; §12 requires tier-2 human confirmation naming them and "
    "their current content, never an auto-reset"
)
_MSG_HUMAN_COMMIT: Final[str] = (
    "refusing to move HEAD off {head}: no wrapper artifact ref pins it, so it "
    "is not this instance's artifact and a reset would leave it unreachable; "
    "§12 requires tier-2 human confirmation, never an auto-reset"
)
_MSG_NO_SNAPSHOT: Final[str] = (
    "refusing to reset {path}: the pre-destruction snapshot could not be "
    "pinned ({error}), so the reset would not be recoverable if the wrapper's "
    "attribution is wrong (§12)"
)
_MSG_RESUME_UNPROVEN: Final[str] = (
    "activation {activation_id} resumes session {session} but carries no "
    "pinned tree OID to prove the shared checkout against; §3 refuses rather "
    "than resetting the tree its session remembers"
)
_MSG_RESUME_MISMATCH: Final[str] = (
    "refusing to resume activation {activation_id} against {path}: the "
    "session was left on tree {expected} and the checkout now holds "
    "{observed}; another writer has run between the two turns (§3)"
)
_MSG_REVIEW_MISMATCH: Final[str] = (
    "refusing to launch non-writer {activation_id} against {path}: its writer "
    "left tree {expected} and the checkout now holds {observed}; the review "
    "would grade bytes no activation produced (§3)"
)
_MSG_READ_ONLY_MUTATED: Final[str] = (
    "activation {activation_id} does not write, but its checkout moved from "
    "tree {expected} to {observed} while it ran (§3)"
)
_MSG_BAND_REQUIRED: Final[str] = (
    "in-repo isolation requires the §12 execution band; acquire it before "
    "preparing the workspace"
)


class Workspace:
    """Creates, asserts and resets the activation's working tree (§5.4, §12)."""

    def __init__(
        self,
        paths: WrapperPaths,
        git: Git,
        clock: Clock,
        band: BandLock,
        *,
        advance_branch: bool = False,
    ) -> None:
        self._paths = paths
        self._git = git
        self._clock = clock
        self._band = band
        self._advance_branch = advance_branch
        self._artifacts = ArtifactManager(paths, git, self.path_for)
        self._attribution = AttributionManager(
            paths, git, clock, self.path_for, self._entry
        )

    @property
    def band(self) -> BandLock:
        """The §12 execution band for this repo."""
        return self._band

    def path_for(self, node: Node) -> Path:
        """Where this node's crew executes: the worktree, or the repo itself."""
        if node.isolation is IsolationMode.IN_REPO:
            return self._paths.config.repo_root
        return self._paths.worktree

    # -- the §5.4 precondition -------------------------------------------

    def prepare(
        self,
        activation: ActivationRecord,
        node: Node,
        *,
        prior_dirty_state: str | None = None,
        confirmation: HumanConfirmation | None = None,
    ) -> PreconditionResult:
        """Assert `HEAD == intended_base_commit` and a clean tree, resetting if needed.

        Idempotent by construction: it computes the plan from the tree's CURRENT
        state every time, so a crash mid-reset converges on re-run (drill 5) and
        a re-run against an already-correct tree does nothing (drill 4).
        """
        if node.isolation is IsolationMode.IN_REPO and not self._band.held:
            raise BandNotHeld(_MSG_BAND_REQUIRED)
        return self._prepare_owned(
            activation,
            node,
            prior_dirty_state=prior_dirty_state,
            confirmation=confirmation,
        )

    def resume(self, activation: ActivationRecord, node: Node) -> PreconditionResult:
        """Prove the shared tree is still the one this session remembers (§3).

        The resumed writer's whole precondition: no reset, no clean, no HEAD
        move — the vendor thread carries the context for exactly these bytes,
        and resetting them is what would make the resume a lie. Ownership and
        the §3.2 trio are still taken, so a rework that follows reads this
        attempt rather than the one whose session it inherited.
        """
        meta = activation.metadata
        in_repo = node.isolation is IsolationMode.IN_REPO
        if in_repo and not self._band.held:
            raise BandNotHeld(_MSG_BAND_REQUIRED)
        expected = meta.expected_tree_oid
        if meta.source_session_id is None or expected is None:
            raise ResumeTreeMismatch(
                _MSG_RESUME_UNPROVEN.format(
                    activation_id=activation.activation_id,
                    session=meta.source_session_id,
                ),
                reason=ResumeMismatchReason.MISSING_SNAPSHOT,
                expected=expected,
            )
        intended = meta.intended_base_commit
        cwd = self._ensure_tree(intended, in_repo=in_repo)
        observed = self._working_tree_oid(cwd)
        if observed != expected:
            raise ResumeTreeMismatch(
                _MSG_RESUME_MISMATCH.format(
                    activation_id=activation.activation_id,
                    path=cwd,
                    expected=expected,
                    observed=observed,
                ),
                reason=ResumeMismatchReason.INTERVENING_WRITER,
                expected=expected,
                observed=observed,
            )
        return self._finish_precondition(
            activation,
            node,
            cwd,
            intended=intended,
            proven=self._git.head_commit(cwd=cwd),
            snapshot=self._snapshot(cwd) if in_repo else None,
            plan=ResetPlan(),
            pre_reset=None,
        )

    def observe_shared_tree(
        self,
        activation: ActivationRecord,
        node: Node,
        *,
        expected_tree_oid: str | None = None,
    ) -> PreconditionResult:
        """Give a non-writing activation the tree as it stands, and record it (§3).

        A reviewer reads what the writer before it left, so the checkout is
        created only where there is none, and nothing else about it moves:
        not HEAD, not the dirty state, not tree ownership. The OID recorded
        here is the before half of `after == before`.

        `expected_tree_oid` is the tree the reviewed writer pinned, where one
        was: the found tree must BE it, or the launch refuses by name. With no
        such proof the observation is record-only.
        """
        in_repo = node.isolation is IsolationMode.IN_REPO
        if in_repo and not self._band.held:
            raise BandNotHeld(_MSG_BAND_REQUIRED)
        intended = activation.metadata.intended_base_commit
        cwd = self._ensure_tree(intended, in_repo=in_repo)
        observed = self._working_tree_oid(cwd)
        if expected_tree_oid is not None and observed != expected_tree_oid:
            raise ReviewTreeMismatch(
                _MSG_REVIEW_MISMATCH.format(
                    activation_id=activation.activation_id,
                    path=cwd,
                    expected=expected_tree_oid,
                    observed=observed,
                ),
                expected=expected_tree_oid,
                observed=observed,
            )
        write_record(
            self._paths.observed_tree(activation.activation_id),
            ObservedTree(
                activation_id=activation.activation_id,
                tree_oid=observed,
                observed_at=to_iso(self._clock.now()),
            ),
        )
        head = self._git.head_commit(cwd=cwd)
        _LOG.info(
            "wf.precondition.observed",
            activation_id=activation.activation_id,
            commit=head,
            tree_oid=observed,
        )
        return PreconditionResult(
            intended_base_commit=intended,
            pre_attempt_commit=head,
            reset_verified_commit=head,
            # §12: in-repo, this activation's exit records attribution too, and
            # an unknown pre-attempt state REPLACES the record with an empty
            # one. A reviewer that observed the tree would therefore erase the
            # writer before it, handing that writer's files to the next fresh
            # reset as the human's work. The snapshot only reads (it creates
            # objects, never touches the tree), so stating what was found here
            # costs the non-writer none of its "move nothing" guarantee.
            pre_attempt_dirty_state=(
                encode_dirty_state(self._snapshot(cwd)) if in_repo else None
            ),
        )

    def verify_shared_tree(self, activation: ActivationRecord, node: Node) -> None:
        """Hold a non-writer to the tree it was given, where the check is reached.

        Best-effort on purpose (§3): a steered or crashed reviewer never gets
        here, and the next resumed writer's mandatory match is what covers that
        gap. An unrecorded observation is therefore silence, not a violation.
        """
        if node.writes:
            return
        record = read_record(
            self._paths.observed_tree(activation.activation_id), ObservedTree
        )
        if record is None:
            return
        observed = self._working_tree_oid(self.path_for(node))
        if observed != record.tree_oid:
            raise ReadOnlyTreeMutation(
                _MSG_READ_ONLY_MUTATED.format(
                    activation_id=activation.activation_id,
                    expected=record.tree_oid,
                    observed=observed,
                )
            )

    def pin_session_tree(self, activation: ActivationRecord, node: Node) -> str | None:
        """Pin what a writing turn left, so a later resume has a tree to prove.

        The same full-tree snapshot §12 takes before a reset — tracked,
        staged, deleted and untracked state alike — pinned under its own
        namespace so nothing collects it, and reported as the tree OID a
        resumed successor must observe.
        """
        if not node.writes:
            return None
        cwd = self.path_for(node)
        ref = namespaced_ref(
            self._paths.root_id, _SESSION_NAMESPACE, activation.activation_id
        )
        head = self._git.head_commit(cwd=cwd)
        commit = self._git.snapshot_commit(
            message=_SESSION_MESSAGE.format(
                activation_id=activation.activation_id, head=head
            ),
            parents=(head,),
            index_path=self._paths.snapshot_index,
            cwd=cwd,
        )
        self._git.update_ref(ref, commit, cwd=cwd)
        if self._git.ref_target(ref, cwd=cwd) != commit:
            raise SnapshotFailed(f"{ref} did not read back as {commit}")
        return self._git.tree_oid(commit, cwd=cwd)

    def session_tree_oid(self, activation_id: str) -> str | None:
        """The §3 tree OID pinned for this activation, or `None` if none was.

        Read from the ref rather than kept in memory, because the turn that
        pinned it and the close that publishes it are different processes.
        """
        cwd = self._paths.config.repo_root
        commit = self._git.ref_target(
            namespaced_ref(self._paths.root_id, _SESSION_NAMESPACE, activation_id),
            cwd=cwd,
        )
        return None if commit is None else self._git.tree_oid(commit, cwd=cwd)

    def working_tree_oid(self, node: Node) -> str:
        """The full-tree OID of this node's checkout, computed without mutation."""
        return self._working_tree_oid(self.path_for(node))

    def resumable_tree_oid(self, activation: ActivationRecord, node: Node) -> str:
        """The tree a successor of this turn will find, checkout or no checkout.

        A killed turn whose instance never materialized a checkout left no
        bytes in one, and its successor's `_ensure_tree` will create it at the
        intended base — so the base commit's tree IS the honest proof for it.
        Anything else would refuse a continuation over a tree nobody wrote.
        """
        cwd = self.path_for(node)
        if not (cwd / ".git").exists():
            return self._git.tree_oid(
                activation.metadata.intended_base_commit,
                cwd=self._paths.config.repo_root,
            )
        return self._working_tree_oid(cwd)

    def _working_tree_oid(self, cwd: Path) -> str:
        """The §3 tree proof for one checkout, over the throwaway index."""
        return self._git.working_tree_oid(
            index_path=self._paths.snapshot_index, cwd=cwd
        )

    def _prepare_owned(
        self,
        activation: ActivationRecord,
        node: Node,
        *,
        prior_dirty_state: str | None,
        confirmation: HumanConfirmation | None,
    ) -> PreconditionResult:
        """Prepare and transfer ownership under the preservation fence."""
        intended = activation.metadata.intended_base_commit
        in_repo = node.isolation is IsolationMode.IN_REPO
        if in_repo and not self._band.held:
            raise BandNotHeld(_MSG_BAND_REQUIRED)
        cwd = self._ensure_tree(intended, in_repo=in_repo)

        snapshot = self._snapshot(cwd) if in_repo else None
        prior = decode_dirty_state(prior_dirty_state) if in_repo else None
        plan = self._plan(
            cwd, intended, snapshot, prior, confirmation, activation.activation_id
        )
        if plan.refused:
            raise DirtyTreeRefused(
                self._refusal(plan),
                plan.protected,
                protected_head=plan.protected_head,
            )
        pre_reset = self._apply(cwd, intended, plan, activation.activation_id)
        self._assert_clean(cwd, intended, in_repo=in_repo)
        return self._finish_precondition(
            activation,
            node,
            cwd,
            intended=intended,
            proven=intended,
            snapshot=snapshot,
            plan=plan,
            pre_reset=pre_reset,
        )

    def _finish_precondition(
        self,
        activation: ActivationRecord,
        node: Node,
        cwd: Path,
        *,
        intended: str,
        proven: str,
        snapshot: DirtySnapshot | None,
        plan: ResetPlan,
        pre_reset: str | None,
    ) -> PreconditionResult:
        """Take ownership of the proven tree and state the §3.2 carry-forward.

        Shared by both writing branches, and the sharing is the point: a
        resumed writer takes the checkout over exactly as a reset one does —
        only the commit it PROVED differs (the reset's intended base, or the
        HEAD the resume found the remembered tree on). Transfer happens only
        after the proof, so a refusal leaves the preceding producer's bytes and
        ownership intact.
        """
        self._write_record(activation, node, cwd, intended)
        _LOG.info(
            "wf.precondition.verified",
            activation_id=activation.activation_id,
            isolation=(node.isolation or IsolationMode.WORKTREE).value,
            commit=proven,
            reset_applied=pre_reset is not None,
            pre_reset_commit=pre_reset,
        )
        return PreconditionResult(
            intended_base_commit=intended,
            pre_attempt_commit=proven,
            reset_verified_commit=proven,
            pre_attempt_dirty_state=(
                encode_dirty_state(snapshot) if snapshot is not None else None
            ),
            plan=plan,
            reset_applied=pre_reset is not None,
            pre_reset_commit=pre_reset,
        )

    def _ensure_tree(self, intended: str, *, in_repo: bool) -> Path:
        """Return the working tree, creating the §5.4 worktree at first dispatch."""
        repo_root = self._paths.config.repo_root
        if not self._git.commit_exists(intended, cwd=repo_root):
            raise PreconditionRefused(
                _MSG_MISSING_COMMIT.format(commit=intended, repo=repo_root)
            )
        if in_repo:
            return repo_root
        worktree = self._paths.worktree
        if not (worktree / ".git").exists():
            worktree.parent.mkdir(parents=True, exist_ok=True)
            self._git.worktree_add(
                worktree,
                BRANCH_TEMPLATE.format(root_id=self._paths.root_id),
                intended,
                cwd=repo_root,
            )
        return worktree

    def _snapshot(self, cwd: Path) -> DirtySnapshot:
        """§12 provenance: the dirty tree as a stash commit plus path digests.

        Known gotcha, verified against git: `stash create` covers tracked
        modifications ONLY — untracked files are not in the snapshot commit
        (there is no `--include-untracked` on `create`). That gap is why this
        is the §3.2 carry-forward's evidence of what PRE-EXISTED the attempt
        and not the reset's undo: `_pin_pre_reset` builds the undo, with
        plumbing that does capture untracked content.
        """
        entries = tuple(
            self._entry(cwd, path, tracked)
            for path, tracked in self._git.status_paths(cwd=cwd)
        )
        stash = self._git.stash_create(cwd=cwd) if entries else None
        return DirtySnapshot(stash_commit=stash, entries=entries)

    def _entry(self, cwd: Path, path: str, tracked: bool) -> DirtyEntry:
        """One dirty path, identified by content WHERE IT HAS content (§12).

        The one place either §12 record is built, because both used to hash
        every dirty path with no filter — and `git hash-object` on the directory
        `git status` reports for a nested checkout or a dirty submodule exits
        128. That fatal escaped `prepare()` and `ExitObserver.observe()` alike,
        wedging the instance on every subsequent tick (probed).
        """
        return DirtyEntry(
            path=path,
            digest=self._git.hash_working_file(path, cwd=cwd),
            tracked=tracked,
            kind=self._git.entry_kind(path, cwd=cwd),
        )

    def _plan(
        self,
        cwd: Path,
        intended: str,
        snapshot: DirtySnapshot | None,
        prior: DirtySnapshot | None,
        confirmation: HumanConfirmation | None,
        activation_id: str,
    ) -> ResetPlan:
        """Decide what may be destroyed, requiring evidence FOR every item (§12).

        The ENGINE's own `.wf/repo-id` is neither side of that judgement in-repo
        (store-restructure §3.6), exactly as `ledger.paths.coordinator_dirt` and
        the §7.5 observation excuse it, through the one `REPO_ID_RELPATH` they
        all read. The file is minted by the first ledger open in a fresh
        checkout, and in-repo that open writes into the very tree this plan
        reads — so a first run would refuse itself as human work on a path the
        engine had just minted. It is excused rather than made resettable:
        deleting it would strand the ledger that already pins the id it holds.
        """
        head = self._git.head_commit(cwd=cwd)
        head_move_required = head != intended
        if snapshot is None:
            dirty = tuple(path for path, _ in self._git.status_paths(cwd=cwd))
            return ResetPlan(resettable=dirty, head_move_required=head_move_required)

        attribution = self._attribution.read()
        resettable: list[str] = []
        protected: list[str] = []
        for entry in snapshot.entries:
            if entry.path == REPO_ID_RELPATH:
                continue
            if self._attribution.is_crew_output(
                entry, attribution, prior, confirmation, activation_id
            ):
                resettable.append(entry.path)
            else:
                protected.append(entry.path)
        head_protected = head_move_required and not self._is_crew_lineage(
            cwd, intended, head
        )
        return ResetPlan(
            resettable=tuple(resettable),
            protected=tuple(protected),
            head_move_required=head_move_required,
            head_protected=head_protected,
            protected_head=head if head_protected else None,
        )

    def _is_crew_lineage(self, cwd: Path, intended: str, head: str) -> bool:
        """Delegate the instance-lineage check to artifact ownership."""
        return self._artifacts.is_crew_lineage(cwd, intended, head)

    @staticmethod
    def _refusal(plan: ResetPlan) -> str:
        """Why this plan may not be applied, naming what is at risk."""
        if plan.protected:
            return _MSG_HUMAN_WORK.format(
                count=len(plan.protected), paths=", ".join(plan.protected)
            )
        return _MSG_HUMAN_COMMIT.format(head=plan.protected_head)

    def _apply(
        self, cwd: Path, intended: str, plan: ResetPlan, activation_id: str
    ) -> str | None:
        """Perform the reset, behind a pinned snapshot. Returns that snapshot.

        Nothing here runs while a path is still protected — and nothing here
        runs at all until the pre-destruction snapshot is pinned, because
        attribution is a judgement and a judgement that destroys work needs an
        undo behind it. `None` means there was nothing to reset.
        """
        if not plan.resettable and not plan.head_move_required:
            return None
        snapshot = self._pin_pre_reset(cwd, activation_id)
        untracked = self._untracked(cwd, plan.resettable)
        self._git.reset_hard(intended, cwd=cwd)
        self._git.clean_paths(untracked, cwd=cwd)
        return snapshot

    def _pin_pre_reset(self, cwd: Path, activation_id: str) -> str:
        """Commit and pin the whole dirty state BEFORE a single byte is destroyed.

        Refuses rather than proceeding unpinned: an unrecoverable reset is the
        failure mode this exists to remove, so a snapshot that cannot be made
        or cannot be pinned stops the reset instead of being logged past.

        The previous snapshot for this activation is carried as a second parent
        so a re-reset cannot strand it: one ref per activation, and every
        snapshot it ever held stays reachable from it.
        """
        ref = namespaced_ref(self._paths.root_id, PRERESET_NAMESPACE, activation_id)
        try:
            head = self._git.head_commit(cwd=cwd)
            previous = self._git.ref_target(ref, cwd=cwd)
            commit = self._git.snapshot_commit(
                message=_SNAPSHOT_MESSAGE.format(
                    activation_id=activation_id, head=head
                ),
                parents=(head,) if previous is None else (head, previous),
                index_path=self._paths.snapshot_index,
                cwd=cwd,
            )
            self._git.update_ref(ref, commit, cwd=cwd)
            pinned = self._git.ref_target(ref, cwd=cwd)
        except (GitCommandError, OSError, UnicodeDecodeError) as exc:
            raise SnapshotFailed(_MSG_NO_SNAPSHOT.format(path=cwd, error=exc)) from exc
        if pinned != commit:
            raise SnapshotFailed(
                _MSG_NO_SNAPSHOT.format(path=cwd, error=f"{ref} reads back as {pinned}")
            )
        _LOG.info(
            "wf.reset.snapshot_pinned",
            activation_id=activation_id,
            ref=ref,
            commit=commit,
        )
        return commit

    def read_recovery(self, activation: ActivationRecord) -> RecoverySnapshot | None:
        """Read and validate producer evidence without reading checkout content."""
        record = read_record(
            self._paths.recovery_snapshot(activation.activation_id), RecoverySnapshot
        )
        if record is None:
            return None
        ref = namespaced_ref(self._paths.root_id, "recovery", activation.activation_id)
        if (
            activation.metadata.wf_root_id != self._paths.root_id
            or record.root_id != self._paths.root_id
            or record.activation_id != activation.activation_id
            or record.intended_base != activation.metadata.intended_base_commit
            or record.ref != ref
        ):
            raise SnapshotFailed("recovery producer identity mismatch")
        if record.commit is not None:
            cwd = self._paths.config.repo_root
            if (
                record.observed_head is None
                or self._git.rev_parse(f"{record.commit}^1", cwd=cwd)
                != record.observed_head
            ):
                raise SnapshotFailed("recovery head identity mismatch")
            if self._git.tree_oid(record.commit, cwd=cwd) != record.tree:
                raise SnapshotFailed("recovery tree identity mismatch")
            target = self._git.ref_target(ref, cwd=cwd)
            if target != record.commit and (
                record.pinned or target != record.previous_commit
            ):
                raise SnapshotFailed("recovery pin identity mismatch")
        return record

    def _finish_recovery_pin(self, record: RecoverySnapshot) -> RecoverySnapshot:
        """Repair pin/persist crashes using the recorded object, never current files."""
        if record.commit is None or record.pinned:
            return record
        cwd = self._paths.config.repo_root
        if self._git.ref_target(record.ref, cwd=cwd) != record.commit:
            self._git.update_ref(record.ref, record.commit, cwd=cwd)
        if self._git.ref_target(record.ref, cwd=cwd) != record.commit:
            raise SnapshotFailed("recovery pin failed read-back")
        record = record.model_copy(update={"pinned": True})
        write_record(self._paths.recovery_snapshot(record.activation_id), record)
        return record

    def preserve_interrupted(
        self, activation: ActivationRecord, node: Node
    ) -> RecoverySnapshot | None:
        """Keep recovery failures distinct from retryable pre-reset refusals."""
        try:
            return self._preserve_interrupted(activation, node)
        except (SnapshotFailed, WrapperDirError, OSError, UnicodeDecodeError) as exc:
            raise InterruptedWorkPreservationFailed(str(exc)) from exc

    def _preserve_interrupted(
        self, activation: ActivationRecord, node: Node
    ) -> RecoverySnapshot | None:
        """Preserve confirmed-dead owned writer content before grading or close.

        Missing legacy ownership is explicitly unavailable. A previous producer's
        evidence can be replayed after reuse, but cannot capture its successor.
        The pending record precedes the ref write so pin failures are retryable.
        """
        if activation.metadata.wf_root_id != self._paths.root_id:
            raise SnapshotFailed("foreign recovery activation")
        if not node.writes:
            return None
        # Worktree callers already hold their activation/coordination guard.
        # Only in-repo isolation needs the shared execution band.
        guard = (
            self._band
            if node.isolation is IsolationMode.IN_REPO and not self._band.held
            else nullcontext()
        )
        with guard:
            try:
                record = self.read_recovery(activation)
                if record is not None:
                    record = self._finish_recovery_pin(record)
                owner = read_record(
                    self._paths.in_repo_owner_record
                    if node.isolation is IsolationMode.IN_REPO
                    else self._paths.workspace_record,
                    WorkspaceRecord,
                )
                cwd = self.path_for(node)
                owned = (
                    owner is not None
                    and owner.owner_activation_id == activation.activation_id
                    and owner.path == str(cwd)
                    and owner.isolation == (node.isolation or IsolationMode.WORKTREE)
                    and owner.expected_head == activation.metadata.intended_base_commit
                    and not owner.read_only
                )
                if not owned or activation.metadata.handle is None:
                    if record is not None and record.pinned:
                        return record
                    unavailable = RecoverySnapshot(
                        root_id=self._paths.root_id,
                        activation_id=activation.activation_id,
                        intended_base=activation.metadata.intended_base_commit,
                        ref=namespaced_ref(
                            self._paths.root_id, "recovery", activation.activation_id
                        ),
                        unavailable="producer ownership or process identity unavailable",
                    )
                    write_record(
                        self._paths.recovery_snapshot(activation.activation_id),
                        unavailable,
                    )
                    return unavailable
                proof = prove_liveness(self._paths.config, activation.metadata.handle)
                if proof.status not in (Liveness.DEAD, Liveness.IDENTITY_MISMATCH):
                    raise SnapshotFailed("recovery requires confirmed process death")
                if not self._git.status_paths(cwd=cwd):
                    return record
                head = self._git.head_commit(cwd=cwd)
                previous = record.commit if record is not None else None
                ref = namespaced_ref(
                    self._paths.root_id, "recovery", activation.activation_id
                )
                if self._git.ref_target(ref, cwd=cwd) != previous:
                    raise SnapshotFailed("unrecorded recovery ref")
                commit = self._git.snapshot_commit(
                    message=f"wf interrupted work from {activation.activation_id} at {head}",
                    parents=(head,) if previous is None else (head, previous),
                    index_path=self._paths.snapshot_index,
                    cwd=cwd,
                )
                tree = self._git.tree_oid(commit, cwd=cwd)
                if record is not None and record.pinned and tree == record.tree:
                    return record
                pending = RecoverySnapshot(
                    root_id=self._paths.root_id,
                    activation_id=activation.activation_id,
                    intended_base=activation.metadata.intended_base_commit,
                    observed_head=head,
                    ref=ref,
                    commit=commit,
                    tree=tree,
                    previous_commit=previous,
                )
                write_record(
                    self._paths.recovery_snapshot(activation.activation_id), pending
                )
                return self._finish_recovery_pin(pending)
            except (
                GitCommandError,
                OSError,
                UnicodeDecodeError,
                WrapperDirError,
            ) as exc:
                raise SnapshotFailed(
                    f"interrupted work preservation failed: {exc}"
                ) from exc

    def _untracked(self, cwd: Path, resettable: tuple[str, ...]) -> tuple[str, ...]:
        """The resettable paths git will not restore for us — untracked files."""
        selected = frozenset(resettable)
        return tuple(
            path
            for path, tracked in self._git.status_paths(cwd=cwd)
            if not tracked and path in selected
        )

    def _assert_clean(self, cwd: Path, intended: str, *, in_repo: bool) -> None:
        """The precondition itself: HEAD at the intended commit, tree clean.

        Clean of everything `_plan` could have acted on: the one path it
        excuses is excused here too, or the reset it deliberately left alone
        would fail the very assertion it was spared for.
        """
        head = self._git.head_commit(cwd=cwd)
        dirty = tuple(
            entry
            for entry in self._git.status_paths(cwd=cwd)
            if not (in_repo and entry[0] == REPO_ID_RELPATH)
        )
        if head != intended or dirty:
            raise PreconditionRefused(
                _MSG_NOT_RESET.format(
                    path=cwd, head=head, dirty=len(dirty), intended=intended
                )
            )

    def _write_record(
        self, activation: ActivationRecord, node: Node, cwd: Path, intended: str
    ) -> None:
        """Record the §5.4 worktree / §12 band ownership for this activation."""
        isolation = node.isolation or IsolationMode.WORKTREE
        record = WorkspaceRecord(
            isolation=isolation,
            path=str(cwd),
            branch=(
                None
                if isolation is IsolationMode.IN_REPO
                else BRANCH_TEMPLATE.format(root_id=self._paths.root_id)
            ),
            owner_activation_id=activation.activation_id,
            expected_head=intended,
            read_only=not bool(node.writes),
            created_at=to_iso(self._clock.now()),
        )
        if isolation is IsolationMode.IN_REPO:
            write_record(self._paths.in_repo_owner_record, record)
        write_record(self._paths.workspace_record, record)

    # -- artifact identity (§7.4) ----------------------------------------

    def pin_artifact(
        self,
        activation: ActivationRecord,
        node: Node,
        *,
        declared: frozenset[str] | None = None,
        quarantine: bool = False,
    ) -> PinResult:
        """Delegate artifact claiming while preserving Workspace's public seam."""
        result = self._artifacts.pin_artifact(
            activation, node, declared=declared, quarantine=quarantine
        )
        if not self._advance_branch or result.identity is None:
            return result
        branch = self.advance_instance_branch(
            result.identity.commit_oid, cwd=self.path_for(node)
        )
        return result.model_copy(update={"branch": branch})

    def advance_instance_branch(self, commit: str, *, cwd: Path) -> BranchAdvance:
        """Advance the instance branch without mistaking divergence for transport failure."""
        branch = INSTANCE_BRANCH_REF.format(root_id=self._paths.root_id)
        current = self._git.ref_target(branch, cwd=cwd)
        if current is None:
            return BranchAdvance(outcome=BranchAdvanceOutcome.MISSING, target=commit)
        if current == commit:
            return BranchAdvance(
                outcome=BranchAdvanceOutcome.UNCHANGED, target=commit, previous=current
            )
        if not self._git.is_ancestor(current, commit, cwd=cwd):
            return BranchAdvance(
                outcome=BranchAdvanceOutcome.DIVERGED, target=commit, previous=current
            )
        if self._git.update_ref_cas(branch, commit, current, cwd=cwd):
            return BranchAdvance(
                outcome=BranchAdvanceOutcome.ADVANCED, target=commit, previous=current
            )
        again = self._git.ref_target(branch, cwd=cwd)
        if again is None:
            return BranchAdvance(outcome=BranchAdvanceOutcome.MISSING, target=commit)
        if again == commit:
            return BranchAdvance(
                outcome=BranchAdvanceOutcome.UNCHANGED, target=commit, previous=again
            )
        if again == current:
            raise GitCommandError("instance branch compare-and-swap failed")
        return BranchAdvance(
            outcome=BranchAdvanceOutcome.DIVERGED, target=commit, previous=again
        )

    def pin_outputs(
        self, activation: ActivationRecord, output_paths: tuple[str, ...]
    ) -> PinResult:
        """Pin the collected wrapper-owned outputs and then remove their snapshot."""
        snapshot = self._paths.outputs_snapshot(activation.activation_id)
        cwd = self._paths.config.repo_root
        ref = namespaced_ref(
            self._paths.root_id, _OUTPUTS_NAMESPACE, activation.activation_id
        )
        commit = self._git.commit_directory(
            output_paths,
            root=snapshot,
            message=_OUTPUTS_MESSAGE.format(activation_id=activation.activation_id),
            index_path=snapshot.parent / f"{activation.activation_id}.outputs.index",
            cwd=cwd,
        )
        self._git.update_ref(ref, commit, cwd=cwd)
        result = PinResult(
            outcome=PinOutcome.PINNED,
            identity=ArtifactIdentity(
                commit_oid=commit, tree_oid=self._git.tree_oid(commit, cwd=cwd)
            ),
            commit=commit,
            ref=ref,
        )
        shutil.rmtree(snapshot, ignore_errors=True)
        return result

    def record_attribution(
        self,
        activation: ActivationRecord,
        node: Node,
        *,
        declared: frozenset[str],
    ) -> CrewAttribution | None:
        """Delegate durable dirty-tree attribution to its focused component."""
        return self._attribution.record_attribution(activation, node, declared=declared)

    def remove_worktree(self) -> None:
        """Remove the instance worktree at terminal (§5.4). Never the repo."""
        worktree = self._paths.worktree
        if worktree.exists():
            self._git.worktree_remove(worktree, cwd=self._paths.config.repo_root)
