# Release note — S6 cutover: the ledger is the only record store

Two operator-visible changes land together in S6. Both are breaking, and both
are safe to take as a clean break (R12): no committed export and no live
ledger exists at this version.

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
