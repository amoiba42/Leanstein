# Leanstein — Prove Less, Repair Better

**Automation-friendly program repair for small models in Lean 4** — AutoSE (CS6.403) group project, team
*Agents of Ultron* (Inesh Dheer, Poojitha J, Gracy Garg).

Small local models are poor at writing Lean proofs. We test whether they produce more *verified* repairs when
they only repair the **code**, shaping it so that a fixed, pre-registered portfolio of Lean automation (`simp`,
`omega`, `grind`, `aesop`, `decide`, induction templates) proves the unchanged specification, instead of writing
proofs themselves.

**Status (2026-11-05): pre-registration frozen, digest `964f1983`, 19 files. The main study has not been run.**
Phase 0, the pilot (504 runs, 0 infrastructure failures) and the power note are done and committed. All seven
pre-freeze team decisions are settled. Nothing under `prereg/` changes from here except `deviations.md`, which is
the log and is not hashed. A `prl run` on split `main` or `heldout` re-hashes `prereg/` and exits 2 on any mismatch.

**Start here:** [`docs/final_proposal.md`](docs/final_proposal.md) (living document) ·
[`docs/final_architecture.md`](docs/final_architecture.md) (decisions + diagram) · [`memory.md`](memory.md) (state) ·
[`context/TEAM_DECISIONS.md`](context/TEAM_DECISIONS.md) (the seven decisions, ADR-001 to ADR-007) ·
[`context/RUN_HANDOFF.md`](context/RUN_HANDOFF.md) (how to run the study on Ada).

| Document | Content |
|---|---|
| [`docs/final_proposal.md`](docs/final_proposal.md) | The proposal to follow: RQs, method, how every input was used, repo map, status |
| [`docs/final_architecture.md`](docs/final_architecture.md) | Proposal vs verdicts vs Gracy's additions; final conditions/models; architecture diagram |
| [`docs/requirements.md`](docs/requirements.md) | All requirements (v2) with reconciliation and adoption tables |
| [`docs/high_level_design.md`](docs/high_level_design.md) | Architecture, components, protocols, threat model |
| [`docs/low_level_design.md`](docs/low_level_design.md) | Module-level specification matching `prl/` |
| [`docs/implementation_plan.md`](docs/implementation_plan.md) | Features, phases, statuses |
| [`docs/feasibility.md`](docs/feasibility.md) | Phase-0 evidence (pending re-run) |
| [`prereg/`](prereg) | Frozen study inputs: config, portfolio, hints, prompts, deviation log |
| [`context/`](context) | Original inputs: proposal + plan PDFs, the three verdicts, Gracy's additions |

## Conditions

| ID | Model writes | Proof from | Purpose |
|---|---|---|---|
| T | — | portfolio | automation coverage on reference and buggy code |
| A | code + proof | model | independent samples (pass@N) |
| B | code + proof | model | feedback-guided proof writing |
| BP | code + proof | portfolio first, else model | isolates "don't write proofs" |
| **C** | **code only** | **portfolio** | **proposed method** (failing test + unsolved goal + structural hint) |
| Cplain | code only | portfolio | ablation: plain retry feedback |
| S / Splain | code only, from a *correct* but unprovable reference | portfolio | mechanism: can a model re-shape code for provability? |
| Bhammer *(exploratory, optional)* | code + proof; prompt lists the frozen portfolio | model | is knowing the tactics enough? |

Secondary analyses without extra model calls: **B_noauto** (B with single-call automation proofs counted as
failures, from the logged `proof_tactic_used`) and the **B→C cross-evaluation** (B's code that compiled but was not
proved, re-checked by C's pipeline).

Success = compiles ∧ locked theorem proved by the allowed source ∧ axioms ⊆ {propext, Classical.choice,
Quot.sound} ∧ static integrity ∧ visible **and hidden** tests pass.

## Setup (Windows 11, tested; the study itself runs on Ada, Linux + llama.cpp)

```bash
# 1. Lean 4.24.0 via elan; Mathlib v4.24.0 is pinned in lean_env/
#    (on throttled networks, scripts/pdownload.py downloads large GitHub assets in parallel)
cd lean_env && lake exe cache get && lake build prlrepl && cd ..
# 2. Benchmark (not committed): VERINA at the pinned commit
git clone https://github.com/sunblaze-ucb/verina.git third_party/verina
git -C third_party/verina checkout 66b3ce5014edafb20cb26b87c681e7f31847249f
# 3. Python
uv sync --extra dev
# 4. Models in LM Studio (GGUF 4-bit, CUDA engine): qwen3.5-0.8b, qwen3.5-2b, qwen3.5-4b, qwen3.5-9b,
#    gemma-4-e4b-it, goedel-code-prover-8b
uv run prl env
```

`lean_env/PrlRepl.lean` is our verification server: it imports Mathlib once per worker and elaborates each
candidate against a fresh copy of that environment (~0.6 s per check instead of ~30 s). `PRL_LEAN_BACKEND=cli`
uses plain `lean` instead (verdict parity is checked).

## Pipeline (everything up to and including `prl freeze` is done; GPU steps only on an otherwise idle GPU)

Steps already run and committed are marked `[done]`. The dataset steps must **not** be re-run: their output is
committed, and re-running changes the natural bugs and would break the freeze.

```bash
uv run prl tasks build                         # [done] parse the 189 VERINA tasks
uv run prl tasks check --tests visible         # [done] reference checks + condition T: basic 35.6%, advanced 5.0%, overall 22.3%
uv run prl hidden                              # [done] hidden tests (precondition proved in Lean)
uv run prl probe compile --models qwen3.5-2b,qwen3.5-4b   # GPU: floor-effect probe
uv run prl probe determinism --models qwen3.5-2b,qwen3.5-4b
uv run prl bugs natural                        # [done] 56 instances, 32 of 114 main families: below 60, so the natural+mutant fallback applies
uv run prl bugs mutants                        # [done] controlled mutants
uv run prl bugs shaping                        # [done] study-S instances
uv run prl splits                              # [done] pilot 20 / main 114 / held-out 50
# pilot (primary models, 1 seed; Bhammer included so its cost can be estimated)
uv run prl run --study pilot --split pilot --allow-unfrozen --seeds 11 --conditions A,B,BP,Bhammer,C,Cplain
uv run prl power --study pilot                 # [done] -> prereg/power_note.json (required by freeze)
uv run prl freeze                              # [done 2026-11-05] digest 964f1983, 19 files
# confirmatory study `main` (refuses if prereg/ changed)
uv run prl run --study main --split main                                   # primary x A,B,BP,C,Cplain x 3 seeds
uv run prl run --study main --split main --models gemma-4-e4b-it --conditions B,BP,C --seeds 11
uv run prl run --study main --split main --models goedel-code-prover-8b --conditions A,B --seeds 11
uv run prl run --study main --split main --conditions Bhammer           # exploratory; ADR-005 commits to running it last
uv run prl run --study main-shaping --split main --kinds shaping --conditions S,Splain
# held-out replication, run once
uv run prl run --study heldout --split heldout --conditions B,BP,C
# analysis
uv run prl crosseval --study main,heldout      # B->C cross-evaluation (Lean only, no model)
uv run prl analyze --study main,main-shaping   # confirmatory + secondary tables into results/
uv run prl analyze --study heldout --out results/heldout   # replication, never pooled with main
uv run prl audit --study main                  # 10% + flagged successes -> results/audit/sample.csv
uv run prl audit --merge                       # after filling the CSV
```

## Tests

```bash
uv run pytest -m "not lean and not llm"   # 95 unit tests (fast)
uv run pytest -m lean                     # 24 integration tests on real Lean: zero false successes
uv run ruff check prl tests
```

## Layout

`prl/tasks` VERINA parsing, regions, eligibility, splits · `prl/lean` verification (server pool, builder, two-tier
portfolio, integrity, hints, verify) · `prl/testgen` literals and hidden tests · `prl/mutate` mutation operators ·
`prl/natural` natural bugs and shaping instances · `prl/models` LM Studio client, prompts, extraction, registry ·
`prl/conditions` protocols, feedback router, probes · `prl/driver` resumable runner with energy blocks ·
`prl/energy.py` energy meter · `prl/analysis` statistics, power simulation, B→C cross-evaluation, mechanism, code
shapes, reports · `prl/cli.py` entry point.
Generated outputs `data/`, `runs/` (except raw prompts/outputs) and `results/` are created by the pipeline and committed as research artifacts; `cache/`, `runs/*/raw/`, `third_party/` and `lean_env/.lake/` are git-ignored.
