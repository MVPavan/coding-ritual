#!/usr/bin/env bash
# §7.3 verifier for the `debrief` node of `feature-delivery` (run-ledger §3.7).
#
# Contract, as the wrapper actually runs it (supervisor/verify.py): argv[0] is
# /proc/self/fd/<n>, there are NO arguments, and cwd is a clean detached
# checkout of the commit under test. Unlike the other verifiers this one IS
# given environment: WF_BASE_COMMIT, the run's own identity — WF_EPIC_SEGMENT,
# WF_TASK_ID and WF_ATTEMPT, pinned on the root record — and the render this
# activation was minted against, WF_RENDER_OID and WF_RENDER_DIGEST, taken from
# the activation's own `LedgerRenderBinding`.
#
# It answers one question: did this round write its knowledge into its own
# directory, and nothing else? Containment is here rather than in the grant
# because a grant is disclosure, not containment (ADR 0001).
#
# Everything it reads it reads from git OBJECTS — `git ls-tree`, `git cat-file`
# against HEAD and against the pinned render id — never from the working tree
# and never through a ref NAME. A ref is a mutable name the sandbox protects
# only as a loose file (`supervisor/sandbox.py`, WF_REFS_DIR: `packed-refs`
# stays writable for the runner's own commit), so a check that resolved
# `refs/wf/render/<task>-a<n>` itself could be pointed at bytes the runner
# chose; an object id pinned in the activation carrier cannot be.
#
# Exit 0 = pass, non-zero at the first failing check. Self-contained: git,
# POSIX tools and one sha256 utility.
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

WORK="$(mktemp -d "${TMPDIR:-/tmp}/wf-debrief.XXXXXX")"
trap 'rm -rf "$WORK"' EXIT

fail() {
    printf 'FAIL %s\n' "$1"
    exit 1
}

# A single safe path component — the same rule `contracts/run_identity.py`
# enforces on the record, re-applied here because this script interpolates
# these values into a path and into a prefix comparison. A glob, not a regex:
# containment must not depend on which regex dialect the host's tools speak.
safe_component() {
    case "$2" in
        '' | .* | *[!A-Za-z0-9._-]*)
            fail "debrief-identity: $1 is not one safe path component: '$2'"
            ;;
    esac
}

# The identity is a FACT on the root, never a parse of an id, so an empty one
# is a wiring defect and not a run this check may quietly pass.
[ -n "${WF_BASE_COMMIT:-}" ] || fail "debrief-identity: WF_BASE_COMMIT is empty"
[ -n "${WF_EPIC_SEGMENT:-}" ] || fail "debrief-identity: WF_EPIC_SEGMENT is empty"
[ -n "${WF_TASK_ID:-}" ] || fail "debrief-identity: WF_TASK_ID is empty"
[ -n "${WF_ATTEMPT:-}" ] || fail "debrief-identity: WF_ATTEMPT is empty"
safe_component WF_EPIC_SEGMENT "$WF_EPIC_SEGMENT"
safe_component WF_TASK_ID "$WF_TASK_ID"
case "$WF_ATTEMPT" in
    '' | *[!0-9]*) fail "debrief-identity: WF_ATTEMPT is not a number" ;;
esac
[ "$WF_ATTEMPT" -ge 1 ] || fail "debrief-identity: WF_ATTEMPT is below 1"
case "${WF_RENDER_OID:-}" in
    '') ;;
    *[!0-9a-f]*) fail "debrief-render: WF_RENDER_OID is not an object id" ;;
esac

DIR="docs/workstreams/$WF_EPIC_SEGMENT/runs/$WF_TASK_ID/a$WF_ATTEMPT"
REQUIRED="debrief.md findings.md evidence.json"
RENDERED="findings.md evidence.json"
BLOB_MODE="100644"
DEBRIEF_MAX_BYTES=16384

sha256_of() {
    if command -v sha256sum >/dev/null 2>&1; then
        sha256sum "$@" | cut -d' ' -f1
    elif command -v shasum >/dev/null 2>&1; then
        shasum -a 256 "$@" | cut -d' ' -f1
    else
        fail "debrief-render: no sha256 utility on this host"
    fi
}

# 1. Containment. Every path this round changed must be inside the one
#    permitted directory. `-z` so a path is compared as bytes rather than as a
#    quoted display form, `--no-renames` so a rename reports both of its ends,
#    and the comparison is a literal `$DIR/` prefix on a whole component — no
#    regex, so no value in the identity can widen it.
outside=""
while IFS= read -r -d '' path; do
    case "$path" in
        "$DIR"/*) ;;
        *) outside="$outside $path" ;;
    esac
done < <(git diff -z --name-only --no-renames "$WF_BASE_COMMIT" HEAD)
if [ -n "$outside" ]; then
    fail "debrief-containment: outside $DIR:$outside"
fi
printf 'PASS debrief-containment\n'

# 2. Presence and shape. All three files as REGULAR blobs, or the round did not
#    happen: a committed symlink satisfies every byte comparison below while
#    pointing at something outside the commit, and a gitlink is not a file at
#    all. The whole permitted directory is swept, not just the three names,
#    because a symlink beside them is still this round's output.
for name in $REQUIRED; do
    entry="$(git ls-tree HEAD -- "$DIR/$name")"
    [ -n "$entry" ] || fail "debrief-files: $DIR/$name is missing"
    mode="${entry%% *}"
    [ "$mode" = "$BLOB_MODE" ] \
        || fail "debrief-files: $DIR/$name has mode $mode, not $BLOB_MODE"
done
while IFS=$'\t' read -r meta path; do
    [ -n "$meta" ] || continue
    mode="${meta%% *}"
    [ "$mode" = "$BLOB_MODE" ] \
        || fail "debrief-files: $path has mode $mode, not $BLOB_MODE"
done < <(git ls-tree -r HEAD -- "$DIR")
printf 'PASS debrief-files\n'

# 3. Fidelity. The two rendered files must be the render this activation was
#    minted against, byte for byte — read from the pinned OBJECT id, and then
#    checked against the digest the binding carries, so neither a moved ref nor
#    a substituted tree can redefine what the debrief is compared against.
#
#    An activation the engine bound NO render to is told so by an empty
#    WF_RENDER_OID and SKIPS this section rather than resolving a render by
#    name. `review` is such an activation: it runs this same check over the
#    debrief's commit, and the graph gives it no render input because an
#    engine source may only be consumed by a writing node. That is not a hole
#    — the three files are produced by the `debrief` activation, which always
#    carries the binding, and a debrief this check refuses is routed to
#    `triage` and never reaches `review` at all.
check_render() {
    for name in $RENDERED; do
        git cat-file blob "$WF_RENDER_OID:$name" >"$WORK/render.$name" \
            || fail "debrief-render: $WF_RENDER_OID:$name is unreadable"
        git cat-file blob "HEAD:$DIR/$name" >"$WORK/landed.$name" \
            || fail "debrief-render: $DIR/$name is unreadable"
        cmp -s "$WORK/render.$name" "$WORK/landed.$name" \
            || fail "debrief-render: $DIR/$name differs from $WF_RENDER_OID:$name"
    done
    # The binding names the whole render with ONE digest over both files,
    # findings first — `foreman/ledger_render.py`, `RenderedRun.payload_digest`.
    cat "$WORK/render.findings.md" "$WORK/render.evidence.json" >"$WORK/payload"
    digest="$(sha256_of "$WORK/payload")"
    [ "$digest" = "$WF_RENDER_DIGEST" ] || fail \
        "debrief-render: render $WF_RENDER_OID hashes to $digest, pinned $WF_RENDER_DIGEST"
    printf 'PASS debrief-render\n'
}

if [ -z "${WF_RENDER_OID:-}" ] || [ -z "${WF_RENDER_DIGEST:-}" ]; then
    printf 'SKIP debrief-render: the engine pinned no render for this activation\n'
else
    check_render
fi

# 4. Size. A debrief is a page, not a corpus; the bound is stated so a node
#    can obey it and a reader can rely on it. Measured on the LANDED blob, for
#    the same reason as everything above.
size="$(git cat-file -s "HEAD:$DIR/debrief.md")"
if [ "$size" -gt "$DEBRIEF_MAX_BYTES" ]; then
    fail "debrief-size: debrief.md is $size bytes, over $DEBRIEF_MAX_BYTES"
fi
[ "$size" -gt 0 ] || fail "debrief-size: debrief.md is empty"
printf 'PASS debrief-size\n'
