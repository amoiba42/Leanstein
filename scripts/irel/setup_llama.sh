#!/bin/bash
# Builds llama.cpp at the study's pinned commit 162e2bb (source relayed as a tarball; see install_relayed.sh), CUDA sm_120.
set -euo pipefail
. /scratch/inesh/irel_jobs/env.sh
command -v cmake || uv tool install cmake
cd /scratch/inesh/llama.cpp
echo "commit $(cat COMMIT)"
cmake -B build -G Ninja -DGGML_CUDA=ON -DCMAKE_CUDA_ARCHITECTURES=120 -DLLAMA_CURL=OFF -DCMAKE_BUILD_TYPE=Release -DCMAKE_CUDA_COMPILER=$CUDA_HOME/bin/nvcc -DLLAMA_BUILD_NUMBER=0 -DLLAMA_BUILD_COMMIT=162e2bb
cmake --build build --target llama-server llama-cli -j 32
$LLAMA_BIN/llama-server --version
echo SETUP_LLAMA_DONE
