# Model fidelity

The one home of the rules that keep a formal check true to the code it guards.
create-formal-verification-skill owns this file; maintain-formal-verification-skill
reads and applies it without restating it. A model that does not describe the
code proves nothing about that code. "Model" means whatever the branch keeps
(`tool-branches.md`): a spec, a verifier harness, proof definitions or a
property test's stand-in; the rules hold for each.

## Traceability table

Every model variable, constant, action and property points to code a reviewer
can open, as `path:line` or `path:start-end` at the sync commit. The table sits
in the generated skill's "Does my change touch it" section, and the comment on
each definition in the spec repeats its `path:line`, so either one leads to the
code.

| Model element | Kind | Code | Note |
|---|---|---|---|
| `TakeHold` | action | `<src>/booking.py:77-81` | the buyer locks the seat's row, then checks it is still free |
| `holds` | variable | `<src>/holds.py:40-52` | the open holds a seat carries |
| `SoldOnce` | property | `<db>/schema.sql:84-89` | the unique constraint it states as a rule |

An element with no single line behind it, such as an over-approximation of a
decision function, names the code it stands for and is marked **abstracted**,
with what the abstraction allows that the code may not. Nothing in the model
is invented: a step the code lacks would let the check prove or refute a
system that does not exist.

## Indivisible steps

One model action is one step the code cannot be interrupted in: a single
statement, one transaction at its stated isolation level, a section under a
held lock. A check and the write that relies on it are two actions when the
code runs them as two statements. Each action's comment names what makes it
indivisible. When unsure, split: a split model shows every ordering the merged
one shows, and more.

## Broken variants

Each property is seen failing on a deliberately broken version of the guarded
code, after it is first written and again after every update. Two kinds:

- **A kept variant**, in the chosen branch's form (`tool-branches.md`): a
  model or harness switch that removes the guard, a proof's counter-lemma, or
  a property test's stand-in without the guard. It sits with that branch's
  artifacts, is listed in `coverage.json` with the property it must break, and
  runs with every check, judged by that branch's oracle.
- **A scratch code edit**, the planted break of the proof run, never kept: a
  model or proof is updated from it; a source verifier or test runs it as is.

A property no variant breaks is vacuous or checks the wrong thing: fix it
before trusting any pass. Read the failure the branch reports (a model
checker's shortest failing path, a verifier's failing assertion, a test's
shrunk input, the counterexample a counter-lemma states); it must fail through
the mechanism the guard exists for, not through a slip in the artifact.

## When to write each

- **Table and comments:** while writing each element, before the first run;
  revised in the same change as any model edit.
- **Step boundaries:** when writing each action, from the code's statements,
  transactions and locks.
- **Broken variants:** once the property first holds, after every update, and
  before the sync commit moves. When a confirmed bug moves the sync commit,
  their verdicts are accepted only from a later run whose main run holds.
