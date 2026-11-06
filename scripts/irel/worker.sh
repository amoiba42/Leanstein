#!/bin/bash
# Pulls jobs from a shared list once the lane it replaces has finished, so the GPU always runs two lanes.
#   worker.sh 1 : starts after main_primary (lane A) is done, port 1236
#   worker.sh 2 : starts after main_shaping (lane B) is done, port 1237
# Each job is claimed with mkdir (atomic), so two workers never run the same job.
# Jobs that write to runs/main while main primary runs get their own study folder (main-gemma, main-goedel,
# main-bhammer); the analysis reads several study folders together. Bhammer starts only after held-out (ADR-005).
# The file /scratch/inesh/irel_jobs/STOP_LANES stops a worker before its next job.
set -uo pipefail
J=/scratch/inesh/irel_jobs
W="--run-workers 12"
case $1 in 1) after=main_primary; port=1236 ;; 2) after=main_shaping; port=1237 ;; esac
while [ ! -f $J/logs/$after.done ]; do sleep 60; done
JOBS="main_gemma main_goedel main_bhammer"
deps() { case $1 in main_bhammer) echo heldout ;; *) echo "" ;; esac; }
args() { case $1 in
  main_gemma)   echo "--study main-gemma --split main --models gemma-4-e4b-it --conditions B,BP,C --seeds 11 $W" ;;
  main_goedel)  echo "--study main-goedel --split main --models goedel-code-prover-8b --conditions A,B --seeds 11 $W" ;;
  main_bhammer) echo "--study main-bhammer --split main --conditions Bhammer $W" ;;
  pilot_irel)   echo "--study pilot-irel --split pilot --conditions A,B,BP,Bhammer,C,Cplain --seeds 11 $W" ;;
esac; }
while true; do
  [ -f $J/STOP_LANES ] && { echo "STOP_LANES present, worker $1 exits"; exit 0; }
  picked=""; pending=0
  for j in $JOBS; do
    [ -f $J/logs/$j.done ] && continue
    d=$(deps $j); if [ -n "$d" ] && [ ! -f $J/logs/$d.done ]; then pending=1; continue; fi
    if mkdir $J/logs/$j.claim 2>/dev/null; then picked=$j; break; fi
  done
  if [ -z "$picked" ]; then
    [ $pending = 1 ] && { sleep 60; continue; }
    echo "$(date '+%F %T') worker $1: nothing left"; exit 0
  fi
  echo "$(date '+%F %T') worker $1 start $picked on port $port"
  $J/run_job.sh $picked $port -- $(args $picked) >> $J/logs/$picked.log 2>&1
  if tail -1 $J/logs/$picked.log | grep -q "exit=0"; then touch $J/logs/$picked.done; echo "$(date '+%F %T') $picked done";
  else echo "$(date '+%F %T') $picked FAILED, worker $1 stopped"; exit 1; fi
done
