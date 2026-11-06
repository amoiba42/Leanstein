"""Aggregate decode throughput on our slice for N concurrent requests (operational check, not a study run)."""
import json, os, subprocess, sys, time, urllib.request
from concurrent.futures import ThreadPoolExecutor
model = sys.argv[1]
port = 1288
env = dict(os.environ, PRL_LMSTUDIO_URL=f"http://127.0.0.1:{port}")
prompt = ("Here is a Lean 4 function with a bug. Explain the bug and write a corrected version.\n" + "def f (xs : List Nat) : Nat := xs.foldl (fun a b => a + b) 1\n" * 40)
def one(i):
    body = {"model": model, "messages": [{"role": "user", "content": prompt + f"\nVariant {i}."}], "temperature": 0.7,
            "top_p": 0.95, "max_tokens": 600, "seed": 1000 + i, "reasoning_effort": "none"}
    req = urllib.request.Request(f"http://127.0.0.1:{port}/v1/chat/completions", json.dumps(body).encode(), {"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=900) as r:
        return json.load(r)["usage"]["completion_tokens"]
for n in (4, 8, 16):
    subprocess.run(["lms", "load", model, "--context-length", "8192", "--parallel", str(n), "--identifier", model], env=env, check=True, capture_output=True)
    t = time.time()
    with ThreadPoolExecutor(n) as ex:
        toks = sum(ex.map(one, range(2 * n)))
    dt = time.time() - t
    print(f"{model} parallel={n}: {toks} tokens in {dt:.0f}s = {toks/dt:.0f} tok/s aggregate", flush=True)
subprocess.run(["lms", "unload", "--all"], env=env, capture_output=True)
