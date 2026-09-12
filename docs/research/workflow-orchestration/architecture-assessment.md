# Assessment: deterministic execution and model-led orchestration

Date: 2026-09-11. Status: advisory opinion, revised after user clarification.

Decision: how much of the [workflow vision](../../workflow-vision.md) should
be enforced by code, and how much should remain under model judgment as
models improve?

## Recommendation

Build a small deterministic execution foundation with replaceable model-led
planning and on-demand supervision. Support a few adaptable workflow
families, dynamically assembled graph instances, and explicit runtime/model
assignments. Routine graph progression should require no supervisor call.

The strongest part of the vision is separating routine local execution
from supervisory judgment. The user explicitly wants a flat system; the
human analogy describes contributions and work flow, not a management
hierarchy to reproduce. The earlier assessment attributed more hierarchy
to the proposal than the user intended. That objection is withdrawn.

The same correction applies to fixed junior/senior assignments and forced
retry rounds: neither was proposed. Model selection is flexible, and every
role can return an outcome that ends or escalates its local workflow early.

This is an architectural recommendation, not a demonstrated cost or quality
advantage for this repository.

## Scope and evidence

Method: focused architecture responsibility and failure-mode assessment,
using the clarified vision, prior local code exploration, primary research,
and the existing Omnigent reports plus narrow source checks. No runtime
benchmark or local model-pair evaluation was performed. All external
sources below were retrieved on 2026-09-11. Vendor engineering accounts
describe their own systems; their results are not direct evidence for this
workload.

The evidence supports caution in both directions. METR's current page
reports task horizons at specified success probabilities and warns that its
well-specified tasks are cleaner than much real work. Better task capability
does not establish dependable autonomous project management.
[METR methodology and limitations](https://metr.org/time-horizons/).

Conversely, model improvements can remove the need for particular harness
rules. Anthropic's April 2026 account describes a context-reset workaround
becoming unnecessary with a stronger model. It separates replaceable
harness behavior from durable sessions and execution environments.
[Managed Agents architecture](https://www.anthropic.com/engineering/managed-agents).

## Compare the choices

| Approach | Best fit | Main sacrifice | Cost and integration | Principal risk |
|---|---|---|---|---|
| Model follows a written process | Exploration, changing requirements, supervised reversible work | Weaker assurance that every procedural rule was followed | Low initial implementation cost; variable inference and intervention cost | Skipped steps, drifting state, repeated mediation |
| Fixed workflow with model tasks | Repeated work with stable inputs and clear transition predicates | Flexibility when decomposition or requirements change | More implementation and maintenance; inexpensive routine routing | Reliably executing the wrong process |
| Model assigns bounded workflows | Mixed judgment and repeatable execution across concurrent work | Additional contracts, state, and integration work | Moderate-to-high foundation cost; savings must be measured | Excess hierarchy and unclear replanning authority |

These choices are architectural shapes, not rankings of particular tools.
Do not choose the hybrid when a single capable agent with the required
checks and approvals already meets the task's quality and operating needs.

## Put the boundary around responsibility

Rules written in a prompt and rules enforced by code are different kinds of
control. A deterministic engine can execute a graph generated dynamically
by a model. Determinism does not require the entire project to be fixed in
advance.

Recommended division:

| Responsibility | Owner |
|---|---|
| Interpret requirements, assess feasibility, decompose work | Model or human judgment |
| Select workers and propose workflows | Model, within configured authority and budgets |
| Check an assignment is valid and authorized | Runtime |
| Dispatch, track attempts, preserve state, apply declared transitions | Runtime |
| Run specified checks and bind results to the reviewed artifact | Runtime |
| Judge adequacy, diagnose disagreement, reconsider the plan | Model or human judgment |
| Enforce approval, permission, and resource limits | Runtime |
| Decide authorized exceptions and substantive scope changes | Responsible supervisor or human |

These are proposed responsibilities, not a claim that all are currently
implemented. A green verifier establishes its tested predicates, not full
product correctness. Model review also remains fallible.

## Implications of the clarified vision

### Adapt workflow complexity to the task

The requested shapes range from basic work with little separate review to
spec-driven development and more demanding assurance loops. Those can share
one execution mechanism. The graph determines the roles needed for this
task; the runtime need not contain a fixed taxonomy of management agents.
Graph nesting does not require adding a supervisor model at each level.

### Treat context isolation and total cost separately

Detailed local exchanges can stay outside the supervisor's context. This
does not require every step to be deterministic: artifacts, bounded reports,
and retrieval can also limit what a model-led supervisor receives.
Anthropic describes this separation through focused subagents returning
condensed results. [Context engineering](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents).

Additional agents can nevertheless increase total usage. Anthropic reports
substantial multi-agent token overhead in its research system and combines
model adaptation with deterministic checkpoints and retry handling.
[Multi-agent research system](https://www.anthropic.com/engineering/multi-agent-research-system).

My inference: the graph's particular value is avoiding model calls for
already-decided transitions and preserving execution state. Context
isolation is a separate contract that both simple and complex systems need.

### Support cross-family review, with evidence-aware assignments

Self-preference is an observed evaluation bias, not merely a hypothetical
concern: evaluators can favor their own outputs even when human assessments
do not justify that preference. [Panickssery et al., 2024](https://arxiv.org/abs/2404.13076).

Model heterogeneity also improved the evaluated multi-agent debate methods
in a study spanning five methods and nine benchmarks. That supports diverse
model participation, though debate benchmarks do not directly establish
repository code-review outcomes. [Zhang et al., 2025](https://arxiv.org/abs/2502.08788).

A direct code-review experiment found benefits depended on assignment
direction: Opus 4.7 improved GPT-5.5 drafts, while GPT-5.5 worsened Opus 4.7
drafts. The 116 LiveCodeBench problems used a single review pass that could
rewrite the solution but could not run tests. This is evidence against an
unconditional benefit from any cross-vendor pair, not a stable model ranking
or a test of the proposed repository workflow.
[Xiang et al., 2026](https://arxiv.org/html/2607.21656v1).

The conclusion is to make cross-runtime and cross-model compatibility a
first-class capability, as the user requests. Supporting that capability
does not require proving every possible pairing beneficial. Track runtime,
underlying model family, and assigned role separately so a workflow can
express its intended diversity policy accurately.

Prefer reviewers that inspect the requirements and artifact directly and
can produce reproducible counterexamples. Evaluate cross-model review on
defects caught, false objections, and rework caused. Preserve any required
human approval policy regardless of model performance.

Model choice remains configurable. The user has not prescribed cheaper
implementation or expensive review; a strong model can occupy either role.

### Escalate on meaningful conditions, not just iteration counts

A retry cap is a useful enforced limit. As the user clarified, approval
advances immediately, an impossible requirement can escalate immediately,
and authorized abandonment terminates the attempt. Only a rework verdict
uses another permitted round. This is outcome-driven deterministic routing:
the model judges the situation and the runtime applies the declared edge.

Extensions need an overall spending or time boundary; repeated grants of
three more iterations can otherwise make a locally bounded system globally
unbounded. The supervisor should state what new information or changed
approach makes another attempt worthwhile.

### Permit deliberate replanning

The assigned process is stable while its assumptions hold. Discovering a
new dependency or invalid decomposition should produce an explicit revision
through the responsible authority. It should not require inventing every
possible future exception in the original graph.

I would define acceptance criteria early and use executable feedback
throughout development. The user's illustrative post-implementation testing
stage remains a supported arrangement, not a mandated order.

## Strongest counterargument

A capable model with good tools, scoped workers, durable notes, and independent
checks may deliver most of the benefit with much less custom machinery.
Improved native agent runtimes could make parts of a custom orchestration
system redundant. Anthropic's older workflow guidance also recommends adding
complexity only when it improves outcomes; the page now points readers to
its newer managed-agent architecture for current tooling.
[Building effective agents](https://www.anthropic.com/engineering/building-effective-agents).

This counterargument wins if the proposed foundation mostly encodes
temporary model weaknesses, or if it cannot beat a simpler baseline on real
work. The defense of the foundation should be dependable execution and
clear authority, not a forecast that today's models always need today's
coordination rules.

## Smallest mechanism worth evaluating

This is a proposed shape, not an approved implementation plan:

1. **One logical LLM planning/supervision role.** It creates the roadmap,
   selects or composes workflow instances, assigns models, and resolves
   exceptions. It can run fresh sessions over durable project state; it
   does not need to remain in an ongoing conversation with every worker.
2. **A small persistent graph runner.** It records each assigned instance,
   dispatches ready work, validates result envelopes, applies declared
   outcome edges, enforces allowances, and wakes the LLM when a graph needs
   judgment. Completion also makes dependent work ready without requiring
   a supervisor to relay the result. Several graphs can progress at once.
3. **A replaceable CLI execution adapter.** It starts an assigned runtime
   and model, observes actual task completion, retrieves artifacts/results,
   and cancels work when required. Native session details remain behind
   this boundary rather than entering every workflow definition.

These are responsibilities, not three required services. For a local
deployment they could share one process, with persisted workflow state in
the existing ledger and artifacts in Git/files. There should be one
authority for workflow progression rather than a second ledger that must
be synchronized with Beads.

Templates and dynamically assembled graphs should use the same small
representation: work, role assignment, inputs, possible outcomes, edges,
limits, and child-graph dependencies. Exact fields are undecided. A graph
node can wait for a child graph's terminal result; the child does not need
a resident LLM supervisor just because it is nested.

The hard parts remain real: launching work around a crash, avoiding duplicate
side effects, recognizing actual vendor completion, isolating parallel
writes, and binding review evidence to the right artifact. A short script
that ignores those conditions is not equivalent to the requested system.
Existing mechanisms should be reused where they satisfy these contracts;
neither a rewrite nor preservation of the whole current interpreter is
justified without mapping that boundary.

## What Omnigent contributes

The local checkout still matches the reports' `33ec5137` snapshot and is
clean. The existing assessment distinguishes useful multi-runtime execution
from durable workflow control; it does not establish a replacement for the
graph runner. [Prior factory assessment](../codebases/omnigent/factory-assessment.md).

Narrow source checks support two material cautions: the Claude-native
executor's `TurnComplete` denotes input delivery, and active turn/steering
state remains process-local. These are execution semantics an adapter must
handle, not details a workflow can treat as successful task completion.
[Native executor](../../../reference_tools/omnigent/omnigent/inner/claude_native_executor.py),
[state documentation](../../../reference_tools/omnigent/omnigent/server/DBSPEC.md).

My recommendation is to keep Omnigent optional behind the execution boundary.
It may save vendor-integration work, but adopting its full server/runner
stack is not automatically the simplest route for a local workflow runner.
The existing reports suffice for this architectural distinction; a current
integration feasibility test would be needed before selecting it.

## Evaluation before expanding

Compare representative bounded changes using:

1. A capable single agent plus the required independent review and checks.
2. A model-led coordinator with scoped workers and compact handoffs.
3. The hybrid with deterministic local workflows.

Hold requirements, acceptance checks, authority, and comparable resource
ceilings constant. Record total usage across all agents, elapsed time,
human intervention, defects found after declared completion, false review
objections, and recovery behavior. Include failures and abandoned runs in
the cost per accepted result. Test interruptions and nonconverging reviews
as well as successful runs.

Retain additional structure when it prevents an observed failure or improves
accepted outcomes enough to justify its cost. Re-evaluate after material
model or runtime changes.

## Confidence and open questions

- **High:** written instructions and executable controls provide different
  guarantees; supervisor context size is not total system cost.
- **Medium:** a thin hybrid is the best fit for this vision. This is supported
  by architecture evidence but not by a local comparative benchmark.
- **Low/unverified:** the best graph decomposition, model pairs, review count,
  task sizes, and expected savings for this repository.
- **Speculative:** how quickly future capability gains will remove particular
  coordination layers. Design for replacing them without assuming a date.

The next decision is the smallest real workflow that can demonstrate this
division of responsibility and expose the execution contracts it needs.
