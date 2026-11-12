# Upstream review: a reference harness released

Unit: one harness, from the pinned commit to the new one. Skills are ruled
trait by trait, so a release review covers only what changed and never
re-decides an earlier take or decline. Other kinds (agents, commands, hooks)
keep one ruling per capability. Traits and their rules:
`harness_lifecycle/registry/README.md` §4a; the stages and status: §5c; the ruling rules: §5b.

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

   Add the result to the skill's entry in `harness_lifecycle/registry/traits/<harness>.yaml` as
   a new analysis at the new sha, named by `proposed`: for a changed skill,
   `added`, `changed` (same meaning) and `removed` traits from the diff;
   untouched traits stay. Never edit an earlier analysis.
3. Evaluate each **new non-skill** capability by `candidate-evaluation.md`.
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
     target will carry, against `harness_lifecycle/prompting-guides/GUIDE.md` rule IDs and
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
   `harness_lifecycle/registry/trait-policy.yaml` entry in the same change. Promote each
   decided entry (`accepted` ← the proposed sha, `proposed` ← null). Then
   `build`, `check` and `status`.
7. Move the submodule pointer in the same commit as the report, the round,
   the catalog and the trait files.
8. When a pending adoption's edit lands, record the completing `adopt` with
   `record --supersedes <pending id>` in the same change as the edit, and
   refresh the skill's `tree_hash`.
