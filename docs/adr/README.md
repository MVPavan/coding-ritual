# Architecture Decision Records

Recorded decisions. Do not re-litigate or silently undo one — supersede it with
a new ADR that says what changed and why.

| ADR | Decision | Status |
|---|---|---|
| [0001](0001-allowed-paths-is-advisory.md) | `allowed_paths` is a disclosure exemption, not a containment bound; detection now, prevention gated on automatic multi-tick execution | Accepted |
| [0002](0002-node-instructions.md) | Task nodes carry inline `instructions`, enforced at `create_root`, rendered inside a deterministic fact frame | Accepted |
| [0003](0003-large-payloads-and-shared-methods.md) | Ceiling is the kernel's argv limit (~130 KB), not bd's — switch metadata writes to `@file`; no git-object bodies. Shared methods resolve-copy-freeze at root creation | Accepted, probe-resolved |
| [0004](0004-deterministic-routing.md) | Routing is a deterministic table lookup; the node holds the verdict, a computed `fail_code` routes on a declared edge. Model router rejected, model gate deferred with a trigger | Accepted |
| [0005](0005-run-ledger.md) | Engine facts move to a per-repository SQLite run ledger behind the store seam, bd keeps the bridge record and one label, nothing closes before its export is durable, and `debrief` writes each run's knowledge into the repo. ADR 0003's argv ceiling applies to the bd path only | Accepted |

Each ADR records who reviewed it. Review artifacts for 0001–0003 are
`scratchpad/probes/decisions-fable.md` and `scratchpad/probes/decisions-sol.md`
(scratch, not durable).
