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
├── registry.py                    # the tool (§6)
├── ledger/
│   ├── <yyyy-mm-dd>-<slug>.jsonl  # one file per round (§5)
│   └── MANIFEST.json              # sha256 of every sealed round
├── skill-records/<domain>/<skill>.md   # our skills (§3)
├── references/<harness>.md        # generated: their capabilities and our ruling (§4)
├── reviews/<yyyy-mm-dd>-<type>-<slug>.md  # evidence behind rulings (§5a)
└── INDEX.md                       # generated: domain → stage → sub-stage
```

The skills themselves stay in `.claude/skills/`, the only source. Records
describe them; they never copy them.

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
3. **Two active skills in one domain · sub-stage** must each state the
   boundary in their record, or they are merge candidates. `INDEX.md` flags
   them.
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
| 10 Orchestration, handoff | X · Orchestration, Continuity |
| 11 Harness authoring | Improvement · Codification |
| 12 Tooling, guardrails | X · Governance; U · Tooling |
| 13 Research, documentation · 14 Learning, content | Discovery · Research; X · Communication; U · Tutoring |

## 3. Skill records

`skill-records/<domain>/<skill>.md`, one per real skill:

```markdown
---
skill: planning                 # the .claude/skills/<name> folder
domain: engineering
stage: Design
substage: Decomposition
secondary: [Orchestration]
family: task-decomposition      # capability family shared with reference skills
aliases: []                     # alias and stub entrypoints that route here
status: active                  # active | retired
---
# planning

## Capability
What it does, when it fires, and where it ends and its neighbours begin.
(Written by hand.)

<!-- registry:generated lineage -->
Each part, and the harness, path and commit it came from, with what was
modified or deliberately dropped. Generated from adopt and adopt-merged
records.
<!-- /registry:generated -->

<!-- registry:generated history -->
Every ledger record about this skill, newest first.
<!-- /registry:generated -->

<!-- registry:generated reviews -->
Every review a ledger record about this skill cites.
<!-- /registry:generated -->
```

Only the frontmatter and Capability are written by hand; `registry.py build`
rewrites the generated blocks.

## 4. Reference pages

`references/<harness>.md` is generated from the harness catalog
(`../catalogs/<harness>.json`) and the ledger. One row per capability the
harness ships:

| Their capability | Status | Into ours | Last ruled at | Changed upstream since? |
|---|---|---|---|---|

Status is the effective ruling, or `present, unruled` (we have a same-named
capability but never ruled), or `not reviewed`.

## 5. Ledger

The ledger follows `.repo-context/coding-style.md` §Ledgers: JSON Lines, one
file per round, append only, sealed when complete.

**First line of every round file: the round header.**

```json
{"type": "round", "round_id": "2026-10-14-agent-skills-0.6.13", "date": "2026-10-14", "scope": "…", "pins": {"agent-skills": "aeac41d"}, "method": "…", "evidence": ["upstream-reviews/…"], "excluded": [{"rule": "…", "why": "…", "count": 0}], "carried_debts": ["…"]}
```

**Every other line: one event.**

| Field | Required | Meaning |
|---|---|---|
| `type` | yes | `"event"` |
| `id` | yes | unique across the ledger: `<round_id>:<n>` |
| `date` | yes | ISO 8601 |
| `kind` | yes | see below |
| `subject` | yes | `ours:<skill>` or `<repo>:<logical_id>` |
| `why` | yes | the reason; never empty |
| `evidence` | yes | list of `path:line`, URLs, comparison folders, commits |
| `skill` | for our skills and adoptions | our target: a skill folder name, or `<kind>:<name>` for a non-skill capability (`agent:code-reviewer`) |
| `source` | for reference rulings | `{repo, logical_id, path, sha, content_hash}` |
| `adaptation` | for `adopt-merged` | `{merged_from: [], modifications: [], deliberately_dropped: []}` |
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

The effective ruling on a subject is its latest event not superseded.
"Superseded" is computed, never recorded. Every reference ruling records the
`content_hash` at the time, whatever its kind, so `gap` notices when a
rejected or deferred capability changes upstream.

`skill` is required on an effective `adopt`/`adopt-merged` ruling (it must name
an existing skill record, alias, stub or non-skill `kind:name`), and optional on
a superseded historical one, which may name a skill we no longer have.

## 5a. Reviews

A review is the evidence behind one or more rulings. One flat folder,
`reviews/`, named `<yyyy-mm-dd>-<type>-<slug>.md`, with two types:

| Type | When | Covers |
|---|---|---|
| `upstream` | A reference harness release; the submodule pointer moves in the same change | Every changed capability: what changed, our counterpart, what is worth taking. Slug: `<harness>-<version>` |
| `skill` | Deciding a merge, upgrade or rebuild of one of our skills | That skill against its upstream counterparts: a component matrix with `file:line` citations, the stronger mechanism per row, and a verdict. Slug: our skill name |

Ledger events cite a review in `evidence`. `build` lists, in each skill
record, every review cited by an event about that skill; there are no
hand-kept links. The earlier per-family comparisons are in
`../archive/skill-comparisons/`.

## 6. `registry.py`

Run with `uv run python harness_lifecycle/registry/registry.py <command>`.
It imports `../scan.py` for catalogs.

| Command | Does |
|---|---|
| `gap <harness> [--kind K] [--beads]` | Lists capabilities never ruled on, and those ruled on whose upstream content changed since. Capabilities we already have under the same logical ID or normalized name, but never ruled on, are listed separately as `present, unruled`. `--beads` prints `bd create` lines for review; it never runs them |
| `ours` | Catalogs our capabilities: root `.claude/` and `.codex/` plus every `mvp-harness/plugins/*`, excluding each plugin's `template/` copy |
| `round open <slug>` / `round seal <round_id>` | Starts a round file with its header; seals it into `MANIFEST.json` |
| `record …` | Appends one validated event to the open round |
| `build` | Regenerates `INDEX.md`, `references/*.md`, and the generated blocks of every skill record |
| `check` | Validates every record (schema, unique IDs, `supersedes` targets exist, sealed rounds unchanged), every skill record's frontmatter, that every `.claude/skills/` folder has a record or is an alias or stub, and that generated files are current |

## 7. Changing skills

Every change to a skill is one ADLC change and follows one path:

| Step | What happens |
|---|---|
| Intake | A bead: `spike` for an upstream review, `bug` for an observed failure, `feature` for a new capability |
| Design | Evidence: `/harness-scan` and a review (§5a) for upstream; the failure, observed before the change, for our own. The decision becomes ledger events |
| Building | In a git worktree on its own branch, so running sessions keep the current skills. Edit the skill by `authoring-for-agents`, and its record |
| Verify | The checks in `authoring-for-agents`, `skill-catalog.py --check`, `registry.py check`; Sol high batch review when the owner asks |
| Delivery | Merge (the promotion), then `.codex` sync, then `/harness-publish` |

| Operation | Starts from | Records |
|---|---|---|
| Add | a new need; check overlap first | `add`; a new skill record |
| Update | our own failure or lesson | `update`, with the failure as evidence |
| Upgrade from upstream | a reference release | one ruling per borrowed or declined part; a submodule pointer moves only with its review document |
| Merge or split | overlap, or a skill grown too big | `merge` or `split`; references fixed in the same change |
| Retire | unused or merged | `retire`; a stub stays for one plugin release, then the folder is removed |
