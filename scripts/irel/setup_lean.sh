#!/bin/bash
# Lean 4.24.0 toolchain, Mathlib cache and the PrlRepl server. Retries the flaky downloads.
set -euo pipefail
. /scratch/inesh/irel_jobs/env.sh
cd $REPO/lean_env
for i in 1 2 3 4 5; do lean --version && break; echo "toolchain retry $i"; sleep 20; done
for i in 1 2 3 4 5; do lake exe cache get && break; echo "cache retry $i"; sleep 30; done
lake build prlrepl
ls -la .lake/build/bin
echo SETUP_LEAN_DONE
