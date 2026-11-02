# Acceptance checks, go/no-go, open issues

[← index](../ARCHITECTURE.md)

## 1. Checks per component

| Component | Check |
|---|---|
| Toolchain (A) | Clean build from scratch on a second machine; lockfile committed; VERINA builds on the pinned Lean 4.24+ |
| Worker (A) | Import time measured and recorded; `proc_wall_secs` clears it with margin; cgroup `memory` controller confirmed delegated; a crash requeues to a fresh worker without consuming N |
| Sandbox (A) | A runaway tactic and a deliberate memory hog are both killed within limits, host unaffected; 1,000 `verify()` calls complete unattended, **spanning a worker restart, with identical results** |
| Pre-filter (A) | Unit tests reject injected `sorry`, `axiom`, weakened spec, edited test, edit outside region, empty body, constant return, spec copy, tautology. **Every reference solution passes (zero false rejections)**, plus a hand-labelled false-positive rate on ~50 real pilot attempts |
| Tactic router (A) | Coverage on references reported for router and full ladder; router closes at least the ladder's set |
| Test runner (A) | Agrees with VERINA's own results on all references; available in Week 2 because Phase 1 needs it |
| Integrity suite (A) | Zero false successes |
| Determinism (A, B) | Same input, same output across reruns; same prompt and seed returns identical text |
| Harvester (B) | 5 hand-verified real errors; yield table; `spec_theorem_elaborates` gate works; cap reached ⇒ task dropped, never an infinite loop |
| Prompts (B) | Length table shows equal budgets across A, B, C, C-plain; `prompt_truncated` rate reported per condition |
| Feedback router (B) | Per failure type and condition, output matches the router table; no feedback string shares a token 5-gram with any hidden-test file |
| Driver (C) | Resumes after a crash; skips finished work; flushes before the next step; a rerun keeps `attempt_idx`; 5-task dry run across all conditions |
| Cross-evaluation (C) | Replays logged B candidates through C's full pipeline; region splice drops B's proof text; three buckets reported |
| Power (C) | Required N computed from pilot `p01`/`p10` under pessimistic and optimistic assumptions, **before the freeze** |
| Energy (C) | Fields populated on every attempt; idle baseline recorded and subtracted |
| Analysis (C) | Every figure regenerates from raw logs with one command |

## 2. Go/no-go (end of Week 2)

- Automation covers at least ~40% of references.
- C repairs at least one task A and B both fail.
- Integrity suite clean: no false successes, no false rejections of references; the sandbox holds.
- Cost estimate fits the available compute.
- Harvest yield is sufficient: 20 pilot tasks obtained from real errors, projected 60+.
- **Power calculation done**, and the required N is reachable.

## 3. Pre-freeze checklist, ordered

1. Measure Mathlib import time for one tier command.
2. Confirm VERINA builds on Lean 4.24+. If not, drop `grind` and pin an older Lean.
3. Confirm cgroup `memory` delegation; confirm no orphan `lean` after a runaway-tactic kill.
4. Power calculation → minimum task count.
5. Jaccard distribution of reference solutions versus their postconditions; hand-label ~50 pilot attempts for pre-filter false positives.
6. Pilot failure-type distribution per condition. If `proof_failed` is rare in C, RQ4 is dead before it starts.
7. Re-estimate total wall-hours from pilot timings; decide GPU server.
8. Write into prereg: unit of analysis, both ITT and T-feasible analyses, the multiple-comparison plan, the `wallclock_cap`-rate-by-condition check.
9. Redefine C-plain (see issue 11). Decide the B-hammer arm (issue 10). Schedule the cross-evaluation.
10. Fix `diagram.png`.

## 4. Assumptions and open issues

1. **Spec statement is shown to the model.** The original manifest wording said the spec file is never given to the model; that cannot hold for B. We show the statement, lock the file, hide tests and reference.
2. **Bug-source model:** default is the 1.5B only; a 3B-sourced set is optional. Decide in Week 1 — RQ5 is confounded without it, because every task is one the 1.5B already failed zero-shot, while the 3B is repairing another model's mistakes.
3. **Import time and memory:** measure before the freeze. Import time sets `proc_wall_secs`; 4 GB per worker is an estimate.
4. **REPL stability** is the main revision 3 risk. The fallback is slower; recompute the load estimate if taken.
5. **Task wall clock (900 s)** was sized for one-shot processes. Recheck against pilot timings now that import is amortised, and report the `wallclock_cap` rate per condition — an unequal rate breaks the equal-N claim.
6. **Heartbeat calibration:** the 2 s / 8 s budgets are calibrated heartbeats; calibrate on the pilot and freeze.
7. **Pre-filter parser:** tokenizer plus regex (default) or tree-sitter Lean grammar.
8. **Energy attribution** under parallel workers is approximate.
9. **Real-error selection bias:** tasks the model happened to get right are dropped; report the yield and the difficulty distribution.
10. **B's use of automation.** `grind`/`aesop` are legal in B. Decide whether to add a **B-hammer** arm (B's prompt given the same frozen tactic list) — it separates "C's code-shaping helps" from "we only told C about `grind`". Costs +25% compute.
11. **C-plain currently differs from C in all feedback, not just the hint.** It gets "failed, retry" even for `compile_fail`, so RQ4 as written answers "does feedback help". Give C-plain the same compile and integrity messages and differ only on `proof_failed`. Costs nothing.
12. **Pre-filter bans helper lemmas in C's code region** (`theorem`, `lemma`, `example`), yet adding a helper is a natural way to shape code for automation. Decide whether `have` and local helpers are allowed, and state the restriction in Threats either way.
13. **Spec-copy thresholds may reject honest code.** For many VERINA tasks the correct implementation genuinely shares tokens with the postcondition. Measure the reference distribution before trusting 0.80 / 0.60.
14. **Condition A at temperature 0.4** will produce near-duplicate samples, and duplicates still consume N. Report the duplicate rate; if it is high, stop calling A pass@N.
15. **Tactic coverage drift.** The router is calibrated on 20 pilot references, then only the router ever runs. Audit by running the full ladder on a random 10% of main-set candidates.
16. **Hint wording is part of the treatment.** Hint templates are frozen with the tactics list and hashed.
17. **Hard paper deadline, compute (laptop only vs GPU server), venue, and whether a pre-registration document must be submitted** remain open in the plan.
