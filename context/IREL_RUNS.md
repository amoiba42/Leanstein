# How the study was actually run: IREL, 2026-11-05

`RUN_HANDOFF.md` describes running on Ada. The study ran on the IREL GPU server instead, and **every step was
redone there from scratch**: dataset (task checks, hidden tests, natural bugs, mutants, shaping instances,
splits), probes, pilot, power note, a second freeze, every study run and the analysis. This file records what was
done, so the run can be reproduced and the paper's setup section checked. The reasons are in
`prereg/deviations.md`, section "Restart on the IREL server" (R-1 to R-10).

## Hardware and software

| What | Value |
|---|---|
| Server | IREL `inesh@10.4.25.56`, Ubuntu 24.04, 64 cores, 503 GB RAM |
| GPU | NVIDIA RTX PRO 6000 Blackwell Max-Q, **GPU 1, MIG device 0, 2g.48gb** (UUID `MIG-def14cbb-599b-58f4-9cef-4befe9ff8506`); every job is pinned to it with `CUDA_VISIBLE_DEVICES` |
| Driver / CUDA | 595.99.02 / CUDA 13.1 toolkit |
| llama.cpp | commit `162e2bb2e42a0bbf6f9c2d3d8a9eb3cc40b4a4ea` (the study's pinned build), CUDA sm_120 |
| Models | the six 4-bit GGUFs, SHA-256 checked against `results/ada_model_hashes.txt` (Hugging Face sources found by hash) |
| Lean | 4.24.0, Mathlib v4.24.0, packages at the `lake-manifest.json` revisions |
| Repo | `/scratch/inesh/Leanstein` at `bd0091f`, cloned with `core.autocrlf=false`. The first freeze checked `True [] 964f19836f224d10` there before the restart; the second freeze is taken on the server |
| Tests on the server | 96 unit + 24 Lean, all passing (96 after the H-1 flag test) |

The job scripts are in `scripts/irel/` (copied from `/scratch/inesh/irel_jobs`). `bin/lms` replaces the missing
`ada_scripts/lms`: it serves a GGUF through `llama-server` with reasoning off and 8192 tokens of context per slot.

## Things that differed from the handoff

- `--lean-workers` is a top-level flag: `prl --lean-workers 6 run ...`. The handoff's `prl run ... --lean-workers 6`
  is rejected by argparse.
- The code expects Lean in `~/.elan`; on IREL `~/.elan` links to `/scratch/inesh/.elan`.
- `third_party/verina` (gitignored) must exist for the tests; it was copied at `66b3ce5`.
- GitHub downloads are throttled on the server, so the Lean toolchain, llama.cpp source, Lean packages and
  Mathlib cache were relayed from the laptop and checked by hash or git revision.

## Measurements before the study

- Same-instance timing check (55 pilot runs, qwen3.5-2b, 4 workers, another user's job on the slice):
  225 tok/s aggregate on IREL against 269 on Ada; Lean 5x faster. 0 infrastructure failures.
- Throughput by concurrency (qwen3.5-4b): 91 tok/s at 4 parallel requests, 168 at 8, 217 at 16.
- With the slice to ourselves and two jobs of 12 requests each, per-request decoding was 66–81 tok/s,
  about the Ada pilot's 67 tok/s. That is where the slice saturates, so two lanes is the maximum.

## Job layout

| Lane | Jobs | Study folder |
|---|---|---|
| 1 (`queue.sh`, then `worker.sh 1`) | main primary, then jobs from the shared list | `runs/main` |
| 2 (`lane.sh B`, then `worker.sh 2`) | held-out, shaping, then jobs from the shared list | `runs/heldout`, `runs/main-shaping` |
| shared list | gemma, goedel, Bhammer (only after held-out) | `runs/main-gemma`, `runs/main-goedel`, `runs/main-bhammer` |

All jobs use `--run-workers 12` and 6 Lean workers.

## Pre-freeze pipeline on IREL (`scripts/irel/redo.sh`)

Started 2026-11-05 19:12, from an empty `data/`, `runs/` and `cache/`: `prl env` (model registry and hashes),
`tasks build`, `tasks check --tests visible`, `hidden`, then on the GPU the compile and determinism probes and
`bugs natural`, with `bugs mutants` on the CPU at the same time, then `bugs shaping`, `splits`, the pilot (504
runs, `--run-workers 12`) and `power --study pilot`. The gate check and `prl freeze` follow by hand.

The first attempt under the first freeze (about 560 study runs and a 55-run timing check) was deleted
unanalysed; its logs are kept on the server in `/scratch/inesh/irel_jobs/logs/attempt1/`.

## Analysis commands, once every job is done

```
uv run prl crosseval --study main,main-gemma,heldout
uv run prl analyze --study main,main-shaping,main-gemma,main-goedel,main-bhammer
uv run prl analyze --study heldout --out results/heldout
uv run prl analyze --study pilot --out results/pilot
uv run prl audit --study main
python paper/make_results.py results results/heldout results/pilot
```

## How the study went (finished 2026-11-06 11:49)

| Job | Runs | Finished | Infrastructure failures |
|---|---|---|---|
| main (primary, 5 conditions x 2 models) | 6,930 | 11:21 | 0 |
| heldout | 1,710 | 02:18 | 0 |
| main-shaping (S, S-plain) | 1,068 | 04:39 | 0 |
| main-gemma | 693 | 07:29 | 0 |
| main-bhammer | 1,386 | 10:37 | 1 (resumed, see below) |
| main-goedel | 462 | 11:49 | 0 |
| **total** | **12,249** | about 14.7 h after the freeze | 1 (0.008%) |

No run hit the 600 s inference cap and no stop rule fired. The one infrastructure failure
(`verina_basic_98__mut__arith__1`, qwen3.5-4b, seed 37, Bhammer) was a temporary-file rename collision in the
shared verification cache; it never charged the model's budget, and resuming the job completed the run.

Final analysis (`scripts/irel/finalize.sh`, 11:50 to 11:55): cross-evaluation catch-up (1,508 attempts), then
the two analyses and the audit sample. The audit crashed on a pandas name clash and lost a column; both bugs
were fixed (deviation D-2) and the same 333-run sample was drawn again. The audit was filled in by Claude, with
every row marked "checked by Claude, awaiting human confirmation" (D-3). The energy meter turned out to read
physical GPU 0, not our slice, so its figures were withdrawn (D-1). The freeze still checks
`True [] 3f2744e1...` on the server after the fixes, since `prl/` is not part of the freeze.

Results are in `results/` (main), `results/heldout`, `results/pilot` and `results/audit`. The paper is
`paper/main.pdf`, built from `paper/results.tex` (hand-written texts) and `paper/results_tables.tex` (generated).

## Energy calibration (deviation D-4), 2026-11-06 14:45-15:30

`scripts/irel/energy_calib.sh` served each model again on the slice with the study settings (llama-server
`162e2bb`, 12 slots x 8192 tokens, temperature 0.7, top-p 0.95, reasoning off) on port 1290 and replayed prompts
the model had received in the study (`runs/*/raw`). It sampled `power.draw.instant` of physical GPU 1 every 100 ms.
Each of three cycles per model has an idle window (40 s), a prefill-only workload (48 prompts), another idle
window and a full workload (48 prompts, up to 1,536 tokens). Marginal energy is power above the adjacent idle
mean. A last run checked qwen3.5-4b at 24 slots. Raw data and the log are in `results/energy_calib/`.
`scripts/irel/energy_estimate.py results/energy_calib results` writes `results/rq5_energy_estimate.{csv,md}` and
`results/energy_coefficients.csv`.

| Model | J per completion token | J per prompt token |
|---|---|---|
| qwen3.5-2b | 0.141 (0.133-0.147) | 0.008 |
| qwen3.5-4b | 0.258 (0.221-0.290); 0.42 at 24 slots | 0.024 |
| gemma-4-e4b-it | 0.252 (0.242-0.263) | 0.021 |
| goedel-code-prover-8b | 0.392 (0.341-0.439) | 0.027 |
