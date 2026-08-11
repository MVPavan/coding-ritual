# Reference-Harness Lifecycle — Round-2 Re-Review (Fable 5)

Adversarial re-review of the fixes committed for round 1
([synthesis](harness-lifecycle-review-synthesis.md),
[my round 1](harness-lifecycle-review-fable5.md)). Goal: (a) confirm each round-1
finding is genuinely fixed (not papered over), (b) find issues the fixes introduced.
Every verdict below is reproduced against the live tree at HEAD (`58eee58` /
mvp-harness `1b0ab86`); commands + observed output cited inline. Reviewer: Fable 5 @
xhigh. Independent of GPT-5.5. Nothing tracked was modified; fixtures ran under a
`/tmp` scratch dir and a scratch copy of the plugin.

## Round-1 verdicts

| # | Round-1 finding | Verdict | Evidence / caveat |
|---|---|---|---|
| C1 | plugin dedup collapses 39 → 1 | **FIXED** | `catalog claude-plugins-official` now reports **39 plugin / 39 logical**; names from `plugin.json`. **But** the fix regresses on the *root-level* `.claude-plugin` layout → new **N1 (HIGH)**. |
| H1 | same-name distinct caps over-merge | **FIXED** | `agent:plugins/feature-dev/agents/code-reviewer` vs `…/pr-review-toolkit/…` stay separate; `skill:…/{discord,imessage,telegram}/skills/access` = 3 caps; ECC still collapses 244 → **182** skills. |
| C2 | template ships project text | **FIXED** | `build-template.sh` self-check is now `grep -rnIi` (case-insensitive) + sweeps `bodha`/`orchestrators`; rebuild exits 0, `grep -i` of payload for project tokens is empty. Minor prose mangle → **N7 (LOW)**. |
| C3 | `/update` clobbers `.beads/beads.md` | **FIXED** | Routed through `copy_one` (three-way). Local edit survives update; both-changed → `.template-new`; pristine+upstream-change → clean update. Stamp written last (line 164) so all reads saw old base. |
| H2 | `drift` crashes on MCP body change | **FIXED** | Guard `"#" not in old.canonical_path` (line 515). Forced same-signature/diff-content MCP → `MATERIAL, "magnitude not computed"`, no `FileNotFoundError`. (MCP signature now hashes full config, so an MCP change is material regardless.) |
| H3 | SSH remote corrupted (`git@…`→`git.com`) | **FIXED** | `awk -v v=…` preserves `git+git@github.com:acme/app.git` verbatim (end-to-end adopt). Residual: awk still mis-handles `\`/`"`/newline in a value, but those never occur in real git URLs → **N6 (LOW)**. |
| H4 | deleted template files never retired | **FIXED** | Unmodified removed file deleted; locally-modified one kept + `WARN`. **But** new path-traversal in the `rm -f` → **N4 (MEDIUM)** and user-owned-blindness → **N5 (LOW)**. |
| H5 | `gap --beads` shell-injectable | **FIXED** | `shlex.quote` on title + description; hostile name `evil$(touch …)` emits inside single quotes, inert. |
| H6 | tool/permission change buckets as minor | **FIXED** | Signature hashes the full normalized frontmatter block; a block-style tool add → `MATERIAL`. **But** now over-sensitive to cosmetic frontmatter → **N3 (MEDIUM)**, and blind on unclosed frontmatter → **N8 (LOW)**. |

All eight round-1 bugs are genuinely fixed. The fixes introduced **1 HIGH + 3 MEDIUM
+ 5 LOW/NIT** new issues, below.

## Invariant re-check

| Inv | Verdict |
|---|---|
| 1 template ⊂ root, no leak | HOLDS — payload subset verified (every `template/{claude,codex}` path exists in root), self-check case-insensitive, no tokens survive. |
| 2 update never clobbers local edits | HOLDS for the reported case (`beads.md` now three-way). Watch N4 (retire can `rm` outside repo) / N5 (retire ignores user-owned). |
| 3 one-way copy | HOLDS. |
| 4 dedup only true dups | **RE-VIOLATED on our own side (N1):** our 3 plugins collapse to one `plugin:` in `build_ours`. |
| 5 materiality hides nothing | HOLDS (and now errs toward over-reporting — N3). One malformed-file blind spot (N8). |

---

## NEW / regressed findings

### HIGH

**N1 — root-level `.claude-plugin` collapses every plugin to `plugin:`; our 3 plugins → 1 in `build_ours`**
`harness_lifecycle/scan.py:286-311` (`_strip_leading_dots` + `dedup_key` PLUGIN branch)

`dedup_key` calls `_strip_leading_dots(parts)` *first*. When a plugin's manifest sits
at the scan root — `.claude-plugin/plugin.json` (parts `('.claude-plugin',
'plugin.json')`) — `_strip_leading_dots` eats the leading `.claude-plugin` segment
(it starts with `.`), leaving `('plugin.json',)`. The PLUGIN branch then tests
`".claude-plugin" in stripped` → **False** (it was just stripped) → falls to
`"/".join(stripped[:-1])` = `""`. So `dedup_key == ""` and `logical_id == "plugin:"`
for *every* root-level plugin.

Reproduced — each of our plugins scanned standalone yields the same key:
```
code-intel:    [('plugin:', 'code-intel')]
codex-adapter: [('plugin:', 'codex-adapter')]
mvp-plugin:    [('plugin:', 'mvp-plugin')]
```
`build_ours()` merges the per-plugin catalogs by `logical_id`; all three share
`plugin:`, so `merge_catalogs` keeps only the first (`code-intel`) and drops the other
two names:
```
$ python3 harness_lifecycle/gap.py ours | grep plugin
plugin             1         1          # we ship 3
```
Concrete failure: (a) our own plugin inventory is under-counted 3→1 — a direct
Invariant-4 violation (distinct capabilities merged); (b) `codex-adapter` and
`mvp-plugin` vanish from the gap "ours" normalized-name index, so a reference harness
that shipped a plugin named `codex-adapter` or `mvp-plugin` would be falsely reported
as a **gap** we don't have. Reference-side the collapse is only cosmetic (a repo can
hold at most one root-level `.claude-plugin`, e.g. superpowers/mattpocock each read as
`plugin:`), but the `build_ours` merge is where distinct plugins actually coalesce.

This is exactly the class of over-merge C1 was meant to kill, re-created for the
root-level layout by ordering `_strip_leading_dots` ahead of the `.claude-plugin`
test.

Fix: detect the plugin's `.claude-plugin` on the *raw* `parts` before stripping mirror
roots — e.g. `if ".claude-plugin" in parts: idx = parts.index(".claude-plugin");
return "/".join(parts[:idx]) or _plugin_name_or_root`. When `idx == 0`, key on the
repo/plugin dir name (or the `plugin.json` `name`) instead of the empty string, so
each root-level plugin gets a distinct identity. (Note `merge_catalogs` first-wins
also silently discards the losing plugin's `name`/`canonical_path`; keying correctly
removes the collision so this never fires.)

---

### MEDIUM

**N2 — path-based `logical_id` makes the ledger + drift unstable across upstream path moves**
`harness_lifecycle/scan.py:297-311` (`dedup_key`) → `harness_lifecycle/gap.py:238`
(ledger keyed on `(ref.repo, logical_id)`)

The C1/H1 fix made `logical_id` embed the (mirror-stripped) *path* instead of the bare
leaf name. That fixes over-merge but makes identity path-dependent: any upstream
directory move that keeps the leaf name now changes the id. Reproduced with a fixture
that moved `skills/alpha` → `plugins/core/skills/alpha`:
```
### ADDED (material)    + skill:plugins/core/skills/alpha
### REMOVED (material)  - skill:skills/alpha
```
A single relocated skill reads as **remove + add** (two material lines) rather than a
move. Downstream this breaks the ledger: an entry recorded as `adopted
skill:skills/alpha` no longer matches after the move, so `compute_gap`
(`gap.py:238`) treats the relocated capability as an un-ledgered **fresh gap** and
re-nags, and the "⚑ upstream improved since we adopted" alert can never fire for it
again. Under the old leaf-name scheme a leaf-preserving move stayed the same id (its
own bug: it also merged genuinely-distinct same-leaf caps). So this is a real
correctness *tradeoff* the fix took on, not a pure win — and it lands on the ledger,
whose entire job is to stop re-nagging.

Fix (either): (a) accept it and document that upstream reorgs invalidate ledger
entries (add a migration/alias path — `aliases.json` can already remap an old
`logical_id` to a new one, so surface that in the drift "REMOVED/ADDED" output as a
suspected rename when content hashes match); or (b) key the ledger on
`(repo, kind, content_hash)` or `(repo, name)` in addition to `logical_id` so a pure
move is recognized. At minimum, `drift` should pair an ADDED+REMOVED with equal
`content_hash` and report it as a rename, not two independent changes.

**N3 — H6 signature is now over-sensitive: cosmetic frontmatter edits read as MATERIAL "surface changed (name/description/tools)"**
`harness_lifecycle/scan.py:314-330` (`_raw_frontmatter`), `:360-365` (`_signature_hash`), reason at `:510`

Hashing the whole normalized frontmatter block catches block-style tool lists (the H6
goal — verified) but also flips the signature on edits that change nothing semantic,
because `normalize()` only unifies newlines and strips *trailing* whitespace — it does
not sort keys, canonicalize indentation, or drop blank/comment lines. Reproduced (300-
line body so body-diff can't mask it):
```
add block tool     -> material  "surface changed (name/description/tools)"   # correct
fm key reorder      -> material  "surface changed (name/description/tools)"   # cosmetic!
fm list re-indent   -> material  "surface changed (name/description/tools)"   # cosmetic!
fm blank line added -> material  "surface changed (name/description/tools)"   # cosmetic!
```
So a purely cosmetic frontmatter reflow upstream (reordered keys, re-indented list, a
bumped `version:` field, an added comment) is reported as a *surface* change with a
label that literally claims name/description/tools changed when they did not. This
never *hides* a real change (Invariant 5 is safe — it errs toward material), but it
defeats the point of materiality: it inflates the "material" bucket with noise and
mislabels it, so the model is told to re-read capabilities whose invocation surface is
unchanged.

Fix: build the signature from *parsed* frontmatter — sort keys, and for list values
compare the set/sequence of trimmed items — rather than a raw block hash; or keep the
raw-block hash only for the keys that define the surface (`name`, `description`,
`allowed-tools`/`tools`/`permissions`) and normalize each. Keep the block-list
sensitivity, drop the whitespace/ordering sensitivity.

**N4 — H4 retire loop `rm -f`s outside the target repo (stamp path-traversal, no containment check)**
`mvp-harness/plugins/mvp-plugin/scripts/install-harness.sh:151-163`

The new retire loop reads paths from the target's own stamp
(`.harness-manifest.txt`) and deletes `"$TARGET/$(hp_to_dotted "$orel")"` when the
local hash matches the recorded hash. `hp_to_dotted` passes through anything that
isn't a `claude/`/`codex/`/`beads/` prefix, and there is no check that the resolved
path stays inside `$TARGET`. Reproduced by planting one line in the stamp:
```
printf '../VICTIM.txt\t<sha>\n' >> target/.harness-manifest.txt
# update run:
  OK   ../VICTIM.txt (retired; removed from harness)
d) VICTIM.txt outside target: DELETED-BY-TRAVERSAL
```
The stamp is normally harness-generated (paths are `find "$TPL"`-relative, so no `..`),
which bounds real-world risk — but the stamp is a plain, committed file, so a
malicious/careless PR that edits `.harness-manifest.txt` (plus a matching-hash file at
the traversal target) turns `/mvp-plugin:update` into an arbitrary `rm -f` outside the
repo. `rm -f` with a file-content-driven path and no containment is unsafe by
construction.

Fix: reject any `orel` that is absolute or contains a `..` segment; resolve `odst` and
assert it is under `$TARGET` (e.g. `case "$odst" in "$TARGET"/*) ;; *) continue ;;
esac` after normalizing) before deleting.

---

### LOW / NIT

**N5 — retire loop ignores `hp_is_user_owned`; a pristine user-owned file dropped from the payload would be deleted**
`install-harness.sh:151-163`. The delete branch checks only `local hash == old base`,
not ownership. Reproduced: dropping `CLAUDE.md` from the template deleted the target's
`CLAUDE.md` ("retired"). Unreachable today (build-template always emits
CLAUDE.md/AGENTS.md/settings.json, so they're always in the new manifest and never
retired), but it contradicts the "user-owned never removed by the tool" contract. Fix:
`hp_is_user_owned "$orel" && continue` at the top of the retire body.

**N6 — `ensure_yaml_key` awk still mangles `\`, `"`, and embedded newlines in a value**
`install-harness.sh:115-119`. `awk -v v=…` applies C-style escape processing to the
assignment, and the emitted value is not YAML-escaped. Probes: `a\nb` → the value
splits across two lines (broken YAML); `a\\b` → collapses to `a\b`; `we"ird` → the
embedded `"` closes the quoted scalar early. None occur in real SSH/HTTPS git remotes,
so the round-1 bug (`@host`) is genuinely fixed; this is a latent robustness gap. Fix:
`awk` with the value via `ENVIRON` (`export v; awk '…ENVIRON["v"]…'`) to skip `-v`
escape processing, and escape `"`/`\` for the double-quoted scalar (or emit a
single-quoted YAML scalar with `''` doubling).

**N7 — leak sweep mangles legitimate prose**
`build-template.sh:136` (`s/\borchestrators\b/the parent repo/gi`). Source
"…from the parent orchestrators repo." ships as "…from the parent **the parent repo**
repo." into every adopted repo (reproduced in the rebuilt payload). No token leaks;
purely a readability wart. Fix: neutralize the phrase at source, or make the
substitution phrase-aware (`s/\bparent orchestrators repo\b/parent repo/`).

**N8 — H6 is blind to tool changes in a file with *unclosed* frontmatter**
`harness_lifecycle/scan.py:314-330`. `_raw_frontmatter` returns `""` when there is no
closing `---`, so a tool addition in a malformed (unterminated) frontmatter rides in as
a body diff → `minor`. Reproduced: unclosed-fm file + `- WebFetch` added → `minor body
edit (~1 lines)`. Malformed skills are unusual, but this is the one gap in H6's "any
tool change is material" promise. Fix: if the block never closes, treat the whole file
tail from the opening `---` as the surface, or flag unterminated frontmatter as
material.

**N9 — mid-path per-tool mirror roots are not collapsed (under-merge)**
`harness_lifecycle/scan.py:286-294`. `_strip_leading_dots` only strips *leading* dot
segments, so identical mirrors under a *nested* tool root —
`plugins/x/.claude/skills/bar` vs `plugins/x/skills/bar` (same content) — read as two
logical caps. Reproduced with a fixture. No current reference repo nests its
per-tool mirrors this way (ECC's are top-level `.kiro/.agents/…`), so latent. Fix: strip
recognized tool-root segments (`.claude`, `.kiro`, `.cursor`, `.agents`) at any depth
when the following segment is a kind dir, rather than only at position 0.

**NITs (carried from round 1, not regressions):** L12 `_change_ratio` still divides by
`len(old)+len(new)` (halves the ratio; small semantic edits read minor) —
`scan.py:492`. L17 `*.template-new` still not in the adopt `.gitignore` block —
`install-harness.sh:142`. L16 staleness hook still uses GNU `find -newermt` (root-only
maintainer hook). None block anything.

---

## Top 3 still worth fixing

1. **N1 (HIGH) — root-level `.claude-plugin` collapses our 3 plugins to one `plugin:`.**
   The C1 fix works for nested plugins (39 distinct) but re-introduces the exact
   over-merge for the root-level layout, and it bites our *own* harness in
   `build_ours` (plugin count 3→1; two plugin names dropped from the gap index). Test
   the plugin id on raw `parts` before stripping mirror roots, and give an `idx==0`
   plugin a real name key.
2. **N2 (MEDIUM) — path-based `logical_id` desyncs the ledger on upstream moves.** A
   leaf-preserving directory move now reads as remove+add and orphans the ledger
   entry (re-nag + dead "improved" alert). Recognize renames by equal `content_hash`
   in `drift`, and/or key the ledger with a move-tolerant identity.
3. **N4 (MEDIUM) — retire loop can `rm -f` outside the repo.** Add a containment check
   (reject `..`/absolute; assert resolved path under `$TARGET`) before deleting, and
   skip `hp_is_user_owned` paths (N5). Same-severity runner-up: N3 (materiality
   over-reports cosmetic frontmatter as a mislabeled "surface change").

Net: the round-1 fixes are real and verified. The remaining risk has shifted from
"silent data loss / crashes" to "identity-model edges (N1/N2) and an unbounded
`rm` (N4)."
