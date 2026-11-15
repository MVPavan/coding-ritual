---- MODULE InitialWarning ----
\* Neither property names a temporal operator: one hides brackets in a
\* string, the other is a top-level definition that starts indented.
EXTENDS Naturals
VARIABLE x
Init == x = 0
Inc == x < 2 /\ x' = x + 1
Stay == x = 2 /\ UNCHANGED x
Next == Inc \/ Stay
Small == x = 0 /\ "[]" = "[]"
  Indented == x = 0
====
