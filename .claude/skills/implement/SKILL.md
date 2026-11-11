---
name: implement
description: "Run settled, tracked work through the implement playbook: a bead, a plan, a roadmap phase, all remaining phases, or a spec. Thin entry point."
disable-model-invocation: true
---

# Implement

Run the implement playbook (`playbooks/implement.md` in the mvp-mode skill) for
the scope named:

- `/implement <bead-id | plan path>`: Task scope.
- `/implement phase <id> [--roadmap <path>]`: Phase scope, e.g.
  `/implement phase E --roadmap docs/workstreams/<name>/roadmap.md`. Carry prior
  approval covering this phase and its plan. Workstream-wide authority does not
  arise from a single-phase invocation; unresolved material scope decisions still
  need the user.
- `/implement all phases [<roadmap>]`: Workstream scope. This invocation **is**
  the explicit user opt-in that workstream mode's auto-approvals and per-phase
  commits require — record it in the workspace ledger as workstream-mode.md's
  preflight directs.
- `/implement spec <path>`: Spec scope.

With no argument, or a roadmap that is omitted and ambiguous, ask which work.
