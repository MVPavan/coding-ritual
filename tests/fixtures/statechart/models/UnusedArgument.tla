---- MODULE UnusedArgument ----
\* Small applies an operator to a temporal argument it ignores, so TLC tests
\* Small against the initial states alone.
EXTENDS Integers
VARIABLE x
Init == x = 0
Next == x' = 1 - x
Small == LET Ignore(P) == x = 0
         IN Ignore([]TRUE)
====
