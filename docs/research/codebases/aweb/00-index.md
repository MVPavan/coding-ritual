# aweb — research registry

Repo: `reference_tools/aweb` (submodule, pinned `da5854cf`, 2026-08-22).
Self-hostable communication + identity substrate for independently running
agents: durable mail/chat, wake events, presence, locks, AWID identity.
Server 1.27.4 (beta) — the most mature of the three evaluated repos.
Explicitly does NOT own agent definitions, processes, or workflow.

| Artifact | What it is | Produced by |
|---|---|---|
| [capabilities.md](capabilities.md) | Docs-first capability + architecture map @ da5854cf | GPT-5.6-luna xhigh, 2026-08-24 |
| [../comparison-beadboard-aweb-looptroop.md](../comparison-beadboard-aweb-looptroop.md) | Two-reviewer assessment + consolidation (Sol high × Opus 5 medium) | 2026-08-24 |

## Verdict (consolidated)

**Reject/defer as platform (4-service footprint at a layer we haven't
opened); steal two mechanisms now.**

1. The `Provider` interface (`cli/go/run/types.go:53-60`): 6 methods → one
   normalized Event, proven on Claude + Codex — the shape for our uniform
   runner floor. Copy the human-facing resume-hint and reject-on-unsupported-
   option; invert its danger-flag default; note its Codex parser extracts no
   usage/cost — cost normalization stays our own work.
2. Wake-as-hint protocol: signal carries ids only → fetch exact durable
   record → durably mark delivery *before* ack → reconcile from durable state
   on reconnect. Earmarked for when the communication layer opens (not v1).

Reopen triggers: durable multi-machine coordination; cross-org agent
identity; runner floor grows past three vendors. Avoid: its native task
queue (a strictly weaker bd), the AWID/federation stack, cursor-less SSE for
anything semantically load-bearing.
