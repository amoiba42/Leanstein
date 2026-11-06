# RQ5 energy (estimate, deviation D-4)

GPU energy = calibrated J per completion token and per prompt token (marginal board power of GPU 1 over its idle baseline, our slice, study serving settings) x the tokens each condition used. CPU = Lean seconds x 5.47 W/thread. CO2 at 0.716 kg/kWh. Range = min/max of the three calibration cycles. Static (idle) GPU power is shared with other tenants and not attributed.

## Coefficients

| model | a_mean | a_min | a_max | b_mean | b_min | b_max | idle_w |
|---|---|---|---|---|---|---|---|
| gemma-4-e4b-it | 0.2515 | 0.2419 | 0.2631 | 0.0206 | 0.0196 | 0.0218 | 52.8847 |
| goedel-code-prover-8b | 0.3919 | 0.3406 | 0.4387 | 0.0265 | 0.0256 | 0.0276 | 54.0877 |
| qwen3.5-2b | 0.1412 | 0.1326 | 0.1466 | 0.0081 | 0.0068 | 0.0089 | 46.2496 |
| qwen3.5-4b | 0.2580 | 0.2215 | 0.2899 | 0.0243 | 0.0229 | 0.0262 | 51.9092 |


## Per condition

| split | model | condition | runs | repairs | gpu_kj_mean | cpu_kj | total_kj | kj_per_repair | kj_per_repair_lo | kj_per_repair_hi | co2_g_per_repair |
|---|---|---|---|---|---|---|---|---|---|---|---|
| main | gemma-4-e4b-it | B | 231 | 2 | 458.57 | 6.16 | 464.73 | 232.36 | 223.13 | 243.56 | 46.21 |
| main | gemma-4-e4b-it | BP | 231 | 53 | 399.85 | 65.42 | 465.27 | 8.78 | 8.48 | 9.15 | 1.75 |
| main | gemma-4-e4b-it | C | 231 | 58 | 118.21 | 32.82 | 151.03 | 2.60 | 2.52 | 2.71 | 0.52 |
| main | goedel-code-prover-8b | A | 231 | 38 | 408.81 | 2.93 | 411.74 | 10.84 | 9.52 | 12.05 | 2.15 |
| main | goedel-code-prover-8b | B | 231 | 48 | 403.67 | 4.98 | 408.65 | 8.51 | 7.58 | 9.39 | 1.69 |
| main | qwen3.5-2b | A | 693 | 13 | 286.75 | 23.40 | 310.15 | 23.86 | 22.24 | 24.87 | 4.74 |
| main | qwen3.5-2b | B | 693 | 7 | 355.10 | 34.95 | 390.04 | 55.72 | 51.72 | 58.24 | 11.08 |
| main | qwen3.5-2b | BP | 693 | 110 | 338.56 | 56.74 | 395.30 | 3.59 | 3.35 | 3.75 | 0.71 |
| main | qwen3.5-2b | Bhammer | 693 | 21 | 411.38 | 29.70 | 441.08 | 21.00 | 19.41 | 22.01 | 4.18 |
| main | qwen3.5-2b | C | 693 | 150 | 225.54 | 68.17 | 293.70 | 1.96 | 1.84 | 2.04 | 0.39 |
| main | qwen3.5-2b | Cplain | 693 | 153 | 246.55 | 63.19 | 309.74 | 2.02 | 1.90 | 2.10 | 0.40 |
| main | qwen3.5-2b | S | 267 | 10 | 113.71 | 49.74 | 163.44 | 16.34 | 15.43 | 16.92 | 3.25 |
| main | qwen3.5-2b | Splain | 267 | 11 | 115.27 | 43.01 | 158.28 | 14.39 | 13.57 | 14.91 | 2.86 |
| main | qwen3.5-4b | A | 693 | 100 | 877.09 | 17.16 | 894.25 | 8.94 | 7.79 | 9.98 | 1.78 |
| main | qwen3.5-4b | B | 693 | 79 | 1039.02 | 23.03 | 1062.05 | 13.44 | 11.84 | 14.93 | 2.67 |
| main | qwen3.5-4b | BP | 693 | 182 | 984.92 | 93.60 | 1078.52 | 5.93 | 5.26 | 6.54 | 1.18 |
| main | qwen3.5-4b | Bhammer | 693 | 131 | 814.08 | 29.95 | 844.04 | 6.44 | 5.73 | 7.12 | 1.28 |
| main | qwen3.5-4b | C | 693 | 191 | 429.86 | 68.87 | 498.72 | 2.61 | 2.36 | 2.85 | 0.52 |
| main | qwen3.5-4b | Cplain | 693 | 188 | 373.01 | 65.19 | 438.19 | 2.33 | 2.11 | 2.55 | 0.46 |
| main | qwen3.5-4b | S | 267 | 34 | 238.42 | 28.58 | 267.01 | 7.85 | 7.03 | 8.63 | 1.56 |
| main | qwen3.5-4b | Splain | 267 | 34 | 201.07 | 33.44 | 234.51 | 6.90 | 6.21 | 7.55 | 1.37 |
| heldout | qwen3.5-2b | B | 285 | 2 | 145.76 | 8.49 | 154.25 | 77.12 | 71.34 | 80.76 | 15.34 |
| heldout | qwen3.5-2b | BP | 285 | 43 | 133.18 | 30.18 | 163.35 | 3.80 | 3.55 | 3.95 | 0.76 |
| heldout | qwen3.5-2b | C | 285 | 43 | 106.88 | 26.24 | 133.12 | 3.10 | 2.90 | 3.22 | 0.62 |
| heldout | qwen3.5-4b | B | 285 | 20 | 470.13 | 14.80 | 484.93 | 24.25 | 21.37 | 26.91 | 4.82 |
| heldout | qwen3.5-4b | BP | 285 | 68 | 453.67 | 52.73 | 506.40 | 7.45 | 6.62 | 8.21 | 1.48 |
| heldout | qwen3.5-4b | C | 285 | 69 | 194.34 | 22.76 | 217.10 | 3.15 | 2.82 | 3.45 | 0.63 |

