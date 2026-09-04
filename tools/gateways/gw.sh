#!/bin/sh
#
# gw.sh — manage the home-box gateways (CLIProxyAPI for Codex, the Claude
# relay for Claude Code) as one compose project with per-service commands.
# Nothing here acts on both services unless you say `all`.

set -eu

SCRIPT_DIR=$(CDPATH= cd "$(dirname "$0")" && pwd)
ENV_FILE="$SCRIPT_DIR/.env"
COMPOSE_FILE="$SCRIPT_DIR/compose.yaml"
CPA=cpa
RELAY=claude-relay

usage() {
    cat <<'USAGE'
Usage: ./gw.sh COMMAND [SERVICE|all] [ARGS]

Services: cpa (CLIProxyAPI, Codex) and claude-relay (nginx relay, Claude Code)

Commands:
  up [SERVICE|all]     Start (default: all). Creates cpa state dirs. Pulls only a missing image.
  down SERVICE|all     Stop and remove. `all` must be spelled out.
  restart SERVICE      Recreate one service from its configured image tag.
  pull cpa             Pull the CPA_IMAGE_TAG from .env ahead of an upgrade.
  status               Show both containers.
  logs SERVICE         Follow one service's logs.
  verify [SERVICE|all] cpa: management API + Management Center. claude-relay: Anthropic answers through it.
  version              Print the running CLIProxyAPI version.
  login PROVIDER       CLIProxyAPI OAuth login: codex, claude, antigravity, kimi, or xai.

Upgrade CLIProxyAPI: set CPA_IMAGE_TAG in .env, then `./gw.sh pull cpa` and `./gw.sh restart cpa`.
USAGE
}

compose() {
    (cd "$SCRIPT_DIR" && docker compose -f "$COMPOSE_FILE" "$@")
}

load_env() {
    if [ ! -f "$ENV_FILE" ]; then
        echo "Missing $ENV_FILE; copy .env.example to .env first." >&2
        exit 1
    fi

    # Source only the expected variables with unquoted, shell-safe values.
    if LC_ALL=C grep -Eqv '^([[:space:]]*(#.*)?|(CPA_API_PORT|CPA_ANTIGRAVITY_CALLBACK_PORT|CPA_MANAGEMENT_PASSWORD|CPA_IMAGE_TAG|CLAUDE_RELAY_PORT)=[A-Za-z0-9_./:@%+,=-]*)$' "$ENV_FILE"; then
        echo "Unsafe or unsupported entry in $ENV_FILE; use simple KEY=value lines." >&2
        exit 1
    fi

    set -a
    # shellcheck disable=SC1090
    . "$ENV_FILE"
    set +a
}

require_port() {
    case "$2" in
        ''|*[!0-9]*)
            echo "$1 must be a numeric port." >&2
            exit 1
            ;;
    esac
}

validate_env() {
    load_env
    require_port CPA_API_PORT "${CPA_API_PORT:-58317}"
    require_port CPA_ANTIGRAVITY_CALLBACK_PORT "${CPA_ANTIGRAVITY_CALLBACK_PORT:-15121}"
    require_port CLAUDE_RELAY_PORT "${CLAUDE_RELAY_PORT:-58380}"
    if [ -z "${CPA_MANAGEMENT_PASSWORD:-}" ]; then
        echo "CPA_MANAGEMENT_PASSWORD must not be empty." >&2
        exit 1
    fi
}

# Validate a SERVICE|all argument. Runs in the main shell so a bad value
# exits here instead of inside a command substitution, where `exit` only
# ends the subshell and the caller would proceed with an empty list.
check_target() {
    case "${1:-all}" in
        all|"$CPA"|"$RELAY") ;;
        *)
            echo "Unknown service: $1 (expected $CPA, $RELAY, or all)" >&2
            exit 2
            ;;
    esac
}

# Map an already-validated SERVICE|all argument to compose service names.
services_for() {
    case "${1:-all}" in
        all) echo "$CPA $RELAY" ;;
        *) echo "$1" ;;
    esac
}

require_service() {
    case "${1:-}" in
        "$CPA"|"$RELAY") ;;
        *)
            echo "$2 requires a service: $CPA or $RELAY" >&2
            exit 2
            ;;
    esac
}

ensure_cpa_dirs() {
    mkdir -p "$SCRIPT_DIR/cpa/auths" "$SCRIPT_DIR/cpa/logs" "$SCRIPT_DIR/cpa/plugins"
}

verify_cpa() {
    api_port=${CPA_API_PORT:-58317}
    base_url="http://127.0.0.1:$api_port"
    curl -fsS -o /dev/null \
        -H "Authorization: Bearer ${CPA_MANAGEMENT_PASSWORD}" \
        "$base_url/v0/management/config"
    echo "cpa: management API OK"
    curl -fsSL -o /dev/null "$base_url/management.html"
    echo "cpa: Management Center OK ($base_url/management.html)"
    model_count=$(curl -fsS -H "Authorization: Bearer ${CPA_MANAGEMENT_PASSWORD}" "$base_url/v0/management/auth-files" | grep -o '"provider"' | wc -l | tr -d ' ')
    echo "cpa: $model_count auth file(s) registered"
}

verify_relay() {
    relay_port=${CLAUDE_RELAY_PORT:-58380}
    # 401 is the pass condition: the request reached Anthropic through the relay
    # and was refused only for lack of a credential.
    code=$(curl -sS -m 15 -o /dev/null -w '%{http_code}' \
        -H 'anthropic-version: 2023-06-01' "http://127.0.0.1:$relay_port/v1/models" || true)
    if [ "$code" = "401" ]; then
        echo "claude-relay: Anthropic reachable through the relay (401 without a credential, as expected)"
    else
        echo "claude-relay: unexpected status '$code' from http://127.0.0.1:$relay_port/v1/models" >&2
        exit 1
    fi
}

login() {
    if [ "$#" -ne 1 ]; then
        echo "login requires exactly one provider." >&2
        usage >&2
        exit 2
    fi

    case "$1" in
        codex)
            compose exec "$CPA" /CLIProxyAPI/CLIProxyAPI -codex-device-login
            ;;
        claude)
            cat >&2 <<'WARN'
WARNING: Claude uses a hardcoded localhost:54545 callback. That port is
intentionally not published here because it collides with the existing proxy.
Use the URL/code manual copy-and-paste flow shown by the CLI; an automatic
browser callback cannot reach this container.
WARN
            compose exec "$CPA" /CLIProxyAPI/CLIProxyAPI -no-browser -claude-login
            ;;
        antigravity)
            load_env
            callback_port=${CPA_ANTIGRAVITY_CALLBACK_PORT:-15121}
            require_port CPA_ANTIGRAVITY_CALLBACK_PORT "$callback_port"
            compose exec "$CPA" /CLIProxyAPI/CLIProxyAPI \
                -no-browser -oauth-callback-port "$callback_port" -antigravity-login
            ;;
        kimi)
            compose exec "$CPA" /CLIProxyAPI/CLIProxyAPI -no-browser -kimi-login
            ;;
        xai)
            compose exec "$CPA" /CLIProxyAPI/CLIProxyAPI -no-browser -xai-login
            ;;
        *)
            echo "Unsupported provider: $1" >&2
            usage >&2
            exit 2
            ;;
    esac
}

command=${1:-}
case "$command" in
    up)
        check_target "${2:-all}"
        validate_env
        ensure_cpa_dirs
        # shellcheck disable=SC2046
        compose up -d --remove-orphans $(services_for "${2:-all}")
        ;;
    down)
        [ -n "${2:-}" ] || { echo "down requires a service or 'all'." >&2; exit 2; }
        if [ "$2" = all ]; then
            compose down
        else
            require_service "$2" down
            compose down "$2"
        fi
        ;;
    restart)
        require_service "${2:-}" restart
        validate_env
        ensure_cpa_dirs
        compose up -d --force-recreate --no-deps "$2"
        ;;
    pull)
        [ "${2:-}" = "$CPA" ] || { echo "pull is for $CPA only." >&2; exit 2; }
        validate_env
        compose pull "$CPA"
        ;;
    status)
        compose ps
        ;;
    logs)
        require_service "${2:-}" logs
        compose logs --follow --tail=200 "$2"
        ;;
    verify)
        check_target "${2:-all}"
        validate_env
        command -v curl >/dev/null 2>&1 || { echo "curl is required for verification." >&2; exit 1; }
        for svc in $(services_for "${2:-all}"); do
            case "$svc" in
                "$CPA") verify_cpa ;;
                "$RELAY") verify_relay ;;
            esac
        done
        ;;
    version)
        version_output=$(compose exec "$CPA" /CLIProxyAPI/CLIProxyAPI --help 2>&1) || {
            printf '%s\n' "$version_output" >&2
            exit 1
        }
        printf '%s\n' "$version_output" | sed -n '1p'
        ;;
    login)
        shift
        login "$@"
        ;;
    help|-h|--help)
        usage
        ;;
    '')
        usage >&2
        exit 2
        ;;
    *)
        echo "Unknown command: $command" >&2
        usage >&2
        exit 2
        ;;
esac
