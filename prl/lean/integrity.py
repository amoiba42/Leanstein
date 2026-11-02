"""Static integrity checks on model-written regions (IR-2, IR-4, IR-5) and degeneracy flags (IR-7).

Static rejection happens before any Lean process runs. Post-Lean checks (locked hash, axioms)
live in `prl.lean.judge`.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from prl.lean import leantext as LT
from prl.tasks.regions import MARKER

ALLOWED_AXIOMS = frozenset({"propext", "Classical.choice", "Quot.sound"})

# Forbidden anywhere (proof escapes, compiler overrides, meta-programming, options).
FORBIDDEN_WORDS = (
    "sorry", "admit", "axiom", "native_decide", "implemented_by", "extern", "unsafe", "opaque",
    "csimp", "macro_rules", "elab_rules", "run_tac", "run_cmd", "run_elab", "set_option", "attribute",
    "ofReduceBool", "Lean.Elab", "Lean.Meta", "Lean.Compiler", "Lean.Parser", "unsafeCast", "unsafeBaseIO",
    "unsafeIO", "IO.Process", "Lean.ofReduceBool", "trustCompiler",
)
# Forbidden as commands (start of a line, optionally after `local`/`scoped`/attributes).
FORBIDDEN_COMMANDS = (
    "import", "namespace", "section", "export", "notation", "infix", "infixl", "infixr", "prefix",
    "postfix", "macro", "syntax", "elab", "initialize", "builtin_initialize", "universe",
    "variable", "omit", "include", "declare_syntax_cat", "end",
)
_FORBIDDEN_RE = re.compile(
    r"(?<![\w.'])(" + "|".join(re.escape(w) for w in sorted(FORBIDDEN_WORDS, key=len, reverse=True)) + r")(?![\w'])"
)
_COMMAND_RE = re.compile(
    r"(?:^|\n)[ \t]*(?:@\[[^\]]*\][ \t]*)?(?:(?:local|scoped|private|protected)[ \t]+)*("
    + "|".join(re.escape(w) for w in sorted(FORBIDDEN_COMMANDS, key=len, reverse=True))
    + r")(?![\w'])"
)
_HASH_CMD = re.compile(r"(^|\n)\s*#[A-Za-z_]+")
_PROOF_DECL_RE = re.compile(r"(?<![\w.'])(theorem|lemma|example|instance|class)(?![\w'])")

CODE_ONLY = "code_only"
WITH_PROOF = "with_proof"


@dataclass
class StaticResult:
    ok: bool
    reasons: list[str] = field(default_factory=list)


def _scan_common(name: str, text: str, reasons: list[str]) -> str:
    if MARKER in text:
        reasons.append(f"{name}:region_marker")
    clean = LT.strip_comments_and_strings(text)
    for m in _FORBIDDEN_RE.finditer(clean):
        reasons.append(f"{name}:forbidden:{m.group(1)}")
    # `end` closes `mutual` blocks legitimately; every other listed command is rejected.
    mutual_ok = re.search(r"(^|\n)\s*mutual\b", clean) is not None
    for m in _COMMAND_RE.finditer(clean):
        w = m.group(1)
        if w == "end" and mutual_ok:
            continue
        reasons.append(f"{name}:command:{w}")
    if _HASH_CMD.search(clean):
        reasons.append(f"{name}:hash_command")
    return clean


def locked_names(fn: str, aux_names: list[str]) -> set[str]:
    return {fn, f"{fn}_precond", f"{fn}_postcond", f"{fn}_spec_satisfied", *aux_names}


def static_check(cand: dict[str, str], kind: str, *, fn: str, aux_names: list[str]) -> StaticResult:
    """`cand` has keys code_aux, code, proof_aux, proof. `kind` is CODE_ONLY or WITH_PROOF."""
    reasons: list[str] = []
    code_aux = cand.get("code_aux", "") or ""
    code = cand.get("code", "") or ""
    proof_aux = cand.get("proof_aux", "") or ""
    proof = cand.get("proof", "") or ""
    locked = locked_names(fn, aux_names)

    if not code.strip():
        reasons.append("code:empty")
    c_aux = _scan_common("code_aux", code_aux, reasons)
    c_code = _scan_common("code", code, reasons)

    # declarations in code regions
    for kw, nm in LT.top_level_decls(code_aux):
        if kw not in {"def", "abbrev", "structure", "inductive"}:
            reasons.append(f"code_aux:decl:{kw}")
        if nm and (nm in locked or nm.startswith("prl_") or nm.split(".")[0] in locked and "." not in nm):
            reasons.append(f"code_aux:redefines:{nm}")
    if _PROOF_DECL_RE.search(c_aux) and not any(k in {"theorem", "lemma"} for k, _ in LT.top_level_decls(code_aux)):
        # e.g. an indented `theorem` or `instance` hidden inside a mutual block
        reasons.append("code_aux:proof_decl")
    if _PROOF_DECL_RE.search(c_code):
        reasons.append("code:proof_decl")
    if re.search(r"(^|\n)def\s", c_code) or re.search(r"(^|\n)\s*def\s+" + re.escape(fn) + r"\b", c_code):
        reasons.append("code:second_definition")
    if re.search(r"(?<![\w.'])prl_\w+", c_aux + c_code):
        reasons.append("code:prl_name")

    if kind == CODE_ONLY:
        if proof_aux.strip() or proof.strip():
            reasons.append("proof_in_code_only_condition")
    elif kind == WITH_PROOF:
        c_paux = _scan_common("proof_aux", proof_aux, reasons)
        _scan_common("proof", proof, reasons)
        for kw, nm in LT.top_level_decls(proof_aux):
            if kw in {"axiom", "opaque", "instance", "class"}:
                reasons.append(f"proof_aux:decl:{kw}")
            if nm and (nm in locked or nm.startswith("prl_")):
                reasons.append(f"proof_aux:redefines:{nm}")
        del c_paux
    else:  # pragma: no cover
        raise ValueError(kind)
    return StaticResult(not reasons, sorted(set(reasons)))


# --------------------------------------------------------------------------- IR-7 flags

_CHOICE = re.compile(r"\b(Classical\.choose|Classical\.epsilon|Exists\.choose|Classical\.indefiniteDescription|Classical\.choice)\b")


def degeneracy_flags(cand: dict[str, str], *, fn: str, visible_inputs: list[dict[str, str]]) -> list[str]:
    text = (cand.get("code_aux", "") or "") + "\n" + (cand.get("code", "") or "")
    clean = LT.strip_comments_and_strings(text, keep_strings=True)
    flags = []
    if re.search(re.escape(fn) + r"_postcond", clean):
        flags.append("mentions_postcond")
    if _CHOICE.search(clean):
        flags.append("uses_choice")
    if re.search(r"\bdecide\b[^\n]*_postcond", clean):
        flags.append("decide_on_spec")
    hits = 0
    for inp in visible_inputs:
        lits = [v for v in inp.values() if len(v) >= 4]
        if lits and all(v in clean for v in lits):
            hits += 1
    if hits >= 3:
        flags.append("hardcoded_tests")
    body = LT.strip_comments_and_strings(cand.get("code", "") or "", keep_strings=True).strip()
    if re.fullmatch(r"(true|false|-?\d+|\(-\d+\)|\[\]|#\[\]|none|\"[^\"]*\"|0\.0)", body):
        flags.append("constant_body")
    return flags


def axioms_clean(axioms: list[str]) -> bool:
    return set(axioms) <= ALLOWED_AXIOMS
