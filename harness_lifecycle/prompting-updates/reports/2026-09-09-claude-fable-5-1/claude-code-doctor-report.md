# Claude Code Doctor Report

- Date: 2026-09-09
- Author: Claude Fable 5.1 (`claude-fable-5-1`), running as Claude Code inside the VS Code extension
- Command: `/doctor`, read-only diagnosis; no changes were applied at the time of writing
- Repo: `dws` (worktree branch `dws`), machine-local Claude Code setup

All token figures are estimates (chars / 4). Scan window for usage signals: 50 most recent session
transcripts, 2026-09-02 to 2026-09-09, across 10 project directories. Lifetime usage counters are
cumulative since install and are never windowed.

## Summary

The install is healthy, the checked-in CLAUDE.md files are already lean, and no hook is slow. The
cleanup candidates are small: one unused plugin, one unused personal skill, three always-loaded Python
rule files that could load only when Python is touched, and a Claude Code binary 8 releases behind
because background updates are off. Everything proposed is reversible. Total context saving is about
1.7k est. tokens per session.

## Inventory and verdicts

| Component | Type | Scope | Uses (total since install) | Used in window? | Est. resident tokens | Verdict |
|---|---|---|---|---|---|---|
| ai@pydantic-skills | plugin (1 skill) | user | 0 | no | ~12 | remove |
| codex-adapter@mvp-plugin | plugin (8 skills) | user | 12 | yes (5 invocations) | ~250 | keep |
| context7@claude-plugins-official | plugin + MCP server | user | 102 (last 2026-09-02) | counter yes, 0 tool calls | deferred / not loaded, failing with HTTP 401 | keep, fix auth |
| Canva, Gmail, Google Calendar, Google Drive | claude.ai connectors | account | n/a (no counter) | no | not loaded (unauthorized) | disconnect at claude.ai if unused |
| graphify | skill | user (`~/.claude/skills`) | 1 (2026-08-06) | no | ~100 (+~60 in `~/.claude/CLAUDE.md`) | remove |
| 46 project skills (28 model-visible, 18 slash-only) | skills | project (checked in) | 1 to 23 each | 8 used | ~2.5k of ~10k budget | keep; they are this repo's product |
| 6 disabled plugins; mvp-plugin@mvp-plugin installed but not enabled | plugins | user | n/a | no | 0 | nothing to do |
| `CLAUDE.md` (root) | memory file | checked in | n/a | always | ~1.5k | already lean |
| `.claude/rules/python/*.md` (3 files) | rules, always loaded | checked in | n/a | always | ~1.5k | scope to Python files |
| `.claude/rules/core/*`, `.claude/rules/harness-lifecycle/curation.md` | rules | checked in | n/a | always | ~1.3k | keep |
| `~/.claude/CLAUDE.md` | local memory | all projects | n/a | always | ~60 | only the graphify note |

## Findings by check

### Check 0: setup health

No findings. Native install at `~/.local/bin/claude` (symlink to `~/.local/share/claude/versions/2.1.258`),
`installMethod` = native, `~/.local/bin` on PATH, no npm-global or `~/.claude/local` leftovers. Every
settings file parses (`~/.claude/settings.json`, `.claude/settings.json`, `~/.claude.json`;
`.claude/settings.local.json`, `.mcp.json`, and managed settings are absent). 4 agent definitions valid,
no name collisions. All 47 `SKILL.md` frontmatters parse. Old version directories 2.1.227, 2.1.251 and
2.1.252 remain on disk; 2.1.252 is still serving other live sessions, so they were left alone.

### Check 1: unused skills, MCP servers, plugins

1. **Disable `ai@pydantic-skills`.** Zero uses ever, no transcript hits; its `lastUsedAt` is the
   install-time seed. Edit: add `"ai@pydantic-skills": false` under `enabledPlugins` in
   `~/.claude/settings.json` (the plugin is enabled at user scope). Undo: set it back to `true`.
2. **Disable the `graphify` user skill.** One lifetime use (2026-08-06), none in the window. Edit: add
   `"skillOverrides": {"graphify": "off"}` to `~/.claude/settings.json`, and delete the graphify note
   from `~/.claude/CLAUDE.md`. That file loads in every project, so the note disappears everywhere.
   Removed text, for restoration:

   ```
   # graphify
   - **graphify** (`~/.claude/skills/graphify/SKILL.md`) - any input to knowledge graph. Trigger: `/graphify`
   When the user types `/graphify`, use the installed graphify skill or instructions before doing anything else.
   ```
3. **context7: keep but repair.** The MCP server rejects its configured Authorization header (HTTP 401),
   so the `docs-researcher` agent and the `CLAUDE.md` tool routing that depend on it are silently broken.
   Fix the token in the plugin's MCP config or via `/mcp`. The header value was not read.
4. **claude.ai connectors** (Canva, Gmail, Google Calendar, Google Drive) cannot be disabled from local
   files. If unused, disconnect them in claude.ai connector settings.

### Check 2: local CLAUDE.md dedup and contradictions

No duplicates and no contradictions. The only local guidance is the graphify note above.

### Check 3: derivable content in checked-in CLAUDE.md

Root `CLAUDE.md` is already lean at 6,153 chars, far under the ~40,000-char warning floor. Nothing to
cut. `AGENTS.md` is a pointer target, not auto-loaded. The Python rules are not derivable from code
because the repo has no first-party Python application code yet.

### Check 4: lazy loading

One migration. The three Python rule files load in every session but only matter when Python is
touched. Add this frontmatter to each of `coding-style.md`, `safety.md`, and `testing.md` under
`.claude/rules/python/`:

```
---
paths:
  - "**/*.py"
  - "pyproject.toml"
---
```

Saves ~1.5k est. tokens in non-Python sessions. Caveat: these rules are published into the plugin by
`scripts/publish-plugin.sh`, so the frontmatter ships too. It is a working-tree edit to review in
`git diff`, never committed by the agent.

### Check 5: slow hooks (warnings only)

Hooks are fast in this repo: SessionStart hooks ~300 ms typical, ~1 s worst; PreToolUse guards 2 to
4 ms. Two hooks fail in other projects, not here: `harness-staleness-nudge.sh` exits 127 (script
missing) in equity-os on 62 session starts, and `block-generated-edits.sh` exits 126 (not executable)
in bodha-complete on 25 edits. Both are non-blocking, so those guards are silently doing nothing.

### Check 6: context-heavy extensions (warnings only)

Largest always-resident context, est.: rules bundle ~2.8k, project skill listing ~2.5k (of a ~10k
budget at 1% of a 1M window), root `CLAUDE.md` ~1.5k, Beads session-start hook output ~1.3k, memory
index ~0.6k. No MCP tool schemas are resident. `/context` gives the live figure.

### Check 7: Claude Code version

Terminal launcher runs 2.1.258; latest on the `latest` channel is 2.1.266 (stable is 2.1.236).
Background auto-updates are off in `~/.claude.json` (`autoUpdates: false`), which is the user's own
setting and why it drifted. Proposed command: `claude update`. Other sessions still run 2.1.252 and the
VS Code extension bundles its own 2.1.266, so the update affects only new terminal sessions.

### Check 8: auto mode as default permission mode

No `defaultMode` is set at any scope and auto mode is not disabled. Proposed: add
`"permissions": {"defaultMode": "auto"}` to `~/.claude/settings.json`. Applies to every project; if auto
mode is unavailable at startup the CLI falls back to default mode with a notice. Must live in the user
file; project or local scope is ignored for the value `auto`.

### Check 9: pre-approve frequently denied read-only commands

Nothing to propose. Every denied command that looked read-only was chained with writes (for example
`git log` followed by `git reset --soft` and `rm -rf`) or was a `git worktree add`. The `grep -n`
denials were user-rejected compound commands in another project. No candidate passes the read-only
validation bar, so no allow rule is justified.

## Proposed action bundle (pending confirmation)

Cleanup (checks 1, 4, 7): disable 1 plugin, disable 1 skill plus its `~/.claude/CLAUDE.md` note, scope
3 Python rule files, run `claude update`. About 1.7k est. tokens saved per session; all reversible.

Permissions (check 8), gated separately: set `permissions.defaultMode` to `auto` in
`~/.claude/settings.json`.

## Method notes

- Data sources: `~/.claude.json` usage counters (key-scoped `jq` reads only), transcript `.jsonl`
  files (counting only; content treated as untrusted), the settings cascade (key-scoped reads), skill
  and agent frontmatter (parse-checked with PyYAML), hook scripts in `.claude/hooks/`.
- Network access: one read-only GET per channel to `downloads.claude.ai/claude-code-releases/`.
- Secrets: no `env`, `headers`, or token values were read or quoted.
