# mvp-plugin Architecture — Dedicated Standalone Review Synthesis

Focused review of *only* the mvp-plugin distribution/adoption structure by two
independent xhigh researchers ([Fable-5](mvp-plugin-architecture-fable5.md),
[GPT-5.5](mvp-plugin-architecture-gpt55.md)). This is the dedicated standalone the
original plan parked; the earlier treatment was one area of a combined brief.

## Verdict: KEEP copy-on-adopt (A) — both agree, from first principles

Both rank **A (copy-on-adopt + three-way merge) as the default**, with **D (hybrid:
copy the core, ship optional/heavy capabilities as plugins) as a documented future
option, not a replacement**. Fable's ranking: **A > D > B >> C ≈ E >> F**. Reject
plugin-native (B), template-as-plugin (C), dependency/submodule (E), symlink (F) as
defaults.

**Key reframe — the original decisive premise is stale but the conclusion holds.**
"Codex has no plugin system" is now **false**: `codex plugin` exists in codex-cli
0.142.2 (verified). But copy-on-adopt still wins on the *durable* constraints:

1. **The Codex + root-file half can only ever be repo files.** ~57% of the payload
   is the `.codex` tree, plus `CLAUDE.md`/`AGENTS.md`/`settings.json`/`rules/` — none
   of which any plugin system (Claude or Codex) can distribute. So B/C/D delete no
   machinery; they add a *second* channel with its own version axis. C is
   unimplementable for ~60% of the payload.
2. **Use-time parity.** One `/update` moves both `.claude` and `.codex` atomically
   under one manifest (check-sync-guarded). Plugin-native pins `.codex` in the repo
   while `.claude` behaviour is whatever plugin version the machine serves →
   invisible skew exactly at the point of use.
3. **Clone-only onboarding + PR-reviewable harness.** Collaborators / CI / containers
   / Codex-only teammates get everything from `git clone`; each repo pins its harness
   version in git; every harness change is an ordinary reviewable diff. Plugins
   convert zero-step clone into per-seat install + trust prompt + network, and lose
   per-repo pinning and the PR audit trail.

**The system is already the right A+D hybrid:** `code-intel` and `codex-adapter`
distribute dependency-bearing optional capabilities as sibling plugins; only the
universal core is copied. Keep that line — do **not** move core skills into plugins.
D's "thin bootstrap" isn't thin (CLAUDE.md/AGENTS.md/rules/settings/hooks/overlay/
`.codex`/beads all stay copied — only skills/agents/commands/docs could move), it
breaks per-repo skill customization (plugin skills are namespaced/read-only), and it
*worsens* dual-tree divergence. Revisit triggers: Codex gains a full plugin surface,
Claude adds per-repo plugin version pinning, or fleet size makes pull-based `/update`
the dominant cost.

## Must-fix smells (verdict-independent), ranked
| # | Sev | Smell | Source | Verified |
|---|---|---|---|---|
| 1 | HIGH | **check-sync.sh is broken:** `sync-manifest.txt:45` still declares the `ak-guide/SKILL.MD` pair; the file was renamed to `SKILL.md`, so check-sync exits 2 (`can't read …SKILL.MD`). Regression from the ak-guide typo fix. | GPT-5.5 | ✅ exit 2 |
| 2 | HIGH | **Untouched core files never update:** `hp_is_user_owned` short-circuits before the three-way merge, so `CLAUDE.md`/`AGENTS.md`/`settings.json`/`config.toml` never receive upstream changes even when unmodified (e.g. new hook wiring can't propagate). Fix: shrink user-owned to the overlay (`project/*`) only; the merge already protects edits. | Fable S1 | ✅ code |
| 3 | MED | **Stale plugin docs:** README / `plugin.json` still imply a bundled/vendored `codex-adapter` ("two plugins"); the marketplace now has 3 sibling plugins. The `docs/usage` run-tests caveat is also stale. | both | ✅ |
| 4 | MED | **Thin update-path test coverage:** `run-tests.sh` covers local-edit-kept but not both-changed `.template-new`, orphan-retire, modified-retired, or the broken sync-manifest. (A standalone reviewfix test covers these but isn't in the committed suite.) | both | ✅ |
| 5 | MED | **`.harness-manifest.txt` commit requirement is undocumented** (it's the merge base for collaborators' future updates); **doctor** doesn't flag lingering `*.template-new` or "update available" (stamp vs plugin manifest — the cheap cure for copy-on-adopt's silent-staleness). | Fable S3 | — |
| 6 | ? | **Possible: dot-less `template/claude/skills/*` still discovered** as directory-scoped skills by Claude Code (Fable observed `…/template:*` duplicates in a subagent session) — would mean the dot-less refactor is incomplete. **Needs verification in a clean session.** | Fable S2 | ⏳ |
| 7 | LOW | build-template `orchestrators→upstream` sweep is a blunt token replace (latent corruption); `beads.md` delivery gated on `bd` presence; build-template treats sync drift as advisory (a broken checker slips through). | both | — |

## Bottom line
The architecture question is **settled with fresh eyes: keep copy-on-adopt.** The
review's real value was (a) correcting the stale "Codex can't plugin" premise while
confirming the conclusion on durable grounds, and (b) surfacing 5–7 concrete
implementation smells — two of them (check-sync regression, silent core non-update)
worth fixing now.
