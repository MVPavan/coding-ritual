# Beads setup

How to install `bd` and adopt Beads in a project that uses this harness, and
how to join an existing Beads project from a new machine or clone. The rules
for using Beads are in `usage.md`. Upgrading `bd` across several projects is
an owner procedure with its own principles: `harness_lifecycle/beads/upgrades.md`.

## 1. Install bd

- Use the release the harness is written for (1.3.0). Download the release
  asset, check it against the release's `checksums.txt`, and put `bd` on
  `PATH` (for example `~/.local/bin`). Never install from a moving `main`
  script.
- Confirm with `bd version` and `which -a bd`. Exactly one `bd` should be on
  `PATH`; a second one, for example from a global npm install, gets used by
  hooks without warning.
- Turn usage metrics off on every new machine, container and sandbox:
  `bd metrics off`. A fresh HOME starts with metrics on.

## 2. Adopt Beads in a project

Run from the project's own clone, not a folder nested inside another Beads
repository.

1. **Check for a database first.** If `.beads/` already exists, or the
   project has a Dolt remote, this is a join, not an adoption: go to §3.
2. **Nested folder only.** A database inside another git repository needs
   its own `git init` and a seeded `.beads/config.yaml` before `bd init`.
   Otherwise `bd init` resolves to the parent's database (and so do
   `BEADS_DIR` and `--directory`), or copies the parent's `sync.remote`.
   Afterwards, check `bd dolt remote list`.
3. **Initialise without agent recipes:**

   ```bash
   bd init --skip-agents --prefix <short-prefix>
   ```

   Plain `bd init` also writes Claude, Codex and Cursor hooks, a
   `.agents/skills/beads` skill and an AGENTS.md block that conflict with
   this harness. Never run `bd setup` either. Then inspect `git status` and
   `git log`: init can commit its own files.
4. **Remove upstream boilerplate.** Delete `.beads/README.md`. It is generic
   text, and it shows `--status done`, which is not a valid status.
5. **Configure** in `.beads/config.yaml`:

   ```yaml
   export:
     auto: true      # keep .beads/issues.jsonl current
     git-add: false  # never stage it automatically; commits stage explicit paths
   ```

   Check the result with `bd config show`. Keep machine-specific settings in
   `.beads/config.local.yaml`, never in the tracked file.
6. **Ignore the gate lock.** Add `*.gate.lock*` to the root `.gitignore`.
   Bd 1.3.0 keeps a permanent `.beads.gate.lock` there; never delete it.
7. **Git hooks.** Run `bd hooks install --beads`, which writes the hook files
   to `.beads/hooks/`. Check `bd hooks list`, and check that
   `git config core.hooksPath` names `.beads/hooks`. The hooks run Beads
   logic on commit, merge, push and checkout.
8. **Session context.** The harness's prime hooks inject Beads context at
   every session start and compaction. Check they are wired:
   - Claude Code: `.claude/hooks/bd-prime.sh` on `SessionStart` (matcher
     `""`) in `.claude/settings.json`;
   - Codex: `.codex/hooks/bd-prime.sh` on `SessionStart` (matcher
     `startup|resume|clear|compact`) in `.codex/hooks.json`.

   Then replace bd's built-in prime text with this skill's rules:

   ```bash
   ln -s ../.claude/skills/beads/references/prime.md .beads/PRIME.md
   bd prime | head -5   # must start with "# Beads: core rules"
   ```

9. **Point AGENTS.md at the skill.** The Beads line names the `beads` skill
   and says that `prime.md` arrives at session start.
10. **Remote.** `bd dolt remote list` shows the remote that init took from
    the git `origin`. The first `bd dolt push` needs the owner's authority.

## 3. Join an existing project (new machine or fresh clone)

- A `git clone` carries no beads; they live on the Dolt remote under
  `refs/dolt/data`. Run `bd bootstrap` in the clone. It downloads the
  database from the remote, or restores it from a backup or JSONL.
- Never run `bd init` here. On a fresh clone, `bd ready` fails with "no beads
  database found" and suggests `bd init`, which would create a new, empty
  database.
- Beads that were never pushed from the other machine will be missing.
  Compare counts (`bd count`) before relying on the clone.
- Run `bd metrics off`, then `bd hooks list`.
- A git worktree needs none of this: it uses the main clone's database
  (`bd where` shows which).

## 4. Verify

| Check | Expect |
|---|---|
| `bd where` | this project's `.beads` |
| `bd ping` | the database answers |
| `bd prime \| head -5` | `# Beads: core rules` |
| `bd hooks list` | five hooks installed |
| `bd config get export.auto` | `true` |
| `bd metrics` | off |
| `git status` | no unexpected files from init |

`bd doctor` is not a check here: it does not run in embedded mode.
