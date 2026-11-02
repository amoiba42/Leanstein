"""Code-shape features of a Lean implementation (RQ4; shared with the hint extractor)."""
from __future__ import annotations

import re

from prl.lean import leantext as LT


def features(fn: str, code_aux: str, code: str, params: list[tuple[str, str]] | None = None) -> dict[str, int]:
    text = (code_aux or "") + "\n" + (code or "")
    c = LT.strip_comments_and_strings(text)
    lines = [ln for ln in c.split("\n") if ln.strip()]
    indents = [len(ln) - len(ln.lstrip(" ")) for ln in lines] or [0]
    helpers = [n for k, n in LT.top_level_decls(code_aux or "") if k in {"def", "abbrev"} and n]
    lrec = LT.let_rec_names(code or "") + LT.let_rec_names(code_aux or "")
    rec = LT.recursive_functions(fn, code_aux or "", code or "")
    ptypes = " ".join(t for _, t in (params or []))
    f = {
        "loc": len(lines),
        "n_helpers": len(helpers),
        "uses_match": int(bool(re.search(r"\bmatch\b", c))),
        "uses_if": int(bool(re.search(r"\bif\b", c))),
        "self_recursive": int(fn in rec),
        "let_rec": int(bool(lrec)),
        "where_helpers": int(bool(LT.where_names(code or ""))),
        "any_recursion": int(bool(rec)),
        "partial": int(bool(re.search(r"\bpartial\b", c))),
        "well_founded": int(bool(re.search(r"\btermination_by\b|\bdecreasing_by\b", c))),
        "imperative_loop": int(bool(re.search(r"\bfor\b[^\n]*\bin\b|\bwhile\b|\blet\s+mut\b|\bdo\b", c))),
        "fold": int(bool(re.search(r"\bfold[lr]?\b|\.foldl\b|\.foldr\b|foldlM", c))),
        "list_combinators": int(bool(re.search(r"\.(map|filter|all|any|zip|count|sum|length|reverse|take|drop|find\?|contains|elem|range)\b|List\.(map|filter|range|sum)", c))),
        "array_index_bang": int(bool(re.search(r"\[[^\]\n]+\]!|\.get!|\bget!\b", c))),
        "array_index_opt": int(bool(re.search(r"\[[^\]\n]+\]\?|\.get\?|getD", c))),
        "array_ops": int(bool(re.search(r"\.(push|set!|size|toList|toArray|modify|swap)\b|Array\.", c))),
        "nat_int_cast": int(bool(re.search(r"\.toNat\b|Int\.toNat|\.natAbs\b|Int\.ofNat|↑|\(\s*\w+\s*:\s*Int\s*\)|Int\.natAbs", c))),
        "nat_sub": int(("Nat" in ptypes) and bool(re.search(r"\w\s*-\s*\w", c))),
        "bool_ops": int(bool(re.search(r"&&|\|\||\bnot\b|!\w", c))),
        "decide_in_code": int(bool(re.search(r"\bdecide\b", c))),
        "max_indent": max(indents) // 2,
    }
    return f


FEATURE_ORDER = [
    "loc", "n_helpers", "uses_match", "uses_if", "self_recursive", "let_rec", "where_helpers", "any_recursion",
    "partial", "well_founded", "imperative_loop", "fold", "list_combinators", "array_index_bang",
    "array_index_opt", "array_ops", "nat_int_cast", "nat_sub", "bool_ops", "decide_in_code", "max_indent",
]
BINARY_FEATURES = [k for k in FEATURE_ORDER if k not in {"loc", "n_helpers", "max_indent"}]
