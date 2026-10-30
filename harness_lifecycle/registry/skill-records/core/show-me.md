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

Show the current topic visually, inline in the conversation. Use when the user asks to see the shape of code, a flow, an architecture, or a change ("/show-me", "show me", "sketch it", "draw the flow", "what does the structure look like"). For a rendered standalone document, use html-artifact instead.

**Boundary:** Draws the current topic inline in the conversation; a standalone rendered document is html-artifact.

<!-- registry:generated traits -->
- `smallest-view`: Pick the smallest view that makes the point, placing each visual next to the brief prose it supports. (One form, occasionally two, never a gallery, with a sentence or two of prose each.)
- `visual-form-catalog`: Offer a set of inline visual forms — pseudocode, call, component and file trees, Mermaid and whole-block — each with its own shape rules.
- `structural-diff`: Show a change as a diff against the structure the reader already holds rather than against raw source.
- `visual-placement`: Place each visual immediately after the sentence it supports and include only the detail the current question needs.
- `real-code-names`: Use real names from the actual code, never invented placeholders.
- `medium-appropriate-form`: Prefer text forms over Mermaid in a terminal and a table over any diagram for a flat list or comparison.
- `html-handoff`: Escalate to the dedicated HTML-artifact skill only under its full gate, and never emit rendered HTML directly.
<!-- /registry:generated traits -->

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

<!-- registry:generated sources -->
No adopted traits recorded.
<!-- /registry:generated sources -->

<!-- registry:generated declined -->
No declined traits recorded.
<!-- /registry:generated declined -->
