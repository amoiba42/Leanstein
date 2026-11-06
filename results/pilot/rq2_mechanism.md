# RQ2 mechanism: shaping vs reverting

*revert* = repair identical to the reference, or within the pre-registered distance of an automation-provable reference; *shaping* = the reference itself is NOT provable by the portfolio, so the verified repair must have a different, automation-friendly shape; *other* = remaining successes.

## Mechanism class of successful runs

| model | condition | other | revert | shaping |
|---|---|---|---|---|
| qwen3.5-2b | BP | 4 | 0 | 1 |
| qwen3.5-2b | C | 7 | 1 | 3 |
| qwen3.5-2b | Cplain | 5 | 1 | 2 |
| qwen3.5-4b | A | 5 | 2 | 2 |
| qwen3.5-4b | B | 4 | 2 | 2 |
| qwen3.5-4b | BP | 4 | 4 | 5 |
| qwen3.5-4b | C | 4 | 4 | 7 |
| qwen3.5-4b | Cplain | 5 | 3 | 3 |

## Success rate by reference provability

| model | condition | ref_auto | n_runs | success_rate | median_dist_to_ref |
|---|---|---|---|---|---|
| qwen3.5-2b | A | False | 33 | 0.000 |  |
| qwen3.5-2b | A | True | 8 | 0.000 |  |
| qwen3.5-2b | B | False | 33 | 0.000 |  |
| qwen3.5-2b | B | True | 8 | 0.000 |  |
| qwen3.5-2b | BP | False | 33 | 0.030 | 0.944 |
| qwen3.5-2b | BP | True | 8 | 0.500 | 0.458 |
| qwen3.5-2b | Bhammer | False | 33 | 0.000 |  |
| qwen3.5-2b | Bhammer | True | 8 | 0.125 | 0.000 |
| qwen3.5-2b | C | False | 33 | 0.091 | 0.942 |
| qwen3.5-2b | C | True | 8 | 1.000 | 0.669 |
| qwen3.5-2b | Cplain | False | 33 | 0.061 | 0.942 |
| qwen3.5-2b | Cplain | True | 8 | 0.750 | 0.669 |
| qwen3.5-4b | A | False | 33 | 0.061 | 0.942 |
| qwen3.5-4b | A | True | 8 | 0.875 | 0.588 |
| qwen3.5-4b | B | False | 33 | 0.061 | 0.942 |
| qwen3.5-4b | B | True | 8 | 0.750 | 0.588 |
| qwen3.5-4b | BP | False | 33 | 0.152 | 0.886 |
| qwen3.5-4b | BP | True | 8 | 1.000 | 0.338 |
| qwen3.5-4b | Bhammer | False | 33 | 0.061 | 0.942 |
| qwen3.5-4b | Bhammer | True | 8 | 0.875 | 0.588 |
| qwen3.5-4b | C | False | 33 | 0.212 | 0.942 |
| qwen3.5-4b | C | True | 8 | 1.000 | 0.338 |
| qwen3.5-4b | Cplain | False | 33 | 0.091 | 0.942 |
| qwen3.5-4b | Cplain | True | 8 | 1.000 | 0.403 |

## Study S: re-shaping correct but automation-resistant references

_(no data)_
