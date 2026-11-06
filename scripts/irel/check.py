"""Stop-rule check across all study folders (read only).
Rule 1: infrastructure failures > 5% of attempted runs (driver.log "[infra] run" lines vs runs.jsonl rows).
Rule 2 (team decision 3): stop_reason == "infer_time" > 1% of runs in any (study, model, condition), once >= 50 runs.
Also counts attempt-level infra errors in attempts.jsonl (retried, never charged)."""
import collections, json, os, sys
R = "/scratch/inesh/Leanstein/runs"
STUDIES = ["main", "heldout", "main-shaping", "main-gemma", "main-goedel", "main-bhammer", "pilot-irel"]
trip = []
for s in STUDIES:
    d = f"{R}/{s}"
    if not os.path.exists(f"{d}/runs.jsonl"):
        continue
    rows = [json.loads(l) for l in open(f"{d}/runs.jsonl", encoding="utf-8") if l.strip()]
    infra = sum(1 for l in open(f"{d}/driver.log", encoding="utf-8") if "[infra] run" in l) if os.path.exists(f"{d}/driver.log") else 0
    n = len(rows)
    rate = infra / max(1, n + infra)
    by = collections.Counter((r["model"], r["condition"]) for r in rows)
    it = collections.Counter((r["model"], r["condition"]) for r in rows if r.get("stop_reason") == "infer_time")
    succ = sum(1 for r in rows if r.get("success"))
    worst = max(((it[k] / by[k], k) for k in by), default=(0, None))
    print(f"{s}: runs={n} infra_fail={infra} ({100*rate:.2f}%) infer_time={sum(it.values())} "
          f"worst={100*worst[0]:.2f}% {worst[1] or ''}")
    if rate > 0.05 and n + infra >= 40:
        trip.append(f"{s}: infra failure rate {100*rate:.1f}% > 5%")
    for k in by:
        if by[k] >= 50 and it[k] / by[k] > 0.01:
            trip.append(f"{s}: infer_time {it[k]}/{by[k]} = {100*it[k]/by[k]:.1f}% > 1% in {k}")
print("STOP_RULE_TRIPPED: " + "; ".join(trip) if trip else "stop rules OK")
sys.exit(3 if trip else 0)
