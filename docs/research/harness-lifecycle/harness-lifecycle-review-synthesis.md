# Harness Lifecycle — Critical Review Synthesis

Two independent xhigh adversarial reviews ([Fable-5](harness-lifecycle-review-fable5.md),
[GPT-5.5](harness-lifecycle-review-gpt55.md)) of the reference-harness lifecycle.
They converged strongly. Every CRITICAL/HIGH below is **confirmed against the code
or reproduced** (not taken on faith). Source column: which reviewer(s) raised it.

## Invariant verdicts
| Invariant | Verdict |
|---|---|
| 1 — template ⊂ root, no project leak | **VIOLATED** (C2) — lowercase project tokens ship; enforcement is convention-only |
| 2 — update never clobbers local edits | **VIOLATED** (C3) — `.beads/beads.md` overwritten every update |
| 3 — copy one-way | holds |
| 4 — dedup merges only true duplicates | **VIOLATED** (C1, H1) — plugins + same-name caps over-merge |
| 5 — materiality hides nothing | edge (H6) — block-list tool/permission changes bucket as *minor* |

## CRITICAL

**C1 — plugin dedup collapses every plugin into one** · both · `scan.py:262`
`canonical_name` for a plugin returns `parts[-2]` = `.claude-plugin` for *every*
`plugin.json`, so all plugins group to `plugin:.claude-plugin`. Verified:
`claude-plugins-official` 39 plugins → **1 logical**. Drift/gap/ledger cannot see
individual plugins. **Fix:** plugin name from `plugin.json` `name` (or the dir that
*contains* `.claude-plugin`).

**C2 — template ships project-specific text** · gpt55 · `build-template.sh:121,144`
Leak self-check greps capital `Bodha` only; genericize misses lowercase `bodha` and
bare `orchestrators`. Verified: template ships `bodha-memory-eval`,
`bodha-chitta-v2_5.md`, "parent orchestrators repo" (3+1 files). **Fix:** make the
self-check case-insensitive and cover `orchestrators`; neutralize the source strings.

**C3 — `/update` clobbers `.beads/beads.md`** · fable · `install-harness.sh:130`
`cp "$TPL/beads/beads.md" …` runs unconditionally, outside the three-way merge and
absent from the manifest → a user's edits are silently overwritten on every update.
Verified by code. **Fix:** mark `.beads/beads.md` user-owned, or route it through the
three-way like any other core file.

## HIGH

**H1 — same-name distinct caps over-merge** · both · `scan.py:250-263,377`
`logical_id = kind:leafname` with no namespace. Verified: `agent:code-reviewer`
merges two different agents; `skill:access` merges discord/imessage/telegram. Note
the fix is subtle: mirror copies are *not* byte-identical (`.kiro`/`.agents` differ),
so "merge only if content matches" would break the real 457→182 collapse. **Fix:**
strip known mirror-root prefixes (`.kiro/.agents/.cursor/.claude/docs`) from the path,
then use the remaining path (which keeps the plugin namespace) as identity.

**H2 — `drift` crashes on an MCP body-only change** · fable · `scan.py:335,457`
MCP `canonical_path` is `…mcp.json#server`; `classify_change` opens it as a file →
`FileNotFoundError`. Any MCP server whose args change (command unchanged) crashes the
drift report. **Fix:** strip the `#fragment` before reading, or don't file-read MCP
bodies (compare stored hashes only).

**H3 — SSH git remote corrupted in beads config** · fable · `install-harness.sh:117`
`ensure_yaml_key` builds a perl `-e` string with bash `${val}` inlined; perl then
interpolates `@host` as an array. Verified: `git@github.com:acme/app.git` →
`git+git.com:acme/app.git`. Every SSH-remote adopter gets a broken `sync.remote`.
**Fix:** pass the value via env/`$ENV{}` or `sed` with escaping — no interpolation.
*(Pre-existing bug, not introduced by this workstream, but in a file we own.)*

**H4 — deleted template files never retired** · both · `install-harness.sh:42-77`
Update iterates only current template files, so a file removed upstream (e.g. a
root-only curation file that leaked, or a retired hook) stays in the adopted repo
forever; summary still says "0 updated". **Fix:** reconcile old-stamp paths minus
new-manifest; delete only when the local hash still equals the old base, else warn.

**H5 — `gap --beads` emits shell-injectable lines** · both · `gap.py:265-270`
Capability names/paths are interpolated into `bd create "…"` strings unquoted. A
reference capability named `evil" $(…) "` executes on copy-paste. **Fix:** `shlex.quote`
every token (or emit argv/JSON).

**H6 — tool/permission changes can be classified *minor*** · gpt55 · `scan.py:57,221`
`parse_frontmatter` drops block-style list values (`allowed-tools:` then indented
`- …`), so `signature_hash` is blind to them; a `Bash(rm *)` addition rides in as a
2-line body diff → *minor*. **Fix:** include the whole frontmatter block in the
signature, or make any frontmatter change material.

## MEDIUM / LOW (batchable)
- **M1** base-hash-unknown → pre-manifest adopters get spurious `.template-new` on
  first update (safe but noisy; withholds the update). *(fable M7)*
- **M2** `build-template.sh` hardcodes `sha256sum` (not on stock macOS) and writes the
  manifest non-atomically → partial template on failure. *(gpt55)*
- **M3** `build_ours` scans root `.claude` + plugins but **not** root `.codex` →
  codex-only capabilities missed in the gap "ours" set. *(fable)*
- **M4** gap normalized-name match can false-merge distinct caps. *(fable M9)*
- **M5** Inv-1 self-check won't catch a *misplaced* curation rule (wrong dir). *(fable M10)*
- **M6** "improved since adopted" provenance is brittle (single hash). *(fable M11)*
- **NITs** materiality denominator double-counts; settings hook-strip edge; tarfile
  `filter` fallback; `-newermt`/bash4/`-print0` are GNU-only (maintainer-side, fine);
  stale `.template-new` never cleaned; `upstream_ref` convoluted idiom; grep dot-regex.

## Recommended fix order
1. **Dedup identity (C1 + H1)** — biggest correctness hole; redefine logical identity
   (strip mirror-root prefixes; plugin name from manifest). Re-calibrate 182 holds.
2. **Stop the two silent data-losses (C3 beads, H3 SSH URL)** — both clobber user data.
3. **Template leak (C2)** — broaden the leak self-check + neutralize the sources.
4. **drift crash (H2)** + **injection (H5)** — one-liners each.
5. **Orphan-on-delete (H4)** + **materiality/permissions (H6)** — moderate.
6. Batch the MEDIUM/LOW.
