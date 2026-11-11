# Examples

Use these as quality calibration only.

## Tech Tooling

Weak:
"Temporal is good for workflows, Celery is good for tasks, and Redis queues are simple."

Strong:
"Temporal's documented strength is workflow correctness that depends on durable timers, signals, retries, and replay across worker crashes. The same sources show its cost: a workflow service to run, deterministic workflow constraints, and a new operational model. Practitioner reports on single-user assistants with human approvals describe Postgres-backed jobs holding up until runs span days or need compensation semantics. The evidence favours Temporal, with medium confidence, only once long-running workflows cannot be reliably resumed or audited with the current job model; whether that point has been reached is the caller's call."

## Developer Tools

Weak:
"Use the SDK because it has tools and handoffs."

Strong:
"The SDK's docs describe it owning the agent loop, and its tools and handoffs fit that loop's failure model. Where the docs list no support for provider portability through LiteLLM, custom approval gates, or first-class artifact logging, and those are requirements, the evidence favours treating the SDK as a component: its utilities can be adopted selectively while the orchestration boundary stays with the caller. Confidence is medium until each gap is checked against the current release notes."

## Quick Tests

- Replacement test: if the paragraph could apply to any industry, make it specific.
- Relevance test: if it does not bear on the caller's question, cut it.
- Source test: if challenged, can the report show where the claim came from?
- Verdict test: if it tells the caller what to do instead of what the evidence favours and how strongly, rewrite it.
- Scope test: if it introduces a new research direction, did the user approve it?
