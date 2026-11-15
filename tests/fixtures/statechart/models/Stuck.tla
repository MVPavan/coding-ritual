---- MODULE Stuck ----
\* Deadlocks: n stops at 2.
EXTENDS Naturals
VARIABLE n
Init == n = 0
Step == n < 2 /\ n' = n + 1
Spec == Init /\ [][Step]_n
TypeOK == n \in 0..2
====
