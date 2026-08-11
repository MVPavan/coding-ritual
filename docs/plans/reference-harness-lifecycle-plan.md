# Reference-Harness Lifecycle — Plan & Research Brief

**Status:** implemented and verified 2026-07-03 (P0-P4); live sweep and capability reviews completed through 2026-07-10. Seventh reference harness added 2026-07-15.
**Owner:** coding-ritual harness.

## Purpose

coding-ritual curates external agent harnesses (`reference_harnesses/*`, git
submodules) and distills the best of them into a reusable, installable harness
(the `mvp-harness` marketplace + `mvp-plugin`'s adopted template). We want a
repeatable **lifecycle**:

```
 reference_harnesses/<upstream>   (git submodules, pinned SHAs)
         │
  [1] DETECT   what is new / materially changed — signal over cosmetic noise
         ▼
  [2] EVALUATE each change against mvp-harness — new capability? overlap? better?
         ▼
  [3] ROUTE    → mvp-plugin/template  |  new plugin  |  merge into existing plugin
         ▼
  [5] SYNC-BACK (if → template): edit .claude + .codex source, check-sync, build-template, bump submodule
```

Separate, standalone: **[4]** review whether `mvp-plugin`'s
*install-once → adopt → copy template into repo root* architecture is the best
structure, or whether a better one exists.

This document scopes the lifecycle and drives **independent design research**
before any implementation.

## Current state (fresh start — prior tooling is out of scope)

- **7 reference-harness submodules** (pinned SHAs), capability counts ranging from
  ~14 skills (superpowers) to **457 skills** (everything-claude-code). Scale matters.
- **`mvp-harness`** submodule = marketplace; plugins: `mvp-plugin`, `code-intel`, `codex-adapter`.
- **`mvp-plugin`**: install once per machine → `/adopt` copies the `template/`
  payload (stored dot-less `claude/ codex/ beads/`) into a target repo's root as
  `.claude/ .codex/ .beads/`. `build-template.sh` + `check-sync.sh` already
  maintain the claude↔codex dual payload. **The [5] sync-back half already works.**
- **Deliberately ignored (stale, pre-restructure):** `inventory_harness_repo.py`,
  the `refresh-harness-from-reference` skill, and the deleted
  `project_agnostic_claude_setup/`. Design fresh; do not build on these.

## Open design areas (A–F) — the questions research must answer

**A. Change detection.** What is the best mechanism to detect *meaningful* new or
changed capabilities (skills, commands, agents, MCP servers, hooks, rules) across a
set of git-submodule reference harnesses, while filtering cosmetic noise
(reformatting, version bumps, typo fixes)? What is the right *unit* of change? How
should state be persisted (what file/format), and how does it scale to a 457-skill
repo? Candidate approaches to evaluate and improve on (non-exhaustive): a
persisted capability manifest with content hashing + a "materiality" filter; pure
git (`diff`/`log`/`notes`); off-the-shelf diff/inventory tooling.

**B. Two comparison axes.** Distinguish (a) *upstream drift* — pinned submodule SHA
→ upstream HEAD ("what did the author add since I pinned") — from (b) *capability
gap vs my harness* — reference capabilities vs mvp-harness capabilities ("what do
they have that I don't, or better"). Should these be one engine with two reports?
What is best practice for cross-repo capability comparison?

**C. Trigger & cadence.** Manual command vs scheduled polling (cron) vs git hooks.
Submodule upstreams do not notify. What is the pragmatic best practice for keeping
"what's new" current without babysitting it?

**D. Evaluate + route.** Given a detected new/changed capability, how should an
agent (a skill/command) evaluate it against the existing harness and decide:
fold into mvp-plugin's adopted template / make a new standalone plugin / merge into
an existing plugin? What rubric distinguishes "common setup for ~every repo"
(→ template) from "distinct standalone capability" (→ its own plugin, e.g.
codex-adapter, code-intel)? How much automation vs human-in-the-loop? What does a
useful "is theirs better than mine" comparison report contain?

**E. mvp-plugin structure review (the separable [4]).** Is *install once → adopt →
copy the whole template into the target repo's root* the best architecture for a
reusable, **updatable** harness? Evaluate alternatives — reference-not-copy
(plugin-native / symlink), a thin adopted layer + plugin-provided skills,
template-as-plugin, others — against: updatability, drift, per-repo
customization, and the claude/codex dual-tree maintenance burden. Recommend.

**F. Orchestration surface.** What minimal set of skills / commands / rules should
live in the coding-ritual **root** harness to drive this lifecycle end to end?

## Method

Two independent researchers, **same brief, no cross-talk**, then I synthesize and
you approve:

- **Fable-5 @ xhigh** (subagent) → `docs/research/harness-lifecycle/harness-lifecycle-fable5.md`
- **GPT-5.5 @ xhigh** (Codex `research` role, web search on) → `docs/research/harness-lifecycle/harness-lifecycle-gpt55.md`
- **Synthesis** (agreements, conflicts, my recommendation) → `docs/research/harness-lifecycle/harness-lifecycle-synthesis.md`
- → your decision → phased build tracked in beads.

Each researcher answers areas A–F with, per area: a concrete recommendation,
rationale, tradeoffs, a rough implementation sketch, and an explicit "where I'd
diverge / what I'm least sure about."
