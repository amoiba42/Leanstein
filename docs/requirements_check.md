# Requirements and NFR compliance check

Checked 2026-11-14 against `main` at commit `2017d88`, the state delivered for review. This document checks the
project against [`docs/requirements.md`](requirements.md) (FR, SR, IR, DR, NFR, the go/no-go gate). It records what
holds, what holds with a documented deviation, and what does not. It changes no code, no study input and nothing
under `prereg/`: the freeze (`3f2744e1`) is unaffected.

**Follow-up, same day:** several of the gaps found here were then closed. Sections 1 to 6 keep the findings as
they were for the delivered state, with a note where a gap is now closed; section 7 lists what was done.

Status legend: **Met** · **Met (deviation)** a documented deviation applies · **Partly** · **Not met** ·
**Not verified** not re-checked here (reported by the team, or no direct evidence).

## 1. How a reviewer can verify the main claims

Use a checkout with Unix line endings: `git clone -c core.autocrlf=false`. The freeze hashes exact bytes, so a
Windows (CRLF) checkout reports every `prereg/` file as modified even though the content is unchanged.
(Since the follow-up a `.gitattributes` file enforces LF, so a plain `git clone` is enough.)

```bash
uv sync --extra dev
uv run python -c "from prl.prereg import freeze_status; ok,d,dig=freeze_status(); print(ok, d, dig[:16])"
#  -> True [] 3f2744e132b37783
uv run pytest -m "not lean and not llm"        # 96 passed (needs no Lean)
uv run pytest -m lean                          # 24 passed (needs Lean 4.24.0, Mathlib cache, third_party/verina)
uv run ruff check prl tests                    # All checks passed
uv run prl analyze --study main,main-shaping,main-gemma,main-goedel,main-bhammer --out /tmp/regen/main
uv run prl analyze --study heldout --out /tmp/regen/heldout
uv run prl analyze --study pilot   --out /tmp/regen/pilot
#  compare every file in /tmp/regen/* with results/, results/heldout, results/pilot
```

The study logs are committed (`runs/<study>/runs.jsonl`, `attempts.jsonl` or `attempts.jsonl.gz`, `crosseval.jsonl`).
The raw model outputs under `runs/*/raw/` are not in the repository (see DR-LOG-2).

### Verification log, 2026-11-14

Run on a scratch copy of the delivered repository on the Ada cluster (CPU only); the study was not re-run.

| Check | Result |
|---|---|
| `freeze_status()` on the unmodified copy | `True []`, digest `3f2744e1…`, 19 files |
| Tamper test: one line appended to `prereg/study.yaml`, then `prl run --study main --split main` | `REFUSING TO RUN: prereg/ differs from FREEZE.json: study.yaml`, exit code 2; file restored, `freeze_status()` again `True []` |
| Unit tests | 96 passed |
| Lean integration tests | 24 passed (zero false successes) |
| `ruff check prl tests` | All checks passed |
| Regenerating results from the committed logs | 57 of 57 files byte-identical to the committed ones (main 20, held-out 20, pilot 17), about 12 s, 6 s and 5 s |
| Independent recomputation of the family-level rates (primary pool, 106 families) | 9 cells match `results/rq1_main.md` to three decimals |
| Run counts | main 6,930, Gemma 693, Goedel 462, Bhammer 1,386, shaping 1,068, held-out 1,710 = 12,249 confirmatory runs (+492 pilot); no duplicate run ids; every confirmatory run carries the second-freeze digest |
| Caps | worst case over the 12,249 runs: 8 attempts (cap 8), 47,962 tokens (cap 48,000), 548 s inference (cap 600 s) |

## 2. Functional requirements

| ID | Status | Evidence |
|---|---|---|
| FR-TASK-1 | Met | 189 family files in `data/families/`; parsing tests in `tests/test_core_units.py` |
| FR-TASK-2 | Met | 184 eligible; the 5 excluded each carry a reason; `ref_proof` recorded for eligible tasks: absent 138, human_ok 33, human_broken 13 |
| FR-TASK-3 | Met | `prereg/exclusions.yaml` (4 known defects, machine-readable) plus `verina_basic_70` excluded by the eligibility check (unrenderable tests) |
| FR-TASK-4 | Met | every instance carries `family_id`; analysis is by family |
| FR-TASK-5 | Met | pilot 20 (11 basic, 9 advanced), main 114, held-out 50 (30.5% of non-pilot); disjoint; together they cover all 184 eligible families |
| FR-TASK-6 | Met | 510 instance manifests (316 mutant, 51 natural, 143 shaping), each with a locked-region hash; hidden-test files carry `sha256` |
| FR-MUT-1 | Met | 8 operator classes in the data: arith, relflip, boolop, const, swap_branches, negate_cond, swap_args, drop_succ. Not checked whether "wrong initial accumulator" is a separate class or covered by `const` |
| FR-MUT-2 | Met | every one of 316 mutants and 51 natural bugs has a failing witness |
| FR-MUT-3 | Met | at most 2 mutants per family; operator, line, column, before and after recorded |
| FR-MUT-4 | Met | `test_mutation_deterministic` |
| FR-NAT-1 | Met | at most 1 natural bug per (family, generator); generators only Qwen3.5-0.8B (6) and 9B (45) |
| FR-NAT-2 | Met | natural bugs cover 33 of 114 main families (< 60), so the pre-registered fallback pool natural + mutant applies; `test_primary_pool_rule` |
| FR-TEST-1 | Met | visible tests run as `#guard`; Lean tests pass |
| FR-TEST-2 | **Partly** | 170 of 184 families have 30 hidden tests, 9 have 6 to 25, and **5 have none**: `verina_advanced_61` (pilot), `verina_advanced_68` and `verina_basic_25` (held-out), `verina_basic_40` and `verina_basic_63` (main); reasons: no admissible inputs, or unsupported return type. The requirement says "up to 30", so this is allowed, and it is now disclosed as D-5 in `prereg/deviations.md`. 260 of the 12,249 confirmatory runs (2.1%) rely on visible tests only |
| FR-TEST-3 | Met (limit above) | pass on visible and hidden tests; families without hidden tests use visible tests only |
| FR-VER-1..4, 6 | Met | 24 Lean tests incl. determinism and the axiom allow-list; locked-region tests |
| FR-VER-5, 7 | Not verified | content-addressed cache and staged verification are implemented; no dedicated test found |
| FR-PORT-1..5 | Met | `prereg/portfolio.yaml` (hashed in `FREEZE.json`); loader rejects non-positive heartbeats (`test_portfolio_rejects_unbounded_heartbeats`); `test_portfolio_tiers_light_before_heavy` |
| FR-HINT-1..3 | Met | `test_pointer_catalogue`, `test_hint_kinds_by_failure_stage`, `test_hint_length_cap_and_determinism`; cap `max_chars: 1200` in `prereg/hints.yaml`. The logs keep hint kinds, not hint text, so the cap cannot be re-checked from logs |
| FR-FB-1..3 | Met | `test_feedback_router_paths`, `test_hidden_failures_never_reveal_inputs` |
| FR-RES-1 | Met (deviation) | the Windows Job Object memory cap is not applied on Linux (`prereg/deviations.md` R-10) |
| FR-RES-2 | Not verified | whole-Mathlib verification server is used for all runs; the CLI parity test was not re-checked |
| FR-FAIL-1, 2 | Met | 1 infrastructure failure in 12,249 runs (shared-cache temp-file race), not charged to the model, resumed; timeouts and resource kills recorded as candidate failures (70 and 23 attempts in the held-out log) |
| FR-FAIL-3 | Met | every attempt record has `failure_kind` (values seen: extraction, integrity, compile, test, timeout, resource, proof, none) |
| FR-EN-1 | **Not met** | the in-run NVML meter read physical GPU 0, not our GPU; the figures were withdrawn (D-1). The withdrawn values are still present in the generated `results/rq5_energy.csv` and in the energy table of `results/rq5_costs.md`, whose caption still says "GPU energy is measured"; the valid figures are in `results/rq5_energy_estimate.md` |
| FR-EN-2, FR-EN-3 | **Partly** | replaced by a post-hoc calibration estimate (D-4): joules per token per model, charged by logged tokens; Lean CPU energy from logged Lean seconds; labelled as estimates, not the pre-registered measurement |
| FR-GEN-1, 3, 4 | Met | extraction tests; `test_prompt_never_leaks_reference_or_hidden`; 100 extraction failures logged as attempts in the held-out log |
| FR-GEN-2 | Met (deviation) | OpenAI-compatible API, fixed decoding, reasoning off; served by llama.cpp `162e2bb` through an `lms` stand-in instead of LM Studio (R-3) |
| FR-GEN-5 | Met | determinism probe: same seed identical, different seed differs, for 2B and 4B (`results/phase0_determinism.json`) |
| FR-COND-1..10 | Met | all conditions were run (T, A, B, BP, C, Cplain, S, Splain, Bhammer); `test_turn0_information_equal_across_conditions`, `test_bhammer_prompt_lists_the_frozen_portfolio_and_nothing_else_differs` |
| FR-BUD-1..3 | Met | no run exceeded a cap (see the log above); `stop_reason` recorded on every run; the 600 s cap is ADR-003 |
| FR-BUD-4 | Met | `lean_s_total` recorded per run and reported (`results/rq5_costs.md`) |
| FR-DRV-1, 2, 5 | Met | `runs.jsonl` and `attempts.jsonl`; `test_driver_resume_identical`; the study jobs were resumed after the one infrastructure failure |
| FR-DRV-3 | **Partly** | deterministic order and parallel Lean workers, but model calls ran 12 in parallel on one GPU slice, not serialized (R-6) |
| FR-DRV-4 | **Partly** | `prl analyze` regenerates all tables in one command (verified); the study itself runs as several `prl run` commands (`scripts/irel/queue.sh`), not one command from one config |
| FR-ANA-1 | **Partly** | `results/outcomes.csv` has verified_repair, correct_unverified, integrity_violation and unresolved; the label `verified_but_behaviourally_wrong` is not a column (it appears only as the cross-evaluation bucket `c_proves_tests_fail`) |
| FR-ANA-2..5 | Met | `comparisons.csv` (only_x, only_y, both, neither), `rq2_mechanism.md`, `rq4_shapes*.csv`, statistics tests |
| FR-ANA-6 | **Not met yet** | the 10% sample plus flagged successes (333 rows) is exported, but the review so far is an automated pre-screen; a human audit is pending (D-3) |
| FR-ANA-7, 8 | Met | `results/crosseval.md`, `runs/*/crosseval.jsonl`, `B_noauto` rows in `comparisons.csv`, `test_crosseval_buckets_and_dedup` |
| FR-ANA-9 | Met | Bhammer ran (1,386 runs), reported separately |

## 3. Scientific, integrity and data requirements

| ID | Status | Evidence |
|---|---|---|
| SR-PRE-1 | **Partly** | `FREEZE.json` hashes 19 files: study config (decoding, budgets, seeds, split parameters, analysis parameters), portfolio, hints, prompts, exclusions, power note. The RQs, hypotheses and analysis plan are written in `docs/`, which is not hashed. The split assignment `data/splits.json` is not hashed; it is derived deterministically from the seed in `study.yaml` |
| SR-PRE-2 | Met | verified by the tamper test above (exit code 2). **No unit test** existed for it, although section 9 asks for one; closed in the follow-up (section 7) |
| SR-PRE-3 | Met | 0 confirmatory runs on pilot families |
| SR-SEL-1, 2 | Met | `results/t_coverage.md`: 189 screened, 184 eligible, basic 35.6%, advanced 5.0%, all 22.3%; the pool is not filtered by T |
| SR-MECH-1..4 | Not verified | `results/rq2_mechanism.md` exists; its numbers were not re-derived here |
| SR-STAT-1..3 | Met | tests on synthetic data; 9 family-level rates recomputed independently and matching |
| SR-STAT-4, 5 | Met | `prereg/power_note.json`, `results/power_note.md`; `test_freeze_requires_power_note`; `min_detectable` column |
| SR-STAT-6, 8 | Met | exploratory results labelled; secondary results descriptive |
| SR-STAT-7 (SHOULD) | **Partly** | stratified by bug source (mutant, natural) and shaping; the other strata (tier, operator, ref_auto, input type) are in `rq4_shapes*` and were not checked |
| IR-1..6, 8, 9 | Met | 24 Lean tests pass with zero false successes (`test_escape_rejected` is parametrised over the escape cases, plus `test_weakened_postcondition_is_impossible`, locked-region and marker-injection tests); prompt-leakage test |
| IR-7 | **Partly** | flags are recorded, but flagged successes must enter a *mandatory* audit, which is a pending human audit (D-3). 239 of the 333 audited successes carry `copies_postcond`; the flag's 0.35 threshold is too low to separate copying from implementing on VERINA (reported in D-3) |
| DR-1, DR-BUG-1, 2, DR-TEST-1, 2, DR-LOG-1, 3 | Met | `data/` and `runs/`; provenance CSVs in `data/provenance/`; hidden tests carry seed and hash |
| DR-LOG-2 | **Partly** | prompt hashes and every attempt's code are committed; full raw outputs, rendered Lean file hashes and Lean logs live in `runs/*/raw/`, which is excluded from git |
| DR-REL | **Partly**, now Met (section 7) | manifests, provenance, prompts, portfolio, logs and analysis scripts are present; there was no `LICENSE` file |

## 4. Non-functional requirements

| ID | Status | Evidence |
|---|---|---|
| NFR-ENV-1 | Met (deviation) | no paid API, no training; the study ran on a 48 GB MIG slice, not the 8 GB laptop (R-3) |
| NFR-ENV-2 | Met | `lean_env/lake-manifest.json`, `uv.lock`, `requires-python = ">=3.12,<3.13"`, VERINA commit pinned, GGUF SHA-256 in `results/ada_model_hashes.txt` |
| NFR-REP-1 | Met | verified: 57 of 57 regenerated files are byte-identical to the committed ones |
| NFR-REP-2 | **Partly**, now Met (section 7) | there was no `scripts/setup`; setup steps are in the README and `scripts/irel/setup_*.sh` (specific to the IREL server). Not tested from a clean machine in this check |
| NFR-REL-1 | Not verified | no dedicated 1,000-call test; indirect evidence: 12,249 runs completed with one infrastructure failure |
| NFR-REL-2 | **Partly**, now Met (section 7) | wall guards are implemented and 93 timeout or resource events were handled in the held-out log; no dedicated test of killing a hung Lean process tree |
| NFR-PERF-1 | Met (deviation) | per-worker memory cap not applied on Linux (R-10); two jobs shared the slice (R-6, R-7) |
| NFR-PERF-2 | **Partly** | one model per study folder, but two `llama-server` instances ran side by side on the slice (R-7) |
| NFR-QA-1 | Met | 96 unit and 24 Lean tests, passing on the delivered code (103 unit tests after the follow-up) |
| NFR-QA-2 | Met | ruff passes; type hints on public APIs not checked |
| NFR-FEAS-1 | Met | `docs/feasibility.md` and `results/phase0_*.json`, collected before the freeze |
| NFR-FEAS-2 | Met | compile probe (20 tasks): Qwen3.5-2B 10%, Qwen3.5-4B 40%, neither near zero |
| NFR-SEC-1 | **Partly** | model output is run only inside Lean, in a temporary directory with stdin closed, and `#eval` and IO are banned (IR-2); no operating-system network isolation of the Lean process was found |

## 5. Go / no-go gate (section 10)

| Criterion | Status | Evidence |
|---|---|---|
| 1. T proves at least 20% | Met | 41 of 184 = 22.3% (basic 35.6%, advanced 5.0%) |
| 2. Compile rate in C above 10% | Met | 233 of 506 attempts = 46.0% on the pilot |
| 3. At least one **hand-verified** repair that neither B nor BP finds | **Partly** | 10 such C-only repairs were found on the pilot; the one reviewed in detail (`verina_basic_107__mut__arith__1`) was checked by an automated pre-screen and its human confirmation is pending |
| 4. Integrity suite, zero false successes | Met | 24 Lean tests pass |
| 5. Cost within about 72 h | Met | 12,249 runs in about 14.7 h |
| 6. Power note written | Met | `prereg/power_note.json` |

## 6. Open items and limitations

1. **Human audit (FR-ANA-6, IR-7, gate 3).** Pending. Until it is complete, claims that depend on the audit are
   stated as pending (ADR-0015).
2. **Energy (FR-EN-1..3).** The measured GPU energy was withdrawn; the energy figures are post-hoc estimates (D-4).
   The withdrawn in-run values remain in the generated `results/rq5_energy.csv` and `results/rq5_costs.md`
   (also in `results/heldout/` and `results/pilot/`). Use only `results/rq5_energy_estimate.md` and
   `results/energy_coefficients.csv`. The generated files were left unchanged so that `prl analyze` still
   regenerates them byte-identically. *Follow-up:* the table in `rq5_costs.md` is now headed as withdrawn
   (section 7, D-6); `rq5_energy.csv` is unchanged. The requirement itself (measured GPU energy) stays not met.
3. **Five families without hidden tests (FR-TEST-2).** 260 runs (2.1%) rely on visible tests only. Disclosed as D-5 in `prereg/deviations.md`.
4. **No test for two stated acceptance checks:** a modified `prereg/` file is refused (verified here by hand), and
   a hung Lean process is killed within its wall guard. *Closed in the follow-up (section 7).*
5. **`scripts/setup` (NFR-REP-2) and `LICENSE` (DR-REL) are absent.** Setup is documented in the README.
   *Follow-up:* `scripts/setup.sh`, `LICENSE` and `NOTICE` were added (section 7).
6. **Raw outputs are not in the repository (DR-LOG-2).** Logs of each attempt's code, verdict and prompt hash are.
7. **Known code issue:** `prl/analysis/report.py:61` applies `~` to a bool, which is deprecated and fails on
   Python 3.16. The project pins Python 3.12, so it has no effect on the results. *Fixed in the follow-up (section 7).*
8. **Underpowered comparison.** C vs BP at 4B (power 0.08 at the pilot's effect size); a tie is not evidence of
   equivalence (`results/power_note.md`).

## 7. Follow-up after the review (2026-11-14)

Each change is a separate commit. No study run, verdict, test outcome or reported number changed, and no hashed
file under `prereg/` was touched; the changes are disclosed as D-5 and D-6 in
[`prereg/deviations.md`](../prereg/deviations.md).

| Gap | What was done | Evidence |
|---|---|---|
| A Windows checkout fails the freeze check (section 1) | `.gitattributes` checks out every text file with LF | Linux checkouts (GitHub CI, Ada copy) report `True []`; a fresh clone on Windows was not tested in this check |
| SR-PRE-2: no unit test for the freeze refusal | six tests in [`tests/test_acceptance_guards.py`](../tests/test_acceptance_guards.py): untouched copy passes; a changed, added or removed file is named; `deviations.md` is exempt; `prl run` on `main` and on `heldout` exits with code 2 and creates no run folder | part of the unit tests |
| NFR-REL-2: no test that a hung Lean process tree is killed | one test in the same file: `run_lean_cli` is given a stand-in process that starts a child and hangs; with a 3 s guard the call returns as a timeout, both processes are gone and the work folder is removed. The test fails when the tree kill is disabled. It covers the `cli` backend; the server-pool backend uses the same `_kill_tree` | part of the unit tests |
| NFR-REP-2: no `scripts/setup` | [`scripts/setup.sh`](../scripts/setup.sh) performs the README's setup steps and then the freeze check, the unit tests and `prl env`; `--no-lean` skips Lean | ran with exit code 0 on a fresh copy (`--no-lean`) and in full on the Ada copy (Lean and Mathlib were already installed there, so the first-time download was not exercised) |
| FR-EN-1: withdrawn energy figures presented as measured | the cost report now heads the in-run energy table as withdrawn and points to the D-4 estimate; the three `rq5_costs.md` files were regenerated | they differ from the earlier versions only in that heading and sentence; `rq5_energy.csv` still carries the figures unlabelled |
| FR-TEST-2: five families without hidden tests were not disclosed | D-5 | 260 of 12,249 confirmatory runs, recounted from the logs |
| Known code issue (`~` on a `bool` in `with_derived`) | uses a boolean series when the column is absent | no result depends on it; regeneration is unchanged |
| The checks could not be seen by a reader | [`.github/workflows/ci.yml`](../.github/workflows/ci.yml) runs ruff, the freeze check, the unit tests and the regeneration of `results/` (all files except figures must equal the committed ones) on every push; the README has a "Verify this project" section | the workflow passes on GitHub |
| DR-REL: no `LICENSE` | [`LICENSE`](../LICENSE) (Apache-2.0, the licence of VERINA) and [`NOTICE`](../NOTICE), which credits VERINA and states which folders are derived from it and how | the licence text equals the official Apache-2.0 text |
| Access: the repository was private | made public | |

### Verification log of the follow-up

| Check | Result |
|---|---|
| `freeze_status()` | `True []`, digest `3f2744e1…` (local copy with LF endings, Ada copy, GitHub CI) |
| Unit tests | 103 passed (96 + 7 new) |
| Lean integration tests (Ada) | 24 passed |
| `ruff check prl tests` | All checks passed |
| Regenerating `results/` with the changed `report.py` | every file equal to the committed one, except the three `rq5_costs.md` files (heading and one sentence), which were then committed |
| `scripts/setup.sh` on the Ada copy | exit code 0; `prl env`: Lean smoke test OK |

Still open after the follow-up: the human audit (item 1), measured energy (item 2), raw outputs
(item 6), the 1,000-call reliability test (NFR-REL-1) and the limits of the study itself (item 8).

## 8. Second follow-up: weak points from the review (2026-11-14)

Disclosed as D-7 in [`prereg/deviations.md`](../prereg/deviations.md). Nothing under `prereg/` that is hashed was
touched, and no run, verdict or confirmatory number changed.

| Weak point | What was done | Evidence |
|---|---|---|
| Claims rest on logs, not re-checked | Every logged success of the six study folders was re-verified in Lean from the logged code and proof, cache disabled ([`scripts/reverify.py`](../scripts/reverify.py)) | [`results/reverify/summary.md`](../results/reverify/summary.md): all 1,858 re-verify, with the same proof source and closing portfolio entry as logged |
| BP ties C at 4B | "C against BP" section in the README and the paper: power 0.08; 180 of BP's 182 4B successes were the portfolio's proofs; C 37k vs BP 65k tokens per verified repair; 3.4 times fewer integrity rejections | `results/power_note.md`, `results/rq5_costs.md`, `results/runs_flat.csv` |
| Many successes are easy (reverts) | Exploratory paired test of C against B and BP on the 85 families whose reference the portfolio cannot prove: C beats B for all three models | [`results/exploratory_shaping.md`](../results/exploratory_shaping.md) ([`scripts/exploratory_shaping.py`](../scripts/exploratory_shaping.py)) |
| Code-shape catalogue and case studies missing | 15 real before/after cases, chosen deterministically from `runs/main/` | [`docs/code_shapes.md`](code_shapes.md) ([`scripts/code_shapes_catalogue.py`](../scripts/code_shapes_catalogue.py)) |
| Thin pool of real bugs | Natural-only and mutant-only results shown side by side in the paper (table "Exploratory robustness checks") and the README; stated as a limitation | `results/rq1_main.md` |
| Small scale; energy estimated | "Limitations" section in the paper; energy removed from the abstract's headline, tokens lead | `paper/main.tex` |
| Paper not in the repository | `paper/` and `report/` (removed by the 2026-11-07 clean-up) restored and rebuilt | `paper/main.pdf`, `report/progress_report.pdf` |
| Server address in the repository | removed from `scripts/irel/README.md` (it remains in older commits) | |

Also affected: SR-STAT-7 now also has the `ref_auto` stratum (exploratory); SR-MECH-1..4 has the case catalogue.
Still open: the human audit, measured energy and
raw outputs.
