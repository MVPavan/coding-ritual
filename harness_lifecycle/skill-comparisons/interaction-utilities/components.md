# Interaction Utilities — Level 3 Components

Column keys:

| Key | Skill |
|---|---|
| `WIZ` | mattpocock — `skills/engineering/wizard/` (`SKILL.md` 44 lines + `template.sh` 204 lines) |
| `LOOP` | mattpocock — `skills/in-progress/loop-me/SKILL.md` (32 lines) |
| `TEACH` | mattpocock — `skills/productivity/teach/` (`SKILL.md` 139 lines + 4 FORMAT files) |
| `QUEST` | mattpocock — `skills/productivity/to-questionnaire/SKILL.md` (53 lines) |
| `WAIT` | mattpocock — `skills/productivity/wait-what/SKILL.md` (7 lines) |

Reference paths are relative to `reference_harnesses/mattpocock_skills/skills/`.
Our files are cited from the repo root. Submodule pin: `84fdeff`.

There is no single "ours" column: the five reference skills do not share one
counterpart. Each matrix carries a *Nearest thing we have* column instead, and
the shared-component analysis argues each row.

## Component inventory

### `WIZ` — wizard

`agents/openai.yaml` carries display metadata only, no behaviour
(`engineering/wizard/agents/openai.yaml:1-3`).

| Component | Citation |
|---|---|
| Definition: a bash script that walks a human through a manual procedure, opens each URL, says what to click, captures values, writes them where they belong, confirms at every stage | `wizard/SKILL.md:8` |
| **Library/stages split** — everything above the `STAGES` marker is identical in every wizard and is never hand-edited; "your job is only to scope the procedure and author its stages" | `wizard/SKILL.md:10`; `wizard/template.sh:6-7,182-185` |
| **Ephemeral by default** — built for one run, deleted when done; commit only when the user wants a repeatable setup path | `wizard/SKILL.md:12` |
| Step 1 scope: read the repo before asking cold — `.env*`, README, compose, framework config | `wizard/SKILL.md:18-21` |
| **CI-reference harvest** — every `secrets.*` / `vars.*` reference in `.github/workflows/*` is a value the wizard must produce | `wizard/SKILL.md:21` |
| Migration variant of scoping: current state, target state, and the irreversible actions between them | `wizard/SKILL.md:22` |
| Confirm the ordered stage list with the user before authoring; they may add, drop, reorder | `wizard/SKILL.md:23` |
| Step-1 done-when: per captured value, (a) where the human gets it, (b) where it is written, (c) whether it is secret | `wizard/SKILL.md:25` |
| Step 2 journey mapping to click-path granularity ("Dashboard → Developers → API keys → Reveal test key → copy") | `wizard/SKILL.md:29` |
| **Anti-invention rule** — where you don't know the current UI or exact command, say so and ask or check docs; "never invent steps that may not exist" | `wizard/SKILL.md:29` |
| Step-2 done-when: every stage traces to instructions a stranger could follow | `wizard/SKILL.md:31` |
| Step 3 authoring: copy the template, one `stage` per step in dependency order, set `TOTAL_STAGES` | `wizard/SKILL.md:35` |
| Authoring bar: open the URL *before* asking for its value; `ask_secret` for secrets; `write_env` every persisted value; `set_secret` only what CI needs; `confirm` before any irreversible action | `wizard/SKILL.md:37` |
| One focused task per stage, *because* each stage clears the screen and anything scrolled away is lost | `wizard/SKILL.md:37` |
| Step 4 syntax gate: `bash -n`, `shellcheck` if available, `chmod +x` | `wizard/SKILL.md:41-42` |
| **Do-not-execute rule** — never run it end-to-end yourself; it opens browsers and blocks on human input | `wizard/SKILL.md:43` |
| **Static trace instead of execution** — every scoped value is captured and lands where step 1 said, and every `set_secret` name exactly matches a `secrets.*` reference in CI | `wizard/SKILL.md:43` |
| Hand-off: tell the user how to run it; if repeatable, commit and link from the README so the next person runs the script instead of asking an AI | `wizard/SKILL.md:44` |
| Library: TTY/`tput`-guarded colour, degrading to empty strings when not a terminal | `wizard/template.sh:15-20` |
| Library: `_clear` is a no-op when stdout is not a terminal, so piped logs stay readable | `wizard/template.sh:33-36` |
| Library: `banner` states stage count and promises resumability ("Stop any time with Ctrl-C and re-run later — it remembers values already saved") | `wizard/template.sh:39-47` |
| Library: `stage` prints `Stage N/TOTAL`, an always-visible progress counter | `wizard/template.sh:51-56` |
| Library: `open_url` cross-platform incl. WSL (`wslview`, `explorer.exe`, `xdg-open`, `open`), degrading to a printed URL | `wizard/template.sh:66-75` |
| Library: `pause` / `confirm` (y/N gate) | `wizard/template.sh:78-89` |
| Library: **idempotent re-run** — `ask`/`ask_secret` read the existing `.env` value and offer it as an Enter-keeps default | `wizard/template.sh:92-126` |
| Library: `ask_secret` hides input (`read -rs`) | `wizard/template.sh:114-126` |
| Library: `write_env` upserts `KEY=VALUE` via a temp file, replacing any existing line | `wizard/template.sh:130-139` |
| Library: `set_secret` / `set_var` check `gh` presence *and* `gh auth status`, and on failure record the item in `SKIPPED` with the manual command instead of failing the run | `wizard/template.sh:143-167` |
| Library: `finish` summary — values written, secrets set, and an explicit **"still to do by hand"** list | `wizard/template.sh:170-180` |
| Worked example stage (Stripe keys) marked for replacement | `wizard/template.sh:187-202` |

### `LOOP` — loop-me

Upstream ships this under `in-progress/`, its own staging area, and marks it
`disable-model-invocation: true` (`in-progress/loop-me/SKILL.md:4`;
`agents/openai.yaml:4-5`).

| Component | Citation |
|---|---|
| Composes an existing skill rather than restating it: "run a stateful `/grilling` session whose only output is **workflow** specs", using grilling's pacing (a round at a time, recommended answer attached) | `loop-me/SKILL.md:8` |
| Specs are live objects — create, edit, and delete them as the grilling resolves things | `loop-me/SKILL.md:8` |
| **The loop lens** — a life is loops within loops; seeing the recurrence is what reveals what is worth delegating | `loop-me/SKILL.md:12` |
| Agent proposes loops the user has not noticed | `loop-me/SKILL.md:12` |
| Workflow = the spec of one loop; `workflows/*.md` is the source of truth | `loop-me/SKILL.md:14` |
| **Anti-checklist rule** — the vocabulary is reached for only when a workflow calls for it; "Mandate nothing structural": no AI, no checkpoint, no schedule unless the grilling shows it | `loop-me/SKILL.md:18` |
| **Trigger** — event vs schedule, with a stated default (event-triggering is usually more efficient) | `loop-me/SKILL.md:20` |
| **Checkpoint** — the named human-in-the-loop verification point; some workflows have none and some use no AI at all | `loop-me/SKILL.md:21` |
| **Push right** — defer the checkpoint as far as it will go; do maximal work before involving the human so they are asked once, late, with everything prepared | `loop-me/SKILL.md:22` |
| **Brief** — what a checkpoint presents: a decision-ready summary of what was produced and why, plus a link *down* to the asset; never the raw output. "The user reads a brief, not a draft." Speed of review is imperative | `loop-me/SKILL.md:23` |
| Definition of done: an implementer agent could build the spec without asking a single question; nothing is done while a question remains | `loop-me/SKILL.md:27` |
| Workspace: `workflows/*.md` one spec per workflow | `loop-me/SKILL.md:31` |
| `NOTES.md` — the user's tools, channels, and their own terminology; interview them about their world before specifying anything when it is thin | `loop-me/SKILL.md:32` |
| Sharpen fuzzy terms into canonical ones as they surface and record them | `loop-me/SKILL.md:32` |

### `TEACH` — teach

| Component | Citation |
|---|---|
| Declares the request **stateful and multi-session**, not a one-shot explanation | `teach/SKILL.md:8` |
| Workspace file map: `MISSION.md`, `reference/*.html`, `RESOURCES.md`, `learning-records/*.md`, `lessons/*.html`, `assets/*`, `NOTES.md` | `teach/SKILL.md:12-20` |
| Philosophy triad — knowledge (from trusted resources), skills (from interactive lessons), wisdom (from other practitioners) | `teach/SKILL.md:24-28` |
| **"Never trust your parametric knowledge"** — until `RESOURCES.md` is populated, the job is finding high-quality sources | `teach/SKILL.md:30` |
| Topic-dependent balance: physics is knowledge-heavy, yoga is skills-heavy | `teach/SKILL.md:32` |
| **Fluency vs storage strength** — fluency gives an illusory sense of mastery; storage strength is the goal | `teach/SKILL.md:34-41` |
| Desirable difficulty via retrieval practice, spacing, interleaving | `teach/SKILL.md:43-45` |
| Lesson unit: one self-contained HTML file, `NNNN-dash-case.html`, sequential | `teach/SKILL.md:49` |
| Lessons must be beautiful ("Think Tufte") because the user returns to them | `teach/SKILL.md:51` |
| Lesson sizing: short, completable fast, bounded by working memory, one tangible win, tied to the mission, inside the ZPD | `teach/SKILL.md:53` |
| Open the lesson file for the user via a CLI command | `teach/SKILL.md:55` |
| Cross-linking via HTML anchors; one recommended primary source per lesson; a standing reminder that the agent is the teacher and takes follow-ups | `teach/SKILL.md:57-61` |
| **Asset component library** — reuse is the default; read `./assets/` before authoring; new reusable things become components, never inlined | `teach/SKILL.md:63-67` |
| Shared stylesheet is the first component every workspace earns, so lessons look like one course | `teach/SKILL.md:69` |
| Mission grounding, with the failure named: without it, knowledge is ungrounded, lessons feel abstract, and there is no basis for choosing what is next | `teach/SKILL.md:71-77` |
| Missions may change; confirm with the user, update `MISSION.md`, and write a learning record | `teach/SKILL.md:79` |
| **Zone of proximal development** computed from the learning records plus the mission | `teach/SKILL.md:81-89` |
| Knowledge-then-practice ordering; only the knowledge the skill requires | `teach/SKILL.md:93` |
| Lessons "littered with citations" to raise trust | `teach/SKILL.md:95` |
| Difficulty is the enemy for knowledge acquisition, the tool for skill acquisition | `teach/SKILL.md:97-103` |
| Feedback loop as tight as possible, ideally automatic | `teach/SKILL.md:108` |
| **Quiz answers all the same length in words and characters — no formatting clues to the answer** | `teach/SKILL.md:110` |
| Wisdom delegated to communities; find high-reputation ones; respect an opt-out | `teach/SKILL.md:112-120` |
| Reference documents = compressed essence; lessons are rarely revisited, references are | `teach/SKILL.md:122-126` |
| Glossary is binding once created — adhered to in every lesson | `teach/SKILL.md:136` |
| `NOTES.md` records how the user wants to be taught | `teach/SKILL.md:138-139` |
| MISSION format: Why / Success looks like / Constraints / **Out of scope** (out-of-scope protects the ZPD) | `teach/MISSION-FORMAT.md:7-23` |
| MISSION rules: one mission per workspace; concrete over abstract; push back on vagueness ("a bad mission is worse than no mission"); revise when reality shifts; keep it under a screen | `teach/MISSION-FORMAT.md:27-31` |
| Learning records = ADRs for learning; sequential `NNNN-slug.md`; directory created lazily | `teach/LEARNING-RECORD-FORMAT.md:3-5` |
| Minimal template (1-3 sentences) with "that is the whole format" | `teach/LEARNING-RECORD-FORMAT.md:9-15` |
| Optional Status / Evidence / Implications sections only when they add value | `teach/LEARNING-RECORD-FORMAT.md:19-23` |
| Four write-triggers: demonstrated understanding, disclosed prior knowledge, corrected misconception, mission shift | `teach/LEARNING-RECORD-FORMAT.md:31-36` |
| **"Coverage is not learning. Wait for evidence."** plus two more non-qualifiers (already in the glossary; activity logs) | `teach/LEARNING-RECORD-FORMAT.md:38-42` |
| Supersession: mark `superseded by LR-NNNN` rather than delete — the evolution is signal | `teach/LEARNING-RECORD-FORMAT.md:44-46` |
| Glossary structure with `_Avoid_` aliases | `teach/GLOSSARY-FORMAT.md:7-25` |
| Glossary rule: add a term only once the user can use it correctly — the glossary is a record of compressed knowledge, not a dictionary | `teach/GLOSSARY-FORMAT.md:29` |
| Glossary rule: be opinionated — pick the best word, list the rest as aliases to avoid | `teach/GLOSSARY-FORMAT.md:30` |
| Glossary rule: tight definitions — what the term IS, not what it does | `teach/GLOSSARY-FORMAT.md:31` |
| **Glossary rule: use the glossary's own terms inside other definitions** — this is what compresses later terms | `teach/GLOSSARY-FORMAT.md:32` |
| Glossary rule: group under subheadings when clusters emerge | `teach/GLOSSARY-FORMAT.md:33` |
| **Glossary rule: flag ambiguities explicitly and record the resolution** ("in this workspace, 'set' always means a working set") | `teach/GLOSSARY-FORMAT.md:34` |
| **Glossary rule: revise in place as understanding deepens; no stale entries** | `teach/GLOSSARY-FORMAT.md:35` |
| Resources: Knowledge / Wisdom split, high-trust only, annotate every entry, explicit `## Gaps` section, prune ruthlessly, record community opt-outs | `teach/RESOURCES-FORMAT.md:7-32` |

### `QUEST` — to-questionnaire

| Component | Citation |
|---|---|
| Artifact definition: a Markdown document handed to **one** person to fill in async, or filled out together in a meeting; the recipient holds knowledge the user lacks | `to-questionnaire/SKILL.md:7` |
| **"Grill the send, not the subject."** Interview the user only about the *send* — what they can always answer — and aim the document's questions at the gap between recipient knowledge and user need | `to-questionnaire/SKILL.md:9` |
| Step 1 — who is it going to: role, expertise, relationship, **in one exchange**; this fixes tone and how much context the document must carry | `to-questionnaire/SKILL.md:11` |
| Step 1 done-when: you know who the recipient is and what they know that the user does not | `to-questionnaire/SKILL.md:11` |
| Step 2 — what do you need back: the decisions or facts the user cannot resolve alone, in one exchange; done when you have a concrete list of what the user must walk away able to decide | `to-questionnaire/SKILL.md:13` |
| Step 3 — write to `to-questionnaire-<slug>.md` in the current directory and report the path; done when every step-2 item is covered by a question | `to-questionnaire/SKILL.md:15` |
| Framing: a **discovery** questionnaire — the user lacks context, the recipient holds it | `to-questionnaire/SKILL.md:19` |
| **Most-important-first ordering, because async means you may only get one pass** | `to-questionnaire/SKILL.md:19` |
| Theme grouping under `##` headings once past a handful of questions | `to-questionnaire/SKILL.md:19` |
| Template header: Purpose + the decision riding on it; From / To / how the answers will be used | `to-questionnaire/SKILL.md:23-27` |
| Template `## Context`: one paragraph orienting a recipient who was not in the user's head — "enough to answer well, not a page" | `to-questionnaire/SKILL.md:29-31` |
| Template `## How to answer`: deadline and rough effort; **partial answers and "I don't know" are useful — flag uncertainty rather than skipping** | `to-questionnaire/SKILL.md:33-35` |
| Question rules: one idea per question, never compound; an answer stub directly beneath; a one-line *why this matters* **only** where the question could be misread or invite a throwaway answer | `to-questionnaire/SKILL.md:39` |
| Worked question example with the `>` answer stub | `to-questionnaire/SKILL.md:41-47` |
| Closing `## Anything else?` catch-all | `to-questionnaire/SKILL.md:49-51` |

### `WAIT` — wait-what

| Component | Citation |
|---|---|
| Trigger is the human's comprehension failure, not a task state: "Stop. That last message did not land — re-pitch it." | `wait-what/SKILL.md:3` |
| User-invoked only (`disable-model-invocation: true`), so it carries no context cost until fired | `wait-what/SKILL.md:4`; `wait-what/agents/openai.yaml:4-5` |
| Repair move 1 — supply the missing context ("give me a little bit of context") | `wait-what/SKILL.md:7` |
| Repair move 2 — **a named controlled-language standard, ASD-STE100 Simplified Technical English**, rather than a vague instruction to simplify | `wait-what/SKILL.md:7` |
| Repair move 3 — re-anchor on the project's ubiquitous language from `CONTEXT.md` | `wait-what/SKILL.md:7` |
| Written in the user's voice, so invoking it *is* the utterance | `wait-what/SKILL.md:7` |

## Cross-skill matrix

Rows are the merged component list. `✓` present, `~` variant (present but
different mechanism or strength), `—` absent.

| Component | WIZ | LOOP | TEACH | QUEST | WAIT | Nearest thing we have |
|---|:--:|:--:|:--:|:--:|:--:|---|
| Produces an artifact for a **human**, not the codebase | ✓ | ~ | ✓ | ✓ | ~ | `.claude/skills/html-artifact/SKILL.md:3` — documents for human reading |
| Artifact targets a **third party**, not the invoking user | — | — | — | ✓ | — | **none** |
| Artifact is **executed** by a human step by step | ✓ | — | ~ | — | — | `.claude/skills/wayfinder/SKILL.md:80` — "hands the human a precise checklist (HITL)"; prose, not a script |
| Stateful multi-session workspace with named files | — | ✓ | ✓ | — | — | `.claude/skills/execution/references/task-engine.md:36-47` (file-recoverable rounds); Beads for work state |
| Interview the user before producing anything | ~ | ✓ | ✓ | ✓ | — | `grilling/SKILL.md:6-22`, `grill-me/SKILL.md:40-111`, `brainstorming/SKILL.md:38` |
| Interview scoped to what the user **can** answer | — | — | — | ✓ | — | **none** — `grilling/SKILL.md:20` splits facts (agent) from decisions (user), but assumes the user holds the decisions |
| Explicit per-step "done when" gates | ✓ | ~ | — | ✓ | — | `.claude/skills/planning/SKILL.md:50`; `CLAUDE.md:113-119` |
| Read the repo before asking the user | ✓ | — | — | — | — | `grilling/SKILL.md:20` "don't ask the user for anything you could look up yourself"; `CLAUDE.md:17-24` |
| Anti-invention rule for external systems | ✓ | — | ~ | — | — | `CLAUDE.md:79` — docs-researcher, "never invent APIs" |
| Generated-vs-authored split with a never-hand-edit boundary | ✓ | — | ~ | — | — | generated `skill-router` catalog (`.claude/scripts/skill-catalog.py`, invariant 8) |
| Idempotent / resumable across interruptions | ✓ | — | ~ | — | — | `execution/references/task-engine.md:44-47` for agent work; **none** for human procedures |
| Verify an artifact the agent must **not** run | ✓ | — | — | — | — | **none** |
| Human-in-the-loop as named ticket/stage state | ~ | ✓ | — | — | — | `wayfinder/SKILL.md:75` HITL vs AFK |
| The word "checkpoint" | ~ | ✓ | — | — | — | `.claude/rules/core/03-ak-guidelines.md:89-92` — **different referent**, see below |
| Defer the checkpoint as late as possible (**push right**) | ~ | ✓ | ~ | — | — | **none** |
| **Brief, not draft** — decision-ready summary + link down to the asset | ✓ | ✓ | — | ✓ | — | `grill-me/references/decision-summary-template.md`; name collision, see below |
| Trigger taxonomy (event vs schedule) | — | ✓ | — | — | — | **none** — `docs/ideas/workflow-graphs.md:52-54` rules loops out of the graph format by design |
| Anti-checklist rule ("mandate nothing structural") | — | ✓ | — | ~ | — | `CLAUDE.md:46` "match ceremony to scope and risk" |
| Spec is done when an implementer needs no questions | — | ✓ | — | ~ | — | `grilling/SKILL.md:22` empty-frontier gate; `planning/SKILL.md:50` |
| Glossary/ubiquitous-language maintenance | — | ~ | ✓ | — | ~ | `domain-modeling/CONTEXT-FORMAT.md:25-30`; `CLAUDE.md:17` |
| Decision-record format with supersession | — | — | ✓ | — | — | `domain-modeling/ADR-FORMAT.md:21,38-46` |
| Evidence gate before recording a durable note | — | — | ✓ | — | — | `.claude/project/learnings.md:3-5` |
| Curated trusted-source list with annotations and gaps | — | — | ✓ | — | — | `.claude/project/docs-index.md`; `docs/research/` |
| Learning-science scheduling (spacing, interleaving, ZPD) | — | — | ✓ | — | — | **none** |
| Answer-leak-proof quizzing | — | — | ~ | — | — | `teach-session/SKILL.md:20` — different leak, see below |
| Mastery gate before advancing | — | — | ✓ | — | — | `teach-session/SKILL.md:9,22` |
| Register change on the learner's demand | — | — | ~ | — | ✓ | `teach-session/SKILL.md:18` — eli5 / eli14 / elii, session-scoped |
| Named controlled-language standard | — | — | — | ~ | ✓ | **none** |
| Batched one-pass questioning | — | ~ | — | ✓ | — | `grilling/SKILL.md:8` asks the whole frontier per round |
| **Anti-questionnaire rule** (ours, not theirs) | — | — | — | ✗ | — | `grill-me/SKILL.md:104,130`; `brainstorming/references/interviewing.md:75` |

`✗` marks the one row where a reference skill does the thing our harness
explicitly forbids — see *Interview scope* below.

## Shared-component differences

### Brief, not draft — `LOOP` ✓ · `WIZ` ✓ · `QUEST` ✓ · ours partial

`LOOP` states it as a definition: a checkpoint presents "a tight,
decision-ready summary — what was produced, why, and a link down to the asset
itself — never the raw output. The user reads a brief, not a draft"
(`loop-me/SKILL.md:23`). `WIZ` realises the same idea mechanically rather than
by rule: `finish` prints what was written, what was set, and a separate "still
to do by hand" list (`wizard/template.sh:170-180`), and each `stage` clears the
screen so only the current decision is visible (`wizard/template.sh:51-56`).
`QUEST` realises it in the artifact's header — Purpose, the decision riding on
it, and how the answers will be used (`to-questionnaire/SKILL.md:25-27`).

`LOOP`'s is the strongest because it is the only one stated as a general
constraint on every human-facing hand-off, and because it names the failure
mode precisely — the raw output being dumped where a summary belonged. The
others only instantiate it once each.

We have one instance and no rule. The instance is `grill-me`'s Decision Summary
(`.claude/skills/grill-me/SKILL.md:111`; template at
`.claude/skills/grill-me/references/decision-summary-template.md:15-56`), which
is decision-ready by construction but produced once at the endgame, not at every
hand-off. `wayfinder/SKILL.md:71` carries the link-down half — "Assets created
while resolving a ticket are linked from the issue, not pasted in" — for tickets
only. `CLAUDE.md:113-119` requires reporting actual command results but never
says *summarise, link down, never paste the raw artifact*.

**Vocabulary collision, if this is ever borrowed.** "Brief" is already taken here
and means the opposite direction of travel — an *agent-facing input*:
`.claude/skills/model-council/SKILL.md:25` ("Write one shared task brief"),
`.claude/skills/codebase-design/DESIGN-IT-TWICE.md:23`,
`.claude/skills/code-review/SKILL.md:19`, and `.claude/project/brief.md`.
`LOOP`'s brief is a human-facing output. Borrowing the term unrenamed would
collide with four existing surfaces.

### Checkpoint placement — `LOOP` ✓ · `WIZ` ~ · `QUEST` ~

`LOOP` gives the placement a rule and a name: **push right** — "defer the
checkpoint as far as it will go… so they are asked once, late, with everything
prepared" (`loop-me/SKILL.md:22`), sitting on top of a checkpoint definition
that explicitly allows zero checkpoints (`loop-me/SKILL.md:21`). `WIZ` inverts
it by necessity — a wizard is *all* checkpoint — but still batches: the agent
does every readable-from-repo discovery itself before the human is asked
anything (`wizard/SKILL.md:18-21`), and `confirm` gates only irreversible
actions (`wizard/SKILL.md:37`). `QUEST` batches into a single async round
because it may only get one (`to-questionnaire/SKILL.md:19`).

`LOOP`'s is stronger as a transferable rule; `WIZ`'s is stronger as evidence,
since "read `.env*`, README, compose, and every `secrets.*` in the workflows
first" is a checkable instruction while "push right" is a disposition.

**Our "checkpoint" is a different referent.** `.claude/rules/core/03-ak-guidelines.md:89-92`
("Checkpoint after every significant step — summarize what was done, what's
verified, what's left") is the *agent* restating its own state so it can resume;
it does not involve a human at all. The human-gate concept lives elsewhere and
unnamed: `wayfinder/SKILL.md:75` types a whole ticket HITL or AFK,
`planning/SKILL.md:50` has an approval gate on the phase graph, and
`.claude/skills/execution/references/workstream-mode.md:50-58` enumerates what is
auto-approved. What none of them supply is `LOOP`'s *placement* rule — where in
the work the human gate should sit, and the instruction to move it as late as it
will go.

### Anti-invention about external systems — `WIZ` ✓ · `TEACH` ~ · ours ✓

`WIZ`: "Where you don't actually know the current UI or the exact command, say
so and ask the user or check the docs — never invent steps that may not exist"
(`wizard/SKILL.md:29`). `TEACH`: "Never trust your parametric knowledge"
(`teach/SKILL.md:30`), enforced structurally by requiring `RESOURCES.md` to be
populated first and lessons to carry citations (`teach/SKILL.md:95`). Ours:
`CLAUDE.md:79` routes library/SDK/API/CLI uncertainty to `docs-researcher` and
says "never invent APIs".

`TEACH`'s is the strongest of the three because it is structural rather than
exhortative — the sources must exist in a file before output is written, and
every claim carries a link. `WIZ`'s adds the part ours lacks: third-party
**UI flows** (dashboard click-paths), which no documentation researcher can
verify and which are the most drift-prone thing a wizard encodes.

### Glossary discipline — `TEACH` ✓ · ours ✓ (same lineage, three rules missing)

`teach/GLOSSARY-FORMAT.md` and our adopted
`.claude/skills/domain-modeling/CONTEXT-FORMAT.md` are the same upstream author's
template, and they agree on the two rules ours carries: be opinionated with
`_Avoid_` aliases (`GLOSSARY-FORMAT.md:30` ≡ `CONTEXT-FORMAT.md:27`) and keep
definitions tight, defining what a term IS (`GLOSSARY-FORMAT.md:31` ≡
`CONTEXT-FORMAT.md:28`), plus subheading grouping (`GLOSSARY-FORMAT.md:33` ≡
`CONTEXT-FORMAT.md:30`).

Three rules exist only on the teaching side and are not learner-specific:

1. **Use the glossary's own terms inside other definitions**
   (`GLOSSARY-FORMAT.md:32`) — the compression mechanism that makes later terms
   cheap to define. Ours has no such rule.
2. **Flag ambiguities explicitly and record the resolution**
   (`GLOSSARY-FORMAT.md:34`) — "in this workspace, 'set' always means a working
   set". Ours says which terms belong (`CONTEXT-FORMAT.md:29`) but never what to
   do when the wider field uses a term loosely.
3. **Revise in place; no stale entries** (`GLOSSARY-FORMAT.md:35`). Ours has a
   lifecycle rule for ADRs (`ADR-FORMAT.md:38-46`) but none for `CONTEXT.md`
   terms.

The fourth rule, "add a term only when the user understands it"
(`GLOSSARY-FORMAT.md:29`), is learner-gated and does not transfer.

### Decision-record format — `TEACH` ~ · ours ✓

`teach/LEARNING-RECORD-FORMAT.md` is a structural clone of the ADR format we
already adopted: sequential `NNNN-slug.md` with lazy directory creation
(`LEARNING-RECORD-FORMAT.md:3` ≡ `ADR-FORMAT.md:3-5`), a 1-3 sentence template
with a "that is the whole format" disclaimer (`:9-15` ≡ `ADR-FORMAT.md:9-15`),
optional sections used only when they earn it (`:19-23` ≡ `ADR-FORMAT.md:17-23`),
scan-and-increment numbering (`:27` ≡ `ADR-FORMAT.md:25-27`), and supersession
instead of deletion (`:44-46` ≡ `ADR-FORMAT.md:38-42`). The only novel half is
the trigger list (`:31-36`) and its negative counterpart, "Coverage is not
learning. Wait for evidence" (`:38-42`) — and our `learnings.md` already encodes
the same evidence gate: "Capture only after a verified fix or a repeated pattern
— not speculation" (`.claude/project/learnings.md:3-5`). Ours is stronger for our
purpose because it names the evidence type (a verified fix) rather than a
demonstration of understanding.

### Answer-leak-proof quizzing — `TEACH` ~ · `teach-session` ~

`TEACH`: "each answer should be exactly the same number of words (and
characters, if possible). Don't give the user any clues about the answer through
formatting" (`teach/SKILL.md:110`). Ours: "be sure to change up the order of the
correct answer, and to not reveal the answer until after the questions are
submitted" (`.claude/skills/teach-session/SKILL.md:20`).

These fix two different leaks. Ours fixes positional bias and premature reveal;
theirs fixes length-and-formatting bias, which ours does not mention and which
is the leak an LLM introduces by default — a correct answer written carefully
tends to be the longest option. Neither subsumes the other; theirs is the one
we lack.

### Interview scope — `QUEST` ✓ · `LOOP` ~ · our grill family ~

Our grilling family and `LOOP` both interrogate the person in the room about the
subject: `grilling` runs rounds against the user's own plan, and `LOOP`
interviews the user about their own week (`loop-me/SKILL.md:32`). `QUEST` is the
only one that separates the two roles — "**Grill the send, not the subject.**
Interview the user only about the _send_, which they can always answer"
(`to-questionnaire/SKILL.md:9`) — and it is a two-question interview by
construction (`:11`, `:13`), because everything else belongs in the document
rather than the conversation.

`QUEST`'s is stronger wherever the user is not the knowledge holder, which is
precisely the case our grill family handles worst: grilling someone about facts
they do not have produces confident guesses. Nothing in our harness detects that
condition or redirects to a third party.

**Our harness forbids the questionnaire form outright** — correctly, for its own
target. `grill-me/SKILL.md:104` — "Ask **1–3 questions per turn**, not 10. This
is a conversation, not a questionnaire"; `:130` lists "Survey mode" as an
anti-pattern; `brainstorming/references/interviewing.md:75` — "Three or more
questions in one message — that is surveying, not interviewing." Those rules are
right when the respondent is present and can be followed up. They are exactly
wrong when the respondent gets one asynchronous pass, which is the condition
`QUEST` is built for (`to-questionnaire/SKILL.md:19`). `grilling` sits between
the two: it batches the whole frontier into one round (`grilling/SKILL.md:8`),
which is questionnaire-shaped pacing, but still addressed to the user in the
room. So the missing piece is not the document format — it is the *trigger* that
notices the knowledge sits with someone who is not here.

### Comprehension repair — `WAIT` ✓ · `i-have-adhd` ~

Both shape output for a human reader, and they are not the same component.
`i-have-adhd` is a **standing contract** applied to every message once invoked —
ten rules, four documented override cases, and a pre-send deletion check
(`.claude/skills/i-have-adhd/SKILL.md:24-100`, `:102-109`, `:111-122`). `WAIT` is a **one-shot repair**
fired by a specific message having failed, and its content is three re-encoding
moves rather than a style policy (`wait-what/SKILL.md:7`).

We do own one register-change mechanism, and it is narrower than either:
`teach-session/SKILL.md:18` — "learner might ask you questions or ask to eli5,
eli14, or elii (explain like learner's an intern)". That is learner-initiated
re-explanation, but it fires only inside a teaching session about a session's own
work, and it names an audience level rather than a language constraint.

The one thing `WAIT` has that we do not is a **named** language standard —
ASD-STE100, a controlled English with a fixed dictionary and approved sense per
word — instead of the usual vague "explain it simply". `i-have-adhd` regulates
structure (lead with the action, cap lists at five, delete preamble) but never
constrains vocabulary; its explain-mode override (`SKILL.md:106`) says "explain
fully… add headers", which lengthens the answer without simplifying its
language. Our harness has no occurrence of ASD-STE100 or any controlled-language
instruction outside prior research notes
(`docs/research/skill-consolidation/member-opus-5.md:388`). The `CONTEXT.md` half
of `WAIT` we do have: `CLAUDE.md:17` already tells every agent to use the domain
glossary's terms.

### Never-hand-edit generated regions — `WIZ` ✓ · ours ✓ (different domain)

`WIZ` splits one file into a frozen library and an authored region marked by a
`STAGES` comment, with the rule stated twice — in the skill
(`wizard/SKILL.md:10`, `:37`) and in the artifact itself
(`wizard/template.sh:6-7,182-185`). We hold the same discipline for the skill
router: its catalog half is generated by `.claude/scripts/skill-catalog.py` and
gated by an invariant, never hand-maintained (ledger entry
`skill:skills/engineering/ask-matt`, 2026-08-14). `WIZ`'s addition is putting the
warning **inside the generated artifact** so a future editor who never reads the
skill still sees the boundary; ours states it only in the ledger and the
invariant list.
