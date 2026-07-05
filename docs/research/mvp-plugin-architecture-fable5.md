# mvp-plugin Distribution/Adoption Architecture — Decision Review (Fable 5, xhigh)

**Question.** Is "install the plugin once per machine → `/adopt` copies the template into a repo's
root → `/update` three-way merges" the right distribution/adoption architecture, or should it change?

**Verdict: KEEP — Architecture A (copy-on-adopt + manifest-stamped three-way merge), with one
boundary endorsement and a short must-fix list.** The endorsement: the system is already a
disciplined A+D hybrid — dependency-bearing/optional capabilities (`code-intel`, `codex-adapter`)
are distributed as sibling plugins, only the universal core is copied. That boundary is correct and
should be kept explicit. Do **not** move the core `.claude` half into the plugin.

Everything below was verified against the real files (paths cited inline), not taken from the
prior synthesis on faith. Ranked outcome: **A (keep) > D (hybrid, already partially realized;
would lose use-time parity if pushed further) > B (plugin-native) >> C ≈ E >> F.**

---

## 1. Constraint verification

| # | Claimed constraint | Verified? | Evidence |
|---|---|---|---|
| 1 | Codex CLI has no plugin system → `.codex/` must be real repo files | ✅ holds | No Codex plugin/marketplace mechanism exists; the template ships a full 69-file `.codex/` tree (`template/codex/`, counted) with its own `config.toml`, TOML agents, Python hook. Nothing in any candidate architecture can serve these except files in the repo. |
| 2 | Collaborators get the harness via `git clone`, no per-machine install | ✅ holds under A | The payload (49 `.claude` + 69 `.codex` + `CLAUDE.md`/`AGENTS.md`/`beads.md` = 121 files, `template/harness-manifest.txt` has 122 entries incl. header) lands as ordinary committed files. Only the *adopter* needs the plugin; collaborators need only the external CLIs (`bd`, optionally `codex`). Note: repo-level `.claude/settings.json` **can** declare `extraKnownMarketplaces` + `enabledPlugins` (verified in `reference_harnesses/claude-code-best-practice/best-practice/claude-settings.md:421-460`), so B/D are *feasible* for teams — but via a per-seat network fetch + trust prompt, not via clone. |
| 3 | Per-repo customization expected | ✅ holds | `hp_is_user_owned` (`scripts/lib/common.sh:35-42`) protects the overlay + root files; the three-way merge (`install-harness.sh:42-66`) preserves local edits to *core* files too. Plugin-served skills are namespaced and read-only — no transparent per-repo override exists in the plugin model. |
| 4 | Non-destructive updates | ✅ implemented | Base/local/new per-file hash merge, conflicts → `<file>.template-new` (`install-harness.sh:57-66`); orphan-retire only deletes files whose local hash equals the old base (`:154-169`). The silent-overwrite bug flagged in `harness-lifecycle-synthesis.md` is fixed. Coverage gap noted in §5 (S6). |
| 5 | Cross-platform / containers / trust | ✅ favors copy | Copied files work in any container/CI with no marketplace access and no symlink semantics; bash installer needs Git-Bash/WSL on Windows but only at adopt/update time, on the adopter's machine. |
| 6 | Dual `.claude`+`.codex` maintenance burden is real | ✅ real, and **architecture-independent** | The trees diverge by design (TOML vs MD agents, bash vs Python hook, Codex-only skills); `check-sync.sh` guards drift with a normalized-hash baseline. Crucially: no candidate architecture removes this burden — it is a *maintainer-side* cost, and only the Claude half could even theoretically move to a plugin. |

**Also verified:** the Claude Code plugin component model is commands/agents/skills/hooks/MCP
servers only (`reference_harnesses/claude-plugins-official/plugins/example-plugin`,
`plugin-dev/skills/plugin-structure`). Plugins **cannot** ship `CLAUDE.md`/`AGENTS.md`, `.claude/rules/`,
`.claude/settings.json`, or any always-loaded root context as repo files. This single fact guts
architectures B and C: the "thin bootstrap" they promise is not thin (see §3).

---

## 2. The three decisive reasons to keep A

### R1 — The Codex constraint makes the copy machinery non-optional; plugin-native only *adds* a channel

57% of the payload by file count (69 of 121, plus the three root files) is the `.codex` half and can
only ever be repo files. Every alternative that moves the `.claude` half elsewhere still needs:
the installer, the manifest stamp, the three-way merge, the orphan-retire, the overlay skeletons,
beads init — the entire `install-harness.sh` machinery — for the Codex half. So B/C/D never
*delete* complexity; they add a second distribution channel (marketplace) on top of the first
(copy), each with its own version axis, failure modes, and docs. A is the only architecture where
one mechanism updates everything.

### R2 — Use-time parity between the two trees is a core product property, and only A preserves it

The harness's promise is "the same ritual in both CLIs." Today that parity is enforced at build
time (`check-sync.sh`, normalized-hash baseline) and shipped **atomically**: one `/update` run
moves `.claude` and `.codex` together, stamped by one manifest. Under B/D, the `.codex` tree is
pinned by the repo's git history while the `.claude` behavior is whatever plugin version the
machine happens to serve — the two halves *will* skew (repo at Codex-v1, machine at Claude-v4),
per machine, invisibly, with no artifact to diff. The check-sync guarantee would hold in the
maintainer's build and evaporate exactly where it matters: at the point of use. This is the
strongest single argument and it is structural, not incidental.

### R3 — Clone-complete repos localize install burden to the adopter role and keep harness changes PR-reviewable

Under A, exactly one person per repo ever needs the plugin (whoever runs `/adopt` / `/update`).
Every collaborator, CI job, container, and air-gapped environment gets a working harness from
`git clone` — including Codex-only teammates who never touch Claude Code. Every harness change
arrives as an ordinary reviewable diff in the repo's PR flow, and each repo pins its own harness
version implicitly in git. Under B/D, every seat needs the plugin (via `extraKnownMarketplaces`
trust-prompt + network fetch), per-repo version pinning is lost (plugin version is per-machine),
and harness behavior changes ship silently machine-wide on marketplace update with no PR trail.
For an audit-conscious team, A's property — "the agent's operating rules are exactly what's
committed" — is the better trust model.

**The honest costs of A** (accepted, with mitigations in §5): (a) updates are pull-based and
silent — adopted repos rot until someone runs `/update` (fix: cheap "update available" doctor
check, S3); (b) fleet drift is unbounded — every repo may fork every file (this is constraint 3
working as intended; fleet coherence is not a stated goal); (c) a ~120-file diff lands in the
adopted repo (one-time; it is precisely what buys R3).

---

## 3. Per-architecture comparison

Criteria: **U** updatability & drift · **C** per-repo customization · **G** collaborator
`git clone` (no install) · **X** Codex-no-plugins reality · **M** maintenance burden (dual tree) ·
**S** template⊂root invariant · **I** install friction · **N** non-destructive update ·
**P** cross-platform/container/trust. (`++` strong, `+` ok, `−` weak, `‑‑` breaks.)

| Arch | U | C | G | X | M | S | I | N | P | Bottom line |
|---|---|---|---|---|---|---|---|---|---|---|
| **A. Copy-on-adopt + 3-way (current)** | + (pull-based; silent staleness) | ++ (edit the file; merge keeps it) | ++ (clone-complete) | ++ (same mechanism both halves) | = (dual tree unchanged; one build, one payload) | ++ (enforced by `template-exclude.txt` + leak check) | + (plugin only for adopter) | ++ (implemented, hash-based) | ++ (plain files everywhere) | **Keep** |
| **B. Plugin-native (repo = overlay + `.codex` only)** | ++ for Claude half / − for Codex half (skew) | ‑‑ (plugin skills namespaced, read-only) | − (per-seat trust prompt + network) | − (copy machinery survives for 57% of payload) | worse (two channels, two version axes) | n/a→harder (three representations) | − (every seat installs) | + (Claude half) / + (Codex half keeps merge) | − (containers/CI need marketplace access) | Breaks parity + customization |
| **C. Template-as-plugin (no copy)** | ++ | ‑‑ | ‑‑ | ‑‑ (cannot ship `.codex`, `CLAUDE.md`, rules, settings at all) | worse | n/a | − | n/a | ‑‑ | **Not implementable** for ~60% of payload; collapses into D at best |
| **D. Hybrid (thin bootstrap + plugin skills)** | ++ for moved skills / − skew vs `.codex` twins | − for moved skills | − (plugin needed for core behavior) | − (bootstrap is not thin: CLAUDE.md, AGENTS.md, rules/, settings, hooks wiring, overlay, `.codex`, beads all stay copied — only skills/agents/commands/docs move) | worse for core (root tree + plugin + adopted copies); **right for optional deps** | harder (invariant now spans a second artifact) | − | mixed | − | **Reject for core; already correctly applied to `code-intel`/`codex-adapter`** |
| **E. Submodule / subtree / package** | + (real git merges) | − (edits = commits in a foreign repo) | − (`--recurse-submodules` friction; detached-HEAD confusion) | ‑‑ (`.claude`/`.codex`/`CLAUDE.md` must sit at repo root; a generated, genericized payload isn't a stable upstream; multi-prefix subtree impossible for root files) | worse (must publish a built template repo artifact) | + | − | + | − (Windows/submodule UX; package managers wrong for arbitrary-language repos) | Structurally misfit |
| **F. Symlink / central store** | ++ (instant) | ‑‑ (edits hit every repo) | ‑‑ (dangling links after clone) | ‑‑ | = | + | − | ‑‑ (no merge concept) | ‑‑ (Windows symlink privileges, container mounts, per-machine state) | Dead on arrival vs constraints 2/3/5 |

### Where each alternative breaks, concretely

- **B/D:** `CLAUDE.md`'s read-order references `.claude/rules/*` and un-namespaced skills; the
  Codex twin keeps local un-namespaced skills. Moving Claude skills to a plugin forces namespaced
  invocation (`/mvp-plugin:phase-execution`) on one side only — the *texts* of the two trees, kept
  deliberately near-identical today (that's what `check-sync.sh` compares), must now diverge
  structurally. The dual-tree burden constraint 6 worries about gets **worse**, not better.
- **C:** cannot exist. Plugins have no mechanism for `.codex/`, root `CLAUDE.md`/`AGENTS.md`,
  `rules/`, or `settings.json` hook wiring (verified component model, §1). At least ~60% of the
  payload has no plugin representation.
- **E:** a submodule/subtree needs a stable upstream repo, but the payload is a *build artifact*
  (genericized, token-swept, curation-excluded — `build-template.sh:51-138`). You'd have to publish
  the built template as its own repo, then still handle root-file placement (`CLAUDE.md` can't live
  in a subtree prefix), two prefixes (`.claude`, `.codex`), and the overlay living *inside* the
  dependency-owned tree. Local skill edits become commits against a foreign remote. Every axis of
  friction increases; the only gain (line-level git merges) is achievable within A (§5, S3-adjacent).
- **F:** breaks Windows (symlink privilege), containers (host path not mounted), collaborators
  (link target absent after clone), and per-repo customization (central edits are global). Nothing
  survives contact with constraints 2/3/5.

### When to revisit (falsifiable triggers)

Flip toward D only if **(a)** Codex ships a first-class plugin/extension system with parity
semantics (kills R1/R2 asymmetry), or **(b)** Claude Code adds per-repo plugin *version pinning*
committed to the repo (restores R3's pinning), or **(c)** the fleet of adopted repos grows to the
point where "run `/update` in N repos" is the dominant cost and fleet coherence becomes a stated
goal (then a marketplace-pushed core beats N pull-based merges). None hold today.

### Counterfactual migration path (if D were chosen later) — cost/risk for completeness

1. Extract `template/claude/{skills,agents,commands,docs}` into a `core-workflows` plugin in
   `mvp-harness`; keep everything else copied. 2. Rewrite `CLAUDE.md`/read-order and all
   cross-skill references to namespaced forms; leave `.codex` twins un-namespaced. 3. Ship
   `extraKnownMarketplaces` + `enabledPlugins` in the template `settings.json`; handle offline/
   declined-trust degradation. 4. Teach `/update` to *retire* the previously copied skills
   (three-way retire already handles unmodified ones; locally-edited copies conflict — an agent-led
   reconcile per repo). 5. Re-point `check-sync.sh` at plugin-vs-`.codex` and accept permanent
   structural asymmetry. Estimate: several days of build + doc + test churn, an ongoing second
   release channel, and a per-repo migration with human review. Benefit: faster Claude-half
   updates only. **Cost/benefit is clearly negative today.**

---

## 4. Fresh-eyes note on the prior decision

The synthesis (`docs/research/harness-lifecycle-synthesis.md`, §E) resolved the Fable/GPT-5.5 fork
as "copy + three-way for core; standalone plugins for heavy/optional." Re-deriving from the
constraints with the *built* system in hand, that resolution is confirmed — and both prerequisites
it demanded are verifiably implemented: the curation-leak exclusion (`scripts/template-exclude.txt`,
enforced at `build-template.sh:57-67` with leak backstops at `:141-160`) and the three-way
`/update` (`install-harness.sh:33-66,149-170`). The one place the prior treatment now reads stale:
its "dot-less storage avoids skill scanning" premise no longer holds (S2 below).

---

## 5. Smells worth fixing regardless (ranked)

**S1 — MUST-FIX: the blanket "user-owned" skip defeats the three-way merge for the files where
updates matter most; docs contradict code.** `hp_is_user_owned` (`lib/common.sh:35-42`) short-circuits
*before* the merge (`install-harness.sh:51`), so `CLAUDE.md`, `AGENTS.md`, `.claude/settings.json`,
`.codex/config.toml`, `.codex/hooks.json` **never receive upstream updates — even when locally
untouched**. Yet `commands/update.md:6-8` claims `/update` refreshes "…hooks, docs,
`CLAUDE.md`/`AGENTS.md`". Concrete trap: upstream adds a hook — the script lands (new file →
copied) but its `settings.json` wiring never propagates; `doctor.sh:29` still passes because it
only greps for the string `hooks`. The pre-three-way rationale ("never clobber what the owner
customises") is now obsolete: the merge already keeps local edits and flags conflicts. **Fix:**
shrink the user-owned set to the overlay (`.claude/project/*`, `.codex/project/*`) and route the
root/config files through the normal three-way path. Bonus: on fresh adopt into a repo with a
pre-existing `CLAUDE.md`, today the harness guide is silently never delivered; under three-way it
lands as `CLAUDE.md.template-new` for a deliberate merge. ~10 lines in `common.sh` + doc updates.

**S2 — MUST-FIX: the dot-less-template trick is defeated by current Claude Code skill discovery.**
`README.md:85-93` and `docs/usage/mvp-plugin.md:169-174` justify dot-less storage as preventing the
source repo's Claude Code from scanning `template/.claude/skills`. Observed live in this repo's
sessions: the template's skills surface as directory-scoped duplicates
(`mvp-harness/plugins/mvp-plugin/template:beads`, `…:brainstorming`, — 15 of them), because current
Claude Code discovers `{.claude|claude}/skills/*/SKILL.md` anywhere in the worktree. Cost: skill-list
noise + context burn in every maintainer session, and triple listings (root harness + template copy +
reference-harness copies). **Fix:** rename the stored dir to something discovery won't match (e.g.
`template/claude/skills__tpl/` or `payload-claude/`), map it back in `hp_to_dotted`/`build-template.sh`/
`check-sync.sh` defaults; handle old stamp keys on read (one-line normalization) so existing adopted
repos don't see spurious conflicts. Bounded: ~20–30 lines across three scripts.

**S3 — Update lifecycle is invisible: no staleness signal, no conflict surfacing, no stamp guidance.**
(a) Nothing tells the adopter that `.harness-manifest.txt` **must be committed** — it is the merge
base; without it on a collaborator's clone, the next `/update` degrades every changed file into a
conflict. Not mentioned in `adopt.md`, the skill, or the report. (b) `doctor.sh` doesn't flag
lingering `*.template-new` files (unresolved conflicts rot silently, and they aren't gitignored —
they'll get committed). (c) `doctor.sh` could diff the repo stamp against the installed plugin's
`template/harness-manifest.txt` and print "harness update available (N files)" — the cheap fix for
A's biggest weakness (silent staleness). All three are small `doctor.sh`/docs additions.

**S4 — The genericization sweep is blunt and rename-stale.** `build-template.sh:128-137` rewrites
the common English word `orchestrators` → `upstream` (case-insensitive, all payload files) — any
future generic skill prose using the word gets silently corrupted, and no leak check can catch it
(the output is the sanctioned token). Currently no collateral hit (verified: only singular
"orchestrator" appears in the payload), but it's a latent corruption vector. Post-rename drift:
the sweep still targets `/data/codes/orchestrators` while the repo is `coding-ritual`; the token
`coding-ritual` is neither swept nor leak-checked (the `/data/codes` grep at `:156` is the only
backstop). Fix: maintain the token list as data with a "does the source still contain this token?"
sanity check, and prefer path-anchored patterns over bare English words.

**S5 — `beads/beads.md` delivery is gated on `bd` being installed.** The policy doc is copied inside
the `command -v bd` branch (`install-harness.sh:124-138`); a repo adopted on a bd-less machine gets
no beads policy even though `CLAUDE.md` points at it. Move the `copy_one "beads/beads.md"` out of
the branch. Two lines.

**S6 — The three-way merge's hard paths are untested.** `test/run-tests.sh:59-65` covers only
"local edit kept". Untested: the conflict path (`.template-new` created, counted, reported), the
untouched-file upgrade path (local==base → overwritten), orphan-retire (clean delete vs
modified-kept), and stamp advancement across two payload versions. These are exactly the paths that
protect user data; simulate a v2 payload by mutating a copy of `template/` in the fixture.

**S7 — Documentation drift, two layers deep.** The plugin `README.md` still describes the
pre-restructure world (two-plugin marketplace, `vendor/codex-adapter/`, `…@mvp-plugin` install IDs —
`README.md:10-33,75`), which `docs/usage/mvp-plugin.md:298-313` duly flags — but that caveat list is
itself stale: caveat 2 claims `test/run-tests.sh` asserts vendored-adapter files; the current
`run-tests.sh` has no such section. One reconciliation pass over both files.

**S8 — Fresh adopt into a repo with an existing `.claude/settings.json` leaves hooks unwired with
only a WARN.** (`doctor.sh:31` says "merge the harness hooks in" — manually.) A deterministic
JSON hooks-block merge in the installer (python3 is already a dependency, see
`build-template.sh:84`) would close the gap; S1's three-way routing makes this mostly moot for
*updates* but not for first adopt into a repo with prior settings.

---

## 6. Summary

The two facts that decide this review: **(1)** the Codex half — the *larger* half — can never be
anything but copied files, so copy machinery is a fixed cost every alternative still pays; and
**(2)** the only mechanism that keeps the two trees at the same version at the point of use is
shipping them in one artifact through one update path. Copy-on-adopt with the manifest-stamped
three-way merge is therefore not a compromise; it is the architecture the constraints select.
The plugin layer is already used for exactly what it's good at — machine-level tooling
(`/adopt`/`/update`/`/doctor`) and dependency-bearing optional capabilities — and should go no
further. Fix S1 and S2 promptly (S1 is a live correctness gap in the update contract; S2 is a live
context leak), wire the S3 visibility checks, and this architecture is sound for the long haul.
