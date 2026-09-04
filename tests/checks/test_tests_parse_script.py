"""`scripts/checks/tests-parse.sh`: the acceptance suite imports and collects.

Run exactly as the wrapper runs it (`supervisor/verify.py`): cwd is the tree
under test, no arguments.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.checks._project import (
    ACCEPTANCE_DIR,
    TESTS_PARSE,
    run_script,
)

pytestmark = pytest.mark.proc

_BROKEN_TEST = '"""A file that does not parse."""\n\ndef test_x(: -> None\n'


def test_tests_parse_passes_when_the_acceptance_suite_collects(
    project: Path, uv_environment: Path
) -> None:
    """The fixture's one acceptance test is collected: exit 0, one line."""
    completed = run_script(TESTS_PARSE, project, uv_environment)

    assert completed.returncode == 0, completed.stdout + completed.stderr
    lines = completed.stdout.splitlines()
    assert len(lines) == 1
    assert lines[0] == f"PASS tests-parse: {ACCEPTANCE_DIR} collected 1 test(s)"


def test_tests_parse_fails_when_a_test_file_does_not_import(
    project: Path, uv_environment: Path
) -> None:
    """A suite that cannot be collected is not a suite a reviewer can grade."""
    (project / ACCEPTANCE_DIR / "test_broken.py").write_text(
        _BROKEN_TEST, encoding="utf-8"
    )

    completed = run_script(TESTS_PARSE, project, uv_environment)

    assert completed.returncode != 0
    lines = completed.stdout.splitlines()
    assert len(lines) <= 8
    assert lines[0].startswith(f"FAIL tests-parse: {ACCEPTANCE_DIR} does not collect")
    log = Path(lines[0].split("(see ", 1)[1].rstrip(")"))
    assert "test_broken.py" in log.read_text(encoding="utf-8")


def test_tests_parse_fails_when_there_is_no_acceptance_suite_at_all(
    project: Path, uv_environment: Path
) -> None:
    """An empty (or absent) suite collects nothing, which is a FAIL, not a pass."""
    for path in (project / ACCEPTANCE_DIR).iterdir():
        path.unlink()

    completed = run_script(TESTS_PARSE, project, uv_environment)

    assert completed.returncode != 0
    assert completed.stdout.startswith(f"FAIL tests-parse: {ACCEPTANCE_DIR}")
    assert len(completed.stdout.splitlines()) <= 8
