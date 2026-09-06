# ADR 0002 — a task node carries its own instructions, enforced at root creation

- **Status:** Accepted; fully implemented 2026-09-03 (slices 1-3)
- **Date:** 2026-09-03
- **Deciders:** repo owner
- **Reviewed by:** Fable 5.1 (high), Sol (xhigh)
- **Related:** ADR 0003 (shared method libraries)

## Context

A `Node` carries topology, bounds, paths, verify entries and outcomes, and
nothing textual (`workflow_interpreter/schema/models.py:221-244`). Every node
in an instance receives the **identical** composed brief: the §6 channel
protocol plus the joined input texts (`foreman/inputs.py:200`). `write_tests`
and `implement` in `workflows/build-loop.toml` differ only in outcome list and
`allowed_paths` — and per ADR 0001, `allowed_paths` is not communicated as a
bound.

So the graph enforces the *order* of a methodology and never states the
methodology. A user describing "TDD: write tests, review them, then implement"
gets order enforcement and no instruction to any node about its job.

Three shapes were considered (`scratchpad/probes/node-design-fable.md`,
`scratchpad/probes/node-design-sol.md`):

- **A1** — required inline `instructions` on every task node.
- **A5** — no prose; derive a deterministic fact frame from declared fields.
- **A7** — a symbolic reference to a versioned method resource, resolved and
  digest-pinned by a repository linker.

## Decision

**Inline `instructions` on task nodes, rendered inside a deterministic fact
frame, enforced at `WorkflowStore.create_root`.**

1. **Schema.** `instructions` is an optional string property on `node` in
   `graph_schema.json` and `Node`. Optional in the schema means
   `exclude_none=True` (`schema/loader.py:153`) leaves the canonical body of
   any graph that omits it byte-identical.

2. **Enforcement at `create_root`, not at a linker.** The originally proposed
   "required at link" is **unsound as stated** — both reviewers raised it as a
   BLOCKER and it was independently confirmed. There is no link step: the CLI
   exposes tick, status, supervise, inspect and steer only
   (`foreman/__main__.py:50-70`), `instantiate()` is a private helper
   (`foreman/resolve.py:110-155`), and `WorkflowStore.create_root` is a public
   typed operation called directly by `tests/_bdio.py:222`,
   `tests/_foreman.py:361` and `tests/_supervisor.py:405`. Enforcing anywhere
   but `create_root` leaves every §13 drill running on roots without
   instructions — precisely the defect class recorded at
   `.claude/project/learnings.md:163-180`.

   `create_root` refuses a definition in which any `kind = "task"` node lacks
   non-empty, non-whitespace `instructions`.

3. **Accept the fixture cost, which is smaller than feared.** Only graphs that
   are actually *rooted* need the field: `feature-delivery.toml` (**both
   copies** — `workflow_interpreter/fixtures/` and `workflows/`, which are
   byte-identical duplicates per spec §2 `:100-102`, now enforced by
   `test_the_authoring_copy_is_byte_identical_to_the_library_fixture`), the
   `tests/_bdio.py` graph builder, and `workflows/build-loop.toml`. Also
   `tests/_helpers.py`'s `MINIMAL_GRAPH` and — found during implementation,
   correcting this ADR's first draft — `fixtures/invalid/`
   `test_flags_require_opt_in.toml`, which despite living under `invalid/`
   is rooted by `test_test_flag_opt_in_reaches_both_root_read_paths` with
   `allow_test_flags=True`. The remaining 37 fixtures are validator inputs,
   are never rooted, and stay byte-identical.
   `FEATURE_DELIVERY_CONTENT_HASH` (`tests/_helpers.py:38-42`) re-pins once.
   **This is acceptable because no live root is pinned on that hash** — the
   only existing instances are in a scratch rig. This is the cheapest moment in
   the project's life to make this change.

4. **A WARNING-severity validator rule**, `task_nodes_instructed`, reports a
   task node without instructions, so the omission surfaces while authoring
   rather than only at root creation. It is a warning, not an error, because
   an error would reject every previously pinned body on read
   (`bdio/records.py:174-220` revalidates on every root load).

   The valid-fixture zero-warning assertion
   (`tests/test_cycles_and_regions.py:25-31`) was reconciled by **instructing
   the fixtures, not weakening the assertion** — a fixture under `valid/`
   claims to be a legal graph, and a graph no instance could be created from
   is not one. Eleven task nodes across `fixtures/valid/` and
   `fixtures/warning/` gained instructions. The rule has its own fixture,
   `fixtures/warning/task_nodes_instructed.toml`, required by
   `test_every_semantic_rule_has_a_fixture`.

   Warnings never enter `GraphValidationError.findings`
   (`schema/loader.py:66-71`), so the 26 invalid fixtures' exactly-one-rule
   assertion is unaffected.

5. **Excluded from resolution.** `instructions` is blacklisted from the
   `resolve()` override reflection (`foreman/resolve.py:54-63`). It is not a
   project-config knob and must not become one.

6. **Composed as a separate section, not inside `RUNNER_PROTOCOL`.** Order:
   protocol → authoritative fact frame → instructions → labeled inputs,
   separated by blank lines. The frame states that **declared facts win over
   instructions**, and carries what a runner cannot derive from its inputs:
   node, graph id and version, round, write permission, expected paths, and
   the verify commands that will run. `Materialized` gained `name` and
   `producer`, populated at all three `materialize()` return sites, so each
   input renders under a `## Input <name> (from <producer>)` heading instead
   of concatenating into one unattributed wall of text.

   Per ADR 0001, the frame describes `allowed_paths` as *"paths whose changes
   are expected here"* — never as a containment bound, which it is not.

   **The frame is proved on the production path, not only in the composer.**
   Bypassing `composer.compose` in `_task_builder` was originally killed by
   exactly one test, and that test asserts the §13 forced-reject clause — so
   instructions and the frame would have become silently droppable the moment
   §13 changed. `test_a_dispatched_task_carries_its_nodes_instructions_and_facts`
   now asserts on a `TaskSpec` built by a real dispatch, and independently
   kills that mutant.

7. **Size caps.** Per-node instructions are capped at **8192 bytes**, declared
   in both the JSON Schema (`maxLength`) and the Pydantic constraint, and
   covered by `test_node_instructions_are_size_capped`. The value is chosen so
   a ten-node graph stays under the **current** ~130 KB inline argv ceiling
   measured in ADR 0003 — i.e. it holds even before the `@file` switch.
   Whitespace-only text does not satisfy presence (`create_root` strips before
   checking). Total graph-body and total composed-prompt caps are **not yet
   implemented** and remain open.

## Consequences

- Every runnable instance is fully specified. Nothing runnable is weaker than
  a required-everywhere field would have given.
- Carrier unit tests may still bypass linking; **foreman tests that run a root
  must not**.
- Existing roots created before this change remain runnable, because pinned
  bodies are revalidated only against graph semantics
  (`bdio/records.py:174-220`). Sol recommends a `link_contract_version`
  attestation so tick/supervise can refuse unattested legacy roots. **Deferred**
  — there are no legacy roots worth protecting, and the attestation is cheap to
  add when there are.

## Resolved — inherited, not created by this ADR

**2026-09-06:** `foreman.resolve.TASK_SETTING_TYPES` now defines the closed task-resolution vocabulary.

## Rejected

- **A7 as the v1 shape** (symbolic method references + resolver + registry).
  Solves a reuse problem with no current instance — two graphs exist and share
  no method. See ADR 0003 for how the shared-method future is preserved.
- **A5 alone** (facts, no prose). Cannot express "write tests first" or a
  review rubric. Necessary, not sufficient; adopted as the frame in point 6.
- **Required-in-schema (Fable's A1).** Would touch all 39 fixtures for no gain
  over `create_root` enforcement.
