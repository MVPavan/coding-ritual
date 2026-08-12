---
description: Canonical invocation rules for calling OpenAI Codex (via the codex-adapter plugin) from this repo. Subagents and the main thread must follow this for review, diagnosis, implementation, research, and critique.
---

# How to use Codex

Authoritative for this repo. On disagreement, this command wins. Codex runs **GPT-5.x**
(a different model family from Claude) and is a one-way, best-effort critic — no reverse loop.

Codex is reached through the installed **codex-adapter** plugin. Each call is an independent,
stateless `codex exec` process, so you can run as many concurrently as you need.

## Entry points

- **`codex-runner` skill** — the full-control path. Invoke it for any run that needs a role,
  a model/effort/sandbox override, backgrounding, or fan-out. It builds and runs
  `node "${CLAUDE_PLUGIN_ROOT}/scripts/codex-run.mjs" [options] "<prompt>"` against the
  installed plugin (resolves the plugin path for you).
- **Slash commands** — one role each, for the common shapes: `/codex` (free-form),
  `/codex-review`, `/codex-diagnose`, `/codex-implement`, `/codex-research`, `/codex-critique`.
- **`/codex-check`** — readiness. If `codex` is missing: `npm i -g @openai/codex` then `codex login`.

Runner options (via the skill): `--role <name>` · `-s read-only|workspace-write|danger-full-access`
· `-w` (= workspace-write) · `-m <model>` · `-e low|medium|high|xhigh|max|ultra` (model-dependent)
· `-c <key=value>` · `--review` (native diff review; target with `--uncommitted|--base=<branch>|--commit=<sha>` — target flags exclude a custom prompt)
· `--resume <session-id>` · `--json` · `--progress`/`--quiet` · `--skip-git-check`. Unrecognized flags
are forwarded verbatim to `codex exec` (use `--flag=value` form). Final answer → **stdout**. The progress
transcript auto-suppresses when stderr is not a TTY (i.e. agent runs — don't redirect stderr): success
prints one `[codex-adapter] session <id> (model …, sandbox) — resume:` footer; failure prints the last
60 transcript lines. Relay the stdout answer attributed to Codex.

## Roles (pick by output shape)

| Want | Role / command | Sandbox / effort |
|---|---|---|
| Adversarial review of the current diff | `review` / `/codex-review` | read-only / high |
| Diff-targeted review (base branch / commit) | `--review --base=<branch>` or `--commit=<sha>` via `codex-runner` | read-only / native |
| Root-cause a failure, no edits | `diagnose` / `/codex-diagnose` | read-only / xhigh |
| Make a bounded change + verify | `implement` / `/codex-implement` | workspace-write / high |
| Investigate with web search, cited | `research` / `/codex-research` | read-only / xhigh |
| Second opinion on a decision/design/plan | `critique` / `/codex-critique` | read-only / xhigh |
| Free-form, no preset | *(no role)* / `/codex` | read-only / default |

Explicit flags override a role's defaults (e.g. `--role implement -s read-only`, `--role critique -e high`).
`review` and `critique` return **prose**, not structured JSON.

## Invocation paths

| Need | Path |
|---|---|
| Standard role run | The matching `/codex*` slash command, or the `codex-runner` skill with `--role`. |
| Flag override (model / effort / sandbox) | The `codex-runner` skill — slash commands don't expose flags. |
| Long / noisy run you needn't block on | The `codex-runner` skill, launched with **`run_in_background: true`**; collect later via BashOutput. |
| Keep a very verbose run out of the main thread | Optional: brief a `general-purpose` subagent to invoke the skill and return only the distilled result. There is **no dedicated Codex subagent**. |

## Rules

1. **Read-only by default.** Only `--role implement` or `-w` may edit the tree — and say so to the user.
2. **`--effort` floor `low`.** `minimal` is legacy (current models don't list it; it also rejects `web_search` → 400). `low` small · `medium`/`high` investigation · `xhigh` deep root-cause · `max`/`ultra` (gpt-5.6 family only) hardest work — use sparingly, with reason.
3. **Fan out freely.** Independent work → several runs in one message (or background). The real ceiling is the API rate limit.
4. **Verify every Codex citation.** GPT-5.x confidently cites lines that don't match current code — grep before acting.
5. **Pick by role.** Reach for `-m`/`-e`/`-s` only to override a role default, with reason. Model picks: omit `-m` (account default = `gpt-5.6-sol`) · `gpt-5.6-terra` for large implementations · `gpt-5.6-luna` for small/cheap fan-out — full catalog in the `codex-runner` skill's **Models** table; never probe the CLI for model ids.
6. **Iterate 2–5 rounds** for non-trivial work. Don't ship on "DO NOT SHIP" without fixing the finding or recording why it's out of scope.
7. **Best-effort.** On capacity/auth error: retry once, then proceed without Codex and log the skip. `small` tasks skip Codex unless risk is unusual.
8. **Resume** a prior thread with `--resume <session-id>` from the footer; otherwise each call is fresh.

## Critique discipline (review / critique roles)

- **Pass the artifact, never your conclusion.** Hand Codex the document/diff/plan plus the
  contract it must satisfy — not your summary, your reasoning, or the claim you hope it
  confirms. Hand over conclusions and you get validation of conclusions.
- **Findings are data, not verdicts.** Classify each before acting: **contract-misread**
  (the artifact or prompt was unclear — fix that first) · **valid + actionable** (act) ·
  **valid trade-off** (record the decision and why) · **noise** (drop, with a one-line
  reason). Never silently drop a finding.
- **Bound the loop: 3 critique cycles per artifact.** If three cycles feel insufficient,
  the artifact is too big — decompose it; do not lift the bound.
- **Doubt-theater check:** two or more cycles with substantive findings and *zero*
  classified valid-actionable means you are collecting validation, not critique — stop,
  re-examine what you are withholding or how you framed the prompt.

## Pointers

- Deep docs ship inside the installed plugin and are directly readable: `${CLAUDE_PLUGIN_ROOT}/` (`README.md`, `docs/writing-roles.md`, `roles/`, `skills/codex-runner/`) from any `/codex*` command or the `codex-runner` skill, or under `~/.claude/plugins/cache/codex-adapter/codex-adapter/<version>/` (latest dir) for a direct read.
- Repo pointers: [`AGENTS.md`](../../AGENTS.md) § Codex And Claude · [`CLAUDE.md`](../../CLAUDE.md) § Claude and Codex.
