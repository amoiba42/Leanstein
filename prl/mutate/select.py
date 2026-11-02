"""Mutant filtering and selection (FR-MUT-2..4): compile ∧ fails ≥1 test; ≤k per family; stratified."""
from __future__ import annotations

import concurrent.futures as cf
import random
from collections.abc import Callable

from prl.analysis.mechanism import normalise_code
from prl.config import sha256_text
from prl.lean.verify import Judge
from prl.mutate.operators import Mutant, generate
from prl.tasks.instances import Instance
from prl.tasks.verina import Family

MAX_CANDIDATES = 12  # verified per family (cost bound), sampled deterministically across operator classes


def candidate_mutants(fam: Family, seed: int) -> list[Mutant]:
    ms = generate(fam.region("code"), "code") + generate(fam.region("code_aux"), "code_aux")
    rng = random.Random(seed * 1_000_003 + int(sha256_text(fam.family_id)[:8], 16))
    by_op: dict[str, list[Mutant]] = {}
    for m in ms:
        by_op.setdefault(m.op, []).append(m)
    for v in by_op.values():
        rng.shuffle(v)
    ops = sorted(by_op)
    rng.shuffle(ops)
    out: list[Mutant] = []
    while len(out) < MAX_CANDIDATES and any(by_op.values()):
        for op in ops:
            if by_op[op] and len(out) < MAX_CANDIDATES:
                out.append(by_op[op].pop())
    return out


def build_mutants(fam: Family, judge: Judge, k: int, seed: int) -> list[Instance]:
    ref_norm = normalise_code(fam.region("code_aux") + "\n" + fam.region("code"))
    pool: list[tuple[Mutant, dict[str, str]]] = []
    for m in candidate_mutants(fam, seed):
        cand = fam.ref_code.copy()
        cand[m.region] = m.text
        if normalise_code(cand["code_aux"] + "\n" + cand["code"]) != ref_norm:
            pool.append((m, cand))
    # one request per candidate: a non-terminating mutant only costs its own short wall guard
    res = [judge.batch_tests(fam, [c], tests="all")[0] for _, c in pool]
    kept_m = [(m, c) for (m, c), r in zip(pool, res, strict=True) if r["compile_ok"] and not all(r["test_vector"])]
    # distinct operator classes first, then the rest (deterministic order from candidate_mutants)
    first, rest, ops = [], [], set()
    for m, c in kept_m:
        (rest if m.op in ops else first).append((m, c))
        ops.add(m.op)
    kept: list[tuple[Mutant, object]] = []
    for m, c in first + rest:
        if len(kept) >= k:
            break
        # full verification (tests + portfolio on the buggy code) only for the short list
        vr = judge.verify(fam, c, "portfolio", tests="all", skip_static=True, force_portfolio=True)
        if vr.compile_ok and not vr.tests_pass:
            kept.append((m, vr))
    # prefer distinct operator classes
    chosen: list[tuple[Mutant, object]] = []
    for m, vr in kept:
        if len(chosen) < k and m.op not in {c[0].op for c in chosen}:
            chosen.append((m, vr))
    for m, vr in kept:
        if len(chosen) < k and (m, vr) not in chosen:
            chosen.append((m, vr))
    out = []
    for idx, (m, vr) in enumerate(chosen):
        cand = fam.ref_code.copy()
        cand[m.region] = m.text
        n_vis = len(fam.visible_tests)
        wit = None
        for i, ok in enumerate(vr.test_vector):
            if not ok:
                if i < n_vis:
                    t = fam.visible_tests[i]
                    act = judge.eval_outputs(fam, cand, [t["input_lean"]])[0]
                    wit = {"source": "visible", "index": i, "input_lean": t["input_lean"],
                           "expected": t["expected_lean"], "actual": act}
                else:
                    wit = {"source": "hidden", "index": i - n_vis}
                break
        if wit and wit["source"] == "hidden":
            # prefer a visible witness if any visible test fails
            pass
        line, col = m.line_col
        out.append(Instance(
            instance_id=f"{fam.family_id}__mut__{m.op}__{idx}", family_id=fam.family_id, kind="mutant",
            start={"code_aux": cand["code_aux"], "code": cand["code"]},
            provenance={"operator": m.op, "region": m.region, "line": line, "col": col, "before": m.before,
                        "after": m.after, "seed": seed},
            witness=wit,
            start_T={"closed": bool(vr.proof_ok), "entry": vr.closing_entry, "weak_spec": bool(vr.proof_ok)},
            hashes={"locked": fam.locked_hash},
            flags=(["weak_spec"] if vr.proof_ok else []),
        ))
    return out


def build_all(fams: list[Family], judge: Judge, k: int, seed: int, workers: int = 4,
              log: Callable[[str], None] = print, on_done=None) -> list[Instance]:
    res: list[Instance] = []
    with cf.ThreadPoolExecutor(workers) as ex:
        futs = {ex.submit(build_mutants, f, judge, k, seed): f for f in fams}
        for n, fu in enumerate(cf.as_completed(futs), 1):
            f = futs[fu]
            try:
                ins = fu.result()
            except Exception as e:  # noqa: BLE001
                log(f"[{n}/{len(fams)}] {f.family_id}: ERROR {e}")
                continue
            res += ins
            if on_done:
                on_done(ins)
            log(f"[{n}/{len(fams)}] {f.family_id}: {len(ins)} mutants {[i.provenance['operator'] for i in ins]}")
    return sorted(res, key=lambda i: i.instance_id)
