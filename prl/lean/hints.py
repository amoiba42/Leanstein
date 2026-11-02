"""Deterministic, rule-based stuck-point hints for conditions C and S (FR-HINT-1..3)."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from functools import lru_cache

from prl.config import PATHS, load_yaml
from prl.lean import leantext as LT
from prl.tasks.verina import Family


@dataclass
class Hint:
    kinds: list[str] = field(default_factory=list)
    text: str = ""


@lru_cache(maxsize=2)
def catalogue() -> dict:
    return load_yaml(PATHS.prereg / "hints.yaml")


def pointers(fam: Family, code_aux: str, code: str) -> list[str]:
    c = LT.strip_comments_and_strings((code_aux or "") + "\n" + (code or ""))
    post = LT.strip_comments_and_strings(fam.region("postcond") + "\n" + fam.region("postcond_aux"))
    types = " ".join(t for _, t in fam.signature.params) + " " + fam.signature.ret
    out = []
    if re.search(r"\bpartial\b", c):
        out.append("partial_def")
    if re.search(r"\btermination_by\b|\bdecreasing_by\b", c):
        out.append("well_founded")
    if re.search(r"\bfor\b[^\n]*\bin\b|\bwhile\b|\blet\s+mut\b", c):
        out.append("imperative_loop")
    if ("Nat" in types and "Int" in types) or re.search(r"\.toNat\b|\.natAbs\b|Int\.ofNat|↑", c):
        if re.search(r"\.toNat\b|\.natAbs\b|Int\.ofNat|↑|\(\s*\w+\s*:\s*(Int|Nat)\s*\)", c):
            out.append("nat_int_mix")
    used = set(re.findall(r"(?<![\w.])([A-Za-z_][\w']*)", c))
    known = set(LT.helper_names(fam.fn, code_aux, code, fam.aux_names)) | {fam.fn}
    defined_here = {n for _, n in LT.top_level_decls(code_aux or "") if n}
    if any(n in used for n in defined_here - known):
        out.append("opaque_helper")
    if re.search(r"\[[^\]\n]+\]!|\.get!|\bget!\b", c):
        out.append("array_index")
    if re.search(r"\bfold[lr]\b|\.foldl\b|\.foldr\b", c):
        out.append("fold_accumulator")
    post_idx = bool(re.search(r"∀\s*\w+\s*(<|,|:)|∀\s*\(\w+\s*:\s*Nat\)|\[\w+\]!|\.get\b|getD", post))
    code_list_rec = bool(re.search(r"\|\s*\w+\s*::\s*\w+", c))
    code_idx = bool(re.search(r"\[[^\]\n]+\]|\bfor\b|\bwhile\b", c))
    post_list_rec = bool(re.search(r"::", post))
    if (post_idx and code_list_rec and not code_idx) or (post_list_rec and code_idx and not code_list_rec):
        out.append("spec_shape_mismatch")
    return out


def _best_entry(vr) -> tuple[str | None, str]:
    best = None
    best_key = None
    for eid, goal in vr.entry_goals.items():
        n_goals = max(1, goal.count("⊢"))
        non_goal = 0 if "⊢" in goal else 1
        k = (non_goal, n_goals, len(goal))
        if best_key is None or k < best_key:
            best, best_key = eid, k
    return best, (vr.entry_goals.get(best, "") if best else "")


def extract(fam: Family, cand: dict[str, str], vr, witness_line: str | None) -> Hint:
    cat = catalogue()
    kinds: list[str] = []
    parts: list[str] = []
    if vr.compile_ok is False:
        kinds.append("compile_error")
        errs = vr.lean_errors[:2]
        parts.append("The code does not compile:\n" + "\n".join(errs))
    elif not vr.tests_pass:
        kinds.append("test_failure")
        if witness_line:
            parts.append(witness_line)
        if vr.n_visible_fail == 0 and vr.n_hidden_fail:
            parts.append(f"{vr.n_hidden_fail} additional behavioural check(s) failed.")
        elif vr.n_visible_fail:
            parts.append(f"{vr.n_visible_fail} visible test(s) failed.")
    else:
        kinds.append("proof_stuck")
        eid, goal = _best_entry(vr)
        g = goal[: int(cat["goal_chars"])]
        parts.append("The code passes the tests, but the automatic tactics could not prove the specification."
                     + (f"\nClosest attempt ({eid}) left this goal:\n{g}" if g else ""))
    ptrs = pointers(fam, cand.get("code_aux", ""), cand.get("code", ""))
    for p in ptrs:
        kinds.append(p)
        parts.append("Hint: " + cat["pointers"][p])
    text = "\n".join(parts)
    cap = int(cat["max_chars"])
    if len(text) > cap:
        text = text[: cap - 3] + "..."
    return Hint(kinds, text)
