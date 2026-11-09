# Skill curation: handoff

Updated 2026-11-04 (MVP stack phase 1 closed; phase 2 running on the playbook
map, batches 2 to 4, pilots 2 and 3 and the Pocock pass done). Branch `mvp-stack` in the main worktree; `dws-workflow` is retired and
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

`main` is at `eb36cc9`; later work is on `mvp-stack` until the owner asks to merge.
`mvp-stack` is pushed through the Pocock update; later commits are local until the owner says to push.

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
  splits, two restored principles and the move of `suspect-the-observation` are their own batch, still to do.
- `cr-r2pa.3.3`: at the end of the project, show the owner everything deferred or
  rejected, from the ledger's `defer` events, the deferred beads and each
  `deliberately_dropped` with its `revisit_when`, to revise and adapt.

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
