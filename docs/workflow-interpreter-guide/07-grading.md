# 07 — Grading: the claim is not proof

`inspector/exit_grade.py`. Its `_compute` docstring states the principle in one line:
*"Decide the outcome the evidence supports — never the one claimed."*

The agent's verdict is an input to grading, not its result. Grading is host-only, runs
after the process is dead, and is deterministic over git plus the wrapper directory —
which is why recovery can simply re-run it if a crash interrupted it.

## Step 1: read the claim

The agent writes a marker into `$WF_OUTCOME_FILE`, the reserved outcome channel.
`read_marker` demands **exactly one** marker that validates and names an outcome the
node declares. Anything else is a reason, not a verdict: absent, wrong count, invalid,
or undeclared.

The separation is strict. The channel reports *"two markers found"* as a fact; *"two
markers means `fail_code`"* is a §7 rule that lives in the grader. The reader never
interprets.

## Step 2: establish where the truth is

```python
verified = intended_base_commit if artifact is None else artifact.commit_oid
```

`verified` is the commit the checks actually ran at — the artifact commit when the
agent produced one, the base commit when it did not (a `no_diff` attempt, or a
non-writing reviewer). The checks then run inside a `VerifyTree`: **a fresh checkout of
that commit**, not the working tree the crew could still be writing. That is what
makes the anti-drift check mean anything.

## Step 3: two early exits

1. **Non-zero exit and no marker** → `error_crew`. The process died without
   reporting; infrastructure, and it does not consume a round.
2. **Zero exit but no valid marker** → flagged `MARKER_INVALID`, reason recorded.

## Step 4: five ways a success claim becomes `fail_code`

`inspector/exit_grade.py:370-411`. Any of these overrides the claim:

1. **A verify check exited non-zero.**
2. **The effects manifest is absent.** The agent must declare what it touched.
3. **Anti-drift**, for a node claiming `accept`: the commit the reviewer says it
   reviewed must equal the commit the checks verified. Flagged `ANTI_DRIFT`.
4. **`no_diff` with a commit.** You said nothing changed, but you committed something.
5. **`done` with no commit on a writing node.** *"done claim produced no commit; that
   is no_diff."*

Points 4 and 5 are a matched pair, and the sharpest idea here: the grader catches the
claim being wrong in **either** direction. You cannot under-claim or over-claim past it.

## Step 5: what was touched, measured two ways

- **`undeclared_effects`** — observed writes minus what the crew declared.
- **`out_of_scope`** — observed writes minus the node's `allowed_paths`, *ignoring the
  manifest entirely*. The comment is pointed: *"a node that writes anywhere and says so
  is graded clean"* by the first measure, so the second asks the question an operator
  can act on (ADR 0001).

`physically_written` then distinguishes a path that genuinely changed on disk from one
that merely appears in a list.

This is where the chain lands: the sandbox grant is *disclosure*, the verifier is
*containment*, this measurement is *the receipt*.

## Step 6: findings, for a judging node only

`review_findings` runs only when the node's `outcomes` include `reject` — the graph's
own statement that this node grades someone else's work. Three rules, each a scar:

- Bytes come from the **pinned tree**, not any directory the crew can still reach, so
  extraction cannot race the child and two replays agree.
- Exactly **one** named file is read, `review.md`. The tree also holds that node's
  evidence, and concatenating it *"would append a command transcript to the last
  numbered finding or invent a finding out of a transcript alone"* — found in review.
- A tree with no report yields no findings **and says so**, recorded as a diagnostic.

## The order that makes it trustworthy

1. The crew exits.
2. The wrapper writes `exit.json` **first**.
3. It pins artifacts and outputs to refs — evidence survives before any verdict exists.
4. It runs the checks in a clean tree at the pinned commit.
5. It computes the outcome from evidence.
6. `record_exit` is its **final** act.
7. A later foreman tick reads the record, records evidence, and closes the activation.

Nothing is closed by the party that produced the work, and nothing is graded from a
surface that party can still touch.
