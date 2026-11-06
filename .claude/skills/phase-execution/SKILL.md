---
name: phase-execution
description: Execute one phase of a workstream roadmap. Thin entry point for the implement skill's phase scope.
disable-model-invocation: true
---

# Phase Execution

Invoke the **implement skill** in **phase scope**
(the implement skill → Phase scope).

- **Input:** phase id and roadmap path, e.g.
  `/phase-execution E --roadmap docs/workstreams/<name>/roadmap.md`. If the
  roadmap is omitted and ambiguous, ask which workstream.
- Carry prior approval covering this phase and its plan. Workstream-wide
  authority does not arise from a single-phase invocation; unresolved material
  scope decisions still need the user.
