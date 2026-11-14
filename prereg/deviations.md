# Deviations and pre-freeze decisions

Pre-freeze changes are allowed (Phase 0 and pilot only) and are logged here with their reason. After
`prl freeze`, any change to [`prereg/`](./) is a deviation and is recorded with date, reason and impact.

## Disclosure

Before the final architecture (v2) was decided, a development version of the harness (v1) was run on VERINA
references and partially on mutants. Those outputs were **deleted** and are not used; the study restarts from
scratch on v2. The team did see one aggregate number from v1: portfolio coverage of reference implementations
≈23% (basic ≈37%, advanced ≈5%) under a single-tier portfolio with 200k heartbeats. The v2 tiering (below) was
chosen for cost and determinism, not to change coverage; Tier H keeps the same 200k limit for the heavy tactics.

## Pre-freeze decisions (v2, 2026-11-02)

| File | Decision | Reason |
|---|---|---|
| [`portfolio.yaml`](portfolio.yaml) | Two tiers: L (decide/simp/simp_all/omega/split, 50k heartbeats) then H (grind/aesop/induction, 200k = Lean default); identical for every portfolio user | Light-first tiering made deterministic (heartbeats, not wall clock); no goal-classifier skipping; no confound between conditions |
| verification (LLD §5.4) | Staged verify: portfolio only if compile ∧ tests pass; entries one per request with early stop; full vector only for T | Cost; success semantics and `closing_entry` unchanged by construction |
| Lean backend (HLD D11) | Own verification server [`lean_env/PrlRepl.lean`](../lean_env/PrlRepl.lean); CLI fallback | ~0.6 s vs 25–40 s per check; parity with the CLI checked (29/29 identical verdicts in v1 development) |
| [`study.yaml: models`](study.yaml) | Repairers Qwen3.5-2B/4B (primary), Gemma-4-E4B (secondary), Goedel-Code-Prover-8B (A/B); generators Qwen3.5-0.8B and 9B | latest small models (team instruction); generators never repair (no self-repair bias) |
| [`study.yaml: bugs`](study.yaml) | Natural bugs primary if ≥60 families of the `main` split have one (counted from the dataset manifests; wording clarified in v2.1), else natural ∪ mutant | Realism of model-written bugs; rule fixed before any natural bug exists |
| [`study.yaml: lean`](study.yaml) | 4 GB Job-Object cap per Lean worker; workers from free RAM; candidate timeouts confirmed once, then count | Resource limits adapted to Windows; shared machine |
| [`study.yaml: energy`](study.yaml) | GPU measured (NVML) per (model, condition) block; CPU estimated (2.29 W/thread); CO2 0.716 kg/kWh | Energy tracking; Windows has no RAPL |
| [`study.yaml: decoding`](study.yaml) | `reasoning_effort: none` | hidden reasoning would consume the token budget invisibly |
| requirements FR-TASK-2, IR-4 | Eligibility does not require a human proof; `by` allowed inside code | 143/189 VERINA references have `sorry` proofs; term-level bounds proofs are legitimate code |
| prompts / extraction | Locked header always re-emitted; echoed locked definitions dropped | models often echo the given spec; dropping copies cannot affect verification |

## Pre-freeze decisions (v2.1, 2026-11-03: team review additions, see [`docs/adr/`](../docs/adr/))

Decided before any data or result existed (nothing has been run on v2).

| File | Decision | Reason |
|---|---|---|
| [`study.yaml: crosseval_conditions`](study.yaml) | B→C cross-evaluation of B attempts that compile but fail their proof (`prl crosseval`); secondary, never pooled | Tests the mechanism on B's own code |
| [`portfolio.yaml: single_call_automation`](portfolio.yaml) | Registry defining single-call automation proofs; B reported overall and as `B_noauto` | Answers "B only called grind" without banning automation in B |
| [`study.yaml: analysis.power`](study.yaml), [`power_note.json`](power_note.json) | Pilot power simulation (3 scenarios, sign-flip at α/4, families and seeds as in the real test); total eligible = ⌈n_main/0.70⌉ + 20; `prl freeze` requires the note | Adapted: pilot families were missing from the conversion |
| [`study.yaml: exploratory_conditions`](study.yaml), [`prompts/Bhammer.txt`](prompts/Bhammer.txt) | Exploratory Bhammer arm (B told the frozen tactics), primary models only; whether it runs is decided from the pilot cost estimate and recorded here before the freeze | Tests whether knowing the tactics is enough |
| [`study.yaml: lean`](study.yaml) | Wall guard must be ≥ 50 s; portfolio entries max(30 s, guard/4); tier heartbeats must be positive | Documents existing behaviour, now enforced |
| (declined) imports | Five tactic modules instead of `import Mathlib` **not adopted**; full Mathlib stays | Three modules do not exist in Mathlib v4.24; a smaller environment changes T coverage, breaks specs, breaks server/CLI parity |

## Pre-freeze decisions (2026-11-04: pre-pilot review)

Decided before any data or result existed (nothing has been run on v2).

| File | Decision | Reason |
|---|---|---|
| [`exclusions.yaml`](exclusions.yaml) (new), [`prl/tasks/eligibility.py`](../prl/tasks/eligibility.py) | Recorded exclusion list of known-bad VERINA tasks: `verina_basic_67` (test contradicts the description), `verina_basic_80` (test contradicts the spec), `verina_advanced_10` (not evaluable within Lean's recursion limits), `verina_basic_104` (custom `Map` type in the signature, checked on the pinned VERINA checkout). Eligibility now marks them `known_defect:<code>[`. Earlier notes said "two Map tasks"; only one was found, and `](./)verina_advanced_29/35/55` use HashMap only internally, so they stay in. Any other family flagged unsupported by the hidden-test generator is added here before the freeze | FR-TASK-3 required a recorded exclusion list but no list existed in [`prereg/`](./) or [`prl/`](../prl/); the defects were found in Phase 0 ([`docs/feasibility.md`](../docs/feasibility.md)), before any v2 result |
| [`docs/requirements.md`](../docs/requirements.md) R1 | VERINA headline numbers checked against the paper (v3): 72.6% / 4.9% is o3, 61.4% / 3.6% is o4-mini, same paper, same pass@1 setting. No conflict; cite o3 and the paper version | The row previously said "different models/settings" and asked for a check |

## Pre-freeze decisions (2026-11-05: team decisions, team decisions 1 to 7)

Recorded as seven team decisions (team decisions 1 to 7), with the evidence behind each; the resulting design is in [`docs/adr/`](../docs/adr/). Decided before the
freeze and before any confirmatory result existed.

| File | Decision | Reason |
|---|---|---|
| [`study.yaml: budget.max_infer_s`](study.yaml) | 240 s -> 600 s (team decision 3) | The 240 s cap was not condition-neutral: it stopped 5 of 42 qwen3.5-4b condition-B runs (11.9%) and 0 of 42 condition-C runs. Pilot truncation by cell: 4B B 5/42, A 1/42, BP 1/42, Cplain 1/42, C 0/42, Bhammer 0/42; qwen3.5-2b 0 of 252. B's p90 was 225.6 s against the cap while C's was 101.5 s, and B slows through a run (15.5 to 26.2 s per attempt) as Lean error text accumulates in its prompt, so the cap removed B's late attempts specifically. 600 s is 1.5x the uncensored pilot maximum of 394.5 s; truncation falls to zero at 480 s and above, and the added wall clock is flat at +1.07 h on a 44 h run for any cap at or above 480 s |
| [`study.yaml: budget.max_total_tokens`](study.yaml) | unchanged at 48000 (team decision 3) | It never bound. The highest total observed in the pilot was 35,668. Raising it, as first proposed, would have had no effect |
| [`exclusions.yaml`](exclusions.yaml) | unchanged; 184 tasks stay eligible (team decision 7) | The "16 of 189 specifications" claim traces to arXiv:2604.16584 §5.2, whose Table 1 lists the 16 task IDs. All 16 were fixed upstream by VERINA PR #17, squash-merged 2026-04-16 as `75c46698739ae00e81c46e973971e1bc61eaf461`, which touches 32 task directories. Verified locally: `git merge-base --is-ancestor 75c46698 66b3ce5...` exits 0, and `git diff --name-status 75c4669 66b3ce5 -- datasets/` is empty, so no dataset file changed between the fix and the pin. Exactly one of the 16, `verina_advanced_10`, was already excluded |

**Gate and shaping (team decision 1).** The screening gate in requirements R2 (>=20%) passed. Condition T coverage is
basic 35.6%, advanced 5.0%, overall 22.3%; the gate is recorded as read against the **overall 22.3%**, the
conservative figure, so that it passes on the stricter reading as well as the looser one. No tiering rule making
shaping (S) co-primary between 20% and 40% exists anywhere in [`prereg/`](./) or [`docs/`](../docs/), so R2 was applied as written.
S remains a mechanism study. The confirmatory family therefore stays at four tests (C vs B and C vs BP, for each
primary model) and Holm stays at alpha/4 = 0.0125, so [`power_note.json`](power_note.json) stands without re-simulation.

**Bug pool (team decision 2).** Natural bugs cover 32 of the 114 `main` families, below the pre-registered minimum of 60,
so the pre-registered fallback pool `natural + mutant` applies. The rule counts families of the confirmatory
split, not bug instances; the instance count is 56, and 54 families carry a natural bug across all splits.
Mutants are reported separately.

**C versus BP (team decision 4).** C vs BP is underpowered by the fixed size of VERINA and cannot be fixed: 327 `main`
families are needed against the 114 available, and it is unreachable under the pessimistic scenario. If C only
ties BP, that is reported as the same success rate without writing proofs, together with cost per repair, and
the power figures are stated in the same place rather than leaving the null bare. C vs B is unaffected.

**Bhammer go/no-go (team decision 5, decided 2026-11-05, before the freeze, from the pilot cost estimate only).**
Bhammer runs for the primary models (qwen3.5-2b, qwen3.5-4b), 3 seeds, on the `main` split, **unconditionally**,
as the last GPU job after the held-out run. No cutoff date and no condition, so no decision about it remains
open once results exist. If it does not run, the reason is a resource constraint and is reported as one; it is
not dropped because of what the main results show. It uses the same frozen checkout, model files and llama.cpp
build as the main study, runs without `--allow-unfrozen`, and is reported whatever it shows, labelled
exploratory and never pooled with B. Pilot cost: 1.73 h of inference over 84 runs, about 23% of the 7.47 h used
by the five main conditions, scaling to roughly 10 GPU hours on the `main` split.

**Quantisation and serving (team decision 6).** All models are 4-bit GGUF built by llama.cpp commit `162e2bb` and served
through llama.cpp rather than LM Studio as designed; hashes are in [`results/ada_model_hashes.txt`](../results/ada_model_hashes.txt). bf16 does not
fit the 11 GB 1080 Ti, and no repository code was changed. Full precision on other hardware was considered and
rejected: it would invalidate the pilot, the power note and the cap calibration, all of which are specific to
these model files. Results are for 4-bit models and do not generalise to full precision. A full-precision side
check remains available afterwards, reported separately and never pooled.

**Second benchmark audit, checked 2026-11-05 (team decision 7).** arXiv:2605.23772, "Isomorphism Is Not Enough", is
mostly an audit of CLEVER; its isomorphism critique does not apply to VERINA. Its Appendix A reports 6 erroneous
VERINA entries (2 basic, 4 advanced). The paper prints no task IDs; they are in sunblaze-ucb/verina issue #16,
footnoted in v1: `verina_basic_40`, `verina_basic_104`, `verina_advanced_10`, `verina_advanced_12`,
`verina_advanced_15`, `verina_advanced_44`. All six were fixed by the same PR #17, and two are already excluded
for unrelated reasons. Note for future readers: arXiv:2604.16584 §5.2 says the VERINA authors "addressed 15; the
remaining one is under review", which appears to contradict the above. It does not. That paper was submitted one
day after PR #17 merged, and `verina_advanced_71` was fixed by a later commit inside the same squashed PR
(closing upstream issue #21). All 16 are fixed at `75c46698`.

**Scope note on the dataset check.** The specs stored in [`data/families/`](../data/families/) match the pinned `task.lean`
byte-for-byte for all 16 affected tasks, but they also match for all 189 families, so that comparison shows the
study's extraction is faithful to the pin and carries no information specific to the 16. The load-bearing
evidence for team decision 7 is the ancestry, which was verified directly.

## Measurement guard added with the cap change (2026-11-05)

If `stop_reason == "infer_time"` exceeds 1% of runs in any condition during a `main` run, the run is halted and
reported before continuing. The `main` study is 7,182 runs against the pilot's 504, so there are fourteen times
as many chances for a pathological run; the field is already logged, so this costs nothing and turns a hidden
confound into a visible event. The truncation rate per condition is reported in the paper whatever the cap.

## Restart on the IREL server: second freeze (2026-11-05)

Everything above describes the **first freeze** (digest `964f19836f224d10`, 2026-11-05 16:05), whose dataset,
probes and pilot were produced on a Windows laptop (RTX 5060, LM Studio) and on Ada (GTX 1080 Ti, llama.cpp).
The study was then moved to one GPU for every step, so that every computation and every model run in the paper
comes from the same hardware and software. The pre-freeze pipeline was rerun from scratch there, and the study
was frozen a second time.

**R-1. Why, and when.** The decision to restart was made on 2026-11-05 at about 19:10, before any confirmatory
result was analysed. Mixing a laptop dataset, an Ada pilot and an IREL study would have meant three
environments in one study. One environment for everything is the coherent design.

**R-2. What was discarded.** Under the first freeze, the IREL server had started `main` (about 310 runs) and
`heldout` (about 250 runs), plus a 55-run timing check on pilot families. All of it was deleted unanalysed.
Disclosure: one stop-rule check printed raw success counts once: `main` 0 of 308 runs (all qwen3.5-2b, A and
B), `heldout` 1 of 250. Nothing else was looked at. These counts played no part in any decision; the decision
to restart was about hardware consistency. The laptop dataset, the Ada pilot and the first power note remain in
git history and are not used.

**R-3. Hardware and serving, for every step of the study.** Everything runs on the IREL server, on one fixed MIG
slice: NVIDIA RTX PRO 6000 Blackwell Max-Q, GPU 1, MIG device 0 (2g.48gb, UUID
`MIG-def14cbb-599b-58f4-9cef-4befe9ff8506`), driver 595.99, CUDA 13.1, AMD Threadripper PRO 7975WX, Ubuntu 24.04.
That covers the dataset (task checks, hidden tests, natural bugs, mutants, shaping instances, splits), probes,
pilot, power note, every study run and the analysis. Models are the same six 4-bit GGUF files, SHA-256 verified
against [`results/ada_model_hashes.txt`](../results/ada_model_hashes.txt), served by llama.cpp at commit `162e2bb` (built for sm_120) through an
`lms` stand-in ([`scripts/irel/bin/lms`](../scripts/irel/bin/lms): all layers on GPU, `--jinja`, reasoning disabled, 8192 tokens of context
per parallel slot). No repository code was changed. Every job log records the GPU, driver, slice, llama.cpp commit
and repo commit. Job scripts: [`scripts/irel/`](../scripts/irel/).

**R-4. The one [`prereg/`](./) change before the second freeze.** [`study.yaml: energy.cpu_watts_per_thread`](study.yaml) changed
from 2.29 (i7-14650HX laptop) to 5.47 (Threadripper PRO 7975WX, 350 W TDP / 64 threads), because the CPU energy
estimate must describe the machine that ran the study. Prompts, portfolio, hints, budgets, the 600 s cap, seeds,
models and the analysis plan are unchanged.

**R-5. The team decisions carry over as rules (team decisions 1 to 7).** They are applied again to the IREL numbers,
recorded in the section below before the second freeze. The 600 s cap and the 1% `infer_time` guard (team decision 3)
stay as decided; the cap was calibrated on the first pilot and is not re-tuned on the second.

**R-6. Concurrency.** `--run-workers 12` instead of 4, with 6 Lean workers. On the slice, qwen3.5-4b gave 91
tok/s aggregate at 4 parallel requests, 168 at 8 and 217 at 16. The 600 s cap is wall-clock, so per-request speed
matters. With two jobs of 12 requests each, per-request decoding was 66–81 tok/s, about Ada's 67 tok/s at 4
workers. That is where the slice saturates, so the study runs at most two jobs at a time. The `infer_time` guard
is monitored per condition throughout.

**R-7. Two lanes and extra study folders.** Two jobs run side by side, each with its own llama-server on the
slice. Jobs that run beside main primary write to their own folders ([`runs/main-gemma`](../runs/main-gemma/), [`runs/main-goedel`](../runs/main-goedel/),
[`runs/main-bhammer`](../runs/main-bhammer/)) instead of [`runs/main`](../runs/main/), so that two processes never append to one `runs.jsonl`. Run IDs
include the study name; seeds, prompts and budgets do not. The analysis reads the folders together
(`prl analyze --study main,main-shaping,main-gemma,main-goedel,main-bhammer`), and the cross-evaluation covers
`main,main-gemma,heldout`.

**R-8. Bhammer timing (team decision 5).** Bhammer starts only after held-out has finished, as team decision 5 requires. It may
overlap the end of other jobs, so it is not strictly the last GPU job. What team decision 5 protects is unchanged: the
commitment is unconditional, independent of any result, and the start time is set by scheduling alone.

**R-9. Energy is not attributable per block.** NVML reads energy per physical GPU. GPU 1 also hosts other users'
MIG slices, and two of our jobs run at once, so a block's joules include other work. Energy per verified repair
(RQ5) is reported only as whole-GPU energy with this caveat, never as a per-condition comparison.

**R-10. No per-worker memory cap on Linux.** The 4 GB cap per Lean worker (FR-RES-1) uses a Windows Job
Object and is not applied on Linux ([`prl/lean/runner.py`](../prl/lean/runner.py)). The study server has 503 GB of RAM and runs at most
12 Lean workers, so the cap's purpose, protecting a shared 24 GB laptop, does not arise. Lean's heartbeat budgets
and the per-request wall guards apply unchanged, and no repository code was changed.

## Second freeze: gate and rules applied to the IREL numbers

Written 2026-11-05 at about 21:15, after the IREL pipeline and pilot, before the second `prl freeze`. Computed by
[`scripts/irel/gate.py`](../scripts/irel/gate.py). The same pre-registered rules as the first freeze, applied to the new numbers:

**Dataset (IREL).** 189 tasks; 184 eligible (104 basic, 80 advanced), the same 5 exclusions. Reference checks,
hidden tests, splits (pilot 20, main 114, held-out 50) and shaping instances (89/39/15) are byte-identical to the
first build. Mutants are identical except one: for `verina_basic_85` a different mutant was kept, because a
candidate crossed the 20 s wall guard on this machine. Natural bugs were re-sampled: 51 instances (first build
56), 34 in `main`, 10 in held-out, 7 in pilot.

**Gate (team decision 1).** Portfolio coverage of eligible references (condition T): overall 41/184 = 22.3%, basic
37/104 = 35.6%, advanced 4/80 = 5.0%, identical to the first build; >=20% on the overall figure, so the gate
passes. S stays a mechanism study, and the confirmatory family stays at four tests, Holm alpha/4.

**Bug pool (team decision 2).** 33 of 114 `main` families carry a natural bug, below 60, so the pre-registered fallback
pool `natural + mutant` applies again. Mutants are reported separately.

**Gate criteria from the pilot** (492 runs: 41 instances x 6 conditions x 2 primary models, seed 11, 0
infrastructure failures, 0 `infer_time` stops at 600 s):
- compile rate in C: 233/506 attempts = 46.0% (> 10%, passes);
- C repairs that neither B nor BP finds on the same instance, model and seed: 10 (>= 1). Automated pre-screen,
  **human check pending**: `verina_basic_107__mut__arith__1` (qwen3.5-2b). The mutant changed
  `(a + b) / 2` to `(a - b) / 2`; C returned `(a + b) / 2`, which `unfold_omega` proves against
  `2 * result = a + b - ((a + b) % 2)` and which passes all visible and hidden tests. A real repair.
- false successes: none found by the automated pre-screen. 90 successes; the one carrying a flag
  (`verina_basic_6__mut__boolop__1`, C, qwen3.5-2b, `mentions_postcond`) is `min a (min b c)`, a correct
  minimum of three. Human check pending.
- cost: 7.17 h of inference for the pilot. Bhammer used 1.45 h, 25% of the five main conditions, so it fits and
  runs unconditionally (team decision 5).

**One harness change before the second freeze (H-1).** Reading the C-only repairs showed two that inline the
postcondition's own expression (`verina_basic_18`, `verina_advanced_22`): correct and verified, but spec-copying.
The `mentions_postcond` flag only catches code that names the postcondition. A new flag, `copies_postcond`,
fires when at least 35% of the postcondition's token 4-grams appear in the code ([`prl/lean/integrity.py`](../prl/lean/integrity.py),
unit test `test_copies_postcond_flag`; on the pilot examples the copies score 0.45 and 0.93, clean repairs 0.00
and 0.14). Flags never change a verdict; they decide what enters the audit, which includes every flagged
success. The verification cache was cleared so that no study run reuses pre-change flags.

**Power (team decision 4), from [`prereg/power_note.json`](power_note.json), point estimate, at 114 `main` families:** C vs B: qwen3.5-2b
1.000 (34 needed), qwen3.5-4b 0.996 (57 needed); C vs BP: qwen3.5-2b 0.706 (136 needed), qwen3.5-4b 0.082 (not
reachable). C vs BP is underpowered by the fixed size of VERINA, as before; a tie is reported with these
figures and cost per repair.

**Unchanged:** the 600 s cap and the 1% `infer_time` guard (team decision 3), 4-bit models (team decision 6), no new exclusions
(team decision 7).

## Post-freeze deviations (second freeze)

All found after the runs finished (2026-11-06). None changes a run, a verdict, a test or a pre-registered rule.

**D-1. GPU energy was read from the wrong device; energy figures are withdrawn.** [`prl/energy.py`](../prl/energy.py) reads the NVML
counter of device index 0. NVML ignores `CUDA_VISIBLE_DEVICES`, so on the IREL server index 0 is physical GPU 0,
which belongs to other users, not GPU 1 where our slice lives. The `gpu_j` values in `runs/*/energy.jsonl`
therefore measure someone else's GPU (they fall to near zero once GPU 0 went idle on the morning of 6 Nov). The
Lean CPU estimate is also unusable: it sums every Lean process on the machine, and two of our jobs ran at once,
so a block's CPU seconds include the other job's (some blocks read 0 because the other job's workers exited).
R-9 already ruled out per-condition energy comparisons; D-1 goes further: no energy or CO2 figure from this
study is reported. RQ5 cost is reported with the per-run measures, which are recorded per run and are not
affected: completion tokens, inference seconds, Lean seconds and attempts per verified repair. The meter code is
left unchanged so that the run outputs stay reproducible from the frozen code.

**D-2. Two bugs in the audit sampler ([`prl/analysis/report.py: audit_sample`](../prl/analysis/report.py)).** (a) `s.flags` resolved to the
pandas `DataFrame.flags` property instead of the `flags` column, so `prl audit` crashed; it now reads
`s["flags"]`. (b) pandas 3 drops the grouping column from `groupby(...).apply(...)`, so the stratified rows lost
their `condition`; the sampled rows are now taken back from the success table by `run_id`. The sample is the
same 333 runs (10% stratified by condition, seed from [`study.yaml`](study.yaml), plus every flagged success); only the missing
column is restored.

**D-3. Audit is an automated pre-screen; human audit pending.** The 333 sampled successes of `main` (126 distinct
programs, 41 families; 239 carry `copies_postcond`) were pre-screened automatically against each family's postcondition and
description. Results are in [`results/audit/sample.csv`](../results/audit/sample.csv), each note marked "automated pre-screen; human audit
pending". Result: 0 spec-gaming; 27 runs (11 families) judged not natural code, because they decide the
postcondition proposition directly (for example `∀ c ∈ s.toList, isDigit c` as a `Bool`) or carry dead code.
Every `copies_postcond` success restates an exact, executable postcondition (closed forms, folds, filters), so the
flag fires on intended computations; the flag's 0.35 threshold is too low to separate copying from
implementing on VERINA and is reported as such.

**D-4. Energy is estimated after the fact by calibration (replaces the withdrawn D-1 figures).** On 2026-11-06,
after the study, each model was served again on our slice with the study's settings (llama.cpp `162e2bb`,
12 parallel slots, 8192 tokens per slot, temperature 0.7, top-p 0.95, reasoning off) and fed prompts that it
actually received in the study (from `runs/*/raw`). Board power of physical GPU 1 was sampled every 100 ms
(`power.draw.instant`). Each of three cycles has an idle window, a prefill-only workload (48 prompts, 1 output
token), another idle window and a full workload (48 prompts, up to 1,536 tokens). The marginal energy of a
workload is its power above the mean of the adjacent idle windows, integrated over the window. This gives
joules per prompt token (from prefill) and per completion token (from the full workload, minus prefill) for each
model: Qwen3.5-2B 0.141 / 0.008, Qwen3.5-4B 0.258 / 0.024, Gemma-4-E4B 0.252 / 0.021, Goedel-8B 0.392 / 0.027
J per completion / prompt token, with cycle-to-cycle spread up to ±15%. Every model call in the study is then
charged by its logged tokens. Lean CPU energy is each run's logged Lean seconds x the pre-registered 5.47 W per
thread, and CO2 uses the pre-registered 0.716 kg/kWh. Script: [`scripts/irel/energy_calib.py`](../scripts/irel/energy_calib.py),
[`scripts/irel/energy_estimate.py`](../scripts/irel/energy_estimate.py). Data: [`results/energy_calib/`](../results/energy_calib/). Output: `results/rq5_energy_estimate.{csv,md}`.
Limits: these are estimates, not the pre-registered measurement. Static (idle) GPU power is shared with other
tenants and is not attributed. The calibration uses one server at a time, whereas the study ran two jobs side by
side; a 24-slot check with Qwen3.5-4B gave about 1.6 times the joules per completion token (0.42), so absolute
figures could be up to that much higher. That factor applies equally to every condition of a model, so
comparisons between conditions are unaffected.

**D-5. Five families have no hidden tests; their runs are judged on visible tests only (disclosure, no change to data).** Hidden-test generation (`prl tasks hidden`) produced no tests for five of the 184 eligible families, because no admissible inputs could be generated or the return type is unsupported: `verina_advanced_61` (pilot), `verina_advanced_68` and `verina_basic_25` (held-out), `verina_basic_40` and `verina_basic_63` (main). The requirement says "up to 30" hidden tests per task, so this is allowed, but it was not stated elsewhere. For these families a candidate passes when it passes the visible tests and the proof checks. Affected confirmatory runs: 260 of 12,249 (2.1%): `verina_basic_40` 94, `verina_basic_63` 94, `verina_advanced_68` 36, `verina_basic_25` 36; `verina_advanced_61` has no confirmatory runs. Nothing was re-generated or re-run, and no result was changed. Readers who want to exclude them can filter these four families from `results/runs_flat.csv`.

**D-6. Maintenance after the instructor's review (2026-11-14); no run, verdict or number changed.** (a) The cost report wrote "GPU energy is measured (NVML counter)" above the in-run energy table, although D-1 withdrew those figures. [`prl/analysis/report.py`](../prl/analysis/report.py) now writes a heading and a sentence that mark the table as withdrawn and point to the D-4 estimate. `results/rq5_costs.md`, `results/heldout/rq5_costs.md` and `results/pilot/rq5_costs.md` were regenerated; they differ from the earlier versions only in that heading and sentence. `results/rq5_energy.csv` still carries the withdrawn figures without a label, because the file is regenerated from the logs. (b) `with_derived` in the same file applied `~` to a Python `bool` when the column `automation_only_proof` is absent. The column is present in every run of this study, so no result depends on it; it now uses a boolean series. (c) Added without touching the study: tests for the freeze refusal and for killing a hung Lean process (`tests/test_acceptance_guards.py`), a setup script (`scripts/setup.sh`), a `.gitattributes` that fixes line endings to LF so that the freeze check passes on a Windows checkout, and a CI workflow (`.github/workflows/ci.yml`) that checks the freeze, runs the unit tests and regenerates `results/` from the committed logs on every push. After these changes `prl analyze` reproduces every other file under `results/` byte for byte.

**D-7. Post-study checks and exploratory tables (2026-11-14); no run, verdict or pre-registered number changed.** (a) *Re-verification of every logged success.* [`scripts/reverify.py`](../scripts/reverify.py) reads each successful run's winning attempt (code, helpers and, in proof-writing conditions, the model's proof) back from `runs/<study>/attempts.jsonl` and gives it again to the trusted judge in the condition's mode, with the verification cache disabled: static integrity, compile, visible and hidden tests, the locked-specification hash, the proof (the model's own, or the frozen portfolio in its frozen order) and the axiom check. It ran on a Windows laptop with Lean 4.24.0 and Mathlib v4.24.0, not on the study machine. Result: all 1,858 logged successes of `main`, `main-gemma`, `main-goedel`, `main-bhammer`, `main-shaping` and `heldout` re-verify, each with the same proof source and the same closing portfolio entry as logged (1.3 h of Lean time). Output: [`results/reverify/`](../results/reverify/). (b) *Exploratory tables, not pre-registered and not Holm-corrected.* [`scripts/exploratory_shaping.py`](../scripts/exploratory_shaping.py) repeats the paired family-level comparison of C against B and BP on the 85 `main` families whose reference implementation the portfolio cannot prove (`results/exploratory_shaping.{csv,md}`); the paper also tabulates the already computed natural-only and mutant-only comparisons from `results/comparisons.csv` side by side. (c) [`scripts/code_shapes_catalogue.py`](../scripts/code_shapes_catalogue.py) writes [`docs/code_shapes.md`](../docs/code_shapes.md): 15 real before/after cases selected deterministically from `runs/main/` (C shaping successes where B failed on the same instance and seed). (d) The paper and the mid-submission report, removed from the tree by the 2026-11-07 clean-up, are restored under `paper/` and `report/`; the paper adds a "C against BP" section, a limitations section and the items above, and states D-3 as an automated pre-screen.
