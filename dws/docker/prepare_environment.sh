#!/bin/sh
# This finite Compose service exclusively prepares the container environment.
set -eu
cd /app
test -f uv.lock || { echo 'Missing uv.lock; refusing an unlocked installation.' >&2; exit 1; }
mkdir -p "$UV_PROJECT_ENVIRONMENT" "$UV_CACHE_DIR" /app/.runtime/cache /app/.runtime/state /app/.runtime/config "$TMPDIR"
python - <<'PY'
import fcntl
import os
import subprocess
import sys
from pathlib import Path

with Path('/app/.runtime/environment.lock').open('a') as lock:
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        sys.exit('Environment is in use. Stop dws-api and dws-worker before preparation.')
    command = ['uv', 'sync', '--locked', '--no-dev']
    if os.environ.get('DWS_MCP_ENABLED', 'false').lower() == 'true':
        command.extend(['--extra', 'mcp'])
    subprocess.run(command, check=True)
    subprocess.run([
        str(Path(os.environ['UV_PROJECT_ENVIRONMENT']) / 'bin/python'),
        '-c',
        'import dws, sqlite3; sqlite3.connect(":memory:").execute("CREATE VIRTUAL TABLE evidence USING fts5(text)")',
    ], check=True)
PY
echo 'DWS container environment is ready.'
