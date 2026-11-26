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
   - Initialises beads (adopt only, never with `--update`, and only on a clean working
     tree, since `bd init` makes its own commit) and points sync at origin.
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
     `gitignore-block - <fingerprint>`). Each hook entry and key it adds to
     `.claude/settings.json` or `.codex/hooks.json` gets a `settings-hook` or
     `settings-key` row (`<file> <event> <command>` or `<file> <key>`, then a
     fingerprint). A recorded entry the repo later removes stays removed: a rerun
     reports it and does not add it back.
2. **Judgement** — the adopt skill's `references/fill-overlay.md` fills
   `.repo-context/*` from repo reality and appends report-only automation
   recommendations.

3. **Other modes of `install-harness.sh`** (the update skill shows how to run them):
   - `--update --all <repo>...` (`scripts/update-all.sh`): updates each repo, one table
     (repo, new, updated, kept, conflicts, retired, status), non-zero if any failed.
   - `fork <unit> as <new>` (`scripts/lib/fork-unit.py`): preflights the whole name
     namespace (`.agents/skills` entries including the repo's own, case-insensitively;
     the stamp; the payload; tombstones; `repo-owned` entries; `routes.md` operands;
     `~/.claude/skills` on this machine for a skill) and refuses before writing. Then it
     stages a copy of the unit with its companions, renames a skill's `name`, prefixes
     its description "Use instead of `<unit>` in this repository.", rewrites a
     playbook's own `<unit>/` references, verifies the copy differs from the source only
     by those rewrites, renames it into place, tombstones and deletes the original,
     updates the Claude view, and appends `repo-owned <new>` and
     `` - Replaces `<old>` with `<new>` (baseline <sha256>) `` to `routes.md`. The
     baseline is the sha256 of the unit's stamp lines (`<path>\t<sha256>`, byte-sorted).
   - `--remove` (`scripts/lib/remove-harness.py`): removes from the settings files only
     entries whose fingerprint equals their wiring row (edited ones are kept and
     reported); keeps every harness hook a remaining entry names by file name (an
     explicit `.claude/hooks/<n>` keeps that file, another spelling such as
     `cd .claude && bash hooks/<n>` every managed file of that name) and what it calls in
     turn (`bead-mirror-session.sh` → `.claude/hooks/bead-mirror.py`); deletes unedited
     stamped files except declared `repo-owned` units; removes the recorded created file,
     `.gitignore` block and view links, keeping the Claude view while skills remain; drops
     the stamp and wiring record last. Preflight refuses a recorded destination that is
     not repository-relative or lies behind a linked folder.
   - Install, `fork` and `--remove` share one workshop detector (`hp_is_workshop` in
     `lib/common.sh`, reading `.gitmodules` with `git config`) and the installer's
     `repo-owned` reader (`lib/repo-owned.sh`). A fork's skill operand is written
     `<new>/SKILL.md` when the bare name would read as a principle (`principle-*`).

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

`doctor.sh` (with `lib/doctor-check.py`) is read-only: it runs none of the repo's code
(every Python it starts runs with `-E -P -B`, ignoring the caller's `PYTHON*` variables
such as `PYTHONPATH`, or `-I -B` on Python older than 3.11, and writes no bytecode) and
reads nothing through a link below the repo (each such path is a FAIL naming it; a
linked `.gitmodules` is a FAIL too, and adopt, update, fork and `--remove` refuse it as
an unreadable workshop marker). Exit codes:

| Exit | Meaning |
|---|---|
| 0 | every check ran and none failed |
| 1 | at least one FAIL |
| 2 | refused: run in the workshop |
| 3 | no FAIL, but a required check could not run: no PyYAML (skill pointers, `Replaces` lines), a committed mirror workflow that cannot be compared, or a missing wiring record (beside a stamp) or a settings file it names that cannot be read; the closing `INCOMPLETE:` line names each |

A repo without `.github/workflows/bead-reference-check.yml` is not incomplete. It checks:

- the stamp: a row without a relative path and a 64-hex digest fails naming its line, and
  one with no valid row fails; every stamped file by hash: missing fails, edited is listed, a tombstoned unit is
  reported retired; `.template-new` leftovers are listed;
- a `repo-owned` unit that collides with a stamped one, and a Claude view that differs
  from `skill-layout.txt` (or dangles), fail;
- each `Replaces` line in `routes.md`, as `skill-catalog.py` parses and resolves it
  (fenced examples skipped; a skill named by declared name, folder or entry point): a
  missing new unit fails; a stale mapping (old
  unit no longer stamped) and drift (the old unit's stamp digest differs from the
  baseline) are reported;
- `skill-catalog.py --pointers-only --contained` on `.agents/skills`, naming each broken
  caller `file:line` and each link inside the tree, unread (needs PyYAML, else
  incomplete);
- the wiring record: a malformed row, an unknown kind, an unsafe path or a settings file
  that is not valid JSON fails naming it; then its links, created files, `.gitignore` block and settings entries;
- the bead mirror: a committed `.github/workflows/bead-reference-check.yml` against the
  plugin's `bead-mirror.py print-check`, only when the installed
  `.claude/hooks/bead-mirror.py` is byte-identical to the plugin's (otherwise incomplete:
  run `install-check` from the installed command to compare), and a failing, stale or held mirror from its local
  state in the git common dir (no network; a link at `bead-mirror/` or at a state file in
  it is a FAIL, not read);
- DUPLICATE: a skill-bearing plugin (< 0.3.0) enabled on a tool, or a `~/.claude/skills`
  name shadowing a repo skill (this machine only);
- hooks executable, `settings.json` portable, Codex hook trust, beads, the overlay
  filled, and whether an update is available.

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
