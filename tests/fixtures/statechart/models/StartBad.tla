---- MODULE StartBad ----
\* Ok breaks in the only initial state; three states are reachable.
EXTENDS Naturals
VARIABLE x
Init == x = 0
Next == x < 2 /\ x' = x + 1
Ok == x > 0
====
