# Reference-Harness Lifecycle — Adversarial Code Review (Fable 5)

Scope: `harness_lifecycle/scan.py`, `harness_lifecycle/gap.py`, the mvp-plugin
scripts (`install-harness.sh`, `build-template.sh`, `lib/common.sh`,
`template-exclude.txt`), and the root-only Claude surface. Every finding below was
reproduced against the live tree or the checked-in reference harnesses; commands and
observed output are cited inline. Reviewer: Fable 5 @ xhigh. Independent of GPT-5.5.

Invariant verdicts up front:
- **Invariant 1 (template is a strict subset, no curation/repo-specific leak): HOLDS today, but enforcement is convention-only (MEDIUM gap below).**
- **Invariant 2 (`/update` never overwrites a user's local edit to a core file): VIOLATED — `.beads/beads.md` (CRITICAL-2).**
- **Invariant 3 (copy is one-way): HOLDS.**
- **Invariant 4 (dedup collapses only true duplicates, never merges distinct capabilities): VIOLATED — plugins (CRITICAL-1) and same-name-cross-plugin caps (HIGH-3).**
- **Invariant 5 (materiality separates signal from noise without hiding real edits): mostly holds; one downranking edge (LOW-12).**

---

## CRITICAL

### C1 — `canonical_name` collapses every plugin into one logical capability `plugin:.claude-plugin`
`harness_lifecycle/scan.py:262` (`canonical_name`, `Kind.PLUGIN` branch)

Problem: for a plugin the identity is taken as `parts[-2]`, but the path is always
`.../<plugin>/.claude-plugin/plugin.json`, so `parts[-2]` is the literal
`.claude-plugin` for **every** plugin. All plugins share `name == ".claude-plugin"`
→ logical_id `plugin:.claude-plugin` → they are deduped into a single capability.

Failure scenario (reproduced):
```
$ python3 harness_lifecycle/scan.py catalog reference_harnesses/claude-plugins-official
# 39 plugin.json files on disk -> scanner reports:
#   logical_id: plugin:.claude-plugin | name: .claude-plugin | #paths: 39 | #distinct hashes: 39
```
39 distinct plugins (asana, context7, discord, mongodb, …), all with **different
content** (39 distinct hashes), collapse into ONE logical capability. This is a
direct Invariant-4 violation and silent data loss: `catalog` reports 1 plugin where
there are 39; `diff`/`drift` shows any change to any of the 39 as a single
`~ plugin:.claude-plugin`; `gap` surfaces at most one plugin candidate, so the user
is never told about 38 of them. The ledger key `(repo, plugin:.claude-plugin)` also
cannot distinguish plugins, so no per-plugin adopt/reject decision is possible.

Fix: identify a plugin by the directory that *contains* `.claude-plugin`, i.e.
`parts[-3]` (with a length guard), or read the `name` field from `plugin.json`.
Prefer the manifest `name` when present, fall back to the containing dir.

### C2 — `/mvp-plugin:update` unconditionally overwrites a user's edited `.beads/beads.md`
`mvp-harness/plugins/mvp-plugin/scripts/install-harness.sh:130`

Problem: `beads/beads.md` is excluded from the three-way copy loop
(`find … -not -path "$TPL/beads/*"`, line 69) and from the manifest
(`build-template.sh:159`). It is instead copied with an unconditional
`cp "$TPL/beads/beads.md" "$TARGET/.beads/beads.md"` on **every** run. There is no
base/local/new comparison and no `.template-new` fallback, so a repo owner's local
edits to their beads policy doc are silently destroyed on re-adopt/update.

Failure scenario (reproduced in a scratch repo):
```
# after adopt, user edits their policy doc:
$ echo "LOCAL-BEADS-POLICY-EDIT" >> repo/.beads/beads.md
# re-run install-harness.sh (== /mvp-plugin:update)
$ grep -c LOCAL-BEADS-POLICY-EDIT repo/.beads/beads.md
0     # CLOBBERED
```
This violates Invariant 2 verbatim: "must NEVER overwrite a user's local edit to a
core file." `beads.md` is shipped harness core that owners routinely customize.

Fix: route `beads/beads.md` through `copy_one` like every other payload file
(include it in the find loop and the manifest), or classify `.beads/beads.md` as
user-owned in `hp_is_user_owned` and only write it when absent.

---

## HIGH

### H3 — Same leaf-name capabilities in different plugins/tools are merged as one
`harness_lifecycle/scan.py:250-263` (`canonical_name`) + `:377-395` (logical grouping)

Problem: dedup key is `f"{kind}:{name}"` where `name` is only the leaf (skill dir,
command/agent/rule tail). It carries no plugin/namespace, so two genuinely distinct
capabilities that happen to share a leaf name collapse — the exact thing Invariant 4
forbids. The scanner cannot distinguish a per-tool *mirror* (`.kiro/skills/foo` vs
`skills/foo`) from two *different* skills named `foo` in two different plugins.

Failure scenario (reproduced):
```
$ python3 harness_lifecycle/scan.py catalog reference_harnesses/claude-plugins-official
agent:code-reviewer   -> merged: plugins/feature-dev/agents/code-reviewer.md
                                  plugins/pr-review-toolkit/agents/code-reviewer.md
skill:access          -> merged: external_plugins/{discord,imessage,telegram}/skills/access/SKILL.md
```
feature-dev's code-reviewer and pr-review-toolkit's code-reviewer are different
agents (2 distinct hashes) reported as one; discord/imessage/telegram `access` are
three different channel-access skills reported as one. Description/body shown is
whichever path sorts first (`min(group, key=(rank, relpath))`). `gap` under-reports:
if only one of the merged pair matches ours, the others are silently marked covered.

Fix: include the owning plugin (dir containing `.claude-plugin`, or the
`plugins/<x>/` segment) in the logical_id, or only treat copies as mirrors when
their normalized content hashes match; keep same-name/different-content as distinct.

### H4 — `scan.py drift` crashes (FileNotFoundError) on an MCP body-only change
`harness_lifecycle/scan.py:457-458` (`classify_change`), with `:336` and `:391`

Problem: an MCP capability's `canonical_path` is stored as `"<file>#<server>"`
(`relpath=f"{rel}#{server_name}"`). When a server's config body changes but its
signature (`command`/`url`/`type`) does not, `classify_change` takes the on-disk
body-size branch and calls `read_text(new_root / new.canonical_path)` — literally
`.../mcp.json#servername`, which is not a real file → uncaught `FileNotFoundError`.
`diff` (catalogs only) is safe because it never touches the disk; `drift` is not.

Failure scenario (reproduced with a synthetic mcp.json whose `args` grew while
`command` stayed `"node"`):
```
CRASH: FileNotFoundError [Errno 2] No such file or directory: '.../old/srv/mcp.json#s'
```
Any real upstream MCP change that touches args/env/headers (very common) aborts the
whole `drift` run for that submodule — no partial report. `/harness-status` loops
drift per-submodule, so it survives for other repos but reports nothing for this one.

Fix: strip the `#server` fragment before reading (`canonical_path.split("#", 1)[0]`),
or store a separate real file path for body comparison; for MCP, size the change
from the catalog’s recorded `line_count`/hash rather than re-reading the file.

### H5 — `ensure_yaml_key` corrupts SSH git remotes: `git@github.com` → `git.com`
`mvp-harness/plugins/mvp-plugin/scripts/install-harness.sh:117` (called at `:133`)

Problem: the "key exists" branch runs
`perl -pi -e "s{^\Q${key}\E:.*}{${key}: \"${val}\"}g"`. The shell substitutes
`${val}` into the perl replacement, and then **perl** interpolates the
double-quoted replacement string. Any `@word` in the URL is read as a Perl array and
expands to empty. Every SSH-form remote (`git@host:org/repo.git`) loses `@host`.

Failure scenario (reproduced end-to-end in a scratch repo whose `origin` is
`git@github.com:acme/app.git`):
```
$ grep sync.remote repo/.beads/config.yaml
sync.remote: "git+git.com:acme/app.git"     # host silently deleted
```
beads sync is now pointed at a nonexistent remote; the failure only surfaces later,
far from adopt. HTTPS remotes (no `@`) are unaffected, which makes this
intermittent and easy to miss. (Also `grep -qE "^${key}:"` at :116 treats the `.`
in `sync.remote` as a regex wildcard — separate NIT.)

Fix: do not interpolate the value inside a perl double-quoted string. Pass it via
`-s`/env and use a non-interpolating replacement, or use `python3`/`awk` with the
value as a literal argument, or `sed` with the value escaped. Add a test with an
`@`-bearing URL.

### H6 — Capabilities deleted from the template are never removed from an adopted repo
`mvp-harness/plugins/mvp-plugin/scripts/install-harness.sh:42-69` (copy loop; no deletion)

Problem: the installer only ever creates/updates files. When upstream curation drops
a skill/rule/command from the template, `/update` leaves the old file in the adopted
repo forever. Orphaned skills keep being auto-loaded by Claude Code; a removed rule
keeps applying.

Failure scenario (reproduced): adopt, then delete `template/claude/skills/ak-guide`
and its manifest line, re-run:
```
orphan after template deletion? SKILL.md  >>> ORPHAN LEFT IN ADOPTED REPO
```
No warning is emitted; the count summary says "0 new, 0 core updated". The adopted
repo silently diverges upward from the template with dead capabilities.

Fix: after copying, diff the previous stamp against the new manifest; for each path
present in the old stamp but absent from the new manifest, and unchanged locally
(local hash == old stamp hash), remove it (and warn if locally edited). At minimum,
report orphans so a human can prune them.

---

## MEDIUM

### M7 — "base hash unknown" turns every legitimate core update into a spurious conflict
`mvp-harness/plugins/mvp-plugin/scripts/install-harness.sh:56-65` (`copy_one`)

Problem: when there is no stamp entry for a file (a repo adopted *before* the
manifest feature, a fresh clone that never stamped, or an install interrupted before
line 77 writes the stamp), `hp_base_hash` returns empty. With `base_hash` empty,
both "untouched locally → update" (:57) and "core unchanged → keep local" (:60)
are skipped, so any file whose template content changed falls through to the
conflict branch (:63): it writes `.template-new`, keeps the local copy, and warns
"local edit kept" — even though the user never edited it.

Failure scenario: an existing adopter runs `/update` after this feature ships and
after any template change. Every changed core file is reported as a BOTH-changed
conflict, litters `.template-new` files, and — critically — the real update is
**withheld** (`overwritten` stays 0). The harness silently fails to update and blames
the user for edits they didn't make.

Fix: when `base_hash` is empty, fall back to a safer default — treat local==new as
up-to-date (already handled) and, for local!=new, prefer applying the update only if
the local file still matches a known-shipped hash from *any* prior manifest; else
warn but do not fabricate a conflict. Or backfill a stamp from the current template
on first post-feature run with an explicit "assuming pristine" notice.

### M8 — `gap --beads` emits shell-injectable `bd create` lines from third-party names
`harness_lifecycle/gap.py:265-271` (`render_gap`)

Problem: the `bd create` lines interpolate `gap.cap.name`, `gap.cap.description`,
`ref.repo`, and `canonical_path` into a double-quoted shell command with no escaping.
Capability names come from upstream frontmatter (`parse_frontmatter` only strips
surrounding quotes; backticks, `$(...)`, `;`, `"` survive), i.e. attacker-influenced
data from arbitrary reference repos the tool is designed to scan.

Failure scenario (reproduced with a benign payload):
```
$ # capability name = ok" ; touch INJECTED ; echo "
bd create --title="Evaluate skill 'ok" ; touch INJECTED ; echo "' from evil" --description=...
```
The `"` closes the title and `; touch INJECTED ;` becomes a separate command if the
user copy-pastes the "review before running" block. A malicious or careless upstream
skill name executes code on the maintainer’s machine.

Fix: shell-quote every interpolated field (`shlex.quote`), or emit the `bd create`
args as a JSON/argv array, or write them to a file the user runs via `xargs -0`.
Never build shell from untrusted names.

### M9 — Normalized-name matching can false-merge two distinct capabilities
`harness_lifecycle/gap.py:110-133` (`_normalize_name`, `match_to_ours`)

Problem: `_normalize_name` strips all non-alphanumerics and lowercases, so
`code-review`, `codereview`, and `Code Review` all key to `codereview`. A reference
capability is considered "covered" if `(kind, normalized_name)` exists in ours —
even when the two are unrelated. There is no content check. Symmetrically,
`_normalized_index` (`:114-118`) keeps only the last of any of OUR caps that
normalize equal (`index[...] = cap.logical_id`), silently choosing one target.

Failure scenario: reference ships `skill:code-review` (a review workflow); ours has
`skill:codereview` (something unrelated). `gap` reports the reference skill as
covered and never surfaces it — a hidden real gap. Not observed in the current six
repos (the two live normalized-only matches — `python-coding-style`→`python/coding-style`,
`python-testing`→`python/testing` — are correct), so this is a latent design risk,
not a current miss.

Fix: treat a normalized-only match as a *hint* requiring confirmation (like fuzzy),
not an automatic cover; or require kind+normalized match *and* a curated alias for
non-exact matches. At least warn when a normalized match has a very different raw name.

### M10 — Invariant-1 (no curation leak) is enforced by naming convention only; the leak self-check won't catch a misplaced curation rule
`mvp-harness/plugins/mvp-plugin/scripts/build-template.sh:56-60,144-152` +
`template-exclude.txt`

Problem: curation tooling is kept out of the template by `template-exclude.txt`
patterns keyed on the `harness-*` name and the `rules/harness-lifecycle/` path. The
build's leak self-check (`:144-151`) greps only for specific tokens (`Bodha`,
`gascity`, machine paths, `reference_harnesses`, `harness_learnings`, and the single
string `harness-staleness`). There is **no** general check that a curation capability
didn't ship. If a future curation rule is placed outside `rules/harness-lifecycle/`
(e.g. `rules/core/harness-audit.md`), or a curation doc/skill is added that doesn't
match a `harness-*` exclude pattern, it ships into every adopted repo and the build
still prints "OK: no project/machine-specific strings".

Failure scenario: maintainer adds `.claude/rules/core/harness-audit.md`; rsync
excludes only `/rules/harness-lifecycle/`, so the file is mirrored into
`template/claude/rules/core/`; self-check greps don't include it → silent
Invariant-1 leak.

Fix: add a structural self-check that fails if any `template/**/harness-*` path or
any `rules/harness-lifecycle/` content exists in the payload, and assert the template
capability set is a subset of root minus the documented excludes (diff the two
`gap.py`-style catalogs in the build).

### M11 — "improved since adopted" ledger alerts are provenance-fragile (false pos + false neg)
`harness_lifecycle/gap.py:227-233` (`compute_gap`) + `:306-313` (`cmd_ledger add`)

Problem: `source_content_hash` is recorded at `ledger add` time only if
`catalogs/<repo>.json` exists, using that catalog's hash. The later `gap` run
compares against `cap.content_hash` computed from whatever reference the user passed
(`reference_harnesses/<name>` working tree, a `catalogs/<name>.json`, or a bare name).
Nothing guarantees the two hash sources are the same snapshot.

Failure scenarios:
- False positive: adopt was ledgered from a stale `catalogs/<repo>.json`, but `gap`
  is later run against the *working tree* (newer). Hashes differ with no real
  "improvement" — the ⚑ alert fires spuriously.
- False negative: no `catalogs/<repo>.json` existed at `add` time → no
  `source_content_hash` stored → the "upstream improved what we adopted" alert can
  never fire for that entry, defeating the feature.
- Key mismatch: matching is on `(ref.repo, logical_id)`; `ref.repo` is the dir name
  when scanning a path but the stored `repo` field when reading a catalog. A name
  drift silently disables both gap-exclusion and the improved-alert.

Fix: record `source_content_hash` from the *same* resolution path the gap uses
(scan the reference at add time rather than trusting a possibly-stale catalog), store
the source commit alongside, and warn when a ledgered adopt has no recorded hash.

---

## LOW

### L12 — Materiality ratio uses (old+new) as denominator, halving it; small semantic edits read as "minor"
`harness_lifecycle/scan.py:433,460`

`_change_ratio` divides changed lines by `len(old)+len(new)`, roughly halving the
ratio, and the material threshold is `changed > 15 or ratio > 0.10`. A 2-line logic
change to a 20-line skill → `changed≈4`, `ratio≈0.10` → **not** material. It still
appears in the "minor" section (so not fully hidden — Invariant 5 mostly holds), but
a semantically important small edit is downranked below reformatting noise. Fix:
compute ratio against `max(len(old), len(new))`, and/or never downrank a body change
whose diff touches known signal lines.

### L13 — settings.json hook-strip drops the whole hook *group* if any one hook is `harness-*`
`mvp-harness/plugins/mvp-plugin/scripts/build-template.sh:85-91`

The filter keeps a group only if *no* hook in it matches `"harness-"`. A group that
co-locates a curation hook with a legitimate one (`[bd-prime, harness-staleness]`)
would be dropped entirely, silently removing `bd-prime` from the template. Currently
the root keeps them in separate groups so it's latent, but the design is a footgun.
Fix: filter per-hook within the group, delete the group only when it becomes empty.

### L14 — tarfile extraction falls back to no-filter on Python <3.12 backport, re-opening path traversal
`harness_lifecycle/scan.py:594-597`

`tar.extractall(dest, filter="data")` guards traversal, but the `except TypeError:
tar.extractall(dest)` fallback (for interpreters without the `filter` kwarg) extracts
with no protection. Sources are trusted git archives so exploitability is low, but
the fallback silently drops the safety the primary path adds. Fix: on the fallback,
validate member names (reject absolute/`..`) before extracting.

### L15 — Build tooling is GNU/bash4-only; a maintainer on stock macOS can't rebuild the template
`build-template.sh:161` (`sha256sum`) and `check-sync.sh:28` (requires bash ≥ 4)

`build-template.sh` hardcodes `sha256sum` for the manifest (macOS ships `shasum`),
and its final advisory step invokes `check-sync.sh`, which hard-dies on bash < 4
(macOS default is 3.2). The *install* side is portable via `hp_hash`, but template
regeneration is Linux-centric. Fix: reuse `hp_hash` from `common.sh` in
build-template, and gate/soften the check-sync bash-4 requirement.

### L16 — Staleness nudge uses GNU `find -newermt '30 days ago'`; on BSD/macOS it errors and nudges every session
`.claude/hooks/harness-staleness-nudge.sh:9`

`-newermt` with a relative English date is a GNU extension; BSD/macOS `find` fails
(stderr hidden by `2>/dev/null`), yielding empty output, so `[ -z … ]` is true and
the nudge prints on **every** session regardless of catalog age. Root-only hook, so
adopted repos are unaffected — impact is limited to a macOS maintainer. Fix: compute
the 30-day cutoff portably (e.g. compare `stat`/`date` epochs) or `find -mtime +30`.

### L17 — Stale `.template-new` files are never cleaned and not gitignored
`mvp-harness/plugins/mvp-plugin/scripts/install-harness.sh:63`

Once a conflict writes `<file>.template-new`, nothing removes it after the user
resolves the conflict, and the harness `.gitignore` block (`:143`) doesn't cover it,
so `git add -A` can commit stray `.template-new` artifacts. Fix: gitignore
`*.template-new` and/or remove it on the next run when local==new.

### L18 — A skill/agent/rule dir literally named a reserved segment is silently excluded
`harness_lifecycle/scan.py:48-51,297`

`EXCLUDE_SEGMENTS` matches any path *segment* named `test`, `tests`, `build`,
`dist`, `examples`, `docs`, `venv`, etc. A skill at `skills/test/SKILL.md` or a rule
under `rules/examples/` is dropped with no signal. Not present in the current six
repos, so latent. Fix: scope exclusions to top-level or well-known vendor roots, or
exclude by (segment AND not immediately under a kind dir).

---

## NIT

- **N19** `install-harness.sh:116` — `grep -qE "^${key}:"` treats the `.` in
  `sync.remote` as a wildcard; harmless today but wrong. Use `grep -qF` on the exact
  prefix or anchor the dot.
- **N20** `scan.py:576` — `upstream_ref` returns via the obscure
  `head.rsplit("/",1)[-1] and f"origin/{…}"` idiom; if `symbolic-ref` ever returned
  empty on success it would yield `""` and the later `rev-parse ""` would fail
  confusingly. Prefer an explicit parse.
- **N21** `gap.py:97-104` (`build_ours`) — "ours" is assembled from root `.claude`
  plus `mvp-harness/plugins/*`, and the codex-side capabilities are only seen via the
  generated `template/` copy inside `mvp-plugin` (root `.codex` is not scanned). If
  the template is stale or the plugin scan is narrowed, codex-only capabilities
  vanish from "ours" and `gap` over-reports. Consider scanning root `.codex` directly.

---

## Top 3 to fix

1. **Namespace the capability identity (C1 + H3).** `logical_id`/`canonical_name`
   ignores the owning plugin/tool, so all `plugin.json` collapse to
   `plugin:.claude-plugin` (39→1) and same-named skills/agents across different
   plugins merge. This is the single biggest correctness hole — it violates
   Invariant 4, silently under-counts, and quietly hides real gaps. Include the
   plugin namespace (or `plugin.json`’s `name`) and only treat same-name copies as
   mirrors when their content hashes match.

2. **Stop clobbering `.beads/beads.md` on update (C2).** Route it through the same
   three-way merge as every other core file (or mark it user-owned). Today every
   `/update` unconditionally overwrites the owner’s edited beads policy doc — a clean
   Invariant-2 violation with no warning.

3. **Fix the two silent/hard failures in the install + drift paths (H5 + H4).** The
   perl value interpolation deletes the host from every SSH git remote
   (`git@github.com` → `git.com`), silently misconfiguring beads sync; and
   `scan.py drift` crashes on any MCP body-only change because it tries to read a
   `mcp.json#server` path. Both are easy to fix (quote/escape the URL value; strip
   the `#server` fragment before reading) and both fail in ways users won't attribute
   to this tooling. Runner-up: orphan-on-delete (H6).
