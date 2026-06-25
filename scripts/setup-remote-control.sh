#!/usr/bin/env bash
#
# setup-remote-control.sh — first-time setup for resilient remote-control
# sessions: one Claude session per default project + one global Codex daemon.
# Thin wrapper around remote-control.sh (the ongoing manager).
#
# After this, manage sessions with:
#   ./remote-control.sh status                # see all sessions (Claude + Codex)
#   ./remote-control.sh add <path>            # add a Claude project
#   ./remote-control.sh remove <name|codex>   # remove a session or the Codex daemon
#
# Re-running this is safe: it never restarts already-running sessions; it only
# adds missing default projects, starts Codex if down, and flags orphans.

set -euo pipefail
exec "$(cd "$(dirname "$0")" && pwd)/remote-control.sh" setup "$@"
