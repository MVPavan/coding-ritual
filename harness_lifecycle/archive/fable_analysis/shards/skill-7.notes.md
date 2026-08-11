# Shard skill-7 — worker notes

27 rows evaluated; 27 source files inspected (24 read from the working tree, 3
recovered from submodule git history because the input paths are stale at the
current pin).

## Stale source paths (compound-engineering-plugin)

The submodule's current pin no longer has the `plugins/compound-engineering/skills/`
layout — skills were renamed to `ce-*` under top-level `skills/`, and several were
deleted. Recovered content via `git show`:

- `every-style-editor` — `git show af80bf23:plugins/.../every-style-editor/SKILL.md`; absent from current skill set.
- `gemini-imagegen` — same commit; absent from current skill set.
- `feature-video` — `git show b979143a~1:...`; upstream commit `fbf543dc` explicitly removed it in favor of a generalized `evidence-capture` skill (and later `ce-demo-reel`). Upstream deletion treated as a negative signal for adoption.
- `frontend-design` (compound copy) also gone at the pin; evaluated the official `claude-plugins-official` variant, which is the strongest of the three listed harness copies.

The scan/gap tooling should ideally re-resolve paths at the pinned commit or flag
these as upstream-removed.

## Input-data bug worth fixing

`skill:inventorydemandplanning` has `description: ">"` — the extractor grabbed the
YAML folded-scalar indicator instead of the folded text. Any skill using
`description: >`-style block scalars will be mangled the same way in the CSV.

## Verdict distribution

- adopt: 2 (both ours — `harness-adopt`, `harness-evaluate`; retained, quality confirmed)
- defer: 2 (`frontend-design`, `frontend-slides`)
- reject_after_review: 23

The shard is dominated by domain-niche content (healthcare x4, blockchain,
retail demand planning, media generation x2), external-dependency skills
(Exa MCP, fal.ai MCP, Google Workspace, hookify runtime), and thin
stubs/templates (example-command, example-skill, grill-with-docs, implement,
edit-article). High instruction quality did not rescue irrelevant domains —
e.g. `evm-token-decimals` and `inventory-demand-planning` are excellently
written and still rejected.

## Cluster relationships

- `design-interrogation`: `grilling` + `grill-with-docs` (mattpocock) duplicate our local `grill-me`. Only distinct rules in `grilling`: ask one question at a time; answer from the codebase instead of asking when possible. Cheap follow-up: parity-check `grill-me` for those two rules. `grill-with-docs`' idea (emit ADRs/glossary during the grill) is a one-line enhancement note, not an adoption.
- `skill-authoring-templates`: `example-command` + `example-skill` are superseded by the `skill-creator` plugin.
- `html-design-quality` / `html-presentations`: `frontend-design` (official) is genuinely strong anti-"AI slop" prose; deferred only because built-in `artifact-design` + `dataviz` + local `html-artifact` already own that slot. `frontend-slides` is the only candidate covering slide decks; adopt on first real presentation need (its single-file zero-dependency stance matches the user's local-artifact preference).
- `healthcare-domain`: 4 skills form one interdependent family (`hipaa-compliance` routes into `healthcare-phi-compliance`); reject as a block. Transferable ideas noted but not worth carrying: tiered CRITICAL/HIGH deploy gates (eval-harness), thin-router-to-canonical-skill structure (hipaa).
- `git-conventions`: `git-workflow` is a 717-line catalog that violates the curation rule against importing catalogs and contains recipes (`git add .`, `reset --hard`, force-push) that contradict CLAUDE.md Git Safety.
- `harness-adoption` / `harness-curation`: the two in-ours rows scored highest in the shard; no action needed beyond retention.

## Weak / judgment-call rows

- `frontend-design`: closest to a merge verdict — if local HTML dashboard quality ever disappoints, fold its "named default looks to avoid" + signature-element guidance into `html-artifact`.
- `hexagonal-architecture`: gpt's "language-neutral" point is fair, but our `coding-style.md` already encodes the lite version (downward dependency flow, `contracts/`, Protocol); rejected rather than rewrite because the delta over model baseline + existing rules is small.
- `google-workspace-ops` and `enterprise-agent-ops`: marginal rejects — generic discipline with hard dependency/relevance gaps, respectively.
