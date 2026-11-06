#!/bin/bash
# Runs the study jobs one after another on our slice (main, held-out, shaping, Gemma, Goedel and Bhammer, in that order;
# Bhammer last, after held-out, as team decision 5 requires). Re-running skips jobs already marked done and resumes
# a partly finished one (the driver skips completed runs).
# A file /scratch/inesh/irel_jobs/STOP makes the queue stop before the next job.
set -uo pipefail
J=/scratch/inesh/irel_jobs
W="--run-workers 12"
run() { # name -- args
  local name=$1; shift
  [ -f $J/logs/$name.done ] && { echo "skip $name (done)"; return 0; }
  [ -f $J/STOP ] && { echo "STOP file present, not starting $name"; exit 0; }
  $J/run_job.sh $name 1234 "$@" >> $J/logs/$name.log 2>&1
  if tail -1 $J/logs/$name.log | grep -q "exit=0"; then touch $J/logs/$name.done; echo "$(date '+%F %T') $name done"; else echo "$(date '+%F %T') $name FAILED, queue stopped"; exit 1; fi
}
run main_primary -- --study main --split main $W
run heldout      -- --study heldout --split heldout --conditions B,BP,C $W
run main_shaping -- --study main-shaping --split main --kinds shaping --conditions S,Splain $W
run main_gemma   -- --study main --split main --models gemma-4-e4b-it --conditions B,BP,C --seeds 11 $W
run main_goedel  -- --study main --split main --models goedel-code-prover-8b --conditions A,B --seeds 11 $W
run main_bhammer -- --study main --split main --conditions Bhammer $W
echo "$(date '+%F %T') QUEUE_DONE"
