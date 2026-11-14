---- MODULE Ghost ----
\* Holds: a traffic light with fairness, one invariant and one temporal property.
EXTENDS Naturals
VARIABLE light
Init == light = "red"
Go   == light = "red"    /\ light' = "green"
Slow == light = "green"  /\ light' = "yellow"
Stop == light = "yellow" /\ light' = "red"
Next == Go \/ Slow \/ Stop
Spec == Init /\ [][Next]_light /\ WF_light(Next)
TypeOK == light \in {"red", "green", "yellow"}
EventuallyGreen == <>(light = "green")
====
