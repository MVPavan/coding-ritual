"""A tiny, self-contained uv project the real check scripts can be run against.

The scripts under `scripts/` are executed for real (`-m proc`), so they need a
tree that answers all five of their commands: a `pyproject.toml` with `ruff`,
`mypy` and `pytest`, a `workflow_interpreter/` package for `mypy` and one
trivial test per selected marker — `pytest` exits 5 ("no tests collected"),
which is a gate failure, when a marker selects nothing.

The uv environment is shared across the copies through
`UV_PROJECT_ENVIRONMENT`, so the fixture is resolved once per test session
rather than once per case.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path
from typing import Final

GIT_TIMEOUT_S: Final[float] = 60.0
SCRIPT_TIMEOUT_S: Final[float] = 900.0

REPO_ROOT: Final[Path] = Path(__file__).resolve().parents[2]
VERIFY_FEATURE: Final[Path] = REPO_ROOT / "scripts" / "verify-feature.sh"
REVIEW_CHECKS: Final[Path] = REPO_ROOT / "scripts" / "review-checks.sh"

ACCEPTANCE_FILE: Final[str] = "tests/acceptance/x.py"
LINT_BROKEN_FILE: Final[str] = "workflow_interpreter/broken.py"
LINT_BROKEN_BODY: Final[str] = '"""Unused import: ruff F401."""\n\nimport os\n'

PYPROJECT: Final[str] = """\
[project]
name = "check-script-fixture"
version = "0.1.0"
requires-python = ">=3.13"
dependencies = ["mypy>=2.3.1", "pytest>=9.1.1", "ruff>=0.16.2"]

[tool.pytest.ini_options]
pythonpath = ["."]
testpaths = ["tests"]
markers = [
    "bd: unused here; declared so the gate's marker expression selects nothing",
    "proc: the fixture's own proc-marked test",
    "live: unused here",
]
"""

_PACKAGE_INIT: Final[str] = '"""The fixture package `mypy --strict` is run over."""\n'
_FIXTURE_TEST: Final[str] = '''\
"""One test per marker the gate selects."""

from __future__ import annotations

import pytest


def test_the_fixture_collects() -> None:
    """`-m "not bd and not live"` must select something."""
    assert True


@pytest.mark.proc
def test_the_fixture_has_a_proc_case() -> None:
    """`-m proc` must select something."""
    assert True
'''


def git(repo: Path, *args: str) -> str:
    """Run git in the fixture repo with an explicit timeout."""
    completed = subprocess.run(
        ["git", *args],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
        timeout=GIT_TIMEOUT_S,
    )
    return completed.stdout.strip()


def build_project(root: Path) -> Path:
    """Create the pristine fixture project as a git repo with one commit."""
    repo = root / "fixture-project"
    (repo / "workflow_interpreter").mkdir(parents=True)
    (repo / "tests").mkdir()
    (repo / "pyproject.toml").write_text(PYPROJECT, encoding="utf-8")
    (repo / "workflow_interpreter" / "__init__.py").write_text(
        _PACKAGE_INIT, encoding="utf-8"
    )
    (repo / "tests" / "test_fixture.py").write_text(_FIXTURE_TEST, encoding="utf-8")
    git(repo, "init", "--quiet", "--initial-branch=main")
    git(repo, "config", "user.email", "wf@test")
    git(repo, "config", "user.name", "wf test")
    git(repo, "config", "commit.gpgsign", "false")
    git(repo, "add", "-A")
    git(repo, "commit", "--quiet", "-m", "initial")
    return repo


def copy_project(pristine: Path, destination: Path) -> Path:
    """A private copy of the fixture project, git history included."""
    shutil.copytree(pristine, destination)
    return destination


def run_script(
    script: Path, repo: Path, environment: Path
) -> subprocess.CompletedProcess[str]:
    """Run a check script the way §7.3 does: cwd only, no arguments."""
    return subprocess.run(
        [str(script)],
        cwd=repo,
        capture_output=True,
        text=True,
        check=False,
        timeout=SCRIPT_TIMEOUT_S,
        env={**os.environ, "UV_PROJECT_ENVIRONMENT": str(environment)},
    )
