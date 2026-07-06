# Plan: unify the three harness plugins under one marketplace

**Status:** PARKED (awaiting decisions 1–3 below) · drafted 2026-06-26
**Owner:** PavanMV · **Scope:** `my_harness/` (gitignored, not part of `coding-ritual`)

> Parked at user request while handling a separate `claudex-rc` heal issue.
> User decision already made: **all three plugins under ONE marketplace.**

## Verified current state

- `my_harness/` is a plain directory inside `coding-ritual`, **gitignored** (`my_harness/*`),
  not its own git repo, not tracked anywhere.
- Three plugins, **each currently its own separate marketplace** (each has both
  `plugin.json` *and* its own `marketplace.json`):
  - **`mvp-plugin`** — standalone GitHub repo `MVPavan/mvp-plugin`, on `main`, README dirty.
    Its marketplace lists 2 plugins (itself + a **vendored copy** of codex-adapter at
    `./vendor/codex-adapter`). Bundles a large `template/` tree.
  - **`codex-adapter`** — standalone GitHub repo `MVPavan/codex-adapter`, on `main`, clean.
  - **`code-intel`** — plain dir, **no git, unpublished**.
- `vendor/codex-adapter` is an in-sync copy of codex-adapter (identical except it lacks the
  marketplace.json). Real references to it: the `source` line in mvp-plugin's marketplace.json,
  4 assertions in `mvp-plugin/test/run-tests.sh`, and wording in `scripts/doctor.sh` +
  `test/README.md` + `mvp-plugin/.claude-plugin/plugin.json` description.
- Reference pattern (`reference_harnesses/claude-plugins-official`): **one** root
  `.claude-plugin/marketplace.json` + a `plugins/<name>/` dir per plugin, each holding **only**
  `plugin.json`. In-tree plugins use `"source": "./plugins/<name>"`.

## Target structure

```
my_harness/
├── .claude-plugin/
│   └── marketplace.json        # THE single marketplace, lists all 3 plugins
├── README.md                   # new: what this marketplace is + install steps
└── plugins/
    ├── mvp-plugin/    └── .claude-plugin/plugin.json   (marketplace.json removed)
    ├── code-intel/    └── .claude-plugin/plugin.json   (marketplace.json removed)
    └── codex-adapter/ └── .claude-plugin/plugin.json   (marketplace.json removed)
```

Unified `marketplace.json` shape:

```json
{
  "$schema": "https://anthropic.com/claude-code/marketplace.schema.json",
  "name": "mvp-harness",
  "owner": { "name": "PavanMV", "email": "mvpavan42@gmail.com" },
  "metadata": { "description": "PavanMV's agent-harness plugins", "version": "0.1.0" },
  "plugins": [
    { "name": "mvp-plugin",    "source": "./plugins/mvp-plugin",    "category": "workflow",    "description": "...", "version": "0.1.0", "author": {} },
    { "name": "code-intel",    "source": "./plugins/code-intel",    "category": "development", "description": "...", "version": "0.1.0", "author": {} },
    { "name": "codex-adapter", "source": "./plugins/codex-adapter", "category": "development", "description": "...", "version": "1.0.1", "author": {} }
  ]
}
```

## Git model — decision needed (recommend A1)

- **A1 — Monorepo (recommended).** `my_harness` becomes one git repo; all 3 plugins live
  in-tree under `plugins/` with `"source": "./plugins/<name>"`. Retire standalone
  `mvp-plugin`/`codex-adapter` repos (archive on GitHub, or import history via `git subtree`).
  → one source of truth, atomic cross-plugin commits, vendor duplicate vanishes, matches the
  in-tree reference examples.
- **A2 — Thin marketplace + git sources.** `my_harness` holds only marketplace.json
  (+ code-intel in-tree); mvp-plugin & codex-adapter stay separate repos, referenced by pinned
  git `source` (url+ref+sha). → keeps independent publishing, but must bump SHAs each release.

## Implementation steps (for A1)

1. Commit/stash the dirty `mvp-plugin/README.md` first so nothing is lost (no push).
2. Create `my_harness/plugins/`; move all three plugin dirs into it.
3. Strip nested `.git` from `mvp-plugin` and `codex-adapter` (history stays on GitHub).
   [decision 2: archive vs `git subtree` import]
4. Delete `vendor/codex-adapter` (codex-adapter becomes a first-class sibling).
5. Delete the 3 per-plugin `marketplace.json`; keep each `plugin.json`.
6. Write `my_harness/.claude-plugin/marketplace.json` (unified, with `$schema`).
7. Fix now-stale references in mvp-plugin:
   - `test/run-tests.sh` — remove the 4 `vendor/codex-adapter/...` assertions + the
     "marketplace lists both plugins" check; optionally add a check that the **root**
     marketplace lists all three.
   - `scripts/doctor.sh` + `test/README.md` + `plugin.json` description — reword
     "bundles/vendored codex-adapter as co-plugin" → "sibling plugin in the harness marketplace".
8. Init `my_harness` as its own git repo; add root `README.md` with install instructions
   (`/plugin marketplace add <path-or-URL>` then `/plugin install mvp-plugin@mvp-harness`, etc.).
9. Verify (below). Do **not** create the GitHub repo or push without explicit go-ahead.

## Verification

- `find my_harness -name marketplace.json` → exactly one, at the root.
- Each `plugins/<name>/.claude-plugin/plugin.json` parses.
- Root `marketplace.json` parses; lists all 3; each `./plugins/<name>` source exists on disk.
- `bash my_harness/plugins/mvp-plugin/test/run-tests.sh` passes after the edits.
- No remaining `vendor/codex-adapter` path references outside template doc prose.

## Open decisions

1. Git model: **A1** (monorepo, recommended) or **A2** (thin marketplace + git sources)?
2. If A1 — old repos: archive `MVPavan/mvp-plugin` & `MVPavan/codex-adapter` and start fresh
   (simplest), or preserve history via `git subtree`?
3. Marketplace name: **`mvp-harness`** (recommended — avoids the `mvp-plugin`
   marketplace-vs-plugin name clash), or `coding-ritual-plugins` / keep `mvp-plugin`?
