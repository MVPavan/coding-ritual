---
skill: i-have-adhd
domain: core
stage: X
substage: Communication
secondary: []
family: conversational-repair
aliases: []
status: active
---
# i-have-adhd

Use when the user invokes /i-have-adhd.

**Boundary:** Shapes every reply for an ADHD reader once invoked (next action first, small concrete steps); it produces no document or diagram (html-artifact, show-me).

<!-- registry:generated traits -->
- `next-action-first`: Lead with the next concrete action — a command, path or snippet — before any prose.
- `numbered-steps`: Render multi-step work as a numbered list with one bounded action per step.
- `single-next-action`: Close with exactly one concrete next action the reader can do in under two minutes.
- `tangent-suppression`: Finish the current issue first, then offer any other concern as a separate question.
- `state-restatement`: Restate the current progress state every turn so the reader need not hold it in memory.
- `concrete-time-estimates`: Give estimates in concrete units as agent execution plus review time rather than human workdays.
- `visible-progress`: Show completed work in concrete, runnable terms instead of burying it in a recap.
- `matter-of-fact-errors`: State an error's cause and fix plainly with no alarm language.
- `capped-lists`: Cap a list at five items, ranking them or splitting into now and later.
- `no-preamble`: Open with the answer and stop when it is done, with no preamble, recap or closing pleasantry.
- `explain-on-request`: When the user asks to explain or walk through, run as long as the topic needs while keeping the brevity discipline.
- `debug-spiral-reset`: After repeated failed fix turns, stop iterating on code, name the assumption that may be wrong, and ask one diagnostic question.
- `repitch-trigger`: When a message did not land, stop and re-pitch it rather than adding more.
- `controlled-language`: Re-pitch in controlled simplified language with short sentences and common words.
- `domain-vocabulary`: Use the project's established domain vocabulary throughout what you write.
- `pre-send-check`: Before sending, delete announcements, closers, sidebars and empty hedges.
<!-- /registry:generated traits -->

<!-- registry:generated lineage -->
- **mattpocock_skills:skill:skills/productivity/wait-what#repitch-trigger** `skills/productivity/wait-what/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2
- **mattpocock_skills:skill:skills/productivity/wait-what#domain-vocabulary** `skills/productivity/wait-what/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2
- **mattpocock_skills:skill:skills/productivity/wait-what#standard-controlled-language** `skills/productivity/wait-what/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2
- **cursor_plugins:skill:pstack/skills/bro#repitch-trigger** `pstack/skills/bro/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/bro#controlled-language** `pstack/skills/bro/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/bro#jargon-free-restatement** `pstack/skills/bro/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe (pending cr-r2pa.2.18)
<!-- /registry:generated lineage -->

<!-- registry:generated history -->
- `2026-11-06` **adopt** (2026-11-06-batch-p1:004): Checkpoint at 4dd1d05 for the owner's trait rulings: 3 adopt.
- `2026-11-06` **adopt** (2026-11-06-batch-p1:003): Owner ruling 2026-11-06: Prevents: A re-pitch still carrying terms the reader cannot follow, so it fails a second time. Lands in i-have-adhd, SKILL.md, When to…
- `2026-11-06` **adopt** (2026-11-06-batch-p1:002): Owner ruling 2026-11-06: The same line asks for short sentences and common words, and for a simpler answer rather than a longer one.
- `2026-11-06` **adopt** (2026-11-06-batch-p1:001): Owner ruling 2026-11-06: i-have-adhd's rule 5 re-explains a message that did not land instead of adding to it, which is what this command asks for.
- `2026-10-30` **adopt-merged** (2026-10-30-mattpocock_skills-5beb35b:585): Checkpoint at 5beb35b for the owner's trait rulings: 3 adopt, 1 defer.
- `2026-10-30` **adopt** (2026-10-30-mattpocock_skills-5beb35b:532): Deliberate: the three named rules are what the re-pitch needs, stated so the agent can apply them (U-06).
- `2026-10-30` **defer** (2026-10-30-mattpocock_skills-5beb35b:531): Owner deferred the report's reject recommendation, to review the set later: ROUTED: i-have-adhd already keeps CONTEXT.md terms (i-have-adhd/SKILL.md:110); find…
- `2026-10-30` **adopt** (2026-10-30-mattpocock_skills-5beb35b:530): Ours keeps the project's own terms from CONTEXT.md in the re-pitch.
- `2026-10-30` **adopt** (2026-10-30-mattpocock_skills-5beb35b:529): Ours re-explains, simpler rather than longer, when the user says the last message did not land.
- `2026-08-14` **adopt** (2026-10-14-migration:150): Adopted-in-part: controlled-language (ASD-STE100-style) re-pitch as a fifth override in i-have-adhd. No standalone skill. Evidence: skill-comparisons/interacti…
<!-- /registry:generated history -->

<!-- registry:generated reviews -->
- [2026-11-04-upstream-cursor_plugins-4dd1d05-batch-p1.md](../../reviews/2026-11-04-upstream-cursor_plugins-4dd1d05-batch-p1.md)
- [skill-comparisons/interaction-utilities](../../../archive/skill-comparisons/interaction-utilities/)
<!-- /registry:generated reviews -->

<!-- registry:generated sources -->
- `controlled-language`:
  - `cursor_plugins:skill:pstack/skills/bro#controlled-language` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
  - `mattpocock_skills:skill:skills/productivity/wait-what#standard-controlled-language` (adopted at 5beb35b040e3de97e54fa9e386d7e42d15c295c2)
- `domain-vocabulary`:
  - `mattpocock_skills:skill:skills/productivity/wait-what#domain-vocabulary` (adopted at 5beb35b040e3de97e54fa9e386d7e42d15c295c2)
- `repitch-trigger`:
  - `cursor_plugins:skill:pstack/skills/bro#repitch-trigger` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
  - `mattpocock_skills:skill:skills/productivity/wait-what#repitch-trigger` (adopted at 5beb35b040e3de97e54fa9e386d7e42d15c295c2)
<!-- /registry:generated sources -->

<!-- registry:generated declined -->
- `mattpocock_skills:skill:skills/productivity/wait-what#context-map-lookup` (defer): Owner deferred the report's reject recommendation, to review the set later: ROUTED: i-have-adhd already keeps CONTEXT.md terms (i-have-adhd/SKILL.md:110); find…
<!-- /registry:generated declined -->
