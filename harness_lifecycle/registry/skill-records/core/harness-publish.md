---
skill: harness-publish
domain: core
stage: Delivery
substage: Release
secondary: []
family: 
aliases: []
status: active
---
# harness-publish

## Capability

Publish this repo's harness into the mvp-plugin (the mvp-harness submodule) — copy the shippable skills and agents, run the provider-neutrality and leak audits, regenerate the shipped router and Codex sidecars, rebuild the residue template, validate both manifests, bump the version. Root-only; never runs in adopted repos.

<!-- registry:generated lineage -->
- **agent-skills:skill:skills/git-workflow-and-versioning** `reference_harnesses/agent-skills/skills/git-workflow-and-versioning/SKILL.md` @ aeac41d
  - merged from: git-workflow-and-versioning (semver and changelog sections)
  - modified: semver and changelog become harness-publish release steps
  - dropped: commit cadence
  - dropped: trunk-based and Conventional Commit defaults
  - dropped: destructive recovery guidance
  - dropped: merge-conflict and worktree content
<!-- /registry:generated lineage -->

<!-- registry:generated history -->
- `2026-10-14` **adopt-merged** (2026-10-14-owner-review:001): Owner ruling: the 2026-08-11 merge target was never built, and the 2026-07-15 objections still hold (commit cadence, trunk and Conventional Commit defaults, de…
<!-- /registry:generated history -->

<!-- registry:generated reviews -->
None yet.
<!-- /registry:generated reviews -->
