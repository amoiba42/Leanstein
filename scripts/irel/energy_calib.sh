#!/bin/bash
# Run the post-hoc energy calibration (D-4) for every study model, then a 24-slot check for qwen3.5-4b.
. /scratch/inesh/irel_jobs/env.sh
cd "$J"
for m in qwen3.5-2b qwen3.5-4b gemma-4-e4b-it goedel-code-prover-8b; do
  python3 -I "$J/energy_calib.py" "$m" 12 || echo "CALIB_FAILED $m"
done
python3 -I "$J/energy_calib.py" qwen3.5-4b 24 || echo "CALIB_FAILED qwen3.5-4b p24"
echo CALIB_DONE
