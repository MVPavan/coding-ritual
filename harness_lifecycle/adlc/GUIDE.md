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
| `../prompting-guides/GUIDE.md` | Rules for how to write instructions. This guide does not restate them |

## 1. The lifecycle spine

Each stage ends by committing one artifact. The next stage starts by reading
that artifact. [playbook:60] [playbook:72]

```text
Admit → Intent → Ground → Specify + tests (frozen) → Plan increments
  → [Build → Qualify → Independent challenge → Integrate (dark)] × n
  → Authorize → Release (ramped) → Observe → Close & learn
       ↑                                              │
       └──── finding / incident / scan → new Intent ──┘
```

The stage detail, exit criteria, and back-edges are in
`council/judge2-final-v2.md` §6.2. The playbook's chain
(intent → spec → plan → diff+tests → PR+findings → incident) is the same spine
with fewer stages.

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

1. Which stage does it serve, and which artifact does it read and write?
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
