# Agent Matrix — progress and resume anchor

Snapshot: 2026-08-11

Workstream state: **paused with catalog reconciliation remaining**

Primary Beads issue: `cr-y9r` — `in_progress`

This file is the model-neutral entry point for resuming Agent Matrix work. It
records the state that was verified from the repository and local evidence; it
does not depend on earlier chat history.

## Current verdict

The architecture research, compact value catalog, provider-specific selection
skills, deterministic validator, unit tests, and runtime evidence harness
exist. The Codex validation run reached exact coverage for its dated test plan.

The required Claude review was completed locally on 2026-07-28 with Claude
Code `2.1.220`. It produced live invocation- and definition-layer evidence and
material corrections to the Claude-facing skill. No repository files were sent
to an external reviewer.

The workstream is **not complete**. `cr-y9r` remains open because the compact
catalog still needs to distinguish invocation-layer values from
definition-layer values, reconcile the observed `extra` effort value, and
update the dated Claude version claim from `2.1.217` to `2.1.220` without
overstating what the runtime proved.

The runtime conclusions are versioned facts, not timeless product promises.
The dated evidence was captured with:

- Claude Code `2.1.220`
- Codex CLI `0.144.4`

Re-check both versions and the active agent-tool schema before extending or
re-running the matrix.

## Read first

From the repository root, read these in order:

1. [`AGENTS.md`](../../../../AGENTS.md) and the current project instructions
   under [`.codex/project/`](../../../../.codex/project/).
2. The approved validation requirements:
   [`2026-07-23-agent-matrix-validation-requirements.md`](../../../brainstorms/2026-07-23-agent-matrix-validation-requirements.md).
3. The implementation plan:
   [`agent-matrix-codex-validation-plan.md`](../../../plans/agent-matrix-codex-validation-plan.md).
4. The research index and report map: [`00-index.md`](00-index.md), followed by
   [`90-open-questions.md`](90-open-questions.md) for version-sensitive gaps.
5. The selectable-value source of truth:
   [`agent-matrix-values.yaml`](agent-matrix-values.yaml). The expanded file,
   [`agent-matrix-values-expanded-reference.yaml`](agent-matrix-values-expanded-reference.yaml),
   is reference material, not the runtime selection registry.
6. The provider-facing skills:
   [Codex](../../../../.codex/skills/agent-matrix/SKILL.md) and
   [Claude](../../../../.claude/skills/agent-matrix/SKILL.md).
7. The validator and tests:
   [`agent_matrix.py`](../../../../tools/agent-matrix/agent_matrix.py) and
   [`test_agent_matrix.py`](../../../../tools/agent-matrix/test_agent_matrix.py).

## Stable design decisions

Model an agent as four separate layers:

1. **Role** — durable identity, delegation description, and behavioral prompt.
2. **Capability policy** — tools, MCP servers, skills, permissions, and
   isolation.
3. **Execution profile** — provider, model, reasoning or effort, and service
   tier where the active surface supports it.
4. **Invocation** — task, context mode, foreground/background behavior, and
   runtime limits.

Keep role definitions independent from model/effort combinations. Do not
create one permanent role file for every Cartesian combination.

Provider constraints that must stay explicit:

- Codex full-history forks inherit their parent configuration; model, effort,
  and role overrides are not reliable on that path.
- Codex fresh and last-N invocations use explicit `fork_turns` values.
- Claude named subagents start with fresh context. `/subtask` is the reliable
  user-started full-context path; `subagent_type: fork` is experimental and was
  absent from the tested `2.1.220` agent registry. Native last-N context is
  unsupported.
- Claude's invocation model field accepts short aliases, while full model IDs
  belong in agent definitions.
- Claude Code `2.1.220` has no per-Agent invocation effort field.
- Requested capability configuration and effective runtime capability are
  different evidence. Report static catalog selection, tool-schema acceptance,
  backend acceptance, and observed child configuration separately.
- Reject undeclared values. Never silently substitute a nearby model, effort,
  capability, skill, or context mode.

## What is implemented

The implementation introduced by commit `8f15953` includes:

- a shared compact YAML registry;
- provider-specific Agent Matrix skills for Codex and Claude;
- a standard-library Python CLI that validates the catalog and selections,
  builds Codex plans, probes config surfaces, collects observations, and checks
  coverage/tracers;
- sixteen unit tests;
- catalog registration and the requirements/plan artifacts.

The prior architecture research was introduced by commit `f16de5f`.

The 2026-07-28 Claude review additionally established that declared and
effective tool lists can differ: with `Bash` in the tested definition tool
lists, `Grep` and `Glob` were silently removed. Treat this as dated observed
behavior, not a documented universal contract.

## Verification evidence

Fresh structural verification on 2026-07-28 produced:

```text
valid catalog: docs/research/codebases/subagent-runtimes/agent-matrix-values.yaml
valid skills: 2
Ran 16 tests ... OK
```

The dated Codex run in local scratch evidence contains exactly 107 planned and
107 collected cases:

| Status | Cases |
|---|---:|
| `pass` | 79 |
| `fail` | 3 |
| `unsupported` | 22 |
| `untestable` | 3 |
| `infra_error` | 0 |

The tracer passed with observed model `gpt-5.6-terra` and effort `low`.

The three `fail` results document hosted-contract drift rather than incomplete
coverage: a blank message was accepted, and full-history model/effort overrides
were accepted but ignored. The 22 unsupported cases record models rejected by
that active spawn surface. The dated evidence also showed that Luna worked as a
direct model and through a Luna-parent inherited child, while the V2 Sol/Terra
parent surface rejected a Luna override before child creation. Treat all of
this as evidence for the 2026-07-23 runtime, not proof of current availability.

## Canonical versus local-only evidence

| Location | Role | Portability |
|---|---|---|
| This research folder | Architecture, value catalog, and this resume anchor | Canonical repository content |
| [Provider skills](../../../../.codex/skills/agent-matrix/SKILL.md) | Operational selection guidance | Canonical repository content |
| [`tools/agent-matrix/`](../../../../tools/agent-matrix/) | Deterministic validation and collection | Canonical repository content |
| [`scratchpad/agent-matrix/`](../../../../scratchpad/agent-matrix/) | Plans, observations, rollout-derived results, Claude review prompt | Local and gitignored |
| [`scratchpad/agent-runtime-source/`](../../../../scratchpad/agent-runtime-source/) | Exact Claude package and tagged Codex source used for research | Local and gitignored |
| Beads issue `cr-y9r` | Durable work status and acceptance history | Canonical tracker; export before handoff |

Scratchpad evidence can disappear on another machine. If it is absent, retain
the committed research conclusions but do not claim the 107-case runtime run
was reproduced. Rebuild a new plan and capture new evidence instead.

Useful local scratch files, when present:

- `scratchpad/agent-matrix/codex-plan.json`
- `scratchpad/agent-matrix/codex-results.jsonl`
- `scratchpad/agent-matrix/codex-results.md`
- `scratchpad/agent-matrix/codex-live-observations.jsonl`
- `scratchpad/agent-matrix/codex-config-results.jsonl`
- `scratchpad/agent-matrix/claude-review-prompt.txt`
- `scratchpad/agent-matrix/claude-runtime.json`
- `scratchpad/agent-matrix/claude-results.md`

`codex-results-rollouts.*` is an earlier rollout-only intermediate. The final
107-case result is `codex-results.*`.

## Remaining work

### Required to close `cr-y9r`

1. Reconcile `agent-matrix-values.yaml` so Claude invocation aliases and agent-
   definition model IDs are separate selectable surfaces.
2. Reconcile `extra`, which was observed in an agent definition but is absent
   from the compact effort registry; do not claim it is effective until that
   can be observed or otherwise verified.
3. Update the versioned Claude research claims from `2.1.217` to `2.1.220`
   where supported by `claude-runtime.json` and `claude-results.md`.
4. Keep the Claude review's material skill corrections. Do not create
   Cartesian agent-definition files or turn observed quirks into timeless
   guarantees.
5. Re-run catalog, skill, unit, and structural verification. Record the
   reconciliation on `cr-y9r`, then close it only if every acceptance criterion
   is satisfied.

### Version-refresh work, only when needed

If either runtime version or the active agent-tool contract has changed, open a
new scoped Beads issue. Re-probe before editing the static catalog. In
particular, re-check:

- exposed models and effort levels;
- full/fresh/last-N context behavior;
- Claude invocation-time effort support;
- Codex role precedence and permission inheritance;
- per-spawn service-tier support;
- reliable effective-model/effective-effort evidence.

Do not overwrite the dated evidence with a new run unless the new run preserves
its own version, tool-contract provenance, cutoff, and result artifacts.

## Safe resume procedure

Run from the repository root:

```bash
bd prime
bd show cr-y9r
git status --short --branch
codex --version
claude --version
uv run python tools/agent-matrix/agent_matrix.py validate-catalog
uv run python tools/agent-matrix/agent_matrix.py validate-skills
uv run python -m unittest tools/agent-matrix/test_agent_matrix.py
uv run python -m py_compile \
  tools/agent-matrix/agent_matrix.py \
  tools/agent-matrix/test_agent_matrix.py
```

If the local final evidence exists, verify its completeness without spawning
new agents:

```bash
python3 tools/agent-matrix/agent_matrix.py check-coverage \
  --plan scratchpad/agent-matrix/codex-plan.json \
  --results scratchpad/agent-matrix/codex-results.jsonl
python3 tools/agent-matrix/agent_matrix.py check-tracer \
  --plan scratchpad/agent-matrix/codex-plan.json \
  --results scratchpad/agent-matrix/codex-results.jsonl
```

Before a new live matrix run, use the current Agent Matrix skill, inspect the
active tool schema, generate a new plan from exactly the models exposed by that
schema, and run one tracer before broad spawning. Live spawning incurs model
usage and is not implied by merely resuming the document work.

## Completion boundary

Do not call Agent Matrix complete until:

- both skills remain discoverable and validate;
- invocation- and definition-layer catalog values are no longer conflated;
- the Claude `extra` effort observation and `2.1.220` version evidence are
  reconciled without unsupported claims;
- the relevant current runtime evidence is exact and auditable;
- open version-dependent exceptions are reported rather than hidden;
- `cr-y9r` is closed, Beads is exported, and `git status` is inspected.

## Copyable resume prompt

```text
Resume the Agent Matrix workstream from
docs/research/codebases/subagent-runtimes/PROGRESS.md. Do not rely on prior chat
history. Read the linked requirements, plan, research index, compact catalog,
both provider skills, and Beads issue cr-y9r. First run the safe resume checks.
Treat scratchpad evidence as optional and dated. Preserve the four-layer design
and strict catalog validation. The Claude review is complete; the remaining
acceptance work is catalog layer separation, `extra` effort reconciliation, and
the `2.1.220` version update. Report verified facts separately from inference
and ask before external sharing or a new paid live matrix run.
```
