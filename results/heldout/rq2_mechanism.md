# RQ2 mechanism: shaping vs reverting

*revert* = repair identical to the reference, or within the pre-registered distance of an automation-provable reference; *shaping* = the reference itself is NOT provable by the portfolio, so the verified repair must have a different, automation-friendly shape; *other* = remaining successes.

## Mechanism class of successful runs

| model | condition | other | revert | shaping |
|---|---|---|---|---|
| qwen3.5-2b | B | 0 | 2 | 0 |
| qwen3.5-2b | BP | 4 | 28 | 11 |
| qwen3.5-2b | C | 5 | 23 | 15 |
| qwen3.5-4b | B | 1 | 12 | 7 |
| qwen3.5-4b | BP | 8 | 28 | 32 |
| qwen3.5-4b | C | 9 | 24 | 36 |

## Success rate by reference provability

| model | condition | ref_auto | n_runs | success_rate | median_dist_to_ref |
|---|---|---|---|---|---|
| qwen3.5-2b | B | False | 249 | 0.000 |  |
| qwen3.5-2b | B | True | 36 | 0.056 | 0.000 |
| qwen3.5-2b | BP | False | 249 | 0.044 | 0.902 |
| qwen3.5-2b | BP | True | 36 | 0.889 | 0.000 |
| qwen3.5-2b | C | False | 249 | 0.060 | 0.902 |
| qwen3.5-2b | C | True | 36 | 0.778 | 0.000 |
| qwen3.5-4b | B | False | 249 | 0.028 | 0.826 |
| qwen3.5-4b | B | True | 36 | 0.361 | 0.000 |
| qwen3.5-4b | BP | False | 249 | 0.129 | 0.902 |
| qwen3.5-4b | BP | True | 36 | 1.000 | 0.000 |
| qwen3.5-4b | C | False | 249 | 0.145 | 0.902 |
| qwen3.5-4b | C | True | 36 | 0.917 | 0.000 |

## Study S: re-shaping correct but automation-resistant references

_(no data)_
