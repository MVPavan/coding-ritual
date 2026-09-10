# Repository context review — 2026-09-10

Review baseline: migration `5d7cefa`, tracking `a546200`. The findings and counts
below describe the 13-file pre-cleanup state, its AGENTS.md routing, and selected
implementation evidence.

Implementation: applied under `cr-xmo` for user review. Eight active context files
remain; historical reports and full incident narratives are archived under
`docs/research/repo-context-history/2026-09-10/`. Existing pytest selections are
retained: the verifier's five-stage output has regression coverage, but this does
not establish that overlapping test execution is necessary. Gate optimization
remains a separate change. AGENTS.md loading rules and Python tooling choices
are unchanged.

Cleanup verification: active guidance fell from 6,127 to 2,335 words; startup
reading from 809 to 401 words. Skill-catalog, active-path, whitespace, and
archive-preservation checks passed. Historical files were compared with
`scratchpad/repo-context-before-cleanup.tar.gz`. No runtime code or test gate was
changed; the interpreter suite was not run for these documentation edits.

Subsequent user-directed change (`cr-5e6`): delegation is shared agent policy,
so its essential contracts now live in AGENTS.md. The delegation context file
was removed, leaving seven active context files; workflow risk labels moved to
the execution skill. Counts above describe the preceding cleanup checkpoint.

## Assessment

Keep `.repo-context/` as current, conditional repository guidance. Its main
problem is overlapping authority and mixed current/historical material, not a
need for a larger instruction system. Prefer eight active entry files; preserve
historical evidence elsewhere rather than deleting it.

The folder contains 6,127 whitespace-delimited words across 798 lines. Only
`repo-map.md` and `docs-index.md` are requested at session start: 809 words
combined. These are file counts, not measured model tokens or runtime loading
telemetry. `learnings.md` accounts for 2,280 words (37.2% of the folder), but is
already conditional. Moving it alone would not reduce startup context.

## Findings and priority

### 1. Separate current guidance from dated evidence

`learnings.md:17-73` mixes version-specific CLI and installation observations
with broad instructions. `learnings.md:241-253` concerns this interpreter's
Codex profile, not every Codex session. The constraint is still documented in
`workflow_interpreter/profiles/codex.py:42-49` and exercised by
`tests/test_profiles_git_isolation.py:216`; do not delete it as obsolete just
because a normal interactive Codex session can commit with approval.

Keep useful lessons, but state the affected component/version, evidence source,
and when revalidation is needed. Do not turn a historical observation into a
universal rule. CLI claims were not re-probed in this review.

The detailed `model_copy` audit at `learnings.md:115-144` and test-rig lessons at
`:75-113` are useful evidence. Extract concise applicable guidance with source
pointers; retain incident narratives in topic references or historical reports.
Prefer durable symbols/tests over volatile line ranges and scratch-only links.
Replace machine-specific paths in active advice with repository-relative or
runtime-resolved descriptions. Updates still require the authority in AGENTS.md;
do not introduce automatic persistent-memory capture.

### 2. Make verification routing precise before shortening commands

`verification.md:36-38` still calls plugin harnesses the closest thing to CI,
despite the interpreter gate below. Remove this leftover framing. The plugin
submodule is uninitialized here; its commands cannot be verified from this
checkout and should carry that prerequisite.

The first pytest selector at `verification.md:52` includes tests marked `proc`
unless they also have `bd` or `live`; line 54 selects `proc` again. For example,
the Codex Git isolation test at `tests/test_profiles_git_isolation.py:216-223`
matches both selections. `scripts/verify-feature.sh:43-44` also has overlapping
selectors. This is a candidate for removing duplicate work, not permission to
change the gates without checking whether the second execution is intentional.

Retain the distinction between host checks and checks inside a vendor sandbox,
the `nested_sandbox` exclusion, and the requirement that a skip is not a pass.
Use a compact change-type → command → prerequisite table. Link to the existing
verifier where applicable; do not present it as equivalent to the full host gate.
No test-selection changes or full interpreter suite were run for this review.

### 3. Keep invariants as contracts, not another policy file

`invariants.md:5-18` repeats Git/path/submodule policy from AGENTS.md and embeds
a Beads remote URL. That URL exists in `.beads/config.yaml:68`; it is current
configuration, not a universal correctness invariant. Submodule wording also
omits AGENTS.md's explicit authorization exception. Consolidate these at their
existing owners instead of maintaining parallel policy.

Keep the canonical pinned-body contract at `invariants.md:25-32`: it agrees with
`workflow_interpreter/schema/loader.py:145-160`. Keep the skill-catalog contract
and its check pointer. Add short pointers to relevant accepted ADR contracts,
especially allowed-path semantics, pinned instructions, payload storage, and
deterministic routing; use `docs/adr/README.md` as the decision index rather than
copying the decisions into this file.

### 4. Remove redundant routing and overly strict terminology

`tools.md` mostly repeats coding, verification, delegation, and skill routing.
Its research description still implies a report on every use, while the current
research skill explicitly permits a direct answer. Move the few useful tool
facts to the map/index or their owning skill, then remove this file.

`tracking.md` adds little beyond `.beads/beads.md` and AGENTS.md. Point callers
directly to the existing owner, then remove it.

`CONTEXT.md:11-12` still limits harness anatomy to the vendor directories; include
the shared entry policy and repository context. The glossary omits interpreter
terms that recur in the schema and ADRs, such as activation, gate, pinned graph,
and carrier. Add only terms needed to distinguish real domain concepts, using
the implementation/spec as evidence. The `Idea doc` definition is tied to the
now-thin `idea-refine` alias; definitions should describe artifacts rather than
require one skill to produce them. Keep useful distinctions such as roadmap vs
plan and ledger vs casebook; remove blanket bans on ordinary words such as
“step”, “config”, or “report” outside those domain meanings.

## File-by-file disposition

| File | Words | Recommendation |
|---|---:|---|
| `repo-map.md` | 388 | Keep as the small startup orientation. Absorb the brief's purpose paragraph; trim plugin internals and duplicated policy. Flag unavailable submodules. |
| `docs-index.md` | 421 | Keep as the other startup file. Use short task triggers; group local guidance, component docs, and external references. Distinguish normative decisions from historical research. |
| `brief.md` | 294 | Merge its purpose into the map; drop the repeated directory list, stack, and AGENTS.md constraints. Update callers before removing. |
| `CONTEXT.md` | 478 | Keep and update domain coverage; narrow synonym restrictions and decouple definitions from skill names. |
| `coding-style.md` | 217 | Keep mostly intact. Ruff, strict mypy, optional ty, Pydantic, and uv are deliberate user choices, not expendable generic advice. Minor wording trims only. |
| `delegation.md` | 199 | Keep concise. Retain owned files, handoff inputs, integration responsibility, and optional workflow labels. Frame independent-review instructions explicitly as applying when that review is required. |
| `verification.md` | 498 | Keep; clarify component/environment routing and investigate duplicate pytest selection before changing it. Preserve meaningful safety checks. |
| `invariants.md` | 261 | Keep; remove duplicate policy/configuration, retain verified contracts, point to accepted ADRs. |
| `learnings.md` | 2,280 | Keep as a concise searchable index of scoped lessons, with longer incidents in conditional topic references. Do not preload or discard useful evidence merely to reduce words. |
| `tools.md` | 260 | Redistribute the few unique facts to owners and remove redundant routing. |
| `tracking.md` | 93 | Remove after routing callers directly to `.beads/beads.md`. |
| `adoption-report.md` | 584 | Archive under historical research; it already labels itself a snapshot. Preserve its original claims as evidence. |
| `code-intel.md` | 154 | Archive the old assessment; reassess only when code-intelligence tooling is an actual decision. |

## Proposed end state

Eight active entry files: `repo-map.md`, `docs-index.md`, `CONTEXT.md`,
`coding-style.md`, `delegation.md`, `verification.md`, `invariants.md`, and
`learnings.md`. Additional topic references are conditional, not more startup
reads. Keep the two existing startup reads and the user's removed sections
removed. No hooks, automatic imports, new tool dependencies, or forced workflows
are needed for this cleanup.

Suggested order: clarify verification/invariant/learning authority; consolidate
orientation and routing; archive historical assessments; update glossary gaps.
Preserve source references and update live callers whenever a file moves or is
removed. The external installer/template migration remains a separate documented
distribution task in `docs/usage/mvp-plugin.md`.

## Validation and limits

Inspected every context file, current loading pointers, the existing verifier,
selected profile and canonicalization code, related tests, and the ADR index.
Verified the migration commit's exact path scope and the separate two-record
tracking commit. Existing migration checks were reported in its completed Bead;
this review does not claim a new full-suite run or a model-behavior evaluation.
No `.repo-context/` source files were edited during the review.
