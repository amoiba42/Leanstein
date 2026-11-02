"""Mechanism metrics (SR-MECH-1..3): shaping vs reverting."""
from __future__ import annotations

import re

from prl.lean import leantext as LT

_TOK = re.compile(r"[A-Za-z_][\w.'!?]*|\d+|:=|=>|->|<-|::|\+\+|<=|>=|!=|==|&&|\|\||[^\s\w]")


def normalise_code(s: str) -> str:
    c = LT.strip_comments_and_strings(s or "", keep_strings=True)
    return " ".join(_TOK.findall(c))


def tokens(s: str) -> list[str]:
    return normalise_code(s).split(" ") if s and s.strip() else []


def levenshtein(a: list[str], b: list[str]) -> int:
    if len(a) < len(b):
        a, b = b, a
    prev = list(range(len(b) + 1))
    for i, x in enumerate(a, 1):
        cur = [i]
        for j, y in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (x != y)))
        prev = cur
    return prev[-1]


def code_distance(x: str, y: str) -> float:
    """Normalised token edit distance in [0, 1]."""
    a, b = tokens(x), tokens(y)
    if not a and not b:
        return 0.0
    return levenshtein(a, b) / max(len(a), len(b))


def classify(*, success: bool, ref_auto: bool, equiv_to_ref: bool | None, dist_to_ref: float | None,
             revert_distance: float) -> str | None:
    """revert: reproduces an automation-provable reference (or is identical to it);
    shaping: the reference itself is NOT automation-provable, so the repair needed a different shape;
    other: success on an automation-provable reference with a materially different implementation."""
    if not success:
        return None
    if equiv_to_ref:
        return "revert"
    if not ref_auto:
        return "shaping"
    if dist_to_ref is not None and dist_to_ref <= revert_distance:
        return "revert"
    return "other"
