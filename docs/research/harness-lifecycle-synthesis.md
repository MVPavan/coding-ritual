# Reference-Harness Lifecycle — Research Synthesis

Synthesis of two independent xhigh research passes on the same A–F brief:
- **Fable-5** → [harness-lifecycle-fable5.md](harness-lifecycle-fable5.md)
- **GPT-5.5** (web search) → [harness-lifecycle-gpt55.md](harness-lifecycle-gpt55.md)

They ran with no cross-talk and **converged ~85%**. That agreement is itself a
signal: the disagreements below are the only places a real decision is needed.

## Verified facts (re-confirmed against the live tree, not taken on faith)

| Fact | Source | Confirmed |
|---|---|---|
| `install-harness.sh` **silently overwrites** any non-user-owned core file that was edited locally; `/update` re-runs it → local edits to skills/rules/agents are lost | [install-harness.sh:36-41](../../mvp-harness/plugins/mvp-plugin/scripts/install-harness.sh#L36-L41) | ✅ read the code |
| `build-template.sh` has **no `skills/` or `commands/` exclusion** → any lifecycle skill added to root `.claude/` leaks into the template payload shipped to every adopted repo | [build-template.sh:50-58](../../mvp-harness/plugins/mvp-plugin/scripts/build-template.sh#L50-L58) | ✅ read the code |
| everything-claude-code: 457 `SKILL.md` / 291 commands / 175 agents in the pinned checkout | both, measured | ✅ counted earlier |
| Those 457 collapse to **~183 unique logical skills** (mirror-tree inflation ~2.5×) | Fable, measured | ⏳ plausible; validate as scanner's first calibration test |

## Per-area verdict

### A — Change detection · STRONG AGREEMENT
Both: **persisted capability manifest with normalized content hashing**; git is the
transport/provenance layer, not the semantic detector; a materiality filter; never
feed 457 bodies to an LLM — inventory deterministically, LLM-read only the changed
shortlist. Both reject embeddings-as-detector (fuzzy = suggestions only).

**Combine the two — each brought something the other missed:**
- **Fable:** dedup to *logical capability* via a per-repo `scan-config.yaml` with
  priority-ordered roots (collapses 457→183 — kills the single biggest noise source).
  Two-tier materiality: deterministic tier-1 (hash body + frontmatter-description
  separately; ADD/REMOVE always material, MOVE cosmetic, MODIFY material only if
  description changed or diff >~15 lines/10%), LLM tier-2 on the shortlist.
- **GPT-5.5:** richer hashing — raw blob + normalized content + a **semantic
  signature hash** (name, description/trigger, tools/permissions, MCP metadata,
  hook event/matcher, script refs, dependency footprint). Keep raw diffs linked in
  every report so aggressive normalization can't hide a real prose edit.

**My rec:** manifest + logical-capability dedup + semantic-signature hash + two-tier
materiality. Stdlib-only Python scanner. State as committed JSON.

### B — Two axes · STRONG AGREEMENT + one important addition
Both: **one inventory engine, two report modes** — *drift* (pinned SHA → upstream
HEAD, "what changed since our pin") vs *gap* (reference vs our mvp-harness manifest,
"what do they have / better"). Keep the report schemas **distinct** (GPT-5.5's point:
reviewers must not confuse "new upstream" with "worth adopting"). Matching order:
exact → curated alias → normalized name+kind → fuzzy (suggestion only).

**Fable's key addition — adopt it:** an **adoption ledger**
(`adopted | rejected | deferred` + reason + `source_sha`). Without it the gap report
re-nags the same rejected items forever; with `source_sha` provenance it yields a
high-value alert almost free — *"upstream improved something we already adopted."*

### C — Trigger & cadence · MINOR FORK ⚠️
Both: **manual-first is authoritative**; **no git hooks** for upstream detection
(submodules never change without you — there's no local event to hook).
- **Fable:** manual command(s) + a **zero-infra SessionStart staleness nudge**
  (>30 days → one printed line). No cron/CI now — reference harnesses are research
  material, not dependencies; nothing breaks when stale.
- **GPT-5.5:** manual + an **optional weekly scheduled poll** (GitHub Action / cron)
  that opens/updates a beads issue only on material change (avoid top-of-hour slots).

**My rec:** Fable's nudge-now, and treat GPT-5.5's weekly poll as a **documented
opt-in for later** (design the scan script so a cron/Action is a thin wrapper). No
scheduled infra until staleness actually bites. *(Low-stakes — easy to change.)*

### D — Evaluate + route · STRONG AGREEMENT
Both: **deterministic shortlist + comparison report by code; human approves the
route; agent argues fit.** Both independently flagged the same failure mode —
importing impressive-but-unused catalogs — and both make **reject/defer the default**
("force *why not reject?*"). Rubric matches closely:
- **template** = universal (~every repo) + low/zero dependency + small context cost +
  must exist in **both** `.claude` and `.codex` (or declared claude-only);
- **new plugin** = external tool/MCP/binary/credential dependency, or domain-specific
  (the code-intel / codex-adapter archetype);
- **merge** = same job-to-be-done + same dependency boundary as an existing plugin;
- **reject/defer** = catalogs, repo/org-specific, duplicate wording, always-on cost.

**Combine:** route decision lands on a **beads issue** for human approval; report
includes GPT-5.5's **context/size cost** and dependency/permission surface, and MCP
servers are treated as dependency-bearing (not mere config). Reserve **Codex critique
for template routes only** (Fable — widest blast radius, so worth the second opinion).

### E — mvp-plugin structure · THE REAL FORK ⚠️⚠️
Both identify the **same root constraint**: Codex CLI has no plugin system, so
`.codex/` must be real repo files no matter what → the dual-tree burden is unavoidable.
They weight it oppositely:
- **Fable (decisive):** **keep copy-on-adopt; fix the update with a manifest-stamped
  three-way merge.** Plugin-native/symlink designs only dedupe the *Claude* half,
  making the trees structurally asymmetric and *worsening* sync; symlinks break
  Windows/collaborators; copy is the only model where a collaborator gets the harness
  from `git clone`. Fix = `build-template` emits `harness-manifest.json` (per-file
  hashes) → adopt stamps it → update does base/local/new three-way (untouched→update,
  local-only→keep, both→keep local + write `.template-new` + agent reconcile) + a
  guaranteed-untouched local-extension convention. **~100–150 lines, no re-architecture.**
- **GPT-5.5:** **gradually evolve** to "thin adopted layer + plugin-provided reusable
  core" (v1 tooling → v2 split reusable skills into a `core-workflows` plugin → v3
  migrate copied core to plugin refs where safe) — but itself hedges: *"I would not
  make template-as-plugin the whole answer until Codex has clean plugin semantics."*

**My rec — they actually reconcile:** **Keep copy-on-adopt and add the three-way
merge (Fable)** for the *core template* — it fixes the verified silent-overwrite bug
directly and cheaply. **Continue routing heavy/optional/dependency-bearing
capabilities to standalone plugins** (GPT-5.5's updatability point) — which is already
exactly how `code-intel` and `codex-adapter` work. So: core → copy + three-way; heavy
optional → plugin. **Reject a full plugin-native migration** now (ergonomic cost,
Claude-only benefit, Codex asymmetry).

### F — Orchestration surface · STRONG AGREEMENT
Both: **lean, root-only, no mega-agent**; one read-only rule ("reference harnesses are
read-only inspiration; never edit submodule internals; scans never move pins"); a
state dir + schema. Fable is leaner (1 scan script with subcommands + 2 commands + 1
evaluate/sync-back skill + 1 nudge hook); GPT-5.5 splits into 5 named commands. Take
**Fable's consolidation** (`scan.py`: scan/drift/gap/status/nudge; `/harness-status`,
`/harness-scan`; `harness-evaluate` skill that also drives the [5] sync-back checklist),
plus GPT-5.5's explicit `harness-sync-back` as a distinct, nameable step.

**Prerequisite (must-fix-first):** add the curation-only exclusion to
`build-template.sh` (rsync `--exclude`/`--exclude-from`), or the entire lifecycle
surface leaks into every adopted repo. Verified leak path today.

## Proposed phased build (consensus Top-3 + the two verified fixes)

- **P0 — leak fix (prerequisite):** add curation-only exclusion to `build-template.sh`
  so root lifecycle skills/commands never enter the payload. *Tiny; unblocks everything.*
- **P1 — scanner + manifests + drift report:** stdlib Python; logical-capability dedup;
  two-tier materiality. **Calibrate on `superpowers` then `everything-claude-code`**
  (success = ~183 logical capabilities, credible material/minor split).
- **P2 — gap report + adoption ledger + beads wiring:** makes the loop an idempotent
  curation queue that stops re-nagging.
- **P3 — three-way `/mvp-plugin:update`:** `harness-manifest.json` + base/local/new
  merge. Independent of P1/P2; fixes the only verified silent-data-loss behavior.
- **P4 — evaluate/route skill + root command surface + read-only rule + nudge hook.**

## Open questions to settle before building
1. Canonical state location: `harness_lifecycle/state/` (Fable) vs
   `state/reference-harness/` (GPT-5.5)? *(cosmetic; pick one.)*
2. Scheduled polling now (GPT-5.5) or nudge-only + opt-in later (Fable)? — **rec: later.**
3. When does a *capability group* (a bundle-only folder) get adopted as a unit vs a
   single skill? — defer to first real case.
