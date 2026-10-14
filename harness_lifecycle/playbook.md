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
| Building | In a git worktree on its own branch, so running sessions keep the current skills. Edit the skill and its record | A diff |
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
   its neighbours begin.

## 4. Upstream review: a reference harness released

Unit: one harness, from the pinned commit to the new one.

1. Run `/harness-scan <harness>`: drift, then `registry.py gap`.
2. For each **changed** capability we have ruled on, read the diff between
   the two pins for that capability only, then:

   | Class | Test | Verdict |
   |---|---|---|
   | Cosmetic | Wording, metadata or version only; no behaviour change | Keep the ruling; record it again at the new hash |
   | Covered | A behaviour change that our counterpart already has (cite `file:line` in ours) | Keep the ruling; record it again at the new hash |
   | Conflict | Contradicts one of our rules (`AGENTS.md`, git safety, uv-only, and so on) | Keep the ruling; record why |
   | Gap | A behaviour we lack, cheap and in scope | `adopt` or `adopt-merged`, and a bead for the edit |
   | Gap, costly | A behaviour we lack, large, uncertain or out of scope | `defer`, with what would bring it back |

3. Evaluate each **new** capability by §6.
4. Write `registry/reviews/<yyyy-mm-dd>-upstream-<harness>-<version>.md`: the
   release themes, then one row per capability with its upstream change
   (`file:line`), our counterpart (`file:line`), class, verdict and reason.
5. A critic checks the classes and verdicts against the diffs.
6. The owner rules. Record each ruling with `source.sha` and `content_hash` at
   the new pin, citing the review.
7. Move the submodule pointer in the same commit as the review, and
   regenerate the catalog (`scan.py catalog`) at the new pin.

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

## 8. Done

A change is done when its rulings are recorded, its skill and record agree,
`registry.py check` and `skill-catalog.py --check` pass, the critic's findings
are closed, and the owner has approved the merge.
