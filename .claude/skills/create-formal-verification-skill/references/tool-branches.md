# Tool branches

What each tool branch keeps in the generated skill, what counts as its pass and
what counts as its broken variant. Read it when building the chosen branch;
create-formal-verification-skill owns it and maintain-formal-verification-skill
reads it. `formal-verify-skill.md` gives the rest of the generated skill.

## Per tool

| Branch | Kept artifacts | Pass | Broken variant (`must_break`) |
|---|---|---|---|
| Model checker | `model/`: spec, main and broken configurations, view file | the TLC gate below | a configuration switch that removes the guard; the named invariant or temporal property fails, by the gate |
| Source verifier | `harness/`: the harness or annotations it reads, run on the real code | every named assertion proved; none skipped, cut short by a bound or assumed away | a harness switch that skips the guard; the named assertion fails |
| Proof | `proof/`: definitions traced to the code, the theorem | the checker accepts it with no admitted step or added axiom | a kept lemma proving a counterexample once the guard is dropped; it must check |
| Generated inputs | `tests/`: a property test calling the real code, fixed seed and example count | passes on every generated input | the test run on a stand-in without the guard, inside the test only; the named property fails |

Each branch names its tool's environment variables in Run. The planted break
of the proof run is a product edit, so it applies to every branch alike.

## The TLC gate

`java -cp <jar> tlc2.TLC -tool`, with `TLA2TOOLS` and `JAVA`, `tool.sha256`
the jar's, and a disposable `-metadir` per run:

- A safety rule sits under `INVARIANT`. `PROPERTY` holds only a temporal
  formula: TLC tests a plain state predicate there on initial states alone and
  still exits 0.
- Never `-continue`: it exits 0 after printing violations.
- A pass is a finished exploration whose exit code is 0 and whose tool-mode
  messages agree (2193, no error message); either alone is not a pass.
- A safety variant counts only when it exits 12 with 2110 naming its
  `must_break` invariant. 2107 (broken in the initial state, which says
  nothing about the main configuration's reach) fails it.
- A temporal variant counts only when it exits 13 with 2116 (temporal
  properties violated) and a counterexample (2264), ending in a loop back
  (2122) or in stuttering (2218). 2116 does not name the property, so that
  variant's configuration checks its `must_break` property alone.
- Exit code and messages agree in every verdict. An error message is one of
  tool-mode severity 1. In a variant, only the expected violation's error
  messages are allowed (safety 2110 and 2121, temporal 2116 and 2264); any
  other exit, any other error message, or a violation of another name fails
  it. The main run allows no error message.
- A variant's verdict means nothing while the main run fails: it may break
  through the same fault, not through the guard it removes.
- Deadlock checking is on by default; `-deadlock` or `CHECK_DEADLOCK FALSE`
  turns it off. The skill's Limits section says which setting the check uses.
- Parse and semantic errors come from TLC itself (exit 150), never from
  standalone SANY, which exits 0 on a semantic error.
