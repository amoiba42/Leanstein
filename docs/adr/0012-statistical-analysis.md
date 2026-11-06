# 0012. Statistical analysis

## Status
Accepted

## Context
Instances of one task are correlated, seeds are repeated measurements, and VERINA's size is fixed.

## Decision
- Unit: the task family. Family score = mean over seeds of "any instance of the family solved".
- RQ1: one-sided paired sign-flip permutation test (100,000 permutations), Holm correction over the four primary
  tests (α = 0.05, smallest level α/4), exact McNemar on majority-solved, 10,000-resample family-cluster bootstrap
  CIs, Cohen's h, families solved only by one condition.
- Secondary and exploratory comparisons are reported with uncorrected p-values and never pooled with the primary
  estimates. Held-out results are analysed separately.

## Consequences
- C vs BP is underpowered: the power simulation gave 0.71 for qwen3.5-2b and 0.08 for qwen3.5-4b at 114 families
  (team decision 4 in `prereg/deviations.md`). A tie is reported as the same success rate without writing
  proofs, together with cost per repair and the power figures.
- C vs B is well powered for both primary models.
