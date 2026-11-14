---- MODULE RegionMarks ----
\* Two independent bits; Ok breaks exactly where x = 1.
EXTENDS Naturals
VARIABLES x, y
Init == x = 0 /\ y = 0
FlipX == x' = 1 - x /\ UNCHANGED y
FlipY == y' = 1 - y /\ UNCHANGED x
Next == FlipX \/ FlipY
Ok == x = 0
====
