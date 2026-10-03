#!/usr/bin/env bash
# Repeat the standalone product scenarios; all artifacts stay inside DWS.
set -euo pipefail
product_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)
cd "$product_dir"
verification_full=false
case "${1:-}" in
    '') ;;
    --full) verification_full=true ;;
    *) echo 'Usage: scripts/verify_product.sh [--full]' >&2; exit 2 ;;
esac
if [[ $# -gt 1 ]]; then
    echo 'Usage: scripts/verify_product.sh [--full]' >&2
    exit 2
fi
verification_python="$product_dir/.venv/bin/python"
if [[ ! -x "$verification_python" ]]; then
    echo 'Prepare the product-local host environment with uv sync --locked first.' >&2
    exit 2
fi
export PYTHONDONTWRITEBYTECODE=1
export UV_CACHE_DIR="$product_dir/.runtime/uv-cache"
export UV_PYTHON_INSTALL_DIR="$product_dir/.runtime/python"
export UV_LINK_MODE=copy
export TMPDIR="$product_dir/.runtime/tmp"
export XDG_CACHE_HOME="$product_dir/.runtime/cache"
export XDG_STATE_HOME="$product_dir/.runtime/state"
export XDG_CONFIG_HOME="$product_dir/.runtime/config"
export MYPY_CACHE_DIR="$product_dir/.runtime/mypy-cache"
export RUFF_CACHE_DIR="$product_dir/.runtime/ruff-cache"
mkdir -p "$UV_CACHE_DIR" "$UV_PYTHON_INSTALL_DIR" "$TMPDIR" \
    "$XDG_CACHE_HOME" "$XDG_STATE_HOME" "$XDG_CONFIG_HOME" \
    "$MYPY_CACHE_DIR" "$RUFF_CACHE_DIR"
if $verification_full; then
    "$verification_python" -B - <<'PY'
import importlib.util
import sys
if importlib.util.find_spec('fastmcp') is None:
    sys.exit('Full verification needs the locked MCP extra: uv sync --locked --extra mcp')
PY
fi
verification_dir="$product_dir/.runtime/verification/$(date -u +%Y%m%dT%H%M%SZ)-$$"
mkdir -p "$verification_dir"
verification_results=()
verification_failed=false

verify_step() {
    local verification_name=$1
    shift
    echo "Running $verification_name"
    if "$@" >"$verification_dir/$verification_name.log" 2>&1; then
        verification_results+=("$verification_name:passed")
        echo "$verification_name: passed"
    else
        verification_results+=("$verification_name:failed")
        verification_failed=true
        echo "$verification_name: failed (see $verification_dir/$verification_name.log)" >&2
        tail -n 15 "$verification_dir/$verification_name.log" >&2
    fi
}

verify_step core "$verification_python" -B -m pytest tests/integration \
    --basetemp="$verification_dir/pytest" -o "cache_dir=$verification_dir/pytest-cache" \
    --junitxml="$verification_dir/core.xml" -q
if $verification_full; then
    # Helpers use isolated workspaces/state. Keep main consumer replacement last.
    verify_step browser_policy "$verification_python" -B tests/qualification/image_browser_qualification.py \
        --output "$verification_dir/browser-policy"
    verify_step rendered_fixture "$verification_python" -B tests/e2e/verify_rendered_fixture.py \
        --output-dir "$verification_dir/rendered-fixture"
    verify_step live "$verification_python" -B tests/e2e/verify_live.py \
        --output-dir "$verification_dir/live"
    verify_step operations "$verification_python" -B tests/e2e/verify_operations.py \
        --output-dir "$verification_dir/operations"
fi
"$verification_python" -B - "$verification_dir" "$verification_full" \
    "${verification_results[@]}" <<'PY'
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

directory = Path(sys.argv[1])
checks = dict(value.split(':', 1) for value in sys.argv[3:])
result = {
    'full': sys.argv[2] == 'true',
    'passed': all(value == 'passed' for value in checks.values()),
    'checks': checks,
    'finished_at': datetime.now(timezone.utc).isoformat(),
    'artifact_directory': str(directory),
}
(directory / 'summary.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(result, indent=2))
PY
if $verification_failed; then exit 1; fi
