---
name: create-formal-verification-skill
description: "Use for /create-formal-verification-skill when a promise whose breaking harms users and that tests rarely reach needs checking across every case in a stated scope; keeping an existing formal check current is maintain-formal-verification-skill, and driving the real app is create-verification-skill. Picks the strongest such promise, checks one property with the tool its question needs, and leaves a project skill that reruns the check, with a coverage and sync record, proven against a planted break."
disable-model-invocation: true
argument-hint: "Optional: the area, promise or bug to verify"
---

# Create Formal Verification Skill

This run leaves a folder in the product's repository: a project skill keeping
one formal check of one promise (the model or other artifact, the command that
reruns it, the commit it last matched), with which a later agent rechecks its
own change against that promise. Its claim is bounded and says so: within the
scope it records, such as every state a compact model reaches or every input up
to a size, the promise holds, or here is how it breaks. Whoever reads the
outcome must be able to rely on it and act on it without reading TLA+ or any
other verification language: every claim this run makes reaches them in plain
words. The person starts this skill; never an agent on its own initiative.

The generated skill lands in the project's skills folder as
`<area>-verification/` (Claude Code: `.claude/skills/<area>-verification/`).

**Scope.** First search every skills folder the project's hosts read for a
formal verify skill: one with a `coverage.json`, an older one without it, or
anything already at `<area>-verification/` (`references/formal-verify-skill.md`,
"How other units recognise it"). If one covers this area, or you cannot rule
that out, stop without writing into it: bringing it up to date is
maintain-formal-verification-skill. This run writes the new skill folder and
only step 5's reversible planted edit besides; product code otherwise changes
only when the person asks, even to fix a finding.

## 1. Choose the target

When the person names an area, a promise or a bug, begin there. Otherwise read
the code, its docs and its tests for promises: a state the product must never
reach, an ordering of events it must survive, a value it must keep. Shortlist
the ones whose breaking would hurt users (lost or wrong data, money, access, a
record that cannot be rebuilt) and that the test suite seldom exercises; for
each, name the tests that do touch it and the cases they leave out.

Pick the one with the most harm and the thinnest test coverage, even when a
milder one would be quicker to check, and say which easier ones you passed over
and why.

Name things as the project does (its glossary, docs, schema and code) in the
model, the property and everything the person reads.

## 2. Choose the tool

The question picks the tool; take the cheapest one that settles it:

- **Can events arrive in a harmful order?** Races, retries, a crash between
  two steps, a protocol: a model checker exploring a compact design model.
  The default here is TLA+ with the TLC checker, whatever the code's language.
- **Does the code itself behave on every input?** Overflow, memory safety, a
  data structure's invariant: a verifier working directly on the source.
- **Must it hold at every size, past any bound?** A proof.

When no verifier handles the project's language, say so, then feed the actual
code inputs that a generator produces (a property-based testing library for
that language) instead of modelling that function by hand.

Prefer a tool the project's developers can install and run themselves, and tell
the person which one you chose and why over the others. Installing it needs the
person's approval first and goes per user or per project, never system-wide.
For TLC, the per-user recipe and its pins live in the `statechart` skill's
`references/install.md`: follow it once approved; without approval, stop and
name what is missing.

## 3. Build the check

Build the chosen branch by `references/tool-branches.md` and the property by
`references/model-fidelity.md`: each variable, action and property traced to
code a reviewer can open, an indivisible step only where the code has one, and
each property seen failing on a broken variant. Put the property and the harm
of breaking it in one plain sentence each (`references/coverage-record.md`).

When the check fails on the current code, that is a finding: report it with its
counterexample. Never loosen the property, the model or the bounds until it
passes.

## 4. Write the verify skill

Write `<area>-verification/` by `references/formal-verify-skill.md`: its
`SKILL.md` with the fixed sections, `coverage.json` by
`references/coverage-record.md`, the branch's kept artifacts and
`scripts/check.py`. From `create-verification-skill`'s
`references/generated-skill.md`, "Writing rules" applies, and "Frontmatter"
with the formal `name` (`<area>-verification`) and `description` in place of
the app's; its app-driving sections (Launch through Use rules) and its list of
fixed sections do not: `formal-verify-skill.md` gives the sections instead. The
model lives in the generated skill, not in scratch: starting this skill is the
request to keep it.

## 5. Prove it on a planted break

A generated skill nobody has followed is a draft. Once its text is final,
record the baseline, the generated skill included: the product checkout's
`git status --porcelain --untracked-files=all` and `git diff`, a sha256 list
of the generated skill's files, and the check's verdict. The person's existing
changes are never cleared; an isolated clean checkout is used only with their
approval. Make one uncommitted, reversible edit to the real code that breaks
the property (delete a lock or a guard the check traces), a different defence
from the kept broken variants. Then, as a cold agent who reads only the
generated skill:

1. Run its check: the drift diff it prints first must list the edited file.
2. Through "Does my change touch it", map the edited lines to the check. Copy
   any model or proof aside, then update it by "Updating for an intended
   change" up to its rerun, never touching `coverage.json` (a source verifier
   or test runs the edit as is). Rerun: the property must break.
3. Through "Reading a failure", replay the counterexample on the code and class
   it a real bug or a modelling error.
4. Remove only the planted edit, restore any model or proof from its copy, and
   rerun: status, diff and hash list match the baseline exactly, and the
   baseline verdict returns.

When the planted edit goes uncaught or a step does not work, fix the skill,
the model or the check, never the planted edit, then rerun from step 1.

## 6. Hand off

The generated skill stays uncommitted unless the person asks for a commit;
`land` makes it. Tell the person that keeping it in step with the code as the
product changes is maintain-formal-verification-skill. Suggest a second target
only when one close to this one turned up, in a line.

## Reply

Plain words throughout, for a reader who never opens the model:

- **Verified:** the property and the harm of breaking it, one sentence each.
- **Tool:** which one, why it fits this question, and its pinned version.
- **Scope:** what the check covers, the bounds and assumptions it holds under,
  and what it leaves out.
- **Findings:** each break on the current code, as a few steps in the code's
  own terms; "none" when it holds.
- **Run:** the one command that reruns it, and how long a run took.
- **Proof:** the planted edit, the step that caught it, and the clean rerun.
- **Skill:** its path, uncommitted, and maintain-formal-verification-skill for
  later upkeep.
- **Blocked or draft:** a refused install, a failed step or an unmet proof,
  stated exactly, and that the skill is a draft.
