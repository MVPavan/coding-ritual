# Accepted application and SearXNG component inventory

**DONE_WITH_CONCERNS — 2026-09-22.** P1 cr-0km.14 evidence for stage5;
independent Sol review follows. This is not a complete runtime freeze,
distribution approval, vulnerability clearance, or browser qualification.
The changing browser-derived overlay is excluded and remains pending input.

The [JSON inventory](accepted-components-inventory.json) is the component index.
It records installed metadata, declared licenses, source locators, metadata/native
hashes, notice provenance, counts, and actionable gaps G1–G8. Existing
[application manifest](application-image-manifest.json) and
[SearXNG manifest](searxng-image-manifest.json) remain the authorities for qualified
versions and behavior; this inventory references them rather than replacing them.
Their historical “review pending” fields are not a new acceptance decision.
The supplied application review snapshot matched all 12 files byte-for-byte.

| Artifact | Exact locally inspected identity | Installed records |
|---|---|---|
| Application, linux/amd64 | `sha256:eb1475855045015fd0aa47e32605dcb5dcb68275d04f70be2386c9322694b616` | 2 Python distributions; 158 npm package locations; 97 Debian package records |
| SearXNG, linux/amd64 | `sha256:a93b665d10ce0675e8d2124187943111399ba69f384228c51b4cd21fdceda0bc` | 32 Python distributions; Void package database absent from inspected paths |

These are Docker image identities verified locally and recorded in the accepted
manifests. Do not reinterpret a local image/config ID as independently verified
registry manifest provenance. SearXNG additionally has its accepted registry
reference and source revision in its manifest.

## Collection and coverage

Four temporary extraction containers used exact accepted image IDs, unique names,
UID/GID 1000, no network, all capabilities dropped, no-new-privileges, and read-only
root filesystems. No application entrypoint or inference was invoked. Each was
removed by its owned container ID, including any anonymous image-declared volumes.
The second pass corrected usr-merge alias double counting and collected package
ownership, vendored versions, and package-database absence evidence. A donor-image
lookup failed before creating a container; no image was pulled or rebuilt.
Scripts and raw metadata are in `scratchpad/dws/accepted-inventory/`; their hashes
and receipt paths are indexed in JSON. No credentials or image contents were
uploaded to a scanning service. No scanner or dependency was installed.

The native file table hashes ELF binaries and files ending in `.node`, `.wasm`,
`.dll`, or `.dylib` below the inspected runtime roots. Resolved-path aliases are
counted once: 921 application files and 181 SearXNG files. This includes unused
cross-platform prebuilds; it is not a count of libraries loaded during operation.
Owners are assigned where package paths or dpkg records support them. Unresolved
ownership is explicit. Static archives, fonts/assets, compressed payloads and
embedded code without individual files are not exhaustively decomposed.
One SearXNG dangling manual-page symlink was unreadable; JSON retains the error.

Original license/copyright/notice texts are preserved byte-for-byte in
`accepted-components-notices/`: 347 provenance entries deduplicate to 223 files.
The JSON maps each content-addressed file to its original image path or immutable
upstream URL and SHA-256. These are evidence copies, not a completed distribution
notice bundle. Original whitespace is intentional. No copyright text was rewritten.

## Application ingredients and provenance

The application Python environment contains the local `dws` scaffold; the base
image also contains `pip`. Pip's installed `vendor.txt` records 19 bundled
component versions separately from the two distribution records, and captured
notices include its vendored libraries. DWS METADATA declares neither a license
nor a License-File: distribution rights remain an owner decision (G5).
CPython's shipped license is preserved. The application manifest pins the Python,
Node, and uv base digests and available source/build annotations.

The QMD lock matches the accepted host lock byte-for-byte. It resolves 178
package locations, while the accepted image contains 158. The JSON identifies
every absent entry: two explicitly pruned MCP packages and 18 absent optional
platform entries. Installed versions match their lock entries. Tarball URLs and
SRI hashes bind the npm artifacts; repository/homepage declarations alone do not
prove their source commits. The two accepted lexical native hashes match the
actual `better-sqlite3` and `sqlite-vec` files.

The retained npm distributions declare MIT (132), ISC (17), BlueOak-1.0.0 (5),
`MIT OR Apache` (2), Apache-2.0 (1), and `(BSD-2-Clause OR MIT OR Apache-2.0)` (1).
These are verbatim top-level declarations, not a conclusion about all bundled
native code. Eight installed package locations have no captured package-local
notice: `sqlite-vec`, `sqlite-vec-linux-x64`, `simple-git`, two `@simple-git`
packages, and three `@reflink` packages. Resolve required notices from their exact
published artifacts/upstream sources before distribution.

Model-related distributions include node-llama-cpp and Linux x64 CUDA/Vulkan,
plus arm64/armv7l packages actually admitted by their npm platform declarations.
The file index also exposes tree-sitter, SQLite, reflink and model native payloads.
Installed does not mean exercised: the accepted application qualification reports
no model weights/downloads or inference. Embedded native third-party/source
mapping remains incomplete (G2).

The recipe copies Node and `libstdc++` from the pinned Node builder. The receiver's
dpkg record cannot establish the donor library's provenance, even where a package
claims that path (G3). Node's official release tag was resolved to commit
`6add85e4c46b8be383c8b637102d6b6fd206adce`; its full
[bundled license](accepted-components-notices/e991d81497a85bb24fc6bffae0a3637a6accd6c6bc5ce1f2c5698bd555cf9d49.txt)
was obtained from that immutable source. It includes third-party terms omitted
when the recipe copies only the executable. Source-tag correspondence is not
independent binary-to-source build verification.

Debian records include exact installed package and declared source versions,
versioned source lookup locators, and original copyright texts where captured.
Multi-license copyright stanzas and exceptions are preserved instead of collapsed
to one SPDX label. Source locators have not been verified as complete matching
source archives. Build-only uv, npm CLI, and the five hash-pinned Python build
tools are recorded by recipe/requirements references, not counted as installed
runtime distributions. Frozen input hashes and build logs are available; no
signed final-image SBOM/provenance or reproducibility attestation was verified.

## SearXNG ingredients and provenance

Installed Python distribution versions exactly match the accepted manifest's
32-package map. Each has captured license text; metadata includes original license
expressions or classifiers and declared source URLs. Source-wheel hashes and
immutable commits were not recovered. Native content includes granian, lxml,
curl_cffi and supporting extensions. The accepted manifest records effective
OpenSSL, SQLite, glibc, libxml/libxslt and curl-impersonate component versions;
this inventory references those facts and hashes the installed files.

SearXNG's installed version file agrees with accepted source revision
`61d660276f1288e7d512e8d8da46cb8442728454`. The previously retrieved upstream
AGPL license matches the manifest hash. The official Dockerfiles at that revision
use mutable base names and pip requirements; the accepted final digest does not
recover the exact upstream base/source build. `/var/db/xbps`, `/usr/share/doc`,
and `/usr/share/licenses` are absent, and no dpkg status exists. Therefore zero
OS package records means **unavailable metadata**, not zero OS components.
Native filenames/hashes do not substitute for Void package versions or licenses.
G1 requires an upstream package/source manifest and missing notices.

The copied SearXNG tree also contains static assets. Its complete asset dependency
and vendored component attribution is not proven by Python METADATA or the
application AGPL label (G6). curl-impersonate/BoringSSL and other embedded native
components need their own source/notice reconciliation (G2).

## Source and notice considerations for stage5

These are targeted conditions from the preserved primary texts, not a sweeping
legal compliance judgment or a source offer made by this document.

- [QMD's original MIT text](accepted-components-notices/24c446836e7e2cdea13a914de10c88c553e6297366061ba24013b8ce73c8f7fa.txt)
  requires its copyright and permission notice in copies or substantial portions.
  Preserve package-specific MIT/ISC/BSD/BlueOak texts rather than substituting
  this inventory's license labels.
- [Apache 2.0 section 4](https://www.apache.org/licenses/LICENSE-2.0) requires the
  license, change notices for modified files, relevant source attribution, and
  readable applicable NOTICE attribution where supplied. The copied originals
  support later assembly; the inventory does not establish its completeness.
- [SearXNG's exact AGPL text](accepted-components-notices/57c8ff33c9c0cfc3ef00e650a1cc910d7ee479a8bc509f6c9209a7c2a11399d6.txt),
  sections 4–6, governs conveying source/object forms and corresponding-source
  options. Section 13 addresses a modified version used through remote network
  interaction. Stage5 must assess the actual modifications and delivery mode,
  preserve notices, and provide the applicable source access mechanism. A GitHub
  revision link alone is not proof that all corresponding source is supplied.
- Debian includes copyleft components. [GPLv2 section 3](accepted-components-notices/8177f97513213526df2cf6184d8ff986c675afb514d4e68a404010521b880643.txt)
  sets object-distribution source/offer alternatives; a written offer has specific
  duration and recipient conditions, and the downstream-offer alternative is
  limited. [LGPL 2.1 sections 4 and 6](accepted-components-notices/dc626520dcd53a22f727af3ee42c770e56c97a64fe3adb063799d8ab032fe551.txt)
  distinguish distributing the library and linked works, including notices,
  library source and relinking/replacement conditions. Select the applicable
  route for the actual artifact; account separately for GCC runtime exceptions.

Corresponding source may include patches and build/install scripts. Source
versions, archive availability and applicable exceptions must be reconciled before
choosing a source delivery/offer mechanism (G4). The retained original texts are
the primary evidence; GNU web retrieval timed out, so those summaries use the
local exact texts. No license interpretation depends on a mutable package tag.

## Remaining boundaries and checks

No optional hosted-provider integration or default credentials are included in the
accepted scaffold. Enabling one later requires a selected provider/service,
credential and data-flow decisions, and then current terms review. This does not
classify SearXNG's public search engines as absent; their behavior/availability
remains bounded by its existing qualification. Browser inventory awaits its own
accepted artifact. No advisory scan was performed, and no vulnerability-clearance
claim is made. Final vulnerability and terms judgments stay with stage5.

Validation: JSON parse; all evidence/notice hashes and local Markdown links;
12 reviewed application snapshot hashes; accepted source/config hash checks;
178-to-158 lock reconciliation; both accepted lexical native hashes; exact
SearXNG Python-version agreement; scoped Markdown/JSON whitespace; and Git status.
The package/database limitations above remain visible rather than being filled
with inferred licenses or versions. No runtime/source/config, branches, worktrees,
commits, or Beads were changed. Independent Sol review is still pending.
