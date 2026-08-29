"""Artifact claiming and instance-ref ownership for the supervisor.

An artifact pin says that a particular activation produced a commit.  That is
also the authority a later in-repo reset needs before it can move HEAD away
from that commit, so every gap in the descent, declaration, or authorship
evidence refuses the claim.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Final

import structlog

from workflow_interpreter.bdio import ActivationRecord, ArtifactIdentity
from workflow_interpreter.schema.models import IsolationMode, Node
from workflow_interpreter.supervisor.channels import runner_committer_email
from workflow_interpreter.supervisor.gitio import Git
from workflow_interpreter.supervisor.models import PinOutcome, PinResult
from workflow_interpreter.supervisor.paths import WrapperPaths

_LOG: Final[structlog.stdlib.BoundLogger] = structlog.get_logger(__name__)

BRANCH_TEMPLATE: Final[str] = "wf/{root_id}"
INSTANCE_BRANCH_REF: Final[str] = "refs/heads/" + BRANCH_TEMPLATE

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


def activation_ref(root_id: str, activation_id: str) -> str:
    """Return the §7.4 artifact pin for an activation."""
    return namespaced_ref(root_id, ARTIFACT_NAMESPACE, activation_id)


def namespaced_ref(root_id: str, namespace: str, activation_id: str) -> str:
    """Return one instance ref in one of the supervisor namespaces."""
    return REF_TEMPLATE.format(
        root_id=root_id, namespace=namespace, activation_id=activation_id
    )


def namespace_prefix(root_id: str, namespace: str) -> str:
    """Return the ref prefix that contains one namespace's pins."""
    return namespaced_ref(root_id, namespace, "")


class ArtifactManager:
    """Claims and preserves commits without coupling to reset planning."""

    def __init__(
        self,
        paths: WrapperPaths,
        git: Git,
        path_for: Callable[[Node], Path],
    ) -> None:
        """Bind this manager to one instance's paths and git transport."""
        self._paths = paths
        self._git = git
        self._path_for = path_for

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
        cwd = self._path_for(node)
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

    def is_runner_lineage(self, cwd: Path, intended: str, head: str) -> bool:
        """Whether HEAD is a wrapper-pinned descendant of the intended base."""
        pinned = self._git.refs_under(
            namespace_prefix(self._paths.root_id, ARTIFACT_NAMESPACE), cwd=cwd
        )
        return head in pinned and self._git.is_ancestor(intended, head, cwd=cwd)

    def _unclaimed(
        self,
        activation: ActivationRecord,
        cwd: Path,
        head: str,
        reason: str,
        quarantine: bool,
    ) -> PinResult:
        """Refuse an unclaimable commit, preserving it when recovering."""
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
        """Return why a commit cannot be this activation's artifact."""
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
