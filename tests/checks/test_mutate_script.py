"""`scripts/checks/mutate.sh`: would the suite notice if this round were wrong?

Run exactly as the wrapper runs it (`supervisor/verify.py`): cwd is the tree
under test, no arguments, and `WF_BASE_COMMIT` in the environment.

Each case pays for a baseline run plus one run per mutant, so the wall time is
printed: the phase 7 plan budgets baseline + 8 mutants inside the node's 25 m
timeout, and this is the only place that number is measured rather than
assumed.
"""

from __future__ import annotations

import hashlib
import re
import subprocess
import time
from pathlib import Path

import pytest

from tests.checks._project import (
    BASE_COMMIT_ENV,
    MUTATE,
    MUTATE_PY,
    REPO_ROOT,
    commit_file,
    git,
    head_commit,
    run_script,
)

pytestmark = pytest.mark.proc

_MODULE_FILE = "workflow_interpreter/rule.py"
_MODULE_BODY = '''\
"""One comparison for the mutants to attack."""

from __future__ import annotations


def is_small(value: int) -> bool:
    """Whether `value` is under the fixed threshold."""
    return value < 10
'''
_MUTATED_LINE = 8
_SITE = f"{_MODULE_FILE}:{_MUTATED_LINE} < -> <="

_COVERED_TEST_FILE = "tests/test_rule.py"
_COVERED_TEST = '''\
"""Both sides of the threshold."""

from __future__ import annotations

from workflow_interpreter.rule import is_small


def test_the_threshold_is_exclusive() -> None:
    """The boundary case is what kills the `<=` mutant."""
    assert is_small(9)
    assert not is_small(10)
'''
_UNCOVERED_TEST = '''\
"""Only the far side of the threshold — the boundary is never asserted."""

from __future__ import annotations

from workflow_interpreter.rule import is_small


def test_a_small_value_is_small() -> None:
    """True for 9 whether the operator is `<` or `<=`."""
    assert is_small(9)
'''

_README_FILE = "README.md"
_README_BODY = "# no python changed\n"


def _timed(
    project: Path, uv_environment: Path, base: str
) -> tuple[subprocess.CompletedProcess[str], float]:
    """Run the check and report how long the whole mutation pass took."""
    started = time.monotonic()
    completed = run_script(MUTATE, project, uv_environment, base_commit=base)
    return completed, time.monotonic() - started


def _report(
    label: str, elapsed: float, completed: subprocess.CompletedProcess[str]
) -> None:
    """Print the measured wall time beside the check's own verdict."""
    print(f"\nmutate wall time [{label}]: {elapsed:.1f}s\n{completed.stdout}")


def test_mutate_kills_every_mutant_when_the_boundary_is_asserted(
    project: Path, uv_environment: Path
) -> None:
    """A test that pins the boundary kills the `<` -> `<=` mutant."""
    base = head_commit(project)
    commit_file(project, _MODULE_FILE, _MODULE_BODY, "a rule")
    commit_file(project, _COVERED_TEST_FILE, _COVERED_TEST, "and its test")

    completed, elapsed = _timed(project, uv_environment, base)
    _report("all killed", elapsed, completed)

    assert completed.returncode == 0, completed.stdout + completed.stderr
    lines = completed.stdout.splitlines()
    assert lines[0].startswith("PASS mutate: 1/1 mutants killed (see ")
    assert len(lines) <= 8
    log = Path(lines[0].split("(see ", 1)[1].rstrip(")"))
    # The NAME of the killing test, never a count (build-loop.md).
    assert "test_the_threshold_is_exclusive" in log.read_text(encoding="utf-8")


def test_mutate_names_the_site_no_test_covers(
    project: Path, uv_environment: Path
) -> None:
    """A survivor is a hole in the tests, reported as site plus mutation."""
    base = head_commit(project)
    commit_file(project, _MODULE_FILE, _MODULE_BODY, "a rule")
    commit_file(project, _COVERED_TEST_FILE, _UNCOVERED_TEST, "and a weak test")

    completed, elapsed = _timed(project, uv_environment, base)
    _report("one survivor", elapsed, completed)

    assert completed.returncode != 0
    lines = completed.stdout.splitlines()
    assert lines[0].startswith("FAIL mutate: 1 of 1 mutants survived (see ")
    assert lines[1] == _SITE
    assert len(lines) <= 8


def test_mutate_passes_in_one_line_when_no_python_changed(
    project: Path, uv_environment: Path
) -> None:
    """Nothing to mutate is a pass, not an error and not a silent green."""
    base = head_commit(project)
    commit_file(project, _README_FILE, _README_BODY, "docs only")

    completed, elapsed = _timed(project, uv_environment, base)
    _report("no sites", elapsed, completed)

    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert completed.stdout.splitlines() == [
        "PASS mutate: no mutable line changed under workflow_interpreter/"
    ]


def test_mutate_reports_a_red_baseline_instead_of_planting_mutants(
    project: Path, uv_environment: Path
) -> None:
    """`run_checks` never short-circuits, so a red tree reaches this check."""
    base = head_commit(project)
    commit_file(project, _MODULE_FILE, _MODULE_BODY, "a rule")
    commit_file(
        project,
        _COVERED_TEST_FILE,
        _COVERED_TEST.replace("is_small(9)", "is_small(99)"),
        "a test that fails",
    )

    completed, elapsed = _timed(project, uv_environment, base)
    _report("red baseline", elapsed, completed)

    assert completed.returncode != 0
    assert completed.stdout.startswith("FAIL mutate: baseline red before any mutant")
    assert len(completed.stdout.splitlines()) == 1


def test_mutate_refuses_a_base_commit_this_checkout_does_not_have(
    project: Path, uv_environment: Path
) -> None:
    """An unresolvable base is refused BEFORE the baseline, in milliseconds."""
    commit_file(project, _MODULE_FILE, _MODULE_BODY, "a rule")

    started = time.monotonic()
    completed = run_script(MUTATE, project, uv_environment, base_commit="0" * 40)
    elapsed = time.monotonic() - started
    _report("unresolvable base", elapsed, completed)

    assert completed.returncode == 1
    assert completed.stdout.splitlines() == [
        f"FAIL mutate: {BASE_COMMIT_ENV} {'0' * 40} is not a commit in this checkout"
    ]


def test_mutate_still_finds_its_sites_under_a_no_prefix_diff_config(
    project: Path, uv_environment: Path
) -> None:
    """`diff.noprefix=true` must not turn the check into a silent PASS.

    The site picker reads `+++ b/<path>`; a checkout configured to drop the
    prefix would yield zero sites, and zero sites is a PASS — a mutation check
    that planted nothing while reporting green.
    """
    git(project, "config", "diff.noprefix", "true")
    base = head_commit(project)
    commit_file(project, _MODULE_FILE, _MODULE_BODY, "a rule")
    commit_file(project, _COVERED_TEST_FILE, _UNCOVERED_TEST, "and a weak test")

    completed, elapsed = _timed(project, uv_environment, base)
    _report("noprefix diff", elapsed, completed)

    assert completed.returncode != 0
    assert completed.stdout.splitlines()[1] == _SITE


def test_the_pinned_site_picker_digest_is_the_real_files_digest() -> None:
    """Editing `mutate.py` without re-pinning it in `mutate.sh` fails HERE.

    Only `mutate.sh`'s bytes are pinned by §7.3, so the picker it runs is
    pinned by the sha256 embedded in it. This test is what keeps the two in
    step; without it the pin would rot into a permanent refusal.
    """
    embedded = re.search(
        r'^MUTATE_PY_SHA256="([0-9a-f]{64})"$',
        MUTATE.read_text(encoding="utf-8"),
        re.MULTILINE,
    )
    digest = hashlib.sha256((REPO_ROOT / MUTATE_PY).read_bytes()).hexdigest()

    assert embedded is not None, "mutate.sh no longer pins its site picker"
    assert embedded.group(1) == digest


def test_mutate_refuses_a_site_picker_the_round_edited(
    project: Path, uv_environment: Path
) -> None:
    """A round cannot neuter its own mutation check by rewriting `mutate.py`."""
    tampered = '"""Neutered: every round has zero sites."""\n'
    commit_file(project, MUTATE_PY, tampered, "rewrite the site picker")
    base = head_commit(project)

    completed = run_script(MUTATE, project, uv_environment, base_commit=base)

    assert completed.returncode == 1
    lines = completed.stdout.splitlines()
    assert len(lines) == 1
    assert lines[0].startswith(f"FAIL mutate: {MUTATE_PY} is ")
    assert "not the pinned " in lines[0]


def test_mutate_refuses_to_pass_when_the_base_commit_is_unset(
    project: Path, uv_environment: Path
) -> None:
    """Unset is a FAILURE naming the variable, never a vacuous zero-site pass."""
    commit_file(project, _MODULE_FILE, _MODULE_BODY, "a rule")

    completed = run_script(MUTATE, project, uv_environment)

    assert completed.returncode != 0
    assert completed.stdout.splitlines() == [f"FAIL mutate: {BASE_COMMIT_ENV} is unset"]
