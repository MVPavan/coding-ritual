Direct answer: build a manifest-first lifecycle with one deterministic inventory/diff engine, two separate reports, and human-reviewed routing. Keep `mvp-plugin`’s copy/adopt flow for now, but evolve it toward a thin adopted repo layer plus versioned plugin-provided reusable capabilities. A good answer must cover unit of change, persisted state, scale, drift vs gap, cadence, routing rubric, update architecture, and the smallest root orchestration surface.

**Observed Baseline**
Repo facts: the lifecycle brief defines A-F and says sync-back already works via `check-sync.sh` and `build-template.sh` ([plan](/data/codes/coding-ritual/docs/plans/reference-harness-lifecycle-plan.md:32)). The repo tracks six reference submodules plus `mvp-harness` ([.gitmodules](/data/codes/coding-ritual/.gitmodules:1)). `mvp-plugin` currently copies a dot-less template into `.claude/`, `.codex/`, and `.beads/`, then preserves overlays on update ([README](/data/codes/coding-ritual/mvp-harness/plugins/mvp-plugin/README.md:43), [install](/data/codes/coding-ritual/mvp-harness/plugins/mvp-plugin/scripts/install-harness.sh:29)). The marketplace has `mvp-plugin`, `code-intel`, and `codex-adapter` ([marketplace](/data/codes/coding-ritual/mvp-harness/.claude-plugin/marketplace.json:12)). I verified the scale: `everything-claude-code` has 457 `SKILL.md`, 291 command markdown, and 175 agent markdown files in this checkout.

External facts: Claude Code docs say standalone `.claude/` is best for project-specific customization, while plugins are best for shared, versioned, updatable extensions (https://code.claude.com/docs/en/plugins). Skills and legacy commands both create slash-command behavior, but skills are the recommended richer format (https://code.claude.com/docs/en/skills). Git submodules record a commit pointer, not full contents, and `git submodule update --remote` fetches upstream before calculating the new target SHA (https://git-scm.com/book/en/v2/Git-Tools-Submodules, https://git-scm.com/docs/git-submodule). GitHub scheduled workflows can poll, but may be delayed or dropped under load (https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule).

**A. Change Detection**
Recommendation: use a persisted capability manifest with normalized hashes. Git is the transport and provenance layer, not the semantic detector.

Unit of change: one logical capability: `skill`, `command`, `agent`, `mcp_server`, `hook`, `rule`, `plugin`, plus a containing `capability_group` when a folder only works as a bundle. Persist raw blob hash, normalized content hash, and semantic signature hash. The semantic signature should include name, description/trigger, frontmatter, tools/permissions, MCP server metadata, hook event/matcher, executable/script references, and dependency footprint.

Sketch:
- `schemas/reference-capability-manifest.v1.json`
- `state/reference-harness/manifests/<repo>/<sha>.json`
- `state/reference-harness/baselines.json`
- `scripts/reference_harness/inventory.py`
- `scripts/reference_harness/diff_manifests.py`
- report: `docs/research/reference-harness/<date>-drift.md`

Materiality filter: ignore whitespace, markdown wrapping, frontmatter key order, generated timestamps, obvious typo-only diffs, and unrelated version bumps. Flag changes to invocation, routing text, allowed/disallowed tools, MCP config, hook behavior, script bodies, agent role prompt, permission mode, dependencies, and file add/remove. For 457 skills, never stuff bodies into one prompt; inventory deterministically, then sample only changed candidates.

Tradeoff: normalization can hide meaningful prose edits if too aggressive. Keep raw diffs linked in every report.

Divergence / least sure: I would not start with embeddings as the detector. Use embeddings only as an analyst aid for “similar to our X,” not as persisted truth.

**B. Two Comparison Axes**
Recommendation: one inventory engine, two report modes.

Upstream drift compares `pinned_sha_manifest -> upstream_head_manifest`: “what changed upstream since our pin?” Capability gap compares `reference_manifest -> mvp_harness_manifest`: “what exists or is better there?” Keep these reports separate because one is time drift and the other is product fit.

Sketch:
- `reference-drift --repo everything-claude-code --from pinned --to origin/HEAD`
- `reference-gap --reference everything-claude-code --target mvp-harness`
- stable matching order: exact id/path, declared alias, normalized name+kind, then fuzzy category tags.
- report fields: capability, upstream provenance, local equivalent, novelty, overlap, materiality, risk, likely route.

Tradeoff: one engine reduces duplicated parsers, but report schemas must remain distinct or reviewers will confuse “new upstream” with “worth adopting.”

Divergence / least sure: cross-repo “better than ours” cannot be fully automated. The engine should shortlist; the agent should argue.

**C. Trigger & Cadence**
Recommendation: manual-first command, optional weekly scheduled poll, no git hooks for upstream detection.

Manual command should be the authoritative workflow because updates require judgment and submodule bumps. Add a weekly GitHub Actions or local cron poll that only opens/updates a Beads issue or report when material changes exist. Avoid top-of-hour schedules because GitHub documents delay/drop risk for high-load periods.

Sketch:
- `/reference-drift all`
- `scripts/reference_harness/poll_upstreams.sh`
- optional `.github/workflows/reference-harness-drift.yml` with `workflow_dispatch` and weekly `schedule`
- poll logic: read `.gitmodules`, `git ls-remote`, compare last checked remote SHA, fetch only changed repos, generate report, never bump submodule automatically.

Tradeoff: manual-only goes stale; scheduled-only creates noisy review debt.

Divergence / least sure: I would not use git hooks except for local validation before committing generated manifests. Hooks do not solve “upstream changed elsewhere.”

**D. Evaluate + Route**
Recommendation: deterministic pre-score, human-in-the-loop final route.

Routing rubric:
- Template: applies to almost every repo, low external dependency, small context footprint, safety/verification/workflow core, must exist in both Claude and Codex trees.
- New plugin: optional capability, external tool/MCP/bin dependency, domain-specific workflow, security-sensitive hook, or high context cost. This matches Claude’s plugin guidance for shared versioned extensions.
- Merge existing plugin: same job-to-be-done and same dependency boundary as `code-intel`, `codex-adapter`, or `mvp-plugin`.
- Reject/defer: giant catalogs, repo/org-specific assumptions, duplicate wording without behavioral gain, or capabilities that increase always-on load.

Comparison report should include: what theirs does, what ours does, exact files, trigger/invocation, dependencies, security/permission surface, context cost, update burden, Claude/Codex parity impact, testability, and a route recommendation with confidence.

Sketch:
- `.codex/skills/reference-evaluate/SKILL.md`
- `.codex/skills/reference-route/SKILL.md`
- `docs/research/reference-harness/evaluations/<capability-id>.md`
- optional Beads issue per accepted route.

Tradeoff: agents are good at explaining fit; scripts are better at repeatable extraction. Keep that split.

Divergence / least sure: I would force “why not reject?” into every evaluation. The obvious failure mode is importing impressive but unused workflow catalogs.

**E. mvp-plugin Structure**
Recommendation: evolve to “thin adopted layer + plugin-provided reusable core,” but do it gradually.

Keep copying repo-local essentials: `AGENTS.md`/`CLAUDE.md`, project overlays, `.beads/beads.md`, minimal safety hooks, and Codex config where plugin parity is weaker. Move optional reusable workflows into versioned plugins so users get marketplace updates instead of copied drift. Claude docs explicitly position plugins as the shareable, versioned, updatable surface; project `.claude/` is better for team-specific settings and customization (https://code.claude.com/docs/en/settings, https://code.claude.com/docs/en/plugin-marketplaces).

Avoid reference-not-copy or symlink as the default. Symlinks are brittle across OSes, containers, trust boundaries, and collaborators. Plugin-native is better where supported; copied thin layer is safer for repo-owned policy.

Sketch:
- v1: current copy architecture plus manifest/diff tooling.
- v2: split reusable skills into `core-workflows` plugin; leave adopted template as bootstrap/overlay.
- v3: `/mvp-plugin:update` migrates copied core files to plugin references where safe.
- Keep current sync scripts for template payload; they already compare shared Claude/Codex drift ([check-sync](/data/codes/coding-ritual/mvp-harness/plugins/mvp-plugin/scripts/check-sync.sh:42)) and build a genericized payload ([build-template](/data/codes/coding-ritual/mvp-harness/plugins/mvp-plugin/scripts/build-template.sh:46)).

Tradeoff: plugin namespaces are less ergonomic than short local commands, but updatability wins for reusable bulk.

Divergence / least sure: I would not make “template-as-plugin” the whole answer until Codex has equally clean plugin semantics in this repo. The dual-tree burden is real.

**F. Orchestration Surface**
Recommendation: add five root lifecycle surfaces, no more.

Minimal set:
- `reference-inventory`: deterministic manifest generation only.
- `reference-drift`: pinned SHA to upstream HEAD report.
- `reference-gap`: reference vs `mvp-harness` report.
- `reference-route`: rubric-based adoption decision.
- `harness-sync-back`: for accepted template changes, run `check-sync`, edit source trees, `build-template`, and prepare submodule bump instructions.

Add one rule: reference harnesses are read-only inspiration; no submodule internal edits, no stale tooling. Add one schema doc and one state directory. Do not add a mega-agent that does everything invisibly.

Tradeoff: more commands would feel convenient but would obscure review gates.

Divergence / least sure: whether `reference-gap` and `reference-route` should be separate commands or one skill with two modes. I would keep them separate until the reports stabilize.

**Cross-Cutting Recommendations**
Use JSON for machine state and Markdown for human reports. Make every report link raw upstream files and local equivalents. Treat MCP servers as dependency-bearing capabilities, not just config lines; MCP exposes tools/resources/prompts as primitives (https://modelcontextprotocol.io/docs/getting-started/intro, https://modelcontextprotocol.io/docs/learn/architecture). Put size/context estimates in every route report because Claude plugin install UI now exposes context cost and install contents.

**Open Questions**
- What is the canonical state location: `state/reference-harness/` vs `docs/research/reference-harness/state/`?
- Should scheduled polling create Beads issues automatically, or only update a report?
- How much Codex-native plugin support should the future architecture assume versus keeping `.codex/` copied?
- What threshold requires adopting a capability group rather than a single skill/agent?

**Top 3 Things I’d Do First**
1. Build the manifest schema and inventory script; verify it handles `everything-claude-code` without truncation.
2. Generate one drift report and one gap report for `superpowers` and `everything-claude-code` to calibrate noise.
3. Split routing decisions into a small rubric skill and require human approval before any template/plugin edits.

Verification note: I made no manual file edits. `git status --short --branch` shows existing dirt: `.beads/issues.jsonl` modified and untracked `docs/`; running `bd prime` appears to have refreshed the Beads export by adding issue `cr-2ks`.


