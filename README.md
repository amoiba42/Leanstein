# P.I.G. (Proof-Independent Generation): Automation for Structurally Verified Code Patches

AutoSE (CS6.403) group project, team

*Agents of Ultron* (Inesh Dheer, Poojitha J, Gracy Garg).

Small local models are poor at writing Lean proofs. We test whether they produce more *verified* repairs when
they only repair the **code**, shaping it so that a fixed, pre-registered portfolio of Lean automation (`simp`,
`omega`, `grind`, `aesop`, `decide`, induction templates) proves the unchanged specification, instead of writing
proofs themselves.

**Status: the study is complete.** Every step ran from
scratch on one machine: the IREL server, one 48 GB MIG slice of an NVIDIA RTX PRO 6000 Blackwell
That covers the dataset, probes, pilot (492 runs), power note, the **second freeze
(digest `3f2744e1`, 19 files)**, 12,249 study runs (1 infrastructure failure) and the analysis. **Result:** C
beats B for both primary models (Qwen3.5-2B 27.7% vs 2.2% of families, 4B 33.0% vs 17.6%; Holm p < 0.001). C
vs BP is +5.0 pp for 2B (p_Holm = 0.012) and a tie for 4B, and C uses about 43% fewer tokens per verified repair.
Held-out replicates C > B; C/BP ties there for both models. The first freeze (`964f1983`) is superseded
([`prereg/deviations.md`](prereg/deviations.md), R-1 to R-10). The post-freeze deviations are D-1 (in-run energy meter read the wrong GPU;
withdrawn), D-2 (audit sampler bugs), D-3 (automated pre-screen of the audit sample; human audit pending) and D-4 (energy
estimated by a post-hoc calibration on our slice: C 2.6 kJ per verified repair vs BP 5.9 and B 13.4 for 4B; the
whole study about 3.1 kWh).

**Start here:** [`docs/proposal.md`](docs/proposal.md) (final design) ·
[`docs/adr/`](docs/adr/README.md) (design decisions) ·
[`prereg/deviations.md`](prereg/deviations.md) (pre-freeze decisions and deviations) ·
[`scripts/irel/`](scripts/irel) (how the study was run).

| Document | Content |
|---|---|
| [`docs/proposal.md`](docs/proposal.md) | Final design: RQs, method, threats, repository map |
| [`docs/adr/`](docs/adr/README.md) | Architecture decision records (Nygard): each design decision with context and consequences |
| [`docs/requirements.md`](docs/requirements.md) | All requirements (v2) with reconciliation and adoption tables |
| [`docs/high_level_design.md`](docs/high_level_design.md) | Architecture, components, protocols, threat model |
| [`docs/low_level_design.md`](docs/low_level_design.md) | Module-level specification matching `prl/` |
| [`docs/implementation_plan.md`](docs/implementation_plan.md) | Features, phases, statuses |
| [`docs/feasibility.md`](docs/feasibility.md) | Phase-0 evidence from development; study probes are in `results/phase0_*.json` |
| [`prereg/`](prereg) | Frozen study inputs: config, portfolio, hints, prompts, deviation log |
| [`context/`](context) | Original proposal and project plan PDFs |

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

## Milestones (2026)

| Date | Milestone |
|---|---|
| 16 Oct | Proposal: Lean 4 as a CI gatekeeper |
| 26–29 Oct | Refined proposal and project plan |
| 2 Nov | Repository, design docs, harness and tests |
| 3 Nov | Review additions (cross-evaluation, Bhammer) |
| 4 Nov | Task exclusion list, probe data, first pilot |
| 5 Nov | Team decisions (ADRs); GPU rerun; freeze |
| 5–6 Nov | 12,249 study runs in 14.7 h; 1 infra failure, resumed |
| 6 Nov | Analysis, audit, paper draft, energy calibration |

## Setup (developed on Windows 11; the study ran on Linux with llama.cpp, see [`scripts/irel/`](scripts/irel/))

```bash
# 1. Lean 4.24.0 via elan; Mathlib v4.24.0 is pinned in lean_env/
cd lean_env && lake exe cache get && lake build prlrepl && cd ..
# 2. Benchmark (not committed): VERINA at the pinned commit
git clone https://github.com/sunblaze-ucb/verina.git third_party/verina
git -C third_party/verina checkout 66b3ce5014edafb20cb26b87c681e7f31847249f
# 3. Python
uv sync --extra dev
# 4. Models, GGUF 4-bit (SHA-256 in results/ada_model_hashes.txt): qwen3.5-0.8b, qwen3.5-2b, qwen3.5-4b,
#    qwen3.5-9b, gemma-4-e4b-it, goedel-code-prover-8b. Served by LM Studio on Windows, or on Linux by llama.cpp
#    162e2bb through the lms stand-in scripts/irel/bin/lms (scripts/irel/setup_*.sh)
uv run prl env
```

[`lean_env/PrlRepl.lean`](lean_env/PrlRepl.lean) is our verification server: it imports Mathlib once per worker and elaborates each
candidate against a fresh copy of that environment (~0.6 s per check instead of ~30 s). `PRL_LEAN_BACKEND=cli`
uses plain `lean` instead (verdict parity is checked).

## Pipeline (as run on IREL; everything up to and including `prl freeze` is done)

Steps already run and committed are marked `[done]`. The dataset steps must **not** be re-run: their output is
committed, and re-running changes the natural bugs and would break the freeze. On IREL, `--lean-workers 6` goes
before the subcommand (`prl --lean-workers 6 run ...`) and study jobs use `--run-workers 12`.

```bash
uv run prl tasks build                         # [done] parse the 189 VERINA tasks
uv run prl tasks check --tests visible         # [done] reference checks + condition T: basic 35.6%, advanced 5.0%, overall 22.3%
uv run prl hidden                              # [done] hidden tests (precondition proved in Lean)
uv run prl probe compile --models qwen3.5-2b,qwen3.5-4b   # [done] floor-effect probe: compile 10% (2B), 40% (4B)
uv run prl probe determinism --models qwen3.5-2b,qwen3.5-4b   # [done] same seed identical, different seed differs
uv run prl bugs natural                        # [done] 51 instances, 33 of 114 main families: below 60, so the natural+mutant fallback applies
uv run prl bugs mutants                        # [done] controlled mutants
uv run prl bugs shaping                        # [done] study-S instances
uv run prl splits                              # [done] pilot 20 / main 114 / held-out 50
# pilot (primary models, 1 seed; Bhammer included so its cost can be estimated)
uv run prl run --study pilot --split pilot --allow-unfrozen --seeds 11 --conditions A,B,BP,Bhammer,C,Cplain   # [done] 492 runs
uv run prl power --study pilot                 # [done] -> prereg/power_note.json (required by freeze)
uv run prl freeze                              # [done] digest 3f2744e1, 19 files (second freeze)
# confirmatory study `main` (refuses if prereg/ changed)
uv run prl run --study main --split main                                   # primary x A,B,BP,C,Cplain x 3 seeds
uv run prl run --study main-gemma --split main --models gemma-4-e4b-it --conditions B,BP,C --seeds 11
uv run prl run --study main-goedel --split main --models goedel-code-prover-8b --conditions A,B --seeds 11
uv run prl run --study main-bhammer --split main --conditions Bhammer   # exploratory; after held-out (team decision 5, R-8)
uv run prl run --study main-shaping --split main --kinds shaping --conditions S,Splain
# held-out replication, run once
uv run prl run --study heldout --split heldout --conditions B,BP,C
# analysis
uv run prl crosseval --study main,main-gemma,heldout   # B->C cross-evaluation (Lean only, no model)
uv run prl analyze --study main,main-shaping,main-gemma,main-goedel,main-bhammer   # confirmatory + secondary tables into results/
uv run prl analyze --study heldout --out results/heldout   # replication, never pooled with main
uv run prl audit --study main                  # 10% + flagged successes -> results/audit/sample.csv
uv run prl audit --merge                       # after filling the CSV
```

## Tests

```bash
uv run pytest -m "not lean and not llm"   # 96 unit tests (fast)
uv run pytest -m lean                     # 24 integration tests on real Lean: zero false successes
uv run ruff check prl tests
```

## Layout

[`prl/tasks`](prl/tasks/) VERINA parsing, regions, eligibility, splits · [`prl/lean`](prl/lean/) verification (server pool, builder, two-tier
portfolio, integrity, hints, verify) · [`prl/testgen`](prl/testgen/) literals and hidden tests · [`prl/mutate`](prl/mutate/) mutation operators ·
[`prl/natural`](prl/natural/) natural bugs and shaping instances · [`prl/models`](prl/models/) OpenAI-compatible (LM Studio / llama.cpp) client, prompts, extraction, registry ·
[`prl/conditions`](prl/conditions/) protocols, feedback router, probes · [`prl/driver`](prl/driver/) resumable runner with energy blocks ·
[`prl/energy.py`](prl/energy.py) energy meter · [`prl/analysis`](prl/analysis/) statistics, power simulation, B→C cross-evaluation, mechanism, code
shapes, reports · [`prl/cli.py`](prl/cli.py) entry point.
Generated outputs [`data/`](data/), [`runs/`](runs/) (except raw prompts/outputs) and [`results/`](results/) are created by the pipeline and committed as research artifacts; `cache/`, `runs/*/raw/`, [`third_party/`](third_party/) and `lean_env/.lake/` are git-ignored.
