# Unit kinds: definitions and rules

Revision 1, 2026-10-31. Read when creating, splitting or reclassifying a
principle, skill, playbook or router line, or when recording traits or
steps. Provisional: follow it, and log deviations (§5). Evidence: `docs/workstreams/skill-curation/boundary-study.md`
(the study), `docs/workstreams/skill-curation/pstack-report.md`, and the
registry (`harness_lifecycle/registry/README.md` §4a). Each rule is tagged:

- **[data]** the study's measurements support it;
- **[ruling]** the owner has decided it;
- **[proposed]** a convention to follow and test; no data forces it.

## 0. The model

| Loaded | Kind | Holds |
|---|---|---|
| every session | `AGENTS.md` | policy for every task |
| every session | router (`mvp-mode`) | which playbook or principle fits the situation |
| on a situation | principle | a judgement lens |
| on a request | playbook | order and gates across units |
| when called or asked | skill | one job's technique |
| at one branch | reference | one unit's branch material |
| for particular work | project document | repository facts and conventions |

Described, not loaded: **traits** (what behaviour a unit gives) and
**steps** (where an action sits in a playbook). Enforced, not described:
**checks and hooks**.

A **unit** is a principle, skill, playbook or the router. References and
project documents are not units.

## 1. Definitions

- **`AGENTS.md`:** policy that applies whichever unit runs.
- **Router (`mvp-mode`):** the always-loaded index from a situation to the
  playbook or principle to load. No policy, no procedure, no technique.
- **Principle:** a lens for a named situation: unordered rules, no steps, no
  output. A file the router maps a situation to, not a skill (P7).
- **Skill:** one job with its own entry point and one deliverable (an
  answer, an artifact, a change or state), whose steps are that job's
  technique.
- **Playbook:** an ordered list for one kind of request that puts units in
  order with gates and ends in a reply contract.
- **Reference:** material one branch of one unit loads when that branch runs.
- **Project document:** a repository fact or convention needed for
  particular work, routed by `.repo-context/docs-index.md`.
- **Trait:** one distinct gate, rule, method, template, artifact or output
  quality a unit gives the agent, from the shared vocabulary (registry §4a).
- **Step:** one position in a playbook's list: its condition, its own
  actions (each described by a trait) and its calls (each to a unit).
- **Subtype:** alias, tool wrapper, setup, style pass, reference pack,
  composite, retired entrypoint. A tag on a unit, never a kind of its own.
  [data: subtypes cut across roles]

## 2. Deciding the kind (first match wins)

1. It applies whichever unit runs → `AGENTS.md`.
2. Code can decide it → a check or hook; prose only points to it.
3. A repository fact or convention, neither judgement nor a job → project
   document.
4. It shapes judgement in a named situation and yields nothing → principle.
   Knowledge about one technology is not a lens: it is a skill (subtype
   reference pack).
5. It puts two or more units in order with gates to finish one kind of
   request → playbook.
6. One job, one deliverable → skill.
7. Only one branch of one unit uses it → a reference of that unit.

**5 against 6, the composite test.** Remove every call from the candidate.
Technique left that still produces the deliverable → a skill that calls
others (composite). Nothing left but order and gates → a playbook. An
exception is named in the deviation log with the owner's ruling.
[proposed; the study found no content rule that separates them exactly;
ruling: owner, 2026-11-02 (E4), added the named exception]

**Promotion by reuse.** A technique starts where its one user is (a
playbook step, or a reference). It becomes a skill when it gets a second
caller or is asked for alone. Length alone never moves anything; branch
material moves to references. [data: H1 holds via standalone use]

## 3. Rules per kind

### `AGENTS.md`

- A1. Only what applies whichever unit runs. [proposed]
- A2. No unit restates it; it is always loaded. [data: `systematic-debugging`
  restates four `AGENTS.md` lines]
- A3. A principle needed on nearly every task is promoted into `AGENTS.md`
  and its file retired; a policy line that matters only in a named situation
  is demoted to a principle. [proposed]
- A4. Routing to units moves to the router when it lands; `AGENTS.md` keeps
  one line pointing at it, plus its document pointers. [proposed; today
  "When needed" routes to `delegation` and `execution`]

### Router (`mvp-mode`)

- R1. Exactly one router, `mvp-mode`; `skill-router` retires into it.
  [ruling 2026-10-31]
- R2. Routing lines, the kind definitions (R4) and the shared rules for
  running a playbook (B2, B3, B5, B7, R8), and the rules that differ between
  the top-level agent and a delegate (R8, the delegation default) only. If it
  disagrees with `AGENTS.md`, `AGENTS.md` wins and the router is fixed.
  [ruling: option D, index and shared rules; amended by owner ruling
  2026-11-01]
- R3. Every unit is reachable from the router, in two layers:
  - **always loaded:** every playbook, every principle by its situation,
    and skills by situation where the description alone would miss or
    collide ("code crossing a function boundary → design skill");
  - **loaded when unsure or asked what exists:** the full skill catalog,
    generated by `.claude/scripts/skill-catalog.py` (as it generates
    `skill-router`'s today), never hand-written.
  A check fails on any unit the router cannot reach. [ruling: route
  skills too; layering proposed, to keep the always-loaded part lean]
- R4. One line defining each kind, so a shipped copy works without this
  file. [proposed]
- R5. Always loaded; the mechanism (hook or `AGENTS.md` pointer) is a
  separate decision. Its size counts against the same per-session budget as
  `AGENTS.md`. [ruling: sticky; mechanism open, R7 the lead]
- R6. The router names a skill; the model invokes it through the platform
  (the skill tool or its slash name), not by reading the file, so the skill
  survives compaction and its frontmatter applies. Router-only units
  (principles, playbooks) are read by path. [proposed]
- R7. The router itself is model-invocable, so any agent with the skill
  list can find it. One `AGENTS.md` line telling agents to invoke it at the
  start of a task makes it sticky on every vendor and keeps it across
  compaction: the leading candidate for R5's mechanism. [proposed]
- R8. Inside a delegated task the router routes to skills and principles
  only and never starts a playbook: the parent runs the playbook, and the
  brief is the delegate's step. [proposed; pstack: the chat that receives
  `/poteto-mode` runs the playbook]

### Principles

- P1. The situation opens the router line, its only copy; the file has no
  description and no frontmatter. [ruling: owner, 2026-11-05]
- P2. Unordered rules: no numbered procedure, no output, no calls. Needing
  any of these makes it a skill or a playbook step. [data: 20 of 24 strict]
- P3. About 35 lines at most. More means it carries technique. [data: all
  pstack principles are 34 lines or fewer]
- P4. Never restates `AGENTS.md` (A2, A3).
- P5. The file is `principles/<name>.md` in `mvp-mode`, cited as
  `principle-<name>`, which stays the unit's name in citations, the registry and
  the ledger. [ruling: owner, 2026-11-05]
- P6. Other units cite a principle by name instead of restating it.
- P7. Not skills: they live in `mvp-mode/principles/` and are read by path. The
  router maps situations to them; a delegate gets one by path in its brief.
  [ruling: owner, 2026-11-05]

### Skills

- S1. Its own entry point: asked for alone, or called by two units. [data]
- S2. One deliverable, stated in the skill. A branch the user or a calling
  playbook opts into may add its own deliverable; a reference pack has none.
  [data: 27 of 33 pstack one, 5 two, 1 none; ruling: owner, 2026-11-02 (E4),
  added the calling playbook]
- S3. Its steps are its own job's technique; ordered steps are allowed. It
  does not put other units in order with gates to finish a request (the
  composite test, §2). [data: 16 of 33 pstack skills are ordered]
- S4. Everything not marked conditional is mandatory core. Each branch
  names its condition. [proposed; makes H9 checkable]
- S5. Description: the activation boundary first, a positive case and the
  nearest case to skip. [existing: `authoring-for-agents`]
- S6. Never restates `AGENTS.md` or a principle; cites the principle (P6).
- S7. Model-invocable by default. The router finds skills (R3), but the
  model can invoke only a model-invocable skill through the platform (R6);
  a router-only skill is read as a file and is lost at compaction. Router-only
  when solo use would skip a playbook gate that matters (measured, not
  assumed: see the bypass trial below). A costly opt-in runs only on an explicit
  request, never by itself. A playbook may start one only where a dated owner
  ruling names its caller and condition. A council is never started that way. A
  skill a playbook wraps names that playbook as its nearest case to skip (S5).
  [proposed; pstack disables 57 of 58 for
  opt-in cost; our 24 invocable descriptions cost about 1k tokens]
- S8. Bypass trial, with the first pilot playbook: run its request prompts
  with the wrapped skills invocable; if the model skips the playbook, make
  those skills router-only and log it (E3). [proposed]

### Playbooks

- B1. One kind of request, named after it (`bug-fix`, `feature`). It lives
  in `mvp-mode/playbooks/<name>.md` and is reached only through the router.
  Declared by location and the router's list, not by missing frontmatter.
  [ruling: option D]
- B2. Ordered steps; each has a condition (when it runs or is skipped), its
  own actions and its calls. At run time the steps become todos; a skipped
  step records why. [data: pstack]
- B3. Calls units whole (H9): never skips or overrides a callee's core. If a
  step needs X without step N, make N a branch of X or split X. Folding a
  callee's output into the reply is allowed when all its required content
  survives; doing less of its work is a skip. [proposed; owner's rule]
- B4. Holds order and gates; technique lives in skills. Own actions are
  allowed when no other unit needs them (promotion by reuse, §2). [data: H7,
  51 of 71 actions are not calls]
- B5. Ends in a reply contract, including what the reply says when it stops
  early. [data: 21 of 23]
- B6. Need not ship code; a read-only playbook is fine when it orders several
  units. [data: 9 of 23 pstack do not]
- B7. Every exit, finished or stopped, runs the playbook's closeout.
  [proposed; from the debugging split]
- B8. A step needing authority (commit, push, publish) runs only with it.
  [proposed; `AGENTS.md` Safety]
- B9. A human entry is a thin alias skill that names the playbook.
  [proposed; keeps B1]
- B10. Playbooks may call playbooks; B3 applies. [data: 4 pstack calls]
- B11. A skill may name a playbook only as a route back through the router:
  at top level the agent returns to `mvp-mode`; inside a delegated task it
  reports the route to its parent (R8). A skill never starts a playbook.
  [proposed: critic 1c]
- B12. The step list is the playbook file's YAML frontmatter; the prose
  steps in its body match it. [proposed: critic 1c]

### References

- F1. Belongs to one unit, named at the branch that loads it; never loaded
  unconditionally. [existing: `authoring-for-agents`]
- F2. Needed by a second unit → it becomes a skill (a job), a principle
  (judgement) or a project document (a fact). [proposed]
- F3. A playbook's references live in `playbooks/<name>/`, beside it.
  [proposed: critic 1c]

### Project documents

- D1. Repository facts and conventions for particular work, routed by the
  docs index with a conditional `AGENTS.md` pointer. [existing]
- D2. Not shipped. A shipped unit reads one only "when present". [proposed]

## 4. Traits and steps

### Traits

- T1. Registry §4a stands, widened from skills to every unit: principles,
  skills, playbooks and the router. [proposed]
- T2. One behaviour, one trait, wherever it lives: the same check in a skill
  and in a playbook step is the same trait. [existing]
- T3. A unit holds only the traits it delivers itself. A call is not a
  trait: the callee holds its traits. So a playbook's traits are its gates,
  ordering rules and own actions. [proposed: Q7]
- T4. Reply formats stay in the playbook's text, untraited, until a second
  playbook shares one. [proposed: Q7]
- T5. A match needs the whole mechanism: every unconditional requirement of
  the definition holds. Otherwise it is a variant with `distinct_from`. A
  completion may follow an already frozen, owner-approved rewording that departs
  from the definition, when the holder's notes cite the exact sealed row and the
  deviation is logged. [data: round 3; ruling: owner, 2026-11-02 (E4), added the
  frozen rewording]
- T6. Check existing definitions before adding a new one; prefer a variant.
  [existing]

### Steps

- St1. A step's ID is local to its playbook (`bug-fix#3`). Its fields:
  condition, actions (each with a trait), calls (each to a unit, by kind
  and name: `skill:<name>`, `playbook:<name>`) and loads (references, by
  path relative to the playbook). A load is not a call: B3 does not apply
  to it. The registry identifies documents by repository path (`doc:`).
  [calls/loads split proposed: critic 1c]
- St2. No separate step-definitions file. The playbooks' step lists are the
  source; a generated index (like `TRAITS.md`) shows every step, its traits
  and calls, and where a trait or call recurs. [proposed]
- St3. Changes are recorded per step (added, removed, reordered, condition
  changed, traits changed), so a small change is an edit, not a new
  playbook. [owner's goal]
- St4. Repeating a step across playbooks is fine. The same own action in two
  playbooks is the signal to make it a skill (promotion by reuse). A short
  closeout identical across playbooks may stay local when logged. [ruling:
  owner, 2026-11-02 (E4), added the closeout]
- St5. Pilot first: tag the four pilot playbooks, measure the cost (the
  study counts 31 new trait definitions), then decide whether every playbook
  is traited. [data: H7]

## 5. How the rules change

- E1. **[proposed]** rules are followed as if settled, and tested by use.
- E2. New and touched units follow the rules. Existing units that do not are
  listed below as known deviations until reworked.
- E3. When a rule would make a unit worse, do not force it: record the unit,
  the rule and why, in the log below.
- E4. Two deviations from one rule for the same reason → propose a rule
  change. Rules change only by the owner's ruling, dated.

### Known deviations (from the study)

- Mixed roles (10): `beads`, `brainstorming`, `codebase-design`,
  `codebase-research`, `domain-modeling`, `performance-optimization`,
  `planning`, `security`, `systematic-debugging`, `wayfinder`.
- Playbook-like (2): `execution`, `harness-publish`.
- Principle-like (1): `i-have-adhd`.
- To retire (1): `skill-router` (R1).

### Deviation log

| Date | Unit | Rule | Why | Outcome |
|---|---|---|---|---|
| 2026-10-31 | `mvp-mode` | R2 | It also holds the shared rules for running a playbook (B2, B3, B5, B7, R8): every playbook needs them and the router is their only always-loaded home | R2 amended: revision 1 omitted the shared rules that ruling D already put in the router; a drafting error, not a deviation |
| 2026-10-31 | `skill-router` | R1 | Kept as a manual-only pointer to `mvp-mode`: the registry's lineage and history views match a skill's exact name and do not follow the recorded `merge` | Open: remove the pointer when the views follow merges |
| 2026-11-01 | `harness_lifecycle/playbook.md` | B1, R3 | A playbook by behaviour, but root-only lifecycle method: moving it breaks about a dozen live references and sealed citations, and routing it from the shipped router leaks a root-only line into the plugin. AGENTS.md routes lifecycle work to it (owner ruling 2026-11-01, pstack report decision 15 (a)) | Open: in phase 3, move it to `mvp-mode/playbooks/` and list it in the router once the publish script drops root-only router lines (owner ruling 2026-11-01); a second root-only playbook before then triggers a rule-change proposal (E4) |
| 2026-11-01 | `bug-fix` playbook, step 3 | B3 | The S8 rerun called `test-driven-development` in 1 of 3 fix runs; the other two ran the test-first cycle by hand and kept the red-before-green proof (owner ruling 2026-11-01) | Open: the Pocock traits landed in batch 1 (`per-seam-note`, `one-test-per-cycle`, `behaviour-test-names`, `prove-the-red`) and bring no new evidence, since `prove-the-red` adds cost only on a forced failure. `skill:pstack/skills/tdd` stays unanalysed. Stays open until the S8 F3 prompts are rerun, which needs `cr-r2pa.2.12` passed and the owner's go-ahead |
| 2026-11-01 | `codebase-design` | S2 | The sketch is a second deliverable from a skill already logged as mixed role, and playbooks call its branch where S2 speaks of a branch the user opts into. A separate skill would split one design vocabulary across two units (owner ruling 5, 2026-11-01) | Closed: S2 amended by owner ruling 2026-11-02 (E4), so a branch a calling playbook opts into may add its own deliverable; `performance-optimization`'s located cost falls under the same wording and needs no row |
| 2026-11-01 | `implement-against-sketch` (Feature, Refactoring, `bug-fix`) | St4 | The same own action sits in three playbooks on purpose: owner ruling 5 keeps it out of `codebase-design`, and a skill holding it would rebuild the implement branch the ruling removed, so each build step states it | Accepted, no skill. Perf issue is the fourth caller, with the same wording and form, so the condition did not fire: revisit if a later caller changes the wording or needs a different form |
| 2026-11-01 | `build-closeout` (Feature, Refactoring) | St4, B4 | Each playbook's closeout stays with its own exits and reply contract, and a skill of three short duties would be ceremony | Accepted, no skill. Perf issue is the third, so the condition fired: stays, since a closeout belongs to its playbook's exits and reply (B7) and its text is three duties. Hillclimb and Runtime forensics take the variants `climb-closeout` and `live-forensics-closeout`, whose duties differ. Revisit when a fourth playbook takes this closeout |
| 2026-11-02 | `decision-trail` | S7 | A critic per run is a costly opt-in, which S7 keeps manual, but only a model-invocable skill can be called through the platform (R6) and Hillclimb calls it. Owner ruling 9 accepted the cost | Accepted: a calling playbook invokes it automatically, and its description limits standalone use to an explicit request. Revisit if real sessions (`cr-r2pa.2.12`) show it invoked unasked |
| 2026-11-03 | `interrogate` from Feature step 6 | S7 | Adversaries are a costly opt-in; Feature starts them without asking. Owner ruling: caller Feature step 6, condition the dispute test shipped in `feature.md` | Accepted. Revisit if real sessions show it fires on the lead's own doubt |
| 2026-11-04 | `wake`'s closing timer from Autonomous run step 3 and Hillclimb step 2 | S7 | A timer schedules a further model turn, unwatched, and "overnight" does not name one. Owner ruling amending ruling 12: `wake` is a closing timer only; callers Autonomous run step 3 and Hillclimb step 2; condition a request with unattended words, which count as the explicit request for that timer; closing only. Waiting on a command needs no `wake` | Accepted. Revisit if real sessions show a timer set for an attended run |
| 2026-11-02 | `skip-polish` on `prototype` | T5 | The definition allows no error handling beyond runnability and no abstractions. The sealed rewording keeps the error handling and safety checks needed to run safely, and abstractions that help answer the question. That rewording is frozen and a completion keeps the same trait and `into`, so the text follows the rewording; `traits/ours.yaml` notes it | Accepted for this row |
| 2026-11-02 | `handover-url-keys` on `prototype` | T5 | The definition names a URL. The sealed rewording says a preview pointer, for a surface with no URL, and is frozen in the same way | Accepted for this row. It is the second deviation for this reason, so E4 fired: the owner ruled on 2026-11-02 and T5 now allows it, still logged |
| 2026-11-02 | `session-pickup`, `pause-safely`, `trace-forensics`, `worktree-cleanup` | §2 composite test | Remove each one's calls and its whole result survives from its own actions, so the test calls it a skill. The map and the owner named each a playbook, and a request reaches it directly. Bug fix's obvious-cause path, Refactoring with an existing pin and Feature's local build survive only on that branch, and their normal paths keep their calls, so they are no exception. `eval` loses its required independent judge and verdict, and `runtime-forensics`, `hillclimb`, `investigation`, `perf-issue` and `multi-phase-plan` lose their capture, method, answer, baseline or plan: each passes as a playbook | Accepted by the owner's ruling of 2026-11-02 (E4), for these four: the test stays as written and now says an exception is named here |
| 2026-11-04 | `autonomous-run` | §2 composite test | Remove its calls and a complete technique is left: fix a predicate, inspect, change, check, discard, pivot, decide scope, stop, report. The map and the owner named it a playbook and a request reaches it directly. No skills are manufactured to pass the test | Accepted by the owner's ruling of 2026-11-04 (E4), a fifth named exception |
| 2026-11-02 | `pause-safely`, step 2 | B5 | A pause can reach a point in a running playbook that its reply contract names no exit for, such as Bug fix's first fix after a confirmed diagnosis. Pause's own reply stands in: it states the step reached, marks proof `not reached` rather than failed, and gives that playbook's closeout result, so no caller is edited | Accepted for a pause only. Revisit if real sessions (`cr-r2pa.2.12`) show a pause misreporting a stopped run |
| 2026-11-02 | `read-only-closeout` (Investigation, `session-pickup`) | St4 | The same short closeout in two playbooks is the signal for a skill, but it belongs to each playbook's exits and reply (B7), and a skill for it would be ceremony | Accepted, no skill. With `build-closeout` this is the second deviation from St4 for this reason, so E4 fired: the owner ruled on 2026-11-02, and St4 now allows it when logged |
| 2026-11-03 | `eval`, routing trials (`cr-r2pa.2.15`) | Eval's gates | Eval says a candidate sees no name hinting at an experiment or a test, but a routing trial must show the real harness, including `playbooks/eval.md`, and an ordinary project's `tests/` (owner ruling 2026-11-03) | Accepted for these trials: everything added for a trial stays free of those names, and results note what a session could see |
| 2026-11-04 | `bounded-background-wait`, `limit-bounded-hold`, `read-trail-first`, `row-then-checkpoint`, `run-limits-first`, `stated-unattended-gate`, `worktree-environment-proof` (Autonomous run, Hillclimb; the first and `stated-unattended-gate` also Bug fix) | St4 | The same short rules in two or three loops; a skill of two sentences each would be ceremony | Accepted, no skill. Revisit on another caller |
| 2026-11-04 | `authoring-for-agents`: `build-check-over-rule`, `relevance-check`, `split-by-invocation`; `grilling`: `yes-accepts-recommendation`; `improve-codebase-architecture`: `domain-vocabulary`; `systematic-debugging`: `falsifiable-hypotheses`, `one-variable-at-a-time`; `teach`: `knowledge-skills-wisdom-frame`, `mission-shift-handling`; `triage`: `brief-acceptance-criteria`, `ready-for-human-rationale`; `wayfinder`: `breadth-first-charting`, `invalidated-ticket-reconciliation` | T5 | Each completion follows its frozen, sealed rewording, which is narrower than or differs from the definition. The holder's note in `traits/ours.yaml` cites the row and says how | Accepted for these rows |
| 2026-11-04 | `delegation`, step 4 | A2, S6 | The sealed `background-dispatch-for-dialogue` rewording ends "collect every result", which `AGENTS.md` also says. The rewording is frozen, so the words stay | Accepted: a second place to maintain, nothing that breaks a dispatch |

## 6. Conflicts with what exists, to settle as we go

1. **`skill-router` retires into `mvp-mode`** (R1). Its hand-owned table
   becomes the router's skill lines; `skill-catalog.py` and
   `publish-plugin.sh` retarget from `skill-router` to `mvp-mode`.
2. **`AGENTS.md` routes to skills** ("When needed"). Moves to the router (A4).
3. **`authoring-for-agents`'s surface table** has no principle or playbook
   row, and it ships while this file would not. It gains one row each,
   summarising this file.
4. **Our playbooks have frontmatter step lists**, pstack's have none. The
   declaration is location plus the router's list (B1).
5. **`mvp-mode` ships in the plugin** (ruling 2026-10-31; pstack report
   revision 4). The publish script still hardcodes `skill-router`;
   retargeting it is phase 3.
6. **The registry tracked skills only.** Settled (owner ruling 2026-11-01):
   a principle holds traits as a `skills.yaml` entry, with its file in
   `mvp-mode/principles/` (P7, ruling 2026-11-05), and a playbook holds traits,
   has a step index and is its own ledger subject (registry README §4b).
7. **"Strip procedure from skills"** becomes "move order and gates across
   units out of skills" (S3, B4): a skill keeps its own technique.
