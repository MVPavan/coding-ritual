# Run Notes

## Execution Summary

- Reconciled the 44 capabilities in `catalogs/agent-skills.json` into
  `capability_usefulness.csv` with Codex-only judgments for new rows.
- Five normalized-name matches enriched existing canonical rows; 39 genuinely
  new logical rows were appended without collapsing semantic near-duplicates.
- Final CSV: 907 data rows.
- Deep analysis: 668 included rows and 239 unchanged historical exclusions.
- Shard outputs: 13 total — 11 historical shards plus two incremental
  `agent-skills` shards.
- Primary clusters: 75. No new primary cluster was needed.
- The adoption ledger was not read as a decision source and was not modified.

## Counts

| Kind | Included Rows |
|---|---:|
| `skill` | 261 |
| `agent` | 109 |
| `plugin` | 43 |
| `mcp` | 9 |
| `rule` | 43 |
| `hook` | 74 |
| `command` | 129 |

| Row Verdict | Count |
|---|---:|
| `adopt` | 82 |
| `defer` | 131 |
| `merge` | 285 |
| `reject_after_review` | 125 |
| `rewrite` | 45 |

The 44 affected canonical evaluations comprise 2 `adopt`, 23 `merge`, 5
`defer`, 2 `rewrite`, and 12 `reject_after_review` verdicts. The 39 new shallow
Codex-only rows comprise 27 `yes`, 4 `maybe`, and 8 `no` judgments. Every new
row received a deep evaluation regardless of its shallow judgment.

| Cluster Decision | Count |
|---|---:|
| `adapt` | 1 |
| `adopt_as_is` | 2 |
| `defer` | 17 |
| `merge` | 41 |
| `reject_after_review` | 14 |

| Priority | Count |
|---|---:|
| `P0` | 3 |
| `P1` | 13 |
| `P2` | 28 |
| `P3` | 31 |

## Reconciliation Decisions

- Preserved all historical Fable and GPT shallow judgments. New-only rows use
  `fable_useful=not_evaluated`, an explicit reason, `consensus=codex_only`, and
  `agree=n/a`; no second-model judgment was inferred.
- Preserved the existing 868-row CSV order, enriched five rows in place, and
  appended 39 new rows in source-catalog order.
- Refreshed the five existing deep evaluations after reading the new source
  variants. Their evidence notes state that the historical Fable judgment
  predates `agent-skills`.
- Preserved every differently named capability as a row-level candidate and
  reconciled semantic overlap only at cluster level.
- Kept the historical 239-row exclusion artifact byte-identical.

Material synthesis changes:

- `C013`: broadened from Codex cited research to official-documentation-grounded
  research and development; `adopt_as_is` became `merge` at P1.
- `C033`: threat-model and hardening evidence promoted security and privacy
  review from P2 to P1.
- `C050`: CI/CD, observability, and launch guidance became a coherent optional
  production-operations pack; retained `defer` and moved from P3 to P2.
- `C056`: general deprecation and expand-contract guidance changed legacy
  modernization from `defer`/P3 to `merge`/P2.
- `C075`: the focused web-performance auditor changed the cluster from
  `reject_after_review`/P3 to `defer`/P2.
- `C010`, `C027`, and `C030` were strengthened with thin-slice execution,
  bounded adversarial review, and structured idea/intent refinement.
- `C041` now expresses an evidence-driven measure/change/re-measure performance
  workflow while remaining a deferred P2 capability.

## Assumptions And Risks

- `session-start-test.sh` and `simplify-ignore-test.sh` are scanner-promoted test
  artifacts, not production hooks. They remain traceable but are rejected as
  standalone capabilities.
- Several reference skills contain useful ideas but are too long, stack-biased,
  or absolute for direct adoption. Deep verdicts distinguish usefulness from
  suitability as a new harness surface.
- Shard input and evaluation JSONL files are intentionally ignored by the repo;
  their merged canonical records are committed artifacts, while shard notes
  preserve the human-readable audit trail.
- `capability_usefulness.html` remains the historical 868-row two-model view. It
  was not silently regenerated as a mixed dual-model/Codex-only report.

## Verification History

- The first deterministic apply wrote the reconciled canonical artifacts, then
  correctly failed because `skill:idearefine` lacked an explicit
  `agent-skills` provenance string in `evidence_notes`.
- A diagnostic checked all 44 affected rows and found no second instance. The
  source shard was corrected, the tool was made idempotent, and apply plus
  verification were rerun successfully.
- A later adversarial review found ten stale source-count claims, one semantic
  split between the equivalent `using-superpowers` and `using-agent-skills`
  routers, and placeholder performance synthesis. The count prose now derives
  from cluster membership, both generic routers are in the portfolio cluster,
  and `C041` has a concrete reconciled recommendation. A verifier assertion now
  rejects stale numerical source claims.
- Final code review found that retaining a multi-file mutation path was unsafe
  and that its temporary-file replacement had changed generated artifacts to
  mode `0600`. The mutation path was removed, normal `0644` modes were restored,
  and the helper now performs read-only verification including explicit source-
  catalog ordering checks. Follow-up review added a locked digest for all 868
  historical Fable/GPT shallow judgments and repeats the Codex-only sentinel
  checks on the new deep-evaluation rows.
- Final deterministic check:
  `PASS reconciliation: csv=907 catalog=44 overlap=5 new=39 excluded=239 included=668 clusters=75`.
- JSON/JSONL schemas, scores, verdict vocabularies, shard/global object equality,
  primary-cluster coverage, derived cluster fields, manifest counts, rendered
  synthesis, CRLF CSV format, and repo-relative stored paths passed.
- Protected hashes remained unchanged:
  - ledger: `b7cbb49a4b8fe8e0bd4e1cf6e085387ab98cd42a7e57d6ab85c3b5e833384d82`
  - exclusions: `5c7ffd8336ffcd543386992aba38ad2faf67f8311d865ce3d9be73ae8357b8d7`
