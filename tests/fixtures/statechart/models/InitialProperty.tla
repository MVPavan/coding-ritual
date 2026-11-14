---- MODULE InitialProperty ----
\* A state-level PROPERTY that the only initial state breaks.
VARIABLE x
Init == x = 0
Next == UNCHANGED x
Small == x = 1
====
