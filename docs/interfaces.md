# Interfaces and schemas

[← index](../ARCHITECTURE.md) · frozen in Week 1, signed off by all three

Only two objects and two calls cross between Parts.

## 1. Task manifest

JSON, one per task. Written by B, read by A and C.

```json
{
  "task_id": "verina_basic_017",
  "description": "natural-language statement shown to the model",
  "spec_lean": "specs/verina_basic_017.lean",
  "tests_path": "tests/verina_basic_017.json",
  "buggy_lean": "buggy/verina_basic_017.lean",
  "reference_lean": "ref/verina_basic_017.lean",
  "bug_type": "wrong_bound",
  "difficulty": "basic",
  "split": "pilot",
  "bug_source_model": "qwen2.5-coder-1.5b-instruct",
  "zero_shot_seed": 5003,
  "resample_idx": 2,
  "spec_theorem_elaborates": true,
  "hashes": {"spec": "sha256:...", "tests": "sha256:..."}
}
```

**Visibility.** The model sees `description`, the spec **statement**, and `buggy_lean`. It never sees the hidden tests, expected outputs, or `reference_lean`. The spec file is locked and hash-checked, but its statement must be visible: B has to prove it and C has to shape code to it.

## 2. Attempt record

JSONL, one line per attempt. Written by the driver.

```json
{
  "task_id": "verina_basic_017", "condition": "C", "model": "qwen2.5-coder-3b-instruct",
  "seed": 22, "attempt_idx": 2, "infra_retry_idx": 0,
  "prompt_hash": "sha256:...", "model_output": "ref:logs/out/....txt",
  "extracted_code": "ref:...", "extracted_proof": "",
  "prompt_truncated": false, "truncated_section": null,
  "prefilter_flags": {"hard": [], "warn": ["short_body"]},
  "compile_ok": true, "proof_ok": false, "closing_tactic": null,
  "proof_tactic_used": null, "single_call_automation": null,
  "route": "heavy", "tactic_trace": [["simp","fail"],["grind","timeout_budget"]],
  "tests_pass": null, "integrity_ok": true,
  "failure_type": "proof_failed",
  "feedback": "stuck-point hint text or generic message (empty for A)",
  "tokens_in": 1840, "tokens_out": 212,
  "model_secs": 4.7, "lean_secs": 18.3,
  "verify_stage_secs": {"compile": 3.1, "light": 14.0, "heavy": 1.2, "tests": 0.0},
  "worker_id": "w0", "worker_candidate_idx": 17, "hit_wall_clock": false,
  "cache_hit": false,
  "gpu_energy_kwh": 0.00012, "cpu_energy_kwh": 0.00031, "co2_kg": 0.00020,
  "energy_tool": "codecarbon", "energy_method": "rapl",
  "idle_baseline_id": "b3", "timestamp_utc": "2026-11-24T09:14:02Z", "cpu_freq_mhz": 2800,
  "audit_selected": false, "audit_result": null,
  "params_hash": "sha256:...",
  "verifier_git_sha": "...", "generate_git_sha": "...", "driver_git_sha": "..."
}
```

Field notes:

| Field | Why it exists |
|---|---|
| `proof_tactic_used`, `single_call_automation` | B may legally use `grind`/`aesop`; this measures how often, instead of banning it |
| `prompt_truncated`, `truncated_section` | B's history carries a proof, so B overflows more often — silent trimming would break "equal budgets" |
| `verify_stage_secs` | defends the energy split and the load estimate |
| `worker_id`, `worker_candidate_idx`, `hit_wall_clock` | worker attribution; wall-clock hits are never cached |
| `cache_hit` | duplicate candidates still consume N; at temperature 0.4, A will produce them |
| `*_git_sha` | `params_hash` covers config only. A mid-run bugfix in `sandbox.py` would otherwise be invisible and break "every number regenerates" |
| `idle_baseline_id`, `timestamp_utc`, `cpu_freq_mhz` | thermal drift correlates with run order and biases the energy comparison |

## 3. The two calls

```python
verify(task, code, proof=None, mode="tactics" | "model_proof") -> VerifyResult
# VerifyResult: compile_ok, proof_ok, closing_tactic, route, tactic_trace,
#               tests_pass, integrity flags, prefilter flags, failure_type,
#               hint object, lean_secs, verify_stage_secs, energy.
#               Deterministic and cached; infra_crash, worker_crash and
#               wall-clock-hit results are never cached.

generate(task, condition, history, seed) -> Candidate
# Candidate: code (and proof for A/B), model_secs, tokens, energy, proof_tactic_used.
# Applies the feedback router to the previous VerifyResult.
# Fixed decoding and frozen prompt template.
```

Both can be built against stubs in Week 1: `verify()` returns fixed dummy values including a `failure_type`, `generate()` returns canned text.
