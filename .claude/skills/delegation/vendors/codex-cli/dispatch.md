# Codex CLI

Call the Codex CLI directly. The codex-adapter plugin (`codex-run.mjs` and its
`/codex-*` skills) was retired on 2026-09-23.

**Model list:** `python3 scripts/models.py refresh codex-cli` records `codex
debug models` under `.delegation/models/`, dropping hidden models, with the time
Codex last fetched its catalog from the server. A catalog with no server fetch
behind it (signed out or offline) fails the check. Check a pair before every
launch with `python3 scripts/models.py check codex-cli <model> --effort <level>`:
Codex has accepted an invalid `-c` effort value without error (CLI 0.144.1).

```bash
# New run. Sandbox: read-only for explorer, reviewer and critic; workspace-write
# for an implementer.
codex exec -C <dir> -s <sandbox> -m <model> -c model_reasoning_effort=<level> \
  -o <answer-file> "<brief>" < /dev/null 2> <log-file>
# Follow-up in the worker's own session. Resume takes no -C or -s; set the
# sandbox with -c.
cd <dir> && codex exec resume <session-id> -m <model> -c sandbox_mode=<sandbox> \
  -c model_reasoning_effort=<level> -o <answer-file> "<follow-up>" < /dev/null
```

- The session ID is the first `session id:` line on stderr; `-o` writes the
  final answer to a file. Prefer resume over a fresh run for follow-ups.
- Always close stdin. Otherwise `codex exec` waits for input with no timeout (a
  review once hung for over 30 minutes).
- `--worktree` runs a new session in a fresh managed Git worktree when a writer
  needs its own checkout.

**Read-only roles:** `-s read-only` (or `-c sandbox_mode=read-only` on resume) is
enforced by Codex's sandbox.

**What ran:** `python3 scripts/models.py ran codex-cli <session-id>` reads the
model, effort and sandbox from the session's own record.
