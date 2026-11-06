#!/bin/bash
# uv, elan/Lean, Python env, Mathlib cache, PrlRepl; then freeze check and tests.
set -euo pipefail
. /scratch/inesh/irel_jobs/env.sh
command -v uv || curl -LsSf https://astral.sh/uv/install.sh | env UV_NO_MODIFY_PATH=1 sh
command -v elan || (curl -sSfL https://raw.githubusercontent.com/leanprover/elan/master/elan-init.sh -o /tmp/elan-init.sh && sh /tmp/elan-init.sh -y --no-modify-path --default-toolchain none)
cd $REPO
uv sync --extra dev
cd lean_env && lake exe cache get && lake build prlrepl && cd ..
uv run python -c "from prl.prereg import freeze_status; ok,diffs,d=freeze_status(); print('FREEZE', ok, diffs, d[:16])"
echo SETUP_ENV_DONE
