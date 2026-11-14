# Re-verification of every logged success

Each successful run's logged code (and, for proof-writing conditions, proof) was given again to the trusted judge in the condition's mode with the verification cache disabled: static integrity, compile, visible and hidden tests, locked-specification hash, proof and axioms. No model was called. Script: `scripts/reverify.py`. Machine: Windows 11 laptop, Lean 4.24.0, Mathlib v4.24.0.

**1858 of 1858 logged successes re-verify** (100.0%).

| study | model | condition | logged successes | re-verified | same proof source | same closing entry |
|---|---|---|---|---|---|---|
| heldout | qwen3.5-2b | B | 2 | 2 | 2 | 2 |
| heldout | qwen3.5-2b | BP | 43 | 43 | 43 | 43 |
| heldout | qwen3.5-2b | C | 43 | 43 | 43 | 43 |
| heldout | qwen3.5-4b | B | 20 | 20 | 20 | 20 |
| heldout | qwen3.5-4b | BP | 68 | 68 | 68 | 68 |
| heldout | qwen3.5-4b | C | 69 | 69 | 69 | 69 |
| main | qwen3.5-2b | A | 13 | 13 | 13 | 13 |
| main | qwen3.5-2b | B | 7 | 7 | 7 | 7 |
| main | qwen3.5-2b | BP | 110 | 110 | 110 | 110 |
| main | qwen3.5-2b | C | 150 | 150 | 150 | 150 |
| main | qwen3.5-2b | Cplain | 153 | 153 | 153 | 153 |
| main | qwen3.5-4b | A | 100 | 100 | 100 | 100 |
| main | qwen3.5-4b | B | 79 | 79 | 79 | 79 |
| main | qwen3.5-4b | BP | 182 | 182 | 182 | 182 |
| main | qwen3.5-4b | C | 191 | 191 | 191 | 191 |
| main | qwen3.5-4b | Cplain | 188 | 188 | 188 | 188 |
| main-bhammer | qwen3.5-2b | Bhammer | 21 | 21 | 21 | 21 |
| main-bhammer | qwen3.5-4b | Bhammer | 131 | 131 | 131 | 131 |
| main-gemma | gemma-4-e4b-it | B | 2 | 2 | 2 | 2 |
| main-gemma | gemma-4-e4b-it | BP | 53 | 53 | 53 | 53 |
| main-gemma | gemma-4-e4b-it | C | 58 | 58 | 58 | 58 |
| main-goedel | goedel-code-prover-8b | A | 38 | 38 | 38 | 38 |
| main-goedel | goedel-code-prover-8b | B | 48 | 48 | 48 | 48 |
| main-shaping | qwen3.5-2b | S | 10 | 10 | 10 | 10 |
| main-shaping | qwen3.5-2b | Splain | 11 | 11 | 11 | 11 |
| main-shaping | qwen3.5-4b | S | 34 | 34 | 34 | 34 |
| main-shaping | qwen3.5-4b | Splain | 34 | 34 | 34 | 34 |

## Runs that did not re-verify

None.

Re-verified runs whose first closing portfolio entry differs from the log: 0 (the closing entry is the first entry, in the frozen order, that closes the goal within its heartbeat budget; a different entry can win when an earlier one is close to its limit).
