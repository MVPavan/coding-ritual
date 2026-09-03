"""`scripts/verify-feature.sh` against a real tree, passing and failing.

The script is run exactly as the wrapper runs it (`supervisor/verify.py:297`):
cwd is the tree under test, there are no arguments and no `$WF_*` environment.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.checks._project import (
    LINT_BROKEN_BODY,
    LINT_BROKEN_FILE,
    VERIFY_FEATURE,
    run_script,
)

pytestmark = pytest.mark.proc

_CHECK_NAMES = ("tests", "proc-tests", "ruff-check", "ruff-format", "mypy")


def test_verify_feature_passes_on_a_clean_tree(
    project: Path, uv_environment: Path
) -> None:
    """Every gate command green: exit 0 and one `PASS <name>` line per check."""
    completed = run_script(VERIFY_FEATURE, project, uv_environment)

    assert completed.returncode == 0, completed.stdout + completed.stderr
    lines = completed.stdout.splitlines()
    assert lines == [f"PASS {name}" for name in _CHECK_NAMES]
    assert len(lines) <= 8


def test_verify_feature_fails_on_a_lint_error_and_names_its_log(
    project: Path, uv_environment: Path
) -> None:
    """A planted `ruff check` failure stops the script non-zero at that check."""
    (project / LINT_BROKEN_FILE).write_text(LINT_BROKEN_BODY, encoding="utf-8")

    completed = run_script(VERIFY_FEATURE, project, uv_environment)

    assert completed.returncode != 0
    lines = completed.stdout.splitlines()
    assert lines[-1].startswith("FAIL ruff-check (see ")
    assert not any(line.startswith("FAIL") for line in lines[:-1])
    log = Path(lines[-1].split("(see ", 1)[1].rstrip(")"))
    assert LINT_BROKEN_FILE in log.read_text(encoding="utf-8")
