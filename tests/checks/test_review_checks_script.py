"""`scripts/review-checks.sh`: the feature gate plus the acceptance-test guard.

The fixture repo carries its own trivial `scripts/verify-feature.sh`, which is
what the script calls (by its repo-relative path — see the script's header);
that keeps these cases about the guard and about the fact that the call
happens at all.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.checks._project import ACCEPTANCE_FILE, REVIEW_CHECKS, git, run_script

pytestmark = pytest.mark.proc

_PASSING_STUB = "#!/usr/bin/env bash\necho 'PASS stub'\n"
_FAILING_STUB = "#!/usr/bin/env bash\necho 'FAIL stub'\nexit 1\n"


def _plant_stub(project: Path, body: str) -> None:
    """Give the fixture repo the sibling script `review-checks.sh` calls."""
    script = project / "scripts" / "verify-feature.sh"
    script.parent.mkdir(exist_ok=True)
    script.write_text(body, encoding="utf-8")
    script.chmod(0o755)


def _commit(project: Path, relative: str, message: str) -> None:
    """Commit one file so it is what `HEAD` touches."""
    path = project / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("value = 1\n", encoding="utf-8")
    git(project, "add", "-A")
    git(project, "commit", "--quiet", "-m", message)


def test_review_checks_passes_when_the_commit_leaves_acceptance_tests_alone(
    project: Path, uv_environment: Path
) -> None:
    """A commit outside `tests/acceptance/` passes the guard."""
    _plant_stub(project, _PASSING_STUB)
    _commit(project, "workflow_interpreter/feature.py", "a feature")

    completed = run_script(REVIEW_CHECKS, project, uv_environment)

    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert "PASS tests-untouched" in completed.stdout.splitlines()
    assert len(completed.stdout.splitlines()) <= 8


def test_review_checks_fails_when_the_commit_touches_acceptance_tests(
    project: Path, uv_environment: Path
) -> None:
    """The reviewed commit may not edit the acceptance tests it is judged by."""
    _plant_stub(project, _PASSING_STUB)
    _commit(project, ACCEPTANCE_FILE, "edit the acceptance tests")

    completed = run_script(REVIEW_CHECKS, project, uv_environment)

    assert completed.returncode != 0
    assert any(
        line.startswith("FAIL tests-untouched: ") and ACCEPTANCE_FILE in line
        for line in completed.stdout.splitlines()
    ), completed.stdout


def test_review_checks_stops_when_the_feature_gate_fails(
    project: Path, uv_environment: Path
) -> None:
    """The gate runs first: a red `verify-feature.sh` ends the script there."""
    _plant_stub(project, _FAILING_STUB)
    _commit(project, "workflow_interpreter/feature.py", "a feature")

    completed = run_script(REVIEW_CHECKS, project, uv_environment)

    assert completed.returncode != 0
    assert "PASS tests-untouched" not in completed.stdout
