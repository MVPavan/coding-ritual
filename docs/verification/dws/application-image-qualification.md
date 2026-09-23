# Application image qualification — cr-0km.4 portion

2026-09-22: application runtime qualification passed; independent Sol review
pending. This is a scaffold foundation for future API/worker processes, not a
product release. Browser containment and renderer/security release gates remain
open and are outside this result.

## Artifact and provenance

Local artifact: `dws-application:qualification`, linux/amd64,
`sha256:eb1475855045015fd0aa47e32605dcb5dcb68275d04f70be2386c9322694b616`.
Docker reports 1,663,705,632 bytes. This includes QMD's locked optional native/model
libraries, but no model weights. Size reduction needs separate dependency
qualification; no new transitive resolution was introduced here. No publication.

The [manifest](application-image-manifest.json) records exact platform manifests,
registry source annotations, file hashes and local evidence paths. Official
Docker Hub Python `3.13.12-slim-bookworm` and Node `22.22.0-bookworm-slim` tags
were inspected with `docker buildx imagetools inspect --raw`; the Dockerfile pins
their linux/amd64 manifests. UV `0.9.8` is digest-pinned from Astral's GHCR image
and used only in the builder. Python/Node share the Bookworm ABI; the final stage
copies Node and its libstdc++ from the pinned Node image.

The independent DWS distribution is built as a wheel using separately hash-pinned
build tools, then installed non-editably in `/opt/dws`. Its existing `uv.lock`
is consumed with `uv sync --frozen --no-dev --no-install-project`; no root project
or editable source mount participates. Only DWS 0.0.1 is installed in that venv.
Build tools, npm, caches and source checkout are not copied into the final stage.

QMD package/lock files exactly match the accepted cr-0km.11 runtime. Its official
[npm metadata](https://registry.npmjs.org/@tobilu%2fqmd/2.8.3) integrity was checked
again against the lock. Lifecycle scripts remain disabled. Both native binary
hashes are verified during build. The [dependency recipe](../../../dws/docker/qmd/README.md)
documents the intentional exclusion of QMD's two MCP SDK packages from the final
stage. Full QMD MCP functionality is therefore unsupported. No FastMCP or Python
MCP SDK is installed. QMD's published source remains unchanged.

## Reproduce

From the repository root, with Docker access and network access for the build:

```bash
bash dws/docker/application_build.sh
bash dws/tests/qualification/image_application_qualification.sh
# Preserve and build the original volume-only target with its original context:
tar -C dws -cf - Dockerfile -C docker image_volume_probe.py |
  docker build --target image-volume-qualification \
    --tag dws-application:volume-qualification -
```

The application build helper streams only explicitly named package inputs and
recipes. Existing volume-only stage content was preserved verbatim. The default
application command is actual `dws --help`; no fictitious service, port or health
endpoint is supplied. The permission wrapper sets umask 077 and execs the command.
Archive/state directories are owned by UID/GID 1000 and mode 0700; new fixture
files are verified 0600. Existing populated volumes need compatible ownership;
the image does not migrate or repair them.

## Observed results

| Check | Result |
| --- | --- |
| Installed scaffold CLI help/version, independent import | Passed; DWS 0.0.1 under `/opt/dws/lib/python3.13/site-packages` |
| Effective Python / its SQLite | 3.13.12 / 3.40.1 |
| Effective Node / ABI | v22.22.0 / 127 |
| QMD / better-sqlite3 / SQLite / sqlite-vec | 2.8.3 / 13.0.3 / 3.53.4 / v0.1.9 |
| Cold collection registration, update, status, search, get | Passed |
| New container reads existing QMD index/config/retained fixture | Passed |
| Changed fixture update replaces lexical hits | Passed |
| Empty model cache and HOME before/after both runs | Passed; no model command invoked |
| Nonroot, zero effective capabilities, no-new-privileges, loopback-only network | Asserted inside both probe containers |
| File and directory fsync, atomic replace, SQLite WAL write/read across containers | Passed using unchanged volume helper |
| Concurrent cross-container advisory lock contention | `LOCK_HELD`, `CONTENTION_CONFIRMED`; holder exits normally |
| Original volume-only target build and read | Passed, same synthetic volume |
| Scoped Ruff format/check, strict mypy, Python compile, shell syntax, JSON and whitespace | Passed; shellcheck unavailable |

Every application probe runs with network `none`, read-only root, ALL capabilities
dropped, no-new-privileges, 1 CPU, 1 GiB memory/swap ceiling, 128 PIDs, and a 64 MiB
noexec/nosuid temporary filesystem. Only a newly created DWS-prefixed named volume
and the two read-only probe files are mounted. No hosted credentials are passed.
The actual image ID is resolved once for all qualification containers.

Retained synthetic evidence volume: `dws-application-1790057403-3386547-state`.
The initial failed probe left `dws-application-1790057372-3382243-state`; no existing
containers or volumes were altered or removed. Test containers auto-remove.
Raw build, registry, image-inspection and probe logs are under
`scratchpad/dws/application-image/` and hashed in the manifest.

## Limits and attempt accounting

An initial script path error mounted a directory instead of the probe file and
failed before application checks. Correcting the script's relative working
path produced the passing run. No infrastructure recovery or isolation relaxation
was needed; ordinary approved Docker/network access was used. A shell hook rejected
a proposed recursive removal in Dockerfile text before execution; the final
recipe instead retains the excluded SDK in the builder outside the copied tree.

Network denial and absent model weights support the observed lexical-only result;
this is not a blanket guarantee for all upstream QMD commands. No inference,
embedding, semantic query, MCP, hosted provider or model-download path was tested.
The model-related dependencies remain a distribution/security review concern.
Only linux/amd64 on this Docker Desktop local named volume was tested; no power-loss,
remote filesystem, resource-exhaustion, production concurrency or broader host
compatibility claim. The fsync/SQLite helper characterizes the filesystem, not
future DWS transaction/job correctness. No unrelated root test suite was run.
