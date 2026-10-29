---
skill: prototype
domain: engineering
stage: Design
substage: Architecture
secondary: [Research]
family: design-validation
aliases: []
status: active
---
# prototype

## Capability

Use when a runnable throwaway experiment can resolve a specific design, state-model, algorithm, or UI question.

<!-- registry:generated traits -->
- `named-question`: Build a throwaway artifact to answer one named design question. (States the question and observable success before building.)
- `pick-form`: Let the question being answered pick the prototype's form, such as a state demo for logic or a UI mockup for layout. (The smallest runnable form, including a script for algorithms.)
- `throwaway-marked`: Keep prototypes clearly marked as throwaway and separate from production. (Also reproducible.)
- `trivial-to-run`: Make the prototype trivial to run: one command, or a single HTML file the user opens directly. (Documents the run command and expected signal; an HTML demo works offline.)
- `surface-state`: Surface the relevant state and the invalid transitions the design might mishandle.
- `scoped-data`: Use synthetic or appropriately scoped data, bringing in external calls and real integration only when the question needs them and they are authorized.
- `persistence-when-needed`: Bring persistence into a prototype only when the question needs it. (Also only when authorized.)
- `cheap-assertions`: Use a small assertion as the cheapest proof where it helps, since a prototype implies neither a full test suite nor a ban on checks.
- `logic-pure-module`: Keep domain logic readable apart from presentation as a reducer, state machine, pure functions or small stateful module.
- `logic-shareable-html`: Offer a self-contained HTML demo with the question, a readable state panel, controls and guided scenarios that reset to a known state. (Only the guided scenarios needed to expose the uncertainty.)
- `ui-contextual-preview`: Prefer an isolated preview, or an authorized existing-page preview that cannot leak into production, over a new live route.
- `variants-when-comparing`: Build UI variants only when comparing alternatives is the question the prototype answers.
- `structural-variants`: Make UI variants differ in meaningful structure and layout, not just colour or styling.
- `variant-switcher`: Provide a labelled control for switching between UI variants.
- `ui-keyboard-safety`: Keep a prototype's keyboard shortcuts from intercepting input while an editable field is focused.
- `ui-accessibility`: Keep focus, contrast and interaction states usable in a UI prototype while real mutations are stubbed.
- `capture-outcome`: Record the prototype's verdict and the question it settled, with a pointer to the preserved artifact. (Also records exercised cases and limitations; an inconclusive result is valid.)
- `separate-promotion`: Treat promoting a prototype's decision or code into production as separate work with its own scope and checks.
<!-- /registry:generated traits -->

<!-- registry:generated lineage -->
- **mattpocock_skills:skill:skills/engineering/prototype** `reference_harnesses/mattpocock_skills/skills/engineering/prototype/SKILL.md` @ 84fdeff
- **mattpocock_skills:skill:skills/engineering/prototype** `skills/engineering/prototype/SKILL.md`
<!-- /registry:generated lineage -->

<!-- registry:generated history -->
- `2026-08-13` **adopt** (2026-10-14-migration:119): Adopted verbatim per user ruling 2026-08-13 (SKILL + LOGIC + UI; their agents/openai.yaml metadata excluded). Both branches kept: UI.md stays behind progressiv…
- `2026-08-11` **adopt** (2026-10-14-migration:038) *(superseded)*: The only skill that answers a design question by building running throwaway code.
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
