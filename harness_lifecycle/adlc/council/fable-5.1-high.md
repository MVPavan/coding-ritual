# Autonomous Development Lifecycle (ADLC)

## 1. Principles

1. **Intent before work.** The most expensive failure is a correct solution to the wrong problem, so intent is made explicit and checkable before any code is touched.
2. **Verification is independent of generation.** The process that produces a change shares blind spots with any check it performs on itself, so judgment must come from a separately-contexted verifier.
3. **Evidence, not assertion.** "Tests pass" is a claim. A reproducible run log with a content hash is evidence. Only evidence advances a stage.
4. **Autonomy ends where reversibility ends.** Agents may act freely on anything that can be undone cheaply. Anything irreversible or externally visible passes a gate whose strictness scales with the blast radius.
5. **Everything is bounded.** Every loop has a budget in attempts, wall time and cost. Running out of budget is a normal exit, not an error, and it routes to escalation rather than retry.
6. **State lives outside the agent.** Agent context is ephemeral and will be lost. Progress is durable only if it is journaled as artifacts that a fresh agent can resume from.
7. **Scope is a contract.** The change does what the spec says and nothing else. Unrequested changes are defects even when they are improvements.
8. **Least privilege per stage.** A stage receives only the credentials and tools it needs, so a confused or manipulated agent cannot do damage outside its stage.
9. **Trust is earned per change class, not granted globally.** Autonomy level is a function of risk class and measured track record, and it can be revoked by data.

## 2. Lifecycle diagram

```
                       ┌──────────────────────────────────────────────────────────────┐
                       │  CROSS-CUTTING (every stage)                                 │
                       │  • Budget ledger (attempts / time / cost)  • Durable journal  │
                       │  • Sandbox + least-privilege credentials   • Provenance log   │
                       │  • Stuck detection                         • Kill switch      │
                       │  • Escalation channel to humans            • Risk class tag   │
                       └──────────────────────────────────────────────────────────────┘

  request ──► [0 INTAKE] ──► [1 SPECIFY] ──► [2 INVESTIGATE] ──► [3 PLAN] ──► [4 ENCODE ACCEPTANCE]
                 │               ▲  ▲             │                 ▲  │              │
                 │ reject/       │  │ spec gap    │                 │  │              │
                 │ duplicate     │  └─────────────┘                 │  │              ▼
                 ▼               │                                  │  │      [5 IMPLEMENT] ◄──────┐
              (closed)           │        human gate G1             │  │              │             │
                                 │  (ambiguous intent / med+ risk)  │  │              ▼             │ fail
                                 │                                  │  │      [6 SELF-VERIFY] ──────┘
                                 │                                  │  │              │ pass          (≤N)
                                 │                                  │  │              ▼
                                 │                                  │  └───► [7 INDEPENDENT REVIEW] ──► fail ──┐
                                 │                                  │   replan after                           │
                                 │                                  │   N review fails        back to 5 (≤M) ◄─┘
                                 │                                  │                 │ pass
                                 │                                  │                 ▼
                                 │                                  │        [8 INTEGRATE] ── conflict/regress ──► 5
                                 │                                  │                 │
                                 │                                  │        human gate G2
                                 │                                  │     (irreversible / high risk)
                                 │                                  │                 ▼
                                 │                                  │        [9 DELIVER] ── bad signal ──► ROLLBACK ──► new INTAKE
                                 │                                  │                 │
                                 │                                  │                 ▼
                                 └──────────────────────────────────┴────── [10 OBSERVE & CLOSE] ──► learnings ──► rules/skills

  Any stage: budget exhausted or stuck ──────────────────────────────────► [ESCALATE to human] (state preserved)
```

Fast path: changes classified **trivial** at Intake skip stages 2, 3 and 7, and merge on self-verify alone. The classifier itself is the control point and is discussed under trade-offs.

## 3. Stage table

| # | Stage | Goal | Inputs | Outputs | Capabilities needed | Exit criterion | On failure |
|---|---|---|---|---|---|---|---|
| 0 | **Intake** | Decide whether and how to work on this | Raw request (text, failing alert, dependency bump, scheduled task) | Ticket with risk class (trivial / low / medium / high), duplicate check, initial budget | Request classification, duplicate detection, risk classification, budget estimation | Ticket has risk class and budget, or is closed as reject/duplicate | Unclassifiable → escalate to human with a one-paragraph summary |
| 1 | **Specify** | Turn request into a checkable contract | Ticket, requester dialogue, product/domain docs | **Change Spec**: intent, acceptance criteria, explicit non-goals, constraints, affected surfaces, rollback expectation | Ambiguity detection, acceptance-criterion writing, non-goal articulation, question formulation | Every acceptance criterion is observable by a test or measurement; no open ambiguities above a threshold. **Gate G1** if ambiguity remains or risk ≥ medium | Open ambiguity → ask the requester, blocking only this ticket. No answer within SLA → park, not guess |
| 2 | **Investigate** | Know enough about the system to plan correctly | Spec, repository, history, runtime docs, prior incidents | **Context Dossier**: affected modules, call graph, existing tests, conventions, prior related changes, hidden couplings | Codebase navigation, dependency and call-graph analysis, history archaeology, runtime probing, convention extraction | Every affected surface in the spec maps to concrete code locations; dossier lists the tests that currently cover them | Dossier reveals the spec is wrong or impossible → back to 1 with findings attached |
| 3 | **Plan** | Choose an approach and how it will be proven | Spec, dossier | **Plan**: ordered steps, declared file/module scope, verification plan, rollback plan, revised budget, alternatives considered and rejected | Decomposition, alternative generation, verification-strategy design, estimation, risk re-assessment | Plan is stepwise, each step has a check, declared scope is explicit, budget fits ticket budget | Cannot fit budget → shrink scope with requester or escalate. Risk class raised → re-enter G1 |
| 4 | **Encode acceptance** | Make intent executable before implementation | Spec, plan, dossier | New or modified tests that **fail** on current code and encode every acceptance criterion; property tests where applicable | Test authoring, property-based test design, fixture construction, reproduction of reported bugs | Each criterion maps to at least one test; all new tests fail for the expected reason on baseline | Criterion cannot be tested → spec is not checkable → back to 1 |
| 5 | **Implement** | Make the acceptance tests pass within declared scope | Plan, acceptance tests, isolated workspace | Candidate diff, build artifacts, per-iteration run logs | Code editing, refactoring, build-system operation, dependency management, migration authoring, debugging from failures | Acceptance tests and existing suite pass locally; diff touches only declared scope or justifies each exception | Attempt budget N exhausted or failure set not shrinking → back to 3 (replan). Replan budget exhausted → escalate |
| 6 | **Self-verify** | Produce evidence the change is sound | Diff, workspace | **Evidence bundle**: full test run, lint/type/static analysis, security scan, mutation score on changed lines, perf benchmark if plan requires, reproducible run hash | Test execution and interpretation, flaky-test discrimination, static analysis, mutation testing, benchmarking, security scanning | All checks green or each red item has a justified, journaled waiver; mutation score on changed lines above threshold | Red → back to 5 with the failure set. Flaky test detected → quarantine ticket opened, not ignored |
| 7 | **Independent review** | Catch what the implementer cannot see | Spec, plan, diff, evidence bundle. **Not** the implementer's reasoning trace | Review verdict with findings; conformance report (does diff match spec, and only spec?) | Spec-conformance review, adversarial review (try to break it), scope-creep detection, test-weakening detection, convention review, change-explanation writing | Zero blocking findings from a fresh-context reviewer; test files were not deleted or weakened; scope report clean | Findings → back to 5 (≤M rounds). Same finding survives two rounds → back to 3. Reviewer and implementer disagree on spec meaning → back to 1 |
| 8 | **Integrate** | Land the change on current mainline safely | Reviewed diff, mainline head | Merged change, re-run evidence on rebased code, release note, provenance record | Conflict resolution, rebasing, incremental re-verification, release-note writing | Rebased code passes stage 6 checks; merge recorded with links to spec, plan, evidence, review | Conflict needs semantic judgment → back to 5. Regression after rebase → back to 5 with the new failure |
| 9 | **Deliver** | Put the change in front of users without irreversible harm | Merged change, rollback plan, environment health baseline | Progressive rollout with health signals; rollback artifact tested before rollout | Rollout control, canary analysis, rollback execution, migration sequencing. **Gate G2** before irreversible steps | Rollout at 100% with health signals within baseline for the observation window | Signal breach → automatic rollback, then a new Intake ticket of type incident, linked to this one |
| 10 | **Observe & close** | Confirm the intent was achieved and learn | Production signals, acceptance criteria, requester | Closure record: criteria confirmed in production, deviations, cost actual vs budget, extracted learnings (new rule, test, or skill) | Metric interpretation, post-mortem writing, learning extraction into durable rules | Each acceptance criterion confirmed or explicitly marked unobservable; learnings committed | Criterion not met in production despite passing tests → new ticket; the test gap is itself a learning |

## 4. Human involvement

Humans are not a stage. They are a gate that fires on conditions, plus a few standing roles. Where a human is required, the reason is one of three: only they hold the intent, only they can own the consequence, or only they can set the rules.

**Gate G1, before Specify exits.** A human confirms the spec when ambiguity remains after the agent has asked its questions, or when risk class is medium or above. The human reviews the spec and acceptance tests, not the diff. Intent-level artifacts are short and humans actually read them. Diffs are long and humans rubber-stamp them. Agents cannot manufacture intent, so this gate cannot be automated away.

**Gate G2, before irreversible delivery.** A human approves actions that cannot be undone or whose consequences are owned by a person: destructive data migrations, deletion of user data, publishing a public API or contract, spending money above a threshold, changes to authentication, authorization, cryptography or billing, and anything touching legal or licensing obligations. Autonomy should not replace this because accountability is a human property. Someone must be answerable.

**Escalation.** Any stage that exhausts its budget or detects it is stuck hands a frozen, resumable state to a human with a summary of what was tried. Humans here decide to extend budget, change scope, or abandon. Agents must not grant themselves more budget.

**Policy authorship.** Humans define the risk-classification rules, budgets per class, which codebases and change classes are eligible for which autonomy level, and the health-signal thresholds for rollback. Agents operate inside policy, never edit it, and may only propose changes to it through the normal lifecycle.

**Calibration sampling.** A random sample of fully autonomous merges is reviewed by humans after the fact. The sample rate per change class rises when sampled defects are found and falls with a clean record. This is how trust tiers move, and it is the only mechanism by which a class graduates from gated to ungated.

Nowhere in this design does a human review a routine low-risk diff before merge. That is deliberate. Pre-merge human diff review of autonomous output does not scale and gives false assurance.

## 5. Failure, safety and recovery

**Bounding cost and time.**
- Each ticket gets a budget at Intake in three currencies: attempts per stage, wall-clock, and spend. Stage budgets nest inside the ticket budget.
- Budgets are set by risk class policy, not by the agent. The agent may request more only through escalation.
- Exhaustion is a clean exit with state preserved, never a silent retry.

**Stopping runaway loops.**
- Every implement iteration records the hash of the diff and the set of failing checks. Two consecutive iterations with an identical failure set, or a growing one, trigger exit from the loop to replan.
- Replan is itself bounded. Two replans without progress route to escalation.
- A reviewer finding that survives two rounds means the implementer does not understand it. That routes to replan, not another attempt.
- Goodhart guards: deleting a test, weakening an assertion, adding a skip marker, or widening a tolerance is flagged automatically and must be justified in the plan. The reviewer sees these flags first.

**Recovering from crashes and interruptions.**
- The journal is append-only and records every stage transition with its artifacts: spec, dossier, plan, diff as a patch against a pinned base commit, evidence bundle, review verdict.
- A workspace is a derived object: base commit plus patch. Any crash is recovered by rebuilding the workspace from the journal and resuming at the last completed stage.
- Every externally visible action carries an idempotency key, so a resume after a crash mid-action does not duplicate a merge, comment or deploy step.
- A global and per-ticket kill switch halts at the next journal boundary, leaving state consistent and resumable.

**Avoiding irreversible mistakes.**
- Every action is tagged reversible or irreversible at the capability level, not by the agent's judgment. Irreversible actions are unavailable to stages 1 through 8 entirely.
- Implementation and verification run in ephemeral sandboxes with no production credentials and allow-listed network egress.
- Credentials are short-lived and scoped per stage. The reviewer has read-only access. Only Deliver holds deploy credentials, and only after G2 where required.
- No deploy without a rollback artifact that was exercised in a pre-production environment during the same run.
- Rollouts are progressive with automatic abort on health-signal breach. The observation window is set by policy per risk class.
- Scope guard: the set of files touched is diffed against the plan's declared scope. Deviations are not blocked but are surfaced to the reviewer as the first item.
- Injection defence: all repository content, issue text and tool output is treated as data. Capabilities and permissions come only from the stage definition, never from anything the agent reads.

## 6. Capability catalogue

**Understanding**
- Codebase navigation: locate code by concept, symbol or behaviour.
- Dependency and call-graph analysis: find what a change can affect.
- History archaeology: recover why code is the way it is from past changes and discussions.
- Runtime probing: run the system and observe behaviour where reading is insufficient.
- Convention extraction: infer the project's style, patterns and idioms from examples.

**Specification**
- Request classification: type, urgency, duplicate detection.
- Risk classification: assign a class from blast radius, surface touched and reversibility.
- Ambiguity detection: find under-specified or contradictory requirements.
- Acceptance-criterion writing: express intent as observable conditions.
- Non-goal articulation: state what the change deliberately will not do.
- Question formulation: ask the minimal set of questions that resolve ambiguity.

**Planning**
- Decomposition: split a change into independently checkable steps.
- Alternative generation and comparison: produce and weigh more than one approach.
- Verification-strategy design: decide what evidence would prove each step.
- Estimation and budgeting: forecast attempts, time and cost against policy.
- Rollback planning: design the undo before the do.

**Construction**
- Code editing and refactoring: make changes that preserve behaviour outside the target.
- Build-system operation: compile, package, resolve toolchain failures.
- Dependency management: add, upgrade and audit third-party code.
- Migration authoring: write reversible data and schema changes.
- Debugging from failure output: map a failing check to a cause.

**Verification**
- Test authoring: unit, integration and property-based tests from criteria.
- Bug reproduction: turn a report into a deterministic failing test.
- Test execution and interpretation: run suites and explain failures.
- Flaky-test discrimination: distinguish nondeterminism from regression.
- Static analysis and type checking.
- Mutation testing: measure whether tests actually constrain the changed code.
- Security scanning: dependency vulnerabilities, secrets, unsafe patterns.
- Performance benchmarking with baseline comparison.

**Review**
- Spec-conformance review: does the diff do what the spec says.
- Scope-creep detection: does the diff do anything the spec does not say.
- Adversarial review: actively attempt to break the change.
- Test-weakening detection: spot deleted, skipped or loosened tests.
- Convention review: conformance to extracted project norms.
- Change explanation: write a reviewer-facing and user-facing description.

**Integration and delivery**
- Conflict resolution and rebasing.
- Incremental re-verification after rebase.
- Release-note and changelog writing.
- Rollout control: progressive exposure with staged percentages.
- Canary analysis: compare health signals against baseline.
- Rollback execution.

**Operations and meta**
- Budget accounting: track attempts, time and spend against limits.
- Journaling and checkpointing: persist resumable state at every transition.
- Stuck detection: recognise non-progress from failure-set history.
- Escalation composition: summarise state and attempts for a human.
- Provenance recording: link every merged change to spec, plan, evidence and review.
- Learning extraction: turn a closure or incident into a durable rule, test or skill.

## 7. Trade-offs and open questions

**Reviewer independence versus cost.** A fresh-context reviewer roughly doubles the cost of every non-trivial change. Worse, two instances of the same model share training-induced blind spots, so "independent" may be weaker than it looks. I am least sure here. Mitigations are a different model family for review, and routing a sample of agent-passed reviews to humans to measure the miss rate. Whether same-model review provides meaningful independence is an empirical question I cannot answer from first principles.

**Tests as the spec.** Stage 4 encodes the agent's interpretation of intent. If the interpretation is wrong, the tests pass and the work is wrong, and no downstream stage can catch it. G1 exists for this, but only fires on medium-plus risk or detected ambiguity. Undetected ambiguity on a low-risk change goes straight through. The question is how to verify the verifier without reintroducing a human on every change.

**Risk classification is the load-bearing control.** The fast path, the gates, the budgets and the credentials all key off the risk class assigned at Intake. If the classifier under-rates a change, every safeguard downstream is weakened at once. A classifier that reads request text is also exposed to manipulation by that text. I would make the classifier conservative, rule-heavy rather than judgment-heavy, and never allow a later stage to lower the class. I am not confident this is sufficient.

**Scope contract versus necessary refactoring.** Treating out-of-scope edits as defects keeps changes reviewable, but real changes often need a preparatory refactor. The design surfaces rather than blocks deviations, and expects the agent to split a refactor into its own ticket. This costs latency and may be ignored under budget pressure.

**Ceremony versus speed.** Ten stages for a typo is absurd, which is why the trivial path exists. But every path shortcut is a place where the classifier's error becomes unrecoverable. The right number of tiers is unknown and probably codebase-specific.

**Evidence depends on determinism.** "Evidence over assertion" assumes a green run means something. Flaky tests, time-dependent code and environment drift all erode that. The design quarantines flakes rather than ignoring them, but a codebase with widespread nondeterminism will stall the lifecycle rather than run it.

**Closing the loop in production.** Stage 10 assumes acceptance criteria are observable after delivery. For many changes they are not, or the signal takes weeks. In practice most tickets will close on "unobservable", which weakens the learning loop that is supposed to calibrate trust.

**Erosion of human understanding.** If the lifecycle works, humans stop reading most changes. In two years, who understands the system well enough to write a good spec, set a sane risk policy, or judge an escalation? The design has no answer beyond calibration sampling, and I suspect that is not enough.

**Concurrency.** Multiple tickets running in parallel on the same codebase will conflict at Integrate and may invalidate each other's investigations. Serialising merges handles correctness but not wasted work. Coordination between concurrent agent runs is out of scope here and is a real gap.