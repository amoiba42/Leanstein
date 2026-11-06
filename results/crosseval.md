# B to C cross-evaluation (secondary analysis)

Every B attempt whose code compiled but whose model proof failed, re-verified as code only through C's full pipeline (integrity, visible + hidden tests, frozen portfolio, axioms). Not part of the primary B or C estimates. `c_proves_tests_fail` is a finding about a weak specification, never a repair.

## Attempts by bucket

| model | condition | c_proves_tests_pass | c_proves_tests_fail | c_cannot_prove | c_rejected_integrity | eligible_attempts |
|---|---|---|---|---|---|---|
| gemma-4-e4b-it | B | 405 | 0 | 591 | 0 | 996 |
| qwen3.5-2b | B | 729 | 0 | 1415 | 0 | 2144 |
| qwen3.5-4b | B | 797 | 0 | 1791 | 0 | 2588 |

## Failed B runs that C's pipeline would have verified

| model | condition | runs | failed_runs | failed_runs_rescued_by_C | rescue_rate_of_failed | runs_with_weak_spec_candidate |
|---|---|---|---|---|---|---|
| gemma-4-e4b-it | B | 231 | 229 | 53 | 0.231 | 0 |
| goedel-code-prover-8b | B | 231 | 183 | 0 | 0.000 | 0 |
| qwen3.5-2b | B | 693 | 686 | 115 | 0.168 | 0 |
| qwen3.5-4b | B | 693 | 614 | 106 | 0.173 | 0 |
