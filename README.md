# Leanstein — Prove Less, Repair Better

**Automation-friendly program repair for small models in Lean 4** — AutoSE (CS6.403) group project, team
*Agents of Ultron* (Inesh Dheer, Poojitha J, Gracy Garg).

Small local models are poor at writing Lean proofs. We test whether they produce more *verified* repairs when
they only repair the **code**, shaping it so that a fixed, pre-registered portfolio of Lean automation (`simp`,
`omega`, `grind`, `aesop`, `decide`, induction templates) proves the unchanged specification, instead of writing
proofs themselves.

**Start here:** [`docs/final_proposal.md`](docs/final_proposal.md) (living document) ·
[`docs/final_architecture.md`](docs/final_architecture.md) (decisions + diagram) · [`memory.md`](memory.md) (state).

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

Success = compiles ∧ locked theorem proved by the allowed source ∧ axioms ⊆ {propext, Classical.choice,
Quot.sound} ∧ static integrity ∧ visible **and hidden** tests pass.

## Setup (Windows 11, tested)

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

## Pipeline (nothing has been run yet; GPU steps only on an otherwise idle GPU)

```bash
uv run prl tasks build                         # parse the 189 VERINA tasks
uv run prl tasks check --tests visible         # reference checks + condition T (coverage)
uv run prl hidden                              # hidden tests (precondition proved in Lean)
uv run prl probe compile --models qwen3.5-2b,qwen3.5-4b   # GPU: floor-effect probe
uv run prl probe determinism --models qwen3.5-2b,qwen3.5-4b
uv run prl bugs natural                        # GPU: natural bugs from Qwen3.5-0.8B and 9B
uv run prl bugs mutants                        # controlled mutants
uv run prl bugs shaping                        # study-S instances
uv run prl splits                              # pilot / main / held-out
uv run prl run --study pilot --split pilot --allow-unfrozen --seeds 11
uv run prl freeze                              # pre-registration hashes
uv run prl run --study main --split main       # confirmatory (refuses if prereg/ changed)
uv run prl run --study main-shaping --split main --kinds shaping --conditions S,Splain
uv run prl analyze --study main,main-shaping   # every table and figure into results/
uv run prl audit --study main                  # 10% + flagged successes -> results/audit/sample.csv
uv run prl audit --merge                       # after filling the CSV
```

## Tests

```bash
uv run pytest -m "not lean and not llm"   # 79 unit tests (fast)
uv run pytest -m lean                     # 24 integration tests on real Lean: zero false successes
uv run ruff check prl tests
```

## Layout

`prl/tasks` VERINA parsing, regions, eligibility, splits · `prl/lean` verification (server pool, builder, two-tier
portfolio, integrity, hints, verify) · `prl/testgen` literals and hidden tests · `prl/mutate` mutation operators ·
`prl/natural` natural bugs and shaping instances · `prl/models` LM Studio client, prompts, extraction, registry ·
`prl/conditions` protocols, feedback router, probes · `prl/driver` resumable runner with energy blocks ·
`prl/energy.py` energy meter · `prl/analysis` statistics, mechanism, code shapes, reports · `prl/cli.py` entry point.
Generated outputs `data/`, `runs/` (except raw prompts/outputs) and `results/` are created by the pipeline and committed as research artifacts; `cache/`, `runs/*/raw/`, `third_party/` and `lean_env/.lake/` are git-ignored.
