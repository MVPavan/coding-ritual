"""Writing a chart as Mermaid `stateDiagram-v2` text, in a stable order."""

from __future__ import annotations

import json
import re
from collections.abc import Callable

from .chart import Chart, Node

# Styles only for the two failure marks, so any viewer shows them; the other
# classes (onPath, repeats, phase_<colour>) are styled by a stylesheet.
MARK_STYLES = (
    "classDef breaks fill:#fde2e1,stroke:#b42318,stroke-width:3px,color:#1a1a1a",
    "classDef mayBreak fill:#fef0c7,stroke:#b42318,stroke-width:2px,stroke-dasharray: 5 4,color:#1a1a1a",
)
_SAFE = re.compile(r"[A-Za-z0-9 .,_()'?!+*/=-]")


def limits(text: str) -> dict[str, object]:
    """Mermaid settings that admit this chart: its own length and arrow
    count, never below Mermaid's defaults (50,000 characters, 500 edges)."""
    edges = sum(" --> " in line for line in text.splitlines())
    return {
        "maxTextSize": max(50_000, len(text)),
        "maxEdges": max(500, edges),
        "securityLevel": "strict",
    }


def escape(text: str) -> str:
    """Any character outside a plain set becomes a Mermaid entity code."""
    return "".join(c if _SAFE.fullmatch(c) else f"#{ord(c)};" for c in text)


def render(chart: Chart) -> str:
    ids: dict[Node, str] = {}
    lines = []
    if chart.title:
        lines += ["---", f"title: {json.dumps(chart.title)}", "---"]
    lines += [
        "stateDiagram-v2",
        "  %% Written by statechart.py; regenerate it rather than edit it.",
    ]
    lines += [f"  {style}" for style in MARK_STYLES]

    def node_id(node: Node) -> str:
        return ids.setdefault(node, f"s{len(ids) + 1}")

    if chart.form == "regions":
        lines.append("  direction LR")
        lines.append(f'  state "{escape(chart.title or "Regions")}" as regions {{')
        for index, region in enumerate(chart.regions):
            if index:
                lines.append("    --")
            lines.append(f'    state "{escape(region)}" as r{index + 1} {{')
            members = [n for n in chart.nodes if n[0] == region]
            lines += [f'      state "{escape(n[1])}" as {node_id(n)}' for n in members]
            lines += [
                f"      [*] --> {node_id(n)}" for n in chart.starts if n[0] == region
            ]
            for arrow in chart.arrows:
                if arrow.source[0] == region:
                    label = escape(" or ".join(sorted(arrow.labels)))
                    lines.append(
                        f"      {node_id(arrow.source)} --> {node_id(arrow.target)} : {label}"
                    )
            lines.append("    }")
        lines.append("  }")
    else:
        _tree(chart, lines, node_id)
        lines += [f"  [*] --> {node_id(n)}" for n in chart.starts]
        for arrow in chart.arrows:
            label = escape(" or ".join(sorted(arrow.labels)))
            lines.append(
                f"  {node_id(arrow.source)} --> {node_id(arrow.target)} : {label}"
            )
    for node in chart.nodes:
        names = sorted(chart.classes.get(node, set()))
        if node in chart.marks:
            names.append(chart.marks[node])  # last, so it wins over phase colours
        for name in names:
            lines.append(f"  class {node_id(node)} {name}")
    return "\n".join(lines) + "\n"


def _tree(chart: Chart, lines: list[str], node_id: Callable[[Node], str]) -> None:
    """Flat states, or nested composites, each parent placed where its first
    leaf comes in the draw order, with its children together."""
    first: dict[Node, int] = {}
    for index, leaf in enumerate(chart.nodes):
        for cut in range(1, len(leaf) + 1):
            first.setdefault(leaf[:cut], index)
    leaves = sorted(
        chart.nodes, key=lambda n: [first[n[:cut]] for cut in range(1, len(n) + 1)]
    )
    opened: list[Node] = []
    for leaf in leaves:
        parents = [leaf[:cut] for cut in range(1, len(leaf))]
        while opened and opened[-1] not in parents:
            opened.pop()
            lines.append("  " + "  " * len(opened) + "}")
        for parent in parents[len(opened) :]:
            lines.append(
                "  "
                + "  " * len(opened)
                + f'state "{escape(parent[-1])}" as {node_id(parent)} {{'
            )
            opened.append(parent)
        lines.append(
            "  " + "  " * len(opened) + f'state "{escape(leaf[-1])}" as {node_id(leaf)}'
        )
    while opened:
        opened.pop()
        lines.append("  " + "  " * len(opened) + "}")
