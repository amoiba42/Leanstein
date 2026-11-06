# B to C cross-evaluation (secondary analysis)

Every B attempt whose code compiled but whose model proof failed, re-verified as code only through C's full pipeline (integrity, visible + hidden tests, frozen portfolio, axioms). Not part of the primary B or C estimates. `c_proves_tests_fail` is a finding about a weak specification, never a repair.

## Attempts by bucket

| model | condition | c_proves_tests_pass | c_proves_tests_fail | c_cannot_prove | c_rejected_integrity | eligible_attempts |
|---|---|---|---|---|---|---|
| qwen3.5-2b | B | 248 | 0 | 581 | 0 | 829 |
| qwen3.5-4b | B | 361 | 0 | 700 | 0 | 1061 |

## Failed B runs that C's pipeline would have verified

| model | condition | runs | failed_runs | failed_runs_rescued_by_C | rescue_rate_of_failed | runs_with_weak_spec_candidate |
|---|---|---|---|---|---|---|
| qwen3.5-2b | B | 285 | 283 | 41 | 0.145 | 0 |
| qwen3.5-4b | B | 285 | 265 | 49 | 0.185 | 0 |
