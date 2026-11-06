"""Pre-registered pilot gate (docs/final_proposal.md section 8) computed from the IREL pilot. Read only.
Run from the repo root with `uv run python /scratch/inesh/irel_jobs/gate.py` after `prl analyze --study pilot --out results/pilot`."""
import collections
import json
from pathlib import Path

R = Path("runs/pilot")
runs = [json.loads(l) for l in open(R / "runs.jsonl", encoding="utf-8") if l.strip()]
atts = [json.loads(l) for l in open(R / "attempts.jsonl", encoding="utf-8") if l.strip()]
infra = sum(1 for l in open(R / "driver.log", encoding="utf-8") if "[infra] run" in l)

# 1. T coverage over the eligible pool (from the dataset)
fams = [json.load(open(f, encoding="utf-8")) for f in Path("data/families").glob("*.json")]
el = [f for f in fams if f.get("eligible")]
cov = collections.defaultdict(lambda: [0, 0])
for f in el:
    t = bool((f.get("ref") or {}).get("T", {}).get("closed"))
    for k in (f["tier"], "all"):
        cov[k][0] += t
        cov[k][1] += 1
print("1. T coverage:", {k: f"{a}/{b} = {100*a/b:.1f}%" for k, (a, b) in cov.items()}, "-> gate >=20%:",
      "PASS" if cov["all"][0] / cov["all"][1] >= 0.20 else "FAIL")

# 2. natural-bug families in the main split (pool rule)
ins = [json.load(open(f, encoding="utf-8")) for f in Path("data/instances").glob("*.json")]
split = json.load(open("data/splits.json"))
main = set(split["main"])
nat = {i["family_id"] for i in ins if i["kind"] == "natural" and i["family_id"] in main}
print(f"2. natural main families: {len(nat)} of {len(main)} (minimum 60) ->",
      "natural pool" if len(nat) >= 60 else "fallback natural+mutant")

# 3. C compile rate (attempt level)
c = [a for a in atts if a["condition"] == "C" and a.get("extract_ok")]
comp = sum(1 for a in c if (a.get("verify") or {}).get("compile_ok"))
call = [a for a in atts if a["condition"] == "C"]
print(f"3. C compile rate: {comp}/{len(call)} attempts = {100*comp/max(1,len(call)):.1f}% -> gate >10%:",
      "PASS" if comp / max(1, len(call)) > 0.10 else "FAIL")

# 4. >=1 C repair that neither B nor BP finds (same instance, model, seed)
ok = {(r["instance_id"], r["model"], r["seed"], r["condition"]) for r in runs if r["success"]}
only_c = sorted({(i, m) for (i, m, s, cnd) in ok if cnd == "C" and (i, m, s, "B") not in ok and (i, m, s, "BP") not in ok})
print(f"4. C-only repairs (neither B nor BP): {len(only_c)} -> gate >=1 (hand check pending):",
      "PASS (candidates)" if only_c else "FAIL")
for i, m in only_c[:8]:
    print("     ", m, i)

# 5. zero false successes: every success passed hidden tests and carries no degeneracy flag
succ = [r for r in runs if r["success"]]
flagged = [r for r in succ if r.get("flags")]
print(f"5. successes: {len(succ)}; with degeneracy flags: {len(flagged)} -> automated check",
      "PASS" if not flagged else "REVIEW", "(hand check pending)")

# 6. cost and infrastructure
inf = sum(r.get("infer_s_total", 0) for r in runs) / 3600
by = collections.defaultdict(float)
for r in runs:
    by[r["condition"]] += r.get("infer_s_total", 0) / 3600
st = collections.Counter((r["condition"], r["stop_reason"]) for r in runs if r.get("stop_reason") == "infer_time")
print(f"6. pilot: {len(runs)} runs, infra failures {infra}, inference {inf:.2f} h; per condition (h):",
      {k: round(v, 2) for k, v in sorted(by.items())}, "; infer_time stops:", dict(st))
print("   Bhammer share of the five main conditions' inference:",
      f"{100*by['Bhammer']/max(1e-9, sum(v for k, v in by.items() if k != 'Bhammer')):.0f}%")

# 7. power note
pn = json.load(open("prereg/power_note.json", encoding="utf-8"))
for row in pn["rows"]:
    if row.get("scenario") == "point":
        print(f"7. power {row['model']} {row['x']} vs {row['y']}: {row['power_at_available']:.3f} at "
              f"{row['main_families_available']} families; needed {row.get('required_main_families')}")
