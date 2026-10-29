---
skill: design-evolve
domain: engineering
stage: Design
substage: Architecture
secondary: []
family: 
aliases: []
status: active
---
# design-evolve

## Capability

Use when integrating supplied discussions or decisions into a self-contained next version of existing design documents.

<!-- registry:generated traits -->
- `integration-not-redesign`: Integrate only authorized decisions into the next version and never treat integration as licence to redesign.
- `resolve-scope`: Resolve source version, target path and included discussion files from the request, using supplied paths without reconfirmation and asking only about missing scope or overwrite permission.
- `classify-maturity`: Inventory source and discussions by concept, separating authoritative decisions from proposals, scratchpads and unresolved conflicts.
- `evidence-before-edit`: Read the actual discussion and affected core sections before a consequential change and record a source-to-target change map, shown before a multi-concept edit.
- `start-from-source`: Begin each target from its complete source and preserve exact identifiers, numbers, error behaviour and invariants unless explicitly superseded.
- `no-gap-filling`: Never fill a gap the source leaves open; record it as TBD with its source and keep ambiguous choices unresolved.
- `version-rekey`: Update version headers, filenames and internal references and copy untouched core files so the target stands alone with prior versions only in provenance.
- `consistency-check`: Check cross-document consistency, section links, invariant coverage and stale version references, consolidating routine duplication but asking when consolidation changes meaning or authority.
- `concept-map`: Keep a compact concept map of source, maturity, affected sections, decision, exclusions and conflicts as an evidence artifact, with durable status in the tracker.
- `layout-mirror`: Mirror the source layout and filename convention under the target version, searching every form of the old version identifier rather than blind-replacing.
- `preserve-structure`: Preserve heading hierarchy, invariant identifiers, table meanings and link targets, distilling implementation guides into decisions only when their meaning is clear.
- `report-provenance`: Report integrated concepts, files, decisions and deferred items with source pointers, never labelling unresolved scratchpad proposals as approved design.
<!-- /registry:generated traits -->

<!-- registry:generated lineage -->
No adopted lineage recorded.
<!-- /registry:generated lineage -->

<!-- registry:generated history -->
No ledger history recorded.
<!-- /registry:generated history -->

<!-- registry:generated reviews -->
None yet.
<!-- /registry:generated reviews -->

<!-- registry:generated sources -->
No adopted traits recorded.
<!-- /registry:generated sources -->

<!-- registry:generated declined -->
No declined traits recorded.
<!-- /registry:generated declined -->
