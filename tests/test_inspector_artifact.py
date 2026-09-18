"""§7.4 artifact identity: which commit is THIS attempt's, and on what evidence.

Split out of the §5.4/§12 precondition family, which is the other half of what
`Workspace` does and had grown past the file cap alongside it. The seam is the
question each half answers: that one asks whether a working TREE may be reset,
this one asks whether a COMMIT may be claimed — and a claimed commit is also the
§12 authority for the next reset to move HEAD off it, which is why the evidence
bar here is descent AND declaration AND authorship, with every gap refusing.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tests._supervisor import commit_all, make_git, runner_commit
from tests._workspace import (
    CLEAN,
    HUMAN_COMMITTED,
    HUMAN_TEXT,
    RUNNER_FILE,
    STRANGER_ACTIVATION,
    Fixture,
    in_repo,
    rebased,
    worktree,
)
from workflow_interpreter.supervisor import (
    DirtyTreeRefused,
    PinOutcome,
    activation_ref,
    channels_for,
)
from workflow_interpreter.supervisor.channels import (
    COMMITTER_NAME,
    ENV_GIT_COMMITTER_EMAIL,
    ENV_GIT_COMMITTER_NAME,
    runner_committer_email,
)

__all__ = ["in_repo", "worktree"]


def test_pin_artifact_records_identity_and_ref(worktree: Fixture) -> None:
    """§7.4: the wrapper pins `refs/wf/<root>/artifact/<activation>` before bd."""
    worktree.workspace.prepare(worktree.activation, worktree.node)
    tree = worktree.paths.worktree
    (tree / RUNNER_FILE).write_text("done\n", encoding="utf-8")
    commit = commit_all(tree, "the attempt")

    pin = worktree.workspace.pin_artifact(worktree.activation, worktree.node)

    assert pin.outcome is PinOutcome.PINNED
    assert pin.identity is not None
    assert pin.identity.commit_oid == commit
    ref = activation_ref(worktree.root.root_id, worktree.activation.activation_id)
    assert pin.ref == ref
    assert make_git(worktree.config).ref_target(ref, cwd=worktree.repo) == commit


def test_pin_artifact_says_no_commit_rather_than_none(worktree: Fixture) -> None:
    """M15/Sol#9: "nothing to pin" and "cannot claim it" are different answers.

    Both used to be `None`, and §5.6 closed on both — so an unattributable
    ahead commit was treated exactly like an attempt that produced nothing.
    """
    worktree.workspace.prepare(worktree.activation, worktree.node)

    pin = worktree.workspace.pin_artifact(worktree.activation, worktree.node)

    assert pin.outcome is PinOutcome.NO_COMMIT
    assert pin.identity is None
    assert pin.settled is True


def test_in_repo_does_not_pin_a_commit_the_runner_did_not_declare(
    in_repo: Fixture,
) -> None:
    """M15: in-repo, a commit becomes THIS attempt's artifact only on evidence."""
    in_repo.workspace.prepare(in_repo.activation, in_repo.node)
    (in_repo.repo / HUMAN_COMMITTED).parent.mkdir(parents=True, exist_ok=True)
    (in_repo.repo / HUMAN_COMMITTED).write_text(HUMAN_TEXT, encoding="utf-8")
    commit_all(in_repo.repo, "a chapter the human wrote")

    pin = in_repo.workspace.pin_artifact(
        in_repo.activation, in_repo.node, declared=frozenset({RUNNER_FILE})
    )

    ref = activation_ref(in_repo.root.root_id, in_repo.activation.activation_id)
    assert pin.outcome is PinOutcome.REFUSED
    assert pin.identity is None
    assert pin.settled is False
    assert make_git(in_repo.config).ref_target(ref, cwd=in_repo.repo) is None


def test_in_repo_with_no_effects_manifest_cannot_attribute_any_commit(
    in_repo: Fixture,
) -> None:
    """M15: no manifest is no evidence — and evidence is what pinning requires.

    `declared=None` used to mean "skip the declaration test", which is the
    worktree convention. In-repo it has to mean the opposite: with nothing
    separating the runner's commit from the human's, there is no attribution
    to be made at all.
    """
    in_repo.workspace.prepare(in_repo.activation, in_repo.node)
    (in_repo.repo / RUNNER_FILE).write_text("runner output\n", encoding="utf-8")
    commit_all(in_repo.repo, "a commit made during the run")

    pin = in_repo.workspace.pin_artifact(
        in_repo.activation, in_repo.node, declared=None
    )

    assert pin.outcome is PinOutcome.REFUSED
    assert pin.reason is not None
    assert "$WF_EFFECTS_FILE" in pin.reason


def test_pin_artifact_refuses_a_commit_that_does_not_descend_from_the_base(
    worktree: Fixture,
) -> None:
    """M15: honest naming — an unrelated commit is not this attempt's artifact."""
    worktree.workspace.prepare(worktree.activation, worktree.node)
    (worktree.paths.worktree / RUNNER_FILE).write_text("work\n", encoding="utf-8")
    commit_all(worktree.paths.worktree, "the attempt")
    (worktree.repo / HUMAN_COMMITTED).parent.mkdir(parents=True, exist_ok=True)
    (worktree.repo / HUMAN_COMMITTED).write_text(HUMAN_TEXT, encoding="utf-8")
    sibling = commit_all(worktree.repo, "an unrelated commit on the main branch")
    elsewhere = rebased(worktree, sibling)

    pin = worktree.workspace.pin_artifact(elsewhere, worktree.node)

    assert pin.outcome is PinOutcome.REFUSED
    assert pin.identity is None


def test_a_quarantined_commit_is_preserved_without_becoming_lineage(
    in_repo: Fixture,
) -> None:
    """B3: preserving a commit and CLAIMING it must be different operations.

    A commit under `orphan/` has a ref, so no reset orphans it and no gc
    collects it — and `_is_runner_lineage` still refuses to move HEAD off it,
    because the ref says "somebody's work, unattributed", not "our artifact".
    """
    in_repo.workspace.prepare(in_repo.activation, in_repo.node)
    (in_repo.repo / HUMAN_COMMITTED).parent.mkdir(parents=True, exist_ok=True)
    (in_repo.repo / HUMAN_COMMITTED).write_text(HUMAN_TEXT, encoding="utf-8")
    human = commit_all(in_repo.repo, "a chapter the human wrote")

    pin = in_repo.workspace.pin_artifact(
        in_repo.activation, in_repo.node, declared=None, quarantine=True
    )

    assert pin.outcome is PinOutcome.QUARANTINED
    assert pin.identity is None
    assert pin.settled is True
    assert make_git(in_repo.config).ref_target(pin.ref or "", cwd=in_repo.repo) == human
    with pytest.raises(DirtyTreeRefused) as refusal:
        in_repo.workspace.prepare(
            in_repo.activation, in_repo.node, prior_dirty_state=CLEAN
        )
    assert refusal.value.protected_head == human
    assert (in_repo.repo / HUMAN_COMMITTED).read_text(encoding="utf-8") == HUMAN_TEXT


def test_a_commit_the_human_made_is_not_this_attempts_artifact(
    in_repo: Fixture,
) -> None:
    """Opus#21: path containment says nothing about WHO wrote the paths.

    A dead runner's `$WF_EFFECTS_FILE` naming a path the human then commits in
    their own checkout satisfied descent AND declaration, so the human's commit
    was pinned as this activation's artifact — and an `artifact/` pin is the §12
    authority for the next reset to move HEAD off it, so the human's work was
    reset away with nothing referencing it (probed). The commit's COMMITTER must
    now be this activation's runner identity as well.
    """
    in_repo.workspace.prepare(in_repo.activation, in_repo.node)
    (in_repo.repo / RUNNER_FILE).write_text("the human's own work\n", encoding="utf-8")
    commit_all(in_repo.repo, "the human commits, in their own checkout")

    pin = in_repo.workspace.pin_artifact(
        in_repo.activation, in_repo.node, declared=frozenset({RUNNER_FILE})
    )

    assert pin.outcome is PinOutcome.REFUSED
    assert pin.identity is None
    assert pin.reason is not None
    assert "runner identity" in pin.reason


def test_a_commit_made_under_the_runner_identity_is_attributed(
    in_repo: Fixture,
) -> None:
    """The other side: the identity the wrapper stamps is what makes it ours.

    `RunnerChannels.env()` puts `GIT_COMMITTER_*` on the child, so a commit the
    runner really made carries it and every §7.4 test passes together.
    """
    in_repo.workspace.prepare(in_repo.activation, in_repo.node)
    (in_repo.repo / RUNNER_FILE).write_text("runner output\n", encoding="utf-8")
    commit = runner_commit(
        in_repo.repo, "the attempt", in_repo.activation.activation_id
    )

    pin = in_repo.workspace.pin_artifact(
        in_repo.activation, in_repo.node, declared=frozenset({RUNNER_FILE})
    )

    assert pin.outcome is PinOutcome.PINNED
    assert pin.identity is not None
    assert pin.identity.commit_oid == commit


def test_another_activations_runner_identity_does_not_attribute_here(
    in_repo: Fixture,
) -> None:
    """The identity carries the ACTIVATION id, so it cannot be reused sideways.

    Two attempts of one instance run in the same checkout one after the other;
    a commit the PREVIOUS attempt left is that attempt's artifact and not this
    one's, and the address is what says so.
    """
    in_repo.workspace.prepare(in_repo.activation, in_repo.node)
    (in_repo.repo / RUNNER_FILE).write_text("an earlier attempt\n", encoding="utf-8")
    runner_commit(in_repo.repo, "the earlier attempt", STRANGER_ACTIVATION)

    pin = in_repo.workspace.pin_artifact(
        in_repo.activation, in_repo.node, declared=frozenset({RUNNER_FILE})
    )

    assert pin.outcome is PinOutcome.REFUSED


def test_the_worktree_mode_pin_asks_nothing_about_authorship(
    worktree: Fixture,
) -> None:
    """§7.4: the worktree is the wrapper's, and nobody else commits in it.

    Both in-repo tests — declaration and authorship — exist because the human's
    checkout has two authors. A per-instance worktree has one, so applying them
    there would refuse every artifact the wrapper ever produced.
    """
    worktree.workspace.prepare(worktree.activation, worktree.node)
    (worktree.paths.worktree / RUNNER_FILE).write_text("out\n", encoding="utf-8")
    commit = commit_all(worktree.paths.worktree, "the attempt")

    pin = worktree.workspace.pin_artifact(worktree.activation, worktree.node)

    assert pin.outcome is PinOutcome.PINNED
    assert pin.identity is not None
    assert pin.identity.commit_oid == commit


def test_the_runner_channels_stamp_this_activations_committer_identity() -> None:
    """§6: the env the child gets is where the §7.4 identity comes from.

    Producer and reader in one assertion — `Workspace._unattributed` looks up
    the same address through the same function, so a change to either side that
    did not change both would fail here rather than silently stop attributing
    anything.
    """
    channels = channels_for(Path("/wf/act"), Path("/wf/act/log.jsonl"), "wf-42")

    env = channels.env()

    assert env[ENV_GIT_COMMITTER_NAME] == COMMITTER_NAME
    assert env[ENV_GIT_COMMITTER_EMAIL] == runner_committer_email("wf-42")
    assert "wf-42" in env[ENV_GIT_COMMITTER_EMAIL]
    # No activation id, no identity — an unattributable commit, never a
    # misattributed one.
    assert (
        ENV_GIT_COMMITTER_EMAIL
        not in channels_for(Path("/wf/act"), Path("/wf/act/log.jsonl")).env()
    )
