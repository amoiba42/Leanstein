"""Feedback router (final architecture §5): failure type × condition → message for the next turn.

| failure \\ cond | A    | B / BP / Bhammer            | C / S                               | Cplain / Splain |
|----------------|------|-----------------------------|-------------------------------------|-----------------|
| extraction     | none | "no `def F` found"          | "no `def F` found"                  | generic         |
| integrity      | none | rule(s) violated            | rule(s) violated                    | generic         |
| compile        | none | Lean errors                 | Lean errors (+ structural pointers) | generic         |
| test (visible) | none | failing input/expected/got  | failing input/expected/got (+ ptrs) | generic         |
| test (hidden)  | none | count only — never inputs   | count only — never inputs           | generic         |
| timeout/resrc. | none | "did not terminate"         | "did not terminate" (+ pointers)    | generic         |
| proof          | none | Lean proof errors           | best unsolved goal + pointers       | generic         |

Infrastructure failures never reach the router: the same candidate is re-verified without charging the
budget (see `protocols.verify_with_infra_retry`).
"""
from __future__ import annotations

from dataclasses import dataclass

from prl.lean import hints as Hn
from prl.models import prompts as P

INTEGRITY_TEXT = {
    "forbidden": "uses a forbidden construct",
    "command": "contains a forbidden command",
    "redefines": "redefines a locked declaration",
    "decl": "declares something other than definitions",
    "proof_decl": "contains a theorem/lemma/instance",
    "proof_in_code_only_condition": "contains a proof (this task asks for code only)",
    "second_definition": "defines the function twice",
    "empty": "has an empty body",
    "region_marker": "contains a benchmark marker",
    "hash_command": "contains a # command",
    "prl_name": "uses a reserved name",
    "locked_hash_mismatch": "changed a locked part of the file",
    "model_proof_axioms": "relies on a non-standard axiom",
}


@dataclass(frozen=True)
class Feedback:
    kind: str  # extraction | integrity | compile | test | timeout | resource | proof | none
    text: str
    hint_kinds: tuple[str, ...] = ()


def _integrity_text(reasons: list[str]) -> str:
    parts = []
    for r in reasons:
        key = next((k for k in INTEGRITY_TEXT if k in r), None)
        detail = r.split(":")[-1] if ":" in r else ""
        msg = INTEGRITY_TEXT.get(key, "violates the rules") if key else "violates the rules"
        parts.append(f"- the answer {msg}" + (f" (`{detail}`)" if detail and detail != key else ""))
    return "The answer was rejected by the checker:\n" + "\n".join(dict.fromkeys(parts))


def route(cond: str, fam, cand: dict[str, str], vr, *, extract_ok: bool, witness_line: str | None) -> Feedback:
    if cond == "A":
        return Feedback("none", "")
    plain = cond in P.PLAIN_CONDITIONS
    fn = fam.fn
    if not extract_ok:
        kind, core = "extraction", f"Could not find a complete `def {fn}` in your answer."
    else:
        fk = vr.failure_kind or "proof"
        kind = fk
        if fk == "integrity":
            core = _integrity_text(vr.static_reasons + vr.integrity_reasons)
        elif fk == "compile":
            core = "The code does not compile:\n" + "\n".join(vr.lean_errors[:3])
        elif fk in ("timeout", "resource"):
            core = "Evaluating your implementation did not terminate within the limits (it may loop forever)."
        elif fk == "test":
            lines = []
            if witness_line:
                lines.append(witness_line)
            if vr.n_visible_fail:
                lines.append(f"{vr.n_visible_fail} visible test(s) failed.")
            if vr.n_hidden_fail:
                lines.append(f"{vr.n_hidden_fail} additional behavioural check(s) failed.")  # never inputs
            core = "\n".join(lines) or "The implementation is behaviourally wrong."
        else:  # proof
            if cond in P.PROOF_CONDITIONS:
                core = "The proof does not check:\n" + "\n".join((vr.proof_errors or vr.lean_errors)[:3])
            else:
                core = ""  # filled by the structural hint below
    if plain:
        return Feedback(kind, P.feedback(cond, witness_line=None, errors=[], hint_text=""))
    if cond in P.PROOF_CONDITIONS:
        return Feedback(kind, P.feedback(cond, witness_line=core, errors=[], hint_text=""))
    # C / S: structural hint (goal + pointers) on top of the routed core message
    hint_kinds: tuple[str, ...] = ()
    if extract_ok and kind not in ("integrity",):
        h = Hn.extract(fam, cand, vr, witness_line)
        hint_kinds = tuple(h.kinds)
        text = h.text if kind in ("compile", "test", "proof") else (core + "\n" + "\n".join(
            "Hint: " + Hn.catalogue()["pointers"][p] for p in h.kinds if p in Hn.catalogue()["pointers"]))
    else:
        text = core
    return Feedback(kind, P.feedback(cond, witness_line=None, errors=[], hint_text=text.strip()), hint_kinds)
