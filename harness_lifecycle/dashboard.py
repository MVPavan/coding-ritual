#!/usr/bin/env python3
"""Render a local, self-contained HTML dashboard for the reference-harness lifecycle,
plus a full per-capability inventory CSV.

Follows the repo's ``html-artifact`` skill (dashboard preset): a KPI row, one
primary inline-SVG chart, a grid of secondary charts, and a collapsed drill-down
table — credible-documentation styling, system fonts, one accent, dark-mode aware,
readable with JS disabled, works double-clicked on ``file://``.

Reads only deterministic local state — the committed ``catalogs/``, our own harness
(``gap.build_ours``), the adoption ``ledger.json``, and beads ``issues.jsonl``. No
network: the pinned picture, not live upstream drift (that is ``/harness-status``).

    python3 harness_lifecycle/dashboard.py [--out PATH]   # writes dashboard.html + dashboard.csv

Fully data-driven and re-runnable. Every number, chart, table and prose note is
derived from whatever catalogs live in ``catalogs/`` — nothing about the harness
set is hardcoded. So:

  * refresh a harness  -> re-catalog it (``scan.py catalog reference_harnesses/<n>
    --out harness_lifecycle/catalogs/<n>.json``) then re-run this; or
  * add a harness      -> add its submodule + drop its catalog in ``catalogs/``,
    then re-run this — the new row/bar/column appear on their own.

The only non-derived text is the single editorial "today's reading" line, read
from an optional ``harness_lifecycle/dashboard-note.html`` (a data-driven status
is shown when that file is absent). Editing the reading is a content edit, never
a code change.
"""

from __future__ import annotations

import argparse
import collections
import csv
import html
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gap  # noqa: E402  (sibling module; path injected above)
import scan  # noqa: E402

HL_DIR = Path(__file__).resolve().parent
REPO_ROOT = HL_DIR.parent
BEADS_JSONL = REPO_ROOT / ".beads" / "issues.jsonl"

KINDS = [
    ("skill", "skills"), ("rule", "rules"), ("agent", "agents"),
    ("command", "commands"), ("hook", "hooks"), ("plugin", "plugins"), ("mcp", "mcp"),
]
KIND_PLURAL = dict(KINDS)


def esc(text: object) -> str:
    return html.escape(str(text), quote=True)


# --- Data ---------------------------------------------------------------------


def load_catalogs() -> list[scan.Catalog]:
    files = sorted((HL_DIR / "catalogs").glob("*.json"))
    return [scan.Catalog.from_dict(json.loads(f.read_text(encoding="utf-8"))) for f in files]


def kind_counts(caps) -> collections.Counter:
    return collections.Counter(c.kind.value for c in caps)


def beads_counts() -> collections.Counter:
    counts: collections.Counter = collections.Counter()
    if BEADS_JSONL.exists():
        for line in BEADS_JSONL.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line:
                try:
                    counts[str(json.loads(line).get("status", "unknown"))] += 1
                except json.JSONDecodeError:
                    pass
    return counts


def distinct_gaps(catalogs: list[scan.Catalog], ours: scan.Catalog) -> int:
    seen: set = set()
    for cat in catalogs:
        for g in gap.compute_gap(cat, ours, None)[0]:
            seen.add((g.cap.kind.value, gap._normalize_name(g.cap.name)))
    return len(seen)


def table_rows(catalogs: list[scan.Catalog], ours: scan.Catalog) -> list[dict]:
    rows = []
    for cat in sorted(catalogs, key=lambda c: len(c.capabilities), reverse=True):
        counts = kind_counts(cat.capabilities)
        n_gap = len(gap.compute_gap(cat, ours, None)[0])
        total = len(cat.capabilities)
        rows.append({
            "harness": cat.repo, "pin": str(cat.source_commit or "")[:10],
            "total": total, "kinds": {k: counts.get(k, 0) for k, _ in KINDS},
            "gap": n_gap, "covered": total - n_gap,
        })
    return rows


# --- Per-capability inventory CSV --------------------------------------------

INVENTORY_COLUMNS = [
    "harness", "kind", "category", "name", "covered",
    "our_equivalent", "similar_to", "decision", "path", "description",
]


def inventory_rows(catalogs: list[scan.Catalog], ours: scan.Catalog) -> list[dict]:
    our_ids = ours.by_logical_id()
    aliases = gap.load_aliases()
    normalized = gap._normalized_index(ours)
    ledger = gap.ledger_index(gap.load_ledger())
    rows: list[dict] = []
    for cat in catalogs:
        for cap in cat.capabilities:
            match = gap.match_to_ours(cap, our_ids, aliases, normalized)
            decision = ledger.get((cat.repo, cap.logical_id))
            rows.append({
                "harness": cat.repo, "kind": cap.kind.value, "category": cap.category,
                "name": cap.name, "covered": "yes" if match else "no",
                "our_equivalent": match or "",
                "similar_to": "" if match else (gap.fuzzy_hint(cap, ours) or ""),
                "decision": str(decision.get("status")) if decision else "",
                "path": cap.canonical_path, "description": cap.description,
            })
    rows.sort(key=lambda r: (r["harness"], r["kind"], r["category"], r["name"]))
    return rows


def write_inventory_csv(rows: list[dict], path: Path) -> None:
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=INVENTORY_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


# --- Inline-SVG charts --------------------------------------------------------

VW = 680          # viewBox width
GUT = 172         # label gutter
PADR = 52         # room for the value label
ROWH = 32
TOP = 8
BARMAX = VW - GUT - PADR


def _svg_open(height: int, aria: str) -> str:
    return (f'<svg viewBox="0 0 {VW} {height}" role="img" aria-label="{esc(aria)}" '
            f'class="chart" preserveAspectRatio="xMinYMin meet">')


def hbar_svg(items: list[tuple[str, int]], aria: str) -> str:
    """Single-series horizontal bars (accent)."""
    maxv = max((v for _, v in items), default=1) or 1
    height = TOP * 2 + len(items) * ROWH
    out = [_svg_open(height, aria)]
    for i, (label, v) in enumerate(items):
        cy = TOP + i * ROWH + ROWH / 2
        w = max(1.0, v / maxv * BARMAX)
        out.append(f'<text x="{GUT - 12}" y="{cy}" class="c-lbl" text-anchor="end">{esc(label)}</text>')
        out.append(f'<rect x="{GUT}" y="{cy - 8:.1f}" width="{w:.1f}" height="16" rx="3" class="c-bar"/>')
        out.append(f'<text x="{GUT + w + 8:.1f}" y="{cy}" class="c-val">{v}</text>')
    out.append("</svg>")
    return "".join(out)


def hbar_split_svg(rows: list[dict], aria: str) -> str:
    """Per-harness bars: neutral track = total, accent-good overlay = covered."""
    maxt = max((r["total"] for r in rows), default=1) or 1
    height = TOP * 2 + len(rows) * ROWH
    out = [_svg_open(height, aria)]
    for i, r in enumerate(rows):
        cy = TOP + i * ROWH + ROWH / 2
        tw = max(1.0, r["total"] / maxt * BARMAX)
        cw = max(0.0, r["covered"] / maxt * BARMAX)
        out.append(f'<text x="{GUT - 12}" y="{cy}" class="c-lbl" text-anchor="end">{esc(r["harness"])}</text>')
        out.append(f'<rect x="{GUT}" y="{cy - 8:.1f}" width="{tw:.1f}" height="16" rx="3" class="c-track"/>')
        if cw > 0:
            out.append(f'<rect x="{GUT}" y="{cy - 8:.1f}" width="{max(2.0, cw):.1f}" height="16" rx="3" class="c-cov"/>')
        out.append(f'<text x="{GUT + tw + 8:.1f}" y="{cy}" class="c-val">{r["total"]}</text>')
    out.append("</svg>")
    return "".join(out)


def kpi(value: object, label: str, sub: str = "", accent: bool = False) -> str:
    cls = "kpi kpi-accent" if accent else "kpi"
    subhtml = f'<div class="kpi-sub">{esc(sub)}</div>' if sub else ""
    return (f'<div class="{cls}"><div class="kpi-n">{esc(value)}</div>'
            f'<div class="kpi-l">{esc(label)}</div>{subhtml}</div>')


def render_table(rows: list[dict], ours_counts: collections.Counter, n_ours: int,
                 n_distinct_gap: int) -> str:
    head = ('<tr><th>Harness</th><th>pin</th><th class="r">total</th>'
            + "".join(f'<th class="r">{esc(lbl)}</th>' for _, lbl in KINDS)
            + '<th class="r">covered</th><th class="r">gap</th></tr>')
    body = []
    for r in rows:
        cells = "".join(f'<td class="r">{r["kinds"][k] or "·"}</td>' for k, _ in KINDS)
        body.append(
            f'<tr><td class="tn">{esc(r["harness"])}</td><td class="mut">{esc(r["pin"])}</td>'
            f'<td class="r"><b>{r["total"]}</b></td>{cells}'
            f'<td class="r good">{r["covered"] or "·"}</td><td class="r">{r["gap"]}</td></tr>'
        )
    totals = {k: sum(r["kinds"][k] for r in rows) for k, _ in KINDS}
    tot_cells = "".join(f'<td class="r">{totals[k]}</td>' for k, _ in KINDS)
    body.append(
        '<tr class="trow"><td class="tn">all references</td><td></td>'
        f'<td class="r"><b>{sum(r["total"] for r in rows)}</b></td>{tot_cells}'
        f'<td class="r good">{sum(r["covered"] for r in rows)}</td>'
        f'<td class="r">{n_distinct_gap}&#8224;</td></tr>'
    )
    ours_cells = "".join(f'<td class="r">{ours_counts.get(k, 0) or "·"}</td>' for k, _ in KINDS)
    body.append(
        '<tr class="orow"><td class="tn">ours</td><td></td>'
        f'<td class="r"><b>{n_ours}</b></td>{ours_cells}'
        '<td class="r">&#8212;</td><td class="r">&#8212;</td></tr>'
    )
    return ('<div class="twrap"><table class="grid"><thead>' + head
            + "</thead><tbody>" + "".join(body) + "</tbody></table></div>"
            '<p class="fn">&#8224; distinct across harnesses — per-row gaps overlap, so '
            "they don't sum to this. Full per-capability inventory (every skill, command, "
            "hook, agent, rule — each tagged covered / not) is exported to "
            "<code>dashboard.csv</code>.</p>")


# --- Narrative notes ----------------------------------------------------------
# All derived from the data so the page never carries a stale fact after a
# harness is added or refreshed. The lone editorial line is externalised.


def primary_note(rows: list[dict], n_ref: int, covered_total: int, n_harness: int) -> str:
    top = rows[0]
    rest = sum(r["total"] for r in rows[1:])
    compare = (f"more than the other {len(rows) - 1} combined"
               if rows[1:] and top["total"] > rest else "the largest single share")
    return (f'One harness — <b>{esc(top["harness"])}</b> — carries {top["total"]} of the '
            f'{n_ref} capabilities, {compare}. Yet the covered slice stays small: across all '
            f'{n_harness} harnesses we hold an equivalent for just <b>{covered_total}</b>.')


def kind_note(mix: collections.Counter) -> str:
    ranked = mix.most_common()
    if not ranked:
        return ""
    lead = " and ".join(KIND_PLURAL.get(k, k) for k, _ in ranked[:2])
    rare = KIND_PLURAL.get(ranked[-1][0], ranked[-1][0])
    return f"{lead[:1].upper()}{lead[1:]} dominate the surveyed surface; {rare} are the rarest."


def cat_note(cat_items: list[tuple[str, int]]) -> str:
    if not cat_items:
        return ""
    name, n = cat_items[0]
    return (f"The largest bucket ({n}) is <b>{esc(name)}</b>; the named groups are where a "
            "candidate's intent — and whether it's worth keeping — shows.")


def today_html(ledger: list[dict], n_gap: int) -> str:
    """The one editorial line: an author-maintained note file if present, else a
    data-driven status so the page is correct even when nobody has updated it."""
    override = HL_DIR / "dashboard-note.html"
    if override.exists():
        return override.read_text(encoding="utf-8")
    by = collections.Counter(str(e.get("status", "?")) for e in ledger)
    decided = (f"{len(ledger)} decisions recorded "
               f"({by.get('adopted', 0)} adopted, {by.get('deferred', 0)} deferred, "
               f"{by.get('rejected', 0)} rejected)" if ledger else "no decisions recorded yet")
    return (f'<span class="tag">{len(ledger)} decisions</span>'
            f'<p>{n_gap:,} distinct capabilities await triage; {decided}. Review candidates with '
            '<code>/harness-scan &lt;harness&gt;</code>; check live upstream drift with '
            '<code>/harness-status</code>.</p>')


# --- Page ---------------------------------------------------------------------


def render(catalogs: list[scan.Catalog], ours: scan.Catalog) -> str:
    ref_caps = [c for cat in catalogs for c in cat.capabilities]
    mix = kind_counts(ref_caps)
    ours_counts = kind_counts(ours.capabilities)
    n_ours = len(ours.capabilities)
    n_gap = distinct_gaps(catalogs, ours)
    rows = table_rows(catalogs, ours)
    beads = beads_counts()
    ledger = gap.load_ledger()
    n_adopted = len(ledger)
    covered_total = sum(r["covered"] for r in rows)

    cat_dist: collections.Counter = collections.Counter()
    for c in ref_caps:
        if c.kind.value == "skill":
            cat_dist[c.category or "(none)"] += 1
    cat_items = [("ungrouped" if n == "skills" else n, v) for n, v in cat_dist.most_common()]

    kpis = "".join([
        kpi(f"{len(ref_caps):,}", "capabilities surveyed", f"across {len(catalogs)} harnesses", accent=True),
        kpi(n_ours, "in our harness", "the baseline we compare to"),
        kpi(f"{covered_total}", "already covered", f"of {len(ref_caps):,} — {round(covered_total/len(ref_caps)*100)}%"),
        kpi(f"{n_gap:,}", "distinct gaps", "pre-triage · deduped"),
        kpi(n_adopted, "adopted by reflex", "default is reject / defer"),
    ])

    primary = hbar_split_svg(rows, "Capabilities per harness, with the covered share highlighted")
    mix_chart = hbar_svg([(lbl, mix.get(k, 0)) for k, lbl in KINDS if mix.get(k)],
                         "Reference capabilities by kind")
    cat_chart = hbar_svg(cat_items, "Reference skills by grouping category")
    table = render_table(rows, ours_counts, n_ours, n_gap)

    return TEMPLATE.format(
        style=STYLE, kpis=kpis, primary=primary, mix_chart=mix_chart,
        cat_chart=cat_chart, table=table, n_harness=len(catalogs),
        primary_note=primary_note(rows, len(ref_caps), covered_total, len(catalogs)),
        kind_note=kind_note(mix), cat_note=cat_note(cat_items),
        today=today_html(ledger, n_gap),
        n_work=sum(beads.values()), n_closed=beads.get("closed", 0),
    )


STYLE = """
:root{
  --bg:#f6f7f9; --surface:#ffffff; --text:#1b1e23; --muted:#6a717c; --border:#e5e7eb;
  --accent:#3b5bd9; --accent-weak:#eaeefc; --good:#2f9e57; --track:#e7eaee;
  --shadow:0 1px 2px rgba(20,24,31,.05);
  --s1:.5rem; --s2:1rem; --s3:1.5rem; --s4:2rem; --s5:3rem; --max:960px;
  --sans:system-ui,-apple-system,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;
  --mono:ui-monospace,"SF Mono","JetBrains Mono",Menlo,Consolas,monospace;
}
@media (prefers-color-scheme:dark){:root{
  --bg:#0f1114; --surface:#16191d; --text:#e7eaee; --muted:#949aa4; --border:#252a30;
  --accent:#8098f6; --accent-weak:#1a2033; --good:#5cc47e; --track:#232830;
  --shadow:0 1px 2px rgba(0,0,0,.4);
}}
*{box-sizing:border-box}
html,body{margin:0}
body{background:var(--bg);color:var(--text);font-family:var(--sans);line-height:1.6;
  -webkit-font-smoothing:antialiased}
.wrap{max-width:var(--max);margin:0 auto;padding:var(--s5) var(--s3) var(--s5)}
.wrap *{margin:0}
.tab{font-variant-numeric:tabular-nums}

header.doc{margin-bottom:var(--s4)}
.kicker{font-size:.74rem;font-weight:600;letter-spacing:.08em;text-transform:uppercase;color:var(--accent)}
h1{font-size:1.9rem;font-weight:680;letter-spacing:-.02em;margin:.5rem 0 .4rem;text-wrap:balance}
.sub{color:var(--muted);max-width:64ch;font-size:1.02rem}
.meta{margin-top:.9rem;font-family:var(--mono);font-size:.74rem;color:var(--muted)}

.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:var(--s2);margin-bottom:var(--s5)}
.kpi{background:var(--surface);border:1px solid var(--border);border-radius:10px;padding:var(--s2) 1.1rem;box-shadow:var(--shadow)}
.kpi-n{font-size:1.95rem;font-weight:680;letter-spacing:-.02em;font-variant-numeric:tabular-nums;line-height:1.05}
.kpi-accent{border-color:color-mix(in srgb,var(--accent) 40%,var(--border))}
.kpi-accent .kpi-n{color:var(--accent)}
.kpi-l{margin-top:.4rem;font-size:.86rem;font-weight:560}
.kpi-sub{font-size:.75rem;color:var(--muted);margin-top:.1rem}

section{margin-top:var(--s5)}
.sh{display:flex;align-items:baseline;gap:.7rem;padding-bottom:.6rem;margin-bottom:var(--s3);border-bottom:1px solid var(--border)}
.sh .no{font-family:var(--mono);font-size:.9rem;font-weight:700;color:var(--muted)}
.sh h2{font-size:1.12rem;font-weight:640}

.card{background:var(--surface);border:1px solid var(--border);border-radius:10px;padding:1.3rem 1.4rem;box-shadow:var(--shadow)}
.cap{font-size:.82rem;font-weight:600;margin-bottom:.15rem}
.cap .win{color:var(--muted);font-weight:400}
.note{font-size:.85rem;color:var(--muted);margin-top:.7rem;max-width:74ch}
.note b{color:var(--text);font-weight:600}
.legend{display:flex;gap:1.1rem;margin-top:.8rem;font-size:.78rem;color:var(--muted)}
.legend i{width:11px;height:11px;border-radius:3px;display:inline-block;margin-right:.4rem;vertical-align:middle}

.grid2{display:grid;grid-template-columns:1fr 1fr;gap:var(--s3)}
@media(max-width:720px){.grid2{grid-template-columns:1fr}}

.chart{width:100%;height:auto;display:block}
.chart text{font-family:var(--sans)}
.c-lbl{fill:var(--muted);font-size:12px}
.c-val{fill:var(--text);font-size:12px;font-weight:600;font-variant-numeric:tabular-nums}
.c-bar{fill:var(--accent)}
.c-track{fill:var(--track)}
.c-cov{fill:var(--good)}

.today p{max-width:74ch;margin-bottom:.7rem}
.today p:last-child{margin-bottom:0}
.today .dim{color:var(--muted);font-size:.9rem}
code{font-family:var(--mono);font-size:.86em;background:var(--accent-weak);color:var(--accent);padding:.06em .38em;border-radius:5px}
.tag{display:inline-block;font-size:.74rem;font-weight:700;letter-spacing:.02em;padding:.22em .7em;border-radius:99px;
  background:var(--accent-weak);color:var(--accent);margin-bottom:.9rem}

details.drill{margin-top:var(--s3);border:1px solid var(--border);border-radius:10px;background:var(--surface);overflow:hidden}
details.drill>summary{cursor:pointer;padding:.9rem 1.2rem;font-weight:600;font-size:.9rem;list-style:none}
details.drill>summary::-webkit-details-marker{display:none}
details.drill>summary::before{content:"▸ ";color:var(--muted)}
details.drill[open]>summary::before{content:"▾ "}
.dbody{padding:0 1.2rem 1.2rem}
.twrap{overflow-x:auto}
.grid{width:100%;border-collapse:collapse;font-size:.82rem;min-width:640px}
.grid th{text-align:left;font-weight:600;font-size:.74rem;padding:.55rem .6rem;border-bottom:2px solid var(--text);white-space:nowrap}
.grid td{padding:.48rem .6rem;border-bottom:1px solid var(--border);font-variant-numeric:tabular-nums}
.grid tbody tr:last-child td{border-bottom:none}
.grid .r{text-align:right}
.grid .tn{font-weight:600;white-space:nowrap}
.grid .mut{color:var(--muted);font-family:var(--mono);font-size:.92em}
.grid .good{color:var(--good);font-weight:600}
.grid tbody tr:hover td{background:color-mix(in srgb,var(--accent) 5%,transparent)}
.grid .trow td{border-top:2px solid var(--text);border-bottom:none;font-weight:700}
.grid .trow:hover td,.grid .orow:hover td{background:transparent}
.grid .orow td{color:var(--muted);background:var(--accent-weak)}
.fn{font-size:.76rem;color:var(--muted);margin-top:.7rem;max-width:78ch}

.foot{margin-top:var(--s5);padding-top:var(--s2);border-top:1px solid var(--border);
  font-family:var(--mono);font-size:.73rem;color:var(--muted);line-height:1.7}
"""

TEMPLATE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Harness lifecycle — reference-harness curation dashboard</title>
<style>{style}</style>
</head>
<body>
<main class="wrap">
  <header class="doc">
    <div class="kicker">Reference-harness curation · pinned survey</div>
    <h1>Harness lifecycle dashboard</h1>
    <p class="sub">Every capability the tracked agent-harnesses ship, catalogued and measured
      against our own — so nothing is adopted by reflex, only by decision.</p>
    <div class="meta">source: harness_lifecycle/catalogs · ours: .claude + .codex + plugins · no network · regenerate: python3 harness_lifecycle/dashboard.py</div>
  </header>

  <div class="kpis">
{kpis}
  </div>

  <section>
    <div class="sh"><span class="no">01</span><h2>Capabilities per harness</h2></div>
    <div class="card">
      <div class="cap">Logical capabilities at our pin <span class="win">· green = we already have an equivalent</span></div>
      {primary}
      <div class="legend"><span><i class="c-track" style="background:var(--track)"></i>total</span>
        <span><i class="c-cov" style="background:var(--good)"></i>covered by ours</span></div>
      <p class="note">{primary_note}</p>
    </div>
  </section>

  <section>
    <div class="sh"><span class="no">02</span><h2>What's out there</h2></div>
    <div class="grid2">
      <div class="card">
        <div class="cap">Reference capabilities by kind</div>
        {mix_chart}
        <p class="note">{kind_note}</p>
      </div>
      <div class="card">
        <div class="cap">Reference skills by grouping</div>
        {cat_chart}
        <p class="note">{cat_note}</p>
      </div>
    </div>
  </section>

  <section>
    <div class="sh"><span class="no">03</span><h2>Today's reading</h2></div>
    <div class="card today">
      {today}
    </div>
  </section>

  <details class="drill">
    <summary>By the numbers — per-harness figures &amp; raw data</summary>
    <div class="dbody">
      {table}
    </div>
  </details>

  <div class="foot">work items tracked in beads: {n_work} ({n_closed} closed) · gaps exclude ledgered decisions · pinned, deterministic, no network</div>
</main>
</body>
</html>
"""


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", default=str(HL_DIR / "dashboard.html"),
                        help="output HTML path (default: harness_lifecycle/dashboard.html)")
    args = parser.parse_args(argv)
    catalogs = load_catalogs()
    if not catalogs:
        print("no catalogs under harness_lifecycle/catalogs/", file=sys.stderr)
        return 1
    ours = gap.build_ours()
    out = Path(args.out)
    out.write_text(render(catalogs, ours), encoding="utf-8")

    csv_path = out.with_suffix(".csv")
    inventory = inventory_rows(catalogs, ours)
    write_inventory_csv(inventory, csv_path)
    covered = sum(1 for r in inventory if r["covered"] == "yes")
    print(f"wrote {out} + {csv_path.name} "
          f"({len(catalogs)} harnesses, {len(inventory)} capabilities, "
          f"{covered} covered / {len(inventory) - covered} not)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
