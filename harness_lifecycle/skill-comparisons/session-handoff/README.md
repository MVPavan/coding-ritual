# Session Handoff

Bucket 10 — Orchestration, Handoff & Context Continuity
(`inventory/skill-buckets.md:166-175`). The taxonomy marks `handoff`[M] and
`claude-handoff`[M] as **substitutes** — adopt one, not both
(`skill-buckets.md:238`).

The family is about one moment: **the context window is about to end, and the
work is not.** Everything else in this comparison is a different answer to
"what survives that boundary, and in what form".

Sibling comparisons: `../research-workflow/` (the other family whose bucket
council ruling was never executed), `../plan-execution-engines/` (the execution
engine whose workspace ledger carries most of our de-facto continuity).

## Scope note on `claude-handoff`

`claude-handoff` ships in mattpocock's `in-progress/` staging directory, which
our own inventory rules exclude from adoption candidacy: "those are drafts and
one-offs its author has not promoted" (`skill-buckets.md:22-25`), and
`claude-handoff` is named in the excluded list (`skill-buckets.md:27`). It
carries `adoption_scope=out-of-scope` in the CSV and was therefore never ruled
on by the council. It is compared here **as a mechanism**, not as an adoption
candidate — the task asked for it explicitly, and its one distinct component
(seed a live agent rather than write a file) is the sharpest contrast in the
set. Any decision arising from it must clear the out-of-scope rule first.

## The claim: we have no dedicated handoff or compaction skill

**Verified, six independent ways.** The claim holds.

1. All 35 directories in `.claude/skills/` enumerated — no handoff, compaction,
   or session-summary skill.
2. All 7 files in `.claude/commands/` — `adopt`, `check-invariants`,
   `harness-scan`, `harness-status`, `phase-execution`, `run-phases`,
   `use-codex`. No handoff command.
3. Filename search across `.claude/` for `*handoff*|*compact*|*session*|
   *continu*` returned exactly one hit, `teach-session`, which is human
   pedagogy — "make sure the human deeply understands the session"
   (`teach-session/SKILL.md:7`), not agent handoff.
4. Content grep for `handoff|compact|continuity|resume|multi-session|next
   session` across `.claude/` hit 19 files, every one incidental inside a skill
   with a different primary job.
5. Skill-description grep found only three surfaces claiming the trigger:
   `wayfinder` ("more than one agent session can hold", `SKILL.md:3`), `beads`
   ("multi-session handoff, or shared work memory", `SKILL.md:3`), and
   `teach-session`.
6. **`.claude/settings.json` registers `SessionStart` hooks only** — there is no
   `PreCompact` and no `SessionEnd` hook, so nothing in this harness writes an
   artifact at compaction or session end.

Point 6 is the structural one. Our continuity is **read-side**: `bd prime` fires
on session *start* (`settings.json:25-34`, `hooks/bd-prime.sh:25-26`) to
reconstruct context from durable stores. There is no corresponding write-side
event. Everything that survives a boundary in this harness survives because
some skill wrote it to bd, to a ledger, or to a roadmap **during** the work —
never because a boundary was detected and a summary was produced.

That is a coherent design, and for engine-driven work it is a better one than
handoff documents. It has two holes, named at the end.

## Level 1 — Placement

| Skill / surface | Repo | Bucket | Triggers when |
|---|---|---|---|
| `handoff` | mattpocock (`productivity/`, promoted) | 10 | User-invoked only: `disable-model-invocation: true` (`SKILL.md:5`) plus `allow_implicit_invocation: false` (`agents/openai.yaml:4-5`). Fires when the human decides to end a session and continue elsewhere; takes an argument describing the next session's focus (`SKILL.md:4`). |
| `claude-handoff` | mattpocock (`in-progress/`, **out of scope**) | 10 | Same double gate (`SKILL.md:5`, `agents/openai.yaml:4-5`), same argument hint. Fires when the human wants the work continued **now, unattended**, rather than saved for later. |
| `beads` + Session Close | **ours** | 10 (proposed — ours are outside the reference taxonomy) | Description claims the trigger directly: "multi-session handoff, or shared work memory … also when starting a new task, choosing what to work on next, or wrapping up a work session" (`beads/SKILL.md:3`). The close protocol fires "Before reporting completion" (`.beads/beads.md:89-91`). |
| `bd prime` (SessionStart hook) | **ours** | 10 (proposed) | Automatic, every session start (`settings.json:25-34`). Fail-open by design — "it must never fail the session" (`hooks/bd-prime.sh:6`). The read half of handoff. |
| `wayfinder` | **ours** (adopted verbatim from M) | 2 (also 1) | "more than one agent session can hold — as a shared map of decision tickets" (`wayfinder/SKILL.md:3`). User-invoked (`agents/openai.yaml:4-5`). Not a handoff skill: it partitions work *so that* no handoff is needed. |
| `execution` workspace ledger | **ours** | 4 (proposed) | Not separately invocable — it is machinery inside the execution skill. The only surface in the harness with an explicit post-compaction recovery step (`references/task-engine.md:49-51`). |
| `PHASE-BOUNDARIES.md` | mattpocock (ask-matt asset, **undecided**) | 10 | Not a skill — the routing layer that decides *whether* handoff is the right move at all. See below. |

### Prior decisions

- **`handoff` — REJECTED by council**, round-001 event `e053`, 2026-08-11
  (`casebook/views/bucket-10.md:35-39`; `rounds/round-001-council-consolidation.jsonl`,
  `subject_id sk-025`, pin `84fdeff`): "16 lines whose trigger the absorbing
  skill already owns. The judge distinguished this from receiving-code-review
  deliberately: that is a substantial protocol with a distinct actor-moment and
  no kept skill claiming its trigger; this is not."
- **`context-engineering` — ADOPTED (merged) by council**, event `e051`, as the
  absorber (`casebook/views/bucket-10.md:9-21`), with three required
  modifications: "absorb all four of handoff's rules (no duplication of existing
  artifacts, reference by path, redact secrets, suggested-skills section)"
  (`:19`), "expose a /handoff command alias at adoption so the user-invoked
  entry point survives" (`:20`), and rescue ask-matt's five-option
  phase-boundary tree (`:21`).
- **`skill:skills/context-engineering` — REJECTED in the ledger**, 2026-07-15
  (`ledger.json:217-224`): "The root read order, project overlay, docs index,
  and adopt workflow already implement selective context; this long generic
  handbook adds no distinct repeated workflow."
- **`ask-matt` — adopted in part** 2026-08-14 into `skill-router`
  (`ledger.json:389-397`), with an explicit carve-out: "Its
  references/PHASE-BOUNDARIES.md is NOT decided here — evaluate separately."
  (The path in that entry is now stale: upstream flattened it to
  `skills/engineering/ask-matt/PHASE-BOUNDARIES.md` in commit `a16a267`.)
- **No ledger entry exists** for `skill:skills/productivity/handoff` or for
  `claude-handoff`. Neither has ever been recorded.

### The orphan

Those decisions do not compose. The council rejected `handoff` **because**
another skill was going to absorb its four rules and expose a `/handoff` alias.
That absorber had already been rejected in the ledger four weeks earlier
(2026-07-15 precedes the 2026-08-11 round), and no later entry reverses it.
Bucket 10 has never been through an execution wave.

Net effect, verified against the filesystem: `context-engineering` is not
installed, no `/handoff` command exists, and **none of handoff's four rules
landed anywhere.** The rejection of `handoff` rests on a premise that is false
on disk. This is not a stale decision — it is an unexecuted one whose
justification was voided before it was written.

Two further cracks in the council's premise, on inspection of the absorber it
picked:

- The reasoning was that context-engineering's "level-5 section already claimed
  session-boundary management" (`bucket-10.md:13`). That section, *Level 5:
  Conversation Management*, is **three bullets of advice** —"Start fresh
  sessions", "Summarize progress", "Compact deliberately"
  (`reference_harnesses/agent-skills/skills/context-engineering/SKILL.md:113-119`).
  It has no artifact, no redaction rule, no suggested-skills section, and no
  location convention. It claims the *topic*, not the protocol. Folding a
  file-producing skill into it would have meant writing the protocol from
  scratch under another skill's name.
- `redact secrets` (`bucket-10.md:19`) has **no home in our harness at all**.
  The only redaction rule we ship is scoped to debugging output —"Redact
  secrets in everything you show — write `<REDACTED>`"
  (`systematic-debugging/SKILL.md:24`) — and applies to diagnostic artifacts
  shown to the user, not to a document seeded into another agent.

## The routing layer: `PHASE-BOUNDARIES.md`

Explicitly undecided (`ledger.json:389-397`) and the most useful artifact in
this family, because it is the only one that says when *not* to hand off.

It defines the phase boundary as the only place the decision belongs —
"Compacting mid-phase makes the agent lose the thread" (`:5`) — and gives five
options: Continue, `/clear`, `/handoff`, Subagent, `/compact` (`:9-15`), worked
top-to-bottom, first yes wins (`:19`).

The load-bearing claim is that **`/handoff` is narrow** (`:27`). It applies to
exactly four cases: swapping harness (Claude → Codex), moving to a new directory
or repo, sending work to a colleague, or forking a mid-phase side task
(`:29-32`). "That list is the whole clause. What `/handoff` buys is
**portability** — a file that travels. If nothing is travelling, you don't need
it." (`:34`)

Two mechanisms underneath it:

- **Primary vs secondary sources** (`:42-51`): every move except Continue turns
  the session-as-it-happened into a summary of it. Continue is full-information
  and low-room-to-move; `/compact` and `/handoff` are lossy but roomy. This is
  why "can you continue?" is question 1 — "You only pay the lossiness when
  staying costs more than it saves" (`:51`).
- **`/compact` is the default, not the first reach** (`:40`). The named failure
  mode: "a fresh session that is confidently wrong about a decision the summary
  flattened."

This directly contradicts the shape of an adoption that installs `/handoff` as
a general session-ending move. By upstream's own routing, three of the four
handoff cases (new harness, new directory, colleague) do not arise in our
single-repo Claude-plus-Codex setup — and the one that does, forking a mid-phase
side task, is already covered by our discovered-work rule: "create a real stage,
never a note that vanishes with the turn" (`execution/SKILL.md:52-54`).

## Level 2 — Capability profiles

### `handoff` (mattpocock)

**Achieves** — a portable Markdown document that lets a fresh agent, anywhere,
resume work the current session cannot finish.

**Can do**
- Writes a handoff document summarising the conversation for a fresh agent (`SKILL.md:8`).
- **Saves outside the workspace** — "the temporary directory of the user's OS -
  not the current workspace" (`:8`).
- Requires a **"suggested skills" section** naming what the next agent should
  invoke (`:10`).
- **No-duplication rule**: "Do not duplicate content already captured in other
  artifacts (specs, plans, ADRs, issues, commits, diffs). Reference them by path
  or URL instead." (`:12`)
- **Redaction rule** for keys, passwords, PII (`:14`).
- Tailors the document to a user-supplied description of the next session's
  focus (`:16`).

**Pros** — the only surface in this comparison that produces a **portable**
artifact: one file, no repo dependency, no tracker dependency, readable by an
agent that has never seen this codebase. Its no-duplication rule (`:12`) is
exactly right and matches conventions we already enforce elsewhere. The
suggested-skills section is the one component here with no analogue anywhere in
our harness, and it addresses a real failure — a resuming agent that
reconstructs *what* the work is but not *which discipline* it was being done
under.

**Cons** — 17 lines with no template, so the document's shape is entirely
model-discretion; two runs produce different structures. Its temp-directory rule
(`:8`) is deliberate — the file is scratch, not project state — but it means the
artifact is invisible to the repo, uncommitted, unversioned, and lost on reboot,
which is a poor fit for a harness whose whole continuity model is durable repo
state. Against our surfaces it duplicates the no-duplication and
reference-by-path discipline we already enforce more strongly, and adds only the
artifact and the suggested-skills section.

### `claude-handoff` (mattpocock, `in-progress/`)

**Achieves** — the work continues immediately in a fresh background agent,
rather than waiting for a human to open the handoff file.

**Can do**
- Everything `handoff` does *except* saving: "Instead of saving it, launch a
  background agent seeded with the summary as its prompt" (`SKILL.md:8`).
- Concrete invocation: `claude --bg --name "<descriptive name>" "<handoff
  summary>"`, starting in the current working directory and returning
  immediately (`:8`).
- **Mandatory `--name`** — "it sets the display name shown in the job list,
  session picker, and terminal title" (`:10`).
- Same suggested-skills (`:12`), no-duplication (`:14`) and argument-tailoring
  (`:18`) rules.
- **Strengthened redaction rationale**: the summary is not a file that might be
  read, it "becomes the agent's prompt" (`:16`).

**Pros** — closes the gap between deciding to hand off and the work restarting,
which is the actual cost of `handoff` in a solo-operator setting where the
"other agent" is the same person ten minutes later. The mandatory naming rule
(`:10`) is a small, genuinely durable operational detail: unnamed background
jobs are unmanageable once there are three of them. Its redaction reasoning is
strictly stronger than `handoff`'s — prompt-injection surface, not just file
hygiene.

**Cons** — out of scope by our own inventory rule (`skill-buckets.md:22-27`),
and upstream agrees it is beta. The summary exists **only** as a process
argument: nothing is written to disk, so if the spawned agent goes wrong there
is no artifact to inspect, correct, or re-seed from. That is a real regression
against `handoff` for anything non-trivial, and it collides with our
execution engine's opposite principle — artifacts are files precisely so state
survives a bad dispatch (`task-engine.md:44-47`). It also hardcodes a CLI shape
that our harness does not otherwise depend on.

### Our covering surfaces (composite)

**Achieves** — continuity without a handoff document, by writing durable state
continuously during the work and reconstructing it at session start.

**Can do**
- **Durability litmus** deciding what must survive: "any work that must survive
  a reset, compaction, handoff, or multi-agent run" goes to bd
  (`.beads/beads.md:9-10`), with in-turn checklists explicitly excluded (`:11-12`).
- **Session Close protocol**, 5 numbered steps ending in "Report the handoff and
  avoid commits/pushes unless explicitly authorized" (`.beads/beads.md:89-97`).
- **Automatic read-side recovery** — `bd prime` on every SessionStart
  (`settings.json:25-34`), fail-open (`hooks/bd-prime.sh:6`).
- **Explicit post-compaction recovery step**: "After any compaction: re-read
  `progress.md`, the latest findings file, and re-query bd + `git status` before
  dispatching anything. A coordinator that lost its place re-dispatches
  completed work." (`task-engine.md:49-51`)
- **Compaction policy**: "`/compact` between phases — never `/clear` (it kills
  the session)" (`workstream-mode.md:62`), with an enumerated persistent-state
  list (`:65-67`) and an intra-phase re-read rule (`:63-64`).
- **File-only recoverability rule**: "The open findings list, round number, and
  snapshot labels must be recoverable from files alone" (`task-engine.md:44-47`).
- **Artifact-as-file dispatch** so text never transits the coordinator's context
  (`scripts/task-brief.sh:2-4`, `task-engine.md:81-84`).
- **Cross-agent resumption framing** for later fix rounds: "you own it now. Read
  the report file for what was tried." (`task-engine.md:146-150`)
- **Post-compaction authorization proof** — workstream preflight records the
  opt-in "so a post-compaction session can prove the opt-in instead of assuming
  it" (`workstream-mode.md:15-17`).
- **Multi-session work partitioning** via wayfinder: map as index-not-store
  (`wayfinder/SKILL.md:23`), one ticket per session (`:105`), ticket bodies sized
  to one 100K-token session (`:57-63`), claim-before-work for concurrent
  sessions (`:67`), resolution recorded as a comment plus context pointer
  (`:125`).
- **Durable-knowledge routing** — facts/decisions/preferences to `MEMORY.md`,
  not `bd remember` (`.beads/beads.md:13-16`, `beads/SKILL.md:47`); verified
  learnings to `.claude/project/learnings.md` with a 3-field template
  (`learnings.md:9-14`).

**Pros** — strictly stronger than either reference skill on everything except
the artifact itself. Ours is **continuous** rather than boundary-triggered, so it
degrades gracefully: an agent that dies without warning loses nothing, whereas
`handoff` requires a human to invoke it *before* the boundary and produces
nothing if the session ends unexpectedly. Our no-duplication discipline is
enforced in three independent places (`wayfinder/SKILL.md:23`,
`task-engine.md:81-84`, `.beads/beads.md:9-12`) versus one advisory line
upstream. And we have a named failure mode with a mechanism attached
(`task-engine.md:51`), which neither reference skill offers.

**Cons** — three real holes. (a) It is **engine-bound**: nearly all of it lives
inside the execution skill's task engine and workstream mode, so ad-hoc work
outside a plan — exploration, debugging, curation like this task — inherits none
of it. (b) The execution ledger is **disposable and gitignored** by design
(`execution/SKILL.md:51`, `task-engine.md:207-208`), so continuity within a
scope is excellent and continuity *across* scope closure is bd-only. (c) It is
**unexercised**: `docs/workstreams/` does not exist and `find -name roadmap.md`
returns zero hits, so the roadmap/mirror continuity machinery is template-only
(`planning/references/decompose.md:8-21`).

## Verdict

**`handoff` and `claude-handoff` are substitutes** (`skill-buckets.md:238`), and
the taxonomy is right: same trigger, same summary, differing only in whether the
summary lands in a file or a process. `claude-handoff` is the better *mechanism*
for a solo operator and the worse *artifact* — and it is out of scope regardless.

**Against our surfaces, `handoff` is neither a duplicate nor a gap-fill — it is
mostly duplicate with one genuine gap-fill.** Component by component against
its four rules:

- *No-duplication / reference by path* (`:12`) — **duplicate**, and ours is
  stronger. Three independent enforcements, one of them tool-level.
- *Redact secrets* (`:14`) — **gap**, but a narrow one. We have redaction only
  for debugging output (`systematic-debugging/SKILL.md:24`). It becomes
  load-bearing only if we start producing handoff artifacts, so it is a
  consequence of the decision, not a reason for it.
- *Suggested skills* (`:10`) — **genuine gap**, uncovered anywhere. `bd prime`
  restores work state; nothing restores *method*. A resuming agent learns what
  is in flight but not that the work was mid-TDD or mid-debugging-loop.
- *The portable document itself* (`:8`) — **genuine gap**, and the only one that
  matters structurally. Our continuity is entirely repo-bound: bd, ledgers,
  roadmaps, learnings. Nothing produces a self-contained artifact that travels
  to another harness, machine, or person. Per upstream's own routing
  (`PHASE-BOUNDARIES.md:27-34`), that is precisely and only what handoff is for.

So the honest verdict is narrower than either "adopt" or "reject". Our harness
covers the *durability* of handoff comprehensively and the *portability* of it
not at all — and portability is a use case (Claude → Codex, work to a colleague)
that this repo, which maintains a `.codex/` twin of its whole harness, actually
has. What our harness does **not** need is the thing both reference skills
mostly are: a conversation-summarising ritual at session end. `bd prime`,
Session Close, and the execution ledger already win that comparison.

**Strongest for what.** For continuity inside planned work: ours, decisively.
For deciding whether a boundary needs any action at all: `PHASE-BOUNDARIES.md`,
which nothing of ours attempts. For moving work out of this repo or this
harness: `handoff`, and only it.

### Smallest durable borrowable patterns

Candidates for the `harness-evaluate` skill to rule on; no adoption implied.
Note that the standing council rejection of `handoff` must be revisited first,
since its stated premise is void (see *The orphan*).

1. **The `/handoff` narrowness clause** (`PHASE-BOUNDARIES.md:27-34`) — 6 lines
   naming the four cases that justify a portable file, plus the one-sentence
   test "If nothing is travelling, you don't need it." This is the highest-value
   borrow in the family because it is the pattern that *prevents* adopting a
   handoff ritual we do not need, while marking the case we do. It is currently
   undecided by explicit carve-out (`ledger.json:389-397`).
2. **The suggested-skills section** (`handoff/SKILL.md:10`) — one line. Its
   natural home in our harness is not a new skill but the existing Session Close
   protocol (`.beads/beads.md:89-97`) or the bd close `--reason`, which already
   carries evidence forward (`execution/SKILL.md:27-30`). Restoring *method*
   alongside *state* is the gap; a handoff document is one way to fill it and
   not obviously the best one.
3. **The primary-vs-secondary source frame** (`PHASE-BOUNDARIES.md:42-51`) — a
   4-row table explaining why every continuity move except continuing is lossy.
   It gives our existing `/compact`-never-`/clear` rule
   (`workstream-mode.md:62`) the *reason* it currently asserts without.
4. **Mandatory descriptive naming for background agents**
   (`claude-handoff/SKILL.md:10`) — one line, mechanism-only, independent of the
   handoff question; applies to any background dispatch. Cheapest item here,
   and the only one that survives `claude-handoff`'s out-of-scope status,
   since it is an operational detail rather than the skill's protocol.

**Not borrowable as-is:** the temp-directory location rule
(`handoff/SKILL.md:8`) — it conflicts with our scratchpad convention
(`CLAUDE.md:87`) and with the principle that continuity artifacts are durable
repo state; and the seed-a-live-agent mechanism
(`claude-handoff/SKILL.md:8`), which drops the artifact our engine deliberately
keeps (`task-engine.md:44-47`) and is out of scope by inventory rule.

Component-level evidence: `components.md`.
