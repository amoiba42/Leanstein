#!/bin/bash
# Usage: run_job.sh NAME PORT -- <prl run args...>
# One study job on our slice, with its own llama-server port. Re-running the same command resumes.
set -euo pipefail
NAME=$1; PORT=$2; shift 3
. /scratch/inesh/irel_jobs/env.sh
export PRL_LMSTUDIO_URL=http://127.0.0.1:$PORT
echo "==== $(date '+%F %T') job=$NAME port=$PORT host=$(hostname)"
nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv,noheader
nvidia-smi -L | grep MIG-def14cbb
echo "slice=$CUDA_VISIBLE_DEVICES llama=$(cat /scratch/inesh/llama.cpp/COMMIT) repo=$(git -C $REPO rev-parse --short HEAD)"
cd $REPO
status=0; uv run prl --lean-workers 6 run "$@" || status=$?

lms unload --all || true
echo "==== $(date '+%F %T') job=$NAME exit=$status"
