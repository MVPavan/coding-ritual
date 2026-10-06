I made no file edits. I also read the spine and principles in `harness_lifecycle/adlc/GUIDE.md`, because two of my changes depend on them.

## 1. Coverage verdict

The proposal covers the main path of a single change well, from incoming request to merged change. It is thin at both ends and puts four things in the wrong place.

**Missing:**
- **Packaging and publishing.** Rollout assumes a running service. A library, CLI or plugin is published, not ramped.
- **Incident response.** Monitoring raises incidents, but nothing handles them.
- **Maintenance.** There are no dependency upgrades, no removal of old feature flags, and no retirement of unused software. That leaves the SDLC "Maintain" phase almost empty.
- **Documentation and refactoring.**
- **Validating against intent.** Nothing checks that the change does what was actually asked, as opposed to merely passing the spec.
- **Continuity of context and memory across sessions and agents.** This is a core agentic concern.

**Misplaced:**
- **Slicing is in Construction.** In your own spine, "Plan increments" comes before the build loop. GUIDE A-08 also puts the human's plan approval between slicing and code.
- **Authorization appears twice.** It is in Triage ("authorize starting") and again in Delivery. It is also wrong where it sits: under the current A-07 setting, merging is gated too, so approval is not a single step after Integration.
- **Closeout is in Operations.** It mixes three things: closing the work item, session handoff, and recording lessons.
- **Improvement is buried as a sub-stage**, even though "the agent improving over time" is part of the stated scope.

**Miscellaneous is a junk drawer.** Communication cuts across every stage. Aliases are a property of how a skill is packaged, not a category. Housekeeping splits into three different stages.

**Naming rules:**
- Rule 1 (no repeated words) passes on names. It fails on meaning: Research vs Grounding, Decision vs Architecture, and two authorization gates.
- Rule 3 (activities in order) fails on artifact nouns that are not activities: Intent, Evidence, Acceptance, Decision.
- Rule 3 also fails on order: Triage "sizes" the work before Intent has fixed the scope.

## 2. Changes

| Change | Item | Reason |
|---|---|---|
| Rename | Decision → **Roadmapping** | "Decision" names an outcome, not an activity. It also blurs into Architecture. Roadmapping says "spans many changes" and produces the input to Intake. |
| Add | **Ideation** (Discovery) | Generating options and running throwaway prototypes or spikes is different from gathering evidence. Brainstorming and prototype skills need a home. |
| Redefine | Triage | Drop "authorize starting" (it is a gate, now in Guardrails). Limit sizing to what is needed to pick a route; real sizing happens in Decomposition. That fixes the order problem with Intent. |
| Rename | Intent → **Clarification** | Intent is an artifact noun; the activity is clarifying. |
| Rename | Acceptance → **Specification** | "Acceptance" is ambiguous: approving work, or writing criteria? It also clashes with Intake's "accepted work". I kept your spine's position: criteria plus frozen failing tests, after Grounding. |
| Move + Rename | Slicing → Design / **Decomposition** | It happens once, before the per-increment loop. The plan-approval gate (A-08) belongs at the Design→Construction boundary. |
| Redefine | Diagnosis | Root-cause analysis only. "Tune performance" is implementation work once the cause is known. |
| Add | **Refactoring**, **Documentation** (Construction) | Both are distinct activities with their own skills. Neither had a home. |
| Rename | Evidence → **Testing** | Evidence is an artifact noun. Testing is the activity and is recognisable against the SDLC "Test" phase. |
| Add | **Validation** (Verification) | Checks against the original intent, not just the spec, so a change that meets the spec but is wrong gets caught. |
| Move | Authorization → Guardrails | Approval gates occur at plan, merge, publish and destructive actions (A-07). A gate that recurs is cross-cutting, not one step in order. |
| Add | **Packaging** (Delivery) | Versioning, build, changelog and release notes. This covers software that is published rather than deployed. |
| Redefine | Rollout | Publish *or* deploy, with the undo ready. |
| Split + Move | Closeout | Closing the work item moves to the end of Delivery. Handoff moves to Continuity. Lessons move to Retrospective. |
| Add | **Response**, **Maintenance** (Operations) | Incident mitigation, plus upkeep: dependencies, removing old flags (Integration creates them), and retirement. |
| Split + Move | Improvement → stage 7, **Improvement** | It splits into Retrospective → Codification → Evaluation. The loop is only closed if a change to the agent is measured. Codification also covers first-time harness setup. |
| Redefine | Orchestration | Remove "resumption" (moves to Continuity). Add model and skill routing. |
| Split | Guardrails | Tracking and the decision trail move to Continuity. Approval gates move in. |
| Add | **Continuity** (cross-cutting) | Context, memory, handoff, tracking and resumption across sessions, compaction and agents. This was unmapped. |
| Move | Communication → cross-cutting | It applies in every stage. |
| Split | Teaching | Explaining the change or the codebase goes to Communication. Teaching a topic for its own sake goes to Tutoring, outside the lifecycle. |
| Remove | Housekeeping | Repo scaffolding → Implementation. Harness setup → Codification. Upkeep → Maintenance. |
| Remove | Aliases | Make it a tag on the skill record, mapped to the target skill's sub-stage. |
| Add | **Capabilities** (outside the lifecycle) | General tool skills (pdf, xlsx, browser, desktop control) will appear in every harness. They need a named non-lifecycle bucket. |
| Rename | bands → **Cross-cutting**, **Outside lifecycle** | Avoids the meta word "stages" inside a stage name. |

## 3. Final proposed list

Stages 3 and 4, plus Integration, repeat once per increment. Every other stage runs once per change.

| # | Stage | Sub-stage | One-line definition |
|---|---|---|---|
| 0 | **Discovery** | | Study a problem space before any specific change exists. |
| | | Research | Gather evidence: literature, prior art, other codebases, data. |
| | | Ideation | Generate candidate approaches and test the risky ones with throwaway prototypes or spikes. |
| | | Roadmapping | Choose a direction spanning many changes, record the decision, and sequence it into candidate work. |
| 1 | **Intake** | | Turn an incoming request into accepted, bounded work. |
| | | Triage | Classify, deduplicate, prioritise and route the request, sizing it only enough to choose a route. |
| | | Clarification | Agree the goal, scope and non-goals with the human. |
| 2 | **Design** | | Decide how the change will be shaped before code is written. |
| | | Grounding | Read this repository's relevant code, constraints and current behaviour as a baseline. |
| | | Architecture | Choose the structure, interfaces, data model and trust boundaries. |
| | | Specification | Write the acceptance criteria and the failing tests that define "done", then freeze them. |
| | | Decomposition | Cut the work into small, ordered, independently verifiable increments: the plan the human approves before code. |
| 3 | **Construction** | | Produce each increment. |
| | | Implementation | Write the code, and its unit tests, for the increment. |
| | | Diagnosis | Find the root cause of a failure, regression or slowdown before changing code. |
| | | Refactoring | Restructure code without changing behaviour once the tests pass. |
| | | Documentation | Update the user, API and in-code documentation the change affects. |
| 4 | **Verification** | | Prove the change is correct before anyone relies on it. |
| | | Testing | Run the tests and automated checks, and record the results that back each claim. |
| | | Review | Get an independent critique from a context that did not write the change. |
| | | Validation | Check the finished change against the original intent, not just the spec. |
| 5 | **Delivery** | | Get the verified change into use safely and close the work. |
| | | Integration | Merge into the mainline, switched off where it alters runtime behaviour. |
| | | Packaging | Version and build the artifact, with its changelog and release notes. |
| | | Rollout | Publish or deploy, exposing the change gradually with the undo ready. |
| | | Closeout | Close the tracked work, record the outcome, and file follow-ups. |
| 6 | **Operations** | | Keep shipped software healthy. |
| | | Monitoring | Watch behaviour in use and raise findings or incidents. |
| | | Response | Mitigate incidents (rollback, kill switch), then send the cause to Intake as new work. |
| | | Maintenance | Keep the software current: dependency upgrades, flag removal, dead-code cleanup, retirement. |
| 7 | **Improvement** | | Make the agent better at future work. |
| | | Retrospective | Review finished work and incidents for mistakes and recurring friction. |
| | | Codification | Turn recurring lessons into agent instructions, skills, rules, hooks or checks, including first-time harness setup. |
| | | Evaluation | Measure whether the agent and harness actually improved, with evals or before/after runs. |
| X | **Cross-cutting** | | Concerns that apply in every stage. |
| | | Orchestration | Coordinate multi-step, parallel or unattended work: delegation, loops, model and skill routing. |
| | | Continuity | Keep work state and context intact across sessions, compaction and agents: tracking, handoff, memory, decision trail. |
| | | Guardrails | Limit what the agent may do: permissions, sandboxes, budgets, and human approval at irreversible steps. |
| | | Communication | How the agent reports status, explains its work and the codebase, and writes for humans. |
| O | **Outside lifecycle** | | Skills that are not development lifecycle work. |
| | | Capabilities | General tool skills usable anywhere: document formats, browsers, desktop control. |
| | | Tutoring | Teaching the human a topic for its own sake. |

How the stages map to the SDLC vocabulary:
- **Plan:** Discovery and Intake
- **Design:** Design
- **Build:** Construction
- **Test:** Verification
- **Deploy:** Delivery
- **Maintain:** Operations and Improvement

## 4. Open questions

1. **Is merge gated or not?** GUIDE A-07 requires authorization to merge. The spine puts a single "Authorize" after "Integrate (dark)". Under either answer I put approval in Guardrails, but the GUIDE contradicts itself and should be fixed.
2. **Is Improvement a stage, or just a source of new work?** A change to the harness is itself a change that goes through Design → Delivery. I kept it as a stage because Retrospective and Evaluation don't happen anywhere else. If you treat the harness as just another product, it collapses into Intake.
3. **What is the mapping rule for skills that span several sub-stages?** Examples: systematic-debugging covers Diagnosis and Response; review covers plan review and code review. One primary sub-stage plus secondary tags, or many-to-many? Decide before mapping.
4. **Does Validation earn its place?** It does if you want an explicit check of "is this what was asked" (agent or demo). If the plan gate plus the approval gate already cover that in your model, and no harness skill maps to it, drop it.
5. **How should the GUIDE spine's vocabulary line up with these names?** It uses Admit, Ground, Qualify, and "Release (ramped)", where Release means what I call Rollout. It will drift from these names. Either rename the spine to match, or add a mapping row, so "Release" doesn't mean two different things.