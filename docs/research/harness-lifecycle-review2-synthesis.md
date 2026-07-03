# Harness Lifecycle — Round-2 Review Synthesis

Round-2 re-review ([Fable-5](harness-lifecycle-review2-fable5.md),
[GPT-5.5](harness-lifecycle-review2-gpt55.md)) of the round-1 fixes.

## Round-1 fixes: verdict (both reviewers)
**All 8 genuinely FIXED** — independently verified. C1/H1 dedup, C2 leak, C3 beads
three-way, H2 MCP-crash, H3 SSH URL, H4 orphan retire, H5 injection, H6 materiality.

The fixes introduced a few new edges (below). Net: risk moved from silent
data-loss/crashes to identity-model edges + an unbounded `rm` — all now addressed.

## New findings & disposition
| # | Sev | Finding | Status |
|---|---|---|---|
| N1 | HIGH | root-level `.claude-plugin` mirror-stripped to empty key → our 3 plugins collapse to `plugin:` | **FIXED** — `_plugin_dedup_key` from raw parts + plugin.json name |
| N4 | HIGH | orphan-retire `rm` could escape `$TARGET` via `../` in a tampered manifest; also retired user-owned files | **FIXED** — reject `..`/absolute, skip `hp_is_user_owned` |
| #3 | MED | `EXCLUDE_SEGMENTS` dropped capabilities nested under `docs/`/`examples/` (e.g. `agents/docs/…`) | **FIXED** — `docs`/`examples` excluded only at top level |
| #7 | LOW | sweep produced garbled prose "the parent the parent repo repo" | **FIXED** — `orchestrators` → `upstream` |
| H6-label | LOW | signature-change reason mislabeled "name/description/tools" for any frontmatter edit | **FIXED** — relabeled "frontmatter/surface changed" |
| N2/#5 | MED | path-based `logical_id` ⇒ an upstream *move* reads as remove+add, orphaning ledger entries | **DEFERRED** — moves are rare; a move is legitimately a path change. Note for a future move-detection pass (match remove+add by content_hash). |
| N3/#8 | LOW | H6 signature over-sensitive to frontmatter key-reorder / blank-line churn | **ACCEPTED** — safe direction (over-flag, never hide); deeper semantic canonicalization deferred. |
| #6/N6 | LOW | `ensure_yaml_key` awk still mishandles a remote URL containing `"` or `\` | **DEFERRED** — git remote URLs don't contain these; the `@host` corruption (the real bug) is fixed. |
| #4 | — | (Codex) leak self-check "not case-insensitive" | **FALSE POSITIVE** — `grep -rnIi` is case-insensitive; verified `BODHA_SECRET` matches. |

## Verification of round-2 fixes
- N1: `gap ours` → `plugin:code-intel`, `plugin:codex-adapter`, `plugin:mvp-plugin` (3 distinct).
- Dedup invariants preserved: everything-claude-code skills **244→182**, claude-plugins-official plugins **39→39**.
- #3: `agents/docs/ankane-readme-writer.md` now catalogued.
- N4: planted `../VICTIM.txt` manifest entry — refused, not deleted; warned.
- #7: template now reads "the parent upstream repo".
- Suites all green: P3 three-way 9/9, review-fix (C3/H3/H4) 7/7, plugin suite 26/0; build-template no leak/no drift.

## Remaining (all minor, none blocking)
Move-tolerant ledger identity (N2), stricter YAML value escaping (N6), semantic
frontmatter canonicalization (N3). None affect correctness on real harnesses today.
