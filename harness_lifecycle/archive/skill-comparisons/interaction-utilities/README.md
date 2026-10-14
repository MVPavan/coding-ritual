# Interaction Utilities

Five small mattpocock skills whose common thread is that a **human** is inside
the mechanism — as the operator of the artifact (`wizard`), the subject being
modelled (`loop-me`), the learner (`teach`), the absent knowledge-holder
(`to-questionnaire`), or the reader who did not understand (`wait-what`). They
were carried into this comparison flagged as likely rejects. This document tests
that presumption component by component; level 3 is in
[`components.md`](components.md).

Reference paths are relative to `reference_harnesses/mattpocock_skills/skills/`
(submodule pin `84fdeff`); ours are repo-root-relative.

**Prior decisions.** `harness_lifecycle/ledger.json` holds **no entry for any of
the five** — verified across all 81 `logical_id`s. They are unadopted *and*
undecided, which is not the same as rejected. The only adjacent rulings are
`skill:skills/misc/scaffold-exercises` (rejected 2026-08-14 — "course-exercise
scaffolding for their teaching repo; no course content here"), which is `teach`'s
genus sibling, and `skill:skills/productivity/grill-me` (rejected 2026-08-11 —
"seven-line alias whose entire body is 'Run a /grilling session'"), the precedent
most often cited against tiny skills like `wait-what`.

**Where the reject presumption comes from.** Two places, both softer than they
look. `harness_lifecycle/inventory/skill-buckets.md:27` excludes `loop-me` for
sitting in upstream's `in-progress/` staging area — an *authorship-state*
judgement, not a content one — and `:213-215` excludes bucket 14 (`teach`,
`wait-what`) because its output is "consumed by people, not by the software
system". `docs/research/skill-consolidation/council-consolidation.md:26` inherits
that ruling. The bucket-14 rationale is inconsistent with what we have since
shipped: `.claude/skills/i-have-adhd/` and `.claude/skills/teach-session/` are
both installed and both produce output consumed by a person. `wizard` and
`to-questionnaire` were never excluded at all — the council kept both untouched
(`council-consolidation.md:31,109,135`); they simply have no ledger row.

## Level 1 — Placement

| Skill | Repo | Bucket | Triggers when |
|---|---|---|---|
| `wizard` | mattpocock | 9 Release, Migration & Operations (also 10) | Provisioning infra, setting up credentials or CI secrets, walking an unfamiliar third-party dashboard, or a one-off migration/cutover — with an explicit not-for: "Don't invoke this for steps the agent can perform itself" (`engineering/wizard/SKILL.md:3`). The real firing condition is narrower than the description implies: it needs a procedure with **human-only** steps *and* values worth capturing; a purely informational walkthrough would produce an empty wizard. |
| `loop-me` | mattpocock | 1 Discovery, Requirements & Decisions (also 11) | User-invoked only (`in-progress/loop-me/SKILL.md:4`) to spec a recurring personal or team workflow, in a dedicated `workflows/` workspace. The description ("Grill me about specs for the workflows I want to build, within this workspace") misfires in an engineering repo: nothing in it names software, and its workspace assumptions (`workflows/*.md`, `NOTES.md` about the user's life) do not hold in a codebase. |
| `teach` | mattpocock | 14 Human Learning, Content & Conversation | User-invoked only (`productivity/teach/SKILL.md:4`) to learn a topic over multiple sessions in a teaching workspace. **The description actively misleads** — "Teach the user a new skill or concept, within this workspace" reads like documentation generation; the body is a multi-session pedagogy system whose own examples are yoga and theoretical physics (`teach/SKILL.md:32`). |
| `to-questionnaire` | mattpocock | 1 (also 10, 14) | User-invoked only (`productivity/to-questionnaire/SKILL.md:4`) when a decision depends on knowledge held by **another person** who is not in the conversation. Description is accurate and its firing condition is unusually sharp — the presence of an absent knowledge-holder. |
| `wait-what` | mattpocock | 14 | User-invoked only (`productivity/wait-what/SKILL.md:4`), the moment a reply fails to land. Description *is* the trigger ("Stop. That last message did not land — re-pitch it"). It can only misfire by never firing: an agent cannot detect its own incomprehensibility, which is why it is written in the user's voice. |

Buckets are taken from `harness_lifecycle/inventory/skill-buckets.csv:8,9,53,70,71`.
No bucket is proposed anew here; the two placements worth contesting are
`loop-me` (filed under the `grilling` genus, which describes its *mechanism*,
while its content is closer to bucket 10 orchestration) and the bucket-14
membership discussed above.

## Level 2 — Capability profiles

### `wizard`

**Achieves** — turns a manual procedure only a human can perform into a staged,
resumable bash script that opens each URL, says what to click, captures the
values, and files them in `.env` and CI, so the procedure never has to be
re-explained to an AI again.

**Can do**
- Splits the artifact into a frozen library and an authored region, so every
  wizard has the same UX and the agent only writes stages
  (`wizard/SKILL.md:10`; `template.sh:182-185`).
- Scopes from the repo rather than the user — `.env*`, README, compose, framework
  config, and every `secrets.*`/`vars.*` in `.github/workflows/*`
  (`wizard/SKILL.md:20-21`).
- Forces per-value clarity before authoring: where the human gets it, where it is
  written, whether it is secret (`wizard/SKILL.md:25`).
- Maps click-paths to stranger-followable granularity, with an explicit
  anti-invention rule for UI it does not actually know (`wizard/SKILL.md:29`).
- **Verifies an artifact it must not run**: `bash -n`, shellcheck, chmod, then a
  static trace that every captured value lands where scoping said and every
  `set_secret` name matches a CI reference (`wizard/SKILL.md:41-43`).
- Ships genuinely non-obvious runtime affordances: WSL-aware URL opening
  (`template.sh:66-75`), hidden secret entry (`:114-126`), idempotent `.env`
  upserts and Enter-keeps-current re-run defaults (`:92-139`), `gh`-absent
  degradation into a "still to do by hand" list (`:143-180`).

**Pros** — the only member of this set whose output a human *executes*, and the
only one that solves its UX once so per-use cost is authoring alone. Its
verification section is a small, transferable discipline that survives deleting
everything else. Its scoping step is repo-grounded, which fits our read-order
norms.

**Cons** — the whole payload is the 204-line `template.sh`, which is bash,
`.env`, and `gh`-shaped; a Python/uv repo with secrets in a manager rather than
`.env` (`.claude/rules/python/safety.md`) gets less from it than a JS app repo
does. It also has no rule about *what may be automated at all* — writing secrets
to disk and pushing them to GitHub is the happy path, which sits against
`adopt.md:61-67`'s stance that trust decisions stay with the user.

### `loop-me`

**Achieves** — produces implementer-ready specs for the user's recurring
workflows by grilling them through a small vocabulary of trigger, checkpoint,
push-right, and brief.

**Can do**
- Composes rather than restates: it is `/grilling` pointed at one output type
  (`loop-me/SKILL.md:8`).
- Supplies the **loop lens** — spotting recurrence as the precondition for
  delegation — and asks the agent to propose loops the user has not noticed
  (`:12`).
- Names four terms and immediately guards against them becoming a checklist:
  "Mandate nothing structural" (`:18`).
- Gives a placement rule for human gates (**push right**, `:22`) and a content
  rule for what a gate presents (**brief, not draft**, `:23`).
- Sets a hard done-condition: an implementer could build it without asking a
  single question (`:27`).

**Pros** — the highest ratio of durable idea to line count in the set. Its
vocabulary is about *automation design*, which is what our harness does, even
though its examples are about a person's week. `push right` and `brief` are the
two components in this whole comparison that our harness most visibly lacks
(see `components.md` → *Checkpoint placement*, *Brief, not draft*).

**Cons** — genuinely unfinished: upstream keeps it in `in-progress/`, and it
assumes a `workflows/`+`NOTES.md` workspace that has no place in a code repo. It
also collides head-on with our existing vocabulary — "brief" already means an
agent-facing task input in four of our skills. And its own premise (a workflow
graph with triggers and loops) is something we have deliberately ruled out:
`docs/ideas/workflow-graphs.md:52-54` — "No loops in the graph format… otherwise
it becomes a programming language / workflow engine."

### `teach`

**Achieves** — runs a multi-session learning programme in a stateful workspace,
grounded in a stated mission and trusted sources, producing HTML lessons pitched
inside the learner's zone of proximal development.

**Can do**
- Mission-grounds every teaching decision and names the failure without it —
  abstract lessons and no basis for choosing what comes next
  (`teach/SKILL.md:71-77`).
- Refuses parametric knowledge: sources go into `RESOURCES.md` first, lessons
  carry citations (`:30`, `:95`).
- Applies named learning science — fluency vs storage strength, retrieval
  practice, spacing, interleaving, ZPD (`:34-45`, `:81-89`).
- Maintains an asset component library with reuse as the default, shared
  stylesheet first (`:63-69`).
- Ships four format files: mission, ADR-shaped learning records, glossary, and
  annotated resources with an explicit `## Gaps` section.
- Bans answer leakage through option length and formatting (`:110`).

**Pros** — by far the most complete artefact in the set, and the only one with a
theory behind its choices rather than a preference.

**Cons** — it is a product for teaching humans a topic, not an engineering skill;
three of its four format files duplicate things we already adopted from the same
author (`CONTEXT-FORMAT.md`, `ADR-FORMAT.md`) or already encode
(`learnings.md:3-5`). Against our own `teach-session`, which explains *this
session's work* in one sitting, `teach` answers a different question entirely —
it is not a stronger version of what we have.

### `to-questionnaire`

**Achieves** — converts a decision the user cannot resolve alone into a Markdown
document aimed at the one person who holds the missing knowledge, built for a
single asynchronous pass.

**Can do**
- Inverts the interview: "**Grill the send, not the subject.** Interview the user
  only about the _send_, which they can always answer"
  (`to-questionnaire/SKILL.md:9`).
- Bounds the interview to two exchanges — who, and what you need back — each with
  a done-when (`:11`, `:13`).
- Orders questions most-important-first *because* async gives you one pass
  (`:19`).
- Ships question hygiene that survives the topic: one idea per question, an
  answer stub beneath each, a *why this matters* line only where the question
  could be misread, and an explicit "'I don't know' is useful — flag it rather
  than skipping" instruction to the recipient (`:35`, `:39`).

**Pros** — the sharpest firing condition in the set, and the only capability here
with **no** counterpart anywhere in our harness. Both prior council members found
it non-overlapping independently (`council-consolidation.md:109`;
`member-opus-5.md:17`). It is also cheap: 53 lines, no assets, no dependencies.

**Cons** — narrow; it fires only when a real third party exists, which in a
solo-operator repo may be rare. Its output lands as a loose
`to-questionnaire-<slug>.md` in the working directory, which does not match our
docs conventions. And its interview is arguably *too* thin — two exchanges may
under-specify a genuinely complex ask compared with running `grilling` about the
send.

### `wait-what`

**Achieves** — lets a human stop the agent mid-flow and force a re-pitch of the
last message in constrained language with the missing context restored.

**Can do**
- Fires on a condition an agent cannot self-detect, which is why it is written in
  the user's voice (`wait-what/SKILL.md:7`).
- Names a real controlled-language standard (ASD-STE100) rather than saying
  "simpler".
- Re-anchors the re-pitch on the project's ubiquitous language in `CONTEXT.md`.
- Costs nothing until used (`disable-model-invocation: true`, `:4`).

**Pros** — the cheapest possible fix for a failure mode our harness has no other
answer to. Its `CONTEXT.md` half already has full support here (`CLAUDE.md:17`),
so only the register half is new.

**Cons** — seven lines, one of which is the trigger; there is no mechanism to
review, and the whole thing is one instruction. It is also the member most
exposed to the `grill-me` precedent (a 7-line alias, rejected 2026-08-11) — though
that rejection was for *redundancy with an installed skill*, and no installed
skill here does what this does.

## Verdict

**Not one set.** These five share a shape, not a capability, and the honest
answer differs per member. Against our harness:

- **`to-questionnaire` — gap-fill, and the only clean one.** Every interrogation
  skill we ship targets the user in the room, and two of them explicitly forbid
  the questionnaire form (`grill-me/SKILL.md:104,130`;
  `brainstorming/references/interviewing.md:75`). Those rules are correct for a
  present respondent and exactly wrong for an absent one. The smallest durable
  borrowable pattern is **one paragraph, not the skill**: *when the knowledge
  sits with someone who is not here, stop interviewing the user about the
  subject; interview them only about the send (who, and what you need back), and
  write the questions at the gap* (`to-questionnaire/SKILL.md:9,11,13`). The
  document template is nice-to-have; the trigger and the inversion are the value.

- **`wizard` — extend, on a seam we already cut.** `wayfinder/SKILL.md:80`
  already types the situation ("provisioning access… it hands the human a precise
  checklist (HITL)") and stops at prose. The smallest durable borrowable pattern
  is `wizard`'s **verification discipline for an artifact the agent must not
  run** — static trace instead of execution, plus the name-match check between
  every `set_secret` and every `secrets.*` reference in CI
  (`wizard/SKILL.md:41-43`) — which generalises to any generated script. The
  `template.sh` library is a separate, larger question, and its `.env`+`gh`
  assumptions cut against `.claude/rules/python/safety.md` and
  `adopt.md:61-67`.

- **`loop-me` — gap-fill on two components, duplicate on the rest.** The grilling
  machinery is already ours (`grilling` adopted 2026-08-11) and the workflow
  workspace conflicts with `docs/ideas/workflow-graphs.md:52-54`. But two
  components have no counterpart: **push right** (`:22`) — defer the human gate
  as far as it will go so the human is asked once, late, with everything prepared
  — and **brief, not draft** (`:23`) — a checkpoint presents a decision-ready
  summary with a link down to the asset, never the raw output. Our nearest
  neighbours are a once-per-session Decision Summary and a tickets-only
  link-down rule. Its `in-progress` status is a reason to borrow the two
  sentences rather than the file, not a reason to skip reading it — which is
  where the original triage stopped (`skill-buckets.md:27`).

- **`teach` — duplicate by structure, with three orphan glossary rules.** Its
  learning-record format is a structural clone of the `ADR-FORMAT.md` we already
  adopted, and its evidence gate is already in `learnings.md:3-5`. Its glossary
  format shares a lineage with our `CONTEXT-FORMAT.md` and agrees with it on
  every rule but three, none of them learner-specific: *use the glossary's own
  terms inside other definitions*, *flag ambiguities and record the resolution*,
  and *revise in place, no stale entries* (`GLOSSARY-FORMAT.md:32,34,35`). That
  is the whole borrowable residue — three lines for
  `.claude/skills/domain-modeling/CONTEXT-FORMAT.md`. The pedagogy itself is out
  of scope by kind, and `teach-session` is not a weaker version of it; they
  answer different questions.

- **`wait-what` — small gap-fill, honestly a judgement call.** We have
  `i-have-adhd` (a standing style contract) and `teach-session:18` (learner-asked
  eli5, session-scoped). Neither covers "the user read it and did not
  understand"; `i-have-adhd:106` responds to "explain" by making the answer
  *longer*, not simpler. The borrowable pattern is one clause: **re-pitch in a
  named controlled language (ASD-STE100), not in vaguely "simpler" words**. That
  clause could live inside `i-have-adhd` as a fifth override rather than as a
  new skill — which would also dodge the `grill-me` seven-line-alias precedent.

**Substitutes vs complements.** Nothing in this set substitutes for anything else
in it. `wizard` and `to-questionnaire` are complements — both extract from a
human, one actions, one knowledge — and upstream's `human-in-the-loop` genus
(`skill-buckets.md:249`) is right about that. `loop-me` is a `grilling` variant
by mechanism but an orchestration skill by content. `teach` and `wait-what` share
only an audience.

**Strongest for what.** `teach` is the strongest artefact and the least
applicable. `wizard` is the strongest engineering fit and the heaviest to carry.
`to-questionnaire` has the best ratio of gap filled to lines added.
`loop-me` has the best ratio of durable idea to lines read. `wait-what` is the
cheapest thing here that is not already ours.

**The presumption was 2/5 right.** `teach` is a genuine reject on scope, with a
three-line residue. `wizard` is not a reject — it is an unbuilt extension of a
seam `wayfinder` already names. `to-questionnaire` was never rejected by anyone
and fills the cleanest gap in the set. `loop-me` was dropped on authorship state
without its components being read. `wait-what` was dropped on a bucket rationale
that two installed skills already contradict. None of the five has a ledger row,
so per `.claude/rules/harness-lifecycle/curation.md` all five will keep
resurfacing on `/harness-scan` until decisions are recorded — but recording them
is the `harness-evaluate` skill's job, not this document's.
