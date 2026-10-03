# DWS Ultra execution brief

## Role

This document supports the [product goal](product-goal.md). The goal defines
what DWS must achieve and how achievement will be verified. This brief supplies
the context needed to make good implementation choices. Neither document
launches a run merely by existing.

Prepared for the owner's requested five-hour Codex Ultra development window,
2 October 2026. Refresh changing runtime and dependency facts at activation.

The owner activated this run at **11:35:36 UTC on 2 October 2026**; its absolute
deadline was **16:35:36 UTC**. Implementation and outcome evidence are recorded
in the [vision acceptance record](verification/vision-acceptance.md). The
starting position and unresolved proposals below describe the pre-run context,
rather than the delivered product's current status.

## Assignment and time budget

When the owner activates the run, build the complete DWS product toward the
vision and verify the result. The owner has **five hours remaining** to make
best use of the available Codex allowance. Establish one absolute UTC deadline
from the remaining window at activation and carry it through handoffs and
resumptions; do not grant a fresh five hours on every restart.

You decide how to organize and orchestrate the work: implementation order,
parallelism, agent responsibilities, runtime-supported models, and allocation
of effort between decisions, implementation, integration, and verification.
There is no prescribed phase sequence or coordinator/worker hierarchy in this
brief. Use concurrency where it helps and retain clear ownership of overlapping
edits. Judge efficiency by progress toward a verified working product.

The owner's active-run instruction prioritizes product implementation and
substantial integration/end-to-end testing. Do not add simple unit-test suites.
Avoid repetitive tracking, review rituals, and agent-governance work that does
not improve the working product or its verification.

Do not assume five hours guarantees completion. At the deadline, stop admitting
new work, preserve the result and evidence, and report the goal's actual
acceptance status with a resumable handoff inside DWS. Do not relax acceptance
criteria to fit the clock. Stop early if the vision is already verified.

## Strict DWS boundary

All task-controlled writes belong inside **`dws/` relative to the repository
root**. This is the independent product directory, not the surrounding
repository's root application.
Keep source, dependencies/locks, container configuration, user docs, verification
tooling, reports, worker checkouts, caches, logs, scratch files, and configured
persistent DWS data beneath it. Configure tools' cache/temp/environment paths
accordingly; do not rely on defaults that write to a user's home or `/tmp`.
The same boundary applies to every delegated worker.

Do not change the parent project's source, tests, policies, orchestration tools,
or global Codex configuration to make DWS work. Do not place new worktrees or
run artifacts outside the product folder. Existing parent documentation and
qualification records are read-only context; preserve unrelated changes.

The existing Beads database resolves outside this product directory. Existing
IDs may be consulted as context, but writing that shared tracker requires an
explicit boundary exception or an authorized product-local tracking arrangement.
Do not silently update it, create a duplicate tracker, or replace task tracking
with a Markdown checklist. This brief and the goal are product contracts, not
task-status ledgers.

## Starting position

| Area | Evidence-backed checkpoint | Consequence |
|---|---|---|
| Product package | Independent `pyproject.toml`, `uv.lock`, Python package, console entrypoint, tests, and tooling exist | Preserve this standalone boundary |
| Actual application | Current CLI reports package information/help; storage, discovery, acquisition, retrieval, jobs, and operator capabilities are not implemented | Foundation work is not a functioning evidence product |
| Runtime qualifications | QMD lexical behavior, process locks, application image/volume behavior, and SearXNG integration have qualification evidence | Reuse relevant evidence; requalify what the chosen runtime actually changes |
| Browser containment | A corrected candidate and test evidence exist; final independent acceptance remains outstanding in the recorded handoff | Do not claim rendered acquisition is fully accepted |
| Packaging | Existing Dockerfile installs application dependencies at build time; existing Compose file is a qualification profile | Neither implements the newly discussed startup-managed environment or full production topology |
| Retrieval decision | `cr-0km.15` was added as a prerequisite to resumed implementation | QMD replacement is under evaluation, not adopted |

Qualification probes answer questions about dependency behavior, concurrency,
image contents, persistence, and browser containment. Keep evidence that protects
the product contracts. Their count is not product progress, and passing them
does not demonstrate the end-to-end user journeys.

## Owner-required retrieval decision

**Resolve the retrieval-backend comparison before resuming dependent DWS
implementation.** This is the owner's explicit prerequisite, not a requested
phase schedule. Organize the comparison and its independent critique freely.

Compare the existing QMD lexical approach with **embedded Turso Database using
Tantivy-backed full-text search**, ordinary **SQLite FTS5**, and direct Python
Tantivy bindings where useful. Verify exact released features, maturity,
licensing, wheel/platform availability, and API/process limitations from
primary sources; do not confuse Turso's embedded database with a requirement to
use its hosted service.

Use the same representative retained-snapshot corpus. Compare total dependency
and image footprint, cold/warm memory and latency, index construction and
update/delete behavior, scope correctness, exact passage/location mapping,
restart/rebuild, and actual API/worker process compatibility. Record how much
document mapping, chunking, snippets, and maintenance DWS would have to own.
Separate measured results from expectations and missing measurements.

The previously qualified application image was about 1.66 GB in total; that is
not a measurement of QMD's isolated contribution or runtime memory. A smaller
candidate must still meet the evidence and recovery contracts.

Keep **management SQLite unchanged** for this evaluation. The owner primarily
requested a replacement for QMD's retrieval layer, not a management-database
migration. Vector support is not a requirement to enable embeddings or add
inference. Record a measured recommendation and fresh independent review inside
DWS; reconcile the selected design with the rationale of historical
ADR-018/020/023 before dependent implementation. Preserve useful prior evidence.

## Technology direction and unresolved choices

The following separates the established direction from discussed packaging and
adapter proposals. Resolve choices against the goal; do not present proposals
as already implemented or measured.

| Concern | Direction / decision boundary |
|---|---|
| Core | Python application; shared service contracts; FastAPI/Pydantic for the local command API; real CLI; independent worker |
| Python management | Use `uv` with a locked product environment; Python 3.13 is the current package baseline |
| Base image | A Debian-based Python image is a Linux image. Include required OS/native runtime libraries; a generic base alone does not guarantee every dependency works |
| App dependency installation | Owner preference: avoid baking Python application packages during image build. Prepare a container-compatible environment with `uv` from the locked product manifest before serving |
| Cache and environment | Persist a product-local bind-mounted `uv` cache and a separate Linux environment. Cache files do not replace installed dependencies; do not reuse an incompatible host environment |
| Environment lifecycle | Prepare once under coordinated ownership; API and worker must not concurrently mutate a live shared environment. Upgrade locks deliberately and validate/restart against the prepared environment |
| Compose topology | One Compose deployment, normally `dws-api`, `dws-worker`, `searxng`, and browser-capable `crawl4ai`; API/worker may share a base image with different commands |
| Search | SearXNG primary, DDGS lightweight fallback library; fallback responses retain common schemas and explain limitations |
| Downloads | HTTPX is the candidate for controlled, bounded streaming acquisition; it does not itself turn HTML into evidence files |
| HTML normalization | Evaluate Crawl4AI's HTML-to-Markdown path before retaining a second extractor. Trafilatura is optional if measured evidence quality justifies it. Preserve useful canonical content and mappings |
| Rendered acquisition | Crawl4AI browser service acquires/renders beneath DWS-owned policy, budgets, durable jobs, and crawl frontier |
| PDFs | A text-PDF parser with page mappings and explicit extraction limitations; no mandatory OCR |
| Metadata/artifacts | Management SQLite plus retained canonical files; short owned transactions; rebuildable retrieval state |
| Retrieval | Pending comparison above; do not assume QMD, Turso, or Tantivy already wins |
| MCP | Thin FastMCP adapter over the engine; verify/pin a compatible release and actual host interoperability; no duplicate job or evidence system |
| Optional providers | Separate explicit opt-in configuration/profiles; no paid or model-backed service required by default |

The generic-image preference applies to DWS application packages; it does not
mean rebuilding SearXNG or Crawl4AI as Python libraries inside the same service.
Their independent provider images must still be pinned and qualified. If QMD
remains, account for its Node/native dependency preparation separately from
`uv`. Any replacement must remove unnecessary runtime requirements only after
its compatibility and evidence behavior are demonstrated.

## Verification and final handoff

Use the goal's V1–V12 outcomes as the acceptance contract. Organize verification
however best supports efficient development; reserve enough capacity to verify
the integrated installation and fix material findings. Require a fresh reviewer
separate from the author for consequential decisions and final acceptance.

Keep compact, reproducible evidence inside DWS. Existing tests and qualification
receipts remain useful at their demonstrated scope; changed pins or topology
need relevant new checks. A skipped prerequisite or unavailable live provider
is an unverified limit, not a pass. Check the final diff and status, preserve
unrelated changes, and keep commits/publishing/deployment behind their existing
authorization boundaries.

At completion or the time limit, report: the vision verdict; verified usable
capabilities; failed/unverified outcomes; selected stack and rationale; actual
checks and evidence; instructions to install/use the current product; and a
concise continuation point if work remains. All persistent handoff material
belongs inside DWS.

## Historical source provenance

This self-contained handoff consolidates the owner's current instructions with
the existing DWS charter, PRD v1.1, technical design, and recorded qualifications.
Their legacy repository paths are `docs/workstreams/dws/README.md`,
`docs/brainstorms/dws/DWS_PRD.md`, `docs/brainstorms/dws/DWS_Design.md`, and
`docs/verification/dws/`. The previous execution goal at
`docs/plans/dws/implementation-goal.md` imposed narrower delivery and worker
prescriptions. Those execution prescriptions are superseded where they conflict
with this owner-requested goal and orchestration freedom. Legacy sources are
read-only background, not required external components of the delivered tool.
