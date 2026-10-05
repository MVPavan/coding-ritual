# Autonomous Development Lifecycle (ADL)

The lifecycle is built around one idea: **a delivered result is a change plus the evidence that it is correct, and every part of that evidence is produced or checked by something other than the agent that wrote the change.** Most of the mechanisms below exist to keep that evidence honest and to keep the lifecycle within bounds.

---

## 1. Principles

| # | Principle | Reasoning |
|---|---|---|
| P1 | **Intent is the contract.** Before any code is written, the change has a written spec with acceptance criteria a machine can check wherever possible. | Agents optimise for whatever is measurable. A requirement nobody wrote down will be broken without anyone noticing. |
| P2 | **Evidence over assertion.** A claim like "fixed" or "tests pass" only counts if an independent process produced an artifact that proves it. | Language-model self-reports are not reliable. Logs, exit codes and reproducible runs are. |
| P3 | **Separate the author from the judge.** The agent that writes the change cannot be the only one that checks it. The checks are fixed before implementation starts and the author cannot edit them. | Otherwise an agent can "pass" by editing the tests, skipping them, or special-casing the test inputs. |
| P4 | **Autonomy scales with reversibility × blast radius.** Actions that are cheap to undo are free. Actions that cannot be undone are gated. | The cost of a mistake is what matters, and that cost depends on whether it can be undone. |
| P5 | **Small, dark, reversible increments.** Ship small diffs that merge with the new behaviour switched off and are turned on gradually. | Review and verification quality fall quickly as diff size grows. Rolling back a flag is cheap. |
| P6 | **Everything is a resumable state machine.** State is durable, steps can be safely repeated, and the system restarts from checkpoints. | Long runs crash, get preempted, or lose context, so recovery has to be the normal path rather than a special case. |
| P7 | **Every loop has a budget and a progress test.** | An agent that retries without measurable progress is spending money, not converging. |
| P8 | **Least privilege, and untrusted input stays data.** Issue text, code comments, web pages and dependency docs are never treated as instructions. Privileged actions are decided by deterministic policy, not by model output. | Prompt injection and over-broad credentials turn small errors into incidents. |
| P9 | **Humans own intent, irreversibility and the guardrails. Agents own execution.** | Accountability and value judgements cannot be delegated. An agent that can relax its own limits is effectively unconstrained. |

---

## 2. Lifecycle diagram

```
 ┌──────────────────────── CROSS-CUTTING (apply to every stage) ─────────────────────────┐
 │ LEDGER (event-sourced state, checkpoints)   BUDGET GOVERNOR (tokens/$/time/iterations) │
 │ POLICY ENGINE (action classes, risk tiers)  SANDBOX + SECRETS BROKER (scoped, expiring)│
 │ PROVENANCE (who/what/why for every artifact) TRUST BOUNDARY (untrusted-input tainting) │
 │ ESCALATION CHANNEL                          KILL SWITCH (halt at next step boundary)   │
 └────────────────────────────────────────────────────────────────────────────────────────┘

 request
    │
    ▼
 [0 INTAKE] ──duplicate / out of scope / rejected──► CLOSE (with reason)
    │  work item + provisional risk tier
    ▼
 [1 GROUND] ◄─────────────────────────────────────────────────────────────┐
    │  context dossier, reproduction (failing test for bugs)              │
    ▼                                                                     │
 [2 SPECIFY] ◄──────────── spec gap / contradiction ──────────┐           │
    │  spec + FROZEN acceptance suite (hash-locked)           │           │
    ╞══ H1: human approves spec (tier ≥ T2, or value-level ambiguity)     │
    ▼                                                         │           │
 [3 PLAN] ◄──────────── infeasible / k failures / design finding          │
    │  increment DAG, per-increment budget, rollback plan     │           │
    ▼                                                         │           │
 ┌─►[4 IMPLEMENT]──►[5 VERIFY]──fail, same signature < k──┐   │           │
 │      ▲               │ pass                            │   │           │
 │      └───────────────┼─────────────────────────────────┘   │           │
 │                      ▼                                     │           │
 │                 [6 REVIEW]──confirmed code finding──► 4    │           │
 │                      │      design finding ───────────────►3           │
 │                      ▼                                                 │
 │                [7 INTEGRATE]──conflict──► 4 ; mainline moved ──► 5     │
 │                      │  merged dark (behaviour off)                    │
 └──more increments─────┤                                                 │
                        ╞══ H2: human approves irreversible actions (T3)  │
                        ▼                                                 │
                  [8 RELEASE]──health check fails──► AUTO-ROLLBACK ───────┤
                        │  progressive exposure                           │
                        ▼                                                 │
                  [9 OBSERVE]──regression traced to this change──► revert ┘ (new work item)
                        │  soak window passes
                        ▼
                  [10 CLOSE & LEARN] ──► evidence bundle to requester;
                                        knowledge base, eval set, trust calibration

 ANY STAGE: budget exhausted │ no progress │ policy deny │ kill switch ──► ESCALATE (H3)
 BACKGROUND: H4 humans audit a random sample of auto-merged changes
             H5 humans own changes to the lifecycle's own policy
```

**Risk tiers.** The final tier is the higher of two assessments: the agent's own, and deterministic rules based on which paths and surfaces the change touches.
- **T0:** docs, tests, internal tooling.
- **T1:** ordinary product code behind a flag.
- **T2:** auth, payments, security, privacy, the data model, public APIs, concurrency primitives.
- **T3:** anything irreversible, such as destructive migrations, data deletion, infrastructure teardown, permission or credential changes, external communications, spending money, or licence changes.

---

## 3. Stage table

### 3a. What each stage does

| Stage | Goal | Inputs | Outputs |
|---|---|---|---|
| **0 Intake** | Decide whether to take the work, and at what risk tier. | Raw request (tagged untrusted); backlog; ownership map | Work item: normalised request, links to duplicates, provisional tier, initial budget, or a rejection with its reason |
| **1 Ground** | Understand the current system and, for bugs, prove the problem exists. | Work item; repository at a pinned base commit; history; runtime telemetry | Context dossier (relevant code, invariants, owners, existing tests, prior attempts); a failing reproduction for bugs; impact surface (callers, data, APIs) |
| **2 Specify** | Turn the intent into a checkable contract. | Dossier; request; conventions | Spec: problem, acceptance criteria, non-goals, constraints (performance, compatibility, security), open questions. A **frozen acceptance suite** (hash recorded in the ledger). Final risk tier |
| **3 Plan** | Choose an approach and split it into increments that can each be verified on their own. | Spec; dossier | A DAG of increments, each with its own scope (allowed paths), verification targets, budget and rollback step. Migration strategy (expand/contract). Flag design. Every action classified as reversible or irreversible |
| **4 Implement** | Make the smallest change that satisfies the current increment. | Plan increment; isolated workspace; frozen suite | Patch series with rationale per commit; new or updated non-frozen tests; checkpoint after each commit |
| **5 Verify** | Produce independent evidence that the change works and nothing was gamed. | Patch; frozen suite; full test suite | Evidence bundle: build, types, lint, unit, acceptance, regression, security scan, performance delta, coverage of changed lines, mutation score on changed code, **scope check** (diff inside planned paths), **integrity check** (no deleted assertions, skips, raised timeouts, or hard-coded test inputs) |
| **6 Review** | Find what the tests can't. | Diff; spec; evidence; dossier. The reviewer does **not** see the author's explanation first. | Findings, each with severity and a reproduction or concrete argument. Each finding is checked before it counts. A verdict |
| **7 Integrate** | Land the change safely on a mainline that keeps moving. | Approved patch; current mainline | Rebased change re-verified on the merge result; merged with behaviour off; ledger records the merge commit |
| **8 Release** | Turn the behaviour on gradually and automatically. | Merged increments; flag; health metrics and their baselines | Exposure ramp (internal → canary → percentage → full), each step gated by automated health comparison. Rollback is pre-staged |
| **9 Observe** | Catch regressions that only show up in production. | Telemetry; error budgets; user reports | Soak verdict, or an automatic revert plus a new work item that includes the evidence |
| **10 Close & Learn** | Deliver the result and improve the system. | Full ledger for the work item | Final report to the requester (what changed, evidence, residual risks). Flag cleanup scheduled. Retro entries, knowledge-base updates, new eval cases, an outcome label for trust calibration |

### 3b. How each stage runs autonomously

| Stage | Capabilities needed | Exit criterion | On failure |
|---|---|---|---|
| **0 Intake** | Request classification, duplicate detection, risk classification, effort estimation | Item accepted with tier and budget, or closed with a reason | If the tier is unclear, take the higher tier. If the request is unintelligible, send one consolidated question to the requester. |
| **1 Ground** | Code navigation and search, history archaeology, environment provisioning, bug reproduction, runtime introspection, impact analysis | Dossier is complete against a checklist. For bugs, a reproduction fails deterministically (passes the same check 3 out of 3 times). | If it can't reproduce, gather telemetry or ask the reporter for specific missing facts (H3). It must not "fix" a bug nobody has reproduced. |
| **2 Specify** | Ambiguity detection, requirement elicitation, acceptance-test authoring, spec critique | Every criterion maps to an executable check or an explicit manual check. Frozen tests **fail** on the base commit, or are correctly vacuous for non-functional work. A critic agent finds no untestable or contradictory criteria. Gets H1 approval when required. | Technical ambiguity is resolved by investigation, with the assumption recorded. Ambiguity about values or product choices goes to H1 as 2–3 options with a recommendation. |
| **3 Plan** | Design reasoning, decomposition, estimation, migration design, rollback design, plan critique | A critic agent signs off. Every increment has a scope, checks, a budget and a rollback. Total budget fits within the request's budget. | If no feasible plan exists within budget, go back to Specify with the reason. If the budget is still too small, escalate (H3) with a cost estimate. |
| **4 Implement** | Code editing, refactoring, dependency management, migration authoring, test writing, local debugging | The agent declares the increment complete and the patch is inside the planned scope. | If it is out of scope, re-plan. A tool or environment fault means retry from the checkpoint. |
| **5 Verify** | Test execution, failure diagnosis, static analysis, security scanning, benchmarking, mutation testing, test-integrity auditing, flaky-test detection | Every required check is green, run on a clean environment from the committed patch (not from the agent's workspace). | Go back to Implement with a diagnosis. Track a failure fingerprint (failing check + error signature); if the same fingerprint appears k=3 times, re-plan. Flaky tests are quarantined only with evidence (fails non-deterministically on the base commit), never by the author. |
| **6 Review** | Adversarial review across several lenses (correctness, security, spec conformance, maintainability), finding verification, ideally a different model or prompt lineage | No unresolved findings at or above the severity threshold. For T2, two independent reviewers agree. | A confirmed code finding goes back to Implement. A design finding goes back to Plan. Findings that can't be verified are logged but don't block, which stops reviewers looping on hallucinated issues. |
| **7 Integrate** | Rebase and conflict resolution, merge-queue participation, re-verification | Merged, and the re-verified merge result is green. | A semantic conflict goes back to Implement. If mainline moved, run Verify again. After 3 integration failures, escalate. |
| **8 Release** | Flag management, progressive rollout control, health evaluation against baseline, rollback execution | 100% exposure and every health gate green, or the work item is defined as flag-off delivery | Automatic rollback (flag off), then return to Ground with the production evidence. T3 actions never run without H2. |
| **9 Observe** | Anomaly detection, change attribution, revert execution | The soak window (scaled to tier) passes with no attributable regression. | Revert, then open a new work item linked to this one. |
| **10 Close & Learn** | Report writing, retrospective analysis, knowledge curation, eval curation, calibration | Report delivered. Ledger sealed. Flag-removal item created. | A failure here never blocks delivery. It is logged and sent to the lifecycle owners. |

---

## 4. Human involvement

Humans are needed in five places. Reviewing T0/T1 code is **not** one of them.

| Gate | When | What the human does | Why autonomy should not replace it |
|---|---|---|---|
| **H1: Intent / spec approval** | Tier ≥ T2, or any ambiguity that comes down to values or product choices (who wins a trade-off, what users should see) | Approves the acceptance criteria and non-goals, not the code. This is a short artifact that takes minutes. | Every later check verifies against the spec. A wrong spec gives a confidently wrong result that passes everything. This is where human attention has the most leverage, and value trade-offs need someone accountable. |
| **H2: Irreversible actions** | T3 actions: destructive migrations, data deletion, infra teardown, credential or permission grants, money, external communications, licence or legal changes | Approves a dry-run diff of the effects, the backup or snapshot reference, and the blast-radius statement. | Rollback is impossible by definition, and someone has to be accountable. Agents also have no reliable sense of external consequences such as legal or reputational ones. |
| **H3: Escalation** | Budget exhausted, no progress, contradictory requirements, can't reproduce, policy deny on something the plan needs | Decides one of: add budget, narrow scope, answer the question, or abandon. | The system has shown it can't settle the question itself. Retrying without new input wastes money. |
| **H4: Audit sampling** | Continuously, on a random sample of auto-merged T0/T1 changes (e.g. 5%, rising when the escape rate rises) | Labels each sampled change as acceptable or defective. | Author and judge models can share blind spots. Independent human labels are the only way to measure the escape rate and calibrate how much autonomy each tier should get. |
| **H5: Guardrail ownership** | Any change to tiers, gates, budgets, policy rules, frozen-suite rules, agent permissions, or the kill switch | Owns and approves those changes. | An agent that can loosen its own limits has no real limits. |

**Design rules for the gates:**
- Every gate presents a decision, not a diff dump: options, a recommendation, the evidence, and the cost of each option.
- Gates have timeouts. When one expires, the work is **parked**, never auto-approved.
- Gate approval rates are tracked. An approval rate near 100% with very short review times is treated as rubber-stamping, which means either the gate should be removed (by moving that class down a tier) or its presentation needs fixing.

---

## 5. Failure, safety and recovery

### Bounding cost and time
- **Hierarchical budgets.** Budgets nest: request → stage → increment → attempt. Each covers tokens, money, wall-clock time, tool calls, and iterations. The initial budget at Intake comes from tier and size. Plan replaces it with a bottom-up estimate. If the estimate is more than 2× the Intake budget, escalate before spending anything.
- **Thresholds.** At 80% of any budget the agent must stop and either compress its context, re-plan, or justify continuing to a critic. At 100% there is a hard stop and an H3 escalation. The governor enforces this, not the agent.
- **Per-stage wall-clock limits** prevent one stage from starving the rest. An overrun parks the work and moves on.

### Stopping runaway loops
- **Progress metric per loop.** Each loop has a monotonic measure: the Verify loop counts failing required checks, Review counts open confirmed findings, Integrate counts conflicts. If an iteration doesn't strictly improve it, that counts as a strike. Two strikes means re-plan; a re-plan that also fails means escalate.
- **Fingerprinting.** The ledger hashes each (diff, failure signature) pair. Seeing the same fingerprint again means the agent is stuck. Patterns like A→B→A diffs mean it is oscillating. Both trigger an immediate re-plan rather than another retry.
- **Back-edge counters.** Each back-edge (Verify→Implement, Review→Plan, Plan→Specify, and so on) has a cap per work item, typically 3. Exceeding it escalates.
- **Kill switch.** A global halt and a per-item halt. Agents check for them at every step boundary, and the policy engine refuses privileged actions while either is set.

### Crash and interruption recovery
- **Event-sourced ledger.** The ledger records every stage transition, artifact hash, decision and its rationale, and external side effect. Current state is a projection of that log, so nothing important lives only in an agent's context.
- **Reconstructible workspace.** A workspace is fully defined by (base commit, ordered patch series, environment manifest). On resume, it is rebuilt from those rather than trusted as found.
- **Leases with heartbeats.** A worker holds a lease on its work item and keeps it alive with heartbeats. If the heartbeat stops, the lease expires and another worker resumes from the last checkpoint.
- **Idempotent steps.** Every external side effect (merge, flag change, migration step, notification) carries an idempotency key and is written to the ledger as *intent → done*. On resume, an intent with no matching done is reconciled by querying the real world state before it is retried.
- **Re-validation on resume.** Before continuing, the agent checks three things: has mainline moved, has the request changed, and has the policy changed? Any change sends the item back to the earliest affected stage.

### Avoiding irreversible mistakes
- **Action classes in the policy engine.** Each action has a class: read, sandbox-write, shared-reversible, or irreversible. The class comes from a registry, not from the model's description of what it is about to do.
- **Two-phase execution for anything irreversible:** plan → dry run → diff of effects → snapshot or backup → H2 → execute → verify the post-state. If the dry run and the real execution diverge, abort.
- **Schema and data changes use expand/contract:** add the new form, dual-write, backfill, verify, switch reads, and only then contract. The contract step is the T3 action and is usually its own later work item.
- **Isolation by default.** Implement and Verify run in sandboxes with no production credentials and an allowlist for network egress. Credentials are issued per stage and per action and expire quickly. Production can only be reached through the release controller.
- **Taint tracking.** Content from untrusted sources is marked as tainted. A plan step whose justification depends on tainted text and that requests a privileged action is denied and escalated.
- **Reward-hacking defences.** The frozen acceptance suite is hash-checked in Verify. The integrity audit compares the test diff against base. Diff scope is enforced. The reviewer is shown any change to test files before seeing the implementation.

---

## 6. Capability catalogue

**Understanding**
- *Code navigation:* find the definitions, callers, and data flow relevant to a change.
- *History archaeology:* recover why the code is the way it is from history, past changes, and incidents.
- *Bug reproduction:* turn a report into a deterministic failing test.
- *Runtime introspection:* read logs, traces and metrics to ground claims about real behaviour.
- *Impact analysis:* list the callers, data, APIs and consumers a change could affect.

**Specification**
- *Ambiguity detection:* find underspecified or contradictory requirements and decide whether each is technical or value-level.
- *Requirement elicitation:* turn the unresolved ambiguities into a small number of decision-ready questions.
- *Acceptance-test authoring:* write executable criteria that fail on the base commit and are tied to the intent.
- *Spec critique:* adversarially check the spec for gaps, untestable criteria, and missing non-goals.

**Planning**
- *Risk classification:* assign a tier from what the change touches; combined with deterministic rules by taking the higher of the two.
- *Decomposition:* split the work into increments that can each be merged and verified on their own.
- *Estimation:* predict the cost and time per increment, calibrated against past outcomes.
- *Migration and rollback design:* plan expand/contract sequences and the undo step for each increment.
- *Plan critique:* independently review feasibility, scope and risk.

**Execution**
- *Code editing and refactoring:* make minimal, convention-matching changes.
- *Test writing:* add regression and unit tests beyond the frozen suite.
- *Dependency management:* add or upgrade dependencies, with supply-chain and licence checks.
- *Environment provisioning:* build hermetic, reproducible workspaces.

**Verification**
- *Test execution and orchestration:* run the right suites on a clean environment and collect the artifacts.
- *Failure diagnosis:* map a failure to its root cause and the fix location.
- *Static and security analysis:* types, lint, vulnerability and secret scanning.
- *Performance benchmarking:* compare against a baseline with statistical significance.
- *Mutation and property testing:* measure whether the tests would actually catch defects in the changed code.
- *Test-integrity auditing:* detect weakened, skipped or special-cased tests.
- *Flake detection:* tell non-determinism apart from real regressions.

**Review**
- *Adversarial multi-lens review:* look for correctness, security, conformance and maintainability defects.
- *Finding verification:* confirm or discard each review finding by reproducing it.

**Integration and release**
- *Conflict resolution:* resolve textual and semantic conflicts against a moving mainline.
- *Merge-queue participation:* serialise landing and re-verify the merge result.
- *Progressive rollout control:* ramp exposure step by step.
- *Health evaluation:* compare canary against baseline and decide whether to proceed.
- *Rollback and revert execution:* undo quickly and verify the undo worked.
- *Change attribution:* link a production regression to a specific change.

**Control plane (deterministic, not model-driven)**
- *Ledger and checkpointing:* durable, event-sourced state and resume.
- *Budget governor:* enforce hierarchical budgets and thresholds.
- *Policy engine:* classify actions and enforce tier gates.
- *Sandbox and secrets broker:* isolation and scoped, short-lived credentials.
- *Progress and stall detection:* fingerprints, strike counters, oscillation detection.
- *Escalation composer:* package a decision for a human with options, evidence and cost.
- *Kill switch:* global and per-item halt.

**Learning**
- *Retrospective analysis:* explain why attempts failed or escaped.
- *Knowledge curation:* keep conventions, invariants and pitfalls up to date for future grounding.
- *Eval curation:* turn escapes and failures into regression evals for the agents themselves.
- *Trust calibration:* adjust tier thresholds and audit rates from measured escape rates.

---

## 7. Trade-offs and open questions

**Tensions in the design**
1. **Spec up front vs. learning while building.** Freezing acceptance tests stops agents gaming them, but real work often reveals that the spec was wrong. I allow a Plan→Specify back-edge that unfreezes the suite, with re-approval for T2+. That adds friction exactly where discovery is most valuable. Too strict and agents escalate constantly; too loose and the freeze means nothing.
2. **Independent judges vs. correlated blind spots.** Using a different prompt, context or even model for review reduces shared errors but doesn't remove them, because models trained on similar data miss similar things. H4 sampling measures the problem but doesn't fix it. Independence costs roughly double the tokens for verification.
3. **Small increments vs. coherent changes.** Some changes, such as cross-cutting refactors or framework upgrades, don't split cleanly. Forcing the split produces awkward intermediate states. Allowing large diffs weakens review.
4. **Escalation threshold.** If the lifecycle escalates too often, humans become the bottleneck and start rubber-stamping (which is why approval rates are monitored). If it escalates too rarely, failures pass silently. The right threshold depends on the organisation and should be learned from outcomes, not fixed.
5. **Deterministic rules vs. agent judgement for risk.** Rules are predictable but crude. Agent judgement is nuanced but can be manipulated or wrong. Taking the higher of the two is safe but over-gates.

**What I am least sure about**
- **Whether tier classification is a single point of failure.** Everything downstream depends on the tier. If a T2 change is misclassified as T1, it skips H1 and the second reviewer. Path rules catch the obvious cases. Semantic risk, like a harmless-looking change to a retry loop that amplifies load, is exactly what rules miss.
- **Long-term codebase health.** Each change can be locally correct and pass every gate while the codebase as a whole drifts: duplicated abstractions, layering violations, rising complexity. Nothing in this lifecycle measures that drift. It probably needs a separate periodic "architecture steward" process with its own human owner. I haven't designed one.
- **Whether spec approval is enough human leverage for T2.** Approving the *what* without seeing the *how* assumes that a correct spec plus green checks means a correct implementation. For security-sensitive code, the implementation may need human review as well. I've chosen not to require it, but I hold that choice loosely.
- **Budget estimation.** Agent cost per task varies very widely. Budgets set at Intake will often be wrong, and the 2× re-estimate rule is a guess, not a calibrated value.
- **Measuring trust at all.** Escape-rate labels arrive late (some defects surface months afterwards) and cover only a sample. Raising autonomy based on that signal may mean acting on data that is already out of date when the underlying models change.

---

The context7 MCP server needs authorisation before it can be used (via `claude mcp` or `/mcp` in an interactive session). I didn't need it for this design.