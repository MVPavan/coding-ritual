Target(s): reference_tools/omnigent
Snapshot: 33ec5137 (clean)   Date: 2026-08-24
Mode: assessment (adjunct — not a codebase-research L1/L2/deep-dive artifact;
consumes them)   Builds on: capabilities.md + architecture/00-architecture.md @ 33ec5137

# Omnigent as a software factory — three-model assessment

Question asked: can Omnigent become the substrate of a "software factory" —
distinct workflow families (ML experiments, research, implementation), each
a pipeline of roles (orchestrator, implementer, reviewer, verifier) on
different models/harnesses?

Process: independent opinions from **GPT-5.6-sol (xhigh)** via codex and an
**Opus 5** subagent, both briefed on the committed L1/L2 research and free to
re-read omnigent source (read-only); coordinator (Fable) formed a position
first, then adjudicated. Source-level claims below were made by an advisor
against snapshot `33ec5137` and spot-checked where load-bearing; this is a
design opinion, not a traced artifact — for evidence discipline see the L2
map.

## Joint verdict

All three positions converge: **premature as the factory's engine; credible
as its execution floor.** Omnigent has no pipeline primitive — stage order,
handoffs, and gates would be LLM promises in an orchestrator prompt. Opus's
sharpest supporting fact: `AgentDef.workflow`, a DAG field in the YAML
schema, is parsed (`omnigent/inner/loader.py:339`) and **never consumed
anywhere in the tree**; Polly's "pipeline" is a ~200-line prompt plus three
skill files. Reframe: **roles with enforceable job descriptions, not stages
in a pipeline** — role constraints survive contact with the runtime, stage
boundaries do not.

## Convergent conclusions (all three, independently)

1. **Beads stays the ledger; the coding-ritual harness stays the foreman.**
   Stage state, gate decisions, idempotency keys, artifact identity live in
   beads. Write every gate decision to beads *before* requesting an
   Omnigent approval — approvals are process-local futures; a lost one must
   surface as an open beads item, not a stalled pipeline.
2. **Model matrix lives in version-controlled agent YAML; smart routing off
   everywhere in the factory.** Same stage, same model, twice. Session pins
   are operator escape hatches, not configuration. (Sol: under
   parent-controlled child routing the router deliberately overrides the
   dispatch model — "pins beat routing" is not universal;
   `orchestration.py:4874`.)
3. **ML experiments are structurally the worst fit.** A turn is not a job;
   native turn-complete = input delivered. Training runs belong in an
   external job system with durable run IDs; Omnigent does the
   analyze/report leg only.
4. **The built-in scheduler is not a trigger of record** — no replay,
   backfill, lease, or startup repair; scheduled tasks cannot create
   worktrees (`entities/scheduled_task.py:44`) and carry reserved-unused
   columns. Required recurrence = host cron + a last-successful-run marker
   we own.
5. **Pilot only one leg of the implementation workflow**, with a deliberate
   server-restart drill as an acceptance test.

## Findings that changed the design

1. **Reviewer vendor IS enforceable** (Opus, narrowing L2 docs-vs-source #1):
   pin `harness: codex-native` in the critic's sub-agent spec, omit
   `allowed_harnesses` (`tools/builtins/spawn.py:211-217,258-280`), attach a
   `read_only_os` DENY policy (sentinel example) and a sandbox with empty
   write paths. Unenforced remainder: whether review happens at all, and
   what the critic can read (filesystem leaks unless sandboxed — polly
   ships `sandbox: none` on every agent).
2. **Harness knowledge transfers free to Claude children only.** The
   claude-sdk executor deliberately does not pass `--bare` so CLAUDE.md,
   skills, and plugins leak through (`inner/claude_sdk_executor.py:2368-2378`;
   `skills: all` default resolves user+project sources, `:1341-1382`).
   Codex/Cursor/Pi children get none of it — **the cross-vendor critic is
   the one role that arrives without our process knowledge** and needs a
   duplicated, drift-prone protocol.
3. **Cost budgets hang unattended children** — the hard limit DENYs while on
   an expensive model and instructs "the user" to `/model` down; headless
   children have no user, so the terminal state is a hang
   (`docs/POLICIES.md:246-284` semantics, per Opus).
4. **Factory YAML would be written against source, not docs** (Opus): the
   shipped examples use a `guardrails.policies` dialect absent from
   AGENT_YAML_SPEC.md; source comments cite POLICIES.md sections that do not
   exist; several load-bearing keys (`spawn:`, `executor.type: omnigent`,
   `allowed_harnesses`, `smart_routing_harness`) are example-only. No
   compatibility promise at 0.11.0.dev0.

## Disagreements and adjudication

1. **Integration seam.** Sol: an `ExecutionBroker` interface
   (start/observe/cancel/collect + caller idempotency keys) driven from our
   controller via the SDK. Opus: no SDK-inside-Claude-Code at all — the SDK
   cannot create durable agents or answer native approvals, so it cannot
   reach the capabilities we'd adopt Omnigent for; run Omnigent as the
   outer surface. **Adjudicated: Opus's direction for the pilot; Sol's
   broker is the later shape if automation grows.** Both prohibit two
   foremen.
2. **Projects.** Sol traced project `config` as a client-owned new-chat
   prefill (`web/src/lib/projectsApi.ts:15`) — server stores, never acts;
   Opus's table marked it enforced, uncited. **Adjudicated: Sol** — pass
   all launch settings explicitly; projects are UI convenience.
3. **Critic vendor.** Sol assumes cross-vendor; Opus proposes the
   alternative — a Claude critic on a different model keeps all process
   knowledge — and makes cross-vendor an experiment with a measurable bar.
   **Adjudicated: run both in the pilot and measure** (see acceptance).

## Pilot specification (agreed shape)

One pinned server + one runner + one repo; Linux sandboxes mandatory; no
default-unsandboxed roles. Template agent `critic-fanout` with two declared
sub-agents: `impl` (claude-native, cwd = repo — inherits CLAUDE.md/rules/
skills free) and `critic` (codex-native, read-only DENY, sandboxed, handed a
diff file only). Worktree per task via the child-create `git` option; PR is
the deliverable; human merges. Beads ledger; smart routing off; scheduler
off; no SDK integration. Five bounded real tasks through
plan → implement → review → verify.

Acceptance criteria (union of both advisors):

- intended vs effective model/provider match on every session
  (`routing_decision` items + usage telemetry);
- reviewer provider differs from implementer; reviewer cannot write;
- reviewed commit equals verified commit before merge;
- every retry idempotent — no duplicate PRs/pushes;
- no workflow state that exists only in chat/SSE;
- deliberate mid-pipeline server restart recovers from beads + commits +
  conversation IDs without duplicate side effects;
- Codex-critic finding quality compared against the current spawned Claude
  critic on the same diffs — the cross-vendor question answered with data.

Explicitly not built yet: ML runs as turns; required schedules on the
built-in scheduler; research workflow (no capability gain over the existing
research skill); smart routing; SDK-driven orchestration; multi-replica;
durable-approval workflows; auto-merge; a second Omnigent-native copy of
skills/rules/verification.

## Advisor executive summaries (verbatim)

**GPT-5.6-sol xhigh:** "Omnigent is credible as the factory's heterogeneous
execution floor, not its durable workflow engine. Keep stage state,
idempotency, approvals, and artifact identity in Beads plus a narrow
controller. Pin models per role in agent definitions; routing is optional
optimization, never reviewer governance. Pilot only bounded implementation
work on one server with explicit sandboxes, worktrees, and human merge. Do
not entrust required schedules, long ML jobs, durable approvals,
multi-replica operation, or auto-merge to it yet."

**Opus 5:** "(1) Omnigent has no pipeline construct — `AgentDef.workflow` is
parsed and never consumed, and polly's 'pipeline' is a prompt; stage order
and handoffs would be LLM promises. (2) What is enforceable is per-role:
sub-agent specs pin harness and model, `allowed_harnesses` gates overrides,
and tool_call policies can DENY writes — design roles with job descriptions,
not stages. (3) The harness transfers free to Claude children and not at all
to Codex/Cursor/Pi, so the cross-vendor critic is the one role that costs a
duplicated protocol. (4) The fragile spots cluster where a phone-driven
factory leans hardest: process-local approvals with day-long timeouts on a
single-replica alpha, native turn-complete ≠ work-complete, and a scheduler
with no replay/backfill/retry/lease. (5) Premature as a factory, worth a
bounded pilot as a surface."

## Status

Decision open. Pending user rulings: (1) adopt the roles-not-stages
reframe; (2) cross-vendor vs Claude-different-model critic (pilot measures
both); (3) pilot now on the alpha vs ledger adopt-narrow/defer until a
stabler release. Per curation rules, the eventual ruling goes to
`harness_lifecycle/ledger.json`.
