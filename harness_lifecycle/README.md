# harness_lifecycle

Tooling for curating the external agent harnesses under `reference_harnesses/`
(git submodules) into our own `mvp-harness`. This directory holds the
**deterministic** half of the lifecycle — "what does a harness ship?" and "what
changed?" — so the model only ever reads the short list of things that actually
moved, never hundreds of files.

Lives at the repo root (not under `.claude/`), so it is **never** copied into an
adopted repo by `mvp-plugin`.

## `scan.py` — capability scanner + differ

Pure Python standard library, no dependencies. A **capability** is a skill /
command / agent / rule / hook / MCP server / plugin.

```bash
# Inventory a harness working tree -> JSON catalog + a summary table
python3 harness_lifecycle/scan.py catalog reference_harnesses/superpowers \
    --out harness_lifecycle/catalogs/superpowers.json

# What changed between two catalogs (e.g. last-reviewed vs now)
python3 harness_lifecycle/scan.py diff old.json new.json

# What did upstream add/change since our pinned submodule commit
python3 harness_lifecycle/scan.py drift reference_harnesses/superpowers
#   fetches origin, catalogs the pinned commit vs upstream HEAD (via git archive,
#   no checkout), and reports the drift. Use --no-fetch to skip the network call.
```

### Logical capabilities (why counts collapse)

Harnesses mirror the same skill into several per-tool trees
(`.claude/`, `.cursor/`, `.kiro/`, `.agents/`) and into translated `docs/`
copies. Raw file counts therefore lie: `everything-claude-code` has 457 `SKILL.md`
files but only **182 logical skills**.

The scanner deduplicates to logical units:

- **`docs/`, `tests/`, `examples/`, vendor/build dirs are excluded** (they hold
  documentation and fixtures, not capabilities). The excluded count is reported —
  nothing is dropped silently.
- Remaining files are grouped by a **namespace-aware identity** — the path with
  leading per-tool mirror roots (`.kiro/`, `.cursor/`, `.claude/`, …) stripped. So
  mirror copies of one skill collapse, while two same-named skills in *different*
  plugins (`plugins/discord/…/access` vs `plugins/telegram/…/access`) stay distinct.
  The **canonical** copy is the one under the top-level, non-hidden root; mirror
  paths and their content hashes are recorded as `variant_hashes`. Plugin identity
  comes from `plugin.json`'s `name`, not the `.claude-plugin` directory.
- Only *true* duplicates collapse. `.cursor/rules/*` that share no name with
  `rules/*` stay distinct — the scanner never merges different capabilities.
- **Files bundled inside a skill's own folder are recorded as that skill's
  `assets`**, not promoted to their own rows. Harnesses ship prompt templates and
  helper scripts next to `SKILL.md` (e.g. superpowers' `implementer-prompt.md`,
  handed to a subagent by `subagent-driven-development`). They are part of the
  skill, so counting them as separate agents/hooks would misrepresent the design.
  Each asset is attributed to its **nearest** enclosing skill.
- **Hooks**: a file under a `hooks/` dir counts when it has a hook suffix *or no
  extension at all* — superpowers' `hooks/session-start` is extensionless and
  invoked through a `run-hook.cmd` dispatcher. Files whose stem starts with
  `test-` or ends with `-test` are self-test programs, not capabilities, and are
  excluded.
- Each capability records its **`category`** — the grouping directory it sits in
  (a skill's own folder's parent: `skills/productivity/foo/SKILL.md` → `productivity`;
  a flat `skills/foo/SKILL.md` → the generic `skills`). `gap` prints it as
  `[category] name` so a reviewer sees where a candidate falls — e.g. an upstream
  `[deprecated]` skill flags itself as one to skip.

### Materiality (signal over noise)

`diff` / `drift` split changes into **material** and **minor**:

- **ADDED / REMOVED** → always material.
- **Surface change** (name / description / tools / MCP command changed, detected
  via `signature_hash`) → material.
- **Body change** → measured precisely when both trees are on disk (`drift`):
  material if more than ~15 lines **or** >10% of lines changed, else minor.
  From catalogs alone (`diff`) the magnitude can't be sized, so a body change is
  surfaced as material rather than risk hiding a real edit.
- **Mirror-only / path-only** change (canonical copy unchanged) → minor.

Thresholds (15 lines / 10%) are conservative defaults; tune in `classify_change`.

## `registry/` — our skills, reference rulings, and the ledger

The registry records every skill we own (`skill-records/`, placed on domain ×
ADLC stage × sub-stage), every ruling on a reference capability, and every
change, in one append-only JSONL ledger, with the reviews behind each ruling
(`reviews/`). Its tool imports `scan.py`. The method,
layout and ledger schema are in [`registry/README.md`](registry/README.md).

```bash
uv run python harness_lifecycle/registry/registry.py gap superpowers --kind skill --beads   # unruled, changed since ruled, present but unruled
uv run python harness_lifecycle/registry/registry.py ours --out harness_lifecycle/catalogs/ours.json
uv run python harness_lifecycle/registry/registry.py build && uv run python harness_lifecycle/registry/registry.py check
```

It replaced `gap.py`, `ledger.json`, `aliases.json`, `export_csv.py`, the
`inventory/` CSVs and `casebook/casebook.py` on 2026-10-14; their content is in
the ledger's migration round, and the files stay in git history.

## `catalogs/` — committed baselines

One `<repo>.json` per reference harness: the last-reviewed capability state.
Re-`catalog` + `diff` against these to see what changed since the last review.
Schema id: `harness-capability-catalog/v1` (see `Catalog.to_dict` in `scan.py`).

`ours.json` is the odd one out — **our own** harness, written by
`registry.py ours --out` rather than `scan.py catalog`, because only `build_ours`
knows what "ours" means (root `.claude/` + `.codex/` + every plugin, minus each
plugin's `template/` copy of the root harness). It is a **working-tree snapshot**,
so its `source_commit` is null; the reference catalogs are pinned, this one is
whatever was on disk when it ran. Regenerate it rather than trusting its age.

## `archive/` — retired artifacts

Frozen and superseded material: the 2026-08 casebook, the 14-bucket
taxonomy, the per-family skill comparisons and the whole-harness comparison, catalogs of removed submodules, the earlier usefulness pipelines
and the generated HTML dashboards. The registry ledger now answers "which
reference capabilities should we take?".

Nothing live reads `archive/`. See [`archive/README.md`](archive/README.md).

## Command surface (Claude Code)

The lifecycle is driven from the root harness. Everything here is curation-only and
kept out of the shipped template by `template-exclude.txt`:

- **`/harness-status`** — upstream-drift one-liner across all reference harnesses.
- **`/harness-scan <name>`** — deep drift + gap for one harness, then routing.
- **`harness-evaluate` skill** — decide template / new-plugin / merge / reject for a
  candidate and drive the sync-back; records the decision in the registry ledger.
- **`harness-*` skills and `AGENTS.md`** — curation and repository guardrails.
- **`.claude/hooks/harness-staleness-nudge.sh`** — SessionStart reminder when the
  catalogs are more than 30 days old.

## `adlc/` — agentic development lifecycle

`GUIDE.md` holds the lifecycle's stages and sub-stages (§1) and the durable
principles, each with its model-dependent setting and revisit trigger.
`skill-map.md` places every skill of the three compared harnesses on those
sub-stages, and `harness-map.html` rates their coverage. `document-model.md`
defines the documents a project keeps across the lifecycle and their layout;
`tracker-model.md` defines how Beads represents it (statuses, bead position,
epics sized by outcome).
`sources/` holds the vendor capture; `council/` holds the council briefs,
member answers and judgments (`council/stages/` chose the stage names).

## Limitations (current)

- Frontmatter parsing is minimal (single-line scalars); multi-line descriptions
  are truncated to their first line.
- MCP detection reads `mcp.json` / `.mcp.json` / `plugin.json` `mcpServers`; other
  bespoke MCP config layouts are not yet recognised.
- Hook signatures use file content only (event/matcher wiring lives in
  `settings.json` / `hooks.json`, not yet parsed) — so a hook is recognised by
  location, not by proof that something wires it.
- Commands are recognised as Markdown only. Harnesses that also ship `.toml`
  command copies for other tool families (Gemini, Antigravity) are **not**
  inventoried — deliberate: this repo curates the Claude/Codex surface only.
- Mirror deduplication cannot collapse copies the scanner never recognised. When
  a platform copy uses an unparsed format, it is dropped before grouping, so
  `variant_hashes` will not reveal that the copies have diverged.
