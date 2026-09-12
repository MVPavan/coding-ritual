# Bridge-Proof Probe Evidence

**Recorded:** 2026-09-10

**Tool:** bd 1.1.0

These observations came from a live, isolated bd 1.1.0 rig in `/tmp`. The rig
has been removed. Reproduce this evidence only by creating another isolated rig,
then running the fixture described for each probe below and inspecting the stated
JSON or `bd ready` result.

## P1 — Parent listing returns a parent field

**Probe.** Create an epic and two children, then run
`bd list --parent <epic> --json`.

**Observed.** The command returned descendants, and every returned row carried a
`parent` field.

**Plan consequence.** Direct-child membership can be read from each row's
`.parent`, supporting D1's narrow phase adapter instead of inferring membership
from an identifier convention (`docs/plans/phase-execution-interpreter-bridge.md:45-49`).

## P2 — Re-parenting preserves the bead ID

**Probe.** Re-parent standalone bead `probe-a4v` under an epic, then list the
epic with `bd list --parent`.

**Observed.** `probe-a4v` kept its original ID; it did not become `<epic>.3`.
`bd list --parent` found it through its `parent` field.

**Plan consequence.** D1 selection must use `.parent`. The execution skill's
current dotted-ID filter cannot match a re-parented ID
(`.claude/skills/execution/SKILL.md:74-77`).

## P3 — Claim and metadata can use one invocation

**Probe.** Run `bd update <id> --claim --metadata '<json>'` once, then inspect
the bead.

**Observed.** The resulting status was `in_progress` and the metadata was present.

**Plan consequence.** The bridge can make the admission write and claim in one
bd invocation, so there is no window in which it crashed between two calls. This
does not prove bd makes both writes in one internal transaction; that remains a
smaller bd-internal risk. D2 still requires the metadata record to be read back
(`docs/plans/phase-execution-interpreter-bridge.md:53-77`).

## P4 — Parent-list rows include metadata

**Probe.** Run `bd list --parent --json` over direct children that carry
metadata.

**Observed.** Returned rows carried `metadata`.

**Plan consequence.** The direct-child discovery scan can read admission intent
without a per-bead `bd show`, which is the discovery path D2 requires
(`docs/plans/phase-execution-interpreter-bridge.md:73-77`).

## P5 — A genuine dependency controls readiness

**Probe.** Add `D1` as the prerequisite of `D2` with `bd dep add D2 D1`; inspect
`bd ready` while `D1` is open and again after it closes.

**Observed.** `D2` was absent while `D1` was open and appeared after `D1` closed.

**Plan consequence.** A dependency is an appropriate readiness mechanism only
when a stage actually needs another stage's output; it must not represent a mere
experimental sequence (`.beads/beads.md:73-74`; `docs/plans/phase-execution-interpreter-bridge.md:216-228`).

## P6 — Metadata merges only at the top level

**Probe.** Write `{"other_key":...}` to metadata containing `phase_bridge`, then
write `{"phase_bridge":{"state":"landed"}}`.

**Observed.** The top-level `other_key` write preserved the existing
`phase_bridge` key. Writing the nested `phase_bridge` object replaced that whole
object: `schema` and `attempt` were lost.

**Plan consequence.** Every D2 write must serialize the complete
`phase_bridge` object, including `previous_attempts[]`; partial nested writes
silently discard required recovery state
(`docs/plans/phase-execution-interpreter-bridge.md:53-66`).
