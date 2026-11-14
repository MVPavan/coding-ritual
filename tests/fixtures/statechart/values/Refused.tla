---- MODULE Refused ----
\* Values the decoder refuses: an unevaluated set, an infinite function, and a
\* model value beside a string of the same text.
EXTENDS Naturals
CONSTANTS a
VARIABLES unevaluated, infinite, clash
Init == unevaluated = Nat /\ infinite = [n \in Nat |-> n] /\ clash = {a, "a"}
Next == UNCHANGED <<unevaluated, infinite, clash>>
====
