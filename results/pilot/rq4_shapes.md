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
| array_ops | 10 | 1.000 | 0.538 | 0.462 | 0.344 | 0.582 |
| nat_int_cast | 2 | 1.000 | 0.589 | 0.411 | 0.297 | 0.521 |
| bool_ops | 1 | 1.000 | 0.595 | 0.405 | 0.297 | 0.521 |
| fold | 12 | 0.667 | 0.587 | 0.079 | -0.231 | 0.371 |
| array_index_bang | 3 | 0.667 | 0.597 | 0.069 | -0.622 | 0.486 |
| uses_if | 17 | 0.353 | 0.672 | -0.319 | -0.567 | -0.066 |
| nat_sub | 13 | 0.154 | 0.694 | -0.540 | -0.748 | -0.297 |
| list_combinators | 20 | 0.200 | 0.745 | -0.545 | -0.746 | -0.331 |
| uses_match | 7 | 0.000 | 0.662 | -0.662 | -0.776 | -0.551 |
| let_rec | 9 | 0.000 | 0.682 | -0.682 | -0.789 | -0.564 |
| any_recursion | 9 | 0.000 | 0.682 | -0.682 | -0.791 | -0.571 |

## Closing portfolio entry of verified repairs

| condition | entry | n |
|---|---|---|
| BP | unfold_omega | 7 |
| BP | simp | 6 |
| BP | simp_all | 2 |
| BP | simp_omega | 2 |
| BP | simp_grind | 1 |
| C | simp | 12 |
| C | unfold_omega | 11 |
| C | simp_grind | 2 |
| C | simp_omega | 1 |
| Cplain | unfold_omega | 10 |
| Cplain | simp | 8 |
| Cplain | simp_grind | 1 |
