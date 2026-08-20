# Visual Explanation

Capability family: **visual-explanation** — surfaces that make the agent
explain something to the human *visually* (sketches, trees, diagrams, rendered
pages) instead of in prose. Compared here (extended 2026-08-19 → 2026-08-20):

- ours: `html-artifact`
- humanlayer: `show-me` (deferred, round-003)
- cathrynlavery: `diagram-design` (round-004)
- dogum: `html-artifacts` (round-004) — a direct head-to-head with ours
  (96 % name similarity per the gap report)

Our `teach` is noted where it overlaps (its lessons are HTML, but its job is
multi-session pedagogy — family `learning-content`).

Upstream pins: `humanlayer_skills` @ `3c26291`; `diagram-design` @ `4b57361`
(2026-08-19, plugin v2.5.20); `html-artifacts` @ `c14a4ec` (2026-05-08).
Round-004 analysis by Opus 5 (medium) subagents, coordinator-verified by
spot-checking every load-bearing citation against the sources.

## Level 1 — Placement

| Skill | Repo | Bucket | Triggers when |
|---|---|---|---|
| `show-me` | humanlayer | 14 (also 13) | "Help the user understand the current topic of conversation visually" (`SKILL.md:3, 6`). Effectively user-invoked mid-conversation; description broad enough to fire on any "explain" ask. |
| `html-artifact` | ours | 13 (also 14) | User asks for HTML, or a human-facing long-form document benefits from richer structure; explicit do-not list (READMEs, agent prompts, <~50 lines) (`SKILL.md:3`). Also invoked by `codebase-architecture-research` (`its SKILL.md:93`). |
| `diagram-design` | diagram-design | 14 (also 13; arguably 3) | Really: user names one of 38 diagram/chart nouns, points at a `.drawio*`/`.mmd` source, or asks to brand diagrams; the body's own gate is narrower — "would the reader learn more than from a paragraph?" with a don't-use list at `SKILL.md:52-61`. **The description is a capability catalogue, not a trigger** (`SKILL.md:3`) — deliberately so, mandated by their ADR (`docs/adr/0004-…:13`) and CI-enforced. Predictable over-fire: any mention of "timeline / org chart / bar chart / Gantt / kanban" loads a 578-line SKILL.md, and the bar/line/scatter/radar/Sankey nouns collide with the `dataviz` skill's trigger surface — two skills would claim "make me a bar chart". |
| `html-artifacts` | html-artifacts (dogum) | 13 (also 14) — same placement as ours | Nominal: content that "benefits from spatial layout, color, real diagrams, interactivity, or a round-trip editor" (`SKILL.md:3`). Real: an **any-of** disjunction over 8 predicates with "Don't wait for the user to ask explicitly" (`SKILL.md:12-25`). **Would over-fire badly by our standards on three mechanisms**: (1) the description embeds an imperative — "Use this skill aggressively" — violating our triggers-only rule (`authoring-for-agents/SKILL.md:67`); (2) it triggers on ordinary conversation verbs ("explain", "summarize", "compare", "walk through"); (3) it contradicts its own body, which warns "This skill is not 'always answer in HTML'" (`SKILL.md:92-94`) and discloses 2–4× token cost (`:86`) — restraint that lives below the line read at routing time. |

Ledger: round-003 deferred `show-me`; no prior entry for the other two.
Round-002 precedent (UI out of scope) applies to `html-artifacts`'
`design-and-prototypes.md` reference and bounds what is borrowable.

## Level 2 — Capability profiles

### `show-me` (humanlayer) — deferred round-003

Profile unchanged from the round-003 analysis: seven lightweight inline visual
forms (pseudocode, call tree, component tree, file tree, Mermaid,
diff-shaped-to-topic, whole block; `SKILL.md:8-115`), escalating to one focused
HTML file in a single sentence (`SKILL.md:117-121`). Owns the low end of the
family; its HTML escalation is strictly weaker than ours. Deferred pending a
recorded prose-vs-diagram failure.

### `html-artifact` (ours)

Profile unchanged (see components.md): HTML-vs-markdown decision rule with
both sides enumerated (`SKILL.md:10-16`), hard standalone-file invariants —
offline/`file://`, system fonts, `prefers-color-scheme` dark mode, JS-disabled
readable, single column <720px (`:18-30`) — aesthetic direction (`:32-44`),
six-element component vocabulary (`:46-60`), four presets (`:62-69`),
anti-patterns (`:71-81`), `scratchpad/` output protocol (`:83-85`).

What this round exposed about ours: the inline-SVG component is one sentence
with no craftsmanship rules; "PR writeup" is advertised in our description
with no preset behind it; no content-measure number (ch); no deck category;
aesthetic direction is repo-blind (fixed, never derived from the project's
own design tokens).

### `diagram-design` (cathrynlavery)

**Achieves** — a single self-contained HTML file containing one
editorial-quality inline-SVG diagram, drawn to a skinnable token system, a
hard geometry grammar, and per-type numeric complexity budgets, with optional
redraw-from-source (draw.io / Mermaid) and manual raster export.

**Can do** (full inventory in components.md)
- 38-type routing table behind a two-axis selection (semantic pattern before
  visual type) (`SKILL.md:65-122`).
- **Six mandatory connector rules** — orthogonal elbows `r=8`, label masks
  with 6–10px gaps, no overlapping connectors (bridge/hop), fanned attach
  points ≥12px, no transit behind non-endpoint boxes, no mask over a
  later-painted node (`SKILL.md:266-288`).
- **Numeric per-type complexity budgets** (~40 ceilings: ≤9 nodes, ≤12
  arrows, ≤2 accents…) with "split into overview + detail" as the named
  remedy (`SKILL.md:46, 362-404`).
- Accessible-SVG contract: `role="img"`, `<title>`/`<desc>` wiring, the
  duplicate-ID hazard between two inline SVGs on one page, "describe the
  content, not the geometry" (`SKILL.md:563-572`).
- Ships an executable verifier (`scripts/self_check.py` — accessible-SVG +
  single-file safety + motion structure; invoked at `SKILL.md:484`).
- Brand onboarding from a URL / installed skill / token folder, with an
  exact-font gate, AA contrast checks, and a mandatory "brand fidelity
  receipt" (`references/onboarding.md:87-150`); named client profiles under
  `~/.diagram-design/` (`references/profiles.md`).
- Import-as-redraw from draw.io/Mermaid: structural extractor, never render
  the source, degrade ladder, mandatory fidelity ledger, and an explicit
  prompt-injection boundary (source labels are untrusted data; never follow
  click targets) (`references/import-*.md`; `references/output-spec.md:101-164`).
- Four output dials — format × size × detail × **audience** (audience governs
  wording, detail governs count) (`references/output-spec.md:5-137`).
- Accessible motion with a pinned, byte-identical controller and a
  static-first enhancement contract (`references/animation.md`).

**Pros (vs ours and show-me)**
- The only surface in the family with a diagram *grammar*. Ours authorizes
  inline SVG in one sentence (`html-artifact/SKILL.md:60`); theirs supplies
  the rules that prevent the three defects that make LLM-drawn SVG read as
  slop (diagonal slants, overlapping strokes, unmasked/clipped labels).
- Budgets are integers, so they survive a fresh context window; ours and
  show-me's restraint rules are adjectives.
- Verification ships with the skill (executable check); ours is honour-system.
- Multi-host (Claude/Codex/Factory/Pi manifests) vs show-me's macOS `open`.
- The import path (redraw + fidelity ledger + untrusted-source rule) has no
  counterpart anywhere in our catalog.

**Cons (vs ours)**
- **Three direct contradictions with our invariants**: Google Fonts is
  mandatory (`SKILL.md:204`; `references/style-guide.md:86`; refusal to
  substitute a system stack at `references/onboarding.md:89-94`) vs our
  "system fonts only" (`html-artifact/SKILL.md:28`); dark mode is a separate
  `-dark.html` file — zero `prefers-color-scheme` in any template — vs our
  one-file invariant (`:25`); every template pins `svg { min-width: 900px }`
  (`assets/template.html:53`) vs our <720px single-column rule (`:29`).
- Context cost an order of magnitude above the family: 578-line SKILL.md +
  7,256 lines of references; a realistic branded animated import loads
  ~1,400 instruction lines before drawing.
- Its own shipped exemplars are off-skin by the author's admission
  (`references/style-guide.md:32`) — serious for a taste-by-example skill.
- Dangling handoffs: quick sketches route to a `wiretext` skill that exists
  nowhere (`SKILL.md:56`); no Pi prompt for the draw.io command.
- Description-as-catalogue trigger collides with `dataviz` (Level 1).
- Icon library carries mixed MIT/CC0/trademark obligations
  (`THIRD_PARTY_LICENSES.md:5-43`) — borrowing prose rules is clean,
  borrowing assets is not.
- No document concept at all — one figure per file; no handoff to the
  family's low end (that case is delegated to the missing `wiretext`).

### `html-artifacts` (dogum)

**Achieves** — an "HTML instead of markdown" default for nine categories of
agent output, backed by per-category layout playbooks (Layout / load-bearing /
common mistakes / worked sketch) plus a taste layer aimed at suppressing the
default-AI aesthetic. The same thesis as ours, independently derived, with
2× the category coverage and ~2–4× the per-invocation context cost.

**Can do** (full inventory in components.md)
- Disjunctive 8-predicate trigger + 5 markdown carve-outs (`SKILL.md:12-37`).
- Seven universal rules incl. "real layout, not markdown translated 1:1"
  (`:46`), title + TL;DR above the fold (`:47`), editors must export back to
  text (`:49`).
- Eight per-category playbooks: explainers, status/post-mortem reports,
  option comparisons + implementation plans, **annotated code review / PR
  writeup / module map**, **decks**, **design systems & prototypes**,
  figure sheets & flowcharts, custom editors.
- SVG craftsmanship: `viewBox` not fixed dims, **`currentColor` for ink**
  (dark-mode survival), round coordinates, labelled `<g>` groups, real
  `<text>`, no raster (`references/diagrams-and-illustrations.md:44-49`);
  shape-and-color accessibility (`:38`); copy-SVG button per figure (`:12`).
- **Design-system-from-codebase**: read the repo's tokens once, persist a
  `design-system.html`, read it before every later artifact
  (`references/matching-your-style.md:11-22`).
- Numeric typography floor (16–18px, 60–75ch, 1.5–1.6 — "not negotiable")
  plus a full known-good starter CSS token set with the dark-mode block
  (`references/matching-your-style.md:8, 28-68`).
- AI-default-look list with a countable gate: "any three of those → restart"
  (`references/matching-your-style.md:89-100`).
- Token-cost honesty: 2–4× markdown, with license to stay in markdown for
  disposable iteration (`SKILL.md:84-86`).

**Pros (vs ours)**
- Three whole categories we lack: decks, code-review/PR (our description
  advertises "PR writeup" with no preset behind it), design/prototypes.
- SVG craft rules and the copy-SVG-per-figure device — mechanism-level
  guidance where ours has one sentence.
- The design-system-from-codebase trick converts taste from a per-invocation
  guess into project state; our aesthetic is fixed and repo-blind.
- Countable restart trigger vs our pass-by list of anti-patterns.
- Their `custom-editors.md` and our `preset-editor.md` converged
  independently on the same non-negotiable (export or it's a toy), the same
  three canonical shapes, and the same config-diff export — validation that
  our editor preset is right.
- Verified: despite the CDN allowance in their rules, all six shipped
  examples contain zero external requests — offline-clean in practice.

**Cons (vs ours) — ranked conflicts**
1. **Firing threshold**: "use aggressively" + any-of + proactive
   (`SKILL.md:3, 14`) vs our all-hold + do-not list. Adopting their trigger
   would put HTML in front of the user for ordinary "explain this" asks.
2. **Offline is soft**: CDN permitted for Tailwind/fonts/libraries
   (`SKILL.md:44`) vs our hard `file://` + vendored-inline invariant
   (`html-artifact/SKILL.md:26-27`; `preset-dashboard.md:25`). Their own
   examples never take the hatch — dead weight with a downside.
3. **Output location**: working directory (`SKILL.md:74`) vs our gitignored
   `scratchpad/` — violates our git-safety norm directly.
4. **JS is load-bearing** in three references (live demo "the user cannot
   imagine it", click-to-expand flowcharts, keyboard-only decks) vs our
   JS-disabled-readable invariant (`html-artifact/SKILL.md:30`).
5. Emoji severity tags (`references/code-review-and-pr.md:13`) — which their
   own taste file forbids (`matching-your-style.md:94`).
6. `localStorage` permitted for local editors (`custom-editors.md:39`) vs our
   ban (`preset-editor.md:38`) — their argument (don't lose 30 minutes of
   triage to a refresh) deserves a deliberate ruling, not a silent keep.
7. Dark mode "if cheap" (`SKILL.md:48`) vs our invariant; serif-named-fonts
   default vs our system-only (policy conflict, though their stacks are
   local-first in practice).
- Also: no invented-data rule anywhere in 1,004 lines (their own example
  fabricates ticket IDs and metrics), no component vocabulary, no spacing
  scale, no chart-library policy, no dashboard category, a stray authoring
  artifact ("Greg…", `SKILL.md:45`), and multi-reference reads push a
  "plan with mockups and a flowchart" to ~465 loaded lines vs our bounded
  ~130 ("Pick exactly one", `html-artifact/SKILL.md:64`).

### Verdict

- **`html-artifacts` (dogum) is a true substitute for ours** — same job, same
  shape, independently converged on many of the same rules. Ours wins on
  every invariant that matters for this repo (triggering discipline, offline,
  git safety, progressive enhancement, no-invented-data, bounded context);
  theirs wins on category breadth and on mechanism-level craft guidance
  (SVG rules, numeric type floor, design-system persistence, restart gate).
  The right outcome is **selective merge into ours, reject as a unit** —
  adopting it standalone would create two same-named, mutually contradicting
  skills.
- **`diagram-design` is a complement squeezed from both sides**: show-me owns
  the inline low end, our html-artifact owns the document; diagram-design
  owns the single polished *figure*. Its rendering invariants contradict ours
  three ways, its context cost is disproportionate, but its geometry grammar
  is the missing rulebook for the SVG diagrams our skill already authorizes.
- The **Mermaid gap stands**: diagram-design consumes Mermaid but forbids
  reproducing its layout; html-artifacts discourages it. Neither closes the
  gap show-me exposed; both argue the other way for rendered figures.
- Diagram guidance should be decided **once** across both repos: the
  strongest combined borrow is dogum's SVG craft rules + copy-SVG device
  (small, invariant-compatible) hardened by diagram-design's connector rules
  and complexity ceiling (the grammar), as one `preset-diagram` /
  inline-SVG-section change to our skill — never two separate imports.

Routing recommendations (recorded in the ledger; adoption edits are a
separate, user-approved step):

- `diagram-design` → **defer**, borrow list named: six connector rules +
  complexity ceiling (`SKILL.md:266-288, 46, 362-404`), accessible-SVG
  contract (`:563-572`), audience dial, fidelity ledger, degrade ladder.
  Explicitly never borrow: Google Fonts stack, `-dark.html` variant model,
  `min-width:900px` templates, the 38-type catalogue description pattern,
  profiles machinery, icon corpus.
- `html-artifacts` → **defer (merge-candidate)**, reject as a shipped unit;
  borrow list named: SVG craft rules + shape-and-color accessibility +
  copy-SVG button; design-system-from-codebase + "any three → restart";
  60–75ch measure; per-preset one-liners (post-mortem "what worked" +
  owners-and-deadlines, plan "explicitly not doing", status "Asks" block,
  marginal glossary, editor pre-fill + keyboard support). Code-review/PR
  category deferred separately until its owner (html-artifact preset vs
  code-review output mode) is decided. Never import: the aggressive
  trigger, CDN allowance, working-dir output, conditional dark mode,
  emoji tags, localStorage permission, decks (no recorded need),
  design-and-prototypes (round-002 UI ruling).

Outcome (see ledger + casebook for the authoritative rulings): round-005
executed the merges — `svg-craft.md` + html-artifact revisions +
`show-me` adopted slash-only. Round-006 then adopted `diagram-design`
**in full** as a user-invoked skill (`disable-model-invocation: true`) on a
user ruling: the never-borrow list above still holds for our own documents —
the installed skill's design system applies only inside explicitly requested
`/diagram-design` deliverables, which the slash-only boundary enforces.
