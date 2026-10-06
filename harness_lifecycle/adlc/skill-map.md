# Skill map: three harnesses on the ADLC

This map places every skill from our harness, Matt Pocock's skills, and pstack
on the stages in `GUIDE.md` §1, using that section's mapping rules. Each skill
appears once, under its primary sub-stage. `harness-map.html` rates each
harness's coverage of every sub-stage. Snapshot: 2026-10-06.

**Prefixes**

| Prefix | Meaning |
|---|---|
| `ours:` | our harness |
| `mp:` | Matt Pocock |
| `ps:` | pstack skill |
| `ps-pb:` | pstack playbook (a recipe file inside poteto-mode, not a skill) |
| `ps-pr:` | pstack principle skill (a lens for decisions, not a procedure) |
| *(alias)*, *(stub)* | mapped to the target skill's sub-stage (rule 2) |

## The map

| Stage | Sub-stage | Skills |
|---|---|---|
| **0 Discovery** | Research | ours:research · ours:codebase-research · mp:research |
| | Charting | ours:model-council · ours:perspective-council · ours:wayfinder · mp:wayfinder |
| **1 Intake** | Triage | ours:triage · mp:triage · ours:cost-estimate *(stub, retired)* |
| | Clarification | ours:brainstorming · ours:grilling · mp:grilling · mp:grill-me · mp:grill-with-docs · mp:to-questionnaire · mp:loop-me (in progress) · ps-pr:experience-first · ours:idea-refine *(alias)* · ours:grill-me *(alias)* · ours:grill-with-docs *(alias)* |
| **2 Design** | Grounding | ps:how · ps:why · ps:blast-radius · ps-pb:investigation · ps-pb:runtime-forensics · ps-pb:trace-forensics · *no skill from ours or mp* |
| | Specification | ours:test-driven-development · mp:to-spec · mp:tdd · ps:tdd · ps-pr:test-behavior-not-implementation |
| | Architecture | ours:codebase-design · ours:improve-codebase-architecture · ours:design-evolve · ours:domain-modeling · ours:prototype · mp:codebase-design · mp:improve-codebase-architecture · mp:domain-modeling · mp:prototype · ps:architect · ps:arena · ps-pb:prototype · ps-pr:foundational-thinking · ps-pr:redesign-from-first-principles · ps-pr:exhaust-the-design-space · ps-pr:model-the-domain · ps-pr:boundary-discipline · ps-pr:type-system-discipline · ps-pr:make-operations-idempotent |
| | Decomposition | ours:planning · mp:to-tickets · ps:figure-it-out · ps-pb:multi-phase-plan · ps-pr:sequence-verifiable-units · ps-pr:outcome-oriented-execution · ps-pr:separate-before-serializing-shared-state |
| **3 Building** | Implementation | ours:execution · mp:implement · mp:wizard · mp:scaffold-exercises · mp:setup-pre-commit · mp:setup-ts-deep-modules (in progress) · ps:no-comments · ps:typescript-best-practices · ps-pb:feature · ps-pb:refactoring · ps-pb:visual-parity · ps-pr:laziness-protocol · ps-pr:subtract-before-you-add · ps-pr:build-the-lever |
| | Diagnosis | ours:systematic-debugging · ours:performance-optimization · mp:diagnosing-bugs · ps-pb:bug-fix · ps-pb:perf-issue · ps-pb:hillclimb · ps-pr:fix-root-causes · ps-pr:attack-the-premise |
| **4 Verification** | Testing | ours:check-invariants · ps:benchmark-checklist · ps-pr:prove-it-works · ps-pr:explain-the-number · ours:verification-before-completion *(stub)* · *no skill from mp* |
| | Review | ours:review · ours:security · mp:code-review · ps:interrogate · ps-pr:minimize-reader-load · ours:document-review *(alias)* · ours:receiving-code-review *(alias)* |
| | Validation | *none in any harness* |
| **5 Delivery** | Integration | ours:resolving-merge-conflicts · mp:pr · ps-pb:opening-a-pr · ps-pb:babysit · ps-pb:shipping |
| | Release | ours:harness-publish |
| | Closure | ps-pb:worktree-cleanup · *ours: the session close is in `.beads/beads.md`, not a skill* |
| **6 Operations** | Monitoring | *none in any harness* |
| | Response | *none in any harness* |
| | Maintenance | mp:migrate-to-shoehorn · ps-pr:migrate-callers-then-delete-legacy-apis |
| **7 Improvement** | Retrospective | mp:retro · ps:reflect |
| | Codification | ours:authoring-for-agents · ours:harness-status · ours:harness-scan · ours:harness-evaluate · ours:harness-skill-compare · ours:migrate-claude-to-codex · mp:writing-for-agents · mp:setup-matt-pocock-skills · ps:correct · ps:automate-me · ps:setup-pstack · ps:create-verification-skill · ps:maintain-verification-skill · ps-pb:authoring-a-skill · ps-pr:encode-lessons-in-structure |
| | Evaluation | ps-pb:eval · *no skill from ours or mp* |
| **X Crosscutting concerns** | Orchestration | ours:skill-router · ours:run-phases · ours:phase-execution · ours:agent-matrix · mp:ask-matt · mp:implement-spec · ps:poteto-mode · ps:swarm · ps-pb:autonomous-run · ps-pb:autopilot-full · ps-pb:autopilot-stack · ps-pb:orchestrate · ps-pr:never-block-on-the-human |
| | Continuity | ours:beads · mp:handoff · mp:claude-handoff (in progress) · ps:recall · ps:show-me-your-work · ps-pb:session-pickup · ps-pb:pause-safely · ps-pr:guard-the-context-window |
| | Governance | mp:git-guardrails-claude-code · *ours: hooks and rules, not skills* |
| | Communication | ours:i-have-adhd · ours:show-me · ours:html-artifact · mp:wait-what · mp:writing-fragments · mp:writing-shape · mp:writing-beats (in progress) · ps:unslop · ps:technical-writing · ps:bro |
| **U Utilities** | Tooling | ps:make-bot-ui |
| | Tutoring | ours:teach · mp:teach · ps:teach · ours:teach-session *(alias)* |

## Placement notes

1. **Routers are Orchestration.** skill-router, ask-matt and poteto-mode route to other skills, so they are not Triage.
2. **Session resumption is Continuity.** This covers recall, session-pickup, pause-safely and handoff.
3. **Skills that author verification skills are Codification.** ps:create-verification-skill and ps:maintain-verification-skill write agent configuration (rule 7), so they are not Testing.
4. **ps:swarm is Orchestration.** It fans work out to parallel workers. ps:interrogate is the reviewer.
5. **ours:harness-publish is Release.** It versions, builds and publishes the plugin. It is the only Release skill in the three harnesses.
6. **Spans, recorded as secondary tags:**
   - brainstorming also writes the spec (secondary: Specification).
   - prototype also serves Discovery (secondary: Research).
   - test-driven-development also runs during Implementation.
   - security is a lens tag that also applies at Architecture.
   - poteto-mode routes to every stage.

## Gaps

- **Not covered by any harness:** Validation, Monitoring and Response.
- **Release:** only ours:harness-publish, and only for our plugin. It has no ramp and no rehearsed rollback.
- **Covered by pstack alone:** Grounding and Evaluation.
- **Not covered by pstack:** Discovery.
- **Not covered by Pocock:** Testing.
