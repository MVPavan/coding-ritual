#!/usr/bin/env bash
# One run of the ruff-zero control loop: sense, control, actuate, check, gate, commit, push and open
# one pull request, in the order of .claude/skills/control-loop/references/run-script.md. Settings in
# loop.env beside this file; the charter is the loop bead's description.
#
# Usage: run.sh [--dry-run]
#   --dry-run  the preflight, sensor and controller run for real on this checkout's tracked files,
#              read only; every other step prints its command and runs nothing. Its outputs go to a
#              temporary folder removed on exit.
#
# Exit 0: the run finished, or stopped by design (another run active, a loop pull request open, the
# set point reached, nothing selectable, the target skipped, the rule-set pin changed), each noted on
# the loop bead. Exit 1: the run failed (noted on the loop bead and its task bead). Exit 2: the
# preflight refused or the usage was wrong. Exit 3: the change is held for a person (a manual check
# of the commit gate needs one): staged on its local branch in the run's worktree, unpushed, noted on
# both beads, the task bead left open.
#
# The grant (control-loop SKILL.md): this script writes only the run's task bead and the loop bead's
# notes, a worktree and a new branch from the base, one gated commit, an ordinary push of that branch
# and its pull request. It never merges, force-pushes, or changes a gate.
set -euo pipefail

HERE=$(cd "$(dirname "$0")" && pwd)
# shellcheck source=loop.env
. "$HERE/loop.env"
AGENT_TIMEOUT=${AGENT_TIMEOUT:-3600}
# A pull request listing that returns this many entries may have been cut short: the run stops.
PR_LIMIT=${PR_LIMIT:-1000}

DRY=0
case "${1:-}" in
  --dry-run) DRY=1 ;;
  "") ;;
  *) echo "usage: run.sh [--dry-run]" >&2; exit 2 ;;
esac

ROOT=$(git -C "$HERE" rev-parse --show-toplevel)
# Run folders live in the git-ignored scratch folder, not the git directory, which agents may refuse
# to edit inside.
STATE="$ROOT/scratchpad/loops/$LOOP_NAME"
RUN_ID=$(date -u +%Y%m%dT%H%M%SZ)
BRANCH="$BRANCH_PREFIX/$RUN_ID"
PY=python3
export PYTHONDONTWRITEBYTECODE=1
# Bead writes are signed by the loop, never by the git user, unless the caller names an actor.
export BEADS_ACTOR="${BEADS_ACTOR:-loop:$LOOP_NAME}"
# Checks in the run's worktree use the main checkout's environment instead of building their own.
if [ -x "$ROOT/.venv/bin/python" ]; then export UV_PROJECT_ENVIRONMENT="$ROOT/.venv"; fi

if [ "$DRY" = 1 ]; then
  RUN=$(mktemp -d "${TMPDIR:-/tmp}/ruff-zero-dry.XXXXXXXX")
  trap 'rm -rf -- "$RUN"' EXIT
else
  RUN="$STATE/runs/$RUN_ID"
fi
TREE="$STATE/runs/$RUN_ID/tree"
TREE_MADE=0
TASK=""
TARGET=""
ENDED=0

say() { printf '== %s\n' "$*"; }
show() {
  case $1 in bdr) set -- bd "${@:2}" ;; ghr) set -- gh "${@:2}" ;; esac
  printf '   $'; printf ' %q' "$@"; printf '\n'
}
# A write or a network call: printed always, run only in a real run.
would() { show "$@"; if [ "$DRY" = 0 ]; then "$@"; fi; }
bdr() { (cd "$ROOT" && bd "$@"); }
ghr() { (cd "$ROOT" && gh "$@"); }
jget() {
  "$PY" -c 'import json, sys
v = json.load(open(sys.argv[1]))
for k in sys.argv[2].split("."):
    v = v[k]
print(json.dumps(v) if isinstance(v, (dict, list)) else v)' "$1" "$2"
}

cleanup_tree() {
  if [ "$TREE_MADE" = 1 ] && [ -d "$TREE" ]; then
    git -c color.ui=never -C "$TREE" diff --no-color --no-ext-diff --no-textconv HEAD > "$RUN/tree.diff" || true
    git -C "$ROOT" worktree remove --force "$TREE"
    TREE_MADE=0
  fi
}
# An exit no step chose (a command failed under set -e): remove this run's worktree and say what
# is left for the owner.
if [ "$DRY" = 0 ]; then
  trap 'rc=$?; if [ "$ENDED" = 0 ] && [ "$rc" -ne 0 ]; then
    echo "run $RUN_ID stopped unexpectedly (exit $rc); task bead ${TASK:-none} left open; logs in $RUN" >&2
    cleanup_tree || true; fi' EXIT
fi
# A stop by design: note it on the loop bead (and close the task bead, when one exists) and exit 0.
stop() {
  say "stop: $1"
  if [ -n "$LOOP_BEAD" ]; then would bdr note "$LOOP_BEAD" "$1 (run $RUN_ID)"; fi
  if [ -n "$TASK" ]; then would bdr close "$TASK" --reason "$1"; fi
  cleanup_tree
  ENDED=1
  exit 0
}
# A failure: note the failed target, close the task bead, exit 1.
fail() {
  say "failed: $1"
  if [ -n "$LOOP_BEAD" ] && [ -n "$TARGET" ]; then
    would bdr note "$LOOP_BEAD" "$LOOP_NAME failed $TARGET $1 (run $RUN_ID)"
  elif [ -n "$LOOP_BEAD" ]; then
    would bdr note "$LOOP_BEAD" "$LOOP_NAME run $RUN_ID failed: $1"
  fi
  if [ -n "$TASK" ]; then would bdr close "$TASK" --reason "failed: $1"; fi
  cleanup_tree
  ENDED=1
  exit 1
}
# Held for a person: keep the staged change on its local branch in the worktree, unpushed; note
# both beads (a `skipped` note, so the controller passes over the file until it is reopened), leave
# the task bead open for the person, exit 3.
hold() {
  say "held: $1"
  would git -C "$TREE" switch -c "$BRANCH"
  would bdr note "$TASK" "held for a person: $1; staged on local branch $BRANCH in $TREE, not pushed (run $RUN_ID)"
  would bdr note "$LOOP_BEAD" "$LOOP_NAME skipped $TARGET held for a person: $1; local branch $BRANCH (run $RUN_ID)"
  ENDED=1
  exit 3
}

# 1. Preflight ----------------------------------------------------------------------------------
say "preflight"
problems=()
for v in LOOP_NAME BASE REMOTE BRANCH_PREFIX SCOPE_ROOTS RULESET_COUNT RULESET_SHA AGENT_BIN TURN_LIMIT GATE; do
  [ -n "${!v:-}" ] || problems+=("setting $v is empty")
done
for f in sensor.py controller.py checks.py actuator.md steering.md; do
  [ -f "$HERE/$f" ] || problems+=("missing $HERE/$f")
done
[ -f "$ROOT/$GATE" ] || problems+=("missing the commit gate $ROOT/$GATE")
for c in git bd gh uv flock timeout "$AGENT_BIN" "$PY"; do
  command -v "$c" >/dev/null 2>&1 || problems+=("command not found: $c")
done
LOOP_JSON=""
ISSUE_URL=""
LOOP_ISSUE=""
if [ -z "$LOOP_BEAD" ]; then
  problems+=("LOOP_BEAD is empty: create the loop's feature bead and set it in loop.env")
elif ! LOOP_JSON=$(bdr show "$LOOP_BEAD" --json 2>/dev/null); then
  problems+=("bd show $LOOP_BEAD failed")
else
  LOOP_ISSUE=$(printf '%s' "$LOOP_JSON" | "$PY" -c 'import json, re, sys
ref = json.load(sys.stdin)[0].get("external_ref") or ""
m = re.search(r"/issues/([0-9]+)$", ref)
print(m.group(1) if m else "")')
  [ -n "$LOOP_ISSUE" ] || problems+=("loop bead $LOOP_BEAD has no mirrored issue to reference")
fi
# The repository every pull request read and write names (--repo HOST/OWNER/REPO): the one the
# remote's fetch URL, its effective push URL (exactly one) and the loop issue all name, host included
# and on the scheme's default port, so the push cannot go anywhere the read and the pull request do
# not. The URLs themselves are never printed (they may hold credentials): checks.py reports counts
# and HOST/OWNER/REPO identities only.
FETCH_URL=$(git -C "$ROOT" remote get-url "$REMOTE" 2>/dev/null || true)
mapfile -t PUSH_URLS < <(git -C "$ROOT" remote get-url --push --all "$REMOTE" 2>/dev/null || true)
FORGE_ARGS=(forge --fetch "$FETCH_URL")
for u in "${PUSH_URLS[@]}"; do FORGE_ARGS+=(--push "$u"); done
if [ -n "$LOOP_JSON" ]; then
  ISSUE_URL=$(printf '%s' "$LOOP_JSON" | "$PY" -c 'import json, sys; print(json.load(sys.stdin)[0].get("external_ref") or "")')
  FORGE_ARGS+=(--issue "$ISSUE_URL")
fi
FORGE_REPO=""
if FORGE_OUT=$("$PY" "$HERE/checks.py" "${FORGE_ARGS[@]}"); then
  FORGE_REPO=$FORGE_OUT
else
  while IFS= read -r line; do problems+=("remote $REMOTE: $line"); done <<< "$FORGE_OUT"
fi
if [ "${#problems[@]}" -gt 0 ]; then
  printf '   problem: %s\n' "${problems[@]}"
  if [ "$DRY" = 0 ]; then echo "preflight refused; nothing done" >&2; ENDED=1; exit 2; fi
  echo "   (dry run: reported, not fatal)"
else
  echo "   ok: loop bead $LOOP_BEAD, issue #$LOOP_ISSUE in $FORGE_REPO, base $BASE"
fi

# 2. One run at a time --------------------------------------------------------------------------
# One lock per loop in the repository's common git dir, which every worktree of this clone shares,
# taken before the open pull request read and held until the script exits, through the creation.
say "lock"
LOCK="$(git -C "$ROOT" rev-parse --path-format=absolute --git-common-dir)/$LOOP_NAME.loop.lock"
if [ "$DRY" = 1 ]; then
  show flock -n "$LOCK"
else
  exec 9>"$LOCK"
  if ! flock -n 9; then echo "another $LOOP_NAME run holds $LOCK; nothing done"; ENDED=1; exit 0; fi
  mkdir -p "$RUN"
fi

# 3. One open pull request per loop -------------------------------------------------------------
say "open pull request bound (branches $BRANCH_PREFIX/*)"
OPEN=""
if [ "$DRY" = 1 ]; then
  show gh pr list --repo "${FORGE_REPO:-<host/owner/repo>}" --state open --json url,headRefName --limit "$PR_LIMIT"
else
  ghr pr list --repo "$FORGE_REPO" --state open --json url,headRefName --limit "$PR_LIMIT" > "$RUN/open-prs.json" \
    || fail "could not read the open pull requests of $FORGE_REPO"
  OPEN=$("$PY" "$HERE/checks.py" open-prs --prefix "$BRANCH_PREFIX" --limit "$PR_LIMIT" < "$RUN/open-prs.json") \
    || fail "the open pull request read of $FORGE_REPO may be incomplete (see $RUN/open-prs.json)"
fi
if [ -n "$OPEN" ]; then stop "$LOOP_NAME waiting: $OPEN is open"; fi

# 4. A fresh tree of the base -------------------------------------------------------------------
say "fresh tree of $REMOTE/$BASE"
would git -C "$ROOT" fetch "$REMOTE" "$BASE"
would git -C "$ROOT" worktree add --detach "$TREE" "$REMOTE/$BASE"
if [ "$DRY" = 1 ]; then SENSE_ROOT=$ROOT; else TREE_MADE=1; SENSE_ROOT=$TREE; fi

# 5. Sense ----------------------------------------------------------------------------------------
say "sense ($SENSE_ROOT)"
read -r -a ROOTS <<< "$SCOPE_ROOTS"
"$PY" "$HERE/sensor.py" --root "$SENSE_ROOT" --roots "${ROOTS[@]}" > "$RUN/sensor.json"
TOTAL=$(jget "$RUN/sensor.json" total)
RCOUNT=$(jget "$RUN/sensor.json" ruleset.count)
RSHA=$(jget "$RUN/sensor.json" ruleset.sha)
echo "   $(jget "$RUN/sensor.json" tool): $TOTAL finding(s) in $(jget "$RUN/sensor.json" files_scanned) file(s); rule set $RCOUNT ($RSHA)"
if [ "$RCOUNT" != "$RULESET_COUNT" ] || [ "$RSHA" != "$RULESET_SHA" ]; then
  stop "$LOOP_NAME paused: Ruff now enables $RCOUNT rules ($RSHA), pinned $RULESET_COUNT ($RULESET_SHA); re-pin in loop.env"
fi
if [ "$TOTAL" = 0 ]; then stop "$LOOP_NAME set point reached on $BASE: no Ruff finding in scope"; fi

# 6. Control --------------------------------------------------------------------------------------
say "control"
if [ -n "$LOOP_JSON" ]; then
  printf '%s' "$LOOP_JSON" | "$PY" -c 'import json, sys; print(json.load(sys.stdin)[0].get("notes") or "")' > "$RUN/notes.txt"
else
  : > "$RUN/notes.txt"
  echo "   no loop bead: no notes read"
fi
rc=0
"$PY" "$HERE/controller.py" --loop "$LOOP_NAME" --sensor "$RUN/sensor.json" --notes "$RUN/notes.txt" \
  --root "$SENSE_ROOT" > "$RUN/controller.json" || rc=$?
case $rc in
  0) ;;
  3) stop "$LOOP_NAME set point reached on $BASE: no Ruff finding in scope" ;;
  4) stop "$LOOP_NAME paused: $TOTAL finding(s) remain, all in files the notes exclude" ;;
  *) fail "controller exited $rc" ;;
esac
TARGET=$(jget "$RUN/controller.json" target)
COUNT=$(jget "$RUN/controller.json" count)
RULES=$(jget "$RUN/controller.json" rules)
mapfile -t TESTS < <(jget "$RUN/controller.json" tests | "$PY" -c 'import json, sys; print("\n".join(json.load(sys.stdin)))' | sed '/^$/d')
echo "   target $TARGET: $COUNT finding(s) $RULES; tests: ${TESTS[*]:-none}"

# 7. The run's task bead --------------------------------------------------------------------------
say "task bead"
TITLE="$LOOP_NAME: clear Ruff findings in $TARGET"
if [ "$DRY" = 1 ]; then
  show bd create --silent --type task --parent "${LOOP_BEAD:-<loop bead>}" --title "$TITLE" --description "..."
  show bd update "<task bead>" --claim
else
  TASK=$(bdr create --silent --type task --parent "$LOOP_BEAD" --title "$TITLE" \
    --description "Run $RUN_ID of the $LOOP_NAME loop ($LOOP_BEAD): clear the $COUNT Ruff finding(s) $RULES in $TARGET with no behaviour change, one pull request against $BASE.")
  bdr update "$TASK" --claim
fi

# 8. Actuate --------------------------------------------------------------------------------------
say "actuate"
{
  cat "$HERE/actuator.md"
  printf '\n## Selected work\n\nFile: `%s`\n\nFindings: %s (%s in total)\n\n' "$TARGET" "$RULES" "$COUNT"
  cat "$HERE/steering.md"
} > "$RUN/prompt.md"
# Every rule's findings with suppressions ignored, before the agent: afterwards no rule may rise and
# the selected rules must drop by the target's count.
IGNORE_NOQA=(uv run --frozen ruff check --no-cache --ignore-noqa --output-format json --exit-zero "$TARGET")
show "${IGNORE_NOQA[@]}"
if [ "$DRY" = 0 ]; then
  (cd "$TREE" && "${IGNORE_NOQA[@]}") > "$RUN/before-ignore-noqa.json" || fail "ruff --ignore-noqa failed before the change"
fi
PROMPT_ARG=$(cat "$RUN/prompt.md")
if [ "$DRY" = 1 ]; then
  PROMPT_ARG="<the prompt: actuator.md, the selected work, steering.md ($(wc -l < "$RUN/prompt.md") lines)>"
fi
# No settings file is loaded (user, project or local: --setting-sources with no source) and every
# hook is off (--settings disableAllHooks), because a hook runs outside the tool allowlist and can
# make network writes outside the grant. Every tool and path restriction is on this command line.
AGENT=(timeout "$AGENT_TIMEOUT" "$AGENT_BIN" -p "$PROMPT_ARG" --output-format json
  --permission-mode dontAsk --setting-sources "" --settings '{"disableAllHooks": true}'
  --strict-mcp-config --no-session-persistence --max-turns "$TURN_LIMIT")
if [ -n "$AGENT_MODEL" ]; then AGENT+=(--model "$AGENT_MODEL"); fi
if [ -n "$AGENT_BUDGET_USD" ]; then AGENT+=(--max-budget-usd "$AGENT_BUDGET_USD"); fi
AGENT+=(--tools Read Glob Grep Edit Bash
  --allowedTools Read Glob Grep "Edit(/$TREE/$TARGET)"
  "Bash(uv run --frozen ruff check --no-cache $TARGET)"
  "Bash(uv run --frozen ruff check --no-cache --fix $TARGET)"
  --disallowedTools "Bash(git add:*)" "Bash(git commit:*)" "Bash(git push:*)" NotebookEdit Task WebFetch WebSearch)
echo "   from $TREE:"
show "${AGENT[@]}"
if [ "$DRY" = 1 ]; then
  echo "   (dry run: the agent is not run; the prompt starts:)"
  sed -n '1,6p' "$RUN/prompt.md" | sed 's/^/   | /'
else
  (cd "$TREE" && "${AGENT[@]}") > "$RUN/agent.json" 2> "$RUN/agent.err" || true
fi

# 9. Check the change -----------------------------------------------------------------------------
say "check the change"
if [ "$DRY" = 1 ]; then
  echo "   (dry run) would require: agent output with no error and an OUTCOME line; changed paths only $TARGET;"
  echo "   then format it, no Ruff finding left in it; counted with suppressions ignored, no rule higher and"
  echo "   the selected rules lower by the target's count; and its tests passing:"
  show uv run --frozen ruff format --no-cache "$TARGET"
  show uv run --frozen ruff check --no-cache "$TARGET"
  show "${IGNORE_NOQA[@]}"
  show "$PY" "$HERE/checks.py" fixed --before before-ignore-noqa.json --after after-ignore-noqa.json --rules "$RULES" --count "$COUNT"
  if [ "${#TESTS[@]}" -gt 0 ]; then show uv run --frozen python -m pytest -q -p no:cacheprovider "${TESTS[@]}"; fi
else
  OUTCOME=$("$PY" -c 'import json, sys
try:
    d = json.load(open(sys.argv[1]))
except (OSError, ValueError):
    d = None
r = d.get("result") if isinstance(d, dict) else None
if not isinstance(r, str) or d.get("is_error"):
    print("error: no usable agent result")
else:
    print((r.strip().splitlines() or [""])[0])' "$RUN/agent.json")
  CHANGED=$(git -c color.ui=never -C "$TREE" status --porcelain=v1 -uall --no-renames | cut -c4-)
  OTHER=$(printf '%s\n' "$CHANGED" | grep -vxF -e "$TARGET" -e '' || true)
  if [ -n "$OTHER" ]; then fail "changed outside the target: ${OTHER//$'\n'/ }"; fi
  case $OUTCOME in
    "OUTCOME: fixed") ;;
    "OUTCOME: skipped"*)
      WHY=${OUTCOME#OUTCOME: skipped}; WHY=${WHY# - }
      stop "$LOOP_NAME skipped $TARGET ${WHY:-no reason given}" ;;
    *) fail "$OUTCOME (see $RUN/agent.json)" ;;
  esac
  [ -n "$CHANGED" ] || fail "reported fixed but changed nothing"
  (cd "$TREE" && uv run --frozen ruff format --no-cache "$TARGET") > "$RUN/format.out" 2>&1 || fail "ruff format failed"
  (cd "$TREE" && uv run --frozen ruff check --no-cache "$TARGET") > "$RUN/recheck.out" 2>&1 || fail "Ruff findings remain in the target"
  (cd "$TREE" && "${IGNORE_NOQA[@]}") > "$RUN/after-ignore-noqa.json" || fail "ruff --ignore-noqa failed after the change"
  "$PY" "$HERE/checks.py" fixed --before "$RUN/before-ignore-noqa.json" --after "$RUN/after-ignore-noqa.json" \
    --rules "$RULES" --count "$COUNT" > "$RUN/fixed.out" \
    || fail "not a real fix, counted with suppressions ignored: $(cat "$RUN/fixed.out")"
  TESTED="none found for this file"
  if [ "${#TESTS[@]}" -gt 0 ]; then
    (cd "$TREE" && uv run --frozen python -m pytest -q -p no:cacheprovider "${TESTS[@]}") > "$RUN/tests.out" 2>&1 \
      || fail "the target's tests fail (see $RUN/tests.out)"
    TESTED="$(tail -n 1 "$RUN/tests.out"): ${TESTS[*]}"
  fi
fi

# 10. Gate, manual checks, commit -----------------------------------------------------------------
# The gate runs on the staged tree; on its exit 0, every manual check it prints is done before the
# commit. The script does the diff-and-status check itself on the staged diff (only the target
# staged, nothing else changed, no added or changed line with a Ruff directive) and writes the
# result with the judged range; any other manual check needs a person, so the change is held
# (exit 3).
say "gate, manual checks, commit"
MSG="style($LOOP_NAME): clear Ruff findings in $TARGET"
would git -C "$TREE" add -- "$TARGET"
show python3 "$GATE"
RANGE="git diff --cached"
if [ "$DRY" = 0 ]; then
  rc=0
  (cd "$TREE" && "$PY" "$GATE") > "$RUN/gate.out" 2>&1 || rc=$?
  case $rc in
    0) ;;
    3) fail "the commit gate found no gate file (see $RUN/gate.out)" ;;
    *) fail "the commit gate exited $rc (see $RUN/gate.out)" ;;
  esac
  RANGE=$(sed -n 's/^judging [^:]*: //p' "$RUN/gate.out" | head -n 1)
  [ -n "$RANGE" ] || fail "the commit gate printed no judged range (see $RUN/gate.out)"
  mapfile -t MANUAL < <(sed -n '/^manual checks to do/,$p' "$RUN/gate.out" | sed -n 's/^  - \([^:]*\):.*/\1/p')
  STAGED=$(git -c color.ui=never -C "$TREE" diff --cached --no-color --no-ext-diff --name-only)
  [ "$STAGED" = "$TARGET" ] || fail "staged paths are not only the target: ${STAGED//$'\n'/ }"
  STATUS=$(git -c color.ui=never -C "$TREE" status --porcelain=v1 -uall)
  [ "$STATUS" = "M  $TARGET" ] || fail "the tree holds more than the staged target: ${STATUS//$'\n'/; }"
  # A plain patch: colour (color.ui=always) puts an escape code before the added-line marker, and an
  # external diff driver, a textconv filter or a binary diff attribute replaces the patch, any of which
  # could hide a directive; --text forces a line patch.
  git -c color.ui=never -C "$TREE" diff --cached --no-color --no-ext-diff --no-textconv --text > "$RUN/staged.diff"
  "$PY" "$HERE/checks.py" suppressions < "$RUN/staged.diff" > "$RUN/suppressions.out" \
    || fail "the change adds or changes a line with a Ruff directive: $(head -n 3 "$RUN/suppressions.out" | tr '\n' ' ')"
  HELD=()
  : > "$RUN/manual.txt"
  for m in "${MANUAL[@]}"; do
    case $m in
      "diff and status")
        printf 'diff and status: done by the run script on %s: staged paths only %s, nothing else changed, no added or changed line with a Ruff directive\n' \
          "$RANGE" "$TARGET" >> "$RUN/manual.txt" ;;
      *) HELD+=("$m") ;;
    esac
  done
  if [ "${#HELD[@]}" -gt 0 ]; then hold "manual check(s) needing a person: ${HELD[*]} (see $RUN/gate.out)"; fi
else
  echo "   (dry run) would require: gate exit 0; then, before the commit, the diff-and-status check on the"
  echo "   judged range: staged paths only $TARGET, nothing else changed, no added or changed Ruff directive line:"
  show git -c color.ui=never -C "$TREE" diff --cached --no-color --no-ext-diff --name-only
  show git -c color.ui=never -C "$TREE" status --porcelain=v1 -uall
  show git -c color.ui=never -C "$TREE" diff --cached --no-color --no-ext-diff --no-textconv --text ">" staged.diff
  show "$PY" "$HERE/checks.py" suppressions "<" staged.diff
  echo "   any other manual check printed: held for a person (local branch, unpushed, exit 3)"
fi
would git -C "$TREE" switch -c "$BRANCH"
would git -C "$TREE" commit -q -m "$MSG" -m "Control loop $LOOP_NAME (${LOOP_BEAD:-<loop bead>}), run $RUN_ID, task ${TASK:-<task bead>}."
SHA="<commit>"
if [ "$DRY" = 0 ]; then SHA=$(git -C "$TREE" rev-parse HEAD); fi
would bdr note "${TASK:-<task bead>}" "manual checks before commit $SHA, on $RANGE: diff and status done by the run script (run $RUN_ID)"

# 11. Build and check the body, push, open the pull request -----------------------------------------
# The body is built and checked before anything is pushed: the script writes its own Refs line, and
# an issue-closing keyword anywhere in the finished body (the agent's section included) fails the run.
say "body, push and pull request"
if [ "$DRY" = 0 ]; then
  {
    printf '## Ruff findings cleared in `%s`\n\n' "$TARGET"
    printf 'Run `%s` of the `%s` control loop: task bead %s, loop bead %s. One file per run; the\n' "$RUN_ID" "$LOOP_NAME" "$TASK" "$LOOP_BEAD"
    printf 'loop opens its next pull request after this one merges or closes.\n\n'
    printf '| | Before | After |\n|---|---|---|\n'
    printf '| Findings in this file | %s %s | 0 |\n' "$COUNT" "$RULES"
    printf '| Findings in scope | %s | %s |\n\n' "$TOTAL" "$((TOTAL - COUNT))"
    printf 'The run also formatted the file with `ruff format`, which the commit gate requires;\n'
    printf 'rerun it on the base file to separate the formatting from the fixes.\n\n'
    "$PY" -c 'import json, sys; print("\n".join(json.load(open(sys.argv[1]))["result"].strip().splitlines()[1:]).strip())' "$RUN/agent.json"
    printf '\n### Validation (run by the loop, not the agent)\n\n'
    printf -- '- `ruff check` on the file: no finding\n- %s\n- tests: %s\n- commit gate: passed (%s)\n\n' \
      "$(cat "$RUN/fixed.out")" "$TESTED" "$(grep -m1 '^commit gate:' "$RUN/gate.out" || echo 'see the run log')"
    printf '### Manual checks done before the commit %s\n\n' "$SHA"
    sed 's/^/- /' "$RUN/manual.txt"
    printf '\nRefs #%s\n' "$LOOP_ISSUE"
  } > "$RUN/pr-body.md"
  "$PY" "$HERE/checks.py" body < "$RUN/pr-body.md" > "$RUN/body-check.out" \
    || fail "the pull request body holds an issue-closing keyword: $(head -n 3 "$RUN/body-check.out" | tr '\n' ' ')"
else
  show "$PY" "$HERE/checks.py" body "<" pr-body.md
fi
if [ "$DRY" = 0 ]; then
  # The push destination again, just before the push: the same one repository preflight found.
  mapfile -t PUSH_NOW < <(git -C "$TREE" remote get-url --push --all "$REMOTE")
  NOW_ARGS=(forge --fetch "$(git -C "$TREE" remote get-url "$REMOTE")" --issue "$ISSUE_URL")
  for u in "${PUSH_NOW[@]}"; do NOW_ARGS+=(--push "$u"); done
  NOW=$("$PY" "$HERE/checks.py" "${NOW_ARGS[@]}") || fail "the push destination changed since preflight: ${NOW//$'\n'/; }"
  [ "$NOW" = "$FORGE_REPO" ] || fail "the push destination is now $NOW, not $FORGE_REPO"
fi
would git -C "$TREE" push -u "$REMOTE" "$BRANCH"
if [ "$DRY" = 0 ]; then
  URL=$(cd "$TREE" && gh pr create --repo "$FORGE_REPO" --base "$BASE" --head "$BRANCH" --title "$MSG" --body-file "$RUN/pr-body.md")
  GOT=$(ghr pr view "$URL" --repo "$FORGE_REPO" --json baseRefName -q .baseRefName)
  if [ "$GOT" != "$BASE" ]; then fail "pull request $URL opened on base $GOT, not $BASE"; fi
else
  show gh pr create --repo "${FORGE_REPO:-<host/owner/repo>}" --base "$BASE" --head "$BRANCH" --title "$MSG" --body-file "<pr-body.md>"
  show gh pr view "<url>" --repo "${FORGE_REPO:-<host/owner/repo>}" --json baseRefName -q .baseRefName
  URL="<pull request>"
fi

# 12. Record --------------------------------------------------------------------------------------
say "record"
would bdr note "${TASK:-<task bead>}" "pull request $URL, commit $SHA, run $RUN_ID"
would bdr note "${LOOP_BEAD:-<loop bead>}" "$LOOP_NAME done $TARGET $URL"
if [ "$DRY" = 0 ]; then
  git -C "$ROOT" worktree remove "$TREE"
  TREE_MADE=0
else
  show git -C "$ROOT" worktree remove "$TREE"
fi
ENDED=1
say "done: $TARGET -> $URL"
