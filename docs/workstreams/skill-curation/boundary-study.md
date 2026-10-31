# Boundary study: principles, skills and playbooks, from the data

Snapshot 2026-10-31, revised the same day after critic round 1 (all nine
findings applied, H9 added) critic round 2 (four findings applied) and critic round 3 (both findings applied). pstack v0.15.36 (`P/plugin.json:4`), checked
out at `4dd1d05`; the committed submodule pointer is still `e43c7ee`, so
this reads the working tree. Pocock at `5beb35b`. Ours at `ab4f6e1`; the
uncommitted edits at the time touch none of `.claude/skills/`. No tracker
writes.

Path aliases: `P/` is `reference_harnesses/cursor_plugins/pstack/`; `PB/` is
`P/skills/poteto-mode/playbooks/`; `MP/` is
`reference_harnesses/mattpocock_skills/skills/`; `O/` is `.claude/skills/`. A
bare `:N` cites the file of the nearest full citation before it.

Counts come from scripts in `scratchpad/boundary/` (gitignored, so local
only). `measure.py` reads every unit (`units.csv`, `edges.csv`).
`analyse.py` joins the hand labels and tests the hypotheses
(`table.csv`, `results.txt`). `check.py` runs the checks. Hand labels:
`annotations.yaml` (round 0, kept for comparison), `recode.yaml`
(deliverables, scope, role and subtype), `edge-types.yaml` (what each name
is), `h7-actions.yaml`, `h9-cases.yaml`. `fix-r1-log.md` and `fix-r2-log.md`
list every count that moved. **J:** marks judgement. Every label in those YAML files is
judgement; everything a regex counts is not. "Inferred" marks a conclusion
the sources do not state.

## Summary

**Clear: principle against everything else.** In pstack, all 24 principles
open their description with "Apply" and no other skill does. All are 34
lines or fewer and 23 yield nothing of their own. The numbered-list proxy
holds for 21 of 24; by **J**, 20 of 24 hold no ordered procedure and no
output (§3, H5).

**Clear by declaration: playbook against skill.** In pstack, 0 of 23
playbooks have frontmatter and all 33 skills do. Playbooks are reached
through the router or another playbook, never by slash command
(`P/skills/poteto-help/SKILL.md:122`). 21 of 23 playbooks end in a `Reply:`
contract, against 5 of 33 skills.

**Not separated by the content rules tested.** No single content rule, and
no tested pair, splits pstack's 23 playbooks from its 33 skills without
exceptions on both sides (§2.3):

- ordered steps: 21 of 23 playbooks, 16 of 33 skills;
- ships code: 14 of 23 playbooks; 8 of 33 skills deliver a change;
- directly calls two or more skills: 9 of 23 playbooks, 8 of 33 skills;
- exactly one deliverable: 22 of 23 playbooks, 27 of 33 skills.

The tightest combination, ordered steps plus a `Reply:` contract, takes 20
playbooks and 2 skills. These are this sample under these codings. They do
not rule out a content boundary with named exceptions.

**What the data supports, per kind.**

- **Principle:** a lens for a named situation ("Apply when …"), unordered
  rules, no output. Exceptions: `build-the-lever` yields a file;
  `separate-before-serializing-shared-state`, `fix-root-causes` and
  `attack-the-premise` carry a short ordered pattern.
- **Skill:** its own entry point and, in 27 of 33, one deliverable. Two
  deliverables in 5 (`architect`, `reflect`, both `maintain-*`, and
  `setup-pstack` when the user accepts its generated verification skill);
  none in 1 (`typescript-best-practices`, a reference pack). 16 have no direct caller.
- **Playbook:** an ordered list for one kind of request, reached through
  the router, ending in a reply contract. 22 of 23 finish the request they
  were chosen for; 14 of 23 ship code. Its steps are its own actions or
  calls to skills, principles and playbooks.

**The boundary is an owner choice** (§6, question 1). The data shows a
reliable declared distinction and several content tendencies. It does not
force either.

**Subtypes cut across roles.** Alias, retired entrypoint, tool wrapper,
setup, style pass, reference pack and composite are subtypes of a role, not
roles of their own. `harness-publish` is a tool wrapper by subtype and
playbook-like by role (§4).

**Ours, whole units.** Of 46: 32 skills (9 of them aliases, 4 tool
wrappers), 10 mixed, 2 playbook-like (`execution`, `harness-publish`), 1
principle-like (`i-have-adhd`), 1 router. `codebase-design` and `beads` are
mixed once their references count.

**H9, the owner's rule: 2 settled firings, 7 open readings.** pstack
playbooks skip or override part of a skill in 2 of 30 direct calls (`eval`
runs two of arena's six phases; `hillclimb` replaces show-me-your-work's
columns). 7 more are ambiguous until three readings are ruled: whether
`architect`'s Phase D is core when the caller implements (4 calls), whether
a Diátaxis "document" is a file (1), and whether Investigation's reply shape
replaces `how`'s and `why`'s output contracts (2). The rate is 2 to 9 of
30. pstack skill-to-skill calls fire more often: 9 of 28, with 1
ambiguous. Our skills: 0 of 33, 1 ambiguous (§3, H9).

**`systematic-debugging` splits, but not cleanly** (§5). Two references
must be cut by section, one fix technique needs a home, and hardening
becomes a conditional branch of the playbook. The playbook fixes only a
confirmed cause and closes out on every exit.

## 1. Units measured

165 units: pstack 81 (1 router, 24 principles, 33 skills, 23 playbooks),
Pocock 38 (every group except `deprecated`), ours 46. Our `in-progress/`
folder holds only a README, so it adds no unit (`O/in-progress/README.md:5`).
Agents, automations and scripts are not units here; they appear where a unit
calls them.

**Measurement scope per feature (F02).**

| Feature | Scope |
|---|---|
| length, numbered items, numbered and `Phase` headings, longest run | entry file only |
| frontmatter keys, description trigger | entry file only |
| `Reply:` contract, Output/Report/Hand-off heading | entry file only |
| files beside `SKILL.md`, reference lines | whole folder |
| names out (edges) | entry file and its Markdown references |
| deliverable, role, subtype (**J**) | whole unit: entry file, its conditional references and every conditional branch, including branches gated on authorization, approval or a request |
| shape (**J**) | entry file; a different shape in a reference is noted as a branch |

Where the entry file alone would label a unit differently, `recode.yaml`
keeps that label as `entry` with the branch that changes it. Five units
differ (§4).

**Names against calls (F06).** A regex finds names, not calls. Round 0
dropped three regex hits that named no unit and added eleven entries by
hand, ten of them new pairs (`brainstorming -> planning` was already
present). Round 1 types every edge used for a call claim, 301 in all:

| Type | Edges | Meaning |
|---|---|---|
| call | 59 | an unconditional step runs it |
| cond-call | 42 | a step runs it under a stated condition |
| part-call | 15 | runs or borrows only part of it |
| forward | 12 | an alias hands the whole request to it |
| lens | 78 | applies a principle |
| handoff | 24 | ends by routing to it |
| mention | 43 | description, comparison, configuration |
| suggest | 12 | tells the user to run it |
| generated | 11 | writes an instruction to run it into an artifact |
| prohibition | 3 | forbids it |
| inferred | 2 | a behaviour paraphrase, not a name |

Every call claim below uses only call, cond-call, part-call and forward
("direct calls"). Four further hits named no unit: two quote the word "why"
(`P/skills/principle-fix-root-causes/SKILL.md:15`), one is Beads' `review`
status, one is "delegation of routine choices". Five missed names were
added with their type, among them Bug fix's `architect/interrogate`
(`PB/bug-fix.md:8`, a mention) and Multi-phase plan's reading list
(`PB/multi-phase-plan.md:152`, generated).

## 2. Measurements and bins

### 2.1 pstack by declared kind

| | Principles | Skills | Playbooks | Router |
|---|---|---|---|---|
| Units | 24 | 33 | 23 | 1 |
| Median lines (range) | 18 (9–34) | 43 (7–163) | 14 (8–155) | 150 |
| Frontmatter | 24 | 33 | 0 | 1 |
| Description opens "Apply" | 24 | 0 | — | 0 |
| Any numbered list | 2 | 17 | 21 | 0 |
| `Reply:` contract | 0 | 5 | 21 | 0 |
| Output, Reply or Hand-off heading | 0 | 11 | 0 | 0 |
| Directly called by 2+ (principles: applied by 2+) | 16 | 11 | 3 | — |
| **J** deliverables: none / one / two | 23 / 1 / 0 | 1 / 27 / 5 | 0 / 22 / 1 | route |

**The deliverable rule (F01), fixed before recoding.** A deliverable is
what a unit hands its caller at the end of its success path, as the thing
asked for or as something kept for use on its own. Not deliverables:
intermediate artifacts the unit consumes itself (a sketch it implements, a
designed workflow it runs, a failing test that becomes part of the
change); completion reporting (summaries, reply contracts, decision trails,
throwaway prototypes kept as evidence); "nothing to do" and "blocked"
exits. Kinds: answer (a finding in any medium), artifact (a made document
that is not a finding), change, state, rewrite, route, none. Zero is
counted apart from one. A branch gated on authorization, approval,
consent or a request counts like any other conditional branch: the gate
decides which branch runs, not whether it is in the label (round 2). The
full rule is at the top of `recode.yaml`.

Skill deliverables: answer 11, artifact 8, change 4, rewrite 4, none 1,
and two kinds in 5. Playbook deliverables: change 14, answer 6,
artifact 1, state 1, artifact and state 1.

### 2.2 Descriptive bins across all 165 units

These are exact bins of two **J** labels, the primary deliverable and the
shape. They are not clusters over all features (F05). Bins of five or more:

| Bin | Units | Who |
|---|---|---|
| change, ordered | 27 | 12 pstack playbooks, 5 pstack skills (`tdd`, `no-comments`, `reflect`, both `maintain-*`), 8 of ours, 2 Pocock |
| none, unordered | 26 | 21 pstack principles, `codebase-design` (ours and Pocock), `security`, `i-have-adhd`, Pocock `writing-for-agents` |
| answer, ordered | 17 | 6 pstack playbooks (`investigation`, both forensics, `prototype`, `eval`, `session-pickup`), `how`, `why`, `recall`, our `research`, `codebase-research`, … |
| artifact, unordered | 15 | `show-me-your-work`, `statechart`, `html-artifact`, `planning`, Pocock `pr`, … |
| answer, unordered | 15 | `review`, `grilling`, `ketchup`, `teach`, the councils, … |
| artifact, ordered | 11 | `multi-phase-plan`, `pause-safely`, `create-verification-skill`, Pocock `to-spec`, … |
| forward, single line | 11 | 9 of ours, Pocock `grill-me` and `grill-with-docs` |
| state, ordered | 8 | 4 Pocock setup skills, `setup-pstack`, `worktree-cleanup`, Pocock `to-tickets`, our `triage` |
| change, unordered | 6 | `opening-a-pr`, `orchestrate`, our `authoring-for-agents`, Pocock `implement`, `tdd`, `chief-of-staff` |

What the bins show, and no more:

1. 21 of the 26 "none, unordered" units are pstack principles. Of the other
   five, three have an answer-yielding branch once their references count:
   both `codebase-design` units and `security`.
2. Playbooks and skills share the "change, ordered" and "answer, ordered"
   bins. Under this coding, output and shape alone do not separate them.

**Trait spread** (`trait-spread.csv`, round 0, labelled by the round-0
kinds): median distinct sub-stages per skill's traits, principle-like 1,
skill 2, mixed 3, playbook-like 4.5, router 5.5, with overlapping ranges.
This describes the kind labels; it does not validate them.

### 2.3 Content rules and their counterexamples

Each rule is tested on pstack's declared playbooks against its skills
(`results.txt`, "content rules").

| Rule for "playbook" | Playbooks | Skills | Counterexamples |
|---|---|---|---|
| no frontmatter (declared) | 23/23 | 0/33 | none |
| ends in `Reply:` | 21/23 | 5/33 | Babysit, Opening a PR; `blast-radius`, `correct`, `figure-it-out`, `recall`, `teach` |
| ordered or phased | 21/23 | 16/33 | Opening a PR, Orchestrate; `architect`, `tdd`, `how`, `why`, … |
| ordered and `Reply:` | 20/23 | 2/33 | Babysit, Opening a PR, Orchestrate; `figure-it-out`, `recall` |
| ships code / delivers a change | 14/23 | 8/33 | the 9 read-only and state playbooks; `architect`, `tdd`, `no-comments`, `reflect`, `correct`, `figure-it-out`, both `maintain-*` |
| ordered, change and `Reply:` | 11/23 | 1/33 | 12 playbooks; `figure-it-out` |
| directly calls 2+ skills | 9/23 | 8/33 | 14 playbooks; `architect`, `teach`, `interrogate`, … |
| exactly one deliverable | 22/23 | 27/33 | Pause safely; the 5 two-deliverable skills |
| directly called by another unit | 7/23 | 17/33 | — |

**J:** only the declared rule separates without exceptions, by
construction. Ordered-and-Reply comes close: 5 exceptions in 56. A content
boundary with those exceptions named is a live alternative (F05).

## 3. Hypotheses

### H1 reuse: a skill is called by more than one unit, or used standalone

**Verdict: holds only through the standalone clause, read as static
invocability.** All 33 pstack skills have frontmatter and a slash name.
That shows each can be invoked alone. It does not show standalone use: no
invocation history was examined.

The reuse clause alone, by direct calls (routers and help excluded):

- two or more callers: 11 of 33;
- one caller: 6, for example `tdd` from Bug fix only (`PB/bug-fix.md:11`),
  `swarm` from Autopilot-full only (`PB/autopilot-full.md:14`);
- none: 16. Among them `blast-radius`, `recall`, `reflect`, `teach`,
  `correct`, `figure-it-out`, both `maintain-*` and `statechart`.

By mentions, as in round 0, the counts are 15 / 8 / 10: mentions such as
`setup-pstack -> architect` (model-role configuration,
`P/skills/setup-pstack/SKILL.md:31`) and
`create-formal-verification-skill -> maintain-formal-verification-skill`
(a suggestion to the user, `P/skills/create-formal-verification-skill/SKILL.md:43`)
are not calls. Principles: 16 of 24 applied by two or more units, 4 by none.

**J:** reuse does not define a skill.

### H2 standalone: each skill has its own invocation; no playbook does

**Verdict: holds, 81 of 81, as declaration.** All 58 skill folders, the
router included, have frontmatter and a slash name. 57 set
`disable-model-invocation: true`; only `setup-pstack` can load from the
user's words (`P/skills/poteto-help/SKILL.md:42`). No playbook has
frontmatter or a slash command (`P/skills/poteto-help/SKILL.md:122`).

Qualifications:

- In Claude Code the Skill tool refuses most pstack skills, so a unit runs
  one by reading its file (`P/docs/harness/claude-code.md:12`).
- "Router-only" is the registration convention, not a ban on handoffs.
  Recall routes to Session pickup (`P/skills/recall/SKILL.md:17`), and 7
  playbooks are directly called by other playbooks, Opening a PR by 9.

### H3 one output: a skill yields one kind of result; a playbook yields finished work

Recoded under the deliverable rule (§2.1), with both playbook tests defined
before counting (`recode.yaml`).

**Skills: holds for 27 of 33.** Two deliverables: `architect` (code and
the rationale that "ships alongside", `P/skills/architect/SKILL.md:79`),
`reflect` (skill edits and Backlog items filed to the tracker,
`P/skills/reflect/SKILL.md:49`), `maintain-verification-skill` (a PR and
product gaps "record[ed] for the user",
`P/skills/maintain-verification-skill/SKILL.md:35`),
`maintain-formal-verification-skill` (verification updates and code bugs
reported as findings, `P/skills/maintain-formal-verification-skill/SKILL.md:17`)
and, on one branch, `setup-pstack` (the model rule, plus a generated
verification or formal-verification skill when the user accepts the offer,
`P/skills/setup-pstack/SKILL.md:74`, `:78`).
None: `typescript-best-practices`, a rule table.

Moved from round 0: `tdd` (the test is part of the change),
`no-comments` (its report is completion reporting) and `figure-it-out` (it
runs the workflow it designs, `P/skills/figure-it-out/SKILL.md:34`) now
have one deliverable.

**Playbooks, "finishes the request" as written: holds for 22 of 23.**
Session pickup hands the remaining work to the routed playbook
(`PB/session-pickup.md:8`). Investigation and Multi-phase plan finish:
their requests are an answer and a plan (`PB/investigation.md:5`,
`PB/multi-phase-plan.md:3`).

**Playbooks, "ships code": holds for 14 of 23.** The nine that do not:
Investigation, both forensics, Eval, Prototype, Multi-phase plan, Session
pickup, Pause safely, Worktree cleanup.

**J:** "finishes" separates little. It was not coded for skills, and most
skills plausibly finish what they are called for (not counted). "Ships
code" is a real split but leaves nine read-only or state playbooks out.

### H4 value: a skill's steps are one capability's technique; a playbook's value is order and gates across capabilities

**Verdict: fails as a separator.** By direct calls, 8 pstack skills call
two or more skills: `architect` (4), `blast-radius`, `no-comments`, `teach`
(3 each), `figure-it-out`, `interrogate`, `recall`, `setup-pstack` (2
each). 14 of 23 playbooks directly call at most one skill. Babysit
(`PB/babysit.md:7-21`), Shipping (`PB/shipping.md:5-10`), Worktree cleanup
(`PB/worktree-cleanup.md:3-8`) and Pause safely (`PB/pause-safely.md:5-8`)
call none: their value is order and gates inside one domain.

**J:** a narrower reading fits more units: a playbook orders and gates one
kind of request; a skill supplies technique. That is a description, not a
measured classifier.

### H5 principles have no numbered procedure and no output of their own

**Verdict: the proxy holds for 21 of 24; the procedure reading, by J, for
20 of 24 (F08).**

- Numbered lists (proxy): `separate-before-serializing-shared-state`, an
  ordered decision sequence
  (`P/skills/principle-separate-before-serializing-shared-state/SKILL.md:14-16`),
  and `make-operations-idempotent`, three questions whose order does not
  matter (`P/skills/principle-make-operations-idempotent/SKILL.md:17-20`).
- An output: `build-the-lever` (`P/skills/principle-build-the-lever/SKILL.md:18`).
- Ordered procedures without numbers (**J**): `fix-root-causes` opens
  "Reproduce first", then traces and instruments
  (`P/skills/principle-fix-root-causes/SKILL.md:14-16`); `attack-the-premise`
  writes the premise, tests it, follows the evidence, then gates
  (`P/skills/principle-attack-the-premise/SKILL.md:14-16`, `:19`).

So the procedure set (**J**) is `separate-before-serializing`,
`fix-root-causes` and `attack-the-premise`; with `build-the-lever`, 4
exceptions. The checklist principle passes.

### H6 every pstack playbook calls two or more skills

**Verdict: fails.** By direct calls: 9 of 23 call two or more skills; 12
counting principles; 15 counting playbooks too. 12 call no skill directly,
among them Babysit (`PB/babysit.md:12`, a script), Shipping (outside
verifiers, `PB/shipping.md:5`) and Authoring a skill (Cursor's
`create-skill` and Opening a PR, `PB/authoring-a-skill.md:5`, `:8`). By
mentions, round 0 had 9, 13 and 20.

**J:** composition is common, not defining.

### H7 the pilot playbooks' step actions against trait definitions

Round 1 inventories every material action in the 22 numbered steps and
Bug fix's gate (`h7-actions.yaml`, F03): 71 actions, plus 4 that restate one
already listed. Each is mapped against
`harness_lifecycle/registry/trait-definitions.yaml` as one of:

- **exact**: a definition states the mechanism;
- **nuance**: a definition states it, and the wording adds no separate
  mechanism;
- **variant**: a looser, stricter or differently gated form. The registry
  requires a separate `distinct_from` trait for it
  (`harness_lifecycle/registry/README.md:226-228`), so it counts as new;
- **missing**: no definition;
- **call**: routing to another unit, not a trait
  (`harness_lifecycle/registry/README.md:229-232`).

Round 2 tightens exact and nuance (R2-02): the action must carry the
definition's whole mechanism, including the part its `distinct_from` note
separates it by. An action that carries only part of it, or lacks a
requirement the definition makes unconditional, is a variant, unless
another existing definition matches it whole. Every exact and nuance
mapping was recompared on that test, and the alternatives searched are
recorded per row (`alt` in `h7-actions.yaml`).

| Match | Actions |
|---|---|
| exact | 9 |
| nuance | 11 |
| variant | 16 |
| missing | 15 |
| call | 20 |

Steps roll up by a stated rule: covered if every non-call action is exact
or nuance; partly covered if some are; uncovered if none are.

| Step roll-up | Steps | Which |
|---|---|---|
| covered | 3 | multi-phase-plan 7; session-pickup 5; pause-safely 4 |
| partly covered | 6 | bug-fix 2, 3; multi-phase-plan 2, 3, 4; session-pickup 1 |
| uncovered | 12 | bug-fix 1, 4, 5; multi-phase-plan 1, 5, 6; session-pickup 2, 3, 4; pause-safely 1, 2, 3 |
| call only | 1 | bug-fix 6 |

The gate is partly covered.

**31 new definitions would be needed**, 16 variants and 15 missing. Examples:

- variants: `reproduce-on-matching-surface` (`PB/bug-fix.md:7`, against
  `reproduction-first`), `delegate-implementation` (`PB/bug-fix.md:9`,
  against `coordinator-delegates-all`), `one-section-per-pr`
  (`PB/multi-phase-plan.md:8`), `no-irreversible-pause`
  (`PB/pause-safely.md:6`, forbids where `irreversible-confirmation` asks);
- missing: `red-commit-first` (`PB/bug-fix.md:11`), `inconclusive-not-pass`
  (`PB/bug-fix.md:10`), `plan-lint` (`PB/multi-phase-plan.md:10`),
  `pickup-verdict` (`PB/session-pickup.md:8`), `wip-commit`
  (`PB/pause-safely.md:7`), `cancel-nested-agents` (`PB/pause-safely.md:5`).

The full list is in `results.txt`.

**Corrections in round 2.** Four mappings move from nuance to variant:

- Bug fix step 3, delegate implementation to a subagent:
  `coordinator-delegates-all` requires all work in subagents
  (`harness_lifecycle/registry/trait-definitions.yaml:3246-3250`), and Bug
  fix reproduces the bug itself (`PB/bug-fix.md:7`). `delegation-threshold`
  delegates only when it pays, and `delegate-afk-work` only work that needs
  no steering. New variant: `delegate-implementation`.
- Bug fix step 4, the original repro now passes (`PB/bug-fix.md:10`):
  `regression-check` requires a durable check shown red then green
  (`harness_lifecycle/registry/trait-definitions.yaml:2401-2405`); this step
  only reruns the repro. `original-failure-check` designs a check and has
  no rerun gate. New variant: `rerun-original-repro`.
- Multi-phase plan step 3, explore in subagents
  (`PB/multi-phase-plan.md:7`): `background-agent` requires the caller to
  keep working meanwhile
  (`harness_lifecycle/registry/trait-definitions.yaml:769-774`). The
  registry's delegated-exploration trait, `delegated-codebase-walk`, fixes
  the walk's target as friction
  (`harness_lifecycle/registry/trait-definitions.yaml:3140-3145`). New
  variant, looser in target: `delegated-exploration`.
- Session pickup step 2, reconstruct operational state
  (`PB/session-pickup.md:6`), found by the recheck: `context-recovery`
  persists scope, decisions and next work before compaction, then rebuilds
  from them (`harness_lifecycle/registry/trait-definitions.yaml:2716-2717`).
  The step is only the rebuild. New variant:
  `reconstruct-operational-state`.

**Corrections in round 3 (R3-01).** The four mappings round 2 kept as
nuance fail the same whole-mechanism test and move to variant, each with
`distinct_from` and the omitted requirement recorded (`omits` in
`h7-actions.yaml`); the rule itself is unchanged:

- Bug fix step 1, synthesize the trigger or instrument until it fires
  (`PB/bug-fix.md:7`): `tighten-loop` requires continually improving the
  loop's speed and determinism
  (`harness_lifecycle/registry/trait-definitions.yaml:2353-2357`), and
  `flake-reproduction` also requires diagnosing the flake class
  (`:2262-2266`). New variant: `force-reproduction`.
- Bug fix step 2, confirm the surviving mechanism before design
  (`PB/bug-fix.md:8`): `owning-fix` also requires the fix at its owning
  layer (`harness_lifecycle/registry/trait-definitions.yaml:2313-2314`),
  which `owning-layer-fix`'s note keeps required (`:2363-2367`). New
  variant: `confirm-cause-before-design`.
- Multi-phase plan step 1, skip the plan, say so and stop
  (`PB/multi-phase-plan.md:5`): a refusal threshold that routes nowhere,
  where `route-by-scale` routes to a brief local sequence or another path
  (`harness_lifecycle/registry/trait-definitions.yaml:1971-1972`). New
  variant: `plan-refusal-threshold`.
- Multi-phase plan step 2, give options (`PB/multi-phase-plan.md:6`):
  `options-with-tradeoffs` requires their tradeoffs
  (`harness_lifecycle/registry/trait-definitions.yaml:278-279`). New
  variant: `give-options`.

**Corrections to round 0.** Multi-phase plan step 5 and Session pickup
step 4 are not call-only. Step 5 also fixes the document mode, headings and
punctuation (`PB/multi-phase-plan.md:9`); step 4 also picks a verdict among
four (`PB/session-pickup.md:8`). Round 0's `revert-refuted-hypothesis` is
not new: `revert-ineffective-experiments` already states the mechanism,
removing one's own failed experimental edits
(`harness_lifecycle/registry/trait-definitions.yaml:2215-2217`).

**What H7 shows (J).** 20 of 71 actions are calls. 20 match existing
definitions closely (9 exact, 11 nuance). Most of the 31 new ones are
specific to one playbook:
plan formatting, transcript pickup, pausing. Four are general coordination
and verification mechanisms that the registry holds only in a stricter or
narrower form: `delegate-implementation`, `delegated-exploration`,
`rerun-original-repro` and `reconstruct-operational-state`. Round 3's
four are weaker forms of existing diagnosis, planning and clarification
traits: `force-reproduction`, `confirm-cause-before-design`,
`plan-refusal-threshold` and `give-options`. `wip-commit`
and `red-commit-first` need commits, which conflict with our commit
authority (`AGENTS.md:64`).

### H8 pstack principles already in our `AGENTS.md`

**Five strong pairs, five partial, one contrast, thirteen with no
counterpart.** Unchanged in round 1. Trait keys on our side are from
`doc:AGENTS.md` in `harness_lifecycle/registry/traits/ours.yaml:181`.

| pstack principle | `AGENTS.md` | Fit |
|---|---|---|
| `laziness-protocol`, "Minimize the diff" (`P/skills/principle-laziness-protocol/SKILL.md:10`) | "smallest necessary change" (`AGENTS.md:3`), `smallest-sufficient-change` | strong |
| `fix-root-causes` (`P/skills/principle-fix-root-causes/SKILL.md:9`) | owning layer, affected callers (`AGENTS.md:36-37`), `owning-layer-fix`, `caller-impact-check` | strong; pstack adds "fix every instance" (`P/skills/principle-fix-root-causes/SKILL.md:19`) |
| `prove-it-works`, no proxies or self-reports (`P/skills/principle-prove-it-works/SKILL.md:9`) | verify agent reports (`AGENTS.md:23-24`); checks and report (`AGENTS.md:51-55`) | strong |
| `never-block-on-the-human` (`P/skills/principle-never-block-on-the-human/SKILL.md:9-14`) | decide routine details, keep working (`AGENTS.md:9-10`); authorization for irreversible acts (`AGENTS.md:11-12`) | strong, a variant: pstack's router lets team chat and ticket updates proceed without asking (`P/skills/poteto-mode/SKILL.md:84`), though the principle asks confirmation for external messages (`P/skills/principle-never-block-on-the-human/SKILL.md:13`); ours needs authorization for messages |
| `guard-the-context-window` (`P/skills/principle-guard-the-context-window/SKILL.md:3`) | logs behind references (`AGENTS.md:20-21`); delegate for context use (`AGENTS.md:42-43`) | strong |
| `subtract-before-you-add`, "observed usage, not speculative" (`P/skills/principle-subtract-before-you-add/SKILL.md:15`) | present requirement only (`AGENTS.md:34-35`) | partial: one bullet of seven |
| `separate-before-serializing-shared-state` (`P/skills/principle-separate-before-serializing-shared-state/SKILL.md:9`) | "serialize … overlapping writes" (`AGENTS.md:40`) | partial, opposite default: pstack removes the sharing first |
| `attack-the-premise` (`P/skills/principle-attack-the-premise/SKILL.md:9`) | change approach when attempts give no new evidence (`AGENTS.md:41`) | partial: ours does not ask for the premise |
| `make-operations-idempotent` (`P/skills/principle-make-operations-idempotent/SKILL.md:9`) | retry only when repetition is safe (`AGENTS.md:60-61`) | partial: a use rule, not a design rule |
| `test-behavior-not-implementation` (`P/skills/principle-test-behavior-not-implementation/SKILL.md:9`) | bug checks detect the original failure (`AGENTS.md:51-52`) | partial; the rest lives in `O/test-driven-development/SKILL.md:48-50` |
| `encode-lessons-in-structure` (`P/skills/principle-encode-lessons-in-structure/SKILL.md:3`) | record recurring patterns in `learnings.md` (`AGENTS.md:27-28`) | contrast: pstack says encode as a check, not text |

No counterpart: `boundary-discipline`, `build-the-lever`,
`exhaust-the-design-space`, `experience-first`, `explain-the-number`,
`foundational-thinking`, `migrate-callers-then-delete-legacy-apis`,
`minimize-reader-load`, `model-the-domain`, `outcome-oriented-execution`,
`redesign-from-first-principles`, `sequence-verifiable-units`,
`type-system-discipline`.

Router lines also match `AGENTS.md`, though they are not principles. "No is
an acceptable answer" (`P/skills/poteto-mode/SKILL.md:90`) matches
`AGENTS.md:13-14`. "Never fabricate a link" and "evidence or its label"
(`P/skills/poteto-mode/SKILL.md:113-114`) match `AGENTS.md:15-16`.

### H9 the owner's rule: a playbook never skips or overrides part of a skill's mandatory core

The rule: "a playbook never skips or overrides part of a skill's mandatory
core; if a step needs skill X without its step N, split X or make N a
conditional branch". Tested on every direct call from a pstack playbook to
a skill (30), and from each of our skills to another of ours (33). pstack
playbook-to-playbook (17) and skill-to-skill (28) calls are reported apart:
the same pattern, outside the rule's words (`h9-cases.yaml`).

Round 2 rereads every clean call against the callee's complete contract
(R2-01): its steps, its output and presentation rules, and its own
exceptions, not only the line the caller cites. A part the callee marks as
a default or optional is a parameter, so setting it is clean.

**pstack playbooks to skills: 2 fire, 7 ambiguous, 2 carve-outs, 19 clean.**

| Caller → callee | Class | Evidence |
|---|---|---|
| Eval → `arena` | skip | runs Phase B and Phase C only (`PB/eval.md:20-21`); arena opens a todo for each of six phases (`P/skills/arena/SKILL.md:9`) |
| Hillclimb → `show-me-your-work` | override | its own columns for `decision.tsv` (`PB/hillclimb.md:9`) in place of the fixed header (`P/skills/show-me-your-work/SKILL.md:15-22`) |
| Bug fix, Perf issue, Feature, Refactoring → `architect` | ambiguous | each uses architect for design, then delegates or does the implementation itself (`PB/bug-fix.md:9`, `PB/perf-issue.md:17`, `PB/feature.md:6`, `PB/refactoring.md:9`); whether architect's Phase D, implement against the sketch, still runs is unstated (`P/skills/architect/SKILL.md:51`) |
| Multi-phase plan → `technical-writing` | ambiguous | how-to body with explanation and reference appendices in one file (`PB/multi-phase-plan.md:9`); the skill says one document, one mode (`P/skills/technical-writing/SKILL.md:32`), split and link instead (`:49`). It fires only if a document is a file, which is unresolved |
| Investigation → `how` | ambiguous | a recommendation table may replace how's output sections (`PB/investigation.md:9`, `P/skills/how/SKILL.md:32-36`) |
| Investigation → `why` | ambiguous | motivation questions go through why (`PB/investigation.md:7`), but the reply is how-shaped or a recommendation table (`:9`); why keeps its confidence separation and one Sources Consulted line per investigator (`P/skills/why/SKILL.md:92`) |

Two calls are carve-outs on the callee's side, so the rule does not fire:

- Opening a PR → `technical-writing`: "every layer except Diátaxis"
  (`PB/opening-a-pr.md:9`) is the skill's own rule for PR descriptions and
  commit messages (`P/skills/technical-writing/SKILL.md:94`). Its "Apply
  all four layers" (`:9`) does not bind them. Round 1 counted this call as
  a skip.
- Bug fix → `tdd`: "skip when the test would be expensive"
  (`PB/bug-fix.md:11`) matches tdd's own "Do not force a test"
  (`P/skills/tdd/SKILL.md:11`).

Several clean calls set a parameter the callee leaves open. For example,
Autopilot-full keeps its decision trail in the root agent's store
(`PB/autopilot-full.md:12`), where show-me-your-work's location is a
default (`P/skills/show-me-your-work/SKILL.md:46`).

No pstack caller argues with `architect`'s mandatory design-it-twice
(`P/skills/architect/SKILL.md:33`). Callers run architect whole, or stop at
the sketch (`P/skills/no-comments/SKILL.md:21`, a skill). Where the caller
implements afterwards, as the four playbooks and `figure-it-out` do
(`P/skills/figure-it-out/SKILL.md:30`, `:34`), whether Phase D still runs is
unstated.

**Outside the rule's words, same pattern.**

- Playbook to playbook, 4 of 17: Autopilot-stack replaces Autopilot-full's
  step 5 and excepts steps 2 and 3 (`PB/autopilot-stack.md:3-6`);
  Hillclimb borrows Autonomous run's wake mechanism without its stop rule
  (`PB/hillclimb.md:16`) and Perf issue's mantra order without its stop
  rule (`PB/hillclimb.md:10`); Multi-phase plan keeps a prototype's
  evidence in place of Prototype's hand-off to Feature
  (`PB/multi-phase-plan.md:6`, `PB/prototype.md:12`).
- Two playbook calls show the rule's remedy already applied: Babysit names
  the Autopilot owner as the exception to its no-rebase rule
  (`PB/babysit.md:10`), and Opening a PR does the same for babysitting
  (`PB/opening-a-pr.md:34`).
- Four playbook calls only borrow a rule or a script, such as Shipping's
  patch-id rule (`PB/autopilot-full.md:5`). The rule would misfire on these.
- pstack skill to skill, 9 of 28 fire and 1 is ambiguous. `no-comments`
  stops `architect` at the sketch; `interrogate` runs part of `arena` "with
  four changes" (`P/skills/interrogate/SKILL.md:17`); `architect` replaces
  arena's runners (`P/skills/architect/SKILL.md:31`); `ketchup` takes
  `bro`'s voice, "not its task" (`P/skills/ketchup/SKILL.md:11`);
  `ketchup-video`, `blast-radius` and `recall` take or reshape part of
  their callees.
- Round 2 adds two skill-to-skill overrides. `teach` says "Reword freely
  for teaching" (`P/skills/teach/SKILL.md:11`); `how` allows light edits
  and forbids substantial rewriting (`P/skills/how/SKILL.md:32`), and `why`
  allows light edits and keeps its confidence separation and sources
  (`P/skills/why/SKILL.md:88`, `:92`). `teach` keeps why's confidence
  language, the one rule why puts in bold. It also narrows why's sweep by
  default because the full sweep is slow (`P/skills/teach/SKILL.md:14`);
  why defaults to the full sweep and skips a source only for a written
  reason (`P/skills/why/SKILL.md:31`, `:70-75`). `figure-it-out` →
  `architect` is ambiguous on Phase D, as above.

**Our skills: 0 of 33 fire; 1 ambiguous; 4 borrow a section.** `security`
reports through review's severity and output contract and disclaims "a
second compulsory review process" (`O/security/SKILL.md:44-45`). That
fires only if review's independent-critic rule (`O/review/SKILL.md:12`)
binds a security pass by the author. The aliases select a mode or
parameter the callee already offers, for example grilling's optional
documentation (`O/grilling/SKILL.md:31`). Rereading all 28 clean calls
against their full callees moved none.

**Verdict (J): the rule names real seams, but its rate is not settled.**
Two pstack playbook calls fire with no reading in dispute. Each names a
real seam and has the rule's remedy: an arena whose fan-out and judge are
reused without its pick and graft (split them into a callable part), and a
log format that should take columns (let show-me-your-work take them).
Round 1's third remedy, a conditional Diátaxis layer, is already in
`technical-writing`. Seven more calls turn on three readings for the owner
to rule: is `architect`'s Phase D core when the caller implements; is a
Diátaxis document a file; may a caller fold a callee's output contract into
its own reply shape. The rate is 2 of 30 on the settled calls and up to 9
if every reading goes against the caller. Extended to skill-to-skill
calls, the rule fires on 9 of 28, so its scope is a further choice. To
avoid firing too often, the rule should count direct calls only, and
exempt section references and callee-side carve-outs.

## 4. Our skills, classified

Same features; role and subtype on separate axes (F05); whole units with
their conditional references (F02).

**Roles.** skill 32, mixed 10, playbook-like 2, principle-like 1, router 1.

**Subtypes,** overlapping and optional: alias 9, composite 7 (directly
calls two or more skills), tool wrapper 5, style pass 2, reference pack 1,
setup 1, retired entrypoint 1. 22 have none.

**Measured differences from pstack.** Our skills carry no `Reply:` contract
(0 of 46). 30 of 46 descriptions carry a trigger phrase. 22 of 46 are
manual-only. Every folder has a file beside `SKILL.md`, at least the
`agents/openai.yaml` sidecar. 8 are directly called by two or more others
besides the router; 31 by none.

**Entry file against whole unit.** Five units change label when their
conditional references count:

- `codebase-design`: the entry file is a lens (`O/codebase-design/SKILL.md:8-9`);
  for a consequential interface choice it routes to `DESIGN-IT-TWICE.md`
  (`O/codebase-design/SKILL.md:39-41`), which sketches designs, compares
  them and recommends one (`O/codebase-design/DESIGN-IT-TWICE.md:3-13`).
  Whole unit: mixed, none or an answer. Pocock's is the same, with a
  three-stage procedure and parallel subagents
  (`MP/engineering/codebase-design/DESIGN-IT-TWICE.md:7-44`).
- `beads`: an index of when to read which file (`O/beads/SKILL.md:37-47`);
  `references/setup.md` is a ten-step adoption procedure that writes
  config and hooks (`O/beads/references/setup.md:20-90`). Whole unit:
  mixed, reference pack and setup.
- `planning`: its Decompose branch seeds epics in the tracker
  (`O/planning/references/decompose.md:51-83`). An artifact, or an
  artifact and state.
- `review`: incoming findings end "fixed with evidence"
  (`O/review/references/feedback.md:7-8`). An answer, or a change.

**Authorized and requested branches (round 2).** A gate decides which
branch runs; it does not remove the branch from the label (§2.1). Nine
units are recoded:

- `harness-evaluate`: a recommendation; with ledger authority, the
  recommendation and its recorded curation decision; with adoption
  authority, the edited canonical source and its adopt record
  (`O/harness-evaluate/SKILL.md:17-26`, `:29-46`). Answer, answer and
  state, or change and state.
- `teach`: an explanation; for an authorized course, lessons plus the
  mission, resources, glossary and learning-record documents
  (`O/teach/SKILL.md:27-37`). The mission persists goals and constraints
  that steer later sessions (`O/teach/MISSION-FORMAT.md:3-22`). Answer, or
  answer and artifact.
- `grilling` and `improve-codebase-architecture`: documentation through
  `domain-modeling` when requested (`O/grilling/SKILL.md:31-32`,
  `O/improve-codebase-architecture/SKILL.md:28-29`). Answer, or answer and
  artifact.
- `review`: document mode edits unambiguous wording when fixes are
  requested (`O/review/SKILL.md:41-43`). Answer, change, or answer and
  change.
- `domain-modeling`: glossary and ADR files only when documentation work is
  authorized (`O/domain-modeling/SKILL.md:18-19`); otherwise the sharpened
  terms in the conversation. Artifact, or answer.
- pstack `setup-pstack`: on the user's yes, a generated verification skill
  (`P/skills/setup-pstack/SKILL.md:74`, `:78`). State, or state and
  artifact; this moves H3 to 27 of 33.
- pstack `reflect`: approved edits and the Backlog items it files without
  waiting; with no edit approved, the Backlog items alone
  (`P/skills/reflect/SKILL.md:47`, `:49`). Change and state, or state.
- Pocock `teach`: round 1 read its course files as made on request. They
  are its default, a stateful teaching workspace
  (`MP/productivity/teach/SKILL.md:8`, `:12-20`). Answer and artifact.

No primary deliverable changed, so the bins in §2.2 stand. Other gated
passages keep their labels: a saved report is an answer's medium
(`O/research/SKILL.md:22`), and a saved council transcript is completion
reporting (`O/perspective-council/SKILL.md:40`).

**Pure roles, by name.**

- Skills (32), among them the aliases `document-review`, `grill-me`,
  `grill-with-docs`, `idea-refine`, `phase-execution`,
  `receiving-code-review`, `run-phases`, `teach-session` and
  `verification-before-completion` (the last forwards to `AGENTS.md`, not
  a skill, `O/verification-before-completion/SKILL.md:9-12`); the tool
  wrappers `check-invariants`, `harness-scan`, `harness-status`,
  `migrate-claude-to-codex`; the style pass `show-me`.
- `cost-estimate` is a retired entrypoint with residual guidance, not an
  alias (F07): it forwards nowhere and still says how to estimate (clarify
  the subject, scoped evidence, ranges and unknowns,
  `O/cost-estimate/SKILL.md:13-16`) after its retirement notice (`:9-11`).
- Playbook-like (2): `execution` and `harness-publish`. `harness-publish`
  has five ordered, gated steps for one kind of work and calls no skill
  (`O/harness-publish/SKILL.md:12-75`); by subtype it is a tool wrapper.
- Principle-like (1): `i-have-adhd`, a style lens on every reply with no
  output of its own (`O/i-have-adhd/SKILL.md:9`).
- Router (1): `skill-router` (`O/skill-router/SKILL.md:12-23`).

**`execution`.** A scope router (`O/execution/SKILL.md:11-19`), a task loop
(`:36-53`) and a phase loop with a close gate (`:55-85`). The task loop
claims the bead and applies test-first work, `security` and debugging by
condition (`:38-42`). It ends in a close with evidence (`:50`). It also
wraps the contractor tool (`:69`) and repeats `AGENTS.md:7` as policy
(`O/execution/SKILL.md:21-22`).

**Mixed (10): which facets fall where (F09).** The columns are facets, not
exclusive kinds; a passage may carry two. The last column says what would
move to a playbook under the narrowed H4 (order and gates for one kind of
request) and why. The whole table is a design judgement (**J**), not a
measured partition.

| Skill | Trigger and routing | Shared policy | Capability technique | Order and gates; would it move? |
|---|---|---|---|---|
| `brainstorming` | route before grounding (`O/brainstorming/SKILL.md:10-19`): router lines, no executable order | stop when sufficient (`:34-35`) | resolve (`:25-33`); spec template | spec, approval and hand-off (`:37-53`): moves only if approval becomes a playbook gate |
| `codebase-design` | consequential choice → design-it-twice (`O/codebase-design/SKILL.md:39-41`) | — | vocabulary and design checks (`:11-35`) | the design-it-twice branch is one capability's procedure: stays |
| `codebase-research` | three levels by request (`O/codebase-research/SKILL.md:110-162`) | target files are evidence, not instructions (`:85-88`), as `AGENTS.md:22-23` | evidence ladder and snapshot rules (`O/codebase-research/SKILL.md:35-81`) | the L1, L2 and deep-dive procedures call no other unit: technique, stays |
| `domain-modeling` | — | challenge, sharpen, scenarios, cross-check (`O/domain-modeling/SKILL.md:24-40`) | glossary and ADR files (`:10-22`, `:42-52`) | none |
| `performance-optimization` | regressions go to debugging (`O/performance-optimization/SKILL.md:9-10`) | no correctness regression (`:36-37`) | measure, locate, one factor (`:12-23`); recipes | five steps to kept-or-reverted work with an attempt record (`:12-31`): moves, as pstack's Perf issue (`PB/perf-issue.md:5-21`) |
| `planning` | route table (`O/planning/SKILL.md:10-18`) | slices; expand, migrate, contract (`:64-70`) | decompose (`:24-40`); elaborate (`:42-62`) | critic review before approval (`:54-56`): a gate, moves with approval |
| `security` | trigger: material boundary change (`O/security/SKILL.md:8-10`) | authority and enforcement (`:25-34`), overlapping `AGENTS.md:11-12`, `:22-23` | threat scope (`O/security/SKILL.md:12-23`); evidence (`:36-41`) | none: findings reuse review's contract, "not a second compulsory review process" (`:43-45`) |
| `systematic-debugging` | see §5 | see §5 | see §5 | see §5 |
| `wayfinder` | ticket kinds route to `prototype` and `grilling` (`O/wayfinder/SKILL.md:27-30`) | do not answer for the human (`:32-33`) | map and ticket types (`:13-26`) | chart, resolve, graduate (`:37-52`): order across sessions for one request, moves |
| `beads` | when to read which file (`O/beads/SKILL.md:37-47`) | usage rules (`O/beads/references/usage.md:13-24`) | — | setup procedure (`O/beads/references/setup.md:20-90`): a setup subtype; moves only if setup becomes a playbook |

**Pocock, briefly** (38 units, whole-unit roles in `recode.yaml`). Skill
27, playbook-like 6, mixed 3, principle-like 1, router 1. Subtypes:
composite 6, setup 4, tool wrapper 3, alias 2, style pass 1. Pocock writes
its flows in the router, not in playbook files: `ask-matt` describes a
main flow and on-ramps through the skills
(`MP/engineering/ask-matt/SKILL.md:13`, `:15`, `:42`). Its playbook-like
units are composite skills. `implement` calls `tdd`, then `code-review`,
then commits (`MP/engineering/implement/SKILL.md:11`, `:15`, `:17`).
`improve-codebase-architecture` ends by calling `grilling` and
`domain-modeling` (`MP/engineering/improve-codebase-architecture/SKILL.md:64`,
`:66`). Its aliases are one line: "Call the Skill tool with "grilling""
(`MP/productivity/grill-me/SKILL.md:7`).

**J:** three designs, one need. pstack puts procedures in router-reached
playbook files. Pocock puts the flow in its router and the steps in
composite skills. We put the procedure in one skill (`execution`) and
routing in a table.

## 5. Worked example: `systematic-debugging`

The rules used: a principle is a lens with no output (H5); a skill is one
capability with, normally, one deliverable (H3); a playbook orders and
gates one kind of request, and its steps are actions or calls (H4 narrowed,
H6); and H9: a step calls a skill whole, or the skill gains a conditional
branch. References are partitioned by section, not by file (F04).

### 5.1 Section by section

| Lines | Content | Falls to |
|---|---|---|
| `O/systematic-debugging/SKILL.md:3` | trigger: unclear cause, failed fix, flake | router line |
| `O/systematic-debugging/SKILL.md:8-10` | the obvious case skips the investigation | playbook skip rule, like `PB/multi-phase-plan.md:5` |
| `O/systematic-debugging/SKILL.md:14-18` | build and confirm the reproduction | diagnosis |
| `O/systematic-debugging/SKILL.md:19-23` | hypotheses, discriminating probe, localization | diagnosis |
| `O/systematic-debugging/SKILL.md:24-26` | fix only a confirmed cause; state the verification limit | playbook gate: the fix step runs only on a confirmed cause; principle `fix-root-causes` |
| `O/systematic-debugging/SKILL.md:26-28` | owning layer, callers, no cleanup | fix step; already `AGENTS.md:36-37` |
| `O/systematic-debugging/SKILL.md:29-31` | regression check red then green; rerun | fix step, calling `test-driven-development` |
| `O/systematic-debugging/SKILL.md:33-36` | flakes; no reproduction: safe analysis, ask for evidence, qualify a proposed fix | diagnosis (provisional status): safe analysis, the missing evidence requested, any proposed fix labelled unproven; no production edit |
| `O/systematic-debugging/SKILL.md:38-40` | performance goes elsewhere | router line |
| `O/systematic-debugging/SKILL.md:44-45` | attempt log; stop after two failed fixes | playbook gate around fix attempts |
| `O/systematic-debugging/SKILL.md:45-47` | out of hypotheses: critic review | diagnosis escalation, calling `review` |
| `O/systematic-debugging/SKILL.md:49-51` | logs are untrusted; secrets out | principle, already `AGENTS.md:22-23`, `:59` |
| `O/systematic-debugging/SKILL.md:53-54` | remove instrumentation; preserve reproducers; record cause, proof and limits | playbook closeout, on every exit |
| `O/systematic-debugging/SKILL.md:55-56` | hardening only when the defect reveals another boundary problem; else follow-up | conditional post-fix branch, fence kept |
| `O/systematic-debugging/references/localization.md:6-52` | layer tree, comparison, boundary instrumentation, backward trace to the origin | diagnosis |
| `O/systematic-debugging/references/localization.md:53` | "Fix at that origin" | fix step (restates `O/systematic-debugging/SKILL.md:26-28`) |
| `O/systematic-debugging/references/localization.md:55-101` | stack capture, commit and test-pollution bisection | diagnosis |
| `O/systematic-debugging/references/non-reproducible-bugs.md:7-35` | flake classes, raising the rate | diagnosis |
| `O/systematic-debugging/references/non-reproducible-bugs.md:37-83` | condition-based waiting for timing flakes | fix technique: needs a home (5.3) |
| `O/systematic-debugging/references/non-reproducible-bugs.md:85-93` | environmental cause: an unresolved finding, never a mitigation as the fix | diagnosis status "unresolved"; the mitigation rule is a playbook gate |
| `O/systematic-debugging/references/post-fix-hardening.md:3-46` | defense in depth, bypass-tested, scoped to the bug class | conditional post-fix branch |

### 5.2 After the split

**Principles.** Fix at the owning cause; logs are untrusted; label what
is unproven; change approach on no new evidence. Four already live in
`AGENTS.md` (`AGENTS.md:36-37`, `AGENTS.md:22-23`, `AGENTS.md:15-16`,
`AGENTS.md:41`). Only "a change that merely hides the symptom is not a fix"
(`O/systematic-debugging/SKILL.md:26`) is not there; pstack's
`fix-root-causes` holds it (`P/skills/principle-fix-root-causes/SKILL.md:17`).

**The diagnosis skill.** Reproduce, localize, raise a flake's rate, bisect,
escalate to a critic when hypotheses run out
(`O/systematic-debugging/SKILL.md:14-23`, `:33-36`, `:45-47`; the
diagnosis sections of the references; `scripts/find-polluter.sh`). It
changes no production code. One deliverable, an answer, with a status and
its limits:

- **confirmed**: the cause, shown by the reproduction or, without one, by
  independent evidence such as traces (`O/systematic-debugging/SKILL.md:24-26`);
- **provisional**: neither a reproduction nor independent confirmation.
  It carries safe source analysis, the missing evidence named and
  requested, and any proposed fix labelled unproven (`:34-36`). It licenses
  no production edit;
- **unresolved**: an environmental cause, claimable only after every
  hypothesis is falsified, with the investigation attached
  (`O/systematic-debugging/references/non-reproducible-bugs.md:85-93`).

Called on its own, it removes the temporary instrumentation it added and
keeps reproducers before answering (`O/systematic-debugging/SKILL.md:53-54`).
Called from the playbook, it lists what it left in place for step 7.

**The playbook: bug fix.**

1. Skip to step 3 when the cause is obvious: the existing failing command
   confirms it (`O/systematic-debugging/SKILL.md:8-10`).
2. Diagnose: call the diagnosis skill. Only a **confirmed** cause goes on
   to step 3 (`O/systematic-debugging/SKILL.md:24-26`). On **provisional**
   or **unresolved**, change no production code and go to step 7. A
   provisional reply carries the analysis, the evidence requested and any
   proposed fix labelled unproven (`:34-36`). An unresolved reply carries
   the finding; a mitigation ships only on the user's decision, never as
   the fix (`O/systematic-debugging/references/non-reproducible-bugs.md:91-92`).
3. Fix with proof, on the confirmed cause only: call
   `test-driven-development` in test-first mode, so the red check runs
   before the fix (`O/test-driven-development/SKILL.md:30-31`), then the
   owning fix (`:32`). The fix is at the owning layer, with callers checked
   and no cleanup (`O/systematic-debugging/SKILL.md:26-28`). For a timing
   flake, the fix uses condition-based waiting
   (`O/systematic-debugging/references/non-reproducible-bugs.md:37-83`).
   Where no regression check is feasible, fix the confirmed cause and report
   the missing proof (`O/test-driven-development/SKILL.md:35-37`).
4. Rerun the original scenario and the repository checks
   (`O/systematic-debugging/SKILL.md:30-31`).
5. Gate around steps 3 and 4: record each attempt; after two failed fixes,
   stop, go to step 7 and bring the log (`:44-45`).
6. Only when the confirmed defect reveals another boundary problem: harden,
   bypass-test each layer, scoped to the bug class
   (`O/systematic-debugging/references/post-fix-hardening.md:33-46`).
   Record out-of-scope hardening as follow-up
   (`O/systematic-debugging/SKILL.md:55-56`).
7. Close out on every exit, fixed or not: remove the temporary
   instrumentation added, keep reproducers and user artifacts, and record
   the cause or the status reached, the proving check if there is one, and
   the remaining limits (`:53-54`).

Reply: the status, the cause or finding, the proving check or the missing
evidence, the limits and follow-ups.

Every row of §5.1 lands in a principle, a router line, the diagnosis
skill or a playbook step. The playbook holds the confirmed-cause gate
(steps 2 and 3), the provisional and unresolved exits (step 2), the red
check before the fix (step 3), the recovery gates (step 5), the hardening
fence (step 6) and cleanup on every exit (step 7). By H9 the playbook is
clean: it calls diagnosis and test-first whole.

### 5.3 Is the split clean?

**Not quite.** Three cuts need an owner decision:

1. Two references must be cut by section:
   `O/systematic-debugging/references/localization.md:53` and
   `O/systematic-debugging/references/non-reproducible-bugs.md:37-83` are
   fix material inside diagnosis files.
2. The timing-flake fix pattern is technique, but its step is the
   playbook's fix. It needs a home: a reference of the playbook, of
   `test-driven-development`, or a small skill of its own.
3. Hardening is technique gated by the playbook. It can stay a reference
   loaded by step 6, or become a defense-in-depth skill called
   conditionally.

**Against pstack's Bug fix (J).** Our steps 2 and 4 match pstack steps 1,
2 and 4 (`PB/bug-fix.md:7-8`, `:10`). Our step 3 matches part of pstack
step 5: red then green, without the commit order (`:11`). pstack has three
actions this one does not: design first when the fix crosses a function
boundary (`:9`), commit the repro before the fix (`:11`), and open a PR
(`:13`). Ours has the two-failure stop, the status outcomes and the
closeout.

**Against Pocock (J).** Pocock's `diagnosing-bugs` is broader than the
diagnosis skill: its Phase 5 writes the regression test and applies the
fix, and Phase 6 verifies and cleans up
(`MP/engineering/diagnosing-bugs/SKILL.md:114-138`). It is one skill for
diagnosis and fix together, closer to today's `systematic-debugging`. It
does not support a diagnosis-only boundary.

**Found on the way.** The references speak a six-phase procedure the
SKILL.md no longer has: "Phase 3", "Phase 4", "Phase 6" and "the Phase 1
loop" (`O/systematic-debugging/references/localization.md:4`, `:37`, `:42`;
`O/systematic-debugging/references/non-reproducible-bugs.md:5`, `:35`,
`:87`). SKILL.md has five numbered steps (`O/systematic-debugging/SKILL.md:14-31`).
The phase numbers match Pocock's `diagnosing-bugs` Phases 1 to 6
(`MP/engineering/diagnosing-bugs/SKILL.md:18`, `:130`). Inferred: the
references came from that source and were not renumbered.

## 6. Open questions for the owner

1. **Which boundary for playbooks?** Three options, with trade-offs:
   - *Declared:* a playbook is whatever `mvp-mode` lists, with no
     frontmatter. Exact and checkable; says nothing about content, so
     anything can be filed either way.
   - *Content with named exceptions:* for example ordered steps plus a
     reply contract, which fits 20 of 23 pstack playbooks and 2 of 33
     skills. Guides authors, but needs a list of exceptions and judgement
     at the edges.
   - *Both:* declare it, and lint content as a warning.
2. **Read-only playbooks.** pstack has nine that do not ship code. Do
   diagnosis-only and planning-only procedures count as playbooks for us,
   or stay skills?
3. **Principles and `AGENTS.md`.** Five pstack principles are already
   always-loaded policy lines. Keep them only in `AGENTS.md`, or also as
   principle files loaded when the situation fits? Skill text repeats
   `AGENTS.md` today (`O/systematic-debugging/SKILL.md:26-28`).
4. **Subtypes.** Keep three top-level roles and record alias, tool wrapper,
   setup, style pass, reference pack, retired entrypoint and composite as
   overlapping subtypes, or give some a router section of their own?
5. **The debugging split (§5.3).** Where does the timing-flake fix pattern
   live, and is hardening a reference or a skill? `performance-optimization`
   is the next candidate (`PB/perf-issue.md`).
6. **Commit-ordering steps.** `red-commit-first` and `wip-commit` need
   commits. Do they enter as steps gated on commit authority
   (`AGENTS.md:64`), or not at all?
7. **Vocabulary.** Under the registry's rules, the four pilot playbooks
   need 31 new trait definitions, and 20 of 71 actions are calls; 20
   match existing definitions, and 3 of 22 steps are fully covered. Eight
   of the 31 are weaker or narrower forms of general traits rather than
   playbook-specific (`delegate-implementation`, `delegated-exploration`,
   `rerun-original-repro`, `reconstruct-operational-state`,
   `force-reproduction`, `confirm-cause-before-design`,
   `plan-refusal-threshold`, `give-options`). Should calls live in a step
   registry, and playbook-specific formatting rules stay in the playbook
   rather than the trait vocabulary?
8. **Adopt H9?** As a lint over direct calls, exempting section
   references and callee-side carve-outs, it fires on 2 pstack playbook
   calls and none of ours, with 7 pstack calls ambiguous. Rulings first:
   is `architect`'s Phase D core when the caller implements (4 playbook
   calls, and `figure-it-out`); is a Diátaxis "document" a file
   (Multi-phase plan); may a caller fold a callee's output contract into its
   own reply shape (Investigation → `how` and `why`); and does the rule
   cover playbook-to-playbook calls (4 more) and skill-to-skill calls (9
   more)?
9. **Stale references.** Fix the phase numbers in `systematic-debugging`'s
   references now, or with the split?
