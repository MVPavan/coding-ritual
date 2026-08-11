#!/usr/bin/env python3
"""Export capability catalogs to one inventory CSV per capability kind.

`scan.py` writes a JSON catalog per reference harness. Reviewing those by hand is
awkward: a reader who wants "every skill across the harnesses" has to walk several
JSON files and filter. This tool flattens a set of catalogs into one CSV per kind
(skill / command / agent / rule / hook / mcp / plugin), so each review question maps
to exactly one file.

  export_csv.py catalogs/agent-skills.json catalogs/superpowers.json --out-dir inventory

Inventory only: the columns are facts the scanner observed. Adoption verdicts live
in `ledger.json`, and model-judged usefulness ratings come from the separate
analysis pipelines — neither is reproducible from a scan, so neither appears here.

A CSV is written for EVERY kind, including kinds with no rows (header only), so a
kind that is genuinely absent from the scanned harnesses is visible as an empty
file rather than a missing one.

Pure Python standard library — no third-party dependencies, matching `scan.py`.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import scan

CSV_COLUMNS = (
    "id",
    "kind",
    "category",
    "name",
    "harness",
    "canonical_path",
    "line_count",
    "asset_count",
    "assets",
    "description",
)

# Assets are a list inside one CSV cell; ";" keeps the cell readable and avoids
# colliding with the "," the CSV writer already quotes around.
ASSET_SEPARATOR = "; "

# Sort key for a stable, review-friendly row order within each CSV.
ROW_SORT_FIELDS = ("harness", "category", "name")

CATALOG_CAPABILITIES_KEY = "capabilities"
CATALOG_REPO_KEY = "repo"
CATALOG_COMMIT_KEY = "source_commit"


@dataclass(frozen=True)
class Row:
    """One capability flattened for CSV output."""

    id: str
    kind: str
    category: str
    name: str
    harness: str
    canonical_path: str
    line_count: int
    assets: tuple[str, ...]
    description: str

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "kind": self.kind,
            "category": self.category,
            "name": self.name,
            "harness": self.harness,
            "canonical_path": self.canonical_path,
            "line_count": self.line_count,
            "asset_count": len(self.assets),
            "assets": ASSET_SEPARATOR.join(self.assets),
            "description": self.description,
        }


def load_rows(catalog_path: Path) -> list[Row]:
    """Flatten one catalog JSON into rows, tagging each with its harness name."""
    data = json.loads(catalog_path.read_text(encoding="utf-8"))
    harness = str(data.get(CATALOG_REPO_KEY) or catalog_path.stem)
    rows: list[Row] = []
    for cap in data.get(CATALOG_CAPABILITIES_KEY, []):
        rows.append(
            Row(
                id=str(cap.get("logical_id", "")),
                kind=str(cap.get("kind", "")),
                category=str(cap.get("category", "")),
                name=str(cap.get("name", "")),
                harness=harness,
                canonical_path=str(cap.get("canonical_path", "")),
                line_count=int(cap.get("line_count", 0)),
                assets=tuple(str(a) for a in cap.get("assets", [])),
                description=str(cap.get("description", "")),
            )
        )
    return rows


def write_kind_csv(out_dir: Path, kind: scan.Kind, rows: list[Row]) -> Path:
    """Write the rows of a single kind to `<out_dir>/<kind>.csv` and return the path."""
    out_path = out_dir / f"{kind.value}.csv"
    ordered = sorted(
        rows, key=lambda row: tuple(getattr(row, field) for field in ROW_SORT_FIELDS)
    )
    with out_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        for row in ordered:
            writer.writerow(row.to_dict())
    return out_path


def cmd_export(args: argparse.Namespace) -> int:
    """Read every catalog, group by kind, and write one CSV per kind."""
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    all_rows: list[Row] = []
    sources: list[tuple[str, str]] = []
    for raw_path in args.catalogs:
        catalog_path = Path(raw_path)
        if not catalog_path.is_file():
            print(f"error: no such catalog: {catalog_path}", file=sys.stderr)
            return 1
        data = json.loads(catalog_path.read_text(encoding="utf-8"))
        sources.append(
            (
                str(data.get(CATALOG_REPO_KEY) or catalog_path.stem),
                str(data.get(CATALOG_COMMIT_KEY) or "working-tree"),
            )
        )
        all_rows.extend(load_rows(catalog_path))

    by_kind: dict[str, list[Row]] = {kind.value: [] for kind in scan.Kind}
    unknown: list[Row] = []
    for row in all_rows:
        if row.kind in by_kind:
            by_kind[row.kind].append(row)
        else:
            unknown.append(row)

    print(f"## inventory export -> {out_dir}")
    print(f"sources: {len(sources)} catalog(s), {len(all_rows)} capabilities\n")
    for repo, commit in sources:
        print(f"  {repo:24} {commit[:12]}")
    print()
    print(f"{'kind':<10} {'rows':>6}   file")
    for kind in scan.Kind:
        rows = by_kind[kind.value]
        path = write_kind_csv(out_dir, kind, rows)
        print(f"{kind.value:<10} {len(rows):>6}   {path}")
    print(f"{'TOTAL':<10} {len(all_rows):>6}")

    if unknown:
        kinds = sorted({row.kind for row in unknown})
        print(
            f"\nwarning: {len(unknown)} row(s) had unrecognised kinds {kinds} "
            "and were NOT written to any CSV",
            file=sys.stderr,
        )
        return 1
    return 0


def main(argv: list[str] | None = None) -> int:
    """Parse arguments and run the export."""
    parser = argparse.ArgumentParser(
        description="Export harness capability catalogs to one CSV per kind."
    )
    parser.add_argument("catalogs", nargs="+", help="catalog JSON files to export")
    parser.add_argument(
        "--out-dir", required=True, help="directory to write the per-kind CSVs into"
    )
    args = parser.parse_args(argv)
    return cmd_export(args)


if __name__ == "__main__":
    raise SystemExit(main())
