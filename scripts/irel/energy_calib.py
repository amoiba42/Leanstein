#!/usr/bin/env python3
"""Post-hoc GPU energy calibration on our MIG slice (deviation D-4).

The study's energy meter read the wrong GPU (D-1), so per-condition GPU energy is estimated afterwards:
for each model we replay prompts the model actually received during the study (from runs/*/raw), at the
study's serving configuration (llama-server, 12 parallel slots, 8192 tokens per slot, same sampling),
and measure the *marginal* board power of physical GPU 1 over its idle baseline:

  per cycle:  idle window -> prefill workload (max_tokens=1) -> idle window -> full workload (max_tokens=1536)
  baseline for a workload = mean power of the idle windows right before and after it
  marginal energy E = integral of (P - baseline) dt over the workload window

Then J per prompt token b = E_prefill / prompt_tokens and J per completion token
a = (E_full - b * prompt_tokens_full) / completion_tokens_full. Other users' slices on GPU 1 add noise;
the adjacent idle windows and three cycles per model bound it. Static (idle) power is shared with other
tenants and is not attributed. Output: $J/energy/calib_<model>_p<parallel>.json
"""
import glob, json, os, random, subprocess, sys, threading, time, urllib.request
from concurrent.futures import ThreadPoolExecutor

J = os.environ["J"]
REPO = os.environ["REPO"]
PORT = 1290
os.environ["PRL_LMSTUDIO_URL"] = f"http://127.0.0.1:{PORT}"
OUT = f"{J}/energy"
os.makedirs(OUT, exist_ok=True)
STUDIES = ["main", "main-bhammer", "main-shaping", "main-gemma", "main-goedel", "heldout"]
N_PER = 48          # prompts per workload window
CYCLES = 3
IDLE_S = 40


class Power(threading.Thread):
    """Samples board power of physical GPU 1 every 100 ms (power.draw.instant)."""

    def __init__(self):
        super().__init__(daemon=True)
        self.samples = []  # (t, watts)
        self.p = subprocess.Popen(["nvidia-smi", "-i", "1", "--query-gpu=power.draw.instant",
                                   "--format=csv,noheader,nounits", "-lms", "100"],
                                  stdout=subprocess.PIPE, text=True)

    def run(self):
        for ln in self.p.stdout:
            try:
                self.samples.append((time.time(), float(ln.strip())))
            except ValueError:
                pass

    def window(self, t0, t1):
        return [(t, w) for t, w in self.samples if t0 <= t <= t1]

    def stop(self):
        self.p.terminate()


def integrate(s, base):
    e = 0.0
    for (t0, w0), (t1, w1) in zip(s, s[1:]):
        e += ((w0 + w1) / 2 - base) * (t1 - t0)
    return e


def mean(s):
    return sum(w for _, w in s) / len(s) if s else float("nan")


def prompts_for(model, n):
    runs = set()
    for st in STUDIES:
        p = f"{REPO}/runs/{st}/runs.jsonl"
        if os.path.exists(p):
            for ln in open(p):
                r = json.loads(ln)
                if r.get("model") == model:
                    runs.add(r["run_id"])
    files = [f for f in glob.glob(f"{REPO}/runs/*/raw/*/*.json") if os.path.basename(f).split("_")[0] in runs]
    random.Random(0).shuffle(files)
    out = []
    for f in files:
        try:
            m = json.load(open(f))["messages"]
        except Exception:
            continue
        out.append(m)
        if len(out) >= n:
            break
    return out


def call(model, messages, max_tokens, seed):
    body = {"model": model, "messages": messages, "temperature": 0.7, "top_p": 0.95, "max_tokens": max_tokens,
            "seed": seed, "stream": False, "reasoning_effort": "none"}
    req = urllib.request.Request(f"http://127.0.0.1:{PORT}/v1/chat/completions", json.dumps(body).encode(),
                                 {"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=1200) as r:
        u = json.load(r)["usage"]
    return u["prompt_tokens"], u["completion_tokens"]


def workload(model, batch, max_tokens, par, seed0):
    t0 = time.time()
    with ThreadPoolExecutor(par) as ex:
        res = list(ex.map(lambda im: call(model, im[1], max_tokens, seed0 + im[0]), enumerate(batch)))
    t1 = time.time()
    return t0, t1, sum(r[0] for r in res), sum(r[1] for r in res)


def main():
    model, par = sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else 12
    pool = prompts_for(model, N_PER * (2 * CYCLES + 1))
    if len(pool) < N_PER * (2 * CYCLES + 1):
        print(f"only {len(pool)} prompts for {model}", file=sys.stderr)
        return 1
    subprocess.run(["lms", "load", model, "--context-length", "8192", "--parallel", str(par), "--identifier", model],
                   check=True)
    pw = Power()
    pw.start()
    time.sleep(2)
    workload(model, pool[:par], 64, par, 7)  # warm-up, discarded
    k = N_PER
    windows = []
    idle = []

    def rest():
        a = time.time()
        time.sleep(IDLE_S)
        idle.append((a + 3, time.time()))  # skip the first 3 s of ramp-down

    rest()
    for c in range(CYCLES):
        for kind, mt in (("prefill", 1), ("full", 1536)):
            batch = pool[k:k + N_PER]
            k += N_PER
            t0, t1, pin, pout = workload(model, batch, mt, par, 1000 * (c + 1) + (0 if kind == "prefill" else 500))
            windows.append({"cycle": c, "kind": kind, "t0": t0, "t1": t1, "prompt_tokens": pin,
                            "completion_tokens": pout, "idle_before": len(idle) - 1})
            rest()
            print(f"{model} p{par} cycle {c} {kind}: {t1 - t0:.0f}s in={pin} out={pout}", flush=True)
    time.sleep(1)
    pw.stop()
    for w in windows:
        b0 = mean(pw.window(*idle[w["idle_before"]]))
        b1 = mean(pw.window(*idle[w["idle_before"] + 1]))
        base = (b0 + b1) / 2
        s = pw.window(w["t0"], w["t1"])
        w.update(baseline_w=base, idle_before_w=b0, idle_after_w=b1, mean_w=mean(s), n_samples=len(s),
                 marginal_j=integrate(s, base), seconds=w["t1"] - w["t0"])
    cyc = []
    for c in range(CYCLES):
        pf = next(w for w in windows if w["cycle"] == c and w["kind"] == "prefill")
        fu = next(w for w in windows if w["cycle"] == c and w["kind"] == "full")
        b = pf["marginal_j"] / pf["prompt_tokens"]
        a = (fu["marginal_j"] - b * fu["prompt_tokens"]) / fu["completion_tokens"]
        cyc.append({"cycle": c, "j_per_prompt_token": b, "j_per_completion_token": a,
                    "j_per_completion_token_all_in": fu["marginal_j"] / fu["completion_tokens"]})
    res = {"model": model, "parallel": par, "gpu": "physical GPU 1 (board power, MIG 2g.48gb slice in use)",
           "llama_commit": open(f"{J}/../llama.cpp/COMMIT").read().strip() if os.path.exists(f"{J}/../llama.cpp/COMMIT") else "",
           "windows": windows, "idle_windows": idle, "cycles": cyc, "n_power_samples": len(pw.samples),
           "power_samples": pw.samples}
    json.dump(res, open(f"{OUT}/calib_{model}_p{par}.json", "w"))
    for c in cyc:
        print(json.dumps(c), flush=True)
    subprocess.run(["lms", "unload", "--all"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
