# Offline activation toolchains

Slice 1 prepares tools before a vendor process can start. Writers and reviewers
receive separate copies at `<activation-dir>/toolchain/uv-cache`; the selected
managed Python installation lives in its `python` child. The checkout stays
read-only for reviewers. Named execution profiles belong to a later slice.

## Host preparation

Configure `[supervisor.toolchain]` in the foreman configuration. `projects` lists
repo-relative uv project directories; its default is `["."]`. A root without
`uv.lock` needs no seed. Set `projects = []` for a graph with no uv toolchain.
Optional absolute `seed_root`, `host_cache`, and `python_root` paths must be
outside checkout and activation grants, and must not overlap each other.
Defaults are `<wrapper_root>/toolchain-seeds`, `uv cache dir`, and `uv python dir`.
The CLI captures operator `UV_CACHE_DIR` and `UV_PYTHON_INSTALL_DIR` overrides
before constructing runner environments; explicit configuration paths win.
Operator `UV_OFFLINE=1` disables host fetching as well as runner fetching.

Install the required managed Python on the host before launching a workflow.
The admitted `.python-version` or `requires-python` selects that installation.
Missing managed interpreters produce a preparation refusal; they are never
silently replaced by system Python. Dependency metadata comes from the root's
admitted base commit. Changes to `uv.lock`, `pyproject.toml`, or `.python-version`
require admitting the updated dependency inputs before dispatch.

On a project-seed miss, the host imports only matching locked wheel versions and
metadata from uv's `wheels-v5`/`archive-v0` cache. It does not copy the whole host
cache. An offline `uv sync --locked` runs against a temporary copy of admitted
metadata, with project/workspace/local installation and source builds disabled.
Only a cache-miss diagnostic permits one host fetch attempt into this seed;
`allow_host_fetch = false` disables that attempt for offline supervisors.
Unsupported source builds, missing workspace metadata, or missing wheels get a
named refusal. Preparation never executes candidate build hooks or changes a lock.

Successful seeds are atomically published under a per-key lock. Later activations
copy the seed and selected interpreter with `cp --reflink=auto`, falling back to
an ordinary copy. Hardlinks are not used. uv-created internal archive links are
made relative before publication; escaping links and special files are refused.
The private copy must pass `UV_OFFLINE=1 uv run --frozen ruff --version` after a
dependency-only sync into a temporary scratch venv (`UV_NO_SYNC=1` on the probe).
The scratch venv is discarded; runner venv and check caches stay under its channels'
scratch directory. Host grading never uses runner-writable toolchain files.

For manual host preparation, run `uv python install` for the admitted Python
requirement, then dependency-only `uv sync --locked --no-install-project
--no-install-workspace --no-install-local --no-build --link-mode=copy` against a
trusted checkout. Dispatch will import only its locked artifacts. Newer uv cache
layouts require qualification; they are never handled by copying the whole cache.

## Receipts and failures

`launch-receipt.json` adds optional `seed_receipts`; old receipts decode with no
seed claim. Each receipt records project and pin digests, seed key, selected
managed interpreter, uv version, logical copied bytes, requested copy method,
probe output, and whether the host seed required fetching. `reflink-auto` records
the copy request, not proof that the filesystem supported reflinks. A reused seed
retains its original host-fetch provenance; it does not imply another fetch.

Defaults bound each command/copy/lock wait to 120 seconds, cache/interpreter data
to 2 GiB and 100,000 entries, and preserve 64 MiB of free disk. Command diagnostics
are bounded to 16 KiB. Preparation failure raises `ToolchainUnavailable` before
the fork barrier, using the existing retry-exempt preparation-refusal path.
No vendor is released with a partly prepared seed.

## Cleanup and recovery

Private toolchains are disposable. After host verification and durable activation
close, cleanup removes that activation's toolchain and interrupted copy staging.
`SeedReceipt` and the host-owned project seed remain. An unclassified, running,
or indeterminate activation retains its private copy. A receipt/ledger indicating
an unidentified runner also prevents deletion. Cleanup failures are logged and
retried by recovery and subsequent foreman ticks, including crashes after close.

Receipt reattachment precedes preparation. A previously launched private cache is
never executed on the host for a new validation probe. Prelaunch retries may
reuse matching completed preparation only after another offline probe.

Local checks remain claims; host checks supply verification. Tests needing nested
bubblewrap remain host-only. This slice does not change vendor network enforcement
or Claude reviewer Bash permissions.
