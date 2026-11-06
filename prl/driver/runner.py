"""Experiment driver: plan expansion, resumable execution, JSONL records (FR-DRV-1..5, SR-PRE-2)."""
from __future__ import annotations

import concurrent.futures as cf
import json
import os
import threading
import time
import traceback
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from prl.analysis.features import features
from prl.analysis.mechanism import code_distance, normalise_code
from prl.conditions.protocols import run_condition
from prl.config import PATHS, ensure_dir, read_json, sha256_text
from prl.energy import EnergyMeter
from prl.models.lmstudio import InfraError
from prl.tasks.instances import Instance
from prl.tasks.verina import Family, get_family


@dataclass(frozen=True)
class RunSpec:
    instance_id: str
    condition: str
    model: str
    seed: int

    def run_id(self, study_id: str) -> str:
        return sha256_text(f"{study_id}|{self.instance_id}|{self.condition}|{self.model}|{self.seed}")[:16]


def plan(instances: list[Instance], conditions: list[str], models: list[str], seeds: list[int]) -> list[RunSpec]:
    specs = [RunSpec(i.instance_id, c, m, s) for m in models for c in conditions for i in instances for s in seeds]
    return sorted(specs, key=lambda r: (models.index(r.model), conditions.index(r.condition), r.instance_id, r.seed))


class FreezeError(RuntimeError):
    pass


def check_freeze() -> str:
    from prl.prereg import freeze_status

    ok, diffs, sha = freeze_status()
    if not ok:
        raise FreezeError("prereg/ differs from FREEZE.json: " + ", ".join(diffs))
    return sha


class JsonlWriter:
    def __init__(self, path: Path):
        self.path = path
        ensure_dir(path.parent)
        self.lock = threading.Lock()

    def write(self, obj: dict[str, Any]) -> None:
        line = json.dumps(obj, ensure_ascii=False, sort_keys=True)
        with self.lock, open(self.path, "a", encoding="utf-8", newline="\n") as f:
            f.write(line + "\n")
            f.flush()
            os.fsync(f.fileno())


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    """Read a JSONL log; falls back to `<path>.gz`, the form in which logs over GitHub's 100 MB limit are committed."""
    out = []
    gz = path.with_name(path.name + ".gz")
    if not path.exists() and not gz.exists():
        return out
    import gzip
    opener = (lambda: open(path, encoding="utf-8")) if path.exists() else (lambda: gzip.open(gz, "rt", encoding="utf-8"))
    with opener() as f:
        for ln in f:
            ln = ln.strip()
            if not ln:
                continue
            try:
                out.append(json.loads(ln))
            except json.JSONDecodeError:
                continue  # torn final line after a crash: the run is re-executed
    return out


class Runner:
    def __init__(self, study_dir: Path, cfg: dict[str, Any], judge, gen, *, run_workers: int = 3,
                 prereg_sha: str = "unfrozen", log=print):
        self.dir = ensure_dir(study_dir)
        self.cfg = cfg
        self.judge = judge
        self.gen = gen
        self.workers = run_workers
        self.prereg_sha = prereg_sha
        self.log = log
        self.attempts = JsonlWriter(self.dir / "attempts.jsonl")
        self.runs = JsonlWriter(self.dir / "runs.jsonl")
        self.energy = JsonlWriter(self.dir / "energy.jsonl")
        self.study_id = cfg["study_id"]
        self._fam_cache: dict[str, Family] = {}
        self._fam_lock = threading.Lock()

    def completed(self) -> set[str]:
        return {r["run_id"] for r in read_jsonl(self.dir / "runs.jsonl")}

    def _prune_orphans(self, done: set[str]) -> None:
        p = self.dir / "attempts.jsonl"
        if not p.exists():
            return
        rows = read_jsonl(p)
        keep = [r for r in rows if r.get("run_id") in done]
        if len(keep) != len(rows):
            tmp = p.with_suffix(".tmp")
            with open(tmp, "w", encoding="utf-8", newline="\n") as f:
                for r in keep:
                    f.write(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n")
            os.replace(tmp, p)
            self.log(f"pruned {len(rows) - len(keep)} orphan attempt records")

    def fam(self, fid: str) -> Family:
        with self._fam_lock:
            if fid not in self._fam_cache:
                self._fam_cache[fid] = get_family(fid)
            return self._fam_cache[fid]

    def run_all(self, specs: list[RunSpec], instances: dict[str, Instance], ensure_model=None) -> dict[str, int]:
        done = self.completed()
        self._prune_orphans(done)
        todo = [s for s in specs if s.run_id(self.study_id) not in done]
        self.log(f"{len(specs)} runs planned, {len(specs) - len(todo)} already complete, {len(todo)} to run")
        stats = {"ok": 0, "infra_fail": 0}
        t_start = time.time()
        # (model, condition) blocks run one after another so that energy can be measured per block
        blocks: dict[tuple[str, str], list[RunSpec]] = {}
        for s in todo:
            blocks.setdefault((s.model, s.condition), []).append(s)
        n_done = 0
        ecfg = self.cfg.get("energy", {})
        for (model, cond), group in blocks.items():
            if ensure_model:
                ensure_model(model)
            meter = EnergyMeter(model, cond, watts_per_thread=float(ecfg.get("cpu_watts_per_thread", 2.29)),
                                kg_per_kwh=float(ecfg.get("grid_kg_co2_per_kwh", 0.716)))
            block_runs: list[str] = []
            with cf.ThreadPoolExecutor(self.workers) as ex:
                futs = {ex.submit(self._one, s, instances[s.instance_id]): s for s in group}
                for f in cf.as_completed(futs):
                    s = futs[f]
                    n_done += 1
                    try:
                        f.result()
                        stats["ok"] += 1
                        block_runs.append(s.run_id(self.study_id))
                    except Exception as e:  # noqa: BLE001
                        stats["infra_fail"] += 1
                        self.log(f"[infra] run {s} failed: {e}\n{traceback.format_exc(limit=3)}")
                    if n_done % 10 == 0 or n_done == len(todo):
                        el = time.time() - t_start
                        eta = el / n_done * (len(todo) - n_done)
                        self.log(f"progress {n_done}/{len(todo)}  elapsed {el / 60:.1f} min  eta {eta / 60:.1f} min")
            eb = meter.finish()
            self.energy.write({**eb.to_json(), "study_id": self.study_id, "run_ids": block_runs})
            self.log(f"energy block {model}/{cond}: GPU {eb.gpu_j} J (measured), Lean CPU {eb.cpu_j_est:.0f} J "
                     f"(estimate, {eb.lean_cpu_s:.0f} CPU-s), CO2 {eb.co2_g_est:.1f} g (estimate)")
        return stats

    def _one(self, spec: RunSpec, inst: Instance, retries: int = 2) -> None:
        fam = self.fam(inst.family_id)
        rid = spec.run_id(self.study_id)
        raw_dir = ensure_dir(self.dir / "raw" / rid[:2])

        def sink(k: int, msgs, text: str) -> None:
            (raw_dir / f"{rid}_{k}.json").write_text(json.dumps({"messages": msgs, "output": text}, ensure_ascii=False),
                                                    encoding="utf-8")

        last: Exception | None = None
        for _ in range(retries + 1):
            try:
                rr = run_condition(spec.condition, inst, fam, spec.model, spec.seed, self.cfg, self.judge, self.gen,
                                   raw_sink=sink)
                break
            except InfraError as e:
                last = e
                time.sleep(10)
        else:
            raise InfraError(str(last))
        base = {"run_id": rid, "instance_id": inst.instance_id, "family_id": inst.family_id,
                "condition": spec.condition, "model": spec.model, "seed": spec.seed, "study_id": self.study_id}
        for a in rr.attempts:
            self.attempts.write({**base, **a})
        self.runs.write(self._run_record(base, rr, inst, fam))

    def _run_record(self, base: dict[str, Any], rr, inst: Instance, fam: Family) -> dict[str, Any]:
        b = rr.budget
        final = rr.final or {"code_aux": "", "code": ""}
        ref = fam.ref_code
        fin_code = (final.get("code_aux", "") + "\n" + final.get("code", "")).strip()
        ref_code = (ref["code_aux"] + "\n" + ref["code"]).strip()
        start_code = (inst.start["code_aux"] + "\n" + inst.start["code"]).strip()
        vr = rr.final_vr
        outcome = outcome_label(rr.attempts)
        win = rr.attempts[rr.success_idx] if (rr.success and rr.success_idx is not None) else {}
        model_proof = bool(vr and rr.success and vr.proof_source == "model")
        return {
            **base, "kind": inst.kind, "split": inst.split, "n_attempts": len(rr.attempts),
            "total_tokens": b.used_tokens, "infer_s_total": round(b.used_infer_s, 3),
            "lean_s_total": round(sum(a["verify"].get("lean_s", 0.0) for a in rr.attempts), 3),
            "stop_reason": rr.stop_reason, "success": rr.success, "success_attempt_idx": rr.success_idx,
            "outcome": outcome, "final_code_aux": final.get("code_aux", ""), "final_code": final.get("code", ""),
            "proof_source": vr.proof_source if (vr and rr.success) else "none",
            "closing_entry": vr.closing_entry if (vr and rr.success) else None,
            # FR-ANA-8: tactics of the accepted model-written proof (None when the portfolio closed it)
            "proof_tactic_used": win.get("proof_tactic_used") if model_proof else None,
            "automation_only_proof": bool(win.get("automation_only_proof")) if model_proof else None,
            "dist_to_ref": code_distance(fin_code, ref_code) if rr.success else None,
            "dist_to_start": code_distance(fin_code, start_code) if rr.success else None,
            "equiv_to_ref": (normalise_code(fin_code) == normalise_code(ref_code)) if rr.success else None,
            "ref_auto": bool(fam.ref.get("T", {}).get("closed")),
            "features": features(fam.fn, final.get("code_aux", ""), final.get("code", ""), fam.signature.params) if rr.success else None,
            "flags": sorted({f for a in rr.attempts for f in a["verify"].get("flags", [])}),
            "prereg_sha": self.prereg_sha, "ts": time.time(),
        }


def outcome_label(attempts: list[dict[str, Any]]) -> str:
    """LLD §11.1 priority: verified_repair > verified_but_wrong > integrity_violation > correct_unverified > unresolved."""
    labels = set()
    for a in attempts:
        v = a["verify"]
        if a.get("success"):
            labels.add("verified_repair")
        if v.get("compile_ok") and v.get("proof_ok") and v.get("integrity_ok") and not (
                v.get("visible_pass") and v.get("hidden_pass") is not False):
            labels.add("verified_but_wrong")
        reasons = v.get("static_reasons", []) + v.get("integrity_reasons", [])
        if any(not r.startswith("extract:") and not r.startswith("code:empty") for r in reasons):
            labels.add("integrity_violation")
        if v.get("compile_ok") and v.get("visible_pass") and v.get("hidden_pass") is not False and not v.get("proof_ok"):
            labels.add("correct_unverified")
    for lab in ("verified_repair", "verified_but_wrong", "integrity_violation", "correct_unverified"):
        if lab in labels:
            return lab
    return "unresolved"


def load_instances(ids: list[str] | None = None) -> dict[str, Instance]:
    out = {}
    for p in sorted(PATHS.instances.glob("*.json")):
        i = Instance.from_json(read_json(p))
        if ids is None or i.instance_id in ids:
            out[i.instance_id] = i
    return out
