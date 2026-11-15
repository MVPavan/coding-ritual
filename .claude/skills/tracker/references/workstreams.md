# Workstreams — layout and seeding

Read from `tracker` on its workstream branch. What the roadmap says per phase, and
approving the breakdown, are `to-roadmap`'s; this file is how it lands in Beads.

## Layout

A new workstream gets `docs/workstreams/<name>/`:

- `README.md` — the charter, one screen: what this workstream is, how it is
  tracked. Flat operational work anchors on it.
- `roadmap.md` — the phased plan written by `to-roadmap`, and the bd `--spec-id`
  anchor of every phase epic.
- `plans/` — empty; per-phase plans land here just in time, from `to-plan`.
- `tracking/` — empty; written only by the render script, never by hand.

Epic titles carry the roadmap's phase identifier as a bracket prefix —
`[<phase-id>] <phase name>`, e.g. `[R1] Intake states` — the join key between
roadmap rows and bd epics. Use whatever identifier scheme the roadmap uses; keep it
consistent within the workstream.

## Seeding

1. **Epic per phase:**
   `epic_id=$(bd create -t epic "[<phase-id>] <phase>" --spec-id docs/workstreams/<name>/roadmap.md --design docs/specs/<spec>.md --actor … --silent) || exit; test -n "$epic_id" || exit 1`
   — **`--spec-id` is the workstream anchor: it must be the roadmap.** The
   renderer derives the workstream name and the `tracking/` output directory from
   `dirname(spec_id)`, so an anchor outside `docs/workstreams/<name>/` produces no
   mirrors (the renderer fails with exit 1 rather than skipping quietly).
   `--design` carries the governing spec — the renderer collects the unique
   `design` values across a workstream, so several specs can feed one workstream.
   Keep every epic in a workstream on the **same** `spec_id`: the renderer groups
   by exact match and writes the same `tracking/` directory once per distinct
   value, so a split anchor silently leaves only the last group in the mirror.

   The flag names read backwards here: the field called `--spec-id` holds the
   roadmap and the field called `--design` holds the spec.
2. **Flat stage children** — one per deliverables row:
   `stage_id=$(bd create "<stage>" --parent "$epic_id" -t task --acceptance "<the row's Verify cell>" --actor … --silent) || exit; test -n "$stage_id" || exit 1`
   → dotted ids `<epic>.N`; keep each returned ID for step 3, never guess `.N`.
   No sub-tasks. Every stage carries acceptance.
3. **Dependencies** — after every bead exists, wire real edges only, by the IDs
   `bd create` returned: `bd dep add <issue> <prereq> --actor …`; stage→stage where
   one genuinely needs another's output; epic→epic where a phase gates another.
   Never blanket-chain listing order — independent work stays unchained so it can
   run in any order or in parallel.
4. **Render** the workstream (`tracker`'s Render).

## Extending

- `to-roadmap` appends the new phases to `roadmap.md`; seed only those.
- Keep the workstream's existing `--spec-id` (its roadmap) on the new epics.
- New epics may carry a different `--design` than older ones — a workstream
  accumulates epics from many specs.
- Add epic→epic edges where a new phase genuinely depends on an old one.
- Re-render the tracking mirrors after seeding.
