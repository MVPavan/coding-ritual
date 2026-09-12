#!/usr/bin/env bash
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
log_dir=$(mktemp -d /tmp/engine-bootstrap-gates.XXXXXX)
printf "Gate logs: %s\n" "$log_dir"
if uv run pytest -q -m "not bd and not live" >"$log_dir/unit.log" 2>&1; then tail -n 2 "$log_dir/unit.log"; else cat "$log_dir/unit.log"; exit 1; fi
if uv run pytest -q -m proc >"$log_dir/proc.log" 2>&1; then tail -n 2 "$log_dir/proc.log"; else cat "$log_dir/proc.log"; exit 1; fi
if uv run pytest -q -m bd >"$log_dir/bd.log" 2>&1; then tail -n 2 "$log_dir/bd.log"; else cat "$log_dir/bd.log"; exit 1; fi
if uv run pytest -q -m acceptance >"$log_dir/acceptance.log" 2>&1; then tail -n 2 "$log_dir/acceptance.log"; else cat "$log_dir/acceptance.log"; exit 1; fi
if uv run ruff check workflow_interpreter/ tests/ >"$log_dir/lint.log" 2>&1; then tail -n 2 "$log_dir/lint.log"; else cat "$log_dir/lint.log"; exit 1; fi
if uv run ruff format --check workflow_interpreter/ tests/ >"$log_dir/format.log" 2>&1; then tail -n 2 "$log_dir/format.log"; else cat "$log_dir/format.log"; exit 1; fi
if MYPYPATH=. uv run mypy --strict --explicit-package-bases workflow_interpreter/ >"$log_dir/types.log" 2>&1; then tail -n 2 "$log_dir/types.log"; else cat "$log_dir/types.log"; exit 1; fi
