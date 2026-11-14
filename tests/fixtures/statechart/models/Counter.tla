---- MODULE Counter ----
\* Two counters; SumSmall breaks at x + y = 4 and TLC explores past it.
EXTENDS Naturals
VARIABLES x, y
Init == x = 0 /\ y = 0
IncX == x < 3 /\ x' = x + 1 /\ UNCHANGED y
IncY == y < 3 /\ y' = y + 1 /\ UNCHANGED x
Reset == x = 3 /\ y = 3 /\ x' = 0 /\ y' = 0
Next == IncX \/ IncY \/ Reset
Spec == Init /\ [][Next]_<<x, y>>
SumSmall == x + y < 4
XNotThree == x # 3
TypeOK == x \in 0..3 /\ y \in 0..3
====
