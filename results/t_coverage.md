# Condition T: portfolio coverage on reference implementations

Screened 189 VERINA tasks; eligible 184; excluded 5 ({'known_defect:not_evaluable,ref_visible_fail': 1, 'known_defect:unsupported_map_type,unrenderable_tests': 1, 'known_defect:test_contradicts_description,ref_visible_fail': 1, 'unrenderable_tests': 1, 'known_defect:test_contradicts_spec,ref_visible_fail': 1}).

## Coverage by tier

| tier | sum | count | mean |
|---|---|---|---|
| advanced | 4 | 80 | 0.050 |
| basic | 37 | 104 | 0.356 |
| all | 41 | 184 | 0.223 |

## Closing entry

| entry | n |
|---|---|
| simp | 13 |
| simp_omega | 7 |
| simp_all | 7 |
| simp_grind | 5 |
| unfold_omega | 5 |
| aesop | 2 |
| split_simp_all | 1 |
| split_omega | 1 |

## Coverage vs. availability of a human reference proof

| ref_proof | T_closed | n |
|---|---|---|
| absent | False | 130 |
| absent | True | 8 |
| human_broken | False | 2 |
| human_broken | True | 11 |
| human_ok | False | 11 |
| human_ok | True | 22 |
