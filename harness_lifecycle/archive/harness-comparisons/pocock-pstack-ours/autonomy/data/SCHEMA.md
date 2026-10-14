# Shared output schema (all three harness maps)

Write ONE markdown file with exactly these sections. Every row cites evidence as
`path:line` (paths relative to the repo root). No claim without a citation;
label judgement as `J:`.

## 1. Infrastructure assumptions
Table: Assumption | Evidence (path:line) | What breaks without it
Cover: VCS/branching model (PRs? worktrees? stacks?), CI / bots, issue tracker,
runtime/harness features (tools, subagent API, modes, hooks), models, human
touchpoints (where a human must act), persistence (logs, ledgers, memory), autonomy level.

## 2. Nodes
Table: id | kind (skill / playbook / agent / script / command / hook / engine / doc) |
invocation (user-only / model / always / code) | one-line purpose
Include EVERY skill (and playbook / agent / script / command / hook that matters).

## 3. Edges
Table: from | to | relation | evidence (path:line)
relation ∈ {routes-to, invokes, hands-off-to, reads, enforces, produces, requires}.
Only edges the source text states. Do not infer edges from topic similarity.

## 4. Main lifecycle
The canonical path from "a request arrives" to "change landed / done", as an ordered
list of node ids with the decision points (where a human or a gate decides).

## 5. Problem map (fixed taxonomy — use these ids exactly)
Table: problem id | node(s) used, in order | how it solves it (one line, mechanism) | gap?
P01 understand code / how it works
P02 understand why (history, rationale)
P03 clarify requirements / settle decisions with the human
P04 design / architecture
P05 plan / decompose work
P06 implement a feature
P07 fix a bug / debug
P08 performance
P09 write tests
P10 review code or documents
P11 verify / prove done
P12 land / ship (PR, merge, release)
P13 parallel / fan-out work
P14 long or unattended autonomous runs
P15 session continuity / handoff / context management
P16 learn from mistakes / improve the harness
P17 writing, docs, communication style
P18 domain language / glossary / ADRs
P19 security
P20 track work / issues
P21 author or maintain skills / the harness itself
P22 prototype / experiment
If the harness has no answer for a problem, write `—` and gap = yes.

## 6. Autonomy
What lets this harness run without a human, step by step; where it must stop for a human;
what failure/recovery mechanisms exist (retries, ledgers, verdicts, rollbacks).
