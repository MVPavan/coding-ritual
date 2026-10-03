# DWS

**One local web evidence tool for every project and research agent.** DWS
discovers public sources, captures static HTML, rendered pages and text PDFs,
retains immutable evidence, and returns bounded exact passages. Your host agent
owns research methods, interpretation, and synthesis.

This directory is an independent Python distribution. Its source, dependencies,
deployment, tests, documentation, cache, and retained data belong here; it does
not require the surrounding repository's application or orchestration engine.

## Start

From this directory, with Docker and Compose installed:

```bash
scripts/setup.sh start
curl --fail http://127.0.0.1:8765/ready
```

The default deployment runs the API, independent worker, SearXNG, and protected
Crawl4AI browser service. A finite preparation service installs locked packages
with `uv` into a persistent Linux environment before API/worker startup. The
generic Debian Python/uv image contains no application packages at build time.
Both the cache and application state are bind-mounted product-local folders.
Only the API publishes a host port, on loopback.

Use a host CLI without installing MCP:

```bash
scripts/setup.sh init
export UV_CACHE_DIR="$PWD/.runtime/uv-cache"
export UV_PYTHON_INSTALL_DIR="$PWD/.runtime/python"
export TMPDIR="$PWD/.runtime/tmp"
uv sync --locked --no-dev
set -a
source .runtime/owner.env
set +a
uv run --no-sync dws search 'SQLite full text search' --limit 5
uv run --no-sync dws fetch https://sqlite.org/fts5.html --render never
```

Use the returned snapshot ID with `dws read`, and search captured evidence with
`dws retrieve`. Indexing runs asynchronously; `read` works immediately. Pin
citations needed later with `dws pin`. See the [operator guide](docs/usage.md)
for workspaces, durable crawls, cancellation, retention, restore, and upgrades.
The [host integration example](docs/host-integration.md) shows a portable
research adapter using the installed CLI.

## Capabilities and stack

| Surface | Available operations |
|---|---|
| Core, command API, CLI | `search`, `fetch`, `crawl`, `retrieve`, `read`, `job_status`, `job_cancel` |
| Operator CLI/API | Workspaces/runs, pin/unpin, export, expiry/GC dry-run, index status/rebuild, diagnostics, backup/restore |
| Optional MCP | The same seven capabilities and exact retained snapshot resources; enable the locked `mcp` extra |

Python/FastAPI/Pydantic provide shared contracts; HTTPX provides controlled
streaming and DNS-pinned acquisition; Markdownify and pypdf normalize content;
Crawl4AI renders; SearXNG discovers sources and DDGS provides a fallback.
Management SQLite is separate from the rebuildable SQLite FTS5 retrieval index.
No Node/QMD, embeddings, inference, research agent, or paid-provider keys are
required for the default product.

Provider outages, missing extraction, index lag, expiry, truncation, and crawl
limits are explicit. Scanned PDFs do not imply OCR support. Private authenticated
scraping, paywall bypass, arbitrary browser control, audio/video processing, and
automatic report generation are outside this product's scope.

## Product verification

The product suite consists of substantial journeys through real CLI/API and
worker processes, HTTP fixtures, persistent databases, restart recovery, and
backup/restore. Historical dependency qualifications remain available under
`tests/qualification/`; they are not the default product suite.

```bash
UV_CACHE_DIR="$PWD/.runtime/uv-cache" \
  UV_PYTHON_INSTALL_DIR="$PWD/.runtime/python" \
  TMPDIR="$PWD/.runtime/tmp" uv sync --locked
.venv/bin/python -m pytest tests/integration \
  --basetemp=.runtime/pytest -o cache_dir=.runtime/pytest-cache
.venv/bin/ruff check src/dws tests/integration
.venv/bin/mypy --strict src/dws
```

## Goal and evidence

- [Product goal](docs/product-goal.md): vision and verifiable outcomes.
- [Execution brief](docs/ultra-execution-brief.md): the owner's time window and
  orchestration freedom; its starting-state section is historical.
- [Retrieval decision](docs/verification/retrieval-choice.md): measured FTS5,
  Turso, and Tantivy tradeoffs.
- [Operator guide](docs/usage.md): installation, use, maintenance, and limits.
- [Host integration](docs/host-integration.md): portable CLI/API/MCP integration.
- [Vision acceptance](docs/verification/vision-acceptance.md): outcome evidence,
  tested identities, and material limits.

Acceptance records under `docs/verification/` distinguish verified behavior from
remaining gaps. Implemented capabilities and green health checks alone do not
establish that the entire vision has been achieved.

To replicate the product scenarios, run `scripts/verify_product.sh`. For the
actual browser/MCP, standalone installation, upgrade, and Compose maintenance
scenarios as well, use `scripts/verify_product.sh --full`. See the
[end-to-end scenario guide](docs/verification/end-to-end-scenarios.md) for
prerequisites, coverage, and results.
