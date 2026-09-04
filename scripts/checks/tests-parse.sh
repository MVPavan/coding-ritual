#!/usr/bin/env bash
# §7.3 verifier: the acceptance suite parses and collects at least one test.
#
# Contract, as the wrapper runs it (supervisor/verify.py): argv[0] is
# /proc/self/fd/<n>, there are NO arguments, and cwd is a clean checkout of the
# commit under test — so the repo root comes from git in cwd, never from `$0`,
# which names a descriptor in /proc.
# Exit 0 = pass. At most eight lines to stdout; pytest's own output goes to the
# PID-suffixed log named on failure (the script also runs inside its own test
# suite, and a fixed name would truncate the outer run's log).
# Self-contained: no `source`, no includes; only git and uv plus POSIX tools.
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

TESTS_DIR="tests/acceptance"
LOG="${TMPDIR:-/tmp}/tests-parse.$$.log"
: >"$LOG"

# A suite that does not import is not a suite: a reviewer reading it would be
# grading text nobody can run, and every later check that measures the tests
# would measure nothing.
if ! uv run pytest --collect-only -q "$TESTS_DIR" >"$LOG" 2>&1; then
    printf 'FAIL tests-parse: %s does not collect (see %s)\n' "$TESTS_DIR" "$LOG"
    exit 1
fi

# Every collected node id carries `::`; the trailing summary lines do not.
collected=$(grep -c '::' "$LOG" || true)
if [ "$collected" -lt 1 ]; then
    printf 'FAIL tests-parse: %s collected no test (see %s)\n' "$TESTS_DIR" "$LOG"
    exit 1
fi

printf 'PASS tests-parse: %s collected %s test(s)\n' "$TESTS_DIR" "$collected"
