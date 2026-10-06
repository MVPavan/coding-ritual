## 1. Coverage verdict

**Revise.** The proposal covers the main change-delivery path and agent learning, but it does not yet cover the entire lifecycle: prioritization and resourcing, validation with users, release preparation, incident response and recovery, and retirement need explicit homes. Its labels already avoid repeated words and are mostly nouns; the larger problems are ambiguous activities, misplaced boundaries, and an overly linear sequence. “Evidence” names an output, “Intent” names an agreement, and “Aliases” names catalog metadata. Planning is hidden inside Intake and Construction, while Operations mixes ongoing service work with finite task closeout. Keep a cross-stage band, but remove Miscellaneous: most of its contents belong elsewhere, and genuinely unrelated skills should be marked outside the ADLC.

## 2. Changes

Severity here concerns the taxonomy’s fitness for mapping skills, not software safety.

| Change | Item | Reason |
|---|---|---|
| Redefine | Overall ordering | **Major:** no truthful lifecycle makes every activity occur once in a fixed sequence. Use a normal progression with explicit iteration, optional activities, and feedback. |
| Redefine | Discovery | **Minor:** discovery can precede a specific request or be commissioned by one; “before any specific change exists” is unnecessarily restrictive. |
| Rename | Decision → Selection | **Minor:** decisions occur everywhere; this activity specifically selects a problem or opportunity worth pursuing. |
| Rename | Intake → Planning | **Major:** gives the common SDLC planning phase a recognizable home and expands beyond processing incoming requests. |
| Redefine | Triage | **Major:** classify and route provisionally; detailed sizing and authorization need enough understanding of the request first. |
| Rename | Intent → Clarification | **Minor:** names the activity that produces agreement about intent. |
| Add | Prioritization | **Major:** choosing when to act, what to defer, and how much capacity to allocate is missing. |
| Split | Acceptance → Specification and Validation | **Major:** defining success before implementation and determining whether the result meets user needs are different activities. |
| Redefine | Architecture | **Major:** explicitly include interaction design, data, interfaces, operational constraints, and prototypes; structure alone is insufficient. |
| Move | Slicing → Design, renamed Decomposition | **Major:** increments and dependencies should shape implementation before construction starts. |
| Add | Preparation | **Minor:** repository setup, reproducible environments, tooling, and scaffolding need a lifecycle home. |
| Split | Diagnosis → Debugging and Optimization | **Minor:** explaining and correcting failures differs from improving measured performance. |
| Rename | Evidence → Testing | **Minor:** evidence is the output; exercising and checking the change is the activity. Record results here, but retain evidence throughout the lifecycle. |
| Redefine | Review | **Minor:** retain independent critique, but allow it for requirements, designs, and plans as well as completed code. |
| Rename | Delivery → Deployment | **Minor:** improves recognition against the requested SDLC vocabulary. Define it broadly enough to include published artifacts. |
| Redefine | Integration | **Major:** merging is insufficient; resolve interactions and reverify the integrated result. Disabled runtime behavior is a release strategy whose applicability must be explicit. |
| Move | Authorization → cross-stage Governance | **Major:** approval belongs before every action that requires it, including some integrations; a single late gate is insufficient. |
| Add | Packaging, Readiness, Distribution | **Major:** merging and rollout omit artifact production, operational preparation, and getting artifacts into their destination. |
| Rename | Operations → Maintenance | **Minor:** aligns with the common vocabulary while retaining ongoing operational responsibilities. |
| Add | Servicing, Response, Recovery, Assessment | **Major:** observing problems is not enough; include routine upkeep, incident handling, restoration, and evaluation of actual outcomes. |
| Move | Closeout → cross-stage band | **Major:** completed, rejected, cancelled, and blocked work all need state disposition; closeout cannot wait for ongoing monitoring to finish. |
| Move | Improvement → cross-stage band | **Major:** agents can learn from discovery, failed implementation, reviews, and incidents—not only shipped changes. |
| Add | Retirement | **Major:** deprecation, migration, resource removal, and data disposition are absent. |
| Rename | Across stages → Crosscutting concerns; Guardrails → Governance | **Minor:** both become noun phrases; Governance describes authority, budgets, tracking, and accountability more precisely. |
| Merge | Communication and Teaching | **Minor:** explanations are a communication activity, not a separate lifecycle phase. |
| Add | Documentation | **Minor:** durable specifications, runbooks, user guidance, and handoffs need an explicit home distinct from conversational communication. |
| Move | Housekeeping → Preparation or Servicing | **Minor:** initial setup and ongoing maintenance have different purposes and belong in the lifecycle. |
| Remove | Miscellaneous and Aliases | **Minor:** aliases are package relationships, not activities; unrelated skills belong outside the taxonomy rather than in a catch-all phase. |

The proposed late authorization step also conflicts with the supplied [ADLC guide’s authority rule](harness_lifecycle/adlc/GUIDE.md), which requires authorization for actions including merge and publication. Moving authorization into Governance makes those gates applicable at the correct boundaries.

## 3. Final proposed list

All labels below are nouns or noun phrases, with no word repeated between labels. The central sequence corresponds to **Plan → Design → Build → Test → Deploy → Maintain**, with discovery before it and retirement after it.

Rows show the normal order within a phase. They are not mandatory one-pass gates: testing can precede implementation, failed checks return to construction, integration triggers renewed verification, and maintenance activities recur or run concurrently. The X band has no chronological order.

| # | Stage | Sub-stage | One-line definition |
|---|---|---|---|
| 0 | **Discovery** | | Establish which problems or opportunities deserve investment. |
| | | Research | Gather evidence about users, needs, existing systems, alternatives, and feasibility through investigation and experiments. |
| | | Selection | Compare opportunities and choose a direction, including deciding not to proceed. |
| 1 | **Planning** | | Turn a candidate request into understood, prioritized, bounded work. |
| | | Triage | Classify the request, identify urgency and ownership, and route or reject it provisionally. |
| | | Clarification | Agree the intended outcome, affected users, scope, non-goals, constraints, and success measures. |
| | | Prioritization | Decide whether and when to proceed, allocating effort and capacity against competing work. |
| 2 | **Design** | | Define the intended behavior and technical approach before committing to implementation. |
| | | Grounding | Inspect relevant code, dependencies, interfaces, and current behavior to establish a reliable baseline. |
| | | Specification | Define behavior, quality requirements, acceptance criteria, and the checks that will demonstrate success. |
| | | Architecture | Choose system structure, interactions, interfaces, and data models, using prototypes where uncertainty warrants them. |
| | | Decomposition | Divide the approach into ordered, independently verifiable increments with dependencies and recovery provisions. |
| 3 | **Construction** | | Produce the artifacts required by each increment. |
| | | Preparation | Establish the repository, environment, tooling, and scaffolding needed to perform reproducible work. |
| | | Implementation | Create or change code, tests, configuration, infrastructure, and associated artifacts for the increment. |
| | | Debugging | Reproduce failures, identify their causes, and correct them at the owning layer. |
| | | Optimization | Improve measured performance or resource use while preserving required behavior. |
| 4 | **Verification** | | Establish whether the result satisfies its requirements and intended use. |
| | | Testing | Execute applicable automated and manual checks, recording results, coverage limits, and unresolved failures. |
| | | Review | Obtain independent critique of the artifacts, assumptions, and supporting evidence. |
| | | Validation | Evaluate representative workflows with users or accountable stakeholders to establish fitness for the intended purpose. |
| 5 | **Deployment** | | Move an accepted change into its intended environment and use. |
| | | Integration | Combine the change with its target baseline, resolve interactions, and reverify the combined result. |
| | | Packaging | Produce identifiable, reproducible release artifacts with their required dependencies and configuration. |
| | | Readiness | Confirm approvals, ownership, observability, support arrangements, and applicable migration and recovery procedures. |
| | | Distribution | Publish or install approved artifacts and apply associated environment or data changes under controlled procedures. |
| | | Rollout | Introduce the change to intended users, observe its effects, and expand, halt, or reverse exposure as appropriate. |
| 6 | **Maintenance** | | Sustain the software in use and evaluate its continuing value and health. |
| | | Monitoring | Observe reliability, security, cost, performance, and usage, producing actionable findings. |
| | | Servicing | Perform authorized routine upkeep such as backups, renewals, access administration, and operational support. |
| | | Response | Assess and contain incidents, coordinate action, and communicate their impact. |
| | | Recovery | Restore acceptable service and data integrity, then verify that restoration succeeded. |
| | | Assessment | Compare actual outcomes with intended benefits and identify corrective, preventive, or further development work. |
| 7 | **Retirement** | | Withdraw software or capabilities while resolving their user, dependency, and data obligations. |
| | | Deprecation | Announce withdrawal, identify affected consumers, and establish the transition conditions and timeline. |
| | | Migration | Move users, dependencies, and required data to their agreed destination where a replacement is needed. |
| | | Decommissioning | Remove the retired capability and resources, resolve data retention or disposal, and confirm closure. |
| X | **Crosscutting concerns** | | Activities that support multiple phases without forming a separate chronological phase. |
| | | Orchestration | Coordinate agents, dependencies, execution loops, context handoffs, pauses, and resumption. |
| | | Governance | Apply authority, permissions, budgets, risk controls, tracking, and decision accountability at relevant boundaries. |
| | | Communication | Exchange decisions, questions, explanations, teaching, and progress with humans or other agents. |
| | | Documentation | Create and maintain durable knowledge, specifications, user guidance, operational instructions, and decision records. |
| | | Improvement | Turn recurring evidence into evaluated changes to agent instructions, skills, tools, and workflows. |
| | | Closeout | Record the work’s disposition, preserve evidence and resumable state, and transfer any remaining responsibility. |

Three mapping rules keep this usable:

- **Allow multiple mappings.** A security skill may support Design, Testing, Review, and Monitoring; security, accessibility, and privacy are also useful secondary tags.
- **Route new changes back through the lifecycle.** Maintenance findings and proposed agent improvements generate new work; they do not bypass planning, verification, or authorization.
- **Keep package metadata separate.** Resolve aliases to their targets, mark stubs as unimplemented, and explicitly mark genuinely unrelated skills as outside the ADLC.

## 4. Open questions

1. **Will the catalog permit multiple mappings per skill?** I recommend yes, with one primary activity where useful; forced exclusivity will misclassify broad skills.
2. **Does the catalog need to retain genuinely non-development skills?** If yes, retain them with an explicit “outside ADLC” status rather than adding a miscellaneous lifecycle band.