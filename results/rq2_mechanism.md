# RQ2 mechanism: shaping vs reverting

*revert* = repair identical to the reference, or within the pre-registered distance of an automation-provable reference; *shaping* = the reference itself is NOT provable by the portfolio, so the verified repair must have a different, automation-friendly shape; *other* = remaining successes.

## Mechanism class of successful runs

| model | condition | other | revert | shaping |
|---|---|---|---|---|
| gemma-4-e4b-it | B | 0 | 0 | 2 |
| gemma-4-e4b-it | BP | 17 | 20 | 16 |
| gemma-4-e4b-it | C | 15 | 18 | 25 |
| goedel-code-prover-8b | A | 6 | 14 | 18 |
| goedel-code-prover-8b | B | 9 | 15 | 24 |
| qwen3.5-2b | A | 2 | 9 | 2 |
| qwen3.5-2b | B | 1 | 6 | 0 |
| qwen3.5-2b | BP | 23 | 70 | 17 |
| qwen3.5-2b | C | 36 | 72 | 42 |
| qwen3.5-2b | Cplain | 37 | 72 | 44 |
| qwen3.5-4b | A | 27 | 36 | 37 |
| qwen3.5-4b | B | 25 | 21 | 33 |
| qwen3.5-4b | BP | 41 | 73 | 68 |
| qwen3.5-4b | C | 54 | 56 | 81 |
| qwen3.5-4b | Cplain | 53 | 53 | 82 |

## Success rate by reference provability

| model | condition | ref_auto | n_runs | success_rate | median_dist_to_ref |
|---|---|---|---|---|---|
| gemma-4-e4b-it | B | False | 190 | 0.011 | 0.809 |
| gemma-4-e4b-it | B | True | 41 | 0.000 |  |
| gemma-4-e4b-it | BP | False | 190 | 0.084 | 0.788 |
| gemma-4-e4b-it | BP | True | 41 | 0.902 | 0.023 |
| gemma-4-e4b-it | C | False | 190 | 0.132 | 0.793 |
| gemma-4-e4b-it | C | True | 41 | 0.805 | 0.000 |
| goedel-code-prover-8b | A | False | 190 | 0.095 | 0.843 |
| goedel-code-prover-8b | A | True | 41 | 0.488 | 0.000 |
| goedel-code-prover-8b | B | False | 190 | 0.132 | 0.839 |
| goedel-code-prover-8b | B | True | 41 | 0.561 | 0.000 |
| qwen3.5-2b | A | False | 570 | 0.004 | 0.800 |
| qwen3.5-2b | A | True | 123 | 0.089 | 0.000 |
| qwen3.5-2b | B | False | 570 | 0.000 |  |
| qwen3.5-2b | B | True | 123 | 0.057 | 0.000 |
| qwen3.5-2b | BP | False | 570 | 0.030 | 0.800 |
| qwen3.5-2b | BP | True | 123 | 0.756 | 0.000 |
| qwen3.5-2b | Bhammer | False | 570 | 0.002 | 0.826 |
| qwen3.5-2b | Bhammer | True | 123 | 0.163 | 0.121 |
| qwen3.5-2b | C | False | 570 | 0.074 | 0.829 |
| qwen3.5-2b | C | True | 123 | 0.878 | 0.000 |
| qwen3.5-2b | Cplain | False | 570 | 0.077 | 0.829 |
| qwen3.5-2b | Cplain | True | 123 | 0.886 | 0.000 |
| qwen3.5-4b | A | False | 570 | 0.065 | 0.857 |
| qwen3.5-4b | A | True | 123 | 0.512 | 0.000 |
| qwen3.5-4b | B | False | 570 | 0.060 | 0.818 |
| qwen3.5-4b | B | True | 123 | 0.366 | 0.200 |
| qwen3.5-4b | BP | False | 570 | 0.123 | 0.818 |
| qwen3.5-4b | BP | True | 123 | 0.911 | 0.000 |
| qwen3.5-4b | Bhammer | False | 570 | 0.082 | 0.818 |
| qwen3.5-4b | Bhammer | True | 123 | 0.683 | 0.000 |
| qwen3.5-4b | C | False | 570 | 0.142 | 0.818 |
| qwen3.5-4b | C | True | 123 | 0.894 | 0.125 |
| qwen3.5-4b | Cplain | False | 570 | 0.144 | 0.822 |
| qwen3.5-4b | Cplain | True | 123 | 0.862 | 0.149 |

## Study S: re-shaping correct but automation-resistant references

| model | condition | sum | count | mean |
|---|---|---|---|---|
| qwen3.5-2b | S | 10 | 267 | 0.037 |
| qwen3.5-2b | Splain | 11 | 267 | 0.041 |
| qwen3.5-4b | S | 34 | 267 | 0.127 |
| qwen3.5-4b | Splain | 34 | 267 | 0.127 |
