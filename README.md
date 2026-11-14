# P.I.G. (Proof-Independent Generation): Automation for Structurally Verified Code Patches

[![verify](https://github.com/amoiba42/Leanstein/actions/workflows/ci.yml/badge.svg)](https://github.com/amoiba42/Leanstein/actions/workflows/ci.yml)

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
whole study about 3.1 kWh). D-5 discloses five families without hidden tests, D-6 the post-review maintenance and
D-7 the post-study re-verification of every logged success (all 1,858 re-verify, [`results/reverify/summary.md`](results/reverify/summary.md)) and the exploratory tables below.

**Paper:** [`paper/main.pdf`](paper/main.pdf) (source in [`paper/`](paper), numbers from [`results/`](results)) ·
mid-submission report: [`report/progress_report.pdf`](report/progress_report.pdf).

## C against BP

C beats B clearly. Against BP (B with the same portfolio tried first), C is ahead for Qwen3.5-2B (+5.0 pp,
p_Holm = 0.012) and **tied for Qwen3.5-4B** (33.0% vs 32.7%, p_Holm = 0.50); on held-out the two tie for both
models. The tie is the result, and it should be read with these facts beside it:

- **Power.** The pre-freeze simulation gave C vs BP a power of **0.08** for 4B at the 106 available families
  ([`results/power_note.md`](results/power_note.md)). A tie means "no large difference", not "equal".
- **BP's successes are the portfolio's.** 180 of BP's 182 verified runs for 4B, and all 110 for 2B, were closed by
  the portfolio, not by the model's proof. The proof-writing half of BP added 2 repairs in 693 runs.
- **Cost.** For the same success rate, C uses **37k model tokens per verified repair against BP's 65k (43% fewer)**
  and 68 s of inference per run against 162 s with 4B (2B: 50k against 89k), because the model never writes a
  proof ([`results/rq5_costs.md`](results/rq5_costs.md)).
- **Integrity.** BP's submissions are rejected by the static checks 3.4 times as often as C's (5,764 against 1,690
  attempts); proof text is where most malformed submissions come from.

## Robustness (exploratory, not pre-registered)

| Subset (C vs B / C vs BP, family-level) | Qwen3.5-2B | Qwen3.5-4B | Gemma-4-E4B |
|---|---|---|---|
| Primary pool, 106 families (confirmatory) | +25.5 / +5.0 pp | +15.4 / +0.3 pp | +28.3 / +2.8 pp |
| Reference **not** provable by the portfolio, 85 families (no success can be a plain revert) | +10.6 / +4.3 pp | +7.8 / +1.2 pp | +15.3 / +7.1 pp |
| Natural bugs only, 33 families | +14.1 / +7.1 pp | +18.2 / +5.1 pp | +18.2 / +9.1 pp |
| Mutants only, 105 families | +24.8 / +5.1 pp | +14.6 / -0.3 pp | +26.7 / +1.0 pp |

C beats B in every subset (one-sided p <= 0.031). Sources: [`results/exploratory_shaping.md`](results/exploratory_shaping.md)
(`scripts/exploratory_shaping.py`) and [`results/rq1_main.md`](results/rq1_main.md). Fifteen real before/after
cases (bug, reference, C's verified code, closing tactic, what B did) are in
[`docs/code_shapes.md`](docs/code_shapes.md) (`scripts/code_shapes_catalogue.py`).

**Limitations.** One benchmark of small functions, two sizes of one primary model family plus Gemma as a second
family, 4-bit weights only; natural bugs cover only 33 families; C vs BP is underpowered; energy is a post-hoc
estimate (lead with tokens); the audit is an automated pre-screen until the human pass is done. Details: paper,
section "Limitations".

**Start here:** [`docs/architecture.md`](docs/architecture.md) (how and why it was designed: drivers, architecture views, decisions with alternatives, design evolution, lessons) ·
[`docs/proposal.md`](docs/proposal.md) (final design) ·
[`docs/adr/`](docs/adr/README.md) (design decisions) ·
[`prereg/deviations.md`](prereg/deviations.md) (pre-freeze decisions and deviations) ·
[`scripts/irel/`](scripts/irel) (how the study was run).

| Document | Content |
|---|---|
| [`docs/architecture.md`](docs/architecture.md) | **Design and architecture:** quality drivers and scenarios, C4 context/container/component views, runtime and data-lineage views, deployment as designed vs as built, decisions with alternatives and trade-offs, patterns, design evolution, lessons, traceability |
| [`docs/proposal.md`](docs/proposal.md) | Final design: RQs, method, threats, repository map |
| [`docs/adr/`](docs/adr/README.md) | Architecture decision records (Nygard): each design decision with context and consequences |
| [`docs/requirements.md`](docs/requirements.md) | All requirements (v2) with reconciliation and adoption tables |
| [`docs/code_shapes.md`](docs/code_shapes.md) | 15 real before/after code-shape cases from the study logs |
| [`docs/requirements_check.md`](docs/requirements_check.md) | Check of the delivered project against the requirements and NFRs, with a verification log |
| [`docs/high_level_design.md`](docs/high_level_design.md) | Architecture, components, protocols, threat model |
| [`docs/low_level_design.md`](docs/low_level_design.md) | Module-level specification matching `prl/` |
| [`docs/implementation_plan.md`](docs/implementation_plan.md) | Features, phases, statuses |
| [`docs/feasibility.md`](docs/feasibility.md) | Phase-0 evidence from development; study probes are in `results/phase0_*.json` |
| [`prereg/`](prereg) | Frozen study inputs: config, portfolio, hints, prompts, deviation log |

## Verify this project

Nothing here needs a GPU or a model. The quickest check needs no installation at all: open the
[Actions tab](https://github.com/amoiba42/Leanstein/actions/workflows/ci.yml). On every push a clean machine
runs checks 1 to 4 below, and the badge at the top of this page shows the latest result.

To run the checks yourself (Linux, macOS or WSL; about 2 minutes without Lean):

```bash
git clone https://github.com/amoiba42/Leanstein.git && cd Leanstein
bash scripts/setup.sh --no-lean    # Python env from uv.lock, VERINA at the pinned commit, checks 1 and 3
uv run ruff check prl tests        # check 2
# check 4: regenerate every table from the committed logs
uv run prl analyze --study main,main-shaping,main-gemma,main-goedel,main-bhammer
uv run prl analyze --study heldout --out results/heldout
uv run prl analyze --study pilot --out results/pilot
git status --short results         # prints nothing: the regenerated files equal the committed ones
# check 5 (optional; downloads about 5 GB of Lean and Mathlib)
bash scripts/setup.sh
uv run pytest -m lean
```

| # | Check | What it shows | Expected |
|---|---|---|---|
| 1 | Pre-registration freeze | No frozen input (config, prompts, portfolio, hints) changed after the freeze | `pre-registration freeze: OK 3f2744e132b37783 []` |
| 2 | Static checks | NFR-QA-2 | `All checks passed!` |
| 3 | Unit tests | Parsing, integrity, protocols, statistics; a modified `prereg/` file is refused; a hung Lean process is killed | `103 passed` |
| 4 | Regeneration | Every number in [`results/`](results/) follows from the logs in [`runs/`](runs/) (NFR-REP-1) | no difference |
| 5 | Lean integration tests | The verifier accepts no false success (`sorry`, extra axioms, edited specification, ...) | `24 passed` |

Requirement-by-requirement status, with the open items, is in
[`docs/requirements_check.md`](docs/requirements_check.md). Changes made after the freeze are listed in
[`prereg/deviations.md`](prereg/deviations.md) (D-1 to D-7). On Windows, clone inside WSL; a checkout that converts
line endings would change the bytes that the freeze hashes (the committed `.gitattributes` prevents this).

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

On Linux, macOS or WSL, `bash scripts/setup.sh` performs steps 1 to 3 below and runs the checks
(`--no-lean` skips step 1). The individual steps:

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
uv run pytest -m "not lean and not llm"   # 103 unit tests (fast)
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
Generated outputs [`data/`](data/), [`runs/`](runs/) (except raw prompts/outputs) and [`results/`](results/) are created by the pipeline and committed as research artifacts; `cache/`, `runs/*/raw/`, `third_party/` and `lean_env/.lake/` are git-ignored.
