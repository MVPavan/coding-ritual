# Reference-Harness Lifecycle — Design Research (Fable-5 @ xhigh)

**Brief:** `docs/plans/reference-harness-lifecycle-plan.md`, areas A–F.
**Date:** 2026-07-03. Independent pass; the parallel GPT-5.5 report was not read.

## Evidence base (measured, not assumed)

All numbers below were measured against the working tree at the pinned submodule SHAs:

- 6 reference submodules + `mvp-harness` (`.gitmodules`); **no `branch =` tracking configured** — upstream drift requires an explicit `git fetch`.
- `everything-claude-code` @ `c7bf143`: **457 `SKILL.md` files, but only 183 unique skill names.** The repo ships multi-tool mirror trees (`skills/` = 181, `.agents/skills/` = 34, `.kiro/skills/` = 18, `.cursor/skills/` = 10, plus `.opencode/`, `.codebuddy/`, `.claude/skills/`…). Same story for commands (291 `.md` across trees vs 79 in top-level `commands/`) and agents (220 vs 47). **Raw file counts overstate logical capabilities ~2.5–4x.**
- Skill file sizes there: p50 ≈ 7.3 KB, p90 ≈ 17 KB, max ≈ 30 KB. Hashing all of them is trivial (<1 s); LLM-reading all of them is not (~1M+ tokens).
- Upstream churn sample: the last 30 commits of `everything-claude-code` touched 33 files, of which only **3** were capability files (`commands/prp-*.md`); the rest were app code (`ecc2/` Rust TUI), translated docs, and marketplace metadata. Raw `git diff` is mostly noise for this purpose; capability-root filtering removes most of it deterministically.
- Repo shapes vary widely: `superpowers` is a clean plugin (14 skills, `.claude-plugin/plugin.json`); `claude-plugins-official` is a marketplace (~25 plugins + 15 `external_plugins/` — the natural unit there is *the plugin*, not its files); `mattpocock_skills` encodes lifecycle in its layout (`deprecated/`, `in-progress/`, `engineering/`…); `claude-code-best-practice` is mostly a tutorial repo; `everything-claude-code` even ships its own modular-install manifests (`manifests/install-{components,modules,profiles}.json`) — useful prior art for area E.
- `mvp-plugin`: template payload = 121 files (15 skills, dual `claude/` + `codex/` trees). `scripts/check-sync.sh` already has a good directive-based manifest format (`body`/`pair`/`claude`/`codex` in `scripts/sync-manifest.txt`) and a normalized-hash baseline (`sync-baseline.txt`) — patterns worth reusing in the new tooling.
- **Verified gap:** `scripts/install-harness.sh` preserves only user-owned files (`CLAUDE.md`/`AGENTS.md`/settings/overlay); every other existing core file is **overwritten in place** on `/mvp-plugin:update` (the copy loop, ~lines 37–41). Local edits to shipped skills/rules are silently clobbered today.
- **Verified gotcha for area F:** `scripts/build-template.sh` excludes only `*/project/` and two python rules from the mirror. Any lifecycle skill/command added to coding-ritual's root `.claude/` will **leak into the template payload** on the next build unless an exclusion is added (the stale `refresh-harness-from-reference` skill in root `.claude/skills/` would leak the same way on a rebuild).

---

## A. Change detection

### Recommendation

A **persisted per-repo capability manifest** (JSON, committed) produced by a small stdlib-only Python scanner, with a **two-tier materiality filter**: tier 1 deterministic (normalization + hashing + thresholds — free), tier 2 LLM judgement applied **only to the tier-1 shortlist**. Git is used *inside* the scanner (`git diff --name-status pinned..target` to know which files to re-hash) but is not the comparison model.

**Unit of change = the logical capability**, not the file: `(kind, canonical-name)` where kind ∈ {skill, command, agent, rule, hook, mcp-server, plugin}. A skill is its directory (SKILL.md + supporting files); a command/agent/rule is one file; for marketplace-shaped repos (`claude-plugins-official`) the unit is the whole plugin. Mirror trees are collapsed: a per-repo priority list of scan roots picks the **canonical instance**; other copies are recorded as `mirrors` and their churn is ignored while the canonical exists. This single decision turns everything-claude-code from 457 tracked things into 183, and eliminates the largest noise source before any cleverness is needed.

### Rationale

- Pure git diffs fail three ways here: they are file-grained (mirror-tree churn multiplies every real change by 2.5–4x), they can't distinguish capability files from app code / translated docs (30 of the last 33 changed files were noise), and they can't express the second axis (vs mvp-harness) at all.
- Off-the-shelf diff/inventory tooling doesn't understand SKILL.md/agent frontmatter semantics or per-repo layout quirks; a ~250-line scanner is cheaper than adapting anything generic — and per the repo's own rule 5 ("if code can answer, code answers"), deterministic transforms belong in code, judgement in the model.
- A committed manifest gives you history for free (git log of the manifest = the audit trail), makes scans reviewable in PRs, and is the shared substrate both comparison axes (area B) consume.

### Implementation sketch

```
harness_lifecycle/
  scan-config.yaml          # per-repo capability roots, priorities, ignores
  state/<repo>.manifest.json
  aliases.yaml              # cross-repo name equivalences (area B)
  ledger.yaml               # adoption decisions (area B/D)
  reports/<repo>/YYYY-MM-DD-{drift,gap}.md
scripts/harness_lifecycle/scan.py   # stdlib only; subcommands: scan | drift | gap | status
```

`scan-config.yaml` (excerpt):

```yaml
everything-claude-code:
  roots:                       # priority order — first hit is canonical
    skills:   [skills, .claude/skills]
    commands: [commands, .claude/commands]
    agents:   [agents, .claude/agents]
    rules:    [rules]
    hooks:    [hooks]
    mcp:      [.mcp.json]
  ignore: [docs/**, ecc2/**, assets/**, examples/**, .cursor/**, .kiro/**,
           .opencode/**, .codebuddy/**, .agents/**, .gemini/**, .trae/**]
mattpocock_skills:
  roots: { skills: [skills] }
  ignore: [skills/deprecated/**, skills/in-progress/**]   # layout carries lifecycle metadata — use it
claude-plugins-official:
  unit: plugin                 # compare plugin.json version + whole-tree hash
  roots: { plugins: [plugins, external_plugins] }
```

Manifest entry (schema v1):

```json
{ "id": "skill:tdd-workflow", "kind": "skill", "name": "tdd-workflow",
  "path": "skills/tdd-workflow/SKILL.md",
  "mirrors": [".agents/skills/tdd-workflow/SKILL.md"],
  "hash": "sha256:…",      "desc_hash": "sha256:…",
  "description": "first ~200 chars of frontmatter description",
  "bytes": 7323, "files": 3 }
```

plus repo-level fields `{schema, repo, scanned_sha, scanned_at}`.

**Normalization before hashing:** CRLF→LF, strip trailing whitespace, collapse 2+ blank lines. Hash the frontmatter `description` separately from the body — a description change is high-signal (it changes when the capability triggers), whitespace-only body churn is zero-signal. This mirrors the normalization trick check-sync.sh already uses (its `.claude`/`.codex` → `<<H>>` sed).

**Tier-1 materiality classification** (drift between two manifests):
- `ADDED` / `REMOVED` capability → always material.
- `MOVED` (same normalized hash, new canonical path) → cosmetic.
- `MODIFIED` → material if the description hash changed, OR the normalized-body diff exceeds ~15 lines or ~10% of the file, OR supporting files were added/removed in a skill dir. Otherwise "minor" — listed in a collapsed section, never sent to tier 2.

**Tier 2** is the `harness-evaluate` skill (area D) reading actual diffs for the shortlist only. On a 183-capability repo a typical monthly delta is a handful of items; the LLM never touches the other ~175.

**Scanning without checkout:** read upstream targets via `git -C <sub> fetch origin` + `git ls-tree -r` / `git show <sha>:<path>` (or a throwaway `git worktree`). The scan must never move the submodule pointer or dirty its worktree — bumping the pin stays a deliberate act after review.

### Tradeoffs

- A manifest is one more artifact to keep honest — mitigated by making the scanner the only writer and committing it (drift is visible in review).
- Canonical-root priority can pick the "wrong" copy if an upstream reorganizes; the fix is a one-line scan-config edit, and `MOVED` detection keeps it cosmetic.
- Per-repo scan-config is manual curation (~10 lines/repo, 6 repos). I consider that a feature: layout knowledge is exactly the kind of judgement that should be written down once.

### Where I'd diverge / least sure

The materiality thresholds (15 lines / 10%) are a guess — tune them after the first real everything-claude-code scan rather than debating them now. I'm also not fully sure the separate `desc_hash` earns its keep vs just "frontmatter block changed?"; keep it only if the first scans show body-churn-with-stable-description is actually common.

---

## B. Two comparison axes

### Recommendation

**One scanner + one manifest schema, two comparators, two reports** — plus a third artifact the brief doesn't name but the loop can't be idempotent without: an **adoption ledger**.

- **Drift report** (`drift <repo>`): manifest(pinned SHA) vs manifest(fetched `origin/HEAD`), same repo, same scan-config. Output: ADDED / REMOVED / MOVED / MODIFIED(material|minor) per capability.
- **Gap report** (`gap <repo>`): manifest(reference @ pinned) vs manifest(**ours**) — where "ours" is produced by pointing the same scanner at `mvp-harness/plugins/mvp-plugin/template/claude` + the sibling plugins (`code-intel`, `codex-adapter`). Statuses: `MISSING` (they have, we don't), `OVERLAP` (both have → candidate for an "is theirs better" pass, area D), `OURS-ONLY` (informational), and `RESOLVED` (already decided — see ledger).

**Cross-repo matching:** exact name → curated alias table → unmatched. `aliases.yaml`, e.g.:

```yaml
everything-claude-code:skill:tdd-workflow:      mvp:skill:test-driven-development
everything-claude-code:skill:verification-loop: mvp:skill:verification-before-completion
superpowers:skill:writing-plans:                mvp:skill:planning
```

The scanner may *suggest* new aliases via description-token overlap, but suggestions are printed for confirmation, never used in the deterministic verdicts. Fuzzy matching that silently decides "these are the same" is how gap reports lose trust.

**The adoption ledger** (`harness_lifecycle/ledger.yaml`) records every decision ever made:

```yaml
- id: everything-claude-code:skill:verification-loop
  decision: rejected            # adopted-template | adopted-plugin:<name> | merged:<target> | rejected | deferred
  reason: "ours covers it; theirs is CI-pipeline-specific"
  at_sha: c7bf143
  date: 2026-07-03
- id: superpowers:skill:writing-skills
  decision: adopted-template
  dest: claude/skills/…         # + codex counterpart
  source_path: skills/writing-skills/SKILL.md
  source_sha: 917e5f5
```

Without it, every gap run re-nags about capabilities you deliberately rejected, and the loop degrades into noise within two cycles. With it, you also get a **third axis almost free**: for `adopted-*` entries, re-diff the upstream file at `origin/HEAD` vs at `source_sha` — "a thing we adopted got improved upstream" is the single highest-value alert this system can produce, and neither plain drift nor plain gap surfaces it.

### Rationale

Drift and gap answer different questions on different timescales (drift: "what changed since I pinned", event-driven; gap: "what am I missing", stock-taking) but consume identical inputs. Two engines would mean two scanners drifting apart; two reports from one substrate keeps the reading experience matched to the question. Cross-repo comparison by name alone is unreliable (`tdd-workflow` vs `test-driven-development`), so the alias table is where human curation buys deterministic reports.

### Tradeoffs

- The alias table is manual. At ~183 capabilities in the biggest repo and maybe 20–30 genuine overlaps with a 15-skill template, this is an hour of one-time work, then drips.
- The ledger grows monotonically; that's fine — it *is* the institutional memory. Add a `review_after` field on `deferred` entries so deferrals resurface rather than rot.

### Where I'd diverge / least sure

Least sure whether description-similarity alias *suggestions* are worth building at all — at this scale, eyeballing the MISSING list once may populate the alias table faster than tuning a similarity threshold. Build the suggestions last, if ever.

---

## C. Trigger & cadence

### Recommendation

**Manual command as the primary trigger, plus a zero-infrastructure staleness nudge. No cron, no CI scheduler, no git hooks — for now.**

- `/harness-status` (cheap, seconds): `git -C reference_harnesses/<r> fetch origin` with a timeout, then one line per repo: `superpowers: pinned 917e5f5, 12 commits behind, 2 capability files touched, last full scan 2026-06-01`. The "capability files touched" count comes from `git diff --name-only pinned..origin/HEAD` filtered through the scan-config roots — so the one-liner already separates signal from noise.
- `/harness-scan [repo]` (minutes): full manifest rebuild + drift/gap reports + beads candidates (area F).
- **Staleness nudge:** a SessionStart hook in coding-ritual (root repo only, not the template) that reads `harness_lifecycle/state/` timestamps and prints one line if the newest scan is >30 days old. That's the entire "keep it current without babysitting" mechanism.

### Rationale

Reference harnesses are research material, not dependencies — nothing breaks when they're stale, so freshness is a nice-to-have, and the cost model should match. Cron/systemd timers on a WSL2 dev box are fragile and invisible; a scheduled GitHub Action needs the repo + submodule remotes reachable from CI and produces reports nobody is in-session to read. Git hooks are a category error here: submodules only change when *you* change them — there is no local event to hook. The one event that matters ("I sat down to work on the harness") is exactly what a SessionStart nudge catches.

### Implementation sketch

- `scripts/harness_lifecycle/scan.py status` does fetch + count; `/harness-status` command file is 10 lines wrapping it.
- Hook: entry in root `.claude/settings.json` SessionStart running `scan.py nudge` (no network — reads timestamps only, so it adds ~0 ms of felt latency and never blocks on a flaky fetch).
- Optional later: a weekly GitHub Actions workflow that runs `status` and commits an updated status file (no PRs, no pings). Add it only if the nudge proves insufficient.

### Tradeoffs

You will occasionally be >30 days stale before noticing. Accepted: the downside is bounded (you review a slightly bigger delta), whereas scheduler infrastructure has unbounded annoyance-per-value.

### Where I'd diverge / least sure

Maybe even the nudge is unnecessary and a monthly habit of running `/harness-status` suffices. I kept the nudge because it's ~5 lines and self-erasing (prints nothing when fresh), but it's the first thing I'd cut.

---

## D. Evaluate + route

### Recommendation

**Automate detection, shortlisting, and the comparison report; keep the route decision human-approved, one candidate at a time, with beads as the queue.** The agent proposes a route + confidence; the human approves; the agent executes the follow-through.

**Routing rubric** (checked in order):

1. **Template** only if ALL three hold: *(a) universal* — you'd want it in >80% of repos you adopt into; *(b) provider-portable* — expressible in both `.claude` and `.codex` trees, or worth a declared `claude`-only entry in `sync-manifest.txt`; *(c) dependency-free* — markdown (+ at most a tiny script), no binaries, no MCP servers, no API keys. Template additions are paid for by **every adopted repo's context window and every future dual-tree sync** — the bar must be high, and "two of three" is not a pass.
2. **Standalone plugin** if it needs external runtime (MCP server, CLI binary, credentials), is domain/stack-specific, or is a large self-contained system with its own docs/scripts. Archetypes already in-house: `code-intel` (binaries + MCP), `codex-adapter` (external CLI + roles). Archetypes upstream: everything in `claude-plugins-official/external_plugins/`.
3. **Merge into an existing plugin** if it extends a domain a plugin already owns (e.g. a new Codex role → `codex-adapter`; a new LSP wrapper → `code-intel`). Test: would a user sensibly want this without the host plugin? If no → merge.
4. **Fold as an improvement** if it overlaps an existing template capability (the OVERLAP bucket): the output is an edit to *our* file, not a new artifact.
5. **Default: reject or defer, with a ledger reason.** The template is a curated ritual, not a kitchen sink — per `harness_learnings/reference-harness-workflow.md`, borrow the smallest durable pattern. Rejection with a recorded reason is a fully successful outcome of this pipeline.

**"Is theirs better than mine" report** (per OVERLAP candidate, generated by the `harness-evaluate` skill; deterministic fields computed by the scanner):

| Field | Source |
|---|---|
| Trigger quality — description specificity, trigger phrases | judged |
| Hard structure — gates, checklists, verification steps, anti-patterns (superpowers' `<HARD-GATE>` is the benchmark) | judged |
| Scope — narrower/wider than ours; what they cover that we don't | judged |
| Token cost — file size, supporting-file count | scanner |
| Dependencies / provider portability | scanner + judged |
| Overlap — normalized diff stats vs our counterpart | scanner |
| **Verdict** — keep-ours / adopt-theirs / **merge-these-specific-sections** (default shape), 3–5 lines | judged |

The verdict must name the exact sections to borrow. "Replace our file with theirs" should be rare; "steal their red-flags table and their gate wording" is the norm.

**Automation boundary:** everything up to and including the report is autonomous. The route decision is a one-line human approval on a beads issue. Follow-through (edit both trees, check-sync, build-template, tests, ledger, submodule bump) is autonomous again, per approved route. For `adopted-template` decisions specifically, run the repo's standard Codex critique on the resulting diff (per `.claude/commands/use-codex.md`) — template changes have the widest blast radius and deserve the second reviewer; plugin merges usually don't.

### Rationale

Adoption edits the shipped harness — high blast radius, low frequency (a handful of candidates per month), and taste-dependent. That's exactly the profile where human-in-the-loop is cheap and auto-adoption is reckless. Conversely, making a human *hunt* for candidates or hand-compute overlap wastes the human on work code can do.

### Tradeoffs

Per-candidate approval adds latency; batching approvals in one report-review session amortizes it. The 80% universality bar will occasionally reject something you later want — that's what `deferred` + `review_after` is for.

### Where I'd diverge / least sure

The 80% bar and the all-three-conditions template test are judgment calls I'd defend but can't prove; the honest version is "start strict, loosen with evidence, never the reverse" — you can always promote a plugin capability into the template later, but evicting something from the template breaks every adopted repo. I'm also unsure how much the judged report benefits from a second model pass on *every* candidate vs only on template routes; I've scoped Codex to template routes to control cost, but that scoping is a guess.

---

## E. mvp-plugin structure review

### Recommendation

**Keep copy-on-adopt as the architecture. Fix its one real weakness — blind-overwrite updates — with a manifest-stamped three-way update** (vendored-dependency-with-lockfile pattern). Do not move to plugin-native or symlinks.

### Why copy-on-adopt survives the review

Evaluated against the four criteria:

| Criterion | Copy (today) | Plugin-native / reference | Symlink | Thin-adopt hybrid |
|---|---|---|---|---|
| Updatability | weak today → **fixed by 3-way update** | best (git pull) | good | mixed |
| Drift | real, but *detectable* (hash manifest) | none for core | none | split-brain |
| Per-repo customization | best — edit the files | poor (fork the plugin) | poor | confusing (which layer?) |
| Dual-tree (.codex) burden | symmetric — both trees are real files | **broken: Codex CLI has no plugin system** — `.codex` must be copied regardless | breaks on Windows / for collaborators | asymmetric: claude in plugin, codex copied → check-sync now compares across *mechanisms* |

The decisive facts:

1. **The `.codex` tree can never be plugin-native.** Codex has no plugin/marketplace mechanism; its harness must be real files in the repo. Any reference-not-copy design only dedups the Claude half and makes the two halves structurally different — which directly worsens the dual-tree maintenance burden the design is graded on. Copy-on-adopt is the only architecture where both trees are the same kind of thing, which is what lets `check-sync.sh` exist at all.
2. **Collaborators and CI get the harness from `git clone` with zero setup.** A plugin-native repo is half-configured for anyone without the marketplace installed. Repo-owned files are also auditable and reviewable — a real property for a harness that instructs agents.
3. Per-repo customization is a first-class need (the `project/` overlay concept already exists); copy is the only model where customizing doesn't mean forking the plugin.

### The fix: three-way update

**Verified problem:** `install-harness.sh` preserves only the user-owned allowlist; every other existing core file is overwritten (`cp -p` in the copy loop, ~lines 37–41). If a repo tweaked a shipped skill, `/mvp-plugin:update` silently reverts it.

**Design:**

- `build-template.sh` additionally emits `template/harness-manifest.json`: `{template_version, mvp_harness_sha, files: {"<relpath>": "sha256", …}}` covering both trees + root files. `install-harness.sh` copies it to `.claude/harness-manifest.json` in the adopted repo.
- `/mvp-plugin:update` becomes a three-way compare per file — **base** = hash in the adopted repo's stamped manifest, **local** = file on disk, **new** = incoming template:
  - local == base (untouched) → update silently;
  - local != base, new == base (only local changed) → keep, list as "local customization retained";
  - local != base, new != base → **conflict**: keep local, write `<file>.template-new` alongside, list for agent-assisted reconciliation (`/mvp-plugin:update` ends by offering to walk the conflict list — merging prose skills is judgement work, i.e. model work);
  - file absent locally but in base (deliberately deleted) → respect the deletion, list it.
- Then re-stamp the new manifest. `doctor.sh` gains a free "local drift vs manifest" section (same comparison, report-only).
- **Local-extension convention**, documented in the adoption report: `.claude/skills/local/**`, `local-*`-prefixed commands, and the `project/` overlay are never touched by update — giving repos a guaranteed-safe place to extend, which shrinks the conflict surface to genuine forks of shipped files.

This is ~100–150 lines added to existing scripts, no architectural change, and it converts the drift criterion from "unknown and silent" to "enumerated at every update and doctor run."

### Alternatives explicitly rejected

- **Symlink:** breaks on Windows, breaks for every collaborator without the plugin at the same path, invisible to review. No.
- **Template-as-plugin:** that is what mvp-plugin already *is* — a plugin whose payload is the template; restating it adds nothing.
- **Selectable install profiles** (prior art: everything-claude-code's `manifests/install-modules.json`): defensible at their scale (183+ capabilities, 4+ tool targets), YAGNI at ours (121 files, 15 skills, 2 targets). Note it in the ledger as *deferred*, revisit if the template triples.

### Where I'd diverge / least sure

Least sure about conflict UX: line-based three-way merge on markdown prose is mediocre, which is why I keep conflicts as "retain local + drop `.template-new` + agent-assisted walk" rather than attempting automatic merges. Also mildly unsure whether `template_version` should be semver or just monotonic + `mvp_harness_sha`; I'd start with the SHA (it's free and unambiguous) and add human-facing versioning only if adopted repos need to communicate about it.

---

## F. Orchestration surface

### Recommendation

**One script, two commands, one skill, one rule, one hook — all in the coding-ritual root, none in the template.** Beads is the queue; reports are committed artifacts.

| Artifact | Path | Role |
|---|---|---|
| Scanner | `scripts/harness_lifecycle/scan.py` (stdlib-only) | deterministic core: `scan`, `drift`, `gap`, `status`, `nudge` |
| `/harness-status` | `.claude/commands/harness-status.md` | fetch + one-liner per repo (area C) |
| `/harness-scan [repo]` | `.claude/commands/harness-scan.md` | full pipeline: manifests → drift+gap reports under `harness_lifecycle/reports/<repo>/` → `bd create` one issue per material candidate (label `harness-candidate`, body links the report section) |
| `harness-evaluate` skill | `.claude/skills/harness-evaluate/SKILL.md` | the judgement half (area D): picks up a candidate bead, produces the comparison report + route proposal; on approval, executes the route end-to-end — including the [5] sync-back checklist for template routes (edit `.claude` **and** `.codex` in coding-ritual → `check-sync.sh` → `build-template.sh` → plugin tests → commit in mvp-harness → bump submodule pointer → ledger entry → close bead) |
| Rule | `.claude/rules/core/04-harness-lifecycle.md` (~10 lines) | invariants: never edit `template/` directly (always via build-template); no adoption without a ledger entry; scans never move submodule pins; borrow the smallest durable pattern; template routes require Codex critique |
| Hook | SessionStart nudge in root `.claude/settings.json` | staleness one-liner (area C) |

**Two prerequisites, do them first:**

1. **Template-leak guard:** extend `build-template.sh` with a curation-only exclusion list (e.g. `scripts/template-excludes.txt` fed to rsync `--exclude-from`) covering `skills/harness-evaluate/`, `commands/harness-*`, `rules/core/04-harness-lifecycle.md` — and while there, the stale `refresh-harness-from-reference` skill. Add a leak self-check for `harness_lifecycle` strings alongside the existing checks (build-template.sh step 6). Without this, the lifecycle machinery ships to every adopted repo, where it is meaningless.
2. **Discoverability:** one pointer line in `.claude/project/docs-index.md` and a short `harness_lifecycle/README.md` (what each file is, who writes it) — per the knowledge-discoverability rule.

Deliberately **not** building: a `/harness-adopt-capability` command separate from the skill (the skill's follow-through covers it); a web dashboard; auto-PRs; any scheduler. Every additional surface item is context-window tax on every future session in this repo.

### Rationale

The lifecycle is curation-repo-specific — it must live in coding-ritual root and be firewalled out of the payload. Two commands split the cheap/frequent action (status) from the expensive/occasional one (scan). One skill keeps all judgement in one place with beads as its inbox, matching the repo's existing pattern (work-state anchored in beads, session-completion protocol in `.beads/beads.md`).

### Where I'd diverge / least sure

Whether evaluate-and-route should be one skill or two (`harness-evaluate` proposes; `harness-integrate` executes). One skill with an explicit internal approval gate is fewer moving parts; split it only if the follow-through grows past what one SKILL.md can hold clearly. I lean one-skill and am ~70/30 on it.

---

## Cross-cutting recommendations

1. **Dedupe before you diff.** The single highest-leverage design fact found: 457 skill files = 183 logical capabilities. Any design that diffs files instead of capabilities starts 2.5x noisier than necessary and misjudges the scale problem entirely (hashing was never the bottleneck; attention is).
2. **The ledger is the loop's memory.** Detect/evaluate/route is stateless nagging without a persisted record of *decisions* (including rejections). It also unlocks the highest-value alert — "upstream improved something we adopted" — via `source_sha` provenance.
3. **Code/judgement split, strictly.** Scanner, hashing, thresholds, three-way file compare: code. Materiality of a shortlisted diff, better-than-mine verdicts, prose merges: model. This is the repo's own rule 5 applied to its own tooling.
4. **Everything is O(delta), never O(corpus).** Fetch → `git diff --name-status` → re-hash changed files only → LLM only on the material shortlist. The 457-skill repo costs the same as the 14-skill repo except on the first scan.
5. **Reuse existing idioms:** check-sync's directive manifest + normalized-hash baseline is the house style for "declared intentional differences + accepted state" — the alias table and ledger deliberately rhyme with it.
6. **Guard the payload boundary.** Two verified leak paths (lifecycle surface into template; blind-overwrite updates) are both boundary failures. The template-excludes list and the stamped harness-manifest are the same idea pointed in both directions: make the boundary explicit and machine-checked.

## Top 3 things I'd do first

1. **Scanner + manifests + drift report** (`scan.py scan|drift` + `scan-config.yaml`), validated on `superpowers` (small, clean) then `everything-claude-code` (the dedupe/scale test — success = 183 logical capabilities, first drift report with a material/minor split that survives eyeballing). Include the `build-template.sh` exclusion-list fix in the same change so the lifecycle surface never ships.
2. **Adoption ledger + gap report vs mvp-harness** (`scan.py gap` + `aliases.yaml` + `ledger.yaml` + beads wiring in `/harness-scan`) — this turns raw detection into a curation queue and makes the loop idempotent from day one.
3. **Manifest-stamped three-way `/mvp-plugin:update`** (area E) — independent of 1–2 and fixes the only verified silent-data-loss behavior in the current system (core-file clobbering on update). Ship the local-extension convention with it.
