# Skill Consolidation Council Report

## Executive verdict

Adopt **40 engineering skills from 63 inputs**.

This count includes nine newly named merged skills. Bucket 14’s two human-learning skills are excluded from the engineering adoption roster as directed, although both should remain available in a separate personal/productivity catalog.

Estimated merged sizes below are design targets, not measurements of files that already exist.

# Part 1 — Per bucket

## B01 — Discovery, Requirements & Decisions

### Kept

- **`product-discovery`** *(merge of `interview-me`, `idea-refine`, and `brainstorming`)* — uniquely provides one coherent progression from discovering the user’s underlying intent, through divergent alternatives and assumption testing, to an explicitly approved design. `interview-me` supplies the one-question-plus-guess protocol and 95% confidence stop; `idea-refine` supplies structured divergence/convergence; `brainstorming` supplies the hard design-approval gate (`reference_harnesses/agent-skills/skills/interview-me/SKILL.md:14-14,53-69,124-138`; `reference_harnesses/agent-skills/skills/idea-refine/SKILL.md:56-140`; `reference_harnesses/superpowers/skills/brainstorming/SKILL.md:61-132`).
- **`grilling`** — uniquely exhausts an adversarial design tree breadth-first, asking the currently unblocked frontier and forbidding action until every branch is visited and shared understanding is confirmed (`reference_harnesses/mattpocock_skills/skills/productivity/grilling/SKILL.md:8-22`). It is only 22 lines and is reused by triage, wayfinding, and architecture work.
- **`to-questionnaire`** — uniquely converts knowledge held by an absent third party into a recipient-specific asynchronous questionnaire, interviewing the user about the recipient and information gap rather than the subject itself (`reference_harnesses/mattpocock_skills/skills/productivity/to-questionnaire/SKILL.md:7-53`).
- **`to-spec`** *(absorbing `spec-driven-development`)* — uniquely supports a no-more-interview transition from settled discussion into a tracker-published specification, while the merge adds explicit constraints, acceptance criteria, project commands, and specification quality gates (`reference_harnesses/mattpocock_skills/skills/engineering/to-spec/SKILL.md:7-19,21-75`; `reference_harnesses/agent-skills/skills/spec-driven-development/SKILL.md:22-169`).

### Dropped

- **`grill-me`** — seven-line invocation wrapper with no method of its own; fold “stateless grilling” into `grilling` (`reference_harnesses/mattpocock_skills/skills/productivity/grill-me/SKILL.md:1-7`).
- **`grill-with-docs`** — seven-line composition wrapper; fold its domain-documenting mode into `grilling`, calling the retained `domain-modeling` skill when durable vocabulary or ADRs are needed (`reference_harnesses/mattpocock_skills/skills/engineering/grill-with-docs/SKILL.md:1-7`).
- **`interview-me`**, **`idea-refine`**, **`brainstorming`** — replaced by `product-discovery`; their three distinct stages survive.
- **`spec-driven-development`** — absorbed by `to-spec`; its downstream PLAN/TASKS/IMPLEMENT stages belong to B02 and B04 rather than a second end-to-end workflow (`reference_harnesses/agent-skills/skills/spec-driven-development/SKILL.md:27-27`).

### Merges

1. **`interview-me` + `idea-refine` + `brainstorming` → `product-discovery`**
   - Unique inputs: latent-intent extraction; 5–8-way divergence and assumption audit; approach comparison and approval-gated design.
   - Merged content: conditional modes—intent discovery when the goal is unclear, ideation when the goal is known but the approach is not, then design approval.
   - Conflict resolution: one-question interviewing and multi-option divergence are sequential stages, not competing rules.
   - Cost: remove repeated motivational prose, examples, and duplicate rationalization tables. Replace the large browser-server visual-companion bundle with an optional handoff to `prototype`.
   - Result: approximately 240–280 main lines plus at most two selectively loaded references; one coherent discovery skill.

2. **`spec-driven-development` + `to-spec` → `to-spec`**
   - Unique inputs: robust specification structure versus rapid synthesis and tracker publication.
   - Merged content: a fast path for already-settled conversation and a quality-gated path when requirements need formalization.
   - Conflict resolution: `to-spec`’s “no interview” rule applies only to the fast path; unclear intent routes back to `product-discovery`.
   - Cost: remove duplicated planning and implementation procedures.
   - Result: approximately 140–170 lines; coherent because both paths produce the same artifact.

3. **`grill-me` + `grill-with-docs` → modes of `grilling`**
   - Preserve stateless and domain-documenting entry modes without separate installed skills.
   - Result: roughly 35–45 lines plus a reference to `domain-modeling`.

**Verdict: 9 in → 4 out.**

---

## B02 — Planning & Work Management

### Kept

- **`triage`** — uniquely moves externally supplied issues and PRs through a verified state machine, including reproduction, duplicate/prior-rejection checks, information requests, and agent-ready briefs (`reference_harnesses/mattpocock_skills/skills/engineering/triage/SKILL.md:9-85,88-112`). It depends on a configured tracker and, conditionally, `grilling` and `domain-modeling`.
- **`planning-and-ticketing`** *(merge of `writing-plans`, `planning-and-task-breakdown`, and `to-tickets`)* — uniquely turns approved requirements into ordered, verifiable vertical work units and can emit either an executable plan or tracker-native tickets with blocking edges.
- **`wayfinder`** — uniquely maps a multi-session effort whose route is not yet knowable, tracking decision tickets, fog, claims, and the live unblocked frontier rather than pretending uncertain decisions are implementation tasks (`reference_harnesses/mattpocock_skills/skills/engineering/wayfinder/SKILL.md:55-115,118-128`).

### Dropped

- **`writing-plans`** — its exact paths, commands, code sketches, tests, and small-step execution discipline move into `planning-and-ticketing` (`reference_harnesses/superpowers/skills/writing-plans/SKILL.md:10-61,103-168`).
- **`planning-and-task-breakdown`** — its dependency graph, vertical slicing, risk ordering, checkpoints, and parallelization annotations move into the merge (`reference_harnesses/agent-skills/skills/planning-and-task-breakdown/SKILL.md:22-148,195-230`).
- **`to-tickets`** — its tracer-bullet tickets, blocking edges, expand/contract handling, and tracker publication become the ticket-output mode (`reference_harnesses/mattpocock_skills/skills/engineering/to-tickets/SKILL.md:7-67,69-105`).

### Merges

**The three plan-authoring/decomposition skills → `planning-and-ticketing`**

- Unique inputs:
  - `writing-plans`: exact implementation instructions and verification commands.
  - `planning-and-task-breakdown`: dependency-aware, risk-first vertical decomposition.
  - `to-tickets`: persistent tracker publication and native blocking relationships.
- Merged content: one decomposition engine with `plan`, `tickets`, or `both` as output targets.
- Conflict resolution: rigid 2–5-minute steps are not universal. Prefer independently verifiable vertical outcomes; add command-level precision where the implementation is deterministic.
- Cost: remove framework-specific examples, repeated plan templates, and duplicate handoff prose.
- Result: approximately 230–280 lines plus tracker adapters from B12. This remains one coherent skill because the planning model is shared; only persistence format changes.

**Verdict: 5 in → 3 out.**

---

## B03 — Architecture & Modeling

### Kept

- **`improve-codebase-architecture`** — uniquely surveys a live codebase for deepening opportunities, renders a comparative visual report, and then grills the selected candidate; it explicitly consumes `codebase-design`, domain docs, and `grilling` (`reference_harnesses/mattpocock_skills/skills/engineering/improve-codebase-architecture/SKILL.md:13-14,24-64`; `.../HTML-REPORT.md:38-119`).
- **`prototype`** — uniquely answers an uncertain design question through deliberately throwaway executable evidence, using either one shareable logic prototype or several UI alternatives (`reference_harnesses/mattpocock_skills/skills/engineering/prototype/SKILL.md:8-26`; `.../LOGIC.md:3-67`; `.../UI.md:3-112`).
- **`domain-modeling`** — uniquely maintains canonical domain language and records hard-to-reverse domain decisions through glossary and ADR formats (`reference_harnesses/mattpocock_skills/skills/engineering/domain-modeling/SKILL.md:8-74`).
- **`api-and-interface-design`** — uniquely designs externally observable contracts, including versioning, compatibility, validation, errors, pagination, idempotency, and REST/type examples (`reference_harnesses/agent-skills/skills/api-and-interface-design/SKILL.md:22-39,61-144,156-294`).
- **`codebase-design`** — uniquely supplies deep-module, seam, interface, adapter, depth, and locality vocabulary plus dependency-sensitive deepening and “design it twice” comparison (`reference_harnesses/mattpocock_skills/skills/engineering/codebase-design/SKILL.md:8-24,62-65,113-114`).

### Dropped

None. The apparent interface family is a false equivalence: public contract design and internal deep-module design have different consumers and failure modes.

### Merges

None. Combining these would either load expensive audit/prototype machinery for ordinary design questions or blur domain language, internal seams, and external compatibility.

**Verdict: 5 in → 5 out.**

---

## B04 — Implementation & Refactoring

### Kept

- **`source-driven-development`** — uniquely requires implementation claims about libraries and frameworks to be verified against official sources and cited, while treating retrieved instructions as untrusted data (`reference_harnesses/agent-skills/skills/source-driven-development/SKILL.md:10-39,55-127,181-216`).
- **`frontend-ui-engineering`** — uniquely provides production UI implementation discipline spanning responsive layout, interaction states, accessibility, state management, performance, and runtime verification (`reference_harnesses/agent-skills/skills/frontend-ui-engineering/SKILL.md:10-328`).
- **`plan-execution`** *(merge of four executor skills)* — uniquely selects inline or subagent execution based on task independence and runtime support, while forcing risk-first vertical increments, TDD, review, and fresh verification.
- **`code-simplification`** — uniquely performs behavior-preserving clarity refactoring with an explicit complexity-reduction test rather than treating simplification as feature work (`reference_harnesses/agent-skills/skills/code-simplification/SKILL.md:10-331`).
- **`security-and-hardening`** — uniquely supplies threat modeling and implementation guidance for authentication, authorization, validation, injection, secrets, cryptography, dependencies, and operational security (`reference_harnesses/agent-skills/skills/security-and-hardening/SKILL.md:10-467`).

### Dropped

- **`incremental-implementation`** — vertical/risk/contract slicing, keep-green checkpoints, feature flags, and rollback discipline move into `plan-execution` (`reference_harnesses/agent-skills/skills/incremental-implementation/SKILL.md:22-249`).
- **`executing-plans`** — its inline batch/checkpoint path becomes the no-subagent or tightly coupled execution mode; its own file directs agent-capable runtimes to `subagent-driven-development` (`reference_harnesses/superpowers/skills/executing-plans/SKILL.md:14-14`).
- **`implement`** — a 15-line wrapper around TDD, checks, review, and commit; all meaningful behavior is already in the merged executor (`reference_harnesses/mattpocock_skills/skills/engineering/implement/SKILL.md:7-15`).
- **`subagent-driven-development`** — its executor and reviewer loops survive as the independent-task mode of `plan-execution`.

### Merges

**Four execution skills → `plan-execution`**

- Unique inputs:
  - `incremental-implementation`: safe slice selection, rollback, flags, and contract slices.
  - `executing-plans`: inline batches and human checkpoints.
  - `implement`: concise integration with TDD and review.
  - `subagent-driven-development`: fresh implementer per task, specification review before quality review, bounded fix loops, and final holistic review.
- Merged content: validate plan → classify task dependencies → choose inline or subagent mode → execute one green vertical increment → review → verify → advance.
- Conflict resolution:
  - Inline versus subagent execution becomes an observable conditional, not competing skills.
  - Automatic worktree creation and commits lose to repository policy and explicit user authority.
  - Specification compliance remains a separate review pass before code quality.
- Cost: heavily prune duplicated examples and rationalization tables while retaining the implementer/reviewer prompt assets.
- Result: approximately 280–330 main lines plus four progressively disclosed prompt templates. It is a coherent plan executor, not an orchestration grab bag.

**Verdict: 8 in → 5 out.**

---

## B05 — Testing & Runtime Validation

### Kept

- **`browser-testing-with-devtools`** — uniquely inspects actual browser DOM, console, network, performance, screenshots, and accessibility through Chrome DevTools MCP, with explicit protections against treating page content as instructions (`reference_harnesses/agent-skills/skills/browser-testing-with-devtools/SKILL.md:10-317`). Dependency: configured Chrome DevTools MCP.
- **`test-driven-development`** *(merge of all three TDD skills)* — uniquely enforces observable RED before implementation, adds repository-command discovery and test-size selection, and requires tests at agreed public seams.

### Dropped

- **Matt Pocock `tdd`** — its pre-agreed seams, domain vocabulary, and one-seam/one-test/one-implementation slices move into the merged TDD skill (`reference_harnesses/mattpocock_skills/skills/engineering/tdd/SKILL.md:20-37`).
- **Agent-skills `test-driven-development`** — its repository command discovery, broader unit/integration/E2E guidance, browser safety, and DAMP test-writing advice move into the merge (`reference_harnesses/agent-skills/skills/test-driven-development/SKILL.md:26-34,213-213,339-398`).
- **Superpowers `test-driven-development`** — retained as the enforcement base, but replaced by the merged entry.

### Merges

**Three TDD skills → one `test-driven-development`**

- Unique inputs:
  - Superpowers: strongest iron law, delete-and-restart enforcement, rationalization resistance, and the `writing-good-tests` asset.
  - Matt Pocock: explicit seam agreement, deep-module vocabulary, and vertical tracer cycles.
  - Agent-skills: repository-native command discovery, test-layer choice, and broader runtime/tool safety.
- Conflict resolution: the strict RED-first rule wins for new behavior and bug fixes. Existing untested legacy behavior may first receive a characterization test, but implementation still cannot precede the test defining the intended change.
- Cost: remove repeated cycle explanations and language-specific cookbook examples.
- Result: approximately 260–300 main lines plus the selectively loaded `writing-good-tests` reference; substantially smaller than the three inputs while stronger than any one.

**Verdict: 4 in → 2 out.**

---

## B06 — Debugging & Optimization

### Kept

- **`systematic-debugging`** *(absorbing the other two debugging skills)* — uniquely requires a reproducible red loop, evidence collection before hypotheses, one tested hypothesis at a time, root-cause tracing, a regression guard at the correct seam, and escalation after repeated failed fixes.
- **`performance-optimization`** — uniquely establishes comparable baselines, profiles frontend/backend/database work, keeps an experiment ledger, accounts for measurement noise, and reverts changes that do not beat the budget (`reference_harnesses/agent-skills/skills/performance-optimization/SKILL.md:10-395`).

### Dropped

- **`debugging-and-error-recovery`** — its reproduce/localize/reduce/fix/guard outline, safe instrumentation, fallback guidance, and untrusted-error-output rule move into `systematic-debugging`.
- **`diagnosing-bugs`** — its unusually strong “already red, fast, deterministic command before theorizing” gate, ranked hypothesis shortlist, tagged probes, redaction rules, correct-seam regression test, and architecture handoff move into the merge (`reference_harnesses/mattpocock_skills/skills/engineering/diagnosing-bugs/SKILL.md:12-66,116-140`).

### Merges

**Three debugging skills → `systematic-debugging`**

- Unique inputs:
  - Superpowers: boundary instrumentation, backwards root-cause tracing, condition-based waiting, pollution isolation, and the three-failed-fixes architecture breaker.
  - Matt Pocock: executable red-loop gate, ranked hypotheses, tagged/removed probes, and correct-seam test rule.
  - Agent-skills: concise general recovery workflow and safety handling for external error material.
- Conflict resolution: first form a short ranked hypothesis set, then test exactly one hypothesis at a time. That preserves Matt’s prioritization without violating Superpowers’ single-variable discipline.
- Cost: retain only root-cause tracing, condition-based waiting, and test-pollution tools as assets; remove duplicate pressure-test history and generic examples.
- Result: approximately 270–310 main lines plus three selective references. Performance stays separate because profiling and optimization experiments begin after correctness diagnosis, not inside it.

**Verdict: 4 in → 2 out.**

---

## B07 — Review & Completion Assurance

### Kept

- **`doubt-driven-development`** — uniquely reviews non-trivial decisions while they are still being made, passing only artifact and contract to a fresh adversarial context, reconciling rather than rubber-stamping findings, and bounding the loop at three cycles (`reference_harnesses/agent-skills/skills/doubt-driven-development/SKILL.md:10-12,49-110,168-191`). It is not a final PR review.
- **`code-review`** *(merge of the four review-generation/reception skills)* — uniquely covers the full review lifecycle: dispatching fresh-context review, keeping standards and specification axes distinct, conducting multi-axis technical review, and skeptically receiving and applying feedback.
- **`verification-before-completion`** — uniquely gates every completion claim on a fresh proving command, full output, exit status, and requirement-by-requirement evidence (`reference_harnesses/superpowers/skills/verification-before-completion/SKILL.md:14-48,74-120`).

### Dropped

- **Matt Pocock `code-review`** — its fixed-point resolution and parallel Standards/Spec axes move into merged `code-review` (`reference_harnesses/mattpocock_skills/skills/engineering/code-review/SKILL.md:17-78`).
- **`code-review-and-quality`** — retained as the broad technical-review base but replaced by the merged entry; its five axes, severity, structural remedies, dependency review, and verification story survive (`reference_harnesses/agent-skills/skills/code-review-and-quality/SKILL.md:22-101,177-203,279-300`).
- **`requesting-code-review`** — fresh-context dispatch, base/head range, and structured reviewer prompt become the request mode (`reference_harnesses/superpowers/skills/requesting-code-review/SKILL.md:24-46`; `.../code-reviewer.md:23-125`).
- **`receiving-code-review`** — technical verification, clarification-before-batching, pushback, per-item testing, and inline-thread replies become the receive mode (`reference_harnesses/superpowers/skills/receiving-code-review/SKILL.md:14-25,40-110,203-205`).

### Merges

**Four review-protocol skills → `code-review`**

- Unique inputs: five-axis breadth; separate Standards/Spec reports; isolated reviewer dispatch; skeptical feedback reception.
- Merged content: `request`, `conduct`, and `receive` modes sharing a severity model and evidence contract.
- Conflict resolution:
  - Preserve Standards and Spec as independent top-level axes; rank findings by severity only within each axis.
  - Balanced strengths belong to ordinary code review. `doubt-driven-development` retains its separate issues-only adversarial framing.
- Cost: remove duplicated checklists, generic examples, and overlapping review-quality prose.
- Result: approximately 300–340 main lines plus one reviewer prompt reference; a coherent review lifecycle.

**Verdict: 6 in → 3 out.**

---

## B08 — Version Control & Change Integration

### Kept

- **`git-workflow-and-versioning`** *(absorbing conflict resolution)* — uniquely covers atomic commits, concern separation, branching, pre-commit hygiene, release tags, semantic versions, and human-facing changelogs (`reference_harnesses/agent-skills/skills/git-workflow-and-versioning/SKILL.md:34-119,211-311`).
- **`using-git-worktrees`** — uniquely detects existing harness isolation and submodules, prefers native workspace tools, verifies local worktree directories are ignored, and establishes a tested baseline (`reference_harnesses/superpowers/skills/using-git-worktrees/SKILL.md:16-100,102-167`). Keeping it separate avoids loading 167 specialized lines on every commit.
- **`finishing-a-development-branch`** — uniquely presents the user with integration choices after fresh tests, distinguishes normal/named/detached workspaces, and uses provenance-aware cleanup plus explicit typed confirmation before discard (`reference_harnesses/superpowers/skills/finishing-a-development-branch/SKILL.md:14-82,132-178`).

### Dropped

- **`resolving-merge-conflicts`** — its source-intent reconstruction, per-hunk reconciliation, and post-merge checks fit as a compact conflict section in `git-workflow-and-versioning` (`reference_harnesses/mattpocock_skills/skills/engineering/resolving-merge-conflicts/SKILL.md:6-14`).

### Merges

**`resolving-merge-conflicts` → `git-workflow-and-versioning`**

- Preserve intent tracing, explicit trade-offs, verification, and continuation of merge/rebase.
- Reject its absolute “always resolve; never abort” rule: aborting can be the safest outcome when the merge was accidental or the intended base was wrong.
- Result: approximately 370 lines, only about 15 lines beyond the base. Coherent because conflict handling is a Git mechanic.
- Worktree creation and branch finishing remain separate due their destructive-action and selective-context profiles.

**Verdict: 4 in → 3 out.**

---

## B09 — Release, Migration & Operations

### Kept

- **`wizard`** — uniquely generates a staged human-operated Bash procedure for dashboard clicks, secrets, credentials, migrations, or cutovers that the agent cannot perform; its template supplies URL opening, secret input, idempotent environment updates, confirmations, and summaries (`reference_harnesses/mattpocock_skills/skills/engineering/wizard/SKILL.md:8-43`; `.../template.sh:31-204`).
- **`deprecation-and-migration`** — uniquely manages replacement readiness, consumer migration, advisory versus compulsory deprecation, usage-proven removal, strangler/adapters, and expand–migrate–contract database changes (`reference_harnesses/agent-skills/skills/deprecation-and-migration/SKILL.md:37-118,120-190,231-247`).
- **`observability-and-instrumentation`** — uniquely derives telemetry from operational questions and implements structured logs, bounded-cardinality RED/USE metrics, distributed traces, symptom-based alerts, and telemetry self-tests (`reference_harnesses/agent-skills/skills/observability-and-instrumentation/SKILL.md:25-50,52-164,190-203`).
- **`ci-cd-and-automation`** — uniquely encodes automated merge/deployment gates, CI services and artifacts, environment separation, branch protections, and pipeline optimization (`reference_harnesses/agent-skills/skills/ci-cd-and-automation/SKILL.md:24-54,56-191,271-358`).
- **`shipping-and-launch`** — uniquely conducts a particular launch: preflight, staged rollout, advance/hold/rollback thresholds, first-hour observation, and rollback readiness (`reference_harnesses/agent-skills/skills/shipping-and-launch/SKILL.md:20-76,94-160,225-265`).

### Dropped

None. CI/CD builds the recurring delivery mechanism; shipping operates one release; observability creates their signals; migration changes live state; wizard transfers irreducible steps to a human.

### Merges

None. Their shared words—rollout, rollback, metrics, secrets—are interfaces between operational stages, not evidence of duplicate jobs.

**Verdict: 5 in → 5 out.**

---

## B10 — Orchestration, Handoff & Context Continuity

### Kept

- **`context-engineering`** — uniquely curates persistent rules, task-specific specs/source, evidence, trust levels, and context size during a live session (`reference_harnesses/agent-skills/skills/context-engineering/SKILL.md:20-119,121-178,192-262`).
- **`handoff`** — uniquely creates a portable, redacted continuation artifact that references canonical specs, plans, commits, and diffs rather than duplicating them (`reference_harnesses/mattpocock_skills/skills/productivity/handoff/SKILL.md:8-16`).
- **`dispatching-parallel-agents`** — uniquely determines whether work domains are genuinely independent, crafts bounded self-contained briefs, dispatches concurrently, and reintegrates with conflict checks and a full-suite verification (`reference_harnesses/superpowers/skills/dispatching-parallel-agents/SKILL.md:16-46,47-127,161-167`).

### Dropped

None. These respectively manage live attention, cross-session portability, and concurrent isolated execution.

### Merges

None. Folding handoff into context engineering would hide a user-invoked portability operation inside a frequently triggered context reference; folding dispatch into either would conflate information selection with work ownership.

**Verdict: 3 in → 3 out.**

---

## B11 — Harness Routing & Agent-System Authoring

### Kept

- **`writing-agent-instructions`** *(merge of `writing-for-agents` and `writing-skills`)* — uniquely combines universal instruction architecture—context pointers, information hierarchy, completion criteria, leading words, pruning—with evaluation-driven skill packaging and deployment.
- **`using-skills`** *(merge of all three routers)* — uniquely enforces pre-action skill discovery while routing both users and agents through the consolidated catalog, with phase-boundary and runtime-specific references loaded only when needed.

### Dropped

- **`writing-for-agents`** — becomes the concise universal base of `writing-agent-instructions`.
- **`writing-skills`** — its skill-specific TDD/evaluation, discovery optimization, packaging, runtime, and pressure-testing material becomes a conditional branch of the merged authoring skill.
- **`ask-matt`** — its exact catalog is invalid after consolidation, but its human-invoked flow map and ordered phase-boundary tree move into `using-skills` (`reference_harnesses/mattpocock_skills/skills/engineering/ask-matt/SKILL.md:11-32,61-90`; `.../PHASE-BOUNDARIES.md:17-55`).
- **`using-agent-skills`** — its phase router and durable operating behaviors move into `using-skills` (`reference_harnesses/agent-skills/skills/using-agent-skills/SKILL.md:12-42,44-140`).
- **`using-superpowers`** — its mandatory complete-read rule, skill priority, user-precedence rule, and platform references move into `using-skills` (`reference_harnesses/superpowers/skills/using-superpowers/SKILL.md:18-31,52-62`).

### Merges

1. **Two authoring skills → `writing-agent-instructions`**
   - `writing-for-agents` uniquely explains the two loads, progressive disclosure, context-pointer branches, completion criteria, leading words, no-op detection, and sediment pruning (`reference_harnesses/mattpocock_skills/skills/productivity/writing-for-agents/SKILL.md:10-80`).
   - `writing-skills` uniquely supplies evaluation-first authoring, baseline/pressure tests, failure-form selection, discovery rules, and bundled-script guidance (`reference_harnesses/superpowers/skills/writing-skills/SKILL.md:10-45,140-220,395-585`).
   - Conflict resolution: descriptions lead with firing conditions and may include only the minimum job label required by the runtime; they must not summarize enough workflow to let the body be skipped. Evaluation-first is mandatory for behavior-changing guidance; pure references use retrieval and gap evaluations rather than coercive pressure tests.
   - Cost: the current 679-line `writing-skills` body and 1,150-line copied official guide violate their own sub-500-line advice (`.../anthropic-best-practices.md:235-243,1097-1115`). Prune copied vendor prose, duplicate examples, persuasion exposition, and the Graphviz rendering utility.
   - Result: approximately 200–240 main lines plus four one-level references. Coherent because skill authoring is a conditional specialization of writing instructions for agents.

2. **Three routers → `using-skills`**
   - Unique inputs: human flow navigation and phase boundaries; phase-based automatic routing and operating posture; hard pre-action invocation plus platform mappings.
   - Conflict resolution: reject Superpowers’ “1% chance means invoke” threshold as excessive. Trigger from explicit requests or concrete description matches, then read the selected skill completely before action.
   - Regenerate the route table from the 40-skill roster; do not preserve obsolete aliases.
   - Result: under 150 main lines plus phase-boundary and per-platform references. This is one coherent catalog router.

**Verdict: 5 in → 2 out.**

---

## B12 — Repository Tooling & Guardrails

### Kept

- **`setup-engineering-skills`** *(genericized rename of `setup-matt-pocock-skills`)* — uniquely bootstraps the shared tracker, triage vocabulary, domain-document layout, and instruction-file pointers required by several retained workflow skills (`reference_harnesses/mattpocock_skills/skills/engineering/setup-matt-pocock-skills/SKILL.md:9-15,19-112`).

### Dropped

- The Matt-specific name is dropped, not the capability.

### Merges

No same-bucket merge is possible. During adoption, add a Beads/native-tracker adapter alongside the existing GitHub, GitLab, and local-Markdown templates; the current setup only offers those three plus freeform “other” (`.../SKILL.md:38-49`; `.../issue-tracker-github.md:28-45`; `.../issue-tracker-gitlab.md:29-46`; `.../issue-tracker-local.md:13-30`).

**Verdict: 1 in → 1 out.**

---

## B13 — Engineering Research & Durable Documentation

### Kept

- **`documentation-and-adrs`** — uniquely maintains durable decision rationale, ADR lifecycle, public API documentation, README structure, changelogs, and agent-facing gotchas while matching existing repository conventions first (`reference_harnesses/agent-skills/skills/documentation-and-adrs/SKILL.md:23-101,102-258,279-288`).
- **`research`** — uniquely delegates primary-source reading to a background agent and leaves a cited Markdown evidence artifact in the repository (`reference_harnesses/mattpocock_skills/skills/engineering/research/SKILL.md:6-12`).

### Dropped

None. One gathers evidence; the other records project decisions and operating knowledge.

### Merges

None. Combining them would force background research for routine ADR/comment work and would blur evidence collection with decision ownership.

**Verdict: 2 in → 2 out.**

---

## B14 — Human Learning, Content & Conversation

### Kept

None in the adopted engineering roster.

If a separate human/productivity catalog is maintained, keep both skills there:

- **`wait-what`** is a seven-line explicit conversational-repair command using missing context, Simplified Technical English, and the project’s ubiquitous language (`reference_harnesses/mattpocock_skills/skills/productivity/wait-what/SKILL.md:1-7`).
- **`teach`** is a large multi-session pedagogy workspace with missions, trusted resources, learning records, HTML lessons, retrieval practice, spacing, interleaving, communities, and reusable teaching components—not an engineering documentation skill (`reference_harnesses/mattpocock_skills/skills/productivity/teach/SKILL.md:8-46,47-140`; `.../LEARNING-RECORD-FORMAT.md:1-46`).

### Dropped

- **`wait-what`** and **`teach`** are excluded solely because their outputs are consumed by people and the brief marks them outside engineering adoption scope, not because they duplicate one another.

### Merges

None. A one-turn repair command and a persistent learning-management system are unrelated.

**Verdict: 2 in → 0 adopted; 2 retained outside scope.**

# Part 2 — Cross-bucket check

## Required sub-skills

No retained capability is left with an intentionally missing required sub-skill, but several references must be renamed:

- `triage`, `wayfinder`, and `improve-codebase-architecture` continue to depend on retained `grilling`; the architecture skill also retains `codebase-design` and `domain-modeling`.
- `to-spec`, `triage`, `wayfinder`, and `planning-and-ticketing` need the genericized `setup-engineering-skills` tracker contract.
- `plan-execution` retains dependencies on merged `test-driven-development`, merged `code-review`, `using-git-worktrees`, and `finishing-a-development-branch`.
- `writing-agent-instructions` retains `test-driven-development` for behavior-changing skill guidance and `dispatching-parallel-agents` for evaluation runs.
- `doubt-driven-development` currently names dropped identifiers such as `code-review-and-quality` and `debugging-and-error-recovery`; rewrite them to `code-review` and `systematic-debugging` (`reference_harnesses/agent-skills/skills/doubt-driven-development/SKILL.md:223-229`).
- `observability-and-instrumentation` and CI guidance similarly need old debugging names rewritten (`reference_harnesses/agent-skills/skills/observability-and-instrumentation/SKILL.md:20-23`; `reference_harnesses/agent-skills/skills/ci-cd-and-automation/SKILL.md:184-191`).
- The merged `using-skills` router and B12 templates must be generated from the final roster; retaining their current route tables would reintroduce dead names.

## Same skill kept and dropped across buckets

None. Every input row belongs to one primary bucket. The duplicate label `test-driven-development` occurs twice within B05 and resolves into one merged entry; it is not a cross-bucket inconsistency.

## Deliberate cross-bucket overlaps

These overlaps are interfaces, not consolidation opportunities:

- **`product-discovery` / `grilling`**: cooperative discovery versus adversarial exhaustive scrutiny.
- **`to-spec` / `documentation-and-adrs`**: prospective behavior contract versus durable historical rationale.
- **`planning-and-ticketing` / `wayfinder`**: decomposition after the route is understood versus discovery of the route itself.
- **`source-driven-development` / `research`**: inline fact verification during implementation versus a durable background research artifact.
- **`systematic-debugging` / `performance-optimization`**: root-cause correctness diagnosis versus measured optimization experiments.
- **`code-review` / `security-and-hardening` / `performance-optimization`**: review detects which specialist analysis to invoke; it does not replace either specialist.
- **`git-workflow-and-versioning` / `using-git-worktrees` / `finishing-a-development-branch`**: routine history, selective isolation, and high-risk integration have different triggers and context costs.
- **`observability-and-instrumentation` / `shipping-and-launch`**: instrumentation creates signals; launch uses them to advance, hold, or roll back.
- **`ci-cd-and-automation` / `shipping-and-launch`**: recurring delivery machinery versus one release decision.
- **`context-engineering` / `handoff`**: live context selection versus portable cross-boundary state.
- **`writing-agent-instructions` / `documentation-and-adrs`**: agent-behavior design versus product/project documentation.

# Part 3 — Capability-loss ledger

Most dropped rows lose no capability: their distinct advantages are explicitly carried into the named merges. The actual losses are:

| Source | Capability not retained | Why acceptable | Recoverable? |
|---|---|---|---|
| `grill-me`, `grill-with-docs` | Dedicated command aliases | Stateless and document-maintaining modes survive inside `grilling`; separate seven-line wrappers add routing noise | Yes—restore aliases if usage data shows humans depend on them |
| `brainstorming` assets | Bespoke browser-server visual-companion pipeline | High dependency and context burden for an occasional interaction; visual uncertainty is better routed to retained `prototype` | Yes—reuse the original asset bundle |
| `idea-refine` assets | Separate visual ideation workspace | Same reason; structured divergence survives in `product-discovery` | Yes |
| `spec-driven-development` | One skill owning SPECIFY through IMPLEMENT | That ownership duplicated B02 planning and B04 execution and created conflicting gates | Yes, but recomposition through named skills is clearer |
| `implement` / execution inputs | Unconditional commit and worktree behavior | Repository/user authority must decide mutations; B08 supplies explicit isolation and finishing protocols | Yes through repository policy |
| Three TDD/debug/review families | Numerous framework-specific examples and repeated rationalization tables | They add tokens but not a distinct job or enforcement mechanism | Yes from source harnesses |
| `resolving-merge-conflicts` | “Always resolve; never abort” | This is an unsafe absolute, not a desirable advantage; an accidental or wrongly based merge may need aborting | The original rule can be restored, but should not be |
| `writing-skills` | Graphviz style guide and automatic SVG renderer | Diagram rendering is peripheral to instruction correctness and adds Graphviz/Node dependencies | Yes from bundled assets |
| `using-superpowers` | “Invoke at 1% possibility” enforcement threshold | It over-triggers costly workflows and conflicts with precise description-based routing | Yes, but evidence should show under-invocation first |
| `ask-matt` | Exact Matt-specific route map and aliases | The source map becomes factually wrong after consolidation | Regenerate from any future roster |
| B14 `wait-what` | Explicit conversational re-pitch command in engineering catalog | Out of adoption scope, not redundant | Yes—retain in a personal/productivity catalog |
| B14 `teach` | Multi-session pedagogy, spaced retrieval, learning records, communities, and HTML lessons | Out of engineering adoption scope | Yes—retain unchanged in a teaching catalog |

# Part 4 — Final roster

Merged names are proposed catalog entries.

| Bucket | Final skills | Count |
|---|---|---:|
| B01 Discovery, Requirements & Decisions | `product-discovery`, `grilling`, `to-questionnaire`, `to-spec` | 4 |
| B02 Planning & Work Management | `triage`, `planning-and-ticketing`, `wayfinder` | 3 |
| B03 Architecture & Modeling | `improve-codebase-architecture`, `prototype`, `domain-modeling`, `api-and-interface-design`, `codebase-design` | 5 |
| B04 Implementation & Refactoring | `source-driven-development`, `frontend-ui-engineering`, `plan-execution`, `code-simplification`, `security-and-hardening` | 5 |
| B05 Testing & Runtime Validation | `browser-testing-with-devtools`, `test-driven-development` | 2 |
| B06 Debugging & Optimization | `systematic-debugging`, `performance-optimization` | 2 |
| B07 Review & Completion Assurance | `doubt-driven-development`, `code-review`, `verification-before-completion` | 3 |
| B08 Version Control & Change Integration | `git-workflow-and-versioning`, `using-git-worktrees`, `finishing-a-development-branch` | 3 |
| B09 Release, Migration & Operations | `wizard`, `deprecation-and-migration`, `observability-and-instrumentation`, `ci-cd-and-automation`, `shipping-and-launch` | 5 |
| B10 Orchestration, Handoff & Context Continuity | `context-engineering`, `handoff`, `dispatching-parallel-agents` | 3 |
| B11 Harness Routing & Agent-System Authoring | `writing-agent-instructions`, `using-skills` | 2 |
| B12 Repository Tooling & Guardrails | `setup-engineering-skills` | 1 |
| B13 Engineering Research & Durable Documentation | `documentation-and-adrs`, `research` | 2 |
| B14 Human Learning, Content & Conversation | None adopted; `wait-what` and `teach` retained outside scope | 0 |

**Total: 63 in → 40 adopted skills.**

# Part 5 — Confidence and open questions

**Overall confidence: high on removals, medium-high on the exact merge boundaries.**

The calls I would revisit first are:

1. **B01’s three-way `product-discovery` merge.** I lean strongly toward one staged skill because the three methods form a natural intent → options → approved-design pipeline. I would split `interview-me` back out only if trigger evaluations show agents entering the full discovery process when a short underlying-intent interview would have sufficed.

2. **B04’s combined `plan-execution`.** I lean toward one executor with explicit inline/subagent modes because the source skills already route to one another. I would split the subagent mode only if its prompt assets or review loops make the main executor exceed roughly 350 lines or cause inline tasks to spawn agents unnecessarily.

3. **B07’s full review-lifecycle merge.** I lean toward one `code-review` because requesting, conducting, and receiving are stages of the same protocol. I would restore `receiving-code-review` as a separate skill if automatic trigger tests show feedback-arrival prompts do not reliably select the receive mode.

4. **B11’s router strictness.** I reject the 1% rule, but under-invocation is a real risk. Run trigger evaluations across small questions, bugs, approved plans, and high-stakes work. Evidence that required process skills are missed would justify stronger enforcement—not necessarily the original universal threshold.

5. **B12’s portability.** The retained bootstrap is necessary for several tracker-coupled skills, but its GitHub/GitLab/local assumptions do not natively model this repository’s Beads workflow. I lean toward adding a first-class Beads adapter before adoption.

All 63 `SKILL.md` files and their bundled assets were read. The review was read-only; no repository file was intentionally edited, created, or deleted.
