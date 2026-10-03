# DWS product goal: achieve the vision

## Purpose and activation

This is the outcome contract for the next owner-authorized DWS implementation
run. Creating or reading it does not launch that run. The companion
[Ultra execution brief](ultra-execution-brief.md) supplies the starting context,
time budget, and open technical decisions. This document defines success.

The final question is **Have we achieved the DWS vision?** A completed plan,
number of probes, passing component tests, or exhausted time allowance is not
an answer. Demonstrated product behavior is the answer.

## Vision

**One complete, reusable web evidence tool that every project and research
agent can use.**

DWS supplies the mechanical foundation of research once: discover sources,
acquire selected pages and documents, crawl bounded sites, normalize and retain
evidence, find relevant passages, and read exact captured content. Projects
should not each rebuild search clients, scrapers, retries, PDF handling,
storage, retrieval, and recovery.

The caller owns the research questions, source judgment, interpretation,
methodology, and final conclusions. DWS provides compact, traceable evidence
through stable interfaces. Changing the caller's model, skills, or application
must not require changing DWS or invalidate its retained citations.

The default product is local, provider-neutral, and usable without inference,
embedding generation, paid-provider credentials, or an installed research
agent. It must be a working independent tool, with installation, operation,
maintenance, and user documentation included.

## Applications the same tool must support

| Application | What DWS provides | What the calling application supplies |
|---|---|---|
| Technical and architecture research | Discover documentation and papers; acquire sources; retrieve and verify passages | Questions, comparisons, architectural judgment |
| Learning and general topic research | Search and retain useful sources; return bounded evidence on demand | Learning strategy, explanations, synthesis |
| Public-company and investment research | Acquire public filings, reports, announcements, and other accessible sources | Financial analysis, valuation, investment conclusions |
| Market and competitor research | Gather and revisit public product and company material | Comparison framework and business conclusions |
| Documentation assistants | Crawl a bounded documentation area and retrieve scoped passages | Answer generation and application-specific instructions |
| Citation and quotation verification | Resolve exact retained snapshots and passage locations | Claim assessment and citation selection |
| Repeated research and monitoring | Capture successive versions and retain earlier evidence | Scheduling, change interpretation, alerts |
| Several agents or projects | Share one service with explicit workspaces and runs | Agent orchestration and project workflow |

These are applications of the same evidence capabilities, not separate DWS
research engines. Supporting them does not promise universal website access or
automatic completion of every research task.

## Required product capabilities

| Capability | Required user-visible outcome |
|---|---|
| `search` | Discover ranked public-web URLs with useful metadata and explicit provider/freshness limitations; do not present snippets as acquired evidence |
| `fetch` | Acquire a selected URL, retain a useful normalized snapshot, and return provenance, a bounded excerpt, and a stable handle |
| `crawl` | Submit a durable, bounded crawl and obtain progress, retained partial results, and a manifest explaining outcomes and why traversal stopped |
| `retrieve` | Find bounded relevant passages within retained evidence and the requested workspace/run/crawl/document scope |
| `read` | Read an exact bounded range or section of a retained snapshot, including immediately after capture and while its search index is unavailable |
| `job_status` | Inspect an acknowledged job's durable state, progress, results, failures, and limits |
| `job_cancel` | Request cancellation, stop admitting new work, preserve already acquired evidence, and disclose residual work |

The core, local command API, and real `dws` CLI share these contracts. The
complete vision also includes a thin MCP adapter for agents over the same
contracts, state, and jobs. The CLI must remain independently useful without
MCP installed. Engine/CLI completion and complete vision completion are distinct
claims if the adapter is still absent.

Operator capabilities include workspace/run organization; pin/unpin and
export; explicit expiry and garbage collection with dry-run; index status and
rebuild; useful local diagnostics; safe backup/restore; and documented dependency
upgrades. Include a portable host integration example without making the host
agent or its research methodology a core dependency.

## Evidence and reliability contract

- Retained snapshots are immutable. Record requested/final URLs, redirects,
  capture time, content hashes, normalization identity, and useful location
  mappings. Unknown source publication dates remain unknown.
- Returned passages and excerpts match the identified normalized snapshot.
  Preserve relevant original artifacts and transformation records; extraction
  or pruning must not silently replace evidence with a generated summary.
- A pinned citation still resolves to its named capture after the live page
  changes, after restart, and after backup/restore. Freshness and retention are
  different policies. Expired content produces an explicit unavailable/expired
  outcome rather than a silent live-page substitution.
- Discovery and acquisition failures, partial crawls, truncation, stale reuse,
  extraction limitations, and indexing delays are visible in bounded,
  machine-readable responses. Zero search hits must not hide incomplete scope.
- Scope is enforced during retrieval. Unrelated workspaces never leak into
  results; filtering a small global result set must not falsely imply the
  requested subset has no matching evidence.
- Canonical artifacts and management state survive search-index loss. The
  selected index is rebuildable; direct reads do not depend on it.
- Jobs persist before acknowledgement. Idempotency, ownership, checkpoints,
  and safe recovery preserve acknowledged work across client/API/worker
  interruption. Completed crawl pages are not blindly reacquired on restart.
- Several callers share bounded resources. Enforce configured page/depth/time,
  byte, retry, queue, process, storage, and output limits. Measure the supported
  concurrency envelope rather than promising unlimited capacity.
- Public-web acquisition enforces outbound policy on targets, redirects, and
  browser subrequests. A policy denial cannot become permission through a
  fallback. Protect local access, secrets, filesystem paths, and subprocesses.

## Default content and deployment

Support public static HTML/text, browser-rendered HTML, and text-bearing PDFs
with useful page/location mappings. Explain failed extraction and scanned or
complex PDF limitations honestly. Mandatory OCR, authenticated private-site
automation, paywall bypass, arbitrary browser control, audio/video processing,
and unrestricted local-file indexing are outside this goal.

Provide a reproducible local installation and one documented Compose deployment
with persistent state, readiness checks, bounded worker execution, and clean
restart behavior. Search and browser providers remain adapters. Optional hosted
providers must require explicit configuration and must not be needed for the
default workflow. Lock and record actual tested dependencies and images.

## How we verify that the vision has been achieved

Verify integrated behavior through the installed product, using deterministic
fixtures plus separately identified live smoke checks. Mocks and library probes
can support diagnosis; they cannot alone establish product acceptance.

Prioritize working product capabilities. Add a small set of substantial product,
integration, and end-to-end scenarios that exercise real services, persistence,
providers, and recovery. Do not add simple unit-test suites or inflate test
counts. Reuse existing checks when relevant. Keep tracking, agent coordination,
and review concise; spend effort on implementation and evidence that changes a
product decision, rather than governance ceremony.

| Outcome | Required demonstration |
|---|---|
| V1 — Independent working tool | Install/start from documented product-local files with hosted/model keys absent; exercise the seven capabilities through the CLI/local API |
| V2 — Reusable across applications | Demonstrate a technical-research journey and a different-domain journey against the same unmodified service; the caller performs synthesis |
| V3 — Useful acquisition | Acquire static, rendered, and text-PDF fixtures; inspect useful artifacts, mappings, bounded excerpts, and honest failure/quality signals |
| V4 — Exact retained evidence | Compare returned passages with their snapshots; change the live source and prove a pinned old citation still returns the original capture |
| V5 — Scoped retrieval and independent reads | Test colliding terms across workspaces/subsets, long-document passages, and unavailable/pending indexing; correct scope and immediate direct reads remain available |
| V6 — Durable bounded crawl | Exercise cycles, off-scope links, failures, limits, disconnects, restart, repeated submission, and cancellation; manifests and counts reconcile without losing partial evidence |
| V7 — Shared operation | Run several callers with acquisition, reads, retrieval, and indexing overlapping; prove bounded admission, consistent ownership, and no scope leakage |
| V8 — Retention and recovery | Demonstrate pin/export/expiry/cleanup dry-run, disk-pressure handling, index-only rebuild, and backup/restore with a known pinned citation |
| V9 — Safe, honest degradation | Exercise unsafe targets/redirects/subrequests, malformed and oversized inputs, provider outages, and secret handling; policy holds and failures remain distinguishable from empty results |
| V10 — Operational completeness | Replace/restart containers without losing persistent work; demonstrate diagnostics and a controlled locked-dependency upgrade; document tested builds and remaining limits |
| V11 — Agent interoperability | Use an actual MCP client for the same capabilities and retained-resource reads; demonstrate CLI/MCP contract parity without duplicate application logic |
| V12 — Standalone ownership | Install, operate, and verify DWS without depending on the surrounding repository's application, orchestration engine, or sources; all project-owned artifacts stay within the DWS boundary |

Write a concise acceptance record inside `dws/docs/verification/`, with paths
interpreted from the repository root. For each V1–V12 outcome, record
**verified**, **failed**, or **unverified**, the actual commands and observations,
the relevant evidence paths, tested build identities, and material limits.
Include a fresh independent review of the integrated result; distinguish review
findings from fixes that have actually been checked.

The final verdict must state **vision achieved** only when all required outcomes
are demonstrated and no material correctness, integrity, safety, or usability
gap remains. Otherwise state **vision not yet achieved**, describe the usable
capabilities, and identify the remaining gaps. A five-hour deadline does not
weaken this definition or turn unverified behavior into a pass.

## Execution freedom and ownership boundary

Choose implementation order, parallel work, agent organization, and efficient
use of the available runtime freely. This goal specifies outcomes, not phases
or a prescribed sequence. Preserve the owner's explicit retrieval-backend
decision prerequisite described in the supporting brief.

For this run, the writable product boundary is **`dws/` relative to the
repository root**, the independent distribution containing this document.
Keep implementation,
documentation, configuration, tests, reports, worktree/worker artifacts,
caches, logs, temporary files, and configured application state inside that
directory. Do not write to repository-root sibling directories, other projects,
shared external trackers, or user/global configuration. DWS must own its
installation and verification tooling. Existing surrounding material may be
consulted as read-only historical context; required ongoing product guidance
must be self-contained inside DWS.

This document expresses the current owner's vision and folder boundary. It
supersedes conflicting older execution prescriptions about worker roles,
fixed sequencing, artifact locations, and limiting the ultimate goal to the CLI
delivery alone. Existing evidence-integrity and safety contracts remain binding.
Implementation activation, commits, publishing, and deployment still require
their applicable authorization; this document's creation authorizes none of
those actions by itself.
