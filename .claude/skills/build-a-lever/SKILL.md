---
name: build-a-lever
description: Use when a rerunnable tool (script, codemod, generator or check) would materially reduce repeated work, such as bulk or repeated edits or a migration, or supply proof a reviewer needs that no existing tool or check gives. Not a default for every analysis or change: skip work existing checks already prove; a throwaway experiment that answers a design question is prototype.
---

# Build a lever

Build the tool that does the repeated work or supplies the missing proof,
and prove the tool before trusting it on everything. The deliverable is the
tool, its result on every unit, and the comparison showing it matches a unit
done by hand.

1. **One unit by hand.** Change or check one representative unit yourself.
   This fixes the recipe and the expected result.
2. **The smallest tool.** Write one script, codemod, generator, query or
   check that does that job, never a framework: no options, plugin points
   or generality the work in front of you does not use.
3. **Safe to rerun.** A second run on input the tool already changed must
   leave it correct: recognise the finished form and skip it, or write the
   target state instead of applying a delta.
4. **Prove it.** Run the tool on an unchanged copy of the hand unit's input
   and compare its output with your hand result. Any difference is a fault
   in the tool or the recipe: fix it and compare again until they match.
5. **Run it on the rest** and keep its output beside the tool.

## Keeping it

Keep the tool and its proof with the task's temporary artifacts. When the
work will be rerun or audited later (a staged migration, a large port that
will be reviewed), propose committing them; commit only with that authority.

## Report

The tool's path and how to run it, the hand-unit comparison, the result on
the rest, and the commit proposal if you made one.
