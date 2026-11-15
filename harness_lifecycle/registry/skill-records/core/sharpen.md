---
skill: sharpen
domain: core
stage: Intake
substage: Clarification
secondary: []
family:
aliases: []
status: active
---
# sharpen

Make a task deeper, not bigger: answer four questions about it, then rewrite the prompt. Use for /sharpen to deepen a task prompt within its scope; settling open scope or behaviour choices is discovery.

**Boundary:** Rewrites a person's own task prompt deeper, not bigger, after four questions, leaving their choices open; open scope or behaviour questions are discovery, human-facing prose wording is unslop, authoring agent instructions is authoring-for-agents, and an interview that challenges the person's plan is grilling.

<!-- registry:generated traits -->
- `depth-not-scope-rewrite`: Treat improving a task as making it deeper, and refuse to make it merely larger.
- `diagnose-then-rewrite-prompt`: Answer a fixed set of diagnostic questions first, then rewrite the prompt to ask for exactly what they revealed.
- `expert-gap-question`: Say what a leading practitioner would do here that the request leaves out.
- `rawest-source-question`: Name the least processed material a practitioner would begin from in place of the summarized input.
- `expert-methods-question`: Name the concrete techniques and instruments a practitioner would apply.
- `outside-correctness-signal`: Name something outside both the agent and the user that would show the result is correct.
- `owner-choices-left-open`: Keep decisions that belong to the user unresolved when rewriting their request.
<!-- /registry:generated traits -->

<!-- registry:generated lineage -->
- **cursor_plugins:skill:pstack/skills/sharpen#depth-not-scope-rewrite** `pstack/skills/sharpen/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/sharpen#diagnose-then-rewrite-prompt** `pstack/skills/sharpen/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/sharpen#expert-gap-question** `pstack/skills/sharpen/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/sharpen#rawest-source-question** `pstack/skills/sharpen/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/sharpen#expert-methods-question** `pstack/skills/sharpen/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/sharpen#outside-correctness-signal** `pstack/skills/sharpen/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/sharpen#owner-choices-left-open** `pstack/skills/sharpen/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
<!-- /registry:generated lineage -->

<!-- registry:generated history -->
- `2026-11-12` **adopt** (2026-11-12-batch-p1-manual:012): Completes pending 2026-11-06-batch-p1:013: owner-choices-left-open is written at .claude/skills/sharpen/SKILL.md:24-25 (plan 60; a new unit, so no frozen wordi…
- `2026-11-12` **adopt** (2026-11-12-batch-p1-manual:011): Completes pending 2026-11-06-batch-p1:012: outside-correctness-signal is written at .claude/skills/sharpen/SKILL.md:20 (plan 60; a new unit, so no frozen wordi…
- `2026-11-12` **adopt** (2026-11-12-batch-p1-manual:010): Completes pending 2026-11-06-batch-p1:011: expert-methods-question is written at .claude/skills/sharpen/SKILL.md:19 (plan 60; a new unit, so no frozen wording).
- `2026-11-12` **adopt** (2026-11-12-batch-p1-manual:009): Completes pending 2026-11-06-batch-p1:010: rawest-source-question is written at .claude/skills/sharpen/SKILL.md:18 (plan 60; a new unit, so no frozen wording).
- `2026-11-12` **adopt** (2026-11-12-batch-p1-manual:008): Completes pending 2026-11-06-batch-p1:009: expert-gap-question is written at .claude/skills/sharpen/SKILL.md:17 (plan 60; a new unit, so no frozen wording).
- `2026-11-12` **adopt** (2026-11-12-batch-p1-manual:007): Completes pending 2026-11-06-batch-p1:008: diagnose-then-rewrite-prompt is written at .claude/skills/sharpen/SKILL.md:15-22 (plan 60; a new unit, so no frozen …
- `2026-11-12` **adopt** (2026-11-12-batch-p1-manual:006): Completes pending 2026-11-06-batch-p1:007: depth-not-scope-rewrite is written at .claude/skills/sharpen/SKILL.md:12-13 (plan 60; a new unit, so no frozen wordi…
- `2026-11-12` **add** (2026-11-12-batch-p1-manual:002): Owner rulings of 2026-11-05 §E (small manual skills) and 2026-11-06 §G (batch P1 as recommended) (scratchpad/mvp-stack/13/owner-rulings-2026-11-05.md); owner r…
- `2026-11-06` **adopt** (2026-11-06-batch-p1:014): Checkpoint at 4dd1d05 for the owner's trait rulings: 7 adopt.
- `2026-11-06` **adopt** (2026-11-06-batch-p1:013) *(superseded)*: Owner ruling 2026-11-06: Prevents: A rewrite that settles a person's choice for them, so it reads as already decided. Lands in sharpen, the new small manual sk…
- `2026-11-06` **adopt** (2026-11-06-batch-p1:012) *(superseded)*: Owner ruling 2026-11-06: Prevents: A result whose only evidence of being right is that the agent or the person says so. Lands in sharpen, the new small manual …
- `2026-11-06` **adopt** (2026-11-06-batch-p1:011) *(superseded)*: Owner ruling 2026-11-06: Prevents: A rewrite that says to do it better and names no method for doing so. Lands in sharpen, the new small manual skill. Upstream…
- `2026-11-06` **adopt** (2026-11-06-batch-p1:010) *(superseded)*: Owner ruling 2026-11-06: Prevents: A task built on a digest of the material when the material itself was available. Lands in sharpen, the new small manual skil…
- `2026-11-06` **adopt** (2026-11-06-batch-p1:009) *(superseded)*: Owner ruling 2026-11-06: Prevents: A task kept at the depth the person happened to ask for, because nobody named what an expert would add. Lands in sharpen, th…
- `2026-11-06` **adopt** (2026-11-06-batch-p1:008) *(superseded)*: Owner ruling 2026-11-06: Prevents: A prompt reworded into something tidier that still asks for the same shallow thing. Lands in sharpen, the new small manual s…
- `2026-11-06` **adopt** (2026-11-06-batch-p1:007) *(superseded)*: Owner ruling 2026-11-06: Prevents: A rewritten prompt that asks for more work and no better work. Lands in sharpen, the new small manual skill. Upstream: SKILL…
<!-- /registry:generated history -->

<!-- registry:generated reviews -->
- [2026-11-04-upstream-cursor_plugins-4dd1d05-batch-p1.md](../../reviews/2026-11-04-upstream-cursor_plugins-4dd1d05-batch-p1.md)
<!-- /registry:generated reviews -->

<!-- registry:generated sources -->
- `depth-not-scope-rewrite`:
  - `cursor_plugins:skill:pstack/skills/sharpen#depth-not-scope-rewrite` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `diagnose-then-rewrite-prompt`:
  - `cursor_plugins:skill:pstack/skills/sharpen#diagnose-then-rewrite-prompt` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `expert-gap-question`:
  - `cursor_plugins:skill:pstack/skills/sharpen#expert-gap-question` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `expert-methods-question`:
  - `cursor_plugins:skill:pstack/skills/sharpen#expert-methods-question` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `outside-correctness-signal`:
  - `cursor_plugins:skill:pstack/skills/sharpen#outside-correctness-signal` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `owner-choices-left-open`:
  - `cursor_plugins:skill:pstack/skills/sharpen#owner-choices-left-open` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `rawest-source-question`:
  - `cursor_plugins:skill:pstack/skills/sharpen#rawest-source-question` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
<!-- /registry:generated sources -->

<!-- registry:generated declined -->
No declined traits recorded.
<!-- /registry:generated declined -->
