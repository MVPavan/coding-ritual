---
name: harness-skill-compare
description: Use when two or more skills — ours, from reference_harnesses/, or a mix — need a structured side-by-side comparison during curation, typically before an adopt/reject/merge decision or when asked how the skills in a capability family differ. Also trigger on compare-skills phrases.
---

# Harness Skill Compare

Produces a durable three-level comparison of a set of skills so a curation
decision can be argued from evidence instead of memory.

## Inputs

- Two or more skill directories. Read every file each skill ships — SKILL.md
  plus its references, agents, and scripts — not just the front matter.
- `harness_lifecycle/inventory/skill-buckets.md` (bucket taxonomy) and
  `harness_lifecycle/ledger.json` (prior decisions on any compared skill).

## Output

One folder per comparison: `harness_lifecycle/skill-comparisons/<slug>/`.
The slug names the capability family being compared (`planning-decomposition`,
`debugging-loop`) — never a concatenation of skill names, which goes stale the
moment the set changes. Two files:

### `README.md` — levels 1 and 2

**Level 1 — placement table.** One row per skill:

| Skill | Repo | Bucket | Triggers when |
|---|---|---|---|

Bucket comes from the taxonomy; if a skill is unbucketed, propose one and mark
it proposed. "Triggers when" is the real firing condition, judged from the
description *and* body — note when a description would misfire.

**Level 2 — capability profiles.** Per skill, a short section:

- **Achieves** — the outcome it exists to produce, one sentence.
- **Can do** — its distinct capabilities, as bullets.
- **Pros / cons** — judged against the others in this set, not in the
  abstract; each pro or con says why.

Close level 2 with a verdict paragraph: which skills genuinely overlap, which
are substitutes vs complements, and which is strongest for what. If the
ledger already holds a decision on a compared skill, cite it here.

### `components.md` — level 3

**Component inventory.** Per skill, its distinct behavioural components —
steps, gates, templates, rules, heuristics, red-flag/rationalization tables —
each cited `file:line`. A component is something that changes agent behaviour,
not a heading.

**Cross-skill matrix.** Rows are the merged component list, one column per
skill, cells: `✓` (present), `~` (variant — differs in mechanism or strength),
`—` (absent).

**Shared-component differences.** For every `~` row and any `✓` row where
implementations differ: how each skill realises the component, which
realisation is stronger, and why — mechanism, not adjectives.

## Rules

- Reference harnesses are read-only; never edit any compared skill.
- Every component claim carries a `file:line` citation — no invented
  components, no summarised guesses.
- Inventory and matrix are factual; judgement lives only in pros/cons,
  verdicts, and "which is stronger" lines, each with its reason.
- Comparison is not decision: adopt/reject/defer goes through the
  `harness-evaluate` skill and the ledger. When a decision follows, cite the
  comparison folder in the ledger reason.
- One comparison per capability family — extend the existing folder when the
  set grows; do not fork a second folder for an overlapping set.
