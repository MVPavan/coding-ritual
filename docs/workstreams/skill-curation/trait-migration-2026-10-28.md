# Trait migration mapping (2026-10-28)

Evidence for the one-time migration in `docs/workstreams/skill-curation/traits-design.md` §8:
every old item (our skills' Covers lines and the Pocock pilot's idea subjects) and the final
trait ID(s) it became in `harness_lifecycle/registry/trait-definitions.yaml` and
`harness_lifecycle/registry/traits.yaml`. Three blind extractions of our 36 skills and two
of Pocock's 25 skills (658 draft definitions) were deduplicated across batches, then Pocock
was mapped onto our vocabulary: 597 definitions, 429 from our
skills and 168 new from Pocock. Our lists went from 398 draft items to
448 traits. Marks: match, split, merge, dropped, new; every non-match carries a reason.
"Merge pass" reasons record the cross-batch dedupe and the splits forced by Pocock's finer
traits. "r1" reasons record the fixes for critic round 1
(`scratchpad/traits-migration/sol-review-r1.md` findings 15–21) and its sweep, and "r2" reasons the fixes for critic round 2
(`scratchpad/traits-migration/sol-review-r2.md` findings 3–7): a shared ID
stays only where both sides provide every clause of its definition; otherwise the shared
core keeps the ID and each side's differing clause became its own trait or a skill note.
Pending critic review (§8 step 6). The 2026-10-29 Pocock rulings added no ID merges: 26 `distinct_from` links on our traits (variants of upstream traits), the two planning rows marked 2026-10-29 below, and two traits extracted in critic round r1 (`decision-relevance-pruning`, `established-notes`; our lists now total 452 traits).

Round-1 renames and replacements carried into the re-keyed pilot drafts
(`scratchpad/traits-migration/pilot-rekeyed/`):

- `recommend-with-assumptions` → `recommended-answer` (subject and `into`).
- `depth-and-delegation` → `decision-sufficient-stop`, `sizeable-delegation` (`into` of
  research#background-agent).
- `spacing-interleaving` → `spacing`, `interleaving` (teach subject split in two).
- Upstream-only replacements: diagnosing-bugs `locate-cost` → `perf-bisection`; prototype
  `scoped-data` → `persistence-when-needed`, `ui-contextual-preview` → `host-in-existing-page`;
  teach `level-adaptation` → `proximal-next-lesson` (now `into: level-adaptation` with a
  modification); wait-what `multi-context-map` → `context-map-lookup`.
- `into` retargeted: wayfinder#no-triage-labels → `label-free-typing`;
  improve-codebase-architecture#vocabulary-ban → `project-term-allowance`.
- Dropped from ours (routing): `scope-measured`, `boundary-debugging`.
- Round 2: `no-mirror-or-tautology` → `no-implementation-coupling` (tdd subject renamed);
  tdd `mock-boundaries` → `system-boundary-mocks-only` (now `into: mock-boundaries` with a
  modification).

## Our skills: Covers items

Old item is `ours:<skill>#<Covers slug>`; `(new mechanism)` rows are traits the Covers list missed.

| Old item | Final trait(s) | Mark | Reason |
|---|---|---|---|
| `ours:agent-matrix#catalog-source` | `catalog-source` | match |  |
| `ours:agent-matrix#validate-selection` | `validate-selection` | match |  |
| `ours:agent-matrix#inherit-defaults` | `inherit-defaults` | match |  |
| `ours:agent-matrix#layer-placement` | `layer-placement` | match |  |
| `ours:agent-matrix#three-reaches` | `three-reaches` | match |  |
| `ours:agent-matrix#no-definition-sprawl` | `no-definition-sprawl` | match |  |
| `ours:agent-matrix#context-modes` | `context-modes` | match |  |
| `ours:agent-matrix#fork-overrides` | `fork-overrides` | match |  |
| `ours:agent-matrix#effective-tools` | `effective-tools` | match |  |
| `ours:agent-matrix#effort-unverified` | `effort-unverified` | match |  |
| `ours:agent-matrix#preserve-role-prompt` | `preserve-role-prompt` | match |  |
| `ours:agent-matrix#report-resolution` | `report-resolution` | match |  |
| `ours:authoring-for-agents#surface-choice` | `surface-choice` | match |  |
| `ours:authoring-for-agents#activation-boundary` | `activation-boundary` | match |  |
| `ours:authoring-for-agents#inline-vs-disclose` | `inline-vs-disclose` | match |  |
| `ours:authoring-for-agents#outputs-and-authority` | `outputs-and-authority` | match | recipes-vs-judgment clause moved to precision-and-discretion to remove the overlap (rule 2) |
| `ours:authoring-for-agents#one-effective-instruction` | `one-effective-instruction` | match |  |
| `ours:authoring-for-agents#context-pointers` | `context-pointers` | match |  |
| `ours:authoring-for-agents#two-loads` | `two-loads` | match |  |
| `ours:authoring-for-agents#precision-and-discretion` | `completion-criteria-clarity`, `precision-and-discretion` | split | absorbs the recipes-vs-judgment mechanism previously bundled in outputs-and-authority; merge pass: `precision-and-discretion` split: bundled checkable completion criteria with matching prescription to fragility |
| `ours:authoring-for-agents#pruning` | `single-source-of-truth`, `environment-as-cache`, `no-op-deletion`, `unsupported-claim-removal` | split | merge pass: `pruning` split: bundled four pruning disciplines, each ruled separately upstream |
| `ours:authoring-for-agents#skill-anatomy` | `skill-packaging`, `invocation-mode`, `invocation-sidecar-sync`, `compatibility-alias` | split | the anatomy reference bundles three separable mechanisms: directory/frontmatter packaging, the model-vs-manual invocation choice, and thin compatibility aliases; r1 sweep: the flag-plus-sidecar regeneration split out of invocation-mode as invocation-sidecar-sync, since upstream shares only the invocation choice |
| `ours:authoring-for-agents#verification` | `verification` | match |  |
| `(new mechanism)` | `decision-relevance-pruning` | new | 2026-10-29 Pocock rulings r1: writing-principles.md:29-30 keeps only what changes decisions (conventions, failure modes, interfaces, invariants); neither `no-op-deletion` (default behaviour) nor upstream `relevance-check` (task bearing and staleness) is that test. |
| `ours:beads#work-types` | `bead-type-taxonomy` | match |  |
| `ours:beads#field-roles` | `field-roles` | match |  |
| `ours:beads#waits-as-edges` | `wait-as-edge` | match |  |
| `ours:beads#actor-discipline` | `actor-identity` | match | the close-with-evidence clause lives in session-close, not here |
| `ours:beads#resume-line` | `resume-line` | match |  |
| `ours:beads#session-close` | `session-close` | match |  |
| `ours:beads#recovery` | `session-recovery` | match |  |
| `ours:beads#git-authority` | — | dropped | restated repository git-authority policy, excluded by rule 3 |
| `ours:beads#knowledge-in-files` | `knowledge-in-files` | match |  |
| `ours:beads#setup-join` | `beads-setup` | match |  |
| `ours:beads#workstream-tracking` | `workstream-render` | match |  |
| `(new mechanism)` | `status-model` | new | usage.md §4 status model (review status, deferred-as-backlog, never hand-set blocked) was absent from the coarse Covers list |
| `(new mechanism)` | `triage-routing` | new | usage.md §10 triage routing and priority scale were not represented |
| `(new mechanism)` | `durable-unit-scope` | new | usage.md §1/§8 scope rules (one durable unit per bead, search-first, discovered-from) were not represented |
| `(new mechanism)` | `review-as-task` | new | usage.md §12 review-as-dependency-task mechanism was not represented |
| `(new mechanism)` | `phase-epic-contract` | new | usage.md §7 phase-epic status-renderer contract was not represented separately from workstream rendering |
| `(new mechanism)` | `destructive-command-guard` | new | usage.md §17 ban on deleting commands was not represented |
| `(new mechanism)` | `repeated-procedures` | new | usage.md §18 wisps and formulas were not represented |
| `(new mechanism)` | `dolt-sync` | new | usage.md §15 durable-sync model (Dolt source of truth, jsonl mirror, bootstrap) was not represented |
| `ours:brainstorming#route-before-grounding` | `match-interaction-to-ambiguity` | match | the bare hand-off to the grilling skill is dropped as routing; the interaction-depth decision is kept |
| `ours:brainstorming#synthesize-settled` | `synthesize-settled` | match |  |
| `ours:brainstorming#read-relevant-context` | `scoped-context-read`, `reuse-before-new` | split | scoped reading and naming the closest existing solution are two separable mechanisms |
| `ours:brainstorming#resolve-decisions` | `decision-frame`, `options-with-tradeoffs` | split | establishing the decision frame and presenting options-with-tradeoffs are distinct mechanisms |
| `ours:brainstorming#spec-template` | `spec-template`, `spec-criteria-and-questions`, `none-keeps-heading` | split | r1 sweep: spec-template narrowed to the skeleton upstream shares; our extra success-criteria and open-questions sections and the keep-every-heading rule are separate traits |
| `ours:brainstorming#testing-decisions` | `testing-seam-decision` | match |  |
| `ours:brainstorming#spec-no-paths` | `no-stale-file-paths`, `no-stale-code-snippets` | split | merge pass: `spec-no-paths` split: file paths and code snippets are separate rules upstream |
| `ours:brainstorming#prototype-snippet-exception` | `prototype-snippet` | match |  |
| `ours:brainstorming#approval-gate` | `spec-approval-gate`, `material-risk-review` | split | the draft-until-approved gate and the material-risk critic review are separately rulable |
| `ours:brainstorming#interview-method` | `question-batching`, `recommended-answer`, `settled-stop`, `self-serve-facts`, `approval-interpretation`, `observable-outcomes` | split | interviewing.md bundles six distinct interview mechanisms, four of which are shared with grilling; r1 sweep: recommend-with-assumptions renamed recommended-answer, assumption labelling now a skill note |
| `ours:brainstorming#exploration-lenses` | `structured-divergence`, `exploration-lenses` | split | the exploration method and the optional ideation lenses are separable |
| `ours:brainstorming#inline-diagrams` | `inline-diagrams`, `visuals-into-spec` | split | drawing inline diagrams and carrying an approved visual into the durable spec are distinct mechanisms |
| `ours:brainstorming#html-mockup-on-request` | `html-mockup-on-request` | match |  |
| `ours:grilling#map-decisions` | `map-decisions` | match |  |
| `ours:grilling#frontier-batches` | `question-batching` | match | renamed to the shared interview trait also used by brainstorming |
| `ours:grilling#recommend-answer` | `recommended-answer` | match | renamed to the shared interview trait also used by brainstorming; r1 sweep: renamed from recommend-with-assumptions; upstream attaches no labelled assumptions, so that clause is a skill note |
| `ours:grilling#facts-yourself` | `self-serve-facts` | match | renamed to the shared interview trait also used by brainstorming |
| `ours:grilling#stop-when-settled` | `settled-stop` | match | renamed to the shared interview trait also used by brainstorming |
| `ours:grilling#absent-respondent` | `absent-respondent`, `grill-the-send`, `gap-targeted-questions` | split | merge pass: `absent-respondent` split: bundled the questionnaire fallback with asking only about the send and gap-targeted questions |
| `ours:grilling#request-gated` | `interview-not-authority` | split | the explicit-request activation trigger is dropped as routing; the authority gate (an interview or questionnaire is not implementation or send authority) is kept |
| `ours:grilling#optional-docs` | `optional-docs` | match |  |
| `(new mechanism)` | `decision-summary` | new | the grill-me alias ships a decision-summary template (references/decision-summary-template.md) absent from the grilling Covers list |
| `ours:harness-evaluate#read-first` | `read-first` | match |  |
| `ours:harness-evaluate#decision-dimensions` | `decision-dimensions` | match |  |
| `ours:harness-evaluate#disposition-choice` | `disposition-choice` | match |  |
| `ours:harness-evaluate#recommendation-vs-record` | `recommendation-vs-record` | match |  |
| `ours:harness-evaluate#record-command` | `record-command` | match |  |
| `ours:harness-evaluate#edit-canonical-source` | `edit-canonical-source` | match |  |
| `ours:harness-evaluate#template-adoption-gate` | `template-adoption-gate` | match |  |
| `ours:harness-evaluate#independent-review` | `material-risk-review` | merge | merge pass: `independent-review` → `material-risk-review`: same mechanism as brainstorming's material-risk-review: an independent critic when risk or blast radius is material |
| `ours:harness-evaluate#adopt-after-state-exists` | `adopt-after-state-exists` | match |  |
| `ours:harness-evaluate#codex-direct` | `codex-direct` | match |  |
| `ours:harness-evaluate#boundary-harness-skill-compare` | — | dropped | bare hand-off to harness-skill-compare, excluded as routing by rule 3 |
| `ours:harness-publish#manual-root-only` | `manual-root-only` | match |  |
| `ours:harness-publish#prerequisites-scope` | `prerequisites-scope` | match |  |
| `ours:harness-publish#repo-context-check` | `repo-context-check` | match |  |
| `ours:harness-publish#authority-separation` | `authority-separation` | match |  |
| `ours:harness-publish#preflight-gates` | `preflight-gates` | match |  |
| `ours:harness-publish#dry-run` | `dry-run` | match |  |
| `ours:harness-publish#publish-bump` | `publish-bump` | match |  |
| `ours:harness-publish#plugin-repo-review` | `plugin-repo-review` | match |  |
| `ours:harness-publish#submodule-pointer` | `submodule-pointer` | match |  |
| `ours:harness-publish#failure-table` | `failure-table` | match |  |
| `ours:harness-publish#never-edit-build-output` | `never-edit-build-output` | match |  |
| `ours:harness-scan#resolve-target` | `resolve-target` | match |  |
| `ours:harness-scan#drift-scan` | `drift-scan` | match |  |
| `ours:harness-scan#gap-report` | `gap-report` | match |  |
| `ours:harness-scan#material-report` | `material-report` | match |  |
| `ours:harness-scan#upstream-review-on-pin-move` | `upstream-review-on-pin-move` | match |  |
| `ours:harness-scan#no-authority` | — | dropped | bare authority-boundary restatement (scanning authorizes no records), excluded by rule 3 |
| `ours:harness-scan#beads-followup` | `beads-followup` | match |  |
| `ours:harness-scan#pin-preserving-offline` | `pin-preserving-fetch` | merge | unified with harness-status#fetch-not-pin into one shared pin-preserving-fetch trait (pins never move; no-fetch skips the network) |
| `ours:harness-scan#reject-valid` | `reject-valid` | match |  |
| `ours:harness-scan#boundary-harness-evaluate` | — | dropped | bare hand-off to harness-evaluate, excluded as routing by rule 3 |
| `ours:harness-status#per-harness-drift` | `drift-scan` | merge | merge pass: `per-harness-drift` → `drift-scan`: same drift-scan mechanism as harness-scan, run for every harness; overlap audit #12 |
| `ours:harness-status#summary-table` | `summary-table` | match |  |
| `ours:harness-status#scan-candidates` | `scan-candidates` | match |  |
| `ours:harness-status#fetch-not-pin` | `pin-preserving-fetch` | merge | unified with harness-scan#pin-preserving-offline into the shared pin-preserving-fetch trait |
| `ours:harness-status#offline-continue` | `offline-continue` | match |  |
| `ours:harness-status#concise-output` | `concise-output` | match |  |
| `ours:harness-skill-compare#scale-to-question` | `scale-to-question` | match |  |
| `ours:harness-skill-compare#inspected-vs-executed` | `inspected-vs-executed` | match |  |
| `ours:harness-skill-compare#registry-consult` | `registry-consult` | match |  |
| `ours:harness-skill-compare#skill-review-file` | `skill-review-file` | match | absorbs the review's opening set and the later evidence-citation linkage |
| `ours:harness-skill-compare#review-sections` | `skill-review-file`, `presence-matrix` | merge | the fixed ordered parts deduplicate into the review-file structure (set/order) and the matrix trait (matrix/differences) rather than being a standalone trait (rule 2) |
| `ours:harness-skill-compare#component-granularity` | `component-inventory` | match | renamed to component-inventory |
| `ours:harness-skill-compare#presence-matrix` | `presence-matrix` | match | absorbs the differences section (explaining each variant row) |
| `ours:harness-skill-compare#verdict` | `verdict` | match |  |
| `ours:harness-skill-compare#narrow-stays-in-chat` | `narrow-stays-in-chat` | match |  |
| `ours:harness-skill-compare#read-only` | — | dropped | restated read-only authority boundary, excluded by rule 3 |
| `ours:harness-skill-compare#boundary-harness-evaluate` | — | dropped | bare hand-off to harness-evaluate (routing); its evidence-citation nuance folded into skill-review-file |
| `ours:html-artifact#trigger-gated` | — | dropped | restates the skill's activation trigger (its description), excluded as routing by rule 3 |
| `ours:html-artifact#self-contained-contract` | `self-contained-contract` | match |  |
| `ours:html-artifact#accessibility-contract` | `accessibility-contract` | match |  |
| `ours:html-artifact#progressive-enhancement` | `progressive-enhancement` | match |  |
| `ours:html-artifact#honest-content` | `honest-content` | match |  |
| `ours:html-artifact#preset-report` | `preset-report` | match |  |
| `ours:html-artifact#preset-dashboard` | `preset-dashboard` | match |  |
| `ours:html-artifact#preset-explainer` | `preset-explainer` | match |  |
| `ours:html-artifact#preset-editor` | `preset-editor` | match |  |
| `ours:html-artifact#visual-style` | `tokens-first-style`, `component-vocabulary` | split | the optional aesthetic (tokens) and the component vocabulary are separable mechanisms |
| `ours:html-artifact#svg-craft` | `svg-figure-grammar`, `svg-complexity-budget`, `svg-accessibility`, `honest-data-encoding` | split | svg-craft.md bundles figure geometry, a complexity budget, an SVG accessibility contract and chart honest-data rules |
| `ours:html-artifact#deliver-verify` | `deliver-verify` | match |  |
| `ours:i-have-adhd#next-action-first` | `next-action-first` | match |  |
| `ours:i-have-adhd#numbered-steps` | `numbered-steps` | match |  |
| `ours:i-have-adhd#one-next-action` | `single-next-action` | match |  |
| `ours:i-have-adhd#suppress-tangents` | `tangent-suppression` | match |  |
| `ours:i-have-adhd#restate-state` | `state-restatement` | match |  |
| `ours:i-have-adhd#concrete-time-estimates` | `concrete-time-estimates` | match |  |
| `ours:i-have-adhd#visible-progress` | `visible-progress` | match |  |
| `ours:i-have-adhd#matter-of-fact-errors` | `matter-of-fact-errors` | match |  |
| `ours:i-have-adhd#cap-lists` | `capped-lists` | match |  |
| `ours:i-have-adhd#no-preamble` | `no-preamble` | match |  |
| `ours:i-have-adhd#break-rules-overrides` | `explain-on-request`, `debug-spiral-reset`, `repitch-trigger`, `controlled-language`, `domain-vocabulary` | split | The five override cases are distinct mechanisms; destructive-action confirmation and real-ambiguity clarification are restated repository policy and dropped.; merge pass: `controlled-language-repitch` split: bundled the re-pitch trigger, controlled language, and keeping the project's terms |
| `ours:i-have-adhd#pre-send-check` | `pre-send-check` | match |  |
| `ours:migrate-claude-to-codex#dry-run-default` | `dry-run-default` | match |  |
| `ours:migrate-claude-to-codex#skill-linking` | `skill-symlinking` | match |  |
| `ours:migrate-claude-to-codex#destination-protection` | `destination-protection` | match |  |
| `ours:migrate-claude-to-codex#command-conversion` | `command-conversion` | match |  |
| `ours:migrate-claude-to-codex#agent-conversion` | `agent-conversion` | match |  |
| `ours:migrate-claude-to-codex#hook-mapping` | `hook-conversion` | match |  |
| `ours:migrate-claude-to-codex#defaults-scaffold` | `config-scaffold` | match |  |
| `ours:migrate-claude-to-codex#shared-policy-preserved` | `shared-policy-untouched` | match |  |
| `ours:migrate-claude-to-codex#verify-structure` | `structural-verify` | match |  |
| `ours:migrate-claude-to-codex#no-destructive` | `non-destructive` | match |  |
| `ours:migrate-claude-to-codex#self-test` | `test-before-reliance` | match |  |
| `ours:migrate-claude-to-codex#mapping-reference` | — | dropped | A pointer to the mapping reference document; the mappings themselves are realized by the conversion traits, so the pointer adds no mechanism. |
| `ours:model-council#trigger-explicit` | — | dropped | Restates the skill's activation trigger (its description), which is routing, not a trait. |
| `ours:model-council#resolve-members` | `member-resolution` | match |  |
| `ours:model-council#runtime-capability-check` | `runtime-capability-check` | match |  |
| `ours:model-council#codex-direct` | `codex-direct` | merge | merge pass: `codex-direct-dispatch` → `codex-direct`: same rule as harness-evaluate's codex-direct (call the Codex CLI directly); overlap audit #14 |
| `ours:model-council#neutral-brief` | `neutral-framing` | match | Same mechanism as perspective-council's neutral framing; unified into one shared trait. |
| `ours:model-council#independent-dispatch` | `member-isolation`, `report-preservation` | split | Bundles member isolation (independence) and preservation of every attributed report, two mechanisms rulable separately. |
| `ours:model-council#judge-synthesis` | `independent-synthesis` | match | Same mechanism as perspective-council's chair synthesis; unified into one shared trait. |
| `ours:model-council#deliver-consolidation` | `consolidated-delivery` | match |  |
| `ours:model-council#record-identities` | `identity-recording` | match |  |
| `ours:model-council#failed-member` | `failed-member-recovery`, `no-silent-substitution` | split | Bundles bounded recovery of a failed member and the never-backfill honesty rule (shared with perspective-council). |
| `ours:model-council#no-implement` | — | dropped | Restates repository policy that analysis requests carry no implementation authority. |
| `ours:perspective-council#trigger-explicit` | — | dropped | Restates the skill's activation trigger (its description), which is routing, not a trait. |
| `ours:perspective-council#boundary-model-council` | — | dropped | A bare hand-off directing named-model councils to model-council; routing, not a trait. |
| `ours:perspective-council#declared-scale` | `declared-scale` | match |  |
| `ours:perspective-council#lens-set` | `opposing-lens-set` | match |  |
| `ours:perspective-council#neutral-framing` | `neutral-framing`, `member-isolation` | split | Bundles neutral framing of the question and advisor isolation (each sees only its lens, not other outputs). |
| `ours:perspective-council#evidence-calibration` | `evidence-calibration` | match |  |
| `ours:perspective-council#anonymized-peer-review` | `anonymized-peer-review` | match |  |
| `ours:perspective-council#chair-synthesis` | `independent-synthesis` | match | Same mechanism as model-council's judge synthesis; unified into one shared trait with a skill note. |
| `ours:perspective-council#configured-agents` | `no-silent-substitution` | split | Its honest unavailable-pass reporting is the no-silent-substitution mechanism; the use-permitted-agents-and-delegation-policy clause restates repository policy and is dropped. |
| `ours:perspective-council#no-authority` | `transcript-on-request` | split | The save-transcript-only-when-requested clause is kept; the no-implementation-or-external-message-authority clause restates repository policy and is dropped. |
| `ours:research#scope-the-question` | `decision-framing` | match |  |
| `ours:research#primary-sources` | `primary-source-preference`, `source-version-dating`, `vendor-claim-testing` | split | r1 sweep: bundled primary-source preference, version and date recording, and independent testing of vendor claims; upstream shares only the first |
| `ours:research#weigh-and-separate` | `evidence-separation` | match |  |
| `ours:research#cited-artifact` | `cited-artifact`, `scaled-report` | split | r1 sweep: citation binding is shared with upstream; answering at the requested scale and saving a report only when useful is ours (upstream always writes a file) |
| `ours:research#depth-and-delegation` | `decision-sufficient-stop`, `sizeable-delegation` | split | r1 finding 18: bundled the stopping rule and the delegation policy |
| `ours:research#frameworks` | `judgment-frameworks` | match |  |
| `(new mechanism)` | `source-weighting` | new | references/source-selection.md adds weighting source types to the claim's domain, distinct from primary-source preference. |
| `(new mechanism)` | `disconfirming-red-team` | new | SKILL body and references/synthesis-engine.md require surfacing the strongest counterargument and reversal conditions. |
| `(new mechanism)` | `structured-synthesis` | new | references/synthesis-engine.md adds a claim table and pattern scan turning facts into decision-relevant implications. |
| `(new mechanism)` | `research-playbooks` | new | references/playbooks.md adds domain-matched research sequences. |
| `ours:review#critic-role` | `independent-critic-verdict` | match |  |
| `ours:review#severity-and-verdict` | `severity-and-verdict` | match |  |
| `ours:review#scope-and-evidence` | `scope-establishment`, `pre-existing-edit-separation`, `callers-and-evidence`, `mechanical-gate-precedence` | split | Bundles scope establishment, reading callers and treating reports as evidence, and mechanical-gate precedence — three separately rulable mechanisms.; r1 sweep: separating pre-existing edits split out of scope-establishment, which upstream lacks |
| `ours:review#requirements-vs-quality` | `requirements-before-quality`, `distinct-axis-verdicts` | split | merge pass: `requirements-before-quality` split: bundled the requirements-first order with separate per-axis verdicts; the second is shared with an upstream trait |
| `ours:review#modes` | `verdict-contract`, `re-review-finding-tracking` | split | The mode list is an index; its distinct mechanisms are the dispatched verdict contract and re-review finding tracking (references/review-contract.md), while inline/spec/quality, document and feedback modes restate other traits. |
| `ours:review#document-review` | `document-review` | match |  |
| `ours:review#feedback` | `finding-adjudication` | merge | merge pass: `feedback-application` → `finding-adjudication`: same mechanism as execution's finding-adjudication (verify each incoming finding, dispose of each visibly); overlap audit #5, review owns it |
| `(new mechanism)` | `test-quality-judgment` | new | references/code.md judges tests by independent-expectation failure detection and does not treat test changes as inherent defects. |
| `(new mechanism)` | `actionable-defects-only` | new | references/code.md requires reporting only actionable defects, deferring formatting, and stating when none are found. |
| `(new mechanism)` | `read-only-isolation` | new | references/code.md requires a read-only review to preserve checkout, index and refs, using isolated facilities for mutating checks. |
| `ours:show-me#smallest-view` | `smallest-view` | match |  |
| `ours:show-me#visual-forms` | `visual-form-catalog` | match |  |
| `ours:show-me#diff-shaped` | `structural-diff` | match |  |
| `ours:show-me#placement` | `visual-placement`, `real-code-names` | split | Bundles placing each visual after its sentence and using real code names rather than placeholders. |
| `ours:show-me#terminal-and-table` | `medium-appropriate-form` | match |  |
| `ours:show-me#html-handoff` | `html-handoff` | match |  |
| `ours:skill-router#need-route-table` | `need-to-skill-routing` | match |  |
| `ours:skill-router#narrowest-contract` | `narrowest-contract` | match |  |
| `ours:skill-router#overlap-arbitration` | `overlap-arbitration` | match |  |
| `ours:skill-router#legacy-entrypoint-guidance` | `legacy-entrypoint-flagging` | match |  |
| `ours:skill-router#catalog-trust-boundary` | `catalog-trust-boundary` | match |  |
| `ours:teach#learning-shape` | `learning-shape` | match |  |
| `ours:teach#level-inference` | `level-adaptation`, `what-vs-why` | split | Bundles inferring and adapting to the learner's level and the separate discipline of separating what happened from why. |
| `ours:teach#teaching-workspace` | `teaching-workspace`, `authorized-course-location` | split | r1 finding 17: the course workspace is shared; opening it only for a requested course in an authorized location is ours |
| `ours:teach#mission-grounding` | `mission-grounding` | match |  |
| `ours:teach#glossary-format` | `glossary-format`, `glossary-admission-on-use` | split | merge pass: `glossary-building` split: term-entry format is domain-modeling's glossary-format (overlap audit #10); teach keeps its admission gate |
| `ours:teach#learning-records` | `learning-records` | match |  |
| `ours:teach#resources-format` | `resources-curation` | match |  |
| `ours:teach#lessons-and-assets` | `lesson-format`, `reusable-assets` | split | merge pass: `lessons-and-assets` split: bundled lesson shape and asset reuse |
| `ours:teach#quiz-answer-hygiene` | `quiz-answer-hygiene` | match |  |
| `ours:teach#retrieval-practice` | `retrieval-practice` | match |  |
| `ours:teach#scope-discipline` | `scope-discipline` | match |  |
| `(new mechanism)` | `sourced-explanations` | new | SKILL body and RESOURCES-FORMAT.md require drawing explanations from trusted cited sources rather than unverified recall. |
| `ours:triage#beads-native-states` | `triage-routing` | merge | Merged with #outcomes: the Beads-native state model and the fixed outcome set are one mechanism — outcomes expressed in Beads natives with no intake labels.; merge pass: `beads-native-outcomes` → `triage-routing`: same outcome model as beads' triage-routing (one outcome in tracker-native fields, no intake labels) |
| `ours:triage#show-attention` | `attention-buckets` | match |  |
| `ours:triage#triage-one` | `triage-decision`, `established-notes`, `triage-resume-notes` | split | Mapped to the decide/apply/record core; its enumerated redundancy, prior-rejection and verify sub-steps are their own traits.; merge pass: `triage-decision` split: bundled deciding within authority with recording what was settled for resumption; 2026-10-29 Pocock rulings r1: recording (`bd note … "Established: …"`, triage/SKILL.md:58-59) split from resuming (:32-33) as `established-notes` |
| `ours:triage#redundancy-and-prior-rejection` | `redundancy-check`, `prior-rejection-check` | split | Bundles the codebase redundancy search and the closed-bead prior-rejection search, two distinct checks. |
| `ours:triage#verify-claim` | `claim-verification` | match |  |
| `ours:triage#agent-ready-gate` | `agent-ready-gate` | match |  |
| `ours:triage#outcomes` | `triage-routing` | merge | Merged with #beads-native-states into one outcome-model trait.; merge pass: `beads-native-outcomes` → `triage-routing`: same outcome model as beads' triage-routing (one outcome in tracker-native fields, no intake labels) |
| `ours:wayfinder#decision-map` | `decision-map-epic`, `plan-not-do`, `dependency-edges` | split | merge pass: `decision-map-epic` split: bundled the map epic, decisions-not-build-slices, and native prerequisite edges (planning's dependency-edges) |
| `ours:wayfinder#index-not-store` | `map-as-index`, `map-body-sections` | split | merge pass: `map-as-index` split: bundled the index rule with the fixed body sections |
| `ours:wayfinder#refer-by-name` | `reference-by-name` | match |  |
| `ours:wayfinder#bounded-ticket` | `bounded-decision-ticket`, `coherence-sized-tickets`, `label-free-typing` | split | r1 finding 15: bundled the bounded question with ticket sizing and label-free typing; upstream sizes to one session and types by label |
| `ours:wayfinder#ticket-types` | `ticket-type-set` | match |  |
| `ours:wayfinder#claim-before-work` | `claim-before-work` | match |  |
| `ours:wayfinder#chart-and-graduate` | `destination-first`, `question-graduation`, `real-id-wiring`, `record-resolution` | split | merge pass: `chart-and-graduate` split: bundled four charting steps: destination first, ticketing sharp questions and graduating others, real-id wiring, recording a resolution |
| `ours:wayfinder#out-of-scope-close` | `out-of-scope-close` | match |  |
| `ours:wayfinder#human-decision-gate` | `human-decision-gate` | match |  |
| `ours:wayfinder#multi-ticket-sessions` | `multi-ticket-sessions` | match |  |
| `ours:check-invariants#read-overlay` | `read-overlay` | match |  |
| `ours:check-invariants#explicit-commands-only` | `explicit-commands-only` | match |  |
| `ours:check-invariants#pass-fail-report` | `pass-fail-report` | match |  |
| `ours:check-invariants#skip-aspirational` | `skip-aspirational` | match |  |
| `ours:check-invariants#repo-relative-paths` | `repo-relative-paths` | match |  |
| `ours:codebase-design#module-vocabulary` | `module-vocabulary`, `project-term-allowance` | split | r1 sweep: upstream bans the project's substitute terms, so allowing them is its own trait |
| `ours:codebase-design#interface-is-everything` | `interface-is-everything` | match |  |
| `ours:codebase-design#depth-as-leverage` | `depth-as-leverage` | match |  |
| `ours:codebase-design#deletion-test` | `deletion-test` | match |  |
| `ours:codebase-design#testability-shaping` | `inject-dependencies`, `return-not-mutate` | split | merge pass: `testability-shaping` split: bundled injected dependencies and return-not-mutate; 'testing through the interface' is meaningful-behaviour-assertion |
| `ours:codebase-design#single-adapter-justified` | `single-adapter-justified` | match |  |
| `ours:codebase-design#internal-seams` | `internal-seams` | match |  |
| `ours:codebase-design#dependency-categories` | `dependency-categories` | match |  |
| `ours:codebase-design#replace-dont-layer` | `covered-test-removal` | match | merge pass: `replace-dont-layer` renamed `covered-test-removal`: the ID named the opposite upstream mechanism (delete old tests); ours removes a test only when covered, so the upstream trait keeps the name |
| `ours:codebase-design#design-it-twice` | `design-it-twice` | match |  |
| `ours:codebase-research#three-modes` | `three-modes` | match |  |
| `ours:codebase-research#levels-vs-dive` | `levels-vs-dive` | match |  |
| `ours:codebase-research#scope-authorization` | `scope-authorization` | match |  |
| `ours:codebase-research#evidence-flags` | `evidence-flags` | match |  |
| `ours:codebase-research#reachability-ladder` | `reachability-ladder` | match |  |
| `ours:codebase-research#oversell-finding` | `oversell-finding` | match |  |
| `ours:codebase-research#claim-honesty` | `claim-honesty` | match |  |
| `ours:codebase-research#snapshot-header` | `snapshot-header` | match | Absorbs the levels' refresh-stale-lower-level-first rule to keep the sha gate in one trait. |
| `ours:codebase-research#registry-index` | `registry-index` | match |  |
| `ours:codebase-research#trust-boundary` | `trust-boundary` | match |  |
| `ours:codebase-research#execution-authorization` | `execution-authorization` | match |  |
| `ours:codebase-research#inline-for-bounded` | `inline-for-bounded` | match |  |
| `ours:codebase-research#artifact-contracts` | `artifact-contracts` | match |  |
| `ours:codebase-research#verify-before-report` | `verify-before-report` | match |  |
| `ours:design-evolve#integration-not-redesign` | `integration-not-redesign` | match |  |
| `ours:design-evolve#resolve-scope` | `resolve-scope` | match |  |
| `ours:design-evolve#classify-maturity` | `classify-maturity` | match |  |
| `ours:design-evolve#evidence-before-edit` | `evidence-before-edit` | match |  |
| `ours:design-evolve#start-from-source` | `start-from-source` | match |  |
| `ours:design-evolve#no-gap-filling` | `no-gap-filling` | match |  |
| `ours:design-evolve#version-rekey` | `version-rekey` | match |  |
| `ours:design-evolve#consistency-check` | `consistency-check` | match |  |
| `ours:design-evolve#concept-map` | `concept-map` | match |  |
| `ours:design-evolve#layout-mirror` | `layout-mirror` | match |  |
| `ours:design-evolve#preserve-structure` | `preserve-structure` | match |  |
| `ours:design-evolve#report-provenance` | `report-provenance` | match |  |
| `ours:domain-modeling#active-discipline` | `active-discipline` | match |  |
| `ours:domain-modeling#declared-glossary-location` | `declared-glossary-location` | match |  |
| `ours:domain-modeling#lazy-glossary-and-adr` | `lazy-glossary-and-adr` | match | r1 sweep: the documentation-authorization clause moved to authorized-model-writes, since upstream creates files without it |
| `ours:domain-modeling#challenge-glossary` | `challenge-glossary` | match |  |
| `ours:domain-modeling#sharpen-fuzzy` | `sharpen-fuzzy` | match |  |
| `ours:domain-modeling#concrete-scenarios` | `concrete-scenarios` | match |  |
| `ours:domain-modeling#cross-reference-code` | `cross-reference-code` | match |  |
| `ours:domain-modeling#update-inline` | `update-inline`, `authorized-model-writes` | split | r1 sweep: the documentation-authorization gate (shared with lazy file creation) split out; upstream writes inline without it |
| `ours:domain-modeling#glossary-is-glossary` | `glossary-is-glossary` | match |  |
| `ours:domain-modeling#adr-three-gate` | `adr-three-gate` | match |  |
| `ours:domain-modeling#adr-minimal-template` | `adr-minimal-template` | match |  |
| `ours:domain-modeling#adr-what-qualifies` | `adr-what-qualifies` | match |  |
| `ours:domain-modeling#adr-match-convention` | `adr-match-convention` | match |  |
| `ours:domain-modeling#adr-lifecycle` | `adr-supersede-lifecycle`, `adr-code-gotcha-link` | split | Bundled the never-delete/supersede lifecycle with the separate rule to leave a code comment linking the record; these can be ruled independently. |
| `ours:domain-modeling#glossary-format` | `glossary-format`, `context-specific-terms` | split | r1 sweep: teach's glossary lacks the context-specific-terms rule, so it is its own trait |
| `ours:domain-modeling#multi-context-map` | `multi-context-map` | match |  |
| `ours:execution#scope-selector` | `scope-selector` | match |  |
| `ours:execution#risk-sized-review` | `risk-sized-review` | match |  |
| `ours:execution#task-loop` | `task-loop`, `finding-adjudication` | split | The loop bundled per-task execution with finding adjudication, which is a distinct gate reused by the fix loop and final review. |
| `ours:execution#phase-loop` | `phase-loop` | match |  |
| `ours:execution#close-gate` | `close-gate` | match |  |
| `ours:execution#workstream-mode` | `workstream-mode` | match |  |
| `ours:execution#child-workflows` | `child-workflows` | match |  |
| `ours:execution#context-recovery` | `context-recovery` | match |  |
| `ours:execution#stop-on-failure` | `stop-on-failure` | match |  |
| `(new mechanism)` | `bounded-fix-loop` | new | task-engine.md's bounded fix loop with a completed-round ceiling and per-round adjudication was missing from the covers list. |
| `(new mechanism)` | `scope-base-review-package` | new | task-engine.md's snapshot-based review of uncommitted work against a base revision, with owned-path scoping, was not captured. |
| `(new mechanism)` | `delegated-report-recovery` | new | task-engine.md's worker status-value interpretation and recovery protocol was not captured. |
| `ours:improve-codebase-architecture#scope-by-evidence` | `scope-by-evidence` | match |  |
| `ours:improve-codebase-architecture#friction-signals` | `friction-signals` | match |  |
| `ours:improve-codebase-architecture#deletion-test-signal` | `deletion-test` | merge | Same mechanism as codebase-design's deletion test; reused as the shared trait with a skill note on its use as a candidate signal. |
| `ours:improve-codebase-architecture#candidate-comparison` | `candidate-comparison` | match |  |
| `ours:improve-codebase-architecture#optional-report` | `optional-report` | match |  |
| `ours:improve-codebase-architecture#architecture-vocabulary` | `module-vocabulary`, `project-term-allowance` | merge | It is the codebase-design vocabulary applied here, not a distinct mechanism; reused as the shared trait with a skill note.; r1 sweep: allowing the repository's normal terms is now project-term-allowance, replacing the skill note |
| `ours:improve-codebase-architecture#adr-conflict-callout` | `adr-conflict-callout` | match |  |
| `ours:improve-codebase-architecture#analysis-only-authority` | `review-no-auto-followup` | split | The review-authorizes-inspection-only half restates repository policy and is dropped; the kept half is the specific no-automatic-followup mechanism. |
| `ours:performance-optimization#scope-measured` | — | dropped | r1 finding 19: restates the skill's activation boundary, which is routing (rule 3) |
| `ours:performance-optimization#boundary-debugging` | — | dropped | r1 finding 19: a bare hand-off to systematic-debugging, which is routing (rule 3) |
| `ours:performance-optimization#define-metric` | `define-metric` | match |  |
| `ours:performance-optimization#baseline` | `baseline`, `representative-baseline` | split | r1 finding 16: the shared core is capturing a baseline before fixing; the representative-conditions standard is ours |
| `ours:performance-optimization#locate-cost` | `locate-cost` | match |  |
| `ours:performance-optimization#one-factor` | `one-factor` | match |  |
| `ours:performance-optimization#compare-and-dispose` | `like-for-like-comparison`, `noise-inconclusive`, `benefit-justifies-complexity`, `revert-ineffective-experiments` | split | r2 #4: bundled comparison, noise interpretation, retention criteria and cleanup (.claude/skills/performance-optimization/SKILL.md:24-26) |
| `ours:performance-optimization#attempt-ledger` | `attempt-ledger` | match |  |
| `ours:performance-optimization#regression-guard` | `regression-guard` | match |  |
| `ours:performance-optimization#measurement-recipes` | `measurement-recipes` | match |  |
| `ours:performance-optimization#frontend-performance` | `frontend-performance` | match |  |
| `ours:planning#route-by-scale` | `route-by-scale` | match |  |
| `ours:planning#decompose-phases` | `decompose-phases` | match | Dependency-edges dropped from this definition to keep it exclusive with the dependency-edges trait. |
| `ours:planning#vertical-slices` | `vertical-slices` | match |  |
| `ours:planning#expand-contract` | `expand-contract` | match |  |
| `ours:planning#dependency-edges` | `dependency-edges` | match |  |
| `ours:planning#ask-material-choices` | — | dropped | merge pass: restates AGENTS.md (ask only material choices; reuse recorded approvals); the overlap audit lists it as repeated policy |
| `ours:planning#beads-native-tracking` | `beads-native-tracking` | match |  |
| `ours:planning#durable-plan-format` | `durable-plan-format` | match |  |
| `ours:planning#plan-evidence-bound` | `plan-evidence-bound` | match |  |
| `ours:planning#test-first-marking` | `test-first-marking` | match |  |
| `(new mechanism)` | `no-placeholder-plan` | new | plan-format.md's no-placeholders quality gate was missing from the covers list. |
| `(new mechanism)` | `real-id-wiring` | new | 2026-10-29 Pocock rulings: decompose.md creates stages first, then wires real `bd dep add` edges; same trait wayfinder lists, missed here. |
| `(new mechanism)` | `no-stale-code-snippets` | new | 2026-10-29 Pocock rulings: plan-format.md keeps task approach in prose with no code blocks; same trait brainstorming lists for specs, missed here. |
| `(new mechanism)` | `plan-self-review` | new | plan-format.md's finished-plan self-review (coverage, name/type consistency, gap-naming) was missing. |
| `(new mechanism)` | `reviewer-rejectable-sizing` | new | plan-format.md's right-sizing test (a reviewer could reject this task while approving its neighbour) was missing. |
| `ours:prototype#named-question` | `named-question` | match |  |
| `ours:prototype#pick-form` | `pick-form` | match |  |
| `ours:prototype#throwaway-marked` | `throwaway-marked` | match |  |
| `ours:prototype#trivial-to-run` | `trivial-to-run` | match |  |
| `ours:prototype#surface-state` | `surface-state` | match |  |
| `ours:prototype#scoped-data` | `scoped-data`, `persistence-when-needed` | split | r1 sweep: bringing in persistence only when needed is shared with upstream; synthetic data and gated external calls are ours |
| `ours:prototype#cheap-assertions` | `cheap-assertions` | match |  |
| `ours:prototype#logic-pure-module` | `logic-pure-module` | match |  |
| `ours:prototype#logic-shareable-html` | `logic-shareable-html` | match |  |
| `ours:prototype#ui-contextual-preview` | `ui-contextual-preview` | match |  |
| `ours:prototype#ui-variants` | `variants-when-comparing`, `structural-variants`, `variant-switcher` | split | merge pass: `ui-variants` split: bundled when to build variants, structural difference and the switcher; each is ruled separately upstream |
| `ours:prototype#ui-accessibility` | `ui-keyboard-safety`, `ui-accessibility` | split | merge pass: `ui-accessibility` split: keyboard-input safety is a separate mechanism upstream rules on its own |
| `ours:prototype#capture-outcome` | `capture-outcome`, `separate-promotion` | split | r1 sweep: recording the verdict is shared; leaving promotion to separate work is ours (upstream folds it in) |
| `ours:resolving-merge-conflicts#capture-conflict-set` | `capture-conflict-set` | match |  |
| `ours:resolving-merge-conflicts#trace-intent` | `trace-intent` | match |  |
| `ours:resolving-merge-conflicts#resolve-preserve-both` | `resolve-preserve-both` | match |  |
| `ours:resolving-merge-conflicts#resolve-over-abort` | `resolve-over-abort` | match |  |
| `ours:resolving-merge-conflicts#run-project-checks` | `run-project-checks` | match |  |
| `ours:resolving-merge-conflicts#explicit-staging` | `explicit-staging` | match |  |
| `ours:resolving-merge-conflicts#commit-authority-gate` | `commit-authority-gate` | match |  |
| `ours:security#scope-threat` | `scope-threat` | match |  |
| `ours:security#abuse-cases` | `abuse-cases` | match |  |
| `ours:security#targeted-control-groups` | `targeted-control-groups` | match |  |
| `ours:security#web-reference` | `web-reference` | match |  |
| `ours:security#boundary-controls-ref` | `boundary-controls-ref` | match |  |
| `ours:security#llm-surface-ref` | `llm-surface-ref` | match |  |
| `ours:security#authority-gate` | `authority-gate` | match |  |
| `ours:security#enforce-in-code` | `enforce-in-code` | match |  |
| `ours:security#evidence-tests` | `evidence-tests` | match |  |
| `ours:security#dependency-triage` | `dependency-triage` | match |  |
| `ours:security#review-read-only` | — | dropped | Bare restatement of the repository policy that a review authorizes inspection and reporting only. |
| `ours:security#boundary-review` | `boundary-review` | match |  |
| `ours:systematic-debugging#reproduction-first` | `reproduction-first`, `unproven-without-reproduction` | split | merge pass: `reproduction-first` split: bundled reproduce-first with the no-reproduction fallback, which upstream rules differently |
| `ours:systematic-debugging#loop-construction` | `loop-construction`, `minimize-to-discriminate` | split | merge pass: `loop-construction` split: bundled the reproduction form with how far to minimize, which upstream rules differently |
| `ours:systematic-debugging#flake-handling` | `flake-reproduction`, `environmental-cause-unresolved` | split | r2 #4: reproduction techniques (references/non-reproducible-bugs.md:7-35) vs the environmental-finding disposition (references/non-reproducible-bugs.md:85-92) |
| `ours:systematic-debugging#hypotheses` | `hypotheses`, `discriminating-observation` | split | r1 sweep: upstream forms hypotheses with a fixed count, so the no-fixed-count discriminating observation is its own trait |
| `ours:systematic-debugging#localized-probing` | `localized-probing` | match |  |
| `ours:systematic-debugging#owning-fix` | `owning-fix` | match |  |
| `ours:systematic-debugging#escalation` | `attempt-log`, `two-failure-stop`, `critic-escalation` | split | r2 #4: bundled attempt logging, the two-failure stop and critic escalation (.claude/skills/systematic-debugging/SKILL.md:44-47); attempt-log is a variant of attempt-ledger |
| `ours:systematic-debugging#regression-check` | `regression-check` | match |  |
| `ours:systematic-debugging#evidence-safety` | `evidence-safety`, `unproven-without-reproduction` | split | merge pass: `evidence-safety` split: its 'qualify a fix without reproduction as unproven' clause repeated reproduction-first's fallback; moved to the shared trait |
| `ours:systematic-debugging#closeout` | `closeout`, `preserve-reproducers` | split | r1 sweep: removing instrumentation and recording the cause are shared; keeping reproducers is ours (upstream deletes prototypes) |
| `(new mechanism)` | `defense-in-depth-hardening` | new | post-fix-hardening.md's defense-in-depth, bypass-tested layered validation was missing from the covers list. |
| `ours:test-driven-development#mode-selection` | `mode-selection` | match |  |
| `ours:test-driven-development#good-test` | `meaningful-behaviour-assertion`, `independent-expectation`, `no-implementation-coupling` | split | Bundled three independent expectations (assert meaningful behaviour, derive values independently, survive refactors); the last is the no-mirror mechanism; r2 #5: renamed from no-mirror-or-tautology and restricted to implementation coupling (.claude/skills/test-driven-development/SKILL.md:21-22) |
| `ours:test-driven-development#seam-selection` | `seam-selection`, `plan-seams-no-approval` | split | r1 sweep: upstream confirms every seam with the user, so taking the plan's seams without approval is its own trait |
| `ours:test-driven-development#anti-patterns` | `no-implementation-coupling`, `deterministic-state`, `independent-expectation` | split | Its no-mirror and independent-expectation content dedupes into the shared traits from good-test; deterministic state is its own mechanism; r2 #5: tautological expectations map only to independent-expectation |
| `ours:test-driven-development#red-green` | `red-green`, `refactor-after-green` | split | r1 sweep: upstream refactors outside the loop, so refactoring after each green is its own trait |
| `ours:test-driven-development#mock-boundaries` | `mock-boundaries` | match |  |
| `ours:test-driven-development#proof-discipline` | `proof-discipline` | match |  |
| `(new mechanism)` | `break-naming-validation` | new | writing-good-tests.md's name-the-break check with an optional mutation trial was missing from the covers list. |

## Pocock: draft definitions mapped onto ours

One row per Pocock draft definition (`<draft file>:<id>`). Match reuses our trait; split maps
onto several; new adds a definition (renamed where the draft ID collided with a different
mechanism of ours or was too general for a global vocabulary).

| Draft definition | Upstream skill(s) | Final trait(s) | Mark | Reason |
|---|---|---|---|---|
| `pocock-1:read-skill-before-claiming` | ask-matt | `read-skill-before-claiming` | new | no ours trait reads the skill text before describing it |
| `pocock-1:unbroken-planning-window` | ask-matt | `unbroken-planning-window` | new | no existing trait names this mechanism |
| `pocock-1:smart-zone-budget` | ask-matt | `smart-zone-budget` | new | no existing trait names this mechanism |
| `pocock-1:boundary-only-context-decisions` | ask-matt | `boundary-only-context-decisions` | new | no existing trait names this mechanism |
| `pocock-1:rule-out-continue-first` | ask-matt | `rule-out-continue-first` | new | context-recovery says what to persist, not to rule out a move first |
| `pocock-1:clear-disposable-context` | ask-matt | `clear-disposable-context` | new | no existing trait names this mechanism |
| `pocock-1:handoff-for-portability` | ask-matt | `handoff-for-portability` | new | no existing trait names this mechanism |
| `pocock-1:delegate-afk-work` | ask-matt | `delegate-afk-work` | new | no existing trait names this mechanism |
| `pocock-1:compact-last` | ask-matt | `compact-last` | new | no existing trait names this mechanism |
| `pocock-1:compact-with-instruction` | ask-matt | `compact-with-instruction` | new | no existing trait names this mechanism |
| `pocock-1:primary-vs-secondary-source` | ask-matt | `primary-vs-secondary-source` | new | no existing trait names this mechanism |
| `pocock-1:two-axis-review` | code-review | `two-axis-review` | new | ours orders spec before general quality; the standards axis is different |
| `pocock-1:distinct-axis-verdicts` | code-review | `distinct-axis-verdicts` | match | same mechanism as the per-axis verdict clause split out of ours requirements-before-quality |
| `pocock-1:no-cross-axis-rerank` | code-review | `no-cross-axis-rerank` | new | no existing trait names this mechanism |
| `pocock-1:scope-capture` | code-review | `scope-establishment` | match | both fix the diff scope from a base before reviewing; r1 sweep: pre-existing-edit separation removed from the shared definition (ours only) |
| `pocock-1:fixed-point-preflight` | code-review | `fixed-point-preflight` | new | no existing trait names this mechanism |
| `pocock-1:three-dot-merge-base` | code-review | `three-dot-merge-base` | new | no existing trait names this mechanism |
| `pocock-1:spec-source-discovery` | code-review | `spec-source-discovery` | new | no existing trait names this mechanism |
| `pocock-1:standards-source-discovery` | code-review | `standards-source-discovery` | new | no existing trait names this mechanism |
| `pocock-1:smell-baseline` | code-review | `smell-baseline` | new | no existing trait names this mechanism |
| `pocock-1:parallel-subagents` | code-review | `parallel-subagents` | new | no existing trait names this mechanism |
| `pocock-1:module-vocabulary` | codebase-design | `module-vocabulary` | match | same glossary; r1 sweep: allowing project terms moved to project-term-allowance, which upstream lacks (it holds vocabulary-ban) |
| `pocock-1:vocabulary-ban` | codebase-design | `vocabulary-ban` | new | stricter variant of module-vocabulary |
| `pocock-1:interface-is-everything` | codebase-design | `interface-is-everything` | match | same mechanism (provisional ID match, verified) |
| `pocock-1:depth-as-leverage` | codebase-design | `depth-as-leverage` | match | same mechanism (provisional ID match, verified); r1 sweep: verified, both provide the whole definition |
| `pocock-1:deletion-test` | codebase-design, improve-codebase-architecture | `deletion-test` | match | same mechanism (provisional ID match, verified) |
| `pocock-1:interface-is-test-surface` | codebase-design | `interface-is-test-surface` | new | conflicts with ours internal-seams |
| `pocock-1:two-adapters-rule` | codebase-design | `two-adapters-rule` | new | opposite variant of ours single-adapter-justified |
| `pocock-1:internal-vs-external-seams` | codebase-design | `internal-seams` | match |  |
| `pocock-1:inject-dependencies` | codebase-design, tdd | `inject-dependencies` | match | same mechanism as the part split out of ours testability-shaping |
| `pocock-1:return-not-mutate` | codebase-design | `return-not-mutate` | match | same mechanism as the part split out of ours testability-shaping |
| `pocock-1:small-interface-surface` | codebase-design | `small-interface-surface` | new | related to depth-as-leverage but a separate rule |
| `pocock-1:dependency-categories` | codebase-design | `dependency-categories` | match | same mechanism (provisional ID match, verified); r1 sweep: the merge policy differs, so it moved to skill notes |
| `pocock-1:replace-dont-layer` | codebase-design | `replace-dont-layer` | new | provisional ID collision: ours means the cautious variant, renamed covered-test-removal |
| `pocock-1:design-it-twice` | codebase-design | `parallel-constrained-designs` | new (renamed) | provisional ID collision: ours is optional and never forces a multi-agent exercise |
| `pocock-1:feedback-loop-first` | diagnosing-bugs | `reproduction-first` | match | both build the reproduction before diagnosing; r1 sweep: our reuse-or-smallest clause moved to a skill note |
| `pocock-1:loop-construction-menu` | diagnosing-bugs | `loop-construction` | match | both choose the reproduction's form to fit the failure |
| `pocock-1:tighten-loop` | diagnosing-bugs | `tighten-loop` | new | ours flake-reproduction is about flake class, not loop quality in general |
| `pocock-1:reproduce-and-minimize` | diagnosing-bugs | `reproduce-and-minimize` | new | opposite variant of ours minimize-to-discriminate |
| `pocock-1:phase1-completion-criterion` | diagnosing-bugs | `phase1-completion-criterion` | new | stricter gate than reproduction-first |
| `pocock-1:redact-secrets` | diagnosing-bugs | `redact-secrets` | new | ours evidence-safety keeps secrets out of reports in general; this is the technique |
| `pocock-1:hypotheses-before-testing` | diagnosing-bugs | `hypotheses` | match | r1 sweep: narrowed to the shared core; our no-fixed-count rule is discriminating-observation, upstream's count is fixed-hypothesis-count |
| `pocock-1:fixed-hypothesis-count` | diagnosing-bugs | `fixed-hypothesis-count` | new | conflicts with ours hypotheses |
| `pocock-1:hypothesis-ranking-presentation` | diagnosing-bugs | `hypothesis-ranking-presentation` | new | no existing trait names this mechanism |
| `pocock-1:one-variable-at-a-time` | diagnosing-bugs | `one-variable-at-a-time` | new | ours one-factor is a performance-experiment rule |
| `pocock-1:tagged-debug-logs` | diagnosing-bugs | `tagged-debug-logs` | new | no existing trait names this mechanism |
| `pocock-1:measure-before-perf-fix` | diagnosing-bugs | `baseline`, `perf-bisection` | split | r1 finding 16: baseline narrowed to the shared measure-first core; upstream then bisects (perf-bisection) rather than profiling (locate-cost) |
| `pocock-1:debugger-first` | diagnosing-bugs | `debugger-first` | new | no existing trait names this mechanism |
| `pocock-1:prove-the-red` | diagnosing-bugs | `prove-the-red` | new | no existing trait names this mechanism |
| `pocock-1:regression-when-feasible` | diagnosing-bugs | `regression-check` | match | r1 sweep: the repository-checks clause moved to our skill note |
| `pocock-1:missing-seam-finding` | diagnosing-bugs | `missing-seam-finding` | new | no ours trait reports a missing seam as the finding |
| `pocock-1:cleanup-checklist` | diagnosing-bugs | `closeout`, `delete-debug-prototypes` | split | r1 sweep: shared core is removing instrumentation and recording the cause; upstream deletes throwaway prototypes (ours keeps reproducers) |
| `pocock-1:hitl-loop-script` | diagnosing-bugs | `hitl-loop-script` | new | no existing trait names this mechanism |
| `pocock-1:escalate-unreproducible` | diagnosing-bugs | `escalate-unreproducible` | new | opposite fallback to ours |
| `pocock-1:active-modeling` | domain-modeling | `active-discipline` | match |  |
| `pocock-1:lazy-doc-structure` | domain-modeling | `lazy-glossary-and-adr`, `multi-context-map` | split | partial: lazy file creation, and the root map is multi-context-map; r1 sweep: the authorization clause left the shared definition |
| `pocock-1:challenge-glossary` | domain-modeling | `challenge-glossary` | match | same mechanism (provisional ID match, verified) |
| `pocock-1:sharpen-fuzzy` | domain-modeling | `sharpen-fuzzy` | match | same mechanism (provisional ID match, verified) |
| `pocock-1:concrete-scenarios` | domain-modeling | `concrete-scenarios` | match | same mechanism (provisional ID match, verified) |
| `pocock-1:cross-reference-code` | domain-modeling | `cross-reference-code` | match | same mechanism (provisional ID match, verified) |
| `pocock-1:update-inline` | domain-modeling | `update-inline` | match | r1 sweep: the authorization clause moved to authorized-model-writes (ours only) |
| `pocock-1:glossary-is-glossary` | domain-modeling | `glossary-is-glossary` | match | same mechanism (provisional ID match, verified) |
| `pocock-1:adr-three-gate` | domain-modeling | `adr-three-gate` | match | same mechanism (provisional ID match, verified) |
| `pocock-1:adr-minimal-template` | domain-modeling | `adr-minimal-template` | match | same mechanism (provisional ID match, verified) |
| `pocock-1:adr-what-qualifies` | domain-modeling | `adr-what-qualifies` | match | same mechanism (provisional ID match, verified) |
| `pocock-1:glossary-format` | domain-modeling | `glossary-format`, `context-specific-terms` | split | r1 sweep: the context-specific-terms rule split out because teach's glossary lacks it |
| `pocock-1:multi-context-map` | domain-modeling | `multi-context-map` | match | same mechanism (provisional ID match, verified) |
| `pocock-1:document-during-interview` | grill-with-docs | `document-during-interview` | new | opposite variant of ours optional-docs |
| `pocock-1:scope-before-scan` | improve-codebase-architecture | `scope-by-evidence` | match | r1 sweep: our maintenance-and-test-friction clause moved to a skill note |
| `pocock-1:friction-signals` | improve-codebase-architecture | `friction-signals` | match | same mechanism (provisional ID match, verified) |
| `pocock-1:html-report` | improve-codebase-architecture | `html-candidate-report` | new (renamed) | ours makes the report optional |
| `pocock-1:diagram-patterns` | improve-codebase-architecture | `diagram-patterns` | new | no existing trait names this mechanism |
| `pocock-1:glossary-and-design-vocabulary` | improve-codebase-architecture | `domain-vocabulary`, `vocabulary-ban` | split | partial: glossary terms for the domain, exact design vocabulary for the architecture |
| `pocock-1:adr-conflict-callout` | improve-codebase-architecture | `adr-conflict-callout` | match | same mechanism (provisional ID match, verified) |
| `pocock-1:no-interfaces-yet` | improve-codebase-architecture | `no-interfaces-yet` | new | no existing trait names this mechanism |
| `pocock-1:grilling-loop` | improve-codebase-architecture | `grilling-loop` | new | opposite of ours review-no-auto-followup |
| `pocock-1:pr-body-template` | pr | `pr-body-template` | new | no existing trait names this mechanism |
| `pocock-1:summary-visual-menu` | pr | `smallest-view`, `visual-form-catalog` | split | partial: the smallest visual, chosen from the same set of forms; r1 sweep: our one-or-two-forms limit moved to a skill note |
| `pocock-1:evidence-before-after` | pr | `evidence-before-after` | new | no existing trait names this mechanism |
| `pocock-1:merge-danger` | pr | `merge-danger` | new | no existing trait names this mechanism |
| `pocock-1:throwaway-answers-a-question` | prototype | `named-question` | match | r1 sweep: our observable-success clause moved to a skill note |
| `pocock-1:pick-branch` | prototype | `pick-form` | match | same mechanism: the question picks the prototype's form; r1 sweep: narrowed so it no longer names our script form |
| `pocock-1:state-question-up-front` | prototype | `state-question-up-front` | new | no existing trait names this mechanism |
| `pocock-1:throwaway-marked` | prototype | `throwaway-marked` | match | r1 sweep: our reproducible clause moved to a skill note |
| `pocock-1:trivial-to-run` | prototype | `trivial-to-run` | match | r1 sweep: our expected-signal clause moved to a skill note |
| `pocock-1:no-persistence` | prototype | `persistence-when-needed` | match | r1 sweep: scoped-data bundled synthetic data and gated external calls upstream lacks; the shared persistence rule is its own trait |
| `pocock-1:skip-polish` | prototype | `skip-polish` | new | no existing trait names this mechanism |
| `pocock-1:no-tests-ban` | prototype | `no-tests-ban` | new | opposite of ours cheap-assertions |
| `pocock-1:surface-state` | prototype | `surface-state` | match | same mechanism (provisional ID match, verified) |
| `pocock-1:capture-outcome` | prototype | `capture-outcome` | match | r1 sweep: narrowed to the shared verdict record; promotion policy is separate-promotion (ours) versus auto-fold-and-branch |
| `pocock-1:auto-fold-and-branch` | prototype | `auto-fold-and-branch` | new | conflicts with ours capture-outcome |
| `pocock-1:rewrite-not-promote` | prototype | `rewrite-not-promote` | new | no existing trait names this mechanism |
| `pocock-1:variants-dont-share-layout` | prototype | `structural-variants` | match |  |
| `pocock-1:logic-pure-module` | prototype | `logic-pure-module` | match | same mechanism (provisional ID match, verified) |
| `pocock-1:logic-shareable-html` | prototype | `logic-shareable-html` | match | r1 sweep: our only-needed-scenarios clause moved to a skill note |
| `pocock-1:ui-variants-one-route` | prototype | `ui-variants-one-route` | new | ours builds variants only when comparing |
| `pocock-1:ui-sub-shapes` | prototype | `host-in-existing-page` | new | r1 sweep: upstream prefers the existing page and ours an isolated preview; a separate variant |
| `pocock-1:ui-keyboard-safety` | prototype | `ui-keyboard-safety` | match | same mechanism as the part split out of ours ui-accessibility |
| `pocock-1:ui-floating-switcher` | prototype | `variant-switcher` | match | same mechanism; upstream fixes its form |
| `pocock-1:background-agent` | research | `background-agent` | new | ours delegates only a sizeable part |
| `pocock-1:primary-sources` | research | `primary-source-preference` | match | r1 sweep: our version/date and vendor-testing clauses split out |
| `pocock-1:cited-markdown-artifact` | research | `cited-artifact`, `findings-file` | split | r1 sweep: citation binding is shared; always writing one Markdown file is upstream's own trait |
| `pocock-1:environment-retro-categories` | retro | `environment-retro-categories` | new | no existing trait names this mechanism |
| `pocock-1:mechanical-vs-judgement` | retro | `mechanical-vs-judgement` | new | no existing trait names this mechanism |
| `pocock-1:build-check-over-rule` | retro | `build-check-over-rule` | new | no existing trait names this mechanism |
| `pocock-1:read-existing-check-first` | retro | `read-existing-check-first` | new | no existing trait names this mechanism |
| `pocock-1:read-session-sources` | retro | `read-session-sources` | new | no existing trait names this mechanism |
| `pocock-1:severity-ordered-proposals` | retro | `severity-ordered-proposals` | new | no existing trait names this mechanism |
| `pocock-1:independent-review` | retro | `separate-review-stage` | new (renamed) | provisional ID collision: ours harness-evaluate trait is risk-triggered review (now material-risk-review) |
| `pocock-1:reviewer-owns-standards` | retro | `reviewer-owns-standards` | new | no existing trait names this mechanism |
| `pocock-1:good-test-definition` | tdd | `meaningful-behaviour-assertion`, `no-implementation-coupling` | split | partial: behaviour through public interfaces, and surviving refactors; r1 sweep: our exact-source-text clause moved to a skill note |
| `pocock-1:boundary-selection` | tdd | `seam-selection` | match | r1 sweep: our plan-seam and missing-seam clauses moved to plan-seams-no-approval |
| `pocock-1:public-only-seams` | tdd | `public-only-seams` | new | conflicts with ours internal-seams |
| `pocock-1:seam-preconfirmation` | tdd | `seam-preconfirmation` | new | no existing trait names this mechanism |
| `pocock-1:per-seam-note` | tdd | `per-seam-note` | new | no existing trait names this mechanism |
| `pocock-1:avoid-implementation-coupled-tests` | tdd | `no-implementation-coupling` | match | same mechanism: tests that mirror the implementation; r1 sweep: our exact-source-text clause moved to a skill note; r2 #5: renamed, tautology excluded (tdd/SKILL.md:30) |
| `pocock-1:avoid-tautological-tests` | tdd | `independent-expectation` | match | same mechanism: expected values from an independent source; r2 #5: the only mapping for tautological expectations (tdd/SKILL.md:31) |
| `pocock-1:vertical-tracer-slices` | tdd | `one-test-per-cycle` | new (renamed) | ID collision with the decomposition trait of the same name in pocock-2; this one is a TDD cadence |
| `pocock-1:red-green-loop` | tdd | `red-green` | match | r1 sweep: the refactor step moved to refactor-after-green (upstream holds refactor-outside-loop) |
| `pocock-1:refactor-outside-loop` | tdd | `refactor-outside-loop` | new | ordering differs from ours red-green |
| `pocock-1:mock-at-boundaries` | tdd | `system-boundary-mocks-only` | new | r2 #3: system boundaries only and never owned modules (tdd/mocking.md:3-14) is a stricter variant of ours mock-boundaries, linked by distinct_from |
| `pocock-1:sdk-interfaces` | tdd | `sdk-interfaces` | new | no existing trait names this mechanism |
| `pocock-2:synthesize-not-interview` | to-spec | `synthesize-settled` | match |  |
| `pocock-2:ground-in-codebase` | to-spec, to-tickets, triage | `ground-in-codebase` | new | ours limits reading rather than requiring it |
| `pocock-2:domain-vocabulary` | to-spec, to-tickets, triage | `domain-vocabulary` | match | same mechanism as the part split out of ours controlled-language-repitch |
| `pocock-2:respect-area-adrs` | to-spec, to-tickets, triage | `respect-area-adrs` | new | no existing trait names this mechanism |
| `pocock-2:seam-sketch` | to-spec | `testing-seam-decision`, `seam-preconfirmation` | split | partial: the seam choice heuristic, and confirming it with the user |
| `pocock-2:spec-template` | to-spec | `spec-template` | match | r1 sweep: narrowed to the shared skeleton; our extra sections and None rule are separate traits |
| `pocock-2:no-stale-file-paths` | to-spec, to-tickets | `no-stale-file-paths` | match | same mechanism as the part split out of ours spec-no-paths |
| `pocock-2:no-stale-code-snippets` | to-spec, to-tickets | `no-stale-code-snippets` | match | same mechanism as the part split out of ours spec-no-paths |
| `pocock-2:prototype-snippet-exception` | to-spec, to-tickets | `prototype-snippet` | match |  |
| `pocock-2:publish-to-tracker` | to-spec, to-tickets | `publish-to-tracker` | new | no existing trait names this mechanism |
| `pocock-2:ready-for-agent-label` | to-spec, to-tickets | `ready-for-agent-label` | new | ours is a field gate, not a label |
| `pocock-2:vertical-tracer-slices` | to-tickets | `vertical-slices` | match |  |
| `pocock-2:blocking-edges` | to-tickets | `dependency-edges` | match |  |
| `pocock-2:prefactor-first` | to-tickets | `prefactor-first` | new | no existing trait names this mechanism |
| `pocock-2:expand-contract-wide-refactor` | to-tickets | `expand-contract` | match |  |
| `pocock-2:quiz-the-user` | to-tickets | `quiz-the-user` | new | no existing trait names this mechanism |
| `pocock-2:dependency-order-publish` | to-tickets | `real-id-wiring` | match | same mechanism: blockers exist first so references use real identifiers; r1 sweep: creation order is now a skill note (this skill publishes blockers first) |
| `pocock-2:tracker-native-edges` | to-tickets | `dependency-edges` | match | same mechanism; merges with blocking-edges in this skill |
| `pocock-2:sub-issue-linkage` | to-tickets | `sub-issue-linkage` | new | no existing trait names this mechanism |
| `pocock-2:ticket-template` | to-tickets | `ticket-template` | new | no existing trait names this mechanism |
| `pocock-2:ai-disclaimer` | triage | `ai-disclaimer` | new | no existing trait names this mechanism |
| `pocock-2:category-state-roles` | triage | `category-state-roles` | new | no existing trait names this mechanism |
| `pocock-2:state-transitions` | triage | `state-transitions` | new | no existing trait names this mechanism |
| `pocock-2:attention-buckets` | triage | `attention-buckets` | match | r1 finding 15: narrowed to the shared mechanism; each side's bucket set is a skill note |
| `pocock-2:recommend-then-wait` | triage | `recommend-then-wait` | new | opposite of ours triage-decision |
| `pocock-2:verify-the-claim` | triage | `claim-verification` | match | r1 sweep: our never-auto-close clause moved to a skill note |
| `pocock-2:needs-info-notes` | triage | `needs-info-notes` | new | a reporter-facing note, not ours resume record |
| `pocock-2:glossary-adr-inline-update` | triage | `document-during-interview` | match | same mechanism as grill-with-docs' live documentation |
| `pocock-2:redundancy-check` | triage | `redundancy-check` | match | same mechanism (provisional ID match, verified) |
| `pocock-2:prior-rejection-check` | triage | `prior-rejection-check` | match | r1 finding 15: narrowed to the shared check; closed beads versus the out-of-scope knowledge base are skill notes |
| `pocock-2:agent-brief-contract` | triage | `agent-brief-contract` | new | no existing trait names this mechanism |
| `pocock-2:brief-durability` | triage | `no-stale-file-paths` | match | same mechanism: interfaces and behaviour rather than paths |
| `pocock-2:brief-behavioural` | triage | `brief-behavioural` | new | no existing trait names this mechanism |
| `pocock-2:brief-acceptance-criteria` | triage | `brief-acceptance-criteria` | new | ours bundles it in a readiness gate |
| `pocock-2:brief-scope-boundaries` | triage | `brief-scope-boundaries` | new | no existing trait names this mechanism |
| `pocock-2:ready-for-human-rationale` | triage | `ready-for-human-rationale` | new | no existing trait names this mechanism |
| `pocock-2:out-of-scope-kb` | triage | `out-of-scope-kb` | new | no existing trait names this mechanism |
| `pocock-2:pr-as-issue` | triage | `pr-as-issue` | new | no existing trait names this mechanism |
| `pocock-2:external-pr-discovery-filter` | triage | `external-pr-discovery-filter` | new | no existing trait names this mechanism |
| `pocock-2:resume-from-triage-notes` | triage | `triage-resume-notes` | match | r1 sweep: narrowed to resuming from notes; writing them is needs-info-notes |
| `pocock-2:shared-map` | wayfinder | `decision-map-epic` | match | r1 sweep: generalized from a Beads epic to one map item |
| `pocock-2:plan-not-do` | wayfinder | `plan-not-do` | match | same mechanism as the part split out of ours decision-map-epic |
| `pocock-2:refer-by-name` | wayfinder | `reference-by-name` | match |  |
| `pocock-2:map-as-index` | wayfinder | `map-as-index` | match | same mechanism (provisional ID match, verified) |
| `pocock-2:map-body-sections` | wayfinder | `map-body-sections` | match | same mechanism as the part split out of ours map-as-index |
| `pocock-2:decision-ticket` | wayfinder | `bounded-decision-ticket`, `session-sized-tickets` | split | r1 finding 15: shared core is one bounded question; upstream sizes to one session (session-sized-tickets) and types by label (no-triage-labels) |
| `pocock-2:claim-before-work` | wayfinder | `claim-before-work` | match | same mechanism (provisional ID match, verified) |
| `pocock-2:native-blocking-frontier` | wayfinder | `dependency-edges` | match |  |
| `pocock-2:ticket-types` | wayfinder | `ticket-type-set` | match | r1 sweep: our authorized-task clause moved to a skill note |
| `(new mechanism)` | wayfinder | `live-human-resolution` | new | r2 #7: wayfinder/SKILL.md:75 resolves a HITL ticket only through a live exchange and forbids the agent answering the human's side |
| `pocock-2:fog-of-war` | wayfinder | `question-graduation` | match | same mechanism: ticket only what is sharp, hold the rest aside |
| `pocock-2:out-of-scope-section` | wayfinder | `out-of-scope-close` | match |  |
| `pocock-2:one-ticket-per-session` | wayfinder | `one-ticket-per-session` | new | opposite of ours multi-ticket-sessions |
| `pocock-2:research-subagent-branch` | wayfinder | `research-subagent-branch` | new | no existing trait names this mechanism |
| `pocock-2:real-id-wiring` | wayfinder | `real-id-wiring` | match | same mechanism as the part split out of ours chart-and-graduate; r1 sweep: the create-then-wire order moved to skill notes |
| `pocock-2:no-triage-labels` | wayfinder | `no-triage-labels` | new | no existing trait names this mechanism |
| `pocock-2:research-branch-pr-policy` | wayfinder | `research-branch-pr-policy` | new | no existing trait names this mechanism |
| `pocock-2:type-directed-resolution` | wayfinder | `type-directed-resolution` | new | no existing trait names this mechanism |
| `pocock-2:destination-first` | wayfinder | `destination-first` | match | same mechanism as the part split out of ours chart-and-graduate |
| `pocock-2:no-map-without-fog` | wayfinder | `no-map-without-fog` | new | no existing trait names this mechanism |
| `pocock-2:record-resolution` | wayfinder | `record-resolution` | match | r1 sweep: our deleting-no-history clause moved to a skill note (upstream may delete invalidated tickets) |
| `pocock-2:template-library` | wizard | `template-library` | new | no existing trait names this mechanism |
| `pocock-2:scope-the-procedure` | wizard | `scope-the-procedure` | new | no existing trait names this mechanism |
| `pocock-2:map-stage-journey` | wizard | `map-stage-journey` | new | no existing trait names this mechanism |
| `pocock-2:author-stages-over-template` | wizard | `author-stages-over-template` | new | no existing trait names this mechanism |
| `pocock-2:ephemeral-by-default` | wizard | `ephemeral-by-default` | new | no existing trait names this mechanism |
| `pocock-2:syntax-check-handoff` | wizard | `syntax-check-handoff` | new | no existing trait names this mechanism |
| `pocock-2:static-trace-verification` | wizard | `static-trace-verification` | new | no existing trait names this mechanism |
| `pocock-2:template-robustness` | wizard | `template-robustness` | new | no existing trait names this mechanism |
| `pocock-2:loop-lens` | loop-me | `loop-lens` | new | no existing trait names this mechanism |
| `pocock-2:workflow-spec-artifact` | loop-me | `workflow-spec-artifact` | new | no existing trait names this mechanism |
| `pocock-2:spec-done-when-buildable` | loop-me | `spec-done-when-buildable` | new | no existing trait names this mechanism |
| `pocock-2:world-notes` | loop-me | `world-notes` | new | no existing trait names this mechanism |
| `pocock-2:workflow-vocabulary` | loop-me | `workflow-vocabulary` | new | no existing trait names this mechanism |
| `pocock-2:mandate-nothing-structural` | loop-me | `mandate-nothing-structural` | new | no existing trait names this mechanism |
| `pocock-2:push-right` | loop-me | `push-right` | new | no existing trait names this mechanism |
| `pocock-2:decision-summary-brief` | loop-me | `decision-summary-brief` | new | no existing trait names this mechanism |
| `pocock-2:deep-module-shape` | setup-ts-deep-modules | `deep-module-shape` | new | no existing trait names this mechanism |
| `pocock-2:entry-point-only-imports` | setup-ts-deep-modules | `entry-point-only-imports` | new | no existing trait names this mechanism |
| `pocock-2:intra-package-freedom` | setup-ts-deep-modules | `intra-package-freedom` | new | no existing trait names this mechanism |
| `pocock-2:tests-through-entry-points` | setup-ts-deep-modules | `tests-through-entry-points` | new | no existing trait names this mechanism |
| `pocock-2:no-cycles` | setup-ts-deep-modules | `no-cycles` | new | no existing trait names this mechanism |
| `pocock-2:public-surface-is-root-files` | setup-ts-deep-modules | `public-surface-is-root-files` | new | no existing trait names this mechanism |
| `pocock-2:discourage-barrels` | setup-ts-deep-modules | `discourage-barrels` | new | no existing trait names this mechanism |
| `pocock-2:prove-the-rules-bite` | setup-ts-deep-modules | `prove-the-rules-bite` | new | no existing trait names this mechanism |
| `pocock-2:document-boundary-readme` | setup-ts-deep-modules | `document-boundary-readme` | new | no existing trait names this mechanism |
| `pocock-2:link-convention-from-agents-file` | setup-ts-deep-modules | `link-convention-from-agents-file` | new | no existing trait names this mechanism |
| `pocock-2:preserve-existing-config` | setup-ts-deep-modules | `preserve-existing-config` | new | no existing trait names this mechanism |
| `pocock-2:wire-umbrella-check` | setup-ts-deep-modules | `wire-umbrella-check` | new | no existing trait names this mechanism |
| `pocock-2:scaffold-example` | setup-ts-deep-modules | `scaffold-example` | new | no existing trait names this mechanism |
| `pocock-2:detect-package-conventions` | setup-ts-deep-modules | `detect-package-conventions` | new | no existing trait names this mechanism |
| `pocock-2:flat-packages` | setup-ts-deep-modules | `flat-packages` | new | no existing trait names this mechanism |
| `pocock-2:design-tree` | grilling | `map-decisions` | match |  |
| `pocock-2:frontier-rounds` | grilling | `question-batching` | match |  |
| `pocock-2:recommended-answer` | grilling | `recommended-answer` | match | r1 sweep: renamed from recommend-with-assumptions; assumption labelling is our skill note |
| `pocock-2:yes-accepts-recommendation` | grilling | `yes-accepts-recommendation` | new | no existing trait names this mechanism |
| `pocock-2:round-format` | grilling | `round-format` | new | no existing trait names this mechanism |
| `pocock-2:facts-via-subagent` | grilling | `self-serve-facts` | match | r1 sweep: each side's delegation detail moved to skill notes |
| `pocock-2:exhaustive-completion` | grilling | `exhaustive-completion` | new | opposite of ours settled-stop |
| `pocock-2:reconfirm-before-action` | grilling | `reconfirm-before-action` | new | differs from ours approval-interpretation |
| `pocock-2:handoff-doc` | handoff | `handoff-doc` | new | ours rebuilds from durable state, not a summary |
| `pocock-2:temp-dir-destination` | handoff | `temp-dir-destination` | new | no existing trait names this mechanism |
| `pocock-2:suggested-skills` | handoff | `suggested-skills` | new | no existing trait names this mechanism |
| `pocock-2:no-duplication` | handoff | `link-dont-copy` | new (renamed) | renamed: the draft ID was too general for the global vocabulary |
| `pocock-2:redact-secrets` | handoff | `redact-secrets` | new | ours evidence-safety keeps secrets out of reports in general; this is the technique |
| `pocock-2:tailor-to-next-focus` | handoff | `tailor-to-next-focus` | new | no existing trait names this mechanism |
| `pocock-2:teaching-workspace` | teach | `teaching-workspace`, `always-stateful-course` | split | r1 finding 17: the course workspace is shared; upstream treats every request as a stateful course |
| `pocock-2:workspace-from-run-dir` | teach | `workspace-from-run-dir` | new | no existing trait names this mechanism |
| `pocock-2:mission-grounding` | teach | `mission-grounding` | match | same mechanism (provisional ID match, verified) |
| `pocock-2:zone-of-proximal-development` | teach | `proximal-next-lesson` | new | r1 finding 17: upstream picks the next lesson from learning records and mission; level-adaptation is conversational |
| `pocock-2:storage-strength` | teach | `storage-strength` | new | no ours trait |
| `pocock-2:spacing-interleaving` | teach | `retrieval-practice`, `spacing`, `interleaving` | split | partial: retrieval practice is ours; r1 finding 18: spacing and interleaving are two methods |
| `pocock-2:lesson-format` | teach | `lesson-format`, `html-lessons` | split | same mechanism as the part split out of ours lessons-and-assets; r2 #3: mandatory self-contained HTML output (teach/SKILL.md:18, 49) is its own trait; ours makes HTML optional |
| `pocock-2:reusable-assets` | teach | `reusable-assets`, `shared-component-extraction` | split | same mechanism as the part split out of ours lessons-and-assets; r1 sweep: narrowed to reuse-first; each side's library policy is a skill note; r2 #3: extracting each new reusable piece as a shared component (teach/SKILL.md:65-69) is its own trait |
| `pocock-2:glossary-format` | teach | `glossary-format` | match | r1 sweep: context-specific-terms split out of glossary-format; teach's glossary lacks it |
| `(new mechanism)` | teach | `glossary-admission-on-use` | match | r2 #6: the blind draft missed it; teach/GLOSSARY-FORMAT.md:29 admits a term only once the user can use it correctly, our existing trait |
| `pocock-2:learning-records` | teach | `learning-records` | match | same mechanism (provisional ID match, verified) |
| `pocock-2:quiz-equal-length` | teach | `quiz-equal-length` | new | conflicts with ours quiz-answer-hygiene |
| `pocock-2:vary-answer-position` | teach | `vary-answer-position` | new | no existing trait names this mechanism |
| `pocock-2:trusted-resources` | teach | `resources-curation` | match |  |
| `pocock-2:wisdom-community-referral` | teach | `wisdom-community-referral` | new | a referral rule, not curation |
| `pocock-2:reference-sheets` | teach | `reference-sheets` | new | no existing trait names this mechanism |
| `pocock-2:preference-notes` | teach | `preference-notes` | new | no existing trait names this mechanism |
| `pocock-2:cite-sources-in-lessons` | teach | `sourced-explanations` | match |  |
| `pocock-2:tight-feedback-loop` | teach | `tight-feedback-loop` | new | no existing trait names this mechanism |
| `pocock-2:grill-the-send` | to-questionnaire | `grill-the-send` | match | same mechanism as the part split out of ours absent-respondent |
| `pocock-2:two-exchange-interview` | to-questionnaire | `two-exchange-interview` | new | no existing trait names this mechanism |
| `pocock-2:gap-targeted-questions` | to-questionnaire | `gap-targeted-questions` | match | same mechanism as the part split out of ours absent-respondent |
| `pocock-2:questionnaire-artifact` | to-questionnaire | `questionnaire-artifact` | new | no existing trait names this mechanism |
| `pocock-2:document-structure` | to-questionnaire | `document-structure` | new | no existing trait names this mechanism |
| `pocock-2:repitch-trigger` | wait-what | `repitch-trigger` | match | same mechanism as the part split out of ours controlled-language-repitch |
| `pocock-2:controlled-language` | wait-what | `controlled-language` | match | same mechanism; upstream names the standard |
| `pocock-2:ubiquitous-language` | wait-what | `domain-vocabulary` | match |  |
| `pocock-2:glossary-map-lookup` | wait-what | `context-map-lookup` | new | r1 sweep: wait-what only follows the map; multi-context-map maintains it |
| `pocock-2:context-pointers` | writing-for-agents | `context-pointers` | match | r1 sweep: our nearest-competing-workflow clause moved to a skill note |
| `pocock-2:two-loads` | writing-for-agents | `two-loads` | match | r1 sweep: our full-read-path clause moved to a skill note |
| `pocock-2:information-hierarchy` | writing-for-agents | `inline-vs-disclose` | match | same mechanism: progressive disclosure; r1 sweep: our unconditional-read clause moved to a skill note |
| `pocock-2:co-location` | writing-for-agents | `co-location` | new | no existing trait names this mechanism |
| `pocock-2:completion-criteria-clarity` | writing-for-agents | `completion-criteria-clarity` | match | same mechanism as the part split out of ours precision-and-discretion |
| `pocock-2:completion-criteria-demand` | writing-for-agents | `completion-criteria-demand` | new | no existing trait names this mechanism |
| `pocock-2:split-by-invocation` | writing-for-agents | `split-by-invocation` | new | no existing trait names this mechanism |
| `pocock-2:sequence-isolation` | writing-for-agents | `sequence-isolation` | new | no existing trait names this mechanism |
| `pocock-2:leading-words` | writing-for-agents | `leading-words` | new | no existing trait names this mechanism |
| `pocock-2:negation-avoidance` | writing-for-agents | `negation-avoidance` | new | related but a separate wording rule |
| `pocock-2:single-source-of-truth` | writing-for-agents | `single-source-of-truth` | match | same mechanism as the part split out of ours pruning |
| `pocock-2:environment-as-cache` | writing-for-agents | `environment-as-cache` | match | same mechanism as the part split out of ours pruning |
| `pocock-2:relevance-check` | writing-for-agents | `relevance-check` | new | no existing trait names this mechanism |
| `pocock-2:no-op-deletion` | writing-for-agents | `no-op-deletion` | match | same mechanism as the part split out of ours pruning |
| `pocock-2:invocation-choice` | writing-for-agents | `invocation-mode` | match | r1 sweep: our sidecar and catalog regeneration split to invocation-sidecar-sync |
| `pocock-2:shared-reference-home` | writing-for-agents | `shared-reference-home` | new | no existing trait names this mechanism |
| `pocock-2:router-skills` | writing-for-agents | `router-skills` | new | no existing trait names this mechanism |

## Pocock: pilot ideas

One row per pilot idea subject (`mattpocock_skills:skill:<path>#<idea>`) → final trait(s);
`(ours)` means the trait is in our vocabulary, `(new)` that it was added from Pocock. Mark and
reason are the normalization step's.

| Old item | Final trait(s) | Mark | Reason |
|---|---|---|---|
| `mattpocock_skills:skill:skills/engineering/ask-matt#flow-map` | — | dropped | A map of which skill fits a situation; routing, not a mechanism the agent applies during work. |
| `mattpocock_skills:skill:skills/engineering/ask-matt#read-skill-before-claiming` | `read-skill-before-claiming` (new) | match |  |
| `mattpocock_skills:skill:skills/engineering/ask-matt#main-flow-roster` | — | dropped | The fixed idea-to-ship chain of skills; a routing roster, not a mechanism. |
| `mattpocock_skills:skill:skills/engineering/ask-matt#on-ramp-triggers` | — | dropped | Situations that route onto the main flow; routing, not a mechanism. |
| `mattpocock_skills:skill:skills/engineering/ask-matt#rule-out-continue-first` | `rule-out-continue-first` (new) | match |  |
| `mattpocock_skills:skill:skills/engineering/ask-matt#clear-disposable-context` | `clear-disposable-context` (new) | match |  |
| `mattpocock_skills:skill:skills/engineering/ask-matt#handoff-for-portability` | `handoff-for-portability` (new) | match |  |
| `mattpocock_skills:skill:skills/engineering/ask-matt#delegate-afk-work` | `delegate-afk-work` (new) | match |  |
| `mattpocock_skills:skill:skills/engineering/ask-matt#compact-last` | `compact-last` (new) | match |  |
| `mattpocock_skills:skill:skills/engineering/ask-matt#compact-with-instruction` | `compact-with-instruction` (new) | match |  |
| `mattpocock_skills:skill:skills/engineering/ask-matt#primary-vs-secondary-source` | `primary-vs-secondary-source` (new) | match |  |
| `mattpocock_skills:skill:skills/engineering/ask-matt#phase-definition` | `boundary-only-context-decisions` (new) | merge | Merged with mid-phase-compaction-ban into one trait: context moves are decided only at phase boundaries, never mid-phase. |
| `mattpocock_skills:skill:skills/engineering/ask-matt#mid-phase-compaction-ban` | `boundary-only-context-decisions` (new) | merge | Same mechanism as phase-definition: the mid-phase ban is the boundary-only rule stated from the other side. |
| `(new mechanism)` | `unbroken-planning-window` (new) | new | SKILL context-hygiene rule (keep grilling, spec and tickets in one unbroken window) that the old list omitted. |
| `(new mechanism)` | `smart-zone-budget` (new) | new | The smart-zone token budget and compact-at-boundary rule, omitted by the old list. |
| `mattpocock_skills:skill:skills/engineering/code-review#two-axis-standards-spec` | `two-axis-review` (new) | match | Renamed to name the mechanism rather than the axes list. |
| `mattpocock_skills:skill:skills/engineering/code-review#distinct-axis-verdicts` | `distinct-axis-verdicts` (ours) | match |  |
| `mattpocock_skills:skill:skills/engineering/code-review#no-cross-axis-rerank` | `no-cross-axis-rerank` (new) | match |  |
| `mattpocock_skills:skill:skills/engineering/code-review#scope-capture` | `scope-establishment` (ours) | match |  |
| `mattpocock_skills:skill:skills/engineering/code-review#fixed-point-preflight` | `fixed-point-preflight` (new) | match |  |
| `mattpocock_skills:skill:skills/engineering/code-review#three-dot-merge-base` | `three-dot-merge-base` (new) | match |  |
| `mattpocock_skills:skill:skills/engineering/code-review#spec-source-discovery` | `spec-source-discovery` (new) | match |  |
| `mattpocock_skills:skill:skills/engineering/code-review#standards-source-discovery` | `standards-source-discovery` (new) | match |  |
| `mattpocock_skills:skill:skills/engineering/code-review#smell-baseline` | `smell-baseline` (new) | match |  |
| `mattpocock_skills:skill:skills/engineering/code-review#parallel-subagents` | `parallel-subagents` (new) | match |  |
| `mattpocock_skills:skill:skills/engineering/codebase-design#module-vocabulary` | `module-vocabulary` (ours) | match |  |
| `mattpocock_skills:skill:skills/engineering/codebase-design#vocabulary-ban` | `vocabulary-ban` (new) | match |  |
| `mattpocock_skills:skill:skills/engineering/codebase-design#interface-is-everything` | `interface-is-everything` (ours) | match |  |
| `mattpocock_skills:skill:skills/engineering/codebase-design#depth-as-leverage` | `depth-as-leverage` (ours) | match |  |
| `mattpocock_skills:skill:skills/engineering/codebase-design#deletion-test` | `deletion-test` (ours) | match |  |
| `mattpocock_skills:skill:skills/engineering/codebase-design#interface-is-test-surface` | `interface-is-test-surface` (new) | match |  |
| `mattpocock_skills:skill:skills/engineering/codebase-design#two-adapters-rule` | `two-adapters-rule` (new) | match |  |
| `mattpocock_skills:skill:skills/engineering/codebase-design#internal-vs-external-seams` | `internal-seams` (ours) | match |  |
| `mattpocock_skills:skill:skills/engineering/codebase-design#testability-shaping` | `inject-dependencies` (ours), `return-not-mutate` (ours), `small-interface-surface` (new) | split | Bundled three separable design rules (accept dependencies, return results not side effects, keep the surface small) into one item. |
| `mattpocock_skills:skill:skills/engineering/codebase-design#dependency-categories` | `dependency-categories` (ours) | match |  |
| `mattpocock_skills:skill:skills/engineering/codebase-design#replace-dont-layer` | `replace-dont-layer` (new) | match |  |
| `mattpocock_skills:skill:skills/engineering/codebase-design#design-it-twice` | `parallel-constrained-designs` (new) | match |  |
| `mattpocock_skills:skill:skills/engineering/diagnosing-bugs#feedback-loop-first` | `reproduction-first` (ours) | match |  |
| `mattpocock_skills:skill:skills/engineering/diagnosing-bugs#loop-construction-menu` | `loop-construction` (ours) | match |  |
| `mattpocock_skills:skill:skills/engineering/diagnosing-bugs#tighten-loop` | `tighten-loop` (new) | match |  |
| `mattpocock_skills:skill:skills/engineering/diagnosing-bugs#reproduce-and-minimize` | `reproduce-and-minimize` (new) | match |  |
| `mattpocock_skills:skill:skills/engineering/diagnosing-bugs#phase1-completion-criterion` | `phase1-completion-criterion` (new) | match |  |
| `mattpocock_skills:skill:skills/engineering/diagnosing-bugs#redact-secrets` | `redact-secrets` (new) | match |  |
| `mattpocock_skills:skill:skills/engineering/diagnosing-bugs#hypotheses-before-testing` | `hypotheses` (ours) | match |  |
| `mattpocock_skills:skill:skills/engineering/diagnosing-bugs#fixed-hypothesis-count` | `fixed-hypothesis-count` (new) | match |  |
| `mattpocock_skills:skill:skills/engineering/diagnosing-bugs#hypothesis-ranking-presentation` | `hypothesis-ranking-presentation` (new) | match |  |
| `mattpocock_skills:skill:skills/engineering/diagnosing-bugs#instrument-one-variable` | `one-variable-at-a-time` (new), `tagged-debug-logs` (new), `baseline` (ours), `perf-bisection` (new) | split | Bundled three separable instrumentation rules (change one variable at a time, tag debug logs for cleanup, measure-first for performance) into one item.; r1 finding 16: the perf branch bisects, so locate-cost became perf-bisection |
| `mattpocock_skills:skill:skills/engineering/diagnosing-bugs#debugger-first` | `debugger-first` (new) | match |  |
| `mattpocock_skills:skill:skills/engineering/diagnosing-bugs#prove-the-red` | `prove-the-red` (new) | match |  |
| `mattpocock_skills:skill:skills/engineering/diagnosing-bugs#regression-when-feasible` | `regression-check` (ours) | match |  |
| `mattpocock_skills:skill:skills/engineering/diagnosing-bugs#missing-seam-finding` | `missing-seam-finding` (new) | match |  |
| `mattpocock_skills:skill:skills/engineering/diagnosing-bugs#cleanup-checklist` | `closeout` (ours), `delete-debug-prototypes` (new) | split | r1 sweep: upstream deletes throwaway prototypes, which the narrowed closeout no longer covers |
| `mattpocock_skills:skill:skills/engineering/diagnosing-bugs#hitl-loop-script` | `hitl-loop-script` (new) | match |  |
| `(new mechanism)` | `escalate-unreproducible` (new) | new | The explicit no-loop escalation protocol (stop, list attempts, ask for access/artifact/instrumentation) that the old list did not capture as its own mechanism. |
| `mattpocock_skills:skill:skills/engineering/domain-modeling#active-discipline` | `active-discipline` (ours) | match | Renamed to name the mechanism. |
| `mattpocock_skills:skill:skills/engineering/domain-modeling#lazy-file-structure` | `lazy-glossary-and-adr` (ours), `multi-context-map` (ours) | match | Renamed to name the mechanism. |
| `mattpocock_skills:skill:skills/engineering/domain-modeling#challenge-glossary` | `challenge-glossary` (ours) | match |  |
| `mattpocock_skills:skill:skills/engineering/domain-modeling#sharpen-fuzzy` | `sharpen-fuzzy` (ours) | match |  |
| `mattpocock_skills:skill:skills/engineering/domain-modeling#concrete-scenarios` | `concrete-scenarios` (ours) | match |  |
| `mattpocock_skills:skill:skills/engineering/domain-modeling#cross-reference-code` | `cross-reference-code` (ours) | match |  |
| `mattpocock_skills:skill:skills/engineering/domain-modeling#update-inline` | `update-inline` (ours) | match |  |
| `mattpocock_skills:skill:skills/engineering/domain-modeling#glossary-is-glossary` | `glossary-is-glossary` (ours) | match |  |
| `mattpocock_skills:skill:skills/engineering/domain-modeling#adr-three-gate` | `adr-three-gate` (ours) | match |  |
| `mattpocock_skills:skill:skills/engineering/domain-modeling#adr-minimal-template` | `adr-minimal-template` (ours) | match |  |
| `mattpocock_skills:skill:skills/engineering/domain-modeling#adr-what-qualifies` | `adr-what-qualifies` (ours) | match |  |
| `mattpocock_skills:skill:skills/engineering/domain-modeling#glossary-format` | `glossary-format` (ours), `context-specific-terms` (ours) | split | r1 sweep: context-specific-terms split out of glossary-format |
| `mattpocock_skills:skill:skills/engineering/domain-modeling#multi-context-map` | `multi-context-map` (ours) | match |  |
| `mattpocock_skills:skill:skills/engineering/grill-with-docs#compose-grill-and-docs` | `document-during-interview` (new) | match | Renamed; the distinctive mechanism is producing docs live as the interview settles decisions, not the bare composition of two skills. |
| `mattpocock_skills:skill:skills/engineering/grill-with-docs#manual-invocation-only` | — | dropped | An activation setting (user-invoked only / model-invocation disabled), not a mechanism the agent applies during work. |
| `mattpocock_skills:skill:skills/engineering/improve-codebase-architecture#scope-before-scan` | `scope-by-evidence` (ours) | match |  |
| `mattpocock_skills:skill:skills/engineering/improve-codebase-architecture#friction-signals` | `friction-signals` (ours) | match |  |
| `mattpocock_skills:skill:skills/engineering/improve-codebase-architecture#deletion-test-signal` | `deletion-test` (ours) | merge | Same deletion test defined in codebase-design, here applied as a scanning signal; folded into the shared trait with a skill note. |
| `mattpocock_skills:skill:skills/engineering/improve-codebase-architecture#html-report` | `html-candidate-report` (new) | match |  |
| `mattpocock_skills:skill:skills/engineering/improve-codebase-architecture#diagram-patterns` | `diagram-patterns` (new) | match |  |
| `mattpocock_skills:skill:skills/engineering/improve-codebase-architecture#glossary-architecture-vocabulary` | `domain-vocabulary` (ours), `vocabulary-ban` (new) | match | Renamed to name the dual-vocabulary mechanism. |
| `mattpocock_skills:skill:skills/engineering/improve-codebase-architecture#adr-conflict-callout` | `adr-conflict-callout` (ours) | match |  |
| `mattpocock_skills:skill:skills/engineering/improve-codebase-architecture#no-interfaces-yet` | `no-interfaces-yet` (new) | match |  |
| `mattpocock_skills:skill:skills/engineering/improve-codebase-architecture#grilling-loop` | `grilling-loop` (new) | match |  |
| `mattpocock_skills:skill:skills/engineering/pr#summary-visual-menu` | `smallest-view` (ours), `visual-form-catalog` (ours) | match |  |
| `mattpocock_skills:skill:skills/engineering/pr#pr-body-template` | `pr-body-template` (new) | match |  |
| `mattpocock_skills:skill:skills/engineering/pr#evidence-before-after` | `evidence-before-after` (new) | match |  |
| `mattpocock_skills:skill:skills/engineering/pr#merge-danger` | `merge-danger` (new) | match |  |
| `mattpocock_skills:skill:skills/engineering/prototype#throwaway-answers-a-question` | `named-question` (ours) | match |  |
| `mattpocock_skills:skill:skills/engineering/prototype#pick-branch` | `pick-form` (ours) | match |  |
| `mattpocock_skills:skill:skills/engineering/prototype#throwaway-marked` | `throwaway-marked` (ours) | match |  |
| `mattpocock_skills:skill:skills/engineering/prototype#trivial-to-run` | `trivial-to-run` (ours) | match |  |
| `mattpocock_skills:skill:skills/engineering/prototype#no-persistence` | `persistence-when-needed` (ours) | match | r1 sweep: re-keyed from scoped-data to the shared persistence rule |
| `mattpocock_skills:skill:skills/engineering/prototype#skip-polish` | `skip-polish` (new) | match |  |
| `mattpocock_skills:skill:skills/engineering/prototype#no-tests-ban` | `no-tests-ban` (new) | match |  |
| `mattpocock_skills:skill:skills/engineering/prototype#surface-state` | `surface-state` (ours) | match |  |
| `mattpocock_skills:skill:skills/engineering/prototype#capture-outcome` | `capture-outcome` (ours) | match |  |
| `mattpocock_skills:skill:skills/engineering/prototype#auto-fold-and-branch` | `auto-fold-and-branch` (new) | match |  |
| `mattpocock_skills:skill:skills/engineering/prototype#logic-pure-module` | `logic-pure-module` (ours) | match |  |
| `mattpocock_skills:skill:skills/engineering/prototype#logic-shareable-html` | `logic-shareable-html` (ours) | match |  |
| `mattpocock_skills:skill:skills/engineering/prototype#ui-variants-one-route` | `ui-variants-one-route` (new) | match |  |
| `mattpocock_skills:skill:skills/engineering/prototype#ui-sub-shapes` | `host-in-existing-page` (new) | new | r1 sweep: opposite default from ui-contextual-preview; its own variant |
| `mattpocock_skills:skill:skills/engineering/prototype#ui-keyboard-safety` | `ui-keyboard-safety` (ours) | match |  |
| `mattpocock_skills:skill:skills/engineering/prototype#ui-floating-switcher` | `variant-switcher` (ours) | match |  |
| `mattpocock_skills:skill:skills/engineering/prototype#anti-patterns` | `rewrite-not-promote` (new), `structural-variants` (ours) | split | Bundled per-branch prohibitions; most restate other traits (no tests, no real DB, no abstractions/generalising, read-only vs no-persistence, structurally-different variants), the genuinely distinct ones are rewriting rather than promoting the prototype and keeping variants from sharing a layout. |
| `(new mechanism)` | `state-question-up-front` (new) | new | Both branches require writing the question visibly at the top of the prototype before building; the old list only captured that a prototype answers one named question, not the write-it-down-first practice. |
| `mattpocock_skills:skill:skills/engineering/research#background-agent` | `background-agent` (new) | match |  |
| `mattpocock_skills:skill:skills/engineering/research#primary-sources` | `primary-source-preference` (ours) | match |  |
| `mattpocock_skills:skill:skills/engineering/research#cited-markdown-artifact` | `cited-artifact` (ours), `findings-file` (new) | split | r1 sweep: always writing one file is upstream's own trait |
| `mattpocock_skills:skill:skills/engineering/retro#environment-retro-categories` | `environment-retro-categories` (new) | match |  |
| `mattpocock_skills:skill:skills/engineering/retro#mechanical-vs-judgement` | `mechanical-vs-judgement` (new) | match |  |
| `mattpocock_skills:skill:skills/engineering/retro#build-check-over-rule` | `build-check-over-rule` (new) | match |  |
| `mattpocock_skills:skill:skills/engineering/retro#read-existing-check-first` | `read-existing-check-first` (new) | match |  |
| `mattpocock_skills:skill:skills/engineering/retro#read-session-sources` | `read-session-sources` (new) | match |  |
| `mattpocock_skills:skill:skills/engineering/retro#severity-ordered-proposals` | `severity-ordered-proposals` (new) | match |  |
| `mattpocock_skills:skill:skills/engineering/retro#independent-review` | `separate-review-stage` (new) | match |  |
| `mattpocock_skills:skill:skills/engineering/retro#reviewer-owns-standards` | `reviewer-owns-standards` (new) | match |  |
| `mattpocock_skills:skill:skills/engineering/tdd#good-test-definition` | `meaningful-behaviour-assertion` (ours), `no-implementation-coupling` (ours) | match |  |
| `mattpocock_skills:skill:skills/engineering/tdd#boundary-selection` | `seam-selection` (ours) | match |  |
| `mattpocock_skills:skill:skills/engineering/tdd#public-only-seams` | `public-only-seams` (new) | match |  |
| `mattpocock_skills:skill:skills/engineering/tdd#seam-preconfirmation` | `seam-preconfirmation` (new) | match |  |
| `mattpocock_skills:skill:skills/engineering/tdd#per-seam-note` | `per-seam-note` (new) | match |  |
| `mattpocock_skills:skill:skills/engineering/tdd#anti-patterns` | `no-implementation-coupling` (ours), `independent-expectation` (ours), `one-test-per-cycle` (new) | split | Bundled three separable anti-patterns (implementation-coupled, tautological, horizontal-slicing vs vertical tracer-bullet slices) into one item. |
| `mattpocock_skills:skill:skills/engineering/tdd#red-green-loop` | `red-green` (ours) | match |  |
| `mattpocock_skills:skill:skills/engineering/tdd#refactor-outside-loop` | `refactor-outside-loop` (new) | match |  |
| `mattpocock_skills:skill:skills/engineering/tdd#mock-at-boundaries` | `system-boundary-mocks-only` (new) | new | r2 #3: stricter variant of ours mock-boundaries (tdd/mocking.md:3-14); the draft adopts it `into: mock-boundaries` with a modification |
| `mattpocock_skills:skill:skills/engineering/tdd#dependency-injection` | `inject-dependencies` (ours) | match | Same mechanism as codebase-design's testability rule; mapped to the shared inject-dependencies trait. |
| `mattpocock_skills:skill:skills/engineering/tdd#sdk-interfaces` | `sdk-interfaces` (new) | match |  |
| `mattpocock_skills:skill:skills/engineering/to-spec#synthesize-not-interview` | `synthesize-settled` (ours) | match |  |
| `mattpocock_skills:skill:skills/engineering/to-spec#explore-glossary-adr` | `ground-in-codebase` (new), `domain-vocabulary` (ours), `respect-area-adrs` (new) | split | Repo exploration, glossary vocabulary, and ADR respect are three independently-rulable mechanisms. |
| `mattpocock_skills:skill:skills/engineering/to-spec#sketch-test-seams` | `testing-seam-decision` (ours), `seam-preconfirmation` (new) | match |  |
| `mattpocock_skills:skill:skills/engineering/to-spec#spec-template` | `spec-template` (ours) | match |  |
| `mattpocock_skills:skill:skills/engineering/to-spec#no-paths-no-code` | `no-stale-file-paths` (ours), `no-stale-code-snippets` (ours) | split | File-path and code-snippet prohibitions are separate rules, as to-tickets treats them. |
| `mattpocock_skills:skill:skills/engineering/to-spec#prototype-snippet-exception` | `prototype-snippet` (ours) | match |  |
| `mattpocock_skills:skill:skills/engineering/to-spec#publish-to-tracker` | `publish-to-tracker` (new), `ready-for-agent-label` (new) | split | Publishing the artifact and applying the triage label are separate mechanisms. |
| `mattpocock_skills:skill:skills/engineering/to-tickets#tracer-bullet-slices` | `vertical-slices` (ours) | match |  |
| `mattpocock_skills:skill:skills/engineering/to-tickets#blocking-edges` | `dependency-edges` (ours) | match |  |
| `mattpocock_skills:skill:skills/engineering/to-tickets#prefactor-first` | `prefactor-first` (new) | match |  |
| `mattpocock_skills:skill:skills/engineering/to-tickets#wide-refactor-expand-contract` | `expand-contract` (ours) | match |  |
| `mattpocock_skills:skill:skills/engineering/to-tickets#quiz-the-user` | `quiz-the-user` (new) | match |  |
| `mattpocock_skills:skill:skills/engineering/to-tickets#publish-to-tracker` | `publish-to-tracker` (new), `real-id-wiring` (ours), `dependency-edges` (ours), `sub-issue-linkage` (new), `ready-for-agent-label` (new) | split | Bundled publishing splits into publish, dependency ordering, native-vs-local edges, sub-issue linkage with parent preservation, and the triage label. |
| `mattpocock_skills:skill:skills/engineering/to-tickets#ticket-templates` | `ticket-template` (new) | match |  |
| `mattpocock_skills:skill:skills/engineering/to-tickets#no-file-paths` | `no-stale-file-paths` (ours) | match |  |
| `mattpocock_skills:skill:skills/engineering/to-tickets#no-code-snippets` | `no-stale-code-snippets` (ours), `prototype-snippet` (ours) | split | The old item bundled the prohibition with the prototype-snippet exception. |
| `mattpocock_skills:skill:skills/engineering/triage#category-state-roles` | `category-state-roles` (new) | match |  |
| `mattpocock_skills:skill:skills/engineering/triage#state-transitions` | `state-transitions` (new) | match |  |
| `mattpocock_skills:skill:skills/engineering/triage#show-what-needs-attention` | `attention-buckets` (ours) | match |  |
| `mattpocock_skills:skill:skills/engineering/triage#triage-one-issue` | `recommend-then-wait` (new), `claim-verification` (ours) | split | The per-issue procedure's distinct gates are recommend-and-wait and verify-the-claim; its gather and apply steps are carried by redundancy-check, prior-rejection-check and the brief and notes traits. |
| `mattpocock_skills:skill:skills/engineering/triage#needs-info-artifact` | `needs-info-notes` (new) | match |  |
| `mattpocock_skills:skill:skills/engineering/triage#auto-grill-doc-mutation` | `document-during-interview` (new) | match |  |
| `mattpocock_skills:skill:skills/engineering/triage#redundancy-and-prior-rejection` | `redundancy-check` (ours), `prior-rejection-check` (ours) | split | Redundancy (already-built) and prior-rejection (out-of-scope knowledge base) are separate checks. |
| `mattpocock_skills:skill:skills/engineering/triage#agent-brief` | `agent-brief-contract` (new), `no-stale-file-paths` (ours), `brief-behavioural` (new), `brief-acceptance-criteria` (new), `brief-scope-boundaries` (new) | split | The brief reference states four independent principles plus the authoritative-contract idea. |
| `mattpocock_skills:skill:skills/engineering/triage#out-of-scope-kb` | `out-of-scope-kb` (new) | match |  |
| `mattpocock_skills:skill:skills/engineering/triage#ai-disclaimer` | `ai-disclaimer` (new) | match |  |
| `mattpocock_skills:skill:skills/engineering/triage#external-pr-triage` | `pr-as-issue` (new), `external-pr-discovery-filter` (new) | split | Treating a PR as an issue and the external-author discovery filter are separate mechanisms. |
| `(new mechanism)` | `ready-for-human-rationale` (new) | new | Ready-for-human reuses the brief structure but must record why the work cannot be delegated; the old list omitted it. |
| `(new mechanism)` | `triage-resume-notes` (ours) | new | Resuming reads prior triage notes and avoids re-asking resolved questions; the old list omitted it. |
| `mattpocock_skills:skill:skills/engineering/wayfinder#shared-map-tracker` | `decision-map-epic` (ours) | match |  |
| `mattpocock_skills:skill:skills/engineering/wayfinder#plan-not-do` | `plan-not-do` (ours) | match |  |
| `mattpocock_skills:skill:skills/engineering/wayfinder#refer-by-name` | `reference-by-name` (ours) | match |  |
| `mattpocock_skills:skill:skills/engineering/wayfinder#map-as-index` | `map-as-index` (ours) | match |  |
| `mattpocock_skills:skill:skills/engineering/wayfinder#map-body-sections` | `map-body-sections` (ours) | match |  |
| `mattpocock_skills:skill:skills/engineering/wayfinder#decision-ticket` | `bounded-decision-ticket` (ours), `session-sized-tickets` (new) | split | r1 finding 15: upstream sizes each ticket to one session |
| `mattpocock_skills:skill:skills/engineering/wayfinder#claim-before-work` | `claim-before-work` (ours) | match |  |
| `mattpocock_skills:skill:skills/engineering/wayfinder#native-blocking-frontier` | `dependency-edges` (ours) | match |  |
| `mattpocock_skills:skill:skills/engineering/wayfinder#ticket-types` | `ticket-type-set` (ours) | match |  |
| `mattpocock_skills:skill:skills/engineering/wayfinder#fog-of-war` | `question-graduation` (ours) | match |  |
| `mattpocock_skills:skill:skills/engineering/wayfinder#out-of-scope-section` | `out-of-scope-close` (ours) | match |  |
| `mattpocock_skills:skill:skills/engineering/wayfinder#one-ticket-per-session` | `one-ticket-per-session` (new) | match |  |
| `mattpocock_skills:skill:skills/engineering/wayfinder#research-subagent-branch` | `research-subagent-branch` (new) | match |  |
| `mattpocock_skills:skill:skills/engineering/wayfinder#real-id-wiring` | `real-id-wiring` (ours) | match |  |
| `mattpocock_skills:skill:skills/engineering/wayfinder#no-triage-labels` | `no-triage-labels` (new) | match |  |
| `mattpocock_skills:skill:skills/engineering/wayfinder#research-branch-pr-policy` | `research-branch-pr-policy` (new) | match |  |
| `mattpocock_skills:skill:skills/engineering/wayfinder#type-directed-resolution` | `type-directed-resolution` (new) | match |  |
| `(new mechanism)` | `destination-first` (ours) | new | Naming the destination first fixes scope and shapes every ticket; the old list folded it into map-body-sections. |
| `(new mechanism)` | `no-map-without-fog` (new) | new | If breadth-first charting surfaces no fog, stop and don't build a map; the old list omitted this gate. |
| `(new mechanism)` | `record-resolution` (ours) | new | Resolving a ticket posts a resolution comment, closes it, and appends a pointer to Decisions-so-far; the old list omitted the recording mechanism. |
| `mattpocock_skills:skill:skills/engineering/wizard#verify-what-you-must-not-run` | `static-trace-verification` (new) | match |  |
| `mattpocock_skills:skill:skills/engineering/wizard#template-library` | `template-library` (new) | match |  |
| `mattpocock_skills:skill:skills/engineering/wizard#interactive-wizard-generation` | `scope-the-procedure` (new), `map-stage-journey` (new), `author-stages-over-template` (new) | split | The three authoring steps are independently-rulable mechanisms. |
| `mattpocock_skills:skill:skills/engineering/wizard#ephemeral-by-default` | `ephemeral-by-default` (new) | match |  |
| `mattpocock_skills:skill:skills/engineering/wizard#syntax-executable-handoff` | `syntax-check-handoff` (new) | match |  |
| `mattpocock_skills:skill:skills/engineering/wizard#template-executable-fixes` | `template-robustness` (new) | match |  |
| `mattpocock_skills:skill:skills/in-progress/loop-me#push-right` | `push-right` (new) | match |  |
| `mattpocock_skills:skill:skills/in-progress/loop-me#decision-summary-brief` | `decision-summary-brief` (new) | match |  |
| `mattpocock_skills:skill:skills/in-progress/loop-me#loop-lens` | `loop-lens` (new) | match |  |
| `mattpocock_skills:skill:skills/in-progress/loop-me#workflow-spec-artifact` | `workflow-spec-artifact` (new), `spec-done-when-buildable` (new), `world-notes` (new) | split | Artifact location, the buildable-without-a-question completion bar, and the NOTES world capture are separate mechanisms. |
| `mattpocock_skills:skill:skills/in-progress/loop-me#trigger-checkpoint-vocab` | `workflow-vocabulary` (new), `mandate-nothing-structural` (new) | split | The vocabulary and the impose-no-structure rule are separate mechanisms. |
| `mattpocock_skills:skill:skills/in-progress/setup-ts-deep-modules#deep-module-shape` | `deep-module-shape` (new) | match |  |
| `mattpocock_skills:skill:skills/in-progress/setup-ts-deep-modules#entry-point-boundary-rules` | `entry-point-only-imports` (new), `intra-package-freedom` (new), `tests-through-entry-points` (new), `no-cycles` (new) | split | Four distinct dependency-cruiser rules. |
| `mattpocock_skills:skill:skills/in-progress/setup-ts-deep-modules#depth-not-designated-index` | `public-surface-is-root-files` (new), `discourage-barrels` (new) | split | Root-files-as-surface and discourage-barrels are separate rules. |
| `mattpocock_skills:skill:skills/in-progress/setup-ts-deep-modules#prove-the-rules-bite` | `prove-the-rules-bite` (new) | match |  |
| `mattpocock_skills:skill:skills/in-progress/setup-ts-deep-modules#context-pointer-to-convention` | `document-boundary-readme` (new), `link-convention-from-agents-file` (new) | split | Writing the README and pointing to it from the agent file are separate mechanisms. |
| `mattpocock_skills:skill:skills/in-progress/setup-ts-deep-modules#preserve-existing-config` | `preserve-existing-config` (new) | match |  |
| `mattpocock_skills:skill:skills/in-progress/setup-ts-deep-modules#wire-umbrella-check` | `wire-umbrella-check` (new) | match |  |
| `mattpocock_skills:skill:skills/in-progress/setup-ts-deep-modules#scaffold-example` | `scaffold-example` (new) | match |  |
| `mattpocock_skills:skill:skills/in-progress/setup-ts-deep-modules#tests-folder-privacy` | `tests-through-entry-points` (new) | merge | Same mechanism as rule 3 of the boundary ruleset. |
| `(new mechanism)` | `detect-package-conventions` (new) | new | Step 1 detects package manager and packages root before configuring; the old list omitted it. |
| `(new mechanism)` | `flat-packages` (new) | new | Packages are one flat tier and may not contain another package; the old list omitted this constraint. |
| `mattpocock_skills:skill:skills/productivity/grilling#design-tree` | `map-decisions` (ours) | match |  |
| `mattpocock_skills:skill:skills/productivity/grilling#frontier-rounds` | `question-batching` (ours) | match |  |
| `mattpocock_skills:skill:skills/productivity/grilling#recommended-answer` | `recommended-answer` (ours) | match | r1 sweep: renamed from recommend-with-assumptions |
| `mattpocock_skills:skill:skills/productivity/grilling#yes-accepts-recommendation` | `yes-accepts-recommendation` (new) | match |  |
| `mattpocock_skills:skill:skills/productivity/grilling#round-format` | `round-format` (new) | match |  |
| `mattpocock_skills:skill:skills/productivity/grilling#facts-via-subagent` | `self-serve-facts` (ours) | match |  |
| `mattpocock_skills:skill:skills/productivity/grilling#stop-on-settled` | `exhaustive-completion` (new) | merge | Same stopping condition as exhaustive-completion (frontier empty, nothing silently assumed). |
| `mattpocock_skills:skill:skills/productivity/grilling#exhaustive-completion` | `exhaustive-completion` (new) | match |  |
| `mattpocock_skills:skill:skills/productivity/grilling#reconfirm-before-action` | `reconfirm-before-action` (new) | match |  |
| `mattpocock_skills:skill:skills/productivity/handoff#handoff-doc` | `handoff-doc` (new) | match |  |
| `mattpocock_skills:skill:skills/productivity/handoff#temp-dir-destination` | `temp-dir-destination` (new) | match |  |
| `mattpocock_skills:skill:skills/productivity/handoff#suggested-skills` | `suggested-skills` (new) | match |  |
| `mattpocock_skills:skill:skills/productivity/handoff#no-duplication` | `link-dont-copy` (new) | match |  |
| `mattpocock_skills:skill:skills/productivity/handoff#redact-secrets` | `redact-secrets` (new) | match |  |
| `mattpocock_skills:skill:skills/productivity/handoff#tailor-to-next-focus` | `tailor-to-next-focus` (new) | match |  |
| `mattpocock_skills:skill:skills/productivity/teach#teaching-workspace` | `teaching-workspace` (ours), `always-stateful-course` (new) | split | r1 finding 17: upstream treats every request as a stateful course |
| `mattpocock_skills:skill:skills/productivity/teach#workspace-from-run-dir` | `workspace-from-run-dir` (new) | match |  |
| `mattpocock_skills:skill:skills/productivity/teach#mission-grounding` | `mission-grounding` (ours) | match |  |
| `mattpocock_skills:skill:skills/productivity/teach#zone-of-proximal-development` | `proximal-next-lesson` (new) | new | r1 finding 17: chooses the next lesson from learning records, unlike level-adaptation |
| `mattpocock_skills:skill:skills/productivity/teach#storage-strength` | `storage-strength` (new) | match |  |
| `mattpocock_skills:skill:skills/productivity/teach#lessons-and-assets` | `lesson-format` (ours), `reusable-assets` (ours), `html-lessons` (new), `shared-component-extraction` (new) | split | Lesson format and the reusable assets component library are separate mechanisms; r2 #3: mandatory HTML (teach/SKILL.md:49) and component extraction (teach/SKILL.md:67) are their own traits, with no draft ruling yet |
| `mattpocock_skills:skill:skills/productivity/teach#glossary-format` | `glossary-format` (ours) | match |  |
| `mattpocock_skills:skill:skills/productivity/teach#learning-records` | `learning-records` (ours) | match |  |
| `mattpocock_skills:skill:skills/productivity/teach#quiz-equal-length` | `quiz-equal-length` (new) | match |  |
| `mattpocock_skills:skill:skills/productivity/teach#vary-answer-position` | `vary-answer-position` (new) | match |  |
| `mattpocock_skills:skill:skills/productivity/teach#trusted-resources` | `resources-curation` (ours) | match |  |
| `mattpocock_skills:skill:skills/productivity/teach#wisdom-community-referral` | `wisdom-community-referral` (new) | match |  |
| `mattpocock_skills:skill:skills/productivity/teach#reference-sheets` | `reference-sheets` (new) | match |  |
| `mattpocock_skills:skill:skills/productivity/teach#spacing-interleaving` | `retrieval-practice` (ours), `spacing` (new), `interleaving` (new) | split | r1 finding 18: spacing and interleaving are two methods |
| `mattpocock_skills:skill:skills/productivity/teach#preference-notes` | `preference-notes` (new) | match |  |
| `(new mechanism)` | `sourced-explanations` (ours) | new | Lessons must carry citations to trusted sources rather than parametric claims; the old list omitted it. |
| `(new mechanism)` | `tight-feedback-loop` (new) | new | Skills are taught through an immediate, ideally automatic feedback loop; the old list omitted it. |
| `mattpocock_skills:skill:skills/productivity/to-questionnaire#grill-the-send` | `grill-the-send` (ours) | match |  |
| `mattpocock_skills:skill:skills/productivity/to-questionnaire#two-exchange-interview` | `two-exchange-interview` (new) | match |  |
| `mattpocock_skills:skill:skills/productivity/to-questionnaire#gap-targeted-questions` | `gap-targeted-questions` (ours) | match |  |
| `mattpocock_skills:skill:skills/productivity/to-questionnaire#questionnaire-artifact` | `questionnaire-artifact` (new) | match |  |
| `mattpocock_skills:skill:skills/productivity/to-questionnaire#document-structure` | `document-structure` (new) | match |  |
| `mattpocock_skills:skill:skills/productivity/wait-what#repitch-trigger` | `repitch-trigger` (ours) | match |  |
| `mattpocock_skills:skill:skills/productivity/wait-what#controlled-language` | `controlled-language` (ours) | match |  |
| `mattpocock_skills:skill:skills/productivity/wait-what#ubiquitous-language` | `domain-vocabulary` (ours) | match |  |
| `mattpocock_skills:skill:skills/productivity/wait-what#glossary-map-lookup` | `context-map-lookup` (new) | new | r1 sweep: only follows the map, which multi-context-map maintains |
| `mattpocock_skills:skill:skills/productivity/writing-for-agents#context-pointers` | `context-pointers` (ours) | match |  |
| `mattpocock_skills:skill:skills/productivity/writing-for-agents#two-loads` | `two-loads` (ours) | match |  |
| `mattpocock_skills:skill:skills/productivity/writing-for-agents#information-hierarchy` | `inline-vs-disclose` (ours) | match |  |
| `mattpocock_skills:skill:skills/productivity/writing-for-agents#co-location` | `co-location` (new) | match |  |
| `mattpocock_skills:skill:skills/productivity/writing-for-agents#completion-criteria` | `completion-criteria-clarity` (ours), `completion-criteria-demand` (new) | split | Clarity (resists premature completion) and demand (drives legwork) are separate levers. |
| `mattpocock_skills:skill:skills/productivity/writing-for-agents#split-by-invocation` | `split-by-invocation` (new) | match |  |
| `mattpocock_skills:skill:skills/productivity/writing-for-agents#sequence-isolation` | `sequence-isolation` (new) | match |  |
| `mattpocock_skills:skill:skills/productivity/writing-for-agents#leading-words` | `leading-words` (new) | match |  |
| `mattpocock_skills:skill:skills/productivity/writing-for-agents#negation-avoidance` | `negation-avoidance` (new) | match |  |
| `mattpocock_skills:skill:skills/productivity/writing-for-agents#pruning` | `single-source-of-truth` (ours), `environment-as-cache` (ours), `relevance-check` (new), `no-op-deletion` (ours) | split | Pruning bundles four independent disciplines: single source of truth, environment-as-cache, relevance, and no-op deletion. |
| `mattpocock_skills:skill:skills/productivity/writing-for-agents#invocation-choice` | `invocation-mode` (ours) | match |  |
| `mattpocock_skills:skill:skills/productivity/writing-for-agents#shared-reference-home` | `shared-reference-home` (new) | match |  |
| `mattpocock_skills:skill:skills/productivity/writing-for-agents#router-skills` | `router-skills` (new) | match |  |
