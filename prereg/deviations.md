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
| `study.yaml: bugs` | Natural bugs primary if ≥60 confirmatory families, else natural ∪ mutant | Gracy G1 + all verdicts (realism); rule fixed before any natural bug exists |
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

Bhammer go/no-go (to be filled after the pilot, before the freeze): _pending_.

## Post-freeze deviations

None yet.
