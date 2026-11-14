# scripts/irel — how the study was run

Every step of the study (dataset, probes, pilot, power note, freeze, all study runs, analysis) ran on the IREL
GPU server at IIIT Hyderabad with these scripts. On the server they live in `/scratch/inesh/irel_jobs`; the
repository at `/scratch/inesh/Leanstein` is the frozen checkout. Differences from the original plan are recorded
in [`prereg/deviations.md`](../../prereg/deviations.md) (R-1 to R-10, D-1 to D-7).

| File | What |
|---|---|
| env.sh | paths, CUDA 13.1, pins every job to our slice MIG-def14cbb-... (GPU 1, MIG device 0, 2g.48gb) |
| setup_env.sh, setup_lean.sh | uv, Python env, Lean 4.24.0, Mathlib cache, PrlRepl, freeze check |
| setup_llama.sh | llama.cpp at the study's pinned commit 162e2bb, CUDA sm_120 |
| setup_models.sh | the six GGUFs, sha256-checked against results/ada_model_hashes.txt |
| install_relayed.sh | installs Lean, llama.cpp and Mathlib pieces downloaded elsewhere (GitHub is throttled on the server) |
| bin/lms | stand-in for LM Studio's `lms` CLI, backed by `llama-server` (reasoning off, 8192 tokens of context per slot) |
| run_job.sh NAME PORT -- ARGS | one `prl run` job with its own llama-server port; logs GPU and commits at the top |
| redo.sh | the full pre-freeze pipeline from an empty [`data/`](../../data/), [`runs/`](../../runs/), `cache/`, up to the pilot and power note |
| queue.sh, lane.sh, worker.sh, goedel_after_main.sh | job order across the two lanes (see "Job layout") |
| check.py, gate.py | stop-rule check and pilot-gate computation (read only) |
| xeval.sh, finalize.sh | cross-evaluation and final analysis |
| energy_calib.sh, energy_calib.py, energy_estimate.py | post-hoc energy calibration and estimate (D-4) |

Jobs run in tmux sessions named `prl_<job>`. Re-running the same command resumes: the driver skips finished runs
and logs `N already complete, M to run`.

## Environment

| What | Value |
|---|---|
| Server | Ubuntu 24.04, 64 cores, 503 GB RAM |
| GPU | NVIDIA RTX PRO 6000 Blackwell Max-Q, GPU 1, MIG device 0, 2g.48gb (`MIG-def14cbb-599b-58f4-9cef-4befe9ff8506`), pinned with `CUDA_VISIBLE_DEVICES` |
| Driver / CUDA | 595.99.02 / CUDA 13.1 |
| llama.cpp | commit `162e2bb2e42a0bbf6f9c2d3d8a9eb3cc40b4a4ea`, CUDA sm_120 |
| Models | six 4-bit GGUFs, SHA-256 in [`results/ada_model_hashes.txt`](../../results/ada_model_hashes.txt) |
| Lean | 4.24.0, Mathlib v4.24.0, packages at the `lake-manifest.json` revisions |
| Tests on the server | 96 unit + 24 Lean, all passing |

Setup notes: `--lean-workers` is a top-level flag (`prl --lean-workers 6 run ...`); the code expects Lean in
`~/.elan` (a link to `/scratch/inesh/.elan` on the server); [`third_party/verina`](../../third_party/verina/) must exist at `66b3ce5` for the
tests; the Lean toolchain, llama.cpp source, Lean packages and Mathlib cache were downloaded elsewhere and checked
by hash or git revision. If elan reports `invalid toolchain name`, the `lean_env` config files have Windows line endings
(`sed -i 's/\r$//'` them).

## Operating rules

- Every `main` and `heldout` run must see the same [`prereg/`](../../prereg/) bytes that were hashed at the freeze. `prl freeze`
  writes [`prereg/FREEZE.json`](../../prereg/FREEZE.json) (SHA-256 of every file under [`prereg/`](../../prereg/) except `FREEZE.json` and `deviations.md`,
  plus a combined digest); every confirmatory run re-hashes and prints `REFUSING TO RUN:` on any mismatch.
  `deviations.md` is the log and is deliberately not hashed.
- Line endings change the hash: clone with `git clone -c core.autocrlf=false`.
- `--allow-unfrozen` exists for the pilot only; never for `main` or `heldout`.
- Stop and report (do not work around) if more than 5% of runs end in an infrastructure failure, or if
  `stop_reason == "infer_time"` exceeds 1% of runs in any condition ([`check.py`](check.py)).
- Never mix runs from different setups in one study; never change prompts, tactics or models after seeing results.

## Measurements before the study

- Throughput by concurrency (qwen3.5-4b): 91 tok/s at 4 parallel requests, 168 at 8, 217 at 16.
- With two jobs of 12 requests each, per-request decoding was 66–81 tok/s; the slice saturates there, so two
  lanes is the maximum.

## Job layout

| Lane | Jobs | Study folder |
|---|---|---|
| 1 ([`queue.sh`](queue.sh), then [`worker.sh 1`](worker.sh)) | main (primary), then jobs from the shared list | [`runs/main`](../../runs/main/) |
| 2 ([`lane.sh B`](lane.sh), then [`worker.sh 2`](worker.sh)) | held-out, shaping, then jobs from the shared list | [`runs/heldout`](../../runs/heldout/), [`runs/main-shaping`](../../runs/main-shaping/) |
| shared list | Gemma, Goedel, Bhammer (only after held-out) | [`runs/main-gemma`](../../runs/main-gemma/), [`runs/main-goedel`](../../runs/main-goedel/), [`runs/main-bhammer`](../../runs/main-bhammer/) |

All jobs use `--run-workers 12` and 6 Lean workers.

## Run record

| Job | Runs | Infrastructure failures |
|---|---|---|
| main (primary, 5 conditions × 2 models × 3 seeds) | 6,930 | 0 |
| heldout | 1,710 | 0 |
| main-shaping (S, S-plain) | 1,068 | 0 |
| main-gemma | 693 | 0 |
| main-bhammer | 1,386 | 1 (resumed) |
| main-goedel | 462 | 0 |
| **total** | **12,249** (about 14.7 h after the freeze) | 1 (0.008%) |

No run hit the 600 s inference cap and no stop rule fired. The one infrastructure failure
(`verina_basic_98__mut__arith__1`, qwen3.5-4b, seed 37, Bhammer) was a temporary-file rename collision in the
shared verification cache; it never charged the model's budget, and resuming the job completed the run. The pilot
was 492 runs (41 instances × 6 conditions × 2 primary models, seed 11).

## Analysis commands

```
uv run prl crosseval --study main,main-gemma,heldout
uv run prl analyze --study main,main-shaping,main-gemma,main-goedel,main-bhammer
uv run prl analyze --study heldout --out results/heldout
uv run prl analyze --study pilot --out results/pilot
uv run prl audit --study main
```

Results are in [`results/`](../../results/) (main), [`results/heldout`](../../results/heldout/), [`results/pilot`](../../results/pilot/) and [`results/audit`](../../results/audit/). The audit is an
automated pre-screen of 333 sampled successes; a human audit is pending (D-3).

## Energy calibration (D-4)

[`energy_calib.sh`](energy_calib.sh) served each model again on the slice with the study settings (llama-server `162e2bb`,
12 slots × 8192 tokens, temperature 0.7, top-p 0.95, reasoning off) and replayed prompts the model had received in
the study (`runs/*/raw`), sampling `power.draw.instant` of physical GPU 1 every 100 ms. Each of three cycles per
model has an idle window (40 s), a prefill-only workload (48 prompts), another idle window and a full workload
(48 prompts, up to 1,536 tokens); marginal energy is power above the adjacent idle mean. A last run checked
qwen3.5-4b at 24 slots. [`energy_estimate.py results/energy_calib results`](energy_estimate.py) writes
`results/rq5_energy_estimate.{csv,md}` and [`results/energy_coefficients.csv`](../../results/energy_coefficients.csv).

| Model | J per completion token | J per prompt token |
|---|---|---|
| qwen3.5-2b | 0.141 (0.133–0.147) | 0.008 |
| qwen3.5-4b | 0.258 (0.221–0.290); 0.42 at 24 slots | 0.024 |
| gemma-4-e4b-it | 0.252 (0.242–0.263) | 0.021 |
| goedel-code-prover-8b | 0.392 (0.341–0.439) | 0.027 |
