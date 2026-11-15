---
trigger: Adding, placing, reviewing, comparing, updating or retiring a skill of this repository, or reviewing an upstream harness release.
traits: [curation-role-separation]   # new
steps:
  - id: skill-curation#1
    when: always
    actions: [{trait: curation-intake-bead}]   # new
  - id: skill-curation#2
    when: always; read only the references the applicable branches need
    actions: [{trait: artifact-owned-placement}, {trait: placement-vs-description}, {trait: blind-extract-then-map}, {trait: skill-entries-with-change}, {trait: upstream-review-on-pin-move}, {trait: append-only-trait-analysis}, {trait: report-pairing-coverage}, {trait: row-recommendation-rules}, {trait: prompting-guide-check}, {trait: failure-first-update}, {trait: withdraw-on-local-update}]   # all new but upstream-review-on-pin-move; the first two for Place and Add, the third for Place, Add and an upstream release, the fourth for Place, Add and an update from our own failure, the next five for an upstream release, the last two for an update from our own failure
    calls: [{to: "skill:harness-scan", when: an upstream release}, {to: "skill:harness-skill-compare", when: "Compare, Merge or split, or two skills in one sub-stage"}, {to: "skill:harness-evaluate", when: "Add with an upstream source, or a new non-skill capability in an upstream release"}, {to: "skill:authoring-for-agents", when: "an update from our own failure: picking the form of the fix"}]
    loads: [{path: skill-curation/placing.md, when: "Place, Add, or finding the owning skill of a failure"}, {path: skill-curation/upstream-review.md, when: "an upstream release; for Place or Add, only its step 2 (extract blind, then map)"}, {path: skill-curation/skill-review.md, when: "Compare, Merge or split, or placing.md step 4 finding two skills in one sub-stage"}, {path: skill-curation/candidate-evaluation.md, when: "Add with an upstream source, or a new non-skill capability in an upstream release"}, {path: skill-curation/failure-update.md, when: an update from our own failure}]
  - id: skill-curation#3
    when: the evidence is ready
    actions: [{trait: ruling-before-change}, {trait: record-command}, {trait: per-trait-ruling}, {trait: mechanism-rule-policy-entry}]   # the first, third and fourth new; the last two for an upstream release
  - id: skill-curation#4
    when: a recorded ruling calls for a change
    actions: [{trait: isolated-skill-build}, {trait: skill-entries-with-change}, {trait: rewrite-borrowed-ideas}, {trait: writing-idea-destination}, {trait: merge-split-reference-fix}, {trait: retire-stub-one-release}, {trait: pending-adoption-completion}]   # new; the fifth for Merge or split, the sixth for Retire, the last when a pending adoption's edit lands
    calls: [{to: "skill:authoring-for-agents"}]
  - id: skill-curation#5
    when: skill-curation#4 changed something
    actions: [{trait: skill-catalog-check}, {trait: curation-verify}]   # the second new
    calls: [{to: "skill:authoring-for-agents", needs: [verification]}]
  - id: skill-curation#6
    when: skill-curation#5 passed, each part only with the owner's approval for this change
    actions: [{trait: authority-separation}, {trait: curation-delivery-order}]   # the second new
    calls: [{to: "skill:land"}, {to: "skill:harness-publish", when: the owner approves the publish}]
  - id: skill-curation#7
    when: every exit
    actions: [{trait: curation-closeout}]   # new
---

# Skill curation

For adding, placing, reviewing, comparing, updating or retiring a skill of
this repository, or reviewing an upstream harness release. Evaluating one
capability with no ruling wanted is `harness-evaluate` alone, not this
playbook.

How we add, place, review, compare, update and retire our skills. The
registry (`harness_lifecycle/registry/README.md`) holds the records and the tool; this file holds
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
| 1. Intake | A bead: `spike` for an upstream review, `bug` for an observed failure, `feature` for a new capability | The bead |
| 2. Evidence | The method for the operation (its reference in the table below; read only the references the applicable branches need, such as `placing.md` then `candidate-evaluation.md` for an upstream source) | A review or sealed report in `harness_lifecycle/registry/reviews/`, or the observed failure |
| 3. Ruling | The owner decides; the author then records each ruling with `registry.py record`, giving its kind, subject, reason (`--why`) and evidence (one event per trait for an upstream skill) | Ledger events citing the evidence |
| 4. Building | In a git worktree on its own branch, so running sessions keep the current skills. Edit the skill, its `harness_lifecycle/registry/skills.yaml` entry when placement or boundary change, and its `harness_lifecycle/registry/traits/ours.yaml` entry, then `registry.py build`; records are generated, never edited. Rewrite every borrowed idea in our words by `authoring-for-agents`; never paste upstream text. Writing ideas from a reference harness go into its `writing-principles.md`, never into `harness_lifecycle/prompting-guides/GUIDE.md` | A diff |
| 5. Verify | The checks in `authoring-for-agents`, `skill-catalog.py --check`, `registry.py build` and `check`; a critic for new or rewritten skill bodies | Recorded results |
| 6. Delivery | Commits through `land`, then merge (the promotion), then `.codex` sync, then `/harness-publish` | A merged commit |

A ruling is recorded before the skill changes. A ruling of `adopt` or
`adopt-merged` waits until the adopted state exists.

Delivery runs one part at a time, each only with the owner's approval for
this change: the commits, the merge, a push, the publish. One approval does
not cover the next, and an instruction not to commit stands.

| Operation | Starts from | Method | Records |
|---|---|---|---|
| Place | a new or moved skill | `skill-curation/placing.md` | the skill's `skills.yaml` entry |
| Add | a new need; check overlap first (`skill-curation/placing.md`) | `skill-curation/placing.md`, then `skill-curation/candidate-evaluation.md` for any upstream source | `add`; a `skills.yaml` entry |
| Update | our own failure or lesson | `skill-curation/failure-update.md` | `update`, with the failure as evidence |
| Upgrade from upstream | a reference release | `skill-curation/upstream-review.md` | one ruling per changed or new trait, citing a sealed report |
| Compare | two or more skills that may overlap | `skill-curation/skill-review.md` | the skill review; then rulings |
| Merge or split | overlap, or a skill grown too big | `skill-curation/skill-review.md` | `merge` or `split`; references fixed in the same change |
| Retire | unused or merged | — | `retire`; a stub stays for one plugin release, then the folder is removed |

## 3. Close out

Step 7, on every exit, done or stopped: note the bead with the evidence reached and
a resume line, or close it with the evidence when the change is done; name
the ledger state (rulings recorded, adoptions still pending, or none); and
confirm nothing was built without a recorded ruling, reporting anything that
was.

## Reply

- **Done**, only when its rulings are recorded, its skill, `skills.yaml`
  entry and trait list agree (`build` regenerates the record),
  `registry.py check` and `skill-catalog.py --check` pass, the critic's findings
  are closed, and the owner has approved the merge: the merged commit, the
  rulings recorded, each check with its result, and the critic's verdict.
- **Recommendation only, or declined:** the evidence (the review or sealed
  report), the recommendation, any ruling recorded (`reject`, `defer`,
  `out-of-scope`), and that nothing was built.
- **Awaiting the owner:** the evidence, the drafted rulings or edit, which
  ruling or approval is needed (a ruling, the commits, the merge, a push, the
  publish), and that nothing waiting on it was done.
- **Verification incomplete:** the change, each check run with its result,
  which check or critic finding did not pass or could not run and why, and
  what is still needed to call it done. Nothing is merged.

Every reply also gives the closeout's bead and ledger state.
