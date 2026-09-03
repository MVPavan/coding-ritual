#!/usr/bin/env bash
# §7.3 verifier for the `review` node of `feature-delivery`: the implementer's
# whole gate, plus the guard that a reviewed commit may not edit the tests it
# is judged by.
#
# Contract, as the wrapper actually runs it (supervisor/verify.py:297-318):
# argv[0] is /proc/self/fd/<n>, there are NO arguments and NO `$WF_*`
# environment. cwd is a clean checkout of the commit under test, so everything
# is derived from git in cwd. Exit 0 = pass. At most eight lines to stdout.
# Self-contained: no `source`, no includes; only git, uv, ruff, mypy and
# pytest (through `uv run`) plus POSIX tools.
#
# The one cross-file call is `scripts/verify-feature.sh`, by its path in this
# checkout: `review` declares BOTH scripts, so `create` pinned both digests and
# run_checks establishes the provenance of that exact file before anything
# here runs — a pinned script calling a pinned script. It is called by path
# rather than through `$0`, which names a /proc descriptor, not a script.
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"

"$ROOT/scripts/verify-feature.sh"

# The acceptance suite is the reviewer's yardstick; a commit that moves it is
# refused whatever the rest of the gate says.
touched="$(git show --name-only --format= HEAD -- tests/acceptance | tr '\n' ' ')"
touched="$(printf '%s' "$touched" | sed 's/ *$//')"
if [ -n "$touched" ]; then
    printf 'FAIL tests-untouched: %s\n' "$touched"
    exit 1
fi
printf 'PASS tests-untouched\n'
