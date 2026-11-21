#!/usr/bin/env bash
# SessionStart hook: the Beads -> GitHub mirror's session start (`bead-mirror.py session`).
#
# In the clone holding the mirror's writer switch it prints a short digest summary and
# starts the background run detached; anywhere else it prints nothing and creates
# nothing. It makes no network call, never waits on the background run, and never
# fails the session: every path exits 0. The command enforces its own short deadline
# (no `timeout` tool needed); `timeout`, where installed, is a second bound.

# Git's repository selectors would point the run at another checkout than this one.
unset GIT_DIR GIT_WORK_TREE GIT_COMMON_DIR GIT_INDEX_FILE
here=$(cd "$(dirname "${BASH_SOURCE[0]}")" 2>/dev/null && pwd) || exit 0
top=$(cd "$here/../.." 2>/dev/null && pwd) || exit 0
cmd="$top/.claude/hooks/bead-mirror.py"
[ -f "$cmd" ] || exit 0
command -v python3 >/dev/null 2>&1 || exit 0
cd "$top" || exit 0
if command -v timeout >/dev/null 2>&1; then
  timeout 5 python3 "$cmd" session </dev/null 2>/dev/null
else
  python3 "$cmd" session </dev/null 2>/dev/null
fi
exit 0
