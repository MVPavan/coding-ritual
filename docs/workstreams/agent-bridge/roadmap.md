# Agent bridge roadmap

Approved by the owner on 2026-09-11 in conversation. Scope: [coordination spec](../../specs/2026-09-11-workflow-coordination.md). Execute all phases in the paused bridge worktree. Terra High implements bounded work; Astra low/medium handles substantial complexity; Fable 5.1 high reviews after P1, P3, and P5. Routine task checks and coordinator verification occur between those reviews. No merge or push.

## P0 — Baseline and contracts

Goal: preserve paused edits and establish the execution baseline. Risk: standard.

| # | Stage | Create/modify paths | Verify |
|---|---|---|---|
| 1 | Record approved scope and baseline | spec, this roadmap, scratchpad evidence | Dirty files preserved; seven baseline results recorded; implementation ownership is explicit. |

Spec references: Implementation Decisions, Testing Decisions.
Exit (phase): the baseline and approved contracts can be reconstructed without chat history.
Test focus: existing checks, no product changes.

## P1 — Complete sequential execution

Goal: finish the existing one-stage bridge and prove two sequential stages. Risk: deep.

| # | Stage | Create/modify paths | Verify |
|---|---|---|---|
| 1 | Authenticated landing and complete verification | bridge authority, landing, models, admission; bridge tests | Wrong/rejected gate and empty/incomplete/red/changed-policy checks refuse; policy and artifact are bound through recovery. |
| 2 | Command recovery and stage closure | bridge command/adapter/retry; Foreman config/CLI; execution skill; phase bridge tests | Normal command completes two sequential stages; injected crashes repair without duplicate execution or unverified closure. |

Stage 2 depends on stage 1's verified landing boundary. P1 depends on P0.
Spec references: bridge and verification decisions; first and fifth success criteria.
Exit (phase): full repository checks, normal-entry two-stage proof, and Fable milestone review findings resolved.
Test focus: actual authenticated gate correspondence, check policy, CAS/receipt/close crash windows, retry eligibility.

## P2 — Bounded model decisions

Goal: models decide only at declared judgment boundaries. Risk: deep.

| # | Stage | Create/modify paths | Verify |
|---|---|---|---|
| 1 | Decision lifecycle and handoff bounds | schema, bdio, Foreman inputs/dispatch; decision and input tests | Immediate signal and exhausted allowance produce bound requests; stale/duplicate/unauthorized responses refuse; required oversized input is explicit. |

P2 depends on P1's durable completion boundary.
Spec references: model decision, human authority, budgets and handoffs.
Exit (phase): ordinary acceptance has zero decision calls; one real decision resumes or replaces work with lineage and bounded allowance.
Test focus: outcome routes, response identity, overall budget, context omissions, human authority preservation.

## P3 — Durable child coordination

Goal: coordinate independent instances without mediating their local loops. Risk: deep.

| # | Stage | Create/modify paths | Verify |
|---|---|---|---|
| 1 | Independent child start, status, collection and cancellation | coordination boundary, bdio relationships, Foreman interface, supervisor locking; coordination tests | Two children overlap in isolated workspaces; duplicate start, restart and cancellation races preserve one authoritative result. Reuse Beads; the orchestrator chooses subsequent runs. |

P3 depends on P2's decision and budget contracts. It exposes independent child runs, not a dependency scheduler. Bridge replacement binding and required-contribution closure guards move to P4, where their integration consumer exists. P3 cannot authorize stage closure or landing from collected child results.
Spec references: child relationships, cancellation, restart, boundedness.
Exit (phase): parallel child proof plus restart/cancellation tests pass; Fable reviews P2 and P3 together and findings are resolved.
Test focus: independent workspaces, canonical lock identity, stale results, compact verified collection.

## P4 — Integrate parallel results

Goal: land combined work with evidence for the actual resulting artifact. Risk: deep.

| # | Stage | Create/modify paths | Verify |
|---|---|---|---|
| 1 | Fresh integration attempts and serialized landing | coordination and bridge integration boundary; integration tests | Two same-base siblings contribute; changed-base/conflicting work gets a fresh bounded attempt and renewed approval/verification. |

P4 depends on P3 results and P1 landing. It owns bridge current-generation replacement binding, separate execution and target bases, and required-contribution guards on all landing/recovery/closure paths. Obsolete roots cannot land or close the stage; uncertain landing must be reconciled before replacement.
Spec references: serialized integration and replacement lineage.
Exit (phase): replay and fault injection never reuse stale approval or lose a required child artifact.
Test focus: stale bases, conflicts, combined review, integration budget, replay.

## P5 — Normal workflow and live proof

Goal: expose the complete approved path through the normal execution entry point. Risk: deep.

| # | Stage | Create/modify paths | Verify |
|---|---|---|---|
| 1 | Templates, execution integration and operating documentation | workflows, config examples, execution skill, CLI documentation and acceptance tests | Basic and design/spec workflows run alongside feature/build loops; normal entry drives design, parallel work, a decision, integration and closure using two live runtimes. |

P5 depends on P4.
Spec references: all success criteria.
Exit (phase): full repository gates, real-runtime evidence, final Fable review resolved, updated handoff and Beads evidence.
Test focus: user entry point, cross-runtime execution, model-role policy, recovery and combined result.
