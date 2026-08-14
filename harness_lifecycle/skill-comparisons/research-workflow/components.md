# Research Workflow — Component Inventory

Level 3 of the comparison in `README.md`. Every component is cited
`file:line`. Paths are relative to each skill's own directory unless prefixed.

Skill roots:
- `research` → `reference_harnesses/mattpocock_skills/skills/engineering/research/`
- `source-driven-development` (SDD) → `reference_harnesses/agent-skills/skills/source-driven-development/`
- `docs-researcher` → `.claude/agents/docs-researcher.md`
- `deep-research` → `.codex/skills/deep-research/`

## Component inventory

### `research` (mattpocock) — 17 lines total across 2 files

| # | Component | Cite |
|---|---|---|
| R1 | Model-invocable trigger: topic research, doc/API fact gathering, or delegating reading legwork | `SKILL.md:3` |
| R2 | **Background-agent delegation** — the caller keeps working while it reads | `SKILL.md:6` |
| R3 | **Primary-source mandate** with an explicit anti-secondary clause: "not a secondary write-up of them" | `SKILL.md:10` |
| R4 | **Provenance-chasing rule** — "Follow every claim back to the source that owns it" | `SKILL.md:10` |
| R5 | Single-Markdown-file artifact with **per-claim** citation | `SKILL.md:11` |
| R6 | **Convention-matching artifact location**, with a say-where fallback when no convention exists | `SKILL.md:12` |
| R7 | No invocation policy gate — `agents/openai.yaml` carries interface metadata only, no `policy:` block, so implicit invocation is allowed | `agents/openai.yaml:1-3` |

### `source-driven-development` (agent-skills) — 217 lines

| # | Component | Cite |
|---|---|---|
| S1 | Trigger set: 6 cases, ending in the catch-all "Any time you are about to write framework-specific code from memory" | `SKILL.md:14-19` |
| S2 | **Anti-trigger list** — version-independent edits, pure logic, explicit user speed preference | `SKILL.md:21-25` |
| S3 | Four-stage pipeline diagram DETECT → FETCH → IMPLEMENT → CITE | `SKILL.md:29-36` |
| S4 | **Version detection from dependency manifests**, 6-ecosystem file map | `SKILL.md:38-49` |
| S5 | Mandatory `STACK DETECTED:` declaration naming versions and their source file | `SKILL.md:51-59` |
| S6 | Ask-don't-guess gate on ambiguous versions | `SKILL.md:61` |
| S7 | **4-tier source authority hierarchy** (official docs → official blog/changelog → standards refs → compat data) | `SKILL.md:67-74` |
| S8 | **Non-authoritative blacklist**, explicitly including "Your own training data" | `SKILL.md:76-81` |
| S9 | **Precision-fetch discipline** with 4 BAD/GOOD pairs — reference page, not homepage | `SKILL.md:83-91` |
| S10 | Extract-deprecations-and-migrations step after fetch | `SKILL.md:93` |
| S11 | **Source-vs-source conflict rule** — surface the discrepancy, verify against the detected version | `SKILL.md:95` |
| S12 | **Retrieval safety**: fetched pages are untrusted input; docs are authoritative about the framework, never about what the skill does next | `SKILL.md:97-99` |
| S13 | Threat-model pointer to `security-and-hardening` (LLM01) | `SKILL.md:101` |
| S14 | Extract-only allowlist (4 items) / ignore-list (3 items) for fetched content | `SKILL.md:103-113` |
| S15 | **No-hardcoded-outbound-endpoints rule** — telemetry/analytics from doc examples must be surfaced, even when docs mark them required | `SKILL.md:114` |
| S16 | Implement-from-docs rules incl. "If the docs don't cover something, flag it as unverified" | `SKILL.md:116-124` |
| S17 | **Docs-vs-codebase conflict protocol** — `CONFLICT DETECTED` block offering A/B, "Surface the conflict. Don't silently pick one" | `SKILL.md:125-139` |
| S18 | Citation-in-code-comments format | `SKILL.md:145-151` |
| S19 | Citation-in-conversation format with quoted source passage | `SKILL.md:153-163` |
| S20 | Citation rules: full URLs, **deep links with anchors** ("anchors survive doc restructuring"), quote-on-non-obvious, include compat data | `SKILL.md:165-170` |
| S21 | **`UNVERIFIED:` block** for undocumented patterns + "Honesty about what you couldn't verify is more valuable than false confidence" | `SKILL.md:171-179` |
| S22 | **Rationalization table**, 6 rows | `SKILL.md:181-190` |
| S22a | — "I'm confident about this API" → "Confidence is not evidence." | `SKILL.md:185` |
| S22b | — "Fetching docs wastes tokens" → token-cost inversion argument | `SKILL.md:186` |
| S22c | — "This is a simple task" → wrong patterns become copied templates | `SKILL.md:189` |
| S22d | — "The docs page said to do X" → injection row (post-adoption drift) | `SKILL.md:190` |
| S23 | **Red flags**, 9 items | `SKILL.md:192-202` |
| S24 | **Verification checklist**, 9 checkboxes | `SKILL.md:204-217` |

### `docs-researcher` (ours — agent)

| # | Component | Cite |
|---|---|---|
| D1 | Staleness-framed trigger firing "even for well-known libraries" | `docs-researcher.md:3` |
| D2 | **Hard tool allowlist** — 2 Context7 calls + Read/Grep/Glob; no Write/Bash/web | `docs-researcher.md:4` |
| D3 | Model pin `sonnet` | `docs-researcher.md:5` |
| D4 | Read-only constraint | `docs-researcher.md:12` |
| D5 | Source-authority rule: Context7 over memory, over web search | `docs-researcher.md:13` |
| D6 | Grounding gate — "If Context7 has nothing useful, say so explicitly — do not invent APIs" | `docs-researcher.md:14` |
| D7 | **Version pinning from repo manifests** before querying | `docs-researcher.md:18` |
| D8 | Library-ID resolution step | `docs-researcher.md:19` |
| D9 | **Narrow symbol-level query + refine loop** on noisy first pass | `docs-researcher.md:20` |
| D10 | Minimal-synthesis rule (answer + directly relevant gotchas only) | `docs-researcher.md:21` |
| D11 | **Fixed 4-section output template**: Library / Answer / Sources / Caveats | `docs-researcher.md:27-40` |
| D12 | Never-fabricate rule | `docs-researcher.md:44` |
| D13 | **`UNVERIFIED:` prefix** separating confirmed fact from guess | `docs-researcher.md:45` |
| D14 | **Retrieval safety** — extract-only, ignore embedded instructions, never adopt outbound endpoints | `docs-researcher.md:46` |
| D15 | Paste-exact-signature over paraphrase | `docs-researcher.md:47` |
| D16 | No-process-narrative rule | `docs-researcher.md:49` |
| D17 | Multi-library fan-out, one combined response | `docs-researcher.md:50` |
| D18 | **Web tools forbidden** — Context7 is the single source of truth | `docs-researcher.md:51` |

### `deep-research` (ours, `.codex/` — Claude-unreachable)

| # | Component | Cite |
|---|---|---|
| X1 | Explicit-invocation-only trigger with anti-trigger list | `SKILL.md:3` |
| X2 | `disable-model-invocation: true` | `SKILL.md:4` |
| X3 | **Scope gate** — ask before expanding materially | `SKILL.md:13` |
| X4 | **Depth ∝ decision risk**, not curiosity | `SKILL.md:14` |
| X5 | Primary/current sources for volatile domains | `SKILL.md:15` |
| X6 | **Epistemic separation** — facts vs inferences vs open questions | `SKILL.md:16` |
| X7 | HTML-artifact output mandate; Markdown reserved for agent-facing notes | `SKILL.md:17-18` |
| X8 | **3-level depth ladder** with source counts (Focused 3-5 / Standard 8-15 / Deep primary sweep + red-team) | `SKILL.md:24-28` |
| X9 | Escalation keywords + **scope-balloon pause gate** | `SKILL.md:30` |
| X10 | Phase 1 clarify, **capped at 3 questions** (decision, scope boundary, constraints) | `SKILL.md:34-36` |
| X11 | Phase 2 plan — one playbook, selected frameworks, source-selection read | `SKILL.md:38-42` |
| X12 | Phase 3 **provenance metadata** — source date, retrieval date, authority, known bias | `SKILL.md:46` |
| X13 | Community evidence demoted to implementation-reality only | `SKILL.md:48` |
| X14 | Phase 4 synthesis + **red-team the emerging recommendation** | `SKILL.md:50-53` |
| X15 | Phase 5 **12 required artifact sections** | `SKILL.md:57` |
| X16 | Conditional reference-routing table (always / selective / on-demand) | `SKILL.md:64-70` |
| X17 | Do-Not list, 7 prohibitions incl. "Do not bury uncertainty" | `SKILL.md:78-84` |
| X18 | **6 domain playbooks**, one-primary selection rule | `references/playbooks.md:3-87` |
| X19 | — Developer-Tooling/Architecture playbook (plane separation) | `references/playbooks.md:47-59` |
| X20 | **Claim-typed source-weight matrix**, 6 areas × 3 tiers | `references/source-selection.md:7-14` |
| X21 | Recency rule — current-state claims need current sources | `references/source-selection.md:18` |
| X22 | High-stakes primary-or-explicit-uncertainty rule | `references/source-selection.md:19` |
| X23 | **6-way conflict-explanation taxonomy** (definition/date/incentive/geography/segment/implementation mismatch) | `references/source-selection.md:21` |
| X24 | Citation + **retrieval dates for volatile pages** | `references/source-selection.md:22` |
| X25 | **6 red-flag source detectors** | `references/source-selection.md:26-31` |
| X26 | **12 analytic frameworks** with a "pick 1-3" budget | `references/frameworks.md:3-109` |
| X27 | — **Source Confidence Ladder, mandatory in every report** | `references/frameworks.md:111-119` |
| X28 | **Synthesis pipeline gate** — run after collection, before writing | `references/synthesis-engine.md:3` |
| X29 | Stage 1 **Claim Table**, 6 fields per claim | `references/synthesis-engine.md:5-15` |
| X30 | Stage 2 Pattern Scan, 5 patterns incl. **Silence** (expected evidence missing) | `references/synthesis-engine.md:17-24` |
| X31 | Stage 3 fact→insight formula + **"so what?" cut test** | `references/synthesis-engine.md:26-33` |
| X32 | Stage 4 Red Team — strongest counterargument must ship in the artifact | `references/synthesis-engine.md:35-44` |
| X33 | Stage 5 confidence calibration, 4 levels | `references/synthesis-engine.md:46-52` |
| X34 | Stage 6 **fixed 7-part narrative order** | `references/synthesis-engine.md:54-63` |
| X35 | 5 weak-vs-strong exemplar pairs (calibration only) | `references/examples.md:3-43` |
| X36 | **4 Quick Tests** (replacement / decision / source / scope) | `references/examples.md:45-51` |
| X37 | Runtime policy gate — `allow_implicit_invocation: false` (second gate alongside X2) | `agents/openai.yaml:5-6` |

## Cross-skill matrix

`✓` present · `~` variant (differs in mechanism or strength) · `—` absent

| Component | `research` | SDD | `docs-researcher` | `deep-research` |
|---|:--:|:--:|:--:|:--:|
| Async/background delegation | ✓ R2 | — | ~ D2 | — |
| Primary-source mandate | ✓ R3 | ✓ S7 | ~ D5 | ✓ X5 |
| Source authority tiering | — | ✓ S7 | ~ D5 | ✓ X20 |
| Non-authoritative blacklist | ~ R3 | ✓ S8 | ~ D18 | ✓ X25 |
| Version detection from manifests | — | ✓ S4/S5 | ✓ D7 | — |
| Precision-fetch (page, not site) | — | ✓ S9 | ✓ D9 | — |
| Retrieval safety / untrusted fetched content | — | ✓ S12-S15 | ✓ D14 | — |
| Per-claim citation | ✓ R5 | ✓ S18/S19 | ~ D11 | ✓ X24 |
| Citation formatting rules (URLs/anchors/dates) | — | ✓ S20 | — | ~ X24 |
| Uncertainty marking | — | ✓ S21 | ✓ D13 | ✓ X27 |
| Epistemic separation (fact/inference/open) | — | — | ~ D11 | ✓ X6 |
| Durable file artifact | ✓ R5 | — | — | ✓ X7 |
| Artifact location convention | ✓ R6 | — | — | ~ X7 |
| Fixed artifact section template | — | — | ✓ D11 | ✓ X15/X34 |
| Source-vs-source conflict handling | — | ✓ S11 | — | ✓ X23 |
| **Docs-vs-codebase conflict protocol** | — | ✓ S17 | — | — |
| Couples research to writing code | — | ✓ S16 | — | — |
| Provenance metadata (dates, authority, bias) | — | ~ S20 | — | ✓ X12 |
| Depth ladder / effort calibration | — | ~ S2 | — | ✓ X8 |
| Scope gate | — | ~ S2 | — | ✓ X3/X9 |
| Clarifying-question cap | — | ~ S6 | — | ✓ X10 |
| Domain playbooks | — | — | — | ✓ X18 |
| Analytic frameworks | — | — | — | ✓ X26 |
| Synthesis pipeline / claim table | — | — | — | ✓ X28/X29 |
| Red-team gate | — | — | — | ✓ X14/X32 |
| Rationalization table | — | ✓ S22 | — | — |
| Red flags | — | ✓ S23 | — | ✓ X25 |
| Verification checklist | — | ✓ S24 | — | ✓ X36 |
| Invocation gating | — | — | ~ D2 | ✓ X2/X37 |
| Tool-level constraint enforcement | — | — | ✓ D2/D18 | — |

## Shared-component differences

**Primary-source mandate** (`~` on `docs-researcher`). SDD defines authority by
a 4-tier ladder topped by first-party documentation (`SKILL.md:67-74`) and
explicitly disqualifies aggregated or AI-generated summaries (`:76-81`).
`research` defines it by provenance-chasing — follow the claim to the source
that owns it (`SKILL.md:10`). `docs-researcher` defines it by *tool binding*:
Context7 is authoritative because it is the only tool available
(`docs-researcher.md:13`, `:51`). This is the sharpest difference in the family.
Context7 is a documentation **aggregator**; by SDD's own hierarchy it is a
secondary write-up of the official docs, and `docs-researcher` is forbidden from
reaching the primary (`:51`). The binding buys determinism and injection
resistance at the cost of authority rank. **Stronger depends on the job:**
`docs-researcher`'s mechanism is stronger for a bounded API fact (it cannot
wander into a blog post because it cannot reach one); SDD's is stronger for
anything where the aggregator may lag the source, which is precisely the
fast-moving-API case both skills exist to defend against.

**Retrieval safety** (`✓` in SDD and `docs-researcher`, different shape). SDD
spends 18 lines (`SKILL.md:97-114`) plus a rationalization row (`:190`), a red
flag (`:202`) and a checkbox (`:216`), and separates extraction hygiene from the
threat model by pointing at another skill (`:101`). `docs-researcher` compresses
the same substance into one sentence (`:46`) covering extract-only,
ignore-embedded-directives, and no-outbound-endpoints. **Ours is stronger per
line and materially equivalent in effect**, and it has a structural advantage
SDD cannot match: the agent has no WebFetch and no Bash (`:4`), so the attack
surface is one MCP channel rather than the open web. What ours lacks is the
teaching layer — the rationalization row that tells an agent *why* a docs page's
instruction is not an instruction. That matters only for a skill an agent must
be argued out of skipping, which is SDD's situation and not ours.

**Uncertainty marking** (`✓` in three, three mechanisms). SDD uses a block-form
`UNVERIFIED:` disclosure with a stated principle — honesty beats false
confidence (`SKILL.md:171-179`) — and pointedly rejects hedging as the worst
option (`:188`). `docs-researcher` uses an inline `UNVERIFIED:` **prefix** at
claim granularity (`:45`) plus a Caveats section (`:38-39`). `deep-research`
uses a **4-level calibrated ladder** mandatory in every report
(`frameworks.md:111-119`) with defined evidentiary conditions per level.
**`deep-research`'s is strongest** — it is the only one that forces a
*positive* confidence statement on confirmed claims rather than only flagging
unconfirmed ones, so a reader can distinguish "verified and recent" from
"verified in 2023". Ours is strongest per token and the only one operating at
claim granularity inline.

**Per-claim citation** (`~` on `docs-researcher`). `research` binds a citation
to each claim inside the artifact (`SKILL.md:11`); SDD binds it to each
generated code decision, in the code itself (`:145-151`); `deep-research` binds
it in the artifact with retrieval dates (`source-selection.md:22`).
`docs-researcher` emits a **trailing Sources list** (`:34-36`) covering the
answer as a whole. **The trailing list is the weakest** of the four: a
multi-claim answer cannot be audited claim-by-claim, and the caller cannot tell
which of three listed sections supports the one line they doubt. This is a
one-line fix and the cheapest quality gain available in this family.

**Conflict handling** (three different conflicts, only one skill covers the
third). SDD handles *source vs source* (`:95`) and, uniquely, *docs vs existing
codebase* as a user-facing A/B stop (`:125-139`). `deep-research` handles
*source vs source* far more precisely, with a taxonomy that explains **why**
sources disagree — definition, date, incentive, geography, segment, or
implementation mismatch (`source-selection.md:21`) — which converts a conflict
from an obstacle into a finding. **`deep-research`'s is stronger for research;
SDD's is the only one that exists for building.** Nothing in our harness has
SDD's docs-vs-codebase stop, and its absence is the concrete failure mode: an
agent fetches correct modern docs, then silently rewrites an established
codebase pattern, satisfying the docs and breaking consistency. Our
`docs-researcher` structurally cannot own this — it is read-only (`:12`) and
never sees the write.

**Effort calibration** (`~` on SDD, `✓` on `deep-research`). SDD calibrates
*binary*: an anti-trigger list that turns the skill off (`:21-25`).
`deep-research` calibrates *continuous*: a 3-level ladder with source counts
tied to decision risk (`SKILL.md:24-28`, `:13`), plus a pause gate when scope
balloons (`:30`). `research` and `docs-researcher` have **no calibration at
all** — every invocation gets the same treatment. Combined with `research`'s
loose model-invocable trigger (`agents/openai.yaml:1-3`, no policy block), that
is the specific over-fire risk in adopting `research` as written: a
background agent spawned to answer something one Context7 call resolves.

**Invocation gating** (`✓` only in `deep-research`). `deep-research` is gated
twice, at skill and runtime layers (`SKILL.md:4`, `agents/openai.yaml:5-6`).
`docs-researcher` is gated *structurally* rather than declaratively — it is an
agent, so it only runs when dispatched (`~`). `research` and SDD are both
freely model-invocable. **`deep-research`'s double gate is the strongest**, and
it is the correct pairing for an expensive protocol; the tension is that it is
gated so thoroughly, and routed so little, that it is currently unreachable
(see `README.md`).

**Artifact durability.** `research` (`SKILL.md:11-12`) and `deep-research`
(`SKILL.md:17`) produce files that outlive the session; SDD produces citations
embedded in shipped code (`:145-151`), which is durable by a different route —
the comment survives in git. `docs-researcher` produces **nothing durable**: the
answer lives in the caller's context and dies with it, so the same lookup
recurs next session. Of the four, `research`'s mechanism is the most portable —
it defers location to repo convention (`:12`) rather than mandating a path, and
our repo already has the convention it would bind to (`CLAUDE.md:19`,
`docs/research/`). `deep-research`'s HTML mandate is the least portable here,
conflicting with this repo's Markdown-native preference for agent-consumed and
repo-committed files.
