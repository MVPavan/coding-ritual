# Task: review a proposed set of lifecycle stages and sub-stages

## Context

We are naming the stages of the **agentic development lifecycle (ADLC)**: the end-to-end
lifecycle of software work done mostly by AI coding agents, from first idea to software
running in use and the agent improving over time. We will later map every skill (a
reusable agent instruction package) from several agent harnesses onto these stages, so the
names must be clean, unambiguous, and cover everything.

Naming rules the set must follow:

1. No word is used twice across stages and sub-stages (e.g. a stage "Plan" must not have a
   sub-stage "Plan increments").
2. One grammar throughout (all nouns, or all verbs), not a mix.
3. Stages are phases; sub-stages are activities, in the order they happen.
4. Each stage should be recognisable against a common SDLC vocabulary
   (Plan, Design, Build, Test, Deploy, Maintain).

Optional background, if you want it (read-only; you do not need to read these):

- `harness_lifecycle/adlc/GUIDE.md` — our ADLC principles.
- `harness_lifecycle/adlc/sources/anthropic-ai-native-sdlc-playbook.md` — a vendor's
  six-stage "AI-native SDLC".
- `harness_lifecycle/adlc/council/judge2-final-v2.md` — an earlier first-principles
  13-stage lifecycle (it starts at an incoming request, so it has no discovery or design).

## Proposed stages and sub-stages

| # | Stage | Sub-stage | One-line definition |
|---|---|---|---|
| 0 | **Discovery** | | Study a problem space before any specific change exists. |
| | | Research | Gather evidence: literature, prior art, codebases, experiments. |
| | | Decision | Compare options and choose a direction that spans many changes. |
| 1 | **Intake** | | Turn an incoming request into accepted, well-defined work. |
| | | Triage | Classify the request, size it, route it, and authorize starting. |
| | | Intent | Agree the goal, scope and non-goals with the human. |
| 2 | **Design** | | Decide how the change will be shaped before code is written. |
| | | Grounding | Learn the relevant code, constraints and current behaviour as a baseline. |
| | | Architecture | Choose the structure, interfaces and data model. |
| | | Acceptance | Write the acceptance criteria and failing tests that define "done". |
| 3 | **Construction** | | Produce the change. |
| | | Slicing | Cut the work into small, ordered, independently verifiable increments. |
| | | Implementation | Write the code for each increment. |
| | | Diagnosis | Debug failures and tune performance. |
| 4 | **Verification** | | Prove the change is correct before anyone relies on it. |
| | | Evidence | Run the checks and record the results that back each claim. |
| | | Review | Get an independent critique from a context that did not write the change. |
| 5 | **Delivery** | | Get the verified change into use safely. |
| | | Integration | Merge the change, switched off where it alters runtime behaviour. |
| | | Authorization | Obtain the human's approval for the irreversible step. |
| | | Rollout | Expose the change gradually, with the undo ready. |
| 6 | **Operations** | | Keep the shipped change healthy and learn from it. |
| | | Monitoring | Watch the change in use and raise findings or incidents. |
| | | Closeout | Close the work, hand off state, and record what was learned. |
| | | Improvement | Turn recurring mistakes into better agent instructions, skills and evals. |
| X | **Across stages** | | Concerns that apply to every stage. |
| | | Orchestration | Run long, multi-step or unattended work: loops, parallel agents, resumption. |
| | | Guardrails | Budgets, permissions, tracking and the decision trail. |
| M | **Miscellaneous** | | Skills that are not lifecycle work. |
| | | Communication | How the agent writes and talks. |
| | | Teaching | Explaining concepts to the human. |
| | | Housekeeping | Repository setup and maintenance. |
| | | Aliases | Shortcuts and stubs that point to other skills. |

## What to do

1. Judge whether this covers the **entire** agentic development lifecycle. Name anything
   missing, and anything that should not be here.
2. Judge each name and definition against the naming rules and for clarity. Point out
   overlaps, ambiguous boundaries, and wrong ordering.
3. Then give **your own final proposed list** of stages and sub-stages, with a one-line
   definition for every entry. You may keep, rename, add, remove, split, merge or reorder
   anything. Keep the "Across stages" and "Miscellaneous" bands only if you think they earn
   their place.

Be concrete and opinionated. Do not edit any files.

## Report format

1. **Coverage verdict** — one paragraph.
2. **Changes** — a table: `Change | Item | Reason`, where Change is Add / Remove / Rename /
   Split / Merge / Move / Redefine.
3. **Final proposed list** — a table: `# | Stage | Sub-stage | One-line definition`.
4. **Open questions** — at most five, only real ones.
