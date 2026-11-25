# Outside sources

Load from Gather step 4. A project records which outside systems it has in
`.repo-context/evidence-sources.md` (if present); this file says how to search each one. Every
search here is read-only: run queries and open records, but create, edit or
acknowledge nothing, not even a saved query or a dashboard.

## The sources file

Not every project has every source; a library with no deployed service has no
telemetry, and "not here, because …" is a complete answer. If the file is
missing, a person can create it from this format:

```markdown
# Evidence sources

Read by the `why` skill. One row per source kind; keep the names as written.

| Source | Status | Detail |
|---|---|---|
| Analytics warehouse | have | Where it is, how to reach it read-only, what it holds |
| Observability | alternative | The alternative to search instead, and how |
| Error tracker | not here | Why not; revisit when … |
| Incident records | … | … |
| External ticket tracker | … | … |
| Document store | … | … |
| Team chat | … | … |
```

- `have`: search it with its section below.
- `alternative`: search the named alternative instead, applying the section below
  where it fits.
- `not here`: list it in the sources line as a known coverage gap, with the reason.

A row that names a credential gives only where it lives, never the secret.

## Runtime signals across sources

These need a dated runtime signal from the warehouse, observability or the error
tracker; skip them when none is `have` or `alternative`.

- Compare when a signal rose, fell, first appeared or stopped, and the releases it
  touched, with the date the target shipped. A change in step with the ship date
  supports a motive; one before it suggests the trigger. Either stays suggestive
  until the other changes that landed in the same window are checked.
- A metric, a logged event or a chart shows that someone was interested, not
  why the target exists: pair it with a commit or pull-request citation before
  claiming cause.
- When a recorded distribution or monitor threshold matches a constant in the code,
  cite it as evidence of where the number came from.

## Analytics warehouse

- Look in product events, usage and billing events, experiment data, system tables
  and pipeline lineage.
- Before any query, confirm table and column names with listing and describe
  statements. Never report from a table you have not confirmed.
- Query the deduplicated, typed models first; drop to raw events only where no model
  serves.
- For events newer than a model's last refresh, query the raw table and deduplicate
  by event id.
- Check that a field existed when the target was written; older data may lack it or
  hold it only in raw form.
- Motive lives in an experiment's exposure counts and decision rows, and in the
  expensive queries behind a migration.
- Record each finding with its type, table, exact query, window, a compact numeric
  summary (never raw rows), its ship-date correlation and its strength.

## Observability

Metrics, monitors, dashboards, traces, logs and notebooks.

- Find the services that own the target, and their dependencies, before searching.
- Read the dashboards and monitors that cover the target, with their queries and
  thresholds, before raw telemetry. A metric or monitor existing at all shows
  someone was concerned.
- For timeouts, retries, slow paths and cross-service behaviour, use span statistics
  and specific traces.
- Narrow log searches by service, tag, text and a window around the change, and
  aggregate in place; never dump raw logs.
- Motive lives in a dashboard built by the target's author, an incident that names
  the code, and a log pattern before the change that the guard would prevent.
- Record each item with its type, name, identifier, owner, dates, the condition or
  query that bears on the question, and the strength of the connection.

## Error tracker

- Open the full error event, not the summary: check that its trace crosses the
  target and that its tags and breadcrumbs match the condition the target guards.
- A root-cause analysis the tool generates is inference only; the events and
  traces are the evidence.
- Record each issue with its id, title, project, first and last seen, event count
  with any sampling, releases, a verbatim trace excerpt, its ship-date correlation,
  a link and the author's notes.

## Incident records

When the target looks defensive (a guard, retry, limit or fallback), search incident
records, incident-labelled tickets and incident channels in a window around the date
it was added.

## External ticket tracker

Search issues, comments, status updates, project documents, labels and milestones
for the business motive, using the terms from Gather step 3 and the ids the commits
name.

## Document store

Requirement documents, specs, decision records, meeting notes, postmortems and
runbooks kept outside the repository. Search with broad keywords, since pages often
carry no link to the code. Follow backlinks and child pages, meeting-note databases
and the authors' personal spaces.

- Motive lives in a problem section that matches the target's purpose, a list of
  rejected approaches, a postmortem naming the target as the fix, dated decision
  notes and a decision record filled in with substance.
- Record each document with its address and whether it is final or a draft.

## Team chat

Search for the deliberation: the author's messages in a window around the merge
date, and messages that carry the pull request's link. A flippant remark before a
commit is not a decision; look for the considered discussion.
