# Verification

This repo has **no first-party application code, build, or CI**. There are no
test/lint/build commands to run for the repo as a whole, so the health gate is
**structural** — do not invent commands.

## Structural gate (run what applies to your change)

1. **Working tree** — `git status` shows only the files you intended to change;
   no `scratchpad/`, no submodule-internal edits, no machine-local paths.
2. **Shell scripts** — for each changed `.sh`, `bash -n <file>` parses clean
   (and `shellcheck <file>` if available).
3. **JSON manifests** — for each changed `plugin.json` / `marketplace.json` /
   `*.json`, validate it parses (e.g. `python3 -m json.tool <file> >/dev/null`).
4. **Python tooling** — for each changed `.py` hook/script,
   `python3 -m py_compile <file>`.
5. **Beads** — `bd ready` / `bd list` runs without error after task changes.
6. **Skill catalog** — after changing anything under `.claude/skills/`,
   `python3 .claude/scripts/skill-catalog.py --check` exits 0 (generated
   catalog current, every slash pointer and `.claude/` path resolves, every
   `agents/openai.yaml` sidecar matches its frontmatter; `--write` regenerates
   both). Slash commands are slash-only skills — there is no `commands/` dir.
7. **Dangerous-commands hook** — after changing
   `.claude/hooks/block-dangerous-commands.sh`, prove it still blocks, not
   just parses: pipe a known-dangerous payload through it, e.g.
   `echo '{"tool_input":{"command":"git push --force"}}' | bash .claude/hooks/block-dangerous-commands.sh`,
   and confirm exit code 2 with a BLOCKED message on stderr.

## Plugin test harnesses (when you touch a plugin)

- `mvp-harness/plugins/mvp-plugin/test/run-tests.sh` — Docker-based from-zero install test
  for the installer (`from-zero.sh`).
- `mvp-harness/plugins/code-intel/test/run-tests.sh` — code-intel plugin tests.

Run the relevant harness after changing that plugin; these are the closest thing
to CI the repo has. Report actual exit status and output — no completion claim
without fresh evidence.

## Workflow interpreter — sandbox tests

The `proc`-marked sandbox tests exercise the real bubblewrap mount bound, so a
green run on a host with no working `bwrap` proves nothing about that bound —
those tests skip loudly with the probe's reason — whereas the refusal-path test
and the `plan_for`/`wrap` unit tests use no real `bwrap` and must never skip.

## Workflow interpreter — the repo gate

Run all five from the repo root; this is the full gate, and it is the ONLY
place the `nested_sandbox` family runs:

1. `uv run pytest -q -m "not bd and not live"`
2. `uv run pytest -q -m bd` (needs the real `bd` binary)
3. `uv run pytest -q -m proc`
4. `uv run ruff check workflow_interpreter/ tests/` and
   `uv run ruff format --check workflow_interpreter/ tests/`
5. `MYPYPATH=. uv run mypy --strict --explicit-package-bases workflow_interpreter/`

`scripts/verify-feature.sh` is the same recipe minus `-m bd` and minus
`nested_sandbox`, because the wrapper runs it INSIDE a vendor sandbox, where a
nested `codex sandbox` cannot start (cr-o85.34.22, phase-7 live D2). The wrapper
sets `UV_CACHE_DIR` and `UV_PYTHON_INSTALL_DIR` below its writable `uv-cache`, so
a read-only `$HOME` is covered by the sandbox probe. Those tests are not weaker — they
are simply unrunnable there — so the repo gate above must be run on any change
that touches `sandbox.py`, `profiles/`, or the git-isolation tests.
