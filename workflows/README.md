# Workflow definitions

This directory is the authoring location for workflow graph TOML files.

`feature-delivery.toml` is the canonical first workflow. Its shipped body is
byte-identical to `workflow_interpreter/fixtures/feature-delivery.toml`; the
fixture's `FEATURE_DELIVERY_CONTENT_HASH` is the authoritative equality check.
Validate graphs with `workflow_interpreter.load_graph` before instantiating an
instance. Each `allowed_paths` entry must be a `<dir>/**` grant with no
hidden (`.`-leading) segment, because those directories become the node's
writable mounts under the default `sandbox = bwrap` bound. The graph contract
and lifecycle semantics are in `docs/specs/workflow-interpreter.md`.

## Ordinary P5 templates

`basic.toml` is the smallest finite writer: supply one `task_brief` instance
input and a binding for `profile:implementer`. Its only writer may change
`src/**`; a successful committed artifact ends the root without bridge landing
or a gate.

`design-spec.toml` is the bridge-compatible Markdown path. Set it as the
normal `bridge_graph`, provide the selected stage description as its sole
instance input `task_brief`, and bind `profile:implementer` plus
`profile:critic`. Its writer is confined to `docs/**`; the runtime supplies
its `candidate_diff` to the non-writing reviewer. Only the existing immutable
human `ship` gate can reach `shipped`, so normal P1 signing configuration is
required for closure. The final live proof records the resolved graph/config
pins, writer/reviewer activation and backend session identities, then the
signed fixture-only ship and landing evidence.

## Bounded ordinary decisions

`workflow_interpreter/fixtures/valid/bounded-decision.toml` is the minimal runnable
example: emitted `fail_plan` → ordinary decision task → useful work → explicit human
gate. Supply normal runtime role bindings and its pinned `scripts/verify-feature.sh`.
Use the existing Foreman `create`, `run <root_id>`, `status <root_id>` and `inspect`
commands. `run` drives decisions automatically; acceptance/rework without a declared
signal invokes no decider. Status reports coordination reservations separately from
actual usage, and activation `input_envelopes` records byte counts/omissions.

A policy permits only `continue_declared`, `replace`, or `human`; the response in
`WF_ARTIFACT_DIR/decision.json` must match the identity supplied in the ordinary task
brief. Supervisor output evidence and current-generation checks authorize consumption,
not a model's assertion. Malformed, stale, duplicate or unauthorized output needs human
attention. An explicit human gate still requires the existing authenticated closure.

Replacement reruns the same graph/config at the bound artifact with advisory text in
its declared optional instance source. Admission requires actual bound consumers; when
present in a replacement, that advice is essential and cannot be trimmed. The original
root remains the command handle, while status names its current successor. Total
member capacities are reserved monotonically under the original owner; restart and
replacement cannot replenish them. Exhausted reservations require human attention.
Bridge-managed replacement is refused in P2; P3 owns successor-root binding and stale
predecessor landing/closure refusal, with normal phase proof in P5.

Use positive `context_budget_bytes` for new task declarations. It measures the complete
UTF-8 brief, not vendor tokens. Legacy `token_budget` is readable but ignored with a
reported diagnostic; without bytes the explicit legacy safety ceiling is 262144 bytes.
Decision-enabled tasks require explicit bytes. New fields are null-elided for unchanged
canonical graph pins. Run the real decision proof explicitly with
`uv run pytest -q --run-live -m live tests/test_decision_live.py`.
