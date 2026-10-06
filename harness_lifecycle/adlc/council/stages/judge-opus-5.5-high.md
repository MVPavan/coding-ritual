# Council judgement: ADLC stages and sub-stages

## 1. Agreement

All four members (or three of four, where noted) agreed on these points.

**Coverage gaps the proposal has:**
- **Incident response.** Monitoring raises incidents, but nothing contains them. All four added a Response activity.
- **Publishing.** Rollout assumes a running service, but libraries, CLIs and plugins are published instead. A, B and C added Packaging; D widened Release to cover this.
- **Upkeep in the Maintain phase.** Dependency upgrades, flag removal, scans and debt have no home. Each member gave this a home in their own way.
- **State across sessions.** Memory, handoff and resumption are split between Closeout and Orchestration. B and D added Continuity; C added Contextualization.
- **Out-of-scope skills.** General tool skills (office files, browser control, desktop control) need a bucket outside the lifecycle. All four said so.

**Renames and moves:**
- **Intent → an activity noun.** Clarification (A, B), Scoping (C), Framing (D). Intent names an artifact, not an activity.
- **Evidence → an activity noun.** Testing (A, B, C), Qualification (D). Same reason.
- **Acceptance → Specification.** "Acceptance" is ambiguous: it can mean approval, user acceptance testing, or Intake's "accepted work".
- **Slicing moves into Design.** It happens before any code is written, and the plan-approval gate sits at the Design→Construction boundary.
- **Authorization should not appear twice.** It is both "authorize starting" in Triage and a sub-stage in Delivery. A, B and C made approval a recurring gate in the cross-cutting band. D kept it as a sub-stage but admits that merging and intent are also gated.
- **Diagnosis loses "tune performance".** B and D made it cause-finding only; A and C split Optimization out.
- **Closeout leaves Operations.** Three of four moved it.
- **Aliases is not a category.** It describes how a skill is packaged, not an activity. A, B and C said this.
- **Mapping needs a primary-plus-secondary rule.** Every member raised this.

## 2. Disputes

| Dispute | Options | Verdict and why |
|---|---|---|
| **Stage names** | Rename to SDLC words: Intake→Planning, Delivery→Deployment, Operations→Maintenance (A, C). Keep the originals (B, D). | **Keep Intake, Delivery and Operations.** Rule 4 asks that stages be *recognisable*, not identical to the SDLC words. Calling Intake "Planning" makes a skill named `write-plan` look like it belongs there, when the plan artifact is produced in Design (D's point). "Deployment" reads as service-only, and Delivery has to cover publishing too. |
| **Where Improvement goes** | Its own stage (B, D). Cross-cutting (A). A sub-stage of Maintenance (C). | **Its own stage.** The brief names "the agent improving over time" as an endpoint of the lifecycle. Its activities run in order (Retrospective → Codification → Evaluation) and happen nowhere else. A is right that the *inputs* come from every stage, but that is true of most stages. |
| **Measuring agent improvement** | Evaluation as a sub-stage (B). Folded into Improvement (D). | **Evaluation as a sub-stage (B).** The loop is only closed if the change to the agent is measured. Eval skills exist and need their own home. |
| **Where Closeout goes** | Cross-cutting (A, C). End of Delivery (B). Operations (D). | **End of Delivery.** Operations is about the software; the *work item* closes once it is delivered. Rejected or cancelled work jumps straight to Closeout. That is a path through the stages, not a reason to make Closeout cross-cutting: it still happens once, at the end. |
| **Authorization** | A cross-cutting gate (A, B, C). A sub-stage (D). | **Cross-cutting gate, under Governance.** Approvals happen at intent, plan, merge, publish and destructive actions. Three members independently say GUIDE A-07 gates merging. **I did not verify GUIDE.md in this session.** |
| **Guardrails vs Governance; separate Tracking** | Guardrails (B, D). Governance (A, C). Tracking as its own entry (D). | **Governance, and no separate Tracking.** Approval is not a limit, and "Governance" is an activity noun. Work state and the decision trail belong in Continuity (B). D's Tracking/Continuity boundary is fuzzy. |
| **Name for the old Slicing** | Decomposition (A, B). Sequencing (C). Planning (D). | **Decomposition.** "Planning" collides with the Plan anchor, which D concedes. Harness "plan" skills map to Decomposition. |
| **Order inside Design** | Architecture before Specification (the proposal, B). Specification before Architecture (D). | **Specification first (D).** By D's reading, the proposal's own spine runs Specify → Plan increments: decide what "done" is before deciding how. B claims to keep that position but lists Architecture first, which contradicts itself. |
| **Validation** | Add it (A, B, C). Leave it out (D). | **Add it, named Validation.** "Acceptance" would collide with Intake again. If no harness has a skill for it, the empty slot itself shows a gap, which is what the comparison is for. |
| **Splitting up deploy** | Packaging, Readiness, Distribution, Rollout (A). Packaging, Readiness, Release, Confirmation (C). Packaging, Rollout (B). A single Release (D). | **Integration plus Release.** Versioning, changelogs and confirming the live state are almost always one "release" skill. Readiness belongs to Governance and Confirmation to Release. Three members proposed Packaging, but majority is not proof: no member showed skills that do packaging alone. |
| **Retirement** | Its own stage (A, C). Inside Maintenance (B). Missing (D). | **Inside Maintenance (B).** Agent skills for deprecation or decommissioning are rare. Folding it in still covers it with less structure. |
| **Discovery sub-stages** | Research + Selection (A, C). Research + Decision + Roadmapping (D). Research + Ideation + Roadmapping (B). | **Research + Roadmapping.** Roadmapping covers both choosing a direction and breaking it into requests (B's definition). Option generation and spikes go in Research and Architecture. |
| **Where Communication goes** | Cross-cutting (A, B, C). Miscellaneous (D). | **Cross-cutting.** It applies in every stage. Tutoring for its own sake goes out of scope (B's split). |
| **Separate upkeep vs filing it as new work** | A Maintenance sub-stage (B). Detect only, then file a new request (D). | **A Maintenance sub-stage.** D's principle is sound: an upgrade is a change. But dependency-bump and flag-cleanup skills exist and need a single home, and Retirement needs one too. |

## 3. Weak or wrong points

**A:**
- Over-built: 44 entries, five deploy sub-stages, and a three-part Retirement stage.
- Servicing (backups, certificate renewals) is human ops work that agent skills rarely target.
- Prioritization overlaps Triage.
- A removes Miscellaneous but then needs an "outside ADLC" status, which is the same thing under another name.
- Calling the stage "Planning" causes the plan-artifact collision described above.

**B:**
- Refactoring and Documentation as separate sub-stages are not needed; Implementation already covers them.
- Ideation duplicates Research and Architecture spikes.
- Its Specification ordering contradicts its own reason.
- "Outside lifecycle" and "Cross-cutting" break the noun grammar (rule 2).

**C:**
- Moving Grounding and Specification into Planning drops the "failing tests that define done" contract.
- Making Improvement a sub-stage of Maintenance buries a lifecycle endpoint the brief names.
- Contextualization is clumsy where Continuity is clear.
- Assistance is too vague to map skills to.

**D:**
- Keeping Authorization as a sub-stage contradicts D's own open question about A-07.
- Aliases is kept as a category, though it is packaging metadata.
- Communication sits in Miscellaneous even though it applies everywhere.
- Setup sits in Miscellaneous, which contradicts D's own argument that maintenance is lifecycle work.
- Tracking duplicates Continuity.

**All members:**
- **Unverified GUIDE references.** Claims about GUIDE A-07, A-08, A-10 and A-12 were not checked in this judgement; I had no file access in this session.
- **Unverified skill claims.** D says its claims about harness skills come from general knowledge, and the others give no checked evidence either.

## 4. Consolidated final list

Stages 3 and 4, plus Integration, repeat once per increment. Bands X and U are classification buckets, not phases, so their entries have no order.

| # | Stage | Sub-stage | One-line definition |
|---|---|---|---|
| 0 | **Discovery** | | Study a problem space before any specific change is admitted. |
| | | Research | Gather evidence: literature, prior art, other codebases, data, throwaway experiments. |
| | | Roadmapping | Compare options, choose a direction that spans many changes, and break it into ordered requests. |
| 1 | **Intake** | | Turn one incoming request into admitted, bounded work. |
| | | Triage | Classify, deduplicate, prioritise and route the request; size it only enough to choose a route; admit, defer or reject it. |
| | | Clarification | Agree the goal, scope, non-goals and success measures with the human. |
| 2 | **Design** | | Decide what "done" means and how the change will be shaped, before code is written. |
| | | Grounding | Learn this repository's relevant code, docs, constraints and current behaviour; reproduce the problem; prepare the workspace. |
| | | Specification | Write the acceptance criteria and the failing tests that define "done", then freeze them. |
| | | Architecture | Choose the structure, interfaces, data model and trust boundaries; test risky choices with a spike. |
| | | Decomposition | Cut the work into small, ordered increments, each with its own check and undo: the plan the human approves. |
| 3 | **Construction** | | Produce the change one increment at a time. |
| | | Implementation | Write the code, tests, docs, configuration and refactors for the increment. |
| | | Diagnosis | Find the root cause of a failure, regression or measured slowdown before changing code. |
| 4 | **Verification** | | Establish, with recorded evidence, that the change is fit to rely on. |
| | | Testing | Run the tests and automated checks against the exact candidate, and record the results behind each claim. |
| | | Review | Get an independent critique of the built change from a context that did not write it. |
| | | Validation | Check the finished change against the original intent, not just the spec. |
| 5 | **Delivery** | | Get the verified change into use and close the work. |
| | | Integration | Commit, open the PR, pass CI, resolve conflicts and merge, switched off where it alters runtime behaviour. |
| | | Release | Version and package, then deploy or publish; confirm the live state; expose gradually where it runs live, with the undo ready. |
| | | Closeout | Close the tracked work (delivered, rejected or cancelled), report the outcome and residual risks, and file follow-ups. |
| 6 | **Operations** | | Keep shipped software healthy. |
| | | Monitoring | Watch the system in use and the codebase at rest (health, usage, scans, drift), and raise findings. |
| | | Response | Contain an incident (roll back, kill switch, restore), then file the repair as a new request. |
| | | Maintenance | Keep software current or retire it: dependency upgrades, flag removal, dead-code cleanup, deprecation, decommissioning. |
| 7 | **Improvement** | | Make the agent better at future work. |
| | | Retrospective | Review finished work and incidents for mistakes and recurring friction. |
| | | Codification | Turn recurring lessons into instructions, skills, rules, hooks or checks, including first-time harness setup; prune stale ones. |
| | | Evaluation | Measure whether the agent and harness actually improved, with evals or before/after runs. |
| X | **Crosscutting concerns** | | Concerns that apply in every stage. |
| | | Orchestration | Coordinate multi-step, parallel or unattended work: delegation, loops, routing to skills, agents and models. |
| | | Continuity | Keep work state intact across sessions, compaction and agents: tracking, memory, handoff, checkpoints, resumption, the decision trail. |
| | | Governance | Apply permissions, sandboxes, budgets and human approval gates at intent, plan, merge, publish and destructive steps. |
| | | Communication | Report status, explain the work and the codebase, and write clearly for humans. |
| U | **Utilities** | | Skills that are not development lifecycle work; use only when nothing above fits. |
| | | Tooling | General tool skills: document formats, browsers, desktop control, scheduling. |
| | | Tutoring | Teaching the human a topic for its own sake. |

**Naming check:**
- No word repeats across the 10 stage or band names and the 28 sub-stage names.
- Everything is a noun or noun phrase.
- Stages 0–7 run in order, and the sub-stages within each run in order.

**SDLC mapping:**

| SDLC phase | Stages |
|---|---|
| Plan | Discovery, Intake |
| Design | Design |
| Build | Construction |
| Test | Verification |
| Deploy | Delivery |
| Maintain | Operations, Improvement |

## 5. Mapping rules

1. **One primary sub-stage per skill, by the outcome it produces.** Add at most two secondary tags, and only for genuine spans. For example, TDD is primary in Specification with Implementation as a secondary.
2. **Resolve aliases to their target and flag them.** Map an alias or stub to the target skill's sub-stage and record "alias" or "stub" on the skill record. Never make it a category.
3. **Map reviewers by what they review.** A reviewer of one artifact type maps to the sub-stage that produces that artifact: plan review → Decomposition, spec review → Specification. Only critique of the built change, or generic critique, maps to Review.
4. **Research vs Grounding.** No change admitted yet → Research. An admitted change → Grounding.
5. **Lenses are tags, not sub-stages.** Security, accessibility, performance and privacy are tags.
6. **Writing that produces an artifact goes with that artifact.** A PR description → Integration; a changelog → Release; docs → Implementation. Communication is only for general writing and explaining.
7. **Map setup skills by purpose.** Agent or harness configuration → Codification. Workspace for a change → Grounding. Scaffolding a new project → Implementation.
8. **Paths are not sub-stages.** Hotfixes, rejections and cancellations skip stages; they get no entries of their own.
9. **Keep empty sub-stages.** After mapping, a sub-stage with no skills in any harness is a coverage finding, not a reason to delete it.

## 6. Open questions for the human

1. **Is merging gated?** Members say GUIDE A-07 gates merging, while the spine shows a single "Authorize" after the dark integration. *I recommend* fixing the GUIDE so approval is a Governance gate at each configured boundary, and removing the single Authorize step from the spine.
2. **Does Improvement make the change itself, or only propose it?** *I recommend* that Codification makes changes to agent artifacts (instructions, skills, hooks, evals) directly, with Evaluation as the gate. Changes to tool *code* re-enter at Intake.
3. **Should the GUIDE spine's vocabulary be renamed to match?** The spine uses Admit, Ground, Qualify and "Release (ramped)". *I recommend* renaming the spine to these names so that "Release" means only one thing.
4. **Can a skill have more than one mapping?** All four members propose a primary sub-stage plus secondary tags. *I recommend* confirming rule 1 above (at most two secondaries) before the first mapping pass.
5. **Should Packaging be its own sub-stage?** *I recommend* keeping it folded into Release, and splitting it out only if the first mapping pass finds skills that package without releasing.