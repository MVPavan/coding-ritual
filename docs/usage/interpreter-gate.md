# Workflow interpreter: verification gate

`workflow_interpreter/` has no CI. This five-stage host gate is its local quality gate.
`.repo-context/verification.md` routes interpreter changes here.

## Full host gate

Run all five stages from the repo root, outside a vendor sandbox:

| Stage | Command | Prerequisite |
|---|---|---|
| Non-live suite | `uv run pytest -q -m "not bd and not live"` | Project dependencies; working sandbox facilities for `nested_sandbox` cases |
| Beads integration | `uv run pytest -q -m bd` | Real `bd` binary and an isolated test database |
| Process/sandbox suite | `uv run pytest -q -m proc` | Working `bwrap` for real mount-bound tests |
| Lint/format | `uv run ruff check workflow_interpreter/ tests/` and `uv run ruff format --check workflow_interpreter/ tests/` | Project Ruff |
| Types | `MYPYPATH=. uv run mypy --strict --explicit-package-bases workflow_interpreter/` | Project mypy |

The pytest selections overlap. These are the existing gate stages; removing
duplicate execution requires a separately validated gate change. The verifier's
five-stage output is covered by `tests/checks/test_verify_feature_script.py`.

Real sandbox tests may skip with the probe's reason; a skip does not verify the
mount boundary. Refusal-path and `plan_for`/`wrap` unit tests need no real `bwrap`
and must not skip. Changes to `workflow_interpreter/inspector/sandbox.py`,
`workflow_interpreter/profiles/`, or Git-isolation tests
require this host gate, including `nested_sandbox` coverage.

## Checks inside a vendor sandbox

`scripts/verify-feature.sh` excludes `bd` and `nested_sandbox`; it does not replace
the full host gate. The wrapper places `UV_CACHE_DIR` and
`UV_PYTHON_INSTALL_DIR` under writable `uv-cache`. The pinned verifier may run
through a file descriptor: use the checkout working directory, not `$0`, to
locate the repo, and do not assume workflow protocol variables are supplied.
