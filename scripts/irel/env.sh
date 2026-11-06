# Source this in every job: . /scratch/inesh/irel_jobs/env.sh
export J=/scratch/inesh/irel_jobs
export REPO=/scratch/inesh/Leanstein
export ELAN_HOME=/scratch/inesh/.elan
export UV_CACHE_DIR=/scratch/inesh/.uvcache
export UV_PYTHON_INSTALL_DIR=/scratch/inesh/.uvpython
export CUDA_HOME=/usr/local/cuda-13.1
export PATH="$J/bin:$HOME/.local/bin:$ELAN_HOME/bin:$CUDA_HOME/bin:$PATH"
export LD_LIBRARY_PATH="$CUDA_HOME/lib64:${LD_LIBRARY_PATH:-}"
# Our slice only: GPU 1, MIG device 0, 2g.48gb. Never GPU 0 or the 24 GB slices.
export CUDA_VISIBLE_DEVICES=MIG-def14cbb-599b-58f4-9cef-4befe9ff8506
export PRL_LMSTUDIO_URL=http://127.0.0.1:1234
export LLAMA_BIN=/scratch/inesh/llama.cpp/build/bin
