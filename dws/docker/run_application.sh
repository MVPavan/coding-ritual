#!/bin/sh
set -eu
cd /app
environment=${UV_PROJECT_ENVIRONMENT:-/app/.runtime/container-env}
test -x "$environment/bin/python" || {
    echo 'DWS environment is missing. Run the Compose prepare service first.' >&2
    exit 1
}
# Shared process lock prevents preparation from mutating a serving environment.
exec python - "$environment/bin/python" "$@" <<'PY'
import fcntl
import os
import sys

lock = os.open('/app/.runtime/environment.lock', os.O_CREAT | os.O_RDWR, 0o600)
try:
    fcntl.flock(lock, fcntl.LOCK_SH | fcntl.LOCK_NB)
except BlockingIOError:
    sys.exit('Environment preparation is running. Retry after it finishes.')
os.set_inheritable(lock, True)
os.execv(sys.argv[1], [sys.argv[1], '-m', 'dws', *sys.argv[2:]])
PY
