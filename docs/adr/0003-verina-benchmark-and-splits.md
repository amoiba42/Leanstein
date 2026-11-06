# 0003. VERINA benchmark and family-level splits

## Status
Accepted

## Context
The study needs Lean 4 programming tasks with formal specifications, reference implementations and tests, and a
split scheme that avoids leakage between related instances.

## Decision
- Benchmark: VERINA, 189 tasks, pinned commit `66b3ce50`.
- Eligible: the reference compiles and passes its tests; a human proof is not required.
- Exclusions: four known-bad tasks recorded in `prereg/exclusions.yaml` (`verina_basic_67`, `verina_basic_80`,
  `verina_advanced_10`, `verina_basic_104`) and `verina_basic_70`, whose tests cannot be rendered (excluded by the hidden-test generator, not listed in `exclusions.yaml`); 184 tasks stay
  eligible (104 basic, 80 advanced).
- Known specification defects reported in the literature were checked: the 16 issues in arXiv:2604.16584 §5.2
  and the 6 in arXiv:2605.23772 Appendix A were all fixed by VERINA PR #17 (commit `75c46698`), an ancestor of the
  pin with no dataset change in between, so no further exclusions (team decision 7 in `prereg/deviations.md`).
- Splits by task family (all instances of one task together): pilot 20, main 114, held-out 50 (30% of the
  non-pilot families, seed 2026).

## Consequences
- The task family is the statistical unit; per-instance results are never treated as independent.
- VERINA's fixed size bounds statistical power (ADR 0012).
- Results describe small standalone functions only.
