---- MODULE DivZero ----
EXTENDS Naturals
VARIABLE x
Init == x = 0
Next == x' = (x + 1) \div (1 - x)
====
