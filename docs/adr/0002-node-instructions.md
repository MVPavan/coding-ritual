# ADR 0002 — a task node carries its own instructions, enforced at root creation

- **Status:** Accepted
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
   are actually *rooted* need the field: `workflow_interpreter/fixtures/`
   `feature-delivery.toml`, the `tests/_bdio.py` graph builder, and
   `workflows/build-loop.toml`. The other 38 fixtures are validator inputs and
   are never rooted — they stay byte-identical.
   `FEATURE_DELIVERY_CONTENT_HASH` (`tests/_helpers.py:38-42`) re-pins once.
   **This is acceptable because no live root is pinned on that hash** — the
   only existing instances are in a scratch rig. This is the cheapest moment in
   the project's life to make this change.

4. **A WARNING-severity validator rule** reports a task node without
   instructions, so a graph fails early at authoring time rather than only at
   root creation. `Severity` is error/warning only
   (`schema/models.py:108-112`), which suffices. The valid-fixture zero-warning
   assertion (`tests/test_cycles_and_regions.py:25-31`) must be reconciled.

5. **Excluded from resolution.** `instructions` is blacklisted from the
   `resolve()` override reflection (`foreman/resolve.py:54-63`). It is not a
   project-config knob and must not become one.

6. **Composed as a separate section, not inside `RUNNER_PROTOCOL`.** Order:
   protocol → authoritative fact frame → instructions → labeled inputs. The
   frame states that **declared facts win over instructions**. `Materialized`
   currently retains only text (`foreman/inputs.py:27-32`) and must also carry
   source name, producer and digest before labeled composition is possible.
   At least one test must drive `DefaultComposer` with a participant the test
   did not author.

7. **Size caps.** Per-node instruction bytes, total graph body bytes, and total
   composed prompt bytes each need an explicit cap. Without them,
   `instructions = ""` satisfies presence and large inline text bypasses the
   currently inert `token_budget` (`foreman/supervise.py:149-160`). Cap values
   depend on ADR 0003's probe.

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

## Open — inherited, not created by this ADR

**The `resolve()` reflection needs replacing, not just blacklisting.** Both
reviewers flagged the one-field blacklist as an acceptable immediate guard and
an unacceptable final policy. `resolve()` registers every non-required scalar
node field as a configuration key, including nonsensical ones such as
`node.ship.model`, which a test asserts is accepted
(`tests/test_foreman_resolution.py:208-251`). Meanwhile minting rereads the
**live** role map (`foreman/cases.py:154-185, 269-286`) and task construction
reads the **raw pinned node** (`foreman/supervise.py:126-160`), so recorded
overrides are inert. The spec's §14 row *"Closed resolved-config key
vocabulary, trigger: phase 5"* (`:952`) has fired. It is **explicitly
re-deferred** here to keep this ADR's scope bounded, and tracked as its own
item.

## Rejected

- **A7 as the v1 shape** (symbolic method references + resolver + registry).
  Solves a reuse problem with no current instance — two graphs exist and share
  no method. See ADR 0003 for how the shared-method future is preserved.
- **A5 alone** (facts, no prose). Cannot express "write tests first" or a
  review rubric. Necessary, not sufficient; adopted as the frame in point 6.
- **Required-in-schema (Fable's A1).** Would touch all 39 fixtures for no gain
  over `create_root` enforcement.
