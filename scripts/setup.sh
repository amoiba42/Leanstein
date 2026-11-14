#!/usr/bin/env bash
# One-command setup from a fresh clone (NFR-REP-2). Linux, macOS or WSL. Run from anywhere:
#
#     bash scripts/setup.sh            # everything: Python env, VERINA, Lean + Mathlib, checks
#     bash scripts/setup.sh --no-lean  # skip Lean and Mathlib (about 5 GB); enough for the unit tests
#                                      # and for regenerating results/ with `prl analyze`
#
# It only performs the steps listed under "Setup" in the README, in order, and is safe to run again.
# It never touches prereg/, data/, runs/ or results/. Models are not downloaded (see scripts/irel/setup_models.sh).
set -euo pipefail

VERINA_URL=https://github.com/sunblaze-ucb/verina.git
VERINA_COMMIT=66b3ce5014edafb20cb26b87c681e7f31847249f

WITH_LEAN=1
for arg in "$@"; do
  case "$arg" in
    --no-lean) WITH_LEAN=0 ;;
    -h|--help) sed -n '2,9p' "$0"; exit 0 ;;
    *) echo "unknown option: $arg" >&2; exit 2 ;;
  esac
done

cd "$(dirname "$0")/.."
export PATH="$HOME/.local/bin:$HOME/.elan/bin:$PATH"
step() { printf '\n== %s\n' "$*"; }

step "1/5 uv (Python package manager)"
command -v uv >/dev/null || curl -LsSf https://astral.sh/uv/install.sh | env UV_NO_MODIFY_PATH=1 sh
uv --version

step "2/5 Python 3.12 environment from uv.lock"
uv sync --extra dev --frozen

step "3/5 VERINA benchmark at the pinned commit"
if [ ! -d third_party/verina/.git ]; then
  mkdir -p third_party
  git clone --quiet "$VERINA_URL" third_party/verina
fi
git -C third_party/verina checkout --quiet "$VERINA_COMMIT"
test "$(git -C third_party/verina rev-parse HEAD)" = "$VERINA_COMMIT"
echo "VERINA at $VERINA_COMMIT"

if [ "$WITH_LEAN" = 1 ]; then
  step "4/5 Lean $(cat lean_env/lean-toolchain), Mathlib cache and the PrlRepl server"
  if ! command -v elan >/dev/null; then
    curl -sSfL https://raw.githubusercontent.com/leanprover/elan/master/elan-init.sh -o "${TMPDIR:-/tmp}/elan-init.sh"
    sh "${TMPDIR:-/tmp}/elan-init.sh" -y --no-modify-path --default-toolchain none
  fi
  (
    cd lean_env
    # the downloads are large and occasionally drop; retry a few times
    for i in 1 2 3 4 5; do lake exe cache get && break; echo "cache retry $i"; sleep 30; done
    lake build prlrepl
  )
else
  step "4/5 Lean skipped (--no-lean)"
fi

step "5/5 Checks"
uv run python -c "
import sys
from prl.prereg import freeze_status
ok, diffs, digest = freeze_status()
print('pre-registration freeze:', 'OK' if ok else 'MISMATCH', digest[:16], diffs)
sys.exit(0 if ok else 1)"
uv run pytest -q -m "not lean and not llm"
if [ "$WITH_LEAN" = 1 ]; then
  uv run prl env
fi

printf '\nSetup complete. Next: see "Tests" and "Pipeline" in the README.\n'
