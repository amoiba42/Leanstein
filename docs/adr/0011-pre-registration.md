# 0011. Pre-registration and freeze

## Status
Accepted

## Context
Tuning the portfolio, prompts or budgets after seeing results would bias the comparison.

## Decision
- A pilot on the 20 pilot families (492 runs, one seed, primary models) is the only place prompts, budgets and the
  portfolio may be tuned.
- A power simulation from the pilot (three scenarios, sign-flip at α/4, families and seeds as in the real test)
  is written to `prereg/power_note.json`; `prl freeze` refuses to run without it.
- `prl freeze` hashes the study inputs in `prereg/` into `prereg/FREEZE.json`; the driver refuses confirmatory
  runs if anything differs.
- Gate at the end of the pilot: portfolio coverage of eligible references at least 20%, compile rate above 10% in
  C, at least one C repair that neither B nor BP finds, no false successes, cost fits.
- The held-out split is run and analysed once, separately.
- Every change after the freeze is a logged deviation in `prereg/deviations.md`.

## Consequences
- The gate passed on the overall coverage of 22.3%; study S stays a mechanism study (no rule promotes it to
  co-primary, and a fifth test would move Holm to α/5 and invalidate the power note), so the primary family stays at
  four tests.
- Deviations after the freeze (energy meter, audit sampler, audit status, energy calibration) are documented and
  change no result.
