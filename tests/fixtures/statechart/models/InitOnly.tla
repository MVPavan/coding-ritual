---- MODULE InitOnly ----
\* PROPERTY Small has no temporal operator, so TLC checks it in Init only.
EXTENDS Naturals
VARIABLE x
Init == x = 0
Next == x < 2 /\ x' = x + 1
Spec == Init /\ [][Next]_x
Small == x < 1
Grows == <>(x = 2)
Wrapped == Grows
====
