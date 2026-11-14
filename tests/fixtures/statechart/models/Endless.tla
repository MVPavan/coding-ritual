---- MODULE Endless ----
\* Millions of states: long enough to interrupt a run (never recorded).
EXTENDS Naturals
VARIABLES x, y
Init == x = 0 /\ y = 0
Next == (x < 5000 /\ x' = x + 1 /\ UNCHANGED y) \/ (y < 5000 /\ y' = y + 1 /\ UNCHANGED x)
====
