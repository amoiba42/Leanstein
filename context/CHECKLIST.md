# Checklist: carrying Leanstein forward

> **Superseded for execution (2026-11-05).** The study was not run on Ada. Every step, from the dataset to the
> analysis, was rerun from scratch on the IREL server (RTX PRO 6000 Blackwell, one 48 GB MIG slice) under a second
> freeze. What was actually done is in `context/IREL_RUNS.md`; the reasons are in `prereg/deviations.md` R-1 to R-10.
> This document is kept as the record of the Ada plan.

From `context/HANDOVER.md` (2026-11-05) and `docs/final_architecture.md`.
Order matters. Each block is blocked by the one above it.

Status today: Phase 0 and the pilot are done and committed (504 pilot runs,
3455 attempts). All seven team decisions are settled and **the pre-registration
is frozen** (2026-11-05, digest `964f1983`, 19 files). The main study, held-out
run, analysis and write-up have not been started.

Update 2026-11-05: Ada account `gracy.garg` is set up with SSH key login. The
repo is copied to `~/Leanstein`, and elan, VERINA, uv and cmake are installed.
Waiting on the `Project/` folder (`ada_scripts/`) from Poojitha or Inesh before
the job scripts and setup jobs can start.

---

## 0. Orient (30 minutes, read only)

- [ ] `docs/final_proposal.md` — the living summary. Start here.
- [ ] `docs/final_architecture.md` — decisions, conditions, the diagram.
- [ ] `memory.md` — current state, agreed decisions, environment facts.
      Update it at the end of every work session.
- [ ] `README.md` — pipeline commands and repo map. Note its "nothing has been
      run yet" line is out of date; the pilot is done.
- [ ] `context/TEAM_DECISIONS.md` — the seven decisions as ADR-001 to ADR-007.
- [ ] `context/RUN_HANDOFF.md` — for whoever runs the study on Ada.

## A. Get access (about 2.5 hours, mostly waiting)

- [x] Get your own Ada account: username, Slurm account `research`, QoS `low`.
      Or ask Poojitha to share theirs, where everything is already installed.
      Done: own account `gracy.garg`, home `/home2/gracy.garg` (50 GB).
- [x] Get added to the private GitHub repo `amoiba42/Leanstein`.
- [ ] Ask Poojitha or Inesh for the `Project/` folder. **It is not in the repo and
      not on this machine.** It holds `TEAM_DECISIONS.md`, `DECISIONS_TO_CONFIRM.md`,
      `ada_scripts/` (all the job scripts and the `lms` stand-in) and
      `tools/budget_check.py`. Part A step 3 and Part D cannot start without it.
- [x] Make an SSH key and copy it to Ada. Never write the password anywhere.
      Keep the private key in `~/.ssh/`, never inside the repo folder.
- [x] Copy the repo to Ada with `git clone -c core.autocrlf=false`. Windows line
      endings hash differently, which breaks the freeze.
      Done another way: the laptop checkout (Linux, 0 CRLF files per
      `git ls-files --eol`) was rsynced to `~/Leanstein`, excluding `.git`,
      `context/` and `models/`. Ada has no GitHub access, so it cannot clone the
      private repo. `models/` was an unfinished old download and is not needed;
      `serve_setup` downloads the study models on Ada. A dry-run rsync showed no
      differences. From now on, treat the Ada copy as the one checkout and never
      replace its `prereg/` files after the freeze.

## B. Set up the machine (about 2 hours, mostly one long job)

- [ ] Fix your username inside the job scripts, and strip `\r` from them.
      Blocked: `~/ada_jobs` and `~/serve` do not exist yet. Needs `ada_scripts/`.
      Once copied to `~/ada_jobs`, also strip `\r` from `lms` and any `.sh`
      files, not only `*.sbatch`, then check `grep -rn poojitha ~/ada_jobs ~/serve/bin`
      prints nothing.
- [x] Install elan, clone VERINA at commit `66b3ce5`, install uv and cmake.
      Done: elan 4.2.4 (`~/.elan/bin`), VERINA at
      `66b3ce5014edafb20cb26b87c681e7f31847249f` in `~/Leanstein/third_party/verina`,
      uv 0.13.7 and cmake 4.4.4 in `~/.local/bin`. PATH is set in `.profile`,
      `.bash_profile` and `.bashrc`. `lean_env/lean-toolchain` is LF and reads
      `leanprover/lean4:v4.24.0`. The elan warning `getpwuid_r: couldn't get user
      data` is harmless.
- [ ] Run the four setup jobs one at a time, waiting for each:
      `mathlib_cache` (7 min), `pyenv_tests` (5 min, expect 95 and 24 passed),
      `serve_setup` (1.5 h, builds llama.cpp and downloads 6 models),
      `smoke` (4 min, expect `same_seed_same_text True`).
- [ ] Read every job log before moving on.
- [ ] Prove the setup works before trusting it:
      `uv run pytest -m "not lean and not llm"` (expect 95 passed),
      `uv run pytest -m lean` (expect 24 passed),
      `uv run ruff check prl tests`.
- [ ] **Do not run** `uv run prl tasks build`, `uv run prl hidden`, `uv run prl bugs` or `uv run prl splits`.
      Their output is already committed. Re-running changes the natural bugs.

## C. Decide the open questions (team, no running)

**All seven are settled, 2026-11-05.** See `context/TEAM_DECISIONS.md`, ADR-001
to ADR-007, with ready-to-paste `deviations.md` text in its Appendix A.

- [x] **Gate tiers / S co-primary (ADR-001).** Gate passed. S stays a mechanism
      study, so Holm stays alpha/4 and the power note stands.
- [x] **Bug pool (ADR-002).** Natural bugs cover 32 of 114 `main` families against
      a minimum of 60, so the fallback `natural + mutant` applies.
- [x] **Time cap (ADR-003).** `max_infer_s` 240 -> 600. `max_total_tokens` stays
      48000; it never bound.
- [x] **C vs BP framing (ADR-004).** A tie is reported with cost per repair and
      the power figures stated.
- [x] **Bhammer (ADR-005).** Runs unconditionally, as the last GPU job after the
      held-out run. No cutoff date.
- [x] **4-bit models (ADR-006).** Kept and recorded: 4-bit GGUF, llama.cpp
      `162e2bb`, hashes in `results/ada_model_hashes.txt`. Full precision rejected.
- [x] **The "16 specs" claim (ADR-007).** Source arXiv:2604.16584 §5.2; all 16
      fixed upstream before our pin. No exclusions, no rebuild.

- [x] **arXiv:2605.23772 checked 2026-11-05.** "Isomorphism Is Not Enough" is
      mostly about CLEVER. Its Appendix A names 6 erroneous VERINA entries
      (`verina_basic_40`, `_104`, `verina_advanced_10`, `_12`, `_15`, `_44`, via
      issue #16), all fixed by the same PR #17, two already excluded. Nothing to
      add.
- [x] **Ancestry confirmed 2026-11-05** on a full clone at
      `third_party/verina` (gitignored, pinned detached at `66b3ce5`):
      `merge-base --is-ancestor 75c46698 66b3ce5` exits **0**, and
      `git diff --name-status 75c4669 66b3ce5 -- datasets/` is **empty**, so no
      dataset file changed between the fix and the pin.

## D. Freeze — DONE 2026-11-05

- [x] `max_infer_s` 240 -> 600 in `prereg/study.yaml` (ADR-003).
      `max_total_tokens` left at 48000.
- [x] All seven decisions written into `prereg/deviations.md`; the Bhammer
      `_pending_` line is gone.
- [x] Committed before the freeze, so the decisions are timestamped ahead of it.
- [x] `uv run prl freeze --note "team decisions of 2026-11-05 (ADR-001 to ADR-007)"`
      → digest `964f19836f224d10`, 19 files, `2026-11-05T16:05:56+0530`.
- [x] Verified: `freeze_status()` returns `True []`.
- [x] `prereg/FREEZE.json` committed.

The freeze hashes every file under `prereg/` **except** `FREEZE.json` and
`deviations.md` (`prl/prereg.py:10`), so the log can still be added to. Nothing
else under `prereg/` changes again, and `--allow-unfrozen` is never passed for
`main` or `heldout`. A mismatch makes `prl run` exit 2 with `REFUSING TO RUN:`,
so a mistake here fails loudly.

## E to H — handed off, not tracked here

Blocks E (main study), F (held-out), G (analysis) and H (hand audit and
write-up) are run by the teammate doing the GPU work.
**`context/RUN_HANDOFF.md` is the document for them** and is the only place the
run procedure lives: the freeze rule and how the tooling enforces it, making
their own `~/ada_jobs`, the six `.sbatch` files to create and what to change in
each, run order, the two stop conditions, analysis, and copying results back.

Deliberately not repeated here. Two copies of the same commands drift apart, and
the handoff is the one the person running them will actually read.

What stays yours after the handoff: chasing `Project/ada_scripts/`, which is
still the one thing blocking every Ada job, and committing results when they come
back. The `prereg/` writes and the freeze are done.

---

## Risks worth knowing before block C

**C vs BP is underpowered.** `results/power_note.md` says you have 114 main
families. C vs BP needs 327 under the point estimate and is unreachable under the
pessimistic one; power at what you have is 0.278 for qwen3.5-2b and 0.000 for
qwen3.5-4b. C vs B is fine (power 1.000 at the point estimate for 2b). VERINA is
fixed, so more families is not an option. This becomes a stated limitation, and it
should shape what the paper claims about BP.

**The pilot is not a result.** 504 runs, 0 infrastructure failures. The 26% vs 0%
numbers are a pilot, not a finding. It also ran under the old 240 s cap, so it is
not comparable to the main study at 600 s and must never be pooled with it.

**Natural bugs fell short.** 32 of 114 `main` families carry a natural bug,
against a pre-registered minimum of 60, so the fallback pool applies. The 56 often
quoted is the instance count, not the family count the rule uses. Pre-registered,
so it is fine, but it must be reported (ADR-002).

**Two different environments.** `README.md` describes the laptop setup: Windows,
LM Studio, CUDA engine. Ada is Linux and serves the same GGUF files through
llama.cpp with the `lms` stand-in. Model hashes are in
`results/ada_model_hashes.txt`. The difference is already a recorded deviation,
but do not mix runs from the two setups in one study.

**The laptop GPU is shared.** `memory.md` says model experiments run only when
the GPU is idle and the user gives the go-ahead. The main study belongs on Ada.

**Known open bugs** (`HANDOVER.md` §8), none blocking:
- `prl/analysis/report.py:61` uses `~` on a bool; breaks in Python 3.16.
- `uv run prl tasks check` crashes when `runs/phase0/` is missing.
