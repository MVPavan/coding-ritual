# Harness Patterns By Capability

This file records the best upstream source for each capability, what was kept, and what was rejected to keep the local harness lean.

| Capability | Best Source | Kept Pattern | Rejected Pattern |
| --- | --- | --- | --- |
| Project brief | Everything Claude Code | short root instruction file with exact verification commands and structure summary | oversized project brain files |
| Brainstorming | Compound Engineering | scope-first brainstorm, one question at a time, 2-3 real options, durable requirements doc | long workflow catalogs and org-specific tooling assumptions |
| Planning | Compound Engineering + Superpowers | research first, requirements as source of truth, tracer-bullet planning, explicit verification | heavyweight plan templates and shell choreography |
| Document review | Compound Engineering | doc-to-repo consistency checks and focused risk review | multi-persona review lattices by default |
| Skill routing | Superpowers | process before execution, use the right workflow surface first | over-aggressive skill triggering for marginal cases |
| Subagent execution | Superpowers | fresh worker per task, task packets, spec review before code review, escalation statuses | high-ceremony orchestration and extra machinery |
| Verification | Superpowers | evidence before claims, fresh command output, no trusting reports | moralizing verbosity and duplicate gates everywhere |
| Python review | Everything Claude Code | Python-first code-review heuristics, layered Python rules | large surrounding catalog and extra repo-specific detail |
| TDD | Matt Pocock + Superpowers | one behavior at a time, red-green-refactor, behavior over implementation | turning every task into a rigid tutorial |
| Debugging | Superpowers | root-cause-first, single hypothesis, falsification loop | speculative fix stacking |
| Git safety | Matt Pocock + Bodha pattern | dangerous-command blocking and explicit staging | heavy git workflow ceremony |
| Memory and learnings | Bodha + Compound Engineering | lightweight progress tracking, verified durable learnings, discoverability | verbose journals and duplicated knowledge stores |
| Discoverability | Compound Engineering | make long-lived docs visible from core instructions | giant documentation scaffolds |
| Claude-Code/Codex collaboration | local synthesis | one-way actor-critic model with high-leverage gates only | symmetric assumptions or Codex on every subtask |

## Resulting Harness Shape

The current local direction is:

- stable core harness
- project-specific overlay
- concise rules
- compact skills and commands
- bounded agent roles
- Python-first defaults
- selective Codex use only at high-leverage checkpoints

## What To Add Carefully

- new skills only when a workflow repeats and is expensive to reconstruct
- new rules only when they are stable and checkable
- new hooks only when the enforcement is fast and mechanical

## What To Avoid

- giant catalogs
- duplicated policy in multiple files
- local absolute paths
- permanent mega-thread orchestration
- vendor-specific internals in the generic canon
