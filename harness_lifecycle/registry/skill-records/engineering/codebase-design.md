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

## Capability

Use for substantive module-interface, encapsulation, or testability decisions. Skip ordinary code explanations and cosmetic refactors.

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
<!-- /registry:generated traits -->

<!-- registry:generated lineage -->
- **mattpocock_skills:skill:skills/engineering/codebase-design** `reference_harnesses/mattpocock_skills/skills/engineering/codebase-design/SKILL.md` @ 84fdeff
- **mattpocock_skills:skill:skills/engineering/codebase-design** `skills/engineering/codebase-design/SKILL.md`
<!-- /registry:generated lineage -->

<!-- registry:generated history -->
- `2026-08-13` **adopt** (2026-10-14-migration:117): Adopted verbatim (SKILL + DEEPENING + DESIGN-IT-TWICE; their agents/openai.yaml metadata excluded). Only source of the deep-module vocabulary (module/interface…
- `2026-08-11` **adopt** (2026-10-14-migration:035) *(superseded)*: The only source of deep-module vocabulary, with the anti-synonym rule, the deletion test and the two-adapters seam rule.
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
