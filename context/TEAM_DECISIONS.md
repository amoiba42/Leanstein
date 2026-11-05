# Team decisions before the freeze

Seven decisions, in Nygard ADR form. All of them block `uv run prl freeze`, and
the freeze blocks the main study, the held-out run and the analysis.

Reconstructed 2026-11-05 from the team chat, because `Project/TEAM_DECISIONS.md`
was never handed over. Every figure was checked against the repository.

| ADR | Decision | Status |
|---|---|---|
| 001 | S stays a mechanism study, not co-primary | Accepted |
| 002 | Fallback bug pool `natural + mutant` | Accepted |
| 003 | `max_infer_s` 240 -> 600; tokens unchanged | Accepted |
| 004 | Report a C/BP tie with its power figures | Accepted |
| 005 | Bhammer runs unconditionally, last GPU job | Accepted |
| 006 | Keep 4-bit models; record as a deviation | Accepted |
| 007 | "16 of 189 specs" does not apply; no rebuild | Accepted |

**Before the freeze**, two checks under ADR-007 must close: skim arXiv:2605.23772,
and confirm the VERINA ancestry on the Ada checkout. Then write the appendix text
into `prereg/deviations.md`, change `max_infer_s` in `prereg/study.yaml`, and run
the freeze on that same checkout.

---

## ADR-001 — Shaping (S) stays a mechanism study

**Status:** Accepted 2026-11-05

**Context.** The chat proposed that coverage landing in a "20 to 40% tier" makes
S co-primary. No such tiering rule exists in the repository:
`docs/requirements.md` R2 sets a single threshold, >=20% screening, with 40% named
as a reported target. Condition T coverage is basic 35.6%, advanced 5.0%, overall
22.3%, so the gate passes on either reading. Promoting S would add a fifth test
to the confirmatory family.

**Decision.** The gate passed. S is **not** co-primary. It stays the mechanism
study it already is in `docs/final_architecture.md` §3.

**Consequences.**
- The confirmatory family stays at four tests: C vs B and C vs BP, for each of
  qwen3.5-2b and qwen3.5-4b. Holm stays at alpha/4 = 0.0125.
- `results/power_note.md` stands. `uv run prl power` does not re-run. At alpha/5
  every figure in it would have become optimistic.
- S still runs under `--study main-shaping` and is reported in full. Because it is
  not confirmatory, that job may run at any point after the freeze.
- `deviations.md` must name which coverage figure the gate was read against, so
  the choice cannot look made after the fact.

---

## ADR-002 — Fallback bug pool `natural + mutant`

**Status:** Accepted 2026-11-05

**Context.** `prereg/study.yaml` sets `min_natural_families: 60`, counted in
**families of the confirmatory split**, not in bug instances. Counted from
`data/instances/`: 56 natural instances, 54 families with a natural bug across all
splits, and **32 in the `main` split** of 114. The chat quoted 56 against 60,
which is the wrong unit; the real comparison is 32 against 60.

**Decision.** The pre-registered fallback applies. The confirmatory bug pool is
`natural + mutant`.

**Consequences.**
- Record **32 of 114 main families carry a natural bug** in `deviations.md`.
  `results/power_note.md` already uses 32.
- Mutants stay reported separately, per G1.
- This is the pre-registered rule firing as written, before any result existed. It
  is a strength of the design and should be reported as one, not as a shortfall.

---

## ADR-003 — Raise `max_infer_s` from 240 to 600; leave tokens at 48000

**Status:** Accepted 2026-11-05

**Context.** The 240 s cap was not condition-neutral. Across 504 pilot runs,
all eight time-cap stops fall on qwen3.5-4b: B 5/42 (11.9%), A, BP and Cplain 1/42
each, **C 0/42**, Bhammer 0/42; qwen3.5-2b 0 of 252.

| seconds per run | C | Cplain | A | BP | Bhammer | B |
|---|---|---|---|---|---|---|
| median | 26.4 | 28.7 | 42.1 | 46.7 | 69.8 | **76.1** |
| p90 | 101.5 | 95.2 | 167.6 | 237.2 | 131.2 | **225.6** |

B's p90 sits against the cap; C's is nowhere near it. B also slows as a run
proceeds, 15.5 to 26.2 s per attempt, because Lean error text accumulates in its
prompt (3,032 to 7,963 characters); C speeds up, 12.2 to 5.6 s, prompt 3,298 to
5,977. So the cap removed B's *late* attempts, which are exactly the ones that
test whether feedback-guided proof writing converges.

A small raise does not fix it. 286.8 s is the longest run *observed*, not wanted:
those runs stopped at 5-7 of 8 attempts, so demand is censored. Extrapolated from
each run's own last-three-attempt rate, true demand is 283-395 s. By candidate
cap, runs still truncated: 240 s cuts 17 of 504, 300 s cuts 7 (all five B runs),
360 s cuts 3, **480 s and above cut none**.

Cost is flat above 480 s: +0.63 h at 300 s, +0.98 h at 360 s, **+1.07 h at 480 s
and at every larger value**, on a 44 h main run at 4 workers. Uncensored pilot
distribution: p50 46.0, p90 157.9, p95 210.6, p99 346.3, max 394.5.

The token cap never binds: the highest total observed is 35,668 against 48,000.

**Decision.** `max_infer_s` 240 -> 600 (1.5x the uncensored pilot maximum).
`max_total_tokens` stays 48000. These are the only two values in `prereg/` that
may be edited before the freeze.

**Consequences.**
- *Legitimate because of where we stand.* `prereg/FREEZE.json` does not exist and
  all 504 pilot runs carry `prereg_sha: "unfrozen"`. The pilot is a calibration
  run by design, and the rule is outcome-independent: 600 s was chosen from
  `stop_reason` counts, never from success counts.
- *The pilot is no longer comparable to the main study.* It ran at 240 s, main
  runs at 600 s. Never pool them; never present pilot success rates as a preview.
- *The power note is mildly optimistic for C vs B.* Its discordant-pair rates were
  measured under the old cap. Re-running `uv run prl power` cannot repair this,
  because its input was itself collected at 240 s. Record it as a limitation.
- *Bhammer's estimate survives.* It had 0 of 84 time-cap stops.
- *Stop rule to pre-register.* Main is 7,182 runs against the pilot's 504. If
  `stop_reason == "infer_time"` exceeds 1% of runs in any condition during `main`,
  halt and report before continuing.
- Report the truncation rate per condition in the paper whatever the cap.

---

## ADR-004 — Report a C/BP tie together with its power figures

**Status:** Accepted 2026-11-05

**Context.** `results/power_note.md`, at 114 main families:

| comparison | model | power | families needed |
|---|---|---|---|
| C vs B | qwen3.5-2b | 1.000 | 34 |
| C vs B | qwen3.5-4b | 0.688 | 136 |
| C vs BP | qwen3.5-2b | 0.278 | 327 |
| C vs BP | qwen3.5-4b | 0.000 | unreachable |
| C vs BP | either, pessimistic | 0.000 | unreachable |

C vs B is in good shape. C vs BP is underpowered and **cannot be fixed**: VERINA
is fixed at 189 tasks, so the families do not exist. A tie is the expected
outcome.

**Decision.** If C only ties BP, report it as "the same success rate without
writing proofs", together with cost per repair, and state in the same place that
C vs BP was underpowered by the fixed size of VERINA, giving the power figures.

**Consequences.**
- A bare null reads as a hidden result; the same null with its power stated is a
  limitation declared up front.
- Cost per repair (RQ5) carries the argument instead, and does not depend on power.
- Agreeing the wording now, before the numbers land, is what makes it credible.

---

## ADR-005 — Bhammer runs unconditionally, as the last GPU job

**Status:** Accepted 2026-11-05

**Context.** `docs/final_architecture.md` §2b R3-4 makes Bhammer exploratory and
optional, primary models only, decided from the pilot cost estimate before the
freeze. Pilot cost: 1.73 h of inference over 84 runs, 23% of the 7.47 h used by
the five main conditions, scaling to about **10 GPU hours** on the main split.
Mean per run: 53.6 s and 19,312 tokens on 2B, 94.4 s and 17,442 tokens on 4B,
close to B (56.1 s and 136.1 s) and about double C (25.5 s and 51.9 s).
Pilot outcome: Bhammer solved 6 instances B missed and 1 fewer than B in the other
direction, but **0** that C missed.

A conditional rule was considered and rejected. "Run it if the GPU frees" has no
closing point, so it survives as an open question into the period when the main
results are known, which makes it outcome-dependent in practice whatever the
intent.

**Decision.** Bhammer runs. Unconditionally, as the last GPU job, after the
held-out run. No cutoff date and no "if", because no decision is left to take.

**Consequences.**
- Nothing can drift: the commitment is made before the freeze and depends on no
  result.
- If it does not run, the reason must be a resource constraint and is reported as
  one. Not running because the main results made it unattractive is not available.
- The late run is valid only on the same frozen checkout, model files
  (`results/ada_model_hashes.txt`) and llama.cpp build, with nothing rebuilt in
  between, without `--allow-unfrozen`.
- Reported whatever it shows, labelled exploratory, never pooled with B.
- It answers "B lost only because it did not know the tactics", which makes the
  C vs B result much harder to call a strawman.

---

## ADR-006 — Keep 4-bit models and record the deviation

**Status:** Accepted 2026-11-05

**Context.** Ada has one 1080 Ti, 11 GB. At bf16, qwen3.5-9b is about 18 GB and
goedel-code-prover-8b about 16 GB, so full precision does not fit; the laptop's
RTX 5060 is 8 GB, smaller still. Ada's 50 GB home already holds about 20 GB of
4-bit weights beside Lean and Mathlib. `HANDOVER.md` lines 49-50 record the
separate GPU server as out of scope for the main study, discussed only as a
full-precision side check and never decided.

Switching now would also invalidate everything derived from the pilot: the
discordant-pair rates behind the power note, the Bhammer cost estimate, and the
timings behind ADR-003. All of it is specific to these model files.

**Decision.** Keep 4-bit for the whole study. Record three things together in
`deviations.md`: 4-bit quantisation, llama.cpp commit `162e2bb` in place of LM
Studio, and the hashes in `results/ada_model_hashes.txt`.

**Consequences.**
- The paper states that results are for 4-bit models and do not generalise to full
  precision.
- A full-precision side check on a few families with one model stays available
  afterwards, reported separately and never pooled with the main runs.
- The research question is about small models on hardware people actually have, so
  4-bit is arguably the setting rather than a defect. What it limits is the claim's
  reach, not its validity.

---

## ADR-007 — The "16 of 189 specs" claim does not apply at our pin

**Status:** Accepted 2026-11-05, with two checks still open

**Context.** The claim threatened about 6 hours of dataset rebuilding, which would
have had to happen before the freeze. `prereg/exclusions.yaml` excludes 4
known-bad tasks plus `verina_basic_70`, leaving 184 eligible; if the claim named
tasks outside that list, the list would have to grow.

The source is arXiv:2604.16584 section 5.2, which lists 16 VERINA specification
issues. All 16 were fixed upstream by VERINA PR #17, commit `75c46698`, an
ancestor of our pinned `66b3ce5`. For the 15 tasks not already excluded, the specs
in `data/families/` match the pinned `task.lean` exactly and differ from it just
before the fix.

**Decision.** No new exclusions. `data/` is not rebuilt. Record the check and the
reference in `deviations.md`.

**Consequences.**
- `exclusions.yaml` is unchanged and 184 tasks stay eligible. The pilot does not
  need re-examining.
- **Two checks must close before the freeze.** Skim arXiv:2605.23772 ("Isomorphism
  Is Not Enough"), which reportedly finds VERINA issues at an unknown task list
  and is *not* the source of "16". And confirm the ancestry on the Ada checkout:
  ```
  git -C third_party/verina merge-base --is-ancestor 75c46698 66b3ce5
  ```
  The whole decision rests on that ancestry holding.
- Reference [14] in the proposal should be completed with authors and arXiv ID.

---

## Appendix A — text for `prereg/deviations.md`

Write all seven before the freeze, so the git timestamp proves the order.

> **Gate and shaping (ADR-001).** The screening gate passed on condition T
> coverage: basic 35.6%, advanced 5.0%, overall 22.3%, against the >=20% threshold
> in requirements R2, read against <state which figure>. No tiering rule promoting
> S to co-primary exists in the repository, so R2 was applied as written. S remains
> a mechanism study and the confirmatory family stays at four tests, Holm alpha/4.

> **Bug pool (ADR-002).** Natural bugs cover 32 of 114 `main` families, below the
> pre-registered minimum of 60, so the pre-registered fallback pool
> `natural + mutant` applies. Mutants are reported separately.

> **Time cap (ADR-003).** `max_infer_s` raised from 240 to 600 on <date>, before
> the freeze. `max_total_tokens` unchanged at 48000; it never bound, the highest
> observed being 35,668. Reason: the 240 s cap stopped 5 of 42 qwen3.5-4b
> condition-B runs and 0 of 42 condition-C runs, so it was not condition-neutral.
> Per-condition pilot truncation counts: 4B B 5/42, A 1/42, BP 1/42, Cplain 1/42,
> C 0/42, Bhammer 0/42; 2B 0 of 252. The pilot ran under the old cap and is not
> comparable to the main study. `results/power_note.md` was estimated under the old
> cap, so its C vs B figures are mildly optimistic. Stop rule: if
> `stop_reason == "infer_time"` exceeds 1% of runs in any condition during `main`,
> halt and report before continuing.

> **C versus BP (ADR-004).** C vs BP is underpowered by the fixed size of VERINA
> (327 main families needed against 114 available; unreachable under the
> pessimistic scenario). A tie is reported as equal success without proof writing,
> together with cost per repair and the power figures.

> **Bhammer go/no-go (ADR-005, decided <date>, before the freeze, from the pilot
> cost estimate only).** Bhammer runs for the primary models (qwen3.5-2b,
> qwen3.5-4b), 3 seeds, on the main split, unconditionally, as the last GPU job
> after the held-out run. The commitment does not depend on any main or held-out
> result. If it does not run, the reason is a resource constraint and is reported
> as one. It uses the same frozen checkout, model files and llama.cpp build as the
> main study, and is reported whatever it shows, labelled exploratory and never
> pooled with B. Pilot cost: 1.73 h of inference for 84 runs, about 23% of the five
> main conditions; estimated about 10 GPU hours on the main split.

> **Quantisation and serving (ADR-006).** All models are 4-bit GGUF, built by
> llama.cpp commit `162e2bb` and served through llama.cpp rather than LM Studio as
> designed. bf16 does not fit the 11 GB 1080 Ti. Hashes are in
> `results/ada_model_hashes.txt`. No repository code was changed. Results are for
> 4-bit models and do not generalise to full precision.

> **"16 of 189 specifications" claim (ADR-007, checked <date>, before the
> freeze).** The source is arXiv:2604.16584 section 5.2. All 16 issues were fixed
> upstream by VERINA PR #17 (commit `75c46698`), an ancestor of our pinned
> `66b3ce5`. For the 15 tasks not already excluded, the specs in `data/families/`
> match the pinned `task.lean` exactly. No exclusions were added and the dataset
> was not rebuilt.

## Appendix B — where the chat and the repository disagreed

| Chat | Repository | Impact |
|---|---|---|
| "20-40% tier, so S co-primary" | R2 has one threshold, >=20%, no tiers | Material. A fifth test would have moved Holm to alpha/5 and invalidated the power note |
| "we're at 35.6%" | that is the *basic* tier; overall is 22.3% | Minor. Both clear the gate |
| "natural bugs are only 56" | the rule counts families; `main` has 32 of 60 | Minor. Same conclusion, different number to record |
| "raise to 96000 tokens and 1800 s" | the token cap never bound; 1800 s costs the same as 600 s | Minor. Tokens dropped from ADR-003; 600 s chosen over 1800 s |

Also: `context/HANDOVER.md:150` has a stray `V`. Cosmetic.
