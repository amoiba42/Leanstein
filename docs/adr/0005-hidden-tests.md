# 0005. Hidden generated tests

## Status
Accepted

## Context
A proof certifies only its specification, and visible tests can be overfitted. A repair needs an independent
behavioural check that the model never sees.

## Decision
For each family, generate 30 hidden test inputs (seed 7, 4× candidates). An input is kept only if its precondition
is proved in Lean; expected outputs come from the reference, with a round-trip check. Hidden tests are never shown:
a failure is reported to the model only as a count. Visible VERINA tests stay visible, and one failing witness may
be shown.

## Consequences
- Every verified repair also passes 30 inputs the model never saw.
- Wrong-but-verified code (a weak specification) is caught by hidden tests and labelled separately.
