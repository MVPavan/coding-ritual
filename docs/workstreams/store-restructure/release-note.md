# Release note — S6 cutover: the ledger is the only record store

Four operator-visible changes land with the cutover. All are breaking, and all
are safe to take as a clean break (R12): no committed export and no live
ledger exists at this version.

## BREAKING: `[tracker]` is required, and `[bd]` moved to `[tracker.bd]`

The foreman TOML must now declare which tracker this repository has
(`tracker: TrackerSettings` on `ForemanConfig`, `foreman/config.py`), and bd's
transport settings live under that section rather than at the top level
(`contractor/tracker_config.py`). bd is one tracker among three now, so "how to
reach bd" is part of "which tracker", not a mandatory field every repository
carries.

**Remedy:** rename the `[bd]` table to `[tracker.bd]` and add a `[tracker]`
section above it with `backend = "bd"`. A `backend = "file"` or `"null"`
repository needs no `[tracker.bd]` at all — a `file` tracker needs
`path = …` instead. Without the change the config fails to load with a raw
pydantic validation error naming the missing field. The worked example is
`config/foreman.example.toml`.

## BREAKING: `wf ledger export` writes only for a LANDED task

`export` and `pin-export` both refuse a task in any other state
(run-ledger D5 said "on demand for any task"; store-restructure R13 supersedes
it). The committed file is the anchor a rebuild prefers over every checkpoint,
so a file written mid-run would be older than the activation closes that follow
it, and `import` clears before it refills — one stale on-demand export would
silently roll a task back.

**Remedy:** to capture an in-flight task's state, use the checkpoint anchor
(`refs/wf/checkpoints/<task>`, written automatically), not an export. To get a
committed export, finish the landing; the refusal names the state it found.

## Schema v7 — the `backend` columns are gone

`ALTER TABLE tasks|roots|sessions DROP COLUMN backend`
(`workflow_interpreter/ledger/schema.py`, `_V7_DROP_BACKEND`). Those columns
were the locator's answer to "which store owns this row?" (run-ledger D18);
there is one store now (R1), so nothing is pinned and nothing can disagree.

**Export bytes change.** `tasks` and `roots` rows lose a field, so a file
written by a v6 build does not round-trip against a v7 one, and the header's
`schema_version` is `7`. An older export is refused at import rather than
silently reshaped. Opening a ledger read-only whose schema is older than this
build's is likewise refused (`LedgerSchemaError`); a writable open migrates it
forward.

Operators with a pre-v7 ledger or export: discard it and re-run. There is no
downgrade path and no value in the dropped column to preserve.

## `costs` reads the ledger only

`python -m workflow_interpreter.costs task|cohort` no longer consults a
tracker. A bead's status and close reason were a MIRROR of what the contractor
record and the export anchor already hold, and a cost report built from a
mirror could disagree with the task it describes.

Consequences for the operator:

- The report's inputs are the read-only ledger plus the runtime logs: the
  contractor record (`contractor_records.record_json`) and the stage's closure
  (`ledger.closure.closed`, which reads the pinned export against git).
- A missing or unreadable ledger exits `2` with a named refusal
  (`LedgerAbsent` / `LedgerSchemaError`) instead of degrading to a tracker read.
- A stage whose export is not pinned and closed grades as
  `partial-observed-spend` rather than claiming a settled total. Run the close
  path (which writes and pins the export) before asking for a final number.
- `bd` availability no longer affects a cost report in either direction.
