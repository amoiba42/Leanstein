#!/bin/bash
# Final analysis on IREL once the study runs are complete. Cross-evaluation is resumable, so this only catches up.
set -uo pipefail
. /scratch/inesh/irel_jobs/env.sh
cd /scratch/inesh/Leanstein
step() { echo "==== $(date "+%F %T") START $*"; "$@"; echo "==== $(date "+%F %T") END exit=$? $*"; }
step uv run prl --lean-workers 8 crosseval --study main,main-gemma,heldout
step uv run prl analyze --study main,main-shaping,main-gemma,main-goedel,main-bhammer
step uv run prl analyze --study heldout --out results/heldout
step uv run prl audit --study main
echo FINALIZE_DONE
