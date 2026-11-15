---- MODULE Hidden ----
\* Safe breaks only at x = 1, whose one step out is After to x = 2: a view
\* that hides After, or keeps 1 and 2 in one chart state, draws no step
\* after the failure. critic-92l probe.
EXTENDS Naturals
VARIABLE x
Init == x = 0
Choose == x = 0 /\ x' \in {1,2,3}
After == x = 1 /\ x' = 2
Stay == x = 2 /\ x' = 2
Return == x = 3 /\ x' = 0
Next == Return \/ Choose \/ After \/ Stay
Safe == x # 1
====
