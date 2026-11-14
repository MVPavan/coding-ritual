---- MODULE Quoted ----
\* A constant whose configured text looks like configuration syntax. TLC
\* keeps a configured string's backslashes as written, so the module doubles
\* them to compare.
EXTENDS Naturals
CONSTANT A
VARIABLE x
Init == x = 0
Next == x < 2 /\ x' = x + 1
Small == x < 1
Named == A = "INVARIANT (* \\\\* *)"
====
