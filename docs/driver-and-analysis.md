# Driver and analysis — loop, logging, audit, cross-evaluation, power, energy

[← index](../ARCHITECTURE.md) · **Member C**

## 1. Phase 2: generation loop

Identical for every condition except what `generate()` sends and how many candidates are independent.

```
for (task, condition, model, seed) in model_major_order(manifests):
    state = preflight(task)                      # verify buggy code once; not counted in N
    for attempt_idx in range(N):                 # N = 5, model-caused attempts only
        if wallclock(task_run) > task_wallclock_secs:
            finish(task_run, "unresolved", reason="wallclock_cap"); break

        cand = generate(task, condition, history_window(state), seed_for(seed, attempt_idx))
        res  = verify_with_infra_retry(task, cand, condition)
        append_jsonl(record(attempt_idx, cand, res)); flush()   # BEFORE anything else

        if res.end_to_end_success:
            maybe_queue_for_audit(record); finish(task_run, "verified"); break
        state = feedback_router(res, condition)  # A: no feedback, independent samples
    else:
        finish(task_run, "unresolved", reason="N_exhausted")
```

| Condition | Candidates | Feedback to next attempt | Proof from |
|---|---|---|---|
| A | N independent samples (pass@N), stop at first success | none | model |
| B | up to N sequential tries | Lean errors; generic warning on test failure; category message on integrity failure | model |
| C | up to N sequential tries | structural hint; generic warning on test failure; category message on integrity failure | fixed tactic pipeline |
| C-plain | up to N sequential tries | only "failed, retry" for every failure type | fixed tactic pipeline |
| T | none | none | pipeline on buggy code (must fail) and on reference (upper bound) |

### What counts as an attempt (the N budget)

- One attempt = one `generate()` call plus its `verify()`.
- **Consumes N:** integrity_fail, format_fail, compile_fail, proof_failed, test_failed, resource_exhausted, and a verified success.
- **Never consumes N:** infra_crash and worker_crash reruns. The rerun keeps the same `attempt_idx` and increments `infra_retry_idx`.
- Identical candidate text (same hash) returns the cached `verify()` result with no Lean time, but still consumes N. Record `cache_hit`; at temperature 0.4 condition A will produce duplicates, which bears on whether A is really pass@N.
- Early stop on first end-to-end success (A included).

### Infrastructure reruns

```
def verify_with_infra_retry(task, cand, condition):
    for k in range(infra_retry_cap + 1):            # cap = 3 reruns
        res = verify(task, cand.code, cand.proof, mode_for(condition))
        log_infra_attempt_if_needed(res, k)         # every try is logged
        if res.failure_type not in ("infra_crash", "worker_crash"):
            return res
        if k == 0: first = res
        elif same_signature(res, first):            # same OOM / timeout twice on the same candidate
            return res.reclassify("resource_exhausted")   # candidate-caused: counts as an attempt
        sleep(infra_backoff_secs[k - 1] if k > 0 else 0)
    return res.mark("infra_failed")                  # cap hit: set aside, requeue once at end of batch
```

A candidate that exhausts memory or time *every* time is a model failure — without the reproduction rule a model could buy free attempts by emitting expensive code. A one-off kill that disappears on rerun is infrastructure. A task-seed still `infra_failed` after its end-of-batch requeue is dropped for **all** conditions to keep pairing, and the count is reported.

Model-server crashes and generation timeouts follow the same path. `worker_crash` also enters this loop: retire the worker, start a fresh one, retry at the same `attempt_idx`. A worker crash kills the in-flight candidate, not the batch. Runaway or repeated text is stopped by `max_new_tokens` and is `format_fail`.

**Run order.** Model-major (all 1.5B, then all 3B), but **interleave conditions within each model block**. Running conditions in contiguous blocks over several days lets thermal drift correlate with condition, which directly biases the energy comparison. Record `timestamp_utc` and `cpu_freq_mhz` per attempt.

---

## 2. Phase 5: logging

- **Every** attempt is appended to `logs/attempts.jsonl` and flushed (`fsync`) before the next attempt, rerun or feedback step — including failed, integrity-failed, format-failed and infrastructure-failed ones. Nothing is dropped.
- `model_secs` (generation) and `lean_secs` (all Lean work for that attempt) are always both recorded, plus tokens and energy.
- Prompts, raw model output, extracted code and Lean logs are stored by hash reference.
- Append-only; analysis never edits it. Every number in the paper regenerates from it with one command.
- On resume, drop a non-parsing final line (truncated by a crash) before appending.

## 3. Hand audit of successes

```
for each verified success:
    audit_selected = in seeded 10% sample per (condition x model), min 3 per cell where available
                     OR carries a pre-filter warning
```

- Question: does the code genuinely solve the task, or is it trivially true, hard-coded, or spec-copying?
- Reviewer sees task description, spec, buggy code, final code — **with the proof stripped**. Otherwise A and B candidates carry a proof and C's do not, which de-blinds the condition instantly.
- A success that fails the audit is reclassified `integrity_violation`, removed from the success count, kept in the log.
- 10% of a small success count is 3–5 cases per cell, which cannot estimate a cheating rate precisely. Put a second reviewer on an overlapping subset and report agreement, or state the limit plainly.

## 4. Cross-evaluation: B's code through C's pipeline

Offline, after the main run (`analysis/crosseval.py`). Replays logged candidates, so it costs only Lean time — no new generation.

**Why.** VERINA already reports that even strong models rarely write valid proofs, so "B fails" on its own repeats a known result. Cross-evaluation splits B's failures into *bad code* and *good code the model could not prove*. That split is the contribution.

**Procedure.** For every B attempt with `compile_ok = true` and `proof_ok = false`: splice the **implementation region only** into the locked file (B's output carries proof text, which C's pre-filter hard-rejects on contact), then run C's full pipeline — tactics **and** hidden tests **and** `#print axioms`. Tests are not optional: in `model_proof` mode the proof failed before tests ran, so B's code is of unknown behaviour.

**Three buckets:** C proves it and tests pass (B was bottlenecked by proof writing) · C proves it but tests fail (weak contract — a finding about VERINA) · C cannot prove it (B's code was genuinely unfit).

**Status: observational secondary analysis, not a condition.** B's code was written under a prompt that also demanded a proof, so it is not drawn from C's distribution. No causal claim. Pre-register it as secondary.

**Automation in B.** `grind`, `aesop` and friends stay legal in B — banning them makes the baseline a strawman, the automation/manual line is incoherent next to C's own `simp`/`omega`/`decide` tier, and a regex cannot enforce it (`by first | grind | aesop`, `<;> grind`, `macro_rules` aliases). Instead log `proof_tactic_used` and report what fraction of B's proofs are a single automation call. Pre-register both readings: B overall, and B excluding single-call-automation proofs.

## 5. Statistical power (before the Week 2 freeze)

`analysis/power.py`. McNemar power depends on the **discordant pair rates**, not on the difference of marginals. "Detect a 10% gap" is not a specifiable input; required N scales with `1 / (p01 + p10)`.

Estimate from the pilot: `p01` = P(B solves, C fails), `p10` = P(C solves, B fails). Then simulate — `statsmodels` has `contingency_tables.mcnemar` for the test but no closed-form power:

```python
import numpy as np
from statsmodels.stats.contingency_tables import mcnemar

def power(n_tasks, p01, p10, p_both, n_sim=10000, alpha=0.05):
    rng = np.random.default_rng(0)
    probs = [1 - p01 - p10 - p_both, p01, p10, p_both]
    hits = 0
    for _ in range(n_sim):
        c = rng.multinomial(n_tasks, probs)
        if mcnemar([[c[0], c[1]], [c[2], c[3]]], exact=True).pvalue < alpha:
            hits += 1
    return hits / n_sim
```

Three constraints:

- **Match the primary test's unit of analysis.** 3 seeds per task means the primary test is clustered (task-clustered permutation, or a GLMM with task as random effect). Simulate *that*, not plain McNemar. The unit must be written into `prereg/definitions.md` before the freeze.
- **Power applies to the main split only** — 70% after held-out. 80 tasks of power means harvesting ≈ 115.
- **20 pilot tasks give noisy `p01`/`p10`.** Report required N under pessimistic and optimistic assumptions, not a point estimate.

Output: the minimum task count, written into `params.yaml` before the freeze. If the pessimistic N is unreachable, say so at the go/no-go — an underpowered null result is not the "clean negative result" the plan relies on.

**Pre-register one primary test** (B versus C, main split) and label everything else exploratory: RQ4, the two models, and the per-bug-type and per-difficulty breakdowns are many comparisons. The held-out split at 18–30 tasks is a qualitative confirmation, not a test.

**Pre-register two analyses, both primary:** all tasks (intention-to-treat) and the T-feasible subset (tasks where the pipeline proves the reference). C cannot exceed the automation ceiling, so the T-infeasible tasks dilute the effect; choosing the subset after seeing results is the post-hoc subsetting the plan bans.

## 6. Energy accounting (Green AI)

Counting model calls alone is not a fair compute comparison, because C moves work from the GPU to CPU-heavy Lean automation. Equal N stays the primary budget; energy is a measured secondary outcome.

- Tool: `codecarbon` (default) or `pyJoules`. Wrap `generate()` and `verify()` with `tracker.start_task()` / `stop_task()` and store `gpu_energy_kwh`, `cpu_energy_kwh`, `co2_kg`, `energy_tool` and tool version.
- Offline tracker with a fixed country code, so CO2e is reproducible.
- **Attribution caveat:** RAPL is package-level and shared across two Lean workers, the model server and the OS, so per-attempt CPU energy is a wall-clock proportional estimate. Report **run-level totals as the headline**; label per-attempt values as estimates and do not put bootstrap CIs on them. Subtract the idle baseline measured at the start of each batch. For a clean sub-sample, re-measure a small set with `lean_workers = 1`.
- RAPL may not be readable without permissions; codecarbon then falls back to a TDP estimate. Record `energy_method`.
- Reported: kWh and CO2e per solved task, per condition and model. The conclusion is machine-specific — it depends on this box's GPU/CPU power ratio. State that.
