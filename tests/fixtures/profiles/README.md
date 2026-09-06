# Captured vendor streams (phase 4)

Every file here is a real CLI's real output, recorded during the phase-4 step-0
probes on 2026-08-26 (`scratchpad/probes/phase4-cli-probes.md` holds the same
bytes with the commands that produced them). Versions: `claude 2.1.227`,
`codex-cli 0.148.0`, `opencode 1.18.21`.

They exist because argv correctness is not stream correctness. A `parse_output`
tested against streams somebody wrote by hand tests the author's model of the
vendor, which is exactly what the probes overturned nine times.

## Provenance and redaction

The transformations applied before committing are declared as executable data in
`tests/_profiles.py::REDACTIONS`, applied by `redact()`, and CHECKED by
`tests/test_profiles_parse.py::test_every_committed_fixture_is_a_fixed_point_of_the_declared_redactor`.
The list here is a description of that code, never a second source of truth:

| # | What | Becomes | Why |
|---|---|---|---|
| 1 | the probe working directory | `/wf/probe` | names this machine's checkout |
| 2 | any `/home/<user>` | `/home/runner` | names the operator |
| 3 | `/tmp/cc-socks/<pid>.sock` | `/tmp/cc-socks/0.sock` | claude's per-process IPC socket carries a host pid |
| 4 | `cf-ray: <id>-<COLO>` | `cf-ray: 0000000000000000-XXX` | Cloudflare request id; the suffix is a datacenter code |

Nothing else is rewritten. Session ids, thread ids, token counts, costs, tool
inputs and error text are the capture and are what the tests assert on.

The earlier claim was "two substitutions and nothing else", and it was not true:
one capture had its socket pid normalized and three did not. That is the whole
reason the list is now code with a test behind it — a provenance claim nobody
can re-derive is a claim nobody can check.

`FORBIDDEN` (same module) is the negative half: no unredacted home, no probe
path, no live socket pid, and no credential-shaped string
(`sk-…`, `ghp_…`, `Bearer …`, an e-mail address). `apiKeySource` is `"none"`
throughout — these runs authenticated from a subscription, not from a key.

## What each file is

| File | The run it came from |
|---|---|
| `claude/oneshot.jsonl` | `-p … --output-format stream-json --verbose`, one turn |
| `claude/resume.jsonl` | `--resume` of that same session — drill 14's identity half |
| `claude/result.json` | the `--output-format json` single-object form; zero denials |
| `claude/tools.jsonl` | the `writes = false` bound: a read, an allowed write, a denied one |
| `claude/writes.jsonl` | the `writes = true` bound: checkout + channel writes allowed, an outside write and `git push` denied |
| `codex/oneshot.jsonl` | `codex exec --json`, one turn |
| `codex/resume.jsonl` | `codex exec resume` of it — same `thread_id` |
| `codex/commands.jsonl` | shell steps, including the `curl` that could not resolve a host |
| `codex/auth_error.jsonl` | a real 401 run: `error` lines, exit 1, usage unknown |
| `opencode/oneshot.jsonl` | `opencode run --format json` |
| `opencode/resume.jsonl` | `-s <session>` of it |
| `opencode/tools.jsonl` | a tool call plus per-step usage |

Two files come from a later run and are labelled so nobody reads them as
phase-4: the first live build-loop run of 2026-09-05
(`scratchpad/probes/phase7-live/`, `claude 2.1.258`), whose `usage: unknown`
records put the vendor streams under suspicion (defect D3, bead cr-o85.34.23).

| File | The run it came from |
|---|---|
| `claude/live-result.jsonl` | the `wf-so4` activation's terminal `result` line — 2.1.258 adds `modelUsage`, `iterations` and `speed` beside the same `usage`/`total_cost_usd` pair |
| `codex/live-turn-completed.jsonl` | the `wf-v8x` reviewer's terminal `turn.completed` line |
