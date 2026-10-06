# Agentic development lifecycle (ADLC) guide

Use this guide when you design an autonomy feature, a workflow, or a skill that
moves work through the lifecycle without a person driving each step. It is
design guidance, not operating policy: `AGENTS.md` and the runtime
configuration still govern sessions.

## 0. How to read it

Every rule has two parts:

- **Principle (durable).** It holds however capable the model is, because it
  rests on accountability, irreversibility, conflict of interest, or audit, and
  none of these depend on model skill.
- **Setting (model-dependent).** It is a value tuned to what current models can
  do. Each setting carries an *as of* date and a *revisit when* trigger. Expect
  settings to move toward more autonomy. Principles do not move.

Do not hard-code a setting where a principle would do. When a new model
generation lands, run the revisit protocol in §4.

| Source (relative to this directory) | Role |
|---|---|
| `sources/anthropic-ai-native-sdlc-playbook.md` | Anthropic, "The AI-native SDLC playbook", 2026-08-21. Vendor practice for enterprise teams; it names product features that change quickly |
| `council/judge2-final-v2.md` | Our first-principles lifecycle (council v2, 2026). It supplies control and recovery machinery that the playbook omits |
| `council/stages/` | The stage and sub-stage names in §1 (council, 2026-10-06; the user later renamed Roadmapping → Charting and Closeout → Closure) |
| `skill-map.md` | Every skill from our harness, Pocock and pstack, mapped onto §1 |
| `document-model.md` | Which documents a project keeps per lifecycle stage, where they live, and what each holds |
| `../prompting-guides/GUIDE.md` | Rules for how to write instructions. This guide does not restate them |

## 1. The lifecycle

Each stage ends by committing one artifact. The next stage starts by reading
that artifact. [playbook:60] [playbook:72]

```text
Discovery → Intake → Design → [Building → Verification → Integration] × n
  → Release → Closure → Operations → Improvement
                ↑                         │
                └── finding / incident → new request (Triage)
Crosscutting under every stage: Orchestration · Continuity · Governance · Communication
```

Integration, Release and Closure are the three Delivery sub-stages. Integration
repeats once per increment, together with Building and Verification.
Stages are phases, and sub-stages are activities listed in the order they
happen. Paths such as a hotfix, a rejection or a cancellation skip stages; they
are not sub-stages. No word appears twice in the names below. An ADLC "stage"
is unrelated to the tracker's **Stage** (a child task, `.repo-context/CONTEXT.md`).

Each stage works on one unit, and the unit shrinks as work moves down:

```text
direction (many changes) → Discovery
  request (one ask)      → Intake
    change (admitted)    → Design
      increment (slice)  → Building, Verification, Integration
```

| # | Stage | Sub-stage | Definition |
|---|---|---|---|
| 0 | **Discovery** | | Study a problem space across many changes, before any one is admitted. Unit: a direction. |
| | | Research | Gather evidence from outside our system: literature, prior art, other codebases, docs for tools not yet in use, experiments. Open-ended. Home here, but any stage may enter it. |
| | | Charting | Compare options, choose a direction spanning many changes, and break it into requests, each of which gets its own Clarification. |
| 1 | **Intake** | | Turn one incoming request into admitted, bounded work. Unit: a request. |
| | | Triage | Classify, deduplicate, prioritise and route the request; size it only enough to route; admit, defer or reject. |
| | | Clarification | Agree the goal, scope, non-goals and success outcomes, in the human's words. A request too big for one change goes back to Charting. |
| 2 | **Design** | | Decide what "done" means and how the change will be shaped, before code is written. Unit: one admitted change. |
| | | Grounding | Learn what already exists in our system: code, docs, history and the reasons behind it, dependencies in use, current behaviour; reproduce the problem; prepare the workspace. Bounded by existing material. |
| | | Specification | Turn the agreed outcomes into acceptance criteria and failing tests that define "done", then freeze them. |
| | | Architecture | Choose the end state's structure, interfaces, data model and trust boundaries; test risky choices with a spike. |
| | | Decomposition | Cut the change into small, ordered increments that share its Specification and are never admitted alone; each has its own check and undo. This is the plan the human approves. |
| 3 | **Building** | | Produce the change one increment at a time. Unit: an increment. |
| | | Implementation | Write the code, tests, docs, configuration and refactors for the increment. |
| | | Diagnosis | Find the root cause of a failure, regression or measured slowdown before changing code. Home here, but entered on demand from Grounding, Testing and Monitoring. |
| 4 | **Verification** | | Establish, with recorded evidence, that the change is fit to rely on. |
| | | Testing | Run the tests and automated checks against the exact candidate; record the results behind each claim. |
| | | Review | Get an independent critique of the built change, against its spec, from a context that did not write it. |
| | | Validation | Check the finished change against the original intent from Clarification, not just the spec. |
| 5 | **Delivery** | | Get the verified change into use and close the work. |
| | | Integration | Commit, open the PR, pass CI, resolve conflicts and merge, switched off where it alters runtime behaviour. |
| | | Release | Version and package, deploy or publish, confirm the live state, expose gradually with the undo ready. |
| | | Closure | Close the tracked work (delivered, rejected or cancelled), report outcome and residual risk, file follow-ups. |
| 6 | **Operations** | | Keep shipped software healthy. Unit: the running system. |
| | | Monitoring | Watch the system in use and the codebase at rest (health, usage, scans, drift); raise findings. |
| | | Response | Contain an incident (roll back, kill switch, restore), then file the repair as a new request. |
| | | Maintenance | Find decay and schedule upkeep: dependency upgrades, flag removal, dead-code cleanup, decommissioning. Upkeep larger than a mechanical edit runs the lifecycle as a new request. |
| 7 | **Improvement** | | Make the agent better at future work. Unit: the agent and its harness. |
| | | Retrospective | Review finished work and incidents for mistakes and recurring friction. |
| | | Codification | Turn recurring lessons into instructions, skills, rules, hooks or checks (including harness setup); prune stale ones. |
| | | Evaluation | Measure whether the agent and harness actually improved, with evals or before/after runs. |
| X | **Crosscutting concerns** | | Concerns that apply in every stage. |
| | | Orchestration | Coordinate multi-step, parallel or unattended work: delegation, loops, routing to skills, agents and models. |
| | | Continuity | Keep work state across sessions, compaction and agents: tracking, memory, handoff, checkpoints, resumption, decision trail. |
| | | Governance | Permissions, sandboxes, budgets, and human approval gates at intent, plan, merge, publish and destructive steps. |
| | | Communication | Report status, explain the work and the codebase, write clearly for humans. |
| U | **Utilities** | | Skills that are not development lifecycle work; use only when nothing above fits. |
| | | Tooling | General tool skills: document formats, browsers, desktop control, scheduling. |
| | | Tutoring | Teaching the human a topic for its own sake. |

**Approval is a Governance gate, not a single stage.** It applies wherever A-07
and A-08 place it: intent (Clarification), plan (Decomposition), merge
(Integration), publish or deploy (Release), and destructive steps.

**SDLC anchors:** Plan = Discovery + Intake · Design = Design · Build = Building ·
Test = Verification · Deploy = Delivery · Maintain = Operations + Improvement.

### What each sub-stage answers

| Sub-stage | Answers | Output | Without it |
|---|---|---|---|
| Research | What is true or possible out there? | Cited evidence | Decisions rest on hunches |
| Charting | Which direction, and which requests? | Decision record and ordered requests | The wrong thing gets built, or one request grows huge |
| Triage | Do we take it, and where does it go? | Admit, defer or reject; a route | Work on duplicates or out-of-scope asks |
| Clarification | What exactly, and what not? | Intent in the human's words | The wrong problem gets solved |
| Grounding | What do we have today, and why is it like this? | Baseline notes, a reproduction | The design targets an imagined codebase |
| Specification | How will we know it is done? | Frozen criteria and failing tests | The goalposts move; tests get weakened |
| Architecture | What shape is the end state? | A design decision | Ad-hoc structure and rework |
| Decomposition | Which pieces, in what order? | Ordered increments | Big diffs that cannot be verified or reverted |
| Implementation | (none: make the increment) | A diff | — |
| Diagnosis | Why is it failing or slow? | Root cause with evidence | Patches that treat only the symptom |
| Testing | Do the checks pass on this exact candidate? | Recorded results | Unproven "it works" claims |
| Review | Would an independent mind accept it against the spec? | Findings by severity | The author's blind spots ship |
| Validation | Is this what was asked for? | A verdict against the intent | It meets the spec but misses the outcome |
| Integration | Is it safely in the mainline? | A merged commit | Breakage when work is combined |
| Release | Is it safely in users' hands? | A live version with the undo ready | A bad deploy with no way back |
| Closure | Is the work item finished and accounted for? | A closed item and follow-ups | Orphaned work and lost follow-ups |
| Monitoring | Is anything wrong now? | Findings | Silent failures |
| Response | How do we stop the harm now? | A contained incident and a repair request | Prolonged damage |
| Maintenance | What decays if nobody acts? | Upkeep requests or mechanical edits | Software rot |
| Retrospective | What went wrong or keeps hurting? | Lessons | Repeated mistakes go unnoticed |
| Codification | How do we stop the agent repeating it? | A changed instruction, skill, rule or hook | Lessons that never change behaviour |
| Evaluation | Did the agent actually get better? | Eval results | Changes that feel better but are not |
| Orchestration | Who or what does the next step? | Routing and delegation | Stalls and the wrong tool |
| Continuity | Can the work resume after a break? | State, handoff, checkpoints | Lost context |
| Governance | Is this allowed, and who must approve? | Allow, block or approval | Irreversible mistakes |
| Communication | Does the human understand? | Clear reports | Confusion and bad decisions |

### Boundaries between sub-stages

Most pairs are strictly separated by their unit or their output. Four are not,
and the definitions above say so.

| Pair | Boundary | Test |
|---|---|---|
| Charting ↔ Decomposition | Strict | A piece that needs its own goal and acceptance is a request (Charting); pieces that share one Specification are increments (Decomposition) |
| Charting ↔ Clarification | Strict | Many changes vs one request. Clarification sends an oversized request back to Charting |
| Research ↔ Architecture, Charting | Strict | Research produces evidence and never decides; the others decide. A Research experiment asks "is it possible?", an Architecture spike asks "does this design hold here?" |
| Architecture ↔ Decomposition | Strict | Changes the end state → Architecture; changes only the order or size of steps → Decomposition |
| Specification ↔ Testing | Strict | Writing the checks vs running them |
| Triage ↔ Orchestration | Strict | Routes a request vs routes a step |
| Closure ↔ Continuity ↔ Retrospective | Strict | Work finished vs work paused to resume vs a lesson for the agent |
| Research ↔ Grounding | Strict by source | Material already in our system (code, docs, history, dependencies in use) → Grounding; anything outside → Research. Brainstorming is neither: it generates options, so it belongs to Clarification or Charting |
| Clarification ↔ Specification | Soft | Outcomes in the human's words vs runnable checks; Grounding sits between them |
| Review ↔ Validation | Soft | Compared against the spec → Review; against the original intent → Validation |
| Grounding ↔ Diagnosis | Soft | Reproduce the symptom (what) vs explain the cause (why) |
| Diagnosis ↔ its stage | Overlap, stated | Entered on demand from Grounding, Testing and Monitoring |
| Maintenance ↔ the main path | Overlap, stated | An upkeep change larger than a mechanical edit runs the whole lifecycle as a new request |
| Integration ↔ Release | Collapses when merging is releasing | Record it as one step, for example skills installed straight from main |
| Codification ↔ Implementation | Collapses when the product is the harness | Classify by purpose: changing agent behaviour → Codification |

**Council v2 names** (`council/judge2-final-v2.md` §6.2 holds the stage
detail, exit criteria and back-edges):

| Council v2 name | Name here |
|---|---|
| Admit | Triage |
| Draft intent | Clarification |
| Ground | Grounding |
| Specify | Specification |
| Plan increments | Decomposition |
| Implement | Implementation |
| Qualify | Testing |
| Independent challenge | Review |
| Integrate | Integration |
| Authorize | a Governance gate |
| Release | Release |
| Observe | Monitoring |
| Close / transfer / learn | Closure, plus Retrospective and Codification |

The playbook's chain (intent → spec → plan → diff+tests → PR+findings →
incident) is the same lifecycle with fewer stages.

### Mapping skills onto the lifecycle

1. Each skill gets one primary sub-stage, chosen by the outcome it produces. Add at most two secondary tags, and only for genuine spans.
2. An alias or stub maps to its target's sub-stage and is tagged as an alias or stub. It is never a category.
3. A reviewer maps to the sub-stage that produces the artifact it reviews. Only critique of the built change is Review.
4. Research or Grounding is decided by source: material already in our system is Grounding, anything outside is Research.
5. Lenses (security, accessibility, performance, privacy) are tags, not sub-stages.
6. Writing that produces an artifact goes with that artifact. Communication covers general writing and explaining.
7. Map setup by purpose. Agent or harness configuration is Codification. A workspace for a change is Grounding. A new project scaffold is Implementation.
8. Keep a sub-stage even if no skill maps to it. An empty sub-stage is a coverage finding.

## 2. Principles and their current settings

| ID | Principle (durable) | Setting as of 2026-10 | Revisit when |
|---|---|---|---|
| A-01 | **Artifacts are the hand-off.** A stage is done when its artifact is committed. The accepted artifact triggers the next stage and is the audit trail. [playbook:60] [playbook:72] | Markdown in the repo for intent, spec, and plan; Beads for the work item | Never for the principle. Change the format only if a reader (human or agent) cannot use it |
| A-02 | **One source of truth per artifact.** Every other system holds a link or a copy. [playbook:178-183] | Repo docs for spec and plan; Beads for status | A second system starts holding authoritative state |
| A-03 | **The author never approves its own work.** Review and verification run in a separate context that did not produce the work. [playbook:290] [playbook:388] [council §6.2 stage 7] | Critic review per the `review` skill; the user picks the critic model | Never for the principle. The number of passes and lenses is a setting (A-14) |
| A-04 | **Protect the oracle.** The agent that fixes code cannot weaken the check on that code. Acceptance tests exist and fail before the fix, and test edits are shown first. [playbook:300] [playbook:303] [council §6.2 stage 3] | Enforced by review only; no hook yet | A hook that blocks test edits during a fix task exists |
| A-05 | **A must-hold policy needs a deterministic check.** A skill makes violations rare; a hook or script makes them close to impossible. [playbook:245] | Skills plus a dangerous-command hook | Never for the principle. Move a rule from skill to hook when it fails in practice |
| A-06 | **Control is deterministic; the model judges at the seams.** Detection, budgets, loop detection, and gating are code. The model is invoked once a condition fires. [playbook:521] [playbook:545] [council §6.5 [ctl]] | Workflow interpreter holds the inner loop | Never |
| A-07 | **Autonomy scales with reversibility × blast radius.** The agent acts up to the irreversible gate and cannot pass it. It never loosens its own limits. [playbook:491] [playbook:500] [council §6.3 H0] | Commit, push, merge, publish, and delete need the user's authorization | Gate telemetry (A-08) shows a delegable gate is rubber-stamped. Then propose delegation; the user decides |
| A-08 | **Humans decide intent, risk, and irreversible actions, at artifacts, off the hot path.** A gate presents a decision (options, recommendation, evidence, cost), not a diff. A timeout parks the work and never approves it. [playbook:256] [playbook:363] [council §6.3] | Human approves the plan before code; the user reviews artifacts after a batch | Approval rate and real catches per gate are measured. A gate with no catches over a sample moves later or becomes sampled |
| A-09 | **Work verifies itself before a person sees it.** Every task has a one-command check with a quantified target. "Done" means pasted evidence. [playbook:291-310] | `.repo-context/verification.md` claim → evidence table | Never for the principle |
| A-10 | **Agent configuration is code.** A change to instructions, skills, or hooks is regression-tested on real tasks. Each escape becomes a permanent eval. [playbook:318-334] | Trigger tests for skill descriptions only; no task evals | Evals exist. Until then, treat every skill change as unverified beyond its trigger test |
| A-11 | **Recurring mistakes become instructions; one-offs do not.** Instructions also get pruned. [playbook:192] [playbook:372] [prompting U-08] | Recorded at the second occurrence, in `.repo-context/learnings.md` or the owning skill | The model stops making the mistake. Then remove the instruction (prompting S-05) |
| A-12 | **A closed loop re-enters at Intent.** An autonomous trigger (monitor, scan, incident) writes a new intent artifact. It never changes code past the gates directly. [playbook:508] [playbook:524] [playbook:560] | Not built | Never for the principle |
| A-13 | **The undo comes before the change.** Rollback is the most-rehearsed path. Behaviour merges switched off and is ramped. [playbook:492] [council §6.2 stages 4, 10] | Git revert only; no flags | We ship runtime behaviour to users |
| A-14 | **Throughput is capped by verification capacity.** Add parallel streams only while review keeps up. [playbook:270] | 2–3 parallel streams per person | Review capacity changes: a better critic model, or sampling replaces full review |
| A-15 | **Every practice names a leading and a lagging indicator,** read from records that already exist (git, Beads, run ledger). [playbook:109-112] [playbook:170] | Not measured | Never for the principle |

## 3. Settings that are scaffolding for current models

The items below exist because today's models need them. Do not promote them
into principles. Each one is a candidate for removal once evals show the
default behaviour is good enough.

| Setting | As of | Revisit when |
|---|---|---|
| Plan mode before code; a person interrogates the plan [playbook:149] | 2026-08-21 | First-pass merge rate is high and plans are accepted without correction |
| Auto mode only after guardrails mature [playbook:173] | 2026-08-21 | — (it is a product feature; check current docs) |
| Instruction file under one page [playbook:193] | 2026-08-21 | Context cost or adherence changes with a new model |
| Mistake count before it becomes an instruction: two [playbook:192] | 2026-08-21 | Measure repeat rate (playbook:213) |
| UI iteration rounds: 2–3 [playbook:301] | 2026-08-21 | Visual verification improves |
| Eval set of 20–50 real tasks; retire cases that stop discriminating [playbook:320] [playbook:326] | 2026-08-21 | Every model generation (the playbook says this itself) |
| Nit cap of 5 per review; severity definitions [playbook:369] | 2026-08-21 | Monthly finding ratings |
| Council thresholds: 80% budget, 2× estimate, fingerprint k=3, back-edge cap 3, two failed fixes [council §6.4] | 2026 council | They are guesses (council §6.6 item 8). Tune from run-ledger data |
| Model-based scans go stale per model generation [playbook:547] | 2026-08-21 | Re-scan on every new model |
| Named products: auto mode, managed settings keys, Code Review service, Claude Tag, Claude Security | 2026-08-21 | Before any use, verify against current official docs (`AGENTS.md`) |

## 4. Applying the guide

### To a new skill or autonomy feature

Answer each question in the design doc or the skill's change record:

1. Which stage and sub-stage (§1) does it serve, and which artifact does it read and write?
2. What is advisory and what is enforced? Each must-hold rule needs a hook or script (A-05).
3. Who verifies the work, in what separate context, and how is the oracle protected (A-03, A-04)?
4. Which actions are irreversible, where is the gate, and what exactly does the human decide (A-07, A-08)?
5. Which values are model-dependent settings? Tag each one with *as of* and *revisit when*.

### Revisit protocol

Trigger: a new model generation in the roster, or a quarter without review.

1. Re-run the evals (A-10). Where none exist, re-run trigger tests and spot-check one real task per affected skill.
2. Walk §2's settings column and §3. Change only settings that the evidence moved, and update the *as of* dates.
3. Record each change and its evidence in the change log below.

## Change log

| Date | Change | Evidence |
|---|---|---|
| 2026-10-05 | Created from the 2026-08-21 playbook and council lifecycle v2 | `sources/`, `council/` |
| 2026-10-06 | §1 replaced the 13-stage spine with 8 stages and 28 sub-stages plus mapping rules. Approval moved from a single Authorize stage to a Governance gate, which removes the conflict with A-07 (merge is gated) | `council/stages/`, `skill-map.md` |
| 2026-10-06 | Renamed Roadmapping → Charting and Closeout → Closure (both collided with repo terms). Added the unit per stage, the per-sub-stage answers, and the boundary table; Research vs Grounding is now decided by source, not timing | User review of §1 |
