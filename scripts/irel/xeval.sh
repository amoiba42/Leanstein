#!/bin/bash
# Cross-evaluation (Lean only, CPU) for one or more studies; resumable.
. /scratch/inesh/irel_jobs/env.sh
cd /scratch/inesh/Leanstein
nice -n 10 uv run prl --lean-workers 6 crosseval --study "$1"
