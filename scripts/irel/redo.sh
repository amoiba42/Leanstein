#!/bin/bash
# Full pre-freeze pipeline on IREL (RTX PRO 6000 Blackwell, MIG 2g.48gb), from scratch, in the study checkout.
# Stops after the pilot and the power note; the gate check and the new freeze are done by hand.
set -uo pipefail
. /scratch/inesh/irel_jobs/env.sh
cd $REPO
LW="--lean-workers 6"
step() { echo "==== $(date '+%F %T') START $*"; "$@"; local s=$?; echo "==== $(date '+%F %T') END exit=$s $*"; [ $s = 0 ] || { echo "REDO_FAILED at: $*"; exit 1; }; }
echo "==== GPU: $(nvidia-smi --query-gpu=name,driver_version --format=csv,noheader | head -1); slice $CUDA_VISIBLE_DEVICES; llama $(cat /scratch/inesh/llama.cpp/COMMIT); repo $(git rev-parse --short HEAD)"
export PRL_LMSTUDIO_URL=http://127.0.0.1:1234
step uv run prl env
step uv run prl $LW tasks build
step uv run prl $LW tasks check --tests visible
step uv run prl $LW hidden
# GPU work (probes, natural bugs) beside CPU work (mutants)
( step uv run prl $LW probe compile --models qwen3.5-2b,qwen3.5-4b
  step uv run prl $LW probe determinism --models qwen3.5-2b,qwen3.5-4b
  step uv run prl $LW bugs natural --run-workers 8 ) > /scratch/inesh/irel_jobs/logs/redo_gpu.log 2>&1 &
gpu=$!
step uv run prl $LW bugs mutants
wait $gpu; gs=$?; cat /scratch/inesh/irel_jobs/logs/redo_gpu.log | grep "===="
[ $gs = 0 ] || { echo "REDO_FAILED in GPU branch"; exit 1; }
step uv run prl $LW bugs shaping
step uv run prl splits
lms unload --all
/scratch/inesh/irel_jobs/run_job.sh pilot 1234 -- --study pilot --split pilot --allow-unfrozen --seeds 11 --conditions A,B,BP,Bhammer,C,Cplain --run-workers 12 >> /scratch/inesh/irel_jobs/logs/pilot.log 2>&1
tail -1 /scratch/inesh/irel_jobs/logs/pilot.log | grep -q "exit=0" || { echo "REDO_FAILED in pilot"; exit 1; }
step uv run prl power --study pilot
echo "REDO_DONE (gate check and freeze next)"
