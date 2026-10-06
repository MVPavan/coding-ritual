I read `GUIDE.md` and the council stage table and capability catalogue, and skimmed the playbook. Statements about what skills other harnesses contain are from general knowledge, not checked against the reference submodules.

## 1. Coverage verdict

The spine is sound, but the set does not yet cover the whole lifecycle. Both the proposal and my list pass rule 1 literally. The gaps and misfilings are:

- **Work above a single change:** nothing covers turning a direction or PRD into separate work items.
- **Implementation planning:** it is hidden under "Slicing", though "the plan" is the most common artifact in every harness.
- **Git and release mechanics:** commit, PR, CI and conflict resolution have no explicit home, and "Rollout" excludes plain deploy or publish.
- **Incident response:** Monitoring raises incidents, but nothing contains them.
- **State across sessions:** memory, handoff and resumption are split between Closeout and Orchestration.
- **Ongoing maintenance:** dependency drift, scans and debt are filed under Miscellaneous as "not lifecycle work", although Maintain is one of your six anchor words.
- **Non-development skills:** office files, browser control and similar have no bucket.
- **Things that should not be here as written:** "tune performance" inside Diagnosis, "codebases" inside Research, and "authorize starting" inside Triage, which collides with Authorization.
- **Rule 3:** Intent, Evidence and Acceptance are artifacts, not activities. Architecture precedes Acceptance, which reverses your own spine (Specify, then Plan increments).

An emergency hotfix lane is also absent, but that is a path through the stages, not a naming gap.

## 2. Changes

| Change | Item | Reason |
|---|---|---|
| Add | Roadmapping (Discovery) | Splitting a direction into separate requests has no home; Slicing only cuts inside one change. |
| Redefine | Research | Drop "codebases", which overlaps Grounding. Boundary: no admitted change yet → Research; admitted change → Grounding. |
| Redefine | Decision | Include generating options, so ideation has a home. |
| Redefine | Triage | "Authorize starting" → "admit"; one concept should not sit in two sub-stages. |
| Rename | Intent → Framing | Intent is an artifact, also produced by Monitoring (A-12); "Intake/Intent" misreads easily in a mapping table. |
| Redefine | Grounding | Add external docs, bug reproduction and workspace setup (council stage 2). |
| Rename + Move | Acceptance → Specification, before Architecture | "Acceptance" reads as UAT, approval, or "accepted work" in Intake's definition. Your spine puts the contract before the how. |
| Rename + Move | Slicing → Planning, last in Design | It is decided before code and approved at the plan gate (A-08), so it belongs in Design. "Slicing" under-describes a plan (order, checks, undo). |
| Redefine | Implementation | Add per-increment tests and docs; otherwise TDD and doc-writing skills have no home. |
| Redefine | Diagnosis | Cause-finding only. Tuning is Implementation driven by a measured shortfall. |
| Rename | Evidence → Qualification | Evidence is an artifact produced in several stages; the activity is qualifying the candidate (council's term). |
| Redefine | Review | The built change only. Critique of a spec or plan maps to the sub-stage that produces it. |
| Redefine | Integration | Name commit, PR, CI and conflict resolution explicitly. |
| Redefine | Authorization | Make it an activity: prepare the decision (evidence, effect, undo) and get approval bound to one artifact and destination. |
| Rename | Rollout → Release | Covers deploy and publish as well as gradual exposure; libraries and plugins have no ramp. |
| Split | Operations → Operations + Learning | Closing work and improving the agent are not operations. "The agent improving over time" is one of your two stated endpoints and deserves a stage. |
| Redefine | Monitoring | Include scheduled scans and dependency drift, so maintenance detection is lifecycle work. |
| Add | Response (Operations) | Containment and rollback are operational actions; only the repair re-enters at Intake. |
| Split | Closeout → Closeout + Retrospective | Closing this work item and extracting lessons are different activities with different skills. |
| Redefine | Improvement | Any evidence-driven change to instructions, skills, hooks or evals, including pruning and regression-testing (A-10, A-11). |
| Redefine | Orchestration | Add routing to skills, agents and models; move resumption to Continuity. |
| Add | Continuity (Across) | Memory, handoff, checkpoints and resumption are one concern with many skills. |
| Split | Guardrails → Guardrails + Tracking | Limits and enforcement are a different concern from work-item state and the decision trail. |
| Split | Housekeeping → Setup | Setup stays in Miscellaneous; maintenance moves to Monitoring and then Intake. |
| Add | Utilities (Misc) | General-purpose skills (office files, browsing, scheduling) need a bucket if every skill must map. |

Both bands earn their place: Across stages holds a large share of real harness skills, and Miscellaneous makes the mapping total. Use Miscellaneous only when nothing else fits.

## 3. Final proposed list

| # | Stage | Sub-stage | One-line definition |
|---|---|---|---|
| 0 | **Discovery** | | Study a problem space before any specific change exists (SDLC: Plan). |
| | | Research | Gather evidence: literature, prior art, experiments and throwaway prototypes. |
| | | Decision | Generate options, compare them, and choose a direction that spans many changes. |
| | | Roadmapping | Break the chosen direction into separate, ordered requests that each enter Intake. |
| 1 | **Intake** | | Turn one incoming request into admitted, well-defined work (SDLC: Plan). |
| | | Triage | Classify the request, check for duplicates, size and risk-tier it, route it, and admit or reject it. |
| | | Framing | Agree the goal, scope and non-goals with the human; record them as the intent. |
| 2 | **Design** | | Decide what "done" is and how the change will be made, before code is written (SDLC: Design). |
| | | Grounding | Learn the relevant code, docs, constraints and current behaviour; reproduce the problem; prepare the workspace. |
| | | Specification | Write the acceptance criteria and failing tests that define "done". |
| | | Architecture | Choose the structure, interfaces and data model, testing risky choices with a spike. |
| | | Planning | Cut the work into small, ordered increments, each with its own check and undo. |
| 3 | **Construction** | | Produce the change, one increment at a time (SDLC: Build). |
| | | Implementation | Write the code, its tests and its docs for each increment. |
| | | Diagnosis | Find the root cause of a failure or measured shortfall, wherever it surfaced. |
| 4 | **Verification** | | Prove the change is correct before anyone relies on it (SDLC: Test). |
| | | Qualification | Run the checks against the exact candidate and record the results behind each claim. |
| | | Review | Get an independent critique of the built change from a context that did not write it. |
| 5 | **Delivery** | | Get the verified change into use safely (SDLC: Deploy). |
| | | Integration | Commit, open the pull request, pass CI, resolve conflicts and merge, switched off where it alters runtime behaviour. |
| | | Authorization | Present the evidence, effect and undo for the irreversible step; a human approves that artifact and destination. |
| | | Release | Deploy or publish the change and expose it gradually where it runs live, with the undo rehearsed. |
| 6 | **Operations** | | Keep the shipped change healthy until the work can be closed (SDLC: Maintain). |
| | | Monitoring | Watch the system in use and the codebase at rest (scans, dependency drift); raise findings as new requests. |
| | | Response | Contain an incident by stopping exposure or rolling back, and file the repair as a new request. |
| | | Closeout | Report the outcome and residual risks, clean up, transfer ownership and close the work item. |
| 7 | **Learning** | | Make the next run better than this one (SDLC: Maintain). |
| | | Retrospective | Extract what went wrong and right from the finished work and its records. |
| | | Improvement | Turn recurring lessons into changed instructions, skills, hooks and evals; prune stale ones; regression-test the change. |
| X | **Across stages** | | Concerns that apply to every stage. |
| | | Orchestration | Run long, multi-step or unattended work: routing to skills, agents and models; delegation; loops; parallel agents. |
| | | Continuity | Carry state across sessions and contexts: memory, handoff notes, checkpoints, resumption. |
| | | Tracking | Keep work-item status, dependencies, the run record and the decision trail. |
| | | Guardrails | Enforce limits on the agent (permissions, budgets, sandboxes, hooks) and escalate to a human when one is hit. |
| M | **Miscellaneous** | | Skills that are not lifecycle work; use only when nothing above fits. |
| | | Communication | How the agent writes and talks. |
| | | Teaching | Explaining concepts to the human. |
| | | Setup | Bootstrapping or configuring a repository, toolchain or harness. |
| | | Utilities | General-purpose capabilities unrelated to a software change: office files, browsing, scheduling. |
| | | Aliases | Shortcuts and stubs that point to other skills. |

## 4. Open questions

1. **Is Authorization one sub-stage or a recurring gate?** Your A-07 setting requires approval for commit, push and merge, and intent and plan approvals also exist. I kept one sub-stage for the irreversible step and treated the others as exit criteria of Framing, Planning and Integration.
2. **May a skill map to more than one sub-stage?** TDD spans Specification and Implementation; brainstorming spans Framing and Architecture; security review is a lens on Architecture, Review and Monitoring. Without a primary/secondary rule you will be pushed to add topic entries such as Security and Documentation, which I deliberately left out.
3. **"Planning" or "Slicing"?** "Planning" matches what every harness calls the artifact, but your SDLC anchor "Plan" maps to Discovery and Intake. The playbook has the same collision (Stage 1 "Plan", with `plan.md` produced in Design). If it bothers you, keep "Slicing" but still move it into Design.
4. **Does Diagnosis belong in Construction or Across stages?** It is entered on demand from Grounding (reported bug), Qualification (failed check) and Monitoring (incident). I left it in Construction, where it most often happens.
5. **Does Improvement make the change or only propose it?** By A-10 and A-12, an agent-configuration change is itself a change that should re-enter at Intake. If so, Improvement's definition should end at "propose", and Learning is a short stage.