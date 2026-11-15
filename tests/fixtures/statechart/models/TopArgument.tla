---- MODULE TopArgument ----
\* Small applies a top-level operator to a temporal argument it ignores, so
\* TLC tests Small against the initial states alone.
EXTENDS Integers
VARIABLE x
Init == x = 0
Next == x' = 1 - x
Ignore(P) == x = 0
Small == Ignore([]TRUE)
====
