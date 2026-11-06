# 0002. Control conditions

## Status
Accepted

## Context
A win for C could have explanations other than the method: C has automation and B does not; C may only revert the
bug; the hint text rather than the code-only contract may do the work; B may be a weak baseline.

## Decision
All conditions share task, budget and checks; only the proof source and feedback differ.

| ID | Role |
|---|---|
| T | portfolio alone on references and buggy starts: coverage and weak-spec detection |
| A | code + proof, independent samples, no feedback: lower bound |
| B | code + proof with Lean errors and witness: main control |
| BP | as B, portfolio tried first, model proof as fallback: separates "not writing proofs" from "having automation" |
| C-plain | as C with a generic retry: tests the hint (RQ3) |
| S / S-plain | start from a correct reference the portfolio cannot prove: tests deliberate re-shaping |
| Bhammer | B whose prompt lists the portfolio's tactics: exploratory, never pooled with B |

Derived analyses (no extra model calls): **B_noauto** counts B successes whose proof is a single-call automation
proof as failures (registry frozen in `prereg/portfolio.yaml`); the **B→C cross-evaluation** re-verifies B attempts
whose code compiled but whose proof failed through C's pipeline.

Bhammer runs unconditionally for the primary models, 3 seeds, on `main`, after the held-out run, as decided before
the freeze from the pilot cost estimate (1.73 h of inference for 84 pilot runs, about 10 GPU hours on `main`). A
conditional rule ("run it if the GPU frees") was rejected because it would stay open until results were known (team decision 5 in `prereg/deviations.md`).

## Consequences
- The primary family is four tests: C vs B and C vs BP, for each primary model.
- Bhammer, `B_noauto` and the cross-evaluation answer "B is a strawman" without changing the primary tests.
