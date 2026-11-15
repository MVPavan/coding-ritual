# Pantry feature map (worked example)

A fictional product, used only to show the shape `../feature-map.md` asks for.
Pantry keeps a household stock list: a web page served by `pantry serve` and a
`pantry` command line over the same data. A real map uses the product's own
names throughout.

Read this index first, then open the one feature file that matches your task
and follow it as the recipe.

## Baseline

- **Launch:** `scripts/control web start --data "$RUN_DIR"`; ready when
  `http://127.0.0.1:8740/items` lists the three seeded items.
- **Command line:** `scripts/control cli -- pantry --data "$RUN_DIR" <args>`.
- **Seed:** `scripts/control seed --data "$RUN_DIR"` loads `rice`, `lentils`
  and `oats`, one each.
- **Sign-in:** none; the local server trusts loopback.
- **Run folder:** `RUN_DIR` is a new temporary folder `pantry-verify-<run-id>/`
  per run, removed by `scripts/control stop`; evidence goes to
  `$RUN_DIR/../pantry-evidence-<run-id>/`, which cleanup keeps.
- **On the path:** `pantry` (built once by `scripts/control build`), a browser
  driver the control helper wraps.

## Features

| File | What the user does |
|---|---|
| `add-item.md` | Adds an item to the stock list from the web page |
| `export-items.md` | Exports the stock list from the command line |
