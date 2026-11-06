# Phase-0 Feasibility

Phase 0 results live in [`results/`](../results/); this file records the environment and static facts they rest on.

## 1. Environment (verified while building the harness)

| Item | Value |
|---|---|
| Lean / Mathlib | `v4.24.0` / `v4.24.0` (commit `f897ebcf`), prebuilt cache |
| Benchmark | VERINA `66b3ce50` (189 tasks: 108 basic, 81 advanced) |
| Lean backend | own verification server [`lean_env/PrlRepl.lean`](../lean_env/PrlRepl.lean) (Mathlib imported once per worker; ~0.6 s per check vs 25–40 s for a plain `lean` process) |
| Inference | Development: LM Studio 0.4.x with the CUDA 12 llama.cpp engine 2.67.0. Study: llama.cpp `162e2bb` on an RTX PRO 6000 Blackwell MIG slice (see [`scripts/irel/README.md`](../scripts/irel/README.md)) |
| Reasoning | disabled with `reasoning_effort: "none"`; otherwise hidden reasoning silently consumes the token budget |
| Shared machine | other projects use the same GPU/RAM; model runs only on an idle GPU; Lean workers from free RAM, 4 GB cap each |

## 2. Static facts about the benchmark (properties of VERINA, not results)

- Only 46/189 tasks ship a human reference proof; 143 have `sorry`. Eligibility therefore requires
  compile + passing tests, not a proof.
- Some functions take no `h_precond` argument; some templates repeat the `import` region.
- Two VERINA test cases contradict their task descriptions: `verina_basic_67` (expects `['a','b','c']` to be a
  palindrome) and `verina_basic_80` (expects `true` for a key occurring twice; the spec says "exactly once").
- `verina_advanced_10` uses inputs too large to evaluate within Lean's recursion limits; two tasks use `Map` types.

## 3. Condition T on references (Gate 1: ≥20% screening)

The portfolio alone proves 22.3% of eligible references (basic 35.6%, advanced 5.0%); full table in [`results/t_coverage.md`](../results/t_coverage.md).

## 4. Hidden tests

Coverage per family is in the dataset manifests ([`data/hidden/`](../data/hidden/)).

## 5. Compile-rate probe (floor effect) and determinism

Compile rate on the probe sample (n = 20 generations each): 10% (Qwen3.5-2B), 40% (Qwen3.5-4B), in [`results/phase0_compile_probe.json`](../results/phase0_compile_probe.json). Same seed gives identical output and a different seed differs ([`results/phase0_determinism.json`](../results/phase0_determinism.json)).

## 5b. Pilot power note (SR-STAT-4)

[`prereg/power_note.json`](../prereg/power_note.json) (written by `prl power` before the freeze). The gate evaluation is recorded in [`prereg/deviations.md`](../prereg/deviations.md).

## 6. Integrity

The real-Lean integrity suite (`uv run pytest -m lean`) passes: 24/24, zero false successes
(this is a test of the harness, not a study result).
