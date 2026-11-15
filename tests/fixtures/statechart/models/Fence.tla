---- MODULE Fence ----
\* A CONSTRAINT bounds the search; NotFour breaks just past the bound.
EXTENDS Naturals
VARIABLE c
Init == c = 0
Next == c' = c + 1
Spec == Init /\ [][Next]_c
Bound == c <= 3
NotFour == c # 4
====
