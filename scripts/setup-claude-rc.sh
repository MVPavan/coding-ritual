#!/usr/bin/env bash
#
# setup-claude-rc.sh — first-time setup for resilient `claude remote-control`
# sessions. Thin wrapper around claude-rc.sh (the ongoing manager).
#
# After this, manage sessions with:
#   ./claude-rc.sh status            # see all sessions
#   ./claude-rc.sh add <path>        # add a project
#   ./claude-rc.sh remove <name>     # remove a project
#
# Re-running this is safe: it never restarts already-running sessions; it only
# adds missing default projects and flags any running session not in the list.

set -euo pipefail
exec "$(cd "$(dirname "$0")" && pwd)/claude-rc.sh" setup "$@"
