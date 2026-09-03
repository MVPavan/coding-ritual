# ADR 0003 — large payload storage, and how shared method libraries will work

- **Status:** Accepted; storage mechanism **resolved 2026-09-03 by probe** (see Probe results)
- **Date:** 2026-09-03
- **Deciders:** repo owner
- **Reviewed by:** Fable 5.1 (high), Sol (xhigh)
- **Related:** ADR 0002 (node instructions)

## Context

Two coupled questions. Both were answered too confidently in the pre-review
draft; the review changed one of them.

**3a — where large payloads live.** The pinned graph body, resolved config,
verifier pins and instance inputs are all bd metadata on one root bead. Adding
per-node instructions grows that. Spec §3.1 already names a fallback: *"a
dedicated child bead or content-addressed git blob referenced by hash"*
(`docs/specs/workflow-interpreter.md:379`, §11 at `:786-790`).

**3b — shared, improvable methods.** The stated future requirement: a library
of common methods, improved once, picked up by every new graph.

## Probe results (2026-09-03) — the storage question is settled

Run against an isolated bd workspace in `/tmp`, replicating the production
argv exactly (`bd -C <ws> --actor <a> create --title ... --metadata <JSON>
--silent`). Every success was read back and compared byte-for-byte.

| Path | Result |
|---|---|
| Inline argv (**production today**) | largest payload created **and verified: 130,818 chars**. Fails at 131,329 with `OSError: [Errno 7] Argument list too long` |
| `--metadata @file` on `create` | **verified exact at 70KB, 200KB, 1MB and 4MB** |
| `--metadata @file` on `update` (root self-ID merge) | **verified exact at 300KB**, sibling keys preserved |
| Inline, multibyte UTF-8 | limit is **bytes, not characters** — 60,000 B verified, 120,000 B fails |

**Conclusion.** The ceiling is the kernel's `MAX_ARG_STRLEN`
(32 x 4096 = 131,072 bytes on this host), not bd's, and it is hit before bd
runs. Fable's hypothesis is confirmed: the phase-0 probe measured a path
production never takes. Switching `BdClient` to `--metadata @file` lifts the
ceiling by **at least 30x** on both the create and merge paths.

The inline failure mode is **safe**: a loud `OSError` at exec time, never
silent truncation or corruption. Nothing shipped is at risk today — measured
bodies are 2,253 and 5,307 bytes against a ~130 KB ceiling.

Not re-verified here: `--event-payload @file`, recorded as lossy at
`bdio/client.py:337-338` (probed 2026-08-25). That hazard is
event-payload-specific and does not affect the `--metadata` switch; event
payloads are small by nature. It stays as recorded.

**Decision: switch `BdClient` metadata writes to the `@file` form, keeping
the existing read-back verification. Git-object bodies are NOT built.**

## Decision 3a — establish the real ceiling before choosing a mechanism (SUPERSEDED BY THE PROBE ABOVE)

**The pre-review draft committed to content-addressed git objects. That is
downgraded to plan B, because the review found the ceiling is probably not
where anyone thought.**

The §11 probe-2 evidence — *"70,000-char metadata value round-trips
byte-identical"* — was obtained via `--metadata=@file.json`
(`scratchpad/probes/phase0-results.md:19-23`). **Production does not use that
path.** `BdClient` passes canonical JSON inline as a single argv element
(`workflow_interpreter/bdio/client.py:334-335`). Linux caps one argv element at
`MAX_ARG_STRLEN` = 32 × page size = **131,072 bytes** (page size verified 4096
on this host). So:

- The probe validated a path production never takes.
- The real production ceiling is likely ~128 KiB, kernel-imposed, not bd's.
- Sol's worst-case estimate of ~108 KiB leaves roughly 20 KiB of headroom.

**Therefore, in order:**

1. **Run a real probe** before asserting any storage mechanism. It must
   sweep/binary-search serialized sizes around failure using an actual
   `RootMetadata` (graph body, config, verifier pins, inputs, method pins),
   cover multibyte UTF-8, and exercise create, self-ID merge, list/show,
   restart and same-key recreation. Record exact failure sizes and **failure
   modes**, and latency. Output is a conservative supported limit for the
   pinned bd backend and version — never a claimed universal ceiling.

2. **Test whether `--metadata=@file` is faithful on `create` with read-back.**
   If it is, switching `BdClient` to it lifts the argv ceiling and **may remove
   the need for git-backed bodies entirely, for a long time**. Note the
   adjacent hazard already recorded in the code: the `@file` form is broken for
   `--event-payload`, storing the literal string `"@file"` and exiting 0
   (`bdio/client.py:337-338`, probed 2026-08-25). `_assert_metadata`
   (`client.py:404`) already read-back-verifies metadata, so a broken `@file`
   would be caught loudly rather than silently.

3. **Only if both fail** — they did not; this branch is now moot, retained
   for the record — adopt content-addressed storage — and then it must be
   a **git object referenced by hash, never a filesystem path**. A path is
   mutable; it destroys the reproducibility guarantee that put the body in bd
   in the first place. That work is not small, and the ADR records what it must
   specify: object type and encoding; SHA-256 content digest alongside the git
   OID; a durable advertised ref namespace (it cannot be `refs/wf/<root_id>/`,
   because bd assigns the root id only after metadata is written —
   `bdio/roots.py:119-126`); write-and-pin-before-root ordering; clone/fetch
   distribution (`refs/wf/*` are not fetched by default, and the git command
   surface deliberately lacks `fetch` — `supervisor/gitcmd.py:98-102`);
   retention against `git gc` pruning unreachable objects; an injected payload
   reader (`bdio` imports nothing from `supervisor`, and `parse_root`
   re-validates from inline metadata — `bdio/records.py:194-210`,
   `bdio/wire.py:291-320` requires an inline `graph_body`); and a loud
   `payload_unavailable` halt **before routing**, with no fallback to the
   mutable authoring file. It also amends premise P1's *"routing needs no
   file"* (`spec:32-33`).

Root identity is unaffected either way: `_assert_same_instance` compares the
content hash and config signature (`bdio/roots.py:225-243`), provided the body
*location* never enters resolved config.

## Decision 3b — shared methods resolve, copy and freeze at root creation

**The principle holds. One claim in the draft was false and is corrected.**

- A future graph may name a method rather than inlining it. At root creation
  the name is resolved from the library, the **text is copied into the
  instance**, and its digest is pinned. The library stays mutable and
  improvable; every created instance is frozen and reproducible; a run in
  flight can never shift underneath itself; new instances pick up improvements
  automatically.

- **Correction: this is not a pure additive change to one step.** The draft
  claimed the graph format would not change. It would. `$defs/node` in
  `graph_schema.json` sets `additionalProperties: false` (verified), so a `use`
  property requires a schema, model and semantic-validator change. It does not
  require a `wf-canon-json/1` bump, and it does not move the hash of any graph
  that omits the field — so it is **a schema change but not a migration**.
  `use` and `instructions` need an exactly-one-of validator rule.

- **Where the copied text lives:** in the pinned body, with a new
  `authored_content_hash` recorded alongside the linked hash. The alternatives
  both break something — resolved config contradicts ADR 0002 point 5 and
  forces the composer to read the resolved view; instance inputs share the
  64 KiB cap (`bdio/roots.py:43`) and become trim-eligible, which for
  instructions is never right. Recording both hashes answers the audit
  question directly: `graph_content_hash` identifies the **authored graph**,
  not the complete executable contract.

- **Resolution reads the instance base commit, not the working tree.**
  `pin_verifier_digests` has the same gap today
  (`supervisor/channels.py:286-289`); one rule covers both.

- **Root identity must cover resolved methods.** Same-key comparison currently
  covers graph hash, instance inputs, test flag, base commit and config
  signature — nothing for methods (`bdio/roots.py:215-258`). An immutable root
  dependency record (canonical method name, body or locator, digest, library
  revision, byte length) must participate in same-key comparison. **Re-linking
  the same instance key after library drift hard-fails; it never returns or
  mutates the old root.**

- **Deferred until the library exists:** whether entries are versioned
  (`name@2`) or always-latest-at-creation, and whether the linked body strips
  `use`.

## Consequences

- ADR 0002 is not blocked by any of this. Instructions go inline now.
- ADR 0002's size caps can now be set against a measured number: ~130 KB
  today, ~4 MB+ after the `@file` switch. Caps should still exist, but to
  bound prompt cost and keep `token_budget` meaningful — not to dodge a
  storage cliff.
- The `@file` switch is a small, well-bounded change to one client method
  with read-back verification already in place.
- No new ref namespace, no retention policy, no P1 amendment, no injected
  payload reader. All of that work is avoided.

## Rejected

- **A filesystem folder with a path pointer.** Mutable; loses reproducibility
  and tamper-evidence. This was the initially proposed shape and is refused.
- **Committing to git objects before the probe.** The evidence that motivated
  it measured a path production does not use.
