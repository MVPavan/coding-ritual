# Curation stages, status, and the `curation` package

Status: revision 7, 2026-10-30 (rounds 1–4: REVISE, 30 findings, all
accepted; round 5: APPROVE; rounds 6–7: REVISE, 5 findings, accepted;
round 8: APPROVE; dispositions at the end). Awaiting owner approval. Revision 6 adds owner decisions: pairing by
purpose as well as traits (2.1) and the prompting-guide check with
`trait-policy.yaml` (2.9, §Trait policy); revision 7 answers rounds 6–7
(3.4a rewording; policy retirement, guide digests and `policy_basis`). Revision 3
also adds two owner decisions: `skills.yaml` with fully generated skill
records, and `traits.yaml` split per source (§Files). Builds on `traits-design.md`
(approved; its §4 rulebook and §5 ledger rules stay unless changed here).
Owner decisions 2026-10-30 are marked **[owner]**.

## Problem

1. **Redone work.** Nothing records how far an upstream skill got: traits
   extracted, compared, reported, or decided. A deferred trait looks the same
   as one nobody looked at.
2. **False coverage.** **[owner]** "Another skill of ours has this trait" is
   never a decision. Only the skill we compare against (or AGENTS.md) counts;
   anything else is an open question for the report.
3. **Unstructured reports.** Free Markdown cannot be checked for coverage,
   true "present" claims, or a report behind each decision.
4. **One large file.** `registry.py` (3,157 lines) and `scan.py` (943).

## Terms

| Term | Meaning |
|---|---|
| Upstream skill | One skill of a reference harness, identified by its logical ID |
| Analysis | One immutable trait list for an upstream skill at one sha (`analyses.<sha>`) |
| Accepted analysis | The analysis the decisions describe (`accepted: <sha>`, or none yet) |
| Proposed analysis | A newer analysis, done but not yet decided (`proposed: <sha>`) |
| Compared skill | The one skill of ours an upstream skill is compared against, or `none` |
| Provider | What makes a trait present: the compared skill or `doc:AGENTS.md` |
| Fact | Computed per upstream trait: `present`, `variant` (with `via`), `absent`, plus `also_in` |
| Report | A YAML file per review pass: analysis evidence, comparison rows, recommendations |
| Ruling | The effective ledger decision on a trait |
| Provision | Whether we actually provide the trait now (delivered, pending, withdrawn, no longer provided) |

## Stages

### Stage 0: what needs analysis

- **0.1 Discovery is read-only.** `scan.py drift` and `harness-status` fetch
  upstream and report what changed; they never move a pin. Moving the
  submodule pin and regenerating the catalog is a separate, authorized step,
  committed with the release's review (playbook §4 step 7).
- **0.2 New upstream skill.** In the catalog at the current pin with no
  entry in `traits/<harness>.yaml`: *not analysed*. It gets a full analysis.
- **0.3 Existing upstream skill.** **[owner]** It already has traits. After
  an authorized pin update, it needs re-analysis only if its folder changed:
  the catalog `tree_hash` (sha256 over relative paths and raw bytes;
  file modes are deliberately ignored, since an executable bit adds no
  mechanism) differs from the analysed one. `drift` previews which skills
  that will be before the pin moves.
- **0.4 Untouched skill.** It keeps every stage it reached; nothing is redone.
- **0.5 Removed upstream.** *Removed upstream*; its rulings stay as history;
  we keep what we adopted (README §5b).

### Stage 1: analysis (what upstream has)

The result is a new analysis in the entry, keyed by its sha, and the entry's
`proposed` pointer names it. Earlier analyses are never edited (§Entries).

- **1.1 New skill.** Blind extraction of the whole folder, then a separate
  mapping pass (README §4a).
- **1.2 Changed skill.** **[owner]** The agent reads
  `git diff <accepted sha>..<new sha> -- <folder>` plus the current files and
  writes the new analysis from the previous one:
  - a mechanism added upstream → a trait added (new definition only if none
    fits): `added: {id: sha}`;
  - a mechanism changed whose meaning still holds → same ID:
    `changed: {id: sha}` (new field);
  - a changed mechanism with a new meaning → new trait B in `added`, old A in
    `removed`; B's later ruling carries `carried_from: [<subject>#A]`;
  - a mechanism removed upstream → `removed: {id: sha}`;
  - untouched traits stay.
- **1.3 Evidence.** The blind list and the mapping go into the report's
  `analysis` section (§Report). A critic checks nothing was missed, bundled
  or forced; the report records that verdict. `tree_hash` and `reviewed_sha`
  of the analysis are its key and fields; the catalog must match them while
  the pin is current.
- **1.4 Our side.** When one of our skills, AGENTS.md or another inventoried
  `doc:` file changes, its list is re-analysed at once (`check` fails on a
  stale `tree_hash` for every entry in `traits/ours.yaml`).
  That re-analysis is what keeps "present" honest: the list is re-confirmed
  against the text.
- **1.5 AGENTS.md and what it references.** **[owner, 2026-10-30]** Only what is always in context makes a trait present for
  every compared skill.
  - `AGENTS.md` (CLAUDE.md only imports it) has its own entry,
    `doc:AGENTS.md`, analysed like a skill; its traits count as present for
    every compared skill (2.2). Its list covers what AGENTS.md itself
    mandates ("run the applicable checks before claiming done"); a bare
    "read X when needed" pointer is routing and no trait (rule 3).
  - Documents AGENTS.md references load only when the model decides, like
    skills, so they never make a trait present. Those with real mechanisms
    get their own entry, `doc:.repo-context/<file>`, analysed like a skill:
    they appear in `also_in`, and a decision may target them. Now:
    `coding-style.md`. After its clean-up (bead `cr-k1b6`):
    `verification.md`. Ignored: `running-codex.md`. No entry: `repo-map.md`, `docs-index.md` (routing),
    `CONTEXT.md` (vocabulary). Later, when a comparison first needs them:
    `invariants.md`, `learnings.md`.
  - `bd prime`, injected at every session start and after compaction, gets
    no entry **[owner]**: its text is the core of the `beads` skill, whose
    list already carries those traits.

### Stage 2: comparison and report (what we have, and a recommendation)

One stage **[owner]**, recorded in the same report file as the analysis.

- **2.1 Pairing.** **[owner]** Three signals, all kept in the report:
  - *trait overlap* (computed): how many of the upstream skill's traits each
    of our skills (and each `doc:` entry) has, present or as a variant;
  - *placement* (computed): whether each candidate shares the upstream
    skill's domain · sub-stage;
  - *purpose* (judged): both descriptions side by side, the artifact each
    produces and when each fires (playbook §3).
  `report draft` suggests the skill with the most trait overlap, ties broken
  by placement. Only skills are pairing candidates; `doc:` entries appear in
  the overlap table but are never `compared_with`. The author names the
  compared skill, or `none`, and the skill whose purpose matches best. When
  those differ from each other or from the suggestion, the report sets
  `pairing.flag` and says why, for the owner. No description-similarity
  score is computed: on short descriptions it misleads. The critic checks
  the pairing; the owner may override at decision.
- **2.2 Facts, computed by the tool, never typed:**
  - `present`: the compared skill lists the trait (`provider` = that skill),
    or `doc:AGENTS.md` does (`provider: doc:AGENTS.md`);
  - `variant`: the compared skill lists a trait whose `distinct_from` names
    this one; `candidates` = those traits' IDs (computed); the row's `via`
    selects one (one row per upstream trait, always);
  - `absent`: neither;
  - `also_in`: every other skill of ours or `doc:` entry that has it, each
    marked `present` or `variant` (`{skill: present|variant}`). Information
    only: the comparison runs across all our skills **[owner]**, but only the
    compared skill or AGENTS.md makes a trait present.
- **2.3** **[owner]** `also_in` is never coverage and never a verdict. A
  partial match (`variant` that is not deliberate) is a gap: recommend adopt
  with an edit.
- **2.4 Our evidence.** Each `present` or `variant` row cites where the
  provider does it (`ours: [file:line]`). A wrong citation means a wrong
  list, fixed by 1.4 before any decision.
- **2.5 Recommendation rules:**
  - `present` → adopt, delivered, target = `provider`;
  - `variant` → adopt modified (`via`, `modification` required) if our
    difference is deliberate; otherwise adopt with an edit (pending), the
    fact staying `variant` (2.3);
  - `absent` → by usefulness for this skill: adopt (pending an edit), defer
    (`revisit_when` required), reject (reason or rule), out-of-scope. With
    `compared_with: none`, an adopt must name its `target`.
- **2.6 Scope** (computable from the entry and earlier reports):
  - new skill: every trait;
  - changed skill: traits in the proposed analysis's `added` or `changed`;
  - **re-comparison**: any undecided trait whose current row's fact,
    `provider`, `candidates`, `via` or `also_in` no longer equals the
    computed value;
  - **reconsideration**: a decided trait the owner reopens, or a deferred
    trait whose `revisit_when` has happened.
  Each row records why it is in scope: `scope: new | changed | recompare |
  reconsider`.
- **2.7** Every in-scope trait has exactly one row (checked).
- **2.8** A critic checks facts against files, recommendations against
  2.5 and guide verdicts against 2.9; the report records
  `comparison_critic`.
- **2.9 Prompting-guide check.** **[owner]** Every row recommending adopt
  (delivered or pending) is checked against
  `harness_lifecycle/prompting-guides/GUIDE.md` by its rule IDs (and the
  writing principles of `authoring-for-agents`). It judges the wording the
  target will carry once the adoption is delivered: our current text for a
  trait the target already lists, the planned edit otherwise. The row
  records `guide: {verdict: ok | reword | conflict, rules: [U-02, …]}`:
  - `ok` → the recommendation stands; a new delivered adopt needs `ok`
    (a row without `guide`, or with `conflict`, supports no delivered adopt;
    a pending adopt from a non-`ok` row needs `rewording`);
  - `reword` → an edit is outstanding: adopt **pending**, with the wording
    change in `rewording` (new field). For a trait the target already
    lists, this is a *wording-only* pending adopt (3.4a);
  - `conflict` → recommend reject, citing the rules.
  A trait with a `trait-policy.yaml` entry gets that stance pre-filled
  (`policy`); the author follows it or argues to change it. The guide judges
  how an instruction is written and when it pays; it does not override
  repository policy (GUIDE §0).

### Stage 3: decision (the owner rules)

- **3.1** The owner decides each in-scope trait: adopt, defer, reject,
  out-of-scope. The recommendation is input only.
- **3.2** Each new trait event carries `report: <path>` (new field). `check`
  validates, for every trait event outside the closed `pre_trait_rounds`,
  whatever its round flag: the report exists and is critic-passed, names the
  same harness and the event's source sha as its `to_sha`, and has a row for
  the subject's trait; the event's target equals that row's `provider`,
  `compared_with`, or the row's adopt `target`, or the event carries
  `retarget: "<reason>"` (new field).
- **3.3 Freshness is checked at record time.** `registry.py record` refuses
  a new decision whose cited row's fact, `provider`, `candidates`, `via` or
  `also_in` differs from the computed value now. `check` validates structure only
  (3.2), so a later delivery that turns `absent` into `present` never
  invalidates history.
- **3.4 Lifecycle events**, exempt from 3.3 and needing no new row:
  - completing a pending adopt: inherits the pending event's `report` and
    `source` exactly, including its sha (README §5b; `source` already
    enforced, `report` added);
  - cancelling a pending adopt: a reject or defer superseding it, inheriting
    the pending event's `report` and `source` exactly, with a reason.
  Both must explicitly supersede the subject's *effective* pending adopt, and
  a completion keeps the pending event's target and adopted trait; anything
  else is a new decision. `record` and `check` share this validation and
  verify the inheritance. Reconsideration (2.6) is a new decision and needs a
  new row.
- **3.4a Rewording.** `record` refuses a new delivered adopt from a row
  whose guide verdict is `reword`, and a pending adopt from such a row
  without `rewording`. A pending adopt carrying `rewording` records the
  target's `tree_hash` at that moment (`target_tree_hash`, new field) and is
  exempt from README §5b's "target already lists the trait" failure. Until
  completed, the provision is *pending*. Its completion is a lifecycle event
  (3.4): it inherits the pending event's `report` and `source`, so it cites
  the same `reword` row and is exempt from the prohibition above. It
  confirms the wording by carrying `guide: {verdict: ok, rules: <the row's
  rules>}` and the reworded lines in `evidence`; `record` refuses it while
  the target's `tree_hash` still equals `target_tree_hash`, and `check`
  verifies the rules match the row's.
- **3.5** Defer requires `revisit_when`, on the event as well as the row
  (whole-skill defers and cancellations into defer included); it never
  counts as adopted or
  rejected.
- **3.5a Trait policy.** When the owner rejects or rewords a trait for a
  guide rule that holds for the mechanism itself, not just this skill, the
  same change adds a `trait-policy.yaml` entry (§Trait policy). `record`
  refuses an adopt of a trait whose stance is `avoid` unless the event
  carries `override: "<reason>"` (new field).
- **3.6 Whole-skill mode.** Outside the `pre_trait_rounds`, whatever a
  round's flag, a skill-level `adopt` or `adopt-merged` needs an accepted
  analysis and its trait rulings. A skill with **no accepted analysis** may be
  decided as a whole: defer, reject or out-of-scope, with no stages 1–2
  **[owner: implement-spec, chief-of-staff]**. A proposed-only entry leaves
  such a whole-skill checkpoint valid until promotion. Once a skill has an
  accepted analysis, decisions are per trait (`record --whole-skill <kind>`
  may expand one verdict into one event per listed trait, all citing the
  report). Earlier adoptions stay retained (README §5b) whatever the later
  verdict. Adopting anything needs stages 1–2.
- **3.7 Promotion.** `check` validates every entry with `accepted` set,
  whether or not a checkpoint exists, and grandfathering ends for a skill
  once it has an accepted analysis. In the change that records the round, the entry's
  `accepted` pointer moves to the proposed sha and `proposed` is cleared (a
  hand edit; no tool writes the trait files). `check` then requires, for the
  accepted analysis: the checkpoint's sha and `tree_hash` equal it; every
  trait in its `added` or `changed` (every trait, for a first analysis) has
  an effective ruling recorded at that sha; every other listed trait has an
  effective ruling that is carried (3.8).
- **3.8 Carry-over.** A ruling recorded at an earlier analysis is *carried*
  to a later one when the trait is listed in both and is not in the later
  one's `added` or `changed` (rule 5: a kept, untouched ID is a kept
  meaning). Carrying never suppresses re-comparison, lifecycle events or
  reconsideration.
- **3.9 Membership** of any trait event resolves against the analysis at the
  event's source sha, which is never deleted. Carried rulings and pending
  completions keep their original sha.

### Stage 4: status (where everything stands)

- **4.1** `registry.py status <harness> [--skill X] [--traits]` is new.
  `gap` stays unchanged (all capability kinds, `--kind`, `--beads`).
- **4.2** Status is computed from the catalog, the trait files, the reports and
  the ledger; nothing stores it.
- **4.3** Each upstream trait T of skill S gets a **stage** against S's
  *newest* analysis N (proposed if any, else accepted) and, once decided, a
  **ruling** and a **provision**. The first matching row wins:

  | Stage | Computed when |
  |---|---|
  | removed upstream | T is in N's `removed`, or S left the catalog |
  | needs re-analysis | the catalog `tree_hash` differs from N's (skill-wide) |
  | decided | T has an effective ruling recorded at N, or carried to N (3.8) |
  | needs re-comparison | T's current row for N exists but is stale (2.6) |
  | reported | T's current row for N is fresh, in a passed report |
  | in review | T has a row for N only in a draft report |
  | analysed | T is listed in N, with no row for N |
  | not analysed | S has no analysis |

  A row is *for N* when its report's `to_sha` is N's sha; rows for earlier
  analyses are history. Ruling = the effective event kind. Provision (for
  adopts) = computed from retained adoptions, withdrawals, pending events
  and retirement replacements: *delivered*, *pending*, *withdrawn*, *no
  longer provided* (target dropped or retired without replacement). A
  skill's stage is its least advanced trait, by progress rank (separate
  from the precedence above): not analysed < needs re-analysis < analysed <
  in review < needs re-comparison < reported < decided < removed upstream;
  skill-wide drift and removal apply first. An analysis with no traits
  shows *analysed, no traits*; a whole-skill ruling and no accepted
  analysis shows *decided (whole skill)*, plus *analysed* if a proposed
  analysis exists.
- **4.4** Non-skill capabilities (agents, commands, hooks) show
  capability-level states: not reviewed, decided, changed since, removed.
- **4.5** The generated reference page per harness shows the same states.

## Files **[owner]**

```
harness_lifecycle/registry/
  skills.yaml                 our skills: placement and identity (new)
  trait-definitions.yaml      the vocabulary: one file, one namespace
  trait-sharing.yaml          why our skills share a trait (new)
  trait-policy.yaml           standing stances on traits, e.g. from the prompting guide (new)
  traits/
    ours.yaml                 our skills' trait lists, plus doc:AGENTS.md
    <harness>.yaml            one per reference harness: its entries and analyses
  reviews/                    reports: <date>-upstream-<harness>-<version>.yaml (+ generated .md)
  ledger/                     rounds (unchanged)
  skill-records/              generated only (new rule)
```

- Split by who changes the data: our skills change together; each reference
  harness is reviewed on its own, so two harness reviews never edit the same
  file. `traits.yaml` becomes the `traits/` folder.
- `traits/<harness>.yaml` holds only keys of that harness; `traits/ours.yaml`
  only `ours:` keys and the local `doc:` entries of rule 1.5 (`doc:AGENTS.md`,
  `doc:.repo-context/<file>`). A key appears in one file only.
- Upstream skills get no `skills.yaml` entry: their identity, paths and
  hashes are in `catalogs/<harness>.json`, their placement in each analysis.

## Skills file and generated records **[owner]**

```yaml
planning:                          # the .claude/skills/<name> folder
  domain: engineering
  stage: Design
  substage: Decomposition
  secondary: [Coordination]
  family: task-decomposition
  aliases: []
  status: active                   # active | retired
  boundary: null                   # optional: where it ends and neighbours begin
```

- One entry per real skill folder in `.claude/skills/`; aliases and legacy
  stubs get none (README §3 rule 5). `check` fails on a folder with no entry
  or an entry with no folder.
- `boundary` is required when two active skills share a domain · sub-stage
  (playbook §3 step 4), else optional.
- Skill records become fully generated by `build`: frontmatter from
  `skills.yaml`, the description from the skill's `SKILL.md`, `boundary`,
  then today's generated blocks. The hand-written Capability section is
  dropped: today it is a copy of the description. `check` fails when a
  record differs from what `build` would write.

## Entries: immutable analyses with two pointers

```yaml
"mattpocock_skills:skill:skills/engineering/tdd":
  accepted: "84fdeff"            # or null: nothing decided at trait level yet
  proposed: "5beb35b"            # or null: no undecided analysis
  analyses:
    "84fdeff":                   # immutable once written
      tree_hash: "…"
      placement: {…}
      traits: [red-green, …]
      added: {…}
      changed: {…}               # new
      removed: {…}
    "5beb35b":
      tree_hash: "…"
      …
```

- Analyses are never edited or deleted; `check` compares each against its
  recorded content hash (manifest) once a round has cited it.
- `accepted` and `proposed`, when set, name existing analyses and differ.
  Only the pointers move.
- A new skill has `accepted: null` until its first decision round.
- A checkpoint is trait-level when its skill has an accepted analysis or any
  trait ruling (replaces "has an entry"); a proposed-only entry changes
  nothing until promotion (3.6).
- Migration: today's 25 Pocock entries become one analysis each at
  `5beb35b`, with `accepted: null` and `proposed: "5beb35b"`; their
  grandfathered `84fdeff` checkpoints stay valid.

## Report file (stages 1–2)

`registry/reviews/<date>-upstream-<harness>-<version>.yaml`; `build`
generates the `.md` beside it.

- A report is a **draft** until `registry.py report seal` accepts it: both
  critic verdicts `pass`, every in-scope trait has one row (2.7), its
  `supersedes` resolve without cycles, and each skill with a `new` or
  `changed` row has its blind list, a mapping covering every blind line and
  a `pairing.purpose`. A draft never replaces anything. A **passed**
  (sealed) report is immutable (content hash in the manifest).
- A later pass writes a new report with `supersedes: [<path>, …]`.
- The **current row** for a trait and an analysis is the row in the passed
  report, for that analysis, that no other passed report supersedes. Two
  passed reports covering the same trait and analysis where neither
  supersedes the other is a `check` error.

```yaml
harness: mattpocock_skills
from_sha: "84fdeff"
to_sha: "5beb35b"
supersedes: null
analysis_critic: {by: "gpt-6.1-sol high", date: "2026-11-02", verdict: pass}
comparison_critic: {by: "gpt-6.1-sol high", date: "2026-11-03", verdict: pass}
themes: |
  Release themes, as prose.
skills:
  "skill:skills/engineering/tdd":
    upstream_tree_hash: "…"
    compared_with: test-driven-development        # or none
    pairing:
      overlap: {test-driven-development: 9, systematic-debugging: 3}   # computed
      placement_match: [test-driven-development]                     # computed
      suggested: test-driven-development                             # computed
      purpose_match: test-driven-development                         # judged
      purpose: "Both produce a test-first loop and fire on behaviour changes."
      flag: null                    # set, with a reason, when the picks differ
      reason: "…"
    analysis:
      blind: ["one line per mechanism", …]
      mapping:
        - {line: 1, to: [red-green], mark: match}
    traits:
      red-green:
        scope: new                  # new | changed | recompare | reconsider
        change: ["skills/engineering/tdd/SKILL.md:12"]   # upstream evidence
        fact: present               # scaffolded by the tool
        provider: test-driven-development
        candidates: []              # computed: our traits naming this one in distinct_from
        via: null                   # the selected candidate, for a variant
        also_in: {}                 # computed: {skill or doc: present | variant}
        ours: [".claude/skills/test-driven-development/SKILL.md:28"]
        recommendation: adopt
        delivery: delivered         # adopt rows: delivered | pending (2.5)
        target: null                # required for adopt when compared_with is none
        modification: null          # required for a variant adopt
        rewording: null             # required when guide.verdict is reword (2.9)
        revisit_when: null          # required for defer
        policy: null                # pre-filled from trait-policy.yaml
        guide: {verdict: ok, rules: []}   # required on adopt rows (2.9)
        reason: "One sentence."
```

- `registry.py report draft <harness> --skill <logical_id> --with <ours|none>`
  scaffolds the in-scope rows (2.6) with `scope`, `fact`, `provider`, `via`
  and `also_in` filled.
- **Where 2.4 lives:** the row's `ours` field; the decision cites the report.
- Older Markdown reviews stay as history.

## Trait policy (`registry/trait-policy.yaml`) **[owner]**

A standing decision about a mechanism, kept apart from its definition (which
stays neutral) and from any one skill:

```yaml
approval-pause-on-routine-step:
  stance: avoid                    # avoid | reword
  rules: {U-02: "3f9a1c0b7d2e", O-02: "a41e9d03c5b8"}   # GUIDE rule ID → digest reviewed
  why: "No approval pause on a routine step."
  decided: "2026-11-05"
  reviewed: "2026-11-05"           # last owner review of the stance against the rules
  ledger: 2026-11-05-pocock-5beb35b:042   # the decision that set it
  from: []                         # retired traits whose policy moved here
```

- Every live key is a defined, non-retired trait; `ledger` names an
  existing event. `rules` holds GUIDE rule IDs only; any other basis goes in
  `why`.
- `report draft` pre-fills `policy` on any row for that trait, from any
  harness.
- **Enforced when a decision is recorded, against the current policy.**
  `record` refuses an adopt of an `avoid` trait without `override` (3.5a).
  For a `reword` trait, the row's `guide.rules` must include the entry's
  rules: `ok` then means our wording already complies; `reword` needs
  `rewording` (3.4a). The new event stores the policy it was recorded
  under, `policy_basis: {stance, rules}` (new field; `null` when the trait
  had no entry).
- **History keeps its basis.** `check` validates each event against its own
  `policy_basis`, never the current file, so a later stance, rule
  replacement or re-review never invalidates a recorded, carried (3.8) or
  inherited decision. Lifecycle events (3.4, 3.4a) copy the pending event's
  `policy_basis` exactly, and `check` verifies the copy. An adoption made
  before a trait became `avoid` stays valid; the ours-side warning below is
  what cleans it out.
- One of our own skills listing an `avoid` trait warns in `check`: it is
  cleaned out by an ours-side `update`.
- **Retirement.** Retiring a definition that has an entry reconciles it in
  the same change. The retired entry stays as history and gains
  `reconciled: {<replacement>: carried | "<why not>"}` covering exactly its
  `replaced_by`. Each `carried` replacement has an entry naming the retired
  ID in `from`. When a replacement already has an entry with another
  stance, the owner rules one stance for it, with both origins in `from`.
  `check` fails on an unreconciled retired key. This applies only to
  retirement (a malformed definition). Upstream A→B (rule 5: a new
  mechanism) leaves A's entry on A, and B gets its own guide check.
- **Guide changes.** A rule's digest is the first 12 hex characters of the
  sha256 of its text after the ID, with citations stripped. `status` lists
  every entry whose stored digest differs from the current one, or whose
  rule is missing or retired, as *guide changed*; `check` warns on them.
  The stance holds until re-reviewed. The owner's re-review updates
  `rules`, `reviewed` and, if the stance changes, `ledger`; `status` prints the current digests. GUIDE rule IDs are
  stable: a rule is never renumbered, and a removed rule keeps its line as
  `- **U-02** Retired <date>; see <ID>.` (convention added to
  `prompting-guides/README.md`).

## Shared traits (`registry/trait-sharing.yaml`)

**[owner]** Trait definitions never name skills. Sharing is a separate file:

```yaml
glossary-format:
  skills: [domain-modeling, teach]
  why: "Both keep glossaries; one format serves both."
  reviewed: "2026-11-03"
```

`check` computes the shared set from `traits/ours.yaml` (a trait listed by two or
more of our active skills, `doc:AGENTS.md` included) and compares: a shared
trait with no entry warns; an entry whose `skills` differ from the computed
set errors. `TRAITS.md` gains a "Shared traits" section. This replaces the
overlap warning (`traits-design.md` §6). `glossary-format` and
`finding-adjudication` move to `core` in the sharing review.

## What `check` adds

1. Reports: strict schema; drafts vs passed; immutable once passed (content
   hash); the current-row rule and its ambiguity error; every in-scope trait
   has one row; `present`/`variant` rows have `ours`;
   `variant` rows have `via`; adopt rows with `compared_with: none` have
   `target`; defer rows have `revisit_when`.
2. Trait events: 3.2 for every event outside `pre_trait_rounds`.
3. Entries: analyses immutable, pointers valid (§Entries); `changed` keys
   defined and listed; promotion completeness (3.7); membership by sha (3.9);
   lifecycle inheritance (3.4).
4. Whole-skill mode only without an accepted analysis (3.6).
5. Every `doc:` entry's `tree_hash` current (AGENTS.md and the referenced
   documents).
6. `trait-sharing.yaml` against the computed shared set.
7. `skills.yaml`: strict schema; one entry per real skill folder; `boundary`
   where two active skills share a sub-stage; records equal `build` output.
8. `traits/`: each key in exactly one file, the file matching its source.
9. Reports: adopt rows carry `guide`; `pairing` holds the computed fields
   and a `flag` with a reason when the picks differ.
10. `trait-policy.yaml`: strict schema; live keys defined and not retired;
    retired keys reconciled; `ledger` exists; each event checked against its
    own `policy_basis` (an adopt under an `avoid` basis without `override`
    fails; lifecycle events copy the pending event's basis); our skills listing an `avoid`
    trait warn; entries with a changed, missing or retired rule warn.
11. Rewording: a new delivered adopt from a `reword` row fails; a pending
    adopt from one needs `rewording`; its completion carries
    `guide: {verdict: ok}` with the row's rules (3.4a).

## Code: the `curation` package **[owner: name]**

```
curation/
  scan/            stdlib-only: catalog.py, drift.py, models.py, cli.py
  registry/
    config.py      RegistryConfig; repo and data roots resolved from __file__
    models.py      Pydantic models only
    loaders.py     duplicate-key-safe YAML and JSONL → models
    ledger.py      rounds, effective rulings, adoptions, withdrawals
    traits.py      holders, facts, sharing
    reports.py     report model, draft, render
    checks/        ledger.py, traits.py, records.py, reports.py, sharing.py
    views/         index.py, references.py, traits_md.py, records.py (whole record)
    cli.py
  status.py
harness_lifecycle/scan.py               thin entry
harness_lifecycle/registry/registry.py  thin entry
tests/curation/
```

- **Entry contract.** Each thin entry puts the repo root (resolved from its
  own `__file__`) on `sys.path`, then calls the package CLI. The commands
  `python3 harness_lifecycle/scan.py …` (system Python, stdlib only) and
  `uv run python harness_lifecycle/registry/registry.py …` keep working with
  `PYTHONPATH` unset. `curation/__init__.py` and `curation/scan/` import no
  third-party package.
- Models do no I/O; loaders hold no business logic; checks return error
  lists and never print; only `cli.py` prints and sets exit codes.
- Out of scope **[owner]**: `workflow_interpreter/`, `workflows/`,
  `scripts/`. `main.py` (empty `uv init` stub) is deleted.
- Plugin boundary: the manifests exclude `harness-*` skills; that stays.

## Build order

1. This design → Sol review → owner approval.
2. **Freeze a baseline** before moving code: on a copy of the repo, record
   the outputs of `build` (every generated file's hash), `check`, `gap` for
   each harness, `ours`, and `scan.py catalog` / `drift` on a fixture
   harness.
3. **Extract only** into `curation/`: same model configs, same behaviour.
   Test bodies and assertions unchanged; only imports move. Parity: the
   baseline manifest matches; subprocess tests run both entry points with
   `PYTHONPATH` unset. Sol code review.
4. **Tighten parsing** as its own change (one strict base where models are
   coercive today), with tests for each behaviour change.
5. **Stages**, test first per rule: entries' analyses, pointers and `changed`;
   `doc:AGENTS.md`; report model, `report draft`, render, immutability;
   3.2 report validation; 3.3 record-time freshness; 3.4 lifecycle events;
   3.6 whole-skill mode; 3.7 promotion; `status`; `trait-sharing.yaml`;
   the `traits/` folder loader; `skills.yaml` and fully generated records;
   pairing signals (2.1); guide verdicts (2.9); rewording (3.4a);
   `trait-policy.yaml` with retirement reconciliation and rule digests
   (3.5a, §Trait policy).
   Sol code review.
6. **Docs and callers** (orchestrator): README §3 (records generated;
   placement, aliases and `boundary` in `skills.yaml`; descriptions in
   `SKILL.md`), §4a, §5, §5b and a report section; playbook §2, §3 and §7
   (edit `skills.yaml` and `SKILL.md`, then `build`; never a record) and §4
   (the guide check of 2.9 and trait policy); README §5b (the rewording
   exemption of 3.4a); `prompting-guides/README.md` (where the guide is
   used; stable rule IDs and the retired-rule line); the `harness-scan`, `harness-status` and
   `harness-evaluate` skills.
7. **Data**: `skills.yaml` from today's record frontmatter; `boundary`
   written (orchestrator) for every group of active skills sharing a
   domain · sub-stage (six groups today), empty elsewhere, since every
   Capability today copies the description; split
   `traits.yaml` into `traits/`; AGENTS.md traits; convert the 25 Pocock
   entries to one analysis each at `5beb35b` (`proposed`, nothing accepted);
   the two placements; `trait-sharing.yaml` for the shared traits (bead
   `cr-talb`, reframed as "justify or remove").
8. **Pocock redo** (`cr-axdt.4`): the report YAML for the 25 skills, using
   the current drafts as raw material minus their "covered elsewhere" and
   overlap-owner logic; critics; owner decisions; then the owner's question
   B (pending versus editing now); record, promote, seal, commit with the
   `5beb35b` pointer.

## Acceptance

1. Pin moves; a skill whose `tree_hash` is unchanged keeps its stage; a
   changed one shows *needs re-analysis*; an executable-bit-only change does
   not.
2. A new analysis set as `proposed` leaves `check` ok while the accepted
   checkpoint stands; promotion without a ruling at the new sha for a
   `changed` trait fails; an untouched trait carries its earlier ruling;
   a pending adopt from the earlier sha still completes after promotion.
3. A trait listed only by a non-compared skill computes `absent` with
   `also_in`; recording a delivered adopt from a row claiming `present` for
   it is refused.
4. A trait listed by `doc:AGENTS.md` computes `present` with that provider;
   its adopt targets `doc:AGENTS.md` without `retarget`; dropping it from
   AGENTS.md's list breaks retention.
5. A report missing an in-scope trait fails; editing a critic-passed report
   fails; a superseding report becomes current.
6. A trait event outside `pre_trait_rounds` with no report, a failed-critic
   report, a report at another sha, or a mismatched target without
   `retarget` fails, in flagged and unflagged rounds alike.
7. `record` refuses a stale row; a later `absent → present` delivery leaves
   `check` ok.
8. Completing and cancelling a pending adopt need no new row, pass `record`
   although the fact changed, and fail if their `report` or `source` differs
   from the pending event's; reopening a deferred trait without a
   `reconsider` row fails.
9. Whole-skill defer with no accepted analysis passes, and stays valid when
   a proposed analysis is added; with an accepted analysis it fails; earlier
   adoptions stay retained after a later whole-skill reject.
10. A→B carry-over, retirement replacements and grandfathered checkpoints
    behave as today.
11. `status` shows every stage of 4.3 (including *in review* and a carried
    *decided*) and every provision state on a fixture; a draft report never
    displaces a passed row; two unrelated passed reports on one trait fail;
    a variant with two candidates is one row with one `via`; a deferred trait is never *not analysed*; withdrawn and
    retired-without-replacement adoptions show their provision.
12. A shared trait with no `trait-sharing.yaml` entry warns; a mismatch
    fails.
13. Refactor parity: the baseline manifest matches, and both entry points
    run with `PYTHONPATH` unset.
14. A skill folder without a `skills.yaml` entry fails; a hand edit to a
    record fails until `build`; a missing `boundary` for two skills in one
    sub-stage fails.
15. A `traits/` key in the wrong file, or in two files, fails.
16. After step 7, the migrated data passes `check` and `build` is stable.
17. A `doc:.repo-context/…` trait shows in `also_in`, never as `present`;
    a `doc:AGENTS.md` trait shows as `present` for any compared skill.
18. `report draft` suggests the skill covering the most traits, with the
    overlap table; `also_in` marks variants elsewhere as `variant`.
19. A report whose purpose pick differs from the suggested skill without a
    `pairing.flag` fails; an adopt row without `guide` fails.
20. Adopting an `avoid` trait is refused by `record` and fails `check`
    without `override`; a `reword`-stance trait's adopt whose row omits the
    entry's rules is refused; `report draft` pre-fills `policy` for the
    same trait from another harness. Making an adopted trait `avoid`, or
    replacing a cited rule and re-reviewing the entry, leaves earlier,
    carried and completed decisions passing `check`.
21. Rewording: a new delivered adopt from a `reword` row is refused; a
    wording-only pending adopt on a trait the target lists passes `check`;
    its completion, citing the same `reword` row, is refused while the
    target's `tree_hash` is unchanged and accepted after the edit with
    `guide: {verdict: ok}` and the row's rules.
22. Retiring an `avoid` trait without reconciling its entry fails `check`;
    after reconciliation, adopting the replacement is refused without
    `override`; an upstream A→B change leaves B without A's stance.
23. Changing a cited rule's text in a GUIDE fixture shows the entry as
    *guide changed* in `status`; updating its digest clears it.

## Follow-up (not in this build)

- **Coverage view** (bead `cr-rgh6`): per domain · sub-stage, our skills,
  their unique and shared traits, pairwise overlap, and flags (merge
  candidate, thin skill, empty sub-stage with trait demand, upstream skill
  needing a new skill). Flags prompt a skill review (playbook §5);
  thresholds are settings, never rules.
- **`verification.md` clean-up** (bead `cr-k1b6`), then its trait list.

## Review round 1 dispositions (Sol high, REVISE)

| # | Finding | Disposition |
|---|---|---|
| 1 | Report enforcement bypassable | Accepted: 3.2 applies to every event outside `pre_trait_rounds`; validates harness, sha, row, critic, target |
| 2 | AGENTS.md presence vs delivery checks | Accepted: `provider` per row; AGENTS.md adopts target `doc:AGENTS.md`; `compared_with: none` requires `target` |
| 3 | Scope not computable | Accepted: `changed` field; `proposed` keeps the baseline; rows record `scope` |
| 4 | Fact labels don't prove freshness | Accepted in part: rows bind `provider` and `via`; freshness checked at record time (3.3). Not bound to text snapshots: 1.4 re-analyses our list whenever our skill changes, which is what re-confirms "present" |
| 5 | Historical reports become stale | Accepted: passed reports immutable, `supersedes`, current row; `check` validates structure, `record` validates freshness |
| 6 | Scope blocks lifecycle events | Accepted: 3.4 completion and cancellation; `reconsider` rows |
| 7 | Ruling and provision conflated | Accepted: 4.3 separates them; precedence and empty inventories defined |
| 8 | Whole-skill vs existing inventories | Accepted: 3.6 whole-skill mode only without an entry; earlier adoptions retained |
| 9 | Re-analysis invalidates the checkpoint | Accepted: `proposed` block; promotion in the decision change (3.7) |
| 10 | Review evidence unrepresented | Accepted: `analysis` section; `via`, `modification`, `change`, `revisit_when` |
| 11 | Entry points lack an import contract | Accepted: entry contract; subprocess parity with `PYTHONPATH` unset; scan stays stdlib-only |
| 12 | `gap` and callers | Accepted: `gap` unchanged; `status` is new; `harness-evaluate` added to callers; plugin boundary kept |
| 13 | Scan described as moving the pin | Accepted: 0.1 discovery read-only; pin moves are authorized steps |
| 14 | Refactor proof too weak | Accepted: baseline manifest, extract-only step, tightening separate, CLI parity, transition tests |
| 15 | Tree hash ≠ git diff | Accepted: 0.3 states the bytes-only condition; modes ignored by design |

Open questions, as answered: report as YAML with generated Markdown;
a kept ID keeps its ruling but never suppresses re-comparison, lifecycle
events or reconsideration; only the two named `pre_trait_rounds` are
exempt.

## Review round 2 dispositions (Sol high, REVISE)

| # | Finding | Disposition |
|---|---|---|
| 1 | Lifecycle reuse conflicts with freshness | Accepted: 3.4 completion and cancellation exempt from 3.3, inherit `report` and `source` exactly |
| 2 | Promotion doesn't enforce in-scope decisions | Accepted: 3.7 requires a ruling at the new sha for every `added`/`changed` trait; others must be carried |
| 3 | Promotion discards membership evidence | Accepted: analyses are immutable and keyed by sha; only the pointers move (3.9, §Entries) |
| 4 | Starting analysis invalidates a whole-skill ruling | Accepted: trait-level means an accepted analysis or trait rulings; proposed-only changes nothing (3.6) |
| 5 | Current row includes unfinished successors | Accepted: draft vs passed reports; current-row rule with explicit `supersedes`; *in review* stage |
| 6 | Carried rulings have no stage | Accepted: *decided* includes carried rulings (3.8); rows are *for* an analysis, others are history |
| 7 | Variant cardinalities conflict | Accepted: one row per trait; `candidates` computed, `via` selects one |

## Review round 3 dispositions (Sol high, REVISE)

| # | Finding | Disposition |
|---|---|---|
| 1 | Migration leaves required boundaries empty | Accepted: step 7 writes `boundary` for the six shared sub-stage groups; acceptance 16 |
| 2 | Callers still direct hand edits to records | Accepted: step 6 adds README §3 and playbook §2, §3, §7 |

## Review round 4 dispositions (Sol high, REVISE)

| # | Finding | Disposition |
|---|---|---|
| 1 | `ours.yaml` forbids `.repo-context` doc entries | Accepted: §Files allows the local `doc:` entries of 1.5 |
| 2 | A document could win pairing | Accepted: 2.1 pairs skills only; documents stay in the overlap table |
| 3 | 2.3 and 2.5 disagree on non-deliberate variants | Accepted: 2.5 recommends adopt with an edit; the fact stays `variant` |
| 4 | Schema example `also_in: []` | Accepted: `{}` with its value set |
| 5 | Referenced documents escape hash checks | Accepted: 1.4 and check item 5 cover every `doc:` entry |
| 6 | Freshness ignores `also_in` | Accepted: 2.6 and 3.3 compare `also_in` too; history stays valid |

## Review round 6 dispositions (Sol high, REVISE)

| # | Finding | Disposition |
|---|---|---|
| 1 | `reword` doesn't separate an outstanding edit from an applied one | Accepted: 2.9 judges the delivered wording; a delivered adopt needs `ok`; `reword` is always a pending adopt with `rewording`; 3.4a wording-only pending adopts, exempt from the "already lists" failure, completed only after the target's `tree_hash` moves |
| 2 | Policy bypassed by retirement | Accepted: retired keys must be reconciled to every `replaced_by` (`reconciled`, `from`); conflicting stances ruled by the owner; upstream A→B stays separate |
| 3 | Guide changes undetectable | Accepted: `rules` stores a per-rule digest; `status` shows *guide changed*; re-review updates digests and `reviewed`; stable rule IDs with a retired-rule line |

## Review round 7 dispositions (Sol high, REVISE)

| # | Finding | Disposition |
|---|---|---|
| 1 | Rewording completion cannot cite its inherited `reword` row | Accepted: 3.4a exempts the completion (a lifecycle event) from the delivered-row prohibition; it carries `guide: {verdict: ok}` with the row's rules and the reworded lines; 2.9, check 11 and acceptance 21 aligned |
| 2 | Current policy rules applied to history | Accepted: policy enforced at record time; each event stores `policy_basis`; `check` validates against it; lifecycle events copy it; acceptance 20 covers later stance and rule changes |

## Review round 8 (Sol high): APPROVE, no findings

## Code review of slices 2–6 (Sol high, REVISE, 14 findings, all accepted)

Rules clarified above: 2.9 (delivered adopt needs `ok`), 3.4 (explicit
supersession of the effective pending adopt; same target and trait), 3.5
(`revisit_when` on events), 3.6 (no skill-level adopt outside
`pre_trait_rounds` without stages 1–2), 3.7 (every accepted entry checked;
grandfathering ends at promotion), 4.3 (progress rank), §Report file (seal
requirements). Code-only fixes: analysis digests never overwritten; `doc:`
retention needs the document's inventory; a missing skills folder fails;
`current_row` uses the full supersession closure; an empty git listing
hashes as empty.
