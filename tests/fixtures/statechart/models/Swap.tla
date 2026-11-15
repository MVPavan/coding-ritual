---- MODULE Swap ----
\* Two bits that are never equal: a regions chart of them cannot be faithful.
VARIABLES a, b
Init == (a = 0 /\ b = 1) \/ (a = 1 /\ b = 0)
Flip == a' = b /\ b' = a
Spec == Init /\ [][Flip]_<<a, b>>
====
