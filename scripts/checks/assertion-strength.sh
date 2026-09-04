#!/usr/bin/env bash
# §7.3 verifier: no acceptance test that cannot fail.
#
# A test function with no `assert` and no `pytest.raises` passes whatever the
# code does, so it inflates the suite a reviewer and the mutants are judged by
# without adding a single constraint.
#
# Contract, as the wrapper runs it (supervisor/verify.py): argv[0] is
# /proc/self/fd/<n>, there are NO arguments, and cwd is a clean checkout of the
# commit under test — so the repo root comes from git in cwd, never from `$0`,
# which names a descriptor in /proc.
# Exit 0 = pass. At most eight lines to stdout; the full offender list goes to
# the PID-suffixed log named on failure.
# Self-contained: no `source`, no includes; only git plus POSIX tools.
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

TESTS_DIR="tests/acceptance"
LOG="${TMPDIR:-/tmp}/assertion-strength.$$.log"
: >"$LOG"

if [ ! -d "$TESTS_DIR" ]; then
    printf 'FAIL assertion-strength: %s does not exist\n' "$TESTS_DIR"
    exit 1
fi

# A test's body is every line indented deeper than its `def`, up to the first
# line that is not — which is what lets one awk pass judge nested helpers and
# decorated tests alike without parsing Python.
find "$TESTS_DIR" -type f -name '*.py' -print | sort | while IFS= read -r file; do
    awk -v file="$file" '
        function report() { if (open_fn && !found) print file ":" start }
        /^[[:space:]]*(async[[:space:]]+)?def[[:space:]]+test_/ {
            report()
            open_fn = 1
            found = 0
            start = FNR
            match($0, /^[[:space:]]*/)
            indent = RLENGTH
            next
        }
        open_fn == 1 {
            if ($0 ~ /^[[:space:]]*$/) next
            match($0, /^[[:space:]]*/)
            if (RLENGTH <= indent) { report(); open_fn = 0; next }
            # An `assert` STATEMENT, not the word: a docstring that says "no
            # assert here" would otherwise vouch for the test that has none.
            if ($0 ~ /^[[:space:]]*assert[[:space:](]/) found = 1
            if ($0 ~ /pytest\.raises\(/) found = 1
        }
        END { report() }
    ' "$file" >>"$LOG"
done

count=$(wc -l <"$LOG" | tr -d ' ')
if [ "$count" -eq 0 ]; then
    printf 'PASS assertion-strength: every test under %s asserts\n' "$TESTS_DIR"
    exit 0
fi

printf 'FAIL assertion-strength: %s test function(s) with no assertion\n' "$count"
head -6 "$LOG"
if [ "$count" -gt 6 ]; then
    printf '... and %s more (see %s)\n' "$((count - 6))" "$LOG"
fi
exit 1
