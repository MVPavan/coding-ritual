# Run script: template

Read at step 4 of `control-loop`, to write the loop's run script. One run does
one iteration, in this order, and stops at the first step that says stop. It
reads its settings from one file beside it (loop name, loop bead, base branch,
branch prefix, scope, the sensor's pin, turn limit, spend cap) and keeps every
file it writes in a run folder that git ignores (the repository's scratch
folder, `<scratch>/loops/<loop>/runs/<run id>/`; not the git directory, where
an agent may refuse to edit), the agent's raw output included, so a failed run
can be read afterwards.

Every bead write goes through the tracker's command line; every write it makes
is in the loop's grant (`SKILL.md`, The grant). Nothing in it merges,
force-pushes, deletes a pushed branch or changes a gate.

1. **Preflight.** Every setting is set; every path the script names exists
   (sensor, controller, actuator instructions, steering file, the commit
   gate); every command it calls is installed; the loop bead exists and has a
   mirrored issue to reference; the remote's fetch URL, its effective push URL
   (exactly one) and the loop issue name one repository, host, owner and name
   alike, on the scheme's default port (written or not; any other port is
   refused), which every forge call then names in full. Any miss: stop,
   printing all of them as counts and repository names, never a URL, which
   may hold a credential.
2. **One run at a time.** Take one lock per loop in the repository's common
   git directory (`git rev-parse --git-common-dir`), which every worktree of
   the clone shares (`flock -n`), before the next step, and hold it until the
   script exits; when another run holds it, exit at once, changing nothing.
3. **One open pull request.** Read every open pull request of the loop (its
   branch prefix, or a label of its own) in one named repository (the loop
   issue's), the same one creation names. A read that fails or may be cut
   short (as many entries as the listing's limit) stops the run; it never
   counts as none. One is open: note it on the loop bead (`<loop> waiting:
   <address> is open`) and stop.
4. **A fresh tree.** Fetch the base and add a detached worktree of it inside
   the run folder. Every later step works there, so nothing uncommitted in the
   main checkout is touched and the commit gate sees a clean tree.
5. **Sense** in that tree, into the run folder. A changed pin (the tool's
   resolved configuration differs from the one the settings name): note it on
   the loop bead and stop, for the owner to re-pin. A total of zero: note the
   set point reached and stop.
6. **Control:** read the loop bead's notes and run the controller on the
   sensor's output. No selectable target: note how many targets are excluded
   and stop.
7. **Task bead:** create the run's child task under the loop bead and claim
   it.
8. **Actuate.** Build the prompt as the actuator instructions, then the
   controller's selected work, then the steering file. Run the agent from the
   tree with its non-interactive command: the prompt; a tool list of read,
   search and edit tools plus the shell; an allow list naming edits to the
   target's paths and each permitted command exactly; a deny list for staging,
   committing and pushing; the permission mode that denies anything not
   allowed (never one that bypasses checks); no extra tool servers; the turn
   limit and spend cap; machine-readable output into the run folder. The
   session loads no settings file (user, project or local) and runs no hooks,
   because a hook runs outside the tool allowlist and can make network writes
   outside the grant: every tool and path restriction is on the command line.
   Before it, measure the target's findings with suppressions ignored. Write
   the command out in the script; check each flag against the agent's own help
   before the first real run.
9. **Check the change**, in the tree (every git diff or status the script
   parses runs with colour off; a diff is forced to text, with no external
   driver or conversion): the agent's output parses and reports no error, and its
   final message starts with an `OUTCOME:` line; the changed paths are only
   the target's (anything else: failed); for `fixed`, something changed, the
   sensor finds no gap left in the target, and, measured with
   suppressions ignored, no rule's count rose and the selected rules dropped
   by the target's count (a hidden finding is neither fixed nor allowed in),
   and the target's tests pass. `skipped`, or nothing changed: note it on the
   loop bead and the task bead, close the task bead with the reason, remove
   the worktree (keeping its diff in the run folder) and stop, opening no pull
   request.
10. **Gate, manual checks, commit:** stage the target's paths by name and run
    the commit gate from the tree. Any exit but 0 (a failing check, a tree that
    differs, no gate file): note it as failed and stop. On 0, do every manual
    check it prints before the commit. The script does the diff-and-status
    check itself on the plain staged diff: only the target's paths staged,
    nothing else changed, and no added or changed line carrying a directive of
    the sensor's tool in any form it honours, judged line by line (a line that
    only removes one passes), and no change to its configuration: failed. It
    writes the result with the range the gate judged. A manual check that
    needs a person holds the change: it stays on the run's local branch,
    unpushed, both beads are noted, the task bead stays open, and the run exits
    nonzero.
    Then create the run's branch and commit, and note the manual checks' range
    and the commit's SHA on the task bead.
11. **Body, push, pull request:** build the body before anything is pushed:
    the actuator's section, the measurement before and after, each validation
    and its result, the manual checks done, the task bead, and the script's own
    `Refs #<loop issue>` line. An issue-closing keyword (close, fix or resolve
    in any form, followed by an issue reference) anywhere in it fails the run.
    Check the push destination is still the preflight's one repository, then
    push the new branch with upstream tracking (an ordinary push) and open the
    pull request against the base, naming that repository in full. Read its
    base back; another base is reported and stops.
12. **Record:** note the pull request on the task bead and `<loop> done
    <target> <address>` on the loop bead; remove the clean worktree. The task
    bead closes once its pull request merges, through the tracker, not here.

**Dry-run mode** (`--dry-run`): steps 1, 5 and 6 run for real against the
current checkout's tracked files, read only, and every other step prints its
command and runs nothing: no lock, no bead write, no fetch, no worktree, no
agent run, no commit, push or pull request. Its outputs go to a temporary
folder it removes on exit.

A stop after step 7 also notes the reason on the task bead and closes it, so
no run leaves an open task without a pull request, except a change held for a
person (step 10), whose task waits for that person.
