# Skill playbook

How we add, place, review, compare, update and retire our skills. The
registry (`registry/README.md`) holds the records and the tool; this file holds
the method. Writing a skill's text follows the `authoring-for-agents` skill.

## 1. Roles

| Role | Does | Never |
|---|---|---|
| Owner | Decides every ruling, approves commits, merges, pushes and publishes | — |
| Author | Gathers evidence, drafts rulings and edits, runs the checks | Approves its own work |
| Critic | Reviews the author's evidence or edit from a separate context | Edits during review |

The owner picks which agent or model fills the author and critic roles.

## 2. One path for every change

| Step | What happens | Output |
|---|---|---|
| Intake | A bead: `spike` for an upstream review, `bug` for an observed failure, `feature` for a new capability | The bead |
| Evidence | The method for the operation (§3–§7) | A review or sealed report in `registry/reviews/`, or the observed failure |
| Ruling | The owner decides; the author records the ledger events (one per trait for an upstream skill) | Ledger events citing the evidence |
| Building | In a git worktree on its own branch, so running sessions keep the current skills. Edit the skill, its `registry/skills.yaml` entry when placement or boundary change, and its `registry/traits/ours.yaml` entry, then `registry.py build`; records are generated, never edited. Rewrite every borrowed idea in our words by `authoring-for-agents`; never paste upstream text. Writing ideas from a reference harness go into its `writing-principles.md`, never into `prompting-guides/GUIDE.md` | A diff |
| Verify | The checks in `authoring-for-agents`, `skill-catalog.py --check`, `registry.py build` and `check`; a critic for new or rewritten skill bodies | Recorded results |
| Delivery | Merge (the promotion), then `.codex` sync, then `/harness-publish` | A merged commit |

A ruling is recorded before the skill changes. A ruling of `adopt` or
`adopt-merged` waits until the adopted state exists.

| Operation | Starts from | Method | Records |
|---|---|---|---|
| Place | a new or moved skill | §3 | the skill's `skills.yaml` entry |
| Add | a new need; check overlap first (§3) | §3, then §6 for any upstream source | `add`; a `skills.yaml` entry |
| Update | our own failure or lesson | §7 | `update`, with the failure as evidence |
| Upgrade from upstream | a reference release | §4 | one ruling per changed or new trait, citing a sealed report |
| Compare | two or more skills that may overlap | §5 | the skill review; then rulings |
| Merge or split | overlap, or a skill grown too big | §5 | `merge` or `split`; references fixed in the same change |
| Retire | unused or merged | — | `retire`; a stub stays for one plugin release, then the folder is removed |

## 3. Placing a skill

Every skill has one primary coordinate: domain · stage · sub-stage. Stages
and sub-stages are defined in `adlc/GUIDE.md` §1; its mapping rules (§1,
"Mapping skills onto the lifecycle") decide placement.

1. Name the artifact the skill produces. The sub-stage that owns that
   artifact is the primary home. A skill that serves every stage belongs to X
   Crosscutting or U Utilities.
2. Check the definition and the boundary table in `adlc/GUIDE.md` §1. A
   placement that needs a boundary exception is wrong.
3. Add at most two secondary tags, only for real spans.
4. List the other skills already in that domain · sub-stage (`INDEX.md`). Two
   active skills in one sub-stage each state their `boundary` in
   `registry/skills.yaml`, or they are merge candidates (§5).
5. Write the placement and boundary in `registry/skills.yaml`; what the skill
   does and when it fires is its `SKILL.md` description. Then list its traits
   in `registry/traits/ours.yaml` by the procedure in §4 step 2 (extract
   blind, then map), with the folder's `tree_hash`, and run `registry.py
   build`.

## 4. Upstream review: a reference harness released

Unit: one harness, from the pinned commit to the new one. Skills are ruled
trait by trait, so a release review covers only what changed and never
re-decides an earlier take or decline. Other kinds (agents, commands, hooks)
keep one ruling per capability. Traits and their rules:
`registry/README.md` §4a; the stages and status: §5c; the ruling rules: §5b.

1. **What needs analysis.** Run `/harness-scan <harness>`: drift and `gap`.
   With the owner's authorization, move the pin and regenerate the catalog
   (`scan.py catalog`). `registry.py status <harness>` then shows each skill's
   stage: *not analysed* (new) or *needs re-analysis* (its folder's
   `tree_hash` changed). Every other skill keeps its stage.
2. **Analysis.** For each new or changed skill, list its traits in two
   passes:
   1. **Extract blind.** An agent reads only the upstream skill folder (and,
      for a changed skill, `git diff <accepted sha>..<new sha> -- <folder>`)
      and lists every material mechanism, one line each, by the rules in
      README §4a. Its brief does not name the trait files, so the existing
      vocabulary cannot anchor it.
   2. **Map**, as a separate pass: each extracted line gets an existing
      trait ID when the mechanism is the same, is split when it only partly
      matches, or gets a new definition. A looser or stricter variant is a
      new trait with `distinct_from`.

   Add the result to the skill's entry in `registry/traits/<harness>.yaml` as
   a new analysis at the new sha, named by `proposed`: for a changed skill,
   `added`, `changed` (same meaning) and `removed` traits from the diff;
   untouched traits stay. Never edit an earlier analysis.
3. Evaluate each **new non-skill** capability by §6.
4. **Report.** `registry.py report draft <harness> --skill <id> --with <our
   skill|none>` per skill. Pick the compared skill from the pairing signals
   (trait overlap, placement, and purpose: what each produces and when it
   fires); set `pairing.flag` with the reason when they disagree. The tool
   fills the facts; only the compared skill or AGENTS.md makes a trait
   present, and a trait elsewhere in our skills is never coverage. The
   author fills, per row:
   - `ours` citations (`file:line`) for a `present` or `variant` row;
   - the recommendation: `present` → adopt, delivered; `variant` → adopt
     modified (`via`, `modification`) when our difference is deliberate,
     else adopt pending an edit; `absent` → adopt pending an edit, `defer`
     (`revisit_when`), `reject` (reason or rule) or `out-of-scope`;
   - **the prompting-guide check** on every adopt row: the wording our
     target will carry, against `prompting-guides/GUIDE.md` rule IDs and
     the writing principles of `authoring-for-agents` (`ok`; `reword`, an
     adopt pending with `rewording`; `conflict`, recommend reject). Follow a
     pre-filled trait-policy stance or argue to change it.
5. **Critics.** One checks the blind lists against the folders (nothing
   missed or bundled) and the mappings (nothing forced); one checks the
   facts against the files, the recommendations against step 4 and the
   guide verdicts. Their verdicts go in the report's `analysis_critic` and
   `comparison_critic`. Then `registry.py report seal <path>`.
6. **The owner rules** each in-scope trait. Open a round. Record one trait
   event per in-scope trait, citing the report (`record` refuses a stale row
   or a broken rule), and one checkpoint per reviewed skill at the new pin
   whose kind agrees with its traits (README §5b). A skill not analysed may
   be ruled whole (`defer`, `reject`, `out-of-scope`). When a rejection or
   rewording follows a guide rule that holds for the mechanism itself, add a
   `registry/trait-policy.yaml` entry in the same change. Promote each
   decided entry (`accepted` ← the proposed sha, `proposed` ← null). Then
   `build`, `check` and `status`.
7. Move the submodule pointer in the same commit as the report, the round,
   the catalog and the trait files.
8. When a pending adoption's edit lands, record the completing `adopt` with
   `record --supersedes <pending id>` in the same change as the edit, and
   refresh the skill's `tree_hash`.

## 5. Skill review: comparing skills

Use it to decide a merge, upgrade or rebuild of one of our skills, or when
§3 step 4 finds two skills in one sub-stage. Run the `harness-skill-compare`
skill. It writes `registry/reviews/<yyyy-mm-dd>-skill-<our-skill>.md` with
the set, the components with `file:line`, the presence matrix, the
differences with the stronger mechanism, and a verdict. The verdict is a
recommendation; rulings follow from §2.

## 6. Evaluating a candidate capability

Run the `harness-evaluate` skill. Read the whole capability, including its
references and scripts, and our nearest skill (§3 step 4). Judge:

- behaviour gain over what we have;
- overlap with our skills, and which one would own it;
- dependencies it brings (tools, other skills, a tracker);
- context cost: how much it loads, and when;
- maintenance: how often upstream changes it.

Outcomes: `adopt` (taken whole), `adopt-merged` (parts into one of ours, with
the adaptation), `reject` (not taken, on merit), `defer` (not now, with what
would bring it back), `out-of-scope` (not our kind of work).

## 7. Updating from our own failure

1. Record the failure before changing anything: the task, what the agent did,
   and what it should have done.
2. Find the owning skill by its coordinate (§3). Fix it there, not in a
   neighbour.
3. Pick the form that fixes the failure (`authoring-for-agents`, "Match the
   form to the failure").
4. Re-run the task, or a fresh-context test of it, and keep both results as
   the `update` event's evidence.
5. Update the skill's traits in `registry/traits/ours.yaml` and its
   `tree_hash`.
   If the fix drops a trait we adopted from upstream, the `update` event
   lists that upstream trait in `withdraws`; an upstream ruling never removes
   it for us.

## 8. Done

A change is done when its rulings are recorded, its skill, `skills.yaml`
entry and trait list agree (`build` regenerates the record),
`registry.py check` and `skill-catalog.py --check` pass, the critic's findings
are closed, and the owner has approved the merge.
