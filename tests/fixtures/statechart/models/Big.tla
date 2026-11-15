---- MODULE Big ----
\* 625 states, over the 500-state chart budget; Small breaks where x + y = 3; Fine holds.
EXTENDS Naturals
VARIABLES x, y
Init == x = 0 /\ y = 0
IncX == x < 24 /\ x' = x + 1 /\ UNCHANGED y
IncY == y < 24 /\ y' = y + 1 /\ UNCHANGED x
Next == IncX \/ IncY
Spec == Init /\ [][Next]_<<x, y>>
Small == x + y # 3
Fine == x <= 24
====
