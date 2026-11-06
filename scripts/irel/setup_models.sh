#!/bin/bash
# The six 4-bit GGUFs pinned in results/ada_model_hashes.txt, laid out where prl/models/registry.py looks.
set -euo pipefail
. /scratch/inesh/irel_jobs/env.sh
ROOT=/scratch/inesh/lmstudio_models
mkdir -p $ROOT ~/.lmstudio
[ -L ~/.lmstudio/models ] || ln -s $ROOT ~/.lmstudio/models
get() { # repo file sha
  mkdir -p "$ROOT/$1"; f="$ROOT/$1/$2"
  if [ ! -f "$f" ] || ! echo "$3  $f" | sha256sum -c --status; then
    curl -L --fail --retry 5 -C - -o "$f" "https://huggingface.co/$1/resolve/main/$2"
  fi
  echo "$3  $f" | sha256sum -c
}
get unsloth/gemma-4-E4B-it-GGUF gemma-4-E4B-it-Q4_K_M.gguf 85a896a047553e842f25297ee5b031d64ff30147d9c4af17b1e4b394cd1fab87
get mradermacher/Goedel-Code-Prover-8B-GGUF Goedel-Code-Prover-8B.Q4_K_M.gguf dcbcf7209f945801579e59b7b410a01c48a7fc55759dccac0806fe412fecac18
get lmstudio-community/Qwen3.5-0.8B-GGUF Qwen3.5-0.8B-Q4_K_M.gguf f5b14da98939b60bbe1019a964eba656407e1e0b64f1fe3003ff6d650e93bfec &
get lmstudio-community/Qwen3.5-2B-GGUF Qwen3.5-2B-Q4_K_M.gguf 0bfe35afc9f05b7fac3fa04925e051ac7939a42a8a17ea11afc99701bea826cc &
get lmstudio-community/Qwen3.5-4B-GGUF Qwen3.5-4B-Q4_K_M.gguf 25082a7dd3776cc3c741c6347d3bd04523f05796607b3fbc32fa3a25dfa1418c &
get lmstudio-community/Qwen3.5-9B-GGUF Qwen3.5-9B-Q4_K_M.gguf cd76ec205963b3b33350093e6904d9de16c4e666fd104e1f632d25c7f15f2a13 &
wait
echo SETUP_MODELS_DONE
