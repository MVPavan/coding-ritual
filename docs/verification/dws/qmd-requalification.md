# QMD lexical requalification — cr-0km.11

**DONE (qualification execution), 2026-09-22.** All four existing real QMD
qualification tests passed again in one approved-host evidence correction run:
**4 passed, 16 deselected in 3.19s** (pytest), exit 0, zero failures/errors/skips.
Monotonic command elapsed time was **3.340313085s**. Independent review supported
the qualification with two minor record findings; coordinator verification of
this correction remains pending. No production deployment is authorized or claimed.

## Candidate and provenance

The source of the pin is [the historical manifest](qmd-qualification-manifest.json).
The [historical report](qmd-qualification.md) remains unchanged. The restored
runtime is isolated at `scratchpad/dws/qmd-requalification/runtime/`.

| Item | Effective value | Comparison |
| --- | --- | --- |
| QMD | `@tobilu/qmd` 2.8.3 | Exact candidate, no upgrade |
| Node | v22.22.0, ABI 127 | Existing installed Node; historical version retained |
| SQLite | 3.53.4 | Historical version retained; queried from actual native module |
| better-sqlite3 | 13.0.3 | Fresh resolution of candidate's `^13.0.3` dependency |
| sqlite-vec | v0.1.9 | Loaded extension queried in an in-memory database |
| Platform | Linux x64 | Current host |
| npm | 11.9.0 | Installed tool; no global modifications |

Official [registry metadata](https://registry.npmjs.org/@tobilu%2fqmd/2.8.3)
identifies the package, version, GitHub repository `tobi/qmd`, and
[tarball](https://registry.npmjs.org/@tobilu/qmd/-/qmd-2.8.3.tgz).
The downloaded tarball's computed SHA-512 matches both official metadata and
the historical pin:

```text
sha512-zjfVwrObPB618B6x8SdhlGv/tX9OxRHsbQnr5DUtBvqPK6HGQ27lM+9/BAY5okpjrHVnW56hLyDkqoTcsrVLzA==
```

All 53 installed QMD package files were compared byte-for-byte with the verified
tarball. The fresh transitive dependency tree is recorded in the scratch
`runtime/package-lock.json` and `dependency-inventory.json`; the historical
manifest did not pin that entire tree, so identical historical transitive
resolution is not claimed. `npm audit signatures` exited 0: 159 packages have
verified registry signatures, and 34 have verified attestations. This is
provenance evidence, not a vulnerability audit or the distribution review
reserved for **cr-0km.5**.

## Supply-chain and execution boundary

Installation used the official npm registry, a scratch-only prefix/cache,
`--ignore-scripts --no-audit --no-fund`, and `/dev/null` user configuration.
No lifecycle scripts, native builds, model downloads, or global npm changes
were performed. Inspection covered the published launcher, CLI routing,
database loader, lazy llama import, package dependency/scripts metadata,
`better-sqlite3` native binding selection, and `sqlite-vec` extension selection.
The installed `better-sqlite3` contains a Linux x64 prebuild; `sqlite-vec-linux-x64`
supplies `vec0.so`. Their SHA-256 hashes are retained. Tree-sitter install scripts
and the llama postinstall remained disabled. No exhaustive source/native binary
security review is claimed.

Every QMD process used the existing helper's `bwrap --unshare-net
--die-with-parent` boundary, read-only host root, a single writable fixture
state directory, cleared environment, separate cwd, and disposable `HOME`,
`INDEX_PATH`, `QMD_CONFIG_DIR`, and `XDG_CACHE_HOME`. Only `collection add`,
`status`, `search`, `get`, and `update` were exercised. Four fixture caches were
empty/absent at creation and checked by the unchanged tests after successful
operations; a post-run inspection also found all four model caches empty/absent.
The read-only root remains visible; this is not a claim of host-file secrecy.

## Evidence checklist

Detailed stdout/stderr stays in `scratchpad/dws/qmd-requalification/logs/`.
`commands.jsonl` records exact argv arrays, absolute cwd, exit codes, timestamps,
and log paths for the six original listed commands, excluding both registry
metadata fetch attempts. It is not an exhaustive execution history. The companion [manifest](qmd-requalification-manifest.json)
provides portable path substitutions and integrity records.

| Check | cwd | Exit | Result / log |
| --- | --- | --- | --- |
| Official metadata content | — | not in structured receipts | `registry.json`; content/provenance evidence only, not a portable fetch execution receipt |
| Tarball fetch and digest | repo root | 0 | `tarball.log`; exact pin match |
| `npm install --ignore-scripts` | scratch runtime | 0 | `install.log`; 159 packages |
| `npm audit signatures` | scratch runtime | 0 | `signatures.log`; signatures and attestations above |
| Sandbox `bwrap --unshare-net … /bin/true` | repo root | 1 | `sandbox-net.log`; NETLINK_ROUTE denied |
| Host network-denied native version probe | repo root | 0 | `host-versions.log`; actual SQLite and extension versions |
| `uv run --locked pytest -q -m qmd -s` | `dws/` | 0 | `host-qmd.log`, `host-qmd.xml`; all four selected tests passed |
| Source/package preservation and fixture inspection | repo root | 0 | `source-verification.json`, `postchecks.json` |

Sandbox failure was exactly:

```text
bwrap: loopback: Failed to create NETLINK_ROUTE socket: Operation not permitted
```

This is an unsupported nested sandbox result, not a QMD failure. Approved host
execution preserved network denial and succeeded on the first host attempt.
The original narrative records two infrastructure transitions: sandbox DNS to
approved host registry access, and sandbox bwrap to approved host isolation.
The metadata-fetch attempts are absent from the structured receipts; this
report does not claim those receipts independently establish their exit codes.
No alternate architecture, weakened isolation, or repeated recovery loop was used.

The test environment set `DWS_QMD_BIN` to the scratch runtime's
`node_modules/.bin/qmd`, put the installed Node v22.22.0 directory first on
`PATH`, unset `UV_FROZEN`, set `UV_OFFLINE=1`, and placed the UV cache, pytest
base directory and JUnit output under owned scratch. `PYTHONDONTWRITEBYTECODE=1`
and `-p no:cacheprovider` avoided writing into the existing Python package.
The required pytest argv was unchanged; environment-only pytest options selected
scratch artifact locations. All existing test sources, `pyproject.toml` and
`uv.lock` matched their before-run SHA-256 hashes afterward. The 16 non-QMD
tests were deselected; their earlier supplied pass result was not rerun here.

## Evidence correction after independent review

The old `host-qmd` UTC timestamps subtract to **0.781648s**, conflicting with
its pytest **2.93s** and JUnit **2.931s** durations. The old clock-based elapsed
duration is unreliable; no cause for the discrepancy is established. Original
receipts, logs, fixtures, and manifest artifact hashes remain unchanged.

One new run used the same isolated runtime and unchanged helper/bwrap boundary.
The command remained `uv run --locked pytest -q -m qmd -s` from `dws/`, with the
same environment settings described above; only UV cache, pytest fixture root,
and JUnit locations moved under `scratchpad/dws/qmd-requalification/fix/`.
The [new immutable receipt](../../../scratchpad/dws/qmd-requalification/fix/receipt.json)
records exact absolute argv/cwd, effective runtime, UTC start/end, and
`time.monotonic_ns()` readings. Its **3.340313085s** measurement governs command
elapsed time (env/uv plus pytest startup, execution, and shutdown).
UTC endpoints are `2026-09-22T06:02:52.134887+00:00` and
`2026-09-22T06:02:55.475221+00:00`.
The [new log](../../../scratchpad/dws/qmd-requalification/fix/host-qmd.log) and
[JUnit](../../../scratchpad/dws/qmd-requalification/fix/host-qmd.xml) record
4 passed, 16 deselected, zero failures/errors/skips; pytest/JUnit duration is
3.19/3.190s. These are separate measurements from the encompassing command.

The registry finding is resolved by narrowing the checklist and manifest scope:
metadata content is retained, but no structured metadata-fetch execution receipt
is claimed. No network fetch was rerun to reconstruct history.

[Correction checks](../../../scratchpad/dws/qmd-requalification/fix/evidence-checks.json)
verify original artifact hashes, QMD test/helper and package-file equality to
`f50238a3b6c615d912b45e702dff062d7dfafc77`, unchanged historical qualification
documents, all 53 installed QMD files against the tarball, both native binary
hashes, and all eight original/new fixture model caches empty or absent.
The manifest appends new evidence separately and retains every historical hash.

## Limits and handoff

This proves the existing cold lexical lifecycle, changed/new content update,
two independent search startups, and observable interrupted-update recovery
for the recorded runtime. It does not qualify a full production adapter,
deployment volumes, container deployment, release readiness, or QMD child
ownership/termination. Killing the observed wrapper is not proof that all QMD
descendants were terminated or of the exact internal SQLite interruption point.
No model-backed commands or general model-free execution claim are covered.

The test helpers and imported tests were not modified. No commits, branch
switches, worktrees, delegation, or Beads mutations were performed. The read-only
Beads lookup could not open the database lock; the supplied assignment and goal
document provided scope. The goal tool returned no active goal. Remaining work:
coordinator verification of this correction and acceptance, separate cr-0km.5 distribution
review, and later production/volume/child-lifecycle qualification.
