# Blast radius

This answers an explicitly requested assessment of what a change could break.

## Scope

Asked what a change could break, list no callers for their own sake: spend the
effort on what a text search will not show. Read all of it: the diff, each symbol
added, changed or deleted, and the new behaviour the diff leaves unsaid. Where the
change has commit messages or a pull request, read them for what it was meant to
do; having neither is no blocker.

## The safety fact

A change that looks risky is usually safe thanks to one fact. Find it and spend
the effort there, not on a list of maybes; if no such fact exists, say so.

A writeup reads the same whether or not it is true, so prove the fact the
change's safety rests on by running real code, and show what happened. If you
could not, write unproven.

Grade each fact the change's safety rests on: said so, line cited, failure walked
through, run in a script or test, reproduced in the running product. Take each
fact up that list as far as a cheap check allows, and state the level it reached.

Usually one short script does it: import the same library the product ships and
call the exact function in question. The script must fail loudly if the claim is
wrong. Read the source of the library the change calls, at its pinned version, and
check for a local patch.

## Tracing

Work out when things run: deferred callbacks, teardown and shutdown, and any
difference between frameworks or runtimes. Follow what a symbol search misses:
returned data, stored columns, wire formats, other-language readers of the same
bytes, flags, code several hops away. An empty search result is still an answer:
report it.

## Weighing

Give each risk an honest chance of occurring and an honest cost if it does. List
the risks you confirmed apart from those you checked and cleared, with why each
cleared one is fine.

## Hand-back

The hand-back opens with what changed, including the part that is not obvious.
State the fact, how far up the list it got and its proof, or write unproven. For
each risk give how it breaks, the real `file:line`, its likelihood and severity,
and how to check it, with the proof for those that matter. End with the cheapest
test or reproduction that would catch the real bug, including any script you
wrote.
