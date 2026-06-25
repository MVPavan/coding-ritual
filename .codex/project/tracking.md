# Issue Tracking

This repo uses **bd (beads)** for durable issue tracking.

- **Backend:** embedded Dolt (`.beads/`), database `coding-ritual`.
- **Issue prefix:** auto-detected from the directory name (`coding-ritual`) on the
  first `bd create`; `issue-prefix` is left unset in `.beads/config.yaml`.
- **Sync remote:** `git+https://github.com/MVPavan/coding-ritual.git`
  (`sync.remote` in `.beads/config.yaml` — the repo's own git remote).
- **JSONL export:** `export.auto: true` — keeps `.beads/issues.jsonl` fresh.
- **State:** initialized, no issues yet (`bd list` → none).

Workflow, agent context profiles, and the session-completion protocol live in
**`.beads/beads.md`**. Run `bd prime` for runtime context, `bd ready` for
actionable work.
