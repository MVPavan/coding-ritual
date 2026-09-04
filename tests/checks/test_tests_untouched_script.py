"""`scripts/checks/tests-untouched.sh`: the round did not edit its own yardstick.

Run exactly as the wrapper runs it (`supervisor/verify.py`): cwd is the tree
under test, no arguments, and `WF_BASE_COMMIT` in the environment.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.checks._project import (
    ACCEPTANCE_DIR,
    BASE_COMMIT_ENV,
    TESTS_UNTOUCHED,
    WEAK_TEST_BODY,
    WEAK_TEST_FILE,
    commit_file,
    head_commit,
    run_script,
)

pytestmark = pytest.mark.proc

_FEATURE_FILE = "workflow_interpreter/feature.py"
_FEATURE_BODY = '"""The round\'s product change."""\n\nVALUE = 1\n'


def test_tests_untouched_passes_when_the_round_only_changed_product_code(
    project: Path, uv_environment: Path
) -> None:
    """A round that leaves `tests/acceptance/` alone passes in one line."""
    base = head_commit(project)
    commit_file(project, _FEATURE_FILE, _FEATURE_BODY, "a feature")

    completed = run_script(TESTS_UNTOUCHED, project, uv_environment, base_commit=base)

    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert completed.stdout.splitlines() == [
        f"PASS tests-untouched: {ACCEPTANCE_DIR} unchanged since {base}"
    ]


def test_tests_untouched_names_the_acceptance_file_the_round_moved(
    project: Path, uv_environment: Path
) -> None:
    """A round that edits its yardstick is named, file by file.

    The whole ROUND is compared, not the last commit: the product change lands
    first and the test edit second, which a `HEAD`-only check would miss.
    """
    base = head_commit(project)
    commit_file(project, _FEATURE_FILE, _FEATURE_BODY, "a feature")
    commit_file(project, WEAK_TEST_FILE, WEAK_TEST_BODY, "and then the tests")

    completed = run_script(TESTS_UNTOUCHED, project, uv_environment, base_commit=base)

    assert completed.returncode != 0
    lines = completed.stdout.splitlines()
    assert lines[0] == (
        f"FAIL tests-untouched: 1 file(s) changed under {ACCEPTANCE_DIR}"
    )
    assert lines[1] == WEAK_TEST_FILE
    assert len(lines) <= 8


def test_tests_untouched_refuses_to_pass_when_the_base_commit_is_unset(
    project: Path, uv_environment: Path
) -> None:
    """Unset is a FAILURE naming the variable, never a vacuously empty diff."""
    commit_file(project, WEAK_TEST_FILE, WEAK_TEST_BODY, "edit the tests")

    completed = run_script(TESTS_UNTOUCHED, project, uv_environment)

    assert completed.returncode != 0
    assert completed.stdout.splitlines() == [
        f"FAIL tests-untouched: {BASE_COMMIT_ENV} is unset"
    ]


def test_tests_untouched_fails_loudly_on_a_base_commit_that_is_not_in_the_tree(
    project: Path, uv_environment: Path
) -> None:
    """A base git cannot resolve is a named failure, not a bare `set -e` exit."""
    completed = run_script(
        TESTS_UNTOUCHED, project, uv_environment, base_commit="0" * 40
    )

    assert completed.returncode != 0
    assert completed.stdout.startswith(
        f"FAIL tests-untouched: cannot diff {BASE_COMMIT_ENV} "
    )
