---
skill: build-a-lever
domain: core
stage: Building
substage: Implementation
secondary: []
family: 
aliases: []
status: active
---
# build-a-lever

No description.

**Boundary:** Builds and proves a rerunnable tool (script, codemod, generator or check) that does or proves real work; a throwaway experiment answering a design question is prototype, and test-first proof of a behaviour change is tdd.

<!-- registry:generated traits -->
- `hand-first-recipe`: Do the first unit by hand, then build the tool and show it reproduces the hand result before running it on the rest.
- `minimal-tool`: Build the smallest script that does or proves the job, never a framework.
- `rerun-safe-tool`: Make a work tool safe to rerun on input it has already changed.
- `proposed-artifact-commit`: Keep a work tool or proof artifact in the scratch folder and propose committing it when the work will be rerun or audited.
<!-- /registry:generated traits -->

<!-- registry:generated lineage -->
- **cursor_plugins:skill:pstack/skills/principle-build-the-lever#hand-first-recipe** `pstack/skills/principle-build-the-lever/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/principle-build-the-lever#rerun-safe-tool** `pstack/skills/principle-build-the-lever/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/principle-build-the-lever#outliving-tool-commit** `pstack/skills/principle-build-the-lever/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/principle-build-the-lever#minimal-tool** `pstack/skills/principle-build-the-lever/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/principle-prove-it-works#audit-trail-proof-commit** `pstack/skills/principle-prove-it-works/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
<!-- /registry:generated lineage -->

<!-- registry:generated history -->
- `2026-11-01` **update** (2026-11-01-principles-fixes:010): R10 revised (owner ruling 2026-11-01, critic 1b-build finding 1): the description and opening line narrow activation to a tool that saves repeated work or supp…
- `2026-11-01` **adopt** (2026-11-01-cursor_plugins-pstack-principles:214): Completes pending 2026-11-01-cursor_plugins-pstack-principles:100: the principles build (cr-r2pa.1.2) delivered proposed-artifact-commit in build-a-lever, chec…
- `2026-11-01` **adopt** (2026-11-01-cursor_plugins-pstack-principles:213): Completes pending 2026-11-01-cursor_plugins-pstack-principles:017: the principles build (cr-r2pa.1.2) delivered minimal-tool in build-a-lever, checked whole ag…
- `2026-11-01` **adopt** (2026-11-01-cursor_plugins-pstack-principles:212): Completes pending 2026-11-01-cursor_plugins-pstack-principles:016: the principles build (cr-r2pa.1.2) delivered proposed-artifact-commit in build-a-lever, chec…
- `2026-11-01` **adopt** (2026-11-01-cursor_plugins-pstack-principles:211): Completes pending 2026-11-01-cursor_plugins-pstack-principles:013: the principles build (cr-r2pa.1.2) delivered rerun-safe-tool in build-a-lever, checked whole…
- `2026-11-01` **adopt** (2026-11-01-cursor_plugins-pstack-principles:210): Completes pending 2026-11-01-cursor_plugins-pstack-principles:012: the principles build (cr-r2pa.1.2) delivered hand-first-recipe in build-a-lever, checked who…
- `2026-11-01` **adopt** (2026-11-01-cursor_plugins-pstack-principles:100) *(superseded)*: Lands as a skill or playbook trait, into `proposed-artifact-commit`. Upstream keeps the proof visible and commits it only for large or complex work needing an …
- `2026-11-01` **adopt** (2026-11-01-cursor_plugins-pstack-principles:017) *(superseded)*: Lands as a skill or playbook trait. AGENTS.md bounds the change delivered and bans speculative abstractions; neither bounds the tool built to deliver it. One c…
- `2026-11-01` **adopt** (2026-11-01-cursor_plugins-pstack-principles:016) *(superseded)*: Lands as a skill or playbook trait, into `proposed-artifact-commit`. Upstream commits on its own condition; AGENTS.md puts temporary artifacts in the scratch f…
- `2026-11-01` **adopt** (2026-11-01-cursor_plugins-pstack-principles:013) *(superseded)*: Lands as a skill or playbook trait. AGENTS.md retries only when repetition is safe; nothing makes a work tool safe to rerun on input it already edited, which i…
- `2026-11-01` **adopt** (2026-11-01-cursor_plugins-pstack-principles:012) *(superseded)*: Lands as a skill or playbook trait. A cheap proof that the tool reproduces the hand result; no holder. It is ordered technique (hand unit, tool, comparison, th…
<!-- /registry:generated history -->

<!-- registry:generated reviews -->
None yet.
<!-- /registry:generated reviews -->

<!-- registry:generated sources -->
- `hand-first-recipe`:
  - `cursor_plugins:skill:pstack/skills/principle-build-the-lever#hand-first-recipe` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `minimal-tool`:
  - `cursor_plugins:skill:pstack/skills/principle-build-the-lever#minimal-tool` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `proposed-artifact-commit`:
  - `cursor_plugins:skill:pstack/skills/principle-build-the-lever#outliving-tool-commit` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
  - `cursor_plugins:skill:pstack/skills/principle-prove-it-works#audit-trail-proof-commit` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `rerun-safe-tool`:
  - `cursor_plugins:skill:pstack/skills/principle-build-the-lever#rerun-safe-tool` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
<!-- /registry:generated sources -->

<!-- registry:generated declined -->
No declined traits recorded.
<!-- /registry:generated declined -->
