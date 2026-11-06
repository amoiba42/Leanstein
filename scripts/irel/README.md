# irel_jobs — the IREL equivalent of ~/ada_jobs

Runs the Leanstein study on the IREL server (inesh@10.4.25.56) instead of Ada.
Everything here is outside the repository; the repo at /scratch/inesh/Leanstein is the frozen checkout.

| File | What |
|---|---|
| env.sh | paths, CUDA 13.1, pins every job to our slice MIG-def14cbb-... (GPU 1, MIG device 0, 2g.48gb) |
| setup_env.sh, setup_lean.sh | uv, Python env, Lean 4.24.0, Mathlib cache, PrlRepl, freeze check |
| setup_llama.sh | llama.cpp at the study's pinned commit 162e2bb, CUDA sm_120 |
| setup_models.sh | the six GGUFs, sha256-checked against results/ada_model_hashes.txt |
| bin/lms | stand-in for LM Studio's lms CLI, backed by llama-server (the original ada_scripts/lms was unavailable) |
| run_job.sh NAME PORT -- ARGS | one prl run job with its own llama-server port; logs GPU and commits at the top |
| logs/ | one log per job |

Jobs run in tmux sessions named prl_<job>. Re-running the same command resumes; the driver skips finished runs.
Differences from Ada are recorded in prereg/deviations.md.
