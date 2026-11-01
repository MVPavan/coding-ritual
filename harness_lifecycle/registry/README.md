# Registry

The registry records every skill we own and every capability we have looked at
in a reference harness: what each one does, where it sits in the lifecycle,
what it was built from, and every decision and change, with reasons. It
replaces `../ledger.json`, `../aliases.json`, `../gap.py`, `../export_csv.py`,
`inventory/` CSVs and `casebook/casebook.py` (all in git history).

It lives under `harness_lifecycle/`, so it is never shipped to adopted repos.

## 1. Layout

```text
registry/
├── README.md                      # this method
├── registry.py                    # thin entry for the tool (§6); the code is in curation/
├── skills.yaml                    # our skills: placement, family, aliases, status, boundary (§3)
├── trait-definitions.yaml         # the trait vocabulary (§4a)
├── traits/
│   ├── ours.yaml                  # our skills' trait lists, plus doc: entries (§4a)
│   └── <harness>.yaml             # one per reference harness: entries and analyses (§4a)
├── trait-sharing.yaml             # why our skills share a trait (§4a)
├── trait-policy.yaml              # standing stances on traits (§4a)
├── ledger/
│   ├── <yyyy-mm-dd>-<slug>.jsonl  # one file per round (§5)
│   └── MANIFEST.json              # sha256 of sealed rounds, sealed reports and cited analyses
├── reviews/                       # evidence behind rulings (§5a)
├── skill-records/<domain>/<skill>.md   # generated: one per skill (§3)
├── references/<harness>.md        # generated: their capabilities, stage and our ruling (§4)
├── TRAITS.md                      # generated: every skill's traits, every trait's holders, shared traits
├── STEPS.md                       # generated: every playbook's steps, and where traits and calls recur (§4b)
└── INDEX.md                       # generated: domain → stage → sub-stage
```

The skills themselves stay in `.claude/skills/`, the only source. Records are
generated from `skills.yaml` and each skill's description; they never copy
the skill body.

## 2. Coordinates

Every skill has one primary home: **domain · stage · sub-stage**.

- **Domain**: the kind of outcome the skill produces.
  - `core`: works in any domain (orchestration, continuity, tracking,
    communication, tutoring, web research, writing for agents).
  - `engineering`: software work.
  - New domains (`design`, `marketing`, `sales`, `media`, …) are added when
    their first skill arrives. A domain is also the natural plugin boundary.
- **Stage**: one of the shared backbone in `../adlc/GUIDE.md` §1: Discovery,
  Intake, Design, Building, Verification, Delivery, Operations, Improvement,
  plus X Crosscutting and U Utilities.
- **Sub-stage**: defined per domain in the ADLC guide. Engineering uses the
  existing table; a new domain adds its own sub-stages when its first skill
  arrives.

Rules:

1. **One primary home.** A skill that serves every stage belongs to X
   Crosscutting or U Utilities; it does not span stages.
2. **Secondary tags** record partial fit for search; they never decide
   ownership.
3. **Two active skills in one domain · sub-stage** must each state their
   `boundary` in `skills.yaml`, or they are merge candidates. `check` fails
   without it; `INDEX.md` flags them.
4. **Split by method, not by domain.** When the method is the same across
   domains, keep one `core` skill with a reference file per domain; when the
   method differs, use a domain skill.
5. **Aliases and legacy stubs** get no record. They are listed in their
   target's `aliases`. A stub with no target is listed in `INDEX.md` under
   "stubs".

The 14 buckets of `../archive/inventory/skill-buckets.md` are frozen history. They map
onto coordinates as follows:

| Old bucket | Coordinate |
|---|---|
| 1 Discovery, requirements and decisions | Intake · Clarification; Design · Specification |
| 2 Planning · 3 Architecture | Design · Decomposition, Architecture |
| 4 Implementation · 6 Debugging | Building · Implementation, Diagnosis |
| 5 Testing · 7 Review | Verification · Testing, Review |
| 8 Version control · 9 Release, operations | Delivery · Integration, Release; Operations |
| 10 Orchestration, handoff | X · Coordination, Continuity |
| 11 Harness authoring | Improvement · Codification |
| 12 Tooling, guardrails | X · Governance; U · Tooling |
| 13 Research, documentation · 14 Learning, content | Discovery · Research; X · Communication; U · Tutoring |

## 3. Skills file and skill records

`skills.yaml` has one entry per real skill folder in `.claude/skills/`
(aliases and legacy stubs get none, rule 5):

```yaml
planning:                       # the .claude/skills/<name> folder
  domain: engineering
  stage: Design
  substage: Decomposition
  secondary: [Coordination]
  family: task-decomposition    # capability family shared with reference skills
  aliases: []                   # alias and stub entrypoints that route here
  status: active                # active | retired
  boundary: null                # where it ends and its neighbours begin (rule 3)
```

`build` writes each `skill-records/<domain>/<skill>.md` whole: the frontmatter
from `skills.yaml`, the title, the description from the skill's `SKILL.md`,
the boundary, then these generated blocks:

| Block | Holds |
|---|---|
| `traits` | the skill's traits from `traits/ours.yaml`, with their definitions |
| `lineage` | each part, and the harness, path and commit it came from, from adopt and adopt-merged records |
| `history` | every ledger record about this skill, newest first |
| `reviews` | every review a ledger record about this skill cites |
| `sources` | per trait, the upstream traits adopted into it; withdrawn, retired and replaced-upstream adoptions stay, labelled |
| `declined` | upstream traits considered for this skill and rejected or deferred, with why |

Never edit a record. Change `skills.yaml` or the skill's `SKILL.md`, then
`build`. `check` fails on a skill folder without an entry, an entry without a
folder, or a record that differs from what `build` writes. What the skill
does, trait by trait, lives in `traits/ours.yaml` (§4a).

## 4. Reference pages

`references/<harness>.md` is generated from the harness catalog
(`../catalogs/<harness>.json`), the trait files, the reports and the ledger.
One row per capability the harness ships:

| Their capability | Status | Stage | Into ours | Traits | Last ruled at | Changed upstream since? |
|---|---|---|---|---|---|---|

A capability's kind is `skill`, `playbook`, `agent`, `command`, `rule`, `hook`,
`mcp` or `plugin`. A `playbook` is each `*.md` directly in an upstream skill's
`playbooks/` folder, with logical ID `playbook:<skill folder>/playbooks/<name>`;
its `content_hash` covers the file, its `tree_hash` the file and its
`playbooks/<name>/` folder. Our own playbooks are not cataloged: they are ledger
subjects (§4b).

`scan.py catalog` scans a sparse reference checkout from a full `git archive`
export of its HEAD, not its working tree. A scan of the partial tree would look
complete and carry the right commit, so it could replace the baseline unnoticed.

Status is the effective ruling, or `present, unruled` (we have a same-named
capability but never ruled), or `not reviewed`. Stage is the skill's stage
from `registry.py status` (§5c); other capabilities show not reviewed,
decided, changed since or removed. `Traits` counts each skill's effective
trait rulings (`3 adopt · 1 reject`, removed traits excluded). Capabilities
removed upstream are listed with their last ruling.

## 4a. Traits

A **trait** is one distinct gate, rule, method, template, artifact or output
quality that a skill gives the agent. Every skill, ours or upstream, is
described as a list of traits drawn from one shared vocabulary, so "which
skills have X" and "what have we declined" are lookups. Rulings stay in the
ledger; the trait files only describe.

**`trait-definitions.yaml`**, the vocabulary:

```yaml
seam-selection:
  definition: Choose the smallest boundary that exercises the real contract.
  placement: {domain: engineering, stage: Design, substage: Specification}
  secondary: [Implementation]
independent-expectations:
  definition: Expected values are derived independently, never copied from the code under test.
  placement: {domain: engineering, stage: Building, substage: Implementation}
  distinct_from: [good-test]
  note: Split from good-test; the two are ruled separately upstream.
```

| Field | Required | Meaning |
|---|---|---|
| `definition` | yes | one sentence, in our words (rule 4) |
| `placement` | yes | where the trait usually sits (§2 coordinates); may differ from the skill's home |
| `secondary` | no | other sub-stages it often serves |
| `distinct_from`, `note` | no | near traits it must not be confused with, and how it differs (`note` required with `distinct_from`) |
| `retired` | no | `{date, replaced_by: [ids]}`, only for a malformed definition (a bundle to split, a duplicate to merge) |

A definition no skill lists is valid: it records a trait we declined.

**`traits/`**, who has what. `traits/ours.yaml` holds our skills and the
`doc:` entries; `traits/<harness>.yaml` holds that harness's skills. A key
appears in one file only.

```yaml
# traits/ours.yaml
ours:test-driven-development:
  tree_hash: "efbff4…"
  traits: [mode-selection, good-test, independent-expectations, seam-selection]
doc:AGENTS.md:
  tree_hash: "91c0d2…"
  traits: [applicable-checks-before-done]

# traits/mattpocock_skills.yaml
mattpocock_skills:skill:skills/engineering/tdd:
  accepted: "84fdeff"          # the analysis the decisions describe, or null
  proposed: "5beb35b"          # a newer analysis not yet decided, or null
  analyses:
    "84fdeff": {…}             # never edited once a sealed round cites it
    "5beb35b":
      tree_hash: "e3e0f7…"
      placement: {domain: engineering, stage: Design, substage: Specification}
      traits: [good-test, seam-selection, public-only-seams, seam-preconfirmation]
      added: {seam-preconfirmation: "5beb35b"}
      changed: {seam-selection: "5beb35b"}
      removed: {}
      notes: {seam-preconfirmation: a live human confirmation, not a plan field}
```

| Field | Where | Meaning |
|---|---|---|
| key | both | `ours:<skill>`, `doc:AGENTS.md`, `doc:.repo-context/<file>`, or the catalog id `<repo>:<logical_id>`. A playbook is a holder too (§4b), but never a key here |
| `tree_hash` | ours entries, each analysis | sha256 over the folder's files that git does not ignore (one file for `doc:`); for ours, `check` fails when it is stale |
| `accepted`, `proposed` | upstream | analysis shas; at least one set; they differ. Only the pointers move |
| `analyses` | upstream | one immutable trait list per sha |
| `placement` | analysis | where the upstream skill sits (ours: `skills.yaml`) |
| `traits` | both | trait IDs; defined, no repeats |
| `added`, `changed`, `removed` | analysis | `{trait: sha}`: new upstream, changed with the same meaning, dropped upstream |
| `notes` | both | `{trait: text}`: nuance the shared definition omits |

**What makes a trait present.** Only the compared skill, or `doc:AGENTS.md`
(always in context), makes an upstream trait present (§5c). Documents
AGENTS.md references load on demand, so their `doc:.repo-context/<file>`
entries only show where else a trait lives. A trait listed by any other skill
of ours is information, never coverage.

All trait files are read with strict parsing: a duplicate key, an unknown
field or a value of the wrong type (YAML reads `no` as false and an all-digit
sha as a number) fails `check`. Quote shas and hashes. No tool writes these
files, so comments are safe. An upstream entry is created when the skill is
first analysed (§5c). Agents, commands, hooks, upstream playbooks and other
kinds keep one ruling per capability, with no analysis and no report row.

**Rules for traits.**

1. One trait is one mechanism. Parts that could be ruled or adopted
   differently are separate traits.
2. Exclusive. No two traits of one skill cover the same mechanism, and no two
   definitions describe the same mechanism. A looser or stricter variant is
   its own trait with `distinct_from` and `note`.
3. Exhaustive. A skill's list covers every material mechanism in its whole
   folder. Not traits: restated `AGENTS.md` policy; wording that adds no
   mechanism; routing (the skill's activation trigger, or a bare "hand this
   to skill X"). A gate the agent applies during the work is a trait.
4. A definition is one sentence in our words. It names no reference harness,
   and names a tool only when the mechanism is specific to that tool.
5. A definition's meaning never changes. Wording fixes are edits; a new
   meaning is a new ID, and the old ID stays live for whoever still has that
   mechanism.
6. IDs are kebab case and name the mechanism, never the skill
   (`seam-selection`, not `tdd-seams`).

**Extract blind, then map** (the procedure is in `../playbook.md` §4): the
agent listing a skill's traits reads only the skill folder, never these two
files; a separate pass maps each extracted trait to an existing ID (same
mechanism), splits it (partial match) or defines a new one. The review keeps
both lists, so a critic can see nothing was forced.

**Retirement.** A retired definition is never deleted and always resolves,
so old events stay valid. A new subject may not use it; a ruling continuing
an existing subject may. While a skill still lists it, `check` warns. An
adoption into it is satisfied while the holder lists it or every
`replaced_by` trait.

**Shared traits** (`trait-sharing.yaml`). Two of our active skills (or a
skill and `doc:AGENTS.md`) may list the same trait, but the sharing is noted
and justified, never written into the definition:

```yaml
glossary-format:
  skills: [domain-modeling, teach]
  why: "Both keep glossaries; one format serves both."
  reviewed: "2026-11-03"
```

`check` computes the shared set: a shared trait without an entry warns, an
entry whose `skills` differ from the computed set fails. `TRAITS.md` lists
them.

**Trait policy** (`trait-policy.yaml`). A standing stance on a mechanism,
usually from the prompting guide (`../prompting-guides/GUIDE.md`), kept apart
from the definition and from any one skill:

```yaml
approval-pause-on-routine-step:
  stance: avoid                    # avoid | reword
  rules: {U-02: "3f9a1c0b7d2e"}    # GUIDE rule ID → digest of the text reviewed
  why: "No approval pause on a routine step."
  decided: "2026-11-05"
  reviewed: "2026-11-05"
  ledger: 2026-11-05-pocock-5beb35b:042   # the decision that set it
  from: []                         # retired traits whose policy moved here
```

- Recording an adopt of an `avoid` trait needs `override: "<reason>"`; a
  `reword` trait's adopt needs a report row whose guide check cites the
  entry's rules. Each new event stores the policy it was recorded under
  (`policy_basis`) and is checked against that, never the current file.
- One of our skills listing an `avoid` trait warns, until an ours-side
  `update` removes it.
- Retiring a definition that has an entry reconciles it in the same change
  (`reconciled: {<replacement>: carried | "<why not>"}`, and `from` on each
  carried replacement).
- A rule's digest is the first 12 hex characters of the sha256 of its text
  (citations stripped). When GUIDE.md changes, `status` shows the entry as
  *guide changed* until the owner re-reviews it and updates `rules`; the
  stance holds meanwhile.

## 4b. Playbooks and steps

A **playbook** (`.repo-context/unit-kinds.md` §3) is a file directly in
`.claude/skills/mvp-mode/playbooks/`; files in its subfolders are its
references, never playbooks. Its frontmatter is the one source of its
trigger, its own traits and its ordered steps (St2):

```yaml
---
trigger: A reported defect, failing check or flaky test to fix with proof.
traits: [confirmed-cause-gate]          # gates and ordering rules (T3)
steps:                                  # excerpt: one of seven
  - id: bug-fix#3                       # <playbook>#<position>
    when: the cause is confirmed        # the whole step's condition
    actions: [{trait: report-missing-proof}]
    calls:
      - {to: "skill:test-driven-development", when: a regression check is feasible}
    loads: [{path: bug-fix/timing-flakes.md, when: the cause is a timing flake}]
---
```

| Field | Required | Meaning |
|---|---|---|
| `trigger` | yes | the kind of request the playbook serves |
| `traits` | no | the playbook's own gates and ordering rules |
| `steps` | yes | ordered; at least one |
| `id` | yes | `<playbook>#<n>`, `n` its position from 1 (St1) |
| `when` | yes | when the step runs or is skipped |
| `actions` | no | own actions, each `{trait}` (T3) |
| `calls` | no | `{to, needs, when}`: `to` is `skill:<name>` or `playbook:<name>`; `needs` the callee traits the step relies on (absent: all); `when` a condition on this call only |
| `loads` | no | `{path, when}`: a reference, by path relative to the playbook file; a load is not a call (St1) |

A step has at least one action, call or load. Two format points are decided:

1. **The step list lives in the frontmatter**, machine-read, with the body
   saying the same in prose; nothing else lists steps (St2).
2. **Calls name units by kind and name** (`skill:`, `playbook:`), as the
   router does. A reference is a load by path relative to its playbook, so
   the installed text never depends on the repository layout. The registry
   identifies files by repository path (`doc:<path>`): the playbook as a
   trait holder, and each load in `STEPS.md`.

Parsing is strict: an unknown field, a wrong type or a duplicate key fails,
as for the trait files (§4a). `check` also fails when a step's ID is not its
position, a trait (playbook, action or a call's `needs`) is undefined or
listed twice in one list, a call names no skill folder or playbook, or a load
is not a file under the calling playbook's own folder `playbooks/<name>/`
(F3). So a reference has one owner (F1); a second consumer promotes it (F2).

**A playbook holds traits** (T1, T3): its own `traits` and its steps'
`actions`, never a callee's. Its holder key is `doc:<its path>`, the same
key a ledger adopt into it targets; that list comes from the frontmatter, so
a `traits/ours.yaml` entry for a playbook fails `check`. A skill's `tree_hash`
leaves out what its playbooks own, ours and upstream alike: each direct `*.md` in
`playbooks/`, and `playbooks/<name>/` beside a `playbooks/<name>.md`. Any other
file there stays in the skill's hash and assets, so its edit shows on the skill;
an upstream playbook edit shows in `gap` through that playbook's own catalog
entry (§4).
A playbook's own hash covers its file and its `playbooks/<name>/` folder, so a
reference edit counts, and is stored on its latest ledger event (below); its
lists are read live, so its changes show in `steps diff` and in `TRAITS.md` and
`STEPS.md`, which `check` keeps current. Playbooks appear in
`TRAITS.md` and in the shared-traits set beside our skills and `AGENTS.md`,
and in a report row's `also_in` like any other holder.

**A playbook is its own ledger subject.** A change to one is recorded on it,
not on the router: `subject` and `skill` are both `doc:<playbook path>`, the
kind is `add` or `update`, and `record` fills `target_tree_hash`. An `update`'s
`why` summarises `steps diff` (St3). An `update` on `ours:mvp-mode` is for the
router's own text.

- `record` refuses a subject that is not a file directly in the playbooks
  folder (`doc:AGENTS.md`, a reference, a missing file), an event whose hash
  equals the playbook's effective event (nothing changed), and a supplied
  `target_tree_hash` that is not today's. An event with `supersedes` is a
  correction and skips the nothing-changed refusal; `record` still computes its
  hash and `check` still verifies it.
- `check` reads each playbook's effective event, so sealed events are never
  rewritten. It fails when a `doc:` `add` or `update` names no playbook path
  or has no `target_tree_hash`; when a playbook file has no event, or its hash
  differs from its event's (the remedy: `record` an `update`); and when an
  event names a playbook file that no longer exists.
- `withdraws` on such an `update` removes a trait adopted into that playbook,
  per destination (§5b).
- `2026-10-31-mvp-mode:009`, `:010` and
  `2026-11-01-cursor_plugins-pstack-principles:224` predate this rule: they
  record playbook changes as `update` on `ours:mvp-mode` and stay as sealed.

**Limit.** Removing or renaming a playbook has no event: every kind but `add`
and `update` is invalid on a `doc:` subject, whatever its `source`, so `check`
fails until the file is back. Add `retire` when the first playbook is removed.

**The step index** (`STEPS.md`, St2), generated by `build`: every playbook's
steps with their condition, traits, calls and loads, then the traits and
calls two or more playbooks use. The same own action in two playbooks is the
signal to make it a skill (St4). `check` fails when the index is stale.

**Step changes** (St3): `steps diff <playbook> [<base>] [<head>]` lists the
changes between two git revisions (default: `HEAD` against the working
tree). Steps pair one to one by what they do, not by number, so
renumbering after an insertion is no change: identical steps (the same
action traits, calls and loads) first, preferring the same condition, then
the nearest position; then the rest by most shared action traits, calls and
loads, then the same condition, then the nearest position. Two steps that do
the same thing under the same condition are told apart only by position, and
a split shows as one changed step plus an added one (a merge: one changed,
one removed); no split is inferred. Order is the longest
subsequence of paired steps kept in order, ties keeping earlier positions;
paired steps outside it are `moved`. Each pair reports `condition`,
`traits`, `calls` and `loads` changes; unpaired steps are `added` or
`removed`; the playbook's `trigger` and own traits are reported too. A
wording edit outside these fields is no change.

## 5. Ledger

The ledger follows `.repo-context/coding-style.md` §Ledgers: JSON Lines, one
file per round, append only, sealed when complete.

**First line of every round file: the round header.**

```json
{"type": "round", "round_id": "2026-10-14-agent-skills-0.6.13", "date": "2026-10-14", "scope": "…", "pins": {"agent-skills": "aeac41d"}, "method": "…", "evidence": ["upstream-reviews/…"], "excluded": [{"rule": "…", "why": "…", "count": 0}], "carried_debts": ["…"]}
```

An upstream review round sets `"trait_level": true` (§5b); every round outside
`pre_trait_rounds` follows the trait rules whatever its flag.

**Every other line: one event.**

| Field | Required | Meaning |
|---|---|---|
| `type` | yes | `"event"` |
| `id` | yes | unique across the ledger: `<round_id>:<n>` |
| `date` | yes | ISO 8601 |
| `kind` | yes | see below |
| `subject` | yes | `ours:<skill>`, `doc:<playbook path>` (§4b), `<repo>:<logical_id>`, or a trait: `<repo>:<logical_id>#<trait id>` |
| `why` | yes | the reason; never empty |
| `evidence` | yes | list of `path:line`, URLs, comparison folders, commits |
| `skill` | for our skills and adoptions | our target: a skill folder name, `<kind>:<name>` for a non-skill capability (`agent:code-reviewer`), or `doc:<repo-relative path>` for a method document. On a playbook event, the same string as `subject`. On a trait `reject` or `defer`, optional: the skill it was considered for |
| `source` | for reference rulings | `{repo, logical_id, path, sha, content_hash, tree_hash}`; `record` fills the hashes from the catalog |
| `adaptation` | for `adopt-merged` | `{merged_from: [], modifications: [], deliberately_dropped: []}`. Outside trait-level rounds, fill it; never leave the parts only in `why` |
| `into`, `modification` | trait `adopt`, optional | `into`: a different trait our skill provides instead (a modified adoption; that trait names the upstream one in `distinct_from`, and `modification` is required). Absent: the same trait ID |
| `pending` | trait `adopt`, optional | the bead for the edit that will deliver it (§5b) |
| `carried_from` | optional, trait events | earlier trait subjects whose ruling this restates, when upstream moved the skill or replaced a trait |
| `report` | trait events outside `pre_trait_rounds` | the sealed report (`reviews/<file>.yaml`) whose row the decision follows (§5b) |
| `retarget` | optional, trait events | why `skill` differs from the row's provider, compared skill or target |
| `revisit_when` | every `defer` outside `pre_trait_rounds` | what would bring it back |
| `rewording`, `target_tree_hash` | trait `adopt`, optional | a wording edit still to make, and the target's hash when it was recorded (§5b) |
| `target_tree_hash` | playbook `add` or `update` | the playbook's hash at this event; `record` fills it (§4b) |
| `guide` | completion of a rewording | `{verdict: ok, rules}`: the delivered wording passes the guide check |
| `override` | trait `adopt`, optional | why an `avoid` trait is adopted anyway (§4a) |
| `policy_basis` | trait events | the trait-policy stance and rule digests when recorded (`record` fills it) |
| `withdraws` | optional, ours-side `update` | upstream trait subjects adopted into this skill or playbook that it no longer provides |
| `family`, `relation` | optional | capability family; `substitutes`, `complements`, `pipeline`, `genus` or `singleton` |
| `commit`, `bead` | optional | the change's commit and tracker ID |
| `supersedes` | optional | list of event IDs this replaces |

**Kinds.**

| On a reference capability | On our skill |
|---|---|
| `adopt`: taken as a whole into `skill` | `add`: new skill |
| `adopt-merged`: parts merged into `skill` (with `adaptation`) | `update`: changed for our own reasons |
| `reject`: not taken, on merit | `merge`: folded into another skill (`skill` = the survivor) |
| `defer`: not now | `split`: divided (`evidence` names the new skills) |
| `out-of-scope`: not our kind of work; never a candidate | `rename`: new name (old name in `why`) |
| | `retire`: removed or reduced to a stub |

"Our skill" includes a playbook for `add` and `update` only (§4b).

The effective ruling on a subject is its latest event not superseded.
"Superseded" is computed, never recorded. Every reference ruling records the
`content_hash` at the time, whatever its kind, so `gap` notices when a
rejected or deferred capability changes upstream.

`skill` is required on an effective `adopt`/`adopt-merged` ruling (it must name
an existing skill record, alias, stub, non-skill `kind:name` or existing
`doc:` file, resolved through our `rename` and `merge` events), and optional on
a superseded historical one, which may name a skill we no longer have. A
pending trait adopt (§5b) may name a skill its delivering build will create,
and so may that upstream skill's checkpoint; its completion needs the skill.

## 5b. Trait rulings

Upstream skills are ruled trait by trait; the ledger stays the only source of
status, and the trait files only describe. The stages that lead to a ruling
are in §5c.

- **Trait events** have a trait subject (`<repo>:<logical_id>#<trait id>`)
  and kind `adopt`, `reject`, `defer` or `out-of-scope`. The trait must be
  listed in the analysis at the event's source sha. An `adopt` names `skill`
  (a skill or `doc:<path>`); the target must list the trait, or `into`,
  unless the adopt is pending.
- **Every decision cites a report.** Outside `pre_trait_rounds`, a trait
  event carries `report`: a sealed report for the same harness whose `to_sha`
  is the event's source sha and which has a row for the trait. Its `skill` is
  the row's provider, the compared skill or the row's target, or the event
  says why in `retarget`.
- **Checked when recorded.** `record` refuses a decision whose row no longer
  matches today's facts (fact, provider, candidates, `via`, `also_in`), a new
  delivered adopt whose row's guide verdict is not `ok` (or a `conflict` with
  an owner override, §5c), a new pending adopt from a row without a guide
  verdict or (unless either of those) without `rewording`, and the
  trait-policy refusals (§4a). `check` validates structure only, so
  a later change never invalidates history.
- **Defer** needs `revisit_when`; it never counts as adopted or rejected.
- **Reconsideration.** A new decision that supersedes an effective decision
  at the same sha cites a row with scope `reconsider`.
- **Checkpoint.** Each reviewed skill also gets a capability-level event at the
  reviewed pin, carrying the hashes `gap` compares. Its kind must agree with
  its effective trait rulings (removed traits excluded):

  | Trait rulings | Checkpoint kind |
  |---|---|
  | all `adopt` | `adopt` |
  | some `adopt` | `adopt-merged` |
  | none `adopt`, all one kind | that kind |
  | none `adopt`, mixed | `reject` |

  Its `skill` must be one of the traits' targets; views list every target.
  Every effective trait ruling needs an effective checkpoint on its skill.
- **Whole-skill rulings.** A skill with no accepted analysis may be ruled as
  a whole: `defer`, `reject` or `out-of-scope`, with no trait events. Outside
  `pre_trait_rounds`, a skill-level `adopt` or `adopt-merged` always needs an
  accepted analysis and its trait rulings. Once a skill has an accepted
  analysis, `record --whole-skill <kind>` writes one event per listed trait.
  Earlier adoptions stay retained whatever the later verdict.
- **Promotion.** In the change that records the round, move the entry's
  `accepted` pointer to the proposed sha and clear `proposed` (a hand edit).
  For every entry with `accepted` set, `check` requires an effective
  checkpoint at that sha and `tree_hash`; a ruling recorded at that sha for
  every trait in its `added` or `changed` (every trait, for a first
  analysis); and a carried ruling for every other trait. A ruling is
  *carried* to a later analysis when the trait is listed in both and is not
  in the later one's `added` or `changed`. A proposed analysis changes
  nothing until promotion. Superseded checkpoints are never re-checked.
- **Analyses are immutable once cited.** `round seal` records the hash of
  every analysis its trait events cite; `check` fails when one changes.
- **Awaiting trait ruling.** The rounds sealed before traits existed are
  listed in the config (`pre_trait_rounds`, closed). Their checkpoints, for a
  subject with an upstream entry, no accepted analysis and no trait rulings,
  are grandfathered: `gap` lists them as awaiting a trait ruling and `check`
  does not fail.
- **Pending adoptions.** A gap (we will add it) is an `adopt` with `pending:
  <bead>`. It is intent, not delivery: the target need not list the trait
  yet, nor exist yet when it is a skill to create (§5), and it never counts
  as a delivered adoption or clears a withdrawal. `check` fails when the
  target already lists the trait but the completing `adopt` is missing.
  - **Complete** it with an `adopt` without `pending` that supersedes the
    effective pending adopt, with the same `skill` and `into`; **cancel** it
    with a `reject` or `defer` that supersedes it, with a reason. Both
    inherit the pending event's `report`, `source` and `policy_basis`
    exactly and need no new row; `record --supersedes <id>` fills them.
    Anything else is a new decision.
  - **Rewording.** When the guide check asks for a wording change, the adopt
    is pending with `rewording`, even when the target already lists the
    trait; `record` stores the target's `target_tree_hash`. Its completion
    carries `guide: {verdict: ok, rules}` and the reworded lines in
    `evidence`, and is refused while the target's hash is unchanged.
- **Re-review.** Add the new analysis to the entry at the new sha as
  `proposed`, report and rule only its `added` and `changed` traits (§5c),
  record a new checkpoint at the new pin, then promote.
- **Upstream replaces trait A with B** (a different mechanism): move A to
  `removed`, list B, and give B's ruling `carried_from: [<subject>#A]`. A
  keeps its ruling, and our skill keeps A; the `sources` block shows
  "upstream replaced it with B".
- **Adopted, then a changed version declined** (same trait, re-ruled): the
  effective ruling describes upstream's current version; our skill keeps
  what it adopted. The `sources` block shows the last delivered adoption,
  labelled with the current ruling. Only an ours-side `update` with
  `withdraws` removes it, and a later delivered `adopt`, in ledger order,
  makes it live again. This holds even when a later event supersedes the
  `adopt`: the skill must keep the trait listed until it is withdrawn.
  Withdrawal is per source: withdrawing one upstream subject never forces
  removing a trait another adoption still needs. An adoption into a `doc:`
  target needs that document to list the trait: `AGENTS.md` and a
  `.repo-context/<file>` through their `traits/ours.yaml` entry, a playbook
  through its frontmatter, never an entry (§4b). Of these only a playbook has
  an `update`, so only it can withdraw one; `AGENTS.md` and a
  `.repo-context/<file>` keep what they adopted.
- **Corrections.** Superseded events never operate: a superseded `merge`,
  `retire` or withdrawing `update` has no effect on current checks, though
  the history block still shows it. After a `merge`, adoptions into the
  merged skill resolve to the survivor, which must list the trait.

**Change detection** (`gap`), per ruled capability, first that applies:

1. the event has `tree_hash`: compare with the catalog (a skill's tree hash
   covers every file in its folder that git does not ignore, as raw bytes,
   except what its playbooks own, §4b);
2. it has `sha`: `git diff` of the folder from that commit to the pin;
3. neither: from the pin in the event's own round header, labelled
   "baseline inferred from round pin";
4. otherwise: "baseline unknown, review".

## 5a. Reviews

A review is the evidence behind one or more rulings, in `reviews/`:

| Type | File | Covers |
|---|---|---|
| `upstream` | `<yyyy-mm-dd>-upstream-<harness>-<version>.yaml` (the report, §5c), with a generated `.md` beside it | Per upstream skill: the analysis evidence, the pairing, one row per in-scope trait with its facts and recommendation |
| `skill` | `<yyyy-mm-dd>-skill-<our skill>.md` | Deciding a merge, upgrade or rebuild of one of our skills: a component matrix against its upstream counterparts with `file:line` citations, the stronger mechanism per row, and a verdict |

A report is a draft until `registry.py report seal` accepts it; a sealed
report is immutable (its hash is in `MANIFEST.json`), and a later pass writes
a new report that `supersedes` it. Older Markdown upstream reviews stay as
history. `build` lists, in each skill record, every review cited by an event
about that skill; there are no hand-kept links. The earlier per-family
comparisons are in `../archive/skill-comparisons/`.

## 5c. Curation stages

Every upstream skill moves through four stages, so nothing is redone. The
full rules and their rationale are in
`../../docs/workstreams/skill-curation/stages-design.md`.

1. **What needs analysis.** A new upstream skill has no entry. An existing
   one needs re-analysis only when its catalog `tree_hash` differs from its
   newest analysis after an authorized pin move; an untouched skill keeps
   every stage it reached. `scan.py drift` and `harness-status` only report;
   moving a pin is a separate, authorized step.
2. **Analysis.** A new skill gets a blind extraction of its whole folder,
   then a separate mapping pass (`../playbook.md` §4). A changed skill gets a
   new analysis from the previous one and `git diff <accepted sha>..<new sha>
   -- <folder>`: added, changed (same meaning), removed traits. The new
   analysis is added as `proposed`; earlier analyses are never edited.
   When one of our skills, AGENTS.md or a `doc:` document changes, its own
   list is re-analysed at once.
3. **Comparison and report.** `registry.py report draft <harness> --skill
   <id> --with <our skill|none>` writes the in-scope rows with computed
   facts:
   - `present`: the compared skill lists the trait, or `doc:AGENTS.md` does
     (`provider`);
   - `variant`: the compared skill lists a trait whose `distinct_from` names
     it (`candidates`; the author picks `via`);
   - `absent`: neither;
   - `also_in`: every other skill or `doc:` entry that has it, as
     information only.
   The report also keeps the pairing signals: trait overlap and placement
   (computed) and purpose (judged); when the picks differ, `pairing.flag`
   says why. The author writes `ours` citations, a recommendation per row
   (`adopt` delivered or pending, `defer` with `revisit_when`, `reject`,
   `out-of-scope`) and, for every adopt row, the prompting-guide check
   (`guide: {verdict: ok | reword | conflict, rules}`); trait-policy stances
   are pre-filled. A `conflict` row is never an adopt unless the owner keeps
   the adoption anyway: then the guide check stays `conflict` and carries
   `override: {ruling, date}`, citing the ruling and its date, and the
   adopt may rest on it. A partial match is a gap, never coverage. Critics
   check the analysis and the comparison; `report seal` then freezes it.
   Each critic field (`analysis_critic`, `comparison_critic`) records `by`,
   `date` and a verdict: `pass` (the critic passed it), `fail`, or `accepted`
   (the critic's last round failed, for example REVISE, and the coordinator
   accepted the fixes without a further critic pass). `accepted` names who
   accepted (`by`) and when (`date`), and records that round as
   `last_critic: {by, date, verdict: fail}`. `report seal` accepts `pass` or
   `accepted` on both fields, nothing else. Scope per row: `new`, `changed`,
   `recompare` (an undecided trait whose facts moved) or `reconsider` (the
   owner reopens it).
4. **Decision.** The owner rules each in-scope trait; `record` enforces §5b.
   **Status.** `registry.py status <harness> [--skill X] [--traits]`
   computes, never stores, each trait's stage (removed upstream, needs
   re-analysis, decided, needs re-comparison, reported, in review, analysed,
   not analysed), its ruling, and whether we provide it (delivered, pending,
   withdrawn, no longer provided). A deferred trait shows as decided, never
   as not analysed.

## 6. `registry.py`

Run with `uv run python harness_lifecycle/registry/registry.py <command>`. It
is a thin entry for the `curation` package at the repo root
(`curation/registry/`, with the scanner in `curation/scan/` behind
`../scan.py`).

| Command | Does |
|---|---|
| `gap <harness> [--kind K] [--beads]` | Lists capabilities never ruled on, those ruled on whose upstream content changed since (§5b, with the `git diff` command and the traits or adaptation already ruled), and those removed upstream. Capabilities we already have under the same logical ID or normalized name, but never ruled on, are listed separately as `present, unruled`. `--beads` prints `bd create` lines for review; it never runs them |
| `status <harness> [--skill X] [--traits]` | Each upstream skill's stage, and per trait its stage, ruling and provision (§5c); trait-policy entries whose guide rules changed |
| `ours` | Catalogs our capabilities: root `.claude/` and `.codex/` plus every `mvp-harness/plugins/*`, excluding each plugin's `template/` copy |
| `round open <slug>` / `round seal <round_id>` | Starts a round file with its header; seals it into `MANIFEST.json`, with the hashes of the analyses it cites |
| `report draft <harness> --skill <id> --with <skill\|none> [--report P] [--reconsider T …] [--refresh]` | Creates or extends a draft report with computed facts and pairing; `--refresh` recomputes them and keeps the judged fields |
| `report seal <path>` | Freezes a report once both critic fields are `pass` or `accepted` (§5c) and every in-scope trait has its row and evidence |
| `record … [--supersedes <id>] [--whole-skill <kind>]` | Appends one validated event to the open round (§5b); fills `source`, lifecycle inheritance, `policy_basis` and a playbook's `target_tree_hash` |
| `steps diff <playbook> [<base>] [<head>]` | Lists a playbook's per-step changes between two git revisions; `base` defaults to `HEAD`, `head` to the working tree (§4b) |
| `build` | Regenerates `INDEX.md`, `TRAITS.md`, `STEPS.md`, `references/*.md`, every skill record and every report's `.md` |
| `check` | Validates the ledger (schema, unique IDs, `supersedes`, sealed rounds and reports unchanged, trait rules of §5b), `skills.yaml` and the records, the trait files (§4a), the playbooks and their ledger hashes (§4b), sharing and policy, the reports, and that generated files are current. Warnings (retired traits still listed, unjustified shared traits, `avoid` traits we still list, changed guide rules) do not fail it |

## 7. Changing skills

The method for every change (placing, upstream reviews, comparisons,
evaluations, updates and retirement) is in `../playbook.md`.
