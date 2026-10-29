# Upstream review: mattpocock_skills 1.2.3 → 1.3.1

- **Harness:** `reference_harnesses/mattpocock_skills`
- **Pins:** `84fdeff` → `49dd158` (125 commits)
- **Versions:** 1.2.3 → 1.3.1 (every `.changeset/*` entry is `patch`)
- **Method:** playbook §4. Baseline pin `84fdeff` for all rulings (rulings with no recorded sha use it too). For each of the 39 gap items I read only that capability's diff `84fdeff..49dd158` (changed), or the capability at `49dd158` (hash-unknown), or the whole skill (new, §6). Classes and verdicts per the §4 table; new skills per §6. Changesets used as a map; judged from the diff.

## Release themes

- Pure maintenance release: every change is a `patch`. No new vocabulary, no reshaped flows.
- Repo-wide rename **`CONTEXT.md` → `GLOSSARY.md`** and **`CONTEXT-FORMAT.md` → `GLOSSARY-FORMAT.md`**; `wait-what` adds a `GLOSSARY-MAP.md` multi-glossary pointer.
- Repo-wide wording swap: em-dash asides → colons/parentheses, and **`/skill` prose → "call the Skill tool with X"** invocation phrasing.
- Four new skills: `implement-spec`, `pr`, `retro` (engineering) and `in-progress/chief-of-staff` (beta).
- Debugging gains a "prove the red" guard; `tdd` gains per-seam trade-off notes; `grilling` words questions so "yes" accepts the recommendation.
- GitHub/GitLab tracker template fixes in `setup-matt-pocock-skills`, `to-tickets` (sub-issues, native edges), `wayfinder` (label/ref/PR hygiene) — all tracker-coupled.
- `diagnosing-bugs` loses its post-mortem tail; that "what would have prevented this?" step moves into the new `retro`.

## Capabilities

Paths are submodule-relative unless they start with `.claude/`.

### New (§6)

| Capability | Upstream (file:line at 49dd158) | Ours (file:line) | Class | Verdict | Why |
|---|---|---|---|---|---|
| implement-spec | `skills/engineering/implement-spec/SKILL.md:1` | `.claude/skills/execution/SKILL.md`, `.claude/skills/phase-execution/SKILL.md` | Gap, costly | reject | Multi-ticket task-graph orchestration: implementer subagents across the ready frontier, one integration branch, one closing `code-review`. Our execution/phase-execution + beads-native blocking edges + worktrees already do this, with a review loop and gate cadence it lacks. No behaviour gain. |
| pr | `skills/engineering/pr/SKILL.md:1` | `.claude/skills/show-me/SKILL.md:1` (visuals); no PR-body home | Gap | adopt-merged | PR-body contract: smallest Summary visual + **before/after Evidence** + **Merge Danger** (one-way/two-way door, blast radius). The Summary visual menu is already our `show-me` (same Dex Horthy source `pr/CREDITS.md:1` credits). New to us: the body template, the evidence block, and the door/blast-radius framing. Cheap, self-contained, model-invoked. |
| retro | `skills/engineering/retro/SKILL.md:1` | playbook §7 (update-from-failure); `.repo-context/learnings.md`; `.claude/skills/authoring-for-agents/` | Gap | adopt-merged | Session retrospective that improves the agent **environment** (navigation pointers, automated checks, coding standards, AGENTS.md pruning, tool economy, no-ops, info access), classifying each finding **mechanical** (→ deterministic check, "build the check over writing the rule") vs **judgement** (→ standards doc). Sharper than our §7/learnings loop; it is also where `diagnosing-bugs`' removed post-mortem now lives. |
| chief-of-staff (beta) | `skills/in-progress/chief-of-staff/SKILL.md:20,43-45` | `.claude/skills/execution/SKILL.md`; `AGENTS.md:11,35,42-43` | Conflict | reject | Long-running single-session orchestrator thread co-ordinating subagents + schedules toward a goal. Concrete conflicts with our policy: it mandates all work through subagents (`SKILL.md:20`) where `AGENTS.md:42-43` delegates only when it materially helps and keeps small work local; it drives unsolicited environment work and prerequisite cleanup (`SKILL.md:43-45`, the "no workarounds" rule) where `AGENTS.md:11,35` require authorization for scope expansion and forbid unrelated/speculative cleanup. `in-progress/` is beta tier. Its "pit of success" framing overlaps `retro`; take it there, not here. |

### Changed (§4)

| Capability | Upstream change (file:line at 49dd158) | Ours (file:line) | Class | Verdict | Why |
|---|---|---|---|---|---|
| ask-matt | `skills/engineering/ask-matt/SKILL.md:11` read-SKILL-first safeguard; new `/implement-spec`,`/pr`,`/retro` cross-refs; GLOSSARY rename | `AGENTS.md:22-24`; `.claude/skills/skill-router/` | Covered | keep (re-record) | The new read-before-recommending line is a real behaviour change, but `AGENTS.md:22-24` already requires verifying consequential summary claims against primary evidence. Our skill-router borrows (compaction vocabulary) untouched; the new skills are judged in their own rows. |
| code-review | `skills/engineering/code-review/SKILL.md:36` search the repo for every standards file, and CODING_STANDARDS.md/CONTRIBUTING.md must be on the list; `:60` sub-agents in foreground; `:13` tracker via doc | `.claude/skills/review/SKILL.md`, `.claude/skills/review/references/review-contract.md` (no standards-discovery rule) | Gap | adopt-merged | We rejected the parallel/foreground sub-agent model (snapshot single-pass), so the foreground fix does not apply; tracker is Beads. But neither our review SKILL nor review-contract implements a standards-file **discovery** rule — searching the repo and always picking up `CODING_STANDARDS.md`/`CONTRIBUTING.md`. That is the gap; adopt it into the review skill. |
| codebase-design | `skills/engineering/codebase-design/SKILL.md`, `DEEPENING.md`, `DESIGN-IT-TWICE.md` GLOSSARY rename + Skill-tool wording | `.claude/skills/codebase-design/` | Cosmetic | keep (re-record) | Adopted verbatim; no behaviour change. |
| diagnosing-bugs | `skills/engineering/diagnosing-bugs/SKILL.md:125` Phase 5: `diff` a forced mutation against a pristine copy before trusting the red | `.claude/skills/systematic-debugging/SKILL.md:16,29` | Gap | adopt-merged | New guard: an edit that silently changed nothing can't pass as a failing test. Cheap, in scope. (Also note Phase 6 post-mortem tail removed — relocated to `retro`.) |
| domain-modeling | `skills/engineering/domain-modeling/GLOSSARY-FORMAT.md` (renamed from CONTEXT-FORMAT), `ADR-FORMAT.md` polish | `.claude/skills/domain-modeling/` | Cosmetic | keep (re-record) | Wording + rename; the ADR substance we took is unchanged. |
| grill-with-docs | `skills/engineering/grill-with-docs/SKILL.md:1` two-line Skill-tool wording | `.claude/skills/grill-with-docs/` | Cosmetic | keep (re-record) | No behaviour change. |
| improve-codebase-architecture | `skills/engineering/improve-codebase-architecture/SKILL.md`, `HTML-REPORT.md` GLOSSARY rename, temp-dir report path, Skill-tool wording | `.claude/skills/improve-codebase-architecture/` | Cosmetic | keep (re-record) | Adopted verbatim per owner override; report-format redirect stays ad hoc. |
| prototype | `skills/engineering/prototype/SKILL.md`, `LOGIC.md`, `UI.md` wording + sub-shape A/B framing reflow | `.claude/skills/prototype/` | Cosmetic | keep (re-record) | No new branch; both branches already kept. |
| research | `skills/engineering/research/SKILL.md:1` primary-source wording | `.claude/skills/research/` | Cosmetic | keep (re-record) | No behaviour change. |
| setup-matt-pocock-skills | `skills/engineering/setup-matt-pocock-skills/SKILL.md:104` now creates missing GitHub/GitLab triage labels; `issue-tracker-*.md`/`triage-labels.md` change operational commands | `AGENTS.md:109` (Beads) | Conflict | keep (reject) | Not merely cosmetic — it configures and provisions GitHub/GitLab/local trackers and now mutates the tracker (creates labels). That alternate durable tracker conflicts with our Beads policy (`AGENTS.md:109`). Reject stands. |
| tdd | `skills/engineering/tdd/SKILL.md:24` give each proposed seam a one-line note on what it catches/misses | `.claude/skills/test-driven-development/SKILL.md:23`; `.claude/skills/planning/` Test-seams field | Gap | adopt-merged | Small refinement to our seam-selection; fits the plan's Test-seams field. |
| to-spec | `skills/engineering/to-spec/SKILL.md:1` rewords the already-present prototype-snippet exception | `.claude/skills/brainstorming/references/spec-template.md` | Cosmetic | keep (re-record) | The prototype-snippet exception existed at `84fdeff` and we already adopted it; this is wording only. |
| to-tickets | `skills/engineering/to-tickets/SKILL.md:1` sub-issues; omit "Blocked by" when blockers are native edges | `.claude/skills/beads/references/usage.md:203-211` (`bd dep add`; waits are `blocks` edges) | Covered | keep (re-record) | Native blocking edges + omit-text-when-native is exactly our Beads model. |
| triage | `skills/engineering/triage/SKILL.md`, `AGENT-BRIEF.md`, `OUT-OF-SCOPE.md` wording + `--json` note | `.claude/skills/triage/` | Cosmetic | keep (re-record) | We adapted onto Beads natives; no new behaviour. |
| wayfinder | `skills/engineering/wayfinder/SKILL.md` no `ready-for-agent` on maps/tickets (#518); real-id cross-refs (#507); no PR from research branch (#576); resolve ticket as its labelled type (#625) | `.claude/skills/wayfinder/SKILL.md:15-30,41` | Covered | keep (re-record) | Our wayfinder is already Beads-native — map epic with children, native prerequisite edges, no labels created, kinds first in the title, IDs created before wiring — and prescribes no research-branch/PR workflow, so these GitHub-tracker hygiene fixes are inapplicable to our counterpart. |
| wizard | `skills/engineering/wizard/SKILL.md` wording; `template.sh:115,132,142,145,223` Readline input, EOF handling, file mode, quoting, run-inside-`run_wizard` structure | `.claude/skills/wayfinder/` (verify-what-you-must-not-run only) | Gap, costly | defer | The template changes are deferred. The adopted part is unaffected: we took only the static-trace "verify what you must not run" discipline, which is unchanged — keep that. The `template.sh` executable fixes are real behaviour changes, but the 200-line `.env`+`gh` machinery stays out of scope (cuts against our python/safety rules); defer. Revisit only if we ever ship an interactive bash-provisioning wizard. |
| loop-me | `skills/in-progress/loop-me/SKILL.md` workflow-spec wording reflow | `.claude/skills/wayfinder/` (push-right, decision-summary) | Cosmetic | keep (re-record) | Our two borrows unchanged; rest already rejected. |
| setup-ts-deep-modules | `skills/in-progress/setup-ts-deep-modules/SKILL.md`, `dependency-cruiser.config.cjs` wording | `.claude/skills/skill-router/` (prove-the-rules-bite pattern) | Cosmetic | keep (re-record) | Pattern-only adopt; TS/dependency-cruiser wiring stays stack-inapplicable. |
| grilling | `skills/productivity/grilling/SKILL.md` "word each question so 'yes' accepts your recommended answer" | `.claude/skills/grilling/SKILL.md` | Gap | adopt-merged | Small question-wording discipline, absent from ours. The ➡️/❓ round formatting is cosmetic. |
| handoff | `skills/productivity/handoff/SKILL.md:1` spells out OS temp-dir names (`$TMPDIR`/`/tmp`/`%TEMP%`); destination and suggested-skills contract unchanged | `.claude/skills/beads/references/usage.md:260` (resume line) | Cosmetic | keep (re-record) | We took the session-close-records-method idea into Beads (resume-with line), not the portable temp-dir file; naming the temp dir is a within-contract clarification, not a behaviour delta for us. |
| teach | `skills/productivity/teach/SKILL.md:110` quiz answer position varies across questions (#611); `:12` workspace resolves from run dir (#377); GLOSSARY-FORMAT | `.claude/skills/teach/SKILL.md:10-18,29-38` | Gap | adopt-merged | Narrow: take only the **answer-position variation** into our quiz guidance. The workspace-root fix addresses upstream's always-a-workspace model; ours makes courses optional with an authorized supplied location and "never assume the repo root is a workspace", so that fix is inapplicable — preserve our boundaries. |
| to-questionnaire | `skills/productivity/to-questionnaire/SKILL.md` template reflow | `.claude/skills/grilling/`; `.claude/skills/grill-me/` | Cosmetic | keep (re-record) | We took the absent-respondent mode; wording only. |
| wait-what | `skills/productivity/wait-what/SKILL.md:7` adds following `GLOSSARY-MAP.md` to pick the right glossary in a multi-glossary repo | `.claude/skills/i-have-adhd/SKILL.md:110` (names only `CONTEXT.md`, no map lookup) | Gap | adopt-merged | Beyond the GLOSSARY rename this adds a real capability: multi-glossary selection. Our controlled-language override names only `CONTEXT.md`; add a map lookup using our own glossary convention (a `CONTEXT-MAP.md`). |
| writing-for-agents | `skills/productivity/writing-for-agents/SKILL.md` wording/punctuation reflow | `.claude/skills/authoring-for-agents/references/writing-principles.md` | Cosmetic | keep (re-record) | Correction from round 1: co-location, the info-hierarchy ladder, completion-criteria demand, premature-completion, split-by-sequence, environment-as-cache and the no-op test **all already exist at `84fdeff`** (`writing-for-agents/SKILL.md:41,49,50,58,79,81`); the diff only rewords them. No release addition. Any reconsideration of whether our compressed writing-principles should absorb more of that older content needs separate evidence, not this review. |

### Hash unknown — re-rule (all hold at 49dd158)

| Capability | At 49dd158 | Class | Verdict | Why |
|---|---|---|---|---|
| plugin:mattpocock-skills | `package.json`, umbrella package | — | reject — holds | Still umbrella packaging; member decisions are carried per-skill, so the umbrella adds nothing we don't already decide skill-by-skill in this registry. |
| implement | `skills/engineering/implement/SKILL.md:17` still ends "Commit your work to the current branch." | Conflict | reject — holds | Unconditional commit still violates git-safety; still a thin router over tdd/code-review. New ticket-fetch + Skill-tool wording don't change the rationale; its verification cadence is already in our implementer agent. |
| in-progress/claude-handoff | `skills/in-progress/claude-handoff/SKILL.md:8` now saves the summary to a file, then launches a background `claude --bg` agent seeded with it | — | reject — holds | The round-1 "no inspectable artifact" rationale no longer holds — it now writes a file first. Reject still stands on a basis true at `49dd158`: `in-progress/` beta tier, and auto-launching a background CLI agent seeded from the file adds a delivery mechanism we do not want; our handoff is the resume note on the bead (`.claude/skills/beads/references/usage.md:260`). |
| in-progress/writing-beats | `skills/in-progress/writing-beats/SKILL.md` | — | out-of-scope — holds | Prose-authoring family, `adoption_scope=out-of-scope`. |
| in-progress/writing-fragments | `skills/in-progress/writing-fragments/SKILL.md` | — | out-of-scope — holds | Prose-authoring family, out-of-scope. |
| in-progress/writing-shape | `skills/in-progress/writing-shape/SKILL.md` | — | out-of-scope — holds | Prose-authoring family, out-of-scope. |
| misc/git-guardrails-claude-code | `skills/misc/git-guardrails-claude-code/SKILL.md` (2-line cosmetic) | — | reject — holds | Our `block-dangerous-commands.sh` is a strict superset with safer fixed-string matching; the install-verification idea already borrowed. |
| misc/migrate-to-shoehorn | unchanged since `84fdeff` | — | reject — holds | Upstream misc/ staging; shoehorn refactor has no local use. |
| misc/scaffold-exercises | unchanged since `84fdeff` | — | reject — holds | Course-exercise scaffolding; no course content here. |
| misc/setup-pre-commit | `skills/misc/setup-pre-commit/SKILL.md` (2-line cosmetic) | — | reject — holds | Husky/lint-staged/Prettier wiring stack-inapplicable (no Node/package.json/CI). |
| productivity/grill-me | `skills/productivity/grill-me/SKILL.md` (2-line cosmetic) | — | reject — holds | Seven-line alias to their `/grilling`; we own the `grill-me` name for a fuller skill. |

## Worth acting on

Gap and adopt-merged rows only, ranked by value.

1. **`pr` → new PR-body home (or merged with `show-me`/a delivery skill).** Take the body template, the before/after Evidence block, and the Merge Danger door + blast-radius framing. The Summary visual menu is already `show-me`, so merge rather than duplicate.
2. **`retro` → merge into our update-from-failure loop (playbook §7 + `.repo-context/learnings.md`).** Take the environment-improvement categories and the mechanical-vs-judgement / build-the-check-over-the-rule default. Also absorbs `diagnosing-bugs`' removed post-mortem.
3. **code-review standards discovery → `.claude/skills/review/`.** Add a rule to search the repo for every file documenting how code should be written, always picking up `CODING_STANDARDS.md`/`CONTRIBUTING.md`. Our review has no such discovery step today.
4. **diagnosing-bugs prove-the-red → `.claude/skills/systematic-debugging/SKILL.md`.** Add: when you force the red by mutating code/fixture, `diff` against a pristine copy to prove the mutation landed. Cheap safety gate.
5. **wait-what multi-glossary lookup → `.claude/skills/i-have-adhd/SKILL.md`.** When a repo has more than one glossary, follow a `CONTEXT-MAP.md` to the right one; today the override names only `CONTEXT.md`.

Lower: `tdd` per-seam catch/miss note → `test-driven-development` / `planning` Test-seams; `grilling` "yes accepts the recommendation" wording; `teach` quiz answer-position variation.

(Removed from round 1: the `writing-for-agents` recommendation — its cited ideas already existed at `84fdeff`, so there is no release gap.)

## Structural, outside skills proper

- **`CONTEXT.md` → `GLOSSARY.md`** and **`domain-modeling/CONTEXT-FORMAT.md` → `GLOSSARY-FORMAT.md`** repo-wide; `teach/GLOSSARY-FORMAT.md` and a new `GLOSSARY-MAP.md` pointer for multi-glossary repos. Informational only — we use `docs/adr/` and our own glossary conventions.
- `setup-matt-pocock-skills/issue-tracker-{github,gitlab,local}.md` and `triage-labels.md` tracker-template fixes — N/A, we track with Beads.
- Repo-wide `/skill` prose → "call the Skill tool with X" invocation phrasing — upstream harness convention, no bearing on ours.

## Coverage

- **Read fully:** the 4 new skills (`implement-spec`, `pr` + `CREDITS.md`, `retro`, `chief-of-staff`); `skills/engineering/implement/SKILL.md` and `skills/in-progress/claude-handoff/SKILL.md` at the new pin; `writing-for-agents/SKILL.md` at **both** pins (round-1 correction); our `.claude/skills/authoring-for-agents/references/writing-principles.md`, `show-me/SKILL.md`, `review/SKILL.md` + `review/references/`, `test-driven-development/SKILL.md` (seam section), `systematic-debugging/SKILL.md`, `wayfinder/SKILL.md`, `teach/SKILL.md`, `i-have-adhd/SKILL.md`; and `AGENTS.md`.
- **Diff-only (84fdeff..49dd158):** the 24 changed capabilities. For the big reflows (`wayfinder`, `improve-codebase-architecture`, `prototype`) I isolated the non-punctuation added/removed lines; for `writing-for-agents` I then re-read the full body at both pins after the critic flagged it.
- **At 49dd158, confirm-or-challenge only:** the 11 hash-unknown items (`migrate-to-shoehorn` and `scaffold-exercises` unchanged since baseline; the rest cosmetic except `claude-handoff`, which gained a file-first save).
- **Unverified:** content hashes at `49dd158` for the ruling records were not computed here (owner/record step). All round-1 unverified items (review standards discovery, wayfinder counterpart) were checked this round and are reflected above.
