#!/bin/sh

set -eu

SCRIPT_DIR=$(CDPATH= cd "$(dirname "$0")" && pwd)
ENV_FILE="$SCRIPT_DIR/.env"
SERVICE=cpa-harness-api

usage() {
    cat <<'EOF'
Usage: ./cpa.sh COMMAND [PROVIDER]

Commands:
  up              Create local state directories and start the harness
  down            Stop and remove the harness
  restart         Recreate the harness from the latest image
  status          Show container status
  logs            Follow service logs
  verify          Check the management API and Management Center
  version         Print the running CLIProxyAPI version
  login PROVIDER  Login with codex, claude, antigravity, kimi, or xai
EOF
}

compose() {
    (cd "$SCRIPT_DIR" && docker compose "$@")
}

load_env() {
    if [ ! -f "$ENV_FILE" ]; then
        echo "Missing $ENV_FILE; copy .env.example to .env first." >&2
        exit 1
    fi

    # Source only the three expected variables with unquoted, shell-safe values.
    if LC_ALL=C grep -Eqv '^([[:space:]]*(#.*)?|(CPA_API_PORT|CPA_ANTIGRAVITY_CALLBACK_PORT|CPA_MANAGEMENT_PASSWORD)=[A-Za-z0-9_./:@%+,=-]*)$' "$ENV_FILE"; then
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
    require_port CPA_API_PORT "${CPA_API_PORT:-18317}"
    require_port CPA_ANTIGRAVITY_CALLBACK_PORT "${CPA_ANTIGRAVITY_CALLBACK_PORT:-15121}"
    if [ -z "${CPA_MANAGEMENT_PASSWORD:-}" ]; then
        echo "CPA_MANAGEMENT_PASSWORD must not be empty." >&2
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
            compose exec "$SERVICE" /CLIProxyAPI/CLIProxyAPI -codex-device-login
            ;;
        claude)
            cat >&2 <<'EOF'
WARNING: Claude uses a hardcoded localhost:54545 callback. That port is
intentionally not published here because it collides with the existing proxy.
Use the URL/code manual copy-and-paste flow shown by the CLI; an automatic
browser callback cannot reach this harness.
EOF
            compose exec "$SERVICE" /CLIProxyAPI/CLIProxyAPI -no-browser -claude-login
            ;;
        antigravity)
            load_env
            callback_port=${CPA_ANTIGRAVITY_CALLBACK_PORT:-15121}
            require_port CPA_ANTIGRAVITY_CALLBACK_PORT "$callback_port"
            compose exec "$SERVICE" /CLIProxyAPI/CLIProxyAPI \
                -no-browser -oauth-callback-port "$callback_port" -antigravity-login
            ;;
        kimi)
            compose exec "$SERVICE" /CLIProxyAPI/CLIProxyAPI -no-browser -kimi-login
            ;;
        xai)
            compose exec "$SERVICE" /CLIProxyAPI/CLIProxyAPI -no-browser -xai-login
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
        validate_env
        mkdir -p "$SCRIPT_DIR/auths" "$SCRIPT_DIR/logs" "$SCRIPT_DIR/plugins"
        compose up -d --pull always --remove-orphans
        ;;
    down)
        compose down
        ;;
    restart)
        validate_env
        mkdir -p "$SCRIPT_DIR/auths" "$SCRIPT_DIR/logs" "$SCRIPT_DIR/plugins"
        compose up -d --pull always --force-recreate --remove-orphans
        ;;
    status)
        compose ps
        ;;
    logs)
        compose logs --follow --tail=200 "$SERVICE"
        ;;
    verify)
        validate_env
        api_port=${CPA_API_PORT:-18317}
        management_password=${CPA_MANAGEMENT_PASSWORD:-}
        if ! command -v curl >/dev/null 2>&1; then
            echo "curl is required for verification." >&2
            exit 1
        fi
        base_url="http://127.0.0.1:$api_port"
        curl -fsS -o /dev/null \
            -H "Authorization: Bearer $management_password" \
            "$base_url/v0/management/config"
        echo "Management API: OK"
        curl -fsSL -o /dev/null "$base_url/management.html"
        echo "Management Center: OK ($base_url/management.html)"
        ;;
    version)
        version_output=$(compose exec "$SERVICE" /CLIProxyAPI/CLIProxyAPI --help 2>&1) || {
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
