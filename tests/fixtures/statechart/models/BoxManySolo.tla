---- MODULE BoxManySolo ----
\* The PROPERTY [](x < 2) breaks at x = 2 and at x = 3: the chart marks both.
EXTENDS Integers
VARIABLE x
Init == x = 0
Next == x' = (x + 1) % 4
Small == [](x < 2)
====
