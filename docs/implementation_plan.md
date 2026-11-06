# Implementation Plan

**Project:** P.I.G. (Proof-Independent Generation): Automation for Structurally Verified Code Patches (package `prl`)
**Related:** [`docs/requirements.md`](requirements.md), [`docs/high_level_design.md`](high_level_design.md), [`docs/low_level_design.md`](low_level_design.md), [`docs/adr/`](adr/).
**State:** all code is implemented and tested, and every phase below has been run from scratch on the study GPU server
(see [`scripts/irel/README.md`](../scripts/irel/README.md); deviations in [`prereg/deviations.md`](../prereg/deviations.md)).

Legend: ☐ todo · ◐ in progress · ☑ done · ⊘ dropped (with reason). Owner roles: A = Verification Engine,
B = Tasks & Models, C = Study Lead.

---

## Phase 0 — Environment and feasibility

| ID | Feature | Owner | Satisfies | Acceptance | Status |
|---|---|---|---|---|---|
| F-00 | Pinned Lean 4.24.0 + Mathlib v4.24.0 workspace ([`lean_env/`](../lean_env/)), manifest committed | A | NFR-ENV-2 | `import Mathlib` compiles | ☑ |
| F-01 | VERINA checkout at commit `66b3ce50` ([`third_party/verina`](../third_party/verina/), not committed) | B | FR-TASK-1 | commit recorded | ☑ |
| F-02 | Python env with lockfile (`uv`) | C | NFR-ENV-2 | `uv run pytest` runs | ☑ |
| F-03 | LM Studio models + CUDA engine; `reasoning_effort: none` | B | NFR-ENV-2 | `lms ls` | ☑ |
| F-04 | Verification server `PrlRepl` + CLI parity | A | FR-RES-2 | parity check | ☑ |
| F-05 | T on all references | A | NFR-FEAS-1, SR-SEL-1 | [`results/t_coverage.md`](../results/t_coverage.md) | ☑ |
| F-06 | Compile-rate probe (10 tasks × models) | B | NFR-FEAS-2 | [`results/phase0_compile_probe.json`](../results/phase0_compile_probe.json) | ☑ |
| F-07 | Determinism probe + throughput | B | FR-GEN-5 | [`results/phase0_determinism.json`](../results/phase0_determinism.json) | ☑ |
| F-08 | Model registry with GGUF SHA-256 | B | NFR-ENV-2 | `results/model_registry.json` | ☑ |

## Phase 1 — Components (all implemented)

| ID | Feature | Module | Satisfies | Test | Status |
|---|---|---|---|---|---|
| F-10 | Config, hashing, Lean env | [`prl/config.py`](../prl/config.py) | — | unit | ☑ |
| F-11 | VERINA regions, render, locked hash | [`prl/tasks/regions.py`](../prl/tasks/regions.py) | FR-TASK-1, IR-1 | round-trip on 189 templates | ☑ |
| F-12 | Family loader (repeated imports, functions without `h_precond`) | [`prl/tasks/verina.py`](../prl/tasks/verina.py) | FR-TASK-1 | 189 load | ☑ |
| F-13 | Type parser, literals, random values | [`prl/testgen/literals.py`](../prl/testgen/literals.py) | FR-TEST | unit | ☑ |
| F-20 | Lean runner: server pool (full Mathlib), Job-Object memory cap, workers from config / free RAM / `PRL_LEAN_WORKERS`, CLI fallback | [`prl/lean/runner.py`](../prl/lean/runner.py) | FR-RES-1/2 | integration | ☑ |
| F-21 | File builder (per-entry heartbeats, conditional precondition argument, eval markers) | [`prl/lean/builder.py`](../prl/lean/builder.py) | FR-VER-2 | integration | ☑ |
| F-22 | Two-tier portfolio (positive heartbeats enforced) + single-call automation registry | [`prl/lean/portfolio.py`](../prl/lean/portfolio.py), [`prereg/portfolio.yaml`](../prereg/portfolio.yaml) | FR-PORT-1..5, FR-ANA-8 | unit (tier order, unbounded rejected) | ☑ |
| F-23 | Static pre-filter (reject) + degeneracy flags | [`prl/lean/integrity.py`](../prl/lean/integrity.py) | IR-1..7 | unit | ☑ |
| F-25 | Staged verify, early stop, failure taxonomy, cache, wall guard ≥ 50 s | [`prl/lean/verify.py`](../prl/lean/verify.py) | FR-VER, FR-FAIL-2/3, FR-PORT-2 | unit + integration | ☑ |
| F-26 | Hint extractor | [`prl/lean/hints.py`](../prl/lean/hints.py) | FR-HINT | unit | ☑ |
| F-27 | Integrity suite on real Lean | [`tests/test_lean_integrity.py`](../tests/test_lean_integrity.py) | IR-8 | 24 pass, zero false successes | ☑ |
| F-30 | Reference checks, eligibility, T | [`prl/tasks/eligibility.py`](../prl/tasks/eligibility.py) | FR-TASK-2 | — | ☑ |
| F-31 | Hidden tests (precondition proved, reference oracle, round-trip) | [`prl/testgen/hidden.py`](../prl/testgen/hidden.py) | FR-TEST-2 | — | ☑ |
| F-32 | Mutation operators + per-candidate selection | [`prl/mutate/`](../prl/mutate/) | FR-MUT | unit | ☑ |
| F-33 | Natural bugs from 0.8B and 9B, resample cap; shaping instances | [`prl/natural/collect.py`](../prl/natural/collect.py) | FR-NAT-1/2, FR-COND-7 | — | ☑ |
| F-35 | Family-level splits | [`prl/tasks/splits.py`](../prl/tasks/splits.py) | FR-TASK-5 | — | ☑ |
| F-40 | LM Studio client (reasoning off, retries, loading) | [`prl/models/lmstudio.py`](../prl/models/lmstudio.py) | FR-GEN-2 | — | ☑ |
| F-41 | Model registry | [`prl/models/registry.py`](../prl/models/registry.py) | NFR-ENV-2 | — | ☑ |
| F-42 | Prompts + TaskView (no leakage) | [`prl/models/prompts.py`](../prl/models/prompts.py), [`prereg/prompts/`](../prereg/prompts/) | FR-GEN-3, IR-9 | leakage test | ☑ |
| F-43 | Extraction (drops echoed locked definitions) | [`prl/models/extract.py`](../prl/models/extract.py) | FR-GEN-4 | unit | ☑ |
| F-50 | Protocols A, B, BP, C, Cplain, S, Splain and exploratory Bhammer (tactic menu); budget; infra retry; proof-tactic logging | [`prl/conditions/protocols.py`](../prl/conditions/protocols.py), [`prereg/prompts/Bhammer.txt`](../prereg/prompts/Bhammer.txt) | FR-COND, FR-COND-10, FR-BUD, FR-FAIL-1, FR-ANA-8 | fake-model tests | ☑ |
| F-51 | Feedback router | [`prl/conditions/feedback.py`](../prl/conditions/feedback.py) | FR-FB-1..3 | unit (all paths) | ☑ |
| F-52 | Driver: (model, condition) blocks, resume, records, freeze guard | [`prl/driver/runner.py`](../prl/driver/runner.py) | FR-DRV, SR-PRE-2 | kill/resume test | ☑ |
| F-53 | Energy meter (GPU measured, CPU estimated, CO2) | [`prl/energy.py`](../prl/energy.py) | FR-EN-1..3 | unit | ☑ |
| F-54 | Statistics + power simulation (`simulate_power`, `pilot_power`) | [`prl/analysis/stats.py`](../prl/analysis/stats.py) | SR-STAT | unit vs scipy; power sanity | ☑ |
| F-55 | Mechanism (shaping vs reverting) | [`prl/analysis/mechanism.py`](../prl/analysis/mechanism.py) | SR-MECH | unit | ☑ |
| F-56 | Code features + shapes | [`prl/analysis/features.py`](../prl/analysis/features.py), `report.py` | RQ4 | — | ☑ |
| F-57 | Report: primary-pool rule, energy, audit sample (+ flagged) and merge | [`prl/analysis/report.py`](../prl/analysis/report.py) | FR-ANA, FR-EN-3 | idempotence test | ☑ |
| F-58 | CLI | [`prl/cli.py`](../prl/cli.py) | FR-DRV-4 | `prl --help` | ☑ |
| F-59 | Pre-registration freeze (refuses without the power note) | [`prl/prereg.py`](../prl/prereg.py), [`prl/cli.py`](../prl/cli.py) | SR-PRE, SR-STAT-4 | unit | ☑ |
| F-60 | Tactic extraction (`proof_tactic_used`) and automation-only rule | [`prl/lean/leantext.py`](../prl/lean/leantext.py) | FR-ANA-8 | unit | ☑ |
| F-61 | B→C cross-evaluation (buckets, de-dup, resume) + report section | [`prl/analysis/crosseval.py`](../prl/analysis/crosseval.py), `prl crosseval`, `report.py` | FR-ANA-7 | unit | ☑ |
| F-62 | Pilot power note (three scenarios, α/4, eligible-family conversion incl. pilot) | [`prl/analysis/power.py`](../prl/analysis/power.py), `prl power` | SR-STAT-4 | unit | ☑ |
| F-63 | Derived `B_noauto` comparison, Bhammer comparisons, proof-style table | [`prl/analysis/report.py`](../prl/analysis/report.py) | FR-ANA-8/9 | unit | ☑ |

## Phase 2 — Dataset build

| ID | Command | Needs | Acceptance | Status |
|---|---|---|---|---|
| D-1 | `prl tasks build` then `prl tasks check --tests visible` | CPU | eligibility table; T coverage (full vector) | ☑ |
| D-2 | `prl hidden` | CPU | hidden tests for most families; reference passes all | ☑ |
| D-3 | `prl bugs natural` | **idle GPU** | ≤1 bug per family per generator (0.8B, 9B) | ☑ |
| D-4 | `prl bugs mutants` | CPU | ≤2 per family; provenance CSV; weak-spec flags | ☑ |
| D-5 | `prl bugs shaping` | — | one per T-unprovable eligible reference | ☑ |
| D-6 | `prl splits` | — | pilot 20 / main / held-out | ☑ |

## Phase 3 — Pilot and gate

| ID | Step | Acceptance | Status |
|---|---|---|---|
| P-1 | `prl run --study pilot --split pilot --kinds natural,mutant --allow-unfrozen --seeds 11 --conditions A,B,BP,Bhammer,C,Cplain` (primary models; Bhammer included only to measure its cost) | logs complete | ☑ |
| P-2 | Pilot-only tuning of prompts / portfolio; every change logged in [`prereg/deviations.md`](../prereg/deviations.md) | — | ☑ |
| P-3 | `prl power --study pilot`: power simulation (3 scenarios, 3 seeds, sign-flip at α/4, n_main → total eligible incl. pilot) | [`prereg/power_note.json`](../prereg/power_note.json), [`results/power_note.md`](../results/power_note.md) | ☑ |
| P-4 | Gate (requirements §10) recorded in [`docs/feasibility.md`](feasibility.md), incl. the Bhammer go/no-go from the cost estimate (logged in [`prereg/deviations.md`](../prereg/deviations.md)) | decision | ☑ |
| P-5 | `prl freeze` (refuses without the power note) | [`prereg/FREEZE.json`](../prereg/FREEZE.json) | ☑ |

## Phase 4 — Confirmatory run

| ID | Step | Status |
|---|---|---|
| M-1 | Study `main`: primary models × {A, B, BP, C, Cplain} × 3 seeds on `main` (natural + mutant instances) | ☑ |
| M-2 | Study `main-shaping`: primary models × {S, Splain} × 3 seeds on shaping instances | ☑ |
| M-3 | Study `main`: Gemma-4-E4B × {B, BP, C} × 1 seed | ☑ |
| M-4 | Study `main`: Goedel-Code-Prover-8B × {A, B} × 1 seed | ☑ |
| M-5 | Study `heldout` (run once): primary models × {B, BP, C} × 3 seeds; analysed separately as a replication | ☑ |
| M-6 | *Optional (P-4 decision):* study `main`, primary models × Bhammer × 3 seeds (exploratory; cost reported) | ☑ |

## Phase 5 — Analysis and reporting

| ID | Step | Status |
|---|---|---|
| R-0 | `prl crosseval --study main,heldout`: B→C cross-evaluation, Lean only | ☑ |
| R-1 | `prl analyze --study main,main-shaping` → [`results/`](../results/) (confirmatory + secondary: `B_noauto`, Bhammer, proof-style table, `crosseval.md`); `prl analyze --study heldout --out results/heldout` (replication, never pooled) | ☑ |
| R-2 | `prl audit --study main` → fill the CSV → `prl audit --merge` | ☑ (automated pre-screen; human audit pending) |
| R-3 | Code-shape catalogue with annotated before/after examples | ◐ (feature tables in [`results/rq4_shapes.md`](../results/rq4_shapes.md); annotated examples not written) |
| R-4 | Results summary with claims locked to [`results/`](../results/) ([`docs/proposal.md`](proposal.md)) | ◐ |
| R-5 | Write up the cross-evaluation buckets (R-0) as a secondary result, separate from B and C | ☑ |
| R-6 | Write up B overall vs `B_noauto` (from R-1) | ☑ |
| R-7 | Report the pre-freeze power note (P-3) and, if underpowered, state it as a limitation | ☑ |
| R-8 | If M-6 ran: Bhammer vs B and C with its compute cost, labelled exploratory | ☑ |

## Design → code → test map

| Item | Code | Test |
|---|---|---|
| Natural bugs from two generators, resample cap, primary-pool rule | [`prl/natural/collect.py`](../prl/natural/collect.py), [`prl/cli.py`](../prl/cli.py), [`prl/analysis/report.py: primary_pool`](../prl/analysis/report.py) | `test_primary_pool_rule` |
| Two-tier portfolio, identical for every portfolio user | [`prereg/portfolio.yaml`](../prereg/portfolio.yaml), [`prl/lean/portfolio.py`](../prl/lean/portfolio.py), [`prl/lean/builder.py`](../prl/lean/builder.py) | `test_portfolio_tiers_light_before_heavy` |
| Energy fields per block (in-run meter; figures withdrawn, see ADR 0014) | [`prl/energy.py`](../prl/energy.py), [`prl/driver/runner.py`](../prl/driver/runner.py), `report.py: energy_table` | `test_energy_block_math` |
| Lean workers sized from free RAM; 4 GB per-worker cap on Windows only | [`prl/lean/runner.py`](../prl/lean/runner.py) | checked on a live worker |
| Failure taxonomy: infrastructure vs candidate timeout/resource | [`prl/lean/verify.py: classify_failure`](../prl/lean/verify.py), [`prl/conditions/protocols.py: verify_with_infra_retry`](../prl/conditions/protocols.py) | `test_failure_classification` |
| Feedback router with every failure path | [`prl/conditions/feedback.py`](../prl/conditions/feedback.py) | `test_feedback_router_paths` |
| Pre-filter split into reject vs flag; flagged successes always audited | [`prl/lean/integrity.py`](../prl/lean/integrity.py), `report.py: audit_sample / audit_merge` | `test_degeneracy_flags` |
| B→C cross-evaluation, four buckets, de-duplicated, resumable | [`prl/analysis/crosseval.py`](../prl/analysis/crosseval.py), `prl crosseval` | `test_crosseval_buckets_and_dedup` |
| `proof_tactic_used` / `automation_only_proof`; frozen registry; derived `B_noauto` | [`prl/lean/leantext.py: proof_tactics`](../prl/lean/leantext.py), [`prl/conditions/protocols.py: proof_log`](../prl/conditions/protocols.py), `report.py: with_derived` | `test_proof_tactics_normalised`, `test_derived_B_noauto_and_crosseval_report` |
| Pilot power simulation; `prl freeze` requires the note | [`prl/analysis/stats.py: simulate_power / pilot_power`](../prl/analysis/stats.py), [`prl/analysis/power.py`](../prl/analysis/power.py) | `test_pilot_power_*`, `test_freeze_requires_power_note` |
| Exploratory Bhammer condition and prompt | [`prl/conditions/protocols.py: tactic_menu`](../prl/conditions/protocols.py), [`prereg/prompts/Bhammer.txt`](../prereg/prompts/Bhammer.txt) | `test_bhammer_*` |
| Wall guard at least 50 s; positive tier heartbeats | [`prl/lean/runner.py`](../prl/lean/runner.py), [`prl/lean/verify.py`](../prl/lean/verify.py), [`prl/lean/portfolio.py`](../prl/lean/portfolio.py) | `test_wall_guard_minimum`, `test_portfolio_rejects_unbounded_heartbeats` |
| Full `import Mathlib` in one pinned environment | [`lean_env/Prl.lean`](../lean_env/Prl.lean), [`lean_env/PrlRepl.lean`](../lean_env/PrlRepl.lean), [`prl/lean/builder.py`](../prl/lean/builder.py) | Lean suite (24 tests) |

---

## Operating rules

- Model runs (D-3, F-06, F-07, Phases 3–4) happen only when the GPU is otherwise idle and the team has given the go-ahead.
- Lean workers are derived from free RAM; never more than the machine can hold next to other jobs.
- Every change to [`prereg/`](../prereg/) after `prl freeze` is a logged deviation; results from different portfolios are never pooled.
- If more than 5% of runs in the confirmatory study end with an infrastructure failure (`driver.log` `[infra]` lines),
  stop and fix the infrastructure before continuing (failed runs re-execute on resume).
- [`prereg/`](../prereg/) and [`docs/adr/`](adr/) are authoritative for every study parameter.

## Testing strategy

1. Unit tests (no Lean, no LLM): `uv run pytest -m "not lean and not llm"` (96 tests).
2. Lean integration: `uv run pytest -m lean` (24 tests: integrity, re-shaping mechanism, determinism).
3. Static: `uv run ruff check prl tests`.
4. End-to-end dry run before the pilot: 3 families × all conditions × 1 seed × Qwen3.5-2B.

## Known issues

Neither affects a reported result.

- [`prl/analysis/report.py: with_derived`](../prl/analysis/report.py) applies `~` to a plain `bool` when the `automation_only_proof` column is
  missing; this breaks on Python 3.16.
- `prl tasks check` crashes when [`runs/phase0/`](../runs/phase0/) does not exist (`mkdir -p runs/phase0`); it only matters when the
  dataset is rebuilt, which the frozen study does not do.
