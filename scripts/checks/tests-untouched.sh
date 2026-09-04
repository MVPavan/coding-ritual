#!/usr/bin/env bash
# §7.3 verifier: this round did not edit the acceptance tests it is judged by.
#
# Contract, as the wrapper runs it (supervisor/verify.py): argv[0] is
# /proc/self/fd/<n>, there are NO arguments, and cwd is a clean checkout of the
# commit under test — so the repo root comes from git in cwd, never from `$0`,
# which names a descriptor in /proc.
#
# `$WF_BASE_COMMIT` is the activation's `intended_base_commit`, injected by the
# wrapper (`verify.py`, phase 7 D5). It is the ONLY way to name where the round
# started: the checkout is detached, with no branch and no upstream, so `HEAD~1`
# would compare against the previous commit of the round instead of its base.
# Unset is a FAILURE naming the variable, never an empty diff that passes.
# Exit 0 = pass. At most eight lines to stdout; the full list of touched files
# goes to the PID-suffixed log named on failure.
# Self-contained: no `source`, no includes; only git plus POSIX tools.
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

TESTS_DIR="tests/acceptance"
LOG="${TMPDIR:-/tmp}/tests-untouched.$$.log"

if [ -z "${WF_BASE_COMMIT:-}" ]; then
    printf 'FAIL tests-untouched: WF_BASE_COMMIT is unset\n'
    exit 1
fi

: >"$LOG"
if ! git diff --name-only "$WF_BASE_COMMIT" HEAD -- "$TESTS_DIR" >"$LOG" 2>&1; then
    printf 'FAIL tests-untouched: cannot diff WF_BASE_COMMIT %s (see %s)\n' \
        "$WF_BASE_COMMIT" "$LOG"
    exit 1
fi

count=$(wc -l <"$LOG" | tr -d ' ')
if [ "$count" -eq 0 ]; then
    printf 'PASS tests-untouched: %s unchanged since %s\n' "$TESTS_DIR" "$WF_BASE_COMMIT"
    exit 0
fi

printf 'FAIL tests-untouched: %s file(s) changed under %s\n' "$count" "$TESTS_DIR"
head -6 "$LOG"
if [ "$count" -gt 6 ]; then
    printf '... and %s more (see %s)\n' "$((count - 6))" "$LOG"
fi
exit 1
