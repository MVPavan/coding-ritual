# Skill curation: handoff

Updated 2026-10-28 (traits replace ideas and Covers). Branch `dws-workflow` (never merge to `main` until DWS is
built). Beads is the work-state authority; this file is the narrative.

## Start here (new session)

1. Read `harness_lifecycle/playbook.md` (the method), then
   `harness_lifecycle/registry/README.md` (records, ledger, tool).
2. `git status` and `git log --oneline -6`; compare with "Uncommitted work"
   below.
3. `UV_CACHE_DIR=/tmp/uv-cache uv run python harness_lifecycle/registry/registry.py check`
   must print `ok`.
4. Resume at "In flight".

## Working rules for this workstream

- **Roles.** Opus 5.5 medium writes all code; GPT-6.1 Sol high reviews,
  read-only. Dispatch both through the T3 `delegate_task` tool with an explicit
  model, one task at a time (the Agent tool's `implementer` type is pinned to
  Opus 4.8). A task that hits a rate limit is resumed by T3 itself: never
  relaunch it. Without T3, Sol runs as
  `codex exec -C <repo> -s read-only -m gpt-6.1-sol -c model_reasoning_effort=high -o <answer> "<prompt>" < /dev/null`.
  Skill and harness doc edits are made by the orchestrating session itself,
  never by the implementer.
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

## Done (all pushed)

| Commit | What |
|---|---|
| `19f3f5a` | Registry replaces `gap.py`, `ledger.json`, inventory CSVs and the casebook. 36 skill records, sealed migration round (243 events), generated `references/` and `INDEX.md`. Epic `cr-skwm` closed |
| `fc7feb3` | Six owner rulings on broken migration adoptions (round `2026-10-14-owner-review`); `registry/reviews/` folder; skill and harness comparisons archived; `harness-skill-compare` writes a skill review; `round open` date fix (`cr-alnr`) |
| `52bf9fc` | `harness_lifecycle/playbook.md`; seven placement fixes; ADLC sub-stage Orchestration renamed Coordination |

Decisions behind them: domains `core` and `engineering`; one primary
coordinate per skill (domain · stage · sub-stage); reviews are flat files
`reviews/<date>-<upstream|skill>-<slug>.md`, linked into records by `build`;
frozen material goes to `harness_lifecycle/archive/`.

## In flight: idea-level rulings (epic `cr-axdt`)

Owner decision, 2026-10-22: before any Pocock ruling, build idea-level
tracking, bump Pocock to its latest upstream, and redo the review and rulings
on the new mechanism. Design: `idea-level-design.md`. The draft 1.3.1 rulings
and the decision record are saved in `pocock-1.3.1-draft-rulings.md`; reuse
them wherever upstream has not changed since `49dd158`.

Order: `cr-axdt.1` Sol design review (DONE: approved after 3 rounds; reviews in `scratchpad/sol-design-review*.md`) → `cr-axdt.2` build (Opus implementer)
and `cr-zo2f` (gap diff, folded in) → `cr-axdt.3` docs → `cr-axdt.4` Pocock
pilot. `cr-z1hk` waits on the pilot. Finding behind the tree hash: catalog
`content_hash` covers `SKILL.md` only, so asset-only upstream changes were
invisible to `gap`.

**Status 2026-10-22 (late):** mechanism built and reviewed (`cr-axdt.1`–`.3`,
`cr-zo2f` closed); Pocock at `5beb35b`; idea-level review at
`harness_lifecycle/registry/reviews/2026-10-22-upstream-mattpocock_skills-1.3.1-47.md`.

**Status 2026-10-28: traits replace ideas and Covers (`cr-axdt.5`).** Design
`traits-design.md` (Sol approved, 4 rounds; §5 amended for grandfathered
pre-trait rounds). Built and migrated: `registry/trait-definitions.yaml` (597
traits), `registry/traits.yaml` (36 ours, 25 Pocock entries), generated
`TRAITS.md`; Covers and `covers_hash` stripped from records; old item →
trait table `trait-migration-2026-10-28.md`. Sol code+data review: 3 rounds,
APPROVE. Gates: 56 registry tests, `check` ok (19 overlap warnings, input to
`cr-talb`), `skill-catalog.py --check` ok. `reference-records/` and
`CAPABILITIES.md` were never committed; moved to
`scratchpad/traits-migration/removed/`. Working files and Sol reviews:
`scratchpad/traits-migration/`.

**Next in the pilot (`cr-axdt.4`), waiting on the owner's ruling.** `gap
mattpocock_skills` lists 23 skills "awaiting trait ruling" (`pr` and `retro`
are unreviewed). Draft rulings, re-keyed to traits:
`scratchpad/traits-migration/pilot-rekeyed/{core,build,design}.jsonl`
(`dropped.jsonl`: 4 routing drafts). Clean them before recording: six subjects
carry two drafts; two drafts have a list in `into`; gap drafts that point
`into` a neighbour become `pending` adopts; `teach#proximal-next-lesson` holds
an implementer's modification, re-rule it; nine upstream traits have no draft
(`delete-debug-prototypes`, `context-specific-terms`, `session-sized-tickets`,
`always-stateful-course`, `findings-file`, `html-lessons`,
`shared-component-extraction`, `glossary-admission-on-use` on teach,
`live-human-resolution`). Then `round open` with `trait_level: true`, record,
seal, `build`, `check`, one bead per pending gap, commit with the `5beb35b`
pointer.

## Superseded: Pocock 1.2.3 → 1.3.1 draft rulings (kept for reuse)

Playbook §4, pins `84fdeff` → `49dd158`, 125 commits, 39 `gap` items.

- Review: `harness_lifecycle/registry/reviews/2026-10-14-upstream-mattpocock_skills-1.3.1.md`.
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
     `prompting-guides/README.md` and `.repo-context/running-codex.md` edits.
- The skill edits themselves come later, in a worktree, per playbook §2.

## Uncommitted work (as of this handoff)

| Path | State |
|---|---|
| `docs/workstreams/skill-curation/` | new; this handoff, `idea-level-design.md`, `traits-design.md`, `trait-migration-2026-10-28.md`, `overlap-audit-2026-10-22.md`, draft review/rulings |
| `harness_lifecycle/registry/` | `registry.py` + `tests/test_registry.py` (traits), `trait-definitions.yaml`, `traits.yaml`, `TRAITS.md`, README, regenerated records, references and `INDEX.md` |
| `harness_lifecycle/playbook.md` | §3–§4, §7 rewritten for traits |
| `harness_lifecycle/registry/reviews/2026-10-14-upstream-mattpocock_skills-1.3.1.md` | new; the Pocock review (draft; redo at idea level) |
| `harness_lifecycle/catalogs/mattpocock_skills.json` | regenerated at `5beb35b` |
| `reference_harnesses/mattpocock_skills` | pointer moved to `5beb35b`; commit with its ruling round |
| `harness_lifecycle/playbook.md` | Building step: rewrite borrowed ideas in our words; writing ideas go to `writing-principles.md` |
| `harness_lifecycle/prompting-guides/README.md` | when `GUIDE.md` may change |
| `.repo-context/running-codex.md` | close stdin for background `codex exec` |
| `reference_harnesses/cursor_plugins` | pointer moved to `ce649c0`; waits for its own review |
| `.beads/issues.jsonl`, `tools/T3/*` | not this workstream; leave alone |

## Next, in order

1. Epic `cr-axdt` (above), ending with the Pocock idea-level rulings.
2. agent-skills 0.6.13 rulings by playbook §4: the review exists
   (`reviews/2026-10-14-upstream-agent-skills-0.6.13.md`) but no rulings; `gap
   agent-skills` shows 12 changed and 2 new (constraint-driven-development
   and `/constraints`). Its six borrow candidates feed the verdicts.
3. Cursor (`cursor_plugins`) upstream review, then commit its pointer.
4. Data clean-up in the migration round: 29 casebook/ledger disagreements and
   84 rulings with no content hash (re-rule them as each harness is reviewed).
5. Hand-written Capability text for the 36 skill records (seeded from each
   skill's description), and proper `family` values.

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
- Deferred rulings to revisit: `context-engineering` and
  `doubt-driven-development` (agent-skills).
- The old worktree `coding-ritual-registry` (a sibling of the repo checkout) (branch `wf/registry`,
  merged) can be removed with `git worktree remove` on the original machine.

## Gotchas

- `codex exec` from a background shell needs `< /dev/null`, or it waits on
  stdin forever.
- Run Python with `UV_CACHE_DIR=/tmp/uv-cache uv run …` (pydantic is not in
  the system Python).
- A ruling's `content_hash` must come from the catalog at the reviewed pin;
  regenerate the catalog (`scan.py catalog … --out …`) before recording.
- Sealed rounds are immutable; an open round can be edited before `round seal`.
