---- MODULE Named ----
\* Deadlocks, and a rule already uses the name NoDeadlock.
EXTENDS Naturals
VARIABLE n
Init == n = 0
Step == n < 1 /\ n' = n + 1
Spec == Init /\ [][Step]_n
NoDeadlock == n \in 0..1
====
