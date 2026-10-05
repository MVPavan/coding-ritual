# Judgment: Member D against consolidation-v1

**Note on independence.** Of the three original members, D is closest to F. Both have failing-first frozen acceptance tests, mutation score on changed code, diff and failure fingerprints, audit sampling, learning loops, risk tiers and the same human-gate pattern (spec gate, irreversibility gate). Where D and F agree, I count it as less than two independent votes. D's structure is its own, though. It ships small increments that merge with the behaviour switched off ("dark"), separates merging from exposure, and gives concrete numbers for loop control. Those parts are judged on their merits.

Abbreviations: F, S, A as in v1; **D** = Member D.

---

## 1. Member D's position

- **Thesis.** "A delivered result is a change plus the evidence that it is correct," and every piece of that evidence is produced or checked by something other than the author. There are nine principles. The distinctive ones:
  - **P4:** autonomy scales with reversibility × blast radius.
  - **P5:** ship small, dark, reversible increments that merge with behaviour off and are ramped by a feature flag.
  - **P9:** an agent that can loosen its own limits has no limits.
- **Stages (0–10).**
  - Intake → **Ground** → **Specify** → Plan → [Implement → Verify → Review → Integrate]×increments → Release → Observe → Close & Learn.
  - D grounds before it specifies (S's order).
  - Specify outputs a **frozen, hash-locked acceptance suite** that must fail on the base commit. This happens *before* Plan and before the human spec gate.
- **Increment DAG.** Plan outputs a DAG of increments. Each increment has allowed paths, checks, a budget, a rollback step and a flag design. An outer loop runs one increment at a time, and each one merges dark.
- **Four concrete risk tiers.** T0 docs/tests; T1 flagged product code; T2 auth, payments, data model, public APIs, concurrency; T3 irreversible. The final tier is **max(agent judgment, deterministic path rules)**. An unclear tier takes the higher one.
- **Human gates.**
  - H1 spec approval when the tier is T2 or above, or on value ambiguity.
  - H2 for T3 actions. The human sees a dry-run diff of effects, a snapshot reference and a blast-radius statement.
  - H3 escalation, H4 5% audit sampling of T0/T1, H5 ownership of all guardrails.
  - Gates time out to **parked**. **Approval rate and review time are monitored to detect rubber-stamping.**
- **Concrete loop control.**
  - Budgets nest: request → stage → increment → attempt.
  - At 80%, the agent must compress context, re-plan, or justify continuing. At 100%, a hard stop.
  - If the Plan's estimate exceeds 2× the Intake budget, escalate before spending.
  - Each loop has a monotonic progress metric; two strikes means re-plan.
  - Fingerprint k=3, A→B→A oscillation detection, back-edge caps of 3, three integration failures → escalate.
- **Evidence integrity.**
  - Verify runs on a **clean environment from the committed patch**, not the agent's workspace.
  - Flaky tests are quarantined only with evidence of nondeterminism on the base commit, **never by the author**.
  - Bugs need a **3/3 deterministic reproduction**, and no unreproduced bug gets "fixed".
  - The reviewer sees test-file changes first and the author's explanation only later.
  - **Each review finding must be verified before it can block.** Unverifiable findings are logged and don't block.
- **Irreversibility and injection.**
  - Action classes come from a registry, not from the model.
  - Irreversible actions run in two phases, plan → dry run → diff of effects → snapshot → H2 → execute → verify, and abort if the dry run and the real run diverge.
  - The contract step of an expand/contract migration is its own later work item.
  - **Taint tracking:** a privileged action whose justification depends on tainted text is denied.
- **Learning.**
  - Escapes become **regression evals for the agents themselves**.
  - Flag-removal items are scheduled at close.
  - D names its own uncertainties: misclassifying semantic risk; architectural drift with no steward; trust labels that arrive late and go stale when models change.

---

## 2. Where D stands vs consolidation-v1

| Element | consolidation-v1 | Member D | Relation |
|---|---|---|---|
| Thesis | F's inner loop on S's control plane with A's records | Change plus independently produced evidence | agrees |
| Intent vs grounding order | Draft intent → ground → freeze (D2) | Intake → Ground → Specify | contradicts mildly (S's order); doesn't address the bias argument |
| Bug reproduction | Capability in stage 5 | Gate in Ground: deterministic 3/3 repro; no fix without one | extends |
| **Acceptance-test timing** | Stage 5, *after* G1 and Plan, yet H1 "approves the contract and acceptance tests" | Inside Specify, frozen *before* H1 and Plan | **contradicts; D is right** (v1 is internally inconsistent) |
| Spec and plan critics | — | Critic agents gate Specify and Plan | D-only |
| Plan output | Steps with checks, file scope, recovery route | Increment DAG: per-increment scope, budget, rollback, flag | extends |
| Multi-increment outer loop | — | Integrate → next increment | D-only |
| Implement/Qualify loop | Retry record; same or growing failure set → 4 | Monotonic metric, two strikes; fingerprint k=3; oscillation; clean-env verify | extends |
| Independent challenge | Separate stage; fresh context; read-only; no reasoning trace; produce evidence | Separate; multi-lens; explanation "not first"; test changes shown first; **finding verification**; two reviewers at T2 | extends (finding verification); slightly weaker on trace blindness |
| Integrate | Conditional write; immutable artifact; provenance | Merge queue; merged dark | extends; artifact and provenance v1-only |
| Authorize stage | Stage 10; approval bound to artifact, destination, expiry | None; H2 inline for T3 | v1-only |
| Release | Bounded exposure; rollback rehearsed this run | Flag ramp internal → canary → % → full; rollback "pre-staged" | extends (flag); weaker (no rehearsal) |
| Breach handling | Always stop expansion; auto-rollback only if rehearsed and state-safe; else contain and escalate | Automatic rollback (flag off) | partly contradicts; flag-off is usually the state-safe case |
| Failure after promotion | Containment from reserve; repair as linked item | Release failure → same item back to Ground; Observe failure → new item | refines |
| Closure | Dispositions; owner handoff; creds revoked; learning as proposals | Report; flag-removal item; KB; **eval curation**; close failures never block | mixed: D-only eval curation and flag cleanup; v1-only handoff, revocation, dispositions |
| Controller | Explicit control plane | Deterministic control plane (ledger, governor, policy engine) | agrees |
| Crash semantics | 5-step protocol; **generation fencing**; unreconcilable → block replay | Event-sourced ledger; workspace rebuilt from (base, patches, env manifest); heartbeat leases; **re-validation on resume** | v1 stronger on fencing; D extends with re-validation and env manifest |
| Budgets | Root > stage; reserved recovery capacity; children draw on root | Request > stage > increment > attempt; 80/100%; 2× re-estimate; per-stage wall-clock | extends; reserve is v1-only |
| Stuck detection | Fingerprints, retry record, two replans → escalate | Plus oscillation and back-edge caps (3) | extends |
| Risk classification | Monotonic; re-derived from diff (judge) | T0–T3; max(agent, path rules); unclear → higher; scope check | agrees and extends (concrete tiers) |
| Irreversibility | Capability tags; unavailable before stage 10 | Action-class registry; two-phase execution with dry-run divergence abort | agrees and extends |
| Injection | Untrusted input is data; capabilities only from stage definitions | Plus taint tracking of justifications | extends (defence in depth only, see §4) |
| Evidence validity | Bound to hash; invalidated on dependency change; infrastructure error ≠ pass | Hash-checked frozen suite; clean env from committed patch | complementary; invalidation rules v1-only |
| Flakes | Quarantine ticket | Only with base-commit evidence, never by author | extends |
| G1 | Ambiguity or risk ≥ medium | T2+ or value ambiguity | agrees |
| G2 | Delegable per class after a clean sampling record | T3 never without H2 | contradicts (F's position) |
| H3 human acceptance judgment | Explicit touchpoint | "Explicit manual check" criteria only | v1-only (D partial) |
| Escalation format | Alternatives, evidence, recommendation, authority | Options, recommendation, evidence, cost; timeout parks | agrees |
| Calibration sampling | Per class; adaptive | T0/T1, 5% and rising | agrees; D narrower |
| Guardrail ownership | H0 plus "learnings go through the lifecycle" | H5: any change to tiers, gates, budgets, permissions, kill switch | agrees; D sharper |
| Gate-health metrics | — | Approval rate and review latency → detect rubber-stamping | D-only |
| Execution modes; dispositions | A's modes; REVERTED vs COMPLETED; "delivered; outcome pending" | — | v1-only |

---

## 3. What D adds

**Better than v1, independent of the gaps**

1. **It fixes an ordering bug in v1.** v1 places G1 at stage 3 and says the human "approves the contract and acceptance tests", but those tests are only written at stage 5, after G1 and after Plan. D freezes the suite inside Specify, so the human approves real tests. It also makes D3's write lock meaningful from the start. D admits the cost: a Plan→Specify back-edge that unfreezes the suite and re-approves at T2+. (→ D3 re-ruled.)
2. **Merge is separated from exposure (dark increments).** Integration risk (does it build and land?) and behavioural risk (is it right for users?) become separate stages. The cheapest rollback becomes a flag flip that doesn't touch artifacts. Large changes become sequences of individually verifiable increments. v1 has no multi-increment structure at all. (→ D6 and D7 refined.)
3. **Review findings must be verified.** A finding blocks only if it is reproduced or concretely argued. This is the only mechanism any member offers against reviewer-hallucination loops, a real way to waste budget that v1's "finding → 6 (≤M)" simply runs into a cap.
4. **Evidence is produced on a clean environment from the committed patch.** v1 binds evidence to an artifact hash but never says the evidence must *not* come from the agent's own workspace. A dirty workspace can make tests pass through local state the commit doesn't contain.
5. **The author cannot quarantine a flaky test.** v1's "flake → quarantine ticket" is an open route for gaming results: declare the failing test flaky. D requires evidence that the test is nondeterministic on the base commit.
6. **Concrete defaults for loop control:** 80%/100% budget lines, the 2× re-estimate rule, k=3, two strikes, back-edge caps of 3, oscillation detection, a 3/3 reproduction rule. v1 left these as N and M. D admits they are guesses, but defaults that can be tuned beat having none.
7. **Re-validation on resume.** Before continuing, the controller checks whether mainline, the request or the policy has changed, and if so goes back to the earliest affected stage. v1's evidence invalidation covers code dependencies but not a requester who edits the ticket while it is parked, or a policy tightened mid-run.
8. **The H2 package is defined, and irreversible actions run in two phases.** The human sees a dry-run diff of effects, a snapshot reference and a blast-radius statement. If the real run diverges from the dry run, it aborts. v1 only said what the approval is *bound to*, not what it is *about*.
9. **Gate-health telemetry.** A ~100% approval rate with short review times means the gate is rubber-stamped. That should lead to removing the gate or redesigning how it is presented. This turns "ritual review" (S/A's D1 argument) from rhetoric into something measured.

**Against v1 §6 gaps**

| v1 gap | D's contribution | Status |
|---|---|---|
| 1 Who writes the oracle | Tests are authored in Specify, before Plan and Implement, frozen, hash-checked, checked by a spec critic, and approved at H1. Separation is by stage, not an explicitly separate context. No back-translation; sampling covers merges, not contracts. | **Partially closed** |
| 2 Risk from the actual diff | max(agent, path rules), plus a Verify scope check that keeps the diff inside planned paths. This keeps the tier valid by construction. Semantic risk is admitted to be open (the retry-loop example). | **Mostly closed** (path risk); semantic risk open |
| 3 Multi-item coordination | Merge-queue participation and an increment DAG *within* one item. Nothing across items. | **Partially closed** (merge queue only) |
| 4 Emergency path | — | **Open** |
| 5 Agent/model versioning | Raises staleness of trust data under model change; eval curation provides a regression suite to re-run. The mechanism isn't connected. | **Partially closed** (judge connects it in v2) |
| 6 Long-horizon health | Flag-removal items; names an "architecture steward" but doesn't design it | **Partially closed** (flag debt only) |
| 7 Human skill erosion | — | **Open** |
| 8 Lifecycle metrics | Gate approval rate and latency; escape rate per tier; estimation calibrated against past outcomes | **Partially closed** |
| 9 Data to model providers | — | **Open** |
| 10 Authorized but harmful | T2 covers permission and auth surfaces; security review lens; taint tracking. Nothing requester-proof. | **Mostly open** |

---

## 4. Where D is weaker or wrong

1. **Leases without fencing.** D uses heartbeat leases only. A paused worker (GC stall, network partition) whose lease has expired can wake up and commit over its replacement. Heartbeats detect death; they don't stop zombies. v1's generation numbers (S) are necessary. D also gives no rule for an external outcome that *can't* be reconciled. v1's "block replay" stands.
2. **No reserved recovery budget.** A 100% hard stop during a flag ramp leaves the system half-exposed with no capacity left to roll back. v1's reserve-first rule (S, A) is strictly safer.
3. **Plan can raise its own budget.** Plan "replaces" the Intake budget with a bottom-up estimate and escalates only above 2×. So an agent-authored estimate can double its own allowance without a human, which breaks v1 agreement #3. Fix: the estimate may raise the working budget only up to a human-authored per-tier ceiling.
4. **Automatic rollback is under-conditioned.** "Pre-staged" is not "rehearsed". Flag-off is state-safe only if everything persisted while the flag was on stays readable by the old path. D's expand/contract rule usually guarantees this, but D never connects the two. D also has no freeze-on-ambiguous-signal. Observe-stage auto-revert depends on *agent* change attribution, and reverting code that later changes have built on can do harm. v1's D6 conditions stay, with flag-off added as the preferred state-safe route.
5. **Thin delivery and closure semantics.** D has no Authorize stage and no approval bound to artifact, destination and expiry, so a stale H2 could be replayed against a different build. Its dry-run divergence check covers this only partly. D also lacks dispositions, so "rolled back" and "succeeded" can blur, and has no ownership transfer or credential revocation. "A failure in Close never blocks delivery" is right for learning extraction and wrong for credential revocation.
6. **Taint tracking is weaker than presented.** Once the model reads an issue, all of its context is effectively tainted. A justification is model-authored text and can be laundered, so the rule either fires on everything or misses rephrased instructions. It is defence in depth. The primary control remains v1's "capabilities come only from stage definitions; registry-classed actions".
7. **Smaller points.**
   - The reviewer doesn't see the explanation "first", but does see it later. That is weaker than F's "never sees the reasoning trace", although showing commit rationale *after* initial findings are recorded is reasonable.
   - "Two independent reviewers agree" at T2 counts reviewers rather than diversifying evidence (A).
   - H4 samples only T0/T1, so T2 escapes are never measured.
   - Critic sign-offs at Specify and Plan add more same-model judgment without measuring it.
   - "Dark" assumes changes can be flagged. Dependency bumps, build configuration, infrastructure and migrations often can't. Even deploying dark code runs initialization and expand migrations in production.

---

## 5. Disputes re-ruled

| # | v1 ruling | Does D change it? | v2 ruling |
|---|---|---|---|
| D1 | G1 per F; G2 per S/A, with F's categories non-delegable by default | **Refined.** D argues for non-delegable T3 (no rollback by definition, no sense of external consequences), which v1 already granted as the default. D's gate-health metric argues for measuring rubber-stamping. | **[v2]** Stands. Merge D's T3 list into the non-delegable defaults (adds infrastructure teardown, credential/permission grants, external communications, licence). Gate-health telemetry is mandatory. For **non-delegable** classes, a rubber-stamped gate may only be *redesigned* (e.g. A's "answer a defined question"). For **delegable** classes, rubber-stamping plus a clean sampling record lets the owner (H0) delegate. Never automatic. G2's package is D's dry-run diff, snapshot reference and blast radius. |
| D2 | Two passes: draft intent → ground → freeze | **No.** D's order is S's and doesn't answer F/A's bias argument. D's bug-reproduction gate fits inside grounding. | Stands, plus **[v2]** D's split of ambiguity into technical (resolve by investigation, record the assumption) and value (G1). |
| D3 | Separate encode-acceptance stage after Plan; fails on baseline; write-locked | **Yes.** v1 has G1 approving tests that don't exist yet. D's placement fixes it, and acceptance tests belong at the contract level (black-box against surfaces in the contract), which is known after grounding. | **[v2]** Acceptance encoding **merges into the contract stage (new stage 3), before G1 and Plan**. The tests are authored in a worker context separate from any later implementer, fail on baseline, then are hash-locked. Surfaces created by Plan get criteria through a Plan→Specify back-edge that re-freezes the suite and repeats G1 if G1 applied. Untestable criteria become A-format predicates or H3 judgments, never silent. |
| D4 | Separate stage; fresh context; evidence-producing; sampling mandatory | **Extended.** | **[v2]** Add finding verification (D). Unverified findings don't block at T0/T1 and raise the item's sampling priority. At T2+, an unverified finding in the security, data-loss or concurrency lenses blocks until a second reviewer of different lineage refutes it *with evidence*, or H4 decides (judge). D's two-reviewer rule is kept only if the reviewers differ in lineage *and* lens (A). Test-file changes are shown first (D). The reasoning trace is never shown; commit rationale is shown only after initial findings are recorded (F + D). |
| D5 | Collapsible obligations; challenge replaced only with diff-derived risk | **Refined.** | **[v2]** Fast path = tier T0. Tier = max(agent, path rules) at stages 0 and 3 (D), re-derived from the actual diff at 6 and 8 (judge), and kept valid by the scope check (D). Monotonic: raise only. |
| D6 | Stop expansion always; auto-rollback only if rehearsed and state-safe | **Refined.** Dark launch makes the state-safe case the normal one. | **[v2]** Stopping expansion is always automatic. **Auto flag-off** is allowed when the change is flag-gated, every persisted-state change is still in the expand phase, and flag-off was rehearsed in pre-prod this run (cheap). Artifact rollback keeps v1's conditions. Ambiguous signals freeze (S). Observe-stage revert by agent attribution needs the same state-safety test; otherwise contain and escalate. |
| D7 | Containment from reserve; repair as linked item | **Refined.** D separates failure during the ramp from failure after delivery. | **[v2]** If the breach happens **during the ramp** and harm stayed within the item's exposure budget, the item is not yet delivered. Flag off, then back-edge to stage 2 *in the same item* with production evidence, drawing on the remaining root budget and counted against the back-edge cap (D, S/A). Breaches after delivery, or harm beyond the exposure budget, become a linked incident item funded by incident policy (v1). |
| D8 | Explicit controller | Agrees. | Stands, plus **[v2]** action-class registry (D = F's tags), two-phase irreversible execution, re-validation on resume. |
| D9 | Learning and ownership transfer both kept | **Extended.** | **[v2]** Learning includes **eval curation** (D). The eval set doubles as the regression gate for agent-configuration changes (judge, closing gap 5 in part). Close obligations split: handoff and revocation *block* closure (S/A); learning failures don't (D). |

---

## 6. Final consolidated lifecycle (v2)

**Thesis.** This is v1's synthesis: F's inner loop and trust governance, run on S's control plane, using A's record formats. **[v2]** It adds D's delivery structure (small increments merged dark, then ramped by flag) and D's evidence-integrity and loop-control defaults.

### 6.1 Diagram

```
CONTROLLER RAILS — every stage; enforced by trusted machinery, not agent goodwill          [S,A; F,D]
  • Budget ledger: root > stage > increment > attempt; recovery reserve set aside first     [F,S,A; [v2] D nesting]
      [v2] 80% → compress / replan / justify; 100% → WAITING (reserve untouched)            [D; reserve S,A]
      [v2] plan estimate may raise budget only to the policy ceiling for the tier;
           > 2× admitted budget → escalate before spending                                  [D + judge]
  • Event-sourced journal; 5-step stage protocol; leases WITH generation fencing             [S,A,D; fencing S]
  • [v2] Re-validate on resume: mainline / request / policy / agent-config changed?
         → earliest affected stage                                                          [D + judge]
  • Evidence ledger: bound to artifact hash, produced on a CLEAN env from the
    committed patch [v2 D]; invalidated on dependency change; infra error ≠ pass             [S,A,D]
  • Action-class registry (read | sandbox-write | shared-reversible | irreversible)
    → per-stage short-lived creds; irreversible unavailable before stage 9                  [F,D]
  • Protected store: policy, verifier config, frozen acceptance suite (hash-checked)         [S; D]
  • Untrusted input = data; [v2] taint marks on untrusted sources (defence in depth)         [all; D]
  • Stuck detection: (diff, failure) fingerprints k=3; [v2] A→B→A oscillation;
    monotonic progress metric per loop (2 strikes → replan); back-edge caps (default 3)     [F,A; [v2] D]
  • Risk tier T0–T3 = max(agent, path rules); raise-only; re-derived from actual diff        [[v2] D tiers; F; judge]
  • [v2] Gate-health telemetry: approval rate, review latency, catches per gate              [D]
  • Kill switch · escalation channel · provenance incl. [v2] agent/model/prompt version      [F,D; judge]
  • Execution modes: RUNNING | WAITING | RECOVERING | STOPPED | TERMINAL                     [A]

request
  │
  ▼
[0 ADMIT & BOUND] ── unauthorized / duplicate / prohibited ──► REJECTED (reason recorded)
  │  tier (unclear → higher), envelope, root budget + reserve, discovery allowance
  ▼
[1 DRAFT INTENT] ◄──────────────────────────────────────────────────────┐
  │  outcome, non-goals, open questions; ambiguity typed technical | value │ spec wrong / infeasible
  ▼                                                                      │
[2 GROUND & BASELINE] ── bug not reproducible 3/3 ──► telemetry / ask ──► H4
  │  dossier, baseline failures, env manifest, deterministic repro [v2 D] │
  ▼                                                                      │
[3 SPECIFY & ENCODE ACCEPTANCE]  [v2: v1 stages 3+5 merged — D]          │
  │  contract + acceptance suite: fails on baseline → hash-locked         │
  │  spec critic; back-translation at T2+ [v2 judge]                      │
  ╞══ G1 (tier ≥ T2 OR value ambiguity): contract + REAL tests ══╡        │◄── spec dispute (7)
  ▼                                                                      │◄── new surface needs criteria (4)
[4 PLAN → INCREMENT DAG] [v2 D] ◄─────────────────────────┐              │     (re-freeze; re-G1 if applied)
  │  per increment: paths, checks, budget, rollback, flag   │
  ▼                                                         │ 2 strikes / fingerprint×3 /
 ┌─►[5 IMPLEMENT] ◄───────────┐                             │ oscillation / design finding /
 │     ▼                      │ red, progress improving     │ finding survives 2 rounds
 │  [6 QUALIFY] ──────────────┘─────────────────────────────┤
 │     ▼  clean env · frozen-suite hash · integrity · scope · mutation · tier re-derived
 │  [7 INDEPENDENT CHALLENGE] ─ confirmed code finding → 5 (≤3) ─ design → 4 ─ spec → 3
 │     ▼  findings must be verified to block [v2 D]
 │  [8 INTEGRATE — MERGE DARK] [v2 D] ─ mainline moved → 6 · semantic conflict → 5
 │     │                                 broken assumption → 2 · 3 failures → H4
 └──── more increments ──┤
                         ▼
[9 AUTHORIZE] ══ G2 if outside delegation or non-delegable class ══
  │  approval bound to artifact + destination + expiry; dry-run effect diff,
  │  snapshot ref, blast radius [v2 D]; stale → refresh evidence
  ▼
[10 RELEASE, BOUNDED EXPOSURE] [v2 D]
  │  (a) promote artifact dark through deploy canary
  │  (b) ramp flag: internal → canary → % → full, each step baseline-gated
  │  unflaggable changes: artifact canary + rehearsed rollback
  │── breach ──► STOP EXPANSION ──► flag-gated ∧ expand-phase ∧ flag-off rehearsed?
  │                 ├─ yes ─► FLAG OFF ─► harm ≤ exposure budget? ─ yes ─► back to 2, same item [v2 D7]
  │                 │                                              └ no ─► linked incident item at 0
  │                 └─ no ─► rehearsed & stateless? ─ yes ─► ROLLBACK ─┘
  │                                                └ no ─► CONTAIN + ESCALATE (H4)
  │── ambiguous signal ──► FREEZE + ESCALATE                                   [S]
  ▼
[11 OBSERVE] soak scaled to tier [v2 D] ── attributable regression ─► same state-safety test
  │                                                     ─► linked repair item at 0
  ▼
[12 CLOSE, TRANSFER, LEARN]
     ──► disposition (COMPLETED | REVERTED | DELIVERED-OUTCOME-PENDING | FAILED …)   [A]
     ──► owner handoff · creds revoked (these BLOCK closure)                         [S,A; v2 split]
     ──► report with residual risks · flag-removal item [v2 D]
     ──► learnings, KB and eval cases [v2 D] as proposals → H0 (non-blocking)
     ──► calibration sample (merges AND contracts [v2 judge]) → H5 → trust tier per class

ANY STAGE: budget at reserve │ stuck │ authority missing │ policy deny │ kill switch
     ──► WAITING (state frozen, resumable; gate timeout PARKS, never approves) ──► H4
```

### 6.2 Stage table

| # | Stage | Goal | Capabilities | Exit criterion | Failure path | Source |
|---|---|---|---|---|---|---|
| 0 | Admit & bound | Decide whether and how work may begin | Request classification; duplicate detection; tiering = max(agent, path rules) **[v2]**; authority check; budget estimation | Authorized; tier; envelope; root budget with reserve; discovery allowance | Reject with reason; unclear tier → higher tier **[v2 D]**; unintelligible → one consolidated question **[v2 D]**; wait for authority | F, S, A, D |
| 1 | Draft intent | Capture the outcome before work biases it | Intent interpretation; ambiguity detection **with typing as technical or value [v2 D]**; non-goal articulation | Outcome, non-goals, open questions recorded | Ask; no answer within SLA → park | F, A, D |
| 2 | Ground & baseline | Know the real system and prove the problem exists | Navigation; call-graph and impact analysis; history archaeology; runtime probing; **hermetic env provisioning with manifest [v2 D]**; baseline characterization; provenance assessment; **deterministic bug reproduction (3/3) [v2 D]** | Dossier complete against a checklist; existing failures characterized; workspace = (base, patches, env manifest); for bugs, a deterministic repro | Spec wrong → 1; can't reproduce → telemetry or specific questions → H4; **an unreproduced bug is never "fixed"**, only reclassified as hardening with predicates checked at Observe **[v2 D + judge]** | F, S, A, D |
| 3 | **[v2]** Specify & encode acceptance | A checkable, executable contract before design | Acceptance design (A-format predicates); **acceptance-test authoring in a context separate from the implementer [v2 judge]**; property tests; fixtures; **spec critique [v2 D]**; **back-translation at T2+ [v2 judge]**; final tiering | Each criterion → executable check, predicate, or explicit H3 judgment; tests fail on baseline for the expected reason (or are justified as vacuous for non-functional work); suite hash-locked; critic finds nothing untestable or contradictory; G1 passed if triggered | Technical ambiguity → investigate (2) and record the assumption; value ambiguity → G1 with 2–3 options; untestable → predicate, narrow, or decline | F (G1, failing-first), S (protection, proof limits), A (predicates), **D (placement before G1 and Plan)** |
| 4 | **[v2]** Plan → increment DAG | A feasible, recoverable route in verifiable slices | Decomposition into increments **[v2 D]**; alternatives; feasibility experiments; verification-strategy design; expand/contract migration design; **flag design [v2 D]**; rollback design; action classification via registry; **plan critique [v2 D]**; calibrated estimation | Each increment has paths, checks, budget, rollback, flag; the contract step of any migration is a separate later item **[v2 D]**; estimate ≤ policy ceiling for the tier | Infeasible → 3 (unfreeze → re-freeze → re-G1 if it applied); estimate > 2× admitted → H4 before spending **[v2 D]**; tier raised → G1 | F, S, A, D |
| 5 | Implement (per increment) | Smallest in-scope change that satisfies the increment | Code editing; refactoring; build; dependency management (supply-chain and licence checks); migration authoring; **non-frozen** test writing; debugging | Increment complete; diff within planned paths; checkpoint after each commit **[v2 D]** | Red → retry with a retry record; out of scope → 4; environment fault → resume from checkpoint **[v2 D]** | F, A, D |
| 6 | Qualify | Evidence bound to the exact candidate | Test execution **on a clean env from the committed patch [v2 D]**; frozen-suite hash check; integrity audit; scope check; flake discrimination; differential diagnosis; static, security and performance analysis; mutation testing on changed lines | All required checks green; mutation threshold met; infra errors give no verdict; tier re-derived from the diff | Defect → 5 with diagnosis; **progress metric (failing checks) not strictly improving twice → 4; fingerprint ×3 or oscillation → 4 [v2 D]**; flake quarantine **only with base-commit nondeterminism evidence, never by the author [v2 D]**; weak evaluation method → 3 | F, S, A, D |
| 7 | Independent challenge | Find what tests and implementer can't see | Fresh-context, read-only, trace-blind review; **test-file changes shown first [v2 D]**; multi-lens (correctness, security, conformance, maintainability) **[v2 D]**, including a **non-waivable "weakens security posture?" lens [v2 judge]**; counterexample search; invariant and reference checks; **finding verification [v2 D]** | No *confirmed* blocking findings; Goodhart flags resolved; at T2, two reviewers of different lineage and lens **[v2 D+A]** | Confirmed code finding → 5 (≤3); design → 4; survives 2 rounds → 4; spec dispute → 3; **unverified: logged and non-blocking at T0/T1 (raises sampling priority); at T2+ in security, data-loss or concurrency lenses, blocks until refuted with evidence or H4 decides [v2 D + judge]** | F, S, A, D |
| 8 | **[v2]** Integrate (merge dark) | Land each increment safely with behaviour off | Rebase and semantic conflict resolution; **merge-queue participation [v2 D]**; requalification on the merge result; conditional write; immutable artifact build; provenance incl. agent config **[v2 judge]** | Merged with behaviour off; re-verified merge result green; merge commit journaled; next increment → 5 | Drift → 6; semantic conflict → 5; broken assumption → 2; **3 failures → H4 [v2 D]** | All; S (conditional writes); D (dark, merge queue) |
| 9 | Authorize | Confirm authority and evidence for this artifact and destination | Policy evaluation [ctl]; evidence-freshness check; **dry-run effect diffing [v2 D]**; decision preparation | Authority confirmed; G2 passed if required; approval bound to artifact, destination, expiry | Stale → refresh; wait; non-waivable failure → deny | A, S, F, D |
| 10 | **[v2]** Release, bounded exposure | Expose behaviour gradually without irreversible harm | Artifact promotion through the deploy canary; **flag management and ramp [v2 D]**; baseline health comparison; **two-phase execution of T3 actions (dry run → snapshot → G2 → execute → verify post-state; divergence aborts) [v2 D]**; receipt capture; reconciliation | Flag-off or rollback rehearsed in pre-prod this run; every ramp step green to full, or the item is defined as flag-off delivery **[v2 D]**; receipts journaled | Breach → stop expansion → D6/D7 tree; unknown result → reconcile, block replay if unreconcilable; ambiguous signal → freeze and escalate | F, S, A, D |
| 11 | Observe | Confirm the contracted outcome | Canary and baseline comparison; anomaly detection; **change attribution [v2 D]**; outcome-predicate evaluation | Predicates hold for the soak window, **scaled to tier [v2 D]**; or "delivered; outcome pending" with a named owner | Attributable regression → stop; flag-off or revert only if state-safe, otherwise contain and escalate; linked repair item | S, A, F, D |
| 12 | Close, transfer, learn | Accountable result; better future runs | Evidence synthesis; requester report with residual risks **[v2 D]**; ownership handoff; credential and resource cleanup; **flag-removal scheduling [v2 D]**; retrospective; **knowledge curation and eval curation [v2 D]** | Disposition recorded; owners assigned; creds revoked; flag-removal item filed; learnings and evals filed as proposals | Missing owner or unrevoked creds → item stays open (blocking); **learning-extraction failure → logged, non-blocking [v2 split S/A + D]** | S, A, F, D |

**Fast path [v2: tier-driven].** T0 (docs, tests, internal tooling by path rule) collapses stages 1–4 into one execution with a single increment. G1 never fires. Stage 7 is replaced by deterministic scope and integrity checks, with a higher sampling rate. Release needs no flag where no runtime behaviour changes. If the tier re-derived from the diff exceeds T0, the full path resumes. (D, judge)

### 6.3 Human touchpoints

| ID | When | What the human decides | Why it stays human | Source |
|---|---|---|---|---|
| H0 | Standing, and on **any proposed change to guardrails [v2]** | Tiers and path rules, budgets and per-tier ceilings, non-delegable classes, rollback thresholds, permissions, kill-switch policy, frozen-suite rules; accepts or rejects learning proposals and delegation requests | An agent that can loosen its own limits has none | F, S, A, **D (H5 → merged here)** |
| H1 (G1) | Stage 3, when the tier is T2+ or there is value ambiguity | Approves the contract **and the frozen acceptance suite, which now exists at gate time [v2]**; chooses among 2–3 options for value questions | Every later check verifies against this; it doesn't depend on the agent noticing its own misreading | F, D, S/A |
| H2 (G2) | Stage 9 or 10 (or recovery), when outside delegation or in a non-delegable class: auth, crypto, billing, destructive data, public contracts, spend, legal, **infrastructure teardown, credential or permission grants, external communications, licence [v2 D]** | Approves one artifact, destination and expiry, **based on the dry-run effect diff, snapshot reference and blast-radius statement [v2 D]** | Irreversible consequences need an accountable person. Delegable classes only after a clean sampling record *and* an H0 decision | F, S/A, D |
| H3 | Stage 3 or 11, when the contract requires human judgment | Supplies the acceptance judgment | No adequate oracle | S, A |
| H4 | Any stage: budget at reserve, stuck, policy deny, can't reproduce, estimate > 2×, recovery beyond mandate, **unverified T2+ security finding [v2]** | Extend, narrow, answer, abandon, or choose among losses | The system has shown it can't settle it | F, S, A, D |
| H5 | Continuously, sampled | Labels a random sample of autonomous merges **per tier including T2, plus a sample of frozen contracts [v2 judge]**; moves trust tiers | The only empirical measure of verifier and oracle miss rates | F, D |

**Gate design rules [v2 D, with judge refinements]:**
- Every gate presents a decision (options, recommendation, evidence, cost), never a diff dump.
- Timeouts **park**, never approve.
- Approval rate, review latency and real catches are tracked per gate. A rubber-stamped *delegable* gate leads to a delegation proposal to H0. A rubber-stamped *non-delegable* gate leads only to a redesign of how it is presented (A: "answer a defined question").

No routine pre-merge human diff review (all four members agree).

### 6.4 Safety and recovery

**Cost and time**
- Multi-currency budgets nested root → stage → increment → attempt **[v2 D]**. Children and back-edges draw on the root (S, A).
- The recovery reserve is set aside first (S, A).
- **[v2 D]** At 80%: compress, replan or justify. At 100%: WAITING, with the reserve still available for containment.
- **[v2 D + judge]** The plan estimate can raise the budget only to the policy ceiling for the tier; more than 2× the admitted budget → H4.
- Per-stage wall-clock limits **[v2 D]**. Exhaustion is a clean exit (F).

**Runaway loops**
- Fingerprints of (diff, failure set) (F, D), with k=3 as the default **[v2 D]**.
- **[v2 D]** A monotonic progress metric per loop (failing checks / open confirmed findings / conflicts); two strikes → replan; a failed replan → escalate.
- **[v2 D]** A→B→A oscillation detection.
- Back-edge caps, default 3 **[v2 D]**.
- Every retry needs an informative-retry record (A); a heartbeat is not progress (A).
- Finding verification stops loops on hallucinated review findings **[v2 D]**.
- Goodhart guards (F), a hash-checked frozen suite (D), the author can't quarantine flakes **[v2 D]**.

**Crash and interruption**
- 5-step stage protocol (S).
- Event-sourced journal (D, S); the workspace is rebuilt from (base, patches, **env manifest [v2 D]**), never trusted as found.
- Leases with **generation fencing** (S, A); D's heartbeats are for liveness only.
- **[v2 D + judge]** On resume, re-validate mainline, request, policy and agent configuration → earliest affected stage.
- Kill switch halts at a journal boundary, and the policy engine refuses privileged actions while it is set (F, D).

**External effects**
- Intent → receipt (A, D); idempotency keys and conditional writes (F, S).
- Unknown outcome → query the destination; if unreconcilable, block replay (S, A).

**Irreversibility**
- Action-class registry (F, D); irreversible actions unavailable before stage 9.
- No production credentials in stages 0–8; the reviewer is read-only; egress is allow-listed.
- **[v2 D]** Two-phase execution with dry-run divergence abort.
- Expand/contract, with the contract step as a separate later work item **[v2 D]**.
- **[v2 D]** Dark merge plus flag ramp, so the default rollback is a flag-off rehearsed this run.
- Recovery menu: reversal, compensation, forward repair, containment (A).
- Ambiguous signal → freeze (S).

**Evidence integrity**
- Bound to hash, invalidated on dependency change (S, A).
- **Clean env from the committed patch [v2 D]**.
- Infrastructure error ≠ pass (S).

**Injection**
- Capabilities come only from stage definitions (all).
- **[v2 D]** Taint marking as defence in depth: a privileged action whose plan step cites only tainted sources is denied and escalated.

**Reporting**
- A's dispositions: rollback success ≠ change success.
- A requester report with residual risks **[v2 D]**.

### 6.5 Capability catalogue

**[ctl]** = deterministic controller machinery, not agent judgment.

| Group | Capability | Purpose | Source |
|---|---|---|---|
| **Intent & authority** | Request classification; duplicate detection | Type, urgency, prior duplicates | F, D |
| | Risk tiering T0–T3: max(agent, path rules), monotonic, diff-rederived **[v2]** | Blast radius and reversibility class | F, D, judge |
| | Authority assessment [ctl] | Which actions are permitted on which resources | S, A |
| | Ambiguity detection **and typing (technical / value) [v2]** | Find gaps; route to investigation or the human | F, A, D |
| | Requirement elicitation; decision preparation | Few decision-ready questions with options and cost | S, A, D |
| | Acceptance design (predicate form); non-goal articulation | Observable success and explicit exclusions | F, S, A |
| | **Spec critique [v2]** | Adversarially find untestable or contradictory criteria | D |
| | **Back-translation [v2]** | Restate the spec from the tests alone; diff against the contract (T2+) | judge |
| **Understanding** | Code navigation; call-graph and impact analysis | Locate code and blast radius | all |
| | History archaeology; convention extraction | Why the code is the way it is; local idioms | F, D |
| | Runtime introspection; baseline characterization | Ground claims about real behaviour | all |
| | **Deterministic bug reproduction [v2 moved here]** | No fix without a 3/3 failing repro | F, D |
| | Source-provenance assessment | Authoritative vs stale or untrusted sources | A |
| | **Hermetic environment provisioning [v2]** | Reproducible workspace from a manifest | D |
| **Planning** | **Increment decomposition (DAG) [v2]** | Independently mergeable, verifiable slices | D, F, S, A |
| | Alternatives; feasibility experiments | Resolve key uncertainty cheaply | F, A |
| | Verification-strategy design | Which evidence proves each increment | F, A, D |
| | Migration (expand/contract), **flag design [v2]**, rollback design | The undo before the change | all; flags D |
| | **Plan critique [v2]** | Independent feasibility, scope and risk check | D |
| | Estimation calibrated against past outcomes **[v2]** | Forecast within the tier ceiling | F, A, D |
| **Construction** | Code and config editing; refactoring | Minimal, convention-matching change | all |
| | Build; dependency management with supply-chain and licence checks | Package and control third-party risk | F, A, D |
| | Migration authoring | Expand/contract persisted-state changes | F, S, D |
| | Debugging from failure output | Failure → cause → testable hypothesis | F, A, D |
| **Verification** | Acceptance-test authoring (separate context), property tests, fixtures | Failing-first executable criteria | F, A, D, judge |
| | Test execution **on a clean env [v2]**; flake discrimination | Trustworthy runs; nondeterminism vs regression | F, D |
| | Differential diagnosis | Candidate vs baseline vs environment vs bad assumption | S |
| | Mutation testing on changed lines | Do the tests constrain the change? | F, D |
| | Static, security, performance (with significance) and compatibility analysis | Non-functional evidence | all |
| | Test-integrity auditing [ctl] | Deleted, skipped, loosened or special-cased checks | F, D |
| | Evidence appraisal; invalidation [ctl-assisted] | Which claims still stand | S, A |
| **Independent challenge** | Multi-lens adversarial review **incl. non-waivable security-posture lens [v2]** | Correctness, security, conformance, maintainability | F, D, judge |
| | **Finding verification [v2]** | Reproduce or refute each finding before it blocks | D |
| | Counterexample search; invariant and reference checks | New evidence, not opinion | F, A |
| | Change explanation | For reviewers and requesters | F, D |
| **Integration & delivery** | Rebase and conflict resolution; requalification | Land on a moving mainline | all |
| | **Merge-queue participation [v2]** | Serialize landing; verify the merge result | D |
| | Immutable artifact construction; provenance incl. agent config **[v2]** | Tie what ships to source, inputs, evidence, producer | S, A, judge |
| | **Flag management and ramp control [v2]** | Expose behaviour stepwise; flag-off as rollback | D |
| | Promotion; canary and baseline health evaluation | Bounded exposure against baseline | all |
| | **Dry-run effect diffing; two-phase execution [v2]** | Make irreversible effects visible and checkable | D |
| | External-state reconciliation [ctl] | Settle unknown outcomes before retry | S, A, D |
| | Rollback, revert, compensation, forward repair | Restore or mitigate, and verify the undo | F, A, D |
| | **Change attribution [v2]**; incident diagnosis and containment | Link regressions to changes; limit harm | D, S, A |
| **Control & continuity [ctl]** | Event-sourced journaling; 5-step protocol | Authoritative state outside agents | all |
| | Budget governor (nested, thresholds, ceilings) **[v2]** | Enforce limits without agent cooperation | all, D |
| | Progress and stall detection (fingerprints, **strikes, oscillation, back-edge caps [v2]**) | Stop cycling work | F, A, D |
| | Leasing with generation fencing | Fence out stale workers | S, A |
| | **Resume re-validation [v2]** | Detect mainline, request, policy or config drift | D, judge |
| | Policy engine; action-class registry; least-privilege credentials | Gate capabilities by class | F, S, A, D |
| | Untrusted-input handling; **taint marking [v2]**; secret filtering | Content never acquires authority | all, D |
| | **Gate-health telemetry [v2]** | Detect rubber-stamped or useless gates | D |
| | Kill switch | Global or per-item halt at a consistent boundary | F, D |
| **Closure & learning** | Closeout; ownership handoff; cleanup and revocation | Accountable result; no lingering privilege | S, A |
| | **Flag-removal scheduling [v2]** | Stop flag debt from accumulating | D |
| | Retrospective; knowledge curation | Better grounding next time | F, D |
| | **Eval curation [v2]** | Escapes → regression evals for the agents; the gate for agent-config changes | D, judge |
| | Calibration-sample selection [ctl] (merges **and contracts [v2]**) | Measure escape rates; move trust tiers | F, D, judge |

### 6.6 Remaining gaps

1. **Oracle quality (partially closed [v2]).** Tests are now stage-separated and frozen before G1, checked by a critic, back-translated at T2+, and contracts are sampled. Still open: spec author and implementer may share one model family's blind spots. Back-translation has never been tested in practice.
2. **Semantic risk misclassification (open, D).** Path rules plus diff re-derivation catch *where* a change lands, not *what it does* (D's retry loop that amplifies load). One candidate: behavioural-surface detectors (retry, timeout, concurrency and caching primitives) as path-like rules.
3. **Multi-item coordination (partial).** Merge queue and increment DAG exist. Still missing: cross-item intent conflicts, invalidating another item's grounding, scheduling, and claim granularity.
4. **Emergency lane (open).** No compressed hotfix path with deferred verification and a mandatory follow-up.
5. **Agent versioning (partial [v2]).** Provenance records the agent configuration. A configuration change → eval-set replay plus a raised sampling rate until the class's record is re-established (judge, built on D). Still open: escape labels arrive months late (D), so trust may be computed from a configuration that no longer exists.
6. **Long-horizon health (partial).** Flag-removal items exist; the "architecture steward" both D and v1 call for is still undesigned.
7. **Human skill erosion (open).**
8. **Lifecycle metrics (partial [v2]).** Gate health and per-tier escape rates exist. Still missing: SLOs for false-escalation rate, time in WAITING and cost per tier, and a tuning loop for D's default thresholds (80%, 2×, k=3, caps of 3), which D admits are guesses.
9. **Data admissibility toward model providers (open).**
10. **Authorized but harmful requests (partial [v2]).** The non-waivable security-posture lens has been added but is untested. It is still model judgment.
11. **[v2 new] Changes that don't decompose (open, D).** Framework upgrades and cross-cutting refactors resist small increments. One candidate: mechanical transformations with differential or equivalence testing in place of increment-level review.
12. **[v2 new] Dark-code risk and flag combinatorics (open).** Deploying "dark" code still runs initialization and expand migrations. Interacting flags create untested states. Some changes can't be flagged at all.

---

## 7. Pros and cons of Member D

**Pros**
1. **Fixes a real flaw in v1.** Freezing acceptance tests inside Specify means the human spec gate reviews real tests, and the write lock holds from the start. D also states the cost honestly (the unfreeze back-edge).
2. **A delivery architecture the others lack.** Small increments merged dark and ramped by flag separate integration risk from behavioural risk. They make the common rollback a cheap, state-safe flag flip and give large changes a verifiable structure.
3. **The most implementable evidence integrity and loop control.** Clean-env verification from the committed patch, author-proof flake quarantine, findings that must be verified to block, deterministic reproduction, gate-health telemetry, and concrete defaults (80/100%, 2×, k=3, two strikes, caps of 3, oscillation detection).

**Cons**
1. **Weaker crash and budget safety than v1.** Heartbeat leases without generation fencing, no rule for unreconcilable outcomes, no reserved recovery budget (a hard stop can strand a half-done ramp), and a plan estimate that can double its own budget.
2. **Thin delivery and closure semantics.** No Authorize stage or approval bound to artifact and expiry, no disposition vocabulary, no ownership transfer or credential revocation. Automatic rollback and revert are under-conditioned: no rehearsal, no state-safety test, and attribution done by the agent itself.
3. **Some mechanisms are presented as stronger than they are.** Taint tracking on model-written justifications can be laundered. Critic sign-offs add unmeasured judgment from the same model. Two-reviewer agreement counts reviewers instead of diversifying evidence. Dark launch quietly assumes the change can be flagged.