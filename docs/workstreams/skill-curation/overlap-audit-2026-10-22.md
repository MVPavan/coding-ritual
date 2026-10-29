# Overlap audit of our 36 skills (2026-10-22, revision 2)

Input: the `### Covers` lists of all 36 skill records
(`harness_lifecycle/registry/skill-records/`), checked against the skill text.
Paths below are relative to `.claude/skills/`. Author: orchestrator; critic: Sol
high (`scratchpad/sol-overlap-review.md`), round 1 REVISE with 15 findings, all
accepted and folded in here.

Test: two skills overlap when both own the same mechanism (a rule, gate, method
or format an agent could follow from either). A pipeline (one hands its output
to the next) and a stated boundary are not overlaps. A different audience alone
does not make a shared method a non-overlap (registry README §2 rule 4).

## Real overlaps: one owner, the others point to it

| # | Skills | Shared mechanism | Evidence | Owner, and what the others keep |
|---|---|---|---|---|
| 1 | test-driven-development · planning · brainstorming · codebase-design · review | Testing mechanics: seam choice (three different heuristics), faithful substitutes, test retention, independent expectations | `test-driven-development/SKILL.md:20-24`, `references/writing-good-tests.md:10-12,28-29`; `planning/references/plan-format.md:47` ("public observable boundaries", required, which also contradicts the Pocock rejection of public-only seams); `brainstorming/references/spec-template.md:75-76` (highest seam, fewest); `codebase-design/SKILL.md:32`, `DEEPENING.md:10-18`; `review/references/code.md:35-36` | **test-driven-development.** Plan and spec only record the chosen seam; design keeps interface justification; review applies TDD's criteria |
| 2 | beads · execution | Continuity: resume from the last note after compaction or a new session | `beads/references/usage.md:260-261,304-305`; `execution/references/workstream-mode.md:29-35` | **beads** owns resume notes and session handling. **execution** keeps its run-ledger, finding and Git-baseline recovery (`references/task-engine.md:14-18`). Pending Pocock ideas must land on this split |
| 3 | beads · planning · execution | Tracker contract: phase-title joins, roadmap/spec fields, direct-child selection | `beads/references/usage.md:158-176`; `planning/references/decompose.md:56-78`; `execution/SKILL.md:57-68` | **beads** owns schema and query recipes; planning owns decomposition; execution owns scheduling and phase acceptance |
| 4 | systematic-debugging · test-driven-development | Regression proof: fails before the fix, passes after | `systematic-debugging/SKILL.md:29-31`; `test-driven-development/SKILL.md:28-37` | **test-driven-development**; debugging hands the regression test over |
| 5 | review · execution | Adjudicating incoming findings: verify, disposition, group compatible fixes, scoped re-review | `review/references/feedback.md:3-18`; `execution/references/task-engine.md:70-90` | **review**; execution keeps dispatch, packaging and round budgets |
| 6 | grilling · brainstorming | Interview method: recommendations with labelled assumptions, prerequisite-aware batches, stop when decisions suffice | `grilling/SKILL.md:11-24`; `brainstorming/references/interviewing.md:3-18` | **grilling**; brainstorming keeps its activation boundary and points to it |
| 7 | html-artifact · prototype · brainstorming | Standalone HTML contract: one offline file, no external assets, keyboard safety | `html-artifact/SKILL.md:16-21`; `prototype/LOGIC.md:4-15`; `brainstorming/references/visuals.md:23-29` | **html-artifact** owns the presentation contract; prototype keeps scenarios and success criteria; brainstorming keeps when to offer it |
| 8 | show-me · brainstorming | Inline structural diagrams: when to draw Mermaid, keep it small | `show-me/SKILL.md:13-17,26-28`; `brainstorming/references/visuals.md:8-14` | **show-me**; brainstorming keeps its decision-recording rules |
| 9 | research · brainstorming | Jobs to Be Done (and the shared framework idea) | `research/references/frameworks.md:51-58`; `idea-refine/frameworks.md:53-65`, loaded via `brainstorming/references/exploration.md:15-17` | One core framework reference; both point to it |
| 10 | domain-modeling · teach | Term entries (canonical term, avoided aliases, tight IS-definitions, grouping) and record format (sequential numbering, short record, supersede, never delete) | `domain-modeling/CONTEXT-FORMAT.md:27-30`, `ADR-FORMAT.md:3-15,27,40-42`; `teach/GLOSSARY-FORMAT.md:30-33`, `LEARNING-RECORD-FORMAT.md:3-15,27,46` | A shared core term-entry reference; each keeps its own admission rules (teach: the learner-understanding gate). Record formats: acknowledge the common subset, keep distinct content |
| 11 | model-council · perspective-council | Council method: neutral brief, isolated members, fresh synthesizer, agreement is not proof, no implementation authority | `model-council/SKILL.md`; `perspective-council/SKILL.md:15-40` | Keep both entrypoints (different triggers, stated boundary); share one council-method reference |
| 12 | harness-status · harness-scan | Running `scan.py drift` | `harness-status/SKILL.md:13-18`; `harness-scan/SKILL.md:11-14` | **harness-scan** owns drift for one harness; status reuses its results where applicable |
| 13 | codebase-design · improve-codebase-architecture | Deletion test | `codebase-design/SKILL.md:26-28`; `improve-codebase-architecture/SKILL.md:20` | **codebase-design** |
| 14 | harness-evaluate · model-council | "Call the Codex CLI directly" | `harness-evaluate/SKILL.md:36`; `model-council/SKILL.md:16-17` (points to "AGENTS.md §Running Codex", now `.repo-context/running-codex.md`) | **`.repo-context/running-codex.md`**; both point there |
| 15 | systematic-debugging · i-have-adhd | Repeated-failure intervention, with conflicting thresholds (two failed fixes vs three "still broken" turns) | `systematic-debugging/SKILL.md:44-47`; `i-have-adhd/SKILL.md:108` | **systematic-debugging** owns the retry and escalation rule; i-have-adhd shapes only how it is said |

## Stale pointer

- `show-me/SKILL.md:29` cites html-artifact's "HTML when all hold" gate, which
  `html-artifact/SKILL.md` does not have. Fix the pointer to the gate that
  exists (`html-artifact#trigger-gated`).

## Repeated policy (AGENTS.md restated in skills)

Git and commit authority (beads, resolving-merge-conflicts, harness-publish),
"ask only material choices" (planning, grilling, brainstorming) and "no
implementation authority" (councils, improve-codebase-architecture,
harness-scan) restate AGENTS.md. Prompting guide S-05 asks to audit repeated
rules: a pruning candidate, not an ownership conflict.

## Independent

- Stated boundaries: performance-optimization ↔ systematic-debugging; security ↔ review; show-me ↔ html-artifact (once the pointer is fixed); research ↔ codebase-research (`research/SKILL.md:11`).
- Pipelines: harness-scan → harness-skill-compare / harness-evaluate; triage, wayfinder, planning (intake bead, decision map, decomposition); skill-router, brainstorming and planning routing (consistent today; drift risk only).
- No shared mechanism found: agent-matrix, check-invariants, design-evolve, resolving-merge-conflicts, migrate-claude-to-codex, harness-publish, authoring-for-agents.

## Covers corrected during this audit

- `beads#recovery` narrowed to what Beads specifies (resume from the last note).
- `systematic-debugging#localized-probing` and `#regression-check` restored to the skill's actual scope ("boundary or variable", "when feasible"); new `#escalation` line.
- `show-me#html-handoff` states the stale gate.
- `brainstorming` gained `interview-method`, `exploration-lenses`, `inline-diagrams`, `html-mockup-on-request`; `research` gained `frameworks`. These mechanisms were hidden, which is why the first pass missed overlaps 6 to 9.

## Effect on the Pocock rulings

Draft ideas that target a non-owner should move to the owner when recorded:
seam ideas to test-driven-development (#1), handoff and recovery ideas split per
#2, prove-the-red and regression ideas per #4.
