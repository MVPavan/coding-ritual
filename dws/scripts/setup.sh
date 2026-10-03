#!/usr/bin/env bash
# All host files this script creates stay in the standalone DWS directory.
set -euo pipefail
product_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)
cd "$product_dir"
umask 077
mkdir -p .runtime/uv-cache .runtime/container-env .runtime/home .runtime/cache .runtime/state .runtime/config .runtime/tmp .state
if [[ ! -f .runtime/owner.env ]]; then
    DWS_SETUP_UID=$(id -u) DWS_SETUP_GID=$(id -g) python3 - <<'PY'
import os
import secrets
from pathlib import Path

path = Path('.runtime/owner.env')
with path.open('x') as output:
    output.write(f"DWS_UID={os.environ['DWS_SETUP_UID']}\n")
    output.write(f"DWS_GID={os.environ['DWS_SETUP_GID']}\n")
    for name in ('DWS_TOKEN', 'DWS_CRAWL4AI_TOKEN', 'SEARXNG_SECRET'):
        output.write(f'{name}={secrets.token_hex(32)}\n')
    output.write('DWS_MCP_ENABLED=false\n')
path.chmod(0o600)
PY
fi
case "${1:-start}" in
    init)
        echo 'DWS directories and .runtime/owner.env are ready.'
        ;;
    start)
        docker compose --env-file .runtime/owner.env stop dws-api dws-worker
        docker compose --env-file .runtime/owner.env up --build -d
        ;;
    *)
        echo 'Usage: scripts/setup.sh [init|start]' >&2
        exit 2
        ;;
esac
