"""The registry viewer (`registry.py viewer`): one self-contained HTML page of
every unit of each harness with rulings beside our skills, playbooks and
principles.

Everything on the page is pulled from text that already exists (SKILL.md and
catalog descriptions, `skills.yaml` boundaries, skill-record summaries, trait
definitions, playbook triggers, router lines, ledger reasons) or counted from
the ledger; nothing is written by a model. Rulings, verdicts and placement
follow README §2, §4a, §4b, §5, §5b and §5c through the ledger helpers.

The page is rebuilt, never kept by hand: two runs on the same tree give the
same bytes (no clock, sorted keys, stable order). It is untracked; `build` and
`check` never read it.
"""

from __future__ import annotations

import collections
import json
import re
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from curation.registry.changes import _change_info
from curation.registry.config import RegistryConfig
from curation.registry.ledger import (
    _round_of,
    build_lifecycle,
    effective_by_subject,
    is_pending_adopt,
    live_events,
    resolve_skill,
    retained_adoptions,
    round_header_by_id,
    withdrawn_destinations,
)
from curation.registry.loaders import (
    _catalog_files,
    load_ledger,
    load_traits,
    record_path,
    routes_text,
    skill_description,
)
from curation.registry.models import Event
from curation.registry.reports import Context, load_context
from curation.registry.status import capability_state, skill_statuses
from curation.registry.steps import Playbook, load_playbooks
from curation.registry.traits import _doc_traits
from curation.registry.vocab import PRINCIPLE_PREFIX, STAGE_ORDER
from curation.scan.models import Catalog

LANES = [*STAGE_ORDER, "Unplaced"]
STAGE_LABEL = {"X": "Cross-cutting", "U": "Utilities"}
# Upstream capability kinds shown even when never ruled; any ruled kind shows too.
TILE_KINDS = ("skill", "playbook", "plugin", "agent")
VERDICT = {
    "adopt": "full",
    "adopt-merged": "partial",
    "defer": "deferred",
    "reject": "rejected",
    "out-of-scope": "oos",
}
TRAIT_BUCKETS = ("adopt", "reject", "defer", "hold", "oos", "unruled")
HOLD_RE = re.compile(r"\bon (provisional )?hold\b", re.IGNORECASE)
# Packaging copies folded into their originals: (harness, copy prefix, original prefix).
COPY_RULES = (("cursor_plugins", "harness/pstack/claude-code/", "pstack/"),)
# Display names; a harness may split into named sources by logical-id fragment.
SOURCE_NAMES = {"mattpocock_skills": "Pocock"}
SOURCE_SPLITS = {"cursor_plugins": (("pstack/", "pstack"),)}
SOURCE_ABBR = {"Pocock": "P", "pstack": "ps"}


def viewer_dir(cfg: RegistryConfig) -> Path:
    return cfg.registry_dir / "viewer"


def default_out(cfg: RegistryConfig) -> Path:
    return viewer_dir(cfg) / "index.html"


# ---------------------------------------------------------------- text helpers


def first_sentence(text: str, cap: int = 240) -> str:
    text = " ".join((text or "").split())
    m = re.search(r"^(.{20,}?[.!?])(\s|$)", text)
    s = m.group(1) if m else text
    return s if len(s) <= cap else s[: cap - 1].rstrip() + "…"


def shorten(text: str, cap: int = 110) -> str:
    text = " ".join((text or "").split())
    return text if len(text) <= cap else text[: cap - 1].rstrip(" ,;:") + "…"


_PREFIX_RE = re.compile(
    r"^(?:(?:Owner(?:'s)? rulings? (?:of )?[0-9-]+(?: and [0-9-]+)?(?: \([^)]*\))?|"
    r"Owner deferred the report's reject recommendation, to review the set later|"
    r"Relocation(?: of [^:]+)?)\s*:\s*)+",
    re.IGNORECASE,
)


def reason_label(why: str) -> str:
    """A short, countable label for a reason: the text before an early colon,
    else its first sentence."""
    t = _PREFIX_RE.sub("", " ".join((why or "").split()))
    m = re.match(r"^([^:`]{3,40}):\s", t)
    if m:
        return m.group(1).strip()
    return shorten(first_sentence(t, 400), 100)


def commonest(labels: list[str]) -> tuple[str | None, int]:
    if not labels:
        return None, 0
    lab, n = min(collections.Counter(labels).items(), key=lambda kv: (-kv[1], kv[0]))
    return lab, n


def _frontmatter(text: str) -> dict[str, Any]:
    if not text.startswith("---"):
        return {}
    end = text.find("\n---", 3)
    if end < 0:
        return {}
    try:
        fm = yaml.safe_load(text[3:end]) or {}
    except yaml.YAMLError:
        return {}
    return fm if isinstance(fm, dict) else {}


def stage_key(stage: str, sub: str) -> tuple[int, str]:
    return (LANES.index(stage) if stage in LANES else len(LANES), sub or "")


def majority_placement(placements: list[tuple[str, str]]) -> tuple[str, str] | None:
    if not placements:
        return None
    c = collections.Counter(placements)
    return min(c.items(), key=lambda kv: (-kv[1], stage_key(*kv[0])))[0]


def _round(event_id: str) -> str:
    return event_id.rsplit(":", 1)[0]


def record_summary(text: str) -> str:
    """A skill record's hand-written text: what is left once the frontmatter,
    title, description, boundary and generated blocks are removed. Records are
    generated today, so this is usually empty."""
    body = re.sub(r"\A---\n.*?\n---\n", "", text, flags=re.DOTALL)
    body = re.sub(
        r"<!-- registry:generated (\w+) -->.*?<!-- /registry:generated \1 -->",
        "",
        body,
        flags=re.DOTALL,
    )
    paras = [p.strip() for p in re.split(r"\n\s*\n", body) if p.strip()]
    if paras and paras[0].startswith("# "):
        paras = paras[1:]
    if paras:
        paras = paras[1:]  # the description, copied from SKILL.md
    paras = [p for p in paras if not p.startswith("**Boundary:**")]
    return "\n\n".join(paras)


# ---------------------------------------------------------------- sources


def source_of(harness: str, lid: str) -> str:
    for frag, name in SOURCE_SPLITS.get(harness, ()):
        if frag in lid:
            return name
    return SOURCE_NAMES.get(harness, harness)


def _abbr(name: str, taken: set[str]) -> str:
    if name in SOURCE_ABBR:
        return SOURCE_ABBR[name]
    parts = [p for p in re.split(r"[-_]", name) if p]
    cands = [
        "".join(p[0] for p in parts).lower() if len(parts) > 1 else name[:2].lower(),
        name[:3].lower(),
        name[:4].lower(),
    ]
    for c in cands:
        if c not in taken:
            return c
    return name.lower()


def ruled_harnesses(cfg: RegistryConfig, ctx: Context) -> list[str]:
    """Every harness with a trait file or a ruling in the ledger."""
    out = {p.stem for p in cfg.traits_dir.glob("*.yaml") if p.stem != "ours"}
    for subject in ctx.current:
        repo = subject.split(":", 1)[0]
        if repo not in ("ours", "doc"):
            out.add(repo)
    return sorted(out)


def upstream_description(cfg: RegistryConfig, harness: str, path: str) -> str:
    """The upstream file's frontmatter `description`, else its first bold
    sentence, read from the checked-out reference tree; empty when the file
    is absent there (the page then says the description is unavailable)."""
    if not path:
        return ""
    file = cfg.repo_root / "reference_harnesses" / harness / path
    if not file.is_file():
        return ""
    text = file.read_text(encoding="utf-8", errors="replace")
    desc = _frontmatter(text).get("description")
    if isinstance(desc, str) and desc.strip():
        return " ".join(desc.split())
    m = re.search(r"\*\*(.+?)\*\*", text)
    return " ".join(m.group(1).split()) if m else ""


def provenance(
    events: list[Event], forward: dict[str, str], retired: set[str]
) -> dict[str, list[tuple[str, str]]]:
    """Destination unit -> sorted (upstream trait subject, state) rows. Our
    content's provenance is the retained adoption fold (README §5, §5b), not
    the effective ruling: every last delivered adopt per destination stays,
    *withdrawn* once an ours-side `update` withdraws it from that destination,
    *no longer provided* when the destination retired, else *delivered*; an
    effective pending adopt adds its own *pending* row, so a pending
    re-adoption shows beside the history it follows instead of replacing it.
    Raw `events`, as `retained_adoptions` and `withdrawn_destinations`
    require."""
    current = effective_by_subject(live_events(events))
    withdrawn = withdrawn_destinations(events, forward)
    out: dict[str, set[tuple[str, str]]] = collections.defaultdict(set)
    for subject, dest in retained_adoptions(events, forward):
        if (subject, dest) in withdrawn:
            state = "withdrawn"
        elif dest in retired:
            state = "no longer provided"
        else:
            state = "delivered"
        out[dest].add((subject, state))
    for subject, event in current.items():
        if is_pending_adopt(event) and event.skill:
            out[resolve_skill(event.skill, forward)].add((subject, "pending"))
    return {k: sorted(v) for k, v in sorted(out.items())}


# ---------------------------------------------------------------- model


@dataclass
class Built:
    tiles: dict[str, dict[str, Any]]
    ours: dict[str, dict[str, Any]]
    router: dict[str, Any]
    sources: list[dict[str, Any]]
    sub_gaps: list[tuple[str, str]]
    status: dict[str, dict[str, str]] = field(default_factory=dict)


def _load_catalog(cfg: RegistryConfig, harness: str) -> Catalog | None:
    for path in _catalog_files(cfg):
        if path.stem == harness:
            return Catalog.from_dict(json.loads(path.read_text(encoding="utf-8")))
    return None


def build(cfg: RegistryConfig) -> Built:
    ctx = load_context(cfg)
    headers, _, _ = load_ledger(cfg)
    headers_by_id = round_header_by_id(headers)
    live = live_events(ctx.events)
    forward, retired = build_lifecycle(live)
    eff = ctx.current
    carried: dict[str, Event] = {}
    for e in live:
        for old in e.carried_from:
            if old != e.subject:
                carried[old] = e
    defs = ctx.definitions
    traits_all, _ = load_traits(cfg)
    playbooks, _ = load_playbooks(cfg)
    router_text = cfg.router_path.read_text(encoding="utf-8")

    def tdef(t: str) -> str:
        d = defs.get(t)
        return d.definition.strip() if d else ""

    def tplace(t: str) -> tuple[str, str] | None:
        d = defs.get(t)
        return (d.placement.stage, d.placement.substage) if d else None

    # ---------------- our units
    ours: dict[str, dict[str, Any]] = {}

    def add_ours(
        uid: str, name: str, kind: str, pl: tuple[str, str], **kw: Any
    ) -> None:
        ours[uid] = {
            "id": uid,
            "name": name,
            "kind": kind,
            "stage": pl[0],
            "substage": pl[1],
            "desc": "",
            "boundary": "",
            "summary": "",
            "path": "",
            "planned": False,
            "fed": {},
            "sources": [],
            "placement_from": "",
            "prov": [],
            **kw,
        }

    for name, sk_entry in sorted(ctx.skills.items()):
        if sk_entry.status != "active":
            continue
        is_pr = name.startswith(PRINCIPLE_PREFIX)
        path = (
            cfg.principles_dir / f"{name.removeprefix(PRINCIPLE_PREFIX)}.md"
            if is_pr
            else cfg.skills_dir / name / "SKILL.md"
        )
        rec = record_path(cfg, name, sk_entry.domain)
        add_ours(
            name,
            name,
            "principle" if is_pr else "skill",
            (sk_entry.stage, sk_entry.substage),
            desc=skill_description(cfg, name),
            boundary=(sk_entry.boundary or "").strip(),
            summary=record_summary(rec.read_text(encoding="utf-8"))
            if rec.is_file()
            else "",
            path=path.relative_to(cfg.repo_root).as_posix(),
            record=rec.relative_to(cfg.repo_root).as_posix() if rec.is_file() else "",
        )

    for pname, book in sorted(playbooks.items()):
        tl = list(book.traits) + [a.trait for s in book.steps for a in s.actions]
        pl = majority_placement([x for x in map(tplace, tl) if x]) or ("Unplaced", "")
        add_ours(
            book.holder,
            pname,
            "playbook",
            pl,
            desc=" ".join(book.trigger.split()),
            path=book.path,
            placement_from="majority of its own and its steps' trait placements",
        )

    agents_line = re.search(
        r"^- \*\*`AGENTS\.md`:\*\* (.+)$", router_text, re.MULTILINE
    )
    for key, doc_entry in sorted(_doc_traits(traits_all).items()):
        if key in ours:
            continue
        pl = majority_placement([x for x in map(tplace, doc_entry.traits) if x]) or (
            "X",
            "",
        )
        desc = agents_line.group(1) if key == "doc:AGENTS.md" and agents_line else ""
        add_ours(
            key,
            key[4:],
            "doc",
            pl,
            desc=desc,
            path=key[4:],
            placement_from="majority of its trait placements",
        )

    # ---------------- upstream tiles
    harnesses = ruled_harnesses(cfg, ctx)
    catalogs = {h: _load_catalog(cfg, h) for h in harnesses}
    tiles: dict[str, dict[str, Any]] = {}
    status: dict[str, dict[str, str]] = {}
    changed: dict[str, str] = {}  # yes / no / unknown, as `_change_info` gives
    for h in harnesses:
        cat = catalogs[h]
        caps = cat.by_logical_id() if cat else {}
        st: dict[str, str] = {}
        if cat:
            st.update({s.logical_id: s.stage for s in skill_statuses(ctx, cat)})
            for cap in cat.capabilities:
                ev = eff.get(f"{h}:{cap.logical_id}")
                if ev is not None:
                    info = _change_info(
                        cfg, cat, cap, ev, headers_by_id.get(_round_of(ev))
                    )
                    changed[f"{h}:{cap.logical_id}"] = info.changed
                if cap.kind.value != "skill":
                    change = changed.get(f"{h}:{cap.logical_id}", "")
                    st[cap.logical_id] = (
                        "unknown, review"
                        if change == "unknown"
                        else capability_state(ev, change)
                    )
        status[h] = st
        subjects = {
            f"{h}:{lid}" for lid, c in caps.items() if c.kind.value in TILE_KINDS
        }
        subjects |= {s for s in eff if "#" not in s and s.split(":", 1)[0] == h}
        subjects |= {
            f"{h}:{lid}"
            for lid in st
            if lid.split(":", 1)[0] in TILE_KINDS or f"{h}:{lid}" in eff
        }
        for s in sorted(subjects):
            lid = s.split(":", 1)[1]
            tiles[s] = {
                "id": s,
                "harness": h,
                "lid": lid,
                "source": source_of(h, lid),
                "kind": lid.split(":", 1)[0],
                "name": lid.split(":", 1)[-1].rstrip("/").split("/")[-1],
                "copies": [],
            }

    # Fold packaging copies into their originals.
    for s in sorted(tiles):
        t = tiles.get(s)
        if t is None:
            continue
        for h, copy_prefix, orig_prefix in COPY_RULES:
            if t["harness"] == h and copy_prefix in t["lid"]:
                orig = f"{h}:{t['lid'].replace(copy_prefix, orig_prefix)}"
                if orig in tiles:
                    ev = eff.get(s)
                    tiles[orig]["copies"].append(
                        {
                            "id": s,
                            "event": ev.id if ev else "",
                            "kind": ev.kind if ev else "never ruled",
                            "why": ev.why if ev else "",
                            "round": _round(ev.id) if ev else "",
                        }
                    )
                    del tiles[s]
                    break

    trait_events: dict[str, dict[str, Event]] = collections.defaultdict(dict)
    for s, e in eff.items():
        if "#" in s and s not in carried:
            base, tid = s.split("#", 1)
            trait_events[base][tid] = e

    def recommended_reject(e: Event, lid: str, tid: str) -> bool:
        rep = ctx.reports.get(e.report or "")
        skill = rep.skills.get(lid) if rep else None
        row = skill.traits.get(tid) if skill else None
        return bool(row and row.recommendation == "reject")

    for s, t in tiles.items():
        h, lid = t["harness"], t["lid"]
        cat = catalogs[h]
        ucap = cat.by_logical_id().get(lid) if cat else None
        ev = eff.get(s)
        entry = ctx.upstream.get(s)
        acc = entry.accepted if entry else None
        analysis = None
        if entry:
            analysis = (
                entry.analyses.get(acc) if acc else entry.analyses[max(entry.analyses)]
            )
        desc = (ucap.description if ucap else "").strip()
        if desc in (">-", "|", ">", "|-"):
            desc = ""
        if not desc and ucap:
            desc = upstream_description(cfg, h, ucap.canonical_path)
        if not desc and ev and ev.source:
            desc = upstream_description(cfg, h, ev.source.path or "")
        t["desc"] = " ".join(desc.replace('\\"', '"').split())
        t["analysis"] = acc or ""
        fallback = "removed" if ucap is None else "decided" if ev else "not reviewed"
        t["stage_status"] = status[h].get(lid, fallback)
        t["change"] = changed.get(s, "")
        t["stale"] = t["change"] == "yes"
        t["removed"] = ucap is None
        t["checkpoint"] = None
        if ev:
            t["checkpoint"] = {
                "id": ev.id,
                "kind": ev.kind,
                "why": ev.why,
                "skill": ev.skill,
                "revisit_when": ev.revisit_when,
                "bead": ev.bead,
                "report": ev.report,
                "date": ev.date,
                "round": _round(ev.id),
                "adaptation": ev.adaptation.model_dump() if ev.adaptation else None,
            }
        t["verdict"] = VERDICT.get(ev.kind, "never") if ev else "never"
        listed = list(analysis.traits) if (analysis and acc) else []
        evs = trait_events.get(s, {})
        rows = []
        for tr in listed + sorted(x for x in evs if x not in listed):
            te = evs.get(tr)
            if te is None:
                b = "unruled"
            elif te.kind != "out-of-scope" and HOLD_RE.search(te.why or ""):
                b = "hold"
            else:
                b = {"out-of-scope": "oos"}.get(te.kind, te.kind)
            row: dict[str, Any] = {
                "id": tr,
                "def": tdef(tr),
                "b": b,
                "listed": tr in listed,
            }
            if te:
                row.update(
                    {
                        "why": te.why or "",
                        "revisit": te.revisit_when or "",
                        "event": te.id,
                        "round": _round(te.id),
                        "pending": te.pending or "",
                        "into": te.into or "",
                        "report": te.report or "",
                        "bead": te.bead or "",
                        "rec_reject": te.kind == "defer"
                        and recommended_reject(te, lid, tr),
                    }
                )
                if te.kind in ("adopt", "adopt-merged") and te.skill:
                    row["to"] = resolve_skill(te.skill, forward)
            rows.append(row)
        t["traits"] = rows
        counted = [x for x in rows if x["listed"]]
        t["n_traits"] = len(counted)
        t["mix"] = {b: sum(1 for x in counted if x["b"] == b) for b in TRAIT_BUCKETS}
        ruled = [x["b"] for x in counted if x["b"] != "unruled"]
        comp = None
        if ruled:  # README §5b checkpoint table
            kinds = {("defer" if b == "hold" else b) for b in ruled}
            if kinds == {"adopt"}:
                comp = "adopt"
            elif "adopt" in kinds:
                comp = "adopt-merged"
            elif len(kinds) == 1:
                only = next(iter(kinds))
                comp = "out-of-scope" if only == "oos" else only
            else:
                comp = "reject"
        t["computed"] = comp
        t["mismatch"] = bool(comp and ev and comp != ev.kind)
        t["targets"] = {}
        t["placement_from"] = ""
        t["_pl"] = None
        if analysis and entry:
            key = acc or max(entry.analyses)
            t["_pl"] = (analysis.placement.stage, analysis.placement.substage)
            t["placement_from"] = f"analysis {key}"

    # Provenance of our content: the retained adoptions (README §5b), not the
    # effective rulings that give the verdicts above.
    tile_of = {s: s for s in tiles}
    tile_of.update({c["id"]: s for s, t in tiles.items() for c in t["copies"]})
    prov_rows: dict[str, list[dict[str, str]]] = collections.defaultdict(list)
    targets: dict[str, collections.Counter[str]] = collections.defaultdict(
        collections.Counter
    )
    providing: set[tuple[str, str, str]] = set()  # (tile, dest, trait subject)
    for dest, rows_ in provenance(ctx.events, forward, retired).items():
        for subject, state in rows_:
            base, _, tid = subject.partition("#")
            tile = tile_of.get(base, base)
            prov_rows[dest].append({"tile": tile, "trait": tid, "state": state})
            if state in ("delivered", "pending") and tile in tiles:
                providing.add((tile, dest, subject))
    for tile, dest, _subject in sorted(providing):
        targets[tile][dest] += 1
    # A genuine whole-capability ruling: the unit never had a trait-level event
    # (so no retained trait history either). A unit whose traits were all
    # withdrawn stays without a target.
    trait_history = {
        tile_of.get(e.subject.split("#", 1)[0], "")
        for e in ctx.events
        if "#" in e.subject
    }
    for s in tiles:
        ev = eff.get(s)
        if (
            s not in trait_history
            and ev
            and ev.kind in ("adopt", "adopt-merged")
            and ev.skill
        ):
            dest = resolve_skill(ev.skill, forward)
            whole = "no longer provided" if dest in retired else "whole capability"
            prov_rows[dest].append({"tile": s, "trait": "", "state": whole})
            if whole == "whole capability":
                targets[s][dest] += 1
    for s, c in targets.items():
        tiles[s]["targets"] = dict(sorted(c.items()))

    # Destinations not among our live units: planned (a pending adopt names a
    # unit not built yet), retired, or another document.
    for dest in sorted(prov_rows):
        if dest not in ours:
            is_doc = dest.startswith("doc:") and (cfg.repo_root / dest[4:]).is_file()
            kind = "retired" if dest in retired else "doc" if is_doc else "planned"
            add_ours(
                dest,
                dest.removeprefix("doc:"),
                kind,
                ("Unplaced", ""),
                planned=kind == "planned",
                path=dest[4:] if is_doc else "",
            )
    for dest, dest_rows in prov_rows.items():
        ours[dest]["prov"] = sorted(
            dest_rows, key=lambda r: (r["tile"], r["trait"], r["state"])
        )
    for t in tiles.values():
        if t["_pl"] is None:
            pb = f"doc:{cfg.playbooks_dir.relative_to(cfg.repo_root).as_posix()}/{t['name']}.md"
            if t["targets"]:
                tgt = min(t["targets"].items(), key=lambda kv: (-kv[1], kv[0]))[0]
                if ours[tgt]["stage"] != "Unplaced":
                    t["_pl"] = (ours[tgt]["stage"], ours[tgt]["substage"])
                    t["placement_from"] = f"its adoption target {ours[tgt]['name']}"
            if t["_pl"] is None and t["kind"] == "playbook" and pb in ours:
                t["_pl"] = (ours[pb]["stage"], ours[pb]["substage"])
                t["placement_from"] = "our playbook of the same name"
            if t["_pl"] is None:
                t["_pl"], t["placement_from"] = (
                    ("Unplaced", ""),
                    "no placement in the registry",
                )
        t["stage"], t["substage"] = t.pop("_pl")
    for u in ours.values():
        if u["stage"] == "Unplaced":
            feeders = [
                (t["stage"], t["substage"])
                for t in tiles.values()
                if u["id"] in t["targets"] and t["stage"] != "Unplaced"
            ]
            fed_pl = majority_placement(feeders)
            if fed_pl:
                u["stage"], u["substage"] = fed_pl
                u["placement_from"] = (
                    "majority placement of the upstream units feeding it"
                )

    for t in tiles.values():
        for tgt, n in t["targets"].items():
            ours[tgt]["fed"][t["id"]] = n
    for u in ours.values():
        u["fed"] = dict(sorted(u["fed"].items()))
        u["sources"] = sorted({tiles[x]["source"] for x in u["fed"]})
        u["overlap"] = len(u["fed"]) >= 2

    covered = {(u["stage"], u["substage"]) for u in ours.values() if not u["planned"]}
    for t in tiles.values():
        t["gap"] = (
            t["verdict"] not in ("full", "partial")
            and t["stage"] != "Unplaced"
            and (t["stage"], t["substage"]) not in covered
        )
    sub_gaps = sorted(
        {
            (t["stage"], t["substage"])
            for t in tiles.values()
            if t["stage"] != "Unplaced" and (t["stage"], t["substage"]) not in covered
        },
        key=lambda p: stage_key(*p),
    )
    for t in tiles.values():
        t["lines"] = drawer_lines(t, ours)

    router = build_router(cfg, router_text, playbooks, ours, forward)

    names = sorted(
        {t["source"] for t in tiles.values()},
        key=lambda n: (n not in ("Pocock", "pstack"), n.lower()),
    )
    taken: set[str] = set()
    sources = []
    for i, n in enumerate(names):
        a = _abbr(n, taken)
        taken.add(a)
        hs = sorted({t["harness"] for t in tiles.values() if t["source"] == n})
        sources.append(
            {"name": n, "abbr": a, "idx": i % 10, "harness": hs[0] if hs else n}
        )
    return Built(tiles, ours, router, sources, sub_gaps, status)


def drawer_lines(
    t: dict[str, Any], ours: dict[str, dict[str, Any]]
) -> list[dict[str, str]]:
    """The ✓/✕/⏸ lines: counts, targets and the commonest recorded reason or
    revisit condition, assembled from the ledger."""
    lines = []
    tr = [x for x in t["traits"] if x["listed"]] or t["traits"]
    total = len(tr)
    cp = t["checkpoint"]
    ad = [x for x in tr if x["b"] == "adopt"]
    if ad:
        tc = collections.Counter(x.get("to", "?") for x in ad)
        tgts = ", ".join(
            f"`{ours[k]['name'] if k in ours else k}` ({n})"
            for k, n in sorted(tc.items(), key=lambda kv: (-kv[1], kv[0]))
        )
        defs = "; ".join(shorten(x["def"].rstrip("."), 90) for x in ad[:2] if x["def"])
        pend = sum(1 for x in ad if x.get("pending"))
        extra = f" {pend} still pending." if pend else ""
        end = "" if defs.endswith("…") else "."
        lines.append(
            {
                "b": "adopt",
                "text": f"Adopted {len(ad)} of {total} → {tgts}: {defs}{end}{extra}",
            }
        )
    elif t["verdict"] in ("full", "partial") and t["targets"]:
        tgts = ", ".join(
            f"`{ours[k]['name'] if k in ours else k}`" for k in sorted(t["targets"])
        )
        lines.append({"b": "adopt", "text": f"Adopted as a whole capability → {tgts}."})
    rj = [x for x in tr if x["b"] == "reject"]
    if rj:
        lab, n = commonest([reason_label(x.get("why", "")) for x in rj])
        tail = (
            f"mostly “{lab}” ({n} of {len(rj)})."
            if n > 1
            else f"each for its own reason, e.g. “{lab}”."
        )
        lines.append({"b": "reject", "text": f"Rejected {len(rj)}: {tail}"})
    elif t["verdict"] == "rejected" and cp:
        lines.append(
            {
                "b": "reject",
                "text": "Rejected whole: "
                + shorten(reason_label(cp["why"]), 160)
                + ".",
            }
        )
    df = [x for x in tr if x["b"] == "defer"]
    if df:
        lab, n = commonest([reason_label(x.get("revisit", "")) for x in df])
        rr = sum(1 for x in df if x.get("rec_reject"))
        extra = f" {rr} of them their report recommended rejecting." if rr else ""
        tail = (
            f"“{lab}” ({n} of {len(df)})."
            if n > 1
            else f"each its own condition, e.g. “{lab}”."
        )
        lines.append({"b": "defer", "text": f"Deferred {len(df)} until {tail}{extra}"})
    elif t["verdict"] == "deferred" and cp and not tr:
        rv = cp.get("revisit_when") or "no revisit condition recorded"
        lines.append(
            {"b": "defer", "text": "Deferred whole until “" + shorten(rv, 160) + "”."}
        )
    hd = [x for x in tr if x["b"] == "hold"]
    if hd:
        lab, n = commonest(
            [shorten(x.get("revisit", ""), 160) for x in hd if x.get("revisit")]
        )
        tail = f" until “{lab}” ({n} of {len(hd)})." if lab else "."
        lines.append({"b": "hold", "text": f"On hold {len(hd)}{tail}"})
    oo = [x for x in tr if x["b"] == "oos"]
    if oo:
        lines.append({"b": "oos", "text": f"Out of scope {len(oo)}."})
    return lines


# ---------------------------------------------------------------- router and links

_SKILL_RE = re.compile(r"`/?([a-z][a-z0-9-]*)`|(?<![\w/.-])/([a-z][a-z0-9-]*)")


def names_in(text: str, known: Iterable[str]) -> set[str]:
    known = set(known)
    out = set()
    for m in _SKILL_RE.finditer(text):
        n = m.group(1) or m.group(2)
        if n in known:
            out.add(n)
    for n in known:  # hyphenated names are unambiguous as bare words
        if "-" in n and re.search(rf"(?<![\w/`-]){re.escape(n)}(?![\w-])", text):
            out.add(n)
    return out


def principles_in(text: str, stems: Iterable[str]) -> set[str]:
    """Principle units a text names, as `principle-<stem>` or `principles/<stem>.md`."""
    out = set()
    for s in stems:
        if re.search(
            rf"(?<![\w-])(?:principle-{re.escape(s)}|principles/{re.escape(s)}\.md)(?![\w-])",
            text,
        ):
            out.add(PRINCIPLE_PREFIX + s)
    return out


def _section(text: str, title: str) -> str:
    m = re.search(
        rf"^## {re.escape(title)}\n(.*?)(?=^## |\Z)", text, re.DOTALL | re.MULTILINE
    )
    return m.group(1) if m else ""


def build_router(
    cfg: RegistryConfig,
    router_text: str,
    playbooks: dict[str, Playbook],
    ours: dict[str, dict[str, Any]],
    forward: dict[str, str],
) -> dict[str, Any]:
    skills = sorted(u["id"] for u in ours.values() if u["kind"] == "skill")
    known = set(skills)
    stems = sorted(
        u["id"].removeprefix(PRINCIPLE_PREFIX)
        for u in ours.values()
        if u["kind"] == "principle"
    )
    pb_id = {name: book.holder for name, book in playbooks.items()}
    # The repo's own route lines (`routes.md`) route wherever they stand.
    routes = routes_text(cfg)

    pb_lines = {
        m.group(1): m.group(2)
        for m in re.finditer(
            r"^- `playbooks/([a-z0-9-]+)\.md`: (.+)$",
            _section(router_text, "Playbooks") + "\n" + routes,
            re.MULTILINE,
        )
    }
    principles = [
        {"name": m.group(1), "text": m.group(2), "unit": PRINCIPLE_PREFIX + m.group(1)}
        for m in re.finditer(
            r"^- `principles/([a-z0-9-]+)\.md`: (.+)$",
            _section(router_text, "Principles") + "\n" + routes,
            re.MULTILINE,
        )
    ]
    situations = []
    for line in (
        _section(router_text, "Skills by situation")
        + "\n"
        + _section(routes, "Skills by situation")
    ).splitlines():
        cols = [c.strip() for c in line.strip().strip("|").split("|")]
        if (
            len(cols) == 2
            and cols[0] not in ("Situation", "---")
            and not set(cols[0]) <= {"-"}
        ):
            situations.append(
                {
                    "text": cols[0],
                    "route": cols[1],
                    "skills": sorted(names_in(cols[1], known)),
                }
            )
    agents_path = cfg.repo_root / "AGENTS.md"
    agents_text = (
        agents_path.read_text(encoding="utf-8") if agents_path.is_file() else ""
    )
    agents_names = sorted(names_in(agents_text, known))

    pbs = []
    called_by: dict[str, set[str]] = collections.defaultdict(set)
    links: dict[str, set[str]] = collections.defaultdict(set)
    for name, book in sorted(playbooks.items()):
        steps = []
        for st in book.steps:
            calls = sorted({c.to for c in st.calls})
            steps.append(
                {
                    "id": st.id,
                    "when": " ".join(st.when.split()),
                    "calls": calls,
                    "actions": [a.trait for a in st.actions],
                }
            )
            for c in calls:
                kind, _, callee = c.partition(":")
                if kind == "skill":
                    callee = resolve_skill(callee, forward)
                    called_by[callee].add(f"pb:{name}")
                    links[book.holder].add(callee)
                    links[callee].add(book.holder)
                elif kind == "playbook" and callee in pb_id:
                    links[book.holder].add(pb_id[callee])
                    links[pb_id[callee]].add(book.holder)
        pbs.append(
            {
                "name": name,
                "line": pb_lines.get(name, ""),
                "steps": steps,
                "unit": book.holder,
                "in_router": name in pb_lines,
            }
        )
    named_by: dict[str, set[str]] = collections.defaultdict(set)
    for name, text in pb_lines.items():
        for n in names_in(text, known):
            named_by[n].add(f"pbline:{name}")
    for i, s in enumerate(situations):
        for n in s["skills"]:
            named_by[n].add(f"sit:{i}")
    for p in principles:
        for n in names_in(p["text"], known):
            named_by[n].add(f"pr:{p['name']}")
    for n in agents_names:
        named_by[n].add("agents")
    named_by["mvp-mode"].add("agents")

    # Principles a playbook or skill names (the router itself excepted).
    pr_named_by: dict[str, set[str]] = collections.defaultdict(set)
    texts = [
        (book.holder, (cfg.repo_root / book.path).read_text(encoding="utf-8"))
        for book in playbooks.values()
    ]
    for n in skills:
        if n == "mvp-mode":
            continue
        p = cfg.skills_dir / n / "SKILL.md"
        if p.is_file():
            texts.append((n, p.read_text(encoding="utf-8")))
    for uid, text in sorted(texts):
        for pr in principles_in(text, stems):
            if pr in ours:
                pr_named_by[pr].add(uid)
                links[uid].add(pr)
                links[pr].add(uid)

    for uid, u in ours.items():
        u["links"] = sorted(x for x in links.get(uid, ()) if x in ours and x != uid)
        if u["kind"] == "principle":
            u["named_by"] = sorted(pr_named_by.get(uid, ()))

    sk = []
    for n in skills:
        u = ours[n]
        sk.append(
            {
                "name": n,
                "sources": u["sources"],
                "called_by": sorted(called_by[n]),
                "named_by": sorted(named_by[n]),
                "orphan": not (called_by[n] or named_by[n]),
                "stage": u["stage"],
                "substage": u["substage"],
            }
        )
    for p in principles:
        p["named_by"] = sorted(pr_named_by.get(p["unit"], ()))
    return {
        "playbooks": pbs,
        "principles": principles,
        "situations": situations,
        "skills": sk,
        "agents_names": agents_names,
    }


# ---------------------------------------------------------------- page


def page_data(b: Built) -> dict[str, Any]:
    tiles, ours = b.tiles, b.ours
    stages = sorted(
        {t["stage"] for t in tiles.values()} | {u["stage"] for u in ours.values()},
        key=lambda s: stage_key(s, ""),
    )
    lanes = []
    for st in stages:
        subs = sorted(
            {t["substage"] for t in tiles.values() if t["stage"] == st}
            | {u["substage"] for u in ours.values() if u["stage"] == st}
        )
        lanes.append(
            {
                "stage": st,
                "label": STAGE_LABEL.get(st, st),
                "subs": [s for s in subs if s],
                "gaps": [s for (g, s) in b.sub_gaps if g == st],
            }
        )
    tile_keys = (
        "id",
        "harness",
        "source",
        "kind",
        "name",
        "lid",
        "stage",
        "substage",
        "verdict",
        "desc",
        "copies",
        "stale",
        "change",
        "removed",
        "checkpoint",
        "traits",
        "mix",
        "n_traits",
        "computed",
        "mismatch",
        "targets",
        "gap",
        "lines",
        "placement_from",
        "stage_status",
        "analysis",
    )
    ours_keys = (
        "id",
        "name",
        "kind",
        "stage",
        "substage",
        "desc",
        "boundary",
        "summary",
        "path",
        "record",
        "planned",
        "fed",
        "sources",
        "overlap",
        "placement_from",
        "links",
        "named_by",
        "prov",
    )
    return {
        "lanes": lanes,
        "tiles": [{k: tiles[s][k] for k in tile_keys} for s in sorted(tiles)],
        "ours": [{k: ours[i].get(k) for k in ours_keys} for i in sorted(ours)],
        "router": b.router,
        "orphans": sorted(s["name"] for s in b.router["skills"] if s["orphan"]),
        "sources": b.sources,
    }


def render(cfg: RegistryConfig, b: Built) -> str:
    data = json.dumps(
        page_data(b), sort_keys=True, ensure_ascii=False, separators=(",", ":")
    )
    # Every `<` becomes the JSON escape, so no text in the data (`</script>`,
    # `<!--<script>`) can end or re-enter the script element; JSON.parse restores it.
    data = data.replace("<", "\\u003c")
    tpl = (viewer_dir(cfg) / "template.html").read_text(encoding="utf-8")
    return tpl.replace("/*__DATA__*/null", data)


def write(cfg: RegistryConfig, out: Path | None = None) -> tuple[Path, Built]:
    b = build(cfg)
    path = out or default_out(cfg)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render(cfg, b), encoding="utf-8")
    return path, b
