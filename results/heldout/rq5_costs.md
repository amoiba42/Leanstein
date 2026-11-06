# RQ5 costs and outcomes

## Cost per condition

| model | condition | runs | success_rate | mean_attempts | mean_tokens | mean_infer_s | mean_lean_s | tokens_per_success |
|---|---|---|---|---|---|---|---|---|
| qwen3.5-2b | B | 285 | 0.007 | 7.954 | 15561.112 | 51.076 | 5.447 | 2217458.500 |
| qwen3.5-2b | BP | 285 | 0.151 | 7.112 | 14144.425 | 54.315 | 19.356 | 93747.930 |
| qwen3.5-2b | C | 285 | 0.151 | 6.986 | 11988.474 | 44.898 | 16.830 | 79458.488 |
| qwen3.5-4b | B | 285 | 0.070 | 7.635 | 20370.291 | 142.561 | 9.491 | 290276.650 |
| qwen3.5-4b | BP | 285 | 0.239 | 6.418 | 18705.049 | 153.908 | 33.826 | 78396.162 |
| qwen3.5-4b | C | 285 | 0.242 | 6.382 | 10932.347 | 57.745 | 14.602 | 45155.348 |

## Outcome labels

| model | condition | correct_unverified | integrity_violation | unresolved | verified_repair | n_runs |
|---|---|---|---|---|---|---|
| qwen3.5-2b | B | 45 | 137 | 101 | 2 | 285 |
| qwen3.5-2b | BP | 24 | 119 | 99 | 43 | 285 |
| qwen3.5-2b | C | 27 | 73 | 142 | 43 | 285 |
| qwen3.5-4b | B | 51 | 174 | 40 | 20 | 285 |
| qwen3.5-4b | BP | 26 | 158 | 33 | 68 | 285 |
| qwen3.5-4b | C | 35 | 112 | 69 | 69 | 285 |

## Sensitivity to the generation budget N (post-hoc truncation)

| model | condition | 2 | 4 | 8 |
|---|---|---|---|---|
| qwen3.5-2b | B | 0.007 | 0.007 | 0.007 |
| qwen3.5-2b | BP | 0.112 | 0.130 | 0.151 |
| qwen3.5-2b | C | 0.140 | 0.147 | 0.151 |
| qwen3.5-4b | B | 0.039 | 0.056 | 0.070 |
| qwen3.5-4b | BP | 0.218 | 0.228 | 0.239 |
| qwen3.5-4b | C | 0.225 | 0.232 | 0.242 |

## Energy per (model, condition) block

GPU energy is measured (NVML counter); Lean CPU energy and CO2 are estimates (see prereg/study.yaml `energy`).

| model | condition | gpu_j | cpu_j_est | co2_g_est | lean_cpu_s | verified_repairs | J_per_repair |
|---|---|---|---|---|---|---|---|
| qwen3.5-2b | B | 486950.613 | 11985.645 | 99.233 | 2191.160 | 2 | 249468.129 |
| qwen3.5-2b | BP | 622170.647 | 22819.855 | 128.281 | 4171.820 | 43 | 14999.779 |
| qwen3.5-2b | C | 619320.571 | 17777.664 | 126.712 | 3250.030 | 43 | 14816.238 |
| qwen3.5-4b | B | 1388744.749 | 28362.661 | 281.847 | 5185.130 | 20 | 70855.371 |
| qwen3.5-4b | BP | 1680509.735 | 50491.054 | 344.277 | 9230.540 | 68 | 25455.894 |
| qwen3.5-4b | C | 791999.060 | 31156.026 | 163.716 | 5695.800 | 69 | 11929.784 |
