# 0004. Bug sources and the bug-pool rule

## Status
Accepted

## Context
VERINA ships only correct code. Synthetic mutants are controlled but may be easy to revert; bugs written by models
are more realistic but their number cannot be known in advance.

## Decision
- **Natural bugs:** zero-shot implementations from Qwen3.5-0.8B and Qwen3.5-9B, which are never used as repairers.
  At most 4 samples per generator per family; kept only if the code compiles and fails at least one visible or
  hidden test; at most 1 kept per family per generator.
- **Mutants:** one edit to the reference (arithmetic, relational, boolean, constant, negated condition, swapped
  branches, dropped ±1, swapped arguments), kept if it compiles and fails a test; at most 2 per family.
- **Shaping set:** correct references the portfolio cannot prove (study S).
- **Pool rule (fixed before any bug existed):** the confirmatory pool is natural bugs if at least 60 families of
  the `main` split carry one, counted from the dataset manifests; otherwise natural ∪ mutant.

## Consequences
- Natural bugs covered 33 of 114 `main` families, so the natural ∪ mutant pool applies (team decision 2 in `prereg/deviations.md`): 231 bugs (34 natural, 197 mutants) over 106 families.
- Mutants and natural bugs are always also reported separately.
