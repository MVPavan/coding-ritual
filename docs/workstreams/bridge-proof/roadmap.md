# Bridge-Proof Roadmap

**Purpose.** Prove the phase-execution interpreter bridge end to end on two real,
independent Beads. This is disposable proof scaffolding, but it is retained after
the proof as the durable description of what was executed.

## P1 — Two-stage bridge proof

**Goal.** Land and close two independent stages through the bridge in the recorded
experimental order, retaining their admission and closure evidence.

| # | Stage | Create/modify paths | Verify |
| --- | --- | --- | --- |
| 1 | `cr-7rp` — task, P3, open, no dependencies; live-verified 2026-09-10. It asserts that `implement`'s verify set must contain `tests-untouched.sh`. | `tests/**` only | The stage's graph run lands and closes with a read-back receipt, and `implement`'s verify set must contain `tests-untouched.sh`. |
| 2 | `cr-0yc` — feature, P3, open, no dependencies; live-verified 2026-09-10. It records the model that actually served each activation. | `workflow_interpreter/**` only | Its admission record post-dates Stage 1's closure; its graph run lands and closes with a read-back receipt; `git merge-base --is-ancestor <stage1-landed-oid> <stage2-instance-base-commit>` succeeds. |

**Spec reference.** `docs/plans/phase-execution-interpreter-bridge.md:18-21,216-241`.

**Proof order and dependencies.** Stage 1 precedes Stage 2 as an experimental
choice: prove the bridge first on the smaller `tests/**` change. No `bd dep`
exists between them because a dependency is allowed only when one task relies on
another's output, not because work is ordered (`.beads/beads.md:73-74`). The
sequence is proved instead by Stage 2's admission record post-dating Stage 1's
closure and by `git merge-base --is-ancestor`; those establish order and inherited
Git state, not dependency enforcement
(`docs/plans/phase-execution-interpreter-bridge.md:216-228`).

**Trust-boundary decision — Stage 1.** The conditional security requirement
applies. This stage is executed through the bridge's LLM/agent feature, an explicit
trust-boundary category, even though its requested file scope is only `tests/**`.
Before implementation, apply the security skill's threat model and LLM/agent
controls to the bridge execution; do not treat the limited path scope as a waiver
(`.claude/skills/execution/SKILL.md:42-44`).

**Trust-boundary decision — Stage 2.** The conditional security requirement also
applies. This stage likewise executes through the bridge's LLM/agent feature, while
its requested scope is `workflow_interpreter/**`; recording the serving model does
not remove that boundary. Before implementation, apply the security skill's threat
model and LLM/agent controls to the bridge execution
(`.claude/skills/execution/SKILL.md:42-44`).

**Test focus.** The two live runs exercise admission, graph execution, signed
fast-forward landing, receipt read-back, stage closure, and the recorded order.

**Risk.** Deep — an LLM/agent bridge coordinates durable Beads and Git landing
evidence; candidate-controlled landing-gate code remains the plan's explicit T1
trust assumption (`docs/plans/phase-execution-interpreter-bridge.md:186-214`).

**Exit (phase).** Both stages are closed with read-back receipts; Stage 2's
admission record is later than Stage 1's closure; the stated ancestry command
succeeds; and the all-closed phase gate succeeds.
