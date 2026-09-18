# Task cost reporting

`workflow_interpreter.costs` reports observed token usage and API-equivalent
cost for one explicit contractor stage or a finite explicit cohort. Reporting
is read-only: it reads Beads, explicitly mapped wrapper artifacts, a local
pricebook, and an optional local supplement. It never launches work, mutates a
task, fetches prices, or emits prompt/transcript content.

## Commands

```text
python -m workflow_interpreter.costs \
  --config scratchpad/foreman.toml \
  --prices config/task-cost-prices-2026-09-13.json \
  task STAGE_ID --format json

python -m workflow_interpreter.costs \
  --config scratchpad/foreman.toml \
  --prices config/task-cost-prices-2026-09-13.json \
  cohort STAGE_ID [STAGE_ID ...] --format text
```

The cohort command accepts IDs only; it never scans a repository. By default,
the command selects the latest snapshot in the supplied pricebook. This gives a
common latest-rate comparison even when a task ran earlier; it is not
historical billing. `--as-of YYYY-MM-DD` instead selects the snapshot with that
exact retrieval date and fails if the pricebook has no exact match. It supports
explicit common-date comparisons, not automatic execution-date pricing. There
is no `--run-date` mode, and neither selection reconstructs historical actual
billing. `--runtime-root ROOT_ID=/absolute/wrapper/instance` may be repeated
when richer raw telemetry is available. The mapping identifies the instance
directory containing `<activation-id>/run.jsonl`, its launch receipt, and exec
ledger. Any missing path, symlink escape, malformed receipt, or ambiguous exec
identity is diagnosed without reading outside that root.

Crew logs are streamed with finite byte and event limits. Only terminal
usage/model fields are retained. Output uses an allowlisted report schema and
never includes event text, prompts, tool arguments, or transcript tails.

## Coverage and pricing

Durable activation usage is the fallback when raw telemetry is absent or
invalid. A usable raw observation replaces, rather than adds to, that baseline.
Prior, failed, abandoned, superseded, and current attempt roots are included.
Invalid counters are excluded and make coverage incomplete; `null` means
unreported while `0` means measured zero. A cost is not complete unless input,
cache-read, output, and cache-write usage are all reported. Cache-write usage
may be either one generic counter or both explicit 5-minute and 1-hour TTL
counters; a missing member of either representation remains an explicit
`missing_usage` item. A still-minted activation with no handle, exit, outcome,
or usage is listed but contributes no observation because it never executed.

A missing service tier is not priced by default. Pass `--normalize-standard`
to deliberately apply standard API rates to observations whose tier is absent;
the report then labels its `pricing_basis` as `standard-rate-normalization`.
An observed but unlisted tier remains unpriced even with normalization. This is
an API-equivalent comparison estimate, not a claim about actual billing.
Vendor-reported cost remains a separate field. Unknown cache-write TTLs and
unavailable OpenAI cache-write rates remain missing whenever their token count
is nonzero.

A report exposes `whole_task_cost_usd` only when task completion, engine usage,
rates, and external attribution are all complete. Otherwise it reports
`partial-observed-spend` and a known priced subtotal. Closed stage status alone
is insufficient: the contractor record, available root terminal and stage
close evidence, mapped landing intent/receipt, and every current and prior root
identity must not contradict one another. Evidence not mapped or retained is
labeled unavailable rather than treated as verified.

Coordinator, planning, and child calls are never assumed to belong to a task.
Supply a strict versioned supplement when they can be explicitly attributed:

```json
{
  "schema": "task-cost-supplement/1",
  "records": [
    {
      "record_id": "ledger-row-17",
      "usage_identity": "session-7/turn-3",
      "owner_task_id": "STAGE_ID",
      "parent_task_id": null,
      "source_reference": "operator-ledger:17",
      "provider": "openai",
      "profile": "codex",
      "model": "gpt-5.6-sol",
      "service_tier": "standard",
      "measurement": "step-delta",
      "role": "coordinator",
      "effort": "high",
      "tokens": {
        "input": 100,
        "cache_read": 0,
        "cache_write": 0,
        "output": 20
      }
    }
  ],
  "scope_declarations": [
    {
      "task_id": "STAGE_ID",
      "source_reference": "operator-ledger:coverage-review",
      "coordinator_complete": true,
      "children_complete": true
    }
  ]
}
```

Use `--supplement PATH`. Exact duplicate records deduplicate; a conflicting
record ID or underlying usage identity fails. Parent/child cohort rollups union
underlying identities so shared usage is counted once. A scope declaration is
explicit evidence from its named source, not automatic historical chat
coverage.

## Reading reports

JSON reports contain completion evidence, all attempts and activations,
requested and observed model identity, role/model subtotals, raw token
categories, known repriced subtotal, separately preserved vendor cost, missing
rates, uncovered scope, measurable activation durations, and pricebook
date/hash/source URLs. Task text always labels the API-equivalent interpretation,
pricing basis, and whether the dated snapshot was the latest available or an
explicit `--as-of` selection. No generation timestamp is emitted, so repeated
reads of unchanged inputs are byte-stable. Cohorts report success rate and total
observed spend separately from mean/median completely measured completed-task
cost. Their JSON and text identify the pricing basis for both statistic groups,
using `mixed` when constituent task reports differ, and list their snapshot
selection and dates. Zero qualifying completions produce `null` statistics.
Mixed-model work remains mixed, and these descriptive totals do not establish
that one model caused a better cost or outcome across unmatched tasks.
