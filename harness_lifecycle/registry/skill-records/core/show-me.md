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
- `minimal-visual-selection`: Use the fewest and smallest visuals that make the point, never a gallery. (One form, occasionally two, never a gallery, with a sentence or two of prose each.)
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
- **mattpocock_skills:skill:skills/engineering/pr#visual-form-catalog** `skills/engineering/pr/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2
- **mattpocock_skills:skill:skills/engineering/pr#structural-diff** `skills/engineering/pr/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2
- **mattpocock_skills:skill:skills/engineering/pr#visual-placement** `skills/engineering/pr/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2
- **mattpocock_skills:skill:skills/engineering/pr#minimal-visual-selection** `skills/engineering/pr/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2
<!-- /registry:generated lineage -->

<!-- registry:generated history -->
- `2026-10-30` **adopt-merged** (2026-10-30-mattpocock_skills-5beb35b:572): Checkpoint at 5beb35b for the owner's trait rulings: 4 adopt, 5 defer.
- `2026-10-30` **adopt** (2026-10-30-mattpocock_skills-5beb35b:273): HELD: show-me (.claude/skills/show-me/SKILL.md:9): Our show-me uses the smallest view, one form or occasionally two. Target show-me already lists it, so the ad…
- `2026-10-30` **adopt** (2026-10-30-mattpocock_skills-5beb35b:272): HELD: show-me (.claude/skills/show-me/SKILL.md:26): Our show-me places each visual after the sentence it supports with only the needed elements. Target show-me…
- `2026-10-30` **adopt** (2026-10-30-mattpocock_skills-5beb35b:271): HELD: show-me (.claude/skills/show-me/SKILL.md:20-22): Our show-me shapes diffs to the structure the reader holds. Target show-me already lists it, so the adop…
- `2026-10-30` **adopt** (2026-10-30-mattpocock_skills-5beb35b:266): HELD: show-me (.claude/skills/show-me/SKILL.md:11-18): Our show-me carries the same catalogue of visual forms the PR summary draws on. Target show-me already l…
- `2026-08-20` **adopt-merged** (2026-10-14-migration:189): Adopted 2026-08-20 (round-005, supersedes round-003 defer) as a user-invoked skill .claude/skills/show-me (disable-model-invocation: true — kills the misfire r…
- `2026-08-20` **adopt-merged** (2026-10-14-migration:177) *(superseded)*: Adopted as .claude/skills/show-me, user-invoked only (disable-model-invocation: true). The round-003 defer precondition (record a prose-vs-diagram failure firs…
<!-- /registry:generated history -->

<!-- registry:generated reviews -->
None yet.
<!-- /registry:generated reviews -->

<!-- registry:generated sources -->
- `minimal-visual-selection`:
  - `mattpocock_skills:skill:skills/engineering/pr#minimal-visual-selection` (adopted at 5beb35b040e3de97e54fa9e386d7e42d15c295c2)
- `structural-diff`:
  - `mattpocock_skills:skill:skills/engineering/pr#structural-diff` (adopted at 5beb35b040e3de97e54fa9e386d7e42d15c295c2)
- `visual-form-catalog`:
  - `mattpocock_skills:skill:skills/engineering/pr#visual-form-catalog` (adopted at 5beb35b040e3de97e54fa9e386d7e42d15c295c2)
- `visual-placement`:
  - `mattpocock_skills:skill:skills/engineering/pr#visual-placement` (adopted at 5beb35b040e3de97e54fa9e386d7e42d15c295c2)
<!-- /registry:generated sources -->

<!-- registry:generated declined -->
No declined traits recorded.
<!-- /registry:generated declined -->
