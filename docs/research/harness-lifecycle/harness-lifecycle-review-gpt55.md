**Findings**

**CRITICAL - [harness_lifecycle/scan.py:377](/data/codes/coding-ritual/harness_lifecycle/scan.py:377)** - Invariant 4 is violated: logical dedup merges distinct capabilities.
Failure scenario: `scan.py catalog reference_harnesses/claude-plugins-official` reports `plugin physical=39 logical=1`; `gap.py gap reference_harnesses/claude-plugins-official --kind plugin` then reports `0` plugin gaps. Discord/iMessage/Telegram `skills/access/SKILL.md` also collapse into one `skill:access`.
Why vulnerable: `canonical_name()` returns `.claude-plugin` for every plugin manifest at [scan.py:261](/data/codes/coding-ritual/harness_lifecycle/scan.py:261), and grouping uses only `kind:name`.
Impact: drift/gap silently drops real plugins and plugin-scoped skills.
Fix: derive plugin identity from manifest or parent plugin dir, and namespace plugin-scoped capabilities instead of deduping globally by name.

**CRITICAL - [mvp-harness/plugins/mvp-plugin/template/codex/docs/codex-usage-guide.md:428](/data/codes/coding-ritual/mvp-harness/plugins/mvp-plugin/template/codex/docs/codex-usage-guide.md:428)** - Invariant 1 is violated: the shipped template still leaks project-specific text.
Failure scenario: current template ships `bodha-memory-eval`, `bodha-chitta-v2_5.md`, and “parent orchestrators repo” into adopted repos at the cited file, [design-evolve/SKILL.md:195](/data/codes/coding-ritual/mvp-harness/plugins/mvp-plugin/template/claude/skills/design-evolve/SKILL.md:195), and [report-set.md:53](/data/codes/coding-ritual/mvp-harness/plugins/mvp-plugin/template/codex/skills/codebase-architecture-research/references/report-set.md:53).
Why vulnerable: `build-template.sh` only rewrites/checks narrow exact strings and misses lowercase `bodha` and bare `orchestrators` at [build-template.sh:121](/data/codes/coding-ritual/mvp-harness/plugins/mvp-plugin/scripts/build-template.sh:121) and [build-template.sh:144](/data/codes/coding-ritual/mvp-harness/plugins/mvp-plugin/scripts/build-template.sh:144).
Impact: adopted repos receive coding-ritual/Bodha-specific instructions despite the generic-template invariant.
Fix: make the leak check case-insensitive and exhaustive for project tokens, then replace examples with neutral placeholders.

**CRITICAL - [harness_lifecycle/scan.py:221](/data/codes/coding-ritual/harness_lifecycle/scan.py:221)** - Invariant 5 is violated: permission-surface changes can be classified as minor.
Failure scenario: changing block YAML from `allowed-tools: [Read, Write]` to include `Bash(rm *)` leaves `parse_frontmatter()` as `{'allowed-tools': ''}` for both; my probe showed `signature_same True` and `change_ratio (2, 0.0093)`, below the [scan.py:460](/data/codes/coding-ritual/harness_lifecycle/scan.py:460) materiality threshold.
Why vulnerable: indented YAML list entries are skipped, but `allowed-tools` is treated as a signature key at [scan.py:57](/data/codes/coding-ritual/harness_lifecycle/scan.py:57).
Impact: dangerous tool/permission expansion can disappear into the “minor” bucket.
Fix: include the full frontmatter block in the signature hash, or at minimum parse block-list values for signature keys and make any frontmatter change material.

**HIGH - [harness_lifecycle/gap.py:267](/data/codes/coding-ritual/harness_lifecycle/gap.py:267)** - `--beads` emits shell-injectable commands from untrusted capability names.
Failure scenario: a reference capability named `evil" $(echo PWNED) "` renders as `bd create --title="Evaluate skill 'evil" $(echo PWNED) "' ...`; command substitution runs if copied.
Why vulnerable: names, repo, logical id, and paths are interpolated inside double-quoted shell strings without shell quoting at [gap.py:265](/data/codes/coding-ritual/harness_lifecycle/gap.py:265)-[270](/data/codes/coding-ritual/harness_lifecycle/gap.py:270).
Impact: hostile reference harness metadata can execute arbitrary local shell code through a generated “ready” command.
Fix: emit argv as JSON or use `shlex.quote()` for every shell token.

**HIGH - [mvp-harness/plugins/mvp-plugin/scripts/install-harness.sh:67](/data/codes/coding-ritual/mvp-harness/plugins/mvp-plugin/scripts/install-harness.sh:67)** - Deleted template files are never retired from adopted repos.
Failure scenario: v1 ships a bad/root-only hook or command, v2 removes it via `template-exclude.txt`; update only iterates current template files and then stamps the new manifest at [install-harness.sh:77](/data/codes/coding-ritual/mvp-harness/plugins/mvp-plugin/scripts/install-harness.sh:77), leaving the old file active forever.
Why vulnerable: no old-manifest minus new-manifest reconciliation exists.
Impact: stale vulnerable hooks/rules or leaked curation files persist invisibly.
Fix: compare old stamp paths to the new manifest; delete only if the destination hash still equals the old base, otherwise report an orphan conflict.

**MEDIUM - [mvp-harness/plugins/mvp-plugin/scripts/build-template.sh:161](/data/codes/coding-ritual/mvp-harness/plugins/mvp-plugin/scripts/build-template.sh:161)** - Template build is not macOS portable and can leave a partial template.
Failure scenario: on stock macOS, `sha256sum` is absent; the script has already rsynced/genericized the template before failing while writing `harness-manifest.txt`.
Why vulnerable: `build-template.sh` hardcodes `sha256sum`, while install’s `hp_hash()` already has a `shasum -a 256` fallback at [common.sh:58](/data/codes/coding-ritual/mvp-harness/plugins/mvp-plugin/scripts/lib/common.sh:58).
Impact: template regeneration fails on macOS and may leave changed payload files with a stale manifest.
Fix: reuse a portable hash helper and write the manifest to a temp file before atomic rename.

Verification: `bash -n` passed for the reviewed shell scripts; AST parse passed for `scan.py` and `gap.py`. Fresh `git status --short` still shows only pre-existing `.beads/issues.jsonl` plus untracked docs/usage files.

**Top 3 Fixes**

1. Fix scanner identity/dedup first; it currently corrupts both drift and gap reports.
2. Block current template leaks and expand the self-check so generic templates cannot ship project-specific text.
3. Make frontmatter/tool-permission changes always material before trusting drift output.
