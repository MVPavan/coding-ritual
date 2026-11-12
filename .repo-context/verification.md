# Verification

Choose checks by what changed, from the table below. A file belongs to the
component it exercises, not to its directory. Documentation-only edits do not
require the interpreter suite.

This repository has no CI; these checks are its local gate.

## Claim → evidence

| Claim | Evidence | Not enough |
|---|---|---|
| Tests pass | The named command exits 0 and the expected tests ran | An earlier run; no tests collected |
| Bug fixed | The command that showed the original failure now passes | "The code changed" |
| Feature works | Driven end to end the way a user reaches it | Unit tests green |
| Agent completed | `git diff <base>..HEAD` and `git status` show the claimed change | The agent's report |
| Requirements met | Checked item by item against the brief | Tests passing |

When an end-to-end check is out of reach, report `PARTIAL`: Verified / Needs
human check / Why.

## Checks by changed material

| Changed material | Check |
|---|---|
| All changes | `git diff --check`; inspect diff/status and preserve unrelated work |
| Documentation | Validate changed paths and links; distinguish historical evidence from active guidance |
| Shell | `bash -n <file>`; `shellcheck <file>` when available |
| JSON | `python3 -m json.tool <file> >/dev/null` |
| Python hooks/scripts | `python3 -m py_compile <file>`; scoped lint/type checks from `.repo-context/coding-style.md` |
| Curation code (`curation/`), skill scripts, or their tests (`tests/curation/`, and the `tests/checks/` files that exercise a skill script) | `uv run pytest -q tests/curation tests/checks` |
| Registry data, or a file it hashes (a skill, playbook or principle, `AGENTS.md`, a `.repo-context/` file with a `doc:` entry) | `uv run python harness_lifecycle/registry/registry.py check`; when it reports a generated view stale, run `build` first |
| Beads | `bd ready` or `bd list` succeeds; keep `.beads/issues.jsonl` current per the `beads` skill (`references/usage.md` §15) |
| Skills | `python3 .claude/scripts/skill-catalog.py --check` validates catalog, pointers and invocation metadata; `--write` regenerates them |
| Interpreter: `workflow_interpreter/`, anything that runs or verifies it (`scripts/verify-feature.sh`, `scripts/review-checks.sh`, `scripts/checks/`), and the tests of either | The five-stage host gate in `docs/usage/interpreter-gate.md`, which carries the repository's Ruff and mypy options. The per-language rows above still apply. |

**Dangerous-commands hook.** After changing
`.claude/hooks/block-dangerous-commands.sh`, prove it still blocks, not just
parses: pipe a known-dangerous payload through it, e.g.
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
