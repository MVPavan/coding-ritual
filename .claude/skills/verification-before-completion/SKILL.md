---
name: verification-before-completion
description: Use before claiming a change is complete, fixed, passing, or ready — in any wording, including paraphrases and satisfaction expressions — and before committing, creating a PR, closing a bead, or moving to the next task.
---

# Verification Before Completion

Evidence comes before claims: a claim lives in the same message as the fresh
run that proves it. The rule binds by meaning, not wording — synonyms,
paraphrases, and any communication implying success are all claims.

## The gate

1. **Identify** the command that proves the claim.
   `.claude/project/verification.md` and `.claude/project/invariants.md` are
   the source of truth — do not invent commands.
2. **Run** it fresh, in full.
3. **Read** the output and the exit status; count the failures — a skim is a
   skip.
4. **Report** what the output actually says. Output contradicts the claim →
   state the actual status with the evidence; never soften it.
5. **`git status`** before presenting completion: only intended files
   changed.

Skipping any step turns the claim into a guess presented as fact.

## Claim → evidence

| Claim | Requires (fresh, this message) | Not sufficient |
| --- | --- | --- |
| "Tests pass" | the named test command; 0 failures in its output | an earlier run; "should pass" |
| "Lint/types clean" | linter and type checker exit 0 on the changed files | a partial check; extrapolation |
| "Build succeeds" | the build command, exit 0 | lint passing; logs look fine |
| "Harness change is sound" | the structural gate rows in `verification.md` that apply to the changed file types | "it's only a markdown edit" |
| "Bug fixed" | the command that showed the original symptom, now green | code changed, symptom assumed gone |
| "Regression test works" | red-green proof: fails with the fix reverted, passes restored | the test passing once |
| "Agent/subagent completed" | the diff (`git status` + `git diff`) shows the claimed changes | the agent's report |
| "Requirements met" | line-by-line checklist against the brief/plan | tests passing |
| "Ready to commit / close" | every row above that applies, plus gate step 5 | intention |

**Red-green proof for fixes**: a fix without a test that failed before it
and passes after it is unproven. Seams and method live in the
test-driven-development skill; this gate demands only the observed red→green
cycle as evidence.

## Red flags — stop and run the gate

- "Should", "probably", "seems to" attached to a status.
- Satisfaction before evidence: "Great — done!", "Perfect."
- The urge to commit, close, or report before the command has run.
- Believing an agent's success report without reading the diff.
- "Just this once" / tired and wanting the work over.

## Rationalizations

| Excuse | Reality |
| --- | --- |
| "Should work now" | Run it. "Should" is the word this gate exists to catch. |
| "I'm confident" | Confidence is not evidence. |
| "The linter passed" | Each claim has its own command; a linter proves only lint. |
| "The agent said success" | Reports are claims; the diff is evidence. |
| "A partial check is enough" | It proves nothing about the parts you skipped. |
| "Different wording, so the rule doesn't apply" | The rule binds meaning. Spirit over letter. |
