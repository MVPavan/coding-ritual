# Harness Bootstrap — Skill Comparison

Capability family: **skill discovery/routing, one-time repo bootstrap, and
umbrella packaging** — the surfaces that tell an agent how to find and use the
harness itself.

Level 3 component inventory and cross-skill matrix:
[`components.md`](./components.md).

Prior ledger decisions engaged with here (all `2026-07-15`):
`skill:skills/using-agent-skills` REJECTED, `hook:hooks/session-start`
REJECTED, `plugin:agent-skills` REJECTED. This comparison re-tests all three
rather than restating them.

**Method note.** `harness-skill-compare` requires asking which subagent runs
the comparison. No subagent was named in the request; the reference-side
reading was done in-thread (~1,400 lines, all citations first-hand) and a
`fable-xhigh` subagent was used only for the our-side survey. Flagging the
deviation rather than hiding it.

---

## Level 1 — Placement

| Skill | Repo | Bucket | Triggers when |
|---|---|---|---|
| `using-agent-skills` | agent-skills | 11 — Harness Routing & Agent-System Authoring (`skill-buckets.csv:58`) | Claimed: session start or "which skill applies". Real: **only via the SessionStart hook** — the description ("Discovers and invokes agent skills", `SKILL.md:3`) is too abstract to fire on a concrete task, so without the hook it is dead weight |
| `hooks/session-start` (agent-skills) | agent-skills | 11 (hook) | Every SessionStart event, unconditionally (`hooks/hooks.json:3-12` — no matcher) |
| `using-superpowers` | superpowers | 11 (`skill-buckets.csv:61`) | Claimed: "starting any conversation" (`SKILL.md:3`). Real: **hook-injected**, then self-enforcing on every subsequent turn via the 1% clause (`SKILL.md:10-16`). Explicitly exempts subagents (`:6-8`) |
| `hooks/session-start` (superpowers) | superpowers | 11 (hook) | SessionStart matching `startup\|clear\|compact` (`hooks/hooks.json:5`) — i.e. also after `/clear` and `/compact` |
| `ask-matt` | mattpocock | 11 (`skill-buckets.csv:59`) | **User-invoked only** — `disable-model-invocation: true` (`SKILL.md:4`). Fires when a human types `/ask-matt`, never automatically. This is the single most important fact about it and the ledger's framing of it as a "router" obscures it |
| `setup-matt-pocock-skills` | mattpocock | 12 — Repository Tooling & Guardrails, also 11 (`skill-buckets.csv:64`) | User-invoked (`SKILL.md:4`), once per repo, before first engineering flow |
| `setup-pre-commit` | mattpocock `misc/` | 12 (`skill-buckets.csv`, `adoption_scope=out-of-scope`) | Model-invocable on "add pre-commit hooks / set up Husky / configure lint-staged" (`SKILL.md:3`) |
| `setup-ts-deep-modules` | mattpocock `in-progress/` | 12, out-of-scope | User-invoked (`SKILL.md:4`); wire dependency-cruiser into a TS monorepo |
| `scaffold-exercises` | mattpocock `misc/` | 14, out-of-scope | Model-invocable on "scaffold exercises / new course section" (`SKILL.md:3`) |
| `plugin.json` × 3 | all three | packaging, not a skill | Install/registration time only |
| **`.claude/commands/adopt.md`** (ours) | ours | proposed: 12, family `harness-bootstrap` | User-invoked `/adopt` after the harness is copied into a target repo (`adopt.md:7`) |
| **`CLAUDE.md` Process Before Execution** (ours) | ours | proposed: 11, family `skill-routing` | Always loaded; the only situation→discipline mapping we have |
| **`wayfinder`** (ours) | ours | 2 — Planning & Work Management, family `task-decomposition` (`skill-buckets.csv:15`) | **Not a routing surface.** Plans a multi-session effort as decision tickets (`SKILL.md:3`), and is itself `disable-model-invocation: true` (`:4`). Listing it as our routing counterpart is a category error — it contributes nothing to discovery. It *does* route internally to other skills (`wayfinder/SKILL.md:77-79`, `:124`), and two of those pointers are **already dead**: `/setup-matt-pocock-skills` (`:25`) and a `/research` subagent (`:77`, `:115`) — neither exists here |

Three of the compared skills (`setup-pre-commit`, `setup-ts-deep-modules`,
`scaffold-exercises`) are already declared out of adoption scope by
`harness_lifecycle/inventory/skill-buckets.md:20-31`, because they come from
upstream's own `misc/` and `in-progress/` staging directories — drafts their
author has not promoted. That is a procedural finding: they should not have
been in the roster. They are still evaluated below for the *patterns* they
encode, which is the only reason to look at them.

---

## Level 2 — Capability profiles

### `using-agent-skills` (191 lines)

**Achieves** — gives a session an always-on map from task shape to skill name,
plus a set of general behavioural rules.

**Can do**
- 21-branch situation→skill decision tree (`SKILL.md:16-42`)
- Six "non-negotiable" operating behaviours: assumptions, confusion, push-back,
  simplicity, scope, verification (`:44-113`)
- 10-item failure-mode list (`:115-128`)
- Four skill rules including "check for an applicable skill before starting
  work" (`:130-138`)
- 16-step canonical feature lifecycle (`:140-163`)
- 24-row catalog quick-reference (`:165-191`)

**Pros** (against this set) — the only one that ships both a routing map *and*
a catalog enumeration in one file. The routing tree covers implementation-time
sub-branches (UI / API / security / performance) that ask-matt's flow graph
handles less directly.

**Cons** — 145 of its 191 lines are useless or duplicative *to us*. Lines
165-191 enumerate **their** 24 skills, none of which are installed here; lines
16-42 route to those same names. Lines 44-128 (81 lines) restate
`.claude/rules/core/03-ak-guidelines.md`, which is already always-loaded — see
components.md §3 for the rule-by-rule mapping. What is left after removing
both is ~10 lines of genuinely portable content. It also has no compliance
mechanism beyond a single declarative sentence (`:132`).

### `using-superpowers` (62 lines + 141 lines of conditional platform refs)

**Achieves** — makes skill invocation mandatory and hard to rationalize out of.

**Can do**
- 1%-threshold mandatory-invocation clause (`SKILL.md:10-16`)
- Ordering rule: skill check precedes clarifying questions, exploration, file
  reads (`:20`)
- Announce-and-todo compliance externalisation (`:24`)
- Process-before-implementation priority with worked examples (`:26-31`)
- 12-row rationalization → reality table (`:33-50`)
- Conditional platform-reference indirection (`:52-58`)
- Precedence ladder: user instructions > skills > defaults (`:62`)
- Subagent exemption (`:6-8`)

**Pros** — a genuinely *different mechanism* from `using-agent-skills`, and the
ledger's rejection reason ("another 191-line meta-skill") does not describe it:
it is 62 lines, contains **no catalog and no routing tree**, and is entirely
about compliance. The rationalization table is the strongest single component
in this comparison — it is the same technique our own
`verification-before-completion` and `systematic-debugging` skills use, applied
one level up. The subagent exemption and the conditional platform refs are both
real context-economy engineering.

**Cons** — its value is proportional to how often an agent *skips* a skill it
should have used, which is unmeasured here. It is written for a plugin
distributing skills to unknown repos; a repo whose `CLAUDE.md` already routes
process discipline (`CLAUDE.md:39-49`) gets less from it. The `<EXTREMELY-
IMPORTANT>` / "you do not have a choice" register conflicts with this repo's
stated preference for factual, non-inflated instruction. And it is only
effective if hook-injected, which couples it to the hook decision.

### `ask-matt` (90 + 55 lines, user-invoked)

**Achieves** — a human-readable map of how a skill catalog's flows connect, plus
a decision procedure for context/phase boundaries.

**Can do**
- Flow vocabulary: main flow / on-ramp / standalone / vocabulary layer (`SKILL.md:11`)
- Main flow with two explicit decision branches (`:13-26`)
- **Near-duplicate disambiguation** — `grill-with-docs` vs `grill-me` resolved
  by "are you in a working directory" (`:17`, restated `:77-78`)
- Negative scope guards — don't triage `/to-tickets` output (`:40`); never use
  wayfinder for a well-scoped feature (`:44`)
- Inter-skill hand-off contracts (`:42`, `:46`, `:52`)
- Context-hygiene rule with a ~150k smart-zone budget (`:28-32`)
- Five-option phase-boundary tree, first-yes-wins, `/compact` deliberately last
  (`PHASE-BOUNDARIES.md:17-40`) with a primary-vs-secondary-source cost model
  (`:42-51`)

**Pros** — the only skill here that models *relations between skills* rather
than a flat lookup, which is what actually prevents mis-routing in a large
catalog. Because it is `disable-model-invocation: true`, it costs **zero**
always-on context: it loads only when a human asks. That makes the usual
"another meta-skill increases context pressure" objection inapplicable to it.
`PHASE-BOUNDARIES.md` is a self-contained capability with no dependency on
mattpocock's catalog at all.

**Cons** — it is a hand-maintained mirror of a catalog, and upstream says so:
"a stale one it still routes to, is a router that lies"
(`mattpocock_skills/CLAUDE.md`). For 34 skills under active churn — this repo
has rebuilt skill buckets five times — a hand-maintained router is a standing
liability. Roughly 60 of its 90 lines describe mattpocock skills we do not have
(`/handoff`, `/wizard`, `/to-questionnaire`, `/wait-what`, `/research`,
`/resolving-merge-conflicts`), so the artefact is not portable, only its shape
is.

### `setup-matt-pocock-skills` (116 lines + 5 templates, user-invoked)

**Achieves** — one-time per-repo configuration of what the other skills assume.

**Can do** — 8-probe repo exploration (`SKILL.md:19-31`); conditional-section
suppression (`:36`, `:51`, `:59-61`); lead-with-recommendation questioning
(`:34-36`); draft-before-write gate (`:63-70`); CLAUDE.md-vs-AGENTS.md
selection and in-place block update (`:74-82`); branch-specific seed templates
(`:104-110`).

**Pros / cons vs ours** — this is a direct substitute for
`.claude/commands/adopt.md`, and ours is the more developed of the two: it has
an explicit authority order (`adopt.md:24-30`) and a refuse-to-invent-
verification rule (`:70-72`) that SMPS lacks entirely. SMPS is better on two
narrow mechanics — suppressing questions exploration already answered (B4), and
the instruction-file collision rule (B7), where `adopt.md:31-45` names the
files to write but states no idempotency rule for a re-run.

### `setup-pre-commit` / `setup-ts-deep-modules` / `scaffold-exercises`

**Achieves** — install a specific toolchain guardrail (Husky+lint-staged;
dependency-cruiser boundaries) or scaffold a course-repo directory tree.

**Pros / cons** — all three are inapplicable as artefacts: this repo has no
`package.json`, no TypeScript, no CI, no build, no first-party code, and
`.claude/project/verification.md` declares a structural-check-only gate; the
user does no frontend work. `scaffold-exercises` is additionally bound to a
private `pnpm ai-hero-cli internal lint` binary (`SKILL.md:8`, `:54`).
The one component that survives translation is `setup-ts-deep-modules`'
**prove-the-rules-bite** loop (`SKILL.md:79-87`): install the guardrail, run it
clean (pass), deliberately introduce a violation (must fail), revert (pass) —
justified as "a config that doesn't fail on a violation is worthless".
`setup-pre-commit`'s verification (`:73-79`) is the weaker existence-check
version of the same idea. `setup-ts-deep-modules:89-95` also carries a
context-pointer rule — after installing a convention, link it from
CLAUDE.md/AGENTS.md, "what makes an agent discover the boundary rule instead of
tripping over it" — which is our `.claude/rules/core/02-knowledge-discoverability.md`
already, independently derived.

### Plugin manifests

`agent-skills/plugin.json:1-5` (3 fields) and
`superpowers/.claude-plugin/plugin.json:1-20` are identity metadata with no
runtime effect. `mattpocock_skills/.claude-plugin/plugin.json:21-47` is
different in kind: its `skills` array *is* the promotion boundary, enforced by a
written rule that `misc/`, `in-progress/`, `deprecated/` must never appear in
it (`mattpocock_skills/CLAUDE.md`). We have no plugin manifest and ship skills
as a directory; our promotion boundary lives in
`harness_lifecycle/inventory/skill-buckets.md:20-31`.

### Verdict

**Substitutes, not complements:** `using-agent-skills` and `ask-matt` both
answer "which skill now" and would duplicate each other. `setup-matt-pocock-
skills` and our `/adopt` are substitutes; ours is ahead.

**Complements, wrongly grouped:** `using-superpowers` is *not* a substitute for
`using-agent-skills`. UAS routes and does not enforce; USP enforces and does not
route (components.md matrix, rows 1 and 5). The `2026-07-15` rejection treated
them as the same class of artefact — that was the shallow part of the first
pass. Re-tested here on their actual mechanisms, the conclusion still lands on
reject for both, but for different and better reasons (below).

**Strongest for what:** ask-matt's relation graph is the strongest routing
mechanism; `using-superpowers`' rationalization table is the strongest
compliance mechanism; our `/adopt` is the strongest repo-bootstrap; and
`PHASE-BOUNDARIES.md` is the strongest artefact in the whole family that has
nothing to do with routing at all.

---

## Recommendation

### 1. `using-agent-skills` — **REJECT (confirm prior decision, corrected reasoning)**

The prior reason was "duplicates native platform behavior and increases context
pressure". The *duplication* half was imprecise and the *cost* half was
unquantified. Both now check out, with better evidence:

- **Quantified cost.** Measured unconditional load in a Claude Code session:
  `CLAUDE.md` 95 lines / 751 words, user `CLAUDE.md` 3/29, all seven
  `.claude/rules/**` files 268 lines / 1,862 words, `bd prime --hook-json`
  ~856 words, and native skill-description injection 1,395 words (25
  model-invocable skills) — **≈5,000 words ≈6.5K tokens**. (`AGENTS.md` is
  *not* in the Claude-side load; it is reached via Read Order or by Codex.)
  UAS adds 191 lines / ~1,150 words: **+23% on total session context, and
  +52% on the hand-authored instruction text** (`CLAUDE.md` + rules = 2,613
  words).
- **Quantified duplication.** 27 of those lines (`:165-191`) enumerate 24
  skills we do not have; 27 more (`:16-42`) route to those same names; 81
  (`:48-128`) restate `.claude/rules/core/03-ak-guidelines.md` rule-for-rule
  (mapping in components.md §3). ~10 lines are portable.
- **It does not work without the hook.** Its description (`:3`) is abstract
  ("Discovers and invokes agent skills") and matches no concrete task, so
  native description-based invocation will never surface it. Adopting the skill
  without the hook buys nothing; adopting both is item 2.

**Take: nothing.** **Leave: everything.** The two sharp devices — the literal
`ASSUMPTIONS I'M MAKING:` template (`:52-58`) and the quantify-the-downside
demand (`:79`) — are worth at most a two-line sharpening of AK §1 and §5, which
is a separate, tiny bead against our own rules file, not an adoption.

### 2. `hooks/session-start` (either repo) — **REJECT (confirm), one premise corrected**

The prior reason cited a `jq` dependency and permanent context cost. Corrections:
the `jq` objection applies only to agent-skills (`session-start.sh:9-12`);
superpowers escapes JSON in pure bash with no dependency
(`hooks/session-start:16-24`). And "we would be adding a hook mechanism" is
false — `.claude/settings.json:25-43` already registers two SessionStart hooks.
What is absent is routing *content*, not the channel.

The decision still holds because the payload is the problem, not the plumbing:
injecting UAS costs 191 lines/session forever, and injecting USP costs 62 lines
of an enforcement register that conflicts with this repo's stated instruction
style. Superpowers' `startup|clear|compact` matcher (`hooks/hooks.json:5`) is
nonetheless the one genuinely superior mechanism found here — re-injection
after `/compact` is exactly when bootstrap rules are lost. **Note it for reuse
if we ever inject anything durable at session start; do not adopt it now, since
we have nothing worth re-injecting.**

**Take: nothing now.** **Leave: both hooks.**

### 3. `ask-matt` — **DEFER, split into two parts**

The decision question was whether a router is a real need at 34 skills. Answer:
**mostly no, with one real residue.**

Our catalog is already substantially self-routing, because descriptions carry
inline cross-references — `brainstorming/SKILL.md:3` ("To open up a raw idea
first, use idea-refine; to interrogate a plan that is already written, use
grill-me"), `planning/SKILL.md:3` ("If scope or behaviour is still unsettled,
use brainstorming first"), `execution/SKILL.md:3` (points at both),
`receiving-code-review/SKILL.md:3` ("For producing a review, use code-review").
That is ask-matt's disambiguation function delivered at **zero always-on
cost**, inside text the platform already indexes. The suspected collisions in
planning/execution, the review family, the two councils
(both explicitly-triggered-only), and systematic-debugging/triage
(`triage/SKILL.md:3-4` is beads-intake-scoped and model-invocation-disabled)
are all already resolved this way.

The residue is four specific defects, and — this is the decisive point — **a
router would fix at most one of them.** Nine of our 34 skills set
`disable-model-invocation: true` and are therefore absent from the native
catalog entirely, which changes what the defects are:

1. **Real three-way collision on "stress-test".** Three *model-invocable*
   skills claim the phrase: `idea-refine/SKILL.md:3` ("stress-test assumptions
   before committing to a plan … 'stress-test my idea'"),
   `grilling/SKILL.md:3` ("wants to stress-test their thinking"), and
   `perspective-council/SKILL.md:3`, which lists "'stress-test this'" and
   "'pressure-test this'" as explicit council requests. "Stress-test this plan"
   matches all three and nothing fences them off. `perspective-council` is also
   internally inconsistent — it opens "Use ONLY when the user explicitly asks
   for the council" then defines phrases with no council semantics as such an
   ask. **This is a description-text defect, fixable in three lines.**
2. **A pointer at a locked door.** `brainstorming/SKILL.md:3` tells the model
   "to interrogate a plan that is already written, use grill-me" — but
   `grill-me/SKILL.md:4` is `disable-model-invocation: true`. The model-
   invocable interrogator is `grilling`. The cross-reference routes to a skill
   the model cannot call.
3. **A discovery gap, not a collision.** `performance-optimization/SKILL.md:4`
   is `disable-model-invocation: true`, so a plain "make this faster" with no
   regression matches *no* model-invocable skill. A router cannot fix this; it
   is an invocability setting.
4. **The grill trio** (`grill-me:3`, `grill-with-docs:3`, `grilling:3`) is
   near-identical in wording, but two of the three are slash-only, so the
   exposure is human-facing. Upstream has the missing rule and we did not adopt
   it: working directory present → `grill-with-docs`, "strictly the better one"
   (`ask-matt/SKILL.md:17`, `:77-78`).

Every one of these is an edit to text we already ship. A 90-line router would
add a fifth surface to keep in sync without repairing any of items 2–4.

**Our own catalog already demonstrates the stale-router failure mode.**
`wayfinder/SKILL.md:25` routes to `/setup-matt-pocock-skills` — a command that
does not exist here, and one this comparison recommends rejecting — and
`:77`/`:115` route to a `/research` subagent we do not have. Those are dead
pointers inside an adopted skill, undetected. Adding a hand-maintained
90-line router to a 34-skill catalog that has been rebuilt five times would
multiply exactly this failure, and upstream names the outcome: "a stale one it
still routes to, is a router that lies" (`mattpocock_skills/CLAUDE.md`).

- **Take (cheap, high value):** the *rule* from `ask-matt:17,77-78` — one
  clause added to `grill-with-docs` and `grill-me`. Bundle it with fixes for
  defects 1–3 above. These are edits to our own skills, so they belong in a
  bead, not a ledger adoption.
- **Defer (separately, on its own merits):** `PHASE-BOUNDARIES.md` — the
  five-option ordered tree (`:17-40`) and the primary-vs-secondary-source cost
  model (`:42-51`). This is not routing and does not go stale with our catalog;
  it is a context-management discipline we have no equivalent of, and it is the
  most genuinely portable artefact in this family. It should get its own
  evaluation under `context-continuity`, not be decided as part of "do we want
  a router".
- **Leave:** the router artefact itself. ~60 of 90 lines describe skills we do
  not have, and the maintenance obligation upstream states plainly
  (`mattpocock_skills/CLAUDE.md`) is a poor trade against a catalog this repo
  has rebuilt five times.

### 4. `setup-matt-pocock-skills` — **REJECT (substitute already ahead)**

`.claude/commands/adopt.md` covers it and is stronger on epistemics
(`:24-30` authority order, `:70-72` no invented verification). Two components
are worth borrowing as edits to `adopt.md`:

- **Take:** the instruction-file collision + in-place-update rule
  (`SMPS:74-82`) — never create `AGENTS.md` when `CLAUDE.md` exists, update an
  existing block in place rather than appending. `adopt.md:31-45` has no
  idempotency rule for re-runs, which is a real gap since `/adopt` is
  explicitly re-runnable.
- **Take (optional):** conditional-section suppression (`SMPS:36,51,59-61`) —
  skip the question exploration already answered.
- **Leave:** everything tracker/label/CONTEXT-layout specific; we use Beads and
  already have `CONTEXT.md` seeding at `adopt.md:42-45`.

### 5. `setup-pre-commit` / `setup-ts-deep-modules` / `scaffold-exercises` — **REJECT**

Categorically inapplicable as artefacts (no `package.json`, no TypeScript, no
CI, no build, no first-party code, structural-only gate, no frontend work), and
all three are already `adoption_scope=out-of-scope` per
`skill-buckets.md:20-31` as upstream staging-directory drafts. Answering the
"durable pattern" half of the question honestly:

- **`setup-ts-deep-modules:79-87` (prove-the-rules-bite) is a real, stack-
  independent pattern** — a guardrail must be observed *failing* on a
  deliberately introduced violation before it is called installed. It has a
  live target here: `/check-invariants` and
  `.claude/project/invariants.md` are our guardrail surface, and nothing
  currently requires demonstrating that a violating input actually trips them.
  **Take this as a one-line addition to our invariants/verification
  discipline**, cited to `setup-ts-deep-modules:79-87`, not as a skill.
- `setup-ts-deep-modules:89-95` (context-pointer after installing a convention)
  is already ours at `.claude/rules/core/02-knowledge-discoverability.md`.
  Nothing to take.
- `setup-pre-commit` and `scaffold-exercises`: **take nothing.** The generic
  shape they share (detect toolchain → install → verify) is not a pattern we
  lack, and `scaffold-exercises` depends on a private binary.

### 6. Umbrella plugin manifests — **REJECT (confirm)**

`agent-skills/plugin.json:1-5` and `superpowers/.claude-plugin/plugin.json:1-20`
are install-time identity metadata with no runtime behaviour and nothing
separable — the prior reason was correct and remains correct.
`mattpocock_skills/.claude-plugin/plugin.json:21-47` is the one that is *not*
mere metadata, because its `skills` array encodes a promotion boundary between
shipped and staging skills. But we already hold that boundary in
`harness_lifecycle/inventory/skill-buckets.md:20-31`, which is what caused three
of the skills in this very roster to be flagged out-of-scope. **Take: nothing.
Leave: all three.** Revisit only if this harness is ever distributed as a Claude
Code plugin rather than copied — at which point the manifest question is about
packaging, not curation.

### Summary table

| Item | Recommendation | Take |
|---|---|---|
| `using-agent-skills` | **Reject** (confirmed, +42% context for ~10 portable lines) | nothing |
| `hooks/session-start` (agent-skills) | **Reject** (confirmed; `jq` objection valid here) | nothing |
| `hooks/session-start` (superpowers) | **Reject**, note the `startup\|clear\|compact` matcher for future reuse | nothing now |
| `using-superpowers` | **Reject**, on corrected reasoning (62 lines, compliance not routing; register conflicts with repo style) | nothing |
| `ask-matt` — router artefact | **Reject** (stale-router liability; our `wayfinder` already carries two dead pointers) | nothing |
| `ask-matt:17,77-78` — grill disambiguation | **Adopt as a bead** against our own skill descriptions, with defects 1–3 | the rule, ~1 clause × 2 files |
| `PHASE-BOUNDARIES.md` | **Defer** to a separate `context-continuity` evaluation | evaluate on its own merits |
| `setup-matt-pocock-skills` | **Reject** (our `/adopt` is ahead) | idempotency/file-collision rule (`:74-82`) into `adopt.md` |
| `setup-pre-commit` | **Reject** | nothing |
| `setup-ts-deep-modules` | **Reject** the skill; **adopt the pattern** | prove-the-rules-bite (`:79-87`) into invariants discipline |
| `scaffold-exercises` | **Reject** | nothing |
| Plugin manifests (×3) | **Reject** (confirmed) | nothing |

No ledger entries were written. Comparison is not decision — routing any of the
above through `harness-evaluate` should cite this folder.

### NOTICED BUT NOT TOUCHING

Surfaced by this comparison, out of its scope, not modified:

- `wayfinder/SKILL.md:25` points at `/setup-matt-pocock-skills` and `:77`,
  `:115` at a `/research` subagent — neither exists in this repo. Dead pointers
  inside an adopted skill. Also violates our own
  `authoring-for-agents/SKILL.md:101-103` ("Match the conventions of the
  harness you are writing into, not the corpus you borrowed from").
- `html-artifact/SKILL.md:4` has `<!-- disable-model-invocation: true -->`
  *inside* the YAML frontmatter. HTML comments are not YAML; the parser
  currently tolerates it and the skill is model-invocable, but the intent is
  ambiguous and it is a latent parse hazard.
- `CLAUDE.md:46` routes "approved plan with bounded tasks" to
  "subagent-driven development" — no skill of that name exists; the `execution`
  skill absorbed it and is routed separately at `:53`. Stale row in the one
  situational table we have.
- `.claude/skills/ak-guide/SKILL.md:3` duplicates
  `.claude/rules/core/03-ak-guidelines.md`, which loads unconditionally every
  session — a second surface for text already in context, against our own
  one-source-of-truth rule (`authoring-for-agents/SKILL.md:73-74`).
- The three Python rule files load unconditionally (907 words) in a repo that
  `.claude/project/tools.md:33-35` itself says has no Python package.

None of these are harness-curation decisions; they are our-side hygiene beads.
