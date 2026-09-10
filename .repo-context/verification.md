# Verification

Select checks for the affected component. Harness documentation/configuration
uses the applicable structural checks below; interpreter changes use the
interpreter gate; plugin changes use their test harness. Documentation-only
edits do not require the interpreter suite.

## Structural checks

| Changed material | Check |
|---|---|
| All changes | `git diff --check`; inspect diff/status and preserve unrelated work |
| Documentation | Validate changed paths and links; distinguish historical evidence from active guidance |
| Shell | `bash -n <file>`; `shellcheck <file>` when available |
| JSON | `python3 -m json.tool <file> >/dev/null` |
| Python hooks/scripts | `python3 -m py_compile <file>`; scoped lint/type checks from `.repo-context/coding-style.md` |
| Beads | `bd ready` or `bd list` succeeds; refresh the export per `.beads/beads.md` |
| Skills | `python3 .claude/scripts/skill-catalog.py --check` validates catalog, pointers and invocation metadata; `--write` regenerates them |

**Dangerous-commands hook** — after changing
   `.claude/hooks/block-dangerous-commands.sh`, prove it still blocks, not
   just parses: pipe a known-dangerous payload through it, e.g.
   `echo '{"tool_input":{"command":"git push --force"}}' | bash .claude/hooks/block-dangerous-commands.sh`,
   and confirm exit code 2 with a BLOCKED message on stderr.

## Plugin checks

These paths require the initialized `mvp-harness/` submodule. Read the relevant
plugin README for its current environment and prerequisites before running:

- `mvp-harness/plugins/mvp-plugin/test/run-tests.sh` — Docker-based from-zero install test
  for the installer (`from-zero.sh`).
- `mvp-harness/plugins/code-intel/test/run-tests.sh` — code-intel plugin tests.

Run the affected plugin's harness. If unavailable, report it as unverified.
Distribution compatibility, including the outstanding context-path migration,
is tracked in `docs/usage/mvp-plugin.md`.

## Interpreter: full host gate

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
and must not skip. Changes to `workflow_interpreter/supervisor/sandbox.py`,
`workflow_interpreter/profiles/`, or Git-isolation tests
require this host gate, including `nested_sandbox` coverage.

## Interpreter: checks inside a vendor sandbox

`scripts/verify-feature.sh` excludes `bd` and `nested_sandbox`; it does not replace
the full host gate. The wrapper places `UV_CACHE_DIR` and
`UV_PYTHON_INSTALL_DIR` under writable `uv-cache`. The pinned verifier may run
through a file descriptor: use the checkout working directory, not `$0`, to
locate the repo, and do not assume workflow protocol variables are supplied.
