#!/usr/bin/env bash
# Run one candidate: a fresh copy of a sandbox template, one headless Claude
# Code session in it inside a bwrap boundary, one log per run named by its run ID.
#
# usage: run.sh --template <git repo> --runs <dir> --logs <dir> --id <run id>
#               --prompt <file> --model <model> --permission-mode <mode>
#               --auth-env <NAME> [--auth-env <NAME>]...
#               [--max-turns N] [--timeout seconds] [--path-prepend <dir>]
#
# Inside, every run looks the same: the copy is writable at /home/user/project,
# which is the working directory, under an empty home. /usr/ and the /etc/ files
# that TLS needs are read-only. The candidate cannot see the host's home, other
# runs, the logs or the template. Its environment is HOME, PATH, a locale,
# DISABLE_AUTOUPDATER, the proxy settings below and each --auth-env, so nothing from
# the parent session changes what it discovers. Its Git has no identity: a template
# whose task commits sets one in its .git/config. One leak remains:
# /proc/self/mountinfo names the host paths of the copy, the CLI and the proxy's
# private directory, so the sandbox path may not hold a word that reveals the
# experiment. Their contents stay out of reach.
#
# The network is the candidate's own: a loopback, no host loopback, no host abstract
# sockets and no route out. The only way out is one Unix socket to egress.py's proxy,
# which runs here on the host and tunnels to api.anthropic.com:443 and nothing else,
# with TLS end to end. Inside, a forwarder gives that socket a port, and HTTPS_PROXY
# points at it. A template carries its own dependencies. Every decision is in
# <logs>/<id>.egress. Revisit the one allowed host when a task needs another.
# /usr/bin/python3 runs both halves and the script refuses without it.
#
# The namespace does not isolate every socket family (AF_VSOCK reaches the Windows
# host on WSL2), so a seccomp filter from `egress.py filter` holds in both boundaries:
# socket() takes AF_UNIX, AF_INET, AF_INET6 and AF_NETLINK only, io_uring_setup and
# other architectures fail, and a machine without its numbers is refused. The boundary
# sets no resource limits (connections, threads, log or disk), so a run can exhaust
# them; revisit when runs are concurrent or adversarial. Kernel exploits are out of scope.
#
# --auth-env names a variable in the caller's environment, which must be
# non-empty; repeat it for more than one. The value is inherited, never put on a
# command line. The sources are ANTHROPIC_API_KEY and the token from `claude
# setup-token` (Claude Code: CLAUDE_CODE_OAUTH_TOKEN). Never bind or copy a
# credentials file: refreshing an OAuth token from a copy can invalidate the
# original. The candidate can read its token, so use one that can be revoked.
#
# --path-prepend goes first on the candidate's PATH, read-only at its own host
# path, so it may not hold such a word either. A venv's bin brings its venv. It has
# to work with only /usr/ visible, so make a venv from /usr/bin/python3.
#
# bwrap is required and the script refuses without it: Linux only. Revisit when a
# candidate has to run on another OS.
#
# Logs go to <logs>/<id>.{jsonl,err,diff,egress} and must sit outside <runs>. The diff is
# GNU diff over the files, inside a boundary too, and never the copy's Git, whose
# filters, hooks and diff programs the candidate controls. It compares with the
# template's files without .git, so commits, new and ignored files all show as
# changes; a failure is recorded in the file and leaves the exit code alone. The
# script exits with the session's exit code.
set -u

die() { echo "run.sh: $1" >&2; exit 2; }

refuse_revealing() {
  if printf '%s' "$1" | tr '[:upper:]' '[:lower:]' | tr -c 'a-z0-9' '\n' |
    grep -Eqx '(eval|test|judge|experiment|rubric|score|compare|benchmark|candidate|arena)s?'; then
    die "path reveals the experiment: $1"
  fi
}

private='' proxy_pid=''
cleanup() {
  if [ -n "$proxy_pid" ]; then
    kill "$proxy_pid" 2>/dev/null
    wait "$proxy_pid" 2>/dev/null
  fi
  if [ -n "$private" ]; then
    rm -f "$private/proxy.sock" "$private/egress.py" "$private/session" "$private/filter"
    rmdir "$private"
  fi
}
# The session and the diff run behind a `wait`, so a signal lands now and not at
# their timeout. The recorded PID can be stale, so only a `timeout` is signalled.
stop_session() {
  local pid
  pid=$(cat "$private/session" 2>/dev/null) || return 0
  [ "$(cat "/proc/$pid/comm" 2>/dev/null)" != timeout ] || kill "$pid" 2>/dev/null
}
trap cleanup EXIT
trap 'stop_session; exit 129' HUP
trap 'stop_session; exit 130' INT
trap 'stop_session; exit 143' TERM

template='' runs='' logs='' id='' prompt='' model='' permission_mode=''
max_turns=15 limit=900 path_prepend='' auth_envs=()
while [ $# -gt 0 ]; do
  [ $# -ge 2 ] || die "$1 needs a value"
  case $1 in
    --template) template=$2 ;;
    --runs) runs=$2 ;;
    --logs) logs=$2 ;;
    --id) id=$2 ;;
    --prompt) prompt=$2 ;;
    --model) model=$2 ;;
    --permission-mode) permission_mode=$2 ;;
    --auth-env) auth_envs+=("$2") ;;
    --max-turns) max_turns=$2 ;;
    --timeout) limit=$2 ;;
    --path-prepend) path_prepend=$2 ;;
    *) die "unknown option: $1" ;;
  esac
  shift 2
done

for pair in "--template:$template" "--runs:$runs" "--logs:$logs" "--id:$id" \
  "--prompt:$prompt" "--model:$model" "--permission-mode:$permission_mode"; do
  [ -n "${pair#*:}" ] || die "${pair%%:*} is required"
done
[ "${#auth_envs[@]}" -gt 0 ] || die "--auth-env is required"
for name in "${auth_envs[@]}"; do
  printf '%s' "$name" | grep -Eq '^[A-Za-z_][A-Za-z0-9_]*$' || die "bad --auth-env name: $name"
  [ -n "${!name:-}" ] || die "--auth-env $name is unset or empty"
done
printf '%s' "$id" | grep -Eq '^[A-Za-z0-9][A-Za-z0-9._-]*$' || die "bad run id: $id"
[ -d "$template/.git" ] || die "template is not a git repository: $template"
[ -s "$prompt" ] || die "prompt is missing or empty: $prompt"

bwrap=$(command -v bwrap) || die "bwrap is required and was not found"
timeout=$(command -v timeout) || die "timeout is required and was not found"
claude=$(command -v claude) || die "claude was not found on PATH"
claude=$(readlink -f "$claude") || die "cannot resolve claude"
python=/usr/bin/python3
[ -x "$python" ] || die "$python is required and was not found"
egress=$(dirname "$(realpath "${BASH_SOURCE[0]}")")/egress.py
[ -f "$egress" ] || die "egress.py was not found beside the script: $egress"

inner_path=/opt/cli:/usr/local/bin:/usr/bin:/bin
prepend_bind=()
if [ -n "$path_prepend" ]; then
  path_prepend=$(realpath "$path_prepend") || die "cannot resolve --path-prepend"
  [ -d "$path_prepend" ] || die "--path-prepend is not a directory: $path_prepend"
  visible=$path_prepend
  [ -e "$path_prepend/../pyvenv.cfg" ] && visible=$(dirname "$path_prepend")
  refuse_revealing "$visible"
  prepend_bind=(--ro-bind "$visible" "$visible")
  inner_path=$path_prepend:$inner_path
fi

mkdir -p "$runs" "$logs" || die "cannot create the run or log directory"
template=$(realpath "$template")
runs=$(realpath "$runs")
logs=$(realpath "$logs")
prompt=$(realpath "$prompt")
dst=$runs/$id

case "$logs/" in "$runs"/*) die "logs must sit outside the runs directory" ;; esac
refuse_revealing "$dst"
git -C "$template" rev-parse --verify --quiet 'HEAD^{commit}' >/dev/null || die "template has no commit: $template"

passwd="user:x:$(id -u):$(id -g):user:/home/user:/bin/bash"
group="user:x:$(id -g):"
hosts="127.0.0.1 localhost"
# Quoted system directories: skill-catalog.py reads a bare one as a slash pointer.
box=(--unshare-all --die-with-parent --new-session --seccomp 6 --ro-bind '/usr' '/usr')
for dir in bin sbin lib lib64; do
  if [ -L "/$dir" ]; then
    box+=(--symlink "$(readlink "/$dir")" "/$dir")
  elif [ -d "/$dir" ]; then
    box+=(--ro-bind "/$dir" "/$dir")
  fi
done
# alternatives: tools such as awk link through it. TLS is end to end, so it needs
# the certificates; nothing here needs the host's resolver, hosts or nsswitch files.
for file in ssl ca-certificates alternatives; do
  box+=(--ro-bind-try "/etc/$file" "/etc/$file")
done
# A fixed hosts file, so a template's own server on localhost resolves.
box+=(--ro-bind-data 3 /etc/passwd --ro-bind-data 4 /etc/group --ro-bind-data 5 /etc/hosts
  --proc '/proc' --dev '/dev' --tmpfs '/tmp' --tmpfs /home/user
  --ro-bind "$claude" /opt/cli/claude "${prepend_bind[@]}"
  --setenv HOME /home/user --setenv PATH "$inner_path"
  --setenv LANG C.UTF-8 --setenv DISABLE_AUTOUPDATER 1)

# Under the system's directory, not $TMPDIR: its path shows in the mount table and a
# socket's is short. Quoted for the same reason as the others.
private=$(mktemp -d '/tmp'/proxy.XXXXXXXX) || die "cannot create the proxy's directory"
case "$private/" in "$runs"/*) die "the runs directory may not hold the proxy's: $private" ;; esac
chmod 700 "$private"
# A copy, since the script's own path holds a word the mount table would show.
cp "$egress" "$private/egress.py" || die "cannot copy egress.py"
env -i "$python" -I "$egress" filter >"$private/filter" || die "cannot write the seccomp filter"

probe=$("$bwrap" "${box[@]}" /usr/bin/true 2>&1 3<<<"$passwd" 4<<<"$group" 5<<<"$hosts" 6<"$private/filter") ||
  die "bwrap cannot start: $probe"

# mkdir and noclobber are the reservation: of two launches with one ID, one runs.
mkdir "$dst" 2>/dev/null || die "run already exists: $dst"
( set -C; : >"$logs/$id.jsonl" ) 2>/dev/null || {
  rmdir "$dst"
  die "log already exists: $logs/$id.jsonl"
}
cp -a "$template/." "$dst/" || die "cannot copy the template"
box+=(--bind "$dst" /home/user/project --chdir /home/user/project)

env -i "$python" -I "$egress" proxy --socket "$private/proxy.sock" \
  --allow api.anthropic.com:443 --log "$logs/$id.egress" </dev/null >/dev/null 2>>"$logs/$id.egress" &
proxy_pid=$!
for _ in {1..100}; do
  [ -S "$private/proxy.sock" ] && break
  sleep 0.05
done
[ -S "$private/proxy.sock" ] || die "the proxy did not start: see $logs/$id.egress"

# in_box <variables to keep, space-separated> <bwrap options and command...>
# A subshell clears the environment, so a kept secret is inherited and never in argv.
in_box() (
  keep=" $1 "
  shift
  drop=()
  while IFS= read -r -d '' pair; do
    name=${pair%%=*}
    case $keep in
      *" $name "*) ;;
      *)
        drop+=(--unsetenv "$name")
        unset "$name" 2>/dev/null
        ;;
    esac
  done < <(env -0)
  for fd in /proc/"$BASHPID"/fd/*; do
    fd=${fd##*/}
    if [ "$fd" -gt 2 ]; then eval "exec $fd>&-"; fi
  done
  echo "$BASHPID" >"$private/session"
  exec "$timeout" "$limit" "$bwrap" "${drop[@]}" "${box[@]}" "$@" 3<<<"$passwd" 4<<<"$group" 5<<<"$hosts" 6<"$private/filter"
)

port=3128
# Read on the forwarder's stdout rather than connect, which the proxy would log.
start='exec 9< <(exec /usr/bin/python3 -I /opt/cli/egress.py forward --socket /run/proxy.sock \
  --port '$port' </dev/null 2>/dev/null)
read -r _ <&9 || { echo "run.sh: the forwarder did not start" >&2; exit 127; }
exec 9<&-
exec /opt/cli/claude "$@"'
network=(--ro-bind "$private/proxy.sock" /run/proxy.sock --ro-bind "$private/egress.py" /opt/cli/egress.py
  --setenv HTTPS_PROXY "http://127.0.0.1:$port" --setenv https_proxy "http://127.0.0.1:$port")

# Pipes, not files: the candidate's descriptors must not name a host path.
session() {
  cat "$prompt" | in_box "${auth_envs[*]}" "${network[@]}" /usr/bin/bash -c "$start" bash -p \
    --model "$model" \
    --setting-sources project --strict-mcp-config \
    --permission-mode "$permission_mode" \
    --max-turns "$max_turns" \
    --no-session-persistence \
    --output-format stream-json --verbose \
    2> >(cat >"$logs/$id.err") | cat >"$logs/$id.jsonl"
  return "${PIPESTATUS[1]}"
}
session &
wait "$!"
status=$?

# diff exits 1 when files differ.
in_box '' --ro-bind "$template" /tmp/baseline /usr/bin/diff -ruN --no-dereference --exclude=.git \
  /tmp/baseline . </dev/null >"$logs/$id.diff" 2>&1 &
wait "$!"
code=$?
[ "$code" -le 1 ] || echo "diff capture failed: exit=$code" >>"$logs/$id.diff"

echo "exit=$status $id"
exit "$status"
