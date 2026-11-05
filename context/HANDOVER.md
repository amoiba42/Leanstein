# Leanstein handover: what was done, what is left, how to run it

Written 2026-11-05. Read sections 1 to 3 first (5 minutes), then follow section 4 in order.
Never put an Ada password in any file, chat or script. Use SSH keys.

## 1. The project in one paragraph

Leanstein tests one question on the VERINA benchmark (189 Lean 4 tasks, pinned commit 66b3ce5): do small language
models (under 10B) get more *verified* repairs when they only fix the **code** and a fixed list of Lean tactics proves
the spec (condition **C**), compared with the model writing proofs itself (**B**, and **BP** = tactics first, then the
model writes a proof)? Success needs: compiles, locked theorem proved, only allowed axioms, integrity checks, visible
and hidden tests pass. The study is **pre-registered**: once `prl freeze` is run, nothing in `prereg/` may change.

## 2. What has been done (all on Ada, 4-bit models, one 1080 Ti GPU)

- Lean 4.24.0, Mathlib cache, verifier build, Python env, 119 tests pass (95 plain, 24 Lean).
- 189 tasks parsed, 184 eligible (5 excluded: 4 known-bad in `prereg/exclusions.yaml`, plus `verina_basic_70`).
- Tactic-only coverage (condition T): basic 35.6%, advanced 5.0%, overall 22.3%.
- Hidden tests built (184 families, most with 30 tests; `verina_basic_63` has 0).
- Bugs built: 56 natural (below the 60 the study needs, so the pre-registered fallback "natural + mutant" applies),
  316 mutants, 143 shaping instances. Splits: pilot 20 families, main 114, held-out 50.
- Pilot done: 504/504 runs, 0 infrastructure failures. It is a pilot only, not a result. Power note written.
- Six models downloaded and checked: Qwen3.5 0.8B, 2B, 4B, 9B, Gemma-4-E4B, Goedel-Code-Prover-8B (Q4_K_M GGUF).
- Everything above (data, logs, pilot, power note) is committed in the GitHub repo `amoiba42/Leanstein`.
- NOT done: the freeze, the main study, the held-out run, analysis, the hand audit, the write-up.

## 3. Where things are

| What | Where |
|---|---|
| Code, data, pilot results | GitHub repo `amoiba42/Leanstein` (private). Folders `data/`, `runs/`, `results/`, `prereg/` |
| Open team decisions | `Project/TEAM_DECISIONS.md` (outside the repo) |
| Older proposals for the decisions | `Project/DECISIONS_TO_CONFIRM.md` |
| All Ada job scripts + the `lms` stand-in | `Project/ada_scripts/` (outside the repo) |
| Budget check tool | `Project/tools/budget_check.py` |
| Raw model outputs of the pilot (not in git) | Poojitha's Ada account: `~/Leanstein/runs/pilot/raw` |
| The full setup that already works | Poojitha's Ada account: `~/Leanstein`, `~/serve`, `~/ada_jobs` |

## 4. Prerequisites (check every box before starting)

1. **Your own Ada account.** Ada accounts are personal. You need: a username, Slurm account `research`, QoS `low`.
   Login nodes: `ada-gw1.iiit.ac.in` or `ada-gw2.iiit.ac.in` (reachable from anywhere, no special wifi).
   (If Poojitha chooses to share their account instead, everything is already installed and you can skip to step 4.
   That is their decision, and the password must never be written down.)
2. **Limits under QoS `low` (per user):** 1 GPU, 10 CPUs, 32 GB RAM, 5 jobs, 4 days maximum per job. A job asking for
   more than this never starts (it shows `QOSMax...` in `squeue`). Ask for at most 8 CPUs and 28 GB.
3. **Disk:** 50 GB home. You need about 30 GB (models 20 GB, Lean/Mathlib 4 GB, runs a few GB).
4. **GitHub access** to the private repo `amoiba42/Leanstein` (ask Poojitha or Inesh).
5. **Do not use the separate GPU server for the main study.** It needs a specific wifi and was only discussed for a
   full-precision side check, not decided. If you ever use it, never run `sudo reboot` on it.
6. **Python 3.12 and uv:** the system Python on Ada is 3.9. `uv` installs its own 3.12 automatically.
7. **The one rule that can ruin the study:** run `prl freeze` and every `main`/`heldout` run on **the same checkout**.
   The freeze hashes the exact bytes of each `prereg/` file, and Windows (CRLF) and Linux (LF) files hash differently.
   On Ada, clone/copy once, never replace the files afterwards.

## 5. Steps (numbered, in order)

### Part A. Set up your own Ada account (about 2.5 hours, mostly waiting)

1. On your laptop, in a terminal: `ssh-keygen -t ed25519` (press Enter for all questions), then
   `ssh-copy-id YOURUSER@ada-gw1.iiit.ac.in` (type your Ada password once; if it says the password expired, change it
   when asked).
2. Copy the repo to Ada. On your laptop (replace YOURUSER):
   `git clone -c core.autocrlf=false https://github.com/amoiba42/Leanstein.git`
   (the `-c core.autocrlf=false` matters: it keeps Unix line endings, so the freeze hashes are stable)
   `cd Leanstein && rsync -a --exclude .git ./ YOURUSER@ada-gw1.iiit.ac.in:Leanstein/`
   (on Windows use WSL for this step, because `rsync` is not in plain cmd)
3. Copy the job scripts: `rsync -a Project/ada_scripts/ YOURUSER@ada-gw1.iiit.ac.in:ada_jobs/`
4. Log in: `ssh YOURUSER@ada-gw1.iiit.ac.in`. Then fix the username inside the scripts:
   `cd ~/ada_jobs && sed -i 's/poojitha\.j/YOURUSER/g' *.sbatch && sed -i 's/\r$//' *.sbatch`
   Also copy `lms` into place: `mkdir -p ~/serve/bin && cp ~/ada_jobs/lms ~/serve/bin/lms && chmod +x ~/serve/bin/lms`
5. Install Lean (elan) and the benchmark (login node, a few minutes):
   `curl https://raw.githubusercontent.com/leanprover/elan/master/elan-init.sh -sSf | sh -s -- -y --default-toolchain none`
   `git clone https://github.com/sunblaze-ucb/verina.git ~/Leanstein/third_party/verina`
   `git -C ~/Leanstein/third_party/verina checkout 66b3ce5014edafb20cb26b87c681e7f31847249f`
   `curl -LsSf https://astral.sh/uv/install.sh | sh` then `~/.local/bin/uv tool install cmake`
6. Submit the setup jobs one at a time and wait for each to finish (`squeue -u YOURUSER` shows nothing when done):
   `cd ~/ada_jobs && sbatch mathlib_cache.sbatch` (about 7 min)
   `sbatch pyenv_tests.sbatch` (about 5 min; expect "95 passed" and "24 passed")
   `sbatch serve_setup.sbatch` (about 1.5 hours: builds llama.cpp and downloads the 6 models)
   `sbatch smoke.sbatch` (about 4 min; expect all six models to answer, `same_seed_same_text True`)
7. Read each log: `tail -40 ~/ada_jobs/<name>_<jobid>.out`. If a job failed, see section 7.
8. **Do NOT run** `prl tasks build`, `prl hidden`, `prl bugs ...` or `prl splits`. Their output is already in the repo
   (`data/`). Re-running would overwrite it (the natural bugs come from a model and would differ).

### Part B. Before the freeze (team decisions, no running)

9. Get the team's answers to `TEAM_DECISIONS.md` (gate tiers, bug pool, time cap, C vs BP framing, Bhammer, 4-bit,
   the "16 specs" source). If the "16 specs" claim adds excluded tasks, data must be rebuilt first (about 6 hours).
10. Write each decision into `prereg/deviations.md`. If the time cap is raised, edit `max_total_tokens` and
    `max_infer_s` in `prereg/study.yaml` and log the old and new values and the pilot counts. Nothing else in `prereg/`.

### Part C. Freeze (once, on the Ada copy, after step 10)

11. `cd ~/Leanstein && ~/.local/bin/uv run prl freeze --note "team decisions of <date>"`
    This writes `prereg/FREEZE.json`. Copy it back to your laptop repo and commit it (together with `deviations.md` and
    `study.yaml`). After this, **never edit anything in `prereg/`**, or the main runs refuse to start.
    Never use `--allow-unfrozen` for `main` or `heldout`.

### Part D. Main study (about 3 to 3.5 days of GPU in total, one GPU job at a time)

12. Make job scripts from `pilot.sbatch` (copy it, rename, change `-J`, `-o`, `-t 2-00:00:00`, and replace the
    `uv run prl ... run ...` line). Submit them **one after another** (you only have 1 GPU). The commands, in order:
    - `prl run --study main --split main --run-workers 4` (2B and 4B, A,B,BP,C,Cplain, 3 seeds; about 44 hours)
    - `prl run --study main --split main --models gemma-4-e4b-it --conditions B,BP,C --seeds 11 --run-workers 4`
    - `prl run --study main --split main --models goedel-code-prover-8b --conditions A,B --seeds 11 --run-workers 4`
    - `prl run --study main-shaping --split main --kinds shaping --conditions S,Splain --run-workers 4`
    - optional, only if the team said yes: `prl run --study main --split main --conditions Bhammer`
    All of them also need `--lean-workers 6` before `run` (as in `pilot.sbatch`).
13. A stopped job can be restarted with the **same command**: the driver skips finished runs
    ("N already complete, M to run" in the log).
14. While it runs: `squeue -u YOURUSER`, `tail -3 ~/Leanstein/runs/main/driver.log`, and the count
    `wc -l ~/Leanstein/runs/main/runs.jsonl`.

### Part E. Held-out run (once, about 12 hours)

15. `prl run --study heldout --split heldout --conditions B,BP,C --lean-workers 6 --run-workers 4`
    Run it once. Never pool it with `main`.

### Part F. Analysis (CPU only, a couple of hours)

16. `prl crosseval --study main,heldout`, then `prl analyze --study main,main-shaping`, then
    `prl analyze --study heldout --out results/heldout`, then `prl audit --study main`.
17. Run `python3 -I Project/tools/budget_check.py ~/Leanstein/runs/main/runs.jsonl` and note how the runs ended.

### Part G. Hand audit and copy-back

18. A person fills in `results/audit/sample.csv` (is each success a real repair?), then `prl audit --merge`.
19. Copy results into the repo on your laptop (no `raw/`):
    `rsync -a --exclude raw/ YOURUSER@ada-gw1.iiit.ac.in:Leanstein/runs/ Leanstein/runs/`
    `rsync -a YOURUSER@ada-gw1.iiit.ac.in:Leanstein/results/ Leanstein/results/`
    Then commit and push (git is always done by a person).

## 6. Rules that protect the study

- Never change prompts, tactic lists or models after seeing pilot results to widen the gap.
- Never change `prereg/` after the freeze. Never mix runs from two different setups in one study.
- One Slurm GPU job at a time. Run Lean and models in sbatch jobs, never on the login node.
- Keep `prl tasks build/hidden/bugs/splits` outputs fixed (they are in git).
- Report the pilot as a pilot. The 26% vs 0% numbers are not a finding.
- The coverage numbers (35.6%) were seen before the gate rule. That is already disclosed in `deviations.md`.

## 7. Problems already met, and fixes

| Problem | Fix |
|---|---|
| `sbatch` says invalid account/partition for `u22-cpu` | use `-p u22` (CPU jobs work there) |
| Job stays pending with `QOSMaxCpuPerUserLimit` | asked for too many CPUs (memory counts too); use `-c 8 --mem=24G` |
| `invalid toolchain name` from elan | Windows line endings in `lean_env/lean-toolchain`; run `sed -i 's/\r$//'` on the lean_env config files |
| `uv sync` has no pytest | use `uv sync --extra dev` |V
| `prl tasks check` crashes with no `runs/phase0` | `mkdir -p runs/phase0` (only needed if you re-run it) |
| `module load` or `nvcc` not found inside a job | use the fixed path: `export CUDA_HOME=/data3/u22/cuda-12.4; export PATH=$CUDA_HOME/bin:$PATH; export LD_LIBRARY_PATH=$CUDA_HOME/lib64:$LD_LIBRARY_PATH` (already in the scripts) |
| `cmake` not found on compute nodes | `uv tool install cmake` once (already in step 5) |
| `ssh-copy-id` says password expired | log in once in a real terminal and change it |
| Monitor or `tail` shows no output for a long time | the driver prints progress every ~10 runs; check `driver.log` |

## 8. Known open issues (not fixed, outside what the team approved)

- `prl/analysis/report.py:61` uses `~` on a bool (DeprecationWarning, breaks in Python 3.16).
- `prl tasks check` crashes if `runs/phase0/` is missing (git does not track empty folders).
- The model client only speaks to LM Studio. On Ada this is bridged by `ada_scripts/lms` plus llama.cpp, so no repo
  code was changed. The models are 4-bit GGUF built by llama.cpp commit 162e2bb; hashes are in
  `results/ada_model_hashes.txt`. Record this as a deviation (4-bit, llama.cpp, not LM Studio).

---

## 9. Addendum, 2026-11-05 (added after handover; sections 1 to 8 are unchanged)

This document is kept as the record of what was handed over. What happened since:

- **The seven open decisions in section 5 step 9 are settled.** They are written
  up as Nygard ADRs in `context/TEAM_DECISIONS.md` (ADR-001 to ADR-007), with the
  evidence checked against the repository, and recorded in `prereg/deviations.md`.
- **The pre-registration is frozen.** 2026-11-05, digest `964f19836f224d10`, 19
  files. Steps 10 and 11 of this document are therefore complete. `prl freeze`
  excludes `FREEZE.json` and `deviations.md` from the hash, so the deviation log
  can still be added to after the freeze.
- **One `prereg/` value changed before the freeze:** `max_infer_s` 240 -> 600.
  The old cap stopped 11.9% of qwen3.5-4b condition-B runs and no condition-C
  runs, so it was not condition-neutral. `max_total_tokens` stays at 48000; it
  never bound.
- **The "16 specs" question in step 9 is closed.** All 16 issues from
  arXiv:2604.16584 §5.2 were fixed upstream by VERINA PR #17, verified as an
  ancestor of the pin; a second audit, arXiv:2605.23772, names 6 entries that the
  same PR also fixed. No exclusions added, no dataset rebuild.
- **Section 3 is out of date in one row.** `Project/TEAM_DECISIONS.md` was never
  received. Its contents were reconstructed from the team chat and checked
  against the repository. `Project/ada_scripts/` and `Project/tools/` are still
  outstanding and still block every Ada job.
- **The run procedure has moved.** Parts D to G of section 5 are superseded by
  `context/RUN_HANDOFF.md`, written for whoever runs the study on Ada: it assumes
  a fresh `~/ada_jobs`, lists the six `.sbatch` files to create, and carries the
  stop conditions. `context/CHECKLIST.md` tracks the remaining non-run work.
