# Project memory (fresh start: 2026-11-02; v2.1: 2026-11-03)

Single source of truth for state between work sessions. Update it at the end of every session.
All previous run outputs (data/, results/, runs/, cache/) were deleted on 2026-11-02; everything is re-run from
scratch. The living proposal is `docs/final_proposal.md`; decisions and the diagram are in
`docs/final_architecture.md`.

## Decisions (agreed basis)

- Research question = the proposal's H1 (repair code so a fixed Lean automation portfolio proves it, instead of
  writing proofs). Framework = GPT verdict + Claude's B+P baseline and shaping-vs-reverting metric (mandatory) +
  Gemini's per-category reporting + Gracy's engineering notes (adopted/adapted, see final_architecture §2).
- Conditions: T, A, B, BP, C, C-plain, S, S-plain, + exploratory Bhammer (optional, pilot-cost decision). Primary
  comparison C vs B and C vs BP (Holm), primary models. Secondary: B_noauto (B without single-call automation
  proofs, from `proof_tactic_used`), B→C cross-evaluation (`prl crosseval`).
- v2.1 (Gracy revision 3, branches `alternate` / `working` 48e9147): adopted cross-eval, proof-tactic logging, power
  simulation (`prl power`, required by `prl freeze`), Bhammer, RAM-aware workers, wall-guard rules; **declined** the
  reduced Mathlib imports (3 of 5 modules don't exist in v4.24). See final_architecture §2b.
- Bugs: natural (Qwen3.5-0.8B + 9B, zero-shot, never repairers) = primary if ≥60 `main`-split families (from the dataset), else
  natural ∪ mutant; mutants always reported separately.
- Repairers: Qwen3.5-2B, 4B (primary); Gemma-4-E4B (secondary); Goedel-Code-Prover-8B (A/B only).
- Lean 4.24.0 + Mathlib v4.24.0 (full `import Mathlib`, never a subset); own verification server
  `lean_env/PrlRepl.lean` (`lake build prlrepl`).
- Portfolio: Tier L (50k heartbeats) then Tier H (200k), frozen order, early stop, identical for all users.
- Energy: GPU measured (NVML counter) per (model, condition) block; CPU/CO2 estimated (study.yaml `energy`).
- Resources: 4 GB Job-Object cap per Lean worker; workers from free RAM; candidate timeouts count after one
  confirmation; infrastructure failures never charge the budget.

## Repository layout (coherent as of 2026-11-03)

`context/` (original inputs: InitialProposal PDFs, InitialVerdicts, GracyAdditions) · `docs/` (final_proposal,
final_architecture, requirements, HLD, LLD, implementation_plan, feasibility — all v2.1) · `prereg/` · `prl/` ·
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

- [x] v2 design, docs, code, tests on GitHub https://github.com/amoiba42/Leanstein. Claude never commits or pushes;
  the user does.
- [x] First freeze `964f1983` (laptop dataset, Ada pilot), 2026-11-05 16:05: **superseded**.
- [x] 2026-11-05: everything rerun from scratch on the IREL server (RTX PRO 6000 Blackwell, MIG 2g.48gb, GPU 1
  device 0). Dataset: coverage 22.3% and hidden tests identical to before; 51 natural instances, 33 of 114 main
  families. Probes; pilot 492 runs, 0 infrastructure failures; power note; gate passed. Harness change H-1:
  `copies_postcond` audit flag. **Second freeze `3f2744e1`, 21:06.** Record: `context/IREL_RUNS.md`; deviations
  R-1 to R-10 and H-1.
- [x] Study 2026-11-05 21:06 to 2026-11-06 11:49: 12,249 runs, 1 infrastructure failure, no cap hits, no stop
  rule. Cross-evaluation, analysis (`results/`, `results/heldout`), audit (333 runs, 0 spec-gaming; done by
  Claude, **human confirmation pending**). Post-freeze deviations D-1 (energy meter read physical GPU 0: no
  energy reported), D-2 (audit sampler bugs fixed), D-3 (audit by Claude).
- [x] Results: C > B for 2B and 4B (Holm p < 0.001), C vs BP +5.0 pp for 2B (p = 0.012) and a tie for 4B;
  held-out replicates C > B, with C/BP tied. Paper `paper/main.pdf` (8 pages) written.
- [ ] Human confirmation of the audit (`results/audit/sample.csv`); commit and push (user).

## Environment facts (study)

- IREL `inesh@10.4.25.56`, scripts in `scripts/irel/` (copy of `/scratch/inesh/irel_jobs`), repo at
  `/scratch/inesh/Leanstein`, llama.cpp `162e2bb`, Lean via `~/.elan` -> `/scratch/inesh/.elan`.
- `reserve_vram.py` holds idle memory on the slice (pinned, no compute) and releases it while `lms` loads a model.
