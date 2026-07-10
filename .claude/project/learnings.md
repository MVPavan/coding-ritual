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
