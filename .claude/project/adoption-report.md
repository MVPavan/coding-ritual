# Adoption Report

Harness adopted into **coding-ritual** via `/mvp-plugin:adopt`. Date: 2026-06-25.

## What this repo is

A **meta-repository** for building and maintaining reusable agent harnesses
(Claude Code + Codex plugins) and studying third-party reference harnesses. Not
an application: no first-party product code, no CI. Stack is Markdown-dominant
(~267 `.md`) + Bash (~23 `.sh`), with light Python (hook/skill scripts) and one
Node ≥18 package (`codex-adapter`, no build step).

## Inputs read

- `CLAUDE.md`, `AGENTS.md` (installed harness entry points), `README.md`.
- Skeleton overlay under `.claude/project/` and `.codex/project/`.
- `.gitmodules`, `.beads/config.yaml`, `.beads/metadata.json`, `.gitignore`,
  `git remote -v`, `git status`.
- `my_harness/` plugin manifests (`plugin.json`, `marketplace.json`) and trees
  for `mvp-plugin`, `codex-adapter`, `code-intel`; `codex-adapter/package.json`.
- `harness_learnings/coding-harness-best-practices.md`.
- Installed core: `.claude/{rules,agents,commands,skills,hooks}/`.
- Tool availability: `bd` v1.0.5 (present), `codex` CLI (present).

## Files updated (overlay)

Filled in **both** `.claude/project/` and `.codex/project/` (mirrored; only path
prefixes differ): `brief.md`, `repo-map.md`, `docs-index.md`, `verification.md`,
`invariants.md`, `tools.md`, `tracking.md`, `learnings.md` (empty), and this
`adoption-report.md`. `.claude/project/code-intel.md` filled (Claude tree only).

Also corrected the genericised **External Submodules** note + read-order line in
`CLAUDE.md` and `AGENTS.md`: they pointed at `external/`; this repo's submodules
are reference harnesses under `reference_harnesses/`.

## Assumptions

- **Structural verification gate.** No build/test/lint/CI exists for the repo as
  a whole, so the gate is structural (manifests parse, changed `.sh` pass
  `bash -n`, changed `.py` pass `py_compile`, `bd list` runs) plus the per-plugin
  test harnesses (`my_harness/mvp-plugin/test/run-tests.sh`,
  `my_harness/code-intel/test/run-tests.sh`) when those plugins change. No
  commands invented.
- **Beads prefix** auto-detects from the directory name (`coding-ritual`);
  `issue-prefix` left unset, no issues created yet.

## Conflicts / gaps

- **`README.md` was stale → fixed.** It documented `project_agnostic_claude_setup/`
  and `bodha_claude_setup/`, both removed. Refreshed during adoption (at the
  user's request) to match the current `my_harness/` + `.claude`/`.codex` layout.
- **`rules/python/` partial mismatch.** The harness ships `.claude/rules/python/`
  and `.codex/rules/python/`, but the repo has no Python application/package —
  only tooling scripts. Noted in `tools.md`; recommend trimming or explicitly
  scoping those rules to the scripts rather than leaving the mismatch silent.
- **Codex critique skipped.** Step 7 (Codex challenge of assumptions) was
  offered but the user declined the tool call, so it was not run.

## Automation recommendations (report-only — nothing enabled)

The harness already ships generic hooks (dangerous-command block,
generated-edit block, bd-prime) and core subagents; only the below add value.

1. **Shell-lint PostToolUse hook** — *signal:* ~23 `.sh` scripts are the repo's
   executable surface (installers, test harnesses, hooks). *Why:* catch breakage
   mechanically. *Opt-in:* add a PostToolUse hook running `bash -n` (and
   `shellcheck` if installed) on edited `*.sh` in `.claude/settings.json`.
2. **JSON-manifest validation hook** — *signal:* multiple `plugin.json` /
   `marketplace.json` that must stay valid JSON. *Why:* a malformed manifest
   silently breaks plugin loading. *Opt-in:* PostToolUse hook validating edited
   `*.json` with `python3 -m json.tool`.
3. **`context7` MCP** — already connected this session; keep it for live
   library/CLI docs referenced throughout the harness docs. No action needed.
4. **`code-intel` plugin — not recommended.** Repo is small and markdown/shell-
   dominant with no dominant LSP language (see `code-intel.md`). The plugin's
   *source* lives here, but that's not a reason to index this repo.
5. **No** database MCP, Playwright MCP, security-reviewer subagent, or
   format-on-save hook — no matching signal (no DB, no frontend/e2e,
   no auth/payments code, no Prettier/ESLint/Ruff config).

## Recommended next review step

1. Review this report and the overlay in `.claude/project/` + `.codex/project/`.
2. Decide on the `rules/python/` trim (README refresh already done).
3. Nothing has been `git add`ed — stage and commit the overlay when satisfied.
