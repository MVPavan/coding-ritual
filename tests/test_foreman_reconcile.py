"""C2b reconciliation contracts over a real git repository."""

from pathlib import Path
from typing import NoReturn

import pytest

from tests._bdio import entry_request
from tests._foreman import ForemanLab
from workflow_interpreter.foreman.reconcile import reconcile
from workflow_interpreter.supervisor.errors import GitCommandError
from workflow_interpreter.supervisor.gitcmd import GitSubcommand


def test_reconcile_requires_the_instance_branch(tmp_path: Path) -> None:
    lab = ForemanLab(tmp_path)
    root = lab.instantiate()
    branch = "refs/heads/wf/" + root.root_id
    lab.git.run(GitSubcommand.UPDATE_REF, "-d", branch, cwd=lab.repo)
    result = reconcile(root, (), lab.git, repo_root=lab.repo)
    assert result.stalled == "instance branch missing"


def test_reconcile_requires_the_recorded_instance_base_commit(tmp_path: Path) -> None:
    lab = ForemanLab(tmp_path)
    root = lab.instantiate()
    missing_base = root.model_copy(
        update={
            "metadata": root.metadata.model_copy(
                update={"instance_base_commit": "f" * 40}
            )
        }
    )

    result = reconcile(missing_base, (), lab.git, repo_root=lab.repo)

    assert result.stalled == "instance base commit is missing"


def test_reconcile_requires_every_intended_commit(tmp_path: Path) -> None:
    lab = ForemanLab(tmp_path)
    root = lab.instantiate()
    activation = (
        lab.wiring().store.mint_activation(root.root_id, entry_request()).activation
    )
    broken = activation.model_copy(
        update={
            "metadata": activation.metadata.model_copy(
                update={"intended_base_commit": "f" * 40}
            )
        }
    )
    result = reconcile(root, (broken,), lab.git, repo_root=lab.repo)
    assert result.stalled == "missing_commit intended_base_commit " + "f" * 40


def test_reconcile_propagates_a_git_transport_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    lab = ForemanLab(tmp_path)
    root = lab.instantiate()

    def refuse(*_args: object, **_kwargs: object) -> NoReturn:
        raise GitCommandError("object database unreadable")

    monkeypatch.setattr(lab.git, "ref_target", refuse)

    with pytest.raises(GitCommandError, match="object database unreadable"):
        reconcile(root, (), lab.git, repo_root=lab.repo)
