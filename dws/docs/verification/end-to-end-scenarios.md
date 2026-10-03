# Repeatable product and end-to-end scenarios

This follows the [product goal](../product-goal.md) and the owner's request to
replicate the complete scenario set. The original four journeys established the
main workflows. A follow-up coverage audit identified unexercised boundary
cases; these are now explicit product scenarios rather than assumed passes.

The subsequent whole-product critic audit expanded the integration coverage
again. Its review rounds, recovered defects, and current build qualification
are recorded in [the critic audit](critic-review.md). Results below labeled
historical describe the earlier build.

## Run from the standalone DWS directory

Prepare the locked host environment and start the local services:

```bash
scripts/setup.sh init
export UV_CACHE_DIR="$PWD/.runtime/uv-cache"
export UV_PYTHON_INSTALL_DIR="$PWD/.runtime/python"
export TMPDIR="$PWD/.runtime/tmp"
uv sync --locked --extra mcp
```

Set `DWS_MCP_ENABLED=true` in `.runtime/owner.env`, then run:

```bash
scripts/setup.sh start
scripts/verify_product.sh --full
```

The full run requires Docker/Compose and public-web access. It uses the real
search and browser providers, an actual MCP client, and installed wheel
consumers. Its maintenance scenario briefly stops/recreates this DWS deployment's
API and worker; run it when a short local interruption is acceptable. It
preserves existing state and creates isolated verification workspaces.

For deterministic core integration journeys without the providers or Docker:

```bash
scripts/verify_product.sh
```

Each run writes logs, JUnit XML, receipts, and `summary.json` under a fresh
`.runtime/verification/<timestamp>-<pid>/`. A failed selected step makes the
command exit nonzero and remains a failure in the summary; later steps still
record their own outcomes. Python environments, cache, temporary files, and
state remain inside DWS. No owner token is printed.

## Scenario coverage

| Scenario | Actual behavior exercised | Goal outcomes |
|---|---|---|
| Technical and filing research | Real CLI discovery/fetch/read/retrieve, table values, PDF page mappings, exact spans, HTTP/BOM encoding precedence, original-byte hashes, source revision, pin/export/unpin/expiry | V1–V4, V8, V12 |
| Shared projects and recovery | Colliding workspace/run/document terms, competing decoys, four coalesced callers, overlapping reads/retrieval/worker indexing, bounded admission, index deletion/rebuild, backup refusal and corruption repair, disk pressure and cleanup | V4, V5, V7–V10 |
| Interrupted documentation crawl | Actual CLI crawl, durable acknowledgement, killed API/worker, idempotent replay, cycles, off-scope links, source failures, page cap, manifest reconciliation, cancellation preserving evidence | V1, V5, V6, V10 |
| Access and provider degradation | Missing auth, malformed headers/schema, unsafe targets/redirects, compressed/wire byte limits, blank PDF, provider outage, rendered HTML fallback provenance/decoding, rejected source/provider/main HTTP 206/226 with no publication and mixed-crawl preservation, adversarial CLI proxy and redirect collectors; real write/file-fsync/post-rename-directory-fsync and unexpected-failure API/CLI errors, rollback, pinned reads and recovery | V3, V9 |
| Budgets and reconnect | Queue capacity and cancellation reopening a slot; unread acknowledgement then one-job replay; depth cap; exactly two retry attempts; global crawl deadline; encoded response byte rejection and a successful smaller read | V4, V6, V7, V9 |
| Capture and index interruption | Real SIGKILL before metadata commit and after committed rebuild intent; orphan dry-run/apply cleanup; pending index recovery; exact pinned reads and scoped passage retrieval after restart | V4, V8–V10 |
| Documentation discovery boundaries | More than 2,000 links with durable partial reporting; interrupted/restarted legacy job restore; HTML bases and padded/spaced links; versioned directory scope; static redirect observers and rejected rendered final URLs | V3, V6, V9, V10 |
| Host startup and crawl admission | Token fsync failure and real publication interruption; concurrent actual API startup; invalid token/state/retention rejection; installed CLI invalid credential/port/deep-JSON errors followed by exact healthy reads; source-validation timeout and concurrent durable acknowledgement replay | V6, V9, V10 |
| Operator and location boundaries | Literal SQLite state-path punctuation; missing original artifact errors and verified repair; copied-file durability ordering and injected failures; restore into empty state; malformed manifests; actual PDF pages, content headings, whitespace-heavy/dense text, and long retrieval queries | V4, V7–V10 |
| Browser traffic policy matrix | Isolated real IPv4/IPv6 browser HTTP/HTTPS/redirect/CONNECT/subrequests, public and mapped-public controls, mixed/rebinding DNS, private/site-local/reserved/multicast targets, observer sensitivity and malformed-receipt detection | V3, V4, V9 |
| Deterministic rendered fixture | Actual protected Crawl4AI and DWS acquire a JavaScript-produced marker; retained raw/normalized artifacts and hashes match; calibrated private-target observer sees no forbidden browser request and DWS denies a private main target | V3, V4, V9 |
| Live public sources and agent host | Static HTML, text PDF, real rendered public page, installed CLI, all seven MCP tools, retained resources, API parity, scoped passages, bounded crawl/status/cancellation | V1–V4, V6, V11 |
| Installation and operation | Fresh installed wheel without MCP or repository sources; locked dependency upgrade with consumers stopped; exact retained pin/job; live preparation refusal; Compose owner-limit forwarding and selected actual consumer environments; real consumer replacement; five fresh offline MCP preparation/API cases | V1, V4, V6, V10, V12 |

The first nine are substantial pytest integration journey families. The last four
are standalone end-to-end helpers under `tests/e2e/` and `tests/qualification/`,
called by the same entrypoint. Full verification now includes five groups.
They do not import earlier ignored verification runners or require the parent
repository's orchestration engine.

## Current expanded replication

The final full command ran at **20:14:25–20:20:54 UTC** on 2 October 2026 and
**passed all five groups**: ten core integration journeys, all **86 browser
cases** and twelve receipt sensitivity mutations, protected rendered fixture,
live public sources/all seven MCP capabilities, and installed-product operations
including all five fresh MCP preparation cases. No forbidden browser traffic,
DNS receipt or cleanup error was recorded. Primary artifacts:
`.runtime/verification/20261002T201425Z-4079616/`.

The tenth fresh independent GPT-6.1/xhigh whole-product critic completed every
layer and returned **CLEAN=true: Important 0, Minor 0**. It independently checked
all fifty-nine frozen inputs, source/wheel/installed/deployed identities, current
primary receipts and raw assertions. Its separate actual Store/shared Engine/MCP
failure and callback rollback probe passed. The fresh full core capture-I/O
receipt is `.runtime/product-tests/journey-ws3xrq2k/capture-io-receipt.json`.
All forty-eight previous findings have corrections; the requested loop is
complete at the documented scope. Final report:
`.runtime/critic-review/round-10/review.md`.

The earlier **18:32:13–18:38:05 UTC** run remains **failed**: its browser matrix
passed 82 of 83 cases before the proxy correction. See [the critic audit](critic-review.md)
for every finding, source/wheel identity and preserved passes and failures.
Only final result annotations follow the clean review; product inputs remain
unchanged.

## Historical result of the first replication

**Final complete entrypoint result: passed.** The command
`scripts/verify_product.sh --full` ran at **14:35:21–14:36:31 UTC on
2 October 2026**. All selected groups passed:

| Group | Result |
|---|---|
| Core integration | **5 passed**, 0 failures/errors/skips; 29.878 seconds |
| Deterministic rendered fixture | Passed; 7.404 seconds; exact retained text/artifacts, private-policy checks, all three containers/two networks and synthetic credentials cleaned up |
| Live public sources and MCP | Passed; static/PDF/rendered capture, installed CLI, all seven MCP tools, resource/API parity, bounded crawl and cancellation; search used the DDGS fallback with three results |
| Installed product and operations | Passed; wheel without MCP/source checkout, actual idna 3.19→3.20 upgrade, retained pinned citation/job, refused live preparation, real API/worker container replacement |

The authoritative combined artifact directory is
`.runtime/verification/20261002T143521Z-760503/`:

- `summary.json`: all four groups passed, with a successful command exit.
- `core.xml` and `core.log`: five substantial pytest journeys.
- `rendered-fixture/receipt.json`: actual browser/rendered artifacts, observers,
  immutable image identifiers, and resource cleanup.
- `live/receipt.json`: individual live/MCP checks and scoped retained handles.
- `operations/receipt.json`: isolated installed versions, exact dependency
  delta, pinned evidence, stopped consumers and changed main container IDs.

The fresh standalone wheel's SHA-256 is
`217c43cb62e3b03b0ab75f276bdb836f02622e4bbd9ee7e368f9a38f4d90de14`.
The product version and main lock remained 0.1.0 and unchanged respectively.

Fresh review of the new verification tooling caught three issues: cleanup after
an individual container command failure, inherited MCP proxies, and urllib
redirects forwarding authentication. All three were fixed and reviewed before
the combined run. Real calibrated proxy/redirect collectors received no
forwarded owner credentials. Review found no remaining material issue in the
verification changes. No production source changes were required by the new
five-journey checks.

Final Ruff lint/format checks, strict mypy (17 source files), shell syntax, and
Git whitespace checks passed. A final response-shape check in the rendered
helper was followed by another actual fixture run: passed in 7.241 seconds,
with complete cleanup. Its receipt is
`.runtime/verification-rerun/rendered-fixture-final/receipt.json`.

The historical 62-case browser transport qualification is source-bound evidence
described in the [acceptance record](vision-acceptance.md). This replication
adds a fresh installed-product rendered/private-subrequest scenario. It does
not claim that the entire historical transport matrix was rerun.

The repeatable runner explicitly configures product-local uv, XDG, temporary,
mypy and Ruff paths. Some original author checks had updated a pre-existing
parent mypy cache before this replication; that shared cache was preserved to
avoid changing unrelated entries. It is not a dependency of this runner or the
standalone installed product.

## Limits

Public engines can be unavailable or rate-limited; live checks report those
failures separately from deterministic failures. The tests establish the
configured behavior and bounded concurrency in the scenarios above. They do
not establish unlimited capacity, universal search relevance, scanned-PDF OCR,
all browser transport schedules, renderer-exploit containment, or research
conclusions supplied by the caller.
