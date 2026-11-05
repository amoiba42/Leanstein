# Deviations and pre-freeze decisions

Pre-freeze changes are allowed (Phase 0 and pilot only) and are logged here with their reason. After
`prl freeze`, any change to `prereg/` is a deviation and is recorded with date, reason and impact.

## Disclosure

Before the final architecture (v2) was decided, a development version of the harness (v1) was run on VERINA
references and partially on mutants. Those outputs were **deleted** and are not used; the study restarts from
scratch on v2. The team did see one aggregate number from v1: portfolio coverage of reference implementations
≈23% (basic ≈37%, advanced ≈5%) under a single-tier portfolio with 200k heartbeats. The v2 tiering (below) was
chosen for cost and determinism, not to change coverage; Tier H keeps the same 200k limit for the heavy tactics.

## Pre-freeze decisions (v2, 2026-11-02)

| File | Decision | Reason |
|---|---|---|
| `portfolio.yaml` | Two tiers: L (decide/simp/simp_all/omega/split, 50k heartbeats) then H (grind/aesop/induction, 200k = Lean default); identical for every portfolio user | Gracy G7 (light first) made deterministic (heartbeats, not wall clock); no goal-classifier skipping; no confound between conditions |
| verification (LLD §5.4) | Staged verify: portfolio only if compile ∧ tests pass; entries one per request with early stop; full vector only for T | Cost; success semantics and `closing_entry` unchanged by construction |
| Lean backend (HLD D11) | Own verification server `lean_env/PrlRepl.lean`; CLI fallback | ~0.6 s vs 25–40 s per check; parity with the CLI checked (29/29 identical verdicts in v1 development) |
| `study.yaml: models` | Repairers Qwen3.5-2B/4B (primary), Gemma-4-E4B (secondary), Goedel-Code-Prover-8B (A/B); generators Qwen3.5-0.8B and 9B | latest small models (team instruction); generators never repair (no self-repair bias) |
| `study.yaml: bugs` | Natural bugs primary if ≥60 families of the `main` split have one (counted from the dataset manifests; wording clarified in v2.1), else natural ∪ mutant | Gracy G1 + all verdicts (realism); rule fixed before any natural bug exists |
| `study.yaml: lean` | 4 GB Job-Object cap per Lean worker; workers from free RAM; candidate timeouts confirmed once, then count | Gracy G3/G4 adapted to Windows; shared machine |
| `study.yaml: energy` | GPU measured (NVML) per (model, condition) block; CPU estimated (2.29 W/thread); CO2 0.716 kg/kWh | Gracy G2; Windows has no RAPL |
| `study.yaml: decoding` | `reasoning_effort: none` | hidden reasoning would consume the token budget invisibly |
| requirements FR-TASK-2, IR-4 | Eligibility does not require a human proof; `by` allowed inside code | 143/189 VERINA references have `sorry` proofs; term-level bounds proofs are legitimate code |
| prompts / extraction | Locked header always re-emitted; echoed locked definitions dropped | models often echo the given spec; dropping copies cannot affect verification |

## Pre-freeze decisions (v2.1, 2026-11-03: Gracy's revision-3 notes, `docs/final_architecture.md` §2b)

Decided before any data or result existed (nothing has been run on v2).

| File | Decision | Reason |
|---|---|---|
| `study.yaml: crosseval_conditions` | B→C cross-evaluation of B attempts that compile but fail their proof (`prl crosseval`); secondary, never pooled | R3-1: tests the mechanism on B's own code |
| `portfolio.yaml: single_call_automation` | Registry defining single-call automation proofs; B reported overall and as `B_noauto` | R3-2: answers "B only called grind" without banning automation in B |
| `study.yaml: analysis.power`, `power_note.json` | Pilot power simulation (3 scenarios, sign-flip at α/4, families and seeds as in the real test); total eligible = ⌈n_main/0.70⌉ + 20; `prl freeze` requires the note | R3-3, adapted (pilot families were missing from the conversion) |
| `study.yaml: exploratory_conditions`, `prompts/Bhammer.txt` | Exploratory Bhammer arm (B told the frozen tactics), primary models only; whether it runs is decided from the pilot cost estimate and recorded here before the freeze | R3-4 |
| `study.yaml: lean` | Wall guard must be ≥ 50 s; portfolio entries max(30 s, guard/4); tier heartbeats must be positive | R3-6 (documents existing behaviour, now enforced) |
| (declined) imports | Five tactic modules instead of `import Mathlib` **not adopted**; full Mathlib stays | R3-7: three modules do not exist in Mathlib v4.24; a smaller environment changes T coverage, breaks specs, breaks server/CLI parity |

## Pre-freeze decisions (2026-11-04: pre-pilot review)

Decided before any data or result existed (nothing has been run on v2).

| File | Decision | Reason |
|---|---|---|
| `exclusions.yaml` (new), `prl/tasks/eligibility.py` | Recorded exclusion list of known-bad VERINA tasks: `verina_basic_67` (test contradicts the description), `verina_basic_80` (test contradicts the spec), `verina_advanced_10` (not evaluable within Lean's recursion limits), `verina_basic_104` (custom `Map` type in the signature, checked on the pinned VERINA checkout). Eligibility now marks them `known_defect:<code>`. Earlier notes said "two Map tasks"; only one was found, and `verina_advanced_29/35/55` use HashMap only internally, so they stay in. Any other family flagged unsupported by the hidden-test generator is added here before the freeze | FR-TASK-3 required a recorded exclusion list but no list existed in `prereg/` or `prl/`; the defects were found in Phase 0 (`docs/feasibility.md`), before any v2 result |
| `docs/requirements.md` R1 | VERINA headline numbers checked against the paper (v3): 72.6% / 4.9% is o3, 61.4% / 3.6% is o4-mini, same paper, same pass@1 setting. No conflict; cite o3 and the paper version | The row previously said "different models/settings" and asked for a check |

## Pre-freeze decisions (2026-11-05: team decisions, ADR-001 to ADR-007)

Recorded as Nygard ADRs in `context/TEAM_DECISIONS.md`, with the evidence behind each. Decided before the
freeze and before any confirmatory result existed.

| File | Decision | Reason |
|---|---|---|
| `study.yaml: budget.max_infer_s` | 240 s -> 600 s (ADR-003) | The 240 s cap was not condition-neutral: it stopped 5 of 42 qwen3.5-4b condition-B runs (11.9%) and 0 of 42 condition-C runs. Pilot truncation by cell: 4B B 5/42, A 1/42, BP 1/42, Cplain 1/42, C 0/42, Bhammer 0/42; qwen3.5-2b 0 of 252. B's p90 was 225.6 s against the cap while C's was 101.5 s, and B slows through a run (15.5 to 26.2 s per attempt) as Lean error text accumulates in its prompt, so the cap removed B's late attempts specifically. 600 s is 1.5x the uncensored pilot maximum of 394.5 s; truncation falls to zero at 480 s and above, and the added wall clock is flat at +1.07 h on a 44 h run for any cap at or above 480 s |
| `study.yaml: budget.max_total_tokens` | unchanged at 48000 (ADR-003) | It never bound. The highest total observed in the pilot was 35,668. Raising it, as first proposed, would have had no effect |
| `exclusions.yaml` | unchanged; 184 tasks stay eligible (ADR-007) | The "16 of 189 specifications" claim traces to arXiv:2604.16584 §5.2, whose Table 1 lists the 16 task IDs. All 16 were fixed upstream by VERINA PR #17, squash-merged 2026-04-16 as `75c46698739ae00e81c46e973971e1bc61eaf461`, which touches 32 task directories. Verified locally: `git merge-base --is-ancestor 75c46698 66b3ce5...` exits 0, and `git diff --name-status 75c4669 66b3ce5 -- datasets/` is empty, so no dataset file changed between the fix and the pin. Exactly one of the 16, `verina_advanced_10`, was already excluded |

**Gate and shaping (ADR-001).** The screening gate in requirements R2 (>=20%) passed. Condition T coverage is
basic 35.6%, advanced 5.0%, overall 22.3%; the gate is recorded as read against the **overall 22.3%**, the
conservative figure, so that it passes on the stricter reading as well as the looser one. No tiering rule making
shaping (S) co-primary between 20% and 40% exists anywhere in `prereg/` or `docs/`, so R2 was applied as written.
S remains a mechanism study. The confirmatory family therefore stays at four tests (C vs B and C vs BP, for each
primary model) and Holm stays at alpha/4 = 0.0125, so `power_note.json` stands without re-simulation.

**Bug pool (ADR-002).** Natural bugs cover 32 of the 114 `main` families, below the pre-registered minimum of 60,
so the pre-registered fallback pool `natural + mutant` applies. The rule counts families of the confirmatory
split, not bug instances; the instance count is 56, and 54 families carry a natural bug across all splits.
Mutants are reported separately, per G1.

**C versus BP (ADR-004).** C vs BP is underpowered by the fixed size of VERINA and cannot be fixed: 327 `main`
families are needed against the 114 available, and it is unreachable under the pessimistic scenario. If C only
ties BP, that is reported as the same success rate without writing proofs, together with cost per repair, and
the power figures are stated in the same place rather than leaving the null bare. C vs B is unaffected.

**Bhammer go/no-go (ADR-005, decided 2026-11-05, before the freeze, from the pilot cost estimate only).**
Bhammer runs for the primary models (qwen3.5-2b, qwen3.5-4b), 3 seeds, on the `main` split, **unconditionally**,
as the last GPU job after the held-out run. No cutoff date and no condition, so no decision about it remains
open once results exist. If it does not run, the reason is a resource constraint and is reported as one; it is
not dropped because of what the main results show. It uses the same frozen checkout, model files and llama.cpp
build as the main study, runs without `--allow-unfrozen`, and is reported whatever it shows, labelled
exploratory and never pooled with B. Pilot cost: 1.73 h of inference over 84 runs, about 23% of the 7.47 h used
by the five main conditions, scaling to roughly 10 GPU hours on the `main` split.

**Quantisation and serving (ADR-006).** All models are 4-bit GGUF built by llama.cpp commit `162e2bb` and served
through llama.cpp rather than LM Studio as designed; hashes are in `results/ada_model_hashes.txt`. bf16 does not
fit the 11 GB 1080 Ti, and no repository code was changed. Full precision on other hardware was considered and
rejected: it would invalidate the pilot, the power note and the cap calibration, all of which are specific to
these model files. Results are for 4-bit models and do not generalise to full precision. A full-precision side
check remains available afterwards, reported separately and never pooled.

**Second benchmark audit, checked 2026-11-05 (ADR-007).** arXiv:2605.23772, "Isomorphism Is Not Enough", is
mostly an audit of CLEVER; its isomorphism critique does not apply to VERINA. Its Appendix A reports 6 erroneous
VERINA entries (2 basic, 4 advanced). The paper prints no task IDs; they are in sunblaze-ucb/verina issue #16,
footnoted in v1: `verina_basic_40`, `verina_basic_104`, `verina_advanced_10`, `verina_advanced_12`,
`verina_advanced_15`, `verina_advanced_44`. All six were fixed by the same PR #17, and two are already excluded
for unrelated reasons. Note for future readers: arXiv:2604.16584 §5.2 says the VERINA authors "addressed 15; the
remaining one is under review", which appears to contradict the above. It does not. That paper was submitted one
day after PR #17 merged, and `verina_advanced_71` was fixed by a later commit inside the same squashed PR
(closing upstream issue #21). All 16 are fixed at `75c46698`.

**Scope note on the dataset check.** The specs stored in `data/families/` match the pinned `task.lean`
byte-for-byte for all 16 affected tasks, but they also match for all 189 families, so that comparison shows the
study's extraction is faithful to the pin and carries no information specific to the 16. The load-bearing
evidence for ADR-007 is the ancestry, which was verified directly.

## Measurement guard added with the cap change (2026-11-05)

If `stop_reason == "infer_time"` exceeds 1% of runs in any condition during a `main` run, the run is halted and
reported before continuing. The `main` study is 7,182 runs against the pilot's 504, so there are fourteen times
as many chances for a pathological run; the field is already logged, so this costs nothing and turns a hidden
confound into a visible event. The truncation rate per condition is reported in the paper whatever the cap.

## Post-freeze deviations

None yet.
