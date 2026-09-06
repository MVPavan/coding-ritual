"""A tiny, self-contained uv project the real check scripts can be run against.

The scripts under `scripts/` are executed for real (`-m proc`), so they need a
tree that answers all five of their commands: a `pyproject.toml` with `ruff`,
`mypy` and `pytest`, a `workflow_interpreter/` package for `mypy` and one
trivial test per selected marker — `pytest` exits 5 ("no tests collected"),
which is a gate failure, when a marker selects nothing.

`scripts/checks/` needs two more things of the same tree: an acceptance suite
with one honest test, and a copy of `mutate.py` at the path `mutate.sh` runs it
from — in a real checkout both are committed files, and a fixture that faked
either would be testing something the wrapper never runs.

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
CHECKS_DIR: Final[Path] = REPO_ROOT / "scripts" / "checks"
TESTS_PARSE: Final[Path] = CHECKS_DIR / "tests-parse.sh"
ASSERTION_STRENGTH: Final[Path] = CHECKS_DIR / "assertion-strength.sh"
TESTS_UNTOUCHED: Final[Path] = CHECKS_DIR / "tests-untouched.sh"
MUTATE: Final[Path] = CHECKS_DIR / "mutate.sh"
MUTATE_PY: Final[str] = "scripts/checks/mutate.py"
"""`mutate.sh` runs its site picker from the CHECKOUT, so the fixture repo
carries the same file at the same path the real tree does."""

BASE_COMMIT_ENV: Final[str] = "WF_BASE_COMMIT"
"""What the wrapper injects for a diff-based check (phase 7, D5)."""

ACCEPTANCE_DIR: Final[str] = "tests/acceptance"
ACCEPTANCE_FILE: Final[str] = "tests/acceptance/x.py"
STRONG_TEST_FILE: Final[str] = "tests/acceptance/test_accepted.py"
WEAK_TEST_FILE: Final[str] = "tests/acceptance/test_weak.py"
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
    "nested_sandbox: unused here; declared because the gate's `-m` names it",
]
"""

_PACKAGE_INIT: Final[str] = '"""The fixture package `mypy --strict` is run over."""\n'

STRONG_TEST_BODY: Final[str] = '''\
"""One acceptance test with a real assertion."""

from __future__ import annotations


def test_the_feature_is_accepted() -> None:
    """A test that can fail."""
    assert 1 + 1 == 2
'''

WEAK_TEST_BODY: Final[str] = '''\
"""An acceptance test that cannot fail — what `assertion-strength.sh` names."""

from __future__ import annotations


def test_nothing_is_asserted() -> None:
    """No assert and no `pytest.raises`: green whatever the code does."""
    value = 1 + 1
    print(value)
'''
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
    (repo / ACCEPTANCE_DIR).mkdir(parents=True)
    (repo / STRONG_TEST_FILE).write_text(STRONG_TEST_BODY, encoding="utf-8")
    (repo / MUTATE_PY).parent.mkdir(parents=True)
    shutil.copy(REPO_ROOT / MUTATE_PY, repo / MUTATE_PY)
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
    script: Path,
    repo: Path,
    environment: Path,
    *,
    base_commit: str | None = None,
) -> subprocess.CompletedProcess[str]:
    """Run a check script the way §7.3 does: cwd only, no arguments.

    `base_commit` is handed over as `BASE_COMMIT_ENV`, exactly as `verify.py`
    hands it over; `None` REMOVES it from the copied environment rather than
    merely not adding it. These very tests run under the wrapper (a §7.3 check
    runs `-m proc`), so `WF_BASE_COMMIT` is ambient there, and an "unset" case
    that inherited it would grade the opposite of what it claims.
    """
    environ = dict(os.environ)
    environ["UV_PROJECT_ENVIRONMENT"] = str(environment)
    if base_commit is None:
        environ.pop(BASE_COMMIT_ENV, None)
    else:
        environ[BASE_COMMIT_ENV] = base_commit
    return subprocess.run(
        [str(script)],
        cwd=repo,
        capture_output=True,
        text=True,
        check=False,
        timeout=SCRIPT_TIMEOUT_S,
        env=environ,
    )


def head_commit(repo: Path) -> str:
    """The fixture repo's current HEAD — what a round's `WF_BASE_COMMIT` is."""
    return git(repo, "rev-parse", "HEAD")


def commit_file(repo: Path, relative: str, body: str, message: str) -> str:
    """Write one file, commit it, and return the new HEAD."""
    path = repo / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")
    git(repo, "add", "-A")
    git(repo, "commit", "--quiet", "-m", message)
    return head_commit(repo)
