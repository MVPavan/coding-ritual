# Skill curation: handoff

Updated 2026-11-02 (MVP stack phase 1 closed; phase 2 running on the playbook
map, batch 2 and pilots 2 and 3 done). Branch `mvp-stack` in the main worktree; `dws-workflow` is retired and
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

`main` is at `eb36cc9`; later work is on `mvp-stack` until the owner asks to merge.
`mvp-stack` is pushed through the first routing trials' runner change; commits after it
are local until the owner says to push.

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
- `cr-r2pa.2.15`, in flight: routing trials ran 77 Claude sessions and 39 Sol sessions
  (2026-11-03), so routing now has real evidence. No wording has changed: a judge check and
  Claude at high effort come first, because model, effort and judges are not yet separated.
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
  are dropped, and unattended climbs wait on batch 4 (`cr-r2pa.2.7`). None of it has run on
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
- Then batches 3 and 4 (`.6`, `.7`), the remaining Pocock
  pass (`.10`).
- `cr-r2pa.2.13`: analyse every skill of ours, Pocock and pstack; its scope is still to
  agree with the owner.
- `cr-r2pa.3.3`: at the end of the project, show the owner everything deferred or
  rejected, from the ledger's `defer` events, the deferred beads and each
  `deliberately_dropped` with its `revisit_when`, to revise and adapt.

The Pocock pending adoptions are tracked in `cr-axdt.6` (13 tasks, one per target
skill) and join the batch that touches the same skill; each completes its adopts
with `record --supersedes`.

## Uncommitted work (as of this handoff)

| Path | State |
|---|---|
| `harness_lifecycle/registry/reviews/2026-10-22-upstream-mattpocock_skills-1.3.1-47.md` | superseded idea-level draft; delete or archive at the owner's word || `.beads/issues.jsonl`, `.claude/agents/*`, `tools/T3/*` | not this workstream; leave alone |

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
