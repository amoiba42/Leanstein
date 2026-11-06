"""Hold idle memory on our MIG slice so it does not look free to other users. Uses no compute.

Holds 1 GiB blocks until about KEEP_FREE GiB is left. While any file `serve/loading-*` exists (bin/lms creates it
while a model loads), every block is released so the model can load; growth resumes 20 s after the last load.
Stop with: tmux kill-session -t prl_vram (memory is returned when the process exits).
"""
import ctypes
import glob
import os
import sys
import time

# Pin to our slice ourselves; never rely on the caller's environment (GPU 0 belongs to someone else).
SLICE = "MIG-def14cbb-599b-58f4-9cef-4befe9ff8506"
os.environ["CUDA_VISIBLE_DEVICES"] = SLICE

KEEP_FREE = float(os.environ.get("KEEP_FREE_GB", "4"))
GIB = 1 << 30
J = "/scratch/inesh/irel_jobs"
rt = ctypes.CDLL("/usr/local/cuda-13.1/lib64/libcudart.so")


def mem_info():
    free, total = ctypes.c_size_t(), ctypes.c_size_t()
    rt.cudaMemGetInfo(ctypes.byref(free), ctypes.byref(total))
    return free.value / GIB, total.value / GIB


blocks: list[ctypes.c_void_p] = []
last_load = 0.0
rt.cudaFree(ctypes.c_void_p(0))  # create the context
n = ctypes.c_int()
rt.cudaGetDeviceCount(ctypes.byref(n))
_, total = mem_info()
if n.value != 1 or not 40 < total < 50:  # the 2g.48gb slice reports about 47.4 GiB
    sys.exit(f"refusing: sees {n.value} device(s) with {total:.1f} GiB, expected only our 48 GB slice")
print(f"pinned to {SLICE}: {total:.1f} GiB", flush=True)
while True:
    loading = glob.glob(f"{J}/serve/loading-*")
    if loading:
        last_load = time.time()
        while blocks:
            rt.cudaFree(blocks.pop())
    elif time.time() - last_load > 20:
        free, _ = mem_info()
        if free > KEEP_FREE + 1.2:
            p = ctypes.c_void_p()
            if rt.cudaMalloc(ctypes.byref(p), ctypes.c_size_t(GIB)) == 0:
                blocks.append(p)
                continue
        elif free < KEEP_FREE - 0.5 and blocks:
            rt.cudaFree(blocks.pop())
            continue
    time.sleep(1)
