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

Use when a runnable throwaway experiment can resolve a specific design, state-model, algorithm, or UI question.

**Boundary:** Builds a runnable throwaway experiment that answers one design question; the decision it informs belongs to codebase-design or domain-modeling.

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
- `self-contained-html-demo`: Offer an interactive demo as one self-contained HTML file that works offline. (Offered when a non-developer needs to manipulate states; offline when sharing is the goal.)
- `demo-states-question`: Include in a demo the question it answers.
- `readable-state-panel`: Show a demo's current state in a readable panel.
- `demo-state-controls`: Give a demo controls that drive its state.
- `resettable-demo-scenarios`: Give a demo guided scenarios that each reset to a known state. (Only the guided scenarios needed to expose the uncertainty.)
- `ui-contextual-preview`: Prefer an isolated preview, or an authorized existing-page preview that cannot leak into production, over a new live route.
- `variants-when-comparing`: Build UI variants only when comparing alternatives is the question the prototype answers.
- `structural-variants`: Make UI variants differ in meaningful structure and layout, not just colour or styling.
- `variant-switcher`: Provide a labelled control for switching between UI variants.
- `ui-keyboard-safety`: Keep a prototype's keyboard shortcuts from intercepting input while an editable field is focused.
- `ui-accessibility`: Keep focus, contrast and interaction states usable in a UI prototype while real mutations are stubbed.
- `capture-outcome`: Record the prototype's verdict and the question it settled, with a pointer to the preserved artifact. (Also records exercised cases and limitations; an inconclusive result is valid.)
- `separate-promotion`: Treat promoting a prototype's decision or code into production as separate work with its own scope and checks.
- `stubbed-mutations`: Point UI variants that need mutations at stubs rather than real backends.
- `production-hidden-switcher`: Hide a prototype's variant switcher from production builds.
<!-- /registry:generated traits -->

<!-- registry:generated lineage -->
- **mattpocock_skills:skill:skills/engineering/prototype#named-question** `skills/engineering/prototype/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2
- **mattpocock_skills:skill:skills/engineering/prototype#pick-form** `skills/engineering/prototype/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2
- **mattpocock_skills:skill:skills/engineering/prototype#state-question-up-front** `skills/engineering/prototype/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2
- **mattpocock_skills:skill:skills/engineering/prototype#throwaway-marked** `skills/engineering/prototype/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2
- **mattpocock_skills:skill:skills/engineering/prototype#trivial-to-run** `skills/engineering/prototype/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2
- **mattpocock_skills:skill:skills/engineering/prototype#persistence-when-needed** `skills/engineering/prototype/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2
- **mattpocock_skills:skill:skills/engineering/prototype#skip-polish** `skills/engineering/prototype/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2 (pending cr-axdt.6.7)
- **mattpocock_skills:skill:skills/engineering/prototype#surface-state** `skills/engineering/prototype/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2
- **mattpocock_skills:skill:skills/engineering/prototype#capture-outcome** `skills/engineering/prototype/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2
- **mattpocock_skills:skill:skills/engineering/prototype#structural-variants** `skills/engineering/prototype/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2
- **mattpocock_skills:skill:skills/engineering/prototype#ui-variants-one-route** `skills/engineering/prototype/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2
- **mattpocock_skills:skill:skills/engineering/prototype#ui-keyboard-safety** `skills/engineering/prototype/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2
- **mattpocock_skills:skill:skills/engineering/prototype#variant-switcher** `skills/engineering/prototype/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2
- **mattpocock_skills:skill:skills/engineering/prototype#domain-vocabulary** `skills/engineering/prototype/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2 (pending cr-axdt.6.7)
- **mattpocock_skills:skill:skills/engineering/prototype#production-hidden-switcher** `skills/engineering/prototype/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2
- **mattpocock_skills:skill:skills/engineering/prototype#handover-url-keys** `skills/engineering/prototype/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2 (pending cr-axdt.6.7)
- **mattpocock_skills:skill:skills/engineering/prototype#stubbed-mutations** `skills/engineering/prototype/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2
- **mattpocock_skills:skill:skills/engineering/prototype#portable-single-file-demo** `skills/engineering/prototype/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2
- **mattpocock_skills:skill:skills/engineering/prototype#dom-free-portable-logic** `skills/engineering/prototype/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2
- **mattpocock_skills:skill:skills/engineering/prototype#readable-state-panel** `skills/engineering/prototype/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2
- **mattpocock_skills:skill:skills/engineering/prototype#always-available-free-play** `skills/engineering/prototype/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2 (pending cr-axdt.6.7)
- **mattpocock_skills:skill:skills/engineering/prototype#resettable-guided-scenarios** `skills/engineering/prototype/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2 (pending cr-axdt.6.7)
- **mattpocock_skills:skill:skills/engineering/prototype#existing-variant-styling-system** `skills/engineering/prototype/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2 (pending cr-axdt.6.7)
<!-- /registry:generated lineage -->

<!-- registry:generated history -->
- `2026-10-30` **adopt-merged** (2026-10-30-mattpocock_skills-5beb35b:567): Checkpoint at 5beb35b for the owner's trait rulings: 23 adopt, 16 defer.
- `2026-10-30` **defer** (2026-10-30-mattpocock_skills-5beb35b:195): Owner deferred the report's reject recommendation, to review the set later: Component naming is an implementation detail; ours already labels variants clearly …
- `2026-10-30` **adopt** (2026-10-30-mattpocock_skills-5beb35b:194): Ours reuses project components and realistic content density (UI.md:3-5) but never requires new variant styling to use the project's existing styling system.
- `2026-10-30` **defer** (2026-10-30-mattpocock_skills-5beb35b:193): Owner deferred the report's reject recommendation, to review the set later: Ours deliberately uses safe fixtures or scoped read-only data with realistic densit…
- `2026-10-30` **defer** (2026-10-30-mattpocock_skills-5beb35b:192): Owner deferred the report's reject recommendation, to review the set later: Highlighting the latest change is a presentation nicety that changes no prototype d…
- `2026-10-30` **adopt** (2026-10-30-mattpocock_skills-5beb35b:191): Ours resets scenarios (LOGIC.md:13) but lets them drive state directly; stepping through the real controls makes a scenario exercise what the user will touch.
- `2026-10-30` **adopt** (2026-10-30-mattpocock_skills-5beb35b:190): Ours requires controls and resettable guided scenarios (LOGIC.md:12-13) but never keeps free play available while a scenario runs.
- `2026-10-30` **adopt** (2026-10-30-mattpocock_skills-5beb35b:189): Ours's HTML demo includes a readable state panel.
- `2026-10-30` **adopt** (2026-10-30-mattpocock_skills-5beb35b:188): Ours deliberately does not design prototype code for reuse, since promotion is separate work (SKILL.md:26-27).
- `2026-10-30` **adopt** (2026-10-30-mattpocock_skills-5beb35b:187): Ours deliberately keeps the format optional and offline (LOGIC.md:3-6, 14-15); the offline rule already removes the server and fetch risk a framework ban targe…
- `2026-10-30` **defer** (2026-10-30-mattpocock_skills-5beb35b:186): Owner deferred the report's reject recommendation, to review the set later: Ours preserves the artifact with a pointer (SKILL.md:24-28) and keeps committing be…
- `2026-10-30` **defer** (2026-10-30-mattpocock_skills-5beb35b:185): Owner deferred the report's reject recommendation, to review the set later: Opposite stance: ours makes production integration separate work, not part of finis…
- `2026-10-30` **adopt** (2026-10-30-mattpocock_skills-5beb35b:184): Ours stubs real mutations unless integration is the authorized subject.
- `2026-10-30` **defer** (2026-10-30-mattpocock_skills-5beb35b:183): Owner deferred the report's reject recommendation, to review the set later: Ours already requires variants to differ in meaningful structure (UI.md:13-14); a c…
- `2026-10-30` **defer** (2026-10-30-mattpocock_skills-5beb35b:182): Owner deferred the report's reject recommendation, to review the set later: Ours makes removal of production code separate authorized work (UI.md:20-21, SKILL.…
- `2026-10-30` **adopt** (2026-10-30-mattpocock_skills-5beb35b:181): Ours shows the preview or file pointer (UI.md:19-20) but not how to reach each variant, which the user needs to compare them.
- `2026-10-30` **adopt** (2026-10-30-mattpocock_skills-5beb35b:180): Ours requires an existing-page preview, switcher included, to be unable to leak into production.
- `2026-10-30` **defer** (2026-10-30-mattpocock_skills-5beb35b:179): Owner deferred the report's reject recommendation, to review the set later: This governs variants hosted in an existing page, which ours uses only by exception…
- `2026-10-30` **defer** (2026-10-30-mattpocock_skills-5beb35b:178): Owner deferred the report's reject recommendation, to review the set later: A written one-line plan before building variants is a recipe step (S-03); ours alre…
- `2026-10-30` **defer** (2026-10-30-mattpocock_skills-5beb35b:177): Owner deferred the report's reject recommendation, to review the set later: Ours makes promotion separate work with its own scope (SKILL.md:26-27); deciding wh…
- `2026-10-30` **defer** (2026-10-30-mattpocock_skills-5beb35b:176): Owner deferred the report's reject recommendation, to review the set later: Ours reuses the project's components and realistic density (UI.md:4), so the projec…
- `2026-10-30` **defer** (2026-10-30-mattpocock_skills-5beb35b:175): Owner deferred the report's reject recommendation, to review the set later: Ours keeps only the scenarios that expose the uncertainty, a representative path an…
- `2026-10-30` **adopt** (2026-10-30-mattpocock_skills-5beb35b:174): Ours asks for domain labels only in HTML demos (LOGIC.md:14); the same names in scripts and UI variants let the answer transfer to the real code.
- `2026-10-30` **defer** (2026-10-30-mattpocock_skills-5beb35b:173): Owner deferred the report's reject recommendation, to review the set later: AGENTS.md already says to decide routine details independently and ask only on mate…
- `2026-10-30` **adopt** (2026-10-30-mattpocock_skills-5beb35b:172): Ours offers a URL selector or small switcher with clearly labelled variants.
- `2026-10-30` **adopt** (2026-10-30-mattpocock_skills-5beb35b:171): Ours keeps keyboard controls from stealing input from editable fields.
- `2026-10-30` **defer** (2026-10-30-mattpocock_skills-5beb35b:170): Owner deferred the report's reject recommendation, to review the set later: Opposite stance: ours prefers an isolated preview and makes hosting in an existing …
- `2026-10-30` **adopt** (2026-10-30-mattpocock_skills-5beb35b:169): Ours deliberately picks a single mockup when testing one interaction (UI.md:3-4); a fixed three-to-five count is a quota (S-08).
- `2026-10-30` **adopt** (2026-10-30-mattpocock_skills-5beb35b:168): Ours varies meaningful structure or behaviour, not colour alone.
- `2026-10-30` **defer** (2026-10-30-mattpocock_skills-5beb35b:167): Owner deferred the report's reject recommendation, to review the set later: Opposite stance: ours allows promoting code as separate work, so a winning implemen…
- `2026-10-30` **adopt** (2026-10-30-mattpocock_skills-5beb35b:166): Ours records the outcome, cases, limits and an artifact pointer.
- `2026-10-30` **adopt** (2026-10-30-mattpocock_skills-5beb35b:165): Ours surfaces the relevant state and invalid transitions.
- `2026-10-30` **defer** (2026-10-30-mattpocock_skills-5beb35b:164): Owner deferred the report's reject recommendation, to review the set later: Opposite stance: ours permits small assertions and explicitly disclaims a ban on ch…
- `2026-10-30` **adopt** (2026-10-30-mattpocock_skills-5beb35b:163): Ours asks for the smallest runnable form (SKILL.md:8-9) but never tells the agent to skip polish; the line keeps the safety checks ours retains (SKILL.md:15) a…
- `2026-10-30` **adopt** (2026-10-30-mattpocock_skills-5beb35b:162): Ours adds persistence only when the question needs it and it is authorized.
- `2026-10-30` **adopt** (2026-10-30-mattpocock_skills-5beb35b:161): Ours documents the run command and expected signal, with an offline HTML file when sharing.
- `2026-10-30` **adopt** (2026-10-30-mattpocock_skills-5beb35b:160): Ours keeps prototypes marked, reproducible and separate from production.
- `2026-10-30` **adopt** (2026-10-30-mattpocock_skills-5beb35b:159): Ours deliberately states the question with its success signal (SKILL.md:12), which is the checkable part.
- `2026-10-30` **adopt** (2026-10-30-mattpocock_skills-5beb35b:158): Ours chooses the smallest runnable form by the question.
- `2026-10-30` **adopt** (2026-10-30-mattpocock_skills-5beb35b:157): Ours builds to answer a named question with observable success.
- `2026-08-13` **adopt** (2026-10-14-migration:119): Adopted verbatim per user ruling 2026-08-13 (SKILL + LOGIC + UI; their agents/openai.yaml metadata excluded). Both branches kept: UI.md stays behind progressiv…
- `2026-08-11` **adopt** (2026-10-14-migration:038) *(superseded)*: The only skill that answers a design question by building running throwaway code.
<!-- /registry:generated history -->

<!-- registry:generated reviews -->
None yet.
<!-- /registry:generated reviews -->

<!-- registry:generated sources -->
- `capture-outcome`:
  - `mattpocock_skills:skill:skills/engineering/prototype#capture-outcome` (adopted at 5beb35b040e3de97e54fa9e386d7e42d15c295c2)
- `logic-pure-module`:
  - `mattpocock_skills:skill:skills/engineering/prototype#dom-free-portable-logic` (adopted at 5beb35b040e3de97e54fa9e386d7e42d15c295c2)
- `named-question`:
  - `mattpocock_skills:skill:skills/engineering/prototype#named-question` (adopted at 5beb35b040e3de97e54fa9e386d7e42d15c295c2)
  - `mattpocock_skills:skill:skills/engineering/prototype#state-question-up-front` (adopted at 5beb35b040e3de97e54fa9e386d7e42d15c295c2)
- `persistence-when-needed`:
  - `mattpocock_skills:skill:skills/engineering/prototype#persistence-when-needed` (adopted at 5beb35b040e3de97e54fa9e386d7e42d15c295c2)
- `pick-form`:
  - `mattpocock_skills:skill:skills/engineering/prototype#pick-form` (adopted at 5beb35b040e3de97e54fa9e386d7e42d15c295c2)
- `production-hidden-switcher`:
  - `mattpocock_skills:skill:skills/engineering/prototype#production-hidden-switcher` (adopted at 5beb35b040e3de97e54fa9e386d7e42d15c295c2)
- `readable-state-panel`:
  - `mattpocock_skills:skill:skills/engineering/prototype#readable-state-panel` (adopted at 5beb35b040e3de97e54fa9e386d7e42d15c295c2)
- `self-contained-html-demo`:
  - `mattpocock_skills:skill:skills/engineering/prototype#portable-single-file-demo` (adopted at 5beb35b040e3de97e54fa9e386d7e42d15c295c2)
- `structural-variants`:
  - `mattpocock_skills:skill:skills/engineering/prototype#structural-variants` (adopted at 5beb35b040e3de97e54fa9e386d7e42d15c295c2)
- `stubbed-mutations`:
  - `mattpocock_skills:skill:skills/engineering/prototype#stubbed-mutations` (adopted at 5beb35b040e3de97e54fa9e386d7e42d15c295c2)
- `surface-state`:
  - `mattpocock_skills:skill:skills/engineering/prototype#surface-state` (adopted at 5beb35b040e3de97e54fa9e386d7e42d15c295c2)
- `throwaway-marked`:
  - `mattpocock_skills:skill:skills/engineering/prototype#throwaway-marked` (adopted at 5beb35b040e3de97e54fa9e386d7e42d15c295c2)
- `trivial-to-run`:
  - `mattpocock_skills:skill:skills/engineering/prototype#trivial-to-run` (adopted at 5beb35b040e3de97e54fa9e386d7e42d15c295c2)
- `ui-keyboard-safety`:
  - `mattpocock_skills:skill:skills/engineering/prototype#ui-keyboard-safety` (adopted at 5beb35b040e3de97e54fa9e386d7e42d15c295c2)
- `variant-switcher`:
  - `mattpocock_skills:skill:skills/engineering/prototype#variant-switcher` (adopted at 5beb35b040e3de97e54fa9e386d7e42d15c295c2)
- `variants-when-comparing`:
  - `mattpocock_skills:skill:skills/engineering/prototype#ui-variants-one-route` (adopted at 5beb35b040e3de97e54fa9e386d7e42d15c295c2)
<!-- /registry:generated sources -->

<!-- registry:generated declined -->
- `mattpocock_skills:skill:skills/engineering/prototype#automatic-decision-integration` (defer): Owner deferred the report's reject recommendation, to review the set later: Opposite stance: ours makes production integration separate work, not part of finis…
- `mattpocock_skills:skill:skills/engineering/prototype#default-form-by-context` (defer): Owner deferred the report's reject recommendation, to review the set later: AGENTS.md already says to decide routine details independently and ask only on mate…
- `mattpocock_skills:skill:skills/engineering/prototype#fetch-above-switcher` (defer): Owner deferred the report's reject recommendation, to review the set later: This governs variants hosted in an existing page, which ours uses only by exception…
- `mattpocock_skills:skill:skills/engineering/prototype#helpful-state-change-highlighting` (defer): Owner deferred the report's reject recommendation, to review the set later: Highlighting the latest change is a presentation nicety that changes no prototype d…
- `mattpocock_skills:skill:skills/engineering/prototype#host-in-existing-page` (defer): Owner deferred the report's reject recommendation, to review the set later: Opposite stance: ours prefers an isolated preview and makes hosting in an existing …
- `mattpocock_skills:skill:skills/engineering/prototype#keep-logic-discard-shell` (defer): Owner deferred the report's reject recommendation, to review the set later: Ours makes promotion separate work with its own scope (SKILL.md:26-27); deciding wh…
- `mattpocock_skills:skill:skills/engineering/prototype#losing-variant-cleanup` (defer): Owner deferred the report's reject recommendation, to review the set later: Ours makes removal of production code separate authorized work (UI.md:20-21, SKILL.…
- `mattpocock_skills:skill:skills/engineering/prototype#named-variant-components` (defer): Owner deferred the report's reject recommendation, to review the set later: Component naming is an implementation detail; ours already labels variants clearly …
- `mattpocock_skills:skill:skills/engineering/prototype#no-shared-variant-layout` (defer): Owner deferred the report's reject recommendation, to review the set later: Ours already requires variants to differ in meaningful structure (UI.md:13-14); a c…
- `mattpocock_skills:skill:skills/engineering/prototype#no-tests-ban` (defer): Owner deferred the report's reject recommendation, to review the set later: Opposite stance: ours permits small assertions and explicitly disclaims a ban on ch…
- `mattpocock_skills:skill:skills/engineering/prototype#prototype-branch-archive` (defer): Owner deferred the report's reject recommendation, to review the set later: Ours preserves the artifact with a pointer (SKILL.md:24-28) and keeps committing be…
- `mattpocock_skills:skill:skills/engineering/prototype#rewrite-not-promote` (defer): Owner deferred the report's reject recommendation, to review the set later: Opposite stance: ours allows promoting code as separate work, so a winning implemen…
- `mattpocock_skills:skill:skills/engineering/prototype#scenario-coverage-triad` (defer): Owner deferred the report's reject recommendation, to review the set later: Ours keeps only the scenarios that expose the uncertainty, a representative path an…
- `mattpocock_skills:skill:skills/engineering/prototype#variant-plan-line` (defer): Owner deferred the report's reject recommendation, to review the set later: A written one-line plan before building variants is a recipe step (S-03); ours alre…
- `mattpocock_skills:skill:skills/engineering/prototype#variant-purpose-data-fidelity` (defer): Owner deferred the report's reject recommendation, to review the set later: Ours deliberately uses safe fixtures or scoped read-only data with realistic densit…
- `mattpocock_skills:skill:skills/engineering/prototype#visual-restraint` (defer): Owner deferred the report's reject recommendation, to review the set later: Ours reuses the project's components and realistic density (UI.md:4), so the projec…
<!-- /registry:generated declined -->
