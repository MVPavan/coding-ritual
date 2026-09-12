# cli-agent-orchestrator — Luna High exploration (raw report)

> GPT-5.6-Luna, effort high, read-only, 2026-09-11. Verbatim reply to the question set
> below, over the pinned `reference_tools/cli-agent-orchestrator/` submodule. Not independently verified:
> every `file:line` is Luna's claim — check before acting on one. Absolute paths were
> rewritten repo-relative; nothing else was edited.
>
> Resume this exploration with its context intact:
> `codex-run.mjs --resume 01a08fe2-80e8-7742-afbd-7de954c7dc18 -m gpt-5.6-luna -e high -s read-only "<question>"`
> (`--resume` ignores `-C`; the session keeps its original cwd, which is the right repo.)

## Question set as sent

```text
Explore this repository thoroughly and answer the questions below. READ-ONLY: make no edits,
no commits, no git operations that mutate anything. This repo is a read-only reference.

WHY I AM ASKING. I am building a "phase bridge" in a different repository: a deterministic
interpreter that runs ONE unit of work to completion while an LLM decides which unit comes
next. Its properties: durable admission written before any claim so a crash cannot orphan
work; exactly one compare-and-swap to land a signed artifact; human approval gates that must
be crossed before anything lands; per-unit retry with a full attempt history; and a CLI that
returns a machine-readable state (phase-exhausted / blocked / result / refused) which is a
FACT for the LLM to act on, never an instruction. I want to know what this project already
solved, what it solved better, and what it learned the hard way.

Answer these. Cite file:line for every substantive claim — I will check them.

1. ARCHITECTURE. What is the actual orchestrator/worker boundary? Who decides what runs
   next, and is that decision in code or in a prompt? Show me the seam.

2. DURABLE STATE AND RESUMPTION. Where does run state live, and what exactly survives a
   crash mid-run? Walk one concrete interruption: a process killed after a worker started
   but before its result was recorded — what happens on the next invocation? Is there a
   write-then-read-back discipline anywhere, or is state assumed written?

3. CONCURRENCY AND DUPLICATE WORK. What stops two orchestrator processes, or two workers,
   from doing the same unit twice? Locks, leases, CAS, idempotency keys, or nothing? Name
   the mechanism and where it is enforced.

4. HUMAN APPROVAL. Is there a human gate? If so: what is the approval bound to (a commit, a
   diff, a run id, a free-text confirmation), can it be replayed or forged, and is it
   verified again at the moment of use or only when given?

5. LANDING WORK. How does completed work actually reach a branch — direct commit, merge, PR,
   patch application? What happens if the target moved while the work was in flight?

6. RETRY AND FAILURE. What is the retry model? Is there a numeric cap, a policy, or an
   escalation to a human? How does it distinguish "try again" from "this needs a person"?
   Is a retry's prior attempt preserved or overwritten?

7. TRUSTING WORKERS. Does the orchestrator verify a worker's claims independently, or accept
   its self-report? Show the code that does the verification, if any.

8. THE CLI SURFACE. What commands exist, what do they return, and are exit codes meaningful
   and distinguishable (invalid request vs crash vs success)?

9. WHAT THEY LEARNED. Read CHANGELOG.md, docs/, DEVELOPMENT.md and CODEBASE.md for
   abandoned approaches, reversals, and warnings. What did they try that did not work? A
   removed abstraction or a reverted design is more valuable to me than a feature list.

10. THE ONE THING. If I could borrow exactly one durable pattern from this codebase — not a
    feature, a pattern — what should it be and why? And name the single biggest thing this
    project does that my design above is missing.

FORMAT: answer each numbered question in order, with citations. Be concrete and specific;
prefer showing a mechanism to describing it. Where the answer is "this does not exist", say
so plainly rather than constructing something plausible — an honest absence is useful data.
End with a short list of anything you found that I did not think to ask about.
```

## Luna's reply


No edits, commits, or mutating Git operations were performed.

1. Architecture

CAO has two different orchestration boundaries.

For ordinary agent orchestration, the supervisor LLM decides what to assign next. The `code_supervisor` profile explicitly makes the supervisor responsible for task assignment, retries, review loops, and coordinating developer/reviewer agents.[code_supervisor.md:12](reference_tools/cli-agent-orchestrator/src/cli_agent_orchestrator/agent_store/code_supervisor.md:12) [code_supervisor.md:21](reference_tools/cli-agent-orchestrator/src/cli_agent_orchestrator/agent_store/code_supervisor.md:21) The code supplies tools such as `handoff` and `assign`; those tools create a terminal, send the prompt, wait, capture output, and clean up.[server.py:307](reference_tools/cli-agent-orchestrator/src/cli_agent_orchestrator/mcp_server/server.py:307)

The seam is:

```text
supervisor LLM prompt
  -> MCP assign/handoff
  -> FastAPI / orchestration utility
  -> provider CLI in a terminal
  -> worker response
```

The workflow engine is different. YAML sequencing is deterministic declaration/topological order, with declaration order breaking ties.[workflow_service.py:595](reference_tools/cli-agent-orchestrator/src/cli_agent_orchestrator/services/workflow_service.py:595) The engine calls `run_agent_step` directly in-process and does not round-trip through HTTP.[workflow_service.py:7](reference_tools/cli-agent-orchestrator/src/cli_agent_orchestrator/services/workflow_service.py:7) Script workflows let the Python script decide branching and fan-out; each `cao_workflow.step()`/`run_step()` call crosses HTTP at `/terminals/run-step`.[__init__.py:1](reference_tools/cli-agent-orchestrator/src/cao_workflow/__init__.py:1) [__init__.py:120](reference_tools/cli-agent-orchestrator/src/cao_workflow/__init__.py:120) [main.py:3747](reference_tools/cli-agent-orchestrator/src/cli_agent_orchestrator/api/main.py:3747)

2. Durable state and resumption

Workflow state lives in SQLite. `workflow_run` is the durable run projection and `workflow_run_step` is the per-step projection; the in-memory `run_registry` is explicitly only a cache.[workflow_journal.py:1](reference_tools/cli-agent-orchestrator/src/cli_agent_orchestrator/services/workflow_journal.py:1) [database.py:983](reference_tools/cli-agent-orchestrator/src/cli_agent_orchestrator/clients/database.py:983)

The strongest admission path is asynchronous submission. It validates and lints first, then atomically inserts the run and seeded steps before returning `202`; an insert failure returns an error and no `202`.[main.py:4828](reference_tools/cli-agent-orchestrator/src/cli_agent_agent_orchestrator/api/main.py:4828) [main.py:5041](reference_tools/cli-agent-orchestrator/src/cli_agent_orchestrator/api/main.py:5041) [workflow_journal.py:432](reference_tools/cli-agent-orchestrator/src/cli_agent_orchestrator/services/workflow_journal.py:432)

However, the older blocking/YAML engine path is explicitly best-effort: it mutates memory first, then attempts journal writes; failures are logged and swallowed.[workflow_service.py:232](reference_tools/cli-agent-orchestrator/src/cli_agent_orchestrator/services/workflow_service.py:232) The separate `insert_run()` and `insert_steps()` calls are also not atomic.[workflow_service.py:278](reference_tools/cli-agent-orchestrator/src/cli_agent_orchestrator/services/workflow_service.py:278)

Concrete interruption: script worker starts, but completion is not recorded.

- When the terminal becomes ready, CAO records the terminal and attempts to write a durable `RUNNING` step row before execution continues.[script_runner.py:397](reference_tools/cli-agent-orchestrator/src/cli_agent_orchestrator/services/script_runner.py:397)
- When the worker completes, state, attempts, result envelope, output, and error are written atomically by `settle_step()`.[workflow_journal.py:1159](reference_tools/cli-agent-orchestrator/src/cli_agent_orchestrator/services/workflow_journal.py:1159)
- If the process dies after the `RUNNING` write but before settlement, the next `resume` sees a `RUNNING` crash remnant and permits resumption.[workflow_service.py:1492](reference_tools/cli-agent-orchestrator/src/cli_agent_orchestrator/services/workflow_service.py:1492)
- The replay gate then executes again only if the declared policy is `idempotent` or `reconcile`; otherwise it returns `DECISION_REQUIRED` and waits for a human decision.[step_replay.py:269](reference_tools/cli-agent-orchestrator/src/cli_agent_orchestrator/services/step_replay.py:269)
- If the `RUNNING` write itself failed, the row may be absent. The replay gate treats an absent row as “never dispatched” and executes it.[step_replay.py:245](reference_tools/cli_agent_orchestrator/src/cli_agent_orchestrator/services/step_replay.py:245) [script_runner.py:423](reference_tools/cli-agent-orchestrator/src/cli_agent_orchestrator/services/script_runner.py:423) That is a real residual duplicate-side-effect risk.

For YAML resume, completed steps are kept, while every other step is reset to `PENDING` and rerun.[workflow_service.py:1511](reference_tools/cli-agent-orchestrator/src/cli_agent_orchestrator/services/workflow_service.py:1511)

There is some write-then-read-back discipline: plan approval is considered successful only after a read-back confirms the row exists.[main.py:4627](reference_tools/cli_agent_orchestrator/src/cli_agent_orchestrator/api/main.py:4627) Schema migration also verifies required columns rather than trusting migrators that merely returned.[workflow_journal.py:264](reference_tools/cli-agent-orchestrator/src/cli_agent_orchestrator/services/workflow_journal.py:264) Ordinary run/step write-through generally assumes the write succeeded; `settle_step` has an atomic write but no post-write read-back.[workflow_journal.py:1189](reference_tools/cli-agent-orchestrator/src/cli_agent_orchestrator/services/workflow_journal.py:1189)

3. Concurrency and duplicate work

There is no cross-process workflow lease or claim lock.

The active-drive guard is an in-process Python set.[workflow_service.py:218](reference_tools/cli-agent-orchestrator/src/cli_agent_orchestrator/services/workflow_service.py:218) The run-id availability check is a pre-check followed by a later insert, so it has a TOCTOU window. The database primary key catches duplicate submissions, and the loser is mapped to `409`.[workflow_service.py:1056](reference_tools/cli-agent-orchestrator/src/cli_agent_orchestrator/services/workflow_service.py:1056) [main.py:5000](reference_tools/cli-agent-orchestrator/src/cli_agent_orchestrator/api/main.py:5000)

That prevents two submissions from creating two durable rows with the same ID, but it does not prevent two API processes from independently driving the same existing run after concurrent resumes. The step settlement itself is atomic, but its diagnostic existence check is not in the same transaction and can under-report a race.[workflow_journal.py:1189](reference_tools/cli-agent-orchestrator/src/cli_agent_orchestrator/services/workflow_journal.py:1189)

Script workflows have a useful generation fence: resume/cancel increments the persisted generation, and stale subprocess calls receive `409` before dispatch.[workflow_service.py:1387](reference_tools/cli_agent_orchestrator/src/cli_agent_orchestrator/services/workflow_service.py:1387) This fences stale workers; it is not a durable work claim or lease.

For ordinary `cao agent handoff`, rerunning after a killed client creates a new worker. The code explicitly calls this manual recovery rather than automatic retry safety.[agent.py:181](reference_tools/cli-agent-orchestrator/src/cli_agent_orchestrator/cli/commands/agent.py:181)

4. Human approval

There is an optional plan-approval gate for script-tier workflows. It is disabled by default and does not apply to YAML.[approval_gate.py:128](reference_tools/cli-agent-orchestrator/src/cli_agent_orchestrator/services/approval_gate.py:128)

Approval is bound to an opaque `plan_id`, derived from execution-affecting manifest fields, not to a commit, diff, run ID, or artifact.[database.py:659](reference_tools/cli-agent-orchestrator/src/cli_agent_orchestrator/clients/database.py:659) [manifest_freeze.py:73](reference_tools/cli-agent-orchestrator/src/cli_agent_orchestrator/services/manifest_freeze.py:73) The approval table is keyed by `plan_id`, not by run, and has only `plan_id`, timestamp, and approver.[database.py:673](reference_tools/cli-agent-orchestrator/src/cli_agent_orchestrator/clients/database.py:673) [database.py:694](reference_tools/cli-agent-orchestrator/src/cli_agent_orchestrator/clients/database.py:694)

It is write-once: repeated approval is ignored, and there is deliberately no update or revoke path.[approval_store.py:13](reference_tools/cli-agent-orchestrator/src/cli_agent_orchestrator/services/approval_store.py:13) [workflow.py:191](reference_tools/cli-agent-orchestrator/src/cli_agent_orchestrator/cli/commands/workflow.py:191) Therefore approval can be replayed for later runs of the same plan.

The approve request does not accept free-text `approved_by`; the server derives a bounded local account name. But the repository explicitly says that value is provenance, not verified identity, and `getpass.getuser()` is environment-influenced.[main.py:4600](reference_tools/cli-agent-orchestrator/src/cli_agent_orchestrator/api/main.py:4600) [approval_provenance.py:8](reference_tools/cli-agent-orchestrator/src/cli_agent_orchestrator/services/approval_provenance.py:8)

Approval is checked again at use: the async route checks it before durable run insertion, and resume checks it before generation bump/spawn.[main.py:4956](reference_tools/cli-agent-orchestrator/src/cli_agent_orchestrator/api/main.py:4956) [approval_gate.py:149](reference_tools/cli-agent-orchestrator/src/cli_agent_orchestrator/services/approval_gate.py:149)

It is not cryptographically signed. The repository itself describes the SHA-256 plan ID as an identity value, not an authentication boundary; anyone able to modify the manifest column can write a matching ID.[plan_identifier.py:32](reference_tools/cli-agent-orchestrator/src/cli_agent_orchestrator/services/plan_identifier.py:32)

5. Landing work

CAO does not implement artifact landing.

Its worktree support is isolation only. A worker worktree is created from the repository’s current `HEAD` on a `cao/<terminal_id>` branch.[worktree_service.py:100](reference_tools/cli-agent-orchestrator/src/cli_agent_orchestrator/services/worktree_service.py:100) The worker is told to commit and merge/push its result before teardown; CAO itself does not perform that operation.[server.py:335](reference_tools/cli-agent-orchestrator/src/cli_agent_orchestrator/mcp_server/server.py:335)

At teardown, uncommitted work is discarded. A branch with unmerged commits is intentionally left behind rather than force-deleted.[worktree_service.py:148](reference_tools/cli-agent-orchestrator/src/cli_agent_orchestrator/services/worktree_service.py:148)

If the target branch moves while work is in flight, CAO has no target-tip CAS, merge, rebase, conflict-resolution, PR, or patch-application behavior. The worker or an external Git workflow must handle it. The worktree phase explicitly describes itself as having “no merge-back story yet.”[worktree_service.py:154](reference_tools/cli-agent-orchestrator/src/cli_agent_orchestrator/services/worktree_service.py:154)

6. Retry and failure

YAML has a numeric per-step retry cap. The engine loops from attempt `1` through `n_retries + 1`, retries the same prompt on `StepExecutionError`, and marks the step failed after exhaustion.[workflow_service.py:701](reference_tools/cli_agent_orchestrator/src/cli_agent_orchestrator/services/workflow_service.py:701) [workflow_service.py:735](reference_tools/cli_agent_orchestrator/src/cli_agent_orchestrator/services/workflow_service.py:735) `on_failure` then chooses halt or continue.[workflow_service.py:877](reference_tools/cli_agent_orchestrator/src/cli_agent_orchestrator/services/workflow_service.py:877)

The YAML projection stores a current attempts count and last output/error. The append-only workflow event log preserves attempt-started, attempt-failed, and completion transitions.[workflow_service.py:742](reference_tools/cli-agent-orchestrator/src/cli_agent_orchestrator/services/workflow_service.py:742) [workflow_journal.py:1409](reference_tools/cli_agent_orchestrator/src/cli_agent_orchestrator/services/workflow_journal.py:1409) It is not a separate attempt-history table.

Script-tier steps use an atomic settle operation and SQL-owned cumulative attempts; the durable count does not move backward across resumes.[workflow_journal.py:1218](reference_tools/cli-agent-orchestrator/src/cli_agent_orchestrator/services/workflow_journal.py:1218) YAML resume, by contrast, resets noncompleted in-memory attempts to zero before rerunning.[workflow_service.py:1571](reference_tools/cli-agent-orchestrator/src/cli_agent_orchestrator/services/workflow_service.py:1571)

The distinction between retry and human escalation is:

- A worker crash or timeout is a retryable `StepExecutionError` in YAML, with `kind="error"` or `kind="timeout"`.[workflow_service.py:809](reference_tools/cli-agent-orchestrator/src/cli_agent_orchestrator/services/workflow_service.py:809) [main.py:3761](reference_tools/cli-agent-orchestrator/src/cli_agent_orchestrator/api/main.py:3761)
- An interrupted script step with no safe recovery policy becomes `DECISION_REQUIRED`.[step_replay.py:269](reference_tools/cli-agent-orchestrator/src/cli_agent_orchestrator/services/step_replay.py:269)
- A human may choose `rerun` or `skip`; each decision authorizes exactly one attempt and is revoked if unused.[workflow_journal.py:631](reference_tools/cli_agent_orchestrator/src/cli_agent_orchestrator/services/workflow_journal.py:631) [workflow_journal.py:781](reference_tools/cli_agent_orchestrator/src/cli_agent_orchestrator/services/workflow_journal.py:781)

Script subprocess failure itself is not automatically retried by `script_runner`; nonzero exit becomes a failed run, and resume is the recovery path.[script_runner.py:1031](reference_tools/cli-agent-orchestrator/src/cli_agent_orchestrator/services/script_runner.py:1031)

7. Trusting workers

CAO does not independently verify a worker’s semantic claims.

It verifies mechanical conditions: provider/terminal status, exit code, sentinel presence for scripts, and optional structured-output schema validation. The successful `run_step` response is taken from `run_agent_step` and the worker’s `last_message` is persisted.[main.py:4023](reference_tools/cli-agent-orchestrator/src/cli_agent_orchestrator/api/main.py:4023) [script_runner.py:818](reference_tools/cli-agent-orchestrator/src/cli_agent_orchestrator/services/script_runner.py:818)

The replay machinery independently checks call fingerprints, stored envelopes, and provenance before replaying. That verifies whether the current call matches the previously recorded call; it does not verify that the worker actually produced a correct patch, passed tests, or made the claimed external-world change.[main.py:3953](reference_tools/cli-agent-orchestrator/src/cli_agent_orchestrator/api/main.py:3953)

The repository is explicit that a recovery policy is merely the author’s claim and CAO cannot verify it.[workflow-scripts-authoring-guide.md:145](reference_tools/cli-agent-orchestrator/docs/workflow-scripts-authoring-guide.md:145) There is no signed artifact verification or independent diff/test gate in this path.

8. CLI surface

The workflow CLI has thirteen verbs: `validate`, `list`, `get`, `delete`, `run`, `status`, `runs`, `wait`, `result`, `events`, `resume`, `cancel`, and `approve`.[workflows.md:314](reference_tools/cli-agent-orchestrator/docs/workflows.md:314) The separate fallback agent CLI provides `assign`, `handoff`, `send-message`, `status`, `result`, and `cancel`.[agent.py:1](reference_tools/cli-agent-orchestrator/src/cli_agent_orchestrator/cli/commands/agent.py:1)

Machine output is JSON, but the shape depends on the command. Normal `workflow run --json` returns only `{run_id,state}`; `result --json` returns the full journal-assembled result; `status --json` returns a snapshot.[workflows.md:155](reference_tools/cli-agent-orchestrator/docs/workflows.md:155) [workflows.md:175](reference_tools/cli-agent-orchestrator/docs/workflows.md:175)

Exit codes are weakly differentiated:

- `completed` is `0`; any other terminal state is `1`.[workflow.py:377](reference_tools/cli-agent-orchestrator/src/cli_agent_orchestrator/cli/commands/workflow.py:377)
- Invalid requests and most HTTP/server errors become Click exceptions, also effectively exit `1`.[workflow.py:539](reference_tools/cli-agent-orchestrator/src/cli_agent_orchestrator/cli/commands/workflow.py:539)
- `--detach` exits `0` after submission, not completion.[workflow.py:467](reference_tools/cli-agent-orchestrator/src/cli_agent_orchestrator/cli/commands/workflow.py:467)
- Lost contact during polling exits `0`, even though completion is unknown.[workflow.py:414](reference_tools/cli-agent-orchestrator/src/cli_agent_orchestrator/cli/commands/workflow.py:414)

The exact states `phase-exhausted`, `blocked`, `result`, and `refused` do not exist as a closed CLI state vocabulary. Whole-run states are only `running`, `completed`, `failed`, and `cancelled`.[workflow_runtime.py:61](reference_tools/cli-agent-orchestrator/src/cli_agent_orchestrator/models/workflow_runtime.py:61) “Blocked” is represented indirectly by a `409 decision_required`; approval refusal is an HTTP `403`.[main.py:4006](reference_tools/cli-agent-orchestrator/src/cli_agent_orchestrator/api/main.py:4006) [main.py:4970](reference_tools/cli_agent_orchestrator/src/cli_agent_orchestrator/api/main.py:4970)

9. What they learned

The clearest reversals and warnings are:

- The old declarative YAML authoring path was retired as the primary path; scripts became recommended because YAML’s parallel, pipeline, and loop modes are reserved and not executable.[workflows.md:7](reference_tools/cli-agent-orchestrator/docs/workflows.md:7)
- Separate run-row and step-row commits caused the possibility of a phantom `RUNNING` run. The async path added a single atomic run-plus-step transaction specifically to remove that failure window.[workflow_journal.py:432](reference_tools/cli-agent-orchestrator/src/cli_agent_orchestrator/services/workflow_journal.py:432)
- A previous two-write step settlement could leave a settled row with no result. The replacement is one atomic `settle_step` write.[manifest_freeze.py:12](reference_tools/cli-agent-orchestrator/src/cli_agent_orchestrator/services/manifest_freeze.py:12) [script_runner.py:772](reference_tools/cli-agent-orchestrator/src/cli_agent_orchestrator/services/script_runner.py:772)
- An unconditional background failure backstop once overwrote genuine `COMPLETED`/`CANCELLED` states as `FAILED`; it was changed to a SQL-guarded update that only changes `RUNNING`.[main.py:4533](reference_tools/cli-agent-orchestrator/src/cli_agent_orchestrator/api/main.py:4533)
- Writing the terminal state before the terminal event caused healthy runs to appear to have trailing event loss. The order was reversed: event first, state second.[workflow_service.py:1022](reference_tools/cli-agent-orchestrator/src/cli_agent_orchestrator/services/workflow_service.py:1022)
- Migration code once treated “migrator returned” as success even though migrators swallowed failures. The journal now verifies schema presence before caching the path.[workflow_journal.py:264](reference_tools/cli-agent-orchestrator/src/cli_agent_orchestrator/services/workflow_journal.py:264)
- The repository noticed that four additive `ALTER TABLE` operations inside one silently failing migration block made the risk larger than either contributing change assumed.[database.py:1108](reference_tools/cli-agent-orchestrator/src/cli_agent_orchestrator/clients/database.py:1108)
- `--legacy-ui` silently selected a Kiro engine with no MCP tools, producing a week-long orchestration/self-learning outage while agents appeared healthy.[CHANGELOG.md:131](reference_tools/cli-agent-orchestrator/CHANGELOG.md:131)
- Session teardown previously deleted registry rows before confirming tmux death, creating orphaned sessions and ghost rows. It now confirms disappearance first and leaves rows intact on failure.[CHANGELOG.md:135](reference_tools/cli-agent-orchestrator/CHANGELOG.md:135)
- The standalone agent CLI still documents that retrying after a kill creates a new worker; durable run identity for that surface remains tracked but unimplemented.[agent.py:188](reference_tools/cli-agent-orchestrator/src/cli_agent_orchestrator/cli/commands/agent.py:188)
- The result route once advertised run-level output that could never be populated from the journal. It now removes that field rather than returning a misleading `null`.[main.py:6163](reference_tools/cli-agent-orchestrator/src/cli_agent_orchestrator/api/main.py:6163)

`DEVELOPMENT.md` is primarily CI, testing, quality, and PR procedure; it does not add a separate orchestration state model or recovery guarantee.[DEVELOPMENT.md:145](reference_tools/cli-agent-orchestrator/DEVELOPMENT.md:145) [DEVELOPMENT.md:228](reference_tools/cli-agent-orchestrator/DEVELOPMENT.md:228)

10. The one thing

Borrow this pattern:

> Durable `RUNNING` admission, followed by one atomic settlement containing state, attempt count, result envelope, output, and error; treat an unsettled `RUNNING` row as unknown and route it through an explicit replay/recovery gate.

That is the repository’s strongest answer to “crashed after dispatch, before result.” It avoids a settled-without-result state, preserves cumulative attempts, and refuses to guess when replay safety is not declared.[workflow_journal.py:1168](reference_tools/cli-agent-orchestrator/src/cli_agent_orchestrator/services/workflow_journal.py:1168) [step_replay.py:269](reference_tools/cli-agent-orchestrator/src/cli_agent_orchestrator/services/step_replay.py:269)

The biggest thing CAO does that your design is missing is the opposite of a feature: CAO has an explicit isolation/worker execution boundary but no authoritative artifact-landing protocol. There is no signed artifact, independent semantic verification, target-tip CAS, or merge/PR operation. Workers are told to commit and merge/push their own results.[server.py:337](reference_tools/cli-agent-orchestrator/src/cli_agent_orchestrator/mcp_server/server.py:337) Your phase bridge has stronger admission, approval, retry, and result semantics, but it needs an equally explicit “verified artifact becomes the target branch” boundary.

Other things worth asking about:

- Generation fencing for stale workers and cancellation.[workflow_service.py:1387](reference_tools/cli-agent-orchestrator/src/cli_agent_orchestrator/services/workflow_service.py:1387)
- Frozen source/input snapshots and deterministic replay obligations.[workflows.md:65](reference_tools/cli-agent-orchestrator/docs/workflows.md:65)
- Event-log gap detection and terminal-event ordering.[workflow_journal.py:1558](reference_tools/cli-agent-orchestrator/src/cli_agent_orchestrator/services/workflow_journal.py:1558)
- Bounded stdout/stderr draining to prevent subprocess deadlock.[script_runner.py:1034](reference_tools/cli-agent-orchestrator/src/cli_agent_orchestrator/services/script_runner.py:1034)
- Retention/deletion of durable runs and recovery artifacts.
- The distinction between local provenance and authenticated human identity.[approval_provenance.py:8](reference_tools/cli-agent-orchestrator/src/cli_agent_orchestrator/services/approval_provenance.py:8)


