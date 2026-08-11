# Harness Lifecycle — progress and resume anchor

Snapshot: 2026-08-11

Workstream state: **operational; one known ledger-drift follow-up is open**

Primary open Beads issue: `cr-bes` — `open`

This file is the model-neutral entry point for resuming Harness Lifecycle work.
It separates committed sources of truth, generated review surfaces, and local
scratch evidence. It does not depend on earlier chat history.

## Current verdict

The P0–P4 lifecycle is implemented: deterministic inventory and materiality,
reference-versus-local gap analysis, an adoption ledger, curation commands and
guardrails, evaluation/routing, and template sync-back support. Two rounds of
adversarial review found implementation defects; the final round-two synthesis
records every round-one and round-two finding as fixed and verified.

The later `agent-skills` reconciliation and focused three-harness synthesis are
also complete as **analysis artifacts**. They are not automatic adoption
decisions. The ledger remains a separate explicit decision surface.

The main known implementation gap is `cr-bes`: content changes to previously
deferred or rejected capabilities remain suppressed, while the existing
“upstream improved” path handles adopted entries only.

## Research organization

The lifecycle and MVP-plugin research is organized under dedicated folders:

- `docs/research/harness-lifecycle/`
- `docs/research/mvp-plugin/`

These are the canonical research locations. Do not restore the former
root-level paths or flatten the folders during future cleanup.

## Read first

From the repository root, read these in order:

1. [`AGENTS.md`](../../../AGENTS.md), [`.codex/project/`](../../../.codex/project/),
   and [`.beads/beads.md`](../../../.beads/beads.md).
2. The lifecycle overview and commands:
   [`harness_lifecycle/README.md`](../../../harness_lifecycle/README.md).
3. The original plan and research brief:
   [`reference-harness-lifecycle-plan.md`](../../plans/reference-harness-lifecycle-plan.md).
4. The research synthesis:
   [`harness-lifecycle-synthesis.md`](harness-lifecycle-synthesis.md).
5. The adversarial review chain:
   [`harness-lifecycle-review-synthesis.md`](harness-lifecycle-review-synthesis.md)
   and [`harness-lifecycle-review2-synthesis.md`](harness-lifecycle-review2-synthesis.md).
   Consult the paired Fable/GPT reports only when exact findings or evidence are
   needed.
6. For the later capability analysis, read:
   [`agent-skills-codex-reconciliation-plan.md`](../../plans/agent-skills-codex-reconciliation-plan.md),
   [`focused-three-harness-synthesis-plan.md`](../../plans/focused-three-harness-synthesis-plan.md),
   and [`harness-lifecycle-visualization-cleanup-plan.md`](../../plans/harness-lifecycle-visualization-cleanup-plan.md).
7. For distribution/adoption architecture questions, read the separate
   [`mvp-plugin` research folder](../mvp-plugin/) beginning with
   [`mvp-plugin-architecture-synthesis.md`](../mvp-plugin/mvp-plugin-architecture-synthesis.md).

## Sources of truth

| Area | Canonical source | Notes |
|---|---|---|
| Scanner/materiality | [`scan.py`](../../../harness_lifecycle/scan.py) | Inventories capability surfaces and compares catalogs or Git states |
| Local gap and ledger | [`gap.py`](../../../harness_lifecycle/gap.py), [`aliases.json`](../../../harness_lifecycle/aliases.json), [`ledger.json`](../../../harness_lifecycle/ledger.json) | Ledger decisions are explicit and separate from recommendations |
| Reviewed baselines | [`catalogs/`](../../../harness_lifecycle/catalogs/) | These are last-reviewed snapshots, not automatically the current submodule pins |
| Global usefulness data | [`capability_usefulness.csv`](../../../harness_lifecycle/capability_usefulness.csv) | 907 canonical rows after Agent Skills reconciliation |
| Global Codex analysis | [`codex_analysis/`](../../../harness_lifecycle/codex_analysis/) | 668 deep evaluations, 239 preserved exclusions, 75 clusters |
| Focused analysis | [`focused-three-harnesses/`](../../../harness_lifecycle/codex_analysis/focused-three-harnesses/) | Agent Skills, Matt Pocock Skills, and Superpowers only |
| Review surfaces | [`visualizations/`](../../../harness_lifecycle/visualizations/) | Generated HTML/CSV; never the adoption source of truth |
| Reference code | [`reference_harnesses/`](../../../reference_harnesses/) | Read-only Git submodules; parent repo tracks pins |
| Work status | Beads | `cr-bes` is the primary open lifecycle follow-up |

## What is implemented

The current lifecycle provides:

- logical capability discovery across skills, commands, agents, rules, hooks,
  MCP servers, and plugins;
- mirror-aware and plugin-aware deduplication;
- material versus minor change classification;
- upstream drift and reference-versus-local gap reporting as separate axes;
- explicit `adopted`, `deferred`, and `rejected` ledger decisions;
- Claude command surfaces
  [`.claude/commands/harness-status.md`](../../../.claude/commands/harness-status.md)
  and [`.claude/commands/harness-scan.md`](../../../.claude/commands/harness-scan.md);
- curation guardrails in
  [`.claude/rules/harness-lifecycle/curation.md`](../../../.claude/rules/harness-lifecycle/curation.md);
- a staleness nudge in
  [`.claude/hooks/harness-staleness-nudge.sh`](../../../.claude/hooks/harness-staleness-nudge.sh);
- the primary evaluation/routing skill
  [`.claude/skills/harness-evaluate/SKILL.md`](../../../.claude/skills/harness-evaluate/SKILL.md);
- consolidated focused and all-reference visualization surfaces.

The older
[`refresh-harness-from-reference`](../../../.claude/skills/refresh-harness-from-reference/SKILL.md)
skill still exists, but the lifecycle plan explicitly treated it as stale and
out of scope for the fresh design. It references the deleted
`project_agnostic_claude_setup/` structure. Do not use it as the primary
lifecycle workflow without first opening a scoped reconciliation issue.

There is no Codex-native `harness-evaluate` skill at this snapshot. A Codex
session can operate the deterministic Python tools and follow this handoff, but
should not claim cross-provider skill parity. Treat a Codex port as separate
work if it is desired.

## Current verified analysis state

Fresh verification on 2026-07-28 produced:

```text
PASS reconciliation: csv=907 catalog=44 overlap=5 new=39 excluded=239 included=668 clusters=75
PASS focused synthesis: repos=44/36/19 unique=97 included=94 excluded=3 clusters=30
```

Current focused-synthesis scope:

| Measure | Count |
|---|---:|
| `agent-skills` canonical rows | 44 |
| `mattpocock_skills` canonical rows | 36 |
| `superpowers` canonical rows | 19 |
| Unique union | 97 |
| Deep evaluations | 94 |
| Prior exclusions | 3 |
| Focused clusters | 30 |

The Agent Skills decision ledger contains 44 entries:

| Decision | Count |
|---|---:|
| `adopted` | 11 |
| `deferred` | 13 |
| `rejected` | 20 |

Do not infer those ledger counts from the focused recommendations. They are an
independent, earlier set of explicit decisions.

The visualization generators also completed successfully. The focused
generator reproduced 97/94/30/3 with throwaway outputs; the lifecycle overview
saw seven reference catalogs. The lifecycle generator's
`--out` option relocates only the HTML and still rewrites the tracked
`inventory.csv`, so its verification delta was inspected and reverted.
Generated artifacts under `harness_lifecycle/visualizations/` remain review
aids.

## Catalog baseline drift at this snapshot

Every committed catalog records an older reviewed commit than the current
submodule pin. Therefore, “catalogued” does not mean “reviewed at the current
pin.” Short hashes are shown only for orientation; use `git rev-parse HEAD` for
the full current value.

| Repository | Catalog source | Current submodule pin | Match |
|---|---|---|---|
| `agent-skills` | `6bcfeb9dae52` | `fefc4075ddfd` | No |
| `claude-code-best-practice` | `cd5af1fba246` | `7bb2c9505d9d` | No |
| `claude-plugins-official` | `f7b31235e6f0` | `e3e378cbbb20` | No |
| `compound-engineering-plugin` | `31b0686c2e88` | `3422ea0916bb` | No |
| `everything-claude-code` | `c7bf1434505b` | `a3130f9ebfae` | No |
| `mattpocock_skills` | `8370e760d025` | `ed37663cc5fb` | No |
| `superpowers` | `917e5f53b16b` | `d884ae04edeb` | No |

This is not itself a request to update catalogs or ledger decisions. Refresh a
catalog only in a scoped review, compare it to the committed baseline first,
and preserve the old decision provenance.

For `agent-skills`, a local no-network scan of the current pin found the same 44
logical capabilities but four material body changes since the committed
catalog:

- `hook:hooks/simplify-ignore-test` — ledger status `rejected`
- `skill:skills/documentation-and-adrs` — ledger status `deferred`
- `skill:skills/security-and-hardening` — ledger status `deferred`
- `skill:skills/test-driven-development` — ledger status `adopted`

Running `gap.py` against the current submodule path resurfaces only the adopted
TDD entry. The other three changed decisions remain suppressed. That concrete
behavior is the reason `cr-bes` remains open.

## Remaining work

### `cr-bes`: resurface changed non-adopted decisions

Implement deterministic re-review surfacing for all ledger statuses:

1. Store the reviewed content hash for `adopted`, `deferred`, and `rejected`
   entries.
2. Report changed entries with their previous decision without automatically
   changing it.
3. Continue suppressing unchanged decided entries.
4. Define and test behavior for legacy entries without a content hash.
5. Cover all three statuses with tests.

The safe policy is “surface for re-review,” not “silently reopen” or “adopt.”
The four current Agent Skills changes are useful characterization fixtures, but
tests should use isolated temporary catalogs/ledgers rather than mutate the
canonical ledger.

### Future catalog reviews

After `cr-bes`, or in separately approved work, review the delta between each
catalog baseline and its current submodule pin. Do not bulk-refresh all seven
baselines merely to make hashes match. For each selected reference:

1. inventory the current pin into a temporary catalog;
2. diff it against the committed baseline;
3. evaluate only material changes;
4. record explicit decisions;
5. replace the committed baseline only after review.

### Optional cleanup decisions

- Decide whether to retire or reconcile the stale
  `refresh-harness-from-reference` skill.
- Decide whether a Codex-native lifecycle evaluation skill is worth adding.
- Keep these separate from `cr-bes`; neither is required to fix ledger drift.

## Scratchpad map

[`scratchpad/focused-three-harnesses/`](../../../scratchpad/focused-three-harnesses/)
contains model inputs, Luna/Sol/Terra recommendation outputs, baseline hashes,
and a pre-canonical bundle used to assemble the focused synthesis. It is local,
gitignored evidence.

The committed bundle under
[`harness_lifecycle/codex_analysis/focused-three-harnesses/`](../../../harness_lifecycle/codex_analysis/focused-three-harnesses/)
is the source of truth. If scratchpad is missing, do not reconstruct it unless a
new analysis run needs new auditable intermediate evidence.

## Safe resume procedure

Run from the repository root:

```bash
bd prime
bd show cr-bes
git status --short --branch
git submodule status --recursive
python3 -m py_compile \
  harness_lifecycle/scan.py \
  harness_lifecycle/gap.py \
  harness_lifecycle/codex_analysis/tools/reconcile_agent_skills.py \
  harness_lifecycle/codex_analysis/tools/verify_focused_synthesis.py
python3 harness_lifecycle/codex_analysis/tools/reconcile_agent_skills.py --verify
python3 harness_lifecycle/codex_analysis/tools/verify_focused_synthesis.py
python3 harness_lifecycle/gap.py gap reference_harnesses/agent-skills
```

To re-check the current Agent Skills pin without changing canonical files:

```bash
mkdir -p scratchpad/harness-lifecycle
python3 harness_lifecycle/scan.py catalog \
  reference_harnesses/agent-skills \
  --out scratchpad/harness-lifecycle/agent-skills-current.json
python3 harness_lifecycle/scan.py diff \
  harness_lifecycle/catalogs/agent-skills.json \
  scratchpad/harness-lifecycle/agent-skills-current.json
```

To verify focused visualization generation without dirtying the repository:

```bash
mkdir -p scratchpad/harness-lifecycle
python3 harness_lifecycle/visualizations/focused-three-harnesses/generate.py \
  --out scratchpad/harness-lifecycle/focused-three.html \
  --csv-out scratchpad/harness-lifecycle/focused-three.csv
```

Do not assume the lifecycle overview's `--out` makes the whole run temporary:
it still writes
`harness_lifecycle/visualizations/lifecycle-overview/inventory.csv`. Run that
generator only when intentionally refreshing the committed visualization, or
inside a disposable copy/worktree, and inspect its HTML and CSV delta together.

Before editing `gap.py`, claim `cr-bes` and use characterization-first tests.
Before completion, run the relevant checks, inspect `git diff`, close the issue,
export Beads, and inspect `git status`. Never edit a reference submodule for a
parent-repo lifecycle task.

## Completion boundary

The existing P0–P4 implementation and analyses are complete at their recorded
versions. The **current follow-up** is complete only when:

- changed entries in all three ledger statuses are surfaced deterministically;
- unchanged decisions remain suppressed;
- legacy no-hash behavior and all statuses have tests;
- no ledger decision changes automatically;
- canonical analysis and reference submodules remain unchanged unless the user
  separately authorizes a review/update;
- `cr-bes` is closed, Beads is exported, and `git status` is inspected.

## Copyable resume prompt

```text
Resume Harness Lifecycle from
docs/research/harness-lifecycle/PROGRESS.md. Do not rely on prior chat history.
Read the linked lifecycle README, plan, research syntheses, current Beads issue,
scanner, gap tool, and ledger. First run the safe resume checks and preserve the
dedicated research-folder organization. Treat reference submodules as
read-only and scratchpad as optional evidence. The primary open implementation
work is cr-bes: surface content-changed adopted, deferred, and rejected ledger
entries for explicit re-review without changing decisions automatically. Do not
turn focused synthesis recommendations into ledger decisions, bulk-refresh
catalogs, or use the stale refresh-harness skill as the current workflow.
Separate verified facts from inference and ask before commits, network fetches,
submodule-pin changes, or adoption changes.
```
