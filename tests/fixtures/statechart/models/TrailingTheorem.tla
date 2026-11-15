---- MODULE TrailingTheorem ----
\* A temporal theorem follows Small; Small itself has no temporal operator.
EXTENDS Integers
VARIABLE x
Init == x = 0
Next == x' = 1 - x
Small == x = 0
THEOREM []TRUE
====
