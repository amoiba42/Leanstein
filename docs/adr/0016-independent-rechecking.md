# 0016. Independent re-checking of reported results

## Status
Accepted (2026-11-14, after the study; disclosed as D-6 and D-7 in `prereg/deviations.md`)

## Context
Every reported number comes from logs written by our own harness during the runs. A reviewer cannot re-run the
study (two days of GPU time on a specific slice), so "the logs say so" was the only evidence that a success was
real and that the tables follow from the logs.

## Decision
Two checks that need neither a GPU nor a model:
1. **Regeneration in CI.** On every push, GitHub Actions lints the code, checks the freeze digest, runs the unit
   tests and regenerates every file under `results/` from the committed logs; any difference fails the build
   (`.github/workflows/ci.yml`).
2. **Re-verification of every success.** `scripts/reverify.py` gives each logged success's code (and, for
   proof-writing conditions, the model's proof) back to the trusted judge in its condition's mode, with the cache
   disabled, on a different machine and operating system from the study.

## Consequences
- All 1,858 logged successes re-verify, with the same proof source and closing portfolio entry
  (`results/reverify/summary.md`); 1.3 h of Lean time.
- Analysis code must stay a pure function of the logs: any hidden state would break the CI comparison.
- Raw prompts and full model responses are not in the repository, so model outputs themselves cannot be
  re-derived; only the extracted code and proofs can be re-checked.
