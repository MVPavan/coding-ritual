#!/usr/bin/env bash
#
# claude-rc.sh — manage resilient `claude remote-control` sessions as systemd
#                user services. One service per project, session "<name>-rc".
#
# Source of truth: env files in ~/.config/claude-rc/*.env (one per project).
# Each service auto-recovers from the ~10-min network timeout, crashes,
# logout, and reboots (Restart=always + linger + a Windows logon task).
#
# Usage:
#   claude-rc.sh setup              First-time system setup + add default projects
#   claude-rc.sh add <path>         Add ONE project (no-op if already present/running)
#   claude-rc.sh remove <name|path> Stop, disable and forget ONE project
#   claude-rc.sh status             Table of all managed sessions
#   claude-rc.sh list              List configured projects
#   claude-rc.sh logs <name> [-f]   Show (or follow) a session's log
#   claude-rc.sh pair <name>        Print the pairing/connect URL from the log
#   claude-rc.sh restart <name|all> Restart one session (or all)
#   claude-rc.sh help               This help
#
# Re-running `setup` never restarts already-running sessions; it only adds
# missing default projects and warns about any running session not in the list.

set -euo pipefail

CFG_DIR="${HOME}/.config/claude-rc"
UNIT_DIR="${HOME}/.config/systemd/user"
UNIT_FILE="${UNIT_DIR}/claude-rc@.service"
RC_SUFFIX="-rc"
WIN_TASK="Start-WSL-ClaudeRC"

# Default projects used by `setup` (edit to taste).
DEFAULT_PROJECTS=(
  "/data/codes/coding-ritual"
  "/data/codes/bodha"
  "/data/codes/multibaggers"
  "/data/codes/orchestrators"
)

# --- output helpers --------------------------------------------------------
log()  { printf '\033[1;34m==>\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33m[warn]\033[0m %s\n' "$*"; }
err()  { printf '\033[1;31m[err]\033[0m %s\n' "$*" >&2; }

uc() { systemctl --user "$@"; }                     # user systemctl shorthand
sanitize() { printf '%s' "$1" | tr -c 'A-Za-z0-9_-' '_'; }

# Map an argument (path, "name", or "name-rc") to a systemd instance key.
resolve_inst() {
  local arg="$1"
  if [ -d "$arg" ]; then
    sanitize "$(basename "$arg")"
  else
    arg="${arg%${RC_SUFFIX}}"      # tolerate a trailing -rc
    sanitize "$arg"
  fi
}

require_systemd() {
  if ! ps -p 1 -o comm= 2>/dev/null | grep -q systemd; then
    err "systemd is not running as PID 1. Run '$0 setup' first (it enables systemd in WSL)."
    exit 1
  fi
}

ensure_claude() {
  if ! bash -lc 'command -v claude >/dev/null 2>&1'; then
    err "'claude' not found on your login PATH. Install/login to Claude Code first."
    exit 1
  fi
}

# Enable systemd in WSL if it is not the init system. Exits with instructions
# the first time, because the distro must be restarted to pick it up.
ensure_systemd_or_bootstrap() {
  if ps -p 1 -o comm= 2>/dev/null | grep -q systemd; then
    return
  fi
  warn "systemd is not running as PID 1."
  if ! grep -q 'systemd=true' /etc/wsl.conf 2>/dev/null; then
    log "Enabling systemd in /etc/wsl.conf (sudo)..."
    printf '[boot]\nsystemd=true\n' | sudo tee -a /etc/wsl.conf >/dev/null
  fi
  err "systemd is now enabled but not active yet."
  err "Run 'wsl --shutdown' in PowerShell, reopen WSL, then re-run: $0 setup"
  exit 1
}

write_unit() {
  mkdir -p "$UNIT_DIR" "$CFG_DIR"
  cat > "$UNIT_FILE" <<'EOF'
[Unit]
Description=Claude remote-control: %i
StartLimitIntervalSec=0

[Service]
Type=simple
EnvironmentFile=%h/.config/claude-rc/%i.env
ExecStart=/bin/bash -lc 'cd "$PROJECT_DIR" && exec claude remote-control --name "$RC_NAME"'
Restart=always
RestartSec=15

[Install]
WantedBy=default.target
EOF
  uc daemon-reload
}

ensure_linger() {
  if [ "$(loginctl show-user "$USER" -p Linger --value 2>/dev/null || true)" = "yes" ]; then
    return
  fi
  log "Enabling linger so sessions survive logout and start on boot (sudo)..."
  sudo loginctl enable-linger "$USER"
}

ensure_windows_task() {
  if ! command -v schtasks.exe >/dev/null 2>&1 || [ -z "${WSL_DISTRO_NAME:-}" ]; then
    warn "schtasks.exe not reachable. To recover after a Windows reboot, run in PowerShell:"
    echo "    schtasks /Create /TN \"${WIN_TASK}\" /SC ONLOGON /RL LIMITED /F /TR \"wsl.exe -d <Distro> -u ${USER} true\""
    return
  fi
  if schtasks.exe /Query /TN "$WIN_TASK" >/dev/null 2>&1; then
    log "Windows logon task '${WIN_TASK}' already present."
    return
  fi
  log "Creating Windows logon task to auto-start WSL (distro: ${WSL_DISTRO_NAME})..."
  if schtasks.exe /Create /TN "$WIN_TASK" /SC ONLOGON /RL LIMITED /F \
       /TR "wsl.exe -d ${WSL_DISTRO_NAME} -u ${USER} true" >/dev/null 2>&1; then
    log "Windows logon task '${WIN_TASK}' created."
  else
    warn "Could not create the Windows task automatically. Run this in PowerShell:"
    echo "    schtasks /Create /TN \"${WIN_TASK}\" /SC ONLOGON /RL LIMITED /F /TR \"wsl.exe -d ${WSL_DISTRO_NAME} -u ${USER} true\""
  fi
}

# Add one project. Idempotent and NON-disruptive: an already-configured,
# running session is left exactly as-is (never restarted).
add_project() {
  local dir="$1"
  if [ ! -d "$dir" ]; then
    warn "Directory not found, skipping: $dir"
    return
  fi
  local base inst envf
  base="$(basename "$dir")"
  inst="$(sanitize "$base")"
  envf="${CFG_DIR}/${inst}.env"

  if [ -f "$envf" ]; then
    local cur
    cur="$(grep -m1 '^PROJECT_DIR=' "$envf" | cut -d= -f2- || true)"
    if [ "$cur" != "$dir" ]; then
      warn "Instance '${inst}' already maps to '${cur}', not '${dir}'. Skipping (name collision)."
      return
    fi
    if uc is-active --quiet "claude-rc@${inst}"; then
      log "unchanged (left running): ${base}${RC_SUFFIX}"
    else
      uc enable --now "claude-rc@${inst}" >/dev/null 2>&1 || uc start "claude-rc@${inst}"
      log "started: ${base}${RC_SUFFIX}"
    fi
    return
  fi

  printf 'PROJECT_DIR=%s\nRC_NAME=%s\n' "$dir" "${base}${RC_SUFFIX}" > "$envf"
  uc daemon-reload
  uc enable --now "claude-rc@${inst}"
  log "added + started: ${base}${RC_SUFFIX}"
}

remove_project() {
  local arg="$1" inst envf
  inst="$(resolve_inst "$arg")"
  envf="${CFG_DIR}/${inst}.env"
  if [ ! -f "$envf" ] && ! uc list-unit-files "claude-rc@${inst}.service" --no-legend --plain >/dev/null 2>&1; then
    warn "No managed session matches '${arg}' (instance '${inst}'). Nothing to remove."
    return
  fi
  log "Removing session: ${inst}${RC_SUFFIX}"
  uc disable --now "claude-rc@${inst}" >/dev/null 2>&1 || true
  rm -f "$envf"
  uc reset-failed "claude-rc@${inst}" >/dev/null 2>&1 || true
  log "removed: ${inst}${RC_SUFFIX}"
}

list_orphans() {
  local active_units u i
  active_units="$(uc list-units 'claude-rc@*' --all --no-legend --plain 2>/dev/null | awk '{print $1}' || true)"
  [ -z "$active_units" ] && return 0
  while read -r u; do
    [ -z "$u" ] && continue
    i="${u#claude-rc@}"; i="${i%.service}"
    if [ ! -f "${CFG_DIR}/${i}.env" ]; then
      warn "Running but not in your list (orphan): ${i}${RC_SUFFIX}  ->  remove with: $0 remove ${i}"
    fi
  done <<<"$active_units"
  return 0
}

cmd_status() {
  require_systemd
  printf '%-24s %-20s %-9s %s\n' "SESSION" "STATE" "RESTARTS" "PROJECT DIR"
  printf '%-24s %-20s %-9s %s\n' "-------" "-----" "--------" "-----------"
  local envf inst dir rcname vals state sub nr found=0
  shopt -s nullglob
  for envf in "$CFG_DIR"/*.env; do
    found=1
    inst="$(basename "$envf" .env)"
    dir="$(grep -m1 '^PROJECT_DIR=' "$envf" | cut -d= -f2- || true)"
    rcname="$(grep -m1 '^RC_NAME=' "$envf" | cut -d= -f2- || true)"
    vals="$(uc show "claude-rc@${inst}" -p ActiveState -p SubState -p NRestarts --value 2>/dev/null | paste -sd'|' - || true)"
    state="${vals%%|*}"; vals="${vals#*|}"; sub="${vals%%|*}"; nr="${vals##*|}"
    printf '%-24s %-20s %-9s %s\n' "${rcname:-$inst}" "${state:-?} (${sub:-?})" "${nr:-0}" "${dir:-?}"
  done
  shopt -u nullglob
  if [ "$found" -eq 0 ]; then
    warn "No projects configured. Add one with: $0 add <path>"
  fi
  echo
  list_orphans
}

cmd_list() {
  shopt -s nullglob
  local envf inst dir found=0
  for envf in "$CFG_DIR"/*.env; do
    found=1
    inst="$(basename "$envf" .env)"
    dir="$(grep -m1 '^PROJECT_DIR=' "$envf" | cut -d= -f2- || true)"
    printf '%-24s %s\n' "${inst}${RC_SUFFIX}" "$dir"
  done
  shopt -u nullglob
  if [ "$found" -eq 0 ]; then warn "No projects configured."; fi
}

cmd_logs() {
  require_systemd
  local arg="${1:-}"; shift || true
  if [ -z "$arg" ]; then err "Usage: $0 logs <name> [-f]"; exit 1; fi
  local inst; inst="$(resolve_inst "$arg")"
  if [ "${1:-}" = "-f" ]; then
    journalctl --user -u "claude-rc@${inst}" -f
  else
    journalctl --user -u "claude-rc@${inst}" -n 100 --no-pager
  fi
}

cmd_pair() {
  require_systemd
  local arg="${1:-}"
  if [ -z "$arg" ]; then err "Usage: $0 pair <name>"; exit 1; fi
  local inst url
  inst="$(resolve_inst "$arg")"
  url="$(journalctl --user -u "claude-rc@${inst}" -n 300 --no-pager 2>/dev/null \
         | grep -oE 'https?://[^ ]+' | tail -n1 || true)"
  if [ -n "$url" ]; then
    log "Pairing/connect URL for ${inst}${RC_SUFFIX}:"
    echo "    $url"
  else
    warn "No URL found in recent logs. View full log: $0 logs ${inst}"
  fi
}

cmd_restart() {
  require_systemd
  local arg="${1:-}"
  if [ -z "$arg" ]; then err "Usage: $0 restart <name|all>"; exit 1; fi
  if [ "$arg" = "all" ] || [ "$arg" = "--all" ]; then
    shopt -s nullglob
    local envf inst
    for envf in "$CFG_DIR"/*.env; do
      inst="$(basename "$envf" .env)"
      uc restart "claude-rc@${inst}"
      log "restarted: ${inst}${RC_SUFFIX}"
    done
    shopt -u nullglob
  else
    local inst; inst="$(resolve_inst "$arg")"
    uc restart "claude-rc@${inst}"
    log "restarted: ${inst}${RC_SUFFIX}"
  fi
}

cmd_add() {
  require_systemd
  ensure_claude
  local arg="${1:-}"
  if [ -z "$arg" ]; then err "Usage: $0 add <path>"; exit 1; fi
  [ -f "$UNIT_FILE" ] || write_unit
  ensure_linger
  add_project "$arg"
}

cmd_remove() {
  require_systemd
  local arg="${1:-}"
  if [ -z "$arg" ]; then err "Usage: $0 remove <name|path>"; exit 1; fi
  remove_project "$arg"
}

cmd_setup() {
  ensure_systemd_or_bootstrap
  ensure_claude
  write_unit
  log "Wrote systemd template: $UNIT_FILE"
  ensure_linger
  ensure_windows_task
  local d
  for d in "${DEFAULT_PROJECTS[@]}"; do
    add_project "$d"
  done
  echo
  cmd_status
  echo
  log "Pair each session once. Get its URL with:  $0 pair <name>"
  log "Done."
}

usage() {
  awk 'NR>1 && /^#/{sub(/^# ?/,""); print; next} NR>1 && !/^#/{exit}' "$0"
}

main() {
  local cmd="${1:-help}"; shift || true
  case "$cmd" in
    setup)         cmd_setup "$@" ;;
    add)           cmd_add "$@" ;;
    remove|rm)     cmd_remove "$@" ;;
    status|st)     cmd_status "$@" ;;
    list|ls)       cmd_list "$@" ;;
    logs|log)      cmd_logs "$@" ;;
    pair|url)      cmd_pair "$@" ;;
    restart)       cmd_restart "$@" ;;
    help|-h|--help) usage ;;
    *) err "Unknown command: $cmd"; echo; usage; exit 1 ;;
  esac
}

main "$@"
