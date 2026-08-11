#!/usr/bin/env python3
"""Append-only curation casebook: validate, project, render, query.

Each analysis round writes ONE immutable file under `rounds/`. Nothing is ever
edited or deleted. A later round that changes an earlier ruling appends a new
event naming the ones it supersedes; the old event stays exactly where it was.

Round-sharded rather than one global log so two concurrent rounds add different
files instead of colliding at the end of a shared one.

  casebook.py validate   check append-only integrity and schema
  casebook.py build      regenerate current.json and views/ from the rounds
  casebook.py query <q>  current ruling plus full history for a skill

`current.json` and `views/` are GENERATED — never hand-edit them; edit nothing,
append a round and rebuild. Pure standard library, matching `scan.py`.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROUNDS_DIR = HERE / "rounds"
VIEWS_DIR = HERE / "views"
MANIFEST = ROUNDS_DIR / "MANIFEST.json"
CURRENT = HERE / "current.json"

ROUND_SCHEMA = "harness-curation-round/v1"
EVENT_SCHEMA = "harness-curation-event/v1"

# A verdict is either a keep or a removal; nothing else is a valid outcome.
KEEP_VERDICTS = frozenset({"adopt", "adopt-merged"})
DROP_VERDICTS = frozenset({"reject", "defer", "out-of-scope"})
VALID_VERDICTS = KEEP_VERDICTS | DROP_VERDICTS | {"superseded"}

REQUIRED_EVENT_FIELDS = (
    "event_id",
    "round_id",
    "recorded_at",
    "bucket",
    "subject_id",
    "source",
    "verdict",
    "reasoning",
    "adaptation",
)
REQUIRED_SOURCE_FIELDS = ("repo", "name", "content_hash", "commit_sha")

VERDICT_LABEL = {
    "adopt": "ADOPTED",
    "adopt-merged": "ADOPTED (merged)",
    "reject": "rejected",
    "defer": "deferred",
    "out-of-scope": "out of scope",
    "superseded": "superseded",
}


def _round_files() -> list[Path]:
    """Round files in chronological (filename) order."""
    return sorted(p for p in ROUNDS_DIR.glob("*.jsonl"))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_rounds() -> tuple[list[dict], list[dict], list[str]]:
    """Read every round file. Returns (headers, events, errors)."""
    headers: list[dict] = []
    events: list[dict] = []
    errors: list[str] = []
    for path in _round_files():
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if not line.strip():
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError as exc:
                errors.append(f"{path.name}:{lineno}: unparseable JSON ({exc})")
                continue
            schema = record.get("schema")
            if schema == ROUND_SCHEMA:
                headers.append(record)
            elif schema == EVENT_SCHEMA:
                events.append(record)
            else:
                errors.append(f"{path.name}:{lineno}: unknown schema {schema!r}")
    return headers, events, errors


def check(headers: list[dict], events: list[dict]) -> list[str]:
    """Every integrity rule the log must satisfy."""
    errors: list[str] = []

    known_rounds = {h.get("round_id") for h in headers}
    for path in _round_files():
        first = path.read_text(encoding="utf-8").splitlines()[:1]
        if not first or json.loads(first[0]).get("schema") != ROUND_SCHEMA:
            errors.append(f"{path.name}: first line must be a {ROUND_SCHEMA} header")

    seen_events: set[str] = set()
    for event in events:
        eid = event.get("event_id", "<missing>")
        for field in REQUIRED_EVENT_FIELDS:
            if field not in event:
                errors.append(f"{eid}: missing required field {field!r}")
        if eid in seen_events:
            errors.append(f"{eid}: duplicate event_id")
        seen_events.add(eid)
        if event.get("verdict") not in VALID_VERDICTS:
            errors.append(f"{eid}: invalid verdict {event.get('verdict')!r}")
        if event.get("round_id") not in known_rounds:
            errors.append(f"{eid}: round_id {event.get('round_id')!r} has no header")
        if not str(event.get("reasoning", "")).strip():
            errors.append(f"{eid}: reasoning is empty — every ruling must state why")
        source = event.get("source")
        if isinstance(source, dict):
            for field in REQUIRED_SOURCE_FIELDS:
                if not source.get(field):
                    errors.append(f"{eid}: source.{field} is empty")
        else:
            errors.append(f"{eid}: source must be an object")

    for event in events:
        for target in event.get("supersedes", []):
            if target not in seen_events:
                errors.append(
                    f"{event.get('event_id')}: supersedes unknown event {target!r}"
                )
            if target == event.get("event_id"):
                errors.append(f"{event.get('event_id')}: supersedes itself")

    # One subject may only be superseded along a single chain, else "current" is ambiguous.
    superseded_by: dict[str, str] = {}
    for event in events:
        for target in event.get("supersedes", []):
            if target in superseded_by:
                errors.append(
                    f"{target}: superseded twice ({superseded_by[target]} and "
                    f"{event.get('event_id')}) — the current ruling would be ambiguous"
                )
            superseded_by[target] = str(event.get("event_id"))
    return errors


def check_immutable() -> list[str]:
    """Reject any change to a round file already recorded in the manifest."""
    recorded: dict[str, str] = {}
    if MANIFEST.is_file():
        recorded = json.loads(MANIFEST.read_text(encoding="utf-8")).get("rounds", {})
    errors: list[str] = []
    present = {p.name: _sha256(p) for p in _round_files()}
    for name, digest in recorded.items():
        if name not in present:
            errors.append(
                f"{name}: recorded round file has been DELETED — the log is append-only"
            )
        elif present[name] != digest:
            errors.append(
                f"{name}: recorded round file has been MODIFIED — the log is append-only"
            )
    return errors


def seal() -> list[str]:
    """Record hashes for any new round files. Returns the names newly sealed."""
    recorded: dict[str, str] = {}
    if MANIFEST.is_file():
        recorded = json.loads(MANIFEST.read_text(encoding="utf-8")).get("rounds", {})
    added = [p.name for p in _round_files() if p.name not in recorded]
    for path in _round_files():
        recorded.setdefault(path.name, _sha256(path))
    MANIFEST.write_text(
        json.dumps(
            {
                "_comment": "sha256 of every sealed round file. casebook.py validate fails if a "
                "sealed file is modified or deleted. Never edit by hand.",
                "rounds": dict(sorted(recorded.items())),
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return added


def project(events: list[dict]) -> dict[str, dict]:
    """Collapse the event history to the effective ruling per subject."""
    superseded = {t for e in events for t in e.get("supersedes", [])}
    current: dict[str, dict] = {}
    for event in events:
        if event.get("event_id") in superseded:
            continue
        current[str(event.get("subject_id"))] = event
    return current


def cmd_validate(_: argparse.Namespace) -> int:
    """Fail loudly on schema breaches or any edit to sealed history."""
    headers, events, errors = load_rounds()
    errors = errors + check(headers, events) + check_immutable()
    if errors:
        for line in errors:
            print(f"error: {line}", file=sys.stderr)
        print(f"\n{len(errors)} problem(s)", file=sys.stderr)
        return 1
    current = project(events)
    kept = sum(1 for e in current.values() if e.get("verdict") in KEEP_VERDICTS)
    print(
        f"ok: {len(headers)} round(s), {len(events)} event(s), "
        f"{len(current)} subject(s), {kept} currently adopted"
    )
    return 0


def _view_lines(
    bucket: int, name: str, events: list[dict], current: dict[str, dict]
) -> list[str]:
    out = [f"# Bucket {bucket} — {name}", ""]
    out += [
        "<!-- GENERATED by casebook.py build. Do not edit. Append a round instead. -->",
        "",
    ]
    live = [
        e
        for e in events
        if int(e["bucket"]) == bucket and current.get(str(e["subject_id"])) is e
    ]
    kept = [e for e in live if e.get("verdict") in KEEP_VERDICTS]
    gone = [e for e in live if e.get("verdict") in DROP_VERDICTS]
    out += [f"**Current ruling: {len(live)} considered → {len(kept)} adopted.**", ""]

    for heading, group in (("Adopted", kept), ("Not adopted", gone)):
        if not group:
            continue
        out += [f"## {heading}", ""]
        for event in sorted(group, key=lambda e: str(e["source"]["name"])):
            src = event["source"]
            out += [f"### `{src['name']}` — {VERDICT_LABEL[event['verdict']]}", ""]
            out += [
                f"*{src['repo']} · `{src['commit_sha']}` · ruled in {event['round_id']}*",
                "",
            ]
            out += [str(event["reasoning"]), ""]
            adapt = event.get("adaptation", {})
            if adapt.get("merged_from"):
                out += [
                    "**Absorbed:** "
                    + ", ".join(f"`{m}`" for m in adapt["merged_from"]),
                    "",
                ]
            if adapt.get("modifications"):
                out += ["**Changes made when adopting:**", ""]
                out += [f"- {m}" for m in adapt["modifications"]] + [""]
            if adapt.get("deliberately_dropped"):
                out += ["**Deliberately dropped:**", ""]
                out += [f"- {m}" for m in adapt["deliberately_dropped"]] + [""]

    history = [e for e in events if e.get("supersedes")]
    if history:
        out += ["## Superseded rulings", ""]
        for event in history:
            replaced = ", ".join(event["supersedes"])
            name = event["source"]["name"]
            why = str(event["reasoning"])[:160]
            line = f"- `{name}` — {event['round_id']} replaced {replaced}: {why}"
            out += [line, ""]
    return out


def cmd_build(_: argparse.Namespace) -> int:
    """Regenerate current.json and the per-bucket views."""
    headers, events, errors = load_rounds()
    errors = errors + check(headers, events)
    if errors:
        for line in errors:
            print(f"error: {line}", file=sys.stderr)
        return 1
    current = project(events)

    CURRENT.write_text(
        json.dumps(
            {
                "_comment": "GENERATED by casebook.py build from rounds/*.jsonl. Do not edit.",
                "rounds": [h.get("round_id") for h in headers],
                "subjects": {
                    sid: {
                        "name": e["source"]["name"],
                        "repo": e["source"]["repo"],
                        "bucket": e["bucket"],
                        "verdict": e["verdict"],
                        "content_hash": e["source"]["content_hash"],
                        "commit_sha": e["source"]["commit_sha"],
                        "event_id": e["event_id"],
                    }
                    for sid, e in sorted(current.items())
                },
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    VIEWS_DIR.mkdir(parents=True, exist_ok=True)
    buckets: dict[int, str] = {}
    for event in events:
        buckets[int(event["bucket"])] = str(event.get("bucket_name", ""))
    index = [
        "# Casebook — current rulings by bucket",
        "",
        "<!-- GENERATED by casebook.py build. Do not edit. -->",
        "",
        "| Bucket | Considered | Adopted | View |",
        "|---|---:|---:|---|",
    ]
    total_kept = 0
    for bucket in sorted(buckets):
        rows = [
            e
            for e in events
            if int(e["bucket"]) == bucket and current.get(str(e["subject_id"])) is e
        ]
        kept = sum(1 for e in rows if e["verdict"] in KEEP_VERDICTS)
        total_kept += kept
        slug = f"bucket-{bucket:02d}.md"
        (VIEWS_DIR / slug).write_text(
            "\n".join(_view_lines(bucket, buckets[bucket], events, current)) + "\n",
            encoding="utf-8",
        )
        index.append(
            f"| {bucket}. {buckets[bucket]} | {len(rows)} | {kept} | [{slug}]({slug}) |"
        )
    index.append(f"| **Total** | **{len(current)}** | **{total_kept}** | |")
    (VIEWS_DIR / "INDEX.md").write_text("\n".join(index) + "\n", encoding="utf-8")

    print(
        f"built: current.json ({len(current)} subjects, {total_kept} adopted), "
        f"views/ ({len(buckets)} buckets + INDEX)"
    )
    return 0


def cmd_query(args: argparse.Namespace) -> int:
    """Show the effective ruling and the full history for a skill."""
    _, events, _ = load_rounds()
    current = project(events)
    needle = args.query.lower()
    hits = [
        e
        for e in events
        if needle in str(e["source"]["name"]).lower()
        or needle == str(e.get("subject_id"))
    ]
    if not hits:
        print(f"no rulings matching {args.query!r}")
        return 1
    for subject in sorted({str(e["subject_id"]) for e in hits}):
        history = [e for e in events if str(e["subject_id"]) == subject]
        live = current.get(subject)
        head = history[0]["source"]
        print(
            f"\n{subject}  {head['name']} [{head['repo']}]  bucket {history[0]['bucket']}"
        )
        print(
            f"  current: {VERDICT_LABEL.get(str(live['verdict'])) if live else 'none'}"
        )
        for event in history:
            marker = "*" if event is live else " "
            print(
                f"  {marker} {event['round_id']}  {event['verdict']:<13} "
                f"hash={event['source']['content_hash'][:10]}"
            )
            print(f"      {str(event['reasoning'])[:200]}")
    return 0


def main(argv: list[str] | None = None) -> int:
    """Parse arguments and dispatch."""
    parser = argparse.ArgumentParser(
        description="Append-only harness curation casebook."
    )
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("validate", help="check append-only integrity and schema")
    build = sub.add_parser("build", help="regenerate current.json and views/")
    build.add_argument(
        "--seal",
        action="store_true",
        help="record hashes of new round files so later edits are rejected",
    )
    query = sub.add_parser("query", help="ruling and history for a skill")
    query.add_argument("query", help="skill name (substring) or subject_id")
    args = parser.parse_args(argv)

    if args.command == "validate":
        return cmd_validate(args)
    if args.command == "query":
        return cmd_query(args)
    code = cmd_build(args)
    if code == 0 and getattr(args, "seal", False):
        added = seal()
        print(
            f"sealed: {len(added)} new round file(s)"
            if added
            else "sealed: nothing new"
        )
    return code


if __name__ == "__main__":
    raise SystemExit(main())
