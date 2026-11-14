# Export items

From the command line, the user exports the stock list as JSON or CSV, to the
terminal or to a file; an empty list exports an empty result, not an error.

## Sub-features

- `export-json`: `--format json` prints every item.
- `export-file`: `--out <path>` writes the export to a file.
- `export-empty`: an empty list prints `[]` and exits 0.

## How to reach it

- `pantry export` with `--format json` or `--format csv`.
- `pantry export --out <path>` to write a file.

## Driving it

- action: export the seeded list as JSON
  command: `scripts/control cli -- pantry --data "$RUN_DIR" export --format json`
  result: exit code 0; stdout parses as JSON with the three seeded names; stderr empty
- action: export to a file, then read the file back
  command: `scripts/control cli -- pantry --data "$RUN_DIR" export --format json --out "$RUN_DIR/out.json"`
  result: exit code 0; `out.json` holds the same three items as the stdout export
- action: clear the list, then export
  command: `scripts/control cli -- pantry --data "$RUN_DIR" clear --yes` then the JSON export again
  result: exit code 0; stdout is exactly `[]`; stderr empty

Reset: `scripts/control seed --data "$RUN_DIR"` after the empty case.

## Gotchas

- `--format csv` prints a header even for an empty list; assert the empty case
  on the JSON output only.
- Without `--data`, `pantry` reads the person's own list; every command in this
  file passes the run folder.
