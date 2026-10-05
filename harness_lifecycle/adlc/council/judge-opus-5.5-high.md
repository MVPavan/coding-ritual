# Council judgment: Autonomous Development Lifecycle

**Note on independence.** Sol and Astra are close structural twins. Both use six principles built around authority, evidence and bounded exposure. Both split work into agents plus a controller and both centre on an "authority envelope" or "change contract". They also share specific phrasing, such as "silence never expands authority" and leases with generation numbers. I therefore count their agreement as roughly one independent vote, not two. Fable reached the problem from a different angle and is often the minority voice. Where its mechanisms are better argued, it wins.

Abbreviations: **F** = Fable 5.1, **S** = GPT-6.1 Sol, **A** = GPT-6 Astra.

---

## 1. Member positions

### Fable 5.1 (F)
- **Principles (9):** intent before work; verification is independent of generation; evidence, not assertion; autonomy ends where reversibility ends; everything is bounded; state lives outside the agent; scope is a contract; least privilege per stage; trust is earned per change class.
- **Stages (11):** 0 Intake → 1 Specify → 2 Investigate → 3 Plan → 4 Encode acceptance → 5 Implement → 6 Self-verify → 7 Independent review → 8 Integrate → 9 Deliver → 10 Observe & close. Any stage can escalate. A **trivial fast path** skips stages 2, 3 and 7.
- **Human touchpoints:**
  - **G1 spec gate.** Fires on leftover ambiguity or risk of medium or above. The human reads the spec and the acceptance tests, never the diff.
  - **G2 gate** before irreversible or owned-consequence actions: auth/crypto/billing, destructive migrations, public APIs, spend, legal.
  - Escalation, policy authorship, and **post-hoc calibration sampling**.
  - Explicitly *no* pre-merge human review of routine diffs.
- **Tests-first stage.** Acceptance tests must **fail on baseline for the expected reason** before implementation starts. Test strength is measured by **mutation score on changed lines**.
- **Concrete loop control:**
  - Each iteration records the diff hash and the set of failing checks. An identical or growing failure set sends the work back to replanning.
  - A review finding that survives two rounds also goes back to replanning.
  - If reviewer and implementer disagree on what the spec means, work returns to Specify.
- **Goodhart guards.** Deleted tests, weakened assertions, skip markers and widened tolerances are auto-flagged and shown to the reviewer first. The reviewer **never sees the implementer's reasoning trace**.
- **Irreversibility is a property of the capability, not the agent's judgment.** Irreversible actions are unavailable to stages 1–8. No deploy happens without a rollback artifact that was **exercised in pre-prod during the same run**.
- **Trust is measured.** The sampling rate per change class adapts to the defects found, and sampling is the *only* way a class graduates to ungated. Learnings feed rules and skills. A later stage can never lower the risk class.

### GPT-6.1 Sol (S)
- **Principles (6):** intent and authority come from outside the agent; evidence proportional to consequences; implementation and acceptance under separate control; limit harm before attempting work; progress is durable and bounded; completion is an observed outcome.
- **Architecture: agents vs a controller.** The controller owns state, permissions, budgets, evidence and transitions. Its enforcement holds "even when an agent ignores its instructions."
- **Stages (12):** Admit & bound → **Ground in reality** → Establish change contract → Design & plan → **Prepare isolation & baseline** → Implement → Qualify → Independently challenge → Integrate & construct delivery candidate → Authorize & promote → Observe contracted outcome → Settle & transfer ownership.
  - It investigates *before* contracting.
  - Stages are logical obligations that can be combined. An obligation that doesn't apply is recorded with a reason.
- **Human touchpoints:**
  - The owner sets a standing delegation.
  - Humans decide unresolved value choices, actions that exceed delegated authority, acceptance that needs human judgment, and recovery beyond the incident mandate.
  - Sol's position: "No per-change human action is inherently required."
  - A decision request must list alternatives, evidence, a recommendation and the exact authority requested.
- **Evidence records.** Each record carries the contract version, candidate, baseline, verifier, environment and limitations, and is **invalidated when any dependency changes**. Approvals are scoped to contract, action, artifact, destination and validity period.
- **Strongest crash semantics:**
  - A durable five-step protocol per stage: record intent → take a lease → execute and capture receipts → evaluate independently → commit.
  - **Leases with generation numbers** fence out stale workers.
  - If an external action's outcome is unknown, the controller queries the destination. If that can't settle it, replay is blocked.
- **Failure-class table.** Transient, defect, invalid assumption, missing authority, unknown action result and exhaustion each get distinct handling.
  - **Reserve budget for containment** before spending the implementation allowance.
  - **Ambiguous health signals freeze expansion** and escalate, rather than triggering a rollback that could itself cause harm.
- **Protected verification.** Acceptance criteria, verifier configuration and result records cannot be written by the candidate. "Infrastructure errors produce no success verdict."

### GPT-6 Astra (A)
- **Principles (6):** success needs an external reference; ability does not imply authority; evidence has a scope; uncertainty requires bounded exposure; progress survives the worker; autonomy is finite and accountable.
- **Three responsibilities:** agent, controller and accountable owner. **Execution modes** (RUNNING / WAITING / RECOVERING / STOPPED / TERMINAL) are kept separate from stages.
- **Stages (11):** Admit & bound authority → Define success → Establish current reality (back-edge to 2) → Design & plan → Implement → **Verify & challenge (merged)** → Assemble & validate final candidate → **Authorize delivery (its own stage)** → Deliver with bounded exposure → Observe & accept → Close & transfer responsibility.
- **Six-part durable work record:** contract, authority envelope, risk assessment, execution state, evidence ledger, delivery and recovery plan. **Acceptance-predicate format:** what is observed, under what conditions, against which threshold, for how long.
- **Human touchpoints:** setting or changing delegation; consequential intent; accepting exceptional consequences; explicitly human acceptance judgments.
  - An irreversible action does *not* need fresh approval if a specific standing authorization covers it.
  - Human review "should answer a defined question rather than serve as a ritual."
- **Informative-retry record:** observed failure, proposed cause, changed action, expected discriminating result, remaining allowance. An unchanged retry is allowed only for a classified transient failure. **A heartbeat is not progress.**
- **Recovery and dispositions.**
  - Recovery options: reversal, compensation, forward repair, or containment plus escalation.
  - Dispositions include **REVERTED** ("a successful rollback is not a successful change") and **"delivered; outcome pending"**.
- **Delegation and review.** Bounded feasibility experiments during planning, and provenance checks on sources. Delegation expands by measured outcomes, never by self-reported confidence. Astra prefers **diversity of evidence over the number of reviewers**.

---

## 2. Stage alignment table

| Merged stage | Fable | Sol | Astra | Verdict |
|---|---|---|---|---|
| Admission, risk, budget | 0 Intake | 1 Admit and bound | 1 Admit and bound authority | agree (F adds risk class and fast-path routing; S/A add an authority envelope) |
| Intent / success definition | 1 Specify | 3 Establish change contract | 2 Define success | agree on content, **differ on order** |
| Grounding / investigation | 2 Investigate | 2 Ground in reality | 3 Establish current reality | agree on content, differ on order |
| Design & plan | 3 Plan | 4 Design and plan | 4 Design and plan | agree |
| Executable acceptance before code | 4 Encode acceptance | — (acceptance design inside 3; criteria "protected") | — (tests written in 5) | **unique (F)** |
| Isolation & baseline characterization | — (sandbox is a cross-cutting rail; dossier lists covering tests) | 5 Prepare isolation & baseline | — (baseline inside 3) | unique as a stage (S); all share the concept |
| Implement | 5 Implement | 6 Implement | 5 Implement | agree |
| Self-verification / qualification | 6 Self-verify | 7 Qualify | 6 Verify & challenge | agree |
| Independent review | 7 Independent review | 8 Independently challenge | 6 (merged with verify) | **differ** (A merges them) |
| Integrate / build delivery candidate | 8 Integrate | 9 Integrate & construct delivery candidate | 7 Assemble & validate final candidate | agree (S/A add an immutable artifact) |
| Delivery authorization | G2 (conditional gate) | 10 (merged into promote) | 8 Authorize delivery | differ in form, mostly agree in substance |
| Promote / deliver | 9 Deliver | 10 Authorize & promote | 9 Deliver with bounded exposure | agree |
| Observe outcome | 10 Observe & close | 11 Observe contracted outcome | 10 Observe & accept | agree |
| Containment / recovery | Automatic ROLLBACK → new Intake | Containment → bounded repair at 2/4/6 or incident; freeze on ambiguity | Contain / reconcile / recover → repair through 3–8 | **differ** |
| Close / transfer ownership | 10 (closure record) | 12 Settle & transfer ownership | 11 Close & transfer responsibility | agree; S/A add ownership transfer and credential release |
| Learning & trust calibration | 10 learnings → rules/skills; calibration sampling | — | — (one line in trade-offs) | **unique (F)** |
| Escalation / waiting states | ESCALATE from any stage | WAITING_FOR_DECISION / BLOCKED / FAILED / CANCELLED | Execution modes, WAIT_FOR_DECISION | agree |

---

## 3. Agreements

1. **A checkable contract comes before code.** Intent, acceptance criteria, non-goals and constraints are made explicit, and weak success criteria are the top unsolved risk. All three name oracle quality as their deepest uncertainty.
2. **Work state lives outside agent context.** A replacement agent resumes from durable records, not from a conversation narrative.
3. **Every loop is bounded, and agents can't extend their own budget.** S and A add that back-edges and new workers draw on the same root budget. F nests stage budgets inside a ticket budget set by policy.
4. **Retries must be informative.** A repeated identical failure triggers replanning or escalation, not another attempt. F uses failure-set hashes; A uses the retry record; S uses failure and candidate fingerprints.
5. **Generation and acceptance are separated.** The implementer cannot certify itself. All three also doubt that a same-model fresh-context reviewer is truly independent.
6. **Least privilege per stage.** Implementation and tests run in sandboxes without production credentials, and credentials are short-lived and scoped.
7. **Untrusted content is data.** Repository text, issues, logs and tool output can never grant authority or change policy.
8. **External actions are idempotent.** Consequential effects carry operation identities so a crash doesn't duplicate them. S and A go further and reconcile unknown outcomes.
9. **Recovery is prepared before promotion, and exposure is progressive** with predetermined stop thresholds and observation windows.
10. **A finite observation window does not prove correctness.** Closure must state exactly what was established.
11. **Humans handle intent, authority and accountability, not routine diff review.** All three reject pre-merge human diff review of routine changes as ritual or false assurance. Escalations must be structured, and silence never authorizes anything (F: "park, not guess").
12. **Trust should expand only on measured outcomes per class of work,** never on an agent's self-reported confidence (F in detail, A in one line).

---

## 4. Disputes and rulings

### D1. Are some human gates mandatory, or can standing delegation cover everything?
- **F's position.** G1 fires on medium+ risk or leftover ambiguity. G2 is mandatory for irreversible and high-consequence categories. Strongest argument: accountability is a human property, and someone must answer for *this* consequence. G1 is cheap because specs are short and humans actually read them.
- **S/A's position.** No per-change human action is inherently required. Standing authorization can cover even irreversible actions, and a ritual approval degrades into rubber-stamping. Strongest argument: F itself says humans rubber-stamp long artifacts, and per-instance approval of a routine irreversible action (say, a scheduled data-retention purge) will be rubber-stamped too.
- **Ruling: split.**
  - **G1 goes to F.** S/A only bring a human in when the *agent detects* an unresolved value choice. But all three agree that undetected misinterpretation is the hardest failure. A risk-triggered gate is the only mechanism offered that doesn't depend on the agent noticing its own error. It is cheap because the human reviews a contract plus tests, not a diff.
  - **G2 goes to S/A, with F's category list as the default policy.** The model is delegation-based (authority envelope, approval bound to artifact, destination and expiry). Out of the box, F's categories are *non-delegable*. An owner can delegate one specific class only after calibration sampling shows a clean record. That gives S/A's flexibility with F's conservative starting point.

### D2. Specify first, or investigate first?
- **F/A: specify first.** Investigation without intent has no boundary, and investigating first biases the spec toward whatever is easy to change.
- **S: ground first.** You can't write checkable criteria about interfaces you haven't examined. S bounds discovery with a "discovery allowance".
- **Ruling: two passes.** First draft the intent (outcome, non-goals, open questions), then ground it, then *freeze* the contract. F and A already have the spec-gap back-edge; S's discovery allowance bounds the grounding step. The contract is frozen, and G1 fires, only after grounding. G1 then reviews an informed contract instead of a guess.

### D3. Should executable acceptance tests be their own stage before implementation?
- **F: yes.** Tests written before the code can't be fitted to it, and a test that fails on baseline is proven to discriminate.
- **S/A: no.** Acceptance is designed in the contract and protected, and tests are built alongside implementation. S/A's strongest argument is that some criteria are runtime outcomes or human judgments that can't be a failing unit test.
- **Ruling: F's stage, with S's write protection and A's format for what can't be tested.**
  - Tests must fail on baseline and are then **write-locked against the implementer** (S principle 3).
  - Criteria that can't be tested in advance become A-format predicates (observed, conditions, threshold, duration) checked at Qualify or Observe.
  - "Untestable" is never accepted silently: it sends work back to the contract (F).

### D4. Should independent review be its own stage, and where does independence come from?
- **F/S: a separate stage.** F: fresh context, no reasoning trace, read-only credentials, a different model family if possible.
- **A: merged into verification.** Diversity of *evidence* (reference behaviour, invariants, external observation) beats counting reviewers.
- **Ruling: keep a separate stage, adopt A's content.** Merging the stages invites the implementer's framing to leak into the challenge. So the separation in context and permissions (F/S) stays. The reviewer's job, though, is to produce *new evidence* (counterexamples, invariant checks, reference comparisons), not an opinion (A). Model diversity is secondary. **Human calibration sampling (F) is the only proposed way to measure the reviewer's miss rate,** so it is mandatory.

### D5. A fast path, or collapsible obligations?
- **F: an explicit trivial path** that skips 2, 3 and 7, keyed off the Intake classifier. F concedes the classifier then becomes a single point of failure.
- **S/A: all obligations always apply.** Small changes combine stages, and skipped obligations are recorded with a reason.
- **Ruling: S/A's framing plus a correction neither side made.** Obligations always exist; for trivial work they collapse into one execution. The independent-challenge stage can be replaced by deterministic checks *only if* the risk class is **re-derived from the actual diff** (touched paths, symbols, surfaces) at Qualify and Integrate. If the diff is outside the class, the class rises (F's monotonic rule). Classifying the request text alone, as F does, can be manipulated; classifying the diff mostly can't.

### D6. Automatic rollback, or freeze and diagnose?
- **F: a health-signal breach triggers automatic rollback.**
- **S/A: rollback can cause harm** after data mutations or external effects. Ambiguous signals should freeze expansion and escalate. A gives the menu: reversal, compensation, forward repair, containment.
- **Ruling: S/A, with F's precondition.**
  - Stopping expansion is **always automatic**.
  - Rollback is automatic only when the rollback artifact was rehearsed in pre-prod during this run (F) *and* the change is stateless or uses an expand/contract-compatible migration.
  - Otherwise the system contains the damage and escalates.

### D7. After a production failure: a new ticket, or bounded repair inside the original budget?
- **F: a new linked Intake.** Its risk class and budget come from incident policy.
- **S/A: repair within the remaining root budget.** Their rule: "children don't create fresh allowance."
- **Ruling: split by activity.** Containment and rollback draw on the original work item's **reserved recovery budget** (S). The *repair* is a new linked work item, because an incident usually has a different risk class and a requester who now cares more. Its budget comes from human-authored incident policy, so this doesn't violate the no-self-granting rule.

### D8. An explicit controller?
- **S/A:** a named control plane whose enforcement holds even if the agent ignores instructions.
- **F:** implicit; policy-set budgets and capability-level tags need such a component but don't name it.
- **Ruling: S/A.** It is the architectural piece that makes every other safeguard real rather than advisory. F contributes **capability-level reversibility tags**, which tell the controller *what* to enforce without trusting agent judgment.

### D9. Closure: learning (F) or ownership transfer (S/A)?
Not a true conflict; keep both. F's learning loop has to respect F's own rule: proposed rule or policy changes go through the lifecycle and never take effect directly.

---

## 5. Consolidated lifecycle

**Thesis.** F's inner loop (contract, tests first, guarded implementation, blind review) and trust governance, run on S's control plane (durable protocol, evidence invalidation, fencing, reconciliation), using A's record formats (predicates, retry records, dispositions).

### 5.1 Diagram

```
CONTROLLER RAILS — every stage; enforced by trusted machinery, not agent goodwill   [S,A; F]
  • Budget ledger: root budget > stage budgets; reserved recovery capacity      [F,S,A; reserve S,A]
  • Durable journal; 5-step stage protocol; leases with generation fencing      [S; A; F journal]
  • Evidence ledger: bound to artifact hash, invalidated on dependency change    [S,A; F hash]
  • Per-stage least-privilege credentials; capability-level reversibility tags  [F; S,A]
  • Untrusted input = data; policy/verifier/acceptance store write-protected    [all; S]
  • Stuck detection: failure fingerprints + informative-retry record            [F,A,S]
  • Monotonic risk class (raise-only, re-derived from actual diff)              [F + judge]
  • Kill switch (halts at journal boundary) · escalation channel · provenance   [F; all]
  • Execution modes: RUNNING | WAITING | RECOVERING | STOPPED | TERMINAL        [A]

request
  │
  ▼
[0 ADMIT & BOUND] ──── unauthorized / duplicate / prohibited ───► REJECTED
  │  risk class, authority envelope, root budget, discovery allowance
  ▼
[1 DRAFT INTENT] ◄──────────────────────────────────────────────┐
  │                                                             │ spec wrong / infeasible
  ▼                                                             │
[2 GROUND & BASELINE] ──────────────────────────────────────────┤
  │                                                             │
  ▼                                                             │
[3 FREEZE CONTRACT] ═══ G1 (ambiguity OR risk ≥ medium) ═══     │◄── criterion untestable (5)
  │                                                             │◄── spec-meaning dispute (8)
  ▼                                                             │
[4 PLAN] ◄───────────────────────────────┐                      │
  │   (risk may rise → re-enter G1)       │                      │
  ▼                                       │ no progress / ≤N spent / finding survives 2 rounds
[5 ENCODE ACCEPTANCE]                     │
  │  tests fail on baseline → write-lock  │
  ▼                                       │
[6 IMPLEMENT] ◄────────┐                  │
  │                    │ red (≤N)         │
  ▼                    │                  │
[7 QUALIFY] ───────────┘──────────────────┤
  │                                       │
  ▼                                       │
[8 INDEPENDENT CHALLENGE] ─ finding → 6 (≤M) ─ repeat → 4
  │
  ▼
[9 INTEGRATE & BUILD CANDIDATE] ─ drift → requalify 7 · semantic conflict → 6 · broken assumption → 2
  │
  ▼
[10 AUTHORIZE] ═══ G2 if outside delegation or non-delegable class ═══
  │   approval bound to artifact + destination + expiry; stale → refresh evidence
  ▼
[11 PROMOTE, BOUNDED EXPOSURE]
  │
  ▼
[12 OBSERVE] ── breach ──► STOP EXPANSION ──► rehearsed & state-safe? ──yes──► ROLLBACK ─┐
  │                                     └──no──► CONTAIN + ESCALATE ─────────────────────┤
  │                                                             linked repair item at 0 ◄─┘
  ▼
[13 CLOSE, TRANSFER, LEARN] ──► disposition · owner handoff · creds revoked
                            ──► learnings proposed as tests/rules (via lifecycle, never direct)
                            ──► calibration sample ──► human ──► trust tier per class

ANY STAGE: budget at reserve │ stuck │ authority missing │ kill switch
      ──► WAITING (state frozen, resumable; silence never expands authority) ──► H4 escalation
```

### 5.2 Stage table

| # | Stage | Goal | Capabilities | Exit criterion | Failure path | Source |
|---|---|---|---|---|---|---|
| 0 | Admit & bound | Decide whether and how work may begin | Request classification, duplicate detection, rule-based risk classification, authority check, budget estimation | Authorized requester; risk class; authority envelope; root budget with reserved recovery capacity; discovery allowance | Reject, wait for authority, or offer a narrower scope; unclassifiable → escalate | F (risk/budget), S (discovery allowance, reserve), A (envelope) |
| 1 | Draft intent | Capture the outcome before work biases it | Intent interpretation, ambiguity detection, non-goal articulation, question formulation | Outcome, non-goals and open questions recorded | Ask the requester; no answer within SLA → park, don't guess | F, A |
| 2 | Ground & baseline | Know the real system and its pre-existing failures | Codebase navigation, call-graph and dependency analysis, history archaeology, runtime probing, sandbox setup, baseline characterization, source-provenance assessment | Every affected surface maps to code; covering tests listed; existing failures characterized; workspace = pinned base + patch | Spec wrong or infeasible → 1; inaccessible consequential fact → block | F (dossier, workspace), S (stage 5, isolation), A (provenance) |
| 3 | Freeze contract | Make success checkable and authority explicit | Acceptance design using A's predicate format, scope declaration, risk reassessment | Each consequential requirement has an evaluation method and recorded proof limits; G1 passed if triggered | Value choice → human; unverifiable promise → decline or narrow | F (G1), S (evaluation methods, proof limits), A (predicates) |
| 4 | Plan | Choose a feasible, recoverable route | Decomposition, alternative generation, feasibility experiments, verification-strategy design, migration and compatibility analysis, rollback planning | Each step has a check; declared file scope; recovery route; fits budget | Shrink scope or escalate; risk raised → re-enter G1 | F, A (experiments), S |
| 5 | Encode acceptance | Make intent executable before code exists | Test authoring, property tests, bug reproduction, fixture construction | Every criterion maps to a check; new tests **fail on baseline for the expected reason**; tests then **write-locked** | Untestable → 3 | F (stage), S (protection) |
| 6 | Implement | Smallest in-scope change that passes acceptance | Code editing, refactoring, build operation, dependency management, migration authoring, debugging | Acceptance and existing suite pass locally; diff within declared scope or each deviation justified | Red → retry with a retry record (≤N); same or growing failure set → 4 | F (stuck rule, scope), A (retry record) |
| 7 | Qualify | Produce evidence bound to the exact candidate | Test execution, flaky-test discrimination, differential diagnosis, static/type analysis, security scan, mutation testing on changed lines, benchmarking | All checks green or waived in the journal; mutation threshold met; infrastructure errors give no verdict; risk re-derived from the diff | Defect → 6; weak evaluation method → 3; flake → quarantine ticket | F (mutation, flakes), S (differential diagnosis, no verdict on infrastructure errors), judge (diff reclassification) |
| 8 | Independent challenge | Find what the implementer can't see | Spec-conformance review, scope-creep detection, test-weakening detection, adversarial counterexample search, invariant and reference checks | Zero blocking findings from a fresh-context, read-only reviewer without the reasoning trace; Goodhart flags resolved | Finding → 6 (≤M); survives 2 rounds → 4; spec dispute → 3 | F (mechanics), S (separate permissions), A (evidence diversity) |
| 9 | Integrate & build candidate | Evidence applies to what actually ships | Rebase and conflict resolution, change-impact analysis, incremental requalification, immutable artifact build, provenance capture | Exact artifact passes requalification against the current mainline via conditional write; provenance and recovery package complete | Drift → 7; semantic conflict → 6; broken assumption → 2; never overwrite silently | All; S (conditional writes, invalidation) |
| 10 | Authorize | Confirm authority and evidence for this artifact and destination | Policy evaluation (controller), evidence-freshness check, decision preparation | Controller confirms authority; G2 passed if the action is outside delegation or non-delegable | Stale evidence → refresh; wait for authority; non-waivable failure → deny | A (stage), S (scoped approval), F (G2 categories) |
| 11 | Promote, bounded exposure | Apply the change without irreversible harm | Rollout control, migration sequencing, receipt capture, external-state reconciliation | Rollback rehearsed in pre-prod this run; increments pass immediate health checks; receipts journaled | Unknown result → reconcile before any retry; breach → stop expansion | F (rehearsal), S/A (reconciliation) |
| 12 | Observe | Confirm the contracted outcome | Canary and baseline comparison, outcome evaluation, anomaly diagnosis | Predicates hold for the window at required exposure, or "delivered; outcome pending" with an owner | Stop expansion; auto-rollback only if rehearsed and state-safe, otherwise contain and escalate; repair as a linked item | S/A (freeze), F (auto-rollback precondition), A (dispositions) |
| 13 | Close, transfer, learn | Accountable, maintainable result plus better future runs | Evidence synthesis, ownership handoff, credential and resource cleanup, learning extraction | Disposition recorded (COMPLETED / REVERTED / FAILED / …); owners assigned; creds revoked; learnings filed as proposals | Missing owner → stays open with the missing obligation named | S/A (handoff), F (learning), A (dispositions) |

**Fast path** (judge, from D5). Trivial classes, defined by human-authored path and surface rules, collapse stages 1–5 into one execution. Stage 8 is replaced by deterministic scope and Goodhart checks plus a higher calibration-sampling rate. If the risk re-derived from the diff exceeds "trivial", the full path resumes.

### 5.3 Human touchpoints

| ID | When | What the human decides | Why it stays human | Source |
|---|---|---|---|---|
| H0 | Standing, before any work | Risk rules, budgets per class, autonomy tiers, non-delegable classes, rollback thresholds | The system can't grant itself authority or decide whose losses are acceptable | F, S, A |
| H1 (G1) | Stage 3, on leftover ambiguity **or** risk ≥ medium | Approves the contract and acceptance tests (never the diff) | Only the owner holds intent; this gate doesn't rely on the agent noticing its own misreading | F (trigger), S/A (value choices) |
| H2 (G2) | Stage 10 / recovery, when an action is outside delegation or in a non-delegable class (auth, crypto, billing, destructive data, public contracts, spend, legal) | Approves one artifact, destination and expiry | Accountability for consequences; delegable per class only after a clean sampling record | F (classes), S/A (scoping, delegation) |
| H3 | Stage 3 / 12, when the contract requires human judgment (UX, legal) | Provides the acceptance judgment | No adequate oracle; a proxy can't silently stand in | S, A |
| H4 | Any stage: budget at reserve, stuck, recovery beyond mandate | Extends, re-scopes, abandons, or chooses among losses | Agents never grant themselves budget; incidents don't confer unlimited authority | F, S, A (structured request format: S/A) |
| H5 | After merge, sampled | Reviews a random sample of autonomous merges per class; moves trust tiers | The only empirical measure of verifier miss rate | F |

No routine pre-merge human diff review. All three agree; the judge concurs.

### 5.4 Safety and recovery mechanisms

**Cost and time**
- Root budget in several currencies: attempts, wall-clock, spend, concurrency, external operations, exposure (F, S, A).
- Children and back-edges draw on the root (S, A).
- Recovery and reporting reserve is set aside first; reaching it stops feature work (S, A).
- Exhaustion is a clean exit into WAITING, not an error (F).

**Runaway loops**
- Per-iteration fingerprint of diff hash and failing-check set; an identical or growing set → replan (F).
- Every retry needs a retry record with an expected discriminating result (A).
- Two replans without progress → escalate (F).
- A heartbeat is not progress; progress means a named milestone (A).
- Goodhart guards flag test deletion or weakening and changed tolerances (F). The acceptance and verifier store is write-protected (S).

**Crash and interruption**
- Five-step stage protocol (S).
- Workspace = pinned base + journaled patch (F).
- Leases with generation numbers, revoked on reassignment (S, A).
- A replacement worker re-derives evidence validity from records, not from the previous narrative (A).
- Kill switch halts at a journal boundary (F).

**External effects**
- Intent recorded before every mutation, receipt after (A).
- Idempotency keys and conditional writes (F, S).
- Unknown outcome → query the destination; if unreconcilable, block replay (S, A).

**Irreversibility**
- Reversibility tags live on capabilities; irreversible capabilities are unavailable before stage 10 (F).
- No production credentials in stages 0–9; reviewer is read-only; egress is allow-listed (F, S, A).
- Rollback is rehearsed in pre-prod this run before promotion (F).
- Expand/contract migrations, so old and new versions coexist (S).
- Recovery options: reversal, compensation, forward repair, containment (A).

**Evidence integrity**
- Evidence is bound to artifact hash, environment and contract version, and invalidated when a dependency changes (S, A).
- An infrastructure error never yields a pass (S).
- Flaky tests are quarantined, not ignored (F).

**Injection**
- Capabilities come only from stage definitions; everything read is data (F, S, A).

**Reporting**
- Precise dispositions; "a rollback succeeded" is never reported as "the change succeeded" (A, S).

### 5.5 Capability catalogue

Capabilities marked **[ctl]** should be deterministic controller machinery, not agent judgment (S, A).

| Group | Capability | Purpose | Source |
|---|---|---|---|
| **Intent & authority** | Request classification and duplicate detection | Type, urgency and prior duplicates of a request | F |
| | Risk classification (rule-heavy, monotonic, diff-rederived) | Assign blast radius, reversibility and sensitivity class | F, S, A, judge |
| | Authority assessment **[ctl]** | Decide which actions are permitted on which resources | S, A |
| | Ambiguity detection and question formulation | Find under-specified intent; ask the fewest resolving questions | F, A |
| | Acceptance design (predicate form) | Turn intent into observable predicates with proof limits | F, S, A |
| | Non-goal articulation | State what the change deliberately won't do | F, A |
| | Decision preparation | Package alternatives, evidence, recommendation and requested authority | S, A |
| **Understanding** | Codebase navigation; call-graph and dependency analysis | Locate code and its blast radius | F, S, A |
| | History archaeology; convention extraction | Learn why code is the way it is, and local idioms | F |
| | Runtime probing; baseline characterization | Observe actual behaviour and pre-existing failures | F, S, A |
| | Source-provenance assessment | Separate authoritative evidence from stale or untrusted claims | A |
| **Planning** | Decomposition and scheduling | Split work into individually checkable steps with ownership | F, S, A |
| | Alternative generation; feasibility experiments | Weigh approaches; resolve key uncertainty cheaply | F, A |
| | Verification-strategy design | Decide what evidence proves each step | F, A |
| | Migration and compatibility analysis; rollback planning | Design the undo before the change | F, S, A |
| | Estimation | Forecast against budget, including reserve | F, A |
| **Construction** | Code and configuration editing; refactoring | Make in-scope coherent changes | all |
| | Build operation; dependency management | Compile, package, control third-party risk | F, A |
| | Migration authoring | Reversible or expand/contract persisted-state changes | F, S |
| | Debugging from failure output | Map a failing check to a cause; form a testable hypothesis | F, A |
| **Verification** | Test authoring, property tests, bug reproduction | Encode criteria as failing-first checks | F, A |
| | Test execution and flaky-test discrimination | Tell nondeterminism from regression | F |
| | Differential diagnosis | Separate candidate defect, baseline defect, environment fault, bad assumption | S |
| | Mutation testing on changed lines | Measure whether tests actually constrain the change | F |
| | Static, security, performance and compatibility analysis | Non-functional evidence | F, S, A |
| | Evidence appraisal and change-impact analysis **[ctl-assisted]** | Decide which claims stand; invalidate stale evidence | S, A |
| **Independent challenge** | Spec-conformance and scope-creep review | Does the diff do exactly the spec? | F |
| | Test-weakening detection **[ctl]** | Flag deleted, skipped or loosened checks | F |
| | Adversarial counterexample search; invariant and reference checks | Produce new evidence, not opinion | F, A |
| | Change explanation | Descriptions for reviewers and users | F |
| **Integration & delivery** | Rebase and conflict resolution; requalification | Land on current mainline safely | all |
| | Immutable artifact construction and provenance | Tie what ships to source, inputs and evidence | S, A |
| | Promotion and rollout control; canary analysis | Bounded exposure against baseline | F, S, A |
| | External-state reconciliation **[ctl]** | Resolve unknown action outcomes before retrying | S, A |
| | Rollback, compensation, forward repair | Restore or mitigate | F, A |
| | Incident diagnosis and containment | Limit harm while establishing actual state | S, A |
| **Control & continuity [ctl]** | Durable orchestration and journaling | Authoritative stage state outside agents | all |
| | Budget and loop enforcement; stuck detection | Stop exhausted or cycling work | all |
| | Leasing and generation fencing | Stop stale workers committing | S, A |
| | Least-privilege credentialing; reversibility tagging | Scope access per stage; gate irreversible capabilities | F, S, A |
| | Untrusted-input handling; secret filtering | Content never acquires authority; evidence stays clean | all |
| | Kill switch | Global or per-item halt at a consistent boundary | F |
| **Closure & learning** | Closeout and ownership handoff; cleanup and revocation | Accountable result; no lingering privileges | S, A |
| | Learning extraction | Turn incidents and closures into proposed tests, rules or skills | F |
| | Calibration-sample selection **[ctl]** | Route a random sample per class to humans; adapt the rate | F |

---

## 6. Gaps that none of them covered well

1. **Who writes the oracle, and how is it checked?** All three name oracle quality as their top uncertainty, yet none separates the *test author* from the implementer.
   - Proposals:
     - author acceptance tests in a separate context from the implementer;
     - "back-translation", where a fresh agent restates the spec from the tests alone and the restatement is diffed against the contract;
     - human calibration sampling that covers *contracts*, not just merges.
2. **Classifying risk from the actual diff.** F makes risk monotonic but classifies from request text, and S/A assess risk up front. None re-derives risk deterministically from the touched paths and surfaces of the real diff, which is the cheapest defence against a manipulated or wrong intake classification.
3. **Coordinating many work items.** F calls this out of scope; S/A prevent stale writes but not wasted or conflicting work. Missing pieces:
   - scheduling across concurrent work items;
   - intent conflicts between tickets;
   - invalidating another ticket's investigation;
   - merge queues;
   - lock or claim granularity.
4. **Emergency path.** No member defines an incident hotfix lane (compressed stages, deferred verification with a mandatory follow-up, tighter exposure limits). Under pressure, people will route around a lifecycle that has none.
5. **Agent and model versioning in provenance and trust.** Trust tiers are earned by a specific agent and model configuration. None says that a model, prompt or toolchain change should reset or re-sample trust, or that provenance must record which agent version produced and reviewed each change.
6. **Long-horizon codebase health.** Each change can be locally correct while the architecture drifts. There is no mechanism for cross-change design review, entropy or tech-debt budgets, or periodic architecture checks of agent-authored code.
7. **Human skill erosion.** F raises it; nobody answers it. Candidates: rotating deep reads, required human authorship of a share of specs, and agent-maintained, human-reviewed architecture notes.
8. **Metrics for the lifecycle itself.** Only F's sampling measures anything. Missing: SLOs for escaped-defect rate, false-escalation rate, cost per change class, time spent in WAITING, and how often the human gates catch something real. Without these, budgets and thresholds can't be tuned.
9. **Data handling toward model providers.** S and A filter secrets from evidence. None addresses what code or data may enter model context at all (residency, licence, PII), which is a precondition for admission.
10. **Authorized but harmful requests.** Authority checks confirm the requester's identity, not that the requested change is benign (an insider asking for a backdoor). The independent challenge should include a "does this weaken security posture?" check that can't be waived by the requester.

---

## 7. Pros and cons per member

**Fable 5.1**
- **Pros**
  - The most operational mechanisms: failing-first acceptance tests, mutation score, diff-hash stuck detection, Goodhart guards, a trace-blind reviewer, capability-level irreversibility tags, rollback rehearsed in the same run.
  - The only real trust-governance loop: calibration sampling that adapts per class and serves as the only graduation route, plus learning extraction.
  - The most candid open questions (the classifier is load-bearing, skill erosion, concurrency), each tied to a specific stage.
- **Cons**
  - Thinner crash semantics: no lease fencing and no reconciliation of unknown external outcomes; concurrency is declared out of scope.
  - The fast path depends on one request-text classifier, a single point of failure F itself admits.
  - Automatic rollback ignores the harm rollback can do to stateful changes, and G2 categories are hard-coded rather than delegable.

**GPT-6.1 Sol**
- **Pros**
  - An explicit controller/agent split whose enforcement doesn't depend on agent cooperation. It is the architectural backbone the others need.
  - The best evidence model: dependency-based invalidation and approvals scoped to artifact, destination and expiry.
  - The strongest crash and external-action semantics: five-step protocol, generation fencing, a failure-class table, reserved recovery budget, freeze-on-ambiguity.
- **Cons**
  - Abstract: few concrete thresholds and no mechanism for test adequacy (nothing like mutation testing or failing-first).
  - No learning or trust-calibration loop, so autonomy levels have no evidence-driven way to change.
  - Twelve stages with no defined fast path ("may be combined" leaves tiering unspecified).

**GPT-6 Astra**
- **Pros**
  - The most usable record formats: the six-part work record, the acceptance-predicate format, the informative-retry record.
  - Precise outcome semantics: REVERTED versus COMPLETED, "delivered; outcome pending", execution modes kept separate from stages.
  - A clear recovery taxonomy (reversal, compensation, forward repair, containment) and the sound "evidence diversity over reviewer count" principle.
- **Cons**
  - Merges verification and independent challenge, weakening generation/acceptance separation in the stage structure itself.
  - Overlaps heavily with Sol, so it adds limited independent signal, and has little on who writes tests or how their strength is measured.
  - Trust expansion is one sentence, with no sampling or measurement mechanism.

**Overall:** there is no single winner. **Fable** has the best inner loop and trust governance. **Sol** has the best control plane. **Astra** has the best records and outcome vocabulary. If one report had to be the base, Fable's is the most directly implementable. It needs Sol's controller, evidence invalidation and fencing to be safe at scale.