# Pre-freeze power note (SR-STAT-4)

Primary test simulated at alpha/4 = 0.0125 per test (Bonferroni bound of Holm), target power 80%, 500 simulated studies, 999 sign-flips each, seed 4242. Seeds per family: 3. Bug pool: natural + mutant (natural covers 32 < 60 families: pre-registered fallback).

`required_main_families` = confirmatory (`main`) families needed; `required_total_eligible` adds the held-out share and the pilot. Empty = not reachable within the simulated range.

| model | x | y | scenario | pilot_families | pilot_both | pilot_only_x | pilot_only_y | pilot_neither | p10 | p01 | p_both | required_main_families | required_total_eligible | main_families_available | power_at_available | mcnemar_power_at_available |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| qwen3.5-2b | C | B | point | 17 | 0 | 6 | 0 | 11 | 0.342 | 0.026 | 0.026 | 34.000 | 69.000 | 114 | 1.000 | 1.000 |
| qwen3.5-2b | C | B | pessimistic | 17 | 0 | 6 | 0 | 11 | 0.221 | 0.075 | 0.026 | 143.000 | 225.000 | 114 | 0.662 | 0.686 |
| qwen3.5-2b | C | B | optimistic | 17 | 0 | 6 | 0 | 11 | 0.508 | 0.001 | 0.026 | 16.000 | 43.000 | 114 | 1.000 | 1.000 |
| qwen3.5-2b | C | BP | point | 17 | 2 | 4 | 2 | 9 | 0.237 | 0.132 | 0.132 | 327.000 | 488.000 | 114 | 0.278 | 0.296 |
| qwen3.5-2b | C | BP | pessimistic | 17 | 2 | 4 | 2 | 9 | 0.128 | 0.248 | 0.132 |  |  | 114 | 0.000 | 0.000 |
| qwen3.5-2b | C | BP | optimistic | 17 | 2 | 4 | 2 | 9 | 0.385 | 0.048 | 0.132 | 35.000 | 70.000 | 114 | 1.000 | 1.000 |
| qwen3.5-4b | C | B | point | 17 | 5 | 2 | 0 | 10 | 0.132 | 0.026 | 0.289 | 136.000 | 215.000 | 114 | 0.688 | 0.696 |
| qwen3.5-4b | C | B | pessimistic | 17 | 5 | 2 | 0 | 10 | 0.048 | 0.075 | 0.289 |  |  | 114 | 0.000 | 0.000 |
| qwen3.5-4b | C | B | optimistic | 17 | 5 | 2 | 0 | 10 | 0.248 | 0.001 | 0.289 | 34.000 | 69.000 | 114 | 1.000 | 1.000 |
| qwen3.5-4b | C | BP | point | 17 | 7 | 0 | 1 | 9 | 0.026 | 0.079 | 0.395 |  |  | 114 | 0.000 | 0.000 |
| qwen3.5-4b | C | BP | pessimistic | 17 | 7 | 0 | 1 | 9 | 0.001 | 0.170 | 0.395 |  |  | 114 | 0.000 | 0.000 |
| qwen3.5-4b | C | BP | optimistic | 17 | 7 | 0 | 1 | 9 | 0.075 | 0.017 | 0.395 | 270.000 | 406.000 | 114 | 0.318 | 0.348 |
