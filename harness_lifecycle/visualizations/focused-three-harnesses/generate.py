#!/usr/bin/env python3
"""Generate the focused three-harness review dashboard and review CSV."""

from __future__ import annotations

import argparse
import collections
import csv
import html
import json
import os
from pathlib import Path
from typing import Any


VIZ_DIR = Path(__file__).resolve().parent
HL_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = HL_DIR / "codex_analysis" / "focused-three-harnesses"
EXPECTED_HARNESSES = ("agent-skills", "mattpocock_skills", "superpowers")
EXPECTED_COUNTS = {
    "unique": 97,
    "included": 94,
    "excluded": 3,
    "clusters": 30,
}
SCORE_FIELDS = (
    "effectiveness",
    "instruction_quality",
    "clarity",
    "precision",
    "concision",
    "structural_efficiency",
)

CSV_FIELDS = (
    "cluster_id",
    "priority",
    "decision",
    "recommended_capability",
    "recommended_surface",
    "source_count",
    "average_score",
    "selected_harnesses",
    "source_ids",
    "source_names",
    "source_verdicts",
    "source_average_scores",
    "row_verdicts",
    "problem_solved",
    "why_this_is_better",
    "reuse_or_merge_plan",
    "risks_or_open_questions",
)


def esc(value: Any) -> str:
    return html.escape(str(value), quote=True)


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def load_data() -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    scope = load_json(DATA_DIR / "scope.json")
    cluster_data = load_json(DATA_DIR / "clusters.json")
    evaluations = load_jsonl(DATA_DIR / "row_evaluations.jsonl")
    clusters = cluster_data["clusters"]

    assert tuple(scope["requested_harnesses"]) == EXPECTED_HARNESSES
    assert scope["unique_canonical_rows"] == EXPECTED_COUNTS["unique"]
    assert scope["included_evaluation_rows"] == EXPECTED_COUNTS["included"]
    assert scope["excluded_rows"] == EXPECTED_COUNTS["excluded"]
    assert scope["focused_clusters"] == EXPECTED_COUNTS["clusters"]
    assert len(evaluations) == EXPECTED_COUNTS["included"]
    assert len(clusters) == EXPECTED_COUNTS["clusters"]

    evaluation_ids = [str(row["source_id"]) for row in evaluations]
    clustered_ids = [str(source_id) for cluster in clusters for source_id in cluster["source_ids"]]
    assert len(evaluation_ids) == len(set(evaluation_ids)) == EXPECTED_COUNTS["included"]
    assert len(clustered_ids) == len(set(clustered_ids)) == EXPECTED_COUNTS["included"]
    assert set(evaluation_ids) == set(clustered_ids)
    assert len(scope["excluded_source_ids"]) == EXPECTED_COUNTS["excluded"]
    return scope, clusters, evaluations


def selected_harnesses(cluster: dict[str, Any]) -> list[str]:
    present = {
        harness
        for harness_list in cluster["source_harnesses"].values()
        for harness in harness_list
    }
    return [harness for harness in EXPECTED_HARNESSES if harness in present]


def row_score(row: dict[str, Any]) -> float:
    return sum(int(row[field]) for field in SCORE_FIELDS) / len(SCORE_FIELDS)


def review_rows(
    clusters: list[dict[str, Any]], evaluation_by_id: dict[str, dict[str, Any]]
) -> list[dict[str, Any]]:
    rows = []
    for cluster in clusters:
        rows.append(
            {
                "cluster_id": cluster["cluster_id"],
                "priority": cluster["priority"],
                "decision": cluster["decision"],
                "recommended_capability": cluster["recommended_capability"],
                "recommended_surface": cluster["recommended_surface"],
                "source_count": cluster["source_count"],
                "average_score": cluster["average_score"],
                "selected_harnesses": "; ".join(selected_harnesses(cluster)),
                "source_ids": "; ".join(cluster["source_ids"]),
                "source_names": "; ".join(cluster["source_names"]),
                "source_verdicts": "; ".join(
                    f"{source_id}:{evaluation_by_id[source_id]['actual_usefulness_verdict']}"
                    for source_id in cluster["source_ids"]
                ),
                "source_average_scores": "; ".join(
                    f"{source_id}:{row_score(evaluation_by_id[source_id]):.2f}"
                    for source_id in cluster["source_ids"]
                ),
                "row_verdicts": "; ".join(
                    f"{key}:{value}" for key, value in cluster["verdict_counts"].items()
                ),
                "problem_solved": cluster["problem_solved"],
                "why_this_is_better": cluster["why_this_is_better"],
                "reuse_or_merge_plan": cluster["reuse_or_merge_plan"],
                "risks_or_open_questions": cluster["risks_or_open_questions"],
            }
        )
    return rows


def write_review_csv(rows: list[dict[str, Any]], path: Path) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def horizontal_bars(items: list[tuple[str, int]], aria: str, *, accent: bool = True) -> str:
    width = 680
    gutter = 176
    right = 50
    row_height = 34
    top = 8
    maximum = max((value for _, value in items), default=1) or 1
    bar_max = width - gutter - right
    height = top * 2 + row_height * len(items)
    pieces = [
        f'<svg class="chart" viewBox="0 0 {width} {height}" role="img" '
        f'aria-label="{esc(aria)}" preserveAspectRatio="xMinYMin meet">',
        f'<title>{esc(aria)}</title>',
        f'<desc>{esc("; ".join(f"{label}: {value}" for label, value in items))}</desc>',
    ]
    bar_class = "bar accent" if accent else "bar neutral"
    for index, (label, value) in enumerate(items):
        center = top + index * row_height + row_height / 2
        bar_width = max(2.0, value / maximum * bar_max)
        pieces.append(
            f'<text class="chart-label" x="{gutter - 12}" y="{center}" '
            f'text-anchor="end">{esc(label)}</text>'
        )
        pieces.append(
            f'<rect class="{bar_class}" x="{gutter}" y="{center - 8:.1f}" '
            f'width="{bar_width:.1f}" height="16" rx="3"></rect>'
        )
        pieces.append(
            f'<text class="chart-value" x="{gutter + bar_width + 8:.1f}" '
            f'y="{center}">{value}</text>'
        )
    pieces.append("</svg>")
    return "".join(pieces)


def cluster_size_counts(clusters: list[dict[str, Any]]) -> list[tuple[str, int]]:
    counts = collections.Counter()
    for cluster in clusters:
        size = int(cluster["source_count"])
        if size == 1:
            counts["1 source"] += 1
        elif size <= 3:
            counts["2–3 sources"] += 1
        elif size <= 6:
            counts["4–6 sources"] += 1
        else:
            counts["7+ sources"] += 1
    return [(label, counts[label]) for label in ("1 source", "2–3 sources", "4–6 sources", "7+ sources")]


def decision_class(decision: str) -> str:
    return "decision-" + decision.replace("_", "-")


def shortlist(clusters: list[dict[str, Any]]) -> str:
    groups = [
        ("P1 review first", [cluster for cluster in clusters if cluster["priority"] == "P1"]),
        ("Needs adaptation", [cluster for cluster in clusters if cluster["decision"] == "adapt"]),
        ("Deferred", [cluster for cluster in clusters if cluster["decision"] == "defer"]),
        (
            "Rejected after review",
            [cluster for cluster in clusters if cluster["decision"] == "reject_after_review"],
        ),
    ]
    cards = []
    for title, members in groups:
        links = "".join(
            f'<li><a href="#{esc(cluster["cluster_id"])}">'
            f'{esc(cluster["recommended_capability"])}</a>'
            f'<span class="mini">{esc(cluster["decision"])} · {esc(cluster["priority"])}</span></li>'
            for cluster in members
        )
        cards.append(
            f'<article class="short-card"><h3>{esc(title)} <span>{len(members)}</span></h3>'
            f'<ul>{links or "<li class=\"muted\">None</li>"}</ul></article>'
        )
    return "".join(cards)


def source_list(
    cluster: dict[str, Any], evaluation_by_id: dict[str, dict[str, Any]]
) -> str:
    items = []
    for source_id, name in zip(cluster["source_ids"], cluster["source_names"], strict=True):
        evaluation = evaluation_by_id[source_id]
        harness_text = ", ".join(cluster["source_harnesses"][source_id])
        items.append(
            f'<li><code>{esc(source_id)}</code> — {esc(name)}'
            f'<span class="source-harness">{esc(harness_text)} · {esc(evaluation["kind"])} · '
            f'{esc(evaluation["actual_usefulness_verdict"])} · score {row_score(evaluation):.2f}</span>'
            f'<span class="source-rationale">{esc(evaluation["rationale"])}</span></li>'
        )
    return "".join(items)


def cluster_table(
    clusters: list[dict[str, Any]], evaluation_by_id: dict[str, dict[str, Any]]
) -> str:
    rows = []
    for cluster in clusters:
        harness_list = selected_harnesses(cluster)
        search = " ".join(
            [
                cluster["cluster_id"],
                cluster["recommended_capability"],
                cluster["recommended_surface"],
                cluster["problem_solved"],
                cluster["why_this_is_better"],
                cluster["reuse_or_merge_plan"],
                cluster["risks_or_open_questions"],
                *cluster["source_ids"],
                *cluster["source_names"],
                *harness_list,
            ]
        ).lower()
        verdict_text = ", ".join(
            f"{key}: {value}" for key, value in cluster["verdict_counts"].items()
        )
        details = f"""
          <details>
            <summary>Evidence and recommendation</summary>
            <div class="detail-grid">
              <div><h4>Problem solved</h4><p>{esc(cluster['problem_solved'])}</p></div>
              <div><h4>Why this recommendation</h4><p>{esc(cluster['why_this_is_better'])}</p></div>
              <div><h4>Reuse or merge plan</h4><p>{esc(cluster['reuse_or_merge_plan'])}</p></div>
              <div><h4>Risks and open questions</h4><p>{esc(cluster['risks_or_open_questions'])}</p></div>
            </div>
            <h4>All selected sources</h4>
            <ul class="sources">{source_list(cluster, evaluation_by_id)}</ul>
            <p class="evidence-meta">Row verdicts: {esc(verdict_text)} · candidate keys: {esc(', '.join(cluster['candidate_cluster_keys']))}</p>
          </details>"""
        rows.append(
            f"""<tr id="{esc(cluster['cluster_id'])}" data-decision="{esc(cluster['decision'])}"
                data-priority="{esc(cluster['priority'])}" data-harnesses="{esc(' '.join(harness_list))}"
                data-search="{esc(search)}">
              <td data-label="Priority"><span class="priority {esc(cluster['priority'].lower())}">{esc(cluster['priority'])}</span></td>
              <td data-label="Decision"><span class="decision {decision_class(cluster['decision'])}">{esc(cluster['decision'])}</span></td>
              <td data-label="Recommended capability" class="capability"><strong>{esc(cluster['recommended_capability'])}</strong>
                <span>{esc(cluster['recommended_surface'])}</span><code>{esc(cluster['cluster_id'])}</code></td>
              <td data-label="Sources" class="number">{cluster['source_count']}<span>{esc(', '.join(harness_list))}</span></td>
              <td data-label="Average score" class="number">{float(cluster['average_score']):.2f}<span>{esc(verdict_text)}</span></td>
              <td data-label="Review detail">{details}</td>
            </tr>"""
        )
    return "".join(rows)


def exclusions(scope: dict[str, Any]) -> str:
    excluded = [
        row for row in scope["inventory"] if row["synthesis_status"] == "excluded_both_rejected"
    ]
    return "".join(
        f'<tr><td data-label="Source ID"><code>{esc(row["source_id"])}</code></td>'
        f'<td data-label="Name">{esc(row["name"])}</td>'
        f'<td data-label="Harness">{esc(", ".join(row["selected_harnesses"]))}</td>'
        '<td data-label="Status"><span class="decision decision-reject-after-review">excluded by both shallow reviews</span></td></tr>'
        for row in excluded
    )


def render(
    scope: dict[str, Any],
    clusters: list[dict[str, Any]],
    evaluations: list[dict[str, Any]],
    *,
    visualizations_href: str,
    review_csv_href: str,
    synthesis_href: str,
) -> str:
    decisions = collections.Counter(cluster["decision"] for cluster in clusters)
    priorities = collections.Counter(cluster["priority"] for cluster in clusters)
    kinds = collections.Counter(row["kind"] for row in evaluations)
    verdicts = collections.Counter(row["actual_usefulness_verdict"] for row in evaluations)
    repository_counts = scope["repository_row_counts"]
    p1_count = priorities["P1"]
    evaluation_by_id = {str(row["source_id"]): row for row in evaluations}

    decision_chart = horizontal_bars(sorted(decisions.items()), "Focused cluster decisions")
    priority_chart = horizontal_bars(
        [(priority, priorities[priority]) for priority in ("P1", "P2", "P3")],
        "Focused cluster priorities",
        accent=False,
    )
    repository_chart = horizontal_bars(
        [(repo, repository_counts[repo]) for repo in EXPECTED_HARNESSES],
        "Canonical rows by selected reference harness",
        accent=False,
    )
    kind_chart = horizontal_bars(sorted(kinds.items(), key=lambda item: (-item[1], item[0])), "Rows by capability kind")
    verdict_chart = horizontal_bars(sorted(verdicts.items()), "Deep row verdicts", accent=False)
    size_chart = horizontal_bars(cluster_size_counts(clusters), "Focused clusters by source count", accent=False)

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Focused harness synthesis review</title>
  <script>document.documentElement.classList.add('js')</script>
  <style>
    :root {{
      color-scheme: light dark; --bg:#f5f7f9; --surface:#fff; --surface-2:#f9fafb;
      --text:#1f242c; --muted:#69727e; --border:#dfe4ea; --accent:#355fc9;
      --accent-soft:#edf2ff; --green:#287a4b; --green-soft:#eaf6ef; --amber:#98680d;
      --amber-soft:#fff4d8; --red:#a63b35; --red-soft:#fdecea; --space-1:.5rem;
      --space-2:1rem; --space-3:1.5rem; --space-4:2rem;
      font-family:system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;
    }}
    @media(prefers-color-scheme:dark){{:root{{--bg:#0f1216;--surface:#171b20;--surface-2:#1c2128;
      --text:#e7eaee;--muted:#9ca5b1;--border:#2b323b;--accent:#8da7ff;--accent-soft:#202a48;
      --green:#70cd92;--green-soft:#183126;--amber:#e0b45c;--amber-soft:#342a15;
      --red:#ee887f;--red-soft:#3b211f;}}}}
    *{{box-sizing:border-box}} html{{scroll-behavior:smooth}} body{{margin:0;background:var(--bg);color:var(--text);line-height:1.55}}
    main{{max-width:1440px;margin:auto;padding:2.5rem 1.5rem 5rem}} a{{color:var(--accent)}}
    .topline{{display:flex;justify-content:space-between;gap:1rem;align-items:center;color:var(--muted);font-size:.8rem}}
    .kicker{{color:var(--accent);font-weight:750;letter-spacing:.09em;text-transform:uppercase}}
    h1{{font-size:clamp(2rem,4vw,3.3rem);line-height:1.08;letter-spacing:-.04em;margin:.55rem 0 .75rem}}
    .lede{{max-width:78ch;color:var(--muted);font-size:1.02rem}}
    .kpis{{display:grid;grid-template-columns:repeat(5,minmax(130px,1fr));gap:1rem;margin:2rem 0}}
    .kpi{{background:var(--surface);border:1px solid var(--border);border-radius:10px;padding:1rem}}
    .kpi.primary{{border-color:color-mix(in srgb,var(--accent) 45%,var(--border))}} .kpi strong{{display:block;font-size:2rem;line-height:1;font-variant-numeric:tabular-nums}}
    .kpi.primary strong{{color:var(--accent)}} .kpi span{{display:block;color:var(--muted);font-size:.78rem;margin-top:.45rem}}
    .section{{margin-top:3rem}} .section-head{{display:flex;align-items:end;gap:1rem;border-bottom:1px solid var(--border);padding-bottom:.65rem;margin-bottom:1.25rem}}
    .section-no{{color:var(--muted);font:700 1.6rem/1 ui-monospace,SFMono-Regular,Menlo,monospace}} h2{{font-size:1.35rem;margin:0;letter-spacing:-.02em}}
    .chart-grid{{display:grid;grid-template-columns:1.15fr .85fr;gap:1.25rem}} .secondary{{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:1.25rem;margin-top:1.25rem}}
    .card{{background:var(--surface);border:1px solid var(--border);border-radius:10px;padding:1.1rem 1.2rem;overflow:auto}}
    .card h3{{font-size:.9rem;margin:0 0 .75rem}} .caption{{color:var(--muted);font-size:.78rem;margin:.55rem 0 0}}
    .chart{{display:block;width:100%;height:auto;max-height:360px}} .bar{{fill:var(--accent)}} .bar.neutral{{fill:color-mix(in srgb,var(--muted) 45%,var(--border))}}
    .chart-label,.chart-value{{fill:var(--muted);font:12px system-ui,sans-serif;dominant-baseline:middle}} .chart-value{{fill:var(--text);font-weight:700}}
    .short-grid{{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:1rem}} .short-card{{background:var(--surface);border:1px solid var(--border);border-radius:10px;padding:1rem}}
    .short-card h3{{font-size:.85rem;margin:0 0 .75rem}} .short-card h3 span{{color:var(--muted);font-weight:500}} .short-card ul{{margin:0;padding-left:1.1rem}}
    .short-card li{{margin:.42rem 0;font-size:.82rem}} .short-card a{{color:var(--text);font-weight:650}} .mini{{display:block;color:var(--muted);font-size:.7rem}} .review-guide{{margin-top:1rem}}
    .controls{{display:none;grid-template-columns:minmax(220px,2fr) repeat(3,minmax(140px,1fr)) auto;gap:.75rem;align-items:end;background:var(--surface);border:1px solid var(--border);border-radius:10px;padding:1rem;margin-bottom:1rem;position:sticky;top:.5rem;z-index:5}} .js .controls{{display:grid}}
    label{{display:block;color:var(--muted);font-size:.72rem;font-weight:700}} input,select,button{{width:100%;margin-top:.3rem;padding:.62rem .7rem;border:1px solid var(--border);border-radius:7px;background:var(--surface-2);color:var(--text);font:inherit}}
    button{{width:auto;cursor:pointer;color:var(--accent);font-weight:700}} .result-count{{display:none;color:var(--muted);font-size:.8rem;margin:.5rem 0}} .js .result-count{{display:block}}
    .table-wrap{{overflow:auto;border:1px solid var(--border);border-radius:10px;background:var(--surface)}} table{{width:100%;border-collapse:collapse;min-width:1050px}}
    th{{position:sticky;top:0;background:var(--surface-2);z-index:2;text-align:left;color:var(--muted);font-size:.7rem;letter-spacing:.05em;text-transform:uppercase}}
    th,td{{padding:.85rem;border-bottom:1px solid var(--border);vertical-align:top}} tbody tr:last-child td{{border-bottom:0}} tbody tr:target{{background:var(--accent-soft)}}
    .number{{text-align:right;font-variant-numeric:tabular-nums;font-weight:750}} .number span{{display:block;max-width:170px;color:var(--muted);font-size:.68rem;font-weight:400}}
    .capability{{min-width:260px}} .capability strong,.capability span,.capability code{{display:block}} .capability span{{color:var(--muted);font-size:.78rem;margin:.2rem 0}} code{{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;font-size:.76em}}
    .decision,.priority{{display:inline-block;border-radius:999px;padding:.2rem .52rem;font-size:.68rem;font-weight:750;white-space:nowrap}}
    .decision-merge{{color:var(--green);background:var(--green-soft)}} .decision-adapt,.decision-defer{{color:var(--amber);background:var(--amber-soft)}} .decision-reject-after-review{{color:var(--red);background:var(--red-soft)}}
    .priority{{color:var(--accent);background:var(--accent-soft)}} .p3{{color:var(--muted);background:var(--surface-2)}}
    details summary{{cursor:pointer;color:var(--accent);font-size:.78rem;font-weight:700}} .detail-grid{{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:.75rem;margin:.85rem 0}}
    .detail-grid div{{background:var(--surface-2);border-radius:7px;padding:.75rem}} h4{{font-size:.74rem;margin:0 0 .35rem}} .detail-grid p{{font-size:.8rem;margin:0;color:var(--muted)}}
    .sources{{padding-left:1.1rem;max-height:320px;overflow:auto}} .sources li{{margin:.55rem 0;font-size:.78rem}} .source-harness,.source-rationale{{display:block;color:var(--muted);font-size:.68rem}} .source-rationale{{margin-top:.15rem;max-width:90ch}}
    .evidence-meta,.muted{{color:var(--muted);font-size:.74rem}} .excluded{{margin-top:1.25rem}} footer{{margin-top:2.5rem;color:var(--muted);font-size:.78rem;border-top:1px solid var(--border);padding-top:1rem}}
    [hidden]{{display:none!important}}
    @media(max-width:980px){{.kpis{{grid-template-columns:repeat(3,1fr)}}.chart-grid,.secondary,.short-grid{{grid-template-columns:1fr 1fr}}.controls{{grid-template-columns:1fr 1fr}}}}
    @media(max-width:720px){{main{{padding:1.5rem .85rem 3rem}}.topline{{display:block}}.kpis,.chart-grid,.secondary,.short-grid,.detail-grid,.controls{{grid-template-columns:1fr}}.controls{{position:static}}h1{{font-size:2.2rem}}.chart{{min-width:600px}}.review-table,.exclusion-table{{min-width:0}}.review-table thead,.exclusion-table thead{{display:none}}.review-table tbody,.review-table tr,.review-table td,.exclusion-table tbody,.exclusion-table tr,.exclusion-table td{{display:block;width:100%}}.review-table tr,.exclusion-table tr{{padding:.55rem .8rem;border-bottom:1px solid var(--border)}}.review-table td,.exclusion-table td{{border:0;padding:.38rem 0;text-align:left}}.review-table td::before,.exclusion-table td::before{{content:attr(data-label);display:block;color:var(--muted);font-size:.65rem;font-weight:700;letter-spacing:.05em;text-transform:uppercase;margin-bottom:.18rem}}.review-table .number span{{max-width:none}}}}
  </style>
</head>
<body>
<main>
  <header>
    <div class="topline"><span class="kicker">Focused synthesis review</span><a href="{esc(visualizations_href)}">All visualizations</a></div>
    <h1>Three reference harnesses, one review surface.</h1>
    <p class="lede">A focused Codex synthesis of <code>agent-skills</code>, <code>mattpocock_skills</code>, and <code>superpowers</code>. Use the shortlist to orient, then filter the complete table to challenge decisions, priorities, merge plans, and risks. Nothing here changes the adoption ledger.</p>
  </header>

  <section class="kpis" aria-label="Scope summary">
    <div class="kpi primary"><strong>{scope['unique_canonical_rows']}</strong><span>unique canonical rows</span></div>
    <div class="kpi"><strong>{scope['included_evaluation_rows']}</strong><span>deep evaluations</span></div>
    <div class="kpi"><strong>{scope['focused_clusters']}</strong><span>problem clusters</span></div>
    <div class="kpi"><strong>{scope['excluded_rows']}</strong><span>explicit exclusions</span></div>
    <div class="kpi"><strong>{p1_count}</strong><span>P1 clusters to review first</span></div>
  </section>

  <section class="section">
    <div class="section-head"><span class="section-no">01</span><h2>Recommendation shape</h2></div>
    <div class="chart-grid">
      <article class="card"><h3>Cluster decisions</h3>{decision_chart}<p class="caption">Most selected evidence should merge into existing workflows; adaptation is reserved for useful capabilities without a proven local owner.</p></article>
      <article class="card"><h3>Adoption-review priority</h3>{priority_chart}<p class="caption">Priority measures remaining adoption work, not the abstract importance of the capability.</p></article>
    </div>
    <div class="secondary">
      <article class="card"><h3>Canonical rows by requested harness</h3>{repository_chart}<p class="caption">Counts overlap where one canonical row is shared by more than one requested harness.</p></article>
      <article class="card"><h3>Included rows by capability kind</h3>{kind_chart}</article>
      <article class="card"><h3>Deep row verdicts</h3>{verdict_chart}</article>
      <article class="card"><h3>Cluster evidence breadth</h3>{size_chart}</article>
    </div>
  </section>

  <section class="section">
    <div class="section-head"><span class="section-no">02</span><h2>Review shortlist</h2></div>
    <div class="short-grid">{shortlist(clusters)}</div>
    <details class="card review-guide" open>
      <summary>How to challenge each recommendation</summary>
      <ol class="evidence-meta">
        <li>Does the selected source evidence actually support the decision, or was a useful pattern promoted into a new surface?</li>
        <li>For every merge, is the named local owner real and still the best owner?</li>
        <li>Does priority measure remaining adoption work rather than general capability importance?</li>
        <li>Are stack-specific assumptions, unsafe automation, and maintenance costs explicit in the risks?</li>
      </ol>
    </details>
  </section>

  <section class="section">
    <div class="section-head"><span class="section-no">03</span><h2>Complete cluster review table</h2></div>
    <noscript><p class="card">JavaScript is disabled. All 30 clusters remain visible; search and filters are optional progressive enhancements.</p></noscript>
    <div class="controls" aria-label="Review table filters">
      <label>Search<input id="search" type="search" placeholder="Capability, source, rationale, risk…"></label>
      <label>Decision<select id="decision"><option value="">All decisions</option>{''.join(f'<option value="{esc(value)}">{esc(value)}</option>' for value in sorted(decisions))}</select></label>
      <label>Priority<select id="priority"><option value="">All priorities</option>{''.join(f'<option value="{esc(value)}">{esc(value)}</option>' for value in ('P1','P2','P3'))}</select></label>
      <label>Harness<select id="harness"><option value="">All harnesses</option>{''.join(f'<option value="{esc(value)}">{esc(value)}</option>' for value in EXPECTED_HARNESSES)}</select></label>
      <button id="reset" type="button">Reset</button>
    </div>
    <p class="result-count" id="result-count">Showing all {len(clusters)} clusters.</p>
    <div class="table-wrap">
      <table class="review-table">
        <thead><tr><th>Priority</th><th>Decision</th><th>Recommended capability</th><th>Sources</th><th>Avg score</th><th>Review detail</th></tr></thead>
        <tbody id="cluster-rows">{cluster_table(clusters, evaluation_by_id)}</tbody>
      </table>
    </div>
    <p class="caption">Spreadsheet review: <a href="{esc(review_csv_href)}">{esc(Path(review_csv_href).name)}</a>. Source synthesis: <a href="{esc(synthesis_href)}">final_synthesis.md</a>.</p>
  </section>

  <section class="section excluded">
    <div class="section-head"><span class="section-no">04</span><h2>Explicit prior exclusions</h2></div>
    <div class="table-wrap"><table class="exclusion-table"><thead><tr><th>Source ID</th><th>Name</th><th>Harness</th><th>Status</th></tr></thead><tbody>{exclusions(scope)}</tbody></table></div>
  </section>

  <footer>Generated from the verified focused synthesis bundle · {scope['unique_canonical_rows']} unique rows · {scope['included_evaluation_rows']} deep evaluations · {scope['focused_clusters']} clusters · no network · no ledger writes</footer>
</main>
<script>
  const rows = [...document.querySelectorAll('#cluster-rows tr')];
  const search = document.querySelector('#search');
  const decision = document.querySelector('#decision');
  const priority = document.querySelector('#priority');
  const harness = document.querySelector('#harness');
  const count = document.querySelector('#result-count');
  function applyFilters() {{
    const term = search.value.trim().toLowerCase();
    let visible = 0;
    for (const row of rows) {{
      const show = (!term || row.dataset.search.includes(term)) &&
        (!decision.value || row.dataset.decision === decision.value) &&
        (!priority.value || row.dataset.priority === priority.value) &&
        (!harness.value || row.dataset.harnesses.split(' ').includes(harness.value));
      row.hidden = !show;
      if (show) visible += 1;
    }}
    count.textContent = `Showing ${{visible}} of ${{rows.length}} clusters.`;
  }}
  for (const control of [search, decision, priority, harness]) {{
    control.addEventListener(control === search ? 'input' : 'change', applyFilters);
  }}
  document.querySelector('#reset').addEventListener('click', () => {{
    search.value = ''; decision.value = ''; priority.value = ''; harness.value = ''; applyFilters();
  }});
</script>
</body>
</html>
"""


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=VIZ_DIR / "index.html")
    parser.add_argument("--csv-out", type=Path, default=VIZ_DIR / "review-table.csv")
    args = parser.parse_args(argv)
    scope, clusters, evaluations = load_data()
    evaluation_by_id = {str(row["source_id"]): row for row in evaluations}
    rows = review_rows(clusters, evaluation_by_id)
    assert len(rows) == len({row["cluster_id"] for row in rows}) == EXPECTED_COUNTS["clusters"]
    output_dir = args.out.resolve().parent
    relative_href = lambda path: Path(os.path.relpath(path.resolve(), output_dir)).as_posix()
    args.out.write_text(
        render(
            scope,
            clusters,
            evaluations,
            visualizations_href=relative_href(VIZ_DIR.parent / "index.html"),
            review_csv_href=relative_href(args.csv_out),
            synthesis_href=relative_href(DATA_DIR / "final_synthesis.md"),
        ),
        encoding="utf-8",
    )
    write_review_csv(rows, args.csv_out)
    print(
        f"wrote {args.out} + {args.csv_out.name} "
        f"({scope['unique_canonical_rows']} unique / {len(evaluations)} evaluated / "
        f"{len(clusters)} clusters / {scope['excluded_rows']} excluded)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
