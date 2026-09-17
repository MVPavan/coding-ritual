#!/usr/bin/env bash
# §7.3 verifier for the `debrief` node of `feature-delivery` (run-ledger §3.7).
#
# Contract, as the wrapper actually runs it (supervisor/verify.py): argv[0] is
# /proc/self/fd/<n>, there are NO arguments, and cwd is a clean detached
# checkout of the commit under test. Unlike the other verifiers this one IS
# given environment: WF_BASE_COMMIT, plus the run's own identity —
# WF_EPIC_SEGMENT, WF_TASK_ID and WF_ATTEMPT, pinned on the root record.
#
# It answers one question: did this round write its knowledge into its own
# directory, and nothing else? Containment is here rather than in the grant
# because a grant is disclosure, not containment (ADR 0001).
#
# Exit 0 = pass, non-zero at the first failing check. Self-contained: git and
# POSIX tools only.
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

fail() {
    printf 'FAIL %s\n' "$1"
    exit 1
}

# The identity is a FACT on the root, never a parse of an id, so an empty one
# is a wiring defect and not a run this check may quietly pass.
[ -n "${WF_BASE_COMMIT:-}" ] || fail "debrief-identity: WF_BASE_COMMIT is empty"
[ -n "${WF_EPIC_SEGMENT:-}" ] || fail "debrief-identity: WF_EPIC_SEGMENT is empty"
[ -n "${WF_TASK_ID:-}" ] || fail "debrief-identity: WF_TASK_ID is empty"
[ -n "${WF_ATTEMPT:-}" ] || fail "debrief-identity: WF_ATTEMPT is empty"

DIR="docs/workstreams/$WF_EPIC_SEGMENT/runs/$WF_TASK_ID/a$WF_ATTEMPT"
RENDER_REF="refs/wf/render/$WF_TASK_ID-a$WF_ATTEMPT"
DEBRIEF_MAX_BYTES=16384

# 1. Containment. Every path this round changed must be inside the one
#    permitted directory. `--no-renames` so a rename reports both of its ends.
outside="$(
    git diff --name-only --no-renames "$WF_BASE_COMMIT" HEAD -- \
    | grep -v "^$DIR/" || true
)"
if [ -n "$outside" ]; then
    fail "debrief-containment: outside $DIR: $(printf '%s' "$outside" | tr '\n' ' ')"
fi
printf 'PASS debrief-containment\n'

# 2. Presence. All three files, or the round did not happen.
for name in debrief.md findings.md evidence.json; do
    [ -f "$DIR/$name" ] || fail "debrief-files: $DIR/$name is missing"
done
printf 'PASS debrief-files\n'

# 3. Fidelity. The two rendered files must be the render, byte for byte. The
#    render is pinned as a commit under a ref named by THIS run's task and
#    attempt, which is the only identity this check is given.
git rev-parse --verify --quiet "$RENDER_REF" >/dev/null \
    || fail "debrief-render: $RENDER_REF is not pinned"
for name in findings.md evidence.json; do
    git cat-file blob "$RENDER_REF:$name" >"${TMPDIR:-/tmp}/wf-render.$$" \
        || fail "debrief-render: $RENDER_REF:$name is unreadable"
    if ! cmp -s "${TMPDIR:-/tmp}/wf-render.$$" "$DIR/$name"; then
        rm -f "${TMPDIR:-/tmp}/wf-render.$$"
        fail "debrief-render: $DIR/$name differs from $RENDER_REF:$name"
    fi
    rm -f "${TMPDIR:-/tmp}/wf-render.$$"
done
printf 'PASS debrief-render\n'

# 4. Size. A debrief is a page, not a corpus; the bound is stated so a node
#    can obey it and a reader can rely on it.
size="$(wc -c <"$DIR/debrief.md")"
if [ "$size" -gt "$DEBRIEF_MAX_BYTES" ]; then
    fail "debrief-size: debrief.md is $size bytes, over $DEBRIEF_MAX_BYTES"
fi
[ "$size" -gt 0 ] || fail "debrief-size: debrief.md is empty"
printf 'PASS debrief-size\n'
