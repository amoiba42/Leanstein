# RQ4 code shapes

## Reference implementations (condition T)

| feature | n_with | p_closed_with | p_closed_without | diff | ci_lo | ci_hi |
|---|---|---|---|---|---|---|
| bool_ops | 19 | 0.158 | 0.230 | -0.072 | -0.234 | 0.125 |
| list_combinators | 70 | 0.157 | 0.263 | -0.106 | -0.224 | 0.006 |
| array_ops | 69 | 0.116 | 0.287 | -0.171 | -0.279 | -0.058 |
| array_index_bang | 58 | 0.086 | 0.286 | -0.200 | -0.300 | -0.087 |
| self_recursive | 1 | 0.000 | 0.224 | -0.224 | -0.284 | -0.164 |
| decide_in_code | 1 | 0.000 | 0.224 | -0.224 | -0.290 | -0.166 |
| where_helpers | 1 | 0.000 | 0.224 | -0.224 | -0.286 | -0.164 |
| imperative_loop | 9 | 0.000 | 0.234 | -0.234 | -0.301 | -0.174 |
| well_founded | 12 | 0.000 | 0.238 | -0.238 | -0.298 | -0.177 |
| array_index_opt | 12 | 0.000 | 0.238 | -0.238 | -0.302 | -0.179 |
| nat_sub | 16 | 0.000 | 0.244 | -0.244 | -0.315 | -0.179 |
| nat_int_cast | 37 | 0.027 | 0.272 | -0.245 | -0.333 | -0.154 |
| fold | 23 | 0.000 | 0.255 | -0.255 | -0.323 | -0.190 |
| uses_match | 66 | 0.015 | 0.339 | -0.324 | -0.414 | -0.235 |
| let_rec | 77 | 0.000 | 0.383 | -0.383 | -0.480 | -0.291 |
| uses_if | 138 | 0.101 | 0.587 | -0.486 | -0.628 | -0.336 |
| any_recursion | 101 | 0.000 | 0.494 | -0.494 | -0.600 | -0.390 |

## Test-passing candidates from code-only conditions (C, C-plain, S, S-plain)

| feature | n_with | p_closed_with | p_closed_without | diff | ci_lo | ci_hi |
|---|---|---|---|---|---|---|
| bool_ops | 35 | 0.686 | 0.543 | 0.143 | -0.016 | 0.301 |
| fold | 173 | 0.509 | 0.551 | -0.042 | -0.120 | 0.040 |
| list_combinators | 562 | 0.482 | 0.584 | -0.101 | -0.153 | -0.049 |
| nat_sub | 113 | 0.372 | 0.560 | -0.188 | -0.283 | -0.092 |
| array_ops | 309 | 0.362 | 0.593 | -0.231 | -0.293 | -0.173 |
| array_index_bang | 212 | 0.297 | 0.587 | -0.289 | -0.353 | -0.221 |
| uses_if | 678 | 0.375 | 0.685 | -0.310 | -0.358 | -0.259 |
| nat_int_cast | 152 | 0.237 | 0.581 | -0.344 | -0.415 | -0.264 |
| uses_match | 233 | 0.103 | 0.626 | -0.523 | -0.572 | -0.476 |
| decide_in_code | 2 | 0.000 | 0.547 | -0.547 | -0.572 | -0.522 |
| where_helpers | 4 | 0.000 | 0.548 | -0.548 | -0.573 | -0.522 |
| well_founded | 4 | 0.000 | 0.548 | -0.548 | -0.572 | -0.523 |
| array_index_opt | 21 | 0.000 | 0.554 | -0.554 | -0.577 | -0.528 |
| self_recursive | 32 | 0.000 | 0.558 | -0.558 | -0.584 | -0.534 |
| let_rec | 252 | 0.012 | 0.652 | -0.641 | -0.670 | -0.610 |
| any_recursion | 288 | 0.007 | 0.672 | -0.665 | -0.692 | -0.637 |

## Closing portfolio entry of verified repairs

| condition | entry | n |
|---|---|---|
| BP | simp | 121 |
| BP | unfold_omega | 74 |
| BP | simp_all | 64 |
| BP | simp_omega | 30 |
| BP | simp_grind | 28 |
| BP | aesop | 10 |
| BP | split_simp_all | 10 |
| BP | split_omega | 6 |
| C | simp | 146 |
| C | unfold_omega | 90 |
| C | simp_all | 58 |
| C | simp_omega | 38 |
| C | simp_grind | 36 |
| C | split_simp_all | 13 |
| C | aesop | 10 |
| C | split_omega | 8 |
| Cplain | simp | 129 |
| Cplain | unfold_omega | 76 |
| Cplain | simp_all | 53 |
| Cplain | simp_omega | 33 |
| Cplain | simp_grind | 26 |
| Cplain | split_simp_all | 11 |
| Cplain | aesop | 7 |
| Cplain | split_omega | 6 |
| S | simp | 30 |
| S | simp_grind | 9 |
| S | simp_omega | 4 |
| S | simp_all | 1 |
| Splain | simp | 31 |
| Splain | simp_grind | 9 |
| Splain | simp_omega | 3 |
| Splain | simp_all | 1 |
| Splain | split_simp_all | 1 |
