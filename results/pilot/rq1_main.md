# RQ1 (pilot, not confirmatory) and secondary paired comparisons

Family-level scores = mean over seeds of 'any instance solved'. One-sided sign-flip permutation test (x > y); Holm correction over the primary tests only; 95% family-cluster bootstrap CI.

Primary bug pool: natural + mutant (natural covers 33 < 60 families: pre-registered fallback)

## Primary

| model | bugs | x | y | n_families | rate_x | rate_y | diff | ci_lo | ci_hi | p_signflip | p_holm | cohens_h | only_x | only_y | both | neither | mcnemar_p_greater | min_detectable |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| qwen3.5-2b | primary_pool | C | B | 17 | 0.353 | 0.000 | 0.353 | 0.118 | 0.588 | 0.016 | 0.062 | 1.272 | 6 | 0 | 0 | 11 | 0.016 | 6.000 |
| qwen3.5-2b | primary_pool | C | BP | 17 | 0.353 | 0.235 | 0.118 | 0.000 | 0.294 | 0.250 | 0.500 | 0.259 | 2 | 0 | 4 | 11 | 0.250 |  |
| qwen3.5-4b | primary_pool | C | B | 17 | 0.471 | 0.235 | 0.235 | 0.059 | 0.471 | 0.062 | 0.188 | 0.499 | 4 | 0 | 4 | 9 | 0.062 |  |
| qwen3.5-4b | primary_pool | C | BP | 17 | 0.471 | 0.412 | 0.059 | -0.118 | 0.235 | 0.500 | 0.500 | 0.119 | 2 | 1 | 6 | 8 | 0.500 |  |

## Secondary / exploratory

| model | bugs | x | y | n_families | rate_x | rate_y | diff | ci_lo | ci_hi | p_signflip | cohens_h | only_x | only_y | both | neither | mcnemar_p_greater | min_detectable |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| qwen3.5-2b | primary_pool | C | Cplain | 17 | 0.353 | 0.294 | 0.059 | 0.000 | 0.176 | 0.500 | 0.126 | 1 | 0 | 5 | 11 | 0.500 |  |
| qwen3.5-2b | primary_pool | C | A | 17 | 0.353 | 0.000 | 0.353 | 0.118 | 0.588 | 0.016 | 1.272 | 6 | 0 | 0 | 11 | 0.016 | 6.000 |
| qwen3.5-2b | primary_pool | BP | B | 17 | 0.235 | 0.000 | 0.235 | 0.059 | 0.471 | 0.062 | 1.013 | 4 | 0 | 0 | 13 | 0.062 |  |
| qwen3.5-2b | primary_pool | C | B_noauto | 17 | 0.353 | 0.000 | 0.353 | 0.118 | 0.588 | 0.016 | 1.272 | 6 | 0 | 0 | 11 | 0.016 | 6.000 |
| qwen3.5-2b | primary_pool | C | Bhammer | 17 | 0.353 | 0.059 | 0.294 | 0.118 | 0.529 | 0.031 | 0.782 | 5 | 0 | 1 | 11 | 0.031 | 5.000 |
| qwen3.5-2b | primary_pool | Bhammer | B | 17 | 0.059 | 0.000 | 0.059 | 0.000 | 0.176 | 0.500 | 0.490 | 1 | 0 | 0 | 16 | 0.500 |  |
| qwen3.5-2b | mutant | C | B | 17 | 0.353 | 0.000 | 0.353 | 0.118 | 0.588 | 0.016 | 1.272 | 6 | 0 | 0 | 11 | 0.016 | 6.000 |
| qwen3.5-2b | mutant | C | BP | 17 | 0.353 | 0.235 | 0.118 | 0.000 | 0.294 | 0.250 | 0.259 | 2 | 0 | 4 | 11 | 0.250 |  |
| qwen3.5-2b | mutant | C | Cplain | 17 | 0.353 | 0.294 | 0.059 | 0.000 | 0.176 | 0.500 | 0.126 | 1 | 0 | 5 | 11 | 0.500 |  |
| qwen3.5-2b | mutant | C | A | 17 | 0.353 | 0.000 | 0.353 | 0.118 | 0.588 | 0.016 | 1.272 | 6 | 0 | 0 | 11 | 0.016 | 6.000 |
| qwen3.5-2b | mutant | BP | B | 17 | 0.235 | 0.000 | 0.235 | 0.059 | 0.471 | 0.062 | 1.013 | 4 | 0 | 0 | 13 | 0.062 |  |
| qwen3.5-2b | mutant | C | B_noauto | 17 | 0.353 | 0.000 | 0.353 | 0.118 | 0.588 | 0.016 | 1.272 | 6 | 0 | 0 | 11 | 0.016 | 6.000 |
| qwen3.5-2b | mutant | C | Bhammer | 17 | 0.353 | 0.059 | 0.294 | 0.118 | 0.529 | 0.031 | 0.782 | 5 | 0 | 1 | 11 | 0.031 | 5.000 |
| qwen3.5-2b | mutant | Bhammer | B | 17 | 0.059 | 0.000 | 0.059 | 0.000 | 0.176 | 0.500 | 0.490 | 1 | 0 | 0 | 16 | 0.500 |  |
| qwen3.5-2b | natural | C | B | 7 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 1.000 | 0.000 | 0 | 0 | 0 | 7 | 1.000 |  |
| qwen3.5-2b | natural | C | BP | 7 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 1.000 | 0.000 | 0 | 0 | 0 | 7 | 1.000 |  |
| qwen3.5-2b | natural | C | Cplain | 7 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 1.000 | 0.000 | 0 | 0 | 0 | 7 | 1.000 |  |
| qwen3.5-2b | natural | C | A | 7 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 1.000 | 0.000 | 0 | 0 | 0 | 7 | 1.000 |  |
| qwen3.5-2b | natural | BP | B | 7 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 1.000 | 0.000 | 0 | 0 | 0 | 7 | 1.000 |  |
| qwen3.5-2b | natural | C | B_noauto | 7 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 1.000 | 0.000 | 0 | 0 | 0 | 7 | 1.000 |  |
| qwen3.5-2b | natural | C | Bhammer | 7 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 1.000 | 0.000 | 0 | 0 | 0 | 7 | 1.000 |  |
| qwen3.5-2b | natural | Bhammer | B | 7 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 1.000 | 0.000 | 0 | 0 | 0 | 7 | 1.000 |  |
| qwen3.5-4b | primary_pool | C | Cplain | 17 | 0.471 | 0.353 | 0.118 | 0.000 | 0.294 | 0.250 | 0.240 | 2 | 0 | 6 | 9 | 0.250 |  |
| qwen3.5-4b | primary_pool | C | A | 17 | 0.471 | 0.294 | 0.176 | 0.000 | 0.353 | 0.125 | 0.366 | 3 | 0 | 5 | 9 | 0.125 |  |
| qwen3.5-4b | primary_pool | BP | B | 17 | 0.412 | 0.235 | 0.176 | 0.000 | 0.353 | 0.125 | 0.381 | 3 | 0 | 4 | 10 | 0.125 |  |
| qwen3.5-4b | primary_pool | C | B_noauto | 17 | 0.471 | 0.235 | 0.235 | 0.059 | 0.471 | 0.062 | 0.499 | 4 | 0 | 4 | 9 | 0.062 |  |
| qwen3.5-4b | primary_pool | C | Bhammer | 17 | 0.471 | 0.294 | 0.176 | 0.000 | 0.353 | 0.125 | 0.366 | 3 | 0 | 5 | 9 | 0.125 |  |
| qwen3.5-4b | primary_pool | Bhammer | B | 17 | 0.294 | 0.235 | 0.059 | 0.000 | 0.176 | 0.500 | 0.134 | 1 | 0 | 4 | 12 | 0.500 |  |
| qwen3.5-4b | mutant | C | B | 17 | 0.471 | 0.235 | 0.235 | 0.059 | 0.471 | 0.062 | 0.499 | 4 | 0 | 4 | 9 | 0.062 |  |
| qwen3.5-4b | mutant | C | BP | 17 | 0.471 | 0.412 | 0.059 | -0.118 | 0.235 | 0.500 | 0.119 | 2 | 1 | 6 | 8 | 0.500 |  |
| qwen3.5-4b | mutant | C | Cplain | 17 | 0.471 | 0.353 | 0.118 | 0.000 | 0.294 | 0.250 | 0.240 | 2 | 0 | 6 | 9 | 0.250 |  |
| qwen3.5-4b | mutant | C | A | 17 | 0.471 | 0.294 | 0.176 | 0.000 | 0.353 | 0.125 | 0.366 | 3 | 0 | 5 | 9 | 0.125 |  |
| qwen3.5-4b | mutant | BP | B | 17 | 0.412 | 0.235 | 0.176 | 0.000 | 0.353 | 0.125 | 0.381 | 3 | 0 | 4 | 10 | 0.125 |  |
| qwen3.5-4b | mutant | C | B_noauto | 17 | 0.471 | 0.235 | 0.235 | 0.059 | 0.471 | 0.062 | 0.499 | 4 | 0 | 4 | 9 | 0.062 |  |
| qwen3.5-4b | mutant | C | Bhammer | 17 | 0.471 | 0.294 | 0.176 | 0.000 | 0.353 | 0.125 | 0.366 | 3 | 0 | 5 | 9 | 0.125 |  |
| qwen3.5-4b | mutant | Bhammer | B | 17 | 0.294 | 0.235 | 0.059 | 0.000 | 0.176 | 0.500 | 0.134 | 1 | 0 | 4 | 12 | 0.500 |  |
| qwen3.5-4b | natural | C | B | 7 | 0.143 | 0.000 | 0.143 | 0.000 | 0.429 | 0.500 | 0.775 | 1 | 0 | 0 | 6 | 0.500 |  |
| qwen3.5-4b | natural | C | BP | 7 | 0.143 | 0.000 | 0.143 | 0.000 | 0.429 | 0.500 | 0.775 | 1 | 0 | 0 | 6 | 0.500 |  |
| qwen3.5-4b | natural | C | Cplain | 7 | 0.143 | 0.000 | 0.143 | 0.000 | 0.429 | 0.500 | 0.775 | 1 | 0 | 0 | 6 | 0.500 |  |
| qwen3.5-4b | natural | C | A | 7 | 0.143 | 0.000 | 0.143 | 0.000 | 0.429 | 0.500 | 0.775 | 1 | 0 | 0 | 6 | 0.500 |  |
| qwen3.5-4b | natural | BP | B | 7 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 1.000 | 0.000 | 0 | 0 | 0 | 7 | 1.000 |  |
| qwen3.5-4b | natural | C | B_noauto | 7 | 0.143 | 0.000 | 0.143 | 0.000 | 0.429 | 0.500 | 0.775 | 1 | 0 | 0 | 6 | 0.500 |  |
| qwen3.5-4b | natural | C | Bhammer | 7 | 0.143 | 0.000 | 0.143 | 0.000 | 0.429 | 0.500 | 0.775 | 1 | 0 | 0 | 6 | 0.500 |  |
| qwen3.5-4b | natural | Bhammer | B | 7 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 1.000 | 0.000 | 0 | 0 | 0 | 7 | 1.000 |  |

`B_noauto` = B with single-call automation proofs counted as failures (analysis only); `Bhammer` is exploratory and never pooled with B.

## Proofs written by the model (successful runs)

| model | condition | model_proof_successes | automation_only | top_tactics |
|---|---|---|---|---|
| qwen3.5-2b | Bhammer | 1 | 1 | omega:1, simp:1 |
| qwen3.5-4b | A | 9 | 1 | simp:8, ring:4, omega:3, ring_nf:3, rfl:2, dsimp:2 |
| qwen3.5-4b | B | 8 | 0 | simp:6, ring:4, dsimp:3, omega:2, ring_nf:2, constructor:2 |
| qwen3.5-4b | Bhammer | 9 | 6 | simp:8, omega:5, unfold:3, ring_nf:1, try:1, constructor:1 |
