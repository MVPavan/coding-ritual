---
name: html-artifact
description: Create polished single-file HTML artifacts as an alternative to markdown, only for documents the user wants rendered for human reading (never Markdown-native repo files). Use when the user asks for HTML, or for a human-facing implementation plan, status report, post-mortem, architecture doc, scaling analysis, capacity dashboard, research explainer, concept walkthrough, PR writeup, or other long-form documents that benefit from richer structure than markdown — KPI tiles, charts, tables, mockups, code blocks with copy buttons, collapsibles, SVG diagrams, or small interactive controls. Also use when the user asks for "an HTML file", "HTML artifact", "HTML doc", "HTML version of this", or "a one-pager". Do NOT use for React components, web apps, marketing pages, or visually expressive design; for READMEs, docstrings, agent prompts, CLAUDE.md, or anything destined for git/CLI/another agent (use markdown); or for content under ~50 lines where visual structure doesn't earn its weight.
---

# html-artifact

Standalone single-file HTML documents that replace what would otherwise be a long markdown file. Goal: readability and credibility — Stripe docs, not portfolio site.

## When to use

**HTML when all hold:** output is for humans (not another agent or pipeline); visual structure adds information (tables, diagrams, mockups, charts, severity colors, interactive controls); content is ~50+ lines; user wants to share or reference, not hand-edit.

**Markdown when any hold:** README, CLAUDE.md, agent prompt, docstring; lives in git and reviewed in PR diffs; ingested by another LLM, RAG, or eval system; destined for a markdown-native surface (GitHub, Linear, Slack); the user is iterating fast on something disposable; too short for scaffolding to pay off.

An HTML artifact costs roughly 2–4× the tokens of the markdown equivalent — spend it on documents that get read more than once.

If unsure, ask before producing.

## Standalone-file invariants

Single self-contained `.html` that works double-clicked. Non-negotiable:

- Viewport meta for mobile responsiveness
- Inline CSS, inline JS, no build step
- Dark mode support via `prefers-color-scheme`
- No external trackers, no analytics, no fetches to third-party APIs
- Works on `file://` — no same-origin fetches, no service workers
- System fonts only — no webfont requests; a named local face (e.g. a serif document stack) is fine when the stack ends in a generic family
- Collapses to single column under 720px
- Readable with JS disabled — interactivity is progressive: the markup is complete before any script runs, and a script error must leave the full content visible
- Prints readably — include an `@media print` block
- If anything animates: an `@media (prefers-reduced-motion: reduce)` fallback, and nothing flashes or changes luminance more than 3×/second

## Aesthetic direction

**Tokens first.** If the project defines its own visual language — CSS custom properties, a theme or tokens file, an installed design skill — read it and use those values as the artifact's CSS variables. If it defines none, apply the direction below. Never invent tokens that merely resemble the project's: match the source or use the default. The invariants above always win — drop any token that would require a webfont request or pure black.

**Color:** Neutral page background — off-white in light mode, near-black in dark mode. One accent color used sparingly for emphasis (a single primary KPI, a copy button, the active tab in a tabset) — more content never buys more accented elements; if a palette offers eight colors, pick three and demote the rest. Reserve red/amber/green for severity tags only. Avoid loud color as a background; the page should look like a document, not an ad. Compute contrast against the token you actually ship: ≥4.5:1 for body and muted text, ≥3:1 (WCAG 1.4.11) for any graphical mark that carries meaning — if the accent can't clear it, carry the meaning on the boundary or weight and make hue redundant.

**Typography:** System or named-local font stack (see invariants). Body 16–18px with generous line-height (1.5–1.7); small caption text, large section titles, and one or two hero numbers per artifact. Monospace is for technical content only — paths, commands, values — never a blanket "dev" look. Tabular numerals for any column of figures.

**Spacing:** Consistent rhythm based on a small set of values (multiples of 4px or 8px). Sections separated by larger gaps than paragraphs; KPI tiles separated by smaller gaps. The same artifact should never mix arbitrary px values — pick a scale and stick to it.

**Layout:** Cap prose measure at 60–75ch. Sections are vertically stacked; multi-column only where it earns its weight (KPI rows, chart grids, controls/preview splits). Always single column under 720px.

**Dark mode:** Same layout, inverted palette — same opacities with the neutral RGB flipped; the accent and severity colors shift to slightly lighter/desaturated variants. No pure `#000000` — it clips on OLED and in print. Never name a tone in prose or a legend ("darkest") — a tone description inverts between themes and ships false in one of them; say "strongest".

## Component vocabulary

Every artifact draws from this small set. Implement each fresh, in keeping with the aesthetic direction above. Lay content out as its own shape — a timeline drawn as a timeline, a comparison as columns, a diff as a diff — never markdown structure translated 1:1 into HTML.

**KPI tile row.** 3–5 cards at the top. Each shows a big number, a small muted label below, and optionally a small delta. Borders, not shadows; vary card widths (e.g. `1.1fr 1fr 0.9fr`) rather than shipping an equal grid. The fastest way to orient a reader — use it whenever there are concrete facts the reader needs before reading anything else.

**Numbered section header.** A large grey number ("01", "02") set alongside the section title, with a thin horizontal rule below. Signals "this is scannable, you can jump by section".

**Code block with copy button.** Monospace pre/code with a small "Copy" button in the top-right that writes to the clipboard and briefly flashes "Copied". A muted caption above naming the file path.

**Severity tag.** A small rounded pill in high/med/low severity colors. Tinted background, full color foreground — never raw severity color as a large background. For risks, incidents, statuses.

**Collapsible.** Native `<details>/<summary>` so JS-disabled readers still get the content. For deep-dives, raw data behind charts, anything off the main path.

**Inline SVG diagram.** Real SVG for flows, architectures, lifecycles — never ASCII, unicode boxes, or embedded screenshots. Before drawing any figure, read `references/svg-craft.md`: craft rules, connector geometry, accessibility contract, and the honest-data rules.

## Presets

Pick exactly one. Read the matching reference before writing. If a request genuinely spans two, pick the dominant preset and take the single component you need from the other — do not read both files. A new preset would require a new *layout*, not a new topic.

- **report** — plans, status updates, post-mortems, architecture docs, design specs, PR writeups, option comparisons → `references/preset-report.md`. Not report when charts are the argument (dashboard) or the reader is learning a concept (explainer).
- **dashboard** — chart-first analyses, capacity, scaling studies, comparisons → `references/preset-dashboard.md`. Not dashboard when there is more than a paragraph of prose between charts (report).
- **explainer** — "how X works", concept teaching, research summaries → `references/preset-explainer.md`. Not explainer when the reader will act on current facts rather than learn (report).
- **editor** — tuners, config editors, triage boards, anything with "copy back to prompt" → `references/preset-editor.md`. Not editor when the user only reads (report or explainer).

For an over-long draft, cut in order — decoration, exact duplicates, leaf detail, single-reader asides — and stop as soon as it fits; split into two artifacts before shrinking type or squeezing content. Match wording to the audience (engineer / mixed / executive): audience changes what things are called, never how many there are. Never invent detail to fill a slot; keep the source's proper nouns.

## Anti-patterns

- Gradient hero with centered headline and CTA — the universal "AI website" tell
- Glassmorphism, neon, "shadcn card everywhere" — reports aren't landing pages
- Google Fonts — system fonts are faster and more credible
- Walls of `<p>` with no scaffolding — that's why we picked HTML
- Importing chart libraries for three bars — write inline SVG
- Animations on initial render — doc must be readable instantly
- Buttons that look tappable but do nothing — render as text if non-interactive
- Lorem ipsum, invented metrics, fake names or timestamps
- Emoji as section headers or severity markers — the tag carries a word
- Centering everything, or a header with a logo placeholder

Three or more of these in a draft means the styling is wrong at the root. Restart it rather than removing items one at a time.

## Output protocol

Save under `scratchpad/` (gitignored) with a descriptive, timestamped filename and tell the user the path; open it locally when the environment allows (`xdg-open` / `open` / `start`). A related set (a contents page plus detail pages) is one folder with relative links — under `scratchpad/` unless a calling skill names its own output tree — and every file still satisfies every invariant. Never paste HTML source into chat.

Name the story in one sentence before structuring — everything that doesn't serve that sentence is a cut candidate. When the artifact condenses a source (a document, dataset, or diagram), close the reply with a short fidelity note: what was merged, collapsed, dropped, and kept in full. Gaps in the source get asked about, never filled; when an extraction is ambiguous, list the candidates and ask rather than guessing.

Before claiming done, verify in the source: the full content is present as markup before any script runs, a print block exists, and reduced motion is handled wherever something animates. A real browser pass (JS off, reduced motion, print preview) is the user's check — ask for it when the artifact matters.
