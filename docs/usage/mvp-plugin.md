# mvp-plugin — structure & usage

> Repo-side guide to the plugin this harness is published as. The plugin lives in the
> `mvp-harness` submodule (`mvp-harness/plugins/mvp-plugin`), whose own
> [`README.md`](../../mvp-harness/plugins/mvp-plugin/README.md) is the user-facing
> doc; this page is the maintainer's mental model and the workflow from *this* repo.
> Updated 2026-11-25 for distribution model B (skills laid into each repository;
> current version in `mvp-harness/plugins/mvp-plugin/publish-info.txt`).

## 1. What it is

The plugin carries three skills of its own — `adopt`, `update`, `doctor` — and a
payload. `adopt` lays the payload into a repository, which then owns and commits it:
the curated skills in `.agents/skills` (both tools read them; Claude Code through its
`.claude/skills` view), the hooks and their wiring, `CLAUDE.md`/`AGENTS.md`, the Codex
residue, the `.repo-context/` overlay and beads. Teammates get the harness from that
commit; they install the plugin only to run `adopt`, `update` or `doctor`.

| Where | What |
|---|---|
| `coding-ritual` (this repo, the workshop) | the canonical `.agents/skills` with its Claude view, `.claude/hooks`, `.codex/`, `.repo-context/` (incl. `harness-settings.txt`: `upstream`, `repo-owned` units that never ship) |
| `mvp-harness/plugins/mvp-plugin/` | the build artifact: `skills/{adopt,update,doctor}`, `template/` payload (`agents/skills/` 62 skills, `claude/`, `codex/`, `CLAUDE.md`, `AGENTS.md`), `scripts/` |
| an adopted repo | `.agents/skills/*` + the Claude view of `skill-layout.txt`, `.claude/{hooks,settings.json}`, `CLAUDE.md`, `AGENTS.md`, `.codex/{config.toml,hooks*,rules/default.rules}`, `.repo-context/*`, `.beads/`, `.agents/plugins/marketplace.json`, records `.harness-manifest.txt` and `.harness-wiring.txt` |

No `.claude/agents`, `.codex/agents`, `.claude/rules`, `.claude/project`, `.codex/project`
or `.codex/rules/{core,python}` in an adopted repo: the installer creates none of them,
and on update it moves or removes the old ones (section 4).

## 2. Install & use

```text
# Claude Code
/plugin marketplace add MVPavan/mvp-harness
/plugin install mvp-plugin@mvp-harness          # user scope (everywhere) or project scope (this repo; teammates prompted)

# Codex (CLI >= 0.122)
codex plugin marketplace add MVPavan/mvp-harness
codex plugin add mvp-plugin@mvp-harness          # user level; new session afterwards

# In any repo you want set up (never in this workshop: adopt and update refuse here)
/mvp-plugin:adopt     ($adopt in Codex)          # lay the harness + fill the overlay
/mvp-plugin:doctor    ($doctor)                  # verify wiring
/mvp-plugin:update    ($update)                  # re-sync from a newer plugin; commits nothing
```

Repo-level on Codex is "repo-discoverable, user-installed": `adopt` writes
`.agents/plugins/marketplace.json` so teammates find the marketplace from the repo.

## 3. Invocation forms

| Context | Form |
|---|---|
| Claude Code, a skill in the repo's `.agents/skills` | `/<name>` |
| Claude Code, a plugin skill | `/mvp-plugin:adopt`, `/mvp-plugin:update`, `/mvp-plugin:doctor` |
| Codex | `$<name>` (or `/skills`) |

Slash-only skills carry `disable-model-invocation: true` **and**
`agents/openai.yaml` → `policy.allow_implicit_invocation: false` (generated; drift
fails `skill-catalog.py --check`), so neither tool auto-triggers them.

## 4. How `adopt` and `update` work

1. **Deterministic** — `scripts/install-harness.sh`, the same script for both
   (update passes `--update`):
   - Preflight, before any move, stub, link or `bd init`: refuses the workshop (a repo
     holding the plugin's `publish-manifest.txt` or an `mvp-harness` submodule); refuses
     a linked `.claude` or `.agents`, and a link at or inside an incoming or stamped
     skill path in `.agents/skills` (the exact Claude view links are allowed); and
     refuses when a skill name, compared case-insensitively, is in both a real
     `.claude/skills` and `.agents/skills`, or in either and the incoming payload,
     listing every clash.
   - Initialises beads (adopt only, never with `--update`; `bd init` makes its own
     commit) and points sync at origin.
   - Legacy layout: each `.claude/project/x` moves to `.repo-context/x` only where that
     name is free; the old links `.codex/project` → `../.claude/project` and
     `.codex/rules/{core,python}` → `../../.claude/rules/{core,python}` are removed only
     when the target is exactly that; edited old rule files stay where they are, and
     untouched ones are retired through the stamp.
   - Each other `.claude/skills/<n>` moves into `.agents/skills` and is listed
     `repo-owned` in `.repo-context/harness-settings.txt`.
   - Lays the payload with a three-way merge (base = `.harness-manifest.txt`); a file
     changed locally and upstream keeps the local copy and gets `<file>.template-new`
     plus a report line. Units in `.harness-retired.txt` are never laid or retired.
   - Writes stubs only when absent (`install-harness.sh --list-stubs` prints them): the
     overlay, `GLOSSARY.md`, `coding-style.md` (from `overrides/python`) and
     `harness-settings.txt` (`upstream` from `publish-info.txt`) in `.repo-context/`;
     `.agents/skills/mvp-mode/routes.md`; `.agents/plugins/marketplace.json`.
   - Appends the `.gitignore` block, merges hooks and the marketplace recommendation
     into `.claude/settings.json`, retires untouched files the payload dropped, stamps
     the new manifest, and builds the Claude view of `scripts/skill-layout.txt`.
   - Records each link, the marketplace file and the `.gitignore` block it created
     (never one that was already there) in
     `.harness-wiring.txt` (`link <path> <target>`, `created <path> <sha256>`,
     `gitignore-block - <fingerprint>`).
2. **Judgement** — the adopt skill's `references/fill-overlay.md` fills
   `.repo-context/*` from repo reality and appends report-only automation
   recommendations.

Never overwritten by update: `.repo-context/*`, `.agents/skills/mvp-mode/routes.md`
(repo routes and `Replaces <old> with <new>` lines, read by the shipped router),
`.harness-retired.txt`.

## 5. Plugin directory structure

```text
mvp-harness/
  .claude-plugin/marketplace.json      Claude marketplace (mvp-plugin, code-intel, codex-adapter)
  .agents/plugins/marketplace.json     Codex marketplace (mvp-plugin)
  plugins/mvp-plugin/
    .claude-plugin/plugin.json         skills ./skills/
    .codex-plugin/plugin.json          skills ./skills/ + interface block
    skills/{adopt,update,doctor}       the plugin's own skills
    template/                          payload (dot-less): agents/skills/ claude/{hooks,settings.json} codex/{config.toml,hooks*,rules/default.rules} CLAUDE.md AGENTS.md harness-manifest.txt
    scripts/                           install-harness.sh doctor.sh build-template.sh check-sync.sh publish-plugin.sh smoke-codex.sh skill-catalog.py skill-layout.txt lib/ overrides/
    publish-manifest.txt               payload source, plugin-owned, counts, neutrality audit patterns
    publish-info.txt                   plugin version + source commit + counts + upstream (provenance)
    test/                              run-tests.sh installer-b-test.sh update-merge-test.sh from-zero.sh Dockerfile
```

## 6. Publishing from this repo — `/harness-publish`

Root-only skill wrapping `mvp-harness/plugins/mvp-plugin/scripts/publish-plugin.sh`:

```bash
uv run python .claude/scripts/skill-catalog.py --check                             # root gates green
bash mvp-harness/plugins/mvp-plugin/scripts/publish-plugin.sh --check              # dry run
bash mvp-harness/plugins/mvp-plugin/scripts/publish-plugin.sh --bump patch --smoke # publish
git -C mvp-harness add … && git -C mvp-harness commit …                            # plugin repo commit
git add mvp-harness && git commit -m "chore(plugin): mvp-plugin vX.Y.Z (source <sha>)"
```

What the script enforces, in order: clean trees + source commit → `.agents/skills`
staged as `template/agents/skills` (Git-ignored files and this repo's `repo-owned`
units stay out; plugin-owned skills protected) → count asserts → router catalog and
sidecars regenerated → pointer check against the install inventory → **provider-neutrality
audit** → genericise + leak check → `build-template.sh` + `check-sync.sh` → manifests
parse + `claude plugin validate` → version bump in all four manifests →
`publish-info.txt`. `--smoke` installs into a throwaway `$HOME` with `codex` and
asserts discovery.

Never hand-edit the plugin's `template/` — it is overwritten on publish. Plugin-owned
skills and `scripts/` are edited in the plugin.

## 7. Invariants

- Payload ⊂ this repo's `.agents/skills`; `repo-owned` units never ship.
- One copy of every skill in an adopted repo: `.agents/skills`, with Claude Code
  reading it through the view; the installer refuses a second copy.
- Every shipped skill: `agents/openai.yaml` policy == `disable-model-invocation`.
- No `.claude/skills/…`, Claude-only tool names, machine paths, or project names in
  shipped text unless two-branched / genericised.
- Adopt and update never overwrite a repo-owned file, never resurrect a tombstoned
  unit, and never commit (beyond `bd init`'s first commit).

## 8. `doctor` checks

`doctor.sh` still checks the pre-model-B layout (`.claude/rules`, `.claude/project`,
the `.codex` links); its model-B rewrite is pending, so on a freshly adopted repo it
reports those as missing.

## 9. Release notes

Glossary rename (2026-11-20): skills no longer read `CONTEXT.md` or
`CONTEXT-MAP.md`. Rename once with `git mv`, in place:
`.repo-context/CONTEXT.md` to `.repo-context/GLOSSARY.md`; a root `CONTEXT.md`
to `GLOSSARY.md`; with several contexts, the root `CONTEXT-MAP.md` to
`GLOSSARY-MAP.md` and each per-context `CONTEXT.md` to `GLOSSARY.md`, then
update the map's links and any instruction (such as `AGENTS.md`) that names the
old files. (`adopt` writes a `GLOSSARY.md` stub only when none exists.)

## 10. Testing

See `mvp-harness/plugins/mvp-plugin/test/README.md`. Host run:
`PLUGIN_DIR=mvp-harness/plugins/mvp-plugin bash mvp-harness/plugins/mvp-plugin/test/run-tests.sh`
(includes `update-merge-test.sh` and `installer-b-test.sh`). Supported platforms:
Linux/macOS.
