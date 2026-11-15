---- MODULE Collision ----
\* Invariants named NoDeadlock and CheckDeadlock, beside a real deadlock at n = 2.
EXTENDS Naturals
VARIABLE n
Init == n = 0
Go == n < 2 /\ n' = n + 1
Next == Go
NoDeadlock == n < 2
CheckDeadlock == n < 1
====
