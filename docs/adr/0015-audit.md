# 0015. Audit of verified repairs

## Status
Accepted

## Context
A verified repair can still be unnatural code, for example code that restates the postcondition or carries dead
code, and the spec-copying flags may be too coarse.

## Decision
Sample 10% of verified repairs, stratified by condition, plus every success that carries a flag (ADR 0007), and
check each against the family's postcondition and description (`prl audit`; results in `results/audit/`). The
current audit of 333 sampled `main` successes is an automated pre-screen; a human audit is pending (D-3 in
`prereg/deviations.md`). Flags never change a result.

## Consequences
- The pre-screen found no specification gaming and 27 correct but unnatural runs (11 families).
- The `copies_postcond` threshold (0.35) fires on correct restatements of executable postconditions, so it cannot
  separate copying from implementing on VERINA; this is reported as a limitation.
- Claims based on the audit are stated as pending until the human audit is complete.
