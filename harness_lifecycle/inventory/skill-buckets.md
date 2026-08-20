# Skill Buckets

A routing taxonomy over the 84 skills in `skill.csv` (agent-skills 24,
mattpocock_skills 35, superpowers 14, humanlayer_skills 5,
The-Claude-Protocol 4, diagram-design 1, html-artifacts 1). Every skill has exactly one **primary**
bucket; **also** lists buckets where a reader would reasonably expect to find it.

Machine-readable form: `skill-buckets.csv`.

## The rules that decide placement

- **Primary = the outcome that caused the invocation**, never the mechanism used
  to reach it. `security-and-hardening` changes code, so it is Implementation, not
  a "security" bucket. `subagent-driven-development` implements a plan, so it is
  Implementation, not Orchestration — the subagents are how, not why.
- **Buckets 10–14 are not lifecycle stages.** They are about the agent, the repo's
  tooling, or the human. The corpus is heterogeneous along exactly those lines;
  forcing them onto a build-lifecycle spine is the main failure mode here.
- **Same bucket does not mean redundant.** `capability_family` +
  `family_relation` answer the redundancy question — see the last section.
- **Upstream's own staging areas are excluded.** mattpocock ships `in-progress/`
  and `misc/` directories; those are drafts and one-offs its author has not
  promoted, so they are not adoption candidates. All 10 carry
  `adoption_scope=out-of-scope` in the CSV and are skipped by the comparison
  rosters. They stay listed below — this file is the inventory of what upstream
  ships, not of what we consider. (`deprecated/` holds a README and no skills.)

**Excluded (10):** `loop-me` (1), `migrate-to-shoehorn` (4), `claude-handoff` (10),
`git-guardrails-claude-code` · `setup-pre-commit` · `setup-ts-deep-modules` (12),
`scaffold-exercises` · `writing-beats` · `writing-fragments` · `writing-shape` (14).
humanlayer's `narrow-react-prop-types` and The-Claude-Protocol's
`react-best-practices` are likewise `out-of-scope` (React-only; no UI work in
this harness — round-002 ruling). In-scope corpus is therefore **72 of 84**;
the per-bucket counts below still count all 84. The-Claude-Protocol ships
`subagents-discipline` twice (root skill + `templates/` copy for adopted
repos); both rows are inventoried, one taxonomy listing below.

| # | Bucket | Primary | Also | Scope |
|---|---|---:|---:|---|
| 1 | Discovery, Requirements & Decisions | 10 | 4 | — |
| 2 | Planning & Work Management | 5 | 3 | — |
| 3 | Architecture & Modeling | 5 | 3 | — |
| 4 | Implementation & Refactoring | 11 | 5 | — |
| 5 | Testing & Runtime Validation | 4 | 2 | — |
| 6 | Debugging & Optimization | 4 | 2 | — |
| 7 | Review & Completion Assurance | 8 | 5 | — |
| 8 | Version Control & Change Integration | 4 | 1 | — |
| 9 | Release, Migration & Operations | 7 | 2 | — |
| 10 | Orchestration, Handoff & Context Continuity | 5 | 9 | — |
| 11 | Harness Routing & Agent-System Authoring | 6 | 5 | — |
| 12 | Repository Tooling & Guardrails | 4 | 2 | — |
| 13 | Engineering Research & Durable Documentation | 3 | 7 | — |
| 14 | Human Learning, Content & Conversation | 8 | 1 | out of scope (exceptions, see §14) |
| | **Total** | **84** | | |

## 1. Discovery, Requirements & Decisions (10)

Turn ambiguity, ideas, or unresolved decisions into an agreed specification or answer.

| Skill | Repo | Family | Also in |
|---|---|---|---|
| `idea-refine` | A | requirements-elicitation | — |
| `interview-me` | A | requirements-elicitation | — |
| `spec-driven-development` | A | spec-authoring | 2 |
| `grill-me` | M | grilling | — |
| `grill-with-docs` | M | grilling | 13 |
| `grilling` | M | grilling | — |
| `loop-me` | M | grilling | 11 |
| `to-questionnaire` | M | human-in-the-loop | 10, 14 |
| `to-spec` | M | spec-authoring | 2 |
| `brainstorming` | S | requirements-elicitation | — |

## 2. Planning & Work Management (5)

Turn an agreed objective into ordered work, tickets, dependencies, or issue state.

| Skill | Repo | Family | Also in |
|---|---|---|---|
| `planning-and-task-breakdown` | A | task-decomposition | — |
| `to-tickets` | M | task-decomposition | — |
| `triage` | M | issue-state-management | 7 |
| `wayfinder` | M | task-decomposition | 1 |
| `writing-plans` | S | plan-authoring | — |

## 3. Architecture & Modeling (5)

Choose system boundaries, interfaces, vocabulary, and structural design.

| Skill | Repo | Family | Also in |
|---|---|---|---|
| `api-and-interface-design` | A | interface-design | — |
| `codebase-design` | M | interface-design | — |
| `domain-modeling` | M | domain-language | 13 |
| `improve-codebase-architecture` | M | architecture-audit | 7 |
| `prototype` | M | design-validation | 1 |

## 4. Implementation & Refactoring (11)

Build, modify, simplify, harden, or mechanically migrate software.

| Skill | Repo | Family | Also in |
|---|---|---|---|
| `code-simplification` | A | refactoring | 7 |
| `frontend-ui-engineering` | A | frontend-build | — |
| `incremental-implementation` | A | increment-sizing | — |
| `security-and-hardening` | A | security-hardening | 7 |
| `source-driven-development` | A | doc-grounded-build | 13 |
| `implement` | M | plan-execution | — |
| `migrate-to-shoehorn` | M | refactoring | 5 |
| `executing-plans` | S | plan-execution | 10 |
| `subagent-driven-development` | S | plan-execution | 10 |
| `narrow-react-prop-types` | H | refactoring | — |
| `react-best-practices` | T | frontend-build | — |

## 5. Testing & Runtime Validation (4)

Create or run behavioural evidence against expected software behaviour.

| Skill | Repo | Family | Also in |
|---|---|---|---|
| `browser-testing-with-devtools` | A | runtime-inspection | 6 |
| `test-driven-development` | A | tdd | 4 |
| `tdd` | M | tdd | 4 |
| `test-driven-development` | S | tdd | 4 |

## 6. Debugging & Optimization (4)

Investigate anomalous or inadequate behaviour and remove its cause or bottleneck.

| Skill | Repo | Family | Also in |
|---|---|---|---|
| `debugging-and-error-recovery` | A | debugging | — |
| `performance-optimization` | A | performance | 4 |
| `diagnosing-bugs` | M | debugging | — |
| `systematic-debugging` | S | debugging | — |

## 7. Review & Completion Assurance (8)

Challenge existing work or claims and decide whether they are acceptable.

| Skill | Repo | Family | Also in |
|---|---|---|---|
| `code-review-and-quality` | A | code-review | — |
| `doubt-driven-development` | A | adversarial-scrutiny | 10 |
| `code-review` | M | code-review | — |
| `receiving-code-review` | S | code-review-protocol | — |
| `requesting-code-review` | S | code-review-protocol | 10 |
| `verification-before-completion` | S | completion-gate | 5 |
| `subagents-discipline` (×2: root + templates) | T | completion-gate | 4 |

## 8. Version Control & Change Integration (4)

Isolate, reconcile, version, and land changes through Git.

| Skill | Repo | Family | Also in |
|---|---|---|---|
| `git-workflow-and-versioning` | A | git-mechanics | 9 |
| `resolving-merge-conflicts` | M | git-mechanics | — |
| `finishing-a-development-branch` | S | branch-integration | 9 |
| `using-git-worktrees` | S | workspace-isolation | 10 |

## 9. Release, Migration & Operations (7)

Deploy, transition, instrument, or operationalise software and infrastructure.

| Skill | Repo | Family | Also in |
|---|---|---|---|
| `ci-cd-and-automation` | A | pipeline-automation | 12 |
| `deprecation-and-migration` | A | migration | 3 |
| `observability-and-instrumentation` | A | observability | 6 |
| `shipping-and-launch` | A | release-management | — |
| `wizard` | M | human-in-the-loop | 10 |
| `build-iterated-agentic-loop` | H | agentic-control-loop | 10, 11 |
| `design-control-loop` | H | agentic-control-loop | 10, 11, 1 |

## 10. Orchestration, Handoff & Context Continuity (5)

Distribute work or preserve context across agents, sessions, and humans.

| Skill | Repo | Family | Also in |
|---|---|---|---|
| `context-engineering` | A | context-curation | 11 |
| `claude-handoff` | M | handoff | — |
| `handoff` | M | handoff | — |
| `dispatching-parallel-agents` | S | subagent-dispatch | — |
| `create-beads-orchestration` | T | subagent-dispatch | 2, 12 |

## 11. Harness Routing & Agent-System Authoring (6)

Route among skills, or create and maintain agent-consumed instructions.

| Skill | Repo | Family | Also in |
|---|---|---|---|
| `using-agent-skills` | A | skill-routing | — |
| `ask-matt` | M | skill-routing | — |
| `writing-for-agents` | M | agent-doc-authoring | 13 |
| `using-superpowers` | S | skill-routing | — |
| `writing-skills` | S | agent-doc-authoring | 13 |
| `improve-claude-md` | H | claude-md-rewrite | — |

## 12. Repository Tooling & Guardrails (4)

Install or configure durable repository-level development constraints.

| Skill | Repo | Family | Also in |
|---|---|---|---|
| `git-guardrails-claude-code` | M | guardrail-install | 8 |
| `setup-matt-pocock-skills` | M | harness-bootstrap | 11 |
| `setup-pre-commit` | M | guardrail-install | 7 |
| `setup-ts-deep-modules` | M | guardrail-install | 3 |

## 13. Engineering Research & Durable Documentation (3)

Establish authoritative technical knowledge or preserve engineering decisions.

| Skill | Repo | Family | Also in |
|---|---|---|---|
| `documentation-and-adrs` | A | decision-records | 3 |
| `research` | M | source-research | 1 |
| `html-artifacts` | HA | visual-explanation | 14 |

## 14. Human Learning, Content & Conversation (8)

Teach people, produce non-engineering content, or repair human communication.

> **Out of scope for local-harness adoption.** These skills produce output
> consumed by people, not by the software system. They are inventoried for
> completeness; they are not adoption candidates.
>
> Exceptions: `show-me`, `diagram-design`, and `html-artifacts` (bucket 13) are
> kept **in-scope** — their output is for the human, but they are
> development-conversation and engineering-documentation aids, which is exactly
> where our `html-artifact` already lives.

| Skill | Repo | Family | Also in |
|---|---|---|---|
| `scaffold-exercises` | M | learning-content | — |
| `teach` | M | learning-content | — |
| `wait-what` | M | conversational-repair | — |
| `writing-beats` | M | prose-authoring | — |
| `writing-fragments` | M | prose-authoring | — |
| `writing-shape` | M | prose-authoring | — |
| `show-me` | H | visual-explanation | 13 |
| `diagram-design` | D | visual-explanation | 13 |

## Capability families

Bucket membership answers *what do I reach for?*. It does **not** answer *which of
these are redundant?* — `frontend-ui-engineering` and `security-and-hardening` share
a bucket and substitute for nothing. That second question is what these families are
for, and only the `substitutes` rows are genuine adopt-one-not-both decisions.

| Family | Relation | Members |
|---|---|---|
| agent-doc-authoring | **substitutes** | `writing-for-agents`[M], `writing-skills`[S] |
| agentic-control-loop | **substitutes** | `build-iterated-agentic-loop`[H], `design-control-loop`[H] |
| visual-explanation | **substitutes** | `show-me`[H], `diagram-design`[D], `html-artifacts`[HA] |
| completion-gate | **substitutes** | `verification-before-completion`[S], `subagents-discipline`[T] |
| code-review | **substitutes** | `code-review-and-quality`[A], `code-review`[M] |
| debugging | **substitutes** | `debugging-and-error-recovery`[A], `diagnosing-bugs`[M], `systematic-debugging`[S] |
| handoff | **substitutes** | `claude-handoff`[M], `handoff`[M] |
| plan-execution | **substitutes** | `executing-plans`[S], `implement`[M], `subagent-driven-development`[S] |
| requirements-elicitation | **substitutes** | `brainstorming`[S], `idea-refine`[A], `interview-me`[A] |
| skill-routing | **substitutes** | `ask-matt`[M], `using-agent-skills`[A], `using-superpowers`[S] |
| spec-authoring | **substitutes** | `spec-driven-development`[A], `to-spec`[M] |
| tdd | **substitutes** | `tdd`[M], `test-driven-development`[A], `test-driven-development`[S] |
| code-review-protocol | **complements** | `receiving-code-review`[S], `requesting-code-review`[S] |
| prose-authoring | **pipeline** | `writing-beats`[M], `writing-fragments`[M], `writing-shape`[M] |
| git-mechanics | **genus** | `git-workflow-and-versioning`[A], `resolving-merge-conflicts`[M] |
| grilling | **genus** | `grill-me`[M], `grill-with-docs`[M], `grilling`[M], `loop-me`[M] |
| guardrail-install | **genus** | `git-guardrails-claude-code`[M], `setup-pre-commit`[M], `setup-ts-deep-modules`[M] |
| human-in-the-loop | **genus** | `to-questionnaire`[M], `wizard`[M] |
| interface-design | **genus** | `api-and-interface-design`[A], `codebase-design`[M] |
| learning-content | **genus** | `scaffold-exercises`[M], `teach`[M] |
| refactoring | **genus** | `code-simplification`[A], `migrate-to-shoehorn`[M], `narrow-react-prop-types`[H] |
| task-decomposition | **genus** | `planning-and-task-breakdown`[A], `to-tickets`[M], `wayfinder`[M] |

Relations: **substitutes** = adopt one, not both · **complements** = two halves of
one protocol · **pipeline** = sequential stages · **genus** = same area, different
scope, not interchangeable. Families with a single member are omitted.

Repo key: **A** = agent-skills, **M** = mattpocock_skills, **S** = superpowers,
**H** = humanlayer_skills, **T** = The-Claude-Protocol, **D** = diagram-design,
**HA** = html-artifacts.