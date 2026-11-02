"""Natural bugs (FR-NAT-1) and shaping instances (FR-COND-7)."""
from __future__ import annotations

import concurrent.futures as cf
from collections.abc import Callable

from prl.lean.integrity import locked_names
from prl.lean.verify import Judge
from prl.models import extract as X
from prl.models import prompts as P
from prl.tasks.instances import Instance
from prl.tasks.verina import Family


def shaping_instance(fam: Family) -> Instance | None:
    """Study S starts from the *correct* reference when T cannot prove it."""
    if not fam.eligible or fam.ref.get("T", {}).get("closed"):
        return None
    if fam.ref.get("hidden_pass") is False:
        return None
    return Instance(instance_id=f"{fam.family_id}__shape__0", family_id=fam.family_id, kind="shaping",
                    start=fam.ref_code, provenance={"source": "reference"}, witness=None,
                    start_T={"closed": False}, hashes={"locked": fam.locked_hash})


def natural_for_family(fam: Family, judge: Judge, client, models: list[str], samples: int, cfg: dict,
                       per_family: int = 1) -> list[Instance]:
    view = P.make_view(fam, None, None, "natural")
    msgs = [{"role": "system", "content": P.system()},
            {"role": "user", "content": P.initial_user(view, "natural", None)}]
    out: list[Instance] = []
    for gm in models:
        for s in range(samples):
            seed = 5000 + s
            comp = client.complete(gm, msgs, seed=seed, temperature=float(cfg["decoding"]["temperature"]),
                                   top_p=float(cfg["decoding"]["top_p"]),
                                   max_tokens=int(cfg["budget"]["max_completion_tokens"]))
            ex = X.extract(comp.text, fn=fam.fn, header=fam.header, want_proof=False, locked_names=locked_names(fam.fn, fam.aux_names))
            if not ex.ok:
                continue
            cand = {"code_aux": ex.code_aux, "code": ex.code}
            vr = judge.verify(fam, cand, "portfolio", tests="all")
            if not (vr.static_ok and vr.compile_ok) or vr.tests_pass:
                continue
            wit = None
            n_vis = len(fam.visible_tests)
            for i, ok in enumerate(vr.test_vector):
                if not ok:
                    if i < n_vis:
                        t = fam.visible_tests[i]
                        wit = {"source": "visible", "index": i, "input_lean": t["input_lean"],
                               "expected": t["expected_lean"],
                               "actual": judge.eval_outputs(fam, cand, [t["input_lean"]])[0]}
                    else:
                        wit = {"source": "hidden", "index": i - n_vis}
                    break
            out.append(Instance(
                instance_id=f"{fam.family_id}__nat__{gm}__{s}", family_id=fam.family_id, kind="natural",
                start=cand, provenance={"generator": gm, "seed": seed, "raw": comp.text[:6000]}, witness=wit,
                start_T={"closed": bool(vr.proof_ok), "entry": vr.closing_entry, "weak_spec": bool(vr.proof_ok)},
                hashes={"locked": fam.locked_hash}, flags=(["weak_spec"] if vr.proof_ok else []),
            ))
            if len(out) >= per_family:
                return out
    return out


def collect_natural(fams: list[Family], judge: Judge, client, model: str, samples: int, cfg: dict,
                    workers: int = 3, log: Callable[[str], None] = print, per_family: int = 1) -> list[Instance]:
    res: list[Instance] = []
    with cf.ThreadPoolExecutor(workers) as ex:
        futs = {ex.submit(natural_for_family, f, judge, client, [model], samples, cfg, per_family): f for f in fams}
        for n, fu in enumerate(cf.as_completed(futs), 1):
            f = futs[fu]
            try:
                ins = fu.result()
            except Exception as e:  # noqa: BLE001
                log(f"[{n}/{len(fams)}] {f.family_id}: ERROR {e}")
                continue
            res += ins
            log(f"[{n}/{len(fams)}] {f.family_id}: {len(ins)} natural bug(s) from {model}")
    return res
