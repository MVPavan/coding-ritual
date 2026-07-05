# mvp-plugin — structure & usage

A reference for the `mvp-plugin` Claude Code plugin: what it is, how it is laid out,
how each command and script works, and what it installs into a target repo.

> **Where it lives now.** `mvp-plugin` is one of three plugins in the **`mvp-harness`**
> marketplace, tracked in this repo as the `mvp-harness/` git submodule
> (`MVPavan/mvp-harness`). Its path is [`mvp-harness/plugins/mvp-plugin/`](../../mvp-harness/plugins/mvp-plugin/).
> The plugin's own `README.md` predates the marketplace restructure and still
> describes a two-plugin / vendored-codex-adapter layout — see
> [Current state & caveats](#current-state--caveats) for what actually holds today.

---

## 1. What it is

`mvp-plugin` installs a **self-contained agent-coding harness** into any repository:
the `.claude/` + `.codex/` trees (rules, skills, agents, commands, hooks, docs),
the `CLAUDE.md` / `AGENTS.md` entry points, and beads (`bd`) issue tracking — then
adapts that harness to the specific repo.

Its guiding principle is a clean split (the same one encoded in the harness's own
`03-ak-guidelines.md` rule #5 — *"if code can answer, code answers"*):

| Half | Mechanism | Responsibility |
|---|---|---|
| **Deterministic** | `scripts/install-harness.sh` (bash) | Copy files, init beads, wire gitignore — reproducible, idempotent, no judgement. |
| **Judgement** | `harness-adopt` skill (model) | Read the repo and fill the per-repo overlay with real facts; recommend automations. |

Enabling the plugin exposes exactly **three commands** and **one skill** — nothing
else. The large `template/` payload is inert data the installer copies; it is not
auto-loaded (it does not sit at the plugin root).

---

## 2. Install & use

```bash
# 1. Register the marketplace once (local path, or the GitHub URL once cloned)
/plugin marketplace add <path-to>/mvp-harness

# 2. Install the plugin
/plugin install mvp-plugin@mvp-harness

# 3. In any repo you want set up:
/mvp-plugin:adopt     # copy the harness, init beads, then adapt it to this repo
/mvp-plugin:doctor    # verify everything is wired
/mvp-plugin:update    # later: re-sync the reusable core, keep your filled overlay
```

External tools the adopted repo expects:

- **beads** (`bd`) — task tracking: `npm i -g @beads/bd` (pin `@beads/bd@1.0.4` if the
  binary download 404s).
- **codex** — only for the sibling `codex-adapter` plugin: `npm i -g @openai/codex && codex login`.

---

## 3. The three commands

Each command is a thin [`commands/*.md`](../../mvp-harness/plugins/mvp-plugin/commands/)
wrapper; the real work is in `scripts/`. All use `${CLAUDE_PLUGIN_ROOT}` so they run
from wherever the plugin is installed.

| Command | Runs | Effect |
|---|---|---|
| `/mvp-plugin:adopt` | `install-harness.sh` **+** `harness-adopt` skill | Full install: deterministic copy, then model-driven overlay fill. Ends by presenting `adoption-report.md` for review — never commits or `git add`s. |
| `/mvp-plugin:update` | `install-harness.sh` **only** | Refresh the reusable core in place; the filled overlay and user config are preserved. Does *not* re-run overlay adaptation. |
| `/mvp-plugin:doctor` | `doctor.sh` | PASS/WARN/FAIL wiring report. Does not change anything. |

---

## 4. How `/mvp-plugin:adopt` works

### 4a. Deterministic — `scripts/install-harness.sh`

Resolves the target repo via `hp_target()` (`$CLAUDE_PROJECT_DIR` → git top-level →
`pwd`) and then:

1. **Copies the payload** — every file under `template/` (except `beads/*`) into the
   target, remapping the dot-less storage names back to dotted (`claude/→.claude/`,
   `codex/→.codex/`). For each file:
   - if it does not exist → copy (counts as *new*);
   - if it exists and is **user-owned** → skip, never clobber (counts as *preserved*);
   - if it exists and is core → overwrite only when content differs (counts as *updated*).
   Hook scripts under `.claude/hooks` and `.codex/hooks` are re-`chmod +x`'d.
2. **Drops overlay skeletons** — placeholder `# Title` + `TODO: fill from repo reality`
   files, so the structure exists before the skill fills it. Written into **both**
   `.claude/project/` and `.codex/project/`:
   `brief.md`, `repo-map.md`, `docs-index.md`, `verification.md`, `invariants.md`,
   `tools.md`, `tracking.md`, `learnings.md`, `adoption-report.md` — plus
   `.claude/project/code-intel.md`. Existing overlay files are preserved.
3. **Initialises beads** — `bd init --non-interactive --skip-agents` (skipped if
   `.beads/metadata.json` already exists), copies the `beads.md` policy doc, sets
   `export.auto true`, and points `sync.remote` at the repo's own `origin`
   (`git+<url>`). If `bd` is absent it warns with the install hint and continues.
4. **Appends a `.gitignore` block** (idempotent, marker-guarded) ignoring
   `scratchpad/`, `**/scratchpad/*`, `.serena/`, `.codebase-memory/`.
5. **Prints a summary** — `N new, N core updated, N user-owned preserved` — and the
   NEXT hint to fill the overlay.

**Guarantees:** idempotent (a second run reports `0 new, 0 core updated`),
non-destructive (user-owned files never overwritten), and it never runs `git add`.

**User-owned set** (`hp_is_user_owned` in `scripts/lib/common.sh` — the never-clobber list):
`CLAUDE.md`, `AGENTS.md`, `.claude/settings.json`, `.codex/config.toml`,
`.codex/hooks.json`, and everything under `.claude/project/*` and `.codex/project/*`.

### 4b. Judgement — the `harness-adopt` skill

After the files land, the [`harness-adopt`](../../mvp-harness/plugins/mvp-plugin/skills/harness-adopt/SKILL.md)
skill does what code can't:

1. Reads `AGENTS.md` / `CLAUDE.md` and the skeleton overlay.
2. Scans the repo — root config, README, manifests/lock files, CI, `.gitmodules`,
   source & tests.
3. Applies an authority order when facts conflict:
   **repo reality → current config/CI → maintained docs → older docs → explicit assumptions.**
4. Fills every overlay file in **both** trees with verified facts (keeping `.claude/project/*`
   and `.codex/project/*` consistent; only path prefixes differ).
5. Appends **report-only** automation recommendations (modeled on Anthropic's
   `claude-automation-recommender`): detected stack → suggested MCP servers / hooks /
   subagents / the `code-intel` plugin. **Nothing is auto-enabled** — enablement is
   the user's trust decision.
6. Optionally has Codex challenge major assumptions (best-effort).
7. Stops and presents `adoption-report.md` for review. No commit, no `git add`.

---

## 5. Plugin directory structure

```
mvp-plugin/
├── .claude-plugin/plugin.json     # manifest (name, version 0.1.0, description, author)
├── README.md  LICENSE  .gitignore
├── commands/                      # the global surface — /mvp-plugin:*
│   ├── adopt.md   doctor.md   update.md
├── skills/harness-adopt/SKILL.md  # the judgement half of adopt
├── scripts/                       # the machinery
│   ├── install-harness.sh         #   deterministic install (adopt + update)
│   ├── doctor.sh                  #   wiring verification
│   ├── build-template.sh          #   (maintainer) regenerate template/ from source harness
│   ├── check-sync.sh              #   (maintainer) drift check: .claude vs .codex payload
│   ├── sync-manifest.txt          #   declared intentional .claude/.codex divergences
│   ├── sync-baseline.txt          #   accepted-state snapshot for the drift check
│   ├── lib/common.sh              #   shared helpers (hp_target, hp_is_user_owned, hp_* log)
│   └── overrides/python/          #   genericised python rules swapped in at build time
│       ├── coding-style.md   safety.md
├── template/                      # the PAYLOAD (inert data). Stored DOT-LESS; installed dotted (see §6)
│   ├── CLAUDE.md   AGENTS.md
│   ├── beads/beads.md
│   ├── claude/ …                  # 49 files (see §6) → installed as .claude/
│   └── codex/ …                   # 69 files (see §6) → installed as .codex/
└── test/                          # Dockerfile  run-tests.sh  from-zero.sh  README.md
```

Only `commands/`, `skills/`, and `.claude-plugin/plugin.json` are plugin-active
surfaces. `scripts/` is invoked by the commands; `template/` is pure payload.

---

## 6. The template payload (what gets installed)

Two parallel harness trees are copied verbatim into the target repo. `.codex/` is a
hand-maintained mirror of `.claude/` — they diverge by design (Markdown vs TOML
agents, a bash vs Python hook, Codex-only skills), which is why [§7.2](#72-check-syncsh--keep-the-two-trees-in-sync)
exists.

> **Storage vs install.** In `template/` the payload dirs are stored **dot-less**
> (`claude/`, `codex/`, `beads/`) so the source harness's own Claude Code does not
> scan `template/.claude/skills` as project skills while you edit the payload.
> `install-harness.sh` restores the leading dots on copy (`claude/→.claude/`, …), so
> the adopted repo gets `.claude/` `.codex/` `.beads/`. The tables below use the
> dotted **installed** names; the stored file contents are identical either way.

### Root & tracking
- **`CLAUDE.md` / `AGENTS.md`** — always-loaded operating guide: critical guidelines,
  read order, working-mode classification (`small` / `standard` / `deep`),
  process-before-execution routing, verification, git-safety.
- **`.beads/beads.md`** — beads workflow + session-close protocol (copied; the store
  itself is `bd init`'d, not copied).

### `.claude/` tree (49 files)
| Group | Contents |
|---|---|
| `agents/` | `claude-max`, `fable-max`, `fable-xhigh`, `implementer`, `planner`, `code-reviewer`, `spec-reviewer`, `docs-researcher` |
| `commands/` | `adopt`, `check-invariants`, `prepare-phases`, `run-phases`, `use-codex` |
| `rules/core/` | `01-delegation`, `02-knowledge-discoverability`, `03-ak-guidelines` |
| `rules/python/` | `coding-style`, `safety`, `testing` (genericised versions) |
| `skills/` | `ak-guide`, `brainstorming`, `planning`, `phase-execution`, `subagent-driven-development`, `test-driven-development`, `systematic-debugging`, `verification-before-completion`, `document-review`, `grill-me`, `design-evolve`, `teach-session`, `cost-estimate`, `html-artifact` |
| `hooks/` | `bd-prime.sh` (SessionStart), `block-dangerous-commands.sh` (PreToolUse/Bash), `block-generated-edits.sh` (PreToolUse/Write\|Edit) |
| `docs/` | beads / codex / mlflow adoption + usage guides |
| `settings.json` | wires the three hooks (see below) |

### `.codex/` tree (69 files)
Mirrors `.claude/` for the Codex CLI, plus Codex-specific extras:
- `config.toml`, `hooks.json`, `rules/default.rules`, `README.md`
- agents as **`.toml`**; hooks include a **Python** `block-generated-edits.py`
- Codex-only skills: `adopt`, `use-codex`, `deep-research`,
  `codebase-architecture-research`, `migrate-claude-to-codex` (several ship
  `agents/openai.yaml` + helper scripts).

### Hooks wired by `.claude/settings.json`
| Event | Matcher | Hook | Purpose |
|---|---|---|---|
| `PreToolUse` | `Bash` | `block-dangerous-commands.sh` | Block git working-tree/history destroyers, `--no-verify`, `bd init --force/--reinit`, and recursive `rm` outside `/tmp`. |
| `PreToolUse` | `Write\|Edit` | `block-generated-edits.sh` | Block hand-edits to bd-generated workstream mirrors. |
| `SessionStart` | — | `bd-prime.sh` | Load beads context at session start. |

### Reusable vs per-repo (the key mental model)
- **Reusable, copied verbatim** (updated by `adopt`/`update`): `rules/`, `skills/`,
  `agents/`, `commands/`, `hooks/`, `docs/`, `settings.json`.
- **Per-repo overlay, generated then filled**: `.claude/project/*`, `.codex/project/*`.
- **Initialised per repo, never copied**: the beads store (`bd init`).

---

## 7. Maintainer workflows

These regenerate and validate the payload. They are **not** part of adopting into a
repo — they are for whoever maintains the harness source of truth.

### 7.1 `build-template.sh` — regenerate `template/` from the source harness

The source of truth is the harness repo itself (this `coding-ritual` checkout — the
script auto-discovers it by walking up from the plugin's parent for an ancestor with
`.claude/rules` + `.codex`, or honours `HARNESS_SRC=/path`). It then:

1. `rsync --delete` mirrors the source `.claude/`/`.codex/` into the dot-less
   `template/claude`/`template/codex`, **excluding** the per-repo overlay (`/project/`)
   and the project-flavoured python rules.
2. Swaps in the genericised python rules from `scripts/overrides/python/`.
3. Copies `CLAUDE.md` / `AGENTS.md` / `.beads/beads.md`, genericising a few
   project-specific lines (submodule names, the "no first-party source tree" note).
4. Sweeps machine-local paths & example tokens out of the payload
   (`/home/<user>` → `$HOME`, repo root → `<repo-root>`, project/submodule names → `<name>`).
5. **Self-checks and fails loudly** if any project/machine string survived
   (`Bodha`, `gascity`, `gastown`, `/home/pavanmv`, `/data/codes`).
6. Runs `check-sync.sh` as an advisory step (warn-only).

### 7.2 `check-sync.sh` — keep the two trees in sync

`.codex/` is not generated from `.claude/`; both are hand-edited, so a shared change
can land on one side only. `check-sync.sh` reports two kinds of drift:
- **structural** — a file on one side with no counterpart and not allowlisted;
- **one-sided** — a shared file changed on one side since the last `accept`.

```bash
bash scripts/check-sync.sh          # report drift (exit 1 if any)
bash scripts/check-sync.sh accept   # re-baseline after reconciling
```

Intentional divergences are declared in `sync-manifest.txt` (directives: `body`,
`pair`, `claude`, `codex`); the accepted state of each compared pair is recorded in
`sync-baseline.txt`, so the report shows only *new* drift.

---

## 8. `doctor.sh` checks

`/mvp-plugin:doctor` reports PASS/WARN/FAIL and exits non-zero only on a hard FAIL
(missing core). It checks:

1. Core payload dirs present (`.claude/{rules,skills,agents,commands,hooks}`,
   `.codex/{rules,skills,agents}`) + `CLAUDE.md` / `AGENTS.md`.
2. Hooks wired in `settings.json` and executable.
3. No machine-local absolute path in `settings.json` (portability).
4. beads: `bd` on PATH, store initialised, `sync.remote` set.
5. Overlay filled (no `TODO: fill from repo reality` skeletons left).
6. `codex` CLI present (for the sibling codex-adapter) — WARN if not.

---

## 9. Testing

Isolated; no Claude Code account needed (`test/README.md` has detail).

```bash
# Tier-1 suite in a clean image
docker build -f test/Dockerfile -t mvp-plugin-test . && docker run --rm mvp-plugin-test

# From-zero clean-room (no bd → install → green)
docker run --rm -v "$PWD:/opt/mvp-plugin:ro" -e PLUGIN_DIR=/opt/mvp-plugin \
  node:22-bookworm bash /opt/mvp-plugin/test/from-zero.sh

# On the host (uses your real bd/codex/claude)
PLUGIN_DIR=. bash test/run-tests.sh
```

`run-tests.sh` drives the plugin directly: creates a fixture git repo, runs
`install-harness.sh`, and asserts the payload landed, hooks are wired/executable,
paths are portable, beads is initialised with `sync.remote`, overlay skeletons +
gitignore block exist, the payload is generic (no project/machine strings), doctor
exits clean, install is idempotent, and `claude plugin validate` passes.

---

## Current state & caveats

The marketplace restructure (mvp-plugin folded into the single `mvp-harness`
marketplace; the per-plugin `marketplace.json` and the vendored `codex-adapter` copy
removed) left three known drifts to reconcile:

1. **The plugin `README.md` is stale.** It still says "single marketplace with two
   plugins", references `vendor/codex-adapter/`, and lists
   `.claude-plugin/{plugin.json, marketplace.json}`. Under `mvp-harness` there is one
   root marketplace, no vendored copy, and no per-plugin `marketplace.json`.
2. **`test/run-tests.sh` will fail its "bundled codex-adapter" section.** It asserts
   `vendor/codex-adapter/...` files and that `.claude-plugin/marketplace.json` "lists
   both plugins" — both removed. Those assertions need to move to the harness level
   (or be dropped) now that codex-adapter is a sibling plugin.
3. **Install IDs changed.** `mvp-plugin@mvp-plugin` / `codex-adapter@mvp-plugin` →
   `…@mvp-harness`. Any docs/READMEs still using the old `@mvp-plugin` suffix are stale.

Minor: `build-template.sh`'s genericization still targets the old project/machine
tokens (`Bodha`, `orchestrators`, `gascity`/`gastown`); revisit if the source harness
has been renamed.
