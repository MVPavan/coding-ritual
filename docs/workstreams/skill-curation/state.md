# Skill curation: handoff

Updated 2026-11-01 (MVP stack phase 1 closed; phase 2 running on the playbook
map). Branch `mvp-stack` in the main worktree; `dws-workflow` is retired and
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

`main` and `mvp-stack` are pushed. `main` is at `eb36cc9`; later work is on
`mvp-stack` until the owner asks to merge.

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
  has not run a real session; `cr-r2pa.2.12` holds that run and its checklist.
- `cr-r2pa.2.1`, next: seven Pocock retargets, ruled as recommended on 2026-11-01, with
  the redaction pair staying on `systematic-debugging`. Their events are still to record.
- Then batch 1 (`.4`), batch 2 (`.5`), pilots 2 and 3 (`.8`, `.9`), batches 3 and 4 (`.6`,
  `.7`), the remaining Pocock pass (`.10`).

The Pocock pending adoptions are tracked in `cr-axdt.6` (13 tasks, one per target
skill) and join the batch that touches the same skill; each completes its adopts
with `record --supersedes`.

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
