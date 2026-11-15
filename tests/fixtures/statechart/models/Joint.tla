---- MODULE Joint ----
\* x counts 0..2 and wraps, y flips. Ok breaks wherever x = 2, and at x = 1
\* only together with y = 1.
EXTENDS Naturals
VARIABLES x, y
Init == x = 0 /\ y = 0
StepX == x' = (x + 1) % 3 /\ UNCHANGED y
FlipY == y' = 1 - y /\ UNCHANGED x
Next == StepX \/ FlipY
Ok == x # 2 /\ ~(x = 1 /\ y = 1)
====
