#!/usr/bin/env bash
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
checks=(tests/test_canonical_and_pinning.py tests/test_foreman_resolution.py tests/test_foreman_inputs.py tests/test_foreman_envelope.py tests/test_foreman_supervise.py tests/test_profiles_command.py tests/test_profiles_git_isolation.py tests/test_supervisor_sandbox.py tests/test_supervisor_sandbox_bound.py)
if [[ -f tests/test_pointer_handoff.py ]]; then checks+=(tests/test_pointer_handoff.py); fi
uv run pytest -q "${checks[@]}" -m "not live"
uv run ruff check workflow_interpreter/ tests/
uv run ruff format --check workflow_interpreter/ tests/
MYPYPATH=. uv run mypy --strict --explicit-package-bases workflow_interpreter/
