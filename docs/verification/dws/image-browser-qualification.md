# P1 image/browser qualification — protective candidate

2026-09-22 · cr-0km.4 · **DONE_WITH_CONCERNS: candidate ready for independent review,
not stage completion.** The bounded protective overlay removed the measured
WebRTC UDP bypass in the exercised cases while preserving real HTTP/HTTPS rendering.
All 62 final cases met their executable receipt assertions; 11 destructive receipt
mutations were rejected. Review findings F1 and F2 are addressed in material review
fix round 1. Transport coverage limits below
remain explicit; this is not a claim that G-05, G-09, AT-026 or release gates passed.
Fresh Sol xhigh re-review is still required.

## Delivered scope and identities

Owned candidate files:

- `dws/docker/crawl4ai-egress/Dockerfile` and `patch.py`.
- `dws/tests/qualification/image_browser_qualification.py`.
- `dws/tests/qualification/browser_containment_fixture.py` and
  `browser_fixture_trust.py`.
- This report and `image-browser-manifest.json`.

No application Dockerfile, Compose, package/source/QMD file, PRD/design or other
worker's application-image report was edited in this resumed work. No commits,
branches/worktrees, delegation or Beads mutations were performed.

Base provider:
`unclecode/crawl4ai@sha256:bd36741e7bdd35ddc1a05d9183e1d6d8cefb61dd640d944a25d026b76e917690`.
Final tested local derived image ID:
`sha256:514fd2123e6511b18c1f06c1d793daf4737b7310be73cf9cfb63ce4db2a52a8b`.
This is a local image content identity, not a published registry digest. Rebuild
from the pinned base and checked patch; do not deploy a mutable candidate tag.
The test tag was removed after evidence capture.

Inherited runtime: Linux amd64, appuser/UID 999, Python 3.12.13, Crawl4AI 0.9.2,
SQLite 3.40.1, Playwright 1.61.0, Patchright 1.61.2, Chromium headless-shell
149.0.7827.55 (revision 1228). The unchanged package inventory and prior executed
browser-version output remain in the baseline evidence and manifest. This overlay
changes only two source files and installs no packages. It is a provider image,
not the DWS Python >=3.13 application image. MCP/model-related provider packages
remain present; no model-free image claim is made.

## Protective implementation and verified source

The installed `/app/egress_broker.py` remains the single URL-resolution and
connection-pinning policy owner. Its existing all-records/non-global-address check
and the stock `/app/egress_proxy.py` numeric-IP dial paths are retained unchanged.
The overlay replaces only the browser-enforcement tail and removes owner escape
hatches for internal URLs and insecure TLS. Proxy construction exceptions now
propagate; a missing/invalid local proxy aborts browser construction.

The same broker function applies at `BrowserManager` construction, its Playwright
argument builder, and both managed-browser flag/argument builders. Thus the raw
startup/pool configuration also passes through enforcement, not only `/crawl`.
The enforced launch flags are appended after conflicting configuration flags are
removed:

```text
--force-webrtc-ip-handling-policy=disable_non_proxied_udp
--disable-quic
```

The patch removes both hard-coded certificate-ignore flags from both library
builders and fixes `ignore_https_errors=False`. Non-Chromium and remote-CDP
configuration is refused. Existing upstream untrusted-field rejection stays in
place: callers cannot set proxy, resolver/transport launch flags, CDP or arbitrary
Python hooks. Internal provider connectivity is still configuration; it never
creates an exception for caller target URLs.

Build-time SHA-256 and expected-context checks abort on unrecognized source before
writes. Base source hashes:

- broker: `9884e0a4d972607e1cd20aa70bf5d8d86767fe3d61a53ebc6bd3776880c822cf`
- browser manager: `76724e47ccace4cee8c5b654f3c132744d30d9a98706984d77517be06a317c3d`

Patched source hashes, printed during the initial build and independently
reconstructed from the same patch:

- broker: `c14ec7c03ec5a1297a3fe005da8b22bf8291a80020b42044af4d5f2fa0c50ae8`
- browser manager: `6f44b845b33553fe5640796c5e8a873647b7d4f9afedd7e120e49c7e7b6de9b6`

Reapplying to changed source was verified to fail the hash gate. Reviewable derived
source and the exact diff are in
`scratchpad/dws/browser-containment/implementation/derived-source/`.
Original installed source remains under
`scratchpad/dws/runtime-qualification/source/`: broker `:113` resolver and `:179`
old enforcement; proxy `:95,105,123,134` resolution/pinned dials; browser manager
`:70,709,779,1057` launch paths; server `:179,198,856` proxy startup, permanent pool
and liveness. The overlay deliberately does not duplicate their URL validators.

## Final measured results

Primary run: `scratchpad/dws/browser-containment/fix1/run2/`.
`results.json` contains cases, independent observations, sensitivity receipts,
image/network/container metadata and actual Chromium command lines.
`commands.jsonl` records exact commands, durations, return codes, stdout and stderr.
Receipt assertions now determine the runner exit status; they are no longer only
an external check of saved evidence. The earlier `implementation/fix2/` run and
its `receipt-checks.json` remain historical evidence, unchanged.

| Exercise | Actual observation |
|---|---|
| Public A and public AAAA, HTTP and trusted HTTPS, direct and valid redirect (8 cases) | 200; DOM-written marker in extracted Markdown; WebSocket-open marker; all six fetch/beacon/image/script/iframe/WebSocket paths reach the fixture |
| Public TURN/TCP | Actual TCP connections and 28-byte TURN Allocate requests, prefix `000300082112a442`; not a full TURN relay |
| Ten forbidden address forms, each direct/HTTP redirect/page resources/HTTPS CONNECT redirect (40 cases) | Direct requests 400; redirects 500; resource pages render with 200; zero forbidden TCP or UDP receipts |
| HTTPS-origin WebTransport to loopback IPv4, metadata IPv4, loopback IPv6 and ULA (4 cases) | Constructor issued and completed without synchronous error; asynchronous handshake rejected; useful HTTPS/resources/WebSocket remain functional; zero forbidden receipts |
| Mixed public/private A and public A/private AAAA | Both DNS records independently observed; 400 and no target TCP/UDP receipt |
| A public→metadata and AAAA public→ULA, TTL 0 | Observer records both answers; 500 and no target TCP/UDP receipt |
| Untrusted CA and trusted CA with wrong hostname | TCP reaches TLS listener, no HTTP request is sent; crawl fails, while trusted matching HTTPS succeeds |
| Legacy Python hook, proxy, CDP and extra-args overrides | 422/400; no forbidden receipt |
| Missing proxy, internal-URL environment escape and insecure-TLS environment escape | All three separate processes refuse execution with the expected RuntimeError |
| Actual browser launch commands | Startup permanent browser and final two browser parents have proxy + both fixed flags, no certificate-ignore flags |

Forbidden forms were IPv4 loopback, RFC1918, link-local/metadata
`169.254.169.254`, decimal loopback, IPv6 `::1`, ULA, link-local, IPv4-mapped,
NAT64 with embedded private IPv4, and 6to4 with embedded loopback IPv4.
They belonged only to synthetic listeners: no real owner private or metadata
service was contacted. IPv6 link-local used an explicitly allocated isolated
Docker network address `fe80:0:0:71::3`; sensitivity injection used its interface
scope. This does not establish every scoped-URL spelling or browser ICE behavior.

After sensitivity injections, the complete final observer histories—not just
per-case time slices—contain **144 public TCP connections, zero forbidden TCP
connections and zero UDP packets**. The browser-container observer has zero
post-sensitivity connections/packets. Baseline STUN bypass observations therefore
remain a meaningful negative control; there was no re-run with weakened policy.

Independent observer controls cover TCP ports 8080/3478 and UDP ports 3478/443 on
both address families. `IP_PKTINFO`/`IPV6_PKTINFO` record the actual UDP destination;
TCP receipts are recorded at accept, before HTTP parsing or TLS negotiation.
Direct injections into each listener's own assigned address proved all observers
sensitive, including loopback, ULA, link-local, NAT64 and 6to4. These local injections
prove listener sensitivity; they are not evidence of a browser request or complete
cross-container route coverage. Public browser HTTP/HTTPS/TURN traffic supplies
separate real cross-container positive controls.

## Material review fix round 1: F1 and F2

Only the runner, containment fixture, this report and manifest changed in this
round. The production Dockerfile/patch and TLS trust loader are byte-identical to
`candidate-review-snapshot.json`; their existing proof remains applicable.

F1: `case_failures()` is now the runner's shared receipt predicate. Every positive
case requires all six actual resource paths, WebSocket-open state and recognizable
TURN Allocate payloads. Every forbidden-resource case requires a DOM-written
`DWS_ACTIONS_ISSUED` marker **and** executed JSON state with `complete=true`, emitted
after all intended actions/constructors have been issued and offer tasks settled.
The initial rendering marker alone cannot pass. TLS negatives require actual TCP
accepts at the target TLS port and no HTTP receipt. Existing denial status, DNS,
listener sensitivity, launch policy and forbidden-receipt checks remain enforced;
the entire post-sensitivity history also rejects forbidden traffic between cases.

`fix1/f1-before.json` records a false pass from the actual old predicate after
removing a required positive fetch receipt from real saved evidence. The new run
mutates real passing cases and verifies eleven rejections: remove each of the six
resource paths, remove TURN payloads, remove the completion marker, remove JSON
completion state, remove TLS TCP receipts, or inject a TLS HTTP leak. These are
executable assertions, not expected values copied into the evidence.

F2: four candidate pages originate on trusted HTTPS and explicitly construct
WebTransport toward synthetic `127.0.0.1`, `169.254.169.254`, `::1` and `fd71:d05::3`
UDP443 targets. Each records available/issued/constructed=true, constructor
error=null and a later `Opening handshake failed` rejection. They also pass all
public resource/TURN/WS assertions. No syntax failure or undefined constructor is
counted as an attempted transport.

A separate **test-only direct-browser calibration** launches the exact same
Chromium 149.0.7827.55 binary in a disposable nonroot/cap-drop/no-new-privileges
container attached only to the synthetic public internal network. Unlike the actual
candidate, this control uses direct Playwright (no Crawl4AI), no proxy, and
`--enable-quic` instead of `--disable-quic`; the WebRTC restriction remains. It also
maps only `public6.dws.test` to its synthetic IPv6 address using a test-only resolver
flag. The fixture CA remains trusted normally; no certificate-ignore flag is used.
These differences are recorded with the actual parent command line. The protected
candidate never receives these control settings or a target-policy exception.

Both control HTTPS pages render and construct WebTransport. Independent listeners
observe **eight real QUIC v1 Initial datagrams, each 1,250 bytes**, four per family:

- `11.203.0.4:48263` → `11.203.0.3:443`.
- `[2001:4860:abcd:71::4]:49211` → `[2001:4860:abcd:71::3]:443`.

The runner recognizes Initial long-header bits, version 1, connection-ID lengths,
empty initial retry token, encoded payload length and minimum datagram length from
recorded bytes. Source and actual destination come from independent socket receipts.
This is browser-generated calibration, distinct from manual listener injections.
A missing family or missing genuine Initial makes the run fail as inconclusive.
The control is removed before listener sensitivity and protected cases; its packets
cannot contaminate the protected candidate's post-sensitivity counters.

The first new run (`fix1/run1/`) stopped at control IPv6 DNS resolution with
`ERR_NAME_NOT_RESOLVED`; cleanup succeeded. A narrow test-only resolver mapping and
per-case error capture corrected that calibration issue. `fix1/run2/` then completed
62 cases: eight public rendering/redirect, two TLS, forty forbidden-address,
four WebTransport, four DNS and four untrusted-override cases; all passed, alongside
three fail-closed guard processes and eleven receipt mutations. Both new raw runs
are preserved separately. This is one material review fix round, not another
production-policy change or a release-gate completion.

## TLS fixtures, isolation and resource limits

The test generates a private synthetic CA, a matching server certificate and a
separate untrusted certificate. Only the fixture CA is imported into the disposable
appuser NSS database using the image's existing NSS libraries. No certificate-ignore
flag, SPKI exception, insecure context option or production trust-store change is
used. The test-only loader follows NSS certificate APIs ([certificate declarations](https://raw.githubusercontent.com/nss-dev/nss/main/lib/certdb/cert.h)); runtime tests verify its effect.
Synthetic certificate keys are retained solely with ignored test evidence.

Containers run as the upstream appuser with cap-drop ALL, no-new-privileges,
2 GiB memory, two CPUs, 256 PIDs and 256 MiB shm. Six uniquely named internal
Docker networks provide fixture-only address classes. No host ports, host network,
NET_ADMIN, sidecars, host firewall changes, archive volumes, Docker socket, home
directory or owner secrets were mounted. Only the explicit fixture scripts and
generated synthetic fixture directory were mounted read-only. Provider filesystem
state and NSS trust were disposable container-layer state.

The final sample was 460.6 MiB / 2 GiB, 181 PIDs, 0.55% CPU. This is an
idle-after-work sample, not a peak or capacity qualification. `/health` is inherited
liveness only; successful real rendering is the useful capability check.
The provider still runs supervised Redis, Gunicorn/Uvicorn and multiple Chromium
processes. **Chromium still uses `--no-sandbox`.** No renderer-compromise containment
claim is made and no Docker sandbox/privilege control was relaxed.

All recorded containers, six networks and the unique candidate image tag were
removed successfully; exact-prefix post-run checks returned no remaining resources.
Base images, build cache and other workers' resources were preserved.

## Limits, review disposition and bounded rounds

The coordinator's Sol recommendation is implemented with measured before/after
UDP evidence, public HTTP/S function, real TCP/TLS/IPv6 observers and command-line
inspection. **Flag presence alone is not the acceptance evidence.**

Remaining limits to disposition in fresh review:

- WebTransport denial now has calibrated real browser QUIC Initial evidence for
  public IPv4/IPv6 and HTTPS-origin forbidden-target constructor evidence. No full
  QUIC server, successful handshake or WebTransport application exchange is claimed.
- TURN/TCP allocation attempts are observed, not a successful relay. Browser ICE
  can reject individual address spellings before dialing; listener sensitivity and
  zero forbidden traffic do not prove every ICE spelling was dial-attempt eligible.
- DNS evidence covers the recorded A/AAAA mixed/rebinding schedules, not every cache,
  connection-reuse, service-worker or alternate-resolver schedule. Service workers,
  popups, browser exploits, sustained load, cancellation and arbitrary browser
  extensions are not qualified here.
- Application image, same-image API/worker boot wiring, SearXNG, provider integration,
  closed DWS DTO and command-access security are separate work. This file does not
  promote a provider probe to a complete Compose deployment or close release gates.

One protective implementation; two bounded fixture fix rounds; no provider-policy
relaxations. Initial run built and proved fail-closed guards, then stopped before
browser launch on unavailable NSS symbols. Fix one corrected NSS exported APIs and
fresh-token initialization; it started the hardened permanent browser, then stopped
on an injected sensitivity-script indentation error. Fix two corrected and compiled
that script and completed the 58-case run. All failed receipts remain alongside
successful evidence. Those original receipts are retained. The separately authorized material review
fix round 1 below adds no production overlay change.

## Reproduction, checks and retained history

From repository root, using ordinary Docker approval controls:

```bash
python3 dws/tests/qualification/image_browser_qualification.py \
  --output scratchpad/dws/browser-containment/fix1/reproduction
```

Use a new output directory (the runner refuses overwrite). It builds the overlay
from the exact base, creates only uniquely named resources, runs bounded fixtures,
records results and cleans its own resources. Missing prerequisites are failures,
not silently skipped tests. The runner may report observed-case success while the
explicit transport limitations above still prevent a broad qualification claim.

Scoped Ruff lint/format, strict mypy and Python compilation pass for the patch and
three qualification scripts; injected container scripts were separately compiled.
JSON manifests and `git diff --check` pass. Initial/source-integrity and final
receipt checks are recorded with their precise scope in the manifest.

The accepted unsafe baseline remains untouched under
`scratchpad/dws/runtime-qualification/{baseline,round1,round2}/`. In particular,
`round2/results.json` independently records four 20-byte STUN packets for each of
loopback, private, metadata and decimal-loopback pages. The previous manifest and
probe source were copied to `scratchpad/dws/browser-containment/implementation/`
for traceability. Earlier Node-based container-volume/WAL/lock observations remain
in `scratchpad/dws/runtime-qualification/volume.log`; they are historical evidence,
not qualification of the separately evolving application image. No historical raw
artifact was rewritten.
