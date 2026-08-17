# HTML Report Format

The architectural review is rendered as a single self-contained HTML file under `scratchpad/`. No CDN links: styling is an inline `<style>` block and every diagram is hand-built inline SVG (or plain divs), so the file opens offline from `file://`. Graph-shaped relationships become SVG boxes-and-arrows; the more editorial visuals (mass diagrams, cross-sections) are divs/SVG too. Vary the forms — one diagram style everywhere starts to look generic.

## Scaffold

```html
<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <title>Architecture review — {{repo name}}</title>
    <style>
      /* all styling inline — no CDN. Define the handful of utility classes
         the report uses (layout, cards, type scale, accents) here. */
      body { margin: 0; font-family: system-ui, sans-serif; background: #fafaf9; color: #0f172a; }
      main { max-width: 64rem; margin: 0 auto; padding: 3rem 1.5rem; }
      .card { border: 1px solid #e2e8f0; background: #fff; border-radius: .5rem; padding: 1rem; }
      .label { font-size: .75rem; text-transform: uppercase; letter-spacing: .05em; }
      .seam { stroke-dasharray: 4 4; }
      .leak { stroke: #dc2626; }
      .deep { background: linear-gradient(135deg, #0f172a, #1e293b); }
    </style>
  </head>
  <body class="bg-stone-50 text-slate-900 font-sans">
    <main class="max-w-5xl mx-auto px-6 py-12 space-y-12">
      <header>...</header>
      <section id="candidates" class="space-y-10">...</section>
      <section id="top-recommendation">...</section>
    </main>
  </body>
</html>
```

## Header

Repo name, date, and a compact legend: solid box = module, dashed line = seam, red arrow = leakage, thick dark box = deep module. No introduction paragraph — straight into the candidates.

## Candidate card

The diagrams carry the weight. Prose is sparse, plain, and uses the glossary terms (from the `/codebase-design` skill) without ceremony.

Each candidate is one `<article>`:

- **Title** — short, names the deepening (e.g. "Collapse the Order intake pipeline").
- **Badge row** — recommendation strength (`Strong` = emerald, `Worth exploring` = amber, `Speculative` = slate), plus a tag for the dependency category (`in-process`, `local-substitutable`, `ports & adapters`, `mock`).
- **Files** — monospaced list, `font-mono text-sm`.
- **Before / After diagram** — the centrepiece. Two columns, side by side. See patterns below.
- **Problem** — one sentence. What hurts.
- **Solution** — one sentence. What changes.
- **Wins** — bullets, ≤6 words each. e.g. "Tests hit one interface", "Pricing logic stops leaking", "Delete 4 shallow wrappers".
- **ADR callout** (if applicable) — one line in an amber-tinted box.

No paragraphs of explanation. If the diagram needs a paragraph to be understood, redraw the diagram.

## Diagram patterns

Pick the pattern that fits the candidate. Mix them. Don't make every diagram look the same — variety is part of the point.

### Dependency / call-flow graph (the workhorse) — inline SVG

Use a hand-built inline SVG boxes-and-arrows graph when the point is "X calls Y calls Z, and look at the mess." Wrap it in a card so it doesn't feel parachuted in; colour leakage edges red (`.leak`) and the deep module dark (`.deep`). A left-to-right lane sequence works well for "before: 6 round-trips; after: 1."

```html
<div class="card">
  <svg viewBox="0 0 640 120" width="100%" height="120" role="img" aria-label="OrderHandler calls OrderValidator calls OrderRepo, which leaks to PricingClient">
    <rect x="10"  y="40" width="130" height="40" rx="6" fill="#fff" stroke="#334155"/><text x="75"  y="65" text-anchor="middle" class="label">OrderHandler</text>
    <rect x="180" y="40" width="130" height="40" rx="6" fill="#fff" stroke="#334155"/><text x="245" y="65" text-anchor="middle" class="label">OrderValidator</text>
    <rect x="350" y="40" width="110" height="40" rx="6" fill="#fff" stroke="#dc2626"/><text x="405" y="65" text-anchor="middle" class="label">OrderRepo</text>
    <rect x="500" y="40" width="130" height="40" rx="6" fill="#fff" stroke="#dc2626"/><text x="565" y="65" text-anchor="middle" class="label">PricingClient</text>
    <line x1="140" y1="60" x2="180" y2="60" stroke="#334155"/><line x1="310" y1="60" x2="350" y2="60" stroke="#334155"/>
    <line x1="460" y1="60" x2="500" y2="60" class="leak seam" stroke-width="2"/>
  </svg>
</div>
```

### Deep-module "after" view

Modules as `<div>`s with borders and labels, or SVG `<rect>`s. Arrows as inline SVG `<line>` or `<path>` elements. Reach for a thick-bordered outer box with greyed-out internals when you want the "after" diagram to read as one deep module hiding its parts.

### Cross-section (good for layered shallowness)

Stack horizontal bands (`h-12 border-l-4`) to show layers a call passes through. Before: 6 thin layers each doing nothing. After: 1 thick band labelled with the consolidated responsibility.

### Mass diagram (good for "interface as wide as implementation")

Two rectangles per module — one for interface surface area, one for implementation. Before: interface rectangle is nearly as tall as the implementation rectangle (shallow). After: interface rectangle is short, implementation rectangle is tall (deep).

### Call-graph collapse

Before: a tree of function calls rendered as nested boxes. After: the same tree collapsed into one box, with the now-internal calls shown faded inside it.

## Style guidance

- Lean editorial, not corporate-dashboard. Generous whitespace. Serif optional for headings (`font-serif` works well with stone/slate).
- Colour sparingly: one accent (emerald or indigo) plus red for leakage and amber for warnings.
- Keep diagrams ~320px tall so before/after sits comfortably side by side without scrolling.
- Use `text-xs uppercase tracking-wider` for module labels inside diagrams — they should read as schematic, not as UI.
- No scripts, no external requests. The report is static HTML + inline CSS + inline SVG — it must open from `file://` with the network off.

## Top recommendation section

One larger card. Candidate name, one sentence on why, anchor link to its card. That's it.

## Tone

Plain English, concise — but the architectural nouns and verbs come straight from the `/codebase-design` skill. Concision is not an excuse to drift.

**Use exactly:** module, interface, implementation, depth, deep, shallow, seam, adapter, leverage, locality.

**Never substitute:** component, service, unit (for module) · API, signature (for interface) · boundary (for seam) · layer, wrapper (for module, when you mean module).

**Phrasings that fit the style:**

- "Order intake module is shallow — interface nearly matches the implementation."
- "Pricing leaks across the seam."
- "Deepen: one interface, one place to test."
- "Two adapters justify the seam: HTTP in prod, in-memory in tests."

**Wins bullets** name the gain in glossary terms: *"locality: bugs concentrate in one module"*, *"leverage: one interface, N call sites"*, *"interface shrinks; implementation absorbs the wrappers"*. Don't write *"easier to maintain"* or *"cleaner code"* — those terms aren't in the glossary and don't earn their place.

No hedging, no throat-clearing, no "it's worth noting that…". If a sentence could be a bullet, make it a bullet. If a bullet could be cut, cut it. If a term isn't in the `/codebase-design` glossary, reach for one that is before inventing a new one.
