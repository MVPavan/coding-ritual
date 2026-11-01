"""Report checks (stages-design §What `check` adds, items 1 and 9): structure,
immutability and currency only; facts are never recomputed here."""

from __future__ import annotations

import hashlib
import re
from itertools import combinations

from curation.registry.config import RegistryConfig
from curation.registry.ledger import manifest_reports
from curation.registry.models import Report, ReportRow, ReportSkill, UpstreamTraitEntry
from curation.registry.policy import guide_rules
from curation.registry.reports import supersede_closure

_CITE_RE = re.compile(r"^\S+:\d+(-\d+)?$")


def guide_rule_ids(cfg: RegistryConfig) -> set[str]:
    """The rule IDs of GUIDE.md, from its `- **X-NN**` lines."""
    return set(guide_rules(cfg.guide_path))


def check_reports(
    cfg: RegistryConfig,
    reports: dict[str, Report],
    upstream: dict[str, UpstreamTraitEntry],
) -> list[str]:
    """Immutability, supersession, the current-row ambiguity error and every
    report's rules: in full once sealed, on judged fields only in a draft."""
    errors: list[str] = []
    sealed = manifest_reports(cfg)
    for key, digest in sealed.items():
        path = cfg.repo_root / key
        if not path.is_file():
            errors.append(f"{key}: sealed report has been DELETED")
        elif hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            errors.append(f"{key}: sealed report has been MODIFIED")
    closure = supersede_closure(reports)
    for key, report in reports.items():
        if report.critics_cleared and key not in sealed:
            errors.append(
                f"{key}: both critics passed or accepted but it is not sealed"
            )
        errors += supersession_errors(key, report, reports, sealed, closure)
        errors += report_errors(cfg, key, report, upstream, complete=key in sealed)
    errors += ambiguity_errors(reports, sealed, closure)
    return errors


def supersession_errors(
    key: str,
    report: Report,
    reports: dict[str, Report],
    sealed: dict[str, str],
    closure: dict[str, set[str]],
    sealing: bool = False,
) -> list[str]:
    """`supersedes` names existing reports, never itself, with no cycle; once
    sealed (or sealing), only sealed ones."""
    errors: list[str] = []
    for target in report.supersedes or []:
        if target == key:
            errors.append(f"{key}: supersedes itself")
        elif target not in reports:
            errors.append(f"{key}: supersedes {target!r}, no such report")
        elif (sealing or key in sealed) and target not in sealed:
            errors.append(f"{key}: supersedes {target!r}, not sealed")
    if key in closure.get(key, set()) and key not in (report.supersedes or []):
        errors.append(f"{key}: supersession cycle")
    return errors


def ambiguity_errors(
    reports: dict[str, Report],
    sealed: dict[str, str],
    closure: dict[str, set[str]],
) -> list[str]:
    """Two sealed reports covering one trait and analysis, neither superseding
    the other (transitively)."""
    covered: dict[tuple[str, str, str, str], list[str]] = {}
    for key in sorted(k for k in reports if k in sealed):
        report = reports[key]
        for logical_id, skill in report.skills.items():
            for tid in skill.traits:
                item = (report.harness, logical_id, tid, report.to_sha)
                covered.setdefault(item, []).append(key)
    errors: list[str] = []
    for (harness, logical_id, tid, sha), keys in covered.items():
        for a, b in combinations(keys, 2):
            if a not in closure[b] and b not in closure[a]:
                errors.append(
                    f"{harness}:{logical_id}#{tid} at {sha}: sealed reports {a} "
                    f"and {b} both cover it and neither supersedes the other"
                )
    return errors


def report_errors(
    cfg: RegistryConfig,
    key: str,
    report: Report,
    upstream: dict[str, UpstreamTraitEntry],
    complete: bool,
) -> list[str]:
    """One report's rules. `complete` (sealed, or sealing) requires every
    judged field; a draft is checked only where a judged field is set."""
    errors: list[str] = []
    rule_ids = guide_rule_ids(cfg)
    for logical_id, skill in report.skills.items():
        where = f"{key}: {logical_id}"
        entry = upstream.get(f"{report.harness}:{logical_id}")
        analysis = entry.analyses.get(report.to_sha) if entry else None
        if analysis is None:
            errors.append(f"{where}: no analysis at {report.to_sha}")
        else:
            if skill.upstream_tree_hash != analysis.tree_hash:
                errors.append(f"{where}: upstream_tree_hash is not the analysis's")
            for tid in skill.traits:
                if tid not in analysis.traits:
                    errors.append(f"{where}: {tid} is not a trait of the analysis")
        errors += _pairing_errors(where, skill, complete)
        for tid, row in skill.traits.items():
            errors += _row_errors(
                f"{where}#{tid}", row, skill.compared_with, rule_ids, complete
            )
    return errors


def evidence_errors(
    key: str, report: Report, upstream: dict[str, UpstreamTraitEntry]
) -> list[str]:
    """At `seal` (1.3, 2.1): every skill states its pairing `purpose`; a skill
    with any `new` or `changed` row carries its blind list and a mapping that
    maps every blind line, only into traits of the analysis."""
    errors: list[str] = []
    for logical_id, skill in report.skills.items():
        where = f"{key}: {logical_id}"
        if not (skill.pairing.purpose or "").strip():
            errors.append(f"{where}: pairing.purpose is empty")
        if not any(row.scope in {"new", "changed"} for row in skill.traits.values()):
            continue
        evidence = skill.analysis
        if not evidence.blind or not evidence.mapping:
            errors.append(
                f"{where}: new or changed rows need `analysis.blind` and `mapping`"
            )
            continue
        mapped = {item.line for item in evidence.mapping}
        for line in range(1, len(evidence.blind) + 1):
            if line not in mapped:
                errors.append(f"{where}: blind line {line} is not mapped")
        entry = upstream.get(f"{report.harness}:{logical_id}")
        analysis = entry.analyses.get(report.to_sha) if entry else None
        listed = set(analysis.traits) if analysis else set()
        for item in evidence.mapping:
            for tid in item.to:
                if tid not in listed:
                    errors.append(
                        f"{where}: mapping line {item.line}: {tid} is not a trait "
                        f"of the analysis"
                    )
    return errors


def _pairing_errors(where: str, skill: ReportSkill, complete: bool) -> list[str]:
    """2.1 and check item 9: the flag, with a reason, is set exactly when the
    compared skill, the suggestion and the purpose pick are not all equal."""
    p = skill.pairing
    errors = [
        f"{where}: overlap {holder}: {n} is not a positive count"
        for holder, n in p.overlap.items()
        if n < 1
    ]
    if p.purpose_match is None:
        if complete:
            errors.append(f"{where}: pairing.purpose_match is not judged")
        return errors
    picks = {skill.compared_with, p.suggested or "none", p.purpose_match}
    if len(picks) > 1 and p.flag is None:
        errors.append(
            f"{where}: compared_with, suggested and purpose_match differ "
            "without pairing.flag"
        )
    if len(picks) == 1 and p.flag is not None:
        errors.append(f"{where}: pairing.flag set but the picks agree")
    if p.flag is not None and not p.reason:
        errors.append(f"{where}: pairing.flag needs a reason")
    return errors


def _row_errors(
    where: str,
    row: ReportRow,
    compared_with: str,
    rule_ids: set[str],
    complete: bool,
) -> list[str]:
    errors: list[str] = []
    rec = row.recommendation
    if rec is None:
        if complete:
            errors.append(f"{where}: no recommendation")
        judged = False
    else:
        judged = True
    for cite in row.ours:
        if not _CITE_RE.fullmatch(cite):
            errors.append(f"{where}: ours {cite!r} is not path:line")
    if judged and row.fact in {"present", "variant"} and not row.ours:
        errors.append(f"{where}: a {row.fact} row cites `ours`")
    if row.fact == "variant":
        if row.via is not None and row.via not in row.candidates:
            errors.append(f"{where}: via {row.via!r} is not a candidate")
        if judged and row.via is None:
            errors.append(f"{where}: a variant row selects `via`")
    elif row.via is not None:
        errors.append(f"{where}: `via` is only for a variant row")
    if row.guide is not None:
        for rule in row.guide.rules:
            if rule not in rule_ids:
                errors.append(f"{where}: guide rule {rule} is not in GUIDE.md")
        if row.guide.verdict == "reword":
            if row.delivery != "pending":
                errors.append(f"{where}: a reword verdict is an adopt, pending")
            if not row.rewording:
                errors.append(f"{where}: a reword verdict needs `rewording`")
        if (
            row.guide.verdict == "conflict"
            and rec == "adopt"
            and row.guide.override is None
        ):
            errors.append(
                f"{where}: a conflict verdict is an adopt only with an owner `override`"
            )
    if rec == "adopt":
        if row.delivery is None:
            errors.append(f"{where}: an adopt row needs `delivery`")
        if row.guide is None:
            errors.append(f"{where}: an adopt row needs `guide`")
        if compared_with == "none" and not row.target:
            errors.append(f"{where}: an adopt with compared_with none needs `target`")
        if row.delivery == "delivered" and not (
            row.fact == "present" or (row.fact == "variant" and row.modification)
        ):
            errors.append(
                f"{where}: a delivered adopt needs fact present, or variant "
                "with `modification`"
            )
    elif row.delivery is not None:
        errors.append(f"{where}: `delivery` is only for an adopt row")
    if rec == "defer" and not row.revisit_when:
        errors.append(f"{where}: a defer row needs `revisit_when`")
    return errors
