"""Observed checks, never labels, authorize the bridge artifact."""

import sys
from pathlib import Path

import pytest

from tests._supervisor import head_of, make_repo
from workflow_interpreter.bridge.landing import DetachedRepositoryGate
from workflow_interpreter.bridge.verification import CheckCommand, VerificationPolicy
from workflow_interpreter.supervisor import Git
from workflow_interpreter.supervisor.config import SupervisorConfig
from workflow_interpreter.supervisor.paths import WrapperPaths


def gate(tmp_path: Path, code: str, timeout: float = 3):
    repo = make_repo(tmp_path)
    config = SupervisorConfig(
        repo_root=repo, wrapper_root=tmp_path / "wrapper", host="test"
    )
    git = Git(config)
    policy = VerificationPolicy.pin(
        (
            CheckCommand(
                name="proof", argv=(sys.executable, "-c", code), timeout_s=timeout
            ),
        ),
        repo,
    )
    return (
        DetachedRepositoryGate(
            git, WrapperPaths(config, "root"), policy, lambda _: None
        ),
        head_of(repo),
        git,
        repo,
    )


def test_observes_exit_status_and_policy(tmp_path: Path) -> None:
    verifier, oid, git, repo = gate(tmp_path, "raise SystemExit(7)")
    result = verifier.verify(oid, git.tree_oid(oid, cwd=repo))
    assert not result.green
    assert result.results[0].exit_code == 7
    assert result.policy_digest


def test_empty_policy_refused(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="nonempty"):
        VerificationPolicy.pin((), tmp_path)


@pytest.mark.parametrize(
    "code",
    ["import time; time.sleep(10)", "open('src/feature.py', 'w').write('changed')"],
)
def test_timeout_and_source_mutation_refuse(tmp_path: Path, code: str) -> None:
    verifier, oid, git, repo = gate(tmp_path, code, 0.05)
    result = verifier.verify(oid, git.tree_oid(oid, cwd=repo))
    assert not result.green


def test_controlled_environment(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("P1_AMBIENT_SECRET", "must-not-leak")
    verifier, oid, git, repo = gate(
        tmp_path, "import os; assert 'P1_AMBIENT_SECRET' not in os.environ"
    )
    result = verifier.verify(oid, git.tree_oid(oid, cwd=repo))
    assert result.green
    assert result.results[0].exit_code == 0


def test_policy_rejects_missing_duplicate_failed_and_wrong_command_results(
    tmp_path: Path,
) -> None:
    verifier, oid, git, repo = gate(tmp_path, "pass")
    result = verifier.verify(oid, git.tree_oid(oid, cwd=repo))
    policy = verifier._checks
    observed = result.results[0]
    assert policy.matches(result.results)
    assert not policy.matches(())
    assert not policy.matches((observed, observed))
    assert not policy.matches((observed.model_copy(update={"exit_code": 1}),))
    assert not policy.matches((observed.model_copy(update={"name": "other"}),))


def test_admission_requires_policy_before_writes(
    fake_bd, fake_client, tmp_path: Path
) -> None:
    from tests.test_phase_bridge import (
        EPIC_ID,
        STAGE_ID,
        TARGET_REF,
        _Roots,
        _stage_row,
    )
    from workflow_interpreter.bridge import PhaseAdapter, PhaseAdmission

    repo = make_repo(tmp_path)
    base = head_of(repo)
    fake_bd.rows[STAGE_ID] = _stage_row()
    admission = PhaseAdmission(
        PhaseAdapter(fake_client), _Roots(fake_client, repo, base), lambda: base
    )
    with pytest.raises(ValueError, match="policy"):
        admission.admit(EPIC_ID, STAGE_ID, TARGET_REF, base)
    assert "phase_bridge" not in fake_bd.rows[STAGE_ID]["metadata"]


def test_duplicate_policy_names_and_missing_program_refuse(tmp_path: Path) -> None:
    command = CheckCommand(name="same", argv=(sys.executable, "-c", "pass"))
    with pytest.raises(ValueError, match="duplicate"):
        VerificationPolicy.pin((command, command), tmp_path)
    with pytest.raises(ValueError, match="missing"):
        VerificationPolicy.pin(
            (CheckCommand(name="missing", argv=("not-present",)),), tmp_path
        )


def test_changed_executable_refuses_without_running(tmp_path: Path) -> None:
    repo = make_repo(tmp_path)
    program = tmp_path / "check"
    program.write_text("#!/bin/sh\nexit 0\n")
    program.chmod(0o755)
    policy = VerificationPolicy.pin(
        (CheckCommand(name="proof", argv=(str(program),)),), repo
    )
    program.write_text("#!/bin/sh\ntouch ran\n")
    config = SupervisorConfig(
        repo_root=repo, wrapper_root=tmp_path / "wrapper", host="test"
    )
    git = Git(config)
    oid = head_of(repo)
    result = DetachedRepositoryGate(
        git, WrapperPaths(config, "root"), policy, lambda _: None
    ).verify(oid, git.tree_oid(oid, cwd=repo))
    assert not result.green
    assert result.results[0].exit_code == 126


def test_label_callback_is_not_a_repository_verification_policy(tmp_path: Path) -> None:
    repo = make_repo(tmp_path)
    config = SupervisorConfig(
        repo_root=repo, wrapper_root=tmp_path / "wrapper", host="test"
    )
    with pytest.raises(TypeError, match="policy"):
        DetachedRepositoryGate(
            Git(config),
            WrapperPaths(config, "root"),
            lambda *_: ("green",),
            lambda _: None,
        )
