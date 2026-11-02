"""Hidden differential tests (FR-TEST-2, DR-TEST-2, LLD §5.8).

Pipeline per family:
  1. candidate inputs: random values by type + perturbations of the visible inputs (restrictive
     preconditions make purely random inputs rarely admissible);
  2. admissibility: `example : F_precond args := by first | decide | trivial | simp_all [..] | omega | grind`
     must elaborate without error (the precondition is *proved* in Lean);
  3. oracle: `#eval!` the reference on admissible inputs (Repr output = expected literal);
  4. round-trip: the reference must pass the rendered guards (drops non-round-tripping literals).
"""
from __future__ import annotations

import copy
import random
import re
from typing import Any

from prl.config import PATHS, sha256_text, write_json
from prl.lean import builder as B
from prl.lean.runner import run_lean_retry
from prl.tasks.verina import Family
from prl.testgen import literals as L

PRE_TACTIC = "by first | decide | trivial | (simp_all [{Q}]; done) | omega | grind [{Q}]"
MAX_REPR = 400


def _json_values(fam: Family) -> list[dict[str, Any]]:
    import json
    p = PATHS.verina_tasks / fam.family_id / "test.json"
    return [t["input"] for t in json.loads(p.read_text(encoding="utf-8"))]


def _parse_visible_value(t: L.LType, v: Any) -> Any:
    """VERINA stores arrays/lists sometimes as pre-rendered strings like '#[1, 2]'."""
    if isinstance(v, str) and t.head in ("Array", "List"):
        s = v.strip().lstrip("#")
        try:
            import json
            return json.loads(s)
        except Exception:  # noqa: BLE001
            return None
    return v


def _perturb(t: L.LType, v: Any, rng: random.Random) -> Any:
    h = t.head
    if v is None:
        return L.random_value(t, rng)
    if h in ("Int", "Nat", "UInt8"):
        nv = int(v) + rng.choice([-2, -1, 1, 2, 3])
        return max(nv, 0) if h != "Int" else nv
    if h in ("List", "Array") and isinstance(v, list):
        xs = copy.deepcopy(v)
        r = rng.random()
        if xs and r < 0.3:
            i = rng.randrange(len(xs))
            xs[i] = _perturb(t.args[0], xs[i], rng)
        elif r < 0.5:
            xs.append(L.random_value(t.args[0], rng) if not xs else rng.choice(xs))
        elif r < 0.65 and xs:
            xs.pop(rng.randrange(len(xs)))
        elif r < 0.8:
            rng.shuffle(xs)
        else:
            xs = list(reversed(xs))
        return xs
    if h == "String" and isinstance(v, str):
        if v and rng.random() < 0.5:
            i = rng.randrange(len(v))
            return v[:i] + v[i + 1:]
        return v + rng.choice("abc")
    if h == "Bool":
        return not v
    return L.random_value(t, rng)


def candidate_inputs(fam: Family, n: int, seed: int) -> list[dict[str, str]]:
    types = [(p, L.parse_type(t)) for p, t in fam.signature.params]
    if not all(L.supported(t) for _, t in types):
        return []
    rng = random.Random(seed * 7919 + int(sha256_text(fam.family_id)[:8], 16))
    vis = _json_values(fam)
    vis_lean = {tuple(sorted(t["input_lean"].items())) for t in fam.visible_tests}
    out, seen = [], set(vis_lean)
    tries = 0
    while len(out) < n and tries < n * 20:
        tries += 1
        if vis and rng.random() < 0.6:
            base = rng.choice(vis)
            vals = {}
            k = rng.randrange(len(types))
            for i, (p, t) in enumerate(types):
                v = _parse_visible_value(t, base.get(p))
                vals[p] = _perturb(t, v, rng) if i == k else (v if v is not None else L.random_value(t, rng))
        else:
            vals = {p: L.random_value(t, rng) for p, t in types}
        try:
            lean = {p: L.render(t, vals[p]) for p, t in types}
        except Exception:  # noqa: BLE001
            continue
        key = tuple(sorted(lean.items()))
        if key in seen:
            continue
        seen.add(key)
        out.append(lean)
    return out


def _file_prefix(fam: Family) -> str:
    return B.candidate_template(fam.template, fam.ref_code, with_proof=False).rstrip("\n") + "\n\n"


def _args(fam: Family, inp: dict[str, str]) -> str:
    return " ".join(f"({inp[p]})" for p, _ in fam.signature.params)


def admissible(fam: Family, inputs: list[dict[str, str]], wall_s: float = 600) -> list[bool]:
    if not inputs:
        return []
    tac = PRE_TACTIC.replace("{Q}", fam.precond_name)
    lines = _file_prefix(fam).split("\n")
    spans = []
    for inp in inputs:
        lines.append(f"example : {fam.precond_name} {_args(fam, inp)} := {tac}")
        spans.append(len(lines))
    r = run_lean_retry("\n".join(lines) + "\n", wall_s=wall_s)
    if r.timeout:
        if len(inputs) == 1:
            return [False]
        mid = len(inputs) // 2
        return admissible(fam, inputs[:mid], wall_s) + admissible(fam, inputs[mid:], wall_s)
    errs = {m.line for m in r.errors()}
    return [ln not in errs for ln in spans]


def oracle(fam: Family, inputs: list[dict[str, str]], wall_s: float = 600) -> list[str | None]:
    if not inputs:
        return []
    lines = _file_prefix(fam).split("\n")
    spans = []
    for k, inp in enumerate(inputs):
        lines.append(f'#eval! IO.println ("<<PRL:{k}>>" ++ reprStr ({B.call(fam.fn, fam.signature.params, inp, B.pre_arg(fam.template, fam.fn))}) ++ "<</PRL>>")')
        spans.append(len(lines))
    r = run_lean_retry("\n".join(lines) + "\n", wall_s=wall_s)
    if r.timeout:
        if len(inputs) == 1:
            return [None]
        mid = len(inputs) // 2
        return oracle(fam, inputs[:mid], wall_s) + oracle(fam, inputs[mid:], wall_s)
    out: list[str | None] = []
    vals = B.parse_eval(r.stdout, len(inputs))
    for ln, val in zip(spans, vals, strict=True):
        if any(m.line == ln and m.severity == "error" for m in r.messages):
            val = None
        if val is not None and (len(val) > MAX_REPR or "\n" in val or re.search(r"\bsorry\b|<", val)):
            val = None
        out.append(val)
    return out


def generate_hidden(fam: Family, judge, per_family: int, seed: int, factor: int = 4) -> dict[str, Any]:
    ret_t = L.parse_type(fam.signature.ret)
    rec: dict[str, Any] = {"family_id": fam.family_id, "seed": seed, "tests": [], "status": "ok"}
    if not L.supported(ret_t) or L.has_float(ret_t):
        rec["status"] = "unsupported_return_type"
        return rec
    cands = candidate_inputs(fam, per_family * factor, seed)
    if not cands:
        rec["status"] = "unsupported_param_type"
        return rec
    adm = admissible(fam, cands)
    ok_inputs = [c for c, a in zip(cands, adm, strict=True) if a]
    outs = oracle(fam, ok_inputs)
    tests = [{"input_lean": c, "expected_lean": (f"({o})" if o.startswith("-") else o)}
             for c, o in zip(ok_inputs, outs, strict=True) if o is not None][: per_family * 2]
    # round-trip: reference must pass every guard
    if tests:
        res = judge.batch_tests_with(fam, [fam.ref_code], tests)[0]
        tests = [t for t, ok in zip(tests, res["test_vector"], strict=True) if ok][:per_family]
    rec.update({"tests": tests, "n_candidates": len(cands), "n_admissible": len(ok_inputs)})
    rec["sha256"] = sha256_text(repr(tests))
    if not tests:
        rec["status"] = "no_admissible_inputs"
    return rec


def save_hidden(rec: dict[str, Any]) -> None:
    write_json(PATHS.hidden / f"{rec['family_id']}.json", rec)
