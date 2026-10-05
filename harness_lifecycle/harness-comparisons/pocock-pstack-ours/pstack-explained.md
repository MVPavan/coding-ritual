# pstack explained

A reference for revisiting pstack without re-reading it. Snapshot: pstack v0.15.9,
submodule commit `e43c7ee`, read 2026-10-05.

`P/` below means `reference_harnesses/cursor_plugins/pstack/`. Citations are
`path:line`. **J:** marks my judgement; everything else is read from the files.

## 1. What it is

A Cursor plugin with 50 skills, 2 agents, and one dormant automation pack. You
type `/poteto-mode <task>` once. From then on, one router skill (poteto-mode)
names every next step: which playbook to follow, which skill to run, which
principle to apply. The model never picks a pstack skill from its description.

## 2. Invocation mechanics

- 49 of 50 skills carry `disable-model-invocation: true`. Only `setup-pstack`
  lacks it. Cursor's documentation says such a skill "is only included when
  explicitly invoked via `/skill-name`. The agent will not automatically apply
  it based on context" (cursor.com/docs/skills, fetched 2026-10-05).
- poteto-mode is itself user-only (`P/skills/poteto-mode/SKILL.md:4`). It
  stays on through `mode: true` and a `reminder:` line
  (`P/skills/poteto-mode/SKILL.md:5,8`). Cursor's documentation does not
  describe either field.
- Routing is by name. poteto-mode's trigger list, its playbooks, and other
  skills name the next skill in prose, for example "→ the **architect**
  skill". J: the model then loads the named skill's file. Neither pstack nor
  Cursor's documentation states this mechanism.
- Consequence: skill descriptions do no routing work. They label the `/` menu
  for a human. The README says the principle files exist "so other skills can
  reference a principle by name, and so the index can point at the full rule"
  (`P/README.md:199`).
- J: each principle's "when to apply" text exists twice, once in the
  poteto-mode index and once in its own description. Nothing keeps the two in
  sync.

## 3. Inventory

### poteto-mode, the router (`P/skills/poteto-mode/`)

`SKILL.md` sections:

| Lines | Section | Role |
|---|---|---|
| 13–36 | Non-negotiables | Layer 1: always-on triggers |
| 38–79 | Principles | Layer 3: the index of all 24 principles |
| 81–89 | Autonomy | Just do reversible work. Always pause for force-push to shared branches, deploys, data deletion, and customer messages. Grant phrases such as "run until done" keep it going |
| 91–99 | Subagents | Every helper is `poteto-agent`, in the background, with an explicit model per role. A fresh subagent is used for each round |
| 101–113 | Writing the reply | Short declarative sentences, no long dashes, every claim labelled measured, inferred, or guess |
| 119–147 | Playbooks | Layer 2: match the task, copy the playbook's steps into the todo list |

**The 23 playbooks** (`P/skills/poteto-mode/playbooks/*.md`) are recipe files,
not skills.

| Group | Playbook | Essence |
|---|---|---|
| Understand | investigation | Read-only cited answer to how, why, are we sure, X or Y. No PR |
| | runtime-forensics | Diagnose a live symptom from instrumentation. Diagnosis only |
| | trace-forensics | Diagnose a captured profile through sqlite. Diagnosis only |
| Change code | feature | how → architect → throughput checkpoint → delegate → verify on the real surface → small commits → interrogate if contested → Opening a PR |
| | bug-fix | Reproduce on the real surface, binary-search the cause, commit the failing repro first |
| | refactoring | Pin behaviour, subtract, reshape in small green steps, prove equivalence |
| | perf-issue | Baseline trace, fix, post trace; the number goes in the PR |
| | hillclimb | Frozen harness; one hypothesis per loop, kept or reverted, logged in `decision.tsv` |
| | prototype | Throwaway variants behind a switcher settle a fork by observation |
| | visual-parity | Migrate per component until the screenshot diff is zero |
| | authoring-a-skill | Create a skill, validate frontmatter and links, PR |
| | eval | Blind multi-model candidates, then a blind judge grades the transcripts |
| Land | opening-a-pr | Clean the diff, write the title and body, open a ready PR. Ends every other playbook |
| | babysit | Drive a PR to merge-ready: conflicts, then threads, then CI. Never merges |
| | shipping | One independent cloud verifier per PR; land the contiguous verified run bottom-up |
| Long runs | autonomous-run | Fix a checkable predicate first; iterate on a `/loop` wake; never relax the predicate |
| | multi-phase-plan | A checklist plan in a fixed skeleton, linted by `check-plan`; stops for "go" |
| | autopilot-full | One cloud owner per PR through merge; a root swarm verdict each round; an hourly audit tick |
| | autopilot-stack | Same owner loop; verified PRs stacked in one line for the operator to land |
| | orchestrate | Multi-day program; the coordinator writes briefs, never code; state lives in `orch` |
| Session | session-pickup | Resume from a transcript, cloud URL, or branch, then route to the matching playbook |
| | pause-safely | Stop at a safe point with a `wip:` commit and a resume note |
| | worktree-cleanup | Audit, then prune worktrees and simulators behind safety gates |

**Scripts** (`P/skills/poteto-mode/scripts/`). These are deterministic tools.

| Script | Essence |
|---|---|
| `orch` | Plain-file store for orchestrate: units, a ledger keyed by PR and head SHA, an inbox, gates, the frontier, standing orders. Never spawns or waits |
| `watch-pr` | PR and stack watcher over `gh`; emits READY, WAITING, ADVANCE, or COMPLETE events. Wakes babysit and shipping |
| `check-plan.mjs` | Lints a multi-phase plan against the skeleton and prints every defect |
| `worktree-audit.sh` | Read-only worktree table: size, age, merged, dirty, PR, last chat, suggested bucket |
| `bootstrap.ts` | Installs the pinned dependencies for the Bun scripts |

**Reference.** `references/bugbot-triage.md` holds the fix, dismiss, or ask
rubric for review-bot comments, plus learned skip patterns that grow from
babysit sweeps.

### Workflow skills (24)

| Group | Skill | Essence |
|---|---|---|
| Understand | how | A simple question gets one explainer in a single pass; a complex one gets 2–4 read-only explorers, then the explainer. When in doubt, simple (`P/skills/how/SKILL.md:17-21`) |
| | why | Git anchor, then one investigator per connected source (Slack, Linear, Sentry…) answers "why is it like this" |
| | recall | Rebuild recent working context from transcripts and shared records |
| | blast-radius | Find what a change breaks beyond its diff; prove the key safety fact by running code |
| Design and build | architect | Ground (how, why) → sketch ≥2 distinct designs via arena → implement against the sketch → scrap on friction (`P/skills/architect/SKILL.md:21-59`) |
| | arena | N parallel candidates judge each other; pick a base, graft, verify |
| | swarm | N parallel cloud workers (slices or races) → one PASS, ISSUES, or BLOCKED report |
| | figure-it-out | Designs a bespoke playbook for large or step-away work: frame, design, hypothesis loop, trail, verify (`P/skills/figure-it-out/SKILL.md:15-49`) |
| | tdd | Failing test first only when cheap; otherwise the closest executable check |
| Review and verify | interrogate | One read-only reviewer per model on one rubric; a lead sorts findings into Act on, Consider, Noted, Dismissed |
| | no-comments | Comment Sicko deletes needless comments; the parent audits its diff |
| | benchmark-checklist | Seven questions before trusting a measured number |
| | show-me-your-work | Append-only `decisions.tsv`, a transcript audit, a cross-model "Attention" review |
| | create-verification-skill | Generate a project `verify-<app>` skill (launch, doctor, drive, evidence, cleanup, feature map); prove it once |
| | maintain-verification-skill | Re-check that verify skill against the source plus one live pass; at most 1 PR of proven fixes |
| Learn | reflect | Three reviewers read the transcript; a synthesizer proposes skill edits; you approve |
| | correct | Mine repeated mistakes and fix each at the highest level: architecture, then types, lint or CI, then tests, then docs |
| | automate-me | Mine your transcripts and draft a personal `<handle>-mode` skill as a PR |
| Writing | unslop | Catalog of AI-writing tells to remove from any prose |
| | technical-writing | Diátaxis, Google style, simplified technical English for docs, PRs, commits |
| | bro | Restate the last message plainly |
| | teach | Run how and why in parallel, then explain diagram by diagram |
| Misc | make-bot-ui | Local page whose buttons trigger a Grok Bot routine over a webhook, exposed over Tailscale |
| | typescript-best-practices | TypeScript rules behind the type-system principle |

**Setup.** `setup-pstack` detects models, asks the budget, and writes the
model-per-role rule every skill reads. It is the only model-invocable skill.

### Principle skills (24)

Lenses read by name from the poteto-mode index (`P/skills/poteto-mode/SKILL.md:38-79`).

| Group | Principle | Essence |
|---|---|---|
| Core | laziness-protocol | Smallest change; bias to deletion |
| | foundational-thinking | Data structures and scaffolding before logic |
| | redesign-from-first-principles | Redesign as if the requirement existed on day one |
| | attack-the-premise | After 2 same-premise fixes fail, question the premise |
| | subtract-before-you-add | Remove dead weight first |
| | minimize-reader-load | Count layers; collapse one-caller wrappers |
| | outcome-oriented-execution | Go straight to the target architecture; no throwaway compatibility states |
| | experience-first | User delight over implementation convenience |
| | exhaust-the-design-space | 2–3 competing prototypes before committing |
| | build-the-lever | Build the tool that does or proves the work |
| Architecture | model-the-domain | Encode the domain in structure, not scattered conditionals |
| | boundary-discipline | Guards at the boundaries, a pure core |
| | type-system-discipline | Illegal states unrepresentable; parse at boundaries |
| | make-operations-idempotent | Converge whatever partial runs came before |
| | migrate-callers-then-delete-legacy-apis | Migrate and delete in one wave |
| | separate-before-serializing-shared-state | Remove sharing before adding locks |
| Verification | prove-it-works | Verify the real artifact, not a proxy |
| | fix-root-causes | Reproduce, trace to the root, no symptom guards |
| | sequence-verifiable-units | Small units, each ending in a check |
| | test-behavior-not-implementation | Call code as users do; assert literal values |
| | explain-the-number | Find what limits a measurement before trusting it |
| Delegation | guard-the-context-window | Bulk work to subagents; summaries in the main thread |
| | never-block-on-the-human | Proceed on reversible work; confirm only irreversible steps |
| Meta | encode-lessons-in-structure | A repeated instruction becomes a lint, flag, check, or script |

### Agents and automations

| Item | Essence |
|---|---|
| `poteto-agent` | Default background subagent. Reads poteto-mode in full first and opens a principle's leaf file when applying it (`P/agents/poteto-agent.md:9`) |
| `Comment Sicko` | Deletes needless comments, flags `MUST KILL` symbols, never writes app code |
| `automations/benny` | Dormant Slack-triggered Cursor automations: triage reports, reproduce confirmed bugs with UI evidence, open a draft PR |

### External dependencies the playbooks require

`deslop`, `control-ui`, `control-cli` (from the `cursor-team-kit` plugin), a
project `verify-<app>` skill, Cursor's built-in `create-skill` and `/loop`,
`gh` or Origin, and GitHub PRs with CI.

## 4. The routing map

```text
/poteto-mode <task>
├─ Layer 1 · Always-on triggers (SKILL.md:13-36), fire inside any playbook
│   nontrivial change, "are we sure?"     → how
│   about to ask about an observable fork  → PB prototype instead of asking
│   any code                               → p:model-the-domain (name the data shape)
│   code crossing a function boundary      → architect → how, why, arena, interrogate
│   parallel fan-out                       → swarm (coverage, races) | arena (bake-offs)
│   contested design                       → interrogate
│   nontrivial multi-step                  → throughput checkpoint (Feature step 3)
│   any prose                              → unslop (+ create-skill for agent prose)
│   docs, PR, commit text                  → technical-writing
│   before commit / before review          → deslop / no-comments → Comment Sicko
│   shipping UI or CLI                     → control-ui / control-cli
│   a measured number                      → benchmark-checklist
│   PR status / land a stack               → PB babysit / PB shipping
│   review-bot comments                    → bugbot-triage.md
│   long or step-away work                 → show-me-your-work
├─ Layer 2 · Playbook match (SKILL.md:119-147), chosen once from the task type
│   question → investigation · defect → bug-fix · slowness → perf-issue
│   metric target → hillclimb · new behaviour → feature · reshape → refactoring
│   design fork → prototype · multi-PR → multi-phase-plan · run to done → autonomous-run
│   queue or program → autopilot-full | autopilot-stack | orchestrate
│   no fit, or large / cross-cutting / step-away → figure-it-out (overrides a narrower match)
│   every code playbook ends → opening-a-pr → (on request) babysit → shipping
├─ Layer 3 · Principles index (SKILL.md:38-79): read the leaf file, name it in the reply
└─ Subagents → poteto-agent; how, why, interrogate, reflect, swarm choose their own models
```

**Never routed by poteto-mode; you type them yourself:** recall, reflect,
correct, automate-me, teach, bro, make-bot-ui, create-verification-skill,
maintain-verification-skill, typescript-best-practices, setup-pstack.
blast-radius is reached only from PB orchestrate. J: the learning skills never
fire on their own, even under full autonomy.

## 5. Planning by scale

pstack has no planning skill. The plan comes from one of five places:

| Scale | Where the plan comes from |
|---|---|
| One task | The matched playbook's steps, copied into the todo list (`SKILL.md:121`), plus Feature's 4-item throughput checkpoint (`P/skills/poteto-mode/playbooks/feature.md:7-11`) |
| A design decision | architect: ground, sketch ≥2 designs via arena, implement, scrap on friction |
| Large, or no playbook fits | figure-it-out: falsifiable predicate, quantified scope, rigor level; atomic landable units, riskiest first, harness before the work |
| Multi-phase or multi-PR | multi-phase-plan: settle open questions by prototype; fixed skeleton, one section per PR with unit, live, and perf evidence; `check-plan` lint; names its execution playbook; stops for "go" (`P/skills/poteto-mode/playbooks/multi-phase-plan.md:5-11`) |
| Multi-day program | orchestrate: briefs and `orch` units |

Compared with our `planning` skill:

| | pstack | Ours |
|---|---|---|
| Open questions | Settled by prototype | Asked of the human |
| Verification | An evidence box per PR inside the plan | Acceptance criteria per stage |
| Plan check | A script lints the plan's structure | Human approval, plus a critic review at material risk |
| Where the plan lives | A markdown checklist | `roadmap.md` plus Beads |

## 6. The three layers: boundaries and overlap

**What each layer is keyed on:**

| Layer | Fires on | Decides | Fires how often |
|---|---|---|---|
| 1 Triggers | A situation that arises mid-task (about to ask, about to commit, a number appeared) | Which skill runs now | Many times, inside any playbook |
| 2 Playbooks | The task type, once at the start | The order of the whole job | Once per task; it chains to the PR playbooks |
| 3 Principles | A judgement inside a step | How to choose | Whenever a decision is made; must be named in the reply |

J: these are not strict layers. They are one router with two dispatch keys
(task type and situation) plus a shared vocabulary of principles. The overlap
is deliberate redundancy:

- **Layer 1 routes into Layer 2.** The PR-status, land, and ask-about-a-fork
  triggers route to playbooks (babysit, shipping, prototype).
- **Layer 2 hard-codes Layer 1's skills.** Feature runs how (step 1) and
  architect (step 2), which the triggers would fire anyway. Opening a PR runs
  deslop and no-comments, which the before-commit and before-review triggers
  also fire. J: if the model forgets a trigger, the recipe still carries it.
- **Layer 3 is used by all three.** A trigger names `p:model-the-domain`.
  Playbooks enforce `p:sequence-verifiable-units`. Skills such as architect
  apply `p:exhaust-the-design-space`.
- **Skills nest the same calls again.** architect's Phase A runs how, so
  Feature runs how twice (step 1, then architect Phase A).

**Where precedence is stated (clear):**

- figure-it-out overrides a narrower playbook for large work (`SKILL.md:123`).
- Orchestrate versus autonomous-run.
- Babysit versus Cursor's built-in babysit.
- A playbook step you skip stays in the list as `skip: <reason>`.

**Where it is left to judgement (unclear):**

- "Nontrivial", "contested", and "large" are undefined thresholds.
- architect Phase D says implement against the sketch, while Feature step 4
  says delegate the code. J: read together, the delegate implements against
  architect's sketch; neither file says so.
- Commit shaping appears three times: Feature step 6, Opening a PR's
  "Commits", and `p:sequence-verifiable-units`.

## 7. Walkthrough: one task through poteto-mode

Task: `/poteto-mode add a human-readable --table view to foreman status`
(it prints JSON today). Each step is tagged with the layer that drives it.

| # | Layer | What happens |
|---|---|---|
| 1 | L2 | New behaviour matches **Feature**. Open `playbooks/feature.md` and copy its 8 steps into the todo list |
| 2 | L1 + L2 | Step 1 (and the "nontrivial change" trigger): **how** over `foreman status`. The status code sits in one place, so it is simple: one explainer traces where status is built and printed |
| 3 | L1 → L3 | "Any code" trigger: name the data shape first under **model-the-domain**. Read the leaf; define one typed `StatusReport` that both the JSON and the table render from |
| 4 | L1 + L2 | Step 2 (and the "crosses a function boundary" trigger): **architect**. Phase A re-runs how (already done). Phase B: **arena** sketches at least 2 distinct designs on different models, for example format the existing status dict directly versus a separate view model. Screen for red flags; synthesize one. No human checkpoint unless asked |
| 5 | L1 → L3 | Tempted to ask "show heartbeat age in the table?". It cannot be observed by running something, and it is reversible, so **never-block-on-the-human**: decide, and report it as an open decision |
| 6 | L2 | Step 3: throughput checkpoint, 4 todos. Blocking first steps: n/a. Independent workstreams: n/a, one module. Shared state: n/a. Smallest split: one worker, because it is one file |
| 7 | L2 | Step 4: delegate to **poteto-agent** on the code model, with file paths, the `StatusReport` shape, and success criteria. The parent reviews the diff and writes its own summary |
| 8 | L1 + L2 → L3 | Step 5: verify on the real surface with **control-cli**: run `foreman status --table` on a live root and check it against the JSON output. "Inconclusive" is a fail. **prove-it-works** |
| 9 | L2 → L3 | Step 6: rebase into small ordered commits under **sequence-verifiable-units** |
| 10 | L2 | Step 7: interrogate if contested. Not contested → `skip: single obvious shape after arena` |
| 11 | L2 + L1 | Step 8, **Opening a PR**: deslop, then no-comments (Comment Sicko), then title and body through technical-writing and unslop, then `gh pr create`, ready, not draft. Post the URL. No babysit |
| 12 | Reply rules | Short sentences; name each principle that changed a decision; label claims measured, inferred, or guess |
| 13 | Later | "Check on the PR" → **babysit**. "Ship it" → **shipping**: an independent verifier, then the landing |

What this shows:

- One task touches all three layers about 15 times.
- The model's real decisions are the playbook match (step 1), skip-or-run
  calls on judgement words (steps 5 and 10), and choosing between arena's
  designs (step 4).
- Everything else is either named by the recipe or fired by a situation.

## 8. Observed run (2026-10-05)

A subagent played `poteto-agent` on the task from §7, read pstack cold, and
stopped once it had decided an approach. It spawned nothing and changed
nothing. Its trace matched §7 on the playbook match, the data-shape-first
step, not asking the human, and how being run twice. It differed in four
places, which §7 did not predict:

- **how took its simple path.** how sizes the question first and skips
  explorers for a single module (`P/skills/how/SKILL.md:17-21`).
- **architect and a principle pulled in opposite directions.** Feature makes
  architect mandatory (`P/skills/poteto-mode/playbooks/feature.md:6`), but
  exhaust-the-design-space says it does not apply when a pattern is already
  established (`P/skills/principle-exhaust-the-design-space/SKILL.md:18-21`).
  The agent ran a 2-candidate arena instead of 3, by its own judgement.
- **Delegation cannot be skipped.** Feature step 4 forbids a `skip:`, says
  Laziness Protocol does not override it, and lets an agent that cannot spawn
  own the diff with review kept separate
  (`P/skills/poteto-mode/playbooks/feature.md:12`).
- **The citation rule limits principle reading.** Only principles whose leaf
  file was read may be cited (`P/skills/poteto-mode/SKILL.md:15`), so the
  agent read and cited two and only listed the rest.

Drivers across its 21 steps (some had two): about 8 came from the playbook, 7 from router
rules, 4 from principles, and 3 from its own judgement. The 3 judgement calls
were: sizing how as simple; grounding the code itself because it could not
spawn; scaling arena down. There was no human stop before code.
