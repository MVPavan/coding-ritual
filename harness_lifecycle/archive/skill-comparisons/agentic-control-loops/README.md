# Agentic Control Loops

Capability family: **agentic-control-loop** — surfaces that set up a coding
agent to run *repeatedly and unattended* against a repository, each run
producing one small reviewable change, with a human steering between runs.
Compared here: humanlayer's two loop-builder skills against the three things in
our harness that play in the same space — the `execution` skill (our in-session
orchestration engine, including its unattended `workstream` scope), the parked
**workflow-graphs** orchestrator draft (`docs/ideas/workflow-graphs.md`, bead
`cr-o85`), and the recorded orchestration rulings in `harness_learnings/`.

Scope note: this family is about the *loop around the agent* (trigger, sensing,
selection, actuation, steering, flow control). Plan-execution engines — how one
session walks an approved plan — are in `../plan-execution-engines/`; review
and verification passes in `../review-protocols/` and
`../post-implementation-passes/`.

Upstream pin: `reference_harnesses/humanlayer_skills` @ `3c26291` (2026-08-13).

## Level 1 — Placement

| Skill | Repo | Bucket | Triggers when |
|---|---|---|---|
| `design-control-loop` | humanlayer | 9 Release, Migration & Operations (also 10, 11, 1) | "User wants to drive some property of their codebase toward a target with small, low-risk, reviewable changes on a schedule" (`SKILL.md:8`). Description is a workflow summary, not a trigger list (`SKILL.md:3`) — an agent would have to infer "schedule / recurring / drift / migrate gradually" phrases. Produces sensor + controller scripts, an actuator skill, a GHA workflow, a memory file, optional dampener (`SKILL.md:33-39`). |
| `build-iterated-agentic-loop` | humanlayer | 9 (also 10, 11) | "User wants to turn a repeatable agent task into a repo-local skill plus a GitHub Actions workflow that runs a coding agent on a schedule, manually, or both" (`SKILL.md:8`). Same shape minus the control-theory framing and the discrete sensor/controller steps; `narrow-react-prop-types` is named as its reference pattern (`SKILL.md:10`). Effectively superseded by `design-control-loop` — same author, same reference set plus two files, later commit. |
| `execution` | ours | 4 Implementation & Refactoring (also 10) | "Approved work is ready to be built — a bd task or standalone plan, a phase of a workstream roadmap, or an explicit request to walk every remaining phase" (`SKILL.md:3`). Scope selector rows (`SKILL.md:14-23`); the unattended **workstream** scope is reachable only by explicit `/run-phases` invocation (`references/workstream-mode.md:3-6`). |
| workflow-graphs (draft) | ours | *proposed* 10 Orchestration | Not a skill — a parked idea doc (`docs/ideas/workflow-graphs.md:3-5`). Listed because it is the orchestrator design the user asked to compare against. |

No ledger entry exists for either humanlayer skill (`harness_lifecycle/ledger.json`
has no `humanlayer_skills` rows) — this harness has never been curated. The
closest prior rulings are (a) `harness_learnings/harness-patterns-by-capability.md:14`
("fresh worker per task, task packets … rejected: high-ceremony orchestration
and extra machinery") and `:47` ("avoid permanent mega-thread orchestration"),
and (b) the plan-execution-engines comparison, which rejected
whole-machine-in-one-file engines.

## Level 2 — Capability profiles

### `design-control-loop` (humanlayer)

**Achieves** — a repository-resident, scheduled, human-steered loop that moves
one measurable property of the codebase toward a set point, one PR at a time.

**Can do**
- Teaches a five-part vocabulary — set point, sensor, controller, actuator,
  disturbance — and a full control-loop diagram before any design
  (`SKILL.md:12-22`; `references/control-loop-taxonomy.md:7-51`).
- Repo-first interview: reads CI, package manager, validation scripts, existing
  skills/loops, static-analysis tooling *before* asking anything; has a
  completion criterion for "understood the system" (`SKILL.md:43-56`).
- Designs each component with the user, explicitly allowing fused components
  (sensor+controller, controller+actuator) and warning not to invent separation
  (`SKILL.md:64-75`; `taxonomy.md:21-28`; `workflow-template.yml:169-171`).
- Offers a **dampener** — a regression gate on PRs that compares the sensor
  against a baseline so the problem cannot get worse while the loop fixes it
  (`SKILL.md:75`; `example-control-loop.md:110-114`).
- "Runnable locally before CI" as a hard phase with its own completion
  criterion (`SKILL.md:95-107`).
- Generates the actuator skill from a template with checkable completion
  criteria per step and a response template that becomes the PR body
  (`SKILL.md:79-93`; `references/skill-template.md`, `response-template.md`).
- Ships a GHA workflow with discrete sensor → controller → actuator steps, an
  iterate path, PR-bound flow control, and artifact upload
  (`references/workflow-template.yml`).
- Human-on-the-loop via two channels: a version-controlled memory file loaded
  into the actuator *after the controller*, and `/iterate` PR comments routed
  by a hidden PR-body marker to the owning workflow, which also distils durable
  feedback back into memory (`SKILL.md:123-134`; `references/agent-iteration.ts:41-55, 60-125`).
- Flow control: default one open PR per loop, scheduled runs no-op, manual
  dispatch bypasses (`SKILL.md:136-145`; `workflow-template.yml:55-63`).
- Agent-agnostic actuator: Claude Code, Codex, OpenCode, CodeLayer run commands
  plus per-agent response extraction (`references/agent-runner-templates.md:17-152`).
- Dry-run bootstrap trick (temporary push trigger) and a "ready to iterate
  faster" ladder (`SKILL.md:147-157`).

**Pros (vs the others here)**
- The only surface in the set with an explicit **measurement** concept. Our
  execution engine selects work from bd (`execution/SKILL.md:75-76`); it never
  measures the repo. A sensor + set point is what makes a loop converge rather
  than just run.
- The only one that bounds *throughput against review capacity* (PR bound);
  ours bounds rounds (`task-engine.md:141-184`) and sequences phases
  (`workstream-mode.md:8-11`), which is a different axis.
- The dampener is a genuinely new idea relative to everything in our catalog:
  a standing regression gate paired with an improvement loop.
- Tailoring is enforced structurally — "no fixed toolset and no template to
  reproduce" (`SKILL.md:10`), "illustration, not a blueprint" (`SKILL.md:22`,
  `example-control-loop.md:78`).

**Cons (vs the others here)**
- Designed for **CI-hosted unattended runs with `bypassPermissions`**
  (`agent-runner-templates.md:31`) and `git add -A` in the iterate path
  (`workflow-template.yml:260-263`) — both collide with our Git Safety rules
  and conservative-git profile. Adoptable only as a pattern, not as shipped
  text.
- GitHub Actions is the default host; non-GHA CI is "use whatever the repo
  uses" with no second template (`SKILL.md:113`). The `/iterate` helper is a
  Bun script shelling to `gh` (`agent-iteration.ts:32, 122-123`) — a toolchain
  dependency our harness does not carry.
- The description is a workflow summary (`SKILL.md:3`), which our authoring
  rule forbids; it would need a trigger-style rewrite before it could sit in
  our catalog.
- No tracker integration: memory is a flat markdown file (`memory-template.md`)
  and loop state is "whatever the open PR is". Our harness puts loop state in
  bd (`execution/SKILL.md:27-30`).
- No independent critique in the loop — the PR review *is* the critique, done
  by the human. Fine for the use case, but it means a human must be in every
  cycle; it is not a substitute for our review gate.

### `build-iterated-agentic-loop` (humanlayer)

**Achieves** — the same artefact set (skill + workflow + memory + optional
iterate helper) for a *task* rather than a *property*: "find N things, change
them, validate" on a schedule.

**Can do**
- Nine-question setup (agent, cadence, task, scope, validation, PR bounding,
  PR metadata, response format, iteration) with recommended defaults from repo
  evidence (`SKILL.md:34-60`).
- Defines the job as find / change / validate (`SKILL.md:62-85`).
- Everything the control-loop skill ships for skill, prompt, memory, workflow,
  validation, dry-run (`SKILL.md:87-203`) — the reference files are the same
  minus the taxonomy and worked example.

**Pros** — shorter path when there is no measurable set point (e.g. "generate
missing docstrings weekly"). **Cons** — no measurement, no dampener, no
local-first phase (`SKILL.md` has no equivalent of Phase D), no design-capture
step; the workflow template has one monolithic agent step
(`workflow-template.yml` diff vs the control-loop one). It is the earlier
draft of the same idea; everything it does, `design-control-loop` does with
more structure.

### `execution` (ours)

**Achieves** — drives approved, already-decomposed work to verified closure in
a session: select unit from bd → dispatch/implement by risk → review gate →
close with evidence; walks whole workstreams unattended when explicitly asked.

**Can do**
- Scope selector (task / phase / workstream) with a "stop, route to planning or
  brainstorming" row (`SKILL.md:14-23`).
- bd as the single state store; close-with-evidence; discovered work becomes
  a real stage (`SKILL.md:27-30, 52-54`).
- Risk-routed dispatch (inline / light / full), with test-first, security,
  and debugging skills mounted by condition (`SKILL.md:34-45`).
- Review gate with spec + code reviewers, bounded five-round fix loop, breaker
  with adjudication matrix, final review with independent critic, optional
  simplification look (`references/task-engine.md:115-226`).
- Unattended workstream walk: preflight authorization record, dirty-tree
  baseline, per-phase commit of explicit paths, `/compact` + bd re-query
  between phases, enumerated auto-approvals, fail-stop rules
  (`references/workstream-mode.md:13-84`).
- Compaction-survival contract: ledger + bd are re-read after compaction
  (`task-engine.md:51-53`; `workstream-mode.md:60-77`).

**Pros (vs the loop skills)** — review and critique are *inside* the loop, not
deferred to a human PR review; bd gives queryable state and dependency
ordering; git safety is structural. **Cons** — selection is "what bd says is
ready", never a measurement; there is no steering channel that changes future
runs (the ledger records rulings, but nothing reads them into the next
unit); there is no throughput bound against review capacity; everything runs
in one session, so the unattended form is bounded by context, not by a
scheduler.

### workflow-graphs (ours, draft)

**Achieves** (intended) — turns the SDLC pipeline from prose into per-task-type
graphs (stages + gates + assignments), interpreted by the agent and seeded into
bd via `bd formula` (`workflow-graphs.md:19-42`).

**Can do** (as designed) — graphs as data, beads as the only state store,
disciplines mounted as a set not one-of-N, no loops in the graph format, v1 =
interpreter + one feature graph (`workflow-graphs.md:44-61`).

Strictly orthogonal to the humanlayer loops: it answers "how does one unit of
work move through stages", theirs answer "how does the repo keep getting
nudged toward a target over weeks". See the orchestrator analysis below.

### Verdict

- `design-control-loop` **supersedes** `build-iterated-agentic-loop`; treat
  them as one candidate and evaluate only the former.
- Neither humanlayer skill is a **substitute** for `execution` or the
  workflow-graphs draft; they are **complements** at a different timescale
  (scheduled, cross-session, PR-granular vs in-session, plan-granular). They
  do not overlap with any shipped skill in our catalog, and the gap report
  finds no name match — correct.
- Strongest for what: humanlayer for *recurring, measurable codebase
  properties* (migrations, lint debt, coverage, invariant drift) where a human
  reviews every PR; ours for *one-off planned work* with in-loop review.
- The adoptable unit is small: the **sensor / set point / controller /
  actuator / dampener / flow-control vocabulary** and the **memory-after-
  controller** steering channel. The shipped artefacts (GHA YAML, Bun script,
  bypassPermissions runner, `git add -A`) are not.

## Orchestrator analysis — the loop skills vs our orchestrator idea

The user asked specifically how these skills relate to "how an orchestrator
should be". The recorded position lives in three places:

1. **`harness_learnings/harness-patterns-by-capability.md:14, 47`** — keep
   fresh-worker-per-task, task packets, spec-before-code review, escalation
   statuses; reject high-ceremony orchestration machinery and "permanent
   mega-thread orchestration".
2. **`docs/ideas/workflow-graphs.md`** (parked 2026-08-12, bead `cr-o85`) — the
   draft for pipeline-as-data; design constraints at `:44-61`.
3. The session-memory note *orchestrator-pattern-validation* (user-validated
   critique of the viral "one long-lived orchestrator thread" pattern): keep
   subagent delegation and scoped worker prompts; reject long-lived threads,
   mega-prompts, ORCHESTRATOR.md-as-CLAUDE.md, and "compaction won't erase"
   assumptions; persistence comes from hooks + checkpoints, not from a
   thread. (Not a repo file; the repo-side echo is item 1.)

Against that position, component by component:

| Our orchestration principle | humanlayer loop skills | Reading |
|---|---|---|
| Orchestrator is not a long-lived thread; state lives outside the session | Each run is a **fresh CI job**; the only carried state is the memory file and the open PR (`SKILL.md:127-134`; `workflow-template.yml:200-213`) | **Agrees**, more radically than we do — there is no session at all. Their "checkpoint" is git. |
| Persistence via hooks/checkpoints, re-query after compaction | Memory file is interpolated deterministically every run, after the controller (`SKILL.md:129`); `/iterate` writes back to it (`agent-iteration.ts:20-25`) | **Agrees**; their channel is simpler (one file) but has a *write-back* path ours lacks — our ledger is written by the coordinator and read by nobody in the next unit. |
| Fresh worker per task with a task packet | Actuator gets prompt + controller output + memory, per run (`workflow-template.yml:203-214`; `prompt-template.md`) | **Agrees**. Their packet = ours (goal, scope, validation, finishing rules) minus owned/forbidden files split and report-file contract. |
| Manager-not-IC; reviewers gate; bounded fix loop | No in-loop reviewer; human reviews the PR; `/iterate` is the fix loop, unbounded but human-driven (`SKILL.md:130`) | **Differs by design**. They push review to the human because the cadence is daily, not per-task. For our in-session work this would be a regression; for a scheduled loop it is the right call. |
| Graphs are process, roadmaps are content; no loops in the graph | Their "graph" is a fixed three-stage pipeline (sense → control → actuate) with the loop *outside* it (the scheduler) (`workflow-template.yml:4-5, 173-221`) | **Agrees** with "no loops in the graph": iteration lives in the scheduler and in `/iterate`, not in the stage definition. It is the simplest instance of our constraint. |
| Mount many disciplines, not route one | Disciplines are whatever the actuator skill encodes (golden patterns, validation commands) (`SKILL.md:72-73, 85-86`) | **Silent** — they have no notion of mounting TDD / security / debugging per run. A gap if one reused their shape for riskier work. |
| bd is the only state store | No tracker; PR label + memory file (`SKILL.md:140-145`) | **Differs**. Adoptable fix if we ever build a loop: sensor output → bd issues (`bd create` per finding), controller = `bd ready`, memory = `bd remember`. That would make their loop a workstream seed rather than a parallel store. |
| Reject "extra machinery" | Ships a 273-line workflow, a 174-line Bun script, four runner variants (`references/`) | **Conflicts** as shipped text; **agrees** in spirit — every piece is justified by a failure ("daily loop stacks unreviewed PRs", "workflow_dispatch needs one run first"). The machinery is proportionate to *their* host (GHA); ours would be a cron/`claude -p` + bd variant of maybe 40 lines. |

**What their design adds that our orchestrator draft does not have**

- **A set point and a sensor.** Our graphs move work through stages; nothing
  in our harness *measures the repo* and derives the next unit from the
  measurement. This is the single transferable idea: a loop that converges.
- **Throughput bound against review capacity** (one open PR per loop).
- **Dampener** — a regression gate that runs on every PR while the improvement
  loop runs on a schedule. We have `check-invariants` (mechanical invariants)
  but no "don't get worse vs baseline" gate.
- **Memory with write-back from review feedback** (`/iterate` → memory).
- **Local-first before CI** as a completion-gated phase.

**What our position has that theirs lacks**

- In-loop independent review and bounded fix rounds with a breaker.
- Risk routing and discipline mounting per unit.
- A queryable tracker for state, dependencies, and evidence.
- Git safety as structure, not as reviewer vigilance.
- Context-survival rules for long sessions (theirs has no long session).

**Contradictions with recorded rulings** — none at the level of principle.
The only conflicts are with shipped mechanics (`bypassPermissions`,
`git add -A`, Bun/GHA dependency), all of which are host choices rather than
orchestration claims.

**Implication for `cr-o85` (workflow-graphs)** — if that idea is resumed, the
control-loop vocabulary is a candidate *second graph type* ("maintenance loop":
sense → control → actuate → review gate, scheduled), which would also test the
draft's assumption that ≥3 graph types are needed (`workflow-graphs.md:69-72`).
That is a note for the idea doc, not an adoption now.

Routing recommendation (for `harness-evaluate`): **defer** `design-control-loop`
with the vocabulary and steering-channel components named as the borrowable
pattern, pending a real recurring-maintenance need in a user repo; **reject**
`build-iterated-agentic-loop` as superseded by its sibling. Full reasoning in
the ledger entries; component evidence in `components.md`.
