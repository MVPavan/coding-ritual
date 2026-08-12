# Testing agent docs

You do not know a document teaches the right thing until you have watched an
agent behave differently because of it. Testing is proportional: pick the
lowest rung that gives real evidence, and climb only when the document
enforces more.

## The ladder

| Rung | When | Method |
| --- | --- | --- |
| Cold reread | any small edit | Reread as a stranger; run the no-op test on each new sentence |
| Fresh-context read | new doc, section, or body rewrite | A subagent gets the doc and a task that should exercise it; watch what it does |
| Packaging test | new or changed description, pointer, rule scope, or command | Fresh context with only the normal entry point — below |
| Baseline + pressure | discipline rules the agent will want to skip | Below |

Never test by asking an agent "is this clear?" — agents say yes. Give it a
task and watch the behaviour.

## Test the packaging, not just the body

A fresh-context read hands the agent the document, which bypasses the very
mechanism most edits are for. When the change is in how the document is
*reached*, test through the real entry point:

- **Description** — fresh context with only the metadata loaded, never the
  body. One task that should fire it, one neighbouring task that should not:
  a trigger that misfires costs as much as one that stays silent.
- **Pointer** — the agent gets the pointing document and a task whose answer
  lives behind the pointer; success is following the pointer unprompted.
- **Command** — invoke it exactly as the human would, arguments included.
- **Rule / root instruction** — a fresh session in the scope where it should
  load; check the behaviour it governs, not whether the file exists.

## Baseline: watch it fail first

Before writing a discipline rule, run the tempting scenario *without* the
document. Record verbatim what the agent does and every rationalization it
offers. Those exact excuses are what the document must counter.

If the baseline shows no failure, there is nothing to fix — stop, do not
write the guidance.

## Pressure-test: watch it hold

Run the same scenario *with* the document, then again with pressures stacked
on top:

- time — "the demo is in five minutes"
- sunk cost — "you've already written it, three hours in"
- authority — "the senior engineer said to skip it"
- exhaustion — end of a long session, one small step from done

Success is compliance under stacked pressure, not in the friendly case.

## Close loopholes

Every *new* excuse that testing surfaces gets three edits:

1. an explicit counter naming that exact workaround,
2. a row in the rationalization table,
3. a red-flag entry.

Re-test after each round. Done when a round produces no new excuses.

## Micro-test wording

To choose between wordings before running full scenarios:

- Fresh-context, single-shot samples: the realistic surrounding context (the
  full skill, not the sentence in isolation) plus one task that tempts the
  failure.
- Always include a no-guidance control. If the control does not fail, stop.
- 5+ reps per variant — single samples lie.
- Read every flagged output manually; template echoes and quoted
  counter-examples masquerade as hits.
- Variance is a metric: five different interpretations across five reps means
  the wording is not binding — tighten the form before adding words.

Micro-tests verify wording; they do not replace pressure scenarios for
discipline rules.

## What to test, by document type

| Document type | Test with | Success looks like |
| --- | --- | --- |
| Discipline rule | pressure scenarios | complies under stacked pressure |
| Technique / process | a new scenario to apply it to | applies it correctly; no missing-step gaps |
| Reference | retrieval questions | finds and correctly applies the right fact |
| Description / pointer | trigger tasks in fresh context | fires when it should, stays quiet when it shouldn't |
