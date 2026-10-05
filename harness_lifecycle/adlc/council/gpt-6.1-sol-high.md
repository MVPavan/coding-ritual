An autonomous development lifecycle should be a **bounded delegation of authority with evidence attached to every consequential transition**. Agents decide how to solve the problem; a durable controller enforces what they may do, what counts as success, and when they must stop.

The unit of work is a **change contract**: intended outcome, scope, acceptance criteria, permitted actions, resource limits, delivery target, and recovery obligations. A change is complete when the contracted result is delivered and verified at that target.

**1. Principles.** Six principles determine the design.

| Principle | Reasoning |
|---|---|
| **Intent and authority come from outside the executing agent.** | An agent can propose interpretations and actions, but cannot grant itself permission or redefine success to match its output. |
| **Claims require evidence proportional to their consequences.** | A passing check supports only the behavior and conditions it actually examined; larger consequences require broader, stronger evidence. |
| **Implementation and acceptance have separate control.** | The actor producing a change must not be able to weaken the criteria, alter the verifier, and then certify its own success. |
| **Limit harm before attempting work.** | Permissions, isolation, exposure limits, and recovery preparation constrain the consequences of mistakes that verification misses. |
| **Progress must be durable and resource-bounded.** | Crashes, retries, and repeated reasoning are normal operating conditions; correctness cannot depend on an uninterrupted conversation or unlimited attempts. |
| **Completion is an observed outcome.** | Producing code, passing checks, publishing an artifact, and delivering useful behavior are distinct events; the contract determines which must be demonstrated. |

These principles imply two cooperating parts:

- **Agents** interpret, investigate, design, implement, test, review, and diagnose.
- **A controller** owns authoritative state, permissions, budgets, evidence records, and transitions. Its enforcement must work even when an agent ignores its instructions.

The controller does not determine whether an arbitrary program is correct. It determines whether the required evidence and authority exist for the next action.

**2. Lifecycle diagram.** Every transition below records its inputs, evidence, and decision.

```text
 REQUEST + OWNER POLICY
          |
          v
 [1 Admit and bound]
          |
          v
 [2 Ground in reality] <-------------------------------+
          |                                            |
          v                                            |
 [3 Establish change contract] <------------------+     |
          |                                      |     |
          v                                      |     |
 [4 Design and plan] <-----------------------+    |     |
          |                                 |    |     |
          v                                 |    |     |
 [5 Prepare isolation and baseline]         |    |     |
          |                                 |    |     |
          v                                 |    |     |
 [6 Implement] <-----------------------+     |    |     |
          |                           |     |    |     |
          v                           |     |    |     |
 [7 Qualify] -- repairable defect -----+     |    |     |
          |                                 |    |     |
          v                                 |    |     |
 [8 Independently challenge] -- design flaw -+    |     |
          |                                      |     |
          |--- wrong/ambiguous requirement ------+     |
          |                                            |
          v                                            |
 [9 Integrate and construct delivery candidate]        |
          |                                            |
          |--- changed baseline / invalid assumptions -+
          |
          v
 [10 Authorize and promote]
          |
          v
 [11 Observe contracted outcome]
          |
          +-- regression --> containment / recovery
          |                         |
          |                         +--> bounded repair at 2, 4, or 6
          |                         +--> incident escalation
          v
 [12 Settle and transfer operational ownership]
          |
          v
       COMPLETE

 Any stage --> WAITING_FOR_DECISION / BLOCKED / FAILED / CANCELLED
 Any back-edge consumes the same root budget.
 Any changed prerequisite invalidates dependent evidence.

 Cross-cutting at EVERY stage:
 authority and identity | least privilege | untrusted-input handling
 durable state and artifact lineage | cost/time limits | observability
 evidence validity | cancellation | recovery readiness
```

Stages are logical obligations, not mandatory separate meetings, agents, or jobs. A small change can combine stages in one execution. An inapplicable obligation is recorded with a reason—for example, runtime deployment for a documentation delivery.

**3. Stage table.** Failure returns work to the earliest invalid prerequisite. Routine repairs remain autonomous within the original contract and budget.

| Stage | Goal | Inputs | Outputs | Capabilities needed | Exit criterion | On failure |
|---|---|---|---|---|---|---|
| **1. Admit and bound** | Determine whether the request can be attempted safely. | Request; requester identity; owner policy; available resources. | Work identity; provisional scope; discovery permissions; root budget; preliminary risk assessment. | Intent interpretation; authority and risk reasoning; budget enforcement. | Authorized requester, identifiable objective, bounded discovery allowance, and enforceable limits exist. | Reject unauthorized work; request a missing decision; queue unavailable capacity. |
| **2. Ground in reality** | Establish the relevant current state. | Admitted request; source and documentation; environment access; existing behavior. | Recorded baseline; dependency and impact map; constraints; known unknowns. | Context reconstruction; environment inspection; security analysis. | Relevant behavior, dependencies, and authoritative constraints are understood well enough to specify the change. | Conduct bounded probes; record inaccessible facts; block if a consequential assumption cannot be established. |
| **3. Establish change contract** | Make success and permissible work explicit. | Intent; baseline; constraints; risk assessment. | Versioned contract: outcomes, scope, exclusions, acceptance evidence, authority, budgets, delivery target, recovery obligations. | Acceptance design; intent interpretation; authority and risk reasoning. | Each consequential requirement has an adequate evaluation method; remaining assumptions are permitted and recorded. | Resolve ambiguities from authoritative evidence; ask the owner about unresolved value choices; decline unverifiable promises. |
| **4. Design and plan** | Choose a feasible route to the contracted outcome. | Contract; impact map; constraints. | Design; dependency graph; work ownership; validation plan; delivery and recovery plan; budget allocation. | Engineering design; decomposition and scheduling; migration engineering. | The plan fits authority and budget, addresses material failure modes, and provides a recovery route. | Simplify or redesign; return to the contract if feasibility changes scope or risk. |
| **5. Prepare isolation and baseline** | Make execution reproducible and contain side effects. | Plan; recorded baseline; approved dependencies and credentials. | Isolated workspace; reproducible environment; baseline check results; scoped access; recovery prerequisites. | Environment preparation; baseline assessment; least-privilege execution. | Isolation works, relevant existing failures are characterized, and required checks and recovery actions can run. | Repair infrastructure within allowance; distinguish existing defects from new ones; block when isolation or recovery is inadequate. |
| **6. Implement** | Produce the smallest coherent change satisfying the contract. | Plan; isolated baseline; protected acceptance criteria. | Candidate source, configuration, documentation, tests, and migration artifacts; change rationale. | Implementation; migration engineering; local testing. | Intended edits are complete, local checks pass, and the change remains within scope. | Diagnose and repair within allowance; escalate discovered scope expansion or architectural infeasibility. |
| **7. Qualify** | Collect behavioral and technical evidence. | Exact candidate; contract; baseline results; protected verification procedures. | Requirement-to-evidence record; check results; security and performance findings; declared proof limits. | Test engineering; differential diagnosis; security analysis; performance analysis. | Required checks execute successfully; results cover the contract; unresolved defects are absent or explicitly permitted. | Return defects to implementation; return weak or missing evaluation methods to contract/design. Infrastructure errors produce no success verdict. |
| **8. Independently challenge** | Find errors in the implementation, assumptions, and evidence. | Candidate; contract; relevant source; qualification results. | Independent findings; severity and resolution record; assurance verdict. | Independent review; acceptance analysis; adversarial reasoning. | Required findings are resolved, and the reviewer judges the evidence adequate for the declared consequences. | Send actionable defects to the appropriate earlier stage. Disputes require evidence or an authorized decision; exhausted review loops stop. |
| **9. Integrate and construct delivery candidate** | Produce what will actually be delivered against the current shared state. | Reviewed candidate; current integration baseline; build inputs; delivery requirements. | Immutable delivery artifact; source/dependency provenance; integration results; final recovery package. | Integration and concurrency control; artifact construction; test engineering. | The exact delivery candidate passes applicable checks against the intended target state; provenance and recovery are complete. | Reconcile baseline drift; requalify affected behavior; re-review material changes. Never overwrite concurrent work silently. |
| **10. Authorize and promote** | Perform the consequential delivery action. | Exact artifact; evidence; destination state; scoped authority; exposure and recovery limits. | Promotion receipt; destination identity/version; rollout state. | Promotion control; authority enforcement; evidence validation. | The controller confirms valid authority and evidence for this artifact and destination, then verifies the promotion occurred. | Refresh stale evidence; wait for an authority decision; reconcile ambiguous action results before retrying. |
| **11. Observe contracted outcome** | Verify delivery produced the promised behavior within acceptable limits. | Promotion receipt; outcome probes; monitoring baseline; exposure thresholds; observation window. | Target-side acceptance evidence; health assessment; recovery actions if needed. | Runtime and outcome verification; diagnosis; rollback and compensation. | Contracted behavior and guardrails hold throughout the defined observation window at the required exposure. | Stop expansion, contain effects, execute authorized recovery, then repair or escalate within remaining limits. |
| **12. Settle and transfer ownership** | Leave an accountable, maintainable result. | Acceptance evidence; final destination state; remaining obligations. | Completion record; user-facing summary; operational owner; monitoring and retention assignments; released resources. | Closeout; evidence management; operational handoff. | Delivery is verified, residual limitations are disclosed, continuing responsibilities have owners, and temporary authority/resources are released. | Keep the work open with a named missing obligation. Report partial delivery accurately. |

The change contract is executable enough to answer these questions:

- What observable behavior must change, and what must remain valid?
- Which paths, systems, data, and external actions may be affected?
- What evidence is required for each claim?
- What consequential actions are preauthorized?
- How much time, computation, money, concurrency, and exposure may be consumed?
- Where must the result arrive?
- What constitutes recovery, and who owns any remaining consequences?

For example, “reject invalid requests before modifying stored data” requires evidence for rejection **and** evidence that stored data remains unchanged. A test of the returned error alone leaves part of the requirement unverified.

Every evidence record identifies the contract version, candidate, relevant baseline, verifier, environment, result, and limitations. Evidence is invalidated when an input on which it depends changes. Reuse requires an explicit dependency argument.

**4. Human involvement.** No per-change human action is inherently required when the change fits an existing delegation and has adequate acceptance and recovery mechanisms.

Human involvement belongs at these specific boundaries:

| Boundary | Human decision or action | Why it remains human |
|---|---|---|
| **Before admission: establish delegation** | An accountable owner sets objectives, acceptable consequences, permitted actions, and resource limits. This can be standing policy. | The executing system cannot legitimately create its own authority or decide whose losses are acceptable. |
| **Stage 3: unresolved intent or value choice** | Decide between materially different outcomes that existing intent and policy do not resolve. | Technical investigation can establish consequences; it cannot establish an unstated preference or consent. |
| **Stages 4 or 10: exceed delegated authority** | Approve a concrete proposal that expands scope, exposure, cost, access, or irreversible consequences. | A successful design does not authorize additional consequences. Some organizations may deliberately make certain actions nondelegable. |
| **Stages 3 or 11: acceptance requires human judgment** | Supply a judgment that has no adequate delegated oracle—for example, whether an unfamiliar interaction achieves the intended experience. | Observable proxies may support the decision without establishing the owner’s actual preference. |
| **Recovery: choices exceed the incident mandate** | Choose among losses or interventions outside preauthorized recovery policy. | An incident does not confer unlimited emergency authority. |

A request for a human decision must contain the concrete alternatives, relevant evidence, consequence differences, recommendation, and exact authority being requested. “Please review everything” is an inadequate escalation.

Routine debugging, reviewing, integrating, and promotion remain autonomous when their gates are satisfied. If a human declines or does not answer, the work stays in its explicitly safe waiting state; silence never expands authority.

**5. Failure, safety and recovery.** These are controller mechanisms, not instructions to “be careful.”

**Bound the whole work graph.** Each root change receives limits for elapsed time, active computation, spend, concurrent workers, external operations, and repair cycles. Children reserve resources from that budget; creating another worker, conversation, or recovery attempt does not create a fresh allowance.

Stage limits sit inside the root limit. Reserve capacity for containment, recovery, and reporting before spending the implementation allowance. When the remaining allowance cannot support another useful attempt plus safe termination, stop.

An illustrative policy could allow three repair cycles and two transient infrastructure retries. Those numbers are policy choices; their crucial property is that all paths consume enforced counters.

**Distinguish failure classes.**

| Failure class | Treatment |
|---|---|
| Transient infrastructure failure | Retry with bounded backoff when the action is safe to repeat. |
| Reproducible implementation defect | Diagnose, make a targeted repair, and rerun affected checks. |
| Invalid assumption or requirement | Return to grounding, contract, or design. |
| Missing authority or unresolved preference | Wait for a specific decision. |
| Unknown consequential action result | Reconcile external state before attempting another action. |
| Resource exhaustion | Stop new work, preserve evidence, and perform reserved cleanup or recovery. |

Repeated attempts must carry a diagnosis, new evidence, or a materially different approach. Fingerprints of failures and candidates detect cycles such as alternating between two broken implementations. Rephrasing the prompt does not count as progress.

**Use durable state rather than conversation history.** Persist the contract, baseline, plan, artifact identities, findings, budgets, pending actions, and transition history outside agent context. A replacement agent reconstructs its task from those records.

A stage follows a durable protocol:

1. Record the intended action and its prerequisites.
2. Obtain a scoped execution lease.
3. Execute and capture artifacts and receipts.
4. Independently evaluate the result.
5. Commit the state transition.

On restart, reconcile unfinished actions with actual state. Process exit and heartbeat activity establish liveness, not success.

Leases carry generation numbers. A worker from an earlier generation cannot commit after its replacement takes ownership. Terminated or abandoned workers lose credentials and write access.

**Do not assume exactly-once external execution.** Prefer idempotency keys and destination-side conditional updates. If a crash occurs after an external effect but before its receipt is saved, query the destination to determine what happened.

Where duplicate detection and reconciliation are impossible, an ambiguous result blocks automatic replay. Guessing can duplicate a payment, publication, deletion, or migration.

**Prevent stale-state actions.** Check the current shared baseline immediately before integration and the destination state immediately before promotion. Use conditional writes or equivalent concurrency controls. If prerequisites changed, invalidate affected evidence and rebuild the candidate.

Approval is scoped to a contract, action, artifact, destination, and validity period. Changing any consequential element can require new authorization.

**Separate authority from candidate-controlled content.**

- Grant stage-specific credentials and access; revoke them when the stage ends.
- Keep production access out of implementation and ordinary test execution.
- Execute candidate code in an isolated verification environment.
- Protect controller policy, acceptance criteria, verifier configuration, and authoritative result records from candidate writes.
- Treat repository text, retrieved content, dependency output, and logs as data unless an authenticated authority has granted them instruction status.
- Filter secrets and sensitive data from evidence and reporting.

Independent reviewers inspect primary artifacts and evidence under separate permissions. They do not accept the implementer’s explanation as proof. A separate review role can use the same model in fresh context, but that offers limited protection against correlated reasoning errors.

**Prepare recovery before promotion.** Promotion requires:

- A last known acceptable state.
- A tested restoration or compensation procedure.
- Access and reserved capacity to execute it.
- Conditions that trigger it.
- Verification that recovery achieved its purpose.

For data changes, include compatibility, retention, and restoration checks. Prefer changes that let old and new versions coexist before removing the old representation.

Some effects cannot be undone. Sending information externally, destroying unique data, or causing downstream decisions may survive a rollback. Those effects require explicit authority and exposure limits before execution.

**Limit exposure and measure outcomes.** Promote in bounded increments when the delivery target permits it. Predetermine stop thresholds and observation windows. Compare against a baseline or control where necessary to distinguish change effects from background variation.

Automatic recovery should respond to sufficiently diagnostic evidence. Ambiguous signals can justify freezing expansion and escalating rather than performing a potentially harmful rollback.

**Make completion precise.** Report one of: completed, awaiting observation, waiting for decision, blocked, failed, or cancelled. A code-only delivery may finish when the contracted artifact is accessible and verified. A runtime change requires the contracted target-side observation.

A completed observation window supports bounded acceptance. It does not establish permanent correctness. Continuing monitoring must have an owner and action policy after the development run closes.

**6. Capability catalogue.** These are distinct lifecycle capabilities. Some require agent judgment; others must be enforced by deterministic infrastructure.

| Group | Capability | Purpose |
|---|---|---|
| **Intent and authority** | Intent interpretation | Recover the requested outcome, constraints, exclusions, and unresolved choices. |
| | Authority and risk reasoning | Determine permitted actions and classify consequences by exposure, reversibility, uncertainty, and sensitivity. |
| | Context reconstruction | Establish relevant behavior, dependencies, operating conditions, and authoritative constraints. |
| | Acceptance design | Turn outcomes into evaluation methods with explicit coverage and proof limits. |
| **Engineering** | Engineering design | Choose a feasible approach and examine consequential alternatives and failure modes. |
| | Decomposition and scheduling | Create dependency-aware work units with ownership, interfaces, budgets, and integration obligations. |
| | Environment preparation | Construct isolated, reproducible execution and verification environments. |
| | Baseline assessment | Characterize existing behavior and failures before attributing effects to the change. |
| | Implementation | Modify code, configuration, tests, and documentation coherently within scope. |
| | Migration engineering | Change persisted state and interfaces while preserving compatibility and recovery options. |
| **Verification and assurance** | Test engineering | Exercise requirements, regressions, boundaries, and failure behavior with meaningful checks. |
| | Differential diagnosis | Distinguish candidate defects, baseline defects, environmental faults, and invalid assumptions. |
| | Security and privacy analysis | Examine access, data flows, dependencies, attack surfaces, and unintended disclosure. |
| | Performance and resource analysis | Verify latency, capacity, consumption, and other contracted operating limits. |
| | Independent review | Challenge implementation, requirement interpretation, and evidence without implementer control. |
| **Delivery and operation** | Integration and concurrency control | Reconcile shared-state changes and prevent overwriting concurrent work. |
| | Artifact construction and provenance | Produce identifiable delivery artifacts tied to their source, dependencies, and build inputs. |
| | Promotion control | Apply an authorized candidate to the intended destination with bounded exposure and a verified receipt. |
| | Runtime and outcome verification | Check the delivered result and its effects at the actual acceptance boundary. |
| | Rollback and compensation | Restore acceptable operation or mitigate effects that restoration cannot undo. |
| **Control and continuity** | Durable orchestration | Enforce stage transitions and persist authoritative progress independently of agent context. |
| | Budget and loop enforcement | Account for resources across the work graph and stop exhausted or cycling attempts. |
| | Crash and action reconciliation | Recover interrupted work without duplicating consequential effects or admitting stale workers. |
| | Evidence and dependency management | Maintain traceable evidence and invalidate it when relevant prerequisites change. |
| | Least-privilege execution | Restrict credentials, writes, network access, and execution rights to the current obligation. |
| | Untrusted-input handling | Prevent acquired content and candidate output from acquiring unintended authority. |
| | Decision escalation | Present bounded, actionable questions when progress requires authority or unavailable judgment. |
| | Closeout and operational handoff | Record delivered status, disclose limitations, release temporary resources, and assign continuing responsibilities. |

Multiple agents are optional. Separation of permissions, evidence, and decision rights is mandatory where the same actor could otherwise manufacture its own acceptance.

**7. Trade-offs and open questions.** The strongest tensions are these.

| Tension | Design choice | Remaining uncertainty |
|---|---|---|
| **Autonomy versus wrong objectives** | Spend early effort on the change contract; escalate consequential ambiguity. | Detecting that an apparently precise request encodes the wrong user objective remains difficult. |
| **Assurance versus cost and latency** | Scale evidence to consequences; reuse evidence only through explicit dependency analysis. | Predicting hidden impact cheaply enough for routine work is unresolved. |
| **Independent review versus correlated errors** | Separate control and context; combine behavioral checks, analysis, and adversarial review. | Different agents can share the same blind spots. Model diversity alone does not establish independence. |
| **Adaptation versus stable enforcement** | Let agents revise plans within the contract; keep authority, budgets, and gate rules externally controlled. | A rigid controller can force needless escalation when circumstances change. |
| **Small changes versus coherent delivery** | Prefer small reversible increments, each preserving required invariants. | Some cross-system changes cannot be meaningfully validated or delivered piecemeal. |
| **Fast promotion versus recoverability** | Require recovery readiness and use bounded exposure. | Recovery itself can cause harm, especially after data mutations or external effects. |
| **Finite acceptance versus delayed effects** | Define observation windows and continuing ownership. | Rare faults and long-term product outcomes exceed a finite development run’s evidence. |
| **Auditability versus confidentiality** | Preserve artifact identities and sufficient evidence under controlled retention. | Choosing the minimum record that supports investigation without retaining excessive sensitive data is context-dependent. |

I am least sure about **acceptance-oracle quality**, **cheap assessment of hidden impact**, and **meaningful independence between automated reviewers**. Strong execution control cannot compensate for a weak definition of success.

The design therefore makes uncertainty operational: it changes required evidence, limits exposure, or produces a specific decision request. It cannot be converted into success merely because the workflow reached its last stage.

