# Deployed stack component inventory — 2026-10-04

The [JSON inventory](component-inventory.json) records every installed Python
distribution found in the deployed prepared environment and provider images,
its version and declared licence metadata, the available OS package lists, and
1,017 notice provenance entries. Exact notice bytes are deduplicated into 586
[content-addressed files](component-notices/). This is an installed-component
and notice record, not a verified SBOM, provenance attestation, vulnerability
clearance, or distribution approval.

## Inspected identities and method

The four running `dws-product` consumers were inspected with `docker inspect`:
API and worker use the runtime ID below and mount the product's
`.runtime/container-env`; SearXNG and Crawl4AI use the IDs below. Each image
was then read by `docker run --rm --network none --read-only --cap-drop ALL`
with an explicit Python or shell entrypoint. No tag was pulled, image rebuilt,
or running service restarted. The extraction and assembly scripts and raw
receipts are under ignored `scratchpad/dws/component-inventory/`.

| Artifact | Running image ID | Recipe base / pinned source | Python distributions | OS packages |
|---|---|---|---:|---:|
| API and worker | `sha256:4109ab41a612c88cb7b683a37e5397b9a8078bf0594d306578ddc5a79ea79f32` | `python:3.13.12-slim-bookworm@sha256:3121f8b0804aa3698ab750d9a39ea4a42657a385c9b133722b915e55c51551a6`; uv 0.9.8 from `ghcr.io/astral-sh/uv@sha256:f76a8aa726a81249cf123ebfbbcf0bda266118f1c30ffcc70116e268b4ecea4f` | 82 | 97 Debian |
| SearXNG 2026.10.4 | `sha256:0aacb9eb84a4d2611bdf1972190e3cdd21f7a5992b0defc3a8e423ea06f4d0bb` | `ghcr.io/searxng/searxng@sha256:0aacb9eb84a4d2611bdf1972190e3cdd21f7a5992b0defc3a8e423ea06f4d0bb`; upstream parent base unreconstructed | 32 | Unknown: Void database absent |
| Crawl4AI 0.9.4 plus DWS overlay | `sha256:86818300a1555ddc6f73f703eeabeda75ef9b5bedbe70ccc55e4c7ded1f42fbb` | `unclecode/crawl4ai@sha256:9021b3cb5c6f12570bbcd5395638495e0a06969b3148e377b953d174af2ebc9b` | 118 | 580 Debian |

The runtime image is generic. `prepare` installs the locked application into
the mounted `.runtime/container-env`; the inspected `uv.lock` SHA-256 is
`f31a16177d362c575a916b5aec7658ff1a584eec21f0cc1e8342bda50a27e6e8`.
The environment includes the MCP extra. Image recipes are in `Dockerfile` and
`docker/crawl4ai-egress/Dockerfile`; the overlay patch SHA-256 is
`3354414c9d3d8118d405c8cef6abc2f706f8c59529171029a0ba2502c68e6ade`.
The base references are recipe declarations; their separate base images were
not available for local digest inspection. The JSON contains both Debian
package lists, the original `/var/lib/dpkg/status` paths and their hashes.

Read-only interpreter probes reported Python/SQLite/OpenSSL versions of
3.13.12/3.40.1/3.0.18 for the runtime, 3.14.7/3.53.4/3.6.5 for SearXNG,
and 3.12.14/3.40.1/3.0.20 for Crawl4AI. Other Debian native libraries are
represented by their installed package records. Crawl4AI ships
Google Chrome for Testing 153.0.8010.12 at
`/home/appuser/.cache/ms-playwright/chromium-1243/chrome-linux64/chrome`,
verified with `chrome --version`. The installed SearXNG version file reports
`2026.10.4+ce913b893` and an `AGPL-3.0-or-later` SPDX header.

## Declared Python licences

Counts are distributions, including separate installations of the same
package. Labels normalize common spelling variants; the JSON preserves each
original expression, field, classifier and metadata hash. `AND`, `OR`,
unspecified and unknown declarations remain distinct. OS copyrights and the
SearXNG core are additional to this table.

| Declared licence | Runtime | SearXNG | Crawl4AI |
|---|---:|---:|---:|
| 0BSD | 0 | 0 | 1 |
| Apache-2.0 | 10 | 0 | 20 |
| Apache-2.0 AND BSD-2-Clause | 0 | 0 | 1 |
| Apache-2.0 AND CNRI-Python | 0 | 0 | 1 |
| Apache-2.0 AND MIT | 0 | 0 | 1 |
| Apache-2.0 OR BSD-2-Clause | 1 | 0 | 1 |
| Apache-2.0 OR BSD-3-Clause | 1 | 0 | 1 |
| BSD | 1 | 0 | 0 |
| BSD (unspecified) | 0 | 3 | 3 |
| BSD-2-Clause | 1 | 1 | 3 |
| BSD-3-Clause | 17 | 11 | 23 |
| BSD-3-Clause AND 0BSD AND MIT AND Zlib AND CC0-1.0 | 0 | 0 | 1 |
| Dual License | 0 | 1 | 0 |
| ISC | 2 | 1 | 2 |
| MIT | 44 | 12 | 49 |
| MIT AND PSF-2.0 | 0 | 0 | 1 |
| MIT OR Apache-2.0 | 0 | 0 | 1 |
| MIT-0 | 1 | 1 | 1 |
| MIT-CMU | 0 | 0 | 1 |
| MPL-2.0 | 1 | 1 | 1 |
| MPL-2.0 AND MIT | 0 | 0 | 1 |
| PSF-2.0 | 1 | 1 | 3 |
| UNKNOWN | 1 | 0 | 1 |
| Unlicense | 1 | 0 | 1 |

## Copyleft and notices

- SearXNG core declares `AGPL-3.0-or-later` in its installed version file.
  Its [AGPL text](component-notices/57c8ff33c9c0cfc3ef00e650a1cc910d7ee479a8bc509f6c9209a7c2a11399d6.txt)
  is copied from the earlier accepted upstream record because the current
  image has no core LICENSE file. Network service deployment and modified
  source availability need an owner-specific AGPL review.
- The locked runtime has one declared copyleft Python distribution:
  `certifi` 2026.7.22 (`MPL-2.0`). SearXNG also has that `certifi` version.
  Crawl4AI has `certifi` 2026.7.22 (`MPL-2.0`) and `tqdm` 4.70.1
  (`MPL-2.0 AND MIT`). Their exact texts are [certifi](component-notices/e93716da6b9c0d5a4a1df60fe695b370f0695603d21f6f83f053e42cfc10caf7.txt)
  and [tqdm](component-notices/fcff87c3a47ce8028a8512aa182d4fcf0ad1c90544ee75cf9b343684cac194de.txt).
  No Python distribution in these three installed sets declares GPL or LGPL.
- The Debian copyright files have GPL/LGPL/MPL-related licence stanzas in 75
  runtime package records and 335 Crawl4AI package records. Each package name,
  exact stanza and notice hash is in `copyleft_os_copyright_records` in the
  JSON. These are references within package copyright files, including
  alternatives and exceptions; they do not establish one effective licence
  for every file. The original copyright files and Debian common licences
  were copied by hash.
- The actual Crawl4AI `/tmp/project/LICENSE` and installed distribution
  LICENSE match byte-for-byte: [Apache License 2.0](component-notices/193fe32704bee15cd74f5153e569cdf830e26445e19798a55daee32da40758aa.txt).
  Redistribution calls for the licence, retained notices, modification
  notices, and any applicable NOTICE contents; the inspected source has no
  top-level NOTICE file. The DWS overlay modifies provider code, so its patch
  and corresponding source need inclusion in any distribution review.

## Remaining gaps

No signed SBOM, final-image provenance, or vulnerability attestation was
verified. The image-based inventory does not fully reconcile embedded native
code, browser third-party components, or corresponding-source delivery. The
SearXNG Void package database and its OS notices were unavailable. `dws` was
inspected before it declared a licence; it is Apache-2.0 from 2026-10-04
(`LICENSE`, `pyproject.toml`). `tiktoken` in Crawl4AI has an unknown licence
declaration; SearXNG's `python-dateutil` metadata says only `Dual License`
although its installed notice contains Apache/BSD terms. These and
the browser's bundled notices require source-level review before distribution.
