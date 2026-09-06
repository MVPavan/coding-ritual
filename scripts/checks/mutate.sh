#!/usr/bin/env bash
# §7.3 verifier: would the unit suite NOTICE if this round's code were wrong?
#
# The gate answers "does it pass"; this answers "can it fail". A mutation of a
# line this round changed that no test kills is a test-suite hole, reported as
# a failure naming the site.
#
# Contract, as the wrapper runs it (supervisor/verify.py): argv[0] is
# /proc/self/fd/<n>, there are NO arguments, and cwd is a clean checkout of the
# commit under test — so the repo root comes from git in cwd, never from `$0`,
# which names a descriptor in /proc.
#
# Zero mutants is a verdict, not an absence: a round that added EXECUTABLE
# Python under `workflow_interpreter/` and yielded no mutable token FAILS
# naming the count, because a mutation check that plants nothing has graded
# nothing. Comments, blank lines, docstrings and imports are not executable, so
# a documentation round still passes on zero mutants — failing it would fail it
# identically on every re-entry of the region (cr-o85.34.25).
#
# `$WF_BASE_COMMIT` is the activation's `intended_base_commit`, injected by the
# wrapper (`verify.py`, phase 7 D5); unset — or naming a commit this checkout
# does not have — is a FAILURE, never a silent "nothing changed" pass.
#
# Only THIS file's bytes are pinned by §7.3, so the site picker it runs is
# pinned HERE, by the sha256 below: `mutate.py` lives in the tree under test,
# and a round that could edit it could delete its own mutation check while
# reporting green. Editing `mutate.py` therefore means updating
# `MUTATE_PY_SHA256` in the same commit; `tests/checks/test_mutate_script.py`
# fails until it is. (Phase 7 §3 recorded this as "mutate.py is unpinned";
# for this script it is now pinned.)
#
# Exit 0 = pass. At most eight lines to stdout; every pytest run's full output
# goes to the PID-suffixed log (the script also runs inside its own test suite,
# and a fixed name would truncate the outer run's log).
# Self-contained: no `source`, no includes; git, uv and coreutils
# (`timeout`, `sha256sum`) plus POSIX tools.
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"

LOG="${TMPDIR:-/tmp}/mutate.$$.log"
: >"$LOG"

MUTATE_PY="scripts/checks/mutate.py"
MUTATE_PY_SHA256="498c511ff432a0a00571e00a69c7d1fb03e9560a29ed1147729c75f1b8767467"

# How long one mutant may run before it is killed. A mutation can turn a loop
# guard into a non-terminating one (`and` -> `or`), and an unbounded child
# would then burn the node's whole 25 m timeout and be killed with the wrapper
# still holding its pipe. Three times the measured baseline is generous enough
# that a merely slower mutant is not mistaken for a hang.
MUTANT_TIMEOUT_FACTOR=3
MIN_MUTANT_TIMEOUT_S=120
BASELINE_TIMEOUT_S=900
KILL_GRACE_S=10
TIMEOUT_EXIT=124
SIGKILL_EXIT=137
TEST_FAILURE_EXIT=1

if [ -z "${WF_BASE_COMMIT:-}" ]; then
    printf 'FAIL mutate: WF_BASE_COMMIT is unset\n'
    exit 1
fi

# Provenance before execution, as everywhere else in §7.3.
actual_sha="$(sha256sum "$ROOT/$MUTATE_PY" | cut -d' ' -f1)"
if [ "$actual_sha" != "$MUTATE_PY_SHA256" ]; then
    printf 'FAIL mutate: %s is %s, not the pinned %s\n' \
        "$MUTATE_PY" "$actual_sha" "$MUTATE_PY_SHA256"
    exit 1
fi

# Before the baseline, so an unusable base costs milliseconds, not a suite run.
if ! git rev-parse --verify --quiet "${WF_BASE_COMMIT}^{commit}" >/dev/null; then
    printf 'FAIL mutate: WF_BASE_COMMIT %s is not a commit in this checkout\n' \
        "$WF_BASE_COMMIT"
    exit 1
fi

WORK="$(mktemp -d "${TMPDIR:-/tmp}/wf-mutate.$$.XXXXXX")"
trap 'rm -rf "$WORK"' EXIT

# One environment for every copy, so `uv run` resolves once for the baseline
# and the mutants reuse it. Set here rather than inherited by accident: without
# it each copy would build its own `.venv` and the check would spend more time
# installing than testing.
export UV_PROJECT_ENVIRONMENT="${UV_PROJECT_ENVIRONMENT:-$WORK/venv}"

# The unit subset: `bd` needs a real bd workspace, `live` spends vendor tokens
# and `proc` forks real children — none of which belongs inside a mutant run.
MARKERS='not bd and not live and not proc'

# `git archive` rather than `git worktree add`: this checkout is ITSELF a
# worktree of the real repository, so a nested `worktree add` would register
# under the real `.git/worktrees` and survive a timeout kill. A tar copy
# touches no git state at all.
copy_tree() {
    rm -rf "$1"
    mkdir -p "$1"
    git archive HEAD | tar -x -C "$1"
}

# $1 tree, $2 output file, $3 timeout seconds. Returns pytest's exit code, or
# `timeout`'s 124/137 — the caller decides what each code means.
run_subset() {
    local status=0
    (cd "$1" && timeout --kill-after="$KILL_GRACE_S" "$3" \
        uv run pytest -q -x -m "$MARKERS") >"$2" 2>&1 || status=$?
    return "$status"
}

# Step 2: a red baseline makes every mutant meaningless — `run_checks` runs
# every declared check and never short-circuits, so this cannot assume the
# gate went green first.
copy_tree "$WORK/baseline"
started=$SECONDS
baseline_status=0
run_subset "$WORK/baseline" "$WORK/baseline.out" "$BASELINE_TIMEOUT_S" ||
    baseline_status=$?
baseline_seconds=$((SECONDS - started))
cat "$WORK/baseline.out" >>"$LOG"
if [ "$baseline_status" -eq "$TIMEOUT_EXIT" ] ||
    [ "$baseline_status" -eq "$SIGKILL_EXIT" ]; then
    printf 'FAIL mutate: baseline did not finish in %ss (see %s)\n' \
        "$BASELINE_TIMEOUT_S" "$LOG"
    exit 1
fi
if [ "$baseline_status" -ne 0 ]; then
    printf 'FAIL mutate: baseline red before any mutant (see %s)\n' "$LOG"
    exit 1
fi

mutant_timeout=$((baseline_seconds * MUTANT_TIMEOUT_FACTOR))
if [ "$mutant_timeout" -lt "$MIN_MUTANT_TIMEOUT_S" ]; then
    mutant_timeout="$MIN_MUTANT_TIMEOUT_S"
fi
printf '=== baseline green in %ss; mutant timeout %ss\n' \
    "$baseline_seconds" "$mutant_timeout" >>"$LOG"

SITES="$WORK/sites.tsv"
if ! uv run python "$ROOT/$MUTATE_PY" sites "$WF_BASE_COMMIT" \
    >"$SITES" 2>>"$LOG"; then
    printf 'FAIL mutate: could not read the changed lines (see %s)\n' "$LOG"
    exit 1
fi

total=$(wc -l <"$SITES" | tr -d ' ')
# Zero sites used to be a bare PASS, and the first live round spent it: a diff
# that rewrote three modules in lines like `deviations = decision.deviations`
# planted no mutant and reported green (cr-o85.34.25). Zero mutants can only be
# a pass when the round added no executable Python line here at all.
if [ "$total" -eq 0 ]; then
    if ! changed="$(uv run python "$ROOT/$MUTATE_PY" changed "$WF_BASE_COMMIT" \
        2>>"$LOG")"; then
        printf 'FAIL mutate: could not read the changed lines (see %s)\n' "$LOG"
        exit 1
    fi
    if [ "$changed" -eq 0 ]; then
        printf 'PASS mutate: no executable Python line added under %s\n' \
            "workflow_interpreter/"
        exit 0
    fi
    printf 'FAIL mutate: no mutable token in %s changed lines under %s\n' \
        "$changed" "workflow_interpreter/"
    exit 1
fi

SURVIVORS="$WORK/survivors.txt"
: >"$SURVIVORS"
survivors=0
index=0
while [ "$index" -lt "$total" ]; do
    copy_tree "$WORK/mutant"
    if ! desc="$(uv run python "$ROOT/$MUTATE_PY" \
        apply "$SITES" "$index" "$WORK/mutant" 2>>"$LOG")"; then
        printf 'FAIL mutate: could not plant mutant %s of %s (see %s)\n' \
            "$((index + 1))" "$total" "$LOG"
        exit 1
    fi
    printf '=== mutant %s/%s: %s\n' "$((index + 1))" "$total" "$desc" >>"$LOG"
    status=0
    run_subset "$WORK/mutant" "$WORK/mutant.out" "$mutant_timeout" || status=$?
    cat "$WORK/mutant.out" >>"$LOG"
    if [ "$status" -eq 0 ]; then
        survivors=$((survivors + 1))
        printf '%s\n' "$desc" >>"$SURVIVORS"
        printf 'SURVIVED %s\n' "$desc" >>"$LOG"
    elif [ "$status" -eq "$TIMEOUT_EXIT" ] || [ "$status" -eq "$SIGKILL_EXIT" ]; then
        # A mutant that never terminates is still a mutant the suite noticed.
        printf 'KILLED %s by a timeout after %ss\n' "$desc" "$mutant_timeout" >>"$LOG"
    elif [ "$status" -eq "$TEST_FAILURE_EXIT" ]; then
        # The failing test's NAME, never a count: a name is the one thing a
        # reader can go and open.
        killer="$(grep -m1 '^FAILED ' "$WORK/mutant.out" | awk '{print $2}' || true)"
        if [ -z "$killer" ]; then
            killer="$(grep -m1 -E '^_{2,}.*_{2,}$' "$WORK/mutant.out" |
                sed -E 's/^_+ *//; s/ *_+$//' || true)"
        fi
        printf 'KILLED %s by %s\n' "$desc" "${killer:-an unnamed test}" >>"$LOG"
    else
        # pytest 2/3/4/5: it could not COLLECT or was misused. Nothing was
        # graded, so calling the mutant killed would claim evidence that the
        # run does not contain.
        printf 'FAIL mutate: pytest exited %s on mutant %s (see %s)\n' \
            "$status" "$desc" "$LOG"
        exit 1
    fi
    index=$((index + 1))
done

if [ "$survivors" -eq 0 ]; then
    printf 'PASS mutate: %s/%s mutants killed (see %s)\n' "$total" "$total" "$LOG"
    exit 0
fi

printf 'FAIL mutate: %s of %s mutants survived (see %s)\n' "$survivors" "$total" "$LOG"
head -6 "$SURVIVORS"
if [ "$survivors" -gt 6 ]; then
    printf '... and %s more (see %s)\n' "$((survivors - 6))" "$LOG"
fi
exit 1
