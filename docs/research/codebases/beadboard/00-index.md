# beadboard — research registry

Repo: `reference_tools/beadboard` (submodule, pinned `9e3059d`, 2026-07-26).
Multi-agent orchestration console built on beads (bd): Next.js dashboard,
`bb` CLI, embedded Pi worker runtime. v0.1.0, `private: true`, orchestrator
"under construction".

| Artifact | What it is | Produced by |
|---|---|---|
| [capabilities.md](capabilities.md) | Docs-first capability + architecture map @ 9e3059d | GPT-5.6-luna xhigh, 2026-08-24 |
| [../comparison-beadboard-aweb-looptroop.md](../comparison-beadboard-aweb-looptroop.md) | Two-reviewer assessment + consolidation (Sol high × Opus 5 medium) | 2026-08-24 |

## Verdict (consolidated)

**Reject as platform; harvest two parts.** Completion = "model stopped
talking" (`worker-session-manager.ts:377-414`); runtime is Pi-only at the
type level; workers/runtime state in-process (lost on restart); the coord.v1
subsystem writes through `bd audit record`, which a live probe showed
silently drops every field outside its closed schema — the coordination
migration is non-functional on bd v1.1.0.

Steal: (1) bd **event beads** (`--type event --event-payload`, `--ephemeral
--wisp-type` for heartbeat noise) as candidate transition/activation records
— the payload round-trips where audit records do not; (2) the read-only
bd→graph projection (blocker normalization + anomaly diagnostics) as a later
operator view. Everything else: anti-example (advisory read-side-only
reservations, dual coordination systems, silent Dolt→JSONL fallback).
