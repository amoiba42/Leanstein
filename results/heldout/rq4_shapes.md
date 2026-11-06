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
| bool_ops | 1 | 1.000 | 0.642 | 0.358 | 0.294 | 0.430 |
| list_combinators | 57 | 0.702 | 0.615 | 0.086 | -0.071 | 0.226 |
| array_ops | 33 | 0.636 | 0.645 | -0.009 | -0.192 | 0.168 |
| fold | 15 | 0.533 | 0.654 | -0.121 | -0.396 | 0.153 |
| array_index_bang | 11 | 0.364 | 0.663 | -0.299 | -0.596 | 0.040 |
| uses_if | 92 | 0.435 | 0.878 | -0.443 | -0.565 | -0.319 |
| imperative_loop | 1 | 0.000 | 0.647 | -0.647 | -0.717 | -0.578 |
| array_index_opt | 1 | 0.000 | 0.647 | -0.647 | -0.717 | -0.576 |
| nat_int_cast | 1 | 0.000 | 0.647 | -0.647 | -0.715 | -0.573 |
| self_recursive | 4 | 0.000 | 0.659 | -0.659 | -0.728 | -0.585 |
| nat_sub | 15 | 0.000 | 0.704 | -0.704 | -0.776 | -0.635 |
| uses_match | 30 | 0.000 | 0.778 | -0.778 | -0.843 | -0.709 |
| let_rec | 32 | 0.000 | 0.789 | -0.789 | -0.852 | -0.719 |
| any_recursion | 36 | 0.000 | 0.812 | -0.812 | -0.872 | -0.744 |

## Closing portfolio entry of verified repairs

| condition | entry | n |
|---|---|---|
| BP | simp_grind | 47 |
| BP | simp | 30 |
| BP | simp_all | 18 |
| BP | aesop | 13 |
| BP | unfold_omega | 2 |
| BP | simp_all_omega | 1 |
| C | simp_grind | 40 |
| C | simp | 31 |
| C | simp_all | 24 |
| C | aesop | 14 |
| C | unfold_omega | 2 |
| C | simp_all_omega | 1 |
