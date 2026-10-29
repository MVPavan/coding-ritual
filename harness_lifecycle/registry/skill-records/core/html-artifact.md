---
skill: html-artifact
domain: core
stage: X
substage: Communication
secondary: []
family: visual-explanation
aliases: []
status: active
---
# html-artifact

## Capability

Use for requested standalone HTML documents or interactive explanations when that format materially helps. Skip agent-facing files, Markdown-native deliverables, and ordinary short answers.

<!-- registry:generated traits -->
- `self-contained-contract`: Produce one HTML file with inline CSS and JS, viewport metadata and no build step, working offline with no external fonts, trackers, fetches or runtime assets.
- `accessibility-contract`: Use semantic markup, keyboard access and adequate contrast, adapt to narrow screens, honour reduced motion, and provide print styles.
- `progressive-enhancement`: Ensure the explanation, data and limitations exist before scripts run and survive with JavaScript disabled.
- `honest-content`: Show only sourced data and explicitly label assumptions and illustrative values.
- `preset-report`: Shape a skim-by-section report — orientation KPIs, numbered sections with a per-type order, and a source footer.
- `preset-dashboard`: Shape a chart-first document where prose only captions inline-SVG charts, with a drill-down data table.
- `preset-explainer`: Shape a concept walkthrough — a TL;DR box, question-headed sections, a glossary and tabbed samples.
- `preset-editor`: Shape an interactive throwaway editor built around a mandatory paste-ready export, with no backend or persisted storage.
- `tokens-first-style`: Derive the artifact's styling from the project's own tokens when they exist, otherwise apply the default neutral aesthetic, never inventing look-alike tokens.
- `component-vocabulary`: Lay content out from a small set of components — KPI tiles, numbered section headers, copy-button code blocks, severity tags, native collapsibles and inline SVG — shaped to the content rather than translating markdown one-to-one.
- `svg-figure-grammar`: Draw inline SVG figures with a viewBox for scaling, currentColor ink, orthogonal masked connectors, a defined paint order and a bottom legend, keeping real text and rounded coordinates.
- `svg-complexity-budget`: Hold each figure to at most nine nodes, twelve arrows and two accents, splitting into overview-plus-detail rather than shrinking, and omit a figure a sentence can carry.
- `svg-accessibility`: Give each inline SVG a role, figure-prefixed title and description IDs, carry meaning in both shape and colour, and mark direction on every edge.
- `honest-data-encoding`: Never clip, truncate, impute or move a mark to make a chart legible; disclose the domain drawn and name any exemption.
- `deliver-verify`: Deliver a link rather than pasted source and verify content fidelity, local links, key interactions, responsive and print behaviour and JS-disabled readability, reporting checks that could not run.
<!-- /registry:generated traits -->

<!-- registry:generated lineage -->
- **diagram-design:skill:skills/diagram-design** `skills/diagram-design/SKILL.md` @ 4b57361
  - merged from: diagram-design SKILL.md §6-7,12
  - merged from: style-guide.md
  - merged from: output-spec.md
  - merged from: animation.md (3 principles)
  - merged from: 9 type references (honest-data lines)
  - merged from: primitive-annotation.md (3 lines)
  - merged from: primitive-terminal.md (no-pure-black)
  - modified: all rules de-fonted and de-branded
  - modified: budgets kept numeric
  - modified: mask rule corrected to the source's direction after critic finding 4
  - modified: exemption form generalised
  - dropped: taxonomy, all templates and 140 assets, both importers, export pipeline, onboarding/profiles machinery, icon corpus, motion system beyond three principles, 4px enumerated grid (LATER)
- **html-artifacts:skill:skill** `skill/SKILL.md` @ c14a4ec
  - merged from: html-artifacts SKILL.md (5 components)
  - merged from: diagrams-and-illustrations.md
  - merged from: matching-your-style.md
  - merged from: reports-and-research.md
  - merged from: exploration-and-planning.md
  - merged from: code-review-and-pr.md (PR-writeup row only)
  - merged from: custom-editors.md (4 rules)
  - modified: tokens-first narrowed: derivation kept, persisted design-system.html dropped
  - modified: click-to-expand re-expressed as details-below-figure
  - modified: all borrows re-phrased to survive our JS-disabled and offline invariants
  - modified: browser checklist restated as source-verifiable requirements (critic finding 1)
  - dropped: aggressive any-of trigger
  - dropped: CDN allowance
  - dropped: working-dir output
  - dropped: conditional dark mode
  - dropped: emoji severity tags
  - dropped: localStorage permission
  - dropped: decks
  - dropped: design-and-prototypes (round-002)
  - dropped: baseline CSS block
  - dropped: all worked sketches (fabricated data)
  - dropped: annotated-diff category (ruled to code-review skill)
- **diagram-design:skill:skills/diagram-design** `skills/diagram-design/SKILL.md` @ 4b57361
  - merged from: (unchanged from round-005 — see round-005-visual-explanation-merge:e002)
  - modified: (none new — this round only removes the round-006 full install)
  - dropped: the full-skill install of round-006: whole directory, licenses, slash-only frontmatter, catalog allowlist entries — all removed pre-push
- **diagram-design:skill:skills/diagram-design** `skills/diagram-design/SKILL.md` @ 4b57361
  - merged from: (unchanged from round-005 — see round-005-visual-explanation-merge:e002)
  - modified: (none new — this round only removes the round-006 full install)
  - dropped: the full-skill install of round-006: whole directory, licenses, slash-only frontmatter, catalog allowlist entries — all removed pre-push
- **html-artifacts:skill:skill** `skill/SKILL.md` @ c14a4ec
  - merged from: html-artifacts SKILL.md (5 components)
  - merged from: diagrams-and-illustrations.md
  - merged from: matching-your-style.md
  - merged from: reports-and-research.md
  - merged from: exploration-and-planning.md
  - merged from: code-review-and-pr.md (PR-writeup row only)
  - merged from: custom-editors.md (4 rules)
  - modified: tokens-first narrowed: derivation kept, persisted design-system.html dropped
  - modified: click-to-expand re-expressed as details-below-figure
  - modified: all borrows re-phrased to survive our JS-disabled and offline invariants
  - modified: browser checklist restated as source-verifiable requirements (critic finding 1)
  - dropped: aggressive any-of trigger
  - dropped: CDN allowance
  - dropped: working-dir output
  - dropped: conditional dark mode
  - dropped: emoji severity tags
  - dropped: localStorage permission
  - dropped: decks
  - dropped: design-and-prototypes (round-002)
  - dropped: baseline CSS block
  - dropped: all worked sketches (fabricated data)
  - dropped: annotated-diff category (ruled to code-review skill)
<!-- /registry:generated lineage -->

<!-- registry:generated history -->
- `2026-08-20` **adopt-merged** (2026-10-14-migration:188): Adopted-merged 2026-08-20 (round-005, supersedes round-004 defer; evidence: skill-comparisons/visual-explanation/ + scratchpad round-004 merge-dossier). Into h…
- `2026-08-20` **adopt-merged** (2026-10-14-migration:187): Standing ruling = round-005 adopt-in-part (geometry grammar + honest-data doctrine into html-artifact's references/svg-craft.md; contrast/typography/dial rules…
- `2026-08-20` **adopt-merged** (2026-10-14-migration:181) *(superseded)*: User reversed round-006's full install before push: 2.9MB (mostly the 140-file assets tree) is too big for this harness. The standing ruling returns to round-0…
- `2026-08-20` **adopt-merged** (2026-10-14-migration:179) *(superseded)*: Adopted-merged into html-artifact per the line-level dossier: 14 of 39 components in reduced form, 4 REMOVEs executed on our side (spacing duplicate, framing r…
- `2026-08-20` **adopt-merged** (2026-10-14-migration:178) *(superseded)*: Adopted in part into html-artifact — the geometry grammar and honesty doctrine, none of the machinery. references/svg-craft.md now carries the six connector ru…
<!-- /registry:generated history -->

<!-- registry:generated reviews -->
- [skill-comparisons/visual-explanation](../../../archive/skill-comparisons/visual-explanation/)
<!-- /registry:generated reviews -->

<!-- registry:generated sources -->
No adopted traits recorded.
<!-- /registry:generated sources -->

<!-- registry:generated declined -->
No declined traits recorded.
<!-- /registry:generated declined -->
