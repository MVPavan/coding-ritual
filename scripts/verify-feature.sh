#!/usr/bin/env bash
# §7.3 verifier for the `implement` node of `feature-delivery`.
#
# Contract, as the wrapper actually runs it (supervisor/verify.py:297-318):
# argv[0] is /proc/self/fd/<n>, there are NO arguments and NO `$WF_*`
# environment. cwd is a clean checkout of the commit under test, so everything
# is derived from git in cwd — including the repo root, because `$0` names a
# descriptor in /proc and `dirname "$0"` would be /proc/self/fd.
# Exit 0 = pass, non-zero at the first failing check. At most eight lines to
# stdout; the full output of every command goes to the log named on failure.
# Self-contained: no `source`, no includes; only git, uv, ruff, mypy and
# pytest (through `uv run`) plus POSIX tools.
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

# PID-suffixed: this script also runs inside its own test suite, and a
# fixed name would have the nested run truncate the outer run's log.
LOG="${TMPDIR:-/tmp}/verify-feature.$$.log"
: >"$LOG"

# One gate command: all of its output to the log, one line to stdout.
check() {
    name=$1
    shift
    if { printf '=== %s: %s\n' "$name" "$*"; "$@"; } >>"$LOG" 2>&1; then
        printf 'PASS %s\n' "$name"
    else
        printf 'FAIL %s (see %s)\n' "$name" "$LOG"
        exit 1
    fi
}

# The gate recipe minus `pytest -m bd`: the bd family needs a real bd
# workspace, which this checkout does not have, so it would fail for a reason
# that is not about the commit under test.
# One proc test is deselected from the LIVE verify set only: it exercises a
# real steer-vs-wrapper close race (cr-us7) that fires under the load a live
# run itself creates, and a flake at a review node costs a whole rework round
# (cr-o85.34.13). The repo gate in .claude/project/verification.md still runs it.
racy="tests/test_foreman_steer.py::test_steer_proc_raises_its_own_flag_and_kills_a_genuinely_live_child"
check tests uv run pytest -q -m "not bd and not live" --deselect "$racy"
check proc-tests uv run pytest -q -m proc --deselect "$racy"
check ruff-check uv run ruff check workflow_interpreter/ tests/
check ruff-format uv run ruff format --check workflow_interpreter/ tests/
check mypy env MYPYPATH=. uv run mypy --strict --explicit-package-bases workflow_interpreter/
