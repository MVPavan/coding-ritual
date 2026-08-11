# plugin-mcp-2 shard — worker notes

25 rows: 16 plugins + 9 MCP servers. All source paths inspected except where stale (see below).

## Assumptions

- The six 1–5 dimensions score the capability **as authored** (quality of the artifact),
  while `actual_usefulness_verdict` folds in fit for this Python-centric, Beads-tracked,
  gh-CLI, local-artifacts harness. A well-built but ill-fitting plugin can score 4s and
  still be `reject_after_review`.
- For `in_ours == yes` rows (mvp-plugin, codebase-memory, serena) I used `adopt` to mean
  "keep as-is; no external action" — the verdict enum has no separate "keep".
- Bundle rows (ecc, mattpocock-skills) were judged as wrappers; their member skills are
  assumed to have their own rows elsewhere in the analysis, per the curation rule
  "borrow the smallest durable pattern; do not import whole catalogs".

## Stale source paths (evidence correction)

Rows `mcp:exa`, `mcp:github`, `mcp:memory`, `mcp:sequentialthinking` cite
`reference_harnesses/everything-claude-code/.mcp.json`, which now contains **only
chrome-devtools**. The actual entries live in
`reference_harnesses/everything-claude-code/mcp-configs/mcp-servers.json` (a ~34-server
copy-what-you-need catalog). Evidence notes on those rows record the corrected location.
`mcp:context7` and `mcp:playwright` remain valid via
`reference_harnesses/claude-code-best-practice/.mcp.json` (pinned versions 2.1.8 / 0.0.70).

## Evidence inspected (23 files)

- 16 `plugin.json` manifests (all plugin rows) + directory listings of each plugin.
- `mvp-harness/plugins/code-intel/.mcp.json` (serena launch args, cbm) + `bin/` listing.
- `claude-code-best-practice/.mcp.json`, `everything-claude-code/.mcp.json`,
  `everything-claude-code/mcp-configs/mcp-servers.json`.
- `.claude/project/tools.md` (local MCP/subagent routing — context7 already wired in).
- `ralph-loop/commands/ralph-loop.md` (completion-promise rule),
  `project-artifact/skills/project-artifact/SKILL.md` head (Artifact-tool dependency).

## Verdict summary

- **adopt (4):** mvp-plugin, codebase-memory, serena (all already ours — keep);
  **mcp:playwright** is the shard's only genuinely new adoption candidate — real gap
  (HTML deliverables + verify-by-driving culture, no first-party browser automation),
  official server, Node>=18 already a harness dep via codex-adapter. Suggest opt-in
  pinned entry (e.g. in code-intel or a small browser plugin).
- **defer (2):** mcp-tunnels (revisit if remote-control work needs a private remote MCP),
  deepwiki (complementary to context7 but intermittent need, immature 0.0.6 package).
- **reject_after_review (19):** everything else.

## Notable disagreements with shallow passes

- `mcp:exa` / `mcp:github` (both shallow **yes/yes**): rejected — saturated by host
  WebSearch/WebFetch + deep-research, and by the CLAUDE.md-mandated `gh` CLI respectively;
  the ECC github entry is also the deprecated `@modelcontextprotocol/server-github` + raw PAT.
- `plugin:mattpocockskills` (gpt "TS-only"): wrong premise — the 20-skill manifest is mostly
  language-neutral process skills; rejected as a *bundle*, several members already local
  (grill-me, teach-session≈teach, systematic-debugging≈diagnosing-bugs, tdd).
- `plugin:projectartifact` (gpt yes): high craft (instruction_quality 5) but its delivery
  mechanism violates the user's recorded "never publish to claude.ai Artifacts" preference;
  only the tabbed status-page structure is borrowable, via html-artifact, locally.
- `plugin:mvpplugin` (gpt "vague MVP prototyping"): name misparse — it is our own
  adoption/update plugin, the load-bearing distribution mechanism.

## Cluster relationships

- `chat-notification-bridge`: discord + telegram are structurally identical twins.
- `output-style`: explanatory- and learning-output-style share the same SessionStart-hook
  injector pattern; both conflict with the lean-output posture.
- `agent-memory`: mcp:memory rejected largely *because* codebase-memory (ours) exists;
  ECC itself ships four competing memory servers, a hedge worth noting.
- `docs-lookup`: context7 (adopted) vs deepwiki (defer) — API-level vs whole-repo docs.
- `git-hosting-integration`: gitlab plugin + github MCP both lose to the gh CLI standard.
- `harness-catalog-bundle`: ecc + mattpocock-skills — wrappers rejected, members judged
  individually elsewhere.
- Borrowable micro-pattern flagged but below adoption threshold: ralph-loop's
  "completion promise may only be emitted when literally true" anti-escape rule.
