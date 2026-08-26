"""Isolation and the §5.4 precondition — the two modes of §12.

**Worktree mode.** One worktree per instance at `.wf/<root_id>/worktree` on
branch `wf/<root_id>`, created at first dispatch and removed at terminal. The
tree belongs to the wrapper, so a dirty tree there is always the previous
runner's and is always resettable.

**In-repo mode.** The human's own checkout. Every invariant of worktree mode
holds except physical isolation, and two things replace it: the §12 execution
band (a single-flight `flock` scoped to the repo path — one active runner,
ever) and recorded provenance. `git stash create` snapshots the dirty tree at
dispatch, preserving it as a dangling commit no reset can lose.

**Whose file is it? POSITIVE ATTRIBUTION, and nothing weaker.** In-repo, a path
is resettable only where the wrapper can PROVE the runner produced it. Nothing
is inferred from a path being new, or absent from a set, or otherwise
unaccounted for: the destructive operation requires evidence FOR the runner,
so every gap in the evidence lands on the protected side.

- **Untracked files are never auto-deleted, whatever the evidence says.**
  Attribution rests in part on the runner's own `$WF_EFFECTS_FILE`, which the
  runner controls: a runner that builds its manifest from `git status` names
  the human's mid-run file with no malice at all, and for never-committed
  content the mistake is unrecoverable — there is no blob, no commit, no reflog
  to go back to. So creation always refuses to tier-2 (probed).
- **Tracked files** — `RunnerAttribution`, written by `ExitObserver` while the
  runner's activation still held the band. An entry exists only where the
  wrapper's own `git status` saw the path dirty AND the runner declared it AND
  it was not already dirty when that attempt started. A path is resettable now
  only if its content still hashes to the digest recorded then — anything that
  has touched it since breaks the match and protects it again.
- **Commits** — wrapper-pinned lineage. HEAD may be moved off
  `intended_base_commit` only when the commit it sits on is one the WRAPPER
  pinned as an ARTIFACT under `refs/wf/<root_id>/artifact/…` and
  `intended_base_commit` is an ancestor of it. A commit nothing of ours
  references is somebody else's work, and `reset --hard` would leave it
  unreachable. The sibling namespaces (`orphan/`, `prereset/`) preserve commits
  WITHOUT blessing them, and `_is_runner_lineage` reads neither.
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

*Flagged reading (§12 sentence "files matching the snapshot are the runner's"):
taken literally that inverts the ownership test, because the `stash create`
snapshot is taken BEFORE the runner runs and can only ever contain what
preceded it. Read as set membership it is worse than inverted — it made every
file that APPEARED during a run the runner's, so a human's untracked notes
written mid-run were auto-`git clean`ed at the next dispatch (probed). What the
same paragraph actually requires — "anything else is human work → tier-2
confirmation required, never auto-reset" — is what is implemented above, with
the snapshot in its real role: proof of what pre-existed the attempt.*

The precondition is asserted BEFORE exec and is idempotent: a precondition
survives crashes, a trailing cleanup does not (§5.4, drills 4, 5, 26).
"""

from __future__ import annotations

from pathlib import Path
from typing import Final

import structlog
from pydantic import ValidationError

from workflow_interpreter.bdio import ActivationRecord, ArtifactIdentity
from workflow_interpreter.schema.loader import canonical_json_bytes
from workflow_interpreter.schema.models import IsolationMode, Node
from workflow_interpreter.supervisor.band import BandLock
from workflow_interpreter.supervisor.channels import runner_committer_email
from workflow_interpreter.supervisor.clock import Clock, to_iso
from workflow_interpreter.supervisor.errors import (
    DirtyTreeRefused,
    GitCommandError,
    PreconditionRefused,
    WrapperDirError,
)
from workflow_interpreter.supervisor.gitio import Git
from workflow_interpreter.supervisor.models import (
    DirtyEntry,
    DirtySnapshot,
    EntryKind,
    HumanConfirmation,
    PinOutcome,
    PinResult,
    PreconditionResult,
    ResetPlan,
    RunnerAttribution,
    WorkspaceRecord,
)
from workflow_interpreter.supervisor.paths import (
    WrapperPaths,
    read_record,
    write_record,
)

_LOG: Final[structlog.stdlib.BoundLogger] = structlog.get_logger(__name__)

BRANCH_TEMPLATE: Final[str] = "wf/{root_id}"

ARTIFACT_NAMESPACE: Final[str] = "artifact"
ORPHAN_NAMESPACE: Final[str] = "orphan"
PRERESET_NAMESPACE: Final[str] = "prereset"
REF_TEMPLATE: Final[str] = "refs/wf/{root_id}/{namespace}/{activation_id}"
"""Three SIBLING namespaces under one instance's refs, and the separation is
load-bearing rather than tidy. `artifact/` is the §7.4 pin, and a commit under
it is also the §12 authority to reset HEAD off it. `orphan/` preserves a commit
recovery could not attribute, and `prereset/` preserves what a reset was about
to destroy — neither is authority for anything, and `_is_runner_lineage` reads
only `artifact/`. A flat `refs/wf/<root_id>/…` prefix could not express that:
every ref the wrapper wrote for any reason would have blessed its commit."""

_SNAPSHOT_MESSAGE: Final[str] = (
    "wf pre-reset snapshot of {activation_id} at {head} (§12): the full dirty "
    "state, untracked content included, as it stood before the reset"
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
    "runner: {paths}; §12 requires tier-2 human confirmation naming them and "
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
_REASON_NOT_DESCENDANT: Final[str] = (
    "it does not descend from intended_base_commit {intended}"
)
_REASON_UNDECLARED: Final[str] = (
    "it touches {paths}, which the runner did not declare in $WF_EFFECTS_FILE"
)
_REASON_NO_MANIFEST: Final[str] = (
    "no $WF_EFFECTS_FILE manifest exists for this attempt, so in-repo there is "
    "nothing separating a commit the runner made from one the human made"
)
_REASON_NOT_OUR_COMMITTER: Final[str] = (
    "it was committed by {found!r}, not by this activation's runner identity "
    "{wanted!r}; path containment alone made a commit the HUMAN made in their "
    "own checkout attributable whenever the dead runner's manifest happened to "
    "name the same path (§7.4)"
)
_MSG_BAND_REQUIRED: Final[str] = (
    "in-repo isolation requires the §12 execution band; acquire it before "
    "preparing the workspace"
)


def activation_ref(root_id: str, activation_id: str) -> str:
    """`refs/wf/<root_id>/artifact/<activation_id>` — the §7.4 artifact pin."""
    return namespaced_ref(root_id, ARTIFACT_NAMESPACE, activation_id)


def namespaced_ref(root_id: str, namespace: str, activation_id: str) -> str:
    """One instance ref in one of the three namespaces (see `REF_TEMPLATE`)."""
    return REF_TEMPLATE.format(
        root_id=root_id, namespace=namespace, activation_id=activation_id
    )


def namespace_prefix(root_id: str, namespace: str) -> str:
    """Everything under one namespace — the set `refs_under` answers about."""
    return namespaced_ref(root_id, namespace, "")


def encode_dirty_state(snapshot: DirtySnapshot) -> str:
    """The §3.2 `pre_attempt_dirty_state` carrier value (canonical JSON)."""
    return canonical_json_bytes(snapshot.model_dump(mode="json")).decode("utf-8")


def decode_dirty_state(value: str | None) -> DirtySnapshot | None:
    """Parse a recorded `pre_attempt_dirty_state`; `None` when absent or corrupt.

    `wire.py` validates that the carrier is canonical JSON of an OBJECT, and
    nothing validates that the object is a `DirtySnapshot` — so a row whose §3.2
    trio was written out of band (a hand edit, an older tool, a direct `bd
    update`; bead cr-too) decodes to a `ValidationError`. That is a `ValueError`,
    which is neither an `OSError` nor a `SupervisorError`, so it escaped
    `ExitObserver._post_exit`'s catch and took `observe()` down BEFORE
    `record_exit` ran — a provably-exited child left recorded as `dispatched`,
    re-classified as an infra failure on every subsequent tick (probed, r4).

    Corrupt provenance is therefore treated as NO provenance, which is the
    answer this package already gives a missing record and the direction §12
    resolves toward: with no snapshot, `_plan` has no attribution to match
    against, `record_attribution` records nothing, and every dirty path lands
    on the protected side. The warning is loud so the anomaly is seen.
    """
    if not value:
        return None
    try:
        return DirtySnapshot.model_validate_json(value)
    except ValidationError as exc:
        _LOG.warning("wf.dirty_state.undecodable", error=str(exc), value=value)
        return None


class Workspace:
    """Creates, asserts and resets the activation's working tree (§5.4, §12)."""

    def __init__(
        self, paths: WrapperPaths, git: Git, clock: Clock, band: BandLock | None = None
    ) -> None:
        self._paths = paths
        self._git = git
        self._clock = clock
        self._band = band if band is not None else BandLock(paths.band_lock)

    @property
    def band(self) -> BandLock:
        """The §12 execution band for this repo."""
        return self._band

    def path_for(self, node: Node) -> Path:
        """Where this node's runner executes: the worktree, or the repo itself."""
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
        intended = activation.metadata.intended_base_commit
        in_repo = node.isolation is IsolationMode.IN_REPO
        if in_repo and not self._band.held:
            raise PreconditionRefused(_MSG_BAND_REQUIRED)
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
        self._assert_clean(cwd, intended)

        self._write_record(activation, node, cwd, intended)
        _LOG.info(
            "wf.precondition.verified",
            activation_id=activation.activation_id,
            isolation=(node.isolation or IsolationMode.WORKTREE).value,
            commit=intended,
            reset_applied=pre_reset is not None,
            pre_reset_commit=pre_reset,
        )
        return PreconditionResult(
            intended_base_commit=intended,
            pre_attempt_commit=intended,
            reset_verified_commit=intended,
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
        """Decide what may be destroyed, requiring evidence FOR every item (§12)."""
        head = self._git.head_commit(cwd=cwd)
        head_move_required = head != intended
        if snapshot is None:
            dirty = tuple(path for path, _ in self._git.status_paths(cwd=cwd))
            return ResetPlan(resettable=dirty, head_move_required=head_move_required)

        attribution = self._attribution()
        resettable: list[str] = []
        protected: list[str] = []
        for entry in snapshot.entries:
            if self._is_runner_output(
                entry, attribution, prior, confirmation, activation_id
            ):
                resettable.append(entry.path)
            else:
                protected.append(entry.path)
        head_protected = head_move_required and not self._is_runner_lineage(
            cwd, intended, head
        )
        return ResetPlan(
            resettable=tuple(resettable),
            protected=tuple(protected),
            head_move_required=head_move_required,
            head_protected=head_protected,
            protected_head=head if head_protected else None,
        )

    @staticmethod
    def _is_runner_output(
        entry: DirtyEntry,
        attribution: RunnerAttribution | None,
        prior: DirtySnapshot | None,
        confirmation: HumanConfirmation | None,
        activation_id: str,
    ) -> bool:
        """Can the wrapper PROVE the runner left this exact content here? (§12)

        Two ways to answer yes, and every other answer is no:

        0. …unless the entry is not a regular FILE, which is refused before
           either. A directory (and a FIFO, and a symlink to one) has no blob,
           so its digest is `""` — and `""` is what every other such entry
           hashes to as well, which turns both the attribution test AND a
           tier-2 confirmation's content binding into `"" == ""`. A
           confirmation given when a nested checkout held one thing would
           release whatever it holds later, and `clean -f -d` on it takes the
           whole subtree (§12).
        1. a human released this path at this content, in THIS activation
           (tier-2, digest-bound and activation-bound);
        2. the path is TRACKED, the wrapper attributed it at a runner's exit,
           and nothing has changed it since — the recorded digest still equals
           what is on disk;
        3. …there is no third way. Absence of evidence is not attribution.

        Condition 2 is restricted to tracked paths because attribution partly
        rests on the runner's own `$WF_EFFECTS_FILE`, and the runner writes
        that file. A declaration naming a human's mid-run file — from malice or
        from a manifest built out of `git status` — would otherwise put
        never-committed content on the destroyable side, where the mistake has
        no undo at all: no blob, no commit, no reflog (probed). For a tracked
        path the content is in the object store either way.

        It carries a second guard even though `ExitObserver` already applies
        it: a path that was dirty when the attempt STARTED pre-existed that
        runner, so the runner cannot have produced it whatever else the record
        says.
        """
        if entry.kind is not EntryKind.FILE:
            return False
        if confirmation is not None and confirmation.releases(
            activation_id, entry.path, entry.digest
        ):
            return True
        if not entry.tracked:
            return False
        if prior is not None and entry.path in prior.paths:
            return False
        if attribution is None:
            return False
        return attribution.digest_of(entry.path) == entry.digest

    def _is_runner_lineage(self, cwd: Path, intended: str, head: str) -> bool:
        """Whether HEAD sits on a commit the WRAPPER pinned, descended from the base.

        The commit half of positive attribution, and it reads the `artifact/`
        namespace ALONE. A commit under `artifact/` is one `pin_artifact`
        decided was an attempt's artifact; a commit under `orphan/` or
        `prereset/` is one the wrapper only PRESERVED, which is the opposite
        claim — recovery pinning a human's commit for safekeeping must not
        thereby hand the next reset permission to destroy it (probed).
        """
        pinned = self._git.refs_under(
            namespace_prefix(self._paths.root_id, ARTIFACT_NAMESPACE), cwd=cwd
        )
        return head in pinned and self._git.is_ancestor(intended, head, cwd=cwd)

    def _attribution(self) -> RunnerAttribution | None:
        """The §12 attribution record, or `None` when there is nothing proven.

        A malformed record is treated as absent rather than raised: the effect
        is that everything becomes protected, which is the direction a
        corrupted provenance file must fail in.
        """
        try:
            return read_record(self._paths.attribution_record, RunnerAttribution)
        except WrapperDirError as exc:
            _LOG.warning("wf.attribution.unreadable", error=str(exc))
            return None

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
        except (GitCommandError, OSError) as exc:
            raise PreconditionRefused(
                _MSG_NO_SNAPSHOT.format(path=cwd, error=exc)
            ) from exc
        if pinned != commit:
            raise PreconditionRefused(
                _MSG_NO_SNAPSHOT.format(path=cwd, error=f"{ref} reads back as {pinned}")
            )
        _LOG.info(
            "wf.reset.snapshot_pinned",
            activation_id=activation_id,
            ref=ref,
            commit=commit,
        )
        return commit

    def _untracked(self, cwd: Path, resettable: tuple[str, ...]) -> tuple[str, ...]:
        """The resettable paths git will not restore for us — untracked files."""
        selected = frozenset(resettable)
        return tuple(
            path
            for path, tracked in self._git.status_paths(cwd=cwd)
            if not tracked and path in selected
        )

    def _assert_clean(self, cwd: Path, intended: str) -> None:
        """The precondition itself: HEAD at the intended commit, tree clean."""
        head = self._git.head_commit(cwd=cwd)
        dirty = self._git.status_paths(cwd=cwd)
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
        write_record(
            self._paths.workspace_record,
            WorkspaceRecord(
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
            ),
        )

    # -- artifact identity (§7.4) ----------------------------------------

    def pin_artifact(
        self,
        activation: ActivationRecord,
        node: Node,
        *,
        declared: frozenset[str] | None = None,
        quarantine: bool = False,
    ) -> PinResult:
        """Pin THIS attempt's commit under `refs/wf/…` BEFORE any bd write (§7.4).

        The result is typed rather than an `ArtifactIdentity | None`, because
        "no commit" and "a commit this attempt cannot claim" are different
        facts and §5.6 used to close on both. `PINNED` is the wrapper's
        statement that this activation produced this commit, and that statement
        also becomes the §12 authority to move HEAD off it — so a commit pinned
        on a guess is a commit a later reset destroys.

        Two attribution tests, both refusing rather than guessing:

        - **Descent** (both modes): `intended_base_commit` must be an ancestor.
          A HEAD on unrelated history is not this attempt's artifact.
        - **Declaration** (in-repo only): every path the commit range touches
          must be in `declared` — the runner's own `$WF_EFFECTS_FILE`. In-repo
          the human's checkout IS the runner's workspace, so a commit made
          during the run may be either party's, and the declaration is the only
          evidence separating them. `declared=None` means NO manifest exists,
          which in-repo is unattributable — not a licence to skip the test.
          Worktree mode never applies it: the tree is the wrapper's and nobody
          else commits in it.
        - **Authorship** (in-repo only): the commit's COMMITTER must be this
          activation's runner identity, which `RunnerChannels.env()` stamps on
          the child (§6, §7.4). Containment is a statement about PATHS and says
          nothing about who wrote them: a dead runner's manifest naming a path
          the human later committed in their own checkout made the human's
          commit this activation's artifact — and an artifact pin is the §12
          authority for the next reset to move HEAD off it, so the human's work
          was reset away (probed, Opus#21).

        `quarantine` is §5.6's need: an unattributable commit found at recovery
        must still survive, so it is pinned under `orphan/` — preserved,
        never claimed, and never lineage `_is_runner_lineage` will bless.
        """
        cwd = self.path_for(node)
        head = self._git.head_commit(cwd=cwd)
        intended = activation.metadata.intended_base_commit
        if head == intended:
            return PinResult(outcome=PinOutcome.NO_COMMIT)
        in_repo = node.isolation is IsolationMode.IN_REPO
        reason = self._unattributed(
            cwd,
            intended,
            head,
            declared,
            activation.activation_id,
            in_repo=in_repo,
        )
        if reason is not None:
            return self._unclaimed(activation, cwd, head, reason, quarantine)
        ref = activation_ref(self._paths.root_id, activation.activation_id)
        self._git.update_ref(ref, head, cwd=cwd)
        _LOG.info(
            "wf.artifact.pinned",
            activation_id=activation.activation_id,
            ref=ref,
            commit=head,
        )
        return PinResult(
            outcome=PinOutcome.PINNED,
            identity=ArtifactIdentity(
                commit_oid=head, tree_oid=self._git.tree_oid(head, cwd=cwd)
            ),
            commit=head,
            ref=ref,
        )

    def _unclaimed(
        self,
        activation: ActivationRecord,
        cwd: Path,
        head: str,
        reason: str,
        quarantine: bool,
    ) -> PinResult:
        """Handle a commit this attempt may not claim: quarantine it, or refuse.

        Quarantining is not a weaker pin — it is the opposite statement. The
        commit is preserved so no reset can orphan it and no gc can collect it,
        while `identity` stays empty so nothing downstream can record it as
        this activation's artifact (§7.4 honest naming).
        """
        _LOG.error(
            "wf.artifact.unattributed",
            activation_id=activation.activation_id,
            commit=head,
            reason=reason,
            quarantined=quarantine,
        )
        if not quarantine:
            return PinResult(outcome=PinOutcome.REFUSED, commit=head, reason=reason)
        ref = namespaced_ref(
            self._paths.root_id, ORPHAN_NAMESPACE, activation.activation_id
        )
        self._git.update_ref(ref, head, cwd=cwd)
        _LOG.warning(
            "wf.artifact.quarantined",
            activation_id=activation.activation_id,
            ref=ref,
            commit=head,
        )
        return PinResult(
            outcome=PinOutcome.QUARANTINED, commit=head, ref=ref, reason=reason
        )

    def _unattributed(
        self,
        cwd: Path,
        intended: str,
        head: str,
        declared: frozenset[str] | None,
        activation_id: str,
        *,
        in_repo: bool,
    ) -> str | None:
        """Why `head` is not this attempt's artifact, or `None` when it is."""
        if not self._git.is_ancestor(intended, head, cwd=cwd):
            return _REASON_NOT_DESCENDANT.format(intended=intended)
        if not in_repo:
            return None
        if declared is None:
            return _REASON_NO_MANIFEST
        touched = self._git.diff_names(intended, head, cwd=cwd)
        undeclared = tuple(sorted(set(touched) - declared))
        if undeclared:
            return _REASON_UNDECLARED.format(paths=", ".join(undeclared))
        wanted = runner_committer_email(activation_id)
        found = self._git.committer_email(head, cwd=cwd)
        if found != wanted:
            return _REASON_NOT_OUR_COMMITTER.format(found=found, wanted=wanted)
        return None

    def record_attribution(
        self,
        activation: ActivationRecord,
        node: Node,
        *,
        declared: frozenset[str],
    ) -> RunnerAttribution | None:
        """Record what this runner provably left dirty, for a later reset (§12).

        Called once, from `ExitObserver`, while the dead runner's activation
        still owns the §12 band — so `git status` here is the wrapper's own
        observation of what that runner left, not a guess made later.

        Entries survive three filters: the wrapper saw the path dirty, the
        runner DECLARED it, and it was not already dirty when this attempt
        started. Prior entries are carried forward untouched — a file the
        implementer left is still its work after a reviewer has run — because
        the reset-time digest comparison is what expires them: anything that
        edits a path breaks its match and returns it to protected.

        Untracked paths are recorded like any other — this file is an
        OBSERVATION, and a wrapper that edited its own observations to match
        its policy would be worth nothing. `_is_runner_output` is where the
        policy lives, and it never resets an untracked path on this evidence.

        Worktree mode records nothing: that tree has no other author.
        """
        if node.isolation is not IsolationMode.IN_REPO:
            return None
        cwd = self.path_for(node)
        pre_attempt = decode_dirty_state(activation.metadata.pre_attempt_dirty_state)
        if pre_attempt is None:
            # Unknown pre-attempt state cannot answer "was it already dirty",
            # so nothing is attributable — and the on-disk record is REPLACED
            # with an empty one, or an earlier attempt's entries would stay
            # live and authorize a reset this attempt cannot vouch for.
            _LOG.warning(
                "wf.attribution.no_pre_attempt_state",
                activation_id=activation.activation_id,
            )
            entries: tuple[DirtyEntry, ...] = ()
            carried: tuple[DirtyEntry, ...] = ()
        else:
            entries = tuple(
                self._entry(cwd, path, tracked)
                for path, tracked in self._git.status_paths(cwd=cwd)
                if path in declared and path not in pre_attempt.paths
            )
            carried = self._carry_forward(entries)
        record = RunnerAttribution(
            activation_id=activation.activation_id,
            observed_at=to_iso(self._clock.now()),
            head_commit=self._git.head_commit(cwd=cwd),
            entries=carried,
        )
        write_record(self._paths.attribution_record, record)
        _LOG.info(
            "wf.attribution.recorded",
            activation_id=activation.activation_id,
            paths=[entry.path for entry in entries],
        )
        return record

    def _carry_forward(self, entries: tuple[DirtyEntry, ...]) -> tuple[DirtyEntry, ...]:
        """This attempt's entries plus every earlier one it does not supersede."""
        existing = self._attribution()
        if existing is None:
            return entries
        fresh = {entry.path for entry in entries}
        return entries + tuple(
            entry for entry in existing.entries if entry.path not in fresh
        )

    def remove_worktree(self) -> None:
        """Remove the instance worktree at terminal (§5.4). Never the repo."""
        worktree = self._paths.worktree
        if worktree.exists():
            self._git.worktree_remove(worktree, cwd=self._paths.config.repo_root)
