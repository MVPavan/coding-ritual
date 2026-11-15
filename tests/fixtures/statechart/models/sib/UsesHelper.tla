---- MODULE UsesHelper ----
\* Extends a module beside it.
EXTENDS Naturals, Helper
VARIABLE x
Init == x = 0
Next == x < Limit /\ x' = x + 1
Spec == Init /\ [][Next]_x
====
