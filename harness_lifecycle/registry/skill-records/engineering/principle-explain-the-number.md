---
skill: principle-explain-the-number
domain: engineering
stage: Building
substage: Diagnosis
secondary: []
family: 
aliases: []
status: active
---
# principle-explain-the-number

Apply when about to measure, or before trusting, reporting or acting on a measured number (performance or eval).

**Boundary:** Decides when a measured number counts as evidence; running the optimisation loop is performance-optimization.

<!-- registry:generated traits -->
- `decision-before-measurement`: Before measuring, name the result that would change a decision and the noise floor the result must clear.
- `named-limiter`: Explain a measured number by the resource or code path that bounds it, found from a profile or counters taken during the run and mapped to source, not from reading code.
- `confound-elimination`: List what else a number could be measuring (errors, skipped or cached work, code that never ran, an untuned side, noise, a negligible share) and rule each out with evidence.
- `evidence-with-number`: Report a measured number together with its run count, spread and limiter.
- `eval-result-scrutiny`: Before trusting an eval result, check that every run did the task, that the gap holds across trials and models, and that the scenario matters.
<!-- /registry:generated traits -->

<!-- registry:generated lineage -->
- **cursor_plugins:skill:pstack/skills/principle-explain-the-number#decision-before-measurement** `pstack/skills/principle-explain-the-number/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/principle-explain-the-number#named-limiter** `pstack/skills/principle-explain-the-number/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/principle-explain-the-number#confound-elimination** `pstack/skills/principle-explain-the-number/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/principle-explain-the-number#evidence-with-number** `pstack/skills/principle-explain-the-number/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/principle-explain-the-number#eval-result-scrutiny** `pstack/skills/principle-explain-the-number/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/benchmark-checklist#confound-elimination** `pstack/skills/benchmark-checklist/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/benchmark-checklist#named-limiter** `pstack/skills/benchmark-checklist/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/benchmark-checklist#evidence-with-number** `pstack/skills/benchmark-checklist/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
<!-- /registry:generated lineage -->

<!-- registry:generated history -->
- `2026-11-02` **adopt** (2026-11-02-batch-2:034): Owner ruling 2026-11-02: .claude/skills/principle-explain-the-number/SKILL.md:19 has a reported number carry its run count, its spread and its limiter. It name…
- `2026-11-02` **adopt** (2026-11-02-batch-2:009): Owner ruling 2026-11-02: .claude/skills/principle-explain-the-number/SKILL.md:13-15 explains a number by the resource or code path that bounds it, found from a…
- `2026-11-02` **adopt** (2026-11-02-batch-2:002): Owner ruling 2026-11-02: .claude/skills/principle-explain-the-number/SKILL.md:16-18 lists what else a number could be measuring (errors, skipped or cached work…
- `2026-11-01` **adopt** (2026-11-01-cursor_plugins-pstack-principles:156): Completes pending 2026-11-01-cursor_plugins-pstack-principles:037: the principles build (cr-r2pa.1.2) delivered eval-result-scrutiny in principle-explain-the-n…
- `2026-11-01` **adopt** (2026-11-01-cursor_plugins-pstack-principles:155): Completes pending 2026-11-01-cursor_plugins-pstack-principles:036: the principles build (cr-r2pa.1.2) delivered evidence-with-number in principle-explain-the-n…
- `2026-11-01` **adopt** (2026-11-01-cursor_plugins-pstack-principles:154): Completes pending 2026-11-01-cursor_plugins-pstack-principles:035: the principles build (cr-r2pa.1.2) delivered confound-elimination in principle-explain-the-n…
- `2026-11-01` **adopt** (2026-11-01-cursor_plugins-pstack-principles:153): Completes pending 2026-11-01-cursor_plugins-pstack-principles:034: the principles build (cr-r2pa.1.2) delivered named-limiter in principle-explain-the-number, …
- `2026-11-01` **adopt** (2026-11-01-cursor_plugins-pstack-principles:152): Completes pending 2026-11-01-cursor_plugins-pstack-principles:032: the principles build (cr-r2pa.1.2) delivered decision-before-measurement in principle-explai…
- `2026-11-01` **adopt** (2026-11-01-cursor_plugins-pstack-principles:037) *(superseded)*: Lands as a principle unit. No holder, and we run evals (skill trials, prompting-guide checks). The guide asks for representative evaluation (U-08); this is the…
- `2026-11-01` **adopt** (2026-11-01-cursor_plugins-pstack-principles:036) *(superseded)*: Lands as a principle unit. Ours records command, conditions and results; the limiter is not recorded.
- `2026-11-01` **adopt** (2026-11-01-cursor_plugins-pstack-principles:035) *(superseded)*: Lands as a principle unit. Ours fixes the comparison conditions but does not list the alternative explanations (cached work, code never run, an untuned side) t…
- `2026-11-01` **adopt** (2026-11-01-cursor_plugins-pstack-principles:034) *(superseded)*: Lands as a principle unit. Ours locates cost with measurements; it never asks what bounds the result, which is what exposes a measurement of the wrong thing.
- `2026-11-01` **adopt** (2026-11-01-cursor_plugins-pstack-principles:032) *(superseded)*: Lands as a principle unit. Ours defines metric, workload and target before tuning; naming the decision threshold and noise floor before the run is the missing …
<!-- /registry:generated history -->

<!-- registry:generated reviews -->
- [2026-11-01-upstream-cursor_plugins-4dd1d05-batch-2.md](../../reviews/2026-11-01-upstream-cursor_plugins-4dd1d05-batch-2.md)
<!-- /registry:generated reviews -->

<!-- registry:generated sources -->
- `confound-elimination`:
  - `cursor_plugins:skill:pstack/skills/benchmark-checklist#confound-elimination` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
  - `cursor_plugins:skill:pstack/skills/principle-explain-the-number#confound-elimination` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `decision-before-measurement`:
  - `cursor_plugins:skill:pstack/skills/principle-explain-the-number#decision-before-measurement` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `eval-result-scrutiny`:
  - `cursor_plugins:skill:pstack/skills/principle-explain-the-number#eval-result-scrutiny` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `evidence-with-number`:
  - `cursor_plugins:skill:pstack/skills/benchmark-checklist#evidence-with-number` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
  - `cursor_plugins:skill:pstack/skills/principle-explain-the-number#evidence-with-number` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `named-limiter`:
  - `cursor_plugins:skill:pstack/skills/benchmark-checklist#named-limiter` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
  - `cursor_plugins:skill:pstack/skills/principle-explain-the-number#named-limiter` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
<!-- /registry:generated sources -->

<!-- registry:generated declined -->
No declined traits recorded.
<!-- /registry:generated declined -->
