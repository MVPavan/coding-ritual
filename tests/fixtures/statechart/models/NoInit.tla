---- MODULE NoInit ----
\* No state satisfies Init.
VARIABLE x
Init == FALSE /\ x = 0
Next == UNCHANGED x
====
