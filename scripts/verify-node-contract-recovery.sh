#!/usr/bin/env bash
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
uv run pytest -q tests/test_foreman_inputs.py tests/test_foreman_functional.py tests/test_profiles_command.py tests/test_profiles_steer.py tests/test_supervisor_workspace.py tests/test_supervisor_exit.py tests/test_supervisor_recover.py tests/test_supervisor_steer.py tests/test_children_lifecycle.py -m "not live and not bd and not nested_sandbox"
uv run ruff check workflow_interpreter/ tests/
uv run ruff format --check workflow_interpreter/ tests/
MYPYPATH=. uv run mypy --strict --explicit-package-bases workflow_interpreter/
