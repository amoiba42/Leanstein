# RQ1 (held-out replication, not confirmatory) and secondary paired comparisons

Family-level scores = mean over seeds of 'any instance solved'. One-sided sign-flip permutation test (x > y); Holm correction over the primary tests only; 95% family-cluster bootstrap CI.

Primary bug pool: natural + mutant (natural covers 33 < 60 families: pre-registered fallback)

## Primary

| model | bugs | x | y | n_families | rate_x | rate_y | diff | ci_lo | ci_hi | p_signflip | p_holm | cohens_h | only_x | only_y | both | neither | mcnemar_p_greater | min_detectable |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| qwen3.5-2b | primary_pool | C | B | 46 | 0.203 | 0.014 | 0.188 | 0.094 | 0.290 | 0.000 | 0.001 | 0.693 | 10 | 0 | 0 | 36 | 0.001 | 9.000 |
| qwen3.5-2b | primary_pool | C | BP | 46 | 0.203 | 0.203 | 0.000 | -0.043 | 0.043 | 0.623 | 1.000 | 0.000 | 2 | 1 | 8 | 35 | 0.500 |  |
| qwen3.5-4b | primary_pool | C | B | 46 | 0.297 | 0.101 | 0.196 | 0.101 | 0.304 | 0.000 | 0.001 | 0.505 | 11 | 0 | 4 | 31 | 0.000 | 9.000 |
| qwen3.5-4b | primary_pool | C | BP | 46 | 0.297 | 0.297 | -0.000 | -0.043 | 0.058 | 0.562 | 1.000 | 0.000 | 1 | 0 | 14 | 31 | 0.500 |  |

## Secondary / exploratory

| model | bugs | x | y | n_families | rate_x | rate_y | diff | ci_lo | ci_hi | p_signflip | cohens_h | only_x | only_y | both | neither | mcnemar_p_greater | min_detectable |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| qwen3.5-2b | primary_pool | BP | B | 46 | 0.203 | 0.014 | 0.188 | 0.101 | 0.290 | 0.000 | 0.693 | 9 | 0 | 0 | 37 | 0.002 | 8.000 |
| qwen3.5-2b | primary_pool | C | B_noauto | 46 | 0.203 | 0.000 | 0.203 | 0.101 | 0.312 | 0.000 | 0.935 | 10 | 0 | 0 | 36 | 0.001 | 9.000 |
| qwen3.5-2b | mutant | C | B | 45 | 0.207 | 0.015 | 0.193 | 0.096 | 0.296 | 0.000 | 0.702 | 10 | 0 | 0 | 35 | 0.001 | 9.000 |
| qwen3.5-2b | mutant | C | BP | 45 | 0.207 | 0.207 | -0.000 | -0.044 | 0.044 | 0.623 | -0.000 | 2 | 1 | 8 | 34 | 0.500 |  |
| qwen3.5-2b | mutant | BP | B | 45 | 0.207 | 0.015 | 0.193 | 0.104 | 0.296 | 0.000 | 0.702 | 9 | 0 | 0 | 36 | 0.002 | 8.000 |
| qwen3.5-2b | mutant | C | B_noauto | 45 | 0.207 | 0.000 | 0.207 | 0.104 | 0.319 | 0.000 | 0.946 | 10 | 0 | 0 | 35 | 0.001 | 9.000 |
| qwen3.5-2b | natural | C | B | 10 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 1.000 | 0.000 | 0 | 0 | 0 | 10 | 1.000 |  |
| qwen3.5-2b | natural | C | BP | 10 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 1.000 | 0.000 | 0 | 0 | 0 | 10 | 1.000 |  |
| qwen3.5-2b | natural | BP | B | 10 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 1.000 | 0.000 | 0 | 0 | 0 | 10 | 1.000 |  |
| qwen3.5-2b | natural | C | B_noauto | 10 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 1.000 | 0.000 | 0 | 0 | 0 | 10 | 1.000 |  |
| qwen3.5-4b | primary_pool | BP | B | 46 | 0.297 | 0.101 | 0.196 | 0.101 | 0.312 | 0.000 | 0.505 | 10 | 0 | 4 | 32 | 0.001 | 9.000 |
| qwen3.5-4b | primary_pool | C | B_noauto | 46 | 0.297 | 0.065 | 0.232 | 0.130 | 0.348 | 0.000 | 0.636 | 12 | 0 | 3 | 31 | 0.000 | 10.000 |
| qwen3.5-4b | mutant | C | B | 45 | 0.304 | 0.104 | 0.200 | 0.104 | 0.304 | 0.000 | 0.512 | 11 | 0 | 4 | 30 | 0.000 | 9.000 |
| qwen3.5-4b | mutant | C | BP | 45 | 0.304 | 0.304 | -0.000 | -0.044 | 0.059 | 0.562 | 0.000 | 1 | 0 | 14 | 30 | 0.500 |  |
| qwen3.5-4b | mutant | BP | B | 45 | 0.304 | 0.104 | 0.200 | 0.096 | 0.311 | 0.000 | 0.512 | 10 | 0 | 4 | 31 | 0.001 | 9.000 |
| qwen3.5-4b | mutant | C | B_noauto | 45 | 0.304 | 0.067 | 0.237 | 0.133 | 0.348 | 0.000 | 0.645 | 12 | 0 | 3 | 30 | 0.000 | 10.000 |
| qwen3.5-4b | natural | C | B | 10 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 1.000 | 0.000 | 0 | 0 | 0 | 10 | 1.000 |  |
| qwen3.5-4b | natural | C | BP | 10 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 1.000 | 0.000 | 0 | 0 | 0 | 10 | 1.000 |  |
| qwen3.5-4b | natural | BP | B | 10 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 1.000 | 0.000 | 0 | 0 | 0 | 10 | 1.000 |  |
| qwen3.5-4b | natural | C | B_noauto | 10 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 1.000 | 0.000 | 0 | 0 | 0 | 10 | 1.000 |  |

`B_noauto` = B with single-call automation proofs counted as failures (analysis only); `Bhammer` is exploratory and never pooled with B.

## Proofs written by the model (successful runs)

| model | condition | model_proof_successes | automation_only | top_tactics |
|---|---|---|---|---|
| qwen3.5-2b | B | 2 | 2 | simp:2 |
| qwen3.5-4b | B | 20 | 9 | simp:20, constructor:5, rfl:4, by_cases:3, aesop:3, dsimp:3 |
