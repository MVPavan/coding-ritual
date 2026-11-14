---- MODULE BoxFirst ----
\* TLC checks the PROPERTY [](x = 0) as an invariant and reports
\* "Invariant Small is violated" in the first run.
EXTENDS Integers
VARIABLE x
Init == x = 0
Next == x' = 1 - x
Small == [](x = 0)
====
