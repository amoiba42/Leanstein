#!/bin/bash
# Installs the pieces relayed from the laptop (GitHub downloads are throttled on this server).
# Usage: install_relayed.sh lean|llama|mathlib
set -euo pipefail
. /scratch/inesh/irel_jobs/env.sh
X=/scratch/inesh/tmp/xfer
case $1 in
lean)
  cat $X/lean.part.* > $X/lean.tar.zst
  echo "b14f5e5159219dd1a1956c3b806813319f5e94ccd5bdfd56f54520609a5bb5ec  $X/lean.tar.zst" | sha256sum -c
  T=$ELAN_HOME/toolchains/leanprover--lean4---v4.24.0
  rm -rf $T $ELAN_HOME/toolchains/*.lock; mkdir -p $T
  tar --zstd -xf $X/lean.tar.zst -C $T --strip-components=1
  cd $REPO/lean_env && lean --version ;;
llama)
  rm -rf /scratch/inesh/llama.cpp; mkdir -p /scratch/inesh/llama.cpp
  tar -xzf $X/llama.cpp-162e2bb.tar.gz -C /scratch/inesh/llama.cpp --strip-components=1
  echo 162e2bb2e42a0bbf6f9c2d3d8a9eb3cc40b4a4ea > /scratch/inesh/llama.cpp/COMMIT
  ls /scratch/inesh/llama.cpp | head -5 ;;
mathlib)
  cat $X/ml.part.* > $X/ml.tar
  tar -xf $X/ml.tar -C /scratch/inesh/.cache
  ls /scratch/inesh/.cache/mathlib | wc -l ;;
pkgs)
  cat $X/pk.part.* > $X/pk.tar
  cd $REPO/lean_env && rm -rf .lake/packages && mkdir -p .lake && tar -xf $X/pk.tar -C .lake
  # laptop checkouts may carry CRLF; restore exact git bytes so Mathlib cache hashes match
  for p in .lake/packages/*; do git -C $p -c core.autocrlf=false reset -q --hard HEAD && echo "$(basename $p) $(git -C $p rev-parse --short=10 HEAD) $(git -C $p status --short | wc -l)"; done ;;
esac
echo INSTALL_$1_DONE
