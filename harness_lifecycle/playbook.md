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
| Evidence | The method for the operation (§3–§7) | A review in `registry/reviews/`, or the observed failure |
| Ruling | The owner decides; the author records one ledger event per capability | Ledger events citing the evidence |
| Building | In a git worktree on its own branch, so running sessions keep the current skills. Edit the skill, its record and its `traits.yaml` entry. Rewrite every borrowed idea in our words by `authoring-for-agents`; never paste upstream text. Writing ideas from a reference harness go into its `writing-principles.md`, never into `prompting-guides/GUIDE.md` | A diff |
| Verify | The checks in `authoring-for-agents`, `skill-catalog.py --check`, `registry.py build` and `check`; a critic for new or rewritten skill bodies | Recorded results |
| Delivery | Merge (the promotion), then `.codex` sync, then `/harness-publish` | A merged commit |

A ruling is recorded before the skill changes. A ruling of `adopt` or
`adopt-merged` waits until the adopted state exists.

| Operation | Starts from | Method | Records |
|---|---|---|---|
| Place | a new or moved skill | §3 | the skill record's frontmatter |
| Add | a new need; check overlap first (§3) | §3, then §6 for any upstream source | `add`; a new skill record |
| Update | our own failure or lesson | §7 | `update`, with the failure as evidence |
| Upgrade from upstream | a reference release | §4 | one ruling per changed or new capability |
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
   active skills in one sub-stage each state their boundary in the record's
   Capability, or they are merge candidates (§5).
5. Write the Capability: what it does, when it fires, and where it ends and
   its neighbours begin. Then list its traits in `registry/traits.yaml` by
   the procedure in §4 step 2 (extract blind, then map), with the folder's
   `tree_hash`.

## 4. Upstream review: a reference harness released

Unit: one harness, from the pinned commit to the new one. Skills are ruled
trait by trait, so a release review covers only what changed and never
re-decides an earlier take or decline. Other kinds (agents, commands, hooks)
keep one ruling per capability. Traits and their rules:
`registry/README.md` §4a.

1. Run `/harness-scan <harness>`: drift, then regenerate the catalog at the
   new pin (`scan.py catalog`), then `registry.py gap`. For each changed
   skill `gap` prints the diff command for its whole folder and the traits
   already ruled; it also lists new and removed capabilities.
2. For each **changed or new** skill, list its traits in two passes:
   1. **Extract blind.** An agent reads only the upstream skill folder (and
      the diff) and lists every material mechanism, one line each, by the
      rules in README §4a. Its brief does not name `trait-definitions.yaml`
      or `traits.yaml`, so the existing vocabulary cannot anchor it.
   2. **Map**, as a separate pass: each extracted line gets an existing
      trait ID when the mechanism is the same, is split when it only partly
      matches, or gets a new definition. A looser or stricter variant is a
      new trait with `distinct_from`.

   Update the skill's upstream entry in `traits.yaml`: new traits, `added`
   and `removed` with the new sha, the new `reviewed_sha` and `tree_hash`.
   Then classify each new or changed trait:

   | Class | Test | Verdict |
   |---|---|---|
   | Cosmetic | Wording, metadata or version only; no behaviour change | Keep its ruling; no new trait event |
   | Covered | A behaviour change our skill already has: our skill lists the same trait (cite `file:line` in ours) | Keep its ruling, or `adopt` if first ruled now |
   | Conflict | Contradicts one of our rules (`AGENTS.md`, git safety, uv-only, and so on) | `reject`, with the rule |
   | Gap | A trait we lack, cheap and in scope | `adopt` with `pending`, and a bead for the edit |
   | Gap, costly | A trait we lack, large, uncertain or out of scope | `defer`, with what would bring it back |

   Unchanged traits keep their rulings. When upstream moves a skill or
   replaces a trait, the new trait events name the old subjects in
   `carried_from`. A trait can go into a method document instead of a skill
   (`doc:<path>`).
3. Evaluate each **new** capability by §6, listing its traits by step 2.
4. Write `registry/reviews/<yyyy-mm-dd>-upstream-<harness>-<version>.md`: the
   release themes; per skill the blind list and the mapping (extracted line
   → trait ID, marked match, split or new); then one row per changed or new
   trait with its upstream change (`file:line`), our counterpart
   (`file:line`), class, verdict and reason.
5. A critic checks the blind lists against the folders (nothing missed or
   bundled), the mappings (nothing forced), and the classes and verdicts
   against the diffs.
6. The owner rules. Open the round with `trait_level: true`. Record one trait
   event per new or changed trait, and one checkpoint per reviewed skill at
   the new pin whose kind agrees with its traits (`registry/README.md` §5b).
   Then `build` and `check`.
7. Move the submodule pointer in the same commit as the review, the round,
   the catalog and the trait files.
8. When a pending adoption's edit lands, record the completing `adopt`
   (README §5b) in the same change as the edit, and refresh the skill's
   `tree_hash`.

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
5. Update the skill's traits in `registry/traits.yaml` and its `tree_hash`.
   If the fix drops a trait we adopted from upstream, the `update` event
   lists that upstream trait in `withdraws`; an upstream ruling never removes
   it for us.

## 8. Done

A change is done when its rulings are recorded, its skill and record agree,
`registry.py check` and `skill-catalog.py --check` pass, the critic's findings
are closed, and the owner has approved the merge.
