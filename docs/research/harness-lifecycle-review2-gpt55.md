| Round-1 finding | Verdict | Evidence |
|---|---|---|
| C1/H1 dedup over-merge | PARTIAL | Plugin same-name skills stayed separate and `everything-claude-code` skills stayed `182`; but non-mirror hidden roots still over-merge and pure moves churn IDs. |
| C2 template leak | PARTIAL | Current payload has no banned token hits, but the self-check is still case-sensitive and the sweep already mangled prose. |
| C3 `.beads/beads.md` clobber | FIXED | Re-run kept a local edit and reported `.beads/beads.md (kept local edit; core unchanged)`. Stamp is written after three-way reads. |
| H2 MCP drift crash | FIXED | MCP `#server` body change no longer crashes; probe returned material change instead of `FileNotFoundError`. |
| H3 SSH URL corruption | PARTIAL | `git@github.com:...` is preserved; quotes/backslashes are still corrupted in YAML output. |
| H4 orphan retire | PARTIAL | Normal unchanged/modified retire behavior works; malformed old manifests can delete outside the target repo. |
| H5 `--beads` injection | FIXED | `shlex.quote` protects `$(...)`, quotes, and embedded single quotes in emitted `bd create` lines. |
| H6 materiality | PARTIAL | Block-style tool changes are material; cosmetic frontmatter whitespace/key reorder is also material noise. |

## NEW / Regressed Findings

### HIGH

1. Location: [install-harness.sh](/data/codes/coding-ritual/mvp-harness/plugins/mvp-plugin/scripts/install-harness.sh:152)  
What can go wrong: a malicious or corrupted `.harness-manifest.txt` can delete files outside the target repo.  
Why vulnerable: orphan retirement trusts `orel`, maps it with `hp_to_dotted`, and runs `rm -f "$TARGET/$(hp_to_dotted "$orel")"` with no path normalization or containment check.  
Concrete scenario: probe used manifest entry `../victim.txt<TAB><hash>`; `/tmp/.../victim.txt` was deleted and output said `../victim.txt (retired; removed from harness)`.  
Impact: data loss outside the adopted repo during `/update`.  
Severity: HIGH.  
Fix: reject absolute paths, `..`, empty segments, and paths resolving outside `$TARGET`; only retire paths present in a validated prior manifest format.

2. Location: [scan.py](/data/codes/coding-ritual/harness_lifecycle/scan.py:286)  
What can go wrong: distinct capabilities under non-mirror hidden roots collapse into one logical capability.  
Why vulnerable: `_strip_leading_dots()` strips every leading dot directory, not only known mirror roots.  
Concrete scenario: `.claude/skills/deploy/SKILL.md` and `.internal/skills/deploy/SKILL.md` scanned as one `skill:skills/deploy` with two variant hashes.  
Impact: drift/gap can hide distinct capabilities, violating “dedup only true dups.”  
Severity: HIGH.  
Fix: whitelist mirror roots (`.claude`, `.cursor`, `.kiro`, etc.) and preserve unknown hidden namespaces.

### MEDIUM

3. Location: [scan.py](/data/codes/coding-ritual/harness_lifecycle/scan.py:48)  
What can go wrong: legitimate nested capabilities under category dirs named `docs`, `test`, `build`, etc. are dropped before classification.  
Why vulnerable: `_iter_files()` excludes any path segment in `EXCLUDE_SEGMENTS`.  
Concrete scenario: real file `reference_harnesses/compound-engineering-plugin/plugins/compound-engineering/agents/docs/ankane-readme-writer.md` is excluded and absent from the catalog.  
Impact: gap/drift silently misses capabilities.  
Severity: MEDIUM.  
Fix: make exclusions context-aware; do not exclude reserved words once inside `skills/`, `commands/`, `agents/`, `rules/`, or `hooks/`.

4. Location: [build-template.sh](/data/codes/coding-ritual/mvp-harness/plugins/mvp-plugin/scripts/build-template.sh:143)  
What can go wrong: case variants of project tokens can ship despite the comment claiming case-insensitive checks.  
Why vulnerable: `grep -rnIi -- "$1"` lacks `-i`; `check 'Bodha'` does not match `BODHA_SECRET`.  
Impact: no-leak invariant is not enforced for future case variants.  
Severity: MEDIUM.  
Fix: use `grep -rniI` with explicit token regexes, and include underscore/compound cases in the leak patterns.

5. Location: [scan.py](/data/codes/coding-ritual/harness_lifecycle/scan.py:303)  
What can go wrong: moving an unchanged skill reports as remove+add.  
Why vulnerable: logical IDs are path-derived after mirror stripping.  
Concrete scenario: `skills/foo/SKILL.md` moved to `tooling/skills/foo/SKILL.md` produced `removed ['skill:skills/foo']` and `added ['skill:tooling/skills/foo']`.  
Impact: drift/ledger continuity breaks and old adoption decisions resurface.  
Severity: MEDIUM.  
Fix: detect same-signature remove/add pairs as moves, or use namespace plus declared name as the stable identity.

### LOW

6. Location: [install-harness.sh](/data/codes/coding-ritual/mvp-harness/plugins/mvp-plugin/scripts/install-harness.sh:115)  
What can go wrong: unusual remote values still corrupt `.beads/config.yaml`.  
Why vulnerable: awk prints `sync.remote: "` + raw value + `"`; quotes are not escaped, and backslashes passed through `awk -v` are interpreted.  
Concrete scenario: `path"withquote.git` emits invalid YAML; `path\withbackslash.git` became `pathwithbackslash.git`.  
Impact: broken Beads sync for edge-case but valid-looking remote strings.  
Severity: LOW.  
Fix: write YAML via a real serializer or escape `\` and `"` before printing.

7. Location: [report-set.md](/data/codes/coding-ritual/mvp-harness/plugins/mvp-plugin/template/codex/skills/codebase-architecture-research/references/report-set.md:53)  
What can go wrong: shipped template prose is corrupted.  
Why vulnerable: broad `orchestrators` replacement rewrote source text into `parent the parent repo repo`.  
Impact: low-level documentation regression in adopted templates.  
Severity: LOW.  
Fix: replace exact project-specific phrases before generic tokens, or maintain generic source text instead of sweeping.

8. Location: [scan.py](/data/codes/coding-ritual/harness_lifecycle/scan.py:314)  
What can go wrong: cosmetic frontmatter edits become material drift.  
Why vulnerable: `_raw_frontmatter()` hashes the normalized raw block, so blank-line/key-order churn changes the signature.  
Impact: noisy material drift reports.  
Severity: LOW.  
Fix: canonicalize frontmatter semantically enough for lists/maps, or ignore blank lines and stable-sort known scalar/list keys.

Verification run: `bash -n` passed for the three target shell scripts plus the staleness hook; Python syntax parse passed for `scan.py` and `gap.py`; `gap.py ours` ran and reported 71 logical capabilities. `git status --short` showed pre-existing untracked files under `docs/plans/`, `docs/research/`, and `docs/usage/`.

Top 3 still worth fixing: path containment before orphan `rm -f`; dot-root dedup whitelist plus move detection; context-aware scanner exclusions.
