---
skill: research
domain: core
stage: Discovery
substage: Research
secondary: []
family: source-research
aliases: []
status: active
---
# research

Use when a decision needs multiple sources gathered and weighed. Answer a single factual lookup directly from an appropriate source.

<!-- registry:generated traits -->
- `decision-framing`: State the decision, scope, constraints and material unknowns, and choose sources by what would change the answer.
- `primary-source-preference`: Prefer primary sources such as official docs, source code and specs over secondary write-ups. (Current primary sources for changing facts and technical behaviour.)
- `source-version-dating`: Record the versions and dates of the sources behind changing facts.
- `vendor-claim-testing`: Test vendor claims with independent observation, distinguishing reported experience from proof.
- `source-weighting`: Weight each source by how well its type supports the claim's domain, discounting weak-alone signals and documented red flags.
- `evidence-separation`: Compare alternatives and counterevidence while separating verified fact, inference, uncertainty and conflicts with recorded decisions.
- `disconfirming-red-team`: Surface the strongest case against the conclusion and name what would reverse the recommendation.
- `structured-synthesis`: For a complex question, organize evidence with a claim table and a pattern scan that turns facts into decision-relevant implications.
- `research-playbooks`: Follow a research sequence matched to the question's domain, pulling from a second only when it truly spans domains.
- `judgment-frameworks`: Apply one to three comparison frameworks to sharpen a choice rather than to decorate the report.
- `cited-artifact`: Bind citations to the claims they support in the research output.
- `scaled-report`: Answer at the requested scale, saving a durable report only when requested or useful for an authorized handoff.
- `decision-sufficient-stop`: Stop investigating when remaining uncertainty no longer changes the decision, or when a named access or budget limit is reached.
- `sizeable-delegation`: Delegate only a sizeable, independent part of the investigation.
<!-- /registry:generated traits -->

<!-- registry:generated lineage -->
- **mattpocock_skills:skill:skills/engineering/research** `reference_harnesses/mattpocock_skills/skills/engineering/research/SKILL.md` @ 84fdeff
- **agent-skills:skill:skills/source-driven-development** `skills/source-driven-development/SKILL.md` @ 7676817
- **mattpocock_skills:skill:skills/engineering/research** `skills/engineering/research/SKILL.md` @ 84fdeff
<!-- /registry:generated lineage -->

<!-- registry:generated history -->
- `2026-08-14` **adopt** (2026-10-14-migration:137): Unified into skill:skills/research: deep-research's full protocol as the body with this skill's durable cited Markdown artifact contract (docs/research/), per-…
- `2026-08-14` **adopt** (2026-10-14-migration:131): Round 2 supersede: conflict A/B stop, rationalization rows, and claim-bound citation formatting absorbed into skill:skills/research. Upstream drift answered: t…
- `2026-08-11` **adopt** (2026-10-14-migration:080) *(superseded)*: The only background-delegated primary-source investigation producing a durable cited artifact. Distinct from source-driven-development, which grounds decisions…
<!-- /registry:generated history -->

<!-- registry:generated reviews -->
- [skill-comparisons/research-workflow](../../../archive/skill-comparisons/research-workflow/)
<!-- /registry:generated reviews -->

<!-- registry:generated sources -->
No adopted traits recorded.
<!-- /registry:generated sources -->

<!-- registry:generated declined -->
No declined traits recorded.
<!-- /registry:generated declined -->
