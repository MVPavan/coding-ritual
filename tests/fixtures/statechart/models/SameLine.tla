---- MODULE SameLine ----
\* A second definition shares Small's line; Small itself has no temporal
\* operator, so TLC tests it against the initial states alone.
EXTENDS Integers
VARIABLE x
Init == x = 0
Next == x' = 1 - x
Small == x = 0   Unused == []TRUE
====
