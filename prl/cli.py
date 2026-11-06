"""`prl` command-line interface (LLD §12)."""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

from prl.config import PATHS, ensure_dir, study_config


def _log(path: Path | None = None):
    f = open(path, "a", encoding="utf-8") if path else None  # noqa: SIM115

    def log(msg: str) -> None:
        line = time.strftime("%H:%M:%S ") + msg
        print(line, flush=True)
        if f:
            f.write(line + "\n")
            f.flush()
    return log


def _workers(a) -> int:
    from prl.lean import runner
    n = a.lean_workers or int(study_config()["lean"]["workers"]) or runner.auto_workers()
    runner.set_repl_workers(n)
    print(f"Lean workers: {n}", flush=True)
    return n


def cmd_env(a) -> int:
    from prl.config import lean_env
    from prl.lean.runner import backend, run_lean
    e = lean_env()
    print("toolchain:", e.toolchain_id)
    print("backend:", backend())
    r = run_lean("import Mathlib\nexample : (2 : Nat) + 2 = 4 := by decide\n#print axioms Nat.add_comm\n", wall_s=600)
    print("lean smoke:", "OK" if not r.errors() else r.errors(), f"({r.elapsed_s:.1f}s)")
    try:
        from prl.models.lmstudio import LMStudio
        print("lm studio models:", LMStudio().models())
    except Exception as ex:  # noqa: BLE001
        print("lm studio: unreachable", ex)
    return 0


def cmd_tasks_build(a) -> int:
    from prl.tasks import verina as V
    fams = V.load_all()
    for f in fams:
        V.save_family(f)
    print(f"{len(fams)} families written to {PATHS.families}")
    return 0


def cmd_tasks_check(a) -> int:
    from prl.lean.verify import Judge
    from prl.tasks import eligibility as E
    from prl.tasks import verina as V
    n = _workers(a)
    fams = V.all_saved()
    if a.ids:
        fams = [f for f in fams if f.family_id in a.ids.split(",")]
    E.check_all(fams, Judge(), workers=n, tests=a.tests, log=_log(PATHS.runs / "phase0" / "tasks_check.log"))
    return 0


def cmd_tests_hidden(a) -> int:
    import concurrent.futures as cf

    from prl.lean.verify import Judge
    from prl.tasks import verina as V
    from prl.testgen import hidden as H
    cfg = study_config()
    n = _workers(a)
    j = Judge()
    fams = [f for f in V.all_saved() if f.eligible]
    if a.ids:
        fams = [f for f in fams if f.family_id in a.ids.split(",")]
    log = _log(PATHS.runs / "phase0" / "hidden.log")
    hc = cfg["hidden_tests"]

    def one(f):
        p = PATHS.hidden / f"{f.family_id}.json"
        if p.exists() and not a.force:
            return f.family_id, "exists", 0
        rec = H.generate_hidden(f, j, int(hc["per_family"]), int(hc["seed"]), int(hc.get("candidates_factor", 4)))
        H.save_hidden(rec)
        # hidden tests are round-trip checked against the reference at generation time, so the
        # reference passes them by construction
        f.ref["hidden_pass"] = True if rec["tests"] else None
        f.ref["n_hidden"] = len(rec["tests"])
        if not rec["tests"]:
            f.flags = sorted(set(f.flags) | {"hidden_unavailable"})
        V.save_family(f)
        return f.family_id, rec["status"], len(rec["tests"])

    with cf.ThreadPoolExecutor(n) as ex:
        for k, (fid, status, nt) in enumerate(ex.map(one, fams), 1):
            log(f"[{k}/{len(fams)}] {fid}: {status} ({nt} hidden tests)")
    return 0


def cmd_bugs_mutants(a) -> int:
    from prl.lean.verify import Judge
    from prl.mutate.select import build_all
    from prl.tasks import instances as INS
    from prl.tasks import verina as V
    cfg = study_config()
    n = _workers(a)
    fams = [f for f in V.all_saved() if f.eligible]
    if a.ids:
        fams = [f for f in fams if f.family_id in a.ids.split(",")]
    ins = build_all(fams, Judge(), int(cfg["mutants_per_family"]), seed=int(cfg["splits"]["seed"]), workers=n,
                    log=_log(PATHS.runs / "phase0" / "mutants.log"),
                    on_done=lambda xs: [INS.save(i) for i in xs])
    _provenance(ins, "mutants.csv")
    print(f"{len(ins)} mutant instances")
    return 0


def _provenance(ins, name: str) -> None:
    import csv
    p = ensure_dir(PATHS.provenance) / name
    with open(p, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["instance_id", "family_id", "kind", "operator_or_generator", "line", "before", "after",
                    "witness_source", "weak_spec"])
        for i in ins:
            pv = i.provenance
            w.writerow([i.instance_id, i.family_id, i.kind, pv.get("operator", pv.get("generator", "")),
                        pv.get("line", ""), pv.get("before", ""), pv.get("after", ""),
                        (i.witness or {}).get("source", ""), "weak_spec" in i.flags])


def cmd_bugs_shaping(a) -> int:
    from prl.natural.collect import shaping_instance
    from prl.tasks import instances as INS
    from prl.tasks import verina as V
    ins = [i for i in (shaping_instance(f) for f in V.all_saved()) if i]
    for i in ins:
        INS.save(i)
    print(f"{len(ins)} shaping instances")
    return 0


def cmd_bugs_natural(a) -> int:
    from prl.lean.verify import Judge
    from prl.models.lmstudio import LMStudio
    from prl.natural.collect import collect_natural
    from prl.tasks import instances as INS
    from prl.tasks import verina as V
    cfg = study_config()
    _workers(a)
    fams = [f for f in V.all_saved() if f.eligible]
    if a.ids:
        fams = [f for f in fams if f.family_id in a.ids.split(",")]
    cl = LMStudio()
    ins = []
    for gm in cfg["models"]["natural_generators"]:   # zero-shot bug sources, never repairers
        cl.ensure_loaded(gm, parallel=a.run_workers)
        got = collect_natural(fams, Judge(), cl, gm, int(cfg["natural"]["samples"]), cfg, workers=a.run_workers,
                              log=_log(PATHS.runs / "phase0" / "natural.log"),
                              per_family=int(cfg["natural"]["per_family_per_generator"]))
        for i in got:
            INS.save(i)
        ins += got
    _provenance(ins, "natural.csv")
    print(f"{len(ins)} natural-bug instances")
    return 0


def cmd_splits(a) -> int:
    from prl.tasks import splits as SP
    from prl.tasks import verina as V
    cfg = study_config()["splits"]
    sp = SP.make_splits(V.all_saved(), int(cfg["pilot_n"]), float(cfg["heldout_frac"]), int(cfg["seed"]))
    counts = SP.apply_splits(sp)
    print({k: len(v) for k, v in sp.items() if k != "seed"}, "instances:", counts)
    return 0


def cmd_run(a) -> int:
    from prl.driver.runner import FreezeError, Runner, check_freeze, load_instances, plan
    from prl.lean.verify import Judge
    from prl.models.lmstudio import LMStudio
    cfg = study_config()
    _workers(a)
    splits = a.split.split(",")
    sha = "unfrozen"
    if any(s in ("main", "heldout") for s in splits) and not a.allow_unfrozen:
        try:
            sha = check_freeze()
        except FreezeError as e:
            print("REFUSING TO RUN:", e)
            return 2
    kinds = a.kinds.split(",")
    insts = {k: v for k, v in load_instances().items() if v.split in splits and v.kind in kinds}
    if a.families:
        keep = set(a.families.split(","))
        insts = {k: v for k, v in insts.items() if v.family_id in keep}
    if a.limit_families:
        fams = sorted({v.family_id for v in insts.values()})[: a.limit_families]
        insts = {k: v for k, v in insts.items() if v.family_id in fams}
    conds = a.conditions.split(",")
    models = a.models.split(",")
    seeds = [int(s) for s in a.seeds.split(",")] if a.seeds else cfg["seeds"]
    specs = plan(list(insts.values()), conds, models, seeds)
    study_dir = PATHS.runs / a.study
    cl = LMStudio()
    log = _log(ensure_dir(study_dir) / "driver.log")
    log(f"study={a.study} splits={splits} kinds={kinds} conditions={conds} models={models} seeds={seeds} "
        f"instances={len(insts)} prereg={sha}")
    r = Runner(study_dir, {**cfg, "study_id": a.study}, Judge(), cl, run_workers=a.run_workers, prereg_sha=sha, log=log)
    stats = r.run_all(specs, insts, ensure_model=lambda m: cl.ensure_loaded(m, parallel=a.run_workers))
    log(f"done: {stats}")
    return 0


def cmd_freeze(a) -> int:
    from prl.analysis.power import has_power_note
    from prl.prereg import freeze
    if not has_power_note() and not a.no_power_note:
        print("REFUSING TO FREEZE: prereg/power_note.json is missing. Run `prl power --study pilot` first "
              "(or pass --no-power-note and record why in prereg/deviations.md).")
        return 2
    rec = freeze(a.note or "")
    print(json.dumps({"digest": rec["digest"], "frozen_at": rec["frozen_at"], "n_files": len(rec["files"])}, indent=1))
    return 0


def cmd_analyze(a) -> int:
    from prl.analysis.report import analyze
    cfg = study_config()
    dirs = [PATHS.runs / s for s in a.study.split(",")] if a.study else []
    s = analyze(dirs, cfg, Path(a.out) if a.out else None)
    print(json.dumps(s, indent=1, default=str))
    return 0


def cmd_audit(a) -> int:
    from prl.analysis.report import audit_merge, audit_sample
    cfg = study_config()
    out = PATHS.results / "audit" / "sample.csv"
    if a.merge:
        summary = audit_merge(out, PATHS.results / "audit" / "summary.md")
        print(summary)
        return 0
    s = audit_sample([PATHS.runs / x for x in a.study.split(",")], float(cfg["analysis"]["audit_frac"]),
                     int(cfg["analysis"]["seed"]), out)
    print(f"{len(s)} runs sampled for audit -> {out} (fill audit_* columns, then run `prl audit --merge`)")
    return 0


def cmd_crosseval(a) -> int:
    from prl.analysis.crosseval import cross_evaluate
    from prl.lean.verify import Judge
    n = _workers(a)
    conds = tuple(a.conditions.split(",")) if a.conditions else tuple(study_config()["crosseval_conditions"])
    for s in a.study.split(","):
        d = PATHS.runs / s
        counts = cross_evaluate(d, Judge(), conditions=conds, workers=n, log=_log(d / "crosseval.log"))
        print(s, counts)
    return 0


def cmd_power(a) -> int:
    from prl.analysis.power import NOTE_PATH, power_note
    note = power_note(PATHS.runs / a.study, study_config(), log=_log())
    print(f"{len(note['rows'])} scenario rows -> {NOTE_PATH} and results/power_note.md")
    return 0


def cmd_probe(a) -> int:
    from prl.conditions.probes import compile_probe, determinism_probe
    _workers(a)
    if a.kind == "compile":
        compile_probe(a.models.split(","), n_tasks=a.n, log=_log(PATHS.runs / "phase0" / "probe.log"))
    else:
        determinism_probe(a.models.split(","), log=_log(PATHS.runs / "phase0" / "probe.log"))
    return 0


def main(argv: list[str] | None = None) -> int:
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    try:
        sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    except Exception:  # noqa: BLE001
        pass
    ap = argparse.ArgumentParser(prog="prl", description="P.I.G. (Proof-Independent Generation) research harness")
    ap.add_argument("--lean-workers", type=int, default=0)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("env").set_defaults(fn=cmd_env)
    t = sub.add_parser("tasks").add_subparsers(dest="sub", required=True)
    t.add_parser("build").set_defaults(fn=cmd_tasks_build)
    c = t.add_parser("check")
    c.add_argument("--ids", default="")
    c.add_argument("--tests", default="all", choices=["all", "visible"])
    c.set_defaults(fn=cmd_tasks_check)
    h = sub.add_parser("hidden")
    h.add_argument("--ids", default="")
    h.add_argument("--force", action="store_true")
    h.set_defaults(fn=cmd_tests_hidden)
    b = sub.add_parser("bugs").add_subparsers(dest="sub", required=True)
    m = b.add_parser("mutants")
    m.add_argument("--ids", default="")
    m.set_defaults(fn=cmd_bugs_mutants)
    nb = b.add_parser("natural")
    nb.add_argument("--ids", default="")
    nb.add_argument("--run-workers", type=int, default=3)
    nb.set_defaults(fn=cmd_bugs_natural)
    b.add_parser("shaping").set_defaults(fn=cmd_bugs_shaping)
    sub.add_parser("splits").set_defaults(fn=cmd_splits)
    r = sub.add_parser("run")
    r.add_argument("--study", required=True)
    r.add_argument("--split", default="pilot")
    r.add_argument("--kinds", default="mutant,natural")
    r.add_argument("--conditions", default="A,B,BP,C,Cplain", help="also: S,Splain (shaping) and Bhammer (exploratory)")
    r.add_argument("--models", default="qwen3.5-2b,qwen3.5-4b")
    r.add_argument("--seeds", default="")
    r.add_argument("--families", default="")
    r.add_argument("--limit-families", type=int, default=0)
    r.add_argument("--run-workers", type=int, default=4)
    r.add_argument("--allow-unfrozen", action="store_true")
    r.set_defaults(fn=cmd_run)
    f = sub.add_parser("freeze")
    f.add_argument("--note", default="")
    f.add_argument("--no-power-note", action="store_true", help="freeze without prereg/power_note.json")
    f.set_defaults(fn=cmd_freeze)
    ce = sub.add_parser("crosseval", help="B-to-C cross-evaluation (secondary; Lean only, no model)")
    ce.add_argument("--study", required=True)
    ce.add_argument("--conditions", default="")
    ce.set_defaults(fn=cmd_crosseval)
    pw = sub.add_parser("power", help="pre-freeze power note from the pilot")
    pw.add_argument("--study", default="pilot")
    pw.set_defaults(fn=cmd_power)
    an = sub.add_parser("analyze")
    an.add_argument("--study", default="")
    an.add_argument("--out", default="")
    an.set_defaults(fn=cmd_analyze)
    au = sub.add_parser("audit")
    au.add_argument("--study", default="")
    au.add_argument("--merge", action="store_true", help="summarise the filled-in audit CSV")
    au.set_defaults(fn=cmd_audit)
    p = sub.add_parser("probe")
    p.add_argument("kind", choices=["compile", "determinism"])
    p.add_argument("--models", default="qwen3.5-2b,qwen3.5-4b")
    p.add_argument("--n", type=int, default=10)
    p.set_defaults(fn=cmd_probe)
    a = ap.parse_args(argv)
    try:
        return a.fn(a)
    finally:
        try:
            from prl.lean import runner
            runner.shutdown()
        except Exception:  # noqa: BLE001
            pass


if __name__ == "__main__":
    sys.exit(main())
