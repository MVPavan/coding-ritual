# Evaluating a candidate capability

Run the `harness-evaluate` skill. Read the whole capability, including its
references and scripts, and our nearest skill (`placing.md` step 4). Judge:

- behaviour gain over what we have;
- overlap with our skills, and which one would own it;
- dependencies it brings (tools, other skills, a tracker);
- context cost: how much it loads, and when;
- maintenance: how often upstream changes it.

Outcomes: `adopt` (taken whole), `adopt-merged` (parts into one of ours, with
the adaptation), `reject` (not taken, on merit), `defer` (not now, with what
would bring it back), `out-of-scope` (not our kind of work).
