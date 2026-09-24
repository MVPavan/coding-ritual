---
name: harness-skill-compare
description: Use for a substantive comparison of skill triggers, behavior or curation choices. Scale narrow overlap questions to the relevant branches.
---

# Harness Skill Compare

Compare selected skills at the depth the question requires. For a narrow overlap
question, read descriptions, relevant body branches and their direct dependencies.
For a full behavioral comparison, inventory all shipped instructions, metadata
and scripts, distinguishing inspected code from executed behavior.

Consult `harness_lifecycle/inventory/skill-buckets.md` for classification and
`harness_lifecycle/ledger.json` for relevant prior decisions. Use configured bounded
delegation only when helpful; no mandatory subagent-choice question applies.

For a durable full comparison, use `harness_lifecycle/skill-comparisons/<family>/`:

- `README.md`: placement/trigger table, distinct capabilities, relative pros/cons
  and a supported verdict about substitutes versus complements.
- `components.md`: behavioral components with file/line evidence, a cross-skill
  presence/variant matrix, and explanations of material mechanism differences.

Extend the relevant comparison when the set changes. A narrow answer need not
create both files or scan unrelated references. State coverage and unverified
behavior; description text alone does not prove actual invocation frequency.

Comparison is read-only on the compared skills. Adoption and ledger decisions
belong to authorized harness-evaluate work; cite the comparison when recording one.
