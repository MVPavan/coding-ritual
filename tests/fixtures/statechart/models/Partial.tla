---- MODULE Partial ----
\* x counts to 2, y is set once; Ok breaks only where x = 2 and y = 1, so a
\* drawing of the failing path alone can miss the x = 2 state that keeps Ok.
EXTENDS Naturals
VARIABLES x, y
Init == x = 0 /\ y = 0
IncX == x < 2 /\ x' = x + 1 /\ UNCHANGED y
SetY == y = 0 /\ y' = 1 /\ UNCHANGED x
Next == IncX \/ SetY \/ (x = 2 /\ y = 1 /\ UNCHANGED <<x, y>>)
Ok == ~(x = 2 /\ y = 1)
====
