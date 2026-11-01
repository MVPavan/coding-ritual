---
skill: codebase-design
domain: engineering
stage: Design
substage: Architecture
secondary: []
family: interface-design
aliases: []
status: active
---
# codebase-design

Use for substantive module-interface, encapsulation, or testability decisions. Skip ordinary code explanations and cosmetic refactors.

**Boundary:** Decides module interfaces, encapsulation and testability in code; domain terms and ADRs are domain-modeling, revising design documents is design-evolve, and runnable experiments are prototype.

<!-- registry:generated traits -->
- `module-vocabulary`: Reason about design with a shared deep-module glossary: module, interface, depth, seam, adapter and locality.
- `project-term-allowance`: Let the project's own precise terms, such as API, service or boundary, stand beside the design glossary rather than banning them.
- `interface-is-everything`: Treat an interface as every fact a caller must know — invariants, ordering, errors, configuration and performance — not just the type signature.
- `depth-as-leverage`: Prefer modules whose manageable interface hides a large amount of useful behaviour.
- `deletion-test`: Question a layer that only forwards and keep one whose removal would spread complexity across callers.
- `inject-dependencies`: Pass a module's external dependencies in as arguments rather than constructing them inside it, so callers and tests can substitute them. (Where it clarifies behaviour, not as a blanket rule.)
- `return-not-mutate`: Design functions to return results rather than cause side effects, so behaviour can be observed directly. (Pure calculations where they clarify behaviour, isolating legitimate side effects.)
- `single-adapter-justified`: Accept an interface justified by encapsulation, ownership or a present testing need with a single adapter, treating extra adapters as evidence of real variation rather than a prerequisite.
- `internal-seams`: Allow internal seams and focused internal tests without exposing internals through the public interface merely to satisfy a testing rule.
- `dependency-categories`: Classify a module's dependencies as in-process, locally substitutable, owned remote or true external to choose how it is tested across its seam. (Categories suggest options, never automatic permission to merge modules.)
- `covered-test-removal`: Remove an old test only when its behaviour is covered elsewhere or deliberately retired, inspecting a changed test rather than deleting it automatically.
- `design-it-twice`: Optionally compare a few materially different interface designs before a consequential choice, without forcing a multi-agent exercise on a clear one.
- `design-proposal-contents`: Have each design proposal return its interface, a usage example, the hidden internals, its dependency strategy and its trade-offs.
- `interface-design-recommendation`: Finish a comparison of interface designs with an opinionated recommendation.
<!-- /registry:generated traits -->

<!-- registry:generated lineage -->
- **mattpocock_skills:skill:skills/engineering/codebase-design#module-vocabulary** `skills/engineering/codebase-design/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2
- **mattpocock_skills:skill:skills/engineering/codebase-design#interface-is-everything** `skills/engineering/codebase-design/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2
- **mattpocock_skills:skill:skills/engineering/codebase-design#depth-as-leverage** `skills/engineering/codebase-design/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2
- **mattpocock_skills:skill:skills/engineering/codebase-design#deletion-test** `skills/engineering/codebase-design/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2
- **mattpocock_skills:skill:skills/engineering/codebase-design#internal-seams** `skills/engineering/codebase-design/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2
- **mattpocock_skills:skill:skills/engineering/codebase-design#inject-dependencies** `skills/engineering/codebase-design/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2
- **mattpocock_skills:skill:skills/engineering/codebase-design#return-not-mutate** `skills/engineering/codebase-design/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2
- **mattpocock_skills:skill:skills/engineering/codebase-design#small-interface-surface** `skills/engineering/codebase-design/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2
- **mattpocock_skills:skill:skills/engineering/codebase-design#dependency-categories** `skills/engineering/codebase-design/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2
- **mattpocock_skills:skill:skills/engineering/codebase-design#design-proposal-contents** `skills/engineering/codebase-design/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2
- **mattpocock_skills:skill:skills/engineering/codebase-design#parallel-interface-generation** `skills/engineering/codebase-design/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2
- **mattpocock_skills:skill:skills/engineering/codebase-design#depth-locality-seam-comparison** `skills/engineering/codebase-design/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2 (pending cr-axdt.6.2)
- **mattpocock_skills:skill:skills/engineering/codebase-design#interface-design-recommendation** `skills/engineering/codebase-design/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2
- **mattpocock_skills:skill:skills/engineering/improve-codebase-architecture#deletion-test** `skills/engineering/improve-codebase-architecture/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2
- **mattpocock_skills:skill:skills/engineering/improve-codebase-architecture#module-vocabulary** `skills/engineering/improve-codebase-architecture/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2
- **mattpocock_skills:skill:skills/engineering/improve-codebase-architecture#dependency-categories** `skills/engineering/improve-codebase-architecture/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2
- **mattpocock_skills:skill:skills/engineering/tdd#inject-dependencies** `skills/engineering/tdd/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2
- **mattpocock_skills:skill:skills/engineering/tdd#module-vocabulary** `skills/engineering/tdd/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2
- **mattpocock_skills:skill:skills/in-progress/setup-ts-deep-modules#module-vocabulary** `skills/in-progress/setup-ts-deep-modules/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2
- **cursor_plugins:skill:pstack/skills/principle-minimize-reader-load#deletion-test** `pstack/skills/principle-minimize-reader-load/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/principle-minimize-reader-load#depth-as-leverage** `pstack/skills/principle-minimize-reader-load/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/principle-minimize-reader-load#return-not-mutate** `pstack/skills/principle-minimize-reader-load/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
<!-- /registry:generated lineage -->

<!-- registry:generated history -->
- `2026-11-01` **adopt-merged** (2026-11-01-cursor_plugins-pstack-principles:084): Checkpoint at 4dd1d05 for the owner's trait rulings: 9 adopt, 1 reject.
- `2026-11-01` **reject** (2026-11-01-cursor_plugins-pstack-principles:083): Lands as a principle unit. An agent cannot run it: there is no new reader to time, and the agent's own speed says nothing about a human's. The two axes (reader…
- `2026-11-01` **adopt** (2026-11-01-cursor_plugins-pstack-principles:078): Lands as covered. codebase-design prefers pure calculations where they clarify (the 'pure functions' part of the line).
- `2026-11-01` **adopt** (2026-11-01-cursor_plugins-pstack-principles:077): Lands as covered. codebase-design defines depth as behaviour hidden behind a manageable interface.
- `2026-11-01` **adopt** (2026-11-01-cursor_plugins-pstack-principles:076): Lands as covered. codebase-design questions a layer that only forwards. Matched for the pass-through rule only; the adapter-count question is the collapse-thin…
- `2026-11-01` **reject** (2026-11-01-cursor_plugins-pstack-principles:054): Lands as a skill or playbook trait. Not held as such. Ours holds stronger forms where a fix has a test: the bug-fix playbook's step 3 calls test-driven-develop…
- `2026-11-01` **defer** (2026-11-01-cursor_plugins-pstack-principles:053): Lands as a skill or playbook trait. A sequencing rule for planning, not a lens. The pending prefactor-first adoption covers most of it.
- `2026-11-01` **defer** (2026-11-01-cursor_plugins-pstack-principles:007): Lands as a principle unit. Sound but abstract; without an example it adds little a reader can apply, and codebase-design's depth vocabulary is its natural home.
- `2026-10-30` **adopt-merged** (2026-10-30-mattpocock_skills-5beb35b:577): Checkpoint at 5beb35b for the owner's trait rulings: 1 adopt, 2 defer, 23 out-of-scope.
- `2026-10-30` **adopt-merged** (2026-10-30-mattpocock_skills-5beb35b:560): Checkpoint at 5beb35b for the owner's trait rulings: 13 adopt, 9 defer.
- `2026-10-30` **adopt** (2026-10-30-mattpocock_skills-5beb35b:381): HELD: codebase-design: its trigger fires on module-interface and testability decisions (codebase-design/SKILL.md:3), the ones this setup encodes.
- `2026-10-30` **adopt** (2026-10-30-mattpocock_skills-5beb35b:212): HELD: codebase-design: its trigger fires on testability decisions (codebase-design/SKILL.md:3), which a test-first change makes.
- `2026-10-30` **adopt** (2026-10-30-mattpocock_skills-5beb35b:207): HELD: codebase-design (.claude/skills/codebase-design/SKILL.md:35): Passing dependencies in is a module-design rule our codebase-design states (SKILL.md:35: pr…
- `2026-10-30` **adopt** (2026-10-30-mattpocock_skills-5beb35b:037): HELD: codebase-design: ours evaluates interfaces with codebase-design (SKILL.md:15-16), which lists the dependency categories.
- `2026-10-30` **adopt** (2026-10-30-mattpocock_skills-5beb35b:031): POINTER: .claude/skills/improve-codebase-architecture/SKILL.md:15-16 evaluates interfaces with codebase-design's vocabulary.
- `2026-10-30` **adopt** (2026-10-30-mattpocock_skills-5beb35b:025): POINTER: .claude/skills/improve-codebase-architecture/SKILL.md:20 applies codebase-design's deletion test to each candidate.
- `2026-10-30` **adopt** (2026-10-30-mattpocock_skills-5beb35b:022): Ours ends the comparison by recommending one design with reasons.
- `2026-10-30` **adopt** (2026-10-30-mattpocock_skills-5beb35b:021): Ours compares depth, locality, error behaviour and testability (DESIGN-IT-TWICE.md:11) but not seam placement, which is the third axis the vocabulary defines; …
- `2026-10-30` **adopt** (2026-10-30-mattpocock_skills-5beb35b:020): Ours deliberately keeps the exercise optional and delegation proportional (DESIGN-IT-TWICE.md:6-8), as U-07 and C-14 require.
- `2026-10-30` **adopt** (2026-10-30-mattpocock_skills-5beb35b:019): Ours asks each design for its caller-facing contract, a usage example, hidden complexity, dependency strategy and migration cost, then compares trade-offs.
- `2026-10-30` **defer** (2026-10-30-mattpocock_skills-5beb35b:018): Owner deferred the report's reject recommendation, to review the set later: AGENTS.md already requires worker briefs to carry relevant context pointers; a skil…
- `2026-10-30` **defer** (2026-10-30-mattpocock_skills-5beb35b:017): Owner deferred the report's reject recommendation, to review the set later: Ours already states caller needs, constraints, dependencies and invariants before d…
- `2026-10-30` **defer** (2026-10-30-mattpocock_skills-5beb35b:016): Owner deferred the report's reject recommendation, to review the set later: Ours tests the owned boundary with safe fixtures or fakes and verifies provider ass…
- `2026-10-30` **defer** (2026-10-30-mattpocock_skills-5beb35b:015): Owner deferred the report's reject recommendation, to review the set later: Ours asks for an explicit transport contract and injects an adapter only when it is…
- `2026-10-30` **defer** (2026-10-30-mattpocock_skills-5beb35b:014): Owner deferred the report's reject recommendation, to review the set later: Ours deliberately allows a real lightweight instance or a faithful fake with integr…
- `2026-10-30` **defer** (2026-10-30-mattpocock_skills-5beb35b:013): Owner deferred the report's reject recommendation, to review the set later: Opposite stance: ours keeps meaningful internal tests and inspects changed tests; i…
- `2026-10-30` **adopt** (2026-10-30-mattpocock_skills-5beb35b:012): Ours classifies dependencies into the same four shapes and treats the categories as options, not automatic permission to merge.
- `2026-10-30` **adopt** (2026-10-30-mattpocock_skills-5beb35b:011): Ours deliberately judges the interface by leverage and leakage (SKILL.md:26-27); a small surface follows where it pays, without a separate minimising rule.
- `2026-10-30` **adopt** (2026-10-30-mattpocock_skills-5beb35b:010): Ours prefers pure calculations and isolates legitimate side effects.
- `2026-10-30` **adopt** (2026-10-30-mattpocock_skills-5beb35b:009): Ours prefers explicit dependencies where they clarify behaviour, a qualified form that S-08 favours over a blanket rule.
- `2026-10-30` **adopt** (2026-10-30-mattpocock_skills-5beb35b:008): Ours allows internal seams and focused internal tests without exposing internals.
- `2026-10-30` **defer** (2026-10-30-mattpocock_skills-5beb35b:007): Owner deferred the report's reject recommendation, to review the set later: Opposite stance: a present need can justify one adapter, and ours explicitly does n…
- `2026-10-30` **defer** (2026-10-30-mattpocock_skills-5beb35b:006): Owner deferred the report's reject recommendation, to review the set later: Opposite stance: ours treats focused internal tests as valid, not as evidence of a …
- `2026-10-30` **adopt** (2026-10-30-mattpocock_skills-5beb35b:005): Ours questions a layer whose deletion only removes forwarding and keeps one whose removal spreads complexity.
- `2026-10-30` **adopt** (2026-10-30-mattpocock_skills-5beb35b:004): Ours defines depth as useful behaviour behind a manageable interface and asks what callers gain.
- `2026-10-30` **adopt** (2026-10-30-mattpocock_skills-5beb35b:003): Ours defines the interface as invariants, ordering, errors, configuration and performance, not just signatures.
- `2026-10-30` **defer** (2026-10-30-mattpocock_skills-5beb35b:002): Owner deferred the report's reject recommendation, to review the set later: Opposite stance: ours uses precise project terms, including the very words upstream…
- `2026-10-30` **adopt** (2026-10-30-mattpocock_skills-5beb35b:001): Ours defines module, interface, depth, seam, adapter and locality as the shared design glossary.
- `2026-08-13` **adopt** (2026-10-14-migration:117): Adopted verbatim (SKILL + DEEPENING + DESIGN-IT-TWICE; their agents/openai.yaml metadata excluded). Only source of the deep-module vocabulary (module/interface…
- `2026-08-11` **adopt** (2026-10-14-migration:035) *(superseded)*: The only source of deep-module vocabulary, with the anti-synonym rule, the deletion test and the two-adapters seam rule.
<!-- /registry:generated history -->

<!-- registry:generated reviews -->
None yet.
<!-- /registry:generated reviews -->

<!-- registry:generated sources -->
- `deletion-test`:
  - `cursor_plugins:skill:pstack/skills/principle-minimize-reader-load#deletion-test` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
  - `mattpocock_skills:skill:skills/engineering/codebase-design#deletion-test` (adopted at 5beb35b040e3de97e54fa9e386d7e42d15c295c2)
  - `mattpocock_skills:skill:skills/engineering/improve-codebase-architecture#deletion-test` (adopted at 5beb35b040e3de97e54fa9e386d7e42d15c295c2)
- `dependency-categories`:
  - `mattpocock_skills:skill:skills/engineering/codebase-design#dependency-categories` (adopted at 5beb35b040e3de97e54fa9e386d7e42d15c295c2)
  - `mattpocock_skills:skill:skills/engineering/improve-codebase-architecture#dependency-categories` (adopted at 5beb35b040e3de97e54fa9e386d7e42d15c295c2)
- `depth-as-leverage`:
  - `cursor_plugins:skill:pstack/skills/principle-minimize-reader-load#depth-as-leverage` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
  - `mattpocock_skills:skill:skills/engineering/codebase-design#depth-as-leverage` (adopted at 5beb35b040e3de97e54fa9e386d7e42d15c295c2)
  - `mattpocock_skills:skill:skills/engineering/codebase-design#small-interface-surface` (adopted at 5beb35b040e3de97e54fa9e386d7e42d15c295c2)
- `design-it-twice`:
  - `mattpocock_skills:skill:skills/engineering/codebase-design#parallel-interface-generation` (adopted at 5beb35b040e3de97e54fa9e386d7e42d15c295c2)
- `design-proposal-contents`:
  - `mattpocock_skills:skill:skills/engineering/codebase-design#design-proposal-contents` (adopted at 5beb35b040e3de97e54fa9e386d7e42d15c295c2)
- `inject-dependencies`:
  - `mattpocock_skills:skill:skills/engineering/codebase-design#inject-dependencies` (adopted at 5beb35b040e3de97e54fa9e386d7e42d15c295c2)
  - `mattpocock_skills:skill:skills/engineering/tdd#inject-dependencies` (adopted at 5beb35b040e3de97e54fa9e386d7e42d15c295c2)
- `interface-design-recommendation`:
  - `mattpocock_skills:skill:skills/engineering/codebase-design#interface-design-recommendation` (adopted at 5beb35b040e3de97e54fa9e386d7e42d15c295c2)
- `interface-is-everything`:
  - `mattpocock_skills:skill:skills/engineering/codebase-design#interface-is-everything` (adopted at 5beb35b040e3de97e54fa9e386d7e42d15c295c2)
- `internal-seams`:
  - `mattpocock_skills:skill:skills/engineering/codebase-design#internal-seams` (adopted at 5beb35b040e3de97e54fa9e386d7e42d15c295c2)
- `module-vocabulary`:
  - `mattpocock_skills:skill:skills/engineering/codebase-design#module-vocabulary` (adopted at 5beb35b040e3de97e54fa9e386d7e42d15c295c2)
  - `mattpocock_skills:skill:skills/engineering/improve-codebase-architecture#module-vocabulary` (adopted at 5beb35b040e3de97e54fa9e386d7e42d15c295c2)
  - `mattpocock_skills:skill:skills/engineering/tdd#module-vocabulary` (adopted at 5beb35b040e3de97e54fa9e386d7e42d15c295c2)
  - `mattpocock_skills:skill:skills/in-progress/setup-ts-deep-modules#module-vocabulary` (adopted at 5beb35b040e3de97e54fa9e386d7e42d15c295c2)
- `return-not-mutate`:
  - `cursor_plugins:skill:pstack/skills/principle-minimize-reader-load#return-not-mutate` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
  - `mattpocock_skills:skill:skills/engineering/codebase-design#return-not-mutate` (adopted at 5beb35b040e3de97e54fa9e386d7e42d15c295c2)
<!-- /registry:generated sources -->

<!-- registry:generated declined -->
- `cursor_plugins:skill:pstack/skills/principle-boundary-discipline#policy-at-edge` (defer): Lands as a principle unit. Sound but abstract; without an example it adds little a reader can apply, and codebase-design's depth vocabulary is its natural home.
- `cursor_plugins:skill:pstack/skills/principle-foundational-thinking#scaffold-first` (defer): Lands as a skill or playbook trait. A sequencing rule for planning, not a lens. The pending prefactor-first adoption covers most of it.
- `cursor_plugins:skill:pstack/skills/principle-foundational-thinking#test-before-fix` (reject): Lands as a skill or playbook trait. Not held as such. Ours holds stronger forms where a fix has a test: the bug-fix playbook's step 3 calls test-driven-develop…
- `cursor_plugins:skill:pstack/skills/principle-minimize-reader-load#thirty-second-trace-test` (reject): Lands as a principle unit. An agent cannot run it: there is no new reader to time, and the agent's own speed says nothing about a human's. The two axes (reader…
- `mattpocock_skills:skill:skills/engineering/codebase-design#design-brief-vocabulary` (defer): Owner deferred the report's reject recommendation, to review the set later: AGENTS.md already requires worker briefs to carry relevant context pointers; a skil…
- `mattpocock_skills:skill:skills/engineering/codebase-design#external-port-mock-adapter` (defer): Owner deferred the report's reject recommendation, to review the set later: Ours tests the owned boundary with safe fixtures or fakes and verifies provider ass…
- `mattpocock_skills:skill:skills/engineering/codebase-design#interface-is-test-surface` (defer): Owner deferred the report's reject recommendation, to review the set later: Opposite stance: ours treats focused internal tests as valid, not as evidence of a …
- `mattpocock_skills:skill:skills/engineering/codebase-design#local-stand-in-testing` (defer): Owner deferred the report's reject recommendation, to review the set later: Ours deliberately allows a real lightweight instance or a faithful fake with integr…
- `mattpocock_skills:skill:skills/engineering/codebase-design#port-with-memory-adapter` (defer): Owner deferred the report's reject recommendation, to review the set later: Ours asks for an explicit transport contract and injects an adapter only when it is…
- `mattpocock_skills:skill:skills/engineering/codebase-design#problem-space-framing` (defer): Owner deferred the report's reject recommendation, to review the set later: Ours already states caller needs, constraints, dependencies and invariants before d…
- `mattpocock_skills:skill:skills/engineering/codebase-design#replace-dont-layer` (defer): Owner deferred the report's reject recommendation, to review the set later: Opposite stance: ours keeps meaningful internal tests and inspects changed tests; i…
- `mattpocock_skills:skill:skills/engineering/codebase-design#two-adapters-rule` (defer): Owner deferred the report's reject recommendation, to review the set later: Opposite stance: a present need can justify one adapter, and ours explicitly does n…
- `mattpocock_skills:skill:skills/engineering/codebase-design#vocabulary-ban` (defer): Owner deferred the report's reject recommendation, to review the set later: Opposite stance: ours uses precise project terms, including the very words upstream…
<!-- /registry:generated declined -->
