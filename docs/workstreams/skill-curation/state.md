# Skill curation: handoff

Updated 2026-10-30 (stages build, `delegation` skill and trait-sharing rulings
committed). Branch `dws-workflow` (never merge to `main` until DWS is built). Beads is the work-state authority; this file is the narrative.

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
  hits a rate limit is resumed by its vendor: never relaunch it. Skill and
  harness doc edits are made by the orchestrating session itself, never by the
  implementer.
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

`c65e0ef` and `2a38fbe` are not pushed.

Decisions behind them: domains `core` and `engineering`; one primary
coordinate per skill (domain · stage · sub-stage); reviews are flat files
`reviews/<date>-<upstream|skill>-<slug>.md`, linked into records by `build`;
frozen material goes to `harness_lifecycle/archive/`.

## In flight: Pocock redo (`cr-axdt.4`)

Build step 8 of `stages-design.md`, the last one: the report YAML for the 25
Pocock skills at `5beb35b`; critics; owner decisions; then the owner's
question B (pending versus editing now); record, promote, seal, commit with
the `5beb35b` pointer. Start from `registry.py status mattpocock_skills` and
playbook §4.

Raw material, minus its "covered elsewhere" and overlap-owner logic: the
trait-level drafts in `scratchpad/traits-migration/rulings/` (298 events,
Sol-approved 2026-10-29) and the owner's six open questions in the bead's
notes. Older drafts, superseded by those: the idea-level review
`registry/reviews/2026-10-22-upstream-mattpocock_skills-1.3.1-47.md`
(uncommitted) and `scratchpad/traits-migration/pilot-rekeyed/`.

## Superseded: Pocock 1.2.3 → 1.3.1 draft rulings (kept for reuse)

Playbook §4, pins `84fdeff` → `49dd158`, 125 commits, 39 `gap` items.

- Review: `pocock-1.3.1-draft-review.md` (this folder).
  Author: Opus medium; critic: Sol high, two rounds. Round 1 REVISE (12
  findings, all applied); round 2 left one MAJOR (wizard verdict) and citation
  fixes, applied by hand. Sol has not re-checked those last edits.
- **Waiting on the owner's ruling.** Proposal shown to the owner:
  - **A. Take (adopt-merged, one edit bead each, `discovered-from` `cr-z1hk`):** `pr` (PR-body template:
    before/after evidence, merge danger) → `show-me` or a delivery skill;
    `retro` (environment-improvement categories; mechanical findings become
    checks) → playbook §7 and `.repo-context/learnings.md`; code-review
    standards-file discovery → `review`; diagnosing-bugs prove-the-red →
    `systematic-debugging`; wait-what multi-glossary map → `i-have-adhd`;
    tdd per-seam catches/misses note → `test-driven-development`; grilling
    "yes accepts the recommendation" → `grilling`; teach answer-position
    variation → `teach`.
  - **B. Reject:** `implement-spec`, `chief-of-staff`, `setup-matt-pocock-skills`.
  - **C. Keep the existing ruling at the new hash:** the other 27.
  - **D. `wizard`:** D1 (recommended) re-record its adoption at the new hash,
    noting the script changes are deferred; D2 record `defer` per the
    playbook table, which buries the earlier adoption.
- **After the ruling:**
  1. `registry.py round open pocock-1.3.1`, then one `registry.py record --stdin`
     per item: `source.sha` = `49dd158`, `content_hash` from
     `harness_lifecycle/catalogs/mattpocock_skills.json` (already regenerated
     at `49dd158`), `evidence` citing the review file, `supersedes` = the
     current effective event. Seal, `build`, `check`; `gap mattpocock_skills`
     should then list nothing changed or unreviewed.
  2. One bead per "take", `discovered-from` `cr-z1hk`.
  3. Commit together: review, ruling round, `MANIFEST.json`, regenerated
     records and references, catalog, submodule pointer
     `reference_harnesses/mattpocock_skills`, plus the playbook,
     `prompting-guides/README.md` edits (`running-codex.md` has since moved
     into the `delegation` skill).
- The skill edits themselves come later, in a worktree, per playbook §2.

## Uncommitted work (as of this handoff)

| Path | State |
|---|---|
| `harness_lifecycle/registry/reviews/2026-10-22-upstream-mattpocock_skills-1.3.1-47.md` | superseded idea-level draft; raw material for the redo |
| `reference_harnesses/mattpocock_skills` | pointer moved to `5beb35b`; commit with its ruling round |
| `reference_harnesses/cursor_plugins` | pointer moved to `ce649c0`; waits for its own review |
| `.beads/issues.jsonl`, `.claude/agents/*`, `tools/T3/*` | not this workstream; leave alone |

## Next, in order

1. The Pocock redo (above), then `cr-z1hk`, which waits on it.
2. agent-skills 0.6.13 rulings by playbook §4: the review exists
   (`reviews/2026-10-14-upstream-agent-skills-0.6.13.md`) but no rulings; `gap
   agent-skills` shows 12 changed and 2 new (constraint-driven-development
   and `/constraints`). Its six borrow candidates feed the verdicts.
3. Cursor (`cursor_plugins`) upstream review, then commit its pointer.
4. `cr-talb`: the overlap-audit items the 2026-10-30 sharing rulings left open
   (#1–#4, #7–#9, #15 and the stale show-me gate; see its comment).
5. Data clean-up in the migration round: 29 casebook/ledger disagreements and
   84 rulings with no content hash (re-rule them as each harness is reviewed).

## Known loose ends

- `adlc/skill-map.md` placement note 7: Pocock and pstack counterparts
  (`mp:tdd`, `ps:tdd`, `mp:improve-codebase-architecture`) keep their old
  placement until reviewed.
- `adlc/harness-map.html` coverage counts are slightly stale after the
  placement moves.
- `registry.py check` does not flag stray `references/*.md` pages that no
  catalog backs.
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
