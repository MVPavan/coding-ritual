---
name: harness-publish
description: Publish this repo's harness into the mvp-plugin (the mvp-harness submodule) — copy the shippable skills and agents, run the provider-neutrality and leak audits, regenerate the shipped router and Codex sidecars, rebuild the residue template, validate both manifests, bump the version. Root-only; never runs in adopted repos.
disable-model-invocation: true
---

# harness-publish

This repo is the workshop; `mvp-harness/plugins/mvp-plugin` is the one plugin both
Claude Code and Codex install. Publishing is a manual, user-run step.

## Steps

1. **Preflight here.** Root gates must be green and committed:

   ```bash
   python3 .claude/scripts/skill-catalog.py --check     # 0 FAIL, 0 WARN
   git status --short                                     # clean (or know why not)
   ```

2. **Dry run.** Shows the gates, the provider-neutrality audit on the source,
   and what rsync would change — writes nothing:

   ```bash
   bash mvp-harness/plugins/mvp-plugin/scripts/publish-plugin.sh --check
   ```

   Fix anything it reports **in this repo** (never in the plugin's `skills/` —
   they are overwritten on publish), re-run the catalog check, return here.

3. **Publish.** Pick the bump from what changed (patch: text/fixes; minor: new
   or removed skills, behaviour changes; major: adopt/update contract change):

   ```bash
   bash mvp-harness/plugins/mvp-plugin/scripts/publish-plugin.sh --bump patch --smoke
   ```

   `--smoke` installs the result into a throwaway `$HOME` with `codex` and
   asserts discovery; drop it if `codex` is not on PATH. `--allow-dirty` only
   when the user has explicitly accepted publishing from an uncommitted tree.

4. **Review + commit the plugin repo** (it is a separate git repo on its own
   branch):

   ```bash
   git -C mvp-harness status --short
   git -C mvp-harness diff --stat
   ```

   Stage explicit paths, commit with a message that names the plugin version
   and the source commit from `plugins/mvp-plugin/publish-info.txt`. Do not
   push; the user pushes and decides the branch/merge.

5. **Bump the submodule pointer here** and commit it:

   ```bash
   git add mvp-harness && git commit -m "chore(plugin): mvp-plugin vX.Y.Z (source <sha>)"
   ```

   Consumers pick the new version up with `/plugin update mvp-plugin` (Claude
   Code) or `codex plugin marketplace upgrade` + a new session (Codex).

## What the script enforces (so you know what a failure means)

| Failure line | Cause | Fix |
|---|---|---|
| `uncommitted changes` | source or plugin tree dirty | commit, or `--allow-dirty` with user consent |
| `NOT NEUTRAL <file>:<line>` | a shipped line names a Claude-only tool / env var / `.claude/skills/…` path without a "Claude Code: … / Codex: …" two-branch | reword in this repo; allowlist only with a reason in `publish-manifest.txt` (`neutral` / `skip`) |
| `expect skills N, found M` | the shipped set changed | if intended, edit `expect` in `publish-manifest.txt` |
| `LEAK (…)` | project/machine string in a shipped file | genericise the source (`scripts/lib/genericize.sh` lists the sweep) |
| `skill-catalog --check failed` | dead slash/path ref or sidecar drift in the shipped set | fix in this repo; plugin-owned skills (`adopt/update/doctor/harness-adopt`) are fixed in the plugin |
| `claude plugin validate failed` | manifest schema | run it by hand for the detail |

Never edit `mvp-harness/plugins/mvp-plugin/skills/` or `agents/` by hand — they
are build output of this repo. Plugin-owned skills and `scripts/` are edited in
the plugin.
