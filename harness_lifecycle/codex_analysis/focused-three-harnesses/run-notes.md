# Focused Synthesis Run Notes

## Scope

- Requested harnesses: `agent-skills`, `mattpocock_skills`, and `superpowers`.
- Repository row counts: 44, 36, and 19 respectively.
- Unique canonical union: 97 rows; two rows are shared by `agent-skills` and `superpowers`.
- Included deep evaluations: 94.
- Explicit prior exclusions: 3.
- Focused problem clusters: 30.

## Method

- Filtered exact semicolon-delimited provenance tokens, not substrings.
- Reused the existing Codex row evaluations without changing scores or verdicts.
- Preserved existing problem-cluster assignments while removing every out-of-scope source.
- Recomputed all cluster aggregates from the 94 selected rows.
- Rewrote qualitative recommendations from only the selected row evidence.
- Kept the canonical CSV, all-harness analysis, exclusion artifact, and ledger unchanged.

## Assumptions

- A shared canonical row is included when any requested harness appears in its provenance.
- Existing Codex row scores and verdicts are reused; this run changes synthesis scope, not row judgments.
- Existing cluster IDs are problem-space anchors, not adoption decisions.
- Focused recommendations remain analysis inputs and do not update the ledger.

## Recommendation Counts

| Decision | Clusters |
|---|---:|
| `adapt` | 2 |
| `defer` | 4 |
| `merge` | 21 |
| `reject_after_review` | 3 |

| Priority | Clusters |
|---|---:|
| `P1` | 7 |
| `P2` | 14 |
| `P3` | 9 |

## Exclusions

- `skill:migratetoshoehorn`
- `skill:setupmattpocockskills`
- `skill:setupprecommit`

These exclusions were not reinterpreted as adoption decisions. They remain traceable in `scope.json` and the final synthesis.
