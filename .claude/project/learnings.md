# Learnings

Durable, verified, likely-to-recur patterns for **this** repo. Capture only
after a verified fix or a repeated pattern — not speculation. Keep each entry
short: what was observed, why it matters, how to apply it.

Format per entry:

```
## <short title>  (<YYYY-MM-DD>)
- Observed: <what happened / the pattern>
- Why it matters: <consequence>
- Apply: <concrete guidance>
```

## Codex CLI silently swallows bad `-c` config values  (2026-07-10)

- Observed: `codex exec -c model_reasoning_effort=bogus` runs fine (exit 0, no
  warning) and silently falls back to the config default; same for any
  unrecognized `-c` key/value. Verified on codex-cli 0.144.1.
- Why it matters: wrapper-side typos in effort/sandbox/config overrides fail
  open, not closed — on a machine whose `config.toml` defaults to
  `workspace-write`, a typo'd sandbox value silently yields a writable run.
- Apply: any wrapper around `codex exec` must validate safety-critical values
  itself (hard-fail for sandbox, warn-and-forward for the rest). Prefer the
  native `-s` flag on plain `codex exec` — it outranks all config overrides,
  including `default_permissions` profile keys that supersede `sandbox_mode`;
  note `exec resume`/`exec review` don't accept `-s` (config override only).

## Codex CLI accepts hidden flags its --help doesn't list  (2026-07-10)

- Observed: `--yolo` and `--full-auto` are accepted by `codex exec` 0.144.1
  (probed via `-h` short-circuit: exit 0 vs exit 2 for a bogus flag) but absent
  from `--help`. Both escalate the sandbox.
- Why it matters: flag allowlists or deny-checks built from `--help` output are
  incomplete; pass-through wrappers can smuggle escalations.
- Apply: when guarding a pass-through surface, probe suspected hidden flags
  with `<cmd> <flag> -h` and deny by pattern, not by the documented list. Always
  emit a `--` before a positional prompt so dash-prefixed text can't be parsed
  as a flag by the child CLI.

## `bd init` commits, and sweeps untracked files at its known paths  (2026-08-19)

- Observed: `bd init --non-interactive --skip-agents` (bd 1.1.0 and 1.2.2)
  always makes one git commit — its own `.beads/` + `.gitignore` — and also
  stages any *untracked* `CLAUDE.md`, `AGENTS.md`, `.claude/settings.json`,
  `.codex/*` it finds (not other untracked files). No flag suppresses the
  commit. With `--skip-agents` it does not edit CLAUDE.md/AGENTS.md, add a
  skill, or touch global config; it sets `core.hooksPath=.beads/hooks` and
  chains pre-existing hooks. Without `--skip-agents` it appends BEADS
  INTEGRATION blocks to both files, adds `.agents/skills/beads/`, and edits
  `.claude/settings.json` + `.codex/hooks.json`.
- Why it matters: an installer that lays files and then runs `bd init` ships a
  half-committed harness; a teammate's clone inherits the half. Found by the
  plugin's live install matrix (cell 8), not by unit tests.
- Apply: run `bd init` before laying any residue; always pass `--skip-agents`;
  tell the user bd made a commit; keep the residue uncommitted for review.

## Plugin scope facts that bite install tooling  (2026-08-19)

- Observed: `claude plugin list --json` lists project-scope rows for every repo
  on the machine (with `projectPath`); `claude plugin install --scope project`
  pre-creates `.claude/settings.json` and later rewrites it dropping unknown
  keys (hook `description`); `claude plugin marketplace remove` uninstalls the
  plugin from every scope silently. Codex has user scope only; repo hooks run
  only after per-hook approvals (`hooks.state."<repo>/.codex/hooks.json:*"`
  in `~/.codex/config.toml`), which only the interactive prompt writes.
- Why it matters: status checks that take the first list row, file-merge on
  settings.json, or `trust_level`-only checks all misreport.
- Apply: filter plugin rows by `projectPath`; JSON-merge settings.json; check
  `hooks.state` counts; test install flows in a clean container with real
  CLIs (`mvp-harness/plugins/mvp-plugin/test/` + a long-lived lab container).
