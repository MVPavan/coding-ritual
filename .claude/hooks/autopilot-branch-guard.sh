#!/bin/bash
# PreToolUse(Edit|Write|MultiEdit|NotebookEdit) guard for Autopilot-full runs.
# Refuses an edit only while a run marker exists and the checkout the edited file lands in is on the
# repository's default branch. Every other edit passes, so ordinary sessions are unaffected.
# - The marker is the file `autopilot-run` in the repository's common git dir
#   (`git rev-parse --git-common-dir`), so every worktree of the repository sees the same marker. The
#   Autopilot-full playbook creates it at intake and removes it at exit, both through
#   `autopilot-full/run_marker.py`, which removes only a marker that holds the run's own id.
# - The checkout is the one holding the edited file's folder (its nearest existing ancestor for a new
#   file), not the session's working directory. A detached HEAD is no branch and passes.
# - The default branch is origin/HEAD's target; without origin/HEAD, both `main` and `master`.
# - The payload is read with jq, else python3; with neither, any edit is refused while the repository
#   of the hook's working directory or of $CLAUDE_PROJECT_DIR holds a marker. Limit: a marked
#   repository that is neither is then not seen.
# Limits: writes made through Bash (redirection, tee, sed -i, scripts) are not covered; a file outside
# any repository, or a git error while reading the checkout, passes.
set -euo pipefail

INPUT=$(cat)

# Read the payload with a JSON decoder: jq, else Python's json module. With neither, the edited path
# is unknown, so refuse whenever the session's own repository holds a run marker.
if command -v jq >/dev/null 2>&1; then
  FILE_PATH=$(jq -r '.tool_input.file_path // .tool_input.notebook_path // empty' <<<"$INPUT" 2>/dev/null) || exit 0
  CWD_IN=$(jq -r '.cwd // empty' <<<"$INPUT" 2>/dev/null) || CWD_IN=
elif command -v python3 >/dev/null 2>&1; then
  FIELD='import json, sys
d = json.loads(sys.stdin.read())
t = d.get("tool_input") or {}
v = {"path": t.get("file_path") or t.get("notebook_path"), "cwd": d.get("cwd")}[sys.argv[1]]
sys.stdout.write(v if isinstance(v, str) else "")'
  FILE_PATH=$(python3 -I -c "$FIELD" path <<<"$INPUT" 2>/dev/null) || exit 0
  CWD_IN=$(python3 -I -c "$FIELD" cwd <<<"$INPUT" 2>/dev/null) || CWD_IN=
else
  for D in "$PWD" "${CLAUDE_PROJECT_DIR:-}"; do
    [ -n "$D" ] && [ -d "$D" ] || continue
    COMMON=$(git -C "$D" rev-parse --path-format=absolute --git-common-dir 2>/dev/null) || continue
    if [ -e "$COMMON/autopilot-run" ]; then
      echo "BLOCKED: an Autopilot-full run is active (run marker: $COMMON/autopilot-run) and neither jq nor python3 is installed to read which file this edit targets. Install one of them, or make the edit through the feature's worktree by other means. If no run is active (a crashed run left the marker behind), delete $COMMON/autopilot-run and retry." >&2
      exit 2
    fi
  done
  exit 0
fi

[ -z "${FILE_PATH:-}" ] && exit 0
case "$FILE_PATH" in
  /*) ;;
  *) FILE_PATH="${CWD_IN:-$PWD}/$FILE_PATH" ;;
esac

DIR=$(dirname -- "$FILE_PATH")
while [ ! -d "$DIR" ]; do DIR=$(dirname -- "$DIR"); done

COMMON=$(git -C "$DIR" rev-parse --path-format=absolute --git-common-dir 2>/dev/null) || exit 0
MARKER="$COMMON/autopilot-run"
[ -e "$MARKER" ] || exit 0

BRANCH=$(git -C "$DIR" symbolic-ref --quiet --short HEAD 2>/dev/null) || exit 0
DEFAULT=$(git -C "$DIR" symbolic-ref --quiet --short refs/remotes/origin/HEAD 2>/dev/null || true)
if [ -n "$DEFAULT" ]; then
  PROTECTED=("${DEFAULT#origin/}")
else
  PROTECTED=(main master)
fi

for name in "${PROTECTED[@]}"; do
  if [ "$BRANCH" = "$name" ]; then
    TOP=$(git -C "$DIR" rev-parse --show-toplevel 2>/dev/null || echo "$DIR")
    echo "BLOCKED: an Autopilot-full run is active in this repository (run marker: $MARKER) and the checkout $TOP is on its default branch '$BRANCH'. Make the edit on the feature's own branch, in its worktree. If no run is active (a crashed run left the marker behind), delete $MARKER and retry." >&2
    exit 2
  fi
done

exit 0
