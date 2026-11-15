# Writing a generated formal verify skill

The contract for a project skill that reruns one formal check, owned by
create-formal-verification-skill and read by maintain-formal-verification-skill.
Its writing rules are `create-verification-skill`'s
`references/generated-skill.md` ("Writing rules"). That file's "Frontmatter"
applies with the formal `name` and `description` below; the sections and files
below replace its app-driving ones.

## Layout

```
<area>-verification/
  SKILL.md          the sections below, in order
  coverage.json     the record of coverage-record.md
  <artifacts>/      the branch's kept files (`tool-branches.md`)
  scripts/check.py  the one command
```

The frontmatter `name` is the folder's, `<area>-verification`, never
`verify-<app>`. The `description` names the area by the project's nouns (the
lock, the guard, the job) and says to use the skill when a change touches that
code. No other field is required.

## `scripts/check.py`

One command reruns every check with the pinned tool version, in a short run:
keep the bounds small enough that it finishes in seconds to a few minutes, and
record the measured time under Run. It uses only the language's standard
library, and in order:

1. Reads `coverage.json`; a missing key stops it with exit 2, naming the key.
2. Prints the drift diff of `coverage-record.md`.
3. Finds the tool and its runtime from the branch's environment variables, else
   the per-user paths written into `check.py`, and checks `tool.sha256`; a
   missing or wrong one stops it with exit 2.
4. Runs the main artifact and each broken variant with its own recorded
   options, by its branch in `tool-branches.md`.
5. Prints, for every break, its failing path as action names (TLC: the 2217
   state headers), or the branch's failing assertion or input. Exits 0 only
   when the main run passes by the branch's oracle and each broken variant
   gives its `must_break` result; any other verdict, including a failure under
   another name, exits 1, naming it. Step 6 leaves the exit code as is.
6. With a non-empty drift diff, its last line says the verdict is for the
   model at `sync_commit`, not to be relied on until the model is updated.

It calls no other skill's script, flag or path.

## Per tool

Each branch's kept artifacts, pass oracle and broken variant, and the TLC
gate, are in `tool-branches.md`: read it when building the chosen branch.

## Sections

**When to use.** The covered files and functions in words, and the kinds of
change that should send an agent here.

**Does my change touch it.** The traceability table of `model-fidelity.md`,
then how to read the drift diff: a covered path in it means the model needs a
look before the change is called done.

**Run.** The command from `coverage.json`, the expected output of a pass, the
measured run time and the exit codes. It names the per-user install recipe and
pins of the tool and its runtime (TLC: the `statechart` skill's
`references/install.md`), which a later pass follows with the person's approval.

**Reading a failure.** First replay the counterexample on the code: follow its
steps through the real functions, by reading or with a scratch test. If the
code allows that ordering, it is a real bug: report it and leave product code
alone unless the person asks. If the code forbids a step the model allowed, it
is a modelling error: fix the model from the code. Describe any counterexample
as a few numbered steps in the code's terms (function, row, lock), never as a
state dump. When the check is a state-machine model, point the generated skill at our `statechart` unit by name for reading results, copying none of its commands, options or paths.

**Updating for an intended change.** Read the covered diff; update the model
from the code, keeping `model-fidelity.md`'s rules; rerun the main
configuration and every broken variant; then, and only after both match,
advance `sync_commit` and the `covers` entries. A maintain pass that confirms
a bug advances them too, with the faithful update (`coverage-record.md`).

**Limits.** The bounds, the assumptions and what is not covered, matching
`coverage.json`, plus what a pass does not say: it covers the model within its
bounds, not the whole system. Reading results with `statechart` needs that
skill installed (it ships with this stack); `check.py` needs none of it.

## How other units recognise it

By content, not name: a `SKILL.md` beside a `coverage.json` whose `format` is
`formal-coverage/1`. maintain-formal-verification-skill and the setup and help
units search every skills folder the project's hosts read for that pair.
A formal skill older than this format has no `coverage.json`: it is a skill
whose command runs a model, proof, verifier harness or property test it keeps.
Such a skill, an occupied `<area>-verification/` folder, or a match that cannot
be ruled out is never overwritten; it goes to maintain-formal-verification-skill.
