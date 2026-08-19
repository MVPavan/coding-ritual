# mvp-plugin — structure & usage

> Repo-side guide to the plugin this harness is published as. The plugin lives in the
> `mvp-harness` submodule (`mvp-harness/plugins/mvp-plugin`), whose own
> [`README.md`](../../mvp-harness/plugins/mvp-plugin/README.md) is the user-facing
> doc; this page is the maintainer's mental model and the workflow from *this* repo.
> Updated 2026-08-19 (dual-manifest, skills-as-plugin-components; current version
> in `mvp-harness/plugins/mvp-plugin/publish-info.txt`).

## 1. What it is

One plugin, two tools. `mvp-plugin` carries this repo's curated skill set and
agents as **plugin components** that both Claude Code (`.claude-plugin/plugin.json`)
and Codex (`.codex-plugin/plugin.json`) read from the **same `skills/` directory**.
Installing it — user-level or (Claude Code) project-level — makes every skill
available in every repo with no files copied. `adopt` then lays the per-repo
**residue** a plugin cannot carry.

| Where | What |
|---|---|
| `coding-ritual/.claude/` (this repo) | the canonical harness — workshop; `.codex/*` here are symlinks into it |
| `mvp-harness/plugins/mvp-plugin/` | the build artifact: `skills/` + `agents/` (copied by publish), `template/` residue, `adopt/update/doctor` |
| an adopted repo | residue only: `.claude/{rules,hooks,settings.json,project/*}`, `CLAUDE.md`, `AGENTS.md`, `.beads/`, `.codex/{config.toml,hooks*,rules/default.rules,agents/*.toml}` + symlinks `.codex/project`, `.codex/rules/{core,python}` |

## 2. Install & use

```text
# Claude Code
/plugin marketplace add MVPavan/mvp-harness
/plugin install mvp-plugin@mvp-harness          # user scope (everywhere) or project scope (this repo; teammates prompted)

# Codex (CLI >= 0.122)
codex plugin marketplace add MVPavan/mvp-harness
codex plugin add mvp-plugin@mvp-harness          # user level; new session afterwards

# In any repo you want set up
/mvp-plugin:adopt     ($adopt in Codex)          # residue + overlay adaptation
/mvp-plugin:doctor    ($doctor)                  # verify wiring, skill availability, duplicates
/mvp-plugin:update    ($update)                  # re-sync residue; skills update via the plugin itself
```

Repo-level on Codex is "repo-discoverable, user-installed": `adopt` writes
`.agents/plugins/marketplace.json` so teammates find the marketplace from the repo
and run the two Codex commands once. `adopt --fork-skills` (rare) copies skills into
the repo as editable files; it is refused while the plugin is enabled (double load)
unless `--force-duplicate`.

## 3. Invocation forms

Skill names are canonical; the prefix depends on where the harness is installed:

| Context | Form |
|---|---|
| Claude Code, from the plugin | `/mvp-plugin:<name>` |
| Claude Code, repo-local copy (this repo, or a forked adopt) | `/<name>` |
| Codex | `$<name>` (or `/skills`) |

Slash-only skills carry `disable-model-invocation: true` **and**
`agents/openai.yaml` → `policy.allow_implicit_invocation: false` (generated; drift
fails `skill-catalog.py --check`), so neither tool auto-triggers them.

## 4. How `adopt` works

1. **Deterministic** — `scripts/install-harness.sh`: reports plugin status per tool
   (`claude plugin list --json`, `codex plugin list --json`), copies the residue
   with a three-way merge (base = `.harness-manifest.txt`) that never clobbers local
   edits (conflicts land as `<file>.template-new`), creates the Codex symlink view,
   drops the overlay skeletons under `.claude/project/`, initialises beads and points
   sync at origin, appends the `.gitignore` block, writes the repo marketplace file;
   `settings.json` already carries `extraKnownMarketplaces.mvp-harness`. Idempotent;
   never `git add`s.
2. **Judgement** — the `harness-adopt` skill fills `.claude/project/*` from repo
   reality and appends report-only automation recommendations. One overlay — there is
   no `.codex/project/` to keep in step.

## 5. Plugin directory structure

```text
mvp-harness/
  .claude-plugin/marketplace.json      Claude marketplace (mvp-plugin, code-intel, codex-adapter)
  .agents/plugins/marketplace.json     Codex marketplace (mvp-plugin)
  plugins/mvp-plugin/
    .claude-plugin/plugin.json         skills ./skills/ (agents/ is the default dir)
    .codex-plugin/plugin.json          skills ./skills/ + interface block
    skills/<name>/…                    43 = 39 published from this repo + adopt/update/doctor/harness-adopt
    agents/*.md                        4
    template/                          residue (dot-less): CLAUDE.md AGENTS.md beads/ claude/{rules,hooks,settings.json} codex/{config.toml,hooks*,rules/default.rules,agents/*.toml} harness-manifest.txt
    scripts/                           install-harness.sh doctor.sh build-template.sh check-sync.sh publish-plugin.sh smoke-codex.sh lib/{common,genericize}.sh overrides/ sync-manifest.txt template-exclude.txt
    publish-manifest.txt               sources, excludes, plugin-owned, counts, neutrality audit patterns
    publish-info.txt                   plugin version + source commit + counts (provenance)
    test/                              run-tests.sh update-merge-test.sh from-zero.sh Dockerfile
```

## 6. Publishing from this repo — `/harness-publish`

Root-only skill (`.claude/skills/harness-publish/`) wrapping
`mvp-harness/plugins/mvp-plugin/scripts/publish-plugin.sh`:

```bash
python3 .claude/scripts/skill-catalog.py --check                                  # root gates green
bash mvp-harness/plugins/mvp-plugin/scripts/publish-plugin.sh --check              # dry run
bash mvp-harness/plugins/mvp-plugin/scripts/publish-plugin.sh --bump patch --smoke # publish
git -C mvp-harness add … && git -C mvp-harness commit …                            # plugin repo commit (its own branch)
git add mvp-harness && git commit -m "chore(plugin): mvp-plugin vX.Y.Z (source <sha>)"
```

What the script enforces, in order: clean trees + source commit → rsync per
`publish-manifest.txt` (`harness-*`, `in-progress/` excluded; plugin-owned protected)
→ count asserts → shipped `skill-router` + sidecars regenerated → **provider-neutrality
audit** (a shipped line naming a Claude-only tool, env var, or `.claude/skills/…` path
must be two-branched "Claude Code: … / Codex: …") → genericise + leak check →
`build-template.sh` + `check-sync.sh` → manifests parse + `claude plugin validate` →
version bump in all four manifests → `publish-info.txt`. `--smoke` installs into a
throwaway `$HOME` with `codex` and asserts the implicit-skill count.

Never hand-edit the plugin's `skills/` or `agents/` — they are overwritten on publish.
Plugin-owned skills and `scripts/` are edited in the plugin.

## 7. Invariants

- Shipped set ⊂ this repo's `.claude/skills` (+ the 4 plugin-owned); `harness-*`
  and `in-progress/` never ship.
- One copy of every skill; Codex reads the same files. Forked repo copies are an
  explicit, warned-about exception.
- Every shipped skill: `agents/openai.yaml` policy == `disable-model-invocation`.
- No `.claude/skills/…`, `.codex/…`, Claude-only tool names, machine paths, or
  project names in shipped text unless two-branched / genericised.
- `template/` = residue only; `.codex/project` and `.codex/rules/{core,python}` are
  symlinks in adopted repos, never copies.

## 8. `doctor` checks

Plugin status per tool (+ DUPLICATE warning when forked copies coexist with the
plugin; "no skills reachable" when neither); residue files present; the three
symlinks; hooks wired/executable; Codex hook trust (best-effort); repo marketplace
file; portable paths; beads; overlay filled; residue version vs plugin manifest;
`*.template-new` conflicts; plugin build provenance.

## 9. Testing

See `mvp-harness/plugins/mvp-plugin/test/README.md`. Host run:
`PLUGIN_DIR=mvp-harness/plugins/mvp-plugin bash mvp-harness/plugins/mvp-plugin/test/run-tests.sh`
(incl. the update-merge suite). Supported platforms: Linux/macOS.

## Current state

43 skills (26 model-invocable / 17 slash-only on publish), 4 agents, residue
template 24 files. Version + source commit: `mvp-harness/plugins/mvp-plugin/publish-info.txt`.
Verified by the plugin test suites and a 12-cell live install matrix (Claude Code +
Codex in a clean container): every install/adopt permutation, hooks firing, the
teammate-clone path, duplicate detection, uninstall.
