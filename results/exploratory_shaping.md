# Exploratory: C against B and BP where the reference is not provable

Not a pre-registered test (no Holm correction). `reference not provable` keeps only bug instances whose reference implementation the frozen portfolio cannot prove (condition T), so a verified repair there must have a different shape from the reference. Family score = mean over seeds of 'any instance solved'; one-sided sign-flip p; 95% family-cluster bootstrap CI. Studies `main` and `main-gemma`.

| subset | model | x | y | n_families | rate_x | rate_y | diff | ci_lo | ci_hi | p_signflip | only_x | only_y |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| reference not provable | qwen3.5-2b | C | B | 85 | 0.106 | 0.000 | 0.106 | 0.055 | 0.165 | 0.000 | 9 | 0 |
| reference not provable | qwen3.5-2b | C | BP | 85 | 0.106 | 0.063 | 0.043 | 0.004 | 0.086 | 0.035 | 7 | 2 |
| reference not provable | qwen3.5-4b | C | B | 85 | 0.176 | 0.098 | 0.078 | 0.031 | 0.133 | 0.002 | 8 | 1 |
| reference not provable | qwen3.5-4b | C | BP | 85 | 0.176 | 0.165 | 0.012 | -0.024 | 0.047 | 0.336 | 3 | 2 |
| reference not provable | gemma-4-e4b-it | C | B | 85 | 0.176 | 0.024 | 0.153 | 0.082 | 0.235 | 0.000 | 13 | 0 |
| reference not provable | gemma-4-e4b-it | C | BP | 85 | 0.176 | 0.106 | 0.071 | 0.000 | 0.141 | 0.055 | 8 | 2 |
| reference provable | qwen3.5-2b | C | B | 21 | 0.968 | 0.111 | 0.857 | 0.762 | 0.937 | 0.000 | 19 | 0 |
| reference provable | qwen3.5-2b | C | BP | 21 | 0.968 | 0.889 | 0.079 | 0.016 | 0.159 | 0.062 | 3 | 0 |
| reference provable | qwen3.5-4b | C | B | 21 | 0.952 | 0.492 | 0.460 | 0.302 | 0.635 | 0.000 | 11 | 0 |
| reference provable | qwen3.5-4b | C | BP | 21 | 0.952 | 0.984 | -0.032 | -0.095 | 0.032 | 0.938 | 0 | 0 |
| reference provable | gemma-4-e4b-it | C | B | 21 | 0.810 | 0.000 | 0.810 | 0.619 | 0.952 | 0.000 | 17 | 0 |
| reference provable | gemma-4-e4b-it | C | BP | 21 | 0.810 | 0.952 | -0.143 | -0.286 | 0.000 | 1.000 | 0 | 3 |
| all (primary pool) | qwen3.5-2b | C | B | 106 | 0.277 | 0.022 | 0.255 | 0.182 | 0.330 | 0.000 | 28 | 0 |
| all (primary pool) | qwen3.5-2b | C | BP | 106 | 0.277 | 0.226 | 0.050 | 0.016 | 0.088 | 0.006 | 10 | 2 |
| all (primary pool) | qwen3.5-4b | C | B | 106 | 0.330 | 0.176 | 0.154 | 0.094 | 0.217 | 0.000 | 19 | 1 |
| all (primary pool) | qwen3.5-4b | C | BP | 106 | 0.330 | 0.327 | 0.003 | -0.028 | 0.035 | 0.500 | 3 | 2 |
| all (primary pool) | gemma-4-e4b-it | C | B | 106 | 0.302 | 0.019 | 0.283 | 0.198 | 0.368 | 0.000 | 30 | 0 |
| all (primary pool) | gemma-4-e4b-it | C | BP | 106 | 0.302 | 0.274 | 0.028 | -0.038 | 0.094 | 0.291 | 8 | 5 |

