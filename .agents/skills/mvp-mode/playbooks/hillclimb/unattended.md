# Hillclimb, stated unattended

Read this for a stated unattended climb only, before step 2 and again after a compaction. The
playbook keeps the gates, the limits, the terminal stops and every reply.

- **Isolation.** Always, by step 2's recipe, counting as "another may write": artifact directory,
  worktree, environment proof, then the card. Attempts run locally with no delegated writer, since
  `delegation` cannot bind this worktree, and every edit and command names its absolute path. So all
  attempts spend the main session's model and context, with no cheaper implementer and more
  compaction over a night. Writing to the right folder is an instruction, not enforced.
- **Environment.** Name what the command needs. Establish it with the project's own commands and
  without the parent's source: no inherited `PYTHONPATH`, parent venv's editable install or stale
  build output. Make a small real change in the worktree, run the frozen command, see it respond,
  put it back and prove the tree is back. Persist the invocation in the recipe. It cannot be
  established or does not respond: Not started, environment: <what>.
- **Recipe.** A small file in the artifact directory: frozen command, gate, environment, predicate,
  direction, noise, floor, baseline, trail path, first tree.
- **Checkpoint.** Each phase's `note` has one `--set` per field, and
  `--require recipe,worktree,artifacts,head,tree,index,row,value,completed,kept`.

  | Phase | Set when |
  |---|---|
  | `setup` | as the card opens, before its timer: row 0, the baseline, nothing done |
  | `climbing` | the trail is open and baseline gates passed; after each attempt's row, set `row, tree, index, value, completed, kept` and `--unset command` |
  | `closing` | settled, before the result |

- **A command.** Before waiting on a background command, `note --set command=<id>`, where the id or
  the recipe gives its invocation and an output file in the artifact directory, so the command and
  its result can be recovered after a compaction.
- **Keep or undo, then write.** Undo a reject, snapshot, append the row, then `note` the checkpoint
  naming it. That `note` is the commit point: a row past it is an incomplete attempt, and a tally
  comes from the checkpoint, never from counting rows. `kept, simplification` counts as kept.
- **The goal test** matches closing: the selected tree's value against the target in the recipe's
  direction, with completed attempts at the floor.
- **After a compaction or interruption:** `show` the card and read the recipe. A card with `stopped`
  takes the terminal stop, and the recovery below never runs on it. `setup` finishes step 2 and its
  gates, never step 4. `climbing` with a `command` is the attempt in hand. `climbing` with none and
  a failed `verify` is a dead attempt: patch it aside, list the patch's paths, undo, `verify`, log
  `undone, interrupted`, go on. That first failed `verify` only shows the attempt is incomplete; a
  non-zero exit after it is a terminal stop.
- **The limit of that recovery.** A run that dies between an unmeant edit and the marker reaches
  recovery with no marker. Recovery saves the incomplete attempt as a patch before undoing, so the
  path survives in that patch, and the reply lists the patch's paths. The worktree is private and
  the writer local, so this is narrow.
- **A closing return**, on every exit as well as from the timer, works from the card and recipe
  alone and starts no attempt. The card stays open until a row below or Closeout closes it, so a
  marker can still be written. The checkpoint's row must exist with the same tree, index and value;
  row 0 is the first tree.

  | Card says | Do |
  |---|---|
  | exit 4, from a timer's `check` | nothing; one line |
  | `stopped` | close and cancel; touch nothing; Stopped, undo unavailable or an unmeant path, no result claimed |
  | `setup` | close; Stopped, limit: no attempts, nothing to bring back |
  | worktree gone, HEAD not the checkpoint's, or the row disagrees | close; Stopped, trail and checkpoint disagree: name it, touch nothing, no result |
  | a `command` still running | name it; undo nothing; go on to the result |
  | `verify` passes | settled |
  | `verify` fails, no command running | incomplete: `snapshot`, `patch`, list its paths, `undo <patch> <tree> <index>`, `verify`, even after the deadline. A non-zero exit from any of these, that last `verify` included: `note --set stopped=<reason>`, close and cancel; Stopped, undo unavailable: tree left, no result claimed |

- **Then, once settled, the result:** the patch from the first tree to the checkpoint's tree; the
  checkpoint's `value` against target, direction and floor, never a best from an earlier row:
  Finished, unattended or Stopped, limit.
- **Closeout**, where every row above ends. `close` and cancel, if a row has not. Write nothing to the
  main tree; keep the worktree; name patch and folder. Then the
  trail's audit and review: one critic, one try, 30 minutes, which may run past the deadline. A wait
  saying to end the turn does so, and the critic's notice brings it back. Critic or roster
  unreachable: `not reviewed` with a reason, never a self-review or a silent substitute.
