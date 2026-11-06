# Pre-freeze power note (SR-STAT-4)

Primary test simulated at alpha/4 = 0.0125 per test (Bonferroni bound of Holm), target power 80%, 500 simulated studies, 999 sign-flips each, seed 4242. Seeds per family: 3. Bug pool: natural + mutant (natural covers 33 < 60 families: pre-registered fallback).

`required_main_families` = confirmatory (`main`) families needed; `required_total_eligible` adds the held-out share and the pilot. Empty = not reachable within the simulated range.

| model | x | y | scenario | pilot_families | pilot_both | pilot_only_x | pilot_only_y | pilot_neither | p10 | p01 | p_both | required_main_families | required_total_eligible | main_families_available | power_at_available | mcnemar_power_at_available |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| qwen3.5-2b | C | B | point | 17 | 0 | 6 | 0 | 11 | 0.342 | 0.026 | 0.026 | 34.000 | 69.000 | 114 | 1.000 | 1.000 |
| qwen3.5-2b | C | B | pessimistic | 17 | 0 | 6 | 0 | 11 | 0.221 | 0.075 | 0.026 | 143.000 | 225.000 | 114 | 0.662 | 0.686 |
| qwen3.5-2b | C | B | optimistic | 17 | 0 | 6 | 0 | 11 | 0.508 | 0.001 | 0.026 | 16.000 | 43.000 | 114 | 1.000 | 1.000 |
| qwen3.5-2b | C | BP | point | 17 | 4 | 2 | 0 | 11 | 0.132 | 0.026 | 0.237 | 136.000 | 215.000 | 114 | 0.706 | 0.710 |
| qwen3.5-2b | C | BP | pessimistic | 17 | 4 | 2 | 0 | 11 | 0.048 | 0.075 | 0.237 |  |  | 114 | 0.000 | 0.000 |
| qwen3.5-2b | C | BP | optimistic | 17 | 4 | 2 | 0 | 11 | 0.248 | 0.001 | 0.237 | 35.000 | 70.000 | 114 | 1.000 | 1.000 |
| qwen3.5-4b | C | B | point | 17 | 4 | 4 | 0 | 9 | 0.237 | 0.026 | 0.237 | 57.000 | 102.000 | 114 | 0.996 | 0.996 |
| qwen3.5-4b | C | B | pessimistic | 17 | 4 | 4 | 0 | 9 | 0.128 | 0.075 | 0.237 |  |  | 114 | 0.128 | 0.136 |
| qwen3.5-4b | C | B | optimistic | 17 | 4 | 4 | 0 | 9 | 0.385 | 0.001 | 0.237 | 23.000 | 53.000 | 114 | 1.000 | 1.000 |
| qwen3.5-4b | C | BP | point | 17 | 6 | 2 | 1 | 8 | 0.132 | 0.079 | 0.342 |  |  | 114 | 0.082 | 0.080 |
| qwen3.5-4b | C | BP | pessimistic | 17 | 6 | 2 | 1 | 8 | 0.048 | 0.170 | 0.342 |  |  | 114 | 0.000 | 0.000 |
| qwen3.5-4b | C | BP | optimistic | 17 | 6 | 2 | 1 | 8 | 0.248 | 0.017 | 0.342 | 46.000 | 86.000 | 114 | 0.998 | 0.998 |
