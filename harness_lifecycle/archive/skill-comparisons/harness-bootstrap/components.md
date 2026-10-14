# Harness Bootstrap — Level 3: Component Inventory

Scope: skill discovery/routing, repo bootstrap configuration, and umbrella
packaging. Every claim cites `file:line`. Paths are repo-relative; reference
paths are under `reference_harnesses/`.

Short names used in the matrix:

| Short | Path |
|---|---|
| `UAS` | `agent-skills/skills/using-agent-skills/SKILL.md` |
| `AS-hook` | `agent-skills/hooks/session-start.sh` + `agent-skills/hooks/hooks.json` |
| `USP` | `superpowers/skills/using-superpowers/SKILL.md` |
| `SP-hook` | `superpowers/hooks/session-start` + `superpowers/hooks/hooks.json` |
| `AM` | `mattpocock_skills/skills/engineering/ask-matt/SKILL.md` + `PHASE-BOUNDARIES.md` |
| `SMPS` | `mattpocock_skills/skills/engineering/setup-matt-pocock-skills/SKILL.md` |
| `SPC` | `mattpocock_skills/skills/misc/setup-pre-commit/SKILL.md` |
| `STDM` | `mattpocock_skills/skills/in-progress/setup-ts-deep-modules/SKILL.md` |
| `SX` | `mattpocock_skills/skills/misc/scaffold-exercises/SKILL.md` |
| `OURS` | `CLAUDE.md`, `AGENTS.md`, `.claude/commands/adopt.md`, `.claude/skills/*` |

---

## 1. Component inventory

### UAS — `using-agent-skills` (191 lines, single file)

| # | Component | Citation | What it does to agent behaviour |
|---|---|---|---|
| U1 | Situation→skill decision tree, 21 branches, ASCII | `agent-skills/skills/using-agent-skills/SKILL.md:16-42` | Maps a task shape ("Something broke?", "UI work?") onto a named skill |
| U2 | "Core Operating Behaviors … non-negotiable" framing | `…SKILL.md:44-46` | Declares the following six rules as always-on, cross-skill |
| U3 | Assumption-surfacing with a literal output template | `…SKILL.md:48-58` | Forces `ASSUMPTIONS I'M MAKING: … → Correct me now` before non-trivial work |
| U4 | Confusion protocol (STOP → name → present → wait) | `…SKILL.md:62-72` | Four ordered steps, with a bad/good example pair |
| U5 | Anti-sycophancy / push-back rule, quantification demand | `…SKILL.md:74-83` | "quantify when possible — 'this adds ~200ms latency' not 'this might be slower'" |
| U6 | Simplicity gate as three pre-finish questions | `…SKILL.md:85-94` | "If you build 1000 lines and 100 would suffice, you have failed" |
| U7 | Scope discipline as a five-item Do-NOT list | `…SKILL.md:96-107` | Bans orthogonal refactors, comment deletion, unrequested features |
| U8 | Verification gate + pointer to a shared Definition of Done | `…SKILL.md:109-113` | Local per-skill check plus one project-wide bar |
| U9 | Failure-mode enumeration, 10 numbered items | `…SKILL.md:115-128` | Named anti-patterns ("plowing ahead when lost") |
| U10 | Skill Rules: check-before-starting; workflows-not-suggestions; multiple-skills-compose; default-to-spec | `…SKILL.md:130-138` | The actual compliance clause (`:132`) |
| U11 | 16-step canonical lifecycle sequence | `…SKILL.md:140-163` | Prescribes a default order for a full feature |
| U12 | Quick-reference table, 24 rows = their whole catalog | `…SKILL.md:165-191` | Phase / skill / one-line summary enumeration |

### AS-hook — agent-skills SessionStart

| # | Component | Citation | Behaviour |
|---|---|---|---|
| A1 | Injects the entire meta-skill file into every session | `agent-skills/hooks/session-start.sh:3`, `:14-21` | `cat`s all 191 lines into a `priority: IMPORTANT` message |
| A2 | Hard `jq` dependency with graceful INFO degrade | `agent-skills/hooks/session-start.sh:9-12` | Without `jq` the hook no-ops and says so |
| A3 | Missing-file fallback message | `agent-skills/hooks/session-start.sh:22-24` | Never hard-fails the session |
| A4 | SessionStart registration with **no matcher** | `agent-skills/hooks/hooks.json:3-12` | Fires on every SessionStart event indiscriminately |
| A5 | Dual path resolution (plugin root → project `.claude/hooks`) | `agent-skills/hooks/hooks.json:8` | Works installed-as-plugin or vendored-in-repo |

### USP — `using-superpowers` (62 lines + 4 platform references, 203 total)

| # | Component | Citation | Behaviour |
|---|---|---|---|
| S1 | `<SUBAGENT-STOP>` exemption | `superpowers/skills/using-superpowers/SKILL.md:6-8` | Dispatched subagents skip the whole bootstrap |
| S2 | 1%-threshold mandatory-invocation clause | `…SKILL.md:10-16` | "even a 1% chance a skill might apply … you ABSOLUTELY MUST invoke" |
| S3 | Invocation-before-anything ordering rule | `…SKILL.md:20` | Skill check precedes clarifying questions, file reads, exploration |
| S4 | Plan-mode precondition | `…SKILL.md:22` | Brainstorming must run before plan mode |
| S5 | Announce + todo-per-checklist-item | `…SKILL.md:24` | Externalises compliance into visible artefacts |
| S6 | Skill-priority ordering (process before implementation) | `…SKILL.md:26-31` | Two worked examples resolve multi-skill conflicts |
| S7 | Rationalization / Red-Flags table, 12 thought→reality rows | `…SKILL.md:33-50` | Pre-refutes the specific excuses for skipping a skill |
| S8 | Platform-adaptation indirection | `…SKILL.md:52-58` → `references/codex-tools.md`, `pi-tools.md`, `antigravity-tools.md` | Only the matching harness's file is read |
| S9 | Explicit precedence ladder | `…SKILL.md:62` | user instructions > skills > default behaviour |
| S10 | Harness-specific tool guidance (e.g. Codex worktree detection) | `superpowers/skills/using-superpowers/references/codex-tools.md:1-10`, `:13-27` | Conditional, not always loaded |

### SP-hook — superpowers SessionStart

| # | Component | Citation | Behaviour |
|---|---|---|---|
| P1 | Injects full `using-superpowers` body | `superpowers/hooks/session-start:11`, `:27` | Wrapped in `<EXTREMELY_IMPORTANT>` |
| P2 | Zero-dependency JSON escaping in pure bash | `superpowers/hooks/session-start:16-24` | No `jq`; five parameter-substitution passes |
| P3 | Three-way platform output shape switch | `superpowers/hooks/session-start:38-47` | Cursor / Claude Code / SDK-standard, explicitly avoiding double-injection |
| P4 | Matcher `startup\|clear\|compact` | `superpowers/hooks/hooks.json:5` | **Re-injects after `/clear` and `/compact`** |
| P5 | `async: false` | `superpowers/hooks/hooks.json:11` | Blocks until context is in place |

### AM — `ask-matt` (90 + 55 lines)

| # | Component | Citation | Behaviour |
|---|---|---|---|
| M1 | `disable-model-invocation: true` | `mattpocock_skills/skills/engineering/ask-matt/SKILL.md:4` | **User-invoked only** — never auto-fires |
| M2 | Flow vocabulary (main flow / on-ramp / standalone / vocabulary layer) | `…ask-matt/SKILL.md:11` | Gives the catalog a shape, not just a list |
| M3 | Main flow, idea→ship, with two decision branches | `…ask-matt/SKILL.md:13-26` | Branch on "settle in conversation?" and "multi-session?" |
| M4 | Near-duplicate disambiguation rule | `…ask-matt/SKILL.md:17`, `:77-78` | `grill-with-docs` vs `grill-me` decided by *working directory present*, stated twice |
| M5 | Context-hygiene rule + smart-zone budget (~150k) | `…ask-matt/SKILL.md:28-32` | One unbroken window through `/to-tickets` |
| M6 | On-ramps with negative scope guards | `…ask-matt/SKILL.md:34-46` | e.g. `:40` "don't triage" tickets `/to-tickets` produced; `:44` never use wayfinder for a well-scoped feature |
| M7 | Hand-off contract between skills | `…ask-matt/SKILL.md:46`, `:42`, `:52` | wayfinder→to-spec; diagnosing-bugs→improve-codebase-architecture; improve-architecture→grill-with-docs |
| M8 | Vocabulary-layer distinction | `…ask-matt/SKILL.md:54-59` | Two skills that run *beneath* others |
| M9 | Phase-boundary five-option summary | `…ask-matt/SKILL.md:61-71` | Continue / clear / handoff / subagent / compact |
| M10 | Ordered phase-boundary decision tree, first-yes-wins | `PHASE-BOUNDARIES.md:17-40` | Five questions in cost order; `/compact` deliberately last |
| M11 | Primary-vs-secondary-source cost model | `PHASE-BOUNDARIES.md:42-51` | Table justifying why "Continue" is ruled out first |
| M12 | Explicit judgement-call disclaimer | `PHASE-BOUNDARIES.md:53-55` | "the same boundary can go two ways on two days" |
| M13 | Router-freshness maintenance obligation | `mattpocock_skills/CLAUDE.md` (Ask-Matt paragraph) | "a stale one it still routes to, is a router that lies" |
| M14 | Precondition pointer to the setup skill | `…ask-matt/SKILL.md:88-90` | Bootstrap runs before first engineering flow |

### SMPS — `setup-matt-pocock-skills` (116 lines + 5 seed templates)

| # | Component | Citation | Behaviour |
|---|---|---|---|
| B1 | `disable-model-invocation: true`, run-once framing | `…setup-matt-pocock-skills/SKILL.md:4`, `:3` | Human-triggered one-time bootstrap |
| B2 | "prompt-driven skill, not a deterministic script" | `…SKILL.md:15` | Explore → present → confirm → write |
| B3 | Explore checklist of 8 concrete probes | `…SKILL.md:19-31` | git remote, CLAUDE.md/AGENTS.md, CONTEXT.md, docs/adr, .scratch, monorepo signals |
| B4 | Conditional-section suppression | `…SKILL.md:36`, `:51`, `:59-61` | Skip a question exploration already answered |
| B5 | Lead-with-recommendation questioning | `…SKILL.md:34-36` | One section, one answer; accept in a word |
| B6 | Draft-before-write confirmation gate | `…SKILL.md:63-70` | User edits the draft before anything is written |
| B7 | Instruction-file selection + no-duplicate rule | `…SKILL.md:74-82` | CLAUDE.md else AGENTS.md; never create the other; update the block **in place** |
| B8 | Seed templates per branch | `…SKILL.md:104-110` + `issue-tracker-{github,gitlab,local}.md`, `triage-labels.md`, `domain.md` | Branch-specific scaffold content |
| B9 | Re-run guidance / exit message | `…SKILL.md:114-116` | Edit the docs directly; re-run only to switch trackers |

### SPC / STDM / SX — stack-specific setup family

| # | Component | Citation | Behaviour |
|---|---|---|---|
| C1 | Package-manager detection from lockfile | `…setup-pre-commit/SKILL.md:17-19`; `…setup-ts-deep-modules/SKILL.md:41` | npm/pnpm/yarn/bun switch |
| C2 | Adapt-to-missing-scripts rule | `…setup-pre-commit/SKILL.md:47` | Omit typecheck/test lines if absent, and say so |
| C3 | Post-install verification checklist | `…setup-pre-commit/SKILL.md:73-79` | Five checkboxes plus a live run |
| C4 | Commit-as-smoke-test | `…setup-pre-commit/SKILL.md:81-85` | The commit exercises the hook it just installed |
| C5 | Never-overwrite-existing-config, merge instead | `…setup-ts-deep-modules/SKILL.md:43` | Merge rules in and report what was added |
| C6 | **Prove-the-rules-bite** pass→fail→pass loop | `…setup-ts-deep-modules/SKILL.md:79-87` | "a config that doesn't fail on a violation is worthless"; deliberately introduce a violation, observe the failure, revert |
| C7 | Fold new check into the repo's umbrella command | `…setup-ts-deep-modules/SKILL.md:59-65` | Otherwise tell the user to wire CI |
| C8 | Document-the-convention + **context pointer** into CLAUDE.md/AGENTS.md | `…setup-ts-deep-modules/SKILL.md:89-95` | "This is what makes an agent discover the boundary rule instead of tripping over it" |
| C9 | Lint-rule summary as the scaffold's acceptance spec | `…scaffold-exercises/SKILL.md:54-63` | Generate → run linter → iterate |
| C10 | `git mv` for renames to preserve history | `…scaffold-exercises/SKILL.md:66-77` | Course-repo-specific mechanic |

### OURS — our counterpart surface

| # | Component | Citation | Behaviour |
|---|---|---|---|
| O1 | Read Order — 6 ranked documents | `CLAUDE.md` Read Order section | Tells the agent what to read, not which skill to run |
| O2 | Working Mode — small/standard/deep classification | `CLAUDE.md` Working Mode section | Ceremony matched to scope |
| O3 | Process Before Execution — 6 situation→discipline lines | `CLAUDE.md` Process Before Execution section | The closest thing we have to U1: "bug, failure, or confusing behavior: systematic-debugging before proposing fixes" |
| O4 | Execution routing to the execution skill + entry commands | `CLAUDE.md` Execution section | Names `/phase-execution N`, `/run-phases` |
| O5 | Tool/subagent routing (`docs-researcher`, brainstorming) | `CLAUDE.md` Tools & Subagents section | Narrow, tool-level |
| O6 | Verification gate, 5 numbered steps | `CLAUDE.md` Verification section | Counterpart to U8 |
| O7 | AK Guidelines — 12 numbered behavioural rules | `.claude/rules/core/03-ak-guidelines.md` | Counterpart to U3–U9, always loaded |
| O8 | Inline cross-references inside skill descriptions | e.g. `.claude/skills/brainstorming/SKILL.md:3` ("To open up a raw idea first, use idea-refine; to interrogate a plan that is already written, use grill-me") | Routing embedded in the description that is already indexed — zero always-on cost |
| O9 | One-time repo bootstrap: explore → authority order → write overlay → present report | `.claude/commands/adopt.md:11`, `:15-21`, `:24-30`, `:31-45`, `:48` | Direct counterpart to SMPS |
| O10 | Do-not-invent-verification rule in bootstrap | `.claude/commands/adopt.md:70-72` | Keeps the gate structural until real code/CI exist |
| O11 | Bootstrap capability assessment without auto-enabling | `.claude/commands/adopt.md:50-63` | Trust decision left to the user |
| O12 | No catalog enumeration anywhere | (absent) | Nothing in the repo lists the 34 skills with when-to-use |
| O13 | No mandatory skill-check clause | (absent) | Nothing states "check for a skill before acting" |
| O14 | SessionStart injection channel exists, but carries **no** routing text | `.claude/settings.json:25-43` registers `bd-prime.sh` and `harness-staleness-nudge.sh`, both `matcher: ""`; `.claude/hooks/bd-prime.sh:25` injects `bd prime --hook-json` (dynamic work state) | The mechanism A1/P1 use is already wired here — what is absent is skill-routing content, not the channel |
| O15 | Always-on context budget | `CLAUDE.md` 95 + `AGENTS.md` 94 + `.claude/rules/**` 268 = **457 lines**, plus 34 skill descriptions and `bd prime` output | Baseline against which any injected bootstrap is measured |

---

## 2. Cross-skill matrix

Rows are the merged component list. `✓` present, `~` variant, `—` absent.

| Component | UAS | AS-hook | USP | SP-hook | AM | SMPS | SPC/STDM/SX | OURS |
|---|---|---|---|---|---|---|---|---|
| Situation→skill routing map | ✓ U1 | — | — | — | ✓ M3/M6 | — | — | ~ O3 |
| Full catalog enumeration | ✓ U12 | — | — | — | ✓ M2 | — | — | — O12 |
| Near-duplicate disambiguation rule | — | — | — | — | ✓ M4 | — | — | ~ O8 |
| Inter-skill hand-off contracts | ~ U11 | — | ~ S6 | — | ✓ M7 | — | — | ~ O4 |
| Mandatory skill-check clause | ~ U10 | — | ✓ S2/S3 | — | — | — | — | — O13 |
| Rationalization pre-refutation table | — | — | ✓ S7 | — | — | — | — | — |
| Compliance externalisation (announce/todo) | — | — | ✓ S5 | — | — | — | — | — |
| Subagent exemption | — | — | ✓ S1 | — | — | — | — | — |
| Precedence ladder (user > skill > default) | — | — | ✓ S9 | — | — | — | — | ~ CLAUDE.md preamble |
| Always-on session injection | — | ✓ A1 | — | ✓ P1 | — | — | — | — O14 |
| Re-injection after clear/compact | — | — A4 | — | ✓ P4 | — | — | — | — |
| Zero-dependency hook implementation | — | — A2 | — | ✓ P2 | — | — | — | n/a |
| Multi-harness output adaptation | — | — | ✓ S8/S10 | ✓ P3 | — | — | — | ~ `.codex/` mirror |
| Generic behavioural rules (assumptions, simplicity, scope, push-back) | ✓ U3-U7,U9 | — | — | — | — | — | — | ✓ O7 |
| Verification gate | ✓ U8 | — | — | — | — | — | ~ C3 | ✓ O6 |
| Context/phase-boundary decision procedure | — | — | — | — | ✓ M9-M12 | — | — | — |
| Canonical lifecycle sequence | ✓ U11 | — | — | — | ~ M3 | — | — | ~ O4 |
| Router-freshness obligation | — | — | — | — | ✓ M13 | — | — | — |
| User-invoked-only gating | — | — | — | — | ✓ M1 | ✓ B1 | ~ STDM:4 | ✓ (several skills carry `disable-model-invocation`) |
| One-time repo bootstrap flow | — | — | — | — | ~ M14 | ✓ B2/B3 | ~ C1 | ✓ O9 |
| Draft-before-write confirmation | — | — | — | — | — | ✓ B6 | — | ~ O9 (`:48` present report) |
| Instruction-file selection / no-duplicate rule | — | — | — | — | — | ✓ B7 | ~ C8 | — |
| Conditional-question suppression | — | — | — | — | — | ✓ B4 | — | — |
| Branch-specific seed templates | — | — | — | — | — | ✓ B8 | ~ STDM config | ~ `.claude/project/*` |
| Prove-the-guardrail-fails loop | — | — | — | — | — | — | ✓ C6 | — |
| Environment/toolchain detection | — | ~ A5 | — | ~ P3 | — | ~ B3 | ✓ C1 | ~ O9 |
| Never-overwrite-existing-config | — | — | — | — | — | ~ B7 | ✓ C5 | ~ adopt.md:67 |
| Umbrella plugin manifest | ~ | — | ~ | — | — | — | — | — |
| Manifest with explicit promoted-skill list | — | — | — | — | — | — | — | — |

Manifest row detail: `agent-skills/plugin.json:1-5` carries three fields and no
skills array; `superpowers/.claude-plugin/plugin.json:1-20` adds authorship and
keywords, still no skills array; only
`mattpocock_skills/.claude-plugin/plugin.json:21-47` enumerates 25 promoted
skill paths, and `mattpocock_skills/CLAUDE.md` makes that array the definition
of "promoted".

---

## 3. Shared-component differences

**Situation→skill routing map (U1 vs M3/M6 vs O3).**
U1 (`SKILL.md:16-42`) is a flat 21-branch dispatch table: one question, one
skill, no relations between skills. M3/M6 (`ask-matt/SKILL.md:13-46`) is a
*graph* — a main flow with two decision branches, on-ramps that merge onto it,
and negative guards (`:40`, `:44`) that say when *not* to take a path. O3
(`CLAUDE.md` Process Before Execution) has 6 lines against UAS's 21 and
ask-matt's ~20 nodes, and covers only process-discipline entry, never the
implementation, review, or context-management skills. **M3/M6 is the stronger
mechanism** because negative guards and hand-off edges are what a flat table
cannot express, and because mis-routing in a large catalog is usually
"reached for the neighbouring skill", which only a relation graph fixes.
**O3 is the weakest of the three by coverage**, but it is the only one that
costs nothing extra at runtime — it lives in a file already loaded.

**Mandatory skill-check clause (U10 vs S2/S3).**
U10 (`SKILL.md:130-138`) states the rule once, declaratively: "Check for an
applicable skill before starting work." S2/S3 (`using-superpowers:10-20`)
states it as a threshold ("1% chance"), forbids the specific evasions
(clarifying questions, codebase exploration, file reads) by name, and backs it
with S7's 12-row rationalization table (`:33-50`) that pre-refutes each excuse
in the agent's own voice. **S2/S3+S7 is materially stronger**: it converts a
rule into a set of recognisable stop-signals, which is the mechanism our own
`verification-before-completion` and `systematic-debugging` skills already use
internally. UAS's version is a sentence an agent can read and still skip.

**Session injection (A1/A4 vs P1/P4).**
Both `cat` the whole bootstrap file into context. Differences that matter:
(a) A2 (`session-start.sh:9-12`) requires `jq` and silently degrades to no
injection without it; P2 (`session-start:16-24`) escapes JSON in pure bash and
has no dependency — **P2 is stronger**, and the superpowers repo's
zero-dependency stance is deliberate. (b) A4 (`hooks.json:3-12`) registers no
matcher; P4 (`hooks.json:5`) matches `startup|clear|compact`, so the bootstrap
survives a `/compact` — **P4 is stronger**, and this is the non-obvious part:
without it the compliance rule evaporates exactly when the session is longest
and most rule-drifty. (c) P3 (`session-start:38-47`) emits three different JSON
shapes and explicitly avoids Claude Code's double-read of
`additional_context` + `hookSpecificOutput`; A-hook emits one shape.
**Cost is identical in kind and different in size:** A1 injects 191 lines
every session; P1 injects 62 lines and defers the 141 lines of platform
references (`S8`) behind a conditional read.

**Generic behavioural rules (U3–U9 vs O7).**
U3–U9 (`SKILL.md:48-128`, 81 lines) and `.claude/rules/core/03-ak-guidelines.md`
(12 rules) are near-duplicates by content: assumptions-first (U3 ≈ AK §1),
simplicity (U6 ≈ AK §2), scope discipline (U7 ≈ AK §3), verification (U8 ≈ AK
§4/§12), confusion management (U4 ≈ AK §1/§10). AK adds token budgets (§6),
conflict resolution (§7), read-before-write (§8), and convention conformance
(§11) that UAS lacks; UAS adds the literal `ASSUMPTIONS I'M MAKING:` output
template (`:52-58`) and the quantification demand (`:79`) that AK states less
concretely. **AK is broader; UAS's two formatting devices are sharper.**
Adopting UAS wholesale would import ~81 lines of duplicate rules to gain two
phrasings.

**One-time repo bootstrap (B2–B9 vs O9–O11).**
Same skeleton: explore the repo, present findings, confirm, write only a
bounded set of files. `adopt.md:24-30` adds an **authority order** (repo
reality > current config/CI > maintained docs > older docs > assumptions) that
SMPS has no equivalent of, and `adopt.md:70-72` refuses to invent verification
commands — both stronger than SMPS for a repo whose ground truth is uncertain.
SMPS is stronger on two mechanics: B4 (`:36`, `:51`, `:59-61`) suppresses
questions exploration already answered, and B7 (`:74-82`) fixes the
CLAUDE.md-vs-AGENTS.md collision and mandates in-place block update rather than
append. `adopt.md:31-45` names files to update but states no idempotency rule
for re-runs. **Net: ours is stronger on epistemics, SMPS is stronger on
idempotency and question economy.**

**Guardrail installation (C3 vs C6).**
SPC's verification (`setup-pre-commit:73-79`) checks that artefacts *exist* and
runs the tool once. STDM's (`setup-ts-deep-modules:79-87`) requires observing
pass → deliberately-introduced-violation-fails → revert-passes.
**C6 is categorically stronger**: existence checks cannot distinguish a wired
guardrail from a misconfigured one, and the skill says so outright ("a config
that doesn't fail on a violation is worthless"). This is the one component in
the SPC/STDM/SX group that is stack-independent.

**Umbrella manifests.**
`agent-skills/plugin.json:1-5` and `superpowers/.claude-plugin/plugin.json:1-20`
are pure identity metadata — nothing an agent reads at runtime.
`mattpocock_skills/.claude-plugin/plugin.json:21-47` is different in kind: the
skills array *is* the promotion boundary, enforced by a written rule in
`mattpocock_skills/CLAUDE.md` that `misc/`, `in-progress/`, and `deprecated/`
must not appear in it. **That manifest carries a curation invariant; the other
two carry none.** Our repo has no plugin manifest and ships skills as a
directory; our equivalent promotion boundary is
`harness_lifecycle/inventory/skill-buckets.md:20-31`, which already excludes
upstream's staging directories from adoption scope.
