# Skill curation: handoff

Updated 2026-11-11 (MVP stack phase 1 closed; phase 2 running on the playbook
map; the renames-and-splits batch closed by U9, the tracker batch by T1c, the discovery batch by D6). Branch `mvp-stack` in the main worktree; `dws-workflow` is retired and
deleted. Beads is the work-state authority; this file is the narrative.

## Start here (new session)

1. Read `harness_lifecycle/playbook.md` (the method), then
   `harness_lifecycle/registry/README.md` (records, ledger, tool).
2. `git status` and `git log --oneline -6`; compare with "Uncommitted work"
   below.
3. `UV_CACHE_DIR=/tmp/uv-cache uv run python harness_lifecycle/registry/registry.py check`
   must print `ok`.
4. Resume at "In flight".

## Working rules for this workstream

- **Roles.** Delegate through the `delegation` skill: the implementer writes
  all code and the reviewer or critic reviews read-only, with models from the
  owner's roster (`.delegation/roster.toml`). One task at a time. A task that
  hits a rate limit is resumed by its vendor: never relaunch it.
- **Git.** Stage explicit paths only; commit with `git -c core.hooksPath=/dev/null`;
  push only when the owner says "push". Never commit `.beads/issues.jsonl`
  with other sessions' beads, `tools/T3/` (another workstream), or a
  submodule pointer without its upstream review.
- **Public repo.** No machine-local absolute paths or private data in
  committed files.
- **Owner preferences.** Lead with the outcome, short lists, one next action;
  inline text choices, no pop-up questions; reports stay as local files.
- **Prompting guidance.** `harness_lifecycle/prompting-guides/GUIDE.md` changes
  only for new frontier-lab guidance or a well-known prompting-experiment
  article. Writing ideas from reference harnesses go into
  `.claude/skills/authoring-for-agents/references/writing-principles.md`.

## Done

| Commit | What |
|---|---|
| `19f3f5a` | Registry replaces `gap.py`, `ledger.json`, inventory CSVs and the casebook. 36 skill records, sealed migration round (243 events), generated `references/` and `INDEX.md`. Epic `cr-skwm` closed |
| `fc7feb3` | Six owner rulings on broken migration adoptions (round `2026-10-14-owner-review`); `registry/reviews/` folder; skill and harness comparisons archived; `harness-skill-compare` writes a skill review; `round open` date fix (`cr-alnr`) |
| `52bf9fc` | `harness_lifecycle/playbook.md`; seven placement fixes; ADLC sub-stage Orchestration renamed Coordination |
| `c65e0ef` | Traits replace ideas and Covers (`cr-axdt.5`, design `traits-design.md`): `trait-definitions.yaml`, generated `TRAITS.md`; Pocock catalog at `5beb35b` |
| `2a38fbe` | Stages build (`cr-w92w`, design `stages-design.md`): `curation/` package, `skills.yaml`, `traits/` with accepted and proposed analyses, `status`, reports, `trait-sharing.yaml` (16 shared traits kept with a why), empty `trait-policy.yaml`. `delegation` skill replaces agent-matrix and use-codex (`cr-sduw`, round `2026-10-30-delegation`) |
| after `222e3d6` | Pocock redo (`cr-axdt.4`): sealed report `reviews/2026-10-30-upstream-mattpocock_skills-5beb35b.yaml` (27 skills, 559 rows, Sol passed analysis and comparison), round `2026-10-30-mattpocock_skills-5beb35b` (591 events), analyses promoted to `5beb35b`, submodule pointer. Owner deferred every reject recommendation (207) to review as a set: `reviews/…-5beb35b-deferred-rejects.md` |

| `a83d5f9`, `876cfa1` | Unit-kinds rules and the boundary study; pstack v0.15.36 report and submodule pointer |
| `c25ed12`, `eb36cc9`, `382962d` | MVP stack phase 1 (`cr-r2pa.1`): `mvp-mode` router, bug-fix pilot, playbook registry, 14 principles, `build-a-lever`, the delegation default, the playbook map (all rulings as recommended), a playbook as its own ledger subject. Comparison: `mvp-stack-changes.md` |
| `f207be9` | pstack's 23 playbooks cataloged as units and ruled whole (`cr-r2pa.2.2`, round `2026-11-01-pstack-playbooks`) |
| `7449497` | Batch 0: Trace forensics, Worktree cleanup and Eval live (`cr-r2pa.2.3`, round `2026-11-01-batch-0`) |
| `862689d` | Seven Pocock retargets (`cr-r2pa.2.1`, round `2026-11-01-pocock-retarget`) |
| after `862689d` | Batch 1 (`cr-r2pa.2.4`, round `2026-11-01-batch-1`), see below |
| after `ba56f66` | Batch 2 (`cr-r2pa.2.5`, round `2026-11-02-batch-2`), see below |
| after `d079219` | Pilot 2 (`cr-r2pa.2.8`, round `2026-11-02-pilot-2`), see below |
| after `2bc70a2` | Pilot 3 (`cr-r2pa.2.9`, round `2026-11-02-pilot-3`), see below |
| `8b9f890` | Batch 3 (`cr-r2pa.2.6`, round `2026-11-03-batch-3`), see below |
| `fe75e0d` | Catalog diff and `gap` report bundled-file changes (`cr-r2pa.2.11`) |
| `9a07dc0` | Batch 4 (`cr-r2pa.2.7`, round `2026-11-04-batch-4`), see below |
| `2fbc414` | Pocock pass (`cr-r2pa.2.10`, round `2026-11-04-pocock-pass`), see below |
| `b9a4d57` | `gap` and `record` read a sparse reference whole (`cr-r2pa.2.17`) |
| `815df70` | The ledger reads in recording order, not filename order (`cr-an42`) |
| `cee1ab3` | Principles stop being skills: the 14 move to `mvp-mode/principles/` (owner ruling 2026-11-05, round `2026-11-05-principle-move`) |
| `5a58e2e` | Two principle edits from the prompting-guide review (round `2026-11-05-principle-edits`) |
| `9fe4027` | `delegation`'s brief names the principles that apply (round `2026-11-05-delegation-principles`) |
| `cd76d3f` | Batch P1 ruled and recorded (`cr-r2pa.2.13`, round `2026-11-06-batch-p1`), with the principle-file fixes to `loaders.py`, see below |
| `97f597e` | A skill's record keeps its history after a rename; `add` refuses a retired name |
| `6763f83` to `12df2d8` | Renames to `tdd`, `unslop`, `brief-me`, `implement` (round `2026-11-06-renames`) |
| `8870acb` | Reference pages name the renamed skill |
| `4c9ba8c` | Fourteen read-only references added for later study (`tstack`, `dori-superagent`, `reference_harnesses/kun/`), epic `cr-56rw` |
| after `4c9ba8c` | Both pins moved and the Pocock update ruled and recorded (`cr-r2pa.2.13`, round `2026-11-09-pocock-4ae2317`), see below |
| after `e8feec8` | Renames and splits, unit U2: three reports ruled and recorded as pending (`cr-r2pa.2.20`, round `2026-11-10-renames-splits`, open), see below |
| after `b4740e4` | U3: `to-spec` split out of `brainstorming` (same round), see below |
| after `3ab290f` | U4: `to-tickets` split out of `planning` (same round), see below |
| after `e43371b` | U5: the spec branch of `implement` (same round), see below |
| after `560788a` | U6: `how` and `why` out of `explain-code` (same round), see below |
| after `161be48` | U7: two principles restored (same round), see below |
| after `fb84021` | U8: `suspect-the-observation` moved to `AGENTS.md` (same round), see below |
| `0eafcea` | U8r: `planning` → `to-plan`, `to-tickets` → `to-roadmap`, ordering rules into one principle (same round), see below |
| after `0eafcea` | U9: closeout; round `2026-11-10-renames-splits` sealed, owner's relocation list, sync list for the end-of-project sync, see below |
| `4647b3a`, `1fc0992` | T1a: `tracker` split out of `beads`; T1b: unit beads in every scope (`cr-r2pa.2.22`, round `2026-11-11-tracker`), see below |
| after `1fc0992` | T1c: closeout; round `2026-11-11-tracker` sealed, owner's relocation list, sync list extended, see below |
| `5d92415`, `5255bb0`, `43d6601`, `3e9eb94`, `d636079`, `236340b`, `fe1228c` | D0-D5: `discovery` replaces `brainstorming` and `idea-refine`; `research` narrowed to evidence (`cr-r2pa.2.21`, round `2026-11-11-discovery`), see below |
| after `fe1228c` | D6: closeout; round `2026-11-11-discovery` sealed, owner's relocation list, sync list extended, see below |

`main` is at `eb36cc9`; later work is on `mvp-stack` until the owner asks to merge.
`mvp-stack` is pushed through U8 of the renames (`43d0d07`); later commits are local until the owner says to push.

Decisions behind them: domains `core` and `engineering`; one primary
coordinate per skill (domain · stage · sub-stage); reviews are flat files
`reviews/<date>-<upstream|skill>-<slug>.md`, linked into records by `build`;
frozen material goes to `harness_lifecycle/archive/`.

## In flight: MVP stack phase 2 (`cr-r2pa.2`)

Runs on `playbook-map.md`: §5 is the order, §7.2 the seventeen rulings, all ruled
as recommended on 2026-11-01. Each batch follows the approved cycle: report, Sol
critic, owner rulings, ledger, build, Sol review, commit after the owner approves.

- `cr-r2pa.2.2`, done (`f207be9`): pstack's 23 playbooks cataloged as units and ruled
  whole (round `2026-11-01-pstack-playbooks`). A `defer` on an adapted playbook means
  not built yet: the `adopt-merged` that delivers it supersedes the `defer`.
- `cr-r2pa.2.3`, done: batch 0's Trace forensics, Worktree cleanup and Eval are live
  (round `2026-11-01-batch-0`). Owner rulings: a candidate's only network is a proxy to
  the Anthropic API, and `bypassPermissions` needs naming in that Eval's go-ahead. Eval
  has since run real sessions on three Claude models (`cr-r2pa.2.12`, 2026-11-02), and
  `eval/run.sh` takes `--effort` and `--max-budget`.
- `cr-r2pa.2.15`, done: routing trials ran 102 Claude sessions and 39 Sol sessions (2026-11-03);
  results and parked changes are in `routing-trials-report.md`. Owner ruling: no existing wording
  changes until the end-of-project revision pass (`cr-r2pa.3.4`). New units follow the report's
  section 6 until then.
- `cr-r2pa.2.6`, done (`8b9f890`): batch 3 (round `2026-11-03-batch-3`, pstack `arena` and `interrogate`). New
  skill `interrogate`, where adversaries attack verified copies and only a finding a run proves
  survives. `model-council` gains a pick-and-graft branch and runs only on an explicit request.
  Feature's steps 2 and 6 are final: it starts `interrogate` unasked only on a real dispute, and
  with two shapes and no council asked for it compares them and carries on. `review` gets the seven
  Pocock rows (`cr-axdt.6.8`). S7 is amended by owner ruling, with a dated row. No real session has
  run any of it.
- `cr-r2pa.2.7`, done (`9a07dc0`): batch 4 (round `2026-11-04-batch-4`). The owner ruled all six questions as
  recommended on 2026-11-04, amending ruling 12: waiting on a command needs no `wake`. New skill
  `wake`: a card holding a run's limits, attempts, closed state and checkpoint, plus one closing
  timer at the deadline, set only for a stated unattended run. New playbook Autonomous run, by a
  fifth named composite-test exception. Hillclimb gains an unattended path, in
  `hillclimb/unattended.md`: isolated, local, nothing committed, the work left aside as a patch and
  a folder. Bug fix gains a long-hunt test and answers Not started to unattended words for now.
  Coordinator's choice, not a ruling: an attended run naming only attempts takes 4 hours. Hours and
  attempts limit starting work, not running work or money. Status `PARTIAL`: no real session has run
  any of it, so timer delivery, what it survives, whether a model follows the steps, whether
  Autonomous run gets picked and what a night costs are all unproved.
- `cr-r2pa.2.1`, done: seven Pocock retargets recorded (round
  `2026-11-01-pocock-retarget`). `reproduction-first`, `regression-check` and `closeout`
  are delivered; `prove-the-red` and `missing-seam-finding` are pending for batch 1; the
  redaction pair stays pending on `systematic-debugging`.
- `cr-r2pa.2.4`, done: batch 1 (round `2026-11-01-batch-1`). `land`, `explain-code`,
  `prose-pass` and `codebase-design`'s sketch branch are built; Investigation, Feature and
  Refactoring are live, and Bug fix has its narrower bindings except the long-hunt branch.
  The owner ruled its 189 upstream rows as recommended, as one set. None of it has run on a
  real session: trials wait on `cr-r2pa.2.12`, and so does the S8 F3 rerun. `cr-an42` holds
  the ledger's same-date ordering flaw.
- `cr-r2pa.2.5`, done: batch 2 (round `2026-11-02-batch-2`). `performance-optimization` gains the cost
  order, a vetting reference and a diagnosis-only branch; `decision-trail` is new; Perf
  issue, Runtime forensics and attended Hillclimb, with `hillclimb/attempt.py`, are live.
  The owner ruled its upstream rows as recommended, as one set, keeping
  `script-evidence-preference`. Hillclimb's loop commits nothing and lands once at the
  end; S2 now lets a calling playbook opt into a branch's deliverable. Parallel attempts
  are dropped; batch 4 (`cr-r2pa.2.7`) added unattended climbs. None of it has run on
  a real session: whether a model picks Perf issue over the skill, whether a span holds
  across a compaction, whether a critic per trail pays, whether a live capture works on a
  stuck process and whether a delegate keeps to one factor all wait on `cr-r2pa.2.12`.
- `cr-r2pa.2.8`, done: pilot 2 (round `2026-11-02-pilot-2`). `prototype` gains one switcher for every variant, a recommendation with
  tradeoffs and a conditional route back to Feature, and stays a skill. `planning` gains a
  Skeleton branch with evidence boxes per unit and `scripts/check_plan.py`. Multi-phase plan
  is live and calls `delegation`, `prototype`, `planning` and `prose-pass`, with no `land`:
  the plan stays uncommitted. None of it has run on a real session: whether a model picks
  the playbook over `planning` or Feature, whether a span holds across a compaction,
  whether `execution` runs tick boxes and whether workers misread task text all wait on
  `cr-r2pa.2.12`.
- `cr-r2pa.2.9`, done: pilot 3 (round `2026-11-02-pilot-3`).
  Session pickup and Pause safely are written with router lines and ledger events. `session-trail` is no skill:
  reading and writing are the two playbooks' own actions, and `beads`, `execution`, `decision-trail` and `land` do not
  change. A note lives on the bead or in a checkpoint file keyed by the work's identity, and ruling 15 holds: no `wip:`
  commit without the owner's own words. Two E4 proposals go to the owner at the commit request. None of it has run on a
  real session: whether a model picks either playbook, opens artifacts before a skip, keeps open calls whole on a
  resumed run or cleans up its file all wait on `cr-r2pa.2.12`.
- `cr-r2pa.2.10`, done (`2fbc414`): the Pocock pass (round `2026-11-04-pocock-pass`). 37 of the 38 pending
  adoptions are delivered into eight skills in their sealed wording, and `delegation` gains ruling
  17's three supervision rules. `triage`'s new close also goes in the Beads table. Owner rulings of
  2026-11-04: `human-facing-description` is deferred to `cr-r2pa.3.4`, which rules on a carve-out
  from S5 for manual skills; `grilling` keeps its frozen sentence and adds that a question after a
  fact stays an ordinary question; the two sharing reasons are accepted. 13 traits follow their
  rewording under T5, logged in `unit-kinds.md`. No description or invocation flag changed. Status
  `PARTIAL`: no real session has run any of it.
- `cr-r2pa.2.17`, done (`b9a4d57`): `gap` and `record`'s source autofill read a sparse reference from a full
  export of its HEAD, as `scan.py catalog` does. `gap cursor_plugins` now sees all 352 capabilities,
  and its not-reviewed list went from 30 to 281: the real gap, for `cr-r2pa.2.13` to scope.
- `cr-an42`, done (`815df70`): `round_order` in `MANIFEST.json` lists the sealed rounds in recording order and
  every reader follows it, so a round's slug no longer decides which ruling wins. `record`, `build`
  and `round seal` refuse a bad list. Merging two branches that each seal a round needs a person to
  choose the order: `check` cannot always tell which is right.
- `cr-r2pa.2.13`: analyse every skill of ours, Pocock and pstack, scope agreed: full trait-level
  analysis of pstack's unanalysed and Pocock's whole-ruled skills in small batches; a recorded reason
  for our thin shortcuts. Batch P1 (eleven pstack skills, 274 rows) is ruled and recorded (round
  `2026-11-06-batch-p1`): the owner accepted it as recommended on 2026-11-06 and made `recall` a new
  skill. 153 adopts are pending on `cr-r2pa.2.18`, which builds them; rows into a new unit carry no
  frozen wording, so each new body's critic maps every row to `file:line`. `principle-no-comments`
  waits for the keep-list in pstack's `agents/comment-sicko.md`. Nothing of P1 is built yet.
  The Pocock update `5beb35b` to `4ae2317` (170 rows: 21 pending adopts, 6 already held, 98 defers,
  45 rejects) is ruled as recommended on 2026-11-09 and recorded (round `2026-11-09-pocock-4ae2317`).
  `cursor_plugins` moved to `2776ddd` with no report: only `third_party/` changed. The 21 are pending
  on `cr-r2pa.2.19`; `software-factory` stays on the owner's hold, and its whole-system comparison
  with `firstmate` and `dori-superagent` is `cr-56rw.15`. The report's critic fields are `accepted`:
  Sol's last round (`critic-15d`) asked for two fixes, which the coordinator made and read.
- Principles against the prompting guides: proposal in
  `scratchpad/mvp-stack/12b/principles-vs-guides.md` (gitignored), critic `critic-12c.md`. Ruled:
  keep 7, small edit 2 (done), keep until tested 5, cut none. A search of past sessions
  (`13/transcript-findings.md`) found principles rarely read even where they applied, so `delegation`
  now names them in briefs; check that on real runs. Editing a principle stales both its own hash and
  `mvp-mode`'s, because `mvp-mode`'s folder hash covers `principles/`.
- Owner rulings of 2026-11-05 on merges, splits, renames and new units:
  `scratchpad/mvp-stack/13/owner-rulings-2026-11-05.md`; P1's ruling is section G there. The renames,
  splits, two restored principles and the move of `suspect-the-observation` are their own batch,
  `cr-r2pa.2.20`, on plan `scratchpad/mvp-stack/14a/plan.md` (units U0 to U9). U0 and U1 are done.
  U2 is recorded (round `2026-11-10-renames-splits`, sealed in U9): three
  sealed reports, one per analysis sha, because a report holds one `to_sha` (Pocock `4ae2317` for
  `implement-spec`, Pocock `5beb35b` for `to-spec` and `to-tickets`, pstack `4dd1d05` for `how`,
  `why`, `fix-root-causes` and `prove-it-works`). Sol passed them (`critic-16b`). 63 rows: 36 pending
  adopts on `cr-r2pa.2.20`, 22 defers, 5 rejects, and four new checkpoints (`to-spec`, `to-tickets`,
  `implement`, `how`). The owner ruled the 28 `why` source rows as recommended on 2026-11-10: adopt
  `pr-discussion-pull`, keep 22 deferred, reject 5. Event sources sit at each report's `to_sha`;
  relocations keep the prior adopt's `into`. U3 is built: `to-spec` writes and approves specs with
  the moved template, and `brainstorming` ends at decisions (Sol `critic-17b`, `critic-17d`). U2 had
  wrongly moved `to-spec#ground-in-codebase`, whose `scoped-context-read` stays delivered in
  `brainstorming`; a one-row report (`reviews/2026-11-10-upstream-mattpocock_skills-5beb35b.yaml`)
  records it there and `to-spec` withdraws it. U4 is built: `to-tickets` splits an approved spec into
  tracked phases and stages; `planning` keeps plan documents, its approval gate before Beads writes
  and its own slicing rules for a plan's tasks, so `vertical-slices`, `prefactor-first`,
  `expand-contract` and `blast-radius-batches` are shared by both (Sol `critic-18b`, `critic-18d`).
  `reviewer-rejectable-sizing` stays in `planning` (its text is in `plan-format.md`), and
  `dependency-edges` gains `implement` in U5. U5 is built: `implement` runs a whole spec whose
  tickets are one epic with edges (`references/spec-run.md`) in one worktree on one integration branch,
  one ticket at a time; the base check stops with the work intact; commits, merges, resets and
  worktree removal each need authority; a run record makes a stopped run resumable (Sol `critic-19d`,
  `critic-19f`). Its pre-report merge brings the base's tip into the integration branch, a different
  mechanism from upstream's `pre-report-tip-merge`, so a one-row report
  (`reviews/2026-11-10-upstream-mattpocock_skills-4ae2317.yaml`) adopts it into the new trait
  `pre-report-base-merge`. U6 is built: `explain-code` is renamed `why` (the history method,
  answering why something in the project is the way it is or what was decided about it, from
  the project's own record) and `how` is new (how something works now, and which option fits);
  `why` loads `references/pull-requests.md` only when a traced commit links a pull request
  (ruling K). Six playbooks and the router re-pointed (Sol `critic-21b`, `critic-21c`). U7 is
  built: `principle-fix-root-causes` holds the three rules moved out of `systematic-debugging`,
  which now points to it (ruling I2); `principle-exhaust-the-design-space` covers decisions with
  no precedent of any kind, with the new trait `novel-decision-design-space`, and leaves runnable
  variants to `prototype` (Sol `critic-22b`). U8 is built: the suspect-the-observation rule is
  one sentence in `AGENTS.md` §Verification, no longer in `systematic-debugging`; the round has no
  pending row left (Sol `critic-23b`). U8r is built (owner rulings M and N): `planning` is renamed
  `to-plan` and `to-tickets` `to-roadmap`; their four shared ordering rules live once in
  `principle-sequence-verifiable-units` (report `reviews/2026-11-11-upstream-mattpocock_skills-5beb35b-r1.yaml`),
  and `to-plan`'s routing table keeps only its own cases (Sol `critic-24b`, `critic-24d`, `critic-25b`).
  U9 closed the batch: the round is sealed; the owner's relocation list (ruling I4,
  `scratchpad/mvp-stack/14/relocations.md`, from `26/relocations.py`) shows 29 adopted rules that
  moved home, 6 newly adopted, 78 that only followed a rename, 7 renames, 3 splits and 5 new units,
  with the coordinator's corrections. The Codex links, `catalogs/ours.json`, the publish manifest's
  `expect`, the plugin's `AGENTS.md` sentence and the rewording caveat for `cr-r2pa.2.18` wait for
  the end-of-project sync, listed on `cr-r2pa`.
  T1 (`cr-r2pa.2.22`, owner ruling N, plan `scratchpad/mvp-stack/27/plan.md`) is done. T1a
  (`4647b3a`): `tracker` holds our work structure on Beads (workstreams, phase epics, seeding and
  extending, one-phase plans with proposed stage names bound to real IDs after approval, plan
  records, approved decision maps, flat work, phase-epic lookup, close gate, rendering); `beads`
  keeps the tool; `to-roadmap` takes only multi-phase specs; `wayfinder` and `triage` create
  through `tracker`. Create recipes capture IDs with `--silent`; the renderer keeps one-phase epics
  on the board, and a title opening with `[` is reserved for phase epics (Sol `critic-27b`, `27d`,
  `28b`, `28d`, `28e`). T1b (`1fc0992`): when an approved plan's units will span sessions, `tracker`
  gives each a child task in every scope; `implement` drains a bead's open children before
  claiming it, and in the Phase loop the coordinator, not the contractor, runs a stage with unit
  beads (Sol `critic-29b`, `29c`). T1c sealed round `2026-11-11-tracker` (events `:001`-`:023`, no
  pending row); the owner's relocation list (ruling I4, `scratchpad/mvp-stack/30/relocations.md`,
  from `30/relocations.py`) shows 5 adopted rules moved to `tracker` (four from `to-roadmap`, one
  from `wayfinder`), 6 of our traits moved (from `beads`, `to-roadmap`, `implement`, `wayfinder`)
  and 7 new ones, two of them T1b's; `scratchpad/mvp-stack/26/sync-list.md` now also lists T1's
  files for the end-of-project sync. Follow-up `cr-7c6i` (pre-existing, not T1's): rendering after
  a contractor stage dirties the checkout the next contractor admits from.
  Discovery (`cr-r2pa.2.21`, owner ruling L, plan `scratchpad/mvp-stack/20/plan.md`) is done. D0
  (`5d92415`) opened round `2026-11-11-discovery` with Pocock `grilling#round-format` as a pending
  rewording adopt (`:001`, report `reviews/2026-11-11-upstream-mattpocock_skills-4ae2317-discovery.yaml`).
  D1 (`5255bb0`): `brainstorming` renamed `discovery`, `idea-refine` merged into it (clean break, its
  references moved unchanged), callers renamed. D2 (`43d6601`): every run writes a record, checked
  by `discovery/scripts/check_record.py` against `templates/record.md` (Source and Status per
  answer; only the owner makes a choice `decided`). D3 (`3e9eb94`): the body sorts each open
  question by who answers it and asks the owner last, one fixed block per question with a recommended
  answer, batching independent questions in a round; the judgment frameworks and decision sequences 1, 4, 6 moved from `research` into
  `discovery/references/frameworks.md`; `:014` completed `:001`. D4 (`d636079`): `research` gathers,
  weighs and cites evidence without deciding; sequences 2, 3, 5, the five maps and the investing,
  product and policy examples are dropped; reports and records file by one area/topic rule. D5
  (`236340b`, `fe1228c`): `to-spec`, `wayfinder` and `how` call through the new split,
  `docs/discovery/INDEX.md` is the generated records index, and the router sends a choice whose
  scope or criteria are still open to discovery (Sol `critic-32b`, `33b`, `34b`, `34d`, `34f`,
  `35b`, `35d`, `36b`, `37b`). Proof: a fresh session ran discovery on `cr-7c6i` and its record
  (`scratchpad/mvp-stack/37/discovery-e2e.md`) passed `check_record.py` with 7 rows and 0 problems
  (owner unavailable, so its owner rows stayed `proposed`; it used code and routine answerers, not
  `research`, a prototype or an answered owner round); the routing trial
  (`scratchpad/mvp-stack/38/result.md`) went 12 exact, 2 acceptable and 2 misses (one pattern) of 16
  in round 1 and 16 of 16 in round 2 after the router fix. Limits: one session decided all 16
  requests per round, one judge scored both rounds, and these were routing choices, not executed
  runs. D6 sealed the round (events `:001`-`:024`,
  no pending row); the owner's relocation list (`scratchpad/mvp-stack/39/relocations.md`, from
  `39/relocations.py`) shows 1 newly adopted rule (`round-format` on `discovery`), 3 of our traits
  moved or gained a home (`judgment-frameworks` research to discovery; `answer-before-next-round`
  and `yes-accepts-recommendation` now also on discovery), 10 new and 1 dropped
  (`research-playbooks`, definition kept), plus the dropped research mechanisms and the removed
  `/brainstorming` and `/idea-refine`; `scratchpad/mvp-stack/26/sync-list.md` now also lists the
  discovery files. Follow-ups: `cr-7c6i` (the run's record and its proposed rows are on it) and
  `cr-onr1` (four points the run found unclear in `discovery`; done 2026-11-12, see
  `mvp-stack-changes.md` §12, follow-up `cr-oiyn`; its computed source is built,
  §13, and it stays open for a check of the grading rule).
- `cr-r2pa.2.23` (P1), built (`5bae85a`, `e721c56`, `0afc9fb`): `implement` is a playbook
  (`mvp-mode/playbooks/implement.md`), `/implement` its manual alias, `/phase-execution` and
  `/run-phases` removed; round `2026-11-11-implement-playbook` sealed; routing trial 14 of 14
  (`scratchpad/mvp-stack/40/routing.md`). Unit U3, the `cr-7c6i` fix, followed in its own
  rounds after the owner's answer of 2026-11-12, with the `.claude/agents/implementer.md:3`
  wording. See `mvp-stack-changes.md` §9 and §11.
- `cr-r2pa.2.24` (P2), built (`93d313c`, `5d47d8c`, `3b725d3`): `plan` replaces
  `multi-phase-plan` by a rename, and the planning skills end at their deliverable; round
  `2026-11-11-plan-playbook` sealed; routing trial 16 of 16
  (`scratchpad/mvp-stack/45/routing.md`). See `mvp-stack-changes.md` §10.
- `cr-r2pa.3.3`: at the end of the project, show the owner everything deferred or
  rejected, from the ledger's `defer` events, the deferred beads and each
  `deliberately_dropped` with its `revisit_when`, to revise and adapt.
- `cr-k1b6`, done: `.repo-context/verification.md` is one router of checks by changed material;
  the interpreter's host gate and sandbox notes moved to `docs/usage/interpreter-gate.md`; 16
  traits listed under `doc:.repo-context/verification.md`. See `mvp-stack-changes.md` §14.

## Uncommitted work (as of this handoff)

| Path | State |
|---|---|
| `harness_lifecycle/registry/reviews/2026-10-22-upstream-mattpocock_skills-1.3.1-47.md` | superseded idea-level draft; delete or archive at the owner's word |
| `.beads/issues.jsonl`, `.claude/agents/*`, `tools/T3/*` | not this workstream; leave alone |

## Next, in order

1. MVP stack phase 2 (above), then phase 3 (`cr-r2pa.3`).
2. agent-skills 0.6.13 rulings by playbook §4: the review exists
   (`reviews/2026-10-14-upstream-agent-skills-0.6.13.md`) but no rulings; `gap
   agent-skills` shows 12 changed and 2 new (constraint-driven-development
   and `/constraints`). Its six borrow candidates feed the verdicts.
3. `cr-talb`: the overlap-audit items the 2026-10-30 sharing rulings left open
   (#1–#4, #7–#9, #15 and the stale show-me gate; see its comment).
4. Data clean-up in the migration round: 29 casebook/ledger disagreements and
   84 rulings with no content hash (re-rule them as each harness is reviewed).

## Known loose ends

- `adlc/skill-map.md` placement note 7: Pocock and pstack counterparts
  (`mp:tdd`, `ps:tdd`, `mp:improve-codebase-architecture`) keep their old
  placement until reviewed.
- `adlc/harness-map.html` coverage counts are slightly stale after the
  placement moves.
- `registry.py check` does not flag stray `references/*.md` pages that no
  catalog backs.
- `catalogs/claude-code-best-practice.json` is at `cd5af1f` while its pin is
  `e56f1bd`: the pin moved in `31d440e` with no catalog refresh. The other committed
  catalogs match a fresh scan except an `excluded` count off by one.
- Unused catalog fields `signature_hash` and `variant_hashes` (no consumer);
  candidate deferred bead.
- Beads: `cr-fxo8` (release contract into `harness-publish`), `cr-dp83` (port
  agent-skills shared references), `cr-70qs` (trigger evals).
- `cr-p43t`: at the next `/harness-publish`, update the manifest's expected
  skills (`delegation` ships, agent-matrix is gone).
- `harness_lifecycle/catalogs/ours.json` still lists agent-matrix and
  use-codex; regenerate it with `scan.py catalog`.
- `mvp-harness/plugins/codex-adapter` is still in the submodule, and the root
  `README.md` lists it; removing it is submodule work for the owner.
- Deferred rulings to revisit: `context-engineering` and
  `doubt-driven-development` (agent-skills).
- The old worktree `coding-ritual-registry` (a sibling of the repo checkout) (branch `wf/registry`,
  merged) can be removed with `git worktree remove` on the original machine.

## Gotchas

- Run Python with `UV_CACHE_DIR=/tmp/uv-cache uv run …` (pydantic is not in
  the system Python).
- A ruling's `content_hash` must come from the catalog at the reviewed pin;
  regenerate the catalog (`scan.py catalog … --out …`) before recording.
- Sealed rounds are immutable; an open round can be edited before `round seal`.
