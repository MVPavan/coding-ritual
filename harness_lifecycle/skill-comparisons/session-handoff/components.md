# Session Handoff — Component Inventory

Level 3 of the comparison in `README.md`. Every component is cited `file:line`.

Surface roots:
- `handoff` → `reference_harnesses/mattpocock_skills/skills/productivity/handoff/`
- `claude-handoff` → `reference_harnesses/mattpocock_skills/skills/in-progress/claude-handoff/`
- `PHASE-BOUNDARIES` → `reference_harnesses/mattpocock_skills/skills/engineering/ask-matt/PHASE-BOUNDARIES.md` (routing layer, undecided)
- ours — `.beads/beads.md`, `.claude/skills/beads/`, `.claude/settings.json`, `.claude/hooks/bd-prime.sh`, `.claude/skills/execution/`, `.claude/skills/wayfinder/`, `.claude/skills/planning/`, `CLAUDE.md`

## Component inventory

### `handoff` (mattpocock) — 17 lines + 5-line agent config

| # | Component | Cite |
|---|---|---|
| H1 | User-invoked only — `disable-model-invocation: true` | `SKILL.md:5` |
| H2 | Runtime policy gate — `allow_implicit_invocation: false` | `agents/openai.yaml:4-5` |
| H3 | Argument hint: "What will the next session be used for?" | `SKILL.md:4` |
| H4 | **Produce a handoff document** summarising the conversation so a fresh agent can continue | `SKILL.md:8` |
| H5 | **Store outside the workspace** — "the temporary directory of the user's OS - not the current workspace" | `SKILL.md:8` |
| H6 | **Suggested-skills section** naming what the next agent should invoke | `SKILL.md:10` |
| H7 | **No-duplication rule** — specs, plans, ADRs, issues, commits, diffs | `SKILL.md:12` |
| H8 | **Reference-by-path-or-URL** rather than restating | `SKILL.md:12` |
| H9 | **Redaction rule** — API keys, passwords, PII | `SKILL.md:14` |
| H10 | Argument tailoring to the next session's stated focus | `SKILL.md:16` |

### `claude-handoff` (mattpocock, `in-progress/`, out of scope)

| # | Component | Cite |
|---|---|---|
| C1 | User-invoked only | `SKILL.md:5` |
| C2 | Runtime policy gate | `agents/openai.yaml:4-5` |
| C3 | Argument hint (identical to H3) | `SKILL.md:4` |
| C4 | Produce a handoff summary | `SKILL.md:8` |
| C5 | **Seed a live background agent instead of saving** — "Instead of saving it, launch a background agent seeded with the summary as its prompt" | `SKILL.md:8` |
| C6 | Concrete invocation `claude --bg --name "<name>" "<summary>"`; starts in cwd, returns immediately, managed via `claude agents` | `SKILL.md:8` |
| C7 | **Mandatory descriptive `--name`** — sets display name in job list, session picker, terminal title | `SKILL.md:10` |
| C8 | Suggested-skills section | `SKILL.md:12` |
| C9 | No-duplication + reference-by-path | `SKILL.md:14` |
| C10 | **Redaction with prompt-injection rationale** — "the summary becomes the agent's prompt" | `SKILL.md:16` |
| C11 | Argument tailoring | `SKILL.md:18` |

### `PHASE-BOUNDARIES` (mattpocock, ask-matt asset — routing layer)

| # | Component | Cite |
|---|---|---|
| P1 | Phase definition — ends when "ok, we're done with that" | `:3` |
| P2 | **Boundary-only rule** — "Compacting mid-phase makes the agent lose the thread" | `:5` |
| P3 | **Five-option table** — Continue / `/clear` / `/handoff` / Subagent / `/compact` | `:9-15` |
| P4 | **Ordered tree, first yes wins** | `:19` |
| P5 | Q1 Continue test — next phase needs this as primary source, or ~150k tokens remain | `:21` |
| P6 | Q2 `/clear` test + one-way-cost warning ("you lose the **why**") | `:23-25` |
| P7 | **Q3 handoff-narrowness clause** — exactly four cases (new harness, new directory, colleague, forked mid-phase side task) | `:27-32` |
| P8 | **Portability test** — "What `/handoff` buys is portability… If nothing is travelling, you don't need it." | `:34` |
| P9 | Q4 AFK/subagent test | `:36` |
| P10 | Q5 `/compact` as terminal default, with a passed instruction | `:38` |
| P11 | **Default-not-first-reach rule** + named failure ("confidently wrong about a decision the summary flattened") | `:40` |
| P12 | **Primary-vs-secondary source frame**, 4-row trade table | `:42-51` |
| P13 | Judgement-call caveat — value is in asking in order, at the boundary | `:53-55` |

### Ours — beads policy, session close, `bd prime`

| # | Component | Cite |
|---|---|---|
| B1 | **Durability litmus** — "any work that must survive a reset, compaction, handoff, or multi-agent run" | `.beads/beads.md:9-10` |
| B2 | In-turn/durable split — turn checklists stay out of bd | `.beads/beads.md:11-12` |
| B3 | **Durable-knowledge routing** — facts/decisions/preferences to `MEMORY.md`, not `bd remember` | `.beads/beads.md:13-16` |
| B4 | Actor-tag convention `<runtime>:<session-or-purpose>` | `.beads/beads.md:17-19` |
| B5 | Handoff report gate — "report changed files, validation, and proposed commands" | `.beads/beads.md:22` |
| B6 | Plaintext mirror as recovery substrate (`.beads/issues.jsonl`) | `.beads/beads.md:23-26` |
| B7 | **Session Close protocol, 5 steps** | `.beads/beads.md:89-97` |
| B8 | — close with evidence in `--reason` | `.beads/beads.md:93` |
| B9 | — refresh the mirror if issues changed | `.beads/beads.md:95` |
| B10 | — report the handoff, no unauthorized commits | `.beads/beads.md:97` |
| B11 | Protocol deferral — live session-close protocol comes from `bd prime` | `.beads/beads.md:3-5` |
| B12 | **SessionStart hook** auto-primes every session | `.claude/settings.json:25-34` |
| B13 | Hook body `bd prime --hook-json` | `.claude/hooks/bd-prime.sh:25-26` |
| B14 | **Fail-open rule** — "it must never fail the session" | `.claude/hooks/bd-prime.sh:6` |
| B15 | Context-recovery routing row | `.claude/skills/beads/SKILL.md:14` |
| B16 | Empty-prime fallback (`bd where`) | `.claude/skills/beads/SKILL.md:8` |
| B17 | Mid-task discovery filed before the turn ends | `.claude/skills/beads/SKILL.md:46` |
| B18 | Session-close mirror export | `.claude/skills/beads/SKILL.md:48` |
| B19 | Triage note-append — "so the next session resumes instead of re-asking" | `.claude/skills/triage/SKILL.md:47-49` |
| B20 | Learnings capture rule + 3-field template | `.claude/project/learnings.md:3-5`, `:9-14` |
| B21 | Survival criterion — "if my session died right now, would I want this to still exist as project state?" | `.claude/docs/beads-issue-tracking-adoption.md:29-30` |
| B22 | Three-layer memory model (bd / TodoWrite / knowledge store) | `.claude/docs/beads-issue-tracking-adoption.md:20-27` |

### Ours — execution engine (workspace ledger, workstream mode)

| # | Component | Cite |
|---|---|---|
| E1 | bd as anchor — "if it's not in bd, it's not real" | `execution/SKILL.md:27-30` |
| E2 | **Workspace contract**, gitignored, never committed | `execution/SKILL.md:46-51` |
| E3 | Discovered-work rule — "create a real stage, never a note that vanishes with the turn" | `execution/SKILL.md:52-54` |
| E4 | Never-re-seed resumability guard | `execution/SKILL.md:68-69` |
| E5 | Report includes parked findings from the ledger | `execution/SKILL.md:96-98` |
| E6 | Never hand-edit generated tracking — update bd, then render | `execution/SKILL.md:135` |
| E7 | **Ledger identity line** `# <plan path> — <epic/task id> — SCOPE_BASE <sha7>` | `task-engine.md:32` |
| E8 | Append-one-line-per-event ledger format | `task-engine.md:33-42` |
| E9 | Division of truth — ledger records what bd cannot (fix-round position, snapshots, parked rulings) | `task-engine.md:28-30` |
| E10 | **File-only recoverability rule** | `task-engine.md:44-47` |
| E11 | **Post-compaction recovery step** + named failure ("A coordinator that lost its place re-dispatches completed work") | `task-engine.md:49-51` |
| E12 | `SCOPE_BASE` commit-free diff anchor | `task-engine.md:57-60` |
| E13 | **Artifact-as-file dispatch** — "so the task text never passes through the coordinator's context" | `scripts/task-brief.sh:2-4` |
| E14 | Paths-not-contents rule — "everything pasted stays resident in your context" | `task-engine.md:81-84` |
| E15 | Review package never enters coordinator context | `task-engine.md:69` |
| E16 | Report file as persistent memory across dispatches | `task-engine.md:143-145` |
| E17 | **Cross-implementer handoff framing** — "you own it now. Read the report file for what was tried." | `task-engine.md:146-150` |
| E18 | Parked findings carried into bd close; workspace disposable | `task-engine.md:207-208` |
| E19 | No raw session history to workers | `task-engine.md:218` |
| E20 | **Compact-never-clear rule** | `workstream-mode.md:62` |
| E21 | Intra-phase compaction + ledger re-read | `workstream-mode.md:63-64` |
| E22 | **Enumerated persistent-state list** | `workstream-mode.md:65-67` |
| E23 | Post-compact re-query — "bd is the source of truth, not conversation memory" | `workstream-mode.md:44-46` |
| E24 | **Authorization recorded so a post-compaction session can prove the opt-in** | `workstream-mode.md:15-17` |
| E25 | Dirty-tree baseline file at preflight | `workstream-mode.md:18-20` |
| E26 | Roadmap↔bd reconciliation gate | `workstream-mode.md:21-23` |
| E27 | Roadmap authoritative for order, bd for status | `workstream-mode.md:26-27` |
| E28 | `/run-phases` invocation **is** the ledger-recorded opt-in | `.claude/commands/run-phases.md:11-13` |

### Ours — wayfinder, planning, root

| # | Component | Cite |
|---|---|---|
| W1 | Purpose gate — work "more than one agent session can hold" | `wayfinder/SKILL.md:3` |
| W2 | Map = single tracker issue labelled `wayfinder:map` | `wayfinder/SKILL.md:21` |
| W3 | **Index-not-store rule** — "a decision lives in exactly one place — its ticket — so the map never restates it" | `wayfinder/SKILL.md:23` |
| W4 | Load-once-per-session, low resolution | `wayfinder/SKILL.md:29` |
| W5 | Map body template (Destination / Notes / Decisions so far / Not yet specified / Out of scope) | `wayfinder/SKILL.md:31-53` |
| W6 | **Ticket sized to one 100K-token agent session** | `wayfinder/SKILL.md:57-63` |
| W7 | **Claim-before-work** so concurrent sessions skip it | `wayfinder/SKILL.md:67` |
| W8 | Fog-of-war graduation on resolution | `wayfinder/SKILL.md:84` |
| W9 | Ticket-vs-fog test (state the question now, not answer it) | `wayfinder/SKILL.md:88` |
| W10 | **One ticket per session cap** | `wayfinder/SKILL.md:105` |
| W11 | Resolution recorded as comment + close + **context pointer** | `wayfinder/SKILL.md:125` |
| W12 | Research findings on a throwaway branch with a context pointer | `wayfinder/SKILL.md:115` |
| W13 | No implicit invocation | `wayfinder/agents/openai.yaml:4-5` |
| W14 | Roadmap per-phase schema (template only — no instance exists) | `planning/references/decompose.md:13-15` |
| W15 | Epic-title join key `[<phase-id>]` binding roadmap rows to bd epics | `planning/references/decompose.md:19-21` |
| W16 | Append-only roadmap — "do not renumber or rewrite existing phases" | `planning/references/decompose.md:29-30` |
| W17 | Plan path recorded in bd notes as a cross-session pointer | `planning/SKILL.md:92-94` |
| W18 | Draft-is-not-a-handoff gate | `planning/SKILL.md:129` |
| W19 | Hand-off step names the execution surface | `planning/SKILL.md:98-100` |
| W20 | Read Order item 4 — roadmap + generated mirrors | `CLAUDE.md:20` |
| W21 | ADRs as non-relitigable prior decisions | `CLAUDE.md:17` |
| W22 | Scratchpad is throwaway, never committed | `CLAUDE.md:87` |
| W23 | Session-completion protocol pointer + `bd prime` | `CLAUDE.md:95` |
| W24 | Conversation-only sessions are lost — "a session that ends as conversation only is lost to the next session" | `idea-refine/SKILL.md:135` |
| W25 | design-evolve Phase 4 handoff checklist (5 items, incl. deferred items + follow-ups) | `design-evolve/SKILL.md:247-255` |

## Cross-skill matrix

`✓` present · `~` variant · `—` absent

| Component | `handoff` | `claude-handoff` | `PHASE-BOUND` | ours: beads/bd | ours: execution | ours: wayfinder |
|---|:--:|:--:|:--:|:--:|:--:|:--:|
| **Produces a portable, self-contained artifact** | ✓ H4 | — C5 | — | — | — | — |
| Artifact survives outside the repo | ✓ H5 | — | — | — | — | — |
| Artifact is durable repo/tracker state | — H5 | — | — | ✓ B6 | ~ E2 | ✓ W2 |
| Seeds a live successor agent | — | ✓ C5 | ~ P9 | — | ✓ E13 | — |
| Descriptive naming of background work | — | ✓ C7 | — | ~ B4 | ~ E7 | — |
| **Suggested-skills / method carry-over** | ✓ H6 | ✓ C8 | ~ P3 | — | — | — |
| No-duplication of existing artifacts | ✓ H7 | ✓ C9 | — | ✓ B1/B2 | ✓ E14 | ✓ W3 |
| Reference-by-path instead of restating | ✓ H8 | ✓ C9 | — | ✓ B3 | ✓ E14 | ✓ W3 |
| **Secret redaction in the carried text** | ✓ H9 | ✓ C10 | — | — | — | — |
| Tailoring to the next session's focus | ✓ H10 | ✓ C11 | ~ P10 | — | — | — |
| **Decides whether to hand off at all** | — | — | ✓ P3/P4 | — | ~ E20 | — |
| Boundary-timing rule | — | — | ✓ P2 | — | ~ E20/E21 | ~ W10 |
| Lossiness/primary-source reasoning | — | — | ✓ P12 | — | — | — |
| Compaction policy | — | — | ✓ P10/P11 | — | ✓ E20 | — |
| **Post-compaction recovery procedure** | — | — | — | ~ B15 | ✓ E11/E23 | — |
| Automatic session-start context restore | — | — | — | ✓ B12/B13 | — | — |
| Boundary-triggered write event | ✓ H4 | ✓ C5 | ✓ P4 | ~ B7 | — | — |
| Continuous durable-state writing | — | — | — | ✓ B1/B17 | ✓ E3/E8 | ✓ W11 |
| Explicit persistent-state enumeration | — | — | — | ✓ B22 | ✓ E22 | — |
| File-only recoverability guarantee | ~ H4 | — | — | ✓ B6 | ✓ E10 | — |
| Named failure mode with a mechanism | — | — | ✓ P11 | ~ B21 | ✓ E11 | — |
| Work sized to one session | — | — | ~ P5 | — | — | ✓ W6 |
| Concurrent-session safety | — | — | — | ~ B4 | ~ E12 | ✓ W7 |
| Evidence carried into closure | — | — | — | ✓ B8 | ✓ E5/E18 | ✓ W11 |
| Invocation gating (user-only) | ✓ H1/H2 | ✓ C1/C2 | — | — | ~ E28 | ✓ W13 |

## Shared-component differences

**The artifact** (`✓` H4 only). This is the family's defining split. `handoff`
writes one self-contained Markdown file to OS temp (`SKILL.md:8`) — portable,
repo-independent, readable by an agent that has never seen this codebase.
`claude-handoff` writes **nothing**: the summary exists only as a process
argument (`SKILL.md:8`). Ours writes continuously into bd, `.beads/issues.jsonl`
(`.beads/beads.md:23-26`), the workspace ledger (`task-engine.md:32-42`), and
tracker tickets (`wayfinder/SKILL.md:125`) — durable but **repo-bound**, none of
it travelling anywhere. **Stronger depends on the axis:** ours dominates on
durability (survives an unannounced session death; `handoff` produces nothing
unless a human invokes it first) and loses completely on portability. The two
are not competing implementations of one component — they are different
components that look alike.

**No-duplication / reference-by-path** (`✓` in five of six columns).
Upstream states it once, as advice, in both skills (`handoff/SKILL.md:12`,
`claude-handoff/SKILL.md:14`). Ours enforces it three times with mechanisms:
wayfinder's index-not-store rule gives it a *reason* — "a decision lives in
exactly one place — its ticket" (`wayfinder/SKILL.md:23`); the task engine gives
it a *cost model* — "everything pasted stays resident in your context for the
rest of the session" (`task-engine.md:81-84`); and beads gives it a *routing
table* deciding which store owns what (`.beads/beads.md:9-16`). **Ours is
substantially stronger.** Upstream tells the agent not to duplicate; ours tells
it where the single copy lives and what duplication costs. Nothing to borrow
here.

**Redaction** (`✓` H9/C10, `—` everywhere in ours). Upstream's two differ in
rationale, and `claude-handoff`'s is stronger: `handoff` treats it as file
hygiene (`SKILL.md:14`), `claude-handoff` notes the text "becomes the agent's
prompt" (`SKILL.md:16`) — an injection surface, not just a leak. Ours has one
redaction rule and it is scoped elsewhere: "Redact secrets in everything you
show — write `<REDACTED>`" applies to debugging artifacts shown to the user
(`systematic-debugging/SKILL.md:24`). **The gap is real but conditional** — it
binds only if we start producing carried text. It is a consequence of adopting a
handoff artifact, not an independent reason to.

**Suggested skills / method carry-over** (`✓` H6/C8, `—` in all of ours). Both
reference skills require the summary to name what the successor should invoke.
Our surfaces restore *state* comprehensively — `bd prime` on SessionStart
(`settings.json:25-34`), ledger re-read (`task-engine.md:49-51`), persistent
state enumerated (`workstream-mode.md:65-67`) — and restore *method* nowhere. A
resumed session learns which tasks are open and which files changed, not that
the work was mid-TDD, mid-debugging-loop, or under a characterization-first
ruling. **This is the one component where upstream is strictly ahead of us and
no substitute exists in our harness.** The nearest thing is planning's hand-off
step, which names the execution surface but not the discipline
(`planning/SKILL.md:98-100`).

**Boundary-triggered vs continuous writing** (the mechanism split behind every
other row). Upstream is **event-driven**: a human decides the moment, and one
document is produced (`handoff/SKILL.md:8`). Ours is **continuous**: durability
is decided per fact, at the moment the fact appears — "create a real stage, never
a note that vanishes with the turn" (`execution/SKILL.md:52-54`), "Durable work
found mid-task → `bd create` … before the turn ends" (`beads/SKILL.md:46`),
ledger appended per event (`task-engine.md:33-42`). **Ours is stronger for
unplanned endings and weaker for planned ones.** An agent that dies mid-turn
loses nothing under ours and everything under upstream's; an operator who wants
one readable summary of a two-hour session gets it upstream and must reconstruct
it from four stores under ours. The two are complements, and this is the precise
sense in which `handoff` is not a duplicate of what we have.

**Post-compaction recovery** (`✓` E11, `~` B15, `—` upstream). Neither reference
skill has any concept of recovering *after* a compaction — `handoff` assumes the
successor starts from the document, `claude-handoff` from the prompt. Ours is the
only surface in the comparison with an explicit re-read procedure and a named
failure: "re-read `progress.md`, the latest findings file, and re-query bd +
`git status` before dispatching anything. A coordinator that lost its place
re-dispatches completed work" (`task-engine.md:49-51`), reinforced by "bd is the
source of truth, not conversation memory" (`workstream-mode.md:44-46`).
**Ours is strongest and unmatched** — but it lives inside the execution engine,
so it applies only to plan-driven work.

**Deciding whether to hand off** (`✓` P3/P4 only). No skill in the compared set
other than `PHASE-BOUNDARIES` asks whether the boundary needs any action.
`handoff` and `claude-handoff` assume the answer is yes — they are invoked, so
they act. Ours has one narrow rule in this space, "`/compact` between phases —
never `/clear` (it kills the session)" (`workstream-mode.md:62`), which is an
assertion without a reason. `PHASE-BOUNDARIES` supplies both the ordered test
(`:19-38`) and the reason, via the primary-vs-secondary source trade
(`:42-51`). **It is the strongest component in the family and belongs to
neither compared skill** — which is why its undecided status
(`ledger.json:389-397`) matters more than the handoff decision itself.

**Invocation gating** (`✓` upstream both, mixed in ours). Both reference skills
are doubly gated to user-only (`handoff/SKILL.md:5` + `agents/openai.yaml:4-5`;
same for `claude-handoff`), which is correct for a destructive context move.
Ours splits: wayfinder carries the identical double gate
(`wayfinder/agents/openai.yaml:4-5`), while the execution engine's continuity
machinery is not separately invocable at all — it runs because the engine runs,
with `/run-phases` treated as the recorded opt-in
(`.claude/commands/run-phases.md:11-13`). **Different problems, both correctly
solved**; nothing to borrow.
