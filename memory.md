# Project memory (fresh start: 2026-11-02)

Single source of truth for state between work sessions. Update it at the end of every session.
All previous run outputs (data/, results/, runs/, cache/) were deleted on 2026-11-02; everything is re-run from
scratch. The living proposal is `docs/final_proposal.md`; decisions and the diagram are in
`docs/final_architecture.md`.

## Decisions (agreed basis)

- Research question = the proposal's H1 (repair code so a fixed Lean automation portfolio proves it, instead of
  writing proofs). Framework = GPT verdict + Claude's B+P baseline and shaping-vs-reverting metric (mandatory) +
  Gemini's per-category reporting + Gracy's engineering notes (adopted/adapted, see final_architecture §2).
- Conditions: T, A, B, BP, C, C-plain, S, S-plain. Primary comparison C vs B and C vs BP (Holm), primary models.
- Bugs: natural (Qwen3.5-0.8B + 9B, zero-shot, never repairers) = primary if ≥60 confirmatory families, else
  natural ∪ mutant; mutants always reported separately.
- Repairers: Qwen3.5-2B, 4B (primary); Gemma-4-E4B (secondary); Goedel-Code-Prover-8B (A/B only).
- Lean 4.24.0 + Mathlib v4.24.0; own verification server `lean_env/PrlRepl.lean` (`lake build prlrepl`).
- Portfolio: Tier L (50k heartbeats) then Tier H (200k), frozen order, early stop, identical for all users.
- Energy: GPU measured (NVML counter) per (model, condition) block; CPU/CO2 estimated (study.yaml `energy`).
- Resources: 4 GB Job-Object cap per Lean worker; workers from free RAM; candidate timeouts count after one
  confirmation; infrastructure failures never charge the budget.

## Repository layout (coherent as of 2026-11-02)

`context/` (original inputs: InitialProposal PDFs, InitialVerdicts, GracyAdditions) · `docs/` (final_proposal,
final_architecture, requirements, HLD, LLD, implementation_plan, feasibility — all v2) · `prereg/` · `prl/` ·
`lean_env/` · `tests/` · `scripts/` · `README.md` · `memory.md`.

## Environment facts (verified)

- Windows 11, RTX 5060 8 GB, 24 GB RAM, i7-14650HX. Other projects (e.g. MechInterpGroupProject) also use
  GPU/RAM: **model experiments only when the GPU is idle and the user gives the go-ahead.**
- LM Studio engine: `llama.cpp-win-x86_64-nvidia-cuda12-avx2@2.67.0` (the CPU engine had been selected).
  Revert: `lms runtime select llama.cpp-win-x86_64-avx2@2.67.0`.
- Thinking must be off: `reasoning_effort: "none"`.
- Each Lean worker ≈ 1.8–2.7 GB RAM.
- GitHub is throttled per connection: `scripts/pdownload.py`.
- Shell tooling note: heredocs passed through the Bash tool can mangle `\n` escapes and apostrophes; write
  Python edit scripts to the scratchpad and run them instead.

## Harness lessons (fixed; covered by tests)

- `#print axioms` / `#eval` output has no `file:line` header → parse by declaration name / markers.
- Some VERINA functions have no `h_precond` argument → call shape from the locked header.
- `first | simp_all | …` does not fall through → `(simp_all; done)`.
- VERINA repeats `import` regions; models echo locked definitions (dropped at extraction).
- Mutants can loop forever → per-candidate checks with a short wall guard.
- Tests must not depend on generated data (load tasks from `third_party/verina`).

## Benchmark facts

- 189 tasks; only 46 ship a human proof. VERINA test defects: `verina_basic_67`, `verina_basic_80`.
  Evaluation limit: `verina_advanced_10`. Unsupported `Map` types: 2 tasks.

## Status

- [x] v2 design, docs, code, tests (79 unit + 24 Lean) — coherent; nothing run.
- [ ] User pushes to https://github.com/amoiba42/Leanstein.git (instructions given; Claude does not push).
- [ ] Phase 0 → dataset → pilot/gate → freeze → main → analysis (GPU steps need an idle GPU + go-ahead).
