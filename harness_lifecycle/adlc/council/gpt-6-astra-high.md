An autonomous development lifecycle should be a **bounded, evidence-driven state machine**. Agents exercise judgment inside it; a separate execution controller enforces permissions, budgets, prerequisites, and stop conditions.

The unit of work is more than a code change. It is a **change contract, an implementation, supporting evidence, and a verified delivery outcome**. A change is complete only when all four agree.

The design below allows routine work to proceed without human intervention. Human involvement occurs where delegated authority or defensible evidence runs out.

The lifecycle follows six first principles:

| Principle | Reasoning |
|---|---|
| **Success must have an external reference.** | An agent’s belief that it solved the problem cannot establish whether the requested behavior exists or is useful. |
| **Ability does not imply authority.** | Access to a system does not establish permission to change it; authorization must constrain each consequential action. |
| **Evidence has a scope.** | A passing check supports particular claims about a particular artifact and environment; it does not establish universal correctness. |
| **Uncertainty requires bounded exposure.** | Since verification is incomplete, limit how much harm a wrong decision can cause before detection and containment. |
| **Progress must survive the worker.** | Crashes, interruptions, and replacement agents must not erase decisions or cause external actions to execute twice. |
| **Autonomy must be finite and accountable.** | Every attempt consumes resources and changes risk; retries require a reason, a limit, and an attributable decision. |

These imply three distinct responsibilities:

- **Agents** interpret requests, investigate, design, implement, and challenge results.
- **The controller** maintains durable state and enforces permissions, budgets, transitions, and evidence freshness.
- **An accountable owner** establishes objectives and delegated authority, and resolves exceptions that exceed them.

These are responsibility boundaries, not necessarily separate services or separate agents. A model may propose a transition; it cannot authorize itself by declaring that its work is safe.

The lifecycle is:

```text
Request
   |
   v
[1 Admit and bound authority]
   |
   v
[2 Define success] <---------------------------+
   |                                          |
   v                                          |
[3 Establish current reality] -----------------+ incompatible assumptions
   |
   v
[4 Design and plan] <--------------------------+
   |                                          |
   v                                          |
[5 Implement] <---------------------+          |
   |                               |          |
   v                               |          |
[6 Verify and challenge] -----------+ defect   |
   |                                          |
   +------------------------------------------+ design failure
   v
[7 Assemble and validate final candidate]
   |                         |
   |                         +--> 3 / 4 / 5 if integration changes assumptions
   v
[8 Authorize delivery]
   |                         |
   |                         +--> missing evidence: relevant earlier stage
   |                         +--> outside authority: WAIT_FOR_DECISION
   v
[9 Deliver with bounded exposure]
   |                         |
   v                         +--> contain / reconcile / recover
[10 Observe and accept]
   |                         |
   |                         +--> contain, then new bounded repair through 3–8
   v
[11 Close and transfer responsibility]
   |
   v
Verified outcome + durable evidence + residual obligations


Cross-cutting at EVERY stage:
  authority • resource budgets • isolation • evidence provenance
  durable checkpoints • concurrency control • secret/data protection
  cancellation • policy enforcement • escalation

Execution modes, separate from stages:
  RUNNING | WAITING | RECOVERING | STOPPED | TERMINAL

Every back-edge consumes an explicit retry allowance.
Every mutation requires authority at the moment of execution.
```

Before stage 1 exits, create a durable work record. Refine it as the task progresses, with versioned changes:

- **Change contract:** intended outcome, acceptance predicates, non-goals, constraints, and unresolved assumptions.
- **Authority envelope:** permitted resources and actions, prohibited effects, spending limits, release limits, and escalation owner.
- **Risk assessment:** affected parties, blast radius, data sensitivity, reversibility, detectability, and recovery time.
- **Execution state:** current stage, dependencies, active workers, leases, checkpoints, and remaining budgets.
- **Evidence ledger:** each claim linked to its checks, results, artifact identity, environment, provenance, and limitations.
- **Delivery and recovery plan:** exposure steps, stop conditions, recovery actions, and ownership after completion.

An acceptance predicate should specify **what is observed, under what conditions, against which threshold, and for how long**. “Works correctly” is insufficient. “Unauthorized users cannot retrieve another user’s document through any supported retrieval interface” is concrete enough to drive investigation and testing.

The stages have the following contracts. Stages may execute within one worker session, but their exit conditions remain distinct.

| Stage and goal | Inputs | Outputs | Capabilities needed | Exit criterion | On failure |
|---|---|---|---|---|---|
| **1. Admit and bound authority** — establish whether work may begin. | Request; requester identity; standing policies; available resources. | Work identity; accountable owner; initial authority envelope; total budget; initial risk assessment. | Request interpretation; authority assessment; risk triage; resource estimation. | Investigation is authorized, its scope is bounded, and escalation has an owner. | Reject prohibited work. Wait for missing authority. Offer a narrower authorized scope when useful. |
| **2. Define success** — turn intent into a testable contract. | Request; stakeholder context; existing commitments. | Acceptance predicates; non-goals; assumptions; constraints; explicit treatment of uncertainty. | Requirements analysis; ambiguity detection; acceptance design; clarification. | Material interpretations are resolved or covered by explicit, low-risk assumptions; success can be evaluated. | Investigate resolvable uncertainty. Escalate consequential value choices. Stop if no acceptable outcome can be defined. |
| **3. Establish current reality** — discover the actual system and baseline. | Contract; source and configuration; interfaces; operational evidence; prior decisions. | Relevant system map; baseline results; dependencies; affected surfaces; known failures; feasibility findings. | Source exploration; behavior tracing; dependency analysis; baseline execution; provenance assessment. | There is enough current evidence to explain the proposed change’s likely effects and distinguish new failures from existing ones. | Repair the investigation environment within scope; revise the contract if assumptions fail; stop when required evidence is inaccessible. |
| **4. Design and plan** — choose a bounded route to the outcome. | Contract; baseline; risk assessment; authority and budget. | Design; work graph; verification strategy; rollout and recovery plan; explicit checkpoints. | Design reasoning; decomposition; estimation; experiment design; compatibility and migration analysis. | Critical uncertainties have been tested or contained; every work item has an output and check; delivery and recovery are feasible within bounds. | Run bounded feasibility experiments. Reduce scope or replan within authority. Escalate infeasibility or required scope changes. |
| **5. Implement** — produce the smallest coherent change. | Approved plan; pinned baseline; isolated workspace; scoped credentials. | Candidate code/configuration; tests; necessary documentation; dependency changes; local check results. | Code modification; test construction; debugging; dependency management; documentation. | Planned behavior is implemented; local checks pass; unexplained or unrelated changes are absent. | Diagnose and repair within the allowance. Return to design for structural problems. Preserve a checkpoint before stopping. |
| **6. Verify and challenge** — attempt to falsify the candidate’s claims. | Candidate; contract; baseline; risk-selected verification plan. | Claim-to-evidence report; findings; resolved defects; residual uncertainty. | Test execution; adversarial review; security and compatibility analysis; evidence appraisal. | Required predicates have adequate evidence; prohibited conditions are absent; remaining uncertainty fits policy. | Return defects to implementation and design failures to planning. Do not weaken acceptance conditions merely to obtain a pass. |
| **7. Assemble and validate final candidate** — establish that the deliverable works as a whole. | Verified components; current integration target; dependency state. | Immutable deliverable; integrated results; provenance; exact delivery manifest. | Integration; conflict resolution; reproducible assembly; system validation; change-impact analysis. | Evidence applies to the actual deliverable and relevant current target state, including interactions between components. | Reconcile concurrent changes, rerun affected checks, and return semantic conflicts to investigation or design. |
| **8. Authorize delivery** — decide whether this exact release may proceed. | Deliverable identity; evidence; authority envelope; operational readiness; recovery plan. | Recorded release decision, bound to artifact, target, exposure limits, and expiry conditions. | Policy evaluation; evidence appraisal; readiness assessment; exception preparation. | The controller establishes that every required condition holds, or an authorized person explicitly resolves a permitted exception. | Return missing evidence for repair. Wait for authority when needed. Deny delivery when a non-waivable condition fails. |
| **9. Deliver with bounded exposure** — apply the authorized change. | Authorized manifest; scoped release credentials; current target state. | Delivery receipts; actual deployed/distributed identity; exposure state; executed action journal. | Release execution; progressive exposure; state reconciliation; migration execution; containment. | Intended recipients or environments receive the authorized artifact; immediate health and integrity checks pass. | Stop expansion, contain impact, and execute an authorized recovery path. Reconcile uncertain actions before retrying. |
| **10. Observe and accept** — establish that the delivered behavior meets its contract. | Delivery state; acceptance predicates; telemetry; observation window. | Outcome evidence; regressions or incidents; explicit acceptance status. | Observability; outcome evaluation; anomaly diagnosis; incident response. | Required behavior holds through the specified window and exposure; relevant safety and compatibility conditions hold. | Contain first. Recover if warranted. Start a bounded repair through the earlier gates; report failure or incomplete evidence honestly. |
| **11. Close and transfer responsibility** — leave a maintainable result. | Accepted outcome or explicit unsuccessful disposition; evidence ledger; residual obligations. | Final report; retained artifacts; operational instructions; ownership transfer; credential and workspace cleanup. | Evidence synthesis; documentation; responsibility transfer; resource cleanup. | The outcome is accurately recorded, ongoing obligations have owners, and temporary privileges/resources are removed. | Keep closure pending for missing ownership or records. If cleanup fails, revoke dangerous access and record remaining cleanup work. |

Verification depth should follow consequences. A text correction may need a rendering check and inspection. A change to financial calculations may require reference examples, invariants, boundary cases, and reconciliation. A destructive data migration needs tested recovery or an explicitly authorized forward-repair strategy.

The lifecycle should not impose the same ceremony on both. It should impose the same requirement: **evidence and containment proportionate to the consequences of being wrong.**

Human involvement belongs at four boundaries:

| Boundary | Exactly when a human is needed | Why autonomy should stop there |
|---|---|---|
| **Establishing or changing delegated authority** | Initially, and whenever the task requires privileges, exposure, spending, or commitments outside existing policy. | An agent cannot legitimately grant itself additional authority. Standing delegation can cover many future tasks. |
| **Resolving consequential intent** | At stage 2, or after new discoveries, when plausible interpretations lead to materially different outcomes and no existing policy resolves the choice. | Investigation can establish facts; it cannot manufacture the owner’s preferences or consent. |
| **Accepting exceptional consequences or uncertainty** | At stage 8 or during recovery, when a permissible exception exceeds delegated risk limits. | Accountability for consequences belongs to an authorized person. The agent should provide a concrete candidate, evidence, alternatives, and recovery limits before asking. |
| **Making an explicitly human acceptance judgment** | At stage 10 when the contract requires a person’s experience, judgment, or legally required decision. | A proxy score cannot silently substitute for the judgment the contract actually requires. |

An irreversible action does **not** automatically require a fresh human approval if specific standing authorization already covers it. It does require a higher standard of preparation and strict adherence to that authorization.

Likewise, humans need not routinely approve plans, review every patch, or press a release button. Those steps can be autonomous when authority and evidence are sufficient. Human review is itself fallible; it should answer a defined question rather than serve as a ritual.

If a required decision never arrives, the task waits until its deadline, then preserves its state and stops safely. **Silence never expands authority.**

Failure handling needs mechanisms outside the model’s willingness to cooperate.

**Bound total expenditure.** Set a task-wide ceiling for elapsed time, compute, monetary cost, external actions, and maximum exposure. Allocate stage and worker budgets from that ceiling; starting another worker or replanning cannot reset it. Reserve resources for diagnostics, containment, recovery, and a final report. When the remaining budget reaches the reserve, stop feature work.

**Require informative retries.** Each retry records:

```text
Observed failure
Proposed cause
Changed action or new information
Expected discriminating result
Remaining retry and resource allowance
```

An unchanged retry is allowed only for a classified transient failure, with bounded backoff. Repeating the same failure without new evidence triggers replanning or escalation. Local limits and a task-wide limit prevent agents from avoiding exhaustion by bouncing between stages.

**Separate activity from progress.** Heartbeats establish that a worker is alive. Progress requires a changed artifact, resolved uncertainty, completed check, or another named milestone. A live worker with no such progress can still be stalled. Timeouts must apply to both worker activity and external calls.

**Persist before consequential effects.** Before an external mutation, record its intent, parameters, authorization, and operation identity. Afterward, record its receipt and observed state. If a crash occurs between execution and acknowledgement, mark the operation’s outcome as unknown and inspect the target before repeating it.

Use idempotent operations and deduplication where available. Where they are unavailable, an uncertain outcome may require reconciliation or human intervention. A retry does not establish that an operation executes only once.

**Fence stale workers.** Give work ownership a lease and generation number. After recovery or reassignment, older generations lose permission to write. Check that shared state still matches the expected version before applying changes; otherwise return to reconciliation. This prevents a delayed worker from overwriting a newer result.

**Resume from verified state.** A replacement worker reads the durable contract and journal, inspects actual workspace and external state, and determines which evidence remains valid. It does not rely on the previous worker’s narrative or replay every previous action.

**Contain execution.** Use isolated workspaces, constrained network access, resource limits, and credentials scoped to the current action. Tests and build steps execute potentially hostile code and require isolation too. Repository text, dependency output, logs, and retrieved documents are evidence inputs; they cannot grant authority or alter governing policy.

The agent must not be able to rewrite its controller, approval rules, or authoritative evidence store as an incidental part of an ordinary change.

**Bind evidence to what was checked.** Record artifact identities, relevant inputs, commands or procedures, environment, and result provenance. Preserve failures as well as successes. Modified artifacts invalidate affected evidence; material changes to the integration or delivery environment require revalidation.

Protect the verifier from the implementation’s influence where practical. Derive checks from the contract and external behavior, review changes to tests, and use established reference cases or independent measurements when available. A separate reviewer helps, but agreement between agents is not proof of independence.

**Prepare recovery before exposure.** Recovery must account for code, persistent data, emitted events, external integrations, and compatibility between old and new versions. Restoring a binary does not undo an email or reconstruct deleted records.

Choose among:

- Reversal, when effects can actually be undone.
- Compensation, when a new action can offset an earlier effect.
- Forward repair, when reversal would be unsafe.
- Containment and escalation, when no authorized safe repair exists.

Backups require a credible restore path. Recovery actions themselves need bounded authority and checks. If recovery fails, stop further mutation, limit exposure where possible, preserve evidence, and transfer the incident to the designated owner.

**Report outcomes precisely.** Useful dispositions include `COMPLETED`, `REJECTED`, `CANCELED`, `FAILED`, and `REVERTED`; waiting and recovery are intermediate states. A successful rollback means recovery succeeded, not that the requested change succeeded.

Keep delivery and product outcomes separate. If a business outcome requires weeks of observation, report “delivered; outcome pending” and assign continuing observation. Do not convert early technical health into a claim that the product objective has been achieved.

The consolidated capability catalogue is below. These are distinct responsibilities; one agent may supply several, while enforcement capabilities should reside in trusted execution machinery.

| Group | Capability | Purpose |
|---|---|---|
| **Intent and authority** | Request interpretation | Extract the requested outcome, context, and implied constraints. |
| | Requirements and acceptance design | Convert intent into observable predicates, non-goals, and explicit assumptions. |
| | Authority assessment | Determine which actions are permitted by whom, on which resources, under which conditions. |
| | Risk assessment | Identify consequences, exposure, reversibility, and detection limits. |
| | Decision preparation | Present unresolved choices with concrete alternatives, evidence, and consequences. |
| **Investigation and design** | System exploration | Locate relevant behavior, interfaces, dependencies, and governing constraints. |
| | Baseline characterization | Establish current behavior and pre-existing failures. |
| | Provenance assessment | Distinguish authoritative evidence from stale, untrusted, or unsupported claims. |
| | Design and decomposition | Choose an implementation approach and divide it into verifiable work. |
| | Feasibility experimentation | Resolve consequential uncertainty with bounded experiments. |
| | Compatibility and migration analysis | Plan safe changes across interfaces, versions, and persistent data. |
| | Resource estimation | Allocate time, cost, and recovery reserves under a global ceiling. |
| **Construction** | Code and configuration modification | Implement a coherent change within its authorized scope. |
| | Test construction | Create checks that exercise contract behavior and relevant failure modes. |
| | Debugging | Distinguish symptoms from causes and test repair hypotheses. |
| | Dependency management | Control introduced components, versions, and associated risks. |
| | Integration and assembly | Produce the exact deliverable from compatible components and inputs. |
| **Assurance** | Verification execution | Run appropriate functional, structural, security, performance, and compatibility checks. |
| | Adversarial review | Search for counterexamples, omitted requirements, and dangerous assumptions. |
| | Evidence appraisal | Determine which claims the available results support and where uncertainty remains. |
| | Change-impact analysis | Identify which prior evidence becomes invalid after a change. |
| **Delivery and operation** | Release planning and execution | Apply an authorized artifact through bounded exposure steps. |
| | Observability and outcome evaluation | Detect regressions and assess delivered behavior against acceptance predicates. |
| | Incident diagnosis and containment | Limit ongoing harm while determining the system’s actual state. |
| | Recovery execution | Reverse, compensate, or repair effects within authorized limits. |
| | Responsibility transfer | Leave usable instructions and explicit ownership for ongoing obligations. |
| **Execution control** | Durable workflow management | Preserve stages, dependencies, decisions, and checkpoints across interruptions. |
| | Budget and loop enforcement | Stop execution when resource or retry limits are reached. |
| | Isolation and credential control | Restrict what a worker can access or change. |
| | Concurrency control | Prevent stale or competing workers from making incompatible mutations. |
| | External-state reconciliation | Resolve whether an interrupted action took effect before retrying. |
| | Evidence recording and reporting | Retain attributable records and communicate outcomes without overstating proof. |
| | Cleanup and revocation | Remove temporary resources and privileges without losing required evidence. |

The main trade-offs remain substantial:

- **Specification effort versus speed.** Fully formalizing ordinary requests is wasteful. I would require executable acceptance predicates for consequential behavior and explicit assumptions elsewhere. The unresolved challenge is detecting when an apparently minor ambiguity has major consequences.
- **Verification cost versus residual risk.** More checks consume time and can introduce unreliable gates. I would choose checks by plausible failure and consequence, with mandatory minimums for critical actions. Calibrating those minimums requires operational evidence.
- **Independent challenge versus coordination cost.** Separate reviewers can catch omissions, but can also share the same mistaken assumptions. I would prioritize diversity of evidence—reference behavior, invariants, external observation—over the number of reviewers.
- **Small changes versus coherent design.** Smaller deliveries reduce exposure, but excessive fragmentation can leave incompatible intermediate states. Each increment should preserve declared invariants; some changes need coordinated activation.
- **Reversibility versus delivery speed.** Compatibility layers, staged migrations, and recovery rehearsal add work. I would pay that cost where persistent state or broad exposure makes failure expensive.
- **Autonomy versus conservative stopping.** Aggressive stopping burdens humans; permissive execution can compound errors. I would expand delegated authority using measured outcomes for defined classes of work, never an agent’s self-reported confidence.
- **Fast closure versus meaningful observation.** A finite observation window cannot establish lifetime correctness. Closure must transfer monitoring and response obligations explicitly, and state exactly what the window established.

I am least certain about **evaluating open-ended product quality**, **measuring correlated verifier failures**, and **calibrating safe delegation across unfamiliar systems**. Those are limitations of the evidence available, not gaps that another workflow stage automatically fixes. Where they matter, the lifecycle should expose the uncertainty, constrain consequences, and preserve the owner’s ability to decide.

