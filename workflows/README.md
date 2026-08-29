# Workflow definitions

This directory is the authoring location for workflow graph TOML files.

`feature-delivery.toml` is the canonical first workflow. Its shipped body is
byte-identical to `workflow_interpreter/fixtures/feature-delivery.toml`; the
fixture's `FEATURE_DELIVERY_CONTENT_HASH` is the authoritative equality check.
Validate graphs with `workflow_interpreter.load_graph` before instantiating an
instance. The graph contract and lifecycle semantics are in
`docs/specs/workflow-interpreter.md`.
