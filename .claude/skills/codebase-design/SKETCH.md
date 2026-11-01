# Sketch a shape before code

The caller wants a settled shape before writing code that crosses a function
boundary, or has several valid implementation shapes, even inside one function; a
clear shape needs no competing designs. The deliverable is usage, types, signatures and a
module map with stub bodies, plus the page below. The sketch is where this skill stops:
no body gets real logic here, and what happens to the sketch next is the caller's decision.

## Ground it

Before sketching, get a working model of each system the design touches and write
out its architectural explanation, since naming a file is not grounding; skip this
only when no surrounding system exists. `explain-code` can produce that explanation.

If the design moves ownership or redraws layers, find out why the current shape
exists and carry that reason as a constraint. `explain-code`'s history branch answers
that question.

## Sketch it

Write the callers' usage before the types, and when the two disagree change the types.

Give the shape as types and signatures with stub bodies, pseudocode for tricky logic
and comments stating intent and invariants, so that types and signatures alone show
the data flow; use one file for a small change and a module map for larger work.

## Screen it

Check each candidate shape against the flags below; a hit means revise or reject it.

- **Shallow module:** callers combine several methods for one operation, options expose internal stages, or using the interface still means learning the implementation.
- **Leaked decision:** one internal choice shows up in several modules, so changing it takes coordinated edits.
- **Pass-through:** a method forwards the same arguments unchanged; remove it unless it adds policy, adaptation or a real abstraction.
- **Split ownership:** two modules write or copy one piece of state; give it one owner that the others read or ask.
- **Several ways:** one task can be done more than one way; keep one, moving callers and deleting the rest in the same change.
- **Open internals:** outside code can import a module's internals; make such an import fail the build.
- **Repeated lists:** several places list the same items; derive them from one, or fail the build when lists that cannot be derived disagree.

Splits by execution stage are `principle-model-the-domain`'s case; apply it.

Assume the next editor sees only the files it opened and copies the closest example,
and prefer the shape where an edit that looks right there is right everywhere.

## Add the page

Add one page beside the sketch: the problem and constraints; the shape with invariants,
validation, non-goals and depth; tradeoffs accepted; at least one rejected alternative (for a
clear shape, the nearest one you passed over); open questions phrased as questions.
