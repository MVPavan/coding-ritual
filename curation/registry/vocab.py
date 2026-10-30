"""Shared vocabulary: lifecycle coordinates, event kinds and ID patterns."""

from __future__ import annotations

import re

SUBSTAGES: dict[str, frozenset[str]] = {
    "Discovery": frozenset({"Research", "Charting"}),
    "Intake": frozenset({"Triage", "Clarification"}),
    "Design": frozenset(
        {"Grounding", "Specification", "Architecture", "Decomposition"}
    ),
    "Building": frozenset({"Implementation", "Diagnosis"}),
    "Verification": frozenset({"Testing", "Review", "Validation"}),
    "Delivery": frozenset({"Integration", "Release", "Closure"}),
    "Operations": frozenset({"Monitoring", "Response", "Maintenance"}),
    "Improvement": frozenset({"Retrospective", "Codification", "Evaluation"}),
    "X": frozenset({"Coordination", "Continuity", "Governance", "Communication"}),
    "U": frozenset({"Tooling", "Tutoring"}),
}


STAGE_ORDER = list(SUBSTAGES)


ALL_SUBSTAGES = frozenset().union(*SUBSTAGES.values())


# Trait placements use only these domains (GUIDE.md §1; traits-design §1).
TRAIT_DOMAINS = frozenset({"core", "engineering"})


DOMAIN_ORDER = ["core", "engineering", "design", "marketing", "sales", "media"]


# Stubs with no target (README §2 rule 5); the in-progress drafts folder.
STUB_SKILLS = frozenset({"cost-estimate", "verification-before-completion"})


IN_PROGRESS_DIR = "in-progress"


REFERENCE_KINDS = frozenset(
    {"adopt", "adopt-merged", "reject", "defer", "out-of-scope"}
)


OURS_KINDS = frozenset({"add", "update", "merge", "split", "rename", "retire"})


EVENT_KINDS = REFERENCE_KINDS | OURS_KINDS


# Trait subjects (<repo>:<logical_id>#<trait_id>) may only carry these kinds (§5);
# `adopt-merged` is a capability-checkpoint kind, never a trait kind (review #16).
TRAIT_KINDS = frozenset({"adopt", "reject", "defer", "out-of-scope"})


_SLUG_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*")


# Trait IDs in the two trait files are kebab slugs (traits-design Terms).
_TRAIT_ID_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
