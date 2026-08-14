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
6. **Skill catalog** — after changing anything under `.claude/skills/` or
   `.claude/commands/`, `python3 .claude/scripts/skill-catalog.py --check`
   exits 0 (generated catalog current, every slash pointer resolves).
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
