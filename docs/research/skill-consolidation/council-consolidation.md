# Skill Consolidation — Judge's Consolidation

**Members:** Opus 5 (549-line report, final count 39) · GPT-5.6-sol at high effort (483-line report, final count 40).
**Judge's verdict up front: 63 in → 40 out** — but not GPT-5.6-sol's 40. The recommended roster is Opus 5's 39 plus `grilling` kept standalone, with two content-level rulings going to GPT-5.6-sol inside merges that survive from Opus 5's structure.

Adjudication method: I worked from the two reports and went to source files only where the members' evidence conflicted or was insufficient. Files I read to adjudicate: `roster-in.csv` (row/bucket arithmetic), `grilling/SKILL.md`, `resolving-merge-conflicts/SKILL.md`, `documentation-and-adrs/SKILL.md` (two disputed sections), `interview-me/SKILL.md` (grep for `idea-refine`), `using-superpowers/SKILL.md` (grep for the 1% rule), plus greps verifying the `../../references/` defect and the `grilling` couplings in `triage`, `wayfinder`, and `improve-codebase-architecture`. All read-only; nothing under `reference_harnesses/` was touched.

---

## Part 1 — Convergence

Agreement across two blind, independent analyses is the strongest evidence in this exercise. The members converge on far more than they diverge — roughly 32 of the 40 recommended skills are jointly supported in identical or near-identical form.

**Buckets returned untouched by both members — joint claims that no duplication exists:**

- **Bucket 3 (Architecture & Modeling): 5 → 5, both members.** Both independently tested and rejected the CSV's `genus` pairing of `api-and-interface-design` with `codebase-design` (Opus 5: "they share the word 'interface' and nothing else"; GPT-5.6-sol: "a false equivalence: public contract design and internal deep-module design have different consumers and failure modes"). This is the strongest joint no-duplication finding in the corpus.
- **Bucket 9 (Release, Migration & Operations): 5 → 5, both members.** Both found the ci-cd/shipping overlap real but topic-level, not skill-level. Opus 5 additionally specified the trims (flags, staged rollout, rollback triggers deleted from `ci-cd` in favor of `shipping-and-launch`); adopt those trims.

**Identical kept sets (modulo merge naming):**

- **Bucket 5: 4 → 2** — three-way TDD merge (superpowers enforcement base + agent-skills stack discovery/Prove-It/size model + mattpocock pre-agreed seams) plus `browser-testing-with-devtools` standalone. Same inputs, same winner-structure, both members.
- **Bucket 6: 4 → 2** — three-way debugging merge plus `performance-optimization` standalone. Both members preserve the same load-bearing content (red-loop gate, ranked falsifiable hypotheses, tagged probes, root-cause tracing, 3-fixes escalation) and both reject folding performance into the debugger.
- **Bucket 8: 4 → 3** — `resolving-merge-conflicts` absorbed into `git-workflow-and-versioning`; worktrees and branch-finishing kept separate, with near-identical trigger-distinctness reasoning from both.
- **Bucket 11: 5 → 2** — `writing-for-agents` merged into `writing-skills` (same merge, same unique-content analysis on both sides: empirical loop from superpowers, two-loads/ladder/no-op-test vocabulary from mattpocock), plus one router/bootstrap regenerated from the final roster. Both members independently ruled all three routers stale-by-construction after consolidation.
- **Bucket 12: 1 → 1** — setup skill kept as forced by the tracker-coupled survivors (`triage`, `wayfinder`); both flag it needs adaptation.
- **Bucket 14: 2 → 0 adopted** — `teach` and `wait-what` out of scope by kind (output consumed by people), both members, with the same reading of `teach` as a spaced-repetition pedagogy product.
- **Bucket 2: 5 → 3, same three survivors** (`wayfinder`, `triage`, one merged planning skill from `writing-plans` + `planning-and-task-breakdown` + `to-tickets`). The dispute is only over how much of `to-tickets` survives inside the merge (resolved below).

**Jointly dropped with the same reasoning:** `grill-me` and `grill-with-docs` (7-line alias wrappers — both members overturned the CSV's `genus` label), `implement` (15-line wrapper, every clause covered elsewhere), `executing-plans` as a standalone (both cite its own text deferring to `subagent-driven-development`), mattpocock `code-review` and `requesting-code-review` (absorbed into the merged review skill), `ask-matt` / `using-agent-skills` / `using-superpowers` as standalone routers (stale indexes), `brainstorming`'s ~1,400-line visual-companion server bundle (both route the need to `prototype` instead), and `resolving-merge-conflicts` as a standalone.

**Jointly kept untouched:** `to-questionnaire`, `wayfinder`, `triage`, all five B3 skills, `code-simplification`, `security-and-hardening`, `source-driven-development`, `frontend-ui-engineering`, `browser-testing-with-devtools`, `performance-optimization`, `verification-before-completion`, `doubt-driven-development`, `using-git-worktrees`, `finishing-a-development-branch`, all five B9 skills, `context-engineering`, `dispatching-parallel-agents`, `research`.

---

## Part 2 — Conflicts, resolved

### C1. Bucket 1 structure — Opus 5: 3 kept · GPT-5.6-sol: 4 kept → **Ruling: 4, in neither member's exact composition**

Two independent sub-disputes:

**C1a. Does `grilling` survive standalone?** Opus 5 merges `grilling` into `interview-me`, resolving their direct contradiction (batch the whole frontier vs. never batch three questions) by fiat in `interview-me`'s favor — and flags this as the ruling it would revisit first, admitting its own capability-loss ledger records the batched-frontier mechanism as "No — mutually exclusive with the kept mechanism," i.e. destroyed. GPT-5.6-sol keeps `grilling` standalone: 22 lines, adversarial design-tree exhaustion, reused by `triage`, `wayfinder`, and `improve-codebase-architecture`.

**Ruling: GPT-5.6-sol wins.** Three grounds. (1) The brief's primary guard: a merge that destroys an advantage is worse than keeping two skills, and Opus 5's own ledger concedes destruction. (2) A direct contradiction on the primary mechanism is evidence of two different tools, not one duplicated one — the removal test has a real answer for `grilling` (exhaustive frontier traversal of a *formed* plan; agent-side fact-finding; batched rounds with recommended answers) that `interview-me` (latent-intent discovery for an *unformed* want, one question at a time) does not cover. (3) Coupling, which I verified in source and which runs deeper than either member stated: `grilling` is not merely invoked by three kept skills — it is a **ticket type in `wayfinder`'s taxonomy** (`wayfinder:<type>` ∈ {research, prototype, **grilling**, task}, `wayfinder/SKILL.md:65,79`) with HITL semantics defined against it ("a grilling agent that answers its own questions has broken this," line 75). Merging it away forces rewriting the internals of three kept skills plus a ticket taxonomy. Keeping it costs 22 lines. `grill-me` and `grill-with-docs` fold into it as alias/modes (GPT-5.6-sol's handling; both members agree they die as separate skills).

Consequently Opus 5's Merge 1 is reversed: `interview-me` stays essentially unchanged, and Opus 5's cross-bucket repathing item 6 (repointing `/grilling` references) disappears.

**C1b. What is the spec/discovery architecture?** GPT-5.6-sol builds `product-discovery` (three-way merge: `interview-me` + `idea-refine` + `brainstorming`) and absorbs `spec-driven-development` into the 75-line, tracker-coupled `to-spec`. Opus 5 keeps `interview-me` as the discovery skill and builds the spec skill on `spec-driven-development` (206 lines, six-area content model), absorbing `brainstorming`'s hard gate and `to-spec`'s no-interview fast path.

**Ruling: Opus 5 wins.** GPT-5.6-sol's `product-discovery` is a three-stage mega-merge with a mushy trigger — the exact defect both members condemn elsewhere (both reject merging `using-git-worktrees` + `finishing-a-development-branch` on trigger-ambiguity grounds; GPT-5.6-sol itself lists this merge as its #1 revisit, worried agents will "enter the full discovery process when a short underlying-intent interview would have sufficed"). And GPT-5.6-sol's base choice is backwards: the richer, more portable skill (`spec-driven-development`) should absorb the thinner, tracker-coupled one (`to-spec`), not the reverse. Ties break toward portability per the brief.

**C1c. `idea-refine`.** Opus 5 drops it outright (product-shape ideation, outside an engineering harness; technical divergence survives in `codebase-design`'s DESIGN-IT-TWICE). GPT-5.6-sol preserves its divergence stage only *inside* `product-discovery`, which I have rejected on independent grounds; GPT-5.6-sol never argued it survives standalone. **Ruling: dropped (Opus 5), recoverable** — the roster's only unabsorbed deletion, restorable intact if the adopting harness does product work.

**Bucket 1 result: `interview-me`, `grilling` (+aliases), `spec-driven-development` (merged), `to-questionnaire`. 9 → 4.**

### C2. Bucket 2 content — does `to-tickets`' tracker publication survive? → **Ruling: GPT-5.6-sol wins (count unchanged, 3)**

Opus 5 absorbs only `to-tickets`' wide-refactor expand–contract rule and drops tracker publication — while itself calling it "the highest-value loss in this ledger" and "a genuine multi-agent capability with no substitute in the kept set." Its stated conflict (tickets avoid file paths; plans mandate exact code) it then defuses itself: "Both are correct for their artifact's lifetime." That is a conditional, not a conflict. GPT-5.6-sol keeps ticket emission as an output mode (`plan`, `tickets`, or `both`) of the merged planning skill. **Ruling: keep the ticket-output mode.** The tracker chain exists in the kept roster anyway (`triage`, `wayfinder`, and the B12 setup skill all require it), so the dependency cost Opus 5 charged against `to-tickets` is already being paid. The merge stays coherent: one decomposition engine, two serializations. This erases the worst entry in Opus 5's loss ledger at near-zero cost.

### C3. Bucket 4 — Opus 5: 6 kept · GPT-5.6-sol: 5 kept → **Ruling: Opus 5, 6 kept**

GPT-5.6-sol merges `subagent-driven-development` + `incremental-implementation` + `executing-plans` + `implement` into one `plan-execution`. Opus 5 keeps SDD (absorbing `executing-plans`' inline path as a degraded mode) and `incremental-implementation` separately. **Ruling: Opus 5 wins.** The removal test protects `incremental-implementation`: it is the only implementation discipline that **fires without a plan** ("any feature or change that touches more than one file"), where GPT-5.6-sol's own merged spine begins "validate plan → classify task dependencies" — presupposing a plan and thereby destroying the no-plan trigger, or else widening the trigger into ambiguity. The two skills also address different actors: SDD is a controller protocol (fresh subagents, bounded fix loops, adjudication ledger); `incremental-implementation` is the discipline of the agent doing the coding. A 280–330-line skill holding both is the "bag of two wearing one name" the brief forbids. Both members agree `implement` and standalone `executing-plans` die; that part is jointly settled.

### C4. Bucket 7 — Opus 5: 4 kept · GPT-5.6-sol: 3 kept → **Ruling: Opus 5, 4 kept**

The dispute is `receiving-code-review`. GPT-5.6-sol folds it into `code-review` as a "receive mode"; Opus 5 keeps it standalone. **Ruling: Opus 5 wins.** The firing condition (feedback has arrived, from an external actor, at a different moment) is distinct, and a three-mode description ("requesting or conducting or receiving") is precisely the ambiguous-trigger defect `writing-skills` documents — evidence both members cite approvingly elsewhere. The CSV's `complements` label means one protocol in two halves; keeping both halves is what honoring it means (Opus 5's phrasing). GPT-5.6-sol half-concedes: its own revisit #3 says restore `receiving-code-review` if trigger tests show the receive mode doesn't fire. I am ruling on that risk now rather than deferring it. The three-input merge (`code-review-and-quality` + mattpocock `code-review` + `requesting-code-review`) is jointly supported and stands, including mattpocock's never-rerank-across-axes rule as a reporting guarantee. On Opus 5's selection-only caveat (repathing SDD's hard reference to `code-reviewer.md`): the plan defers writing, and writing merges necessarily includes repathing, so the merge stands and the count does **not** revert to Opus 5's contingency. Both members independently listed the same rename/repath obligations, which settles that repathing is in scope.

### C5. Bucket 10 — Opus 5: 2 kept · GPT-5.6-sol: 3 kept → **Ruling: Opus 5, 2 kept**

GPT-5.6-sol keeps `handoff` standalone ("folding a user-invoked portability operation inside a frequently triggered context reference" hides it). Opus 5 merges its 16 lines into `context-engineering`, whose Level 5 already claims session-boundary management, and co-locates it with the rescued five-option phase-boundary tree (Continue / clear / **handoff** / Subagent / compact) from `ask-matt`. **Ruling: Opus 5 wins.** Handoff is one branch of the phase-boundary decision; splitting the tree from one of its five options across two skills fractures a single decision. The distinction from C4 is principled, not ad hoc: `receiving-code-review` is a substantial behavioral protocol with a distinct actor-moment and no kept skill claiming its trigger; `handoff` is 16 lines whose trigger the absorbing skill already owns. GPT-5.6-sol's user-invocation point survives as a note: expose a `/handoff` command alias at adoption time — capability preserved, invocability preserved, one skill.

### C6. Bucket 13 — Opus 5: 1 kept · GPT-5.6-sol: 2 kept → **Ruling: Opus 5, 1 kept**

GPT-5.6-sol keeps `documentation-and-adrs` with a one-line "uniquely maintains…" justification — but it also keeps `domain-modeling` (B3) for "glossary and ADR formats," leaving **two skills owning ADRs** without ever engaging the duplication. That is failure mode 1 crossing a bucket line, which the brief explicitly ordered tested; Opus 5 caught it and GPT-5.6-sol did not. Opus 5's dissolution is well-evidenced: ADR content (including the convention-detection and never-delete/supersede lifecycle rules) → `domain-modeling`; changelog → `git-workflow-and-versioning`, which both members agree holds the stronger version; README/JSDoc/comment-why dropped as no-ops. I verified the two sections Opus 5 did not enumerate: "Documentation for Agents" (`SKILL.md:250-258`) is a four-bullet index over things other kept skills own (rules files, specs, ADRs, gotchas) — no capability; "Document Known Gotchas" (`:137-150`) is one worked example whose rule ("comment the trap, link the ADR") is worth **one line** carried into the `domain-modeling` redistribution. With that line carried, nothing survives the removal test. Opus 5's stated contingency stands: if `domain-modeling` were ever not adopted, restore `documentation-and-adrs` as the single ADR home instead.

### C7. Bucket 6 merge base and safe-fallbacks → **Ruling: Opus 5 on both; naming is a writing-time decision**

Same three inputs, same two outputs, but Opus 5 builds on `diagnosing-bugs` (mattpocock) as spine and GPT-5.6-sol on `systematic-debugging` (superpowers). Functionally convergent; I lean **Opus 5's spine** because the checkable Phase-1 exit ("one command, already run at least once, that shows the bug red") is the strongest enforcement mechanism in the family, and enforcement strength is a ranked criterion. The name can be either; do not count this as a roster difference. One real content conflict: GPT-5.6-sol carries `debugging-and-error-recovery`'s "fallback guidance" into the merge; Opus 5 drops safe-fallback/graceful-degradation patterns as directly conflicting with the root-cause gate both other skills share. **Opus 5 wins** — you cannot keep a hard root-cause gate and a time-pressure symptom-patch path in one skill without the gate becoming prose advice.

### C8. Bucket 8 — "Always resolve; never `--abort`" → **Ruling: Opus 5, with GPT-5.6-sol's caveat absorbed as scoping**

GPT-5.6-sol rejects the rule as an unsafe absolute (accidental merge, wrong base). Opus 5 keeps it as unique content. I read the 14-line file: the skill's trigger is "an **in-progress** git merge/rebase conflict," and the rule sits inside step 3 ("Resolve each hunk"). It targets the agent failure mode of bailing out of conflict resolution; aborting a merge you never meant to start is not conflict resolution and is outside the skill's declared trigger. **Ruling: keep the rule, add one scoping line** ("an accidental or wrong-base merge is not a resolution scenario — aborting it is out of this skill's scope"). Substance to Opus 5; GPT-5.6-sol's concern honored without deleting a real behavioral rule.

### C9. Bucket 11 — router aggressiveness and the phase-boundary tree's home → **Ruling: Opus 5 on both**

GPT-5.6-sol rejects `using-superpowers`' threshold (verified in source: "even a 1% chance a skill might apply, you ABSOLUTELY MUST invoke," `SKILL.md:11`) as over-triggering; Opus 5 keeps the full mandate. **Ruling: keep the strong mandate including the threshold.** The corpus's only empirical evidence points at under-invocation as the observed failure (superpowers' own claim that without the bootstrap "the skills are dead weight"; `writing-skills`' tested finding that weak descriptions cause skipped behavior). Over-firing costs a read; under-firing costs the discipline. Run GPT-5.6-sol's proposed trigger evals before ever weakening it — evidence first, then tuning. On the phase-boundary tree: Opus 5 homes it in `context-engineering`, GPT-5.6-sol in the router. **Opus 5 wins** — the tree decides context lifecycle (continue/clear/handoff/subagent/compact), which is `context-engineering`'s job; the router routes to skills, and stuffing a context-management decision tree into it re-creates the mixed-trigger defect.

### C10. Bucket 12 — narrow vs. genericize → **Ruling: compose both (no real conflict)**

Opus 5 narrows (drop Section C domain-doc scaffolding as duplicating `domain-modeling`); GPT-5.6-sol genericizes the name and wants a first-class Beads adapter for this repo. These are compatible: **narrowed + genericized + Beads adapter at adoption.** 1 → 1 either way.

### C11. Headline count — 39 vs. 40 → **Ruling: 40**

Neither member's arithmetic was wrong; the counts diverge purely from the rulings above. Resolved composition: Opus 5's roster + `grilling` = 40. Note the coincidence is superficial — GPT-5.6-sol's 40 contains `product-discovery`, `to-spec`, `plan-execution`, `handoff`, and `documentation-and-adrs`, none of which are in the recommended roster, and lacks `interview-me`-standalone, `incremental-implementation`, `subagent-driven-development`, and `receiving-code-review` as standalone entries.

**Score by ruling, for the record:** Opus 5 wins C1b, C1c, C3, C4, C5, C6, C7, C8 (substance), C9; GPT-5.6-sol wins C1a and C2, and contributes absorbed caveats in C8/C10 plus the B5 characterization-test allowance (adopted — it matches this repo's own testing rule). GPT-5.6-sol's two wins are both places where Opus 5's merge destroyed a capability its own ledger admitted was real — exactly the failure mode the brief ranks worse.

---

## Part 3 — Recommended roster

**63 in → 40 out.** Per-bucket: B1 9→4 · B2 5→3 · B3 5→5 · B4 8→6 · B5 4→2 · B6 4→2 · B7 6→4 · B8 4→3 · B9 5→5 · B10 3→2 · B11 5→2 · B12 1→1 · B13 2→1 · B14 2→0.
Inputs: 9+5+5+8+4+4+6+4+5+3+5+1+2+2 = **63** ✓ (verified against `roster-in.csv`: 63 rows, bucket sizes match). Outputs: 4+3+5+6+2+2+4+3+5+2+2+1+1+0 = **40** ✓.

| # | Skill | B | Provenance | Survives the removal test because |
|---|---|---|---|---|
| 1 | `interview-me` | 1 | agent-skills, near-unchanged (delete/repoint `idea-refine` pointers at lines 14, 182, 225) | Only skill detecting the want-vs-should-want gap, with an explicit-yes gate and the predict-the-next-three-answers stop test |
| 2 | `grilling` | 1 | mattpocock + `grill-me`/`grill-with-docs` as alias/modes | Only adversarial design-tree exhaustion (batched frontier, agent-side fact-finding); named sub-skill and `wayfinder` ticket type of three kept skills |
| 3 | `spec-driven-development` | 1 | merged: base + `brainstorming` (hard gate, decomposition check, self-review) + `to-spec` (no-interview fast path) | Only skill producing an approved written spec behind a hard no-implementation gate, with the six-area content model |
| 4 | `to-questionnaire` | 1 | mattpocock, unchanged | Only skill whose artifact targets an absent third party who holds knowledge the user lacks |
| 5 | merged planning skill (`writing-plans` base; GPT-5.6-sol's name `planning-and-ticketing` is apt) | 2 | `writing-plans` + `planning-and-task-breakdown` + `to-tickets` **including the ticket-output mode** and wide-refactor rule | Only skill turning approved work into zero-context-executable units — emitted as a plan file, tracker tickets with native blocking links, or both |
| 6 | `wayfinder` | 2 | mattpocock, unchanged | Only planner for work larger than one context window under uncertainty (fog of war, decision tickets, frontier) |
| 7 | `triage` | 2 | mattpocock, unchanged | Only inbound-work state machine, with concept-level redundancy checks and a prior-rejection knowledge base |
| 8 | `improve-codebase-architecture` | 3 | mattpocock; HTML report demoted to optional (CDN dependency), badges + vocabulary moved inline | Only skill that *finds* restructuring candidates, scoped by commit-history hot spots |
| 9 | `prototype` | 3 | mattpocock, unchanged | Only skill answering a design question with running throwaway code |
| 10 | `domain-modeling` | 3 | mattpocock + ADR content from `documentation-and-adrs` (convention detection, supersede lifecycle, one-line gotcha-comment rule) | Only skill maintaining ubiquitous language as an active discipline; now the single ADR home |
| 11 | `api-and-interface-design` | 3 | agent-skills; validation section trimmed to its design consequence (threat model points at security) | Only skill covering published contracts and the consequences of having consumers (Hyrum's Law, additive-only evolution) |
| 12 | `codebase-design` | 3 | mattpocock, unchanged | Only source of deep-module vocabulary with the anti-synonym rule, deletion test, and two-adapters seam rule |
| 13 | `subagent-driven-development` | 4 | superpowers + degraded inline mode from `executing-plans` | Only plan executor with bounded fix loops, capability escalation, and a compaction-surviving adjudication ledger |
| 14 | `incremental-implementation` | 4 | agent-skills, unchanged | Only implementation discipline that fires **without a plan**; contract-first/risk-first slicing; NOTICED-BUT-NOT-TOUCHING |
| 15 | `code-simplification` | 4 | agent-skills, unchanged | Only skill whose contract is change-how-it-reads-never-what-it-does, with the over-simplification guard |
| 16 | `security-and-hardening` | 4 | agent-skills, unchanged | The corpus's single source of truth for "treat X as untrusted"; STRIDE, SSRF/TOCTOU, OWASP LLM Top 10 |
| 17 | `source-driven-development` | 4 | agent-skills, unchanged | Only skill pinning framework facts to a version with citations and an UNVERIFIED flag |
| 18 | `frontend-ui-engineering` | 4 | agent-skills, unchanged | Only UI skill; the AI-aesthetic tells table has no counterpart |
| 19 | `test-driven-development` | 5 | merged ×3: superpowers base + agent-skills (stack discovery, Prove-It, size model) + mattpocock (pre-agreed seams, mockability); + characterization-test allowance for legacy (GPT-5.6-sol) | Only discipline gate making violation recoverable-only-by-deletion, with mandatory watched-RED |
| 20 | `browser-testing-with-devtools` | 5 | agent-skills, unchanged | Only skill observing live runtime state, with the browser-profile blast-radius analysis |
| 21 | merged debugging skill (`diagnosing-bugs` spine; name at writing time) | 6 | mattpocock + `systematic-debugging` (3-fixes escalation, per-boundary evidence, 3 technique assets) + `debugging-and-error-recovery` (non-reproducible tree, bisect); safe-fallbacks dropped | Only skill making red-loop construction the skill itself, with a checkable Phase-1 exit |
| 22 | `performance-optimization` | 6 | agent-skills, unchanged | Only skill with a disposal rule for unsuccessful work ("neutral is a revert") and an attempt ledger |
| 23 | `code-review` | 7 | merged: `code-review-and-quality` + mattpocock `code-review` (never-rerank-across-axes, smell baseline) + `requesting-code-review` (dispatch + reviewer template asset) | The review rubric and dispatch mechanism in one place; axes reported separately as a process guarantee |
| 24 | `receiving-code-review` | 7 | superpowers, unchanged | Only skill for the moment feedback arrives: forbids performative agreement, clarify-all-before-implementing-any |
| 25 | `verification-before-completion` | 7 | superpowers, unchanged | Only pre-claim gate with a claim→required-evidence table |
| 26 | `doubt-driven-development` | 7 | agent-skills, unchanged (note: load-bearing `orchestration-patterns.md` + `agents/` persona dependency) | Only in-flight per-decision adversarial review, with pass-artifact-not-claim bias control |
| 27 | `git-workflow-and-versioning` | 8 | agent-skills + `resolving-merge-conflicts` (intent-tracing; never-abort kept with accidental-merge scoping line) + changelog content; worktree stub deleted | Only skill covering commit discipline and the release contract (semver-as-promise, changelog-with-the-change) |
| 28 | `using-git-worktrees` | 8 | superpowers, unchanged | Only correct isolation setup; carries the submodule guard and native-tool preference |
| 29 | `finishing-a-development-branch` | 8 | superpowers, unchanged | Only integration decision gate; typed-confirmation destruction guard, cleanup provenance rule |
| 30 | `wizard` | 9 | mattpocock, unchanged | Only skill producing an artifact a human executes step by step, UX solved once in `template.sh` |
| 31 | `deprecation-and-migration` | 9 | agent-skills, unchanged | Only skill covering removal as a discipline (churn rule, expand→contract schema migration) |
| 32 | `observability-and-instrumentation` | 9 | agent-skills, unchanged | Only skill making production visible, gated question-first, with cardinality as the named failure mode |
| 33 | `ci-cd-and-automation` | 9 | agent-skills; flag/rollout/rollback-trigger sections trimmed in favor of `shipping-and-launch` (Opus 5's trims) | Only skill configuring automated enforcement; agent feedback loop; no-gate-skipping rule |
| 34 | `shipping-and-launch` | 9 | agent-skills, unchanged | Only skill with numeric rollout thresholds and a rollback plan template |
| 35 | `context-engineering` | 10 | agent-skills + `handoff` (all four rules; expose `/handoff` command alias at adoption) + `ask-matt`'s phase-boundary tree | Only skill governing what enters the window, in-session and across boundaries, with the five-option boundary tree |
| 36 | `dispatching-parallel-agents` | 10 | superpowers; generic dispatch guidance trimmed to a pointer at SDD | Only skill for parallel fan-out over independent problems, with the independence gate |
| 37 | `writing-skills` (merged; GPT-5.6-sol's name `writing-agent-instructions` acceptable) | 11 | superpowers + `writing-for-agents` (ladder, two loads, pointer wording, no-op test, negation scoping) | Only empirical method for proving a document changes behavior, now with the what-goes-where vocabulary |
| 38 | skill-invocation bootstrap/router | 11 | from `using-superpowers` (full mandate incl. threshold, rationalization table, precedence rule); index regenerated from this roster | The only content that makes the rest of the roster fire at all |
| 39 | setup skill (`setup-matt-pocock-skills`, genericized) | 12 | narrowed to tracker config + triage labels (Opus 5); genericized name + Beads adapter at adoption (GPT-5.6-sol) | Declared precondition of kept `triage` and `wayfinder`; no independent job |
| 40 | `research` | 13 | mattpocock, unchanged | Only background-delegated, primary-source, durable cited artifact; distinct from `source-driven-development`'s inline grounding |

**Dropped (23):** `grill-me`, `grill-with-docs` (aliases → `grilling`); `brainstorming`, `to-spec` (→ `spec-driven-development`); `idea-refine` (outright; the only unabsorbed deletion); `planning-and-task-breakdown`, `to-tickets` (→ merged planning skill); `implement` (outright); `executing-plans` (→ SDD degraded mode); agent-skills `test-driven-development`, mattpocock `tdd` (→ merged TDD); `systematic-debugging`, `debugging-and-error-recovery` (→ merged debugger); mattpocock `code-review`, `requesting-code-review` (→ `code-review`); `resolving-merge-conflicts` (→ git-workflow); `handoff` (→ `context-engineering`); `ask-matt` (tree rescued), `using-agent-skills` (six behaviors verified present in kept skills — Opus 5's six-for-six enumeration), `using-superpowers` (mandate kept as bootstrap); `writing-for-agents` (→ `writing-skills`); `documentation-and-adrs` (dissolved three ways); `teach`, `wait-what` (out of scope; `wait-what` optionally reinstatable at zero context cost as user-invoked). 40 + 23 = 63 ✓.

---

## Part 4 — Gaps neither member covered (and one asymmetry)

**G1. The `../../references/*.md` defect — VERIFIED, and it is as serious as Opus 5 said.** I ran the grep myself: `reference_harnesses/agent-skills/references/` holds exactly seven files (`accessibility-checklist.md`, `definition-of-done.md`, `observability-checklist.md`, `orchestration-patterns.md`, `performance-checklist.md`, `security-checklist.md`, `testing-patterns.md`), referenced from **eleven** distinct agent-skills skills — of which **nine are in the recommended roster** directly or as merge bases (`code-review-and-quality`, `doubt-driven-development`, `frontend-ui-engineering`, `incremental-implementation`, `observability-and-instrumentation`, `performance-optimization`, `security-and-hardening`, `shipping-and-launch`, plus the merged-in `planning-and-task-breakdown` and agent-skills TDD; only `using-agent-skills` is fully dropped). `doubt-driven-development`'s case is load-bearing, not cosmetic: its Loading Constraints are written against `orchestration-patterns.md`'s persona rules (`SKILL.md:46,229`), and it additionally depends on the harness's `agents/` persona roster. **Consequence for any adopted roster: porting the seven `references/` files (or inlining/trimming each pointer) is a mandatory adoption work item, on par with the merge-writing itself.** GPT-5.6-sol's cross-bucket check covered skill-name renames only and **missed this entirely** — the single largest analytical gap between the two reports.

**G2. Disclosure asymmetry.** Opus 5 itemized every unread asset and stated per item whether a ruling depended on it (none did; the closest call, `brainstorming/scripts/*`, was ruled on documented dependency cost, which is legitimate). GPT-5.6-sol made the blanket claim "All 63 `SKILL.md` files and their bundled assets were read" with zero enumerated exceptions — including ~1,400 lines of brainstorming server scripts, `teach`'s four FORMAT files, and five setup seed templates. It did **not** disclose gaps the way Opus 5 did. I cannot prove non-reading, and I found no ruling demonstrably undermined by it; but an unfalsifiable blanket claim is worth less than an itemized disclosure, and several of GPT-5.6-sol's citations are whole-file ranges (e.g. `SKILL.md:10-467`) that certify nothing specific. Weight accordingly: where the members disagreed on what a file *says*, I trusted quoted content over ranged citations, and where it mattered I read the file myself.

**G3. Gaps both members share.**
- Neither enumerated `documentation-and-adrs`' "Documentation for Agents" and "Document Known Gotchas" sections in their rulings; I checked both (no surviving capability; one line carried — see C6).
- Neither fully stated `grilling`'s depth of coupling (`wayfinder` ticket type + HITL semantics), which turns out to be decisive evidence for C1a.
- Neither addressed that agent-skills ships **trigger/routing evals** (`evals/`, `node scripts/run-evals.js` per its CLAUDE.md); every merge in this roster orphans the upstream eval coverage for its inputs. Rebuilding trigger evals for the ~9 merged skills is an unclaimed adoption work item — and it is also exactly the instrument both members keep appealing to for their open questions.
- `interview-me`'s `idea-refine` references are at **three** locations (lines 14, 182, 225), not just the one Opus 5's Part 2 flagged; the repathing sweep should grep, not spot-fix.
- Both members' merged-size figures are design targets, unvalidated by any written artifact (GPT-5.6-sol says so explicitly; Opus 5's "~" figures are the same in kind).

---

## Part 5 — Confidence

**Overall: high on the roster's membership, medium-high on merge internals.** The core is jointly supported by two blind analyses: all of B3, B5, B6, B8, B9, B12, B14, the B2 trio, the B11 pair, and ~20 unchanged singletons are effectively settled. The eight rulings that required adjudication are ranked below by fragility, most fragile first:

1. **`grilling` standalone (C1a).** I overrode Opus 5 using its own self-flag, the brief's failure-mode-2 guard, and coupling evidence I verified in source. Would change on: an eval showing one-at-a-time interviewing reaches confirmed shared understanding with fewer user round-trips *in grilling's own use cases* (stress-testing a formed plan), or a decision not to adopt `wayfinder`/`triage`, which removes the coupling argument. I lean keep-standalone firmly — the mechanism contradiction plus the ticket-type coupling make the merge strictly worse.
2. **B4 stays at 6 (C3).** Would change on: adoption-time evidence that virtually all implementation runs through SDD from written plans, leaving `incremental-implementation`'s no-plan trigger nearly dead. Then GPT-5.6-sol's merge becomes defensible. I lean keep-separate; the no-plan case is the common case in real sessions.
3. **B13 dissolution (C6).** Explicitly contingent: it holds if and only if `domain-modeling` is adopted. If not, restore `documentation-and-adrs` as the single ADR home. I lean dissolve.
4. **Ticket-output mode kept in the B2 merge (C2).** Would change on: the adopting harness abandoning tracker-based multi-session work entirely — but then `triage`, `wayfinder`, and the setup skill fall too (Opus 5's own contingency: roster → ~37), so this ruling stands or falls with the tracker chain as a unit, not alone.
5. **`receiving-code-review` standalone (C4).** GPT-5.6-sol's own revisit condition points the other way only if trigger evals prove the receive-mode fires reliably inside a merged skill; absent that evidence, separate is the safe default. Lean keep.
6. **`handoff` merged (C5).** The cheapest ruling to reverse (16 lines back out, alias removed). Would change on: evidence users reach for `/handoff` as a reflex command and the merged placement buries it despite the alias.
7. **Bootstrap keeps the 1% mandate (C9).** Would change on: trigger-eval evidence of material over-invocation cost. Until measured, the documented under-invocation failure dominates.
8. **Debugger spine choice (C7).** Lowest stakes — same content either way; a writing-time decision.

**Independent of every ruling above:** the `references/` port (G1) and the merge-eval rebuild (G3) are mandatory adoption work items that no roster choice avoids. Budget them with the merge-writing, not after it.
