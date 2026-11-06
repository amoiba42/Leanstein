#!/bin/bash
# Two lanes on our slice, each with its own llama-server port.
#   lane A (port 1234): waits for main_primary (run by queue.sh), then gemma, goedel, and Bhammer last,
#                       which also waits for held-out to finish (team decision 5).
#   lane B (port 1235): held-out, then shaping. These write to their own study folders, so they can run
#                       beside lane A; everything with --study main stays in lane A, one at a time.
# A file /scratch/inesh/irel_jobs/STOP_LANES stops a lane before its next job.
set -uo pipefail
J=/scratch/inesh/irel_jobs
W="--run-workers 12"
waitfor() { while [ ! -f $J/logs/$1.done ]; do sleep 60; done; }
run() { # name port -- args
  local name=$1 port=$2; shift 2
  [ -f $J/logs/$name.done ] && { echo "skip $name (done)"; return 0; }
  [ -f $J/STOP_LANES ] && { echo "STOP_LANES present, not starting $name"; exit 0; }
  echo "$(date '+%F %T') start $name on port $port"
  $J/run_job.sh $name $port "$@" >> $J/logs/$name.log 2>&1
  if tail -1 $J/logs/$name.log | grep -q "exit=0"; then touch $J/logs/$name.done; echo "$(date '+%F %T') $name done"; else echo "$(date '+%F %T') $name FAILED, lane stopped"; exit 1; fi
}
case $1 in
A)
  waitfor main_primary
  run main_gemma   1234 -- --study main --split main --models gemma-4-e4b-it --conditions B,BP,C --seeds 11 $W
  run main_goedel  1234 -- --study main --split main --models goedel-code-prover-8b --conditions A,B --seeds 11 $W
  waitfor heldout
  run main_bhammer 1234 -- --study main --split main --conditions Bhammer $W
  echo "$(date '+%F %T') LANE_A_DONE" ;;
B)
  run heldout      1235 -- --study heldout --split heldout --conditions B,BP,C $W
  run main_shaping 1235 -- --study main-shaping --split main --kinds shaping --conditions S,Splain $W
  echo "$(date '+%F %T') LANE_B_DONE" ;;
esac
