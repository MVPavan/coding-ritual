#!/usr/bin/env bash
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
log_dir=$(mktemp -d /tmp/engine-bootstrap-gates.XXXXXX)
printf "Gate logs: %s\n" "$log_dir"
if uv run pytest -q tests/test_profiles_command.py tests/test_profiles_git_isolation.py tests/test_inspector_sandbox.py tests/test_inspector_sandbox_bound.py tests/test_codex_writer_qualification.py -m "not live" >"$log_dir/focused.log" 2>&1; then tail -n 2 "$log_dir/focused.log"; else cat "$log_dir/focused.log"; exit 1; fi
if uv run ruff check workflow_interpreter/ tests/ >"$log_dir/lint.log" 2>&1; then tail -n 2 "$log_dir/lint.log"; else cat "$log_dir/lint.log"; exit 1; fi
if uv run ruff format --check workflow_interpreter/ tests/ >"$log_dir/format.log" 2>&1; then tail -n 2 "$log_dir/format.log"; else cat "$log_dir/format.log"; exit 1; fi
if MYPYPATH=. uv run mypy --strict --explicit-package-bases workflow_interpreter/ >"$log_dir/types.log" 2>&1; then tail -n 2 "$log_dir/types.log"; else cat "$log_dir/types.log"; exit 1; fi
