# Coverage and sync record

Each formal verify skill keeps one small data file, `coverage.json`, beside its
`SKILL.md`. It records per check which code the check guards and the last
commit at which the model was confirmed to describe that code, so drift shows.
Its readers are the skill's `scripts/check.py`,
maintain-formal-verification-skill and the help unit's freshness check, so it
stays a data file, never prose inside `SKILL.md`.

## Format

```json
{"format": "formal-coverage/1",
 "checks": [{
   "id": "seat-sold-once",
   "property": "A seat is sold to at most one order.",
   "harm": "Two buyers would pay for the same seat, and one is turned away at the door.",
   "tool": {"name": "TLC", "version": "1.7.4", "sha256": "<64 hex>", "runtime": "temurin-25.0.5+8.0.LTS"},
   "model": "model/SeatBooking.tla",
   "config": "model/SeatBooking.cfg",
   "broken_variants": [{"config": "model/broken-no-row-lock.cfg", "must_break": "SoldOnce"}],
   "covers": [{"path": "<src>/booking.py", "symbols": ["reserve_seat"], "model": ["TakeHold", "Pay"]}],
   "bounds": ["two seats, two buyers, at most two retries each"],
   "assumptions": ["the database runs at read committed"],
   "not_covered": ["refunds", "restore from backup"],
   "sync_commit": "<40 hex>",
   "run": "python3 <skills-folder>/<area>-verification/scripts/check.py"}]}
```

| Key | Holds |
|---|---|
| `format` | Always `formal-coverage/1`; other units recognise the skill by it |
| `id` | A short stable name for the check, in the project's words |
| `property` | The rule checked, one plain sentence, no notation |
| `harm` | What a user loses when it breaks, one plain sentence |
| `tool` | Name, exact version, `sha256` of the pinned artifact (jar, binary or locked package) and `runtime` version |
| `model`, `config` | The main artifact (spec, harness, proof or property test) and its configuration, or `null`; paths relative to the skill folder |
| `broken_variants` | Each broken configuration or file and its `must_break` name (`tool-branches.md`) |
| `covers` | Each guarded file: its real path, its real symbols, the model elements tracing to them |
| `bounds`, `assumptions`, `not_covered` | Plain phrases; empty lists are written, never left out |
| `sync_commit` | Full hash of the last commit the model was confirmed against |
| `run` | The one command that reruns every check in the file |

## Rules

- `covers` names paths and symbols that exist at `sync_commit`; the model's
  comments give the exact lines (`model-fidelity.md`). A file the model only
  abstracts is still listed, with `"abstracted": true`.
- `property` and `harm` are each one sentence a reader who never opens the
  model can act on.
- `sync_commit` moves forward only after a rerun confirms that the model
  matches the code as of the new commit: the covered diff read, the model
  updated from it, the main configuration and every broken variant giving their
  expected verdicts. A check that passes on a model nobody compared with the
  new code does not move it.
- `check.py` prints `git diff --stat <sync_commit> -- <covered paths>` first,
  working tree included, so drift shows before any verdict, and refuses to run
  when a key is missing.
- A formal verify skill older than this format has no `coverage.json`; it is
  recognised by content (`formal-verify-skill.md`, last section), and
  maintain-formal-verification-skill infers its sync commit and writes the file
  at its first pass.
