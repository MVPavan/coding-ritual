# Retrieval decision — measured local lexical backends

Date: 2 October 2026. Scope: resolve the owner's retrieval prerequisite without
changing management SQLite or adding model inference.

## Recommendation

Use **a separate SQLite FTS5 retrieval database**, through Python's `sqlite3`.
Canonical snapshots, provenance and workspace/run membership remain DWS-owned;
the index contains derived chunks and exact snapshot/line identifiers. Keep
management SQLite unchanged. Direct reads never depend on FTS availability.

This replaces QMD for the default DWS retrieval path. It removes its Node/model
runtime dependency while providing measured lexical search, SQL scope filtering,
updates/deletes, reopening and independent process access. DWS still owns
chunking and exact passage mapping; no candidate removes that product obligation.

**Turso/Tantivy works for single-process lexical search, but is unsuitable for
the planned directly shared API/worker index in its default released mode.**
`pyturso` 0.8.1 rejected both an independent reader and an independent writer
while the parent connection was open. A single owning process with an index RPC
broker would avoid that constraint, but adds service lifecycle, queueing,
backpressure and failure handling with no present measured need. Reconsider if
its search features justify that cost or stable multiprocess support arrives.

Direct `tantivy` 0.26.2 is a viable future option if measured retrieval scale or
language/ranking requirements outgrow FTS5. It was much faster on this small
corpus but requires an additional native package and explicit reader reload,
single writer ownership, commit and merge lifecycle. The roughly 1 ms SQLite
query measured here does not establish a product bottleneck.

## Actual comparison

Linux x86_64; CPython 3.13.9; SQLite 3.50.4. Binary wheels installed successfully
without compilation. One deterministic synthetic corpus: 1,000 chunks, five
workspaces, seven runs, approximately 1.5 MB of repetitive text; matching terms
deliberately collide across scopes. One process per measured backend; 100 warm
queries. These are prototype measurements, not product acceptance or a general
search-quality benchmark.

| Measurement | SQLite FTS5 | Turso 0.8.1 native Tantivy FTS | Direct Tantivy 0.26.2 |
|---|---:|---:|---:|
| Extra installed package bytes | 0 | 103,863,478 plus 182,965 typing-extensions | 14,471,402 |
| Build 1,000 chunks, ms | 11.923 | 1,589.165 | 23.162 |
| First in-process query, ms | 1.324 | 0.786 | 0.114 |
| Warm query median, ms | 1.0565 | 0.1915 | 0.017 |
| Total process peak RSS, KiB | 25,856 | 52,748 | 50,156 |
| Resulting index/database bytes | 2,322,432 | 2,277,376 | 186,337 |
| Exact retained chunk + line mapping | Pass | Pass | Pass |
| Workspace/run filter before top-K | Pass | Pass | Pass |
| Update removes old/adds new term; delete removes hit | Pass | Pass | Pass |
| Reopen retained hit | Pass | Pass | Pass |
| Independent reader while parent open | Pass | **Rejected: file locked** | Pass |
| Independent writer while parent open | Pass | **Rejected: file locked** | Not measured |
| In-place derived-index rebuild | Pass | Pass | Not measured |

RSS is interpreter plus backend high-water usage, not isolated library memory.
First query is not a cold process startup measurement. The Tantivy index benefits
greatly from compression on repetitive text; this size must not be extrapolated
to a diverse archive. Turso rejected attempts are recorded as JSON errors even
though the prototype child process exits zero; they are failures, not passes.

The existing QMD 2.8.3 application image remains approximately 1,663,705,632
bytes total. A read-only inspection of that existing image measured its installed
`/opt/qmd` tree at 874,720,003 bytes and its Node executable at 123,405,064
bytes; these are not QMD's isolated incremental image size. No new same-corpus
QMD latency or RSS measurement was
performed. Existing lexical, update/restart and lock qualification remains
relevant history; there is no claim that SQLite outperforms QMD.

## Integration design and limitations

- Filter workspace/run/crawl/document membership **inside the SQL query before
  ranking/LIMIT**, not by filtering a small global result set in application
  code. The measured prototype includes workspace/run fields directly in its
  index entries. Integrating authoritative metadata joins remains product work.
- Store canonical snapshot IDs and line bounds alongside index entries. Return
  passages from the immutable archive and check the indexed capture identity.
  Never use highlighted/pruned index snippets as the canonical artifact.
- Use WAL and short owned transactions for concurrent API/worker access.
  Handle busy/time budgets explicitly. The prototype proves two-process opening
  and reads/writes; sustained mixed-load and kill/recovery proof belongs to
  product integration verification.
- Cross-file transactions are not an assumed atomic commit mechanism. Publish
  snapshots in management state, represent index readiness explicitly, and make
  indexing idempotent/rebuildable from canonical snapshots. Do not make readers
  depend on immediate successful indexing.
- FTS5's in-place `rebuild` check proves intact derived rows can rebuild their
  term index. Reconstructing a deleted index database from canonical files is a
  separate required product behavior, still to implement and verify.
- This corpus does not establish multilingual quality, stemming suitability,
  diverse-query relevance, large archive scaling, realistic mixed-load latency,
  container memory limits or full crash safety. Track those through meaningful
  product scenarios, without expanding this decision into a general benchmark.

The historical reason for QMD was avoiding ownership of a document indexing
workflow. The current owner prioritizes a lighter local runtime. The measured
FTS5 path accepts explicit chunking/mapping ownership and preserves the useful
separation between management state, immutable artifacts and rebuildable index.
There is no management-database migration and no default vectors.

## Reproduction and evidence

Task artifacts are all inside the product at `.runtime/retrieval-choice/`:
`measure.py`, `sqlite-results.json`, `turso-results.json`,
`tantivy-results.json`, `environment.json`, and `qmd-footprint.json`.
The prototype source plus recorded exact package versions reproduces the
comparison; run it in a fresh product-local directory/environment to avoid
reusing already created databases. The script is a disposable comparison, not
production retrieval code or a proposed unit-test suite.

Installation used `uv pip install --only-binary :all:` into a product-local
environment, with `UV_CACHE_DIR`, `UV_PYTHON_INSTALL_DIR`, and `TMPDIR` under
the same product-local runtime folder. Initial sandbox DNS denial was resolved
through an approved narrow network escalation. No source compilation, model
downloads, shared tracker writes or global configuration changes occurred.

## Primary sources

- [SQLite FTS5 reference](https://www.sqlite.org/fts5.html): lexical indexing,
  BM25, tokenization, SQL filtering and rebuild facilities. SQLite is public
  domain; no added retrieval package is required when the runtime enables FTS5.
- [Turso Python binding](https://github.com/tursodatabase/turso/blob/main/bindings/python/README.md)
  and [package metadata](https://github.com/tursodatabase/turso/blob/main/bindings/python/pyproject.toml):
  embedded `pyturso`, pre-1.0/Beta status, Python/platform support and MIT license.
- [Turso current manual](https://github.com/tursodatabase/turso/blob/main/docs/manual.md):
  default multiprocess limitation; experimental multiprocess WAL is explicitly
  not production ready. Released 0.8.1 behavior was directly measured above.
- [Turso FTS implementation](https://turso.tech/blog/beyond-fts5): native Tantivy
  SQL index, transaction integration and maintenance design. FTS requires
  `experimental_features="index_method"` in the measured Python release;
  default connections reject its DDL.
- [Tantivy Python bindings](https://github.com/quickwit-oss/tantivy-py) and
  [API reference](https://tantivy-py.readthedocs.io/en/latest/api/tantivy/tantivy.html):
  Python native bindings, Boolean scope queries, writer ownership and reader
  reload APIs. The installed Python binding's metadata records MIT; the Rust
  Tantivy engine uses Apache-2.0.

## Adoption and independent disposition

The comparison received a fresh review separate from its author. The default
backend was adopted as separate SQLite FTS5 with management SQLite unchanged.
The review accepted the measured recommendation and its process/maturity
limits; it did not treat the prototype as integrated product acceptance.

The delivered product now filters scope before ranking, reconstructs a deleted
index from immutable captures, and supports independent API/worker processes.
Actual product evidence and remaining scale limitations are recorded in the
[vision acceptance record](vision-acceptance.md). The prototype limitations
above remain limits of the comparison itself.
