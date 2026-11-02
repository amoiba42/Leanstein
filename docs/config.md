# Shared configuration, limits and failure taxonomy

[← index](../ARCHITECTURE.md) · read by all three Parts

## 1. `prereg/params.yaml`

Every constant lives here and is read through `common/config.py`. Nothing is hard-coded elsewhere. Hashed at the Week 2 freeze; the hash goes into every attempt record.

```yaml
study:
  max_attempts_N: 5            # model-caused attempts per (task, condition, model, seed)
  seeds: [11, 22, 33]
  conditions: [A, B, C, C-plain]   # T is run separately on buggy and reference code
  held_out_fraction: 0.30

phase1_harvest:
  resample_cap_R: 5            # zero-shot resamples per task, new seed each time
  bug_source_models: [qwen2.5-coder-1.5b-instruct]   # default; 3B-sourced set optional
  min_tasks_before_mutation_fallback: 60
  keep_if: "compiles and fails at least one hidden test"

loop:
  infra_retry_cap: 3           # reruns per attempt, never consume N
  infra_backoff_secs: [5, 15, 45]
  gen_timeout_secs: 120
  task_wallclock_secs: 900     # per (task, condition, model, seed); see checks.md open issue 3b
  history_window: 1            # original buggy code + last candidate + its feedback
  lean_workers: 2              # persistent REPL workers, not one-shot processes
  gen_inflight: 1

sandbox:
  mem_limit_mb: 4096           # per worker; raised from 2048
  cmd_wall_secs: 40            # per command sent to a worker
  proc_wall_secs: 60           # OS-level backstop per worker process; >= 50
  candidate_verify_cap_secs: 120   # compile + light + heavy + tests
  host_guard_min_free_ram_mb: 2048 # pause the queue below this

worker:                        # persistent Lean worker (revision 3)
  impl: repl                   # leanprover-community/repl
  restart_every_n_candidates: 50
  restart_if_rss_mb_over: 3584
  warmup_timeout_secs: 180     # one import per worker lifetime
  imports: [Mathlib.Tactic.Omega, Mathlib.Tactic.Linarith, Mathlib.Tactic.NormNum,
            Mathlib.Tactic.Aesop, Mathlib.Tactic.Grind]   # never bare `import Mathlib`
  health_probe: "example : 1 + 1 = 2 := by decide"

tactics:
  light_per_tactic_secs: 2     # implemented as a calibrated heartbeat budget
  heavy_per_tactic_secs: 8
  light: [simp, simp_all, omega, decide, "unfold;simp", "unfold;omega", "split;simp_all"]
  heavy: [grind, aesop]
  complex_goals_enter_at: heavy
  coverage_check: "router must close >= the goals the full ladder closes on the 20 pilot references"

prompt:
  ctx_tokens: 4096
  prompt_budget_tokens: 3072
  max_new_tokens: 1024
  feedback_cap_tokens: 400     # same cap for B's Lean error and C's hint

prefilter:
  spec_copy_hard_jaccard: 0.80 # tuned on pilot only, then frozen
  spec_copy_warn_jaccard: 0.60
  short_body_warn_ratio: 0.30  # body tokens / buggy-code tokens

audit:
  fraction: 0.10
  seed: 4242
  min_per_cell: 3              # cell = condition x model, where available
  always_audit_warnings: true

energy:
  tool: codecarbon             # alternative: pyJoules
  measure_power_secs: 1
  country_iso_code: "SET_ME"   # needed for CO2e
```

**Load estimate.** 100 tasks × 4 conditions × 2 models × 3 seeds × N=5 = **12,000 attempts**. The revision 2 figure of 15 s mean verify (≈ 25 Lean wall-hours) assumed one-shot processes paying four imports per candidate; recompute from pilot timings once the persistent worker is running. Generation is the serial bottleneck (`gen_inflight = 1`). Early stopping lowers both. Trim to 60 tasks first if it does not fit.

---

## 2. `prereg/models.yaml`

"Shared" means every component, condition and phase uses the same registered weights and decoding. That is what makes conditions differ only by design.

```yaml
models:
  - id: qwen2.5-coder-1.5b-instruct
    hf_repo: Qwen/Qwen2.5-Coder-1.5B-Instruct
    gguf_file: <filename>        # fill in
    sha256: <hash>               # fill in, verified at server start
    quantization: Q4_K_M
    ctx_tokens: 4096
  - id: qwen2.5-coder-3b-instruct
    hf_repo: Qwen/Qwen2.5-Coder-3B-Instruct
    gguf_file: <filename>
    sha256: <hash>
    quantization: Q4_K_M
    ctx_tokens: 4096
  # optional, never pooled with primary results:
  # - qwen2.5-coder-7b-instruct (GPU server), one non-Qwen small model

decoding:                          # identical for harvesting and all conditions
  temperature: 0.4
  top_p: 0.95
  max_new_tokens: 1024
  seed_rule: "seed * 1000 + attempt_idx"   # deterministic per attempt
```

1. **One registry, one hash check.** The server refuses to start on a weights-hash mismatch. Hash and quantization are copied into the run header.
2. **Same model for Phase 1 and Phase 2.** Harvest and repair share weights and decoding. `bug_source_model` is recorded per task. Default: the 1.5B produces the shared bug set and every repair model repairs it, so comparisons stay paired. Report self-repair versus cross-repair separately if a 3B-sourced set is added.
3. **Serving.** One server process per model, one loaded at a time, model-major run order. `gen_inflight = 1`; the two Lean workers run in parallel with generation. Fits 6–8 GB VRAM and 16 GB RAM.
4. **Equal prompt budgets.** One skeleton for A, B, C, C-plain: ≤ 3,072 prompt tokens, ≤ 400 feedback tokens, 1,024 new tokens. The prompt-length table is the check.
5. **Determinism.** Same prompt and seed returns identical text. Checked in Week 1.
6. **Only generation uses a model.** Goal analyzer, hint extractor, pre-filter and feedback router are rule-based.

---

## 3. Master table of limits and timeouts

| Limit | Value | Where enforced | On breach |
|---|---|---|---|
| Model attempts per (task, condition, model, seed) | N = 5 | driver | `unresolved` (N_exhausted) |
| Harvest resamples per task | R = 5 | `harvest.py` | drop task, log reason |
| Infra reruns per attempt | 3 (backoff 5, 15, 45 s) | driver | `infra_failed`, requeue once, then drop task-seed for all conditions |
| Generation timeout | 120 s | model client | infrastructure, regenerate, no N consumed |
| Generation length | 1,024 new tokens | model server | stops; empty or cut output is `format_fail` (counts) |
| Prompt | 3,072 tokens of 4,096 context | `generate()` | oldest context trimmed first, never the feedback |
| Feedback length | 400 tokens (B and C equal) | router | truncate |
| Per-worker memory | 4 GB | sandbox (cgroup only) | `oom`: rerun once; reproduces ⇒ `resource_exhausted` (counts) |
| Per-command wall clock | 40 s | worker | `worker_crash`: fresh worker, same `attempt_idx`, no N |
| Per-worker process wall clock | 60 s, kill process group | sandbox | `proc_timeout`: same rule as `oom` |
| Worker restart | 50 candidates, or RSS > 3584 MB | sandbox | retire, re-import, health probe |
| Light tactic budget | 2 s each (≤ 14 s tier) | tactic file (heartbeats) | rung fails, next rung |
| Heavy tactic budget | 8 s each (≤ 16 s tier) | tactic file (heartbeats) | `proof_failed` |
| Per-candidate verify cap | 120 s | `verify()` | fail with last stage's outcome |
| Task wall clock | 900 s per (task, condition, model, seed) | driver | `unresolved` (wallclock_cap), same for all conditions |
| Concurrent Lean workers | 2 | scheduler | queue |
| Concurrent generations | 1 | scheduler | queue |
| Free RAM guard | 2 GB | scheduler | pause queue |
| Infra failure rate in the main run | ≤ 5% | C checks daily | stop and ask Member A |

---

## 4. Failure taxonomy

| failure_type | Cause | Consumes N | Rerun |
|---|---|---|---|
| none | verified end-to-end | n/a | n/a |
| integrity_fail | pre-filter hard flag, region diff, axiom scan | yes | no |
| format_fail | empty, truncated, or unparseable output | yes | no |
| compile_fail | Lean compile error | yes | no |
| proof_failed | no tactic closed the goal, or the model's proof is invalid | yes | no |
| test_failed | hidden tests fail (including reproducible test timeouts) | yes | no |
| resource_exhausted | OOM or timeout that reproduces on rerun | yes | no |
| infra_crash | OOM, process crash, server crash or timeout that does **not** reproduce | no | up to 3 times |
| worker_crash | Lean worker died or hit `cmd_wall_secs`; does **not** reproduce | no | fresh worker, same `attempt_idx`, up to 3 times |
| infra_failed | infra reruns exhausted | no | requeued once, then task-seed dropped for all conditions |

Outcome labels kept separate in the analysis: verified repair · behaviourally correct but unverified · verified but behaviourally wrong (weak contract) · integrity violation · unresolved.
