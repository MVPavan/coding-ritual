"""`scripts/checks/assertion-strength.sh`: no acceptance test that cannot fail.

Run exactly as the wrapper runs it (`supervisor/verify.py`): cwd is the tree
under test, no arguments.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.checks._project import (
    ACCEPTANCE_DIR,
    ASSERTION_STRENGTH,
    WEAK_TEST_BODY,
    WEAK_TEST_FILE,
    run_script,
)

pytestmark = pytest.mark.proc

_MAX_LINES = 8
_OFFENDER_LIMIT = 6
_WEAK_COUNT = 7
_HEADER = (
    '"""Many tests, none of which asserts."""\n\nfrom __future__ import annotations\n'
)
_WEAK_TEMPLATE = '\n\ndef test_weak_{index}() -> None:\n    """No assertion."""\n    value = {index}\n    print(value)\n'
_RAISES_TEST = '''\
"""A test whose only claim is that something raises."""

from __future__ import annotations

import pytest


def test_it_raises() -> None:
    """`pytest.raises` counts as an assertion."""
    with pytest.raises(ValueError):
        raise ValueError("boom")
'''


def test_assertion_strength_passes_when_every_test_asserts(
    project: Path, uv_environment: Path
) -> None:
    """The fixture's acceptance test asserts: exit 0, one line."""
    completed = run_script(ASSERTION_STRENGTH, project, uv_environment)

    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert completed.stdout.splitlines() == [
        f"PASS assertion-strength: every test under {ACCEPTANCE_DIR} asserts"
    ]


def test_assertion_strength_accepts_a_pytest_raises_body(
    project: Path, uv_environment: Path
) -> None:
    """A test that only asserts a raise still constrains the code."""
    (project / ACCEPTANCE_DIR / "test_raises.py").write_text(
        _RAISES_TEST, encoding="utf-8"
    )

    completed = run_script(ASSERTION_STRENGTH, project, uv_environment)

    assert completed.returncode == 0, completed.stdout + completed.stderr


def test_assertion_strength_names_the_test_that_cannot_fail(
    project: Path, uv_environment: Path
) -> None:
    """The offender is reported as `file:line`, not as a count."""
    (project / WEAK_TEST_FILE).write_text(WEAK_TEST_BODY, encoding="utf-8")

    completed = run_script(ASSERTION_STRENGTH, project, uv_environment)

    assert completed.returncode != 0
    lines = completed.stdout.splitlines()
    assert lines[0] == "FAIL assertion-strength: 1 test function(s) with no assertion"
    # `def test_nothing_is_asserted` is the sixth line of the weak fixture body.
    assert lines[1] == f"{WEAK_TEST_FILE}:6"
    assert len(lines) <= _MAX_LINES


def test_assertion_strength_truncates_a_long_offender_list(
    project: Path, uv_environment: Path
) -> None:
    """Seven offenders still fit the eight-line budget the wrapper records."""
    body = _HEADER + "".join(
        _WEAK_TEMPLATE.format(index=index) for index in range(_WEAK_COUNT)
    )
    (project / ACCEPTANCE_DIR / "test_many_weak.py").write_text(body, encoding="utf-8")

    completed = run_script(ASSERTION_STRENGTH, project, uv_environment)

    assert completed.returncode != 0
    lines = completed.stdout.splitlines()
    assert lines[0].startswith(f"FAIL assertion-strength: {_WEAK_COUNT} test function")
    assert len(lines) == 2 + _OFFENDER_LIMIT
    assert lines[-1].startswith(f"... and {_WEAK_COUNT - _OFFENDER_LIMIT} more (see ")
    assert len(lines) <= _MAX_LINES
