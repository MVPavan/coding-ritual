# DWS vision acceptance — 2 October 2026

## Final independent critic audit

**Current verdict: vision achieved at the documented product scope.** The
owner's review loop completed **ten fresh GPT-6.1/xhigh whole-product critiques**.
All forty-eight Important/Minor findings from rounds 1–9 have corrections;
the tenth complete critic reports **CLEAN=true, Important 0, Minor 0**, with no
deferred confirmed finding.

The final reviewed build passed all five qualification groups at
**20:14:25–20:20:54 UTC**: ten integration journeys, all 86 actual browser cases
and twelve rejected mutations, protected rendered fixture, live public/CLI/all
seven MCP capabilities, and installed-product operations including five fresh
MCP preparation cases. The critic independently bound all fifty-nine frozen
inputs, fifteen source/wheel/installed/deployed payloads, primary receipts,
browser controls, and exact recovered evidence. Its separate Store/Engine/MCP
failure and callback rollback probe passed. Report and final bindings:
`.runtime/critic-review/round-10/review.md` and
`.runtime/critic-review/round-10/final-binding.json`.

Final wheel SHA-256:
`865ec85ba073525d37f234a703f5b986ba373932deb7793e25a851f99038e712`.
Current primary qualification:
`.runtime/verification/20261002T201425Z-4079616/summary.json`.
All twelve required outcomes are supported by actual product evidence and the
complete independent audit. The limits below still apply. Final result
annotations follow the review; runtime, tests, build and deployment remain the
qualified candidate.
The original acceptance below is historical.
All findings, their evidence, current build identity, and qualification limits
are in the [critic audit](critic-review.md).

## Original acceptance

Contract: [product goal](../product-goal.md). Product version: **0.1.0**.
The authorized window began at **11:35:36 UTC**, with deadline **16:35:36 UTC**.
This record reports product behavior, rather than completed planning or probe
counts. Paths below are relative to this standalone product directory.

**Verdict: vision achieved at the documented scope.** All twelve required
outcomes have been demonstrated, the final installed/deployed code matches the
verified build, and fresh independent review found no remaining material gap.
The content, concurrency, browser and platform limits below remain explicit;
this verdict does not promise universal website access or unmeasured capacity.

**Follow-up replication:** the owner's subsequent coverage audit added an
actual deterministic rendered fixture and explicit depth/deadline, queue/retry,
lost-acknowledgement and encoded-response boundaries. The portable full command
then passed all groups, including five integration journeys. See the
[end-to-end scenario record](end-to-end-scenarios.md) for the fresh results,
repeatable command, exact scope and checker-cache provenance note. The earlier
four-test timing and wheel identities below describe the original acceptance
run; they are not the new replication's timings or wheel hash.

## Outcome evidence

| Outcome | Status | Actual demonstration and evidence |
|---|---|---|
| V1 — Independent working tool | Verified | The installed CLI exercised all seven capabilities against a real API and independent worker. Compose started without model or paid-provider keys. The isolated wheel consumer ran API/worker without MCP or repository sources. `tests/integration/test_product.py`; `.runtime/standalone-product-results.json`; `.runtime/live-product-results.json`. |
| V2 — Reusable across applications | Verified | The same unchanged service supported technical HTML/table research and a public-company PDF filing fixture, with caller-selected queries. The portable host integration example retained real SQLite documentation. Research journey and `.runtime/host-integration-example.json`. |
| V3 — Useful acquisition | Verified | Static HTML, tables, a text PDF with page mappings, and actual JavaScript-rendered `quotes.toscrape.com/js/` were captured. Original bytes/rendered HTML and normalized evidence were retained. Blank PDF, missing source, oversized/compressed response, and browser quality limitations were explicit. Research/access journeys; `.runtime/live-product-results.json`. |
| V4 — Exact retained evidence | Verified | Retrieved character spans matched canonical text and bounded line reads. Updating the fixture produced another snapshot; pinned old text remained exact. The pinned live example survived consumer/container replacement. Research journey; maintenance and MCP receipts. |
| V5 — Scoped retrieval and independent reads | Verified | Four workspaces shared colliding terms alongside eight stronger unrelated decoys. Workspace/run/document/crawl filters returned the correct captures. Deleted index files left reads available and retrieval explicitly partial; reconstruction restored hits. Shared and crawl journeys. |
| V6 — Durable bounded crawl | Verified | Actual CLI submission persisted before acknowledgement. Killed API/worker resumed the same job without reacquiring completed pages. Cycles, off-scope links, one failed page, page limits, manifest counts, repeated idempotent submission, and cancellation were exercised. Changed request/key conflict and policy-denied replay were also verified. Crawl journey; `.runtime/jobs-replay-product-check/result.json`; real MCP receipt. |
| V7 — Shared operation | Verified | Four equivalent callers shared one HTTP acquisition and snapshot; reads/retrieval overlapped held acquisitions. The independent worker indexed another capture during the overlap. Seven competing callers against a six-request admission limit produced explicit `429 busy` for excess work, then normal operation resumed. Cross-workspace reads were rejected. Shared journey; final JUnit receipt. This is the measured envelope, not a sustained-load claim. |
| V8 — Retention and recovery | Verified | Pin/export/expiry/GC dry-run, independent index reconstruction, corrupted-artifact repair, old-backup refusal preserving newer pins/jobs, and disk-pressure rejection/recovery all passed. Five write paths returned 507 while retained reads/status and retention cleanup remained useful. `.runtime/product-tests/final-results.xml`; `.runtime/jobs-replay-product-check/quota-result.json`. |
| V9 — Safe, honest degradation | Verified | Real API/CLI journeys denied unauthorized access, unsafe targets/redirects, malformed headers/schema, oversized wire/decompressed content and provider outages. Adversarial proxy/redirect collectors did not receive CLI bearer credentials. Existing browser traffic qualification was independently bound to the deployed protected provider; scope and exclusions are below. |
| V10 — Operational completeness | Verified | Actual locked DWS preparation upgraded 0.0.1→0.1.0; live preparation was refused; API/worker replacement preserved a pinned citation and diagnostics passed. A separate installed-product environment upgraded actual idna 3.19→3.20 through locked uv preparation with consumers stopped; exact pinned evidence and acknowledged jobs survived restart. `.runtime/maintenance-product-results.json`; `.runtime/live-preparation-refusal.json`; `.runtime/dependency-upgrade/receipt.json`. |
| V11 — Agent interoperability | Verified | A real HTTP MCP client invoked all seven tools, read the retained resource, compared API text/maps/passages and job identities, and preserved evidence after cancellation. `.runtime/mcp-full-journey/receipt.json`; `.runtime/live-product-results.json`. The adapter uses the same engine/state. |
| V12 — Standalone ownership | Verified | A built wheel installed into an isolated environment ran from a separate working directory, without `PYTHONPATH`, optional MCP, or surrounding repository sources. Source, deployment, examples, state, cache, temp files and verification records are inside DWS. `.runtime/standalone-product-results.json`; [operator guide](../usage.md); [host integration](../host-integration.md). |

## Checks and reproduction

Four substantial journeys in `tests/integration/test_product.py` use real HTTP
fixtures and separate installed CLI/API/worker processes. They cover the
technical/PDF research journey, shared scope/retention/recovery, interrupted
crawling, and access/provider/resource degradation. No simple unit-test suite
was added. Fixture-only private-host allowance is confined to each isolated
test environment; the deployed default denies private targets.

Final complete run: **4 passed, 0 failures/errors/skips, 21.262 seconds**,
started at **13:01:47 UTC**. The four fixture directories, in scenario order,
are `.runtime/product-tests/journey-xcximpnv`, `journey-retqhof9`,
`journey-4d_z7dqk`, and `journey-_9tqapfe` under the same directory. The initial
restore failure and a timing-sensitive admission assertion were corrected;
the final complete receipt above verifies the resulting behavior.

```bash
scripts/setup.sh start
curl --fail http://127.0.0.1:8765/ready

PYTHONDONTWRITEBYTECODE=1 TMPDIR="$PWD/.runtime/tmp" \
  .venv/bin/python -m pytest tests/integration \
  --basetemp=.runtime/pytest -o cache_dir=.runtime/pytest-cache \
  --junitxml=.runtime/product-tests/final-results.xml -q
.venv/bin/ruff check src/dws tests/integration
.venv/bin/ruff format --check src/dws tests/integration
.venv/bin/mypy --strict --cache-dir .runtime/mypy-cache src/dws
bash -n scripts/setup.sh
sh -n docker/prepare_environment.sh docker/run_application.sh
docker compose --env-file .runtime/owner.env config --quiet

UV_CACHE_DIR="$PWD/.runtime/uv-cache" \
  UV_PYTHON_INSTALL_DIR="$PWD/.runtime/python" \
  TMPDIR="$PWD/.runtime/tmp" uv build --wheel --offline --out-dir .runtime/dist
```

Prepare the host verification environment with the README's locked `uv sync`
instructions first. Socket/Docker/public-web checks required narrow authorized
sandbox escalation. One automatic approval review timed out; the permitted
single retry succeeded. Shellcheck was unavailable; shell syntax checks ran.

Separate live/consumer checks actually ran:

- `.venv/bin/python -B .runtime/live_product.py`: real public static/PDF/rendered
  acquisition, useful SearXNG discovery, installed CLI and MCP parity.
- `.venv/bin/python -B .runtime/standalone_product.py`: wheel-only independent
  API/worker, fresh static capture, exact read, indexing and pin, without MCP.
- `.venv/bin/python .runtime/maintenance_product.py`: stop consumers, locked
  preparation, consumer replacement, readiness and pinned evidence continuity.
- `.venv/bin/python .runtime/mcp-full-journey/verify.py`: all seven real MCP
  calls, exact resources, scoped passages, crawl/status/cancellation.
- The documented Python block in `docs/host-integration.md` ran unchanged using
  the isolated installed CLI; its response is retained locally.
- `.venv/bin/python -B .runtime/final_deployment.py`: after the documented
  `scripts/setup.sh start`, readiness and retained pin passed; real MCP/API
  reads matched, all seven tools were present, deployed browser module hashes
  matched the audited provider, and every wheel Python member matched the final
  source. Receipt: `.runtime/final-deployment-results.json`; source/config hashes:
  `.runtime/final-build-manifest.json`.

The `.runtime/` files are local verification artifacts, ignored by Git and
excluded from the wheel. They contain evidence for this run, not required host
frameworks. The product tests and installation instructions are distributable.
Public upstream results are time-specific smoke evidence, not availability
guarantees.

## Tested identities and selected architecture

| Component | Tested identity |
|---|---|
| Application | DWS 0.1.0; wheel SHA-256 `5894ce64126ef57e4d9f6885e7160e862903491f5167e3e98692d1ec7a20bec6` |
| Host runtime | Python 3.13.9; SQLite 3.50.4 |
| Container runtime | Python 3.13.12 on Debian Bookworm; SQLite 3.40.1 |
| Generic application base | `python:3.13.12-slim-bookworm@sha256:3121f8b0804aa3698ab750d9a39ea4a42657a385c9b133722b915e55c51551a6` |
| uv | 0.9.8, pinned image digest in `Dockerfile` |
| API/contracts | FastAPI 0.142.2; Pydantic 2.13.5; Uvicorn 0.54.0 |
| Acquisition | HTTPX 0.28.1/httpcore 1.0.9; Markdownify 1.2.3; BeautifulSoup 4.15.0; pypdf 6.19.0 |
| Discovery | DDGS 9.16.0; SearXNG image digest `a93b665d10ce0675e8d2124187943111399ba69f384228c51b4cd21fdceda0bc` |
| Optional MCP | FastMCP 4.0.10; MCP SDK 2.2.0 |
| Browser | Crawl4AI 0.9.2; Chromium 149.0.7827.55; protected overlay described below |
| Retrieval | Separate SQLite FTS5; management SQLite and canonical artifacts remain authoritative |

One Compose deployment has a finite environment preparation job plus API,
worker, SearXNG, and Crawl4AI. Application packages are installed at preparation
time from `uv.lock`; none are baked into the generic application image. The uv
cache and separate container environment are persistent product-local mounts.
Preparation cannot mutate an environment used by serving consumers. Only the
authenticated API publishes a loopback host port.

The third-party upgrade used an isolated **installed wheel**, rather than the
main serving environment. UV verified compatible idna constraints; only idna
changed in the lock. Both API and worker stopped before synchronization and
restarted afterwards, with a changed live fixture and exact old pinned content.
Main product manifest/lock/environment remained unchanged. The separate Compose
maintenance check verifies real consumer replacement and preparation locks;
the two checks establish different parts of the maintenance workflow.

The independently reviewed [retrieval comparison](retrieval-choice.md) selected
FTS5 after actual scope/update/delete/reopen and independent-process checks.
Turso 0.8.1's experimental FTS worked in one process but rejected shared
reader/writer access in its default mode. Direct Tantivy was fast but added
native lifecycle requirements. No QMD/Node, embeddings, model inference or paid
keys are required. Static normalization uses Markdownify to preserve useful
tables/text without requiring browser rendering. Rendered capture retains the
rendered HTML and normalized text derived from provider raw Markdown, with its
transformation identity and explicit limits.

## Independent review and browser evidence

A fresh reviewer separate from the authors found five material implementation
issues, then a sixth restore issue: CLI proxy/redirect token handling, response
byte bounds, idempotent replay before DNS, metadata quota enforcement, repairing
corrupted artifacts, and silent rollback of newer retained/job state. Fixes were
reviewed against source. Their checked behavior is covered by the final passing
product journeys, including refusal before rollback and recovery under quota.
The reviewer reopened the final passing JUnit, standalone-wheel and actual
dependency-upgrade receipts. The independent disposition supported acceptance
at this record's bounded scope, with no remaining material finding. The final
deployed receipt subsequently confirmed the same runtime/source identities and
retained evidence after the documented startup.

The existing browser qualification was reused only after fresh verification of
its raw receipts, current sources, deployed modules and runtime versions. Copies
are now owned by this product under `.runtime/browser-policy-evidence/`:

- `results.json` SHA-256:
  `158ce5a63f2faf15be772e8bf401175e8e6bd2656d5676d33606b1e80d4d79c1`.
- `manifest.json` SHA-256:
  `9c9161128bad36d7d8a48a5ca94b448f51381ca538715de7bcb71467fd37955a`.
- Current rebuilt provider image:
  `sha256:6a2f13f52cd8e84cb8538f90d060dbcdb9e3778748fdbfcfaa5afd6ab884e061`.
  Its image ID differs from the historical tested image; audited source/module
  hashes and Crawl4AI/Chromium versions match.
- Pinned browser base:
  `unclecode/crawl4ai@sha256:bd36741e7bdd35ddc1a05d9183e1d6d8cefb61dd640d944a25d026b76e917690`.
- Deployed broker SHA-256:
  `c14ec7c03ec5a1297a3fe005da8b22bf8291a80020b42044af4d5f2fa0c50ae8`.
- Deployed browser-manager SHA-256:
  `6f44b845b33553fe5640796c5e8a873647b7d4f9afedd7e120e49c7e7b6de9b6`.

The raw record contains 62 passing traffic cases, 11 rejected receipt mutations,
actual 1,250-byte QUIC Initial controls for IPv4/IPv6, executed protected page
actions, observer sensitivity and DNS receipts, and zero forbidden traffic in
protected cases. The reviewer accepted the browser policy gate at this scope.
The only credential in copied receipts is a fixed disposable synthetic fixture
token; owner tokens and fixture private keys were not copied.

## Material limits and revisit conditions

- Search engines can return CAPTCHA/rate limits; actual SearXNG discovery
  returned useful results with `searxng_engines_incomplete`. DDGS auto backend
  separately returned useful results. Neither promises universal discovery.
- The default is lexical search. Diverse multilingual relevance, very large
  archives and sustained-load performance have not been established. The
  measured shared envelope is the bounded scenario described under V7.
- Text PDF extraction preserves page mappings and reports layout limits;
  scanned/complex PDFs can fail. OCR, private-site authentication automation,
  paywall bypass, arbitrary browser control and audio/video are excluded.
- Rendered capture reports that intermediate browser redirect chains are
  unavailable and subrequest policy is delegated to the configured protected
  provider. A custom provider is a trust boundary and needs equivalent proof.
- Browser qualification does not prove a full WebTransport/QUIC exchange,
  successful TURN relay, arbitrary service-worker/pop-up schedules, all DNS
  timing schedules, sustained attack load, or renderer-compromise containment.
  Upstream Chromium disables its renderer sandbox; container controls do not
  establish containment of a browser exploit.
- Local owner tokens grant owner access. Workspaces enforce evidence scope,
  rather than independent tenant authentication. The tested deployment is
  Linux x86_64; other architectures/platforms require verification.
- Restore conservatively rejects any incompatible current canonical metadata,
  including newer cache events. Intentional point-in-time rollback is not an
  implicit operation; recover an older backup into an empty product-local state
  directory. This preserves newer acknowledged work and pins.
- No commits, pushes or publication were performed. The pre-existing parent
  Beads changes were preserved; the parent's shared tracker was not mutated
  because it lies outside the owner's product boundary.
