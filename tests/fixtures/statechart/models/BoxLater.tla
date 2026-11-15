---- MODULE BoxLater ----
\* Inv breaks first; the PROPERTY [](x < 2) breaks, as an invariant, in the
\* run of its own.
EXTENDS Integers
VARIABLE x
Init == x = 0
Next == x' = (x + 1) % 3
Inv == x < 1
Small == [](x < 2)
====
