# Run handoff: executing the Leanstein study

For whoever runs the main study, the held-out run and the analysis on Ada.

Written 2026-11-05. Everything before this point is done: Phase 0, the pilot, the
power note, and all seven pre-freeze team decisions. What is left is execution.

Read sections 1 and 2 before touching anything. They contain the one mistake that
cannot be undone.

---

## 1. What you are picking up

Leanstein asks whether small language models produce more *verified* Lean 4
repairs when they fix only the code and a fixed tactic portfolio proves the
specification (condition **C**), rather than writing proofs themselves (**B**,
and **BP** = portfolio first, then the model's proof). The benchmark is VERINA,
189 tasks, pinned at commit `66b3ce5014edafb20cb26b87c681e7f31847249f`, 184
eligible.

The study is pre-registered and **the freeze has already happened**, on
2026-11-05, digest `964f1983`, 19 files. The contents of `prereg/` are fixed and
the tooling refuses to run `main` or `heldout` against a modified `prereg/`. You
will not need to freeze anything.

Your job is blocks E, F and G below: about 3.5 days of GPU, then a few hours of
CPU analysis. You do not make design decisions. All seven are settled and
recorded in `context/TEAM_DECISIONS.md` as ADR-001 to ADR-007.

## 2. The rule that can ruin the study

**Every `main` and `heldout` run must see the same `prereg/` bytes that were
hashed at the freeze.**

How it is enforced, so you know what you are looking at:

- `prl freeze` writes `prereg/FREEZE.json`, holding a SHA-256 of every file under
  `prereg/` **except** `FREEZE.json` and `deviations.md`, plus a combined digest,
  a timestamp and the git commit.
- Every `prl run` on split `main` or `heldout` re-hashes `prereg/` and compares.
  On any mismatch it prints `REFUSING TO RUN:` and exits 2.

So you cannot corrupt the study silently; you will get a hard error. Two
consequences worth knowing:

- **`prereg/deviations.md` is deliberately not hashed.** It is the log, not an
  input. Adding to it later is allowed and expected.
- **Line endings matter.** CRLF and LF hash differently. If you clone on Windows,
  use `git clone -c core.autocrlf=false`. Work in WSL or on Linux if you can.

Never pass `--allow-unfrozen` for `main` or `heldout`. It exists for the pilot.

## 3. Before you start

1. **Get the frozen commit.** Clone or pull `amoiba42/Leanstein` so that
   `prereg/FREEZE.json` is present. Ada has no GitHub access, so copy from your
   laptop:
   ```
   git clone -c core.autocrlf=false git@github.com:amoiba42/Leanstein.git
   cd Leanstein && rsync -a --exclude .git --exclude context/ ./ YOURUSER@ada-gw1.iiit.ac.in:Leanstein/
   ```
2. **Confirm the freeze is intact** on the Ada copy, before anything else:
   ```
   cd ~/Leanstein
   uv run python -c "from prl.prereg import freeze_status; ok,diffs,d=freeze_status(); print(ok, diffs, d[:16])"
   ```
   Expect exactly:
   ```
   True [] 964f19836f224d10
   ```
   That digest is the study's pre-registration, taken 2026-11-05 over 19 files.
   A different digest means your `prereg/` is not the frozen one, almost always
   line endings. Anything other than `True []`: stop and ask. Do not "fix" it by
   editing `prereg/`.
3. **Confirm the environment works.**
   ```
   uv run pytest -m "not lean and not llm"    # expect 95 passed
   uv run pytest -m lean                      # expect 24 passed
   uv run prl env                             # Lean smoke test, model list
   ```
4. **Do not run** `prl tasks build`, `prl hidden`, `prl bugs ...` or `prl splits`.
   Their output is committed. Re-running changes the natural bugs and invalidates
   the dataset the freeze was taken against.

## 4. Make your own `~/ada_jobs`

`ada_jobs` is just a folder in your Ada home holding the Slurm job scripts
(`.sbatch`) and their logs. Not a tool, not a package. It exists only in
Poojitha's account, at `/home2/poojitha.j/ada_jobs`, and Ada accounts are
personal, so **your account is empty and you make your own**. Budget about 2.5
hours, almost all of it waiting on jobs.

Never write an Ada password into a file, a script or a chat message. Use SSH keys.

1. Get `Project/ada_scripts/` from Poojitha or Inesh. It is **not in the
   repository**. It holds the setup `.sbatch` files, `pilot.sbatch`, the `lms`
   llama.cpp stand-in, and `tools/budget_check.py`.
2. Copy it into a new folder and make it yours:
   ```
   rsync -a Project/ada_scripts/ YOURUSER@ada-gw1.iiit.ac.in:ada_jobs/
   ssh YOURUSER@ada-gw1.iiit.ac.in
   cd ~/ada_jobs && sed -i 's/poojitha\.j/YOURUSER/g' *.sbatch && sed -i 's/\r$//' *.sbatch *.sh lms
   mkdir -p ~/serve/bin && cp ~/ada_jobs/lms ~/serve/bin/lms && chmod +x ~/serve/bin/lms
   grep -rn poojitha ~/ada_jobs ~/serve/bin        # must print nothing
   ```
   The `sed` for `\r` has to cover `lms` and any `.sh`, not only `*.sbatch`.
3. Run the four setup jobs **one at a time**, reading each log before the next:
   `mathlib_cache` (7 min), `pyenv_tests` (5 min, expect 95 and 24 passed),
   `serve_setup` (1.5 h, builds llama.cpp and downloads six models), `smoke`
   (4 min, expect `same_seed_same_text True`). Read with
   `tail -40 ~/ada_jobs/<name>_<jobid>.out`.

Run Lean and the models inside sbatch jobs, never on the login node. One GPU job
at a time.

### Your account's Slurm settings

`-A research` in the copied scripts is the allocation the compute is billed to.
If yours differs, change that line. It has no effect on results.

QoS `low` matters only for what it guarantees, and a higher QoS is fine. What the
study needs is: enough VRAM for 4-bit models (the largest, `goedel-code-prover-8b`
Q4_K_M, needs a few GB, so almost anything clears it); a job time limit above
about 48 hours, since the main run is ~44 and `low` allows 4 days; and above all
**the same GPU model for every run in the study, including Bhammer weeks later**.
llama.cpp output can differ across GPU architectures even at a fixed seed, and
mixing two setups inside one study is the thing the design forbids. A slower card
also means more time-cap truncation, which can trip the 1% stop rule in §8.

Nothing in the run outputs currently records which GPU was used, so put this line
near the top of every job script. Then the card is in every log and "same
hardware throughout" is checkable rather than assumed:

```
nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv,noheader
```

### What `~/ada_jobs` must contain

After copying `Project/ada_scripts/` across, `~/ada_jobs` holds the setup jobs
and `pilot.sbatch`. The study jobs do not exist yet: you create them, one per
run, by copying `pilot.sbatch` and changing four things. Six new files:

| File | `-J` | `-t` | Replaces the `prl run` line with |
|---|---|---|---|
| `main_primary.sbatch` | `main_primary` | `2-00:00:00` | `--study main --split main` |
| `main_gemma.sbatch` | `main_gemma` | `12:00:00` | `--study main --split main --models gemma-4-e4b-it --conditions B,BP,C --seeds 11` |
| `main_goedel.sbatch` | `main_goedel` | `12:00:00` | `--study main --split main --models goedel-code-prover-8b --conditions A,B --seeds 11` |
| `main_shaping.sbatch` | `main_shaping` | `12:00:00` | `--study main-shaping --split main --kinds shaping --conditions S,Splain` |
| `heldout.sbatch` | `heldout` | `1-00:00:00` | `--study heldout --split heldout --conditions B,BP,C` |
| `main_bhammer.sbatch` | `main_bhammer` | `1-00:00:00` | `--study main --split main --conditions Bhammer` |

Every one of them also needs `--lean-workers 6 --run-workers 4` on that line, and
a distinct `-o` log path so the jobs do not overwrite each other's output.

The four changes, and nothing else: `-J`, `-o`, `-t`, and the `prl run` line.
Leave the partition, account, CUDA exports and the model-server startup block
exactly as `pilot.sbatch` has them. That block launches llama.cpp through
`~/serve/bin/lms` and is easy to get subtly wrong; copy it verbatim rather than
rewriting it.

A finished script should look like this. Check it against `pilot.sbatch` and
prefer `pilot.sbatch` wherever the two differ, since it is the version that has
actually run:

```bash
#!/bin/bash
#SBATCH -J main_primary
#SBATCH -o /home2/YOURUSER/ada_jobs/main_primary_%j.out
#SBATCH -A research
#SBATCH -p <same partition as pilot.sbatch>
#SBATCH --gres=gpu:1
#SBATCH -c 8
#SBATCH --mem=24G
#SBATCH -t 2-00:00:00

set -euo pipefail
export CUDA_HOME=/data3/u22/cuda-12.4
export PATH="$CUDA_HOME/bin:$HOME/.local/bin:$HOME/.elan/bin:$PATH"
export LD_LIBRARY_PATH="$CUDA_HOME/lib64:${LD_LIBRARY_PATH:-}"

# --- model server startup: copy this block verbatim from pilot.sbatch ---

cd "$HOME/Leanstein"
uv run prl run --study main --split main --lean-workers 6 --run-workers 4
```

`-c 8 --mem=24G` is deliberate. QoS `low` allows 10 CPUs and 32 GB per user and
counts memory against the CPU limit, so asking for more leaves the job pending
with `QOSMaxCpuPerUserLimit` forever. `-t` may not exceed 4 days.

Before submitting anything, strip carriage returns from the files you created and
check no one else's username survived:

```
cd ~/ada_jobs && sed -i 's/\r$//' *.sbatch
grep -rn poojitha ~/ada_jobs ~/serve/bin      # must print nothing
```

Submit one job, wait for it to finish, read its log, then submit the next.

## 5. Block E — main study (about 3 to 3.5 days of GPU)

Submit them **one after another**. You have one GPU, and a second job will
contend for it.

```
sbatch main_primary.sbatch     # about 44 h
sbatch main_gemma.sbatch
sbatch main_goedel.sbatch
sbatch main_shaping.sbatch
```

The first is the long one: primary models, conditions A,B,BP,C,Cplain, 3 seeds,
114 families.

`--run-workers 4` and `--lean-workers 6` are already the right numbers. Raising
them does not help: inference is 75% of the work and all of it goes through one
GPU, and 6 is the hard cap on Lean workers in the code.

## 6. Block F — held-out run (about 12 hours)

```
sbatch heldout.sbatch
```

Run it **once**. Never pool it with `main`; it is analysed separately.

## 7. Bhammer, last

```
sbatch main_bhammer.sbatch
```

About 10 GPU hours. ADR-005 commits to running it **unconditionally**, as the
last GPU job, after the held-out run. The commitment was made before the freeze
and does not depend on any result.

If the schedule genuinely does not allow it, do not run it and say so, in those
words: it was pre-registered to run and time did not permit. Do not skip it
because the main results make it look unnecessary; that choice is not available
and would not survive review.

It must use the same frozen checkout, the same model files and the same
llama.cpp build as the main study, with nothing rebuilt in between.

## 8. While a job runs

```
squeue -u YOURUSER
tail -3 ~/Leanstein/runs/main/driver.log
wc -l ~/Leanstein/runs/main/runs.jsonl
```

The driver prints progress every ten runs, so silence for a few minutes is
normal.

**Two stop conditions. Both mean stop and report, not work around:**

1. Infrastructure failure rate above 5%. The pilot had 0 of 504.
2. `stop_reason == "infer_time"` above 1% of runs in any condition. This is the
   guard from ADR-003, pre-registered with the cap change. Check with:
   ```
   python3 -I -c "import json,collections;rows=[json.loads(l) for l in open('runs/main/runs.jsonl')];c=collections.Counter((r['condition'],r['stop_reason']) for r in rows);print(c)"
   ```

A stopped or killed job restarts with the **same command**. The driver skips
finished runs and logs `N already complete, M to run`.

## 9. Block G — analysis (CPU only, a couple of hours)

```
uv run prl crosseval --study main,heldout
uv run prl analyze --study main,main-shaping
uv run prl analyze --study heldout --out results/heldout
uv run prl audit --study main
python3 -I Project/tools/budget_check.py runs/main/runs.jsonl
```

`analyze` on `heldout` writes to a separate directory on purpose. The held-out
split is a replication and is never pooled with `main`.

`audit` writes `results/audit/sample.csv`: 10% of successes plus every success
carrying a degeneracy flag. A **person** fills in whether each is a real repair,
then `uv run prl audit --merge`.

## 10. Sending results back

```
rsync -a --exclude raw/ YOURUSER@ada-gw1.iiit.ac.in:Leanstein/runs/ runs/
rsync -a YOURUSER@ada-gw1.iiit.ac.in:Leanstein/results/ results/
```

`runs/*/raw/` holds raw prompts and model outputs and is gitignored; everything
else under `runs/` and `results/` is committed as a research artifact. Commit by
hand. Then update `memory.md` with where the study stands.

## 11. Things that will bite you

| Symptom | Cause and fix |
|---|---|
| `REFUSING TO RUN: ...` | `prereg/` differs from `FREEZE.json`. Usually line endings. Do not edit `prereg/`; ask |
| `invalid toolchain name` from elan | CRLF in `lean_env/lean-toolchain`. `sed -i 's/\r$//'` the `lean_env` config files |
| Job pending with `QOSMaxCpuPerUserLimit` | Asked for too many CPUs; memory counts too. Use `-c 8 --mem=24G` |
| `sbatch` rejects `u22-cpu` | Use `-p u22` for CPU jobs |
| `uv sync` has no pytest | `uv sync --extra dev` |
| `nvcc` or `module load` missing in a job | `export CUDA_HOME=/data3/u22/cuda-12.4` and prepend its `bin`/`lib64`. Already in the scripts |
| `cmake` not found on compute nodes | `uv tool install cmake`, once |
| `prl tasks check` crashes, no `runs/phase0` | `mkdir -p runs/phase0`. Only matters if you re-run it, which you should not |

Two known open bugs, neither blocking: `prl/analysis/report.py:61` applies `~` to
a bool and will break on Python 3.16; `prl tasks check` crashes when
`runs/phase0/` is missing.

## 12. Rules that protect the study

- Never change prompts, tactic lists or models after seeing results.
- Never edit anything under `prereg/` after the freeze, except `deviations.md`,
  which is the log and is excluded from the hash by design.
- Never mix runs from two different setups in one study. The laptop setup
  (Windows, LM Studio) and Ada (Linux, llama.cpp with the `lms` stand-in) are
  different environments; the difference is already a recorded deviation.
- The pilot is a pilot. Its 26% versus 0% numbers are not a finding, and it ran
  under the old 240 s cap, so it is not comparable to the main study at 600 s.
- Report Bhammer whatever it shows, labelled exploratory, never pooled with B.

## 13. Where to look

| What | Where |
|---|---|
| The seven decisions, with evidence | `context/TEAM_DECISIONS.md` (ADR-001 to ADR-007) |
| Ordered task list and status | `context/CHECKLIST.md` |
| Original handover from Poojitha | `context/HANDOVER.md` |
| Study design and conditions | `docs/final_architecture.md`, `docs/final_proposal.md` |
| Power analysis | `results/power_note.md` |
| Current state between sessions | `memory.md` |
| Job scripts, `lms`, budget tool | `Project/ada_scripts/` — **not in the repo**, ask Poojitha or Inesh |
