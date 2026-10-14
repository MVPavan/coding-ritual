---
skill: show-me
domain: core
stage: X
substage: Communication
secondary: []
family: visual-explanation
aliases: []
status: active
---
# show-me

## Capability

Show the current topic visually, inline in the conversation. Use when the user asks to see the shape of code, a flow, an architecture, or a change ("/show-me", "show me", "sketch it", "draw the flow", "what does the structure look like"). For a rendered standalone document, use html-artifact instead.

<!-- registry:generated lineage -->
- **humanlayer_skills:skill:plugins/show-me/skills/show-me** `plugins/show-me/skills/show-me/SKILL.md` @ 3c26291
  - merged from: show-me (humanlayer)
  - modified: description rewritten to triggers only
  - modified: Mermaid marked client-dependent, never terminal
  - modified: handoff bound to html-artifact's all-hold gate (critic finding 3)
  - modified: five inline forms merged, file-path/hook annotations kept
  - dropped: one-sentence HTML escalation (html-artifact owns that end)
  - dropped: macOS-only open command
  - dropped: model auto-invocation (revisit with observed usage)
- **humanlayer_skills:skill:plugins/show-me/skills/show-me** `plugins/show-me/skills/show-me/SKILL.md` @ 3c26291
  - merged from: show-me (humanlayer)
  - modified: description rewritten to triggers only
  - modified: Mermaid marked client-dependent, never terminal
  - modified: handoff bound to html-artifact's all-hold gate (critic finding 3)
  - modified: five inline forms merged, file-path/hook annotations kept
  - dropped: one-sentence HTML escalation (html-artifact owns that end)
  - dropped: macOS-only open command
  - dropped: model auto-invocation (revisit with observed usage)
<!-- /registry:generated lineage -->

<!-- registry:generated history -->
- `2026-08-20` **adopt-merged** (2026-10-14-migration:189): Adopted 2026-08-20 (round-005, supersedes round-003 defer) as a user-invoked skill .claude/skills/show-me (disable-model-invocation: true — kills the misfire r…
- `2026-08-20` **adopt-merged** (2026-10-14-migration:177) *(superseded)*: Adopted as .claude/skills/show-me, user-invoked only (disable-model-invocation: true). The round-003 defer precondition (record a prose-vs-diagram failure firs…
<!-- /registry:generated history -->

<!-- registry:generated reviews -->
None yet.
<!-- /registry:generated reviews -->
