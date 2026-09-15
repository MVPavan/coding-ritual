# QMD lexical qualification

## Scope and verdict

This adds a real-CLI characterization suite for the pinned QMD candidate's
restricted lexical surface: collection registration/status, `search`, `get`,
and `update`. It does not add a DWS QMD adapter or qualify G-03, container
deployment, release readiness, vector/hybrid search, `query`, reranking,
embedding, MCP, model downloading, or every QMD execution path.

Every probe creates its Markdown corpus and all QMD state below pytest's
temporary directory. It supplies `INDEX_PATH`, `QMD_CONFIG_DIR`,
`XDG_CACHE_HOME`, and a disposable `HOME`; it has a separate subprocess cwd.
The runner uses argument arrays only and wraps every QMD process in
`bwrap --unshare-net --die-with-parent`, with the temporary state as its only
writable mount. The suite fails explicitly if `DWS_QMD_BIN`/`qmd` or `bwrap`
is unavailable; it never skips a missing essential prerequisite.

The qualified test behavior is:

- cold collection registration, status, update, lexical JSON search, and get;
- expected `qmd://lexical/...` paths and retained document text;
- changed and newly created Markdown after `update`, without mtime sleeps;
- two independent lexical startup processes sharing one isolated database;
- an update killed only after it has emitted execution output, followed by
  supported update recovery plus lexical search/get; and
- an initially empty model-cache directory that remains empty after every
  successful lexical operation.

The empty cache plus successful HOST network-denied runs are empirical
model-free evidence for these paths, not proof of every possible QMD path.

## Candidate inventory

The supplied candidate is `@tobilu/qmd` 2.8.3, installed with lifecycle
scripts disabled. Its supplied npm integrity is
`sha512-zjfVwrObPB618B6x8SdhlGv/tX9OxRHsbQnr5DUtBvqPK6HGQ27lM+9/BAY5okpjrHVnW56hLyDkqoTcsrVLzA==`.

Observed locally through the supplied executable/module:

- Node: `v22.22.0`
- QMD: `qmd — Quick Markdown Search` from `qmd --help` (package metadata
  identifies version 2.8.3)
- SQLite: `3.53.4` from the candidate's `better-sqlite3` `sqlite_version()`
  query

## Local evidence and required HOST evidence

The candidate formatter/test record reports these local commands succeeding
(exit 0):

```text
node --version
node -e '<candidate better-sqlite3 sqlite_version() query>'
qmd --help
python3 -m py_compile tests/qualification/qmd_qualification.py \
  tests/qualification/test_qmd_qualification.py
git diff --check
cd dws && env -u UV_FROZEN uv run --locked ruff format .
cd dws && env -u UV_FROZEN uv run --locked ruff format --check .
cd dws && env -u UV_FROZEN uv run --locked ruff check .
cd dws && env -u UV_FROZEN uv run --locked pytest -q -m "not qmd"
```

The non-QMD pytest command reported `16 passed`. The full pytest run reached
the QMD probes, but nested `bwrap --unshare-net` could not create its
`NETLINK_ROUTE` socket in the model sandbox. That is the current reason the
four real network-denied QMD probes require HOST execution; it is not a QMD
result. The HOST must run:

```text
cd dws
DWS_QMD_BIN=<configured-qmd> uv run --locked pytest -q -m qmd -s
```

That command is the required evidence for the real `bwrap --unshare-net`
probes. It must not be replaced by a direct QMD run or a test skip. Run the
declared `scripts/verify-dws-pilot.py` HOST gate separately after this node.

## Round-two lint repair

The formatter repair was applied by `ruff format`; it did not hand-wrap test
source. The candidate record above reports `ruff format .`, its format check,
and `ruff check .` all exiting 0.

This node's fresh first invocation with the engine-injected `UV_FROZEN=1`
exited 2 before Ruff because `--frozen` conflicts with `--locked`. Retrying
with only that variable removed exited 1 before Ruff because the writable UV
cache lacked `hatchling>=1.27` and network DNS is denied. No dependency
installation was retried. Those local tooling limitations do not replace the
required HOST Ruff gate.

## Limitations

- The tests intentionally do not prove that a future DWS runtime correctly
  serializes its own update lifecycle or exposes QMD safely to callers.
- A process kill after QMD emits update output proves an in-flight observable
  interruption, not the precise internal SQLite statement at the kill point.
- The host's network-denied result and model-cache observation qualify only
  this candidate and this restricted lexical command set.
