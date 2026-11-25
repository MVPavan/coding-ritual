---
name: control-loop
description: "Use when asked to set up a recurring, scheduled loop that drives one measured property of a codebase toward a target (lint findings to zero, an old pattern gone, a threshold met) through one small pull request per run, across sessions. Driving one condition within a session is the autonomous-run playbook, climbing one metric in a session is hillclimb, and building settled beads unattended to pull requests is autopilot-full."
---

# Control loop

Deliverable: one loop for one property of one repository, designed with the
owner and built by hand: its charter on a loop bead, its parts committed in a
loop folder, each part run on its own, one dry run that opened one real pull
request, and a timer only if the owner asks for one.

A loop is a small control system. Explain these terms to the owner before
designing anything; the interview uses them.

| Part | What it is |
|---|---|
| Set point | The property and its target (an invariant, a threshold or a direction), and the scope: the paths the loop may change and those it only reads |
| Sensor | A command that measures the gap: per target and in total, in a stable, machine-readable form |
| Controller | Picks the next increment from the sensor's output and the loop bead's notes: one reviewable unit per run (one file, by default) |
| Actuator | A headless agent, run on that increment with the loop's instructions |
| Steering file | The owner's standing guidance, read after the controller on every run |
| Run script | Sense, control, actuate, check, commit, push, open the pull request |
| Disturbance | What changes the code from outside the loop: other work, upgrades, generated code |
| Dampener (optional) | A check that stops other changes from making the measurement worse |

Parts may fuse (a sensor that ranks its targets is also the controller): build
only the separation the design has.

## What every loop keeps

- **State in Beads.** The loop is one feature bead, open while the loop lives;
  its description is the charter: set point, scope, sensor, controller,
  cadence, base branch, steering file and loop folder. Each run that acts
  creates a child task bead and opens one pull request that names it and
  references the feature's issue (`Refs #<n>`, never `Closes`). Each run notes
  its target on the loop bead, one line: `<loop> done|skipped|failed|reopened
  <target> <pull request or reason>`. The controller reads those lines: a
  target noted done or skipped, or failed twice, is not chosen again until a
  later `reopened` line.
- **One open pull request per loop.** A run that finds one open notes it on
  the loop bead and does nothing else, a run started by hand included.
- **The agent edits; the script commits.** The headless agent runs with an
  explicit tool allowlist (read and search tools, edits to the target's paths
  only, and only the commands the design names), a turn limit, and a spend cap
  where the agent offers one; never in a permission mode that bypasses its
  checks. It never stages, commits or pushes. The run script refuses a change
  outside the target's paths, stages the target's paths by name, runs the
  commit gate (`commit_gate.py`, beside the mvp-mode autopilot-full playbook)
  before the commit, commits, pushes the run's new branch and opens the pull
  request against the charter's base branch.
- **The grant.** The owner's go on the loop authorizes, per run: the run's task
  bead and its notes, a branch from the base, the gated commit, an ordinary
  push of that branch, and its pull request with its body. Nothing else:
  never force-push, never merge (merging is the shipping playbook's, on the
  owner's word), and hold every other network write for the owner. Silencing
  the sensor's tool to clear a target (an ignore entry, a suppression comment,
  a changed tool configuration) loosens a gate: the actuator skips the target
  and says why, and the owner decides.
- **Runs are local first.** Every part runs by hand before any schedule, and a
  schedule runs on the owner's machine.

## Build a loop

1. **Read the repository before asking anything:** its package and build
   files, the validation commands it already runs and where they are written,
   its commit gate file, its CI, any existing loops or scheduled automation,
   and the analysis tools that could be a sensor, with the configuration each
   one actually resolves. Done when you can name the install and validation
   commands, the commit gate, the base branch and a candidate tool for each
   part.
2. **Interview, with proposals.** Take the parts one at a time. For each,
   offer the options this repository supports with their trade-offs, recommend
   one, and record the owner's answer:
   - set point and scope: which paths may change, which are read only, what is
     left out (generated or vendored code, a package too risky to touch);
   - sensor: how stable, cheap and repeatable it is, and whether it can be
     switched off unnoticed (pin its configuration, and have the run stop when
     the pin changes);
   - controller: how targets are ordered and how large one increment is; start
     simple and expect to tune it from the loop's output;
   - actuator: the golden pattern, found in the code and confirmed with the
     owner (what a good change looks like here), the validation commands it
     must pass before the commit, and the pull-request body;
   - disturbances, and whether to add a dampener;
   - the agent, its allowlist and turn limit; the cadence, proposed by the
     change's risk and the owner's review time, set by the owner's answer.
   Done when every row of the parts table has an agreed answer.
3. **Write the design down before building:** the charter as the loop bead's
   description, invoking `beads` before its first write; the owner's request to
   build the loop covers creating this bead. Done when the owner has read the
   charter and any correction is in it.
4. **Build the parts** in a version-controlled loop folder, where the
   repository keeps its scripts:
   - the sensor and controller as scripts that run standalone, with tests for
     selection logic worth testing;
   - the actuator instructions, from [references/actuator.md](references/actuator.md);
   - the steering file, from [references/steering.md](references/steering.md);
   - the run script, from [references/run-script.md](references/run-script.md),
     its settings (base branch, loop bead, scope, limits, pins) in one file
     beside it.
   Each rule has one home: the golden pattern and body format in the actuator
   instructions, standing corrections in the steering file, selection in the
   controller, the grant and every check in the run script. Done when every
   part exists and the run script's preflight finds every path it names.
5. **Run each part by hand:** the sensor twice (the same output both times,
   its total equal to the tool's own count); the controller on that real output
   (a sensible target, the exclusions right); the run script in its dry-run
   mode (each step printed, nothing written); and the actuator once on the
   chosen target, in a throwaway worktree with the allowlist a run uses,
   inspecting its diff and running the validations. Done when each part works
   on its own.
6. **Dry run, on the owner's go:** one real run of the run script on real
   output, opening one real pull request for the owner to review. Fix what it
   showed and repeat until a run's pull request needs no correction.
7. **Schedule, only when the owner asks:** a local timer at the owner's
   cadence, from [references/local-timer.md](references/local-timer.md). A CI
   runner is a later option: it needs an agent credential stored with the
   forge, a repository setting the owner makes; build it only when asked.
8. **Keep tuning.** A review lesson that should change future runs goes into
   the steering file; a selection change is a controller commit. Raise
   throughput (cadence, increment size, cycles per run) only on the owner's
   word, and the one-open-pull-request bound stays. Review comments on a loop's
   pull request are the babysit playbook's when the owner asks. When the sensor
   reports the set point reached, the run notes it and stops; the owner
   retires the loop and its feature bead closes.

## Reply

- The charter (its bead), the loop folder and each part's path.
- Each by-hand run and its result; the dry run's pull request by its full web
  address and what the owner corrected.
- The timer: installed (its unit or entry, cadence, and how to stop it) or not
  installed.
- What is held for the owner.
