"""Phase-0 probes: compile-rate floor check (NFR-FEAS-2) and decoding determinism (FR-GEN-5)."""
from __future__ import annotations

import json
import random
from collections.abc import Callable

from prl.config import PATHS, study_config, write_json
from prl.lean.integrity import locked_names
from prl.lean.verify import Judge
from prl.models import extract as X
from prl.models import prompts as P
from prl.models.lmstudio import LMStudio
from prl.tasks import verina as V


def _probe_families(n: int) -> list:
    fams = sorted((f for f in V.all_saved() if f.eligible), key=lambda f: f.family_id)
    rng = random.Random(4242)
    return rng.sample(fams, min(n, len(fams)))


def compile_probe(models: list[str], n_tasks: int = 10, log: Callable[[str], None] = print) -> dict:
    """For each model: write the function from scratch (no faulty code shown), code-only and code+proof.
    Reports extraction rate, compile rate, test-pass rate, proof rate."""
    cfg = study_config()
    cl = LMStudio()
    judge = Judge()
    fams = _probe_families(n_tasks)
    res: dict = {}
    for m in models:
        cl.ensure_loaded(m)
        stats = {"n": 0, "extract": 0, "compile": 0, "tests": 0, "model_proof": 0, "portfolio": 0,
                 "tok_s": [], "gen_s": []}
        for f in fams:
            view = P.make_view(f, None, None, "natural")
            for cond in ("natural", "A"):
                msgs = [{"role": "system", "content": P.system()},
                        {"role": "user", "content": P.initial_user(view, cond if cond == "natural" else "A", None)
                         if cond == "natural" else P.initial_user(view, "A", None).replace(
                             "The current implementation is incorrect. Write a correct implementation",
                             "Write a correct implementation")}]
                comp = cl.complete(m, msgs, seed=1, temperature=float(cfg["decoding"]["temperature"]),
                                   top_p=float(cfg["decoding"]["top_p"]),
                                   max_tokens=int(cfg["budget"]["max_completion_tokens"]))
                stats["n"] += 1
                stats["gen_s"].append(comp.elapsed_s)
                if comp.elapsed_s > 0:
                    stats["tok_s"].append(comp.tokens_out / comp.elapsed_s)
                ex = X.extract(comp.text, fn=f.fn, header=f.header, want_proof=(cond == "A"), locked_names=locked_names(f.fn, f.aux_names))
                if not ex.ok:
                    continue
                stats["extract"] += 1
                mode = "portfolio_then_model" if cond == "A" else "portfolio"
                vr = judge.verify(f, ex.cand(), mode)
                stats["compile"] += bool(vr.compile_ok)
                stats["tests"] += bool(vr.compile_ok and vr.tests_pass)
                stats["model_proof"] += bool(vr.model_proof_ok)
                stats["portfolio"] += bool(vr.proof_ok and vr.proof_source == "portfolio")
        n = max(1, stats["n"])
        summary = {k: (round(v / n, 3) if isinstance(v, int) and k != "n" else v) for k, v in stats.items()
                   if k not in ("tok_s", "gen_s")}
        summary["mean_gen_s"] = round(sum(stats["gen_s"]) / max(1, len(stats["gen_s"])), 2)
        summary["mean_tok_per_s"] = round(sum(stats["tok_s"]) / max(1, len(stats["tok_s"])), 1)
        res[m] = summary
        log(f"compile probe {m}: {json.dumps(summary)}")
    write_json(PATHS.results / "phase0_compile_probe.json", res)
    return res


def determinism_probe(models: list[str], log: Callable[[str], None] = print) -> dict:
    cfg = study_config()
    cl = LMStudio()
    f = _probe_families(1)[0]
    view = P.make_view(f, None, None, "natural")
    msgs = [{"role": "system", "content": P.system()}, {"role": "user", "content": P.initial_user(view, "natural", None)}]
    res = {}
    for m in models:
        cl.ensure_loaded(m)
        outs = [cl.complete(m, msgs, seed=7, temperature=float(cfg["decoding"]["temperature"]),
                            top_p=float(cfg["decoding"]["top_p"]), max_tokens=400).text for _ in range(3)]
        other = cl.complete(m, msgs, seed=8, temperature=float(cfg["decoding"]["temperature"]),
                            top_p=float(cfg["decoding"]["top_p"]), max_tokens=400).text
        res[m] = {"same_seed_identical": len(set(outs)) == 1, "different_seed_differs": other != outs[0],
                  "has_think": "<think>" in outs[0]}
        log(f"determinism {m}: {res[m]}")
    write_json(PATHS.results / "phase0_determinism.json", res)
    return res
