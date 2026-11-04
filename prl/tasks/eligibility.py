"""Reference checks, eligibility and condition T on references (FR-TASK-2, FR-COND-1, SR-SEL-1)."""
from __future__ import annotations

import concurrent.futures as cf
import re
from collections.abc import Callable

from prl.config import PATHS, load_yaml
from prl.lean.verify import Judge
from prl.tasks import verina as V
from prl.tasks.verina import Family


def known_exclusions() -> dict[str, str]:
    """Family id -> exclusion code from prereg/exclusions.yaml (pre-registered known-bad VERINA tasks)."""
    p = PATHS.prereg / "exclusions.yaml"
    if not p.exists():
        return {}
    data = load_yaml(p) or {}
    return {e["id"]: e["code"] for e in data.get("exclusions", [])}


def ref_proof_status(fam: Family) -> str:
    p = fam.region("proof").strip()
    return "absent" if (not p or re.search(r"\bsorry\b", p)) else "present"


def check_family(fam: Family, judge: Judge, tests: str = "all") -> Family:
    cand = fam.ref_code
    vr = judge.verify(fam, cand, "portfolio", tests=tests, skip_static=True, full_vector=True)
    ref = {
        "compiles": bool(vr.compile_ok),
        "visible_pass": bool(vr.visible_pass) if vr.compile_ok else False,
        "hidden_pass": vr.hidden_pass,
        "n_visible_fail": vr.n_visible_fail,
        "n_hidden_fail": vr.n_hidden_fail,
        "errors": vr.lean_errors[:2],
        "T": {"closed": bool(vr.proof_ok), "entry": vr.closing_entry, "vector": vr.entry_vector,
              "timeout": vr.lean_timeout},
        "lean_s": round(vr.lean_s, 1),
        "proof": ref_proof_status(fam),
    }
    if ref["proof"] == "present":
        pv = judge.verify(fam, {**cand, "proof_aux": fam.region("proof_aux"), "proof": fam.region("proof")},
                          "model_proof", tests="none", skip_static=True)
        ref["proof"] = "human_ok" if pv.model_proof_ok else "human_broken"
    fam.ref = ref
    reasons = []
    code = known_exclusions().get(fam.family_id)
    if code:
        reasons.append(f"known_defect:{code}")
    if not ref["compiles"]:
        reasons.append("ref_compile_error")
    elif not ref["visible_pass"]:
        reasons.append("ref_visible_fail")
    if any(f.startswith("visible_tests_unrenderable") for f in fam.flags) and not fam.visible_tests:
        reasons.append("unrenderable_tests")
    fam.eligible = not reasons
    fam.exclusion_reason = ",".join(reasons) or None
    return fam


def check_all(fams: list[Family], judge: Judge, workers: int = 6, tests: str = "all",
              log: Callable[[str], None] = print) -> list[Family]:
    out = []
    with cf.ThreadPoolExecutor(workers) as ex:
        futs = {ex.submit(check_family, f, judge, tests): f for f in fams}
        for k, fu in enumerate(cf.as_completed(futs), 1):
            f = fu.result()
            V.save_family(f)
            out.append(f)
            log(f"[{k}/{len(fams)}] {f.family_id}: eligible={f.eligible} T={f.ref['T']['closed']} "
                f"({f.ref['T']['entry']}) proof={f.ref['proof']} {f.ref['lean_s']}s")
    return sorted(out, key=lambda f: f.family_id)
