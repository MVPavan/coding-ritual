---
trigger: An instruction or routing variant to try on fresh Claude Code sessions and judge from what they actually did.
traits: [candidate-blinding, judge-blinding]   # new
steps:
  - id: eval#1
    when: always
    actions: [{trait: judge-only-rubric}, {trait: eval-spend-go-ahead}]   # new
  - id: eval#2
    when: the go-ahead was given
    actions: [{trait: sandbox-template-per-variant}]   # new
  - id: eval#3
    when: the sandbox template is ready
    actions: [{trait: organic-prompt}]   # new
  - id: eval#4
    when: the prompt is written
    actions: [{trait: top-level-candidate-runs}, {trait: candidate-run-boundary}]   # new
    loads: [{path: eval/run.sh}]
  - id: eval#5
    when: every planned run has ended
    actions: [{trait: one-judge-one-scale}]   # new
    calls: [{to: "skill:delegation"}]
  - id: eval#6
    when: the candidates ran on Claude Code
    actions: [{trait: chain-from-tool-events}]   # new; variant of direct-observation, scored from matched tool results
    loads: [{path: eval/classify.py}]
  - id: eval#7
    when: the judge has reported
    actions: [{trait: read-every-output}]   # new
  - id: eval#8
    when: every exit
    actions: [{trait: eval-closeout}]   # new
---

# Eval

For a variant of agent instructions or routing to try on fresh sessions and
judge from what they did. Scope is Claude Code candidates only: comparing
vendors waits for a second vendor's headless runner and event stream, and the
chain check is unavailable for any other vendor until then. Weighing a reference
harness capability for adoption is `harness-evaluate`, not this playbook.

**The gates.** Anything a candidate can see stays free of the experiment:

- Names of directories, files and slugs look like a project a user might have,
  with no word such as eval, test, judge, experiment, rubric, score, compare,
  benchmark, candidate or arena. A task that is really about a test may say so
  in its prompt. `eval/run.sh` refuses one of these words in the sandbox path,
  which the mount table shows, and in `--path-prepend`; the rest is yours to check.
- The prompt states a user's goal. It never asks which skills or files were
  used, and never mentions other candidates.

The judge knows it is judging, but sees outputs only under neutral labels: no
model name, and no sign of which variant produced them.

1. **Frame.** State the variant, the behaviour that counts as success, and a
   rubric of three to six concrete criteria for the judge alone. Then state the
   prompts, runs per prompt, model, turn limit and permission mode. Real runs cost
   money: start only on the go-ahead for that spend, and name the mode in what you
   ask. A go-ahead to spend does not cover `bypassPermissions`, which needs its own
   explicit approval (`AGENTS.md`, Safety).
2. **Sandbox.** Build one template per variant, a Git repository with its
   baseline committed. The run's diff compares the copy's files with the template's,
   so it shows only the candidate's work. Install
   the variant where a user's discovery would find it, with whatever an organic
   task would have around it. Every run has the same boundary: only its copy is
   writable, with an empty home and no view of the host, other candidates or the
   logs. Its only network is a proxy that allows the Anthropic API, so a template
   carries its own dependencies, a task that needs a package install or the web
   fails, and a refused host shows in `<logs>/<id>.egress`. The candidate can still
   read its token and can send it only to the API, so use one that can be revoked,
   and keep secrets out of the template.
3. **Prompt.** Write what a user would type, the same for every candidate.
4. **Candidates.** Run `eval/run.sh` once per run with a run ID of its own. Each
   run is a fresh top-level headless session in a new copy of the template,
   never a delegate: a delegated task cannot start a playbook, and that is often
   the behaviour under test. It refuses to run without `bwrap`, so Linux only.
   Judge a run's outcome by the `status` and `result_error` that `eval/classify.py`
   reports, not its exit code. The script's header lists its options. Make a new
   setup's first run a small one and confirm sign-in, discovery, tools and the
   proxy log before trusting its results. Expect the CLI's bundled skills and
   plugins beside the template's and one refused telemetry host per run. Models
   differ: one may read a skill's file instead of calling it, which grades as
   `unproven`, and one may edit through the shell, which counts only with a
   `bash_write` pattern.
5. **Judge.** Dispatch one critic through `delegation`, from a different model
   family than the candidates, by the roster. Its brief holds the rubric and the
   outputs under neutral labels. To compare two variants, it scores both sets in
   one pass on one scale.
6. **Check the chain.** Write the variant's patterns file (the format is in
   `eval/classify.py`'s header) and run it over the logs. Grade which units a
   candidate used from this and from what it produced, never from what it says
   it did. Read each `unproven` entry by hand; it never counts as a read until you
   have. A `delegate_reads` entry is not the candidate's own read. Read only this
   run's logs, never other sessions' transcripts.
7. **Read everything.** Read every output yourself, end to end, and compare with
   the judge. A disagreement means a biased judge or an ambiguous rubric: say
   which, and do not average it away. Apply `principle-explain-the-number` before
   trusting any rate.
8. **Close out**, on every exit. Keep the logs, prompts, rubric and patterns
   file, say where, and record the runs made and their total cost. Change nothing
   in the variant's real home; promotion is a later decision.

## Reply

- **Finished:** the variant, the rubric, the prompts and runs, each candidate's
  notes under its label with its chain result, its `unproven` and its
  `delegate_reads`, the judge's verdict, your synthesis with any disagreement, and
  a recommendation on promoting the variant.
- **Stopped before any run:** the frame and what is missing, such as the go-ahead
  or a runner for the vendor asked about.
- **Stopped during the runs:** the runs made, how each ended, and which results
  stand; no recommendation unless the finished runs can carry one.

Every reply also gives the total cost and where the logs are.
