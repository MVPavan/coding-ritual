# Shard plugin-mcp-1 — worker notes

26 rows (plugins/MCP), all from `claude-plugins-official`, `superpowers`,
`compound-engineering-plugin`, or our own `mvp-harness`. Evaluated 2026-07-06.

## Evidence inspected

- Every row's `plugin.json` plus a directory tree (`find -maxdepth 2`).
- Content samples: agent-sdk-dev (new-sdk-app command + py verifier agent),
  claude-automation-recommender SKILL, claude-md-improver SKILL +
  revise-claude-md command, code-review command (full), code-simplifier agent,
  commit/commit-push-pr commands, feature-dev command, hookify README,
  build-mcp-server SKILL, plugin-dev README, pr-review-toolkit README,
  security-guidance README, skill-creator SKILL, superpowers README + skills
  listing, compound-engineering README/CHANGELOG/skills listing.
- All six config-only external plugins' `.mcp.json` (context7, github,
  playwright, serena, terraform, asana).
- Local overlap baseline: `.claude/settings.json` (hooks), `.claude/skills/`
  listing, `mvp-harness/plugins/` + `marketplace.json`, our code-intel and
  codex-adapter READMEs, plus the session skill inventory (confirms
  skill-creator, claude-code-setup, context7 already installed/active).

## Stale paths

- `plugin:compoundengineering` — `plugins/compound-engineering/` no longer
  exists; the repo restructured into a single root plugin
  (`.claude-plugin/plugin.json`, v3.18.0, ~30 `ce-*` skills). Evaluated the
  root plugin.
- `plugin:codingtutor` — removed upstream entirely (CHANGELOG line 24:
  "bump marketplace catalogs for coding-tutor removal", #951). Scored from
  residual evidence; verdict reject_after_review. Weakest-evidence row in
  the shard.

## Disagreements with shallow passes

- `code-modernization`: both shallow passes said yes ("applies to Python");
  the plugin self-describes as COBOL / legacy Java/C++/.NET / monolith
  modernization with 10 commands + 7 agents + JS orchestrators. Rejected.
- `code-simplifier`: shallow yes, but the agent hardcodes JS/React project
  standards and the built-in `simplify` skill already covers it. Rejected.
- `github` MCP: shallow yes, but the environment standardizes on `gh` CLI;
  the MCP server is duplicate context weight. Rejected.
- `compound-engineering`: gpt "maybe" undersold the content, fable "yes"
  oversold adoption — merged verdict: borrow only the docs/solutions
  compound-grounding pattern.

## Cluster relationships

- `code-review-core`: plugin:codereview (merge — its 0-100 confidence rubric
  + false-positive taxonomy is the durable pattern) and pr-review-toolkit
  (defer) both compete with built-in code-review//review/codex-review.
- `semantic-code-intel`: our code-intel (adopt) supersedes the bare serena
  external plugin (reject).
- `core-dev-methodology`: superpowers is the upstream of ~5 identically-named
  local skills — merge means continued selective sync via the lifecycle
  tooling, never plugin install (would duel with local ports).
- `learning-compounding` (compound-engineering) is adjacent to
  `claude-md-hygiene` (claude-md-management): both feed session learnings back
  into persistent context; our learnings.md flow is the local anchor for both
  merges.
- Authoring stack complements: skill-creator (skills, installed) + plugin-dev
  (hooks/MCP/agents/commands, adopt) + mcp-server-dev (MCP servers, adopt) +
  hookify (guard-rule authoring, defer).

## Verdict tally

adopt 7 (claude-code-setup, code-intel, codex-adapter, context7,
mcp-server-dev, plugin-dev, skill-creator — 4 of which are already
installed/ours), merge 4 (claude-md-management, code-review, superpowers,
compound-engineering), defer 4 (agent-sdk-dev, hookify, playwright,
pr-review-toolkit, security-guidance — 5 actually), reject_after_review 9.
Note: defer count is 5; adopt 7, merge 4, defer 5, reject 10 = 26.
Corrected tally: adopt 7, merge 4, defer 5, reject_after_review 10.
