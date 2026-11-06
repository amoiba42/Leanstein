#!/bin/bash
# goedel is pre-claimed so worker 2 takes Bhammer right after gemma; this runs goedel on lane 1 once main primary or Bhammer is done, whichever frees a lane first.
J=/scratch/inesh/irel_jobs
while [ ! -f $J/logs/main_primary.done ] && [ ! -f $J/logs/main_bhammer.done ]; do sleep 60; done
echo "$(date "+%F %T") start main_goedel on port 1236 (first free lane)" >> $J/logs/lanes.log
$J/run_job.sh main_goedel 1236 -- --study main-goedel --split main --models goedel-code-prover-8b --conditions A,B --seeds 11 --run-workers 12 >> $J/logs/main_goedel.log 2>&1
if tail -1 $J/logs/main_goedel.log | grep -q "exit=0"; then touch $J/logs/main_goedel.done; echo "$(date "+%F %T") main_goedel done" >> $J/logs/lanes.log; else echo "$(date "+%F %T") main_goedel FAILED" >> $J/logs/lanes.log; fi
