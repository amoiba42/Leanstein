"""Assemble one self-contained Lean file per verification and record line ranges (LineMap)."""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from prl.lean.portfolio import Entry
from prl.tasks import regions as R

PRE_PROOF = "(by first | decide | trivial | (simp_all; done) | omega | sorry)"


@dataclass
class LineMap:
    code_span: tuple[int, int] = (1, 1)  # template lines before proof_aux (code + spec)
    proof_span: tuple[int, int] = (1, 1)  # proof_aux start .. end of template
    tests: list[tuple[int, int]] = field(default_factory=list)
    entries: list[tuple[str, int, int, int]] = field(default_factory=list)  # (id, start, end, axioms_line)
    model_axioms_line: int | None = None
    template_end: int = 1


def _line_of(text: str, offset: int) -> int:
    return text.count("\n", 0, offset) + 1


def ensure_mathlib(template: str) -> str:
    imp = R.region_text(template, "import")
    if re.search(r"^\s*import\s+Mathlib\s*$", imp, re.M):
        return template
    return "import Mathlib\n" + template


def candidate_template(template: str, cand: dict[str, str], with_proof: bool) -> str:
    repl = {"code_aux": cand.get("code_aux", "") or "", "code": cand.get("code", "") or ""}
    if with_proof:
        repl["proof_aux"] = cand.get("proof_aux", "") or ""
        repl["proof"] = cand.get("proof", "") or ""
    else:
        repl["proof_aux"] = ""
        repl["proof"] = "sorry"
    return ensure_mathlib(R.render(template, repl))


def pre_arg(template: str, fn: str) -> str:
    """The precondition-proof argument, or "" when the locked signature has no `h_precond` parameter
    (some VERINA functions take none)."""
    return PRE_PROOF if "h_precond" in R.def_header(template, fn) else ""


def call(fn: str, params: list[tuple[str, str]], inp: dict[str, str], pre: str) -> str:
    args = " ".join(f"({inp[p]})" for p, _ in params)
    return f"{fn} {args} {pre}".rstrip()


def guard_line(fn: str, params: list[tuple[str, str]], ret: str, inp: dict[str, str], exp: str,
               pre: str = PRE_PROOF) -> str:
    return f"#guard ({call(fn, params, inp, pre)}) == ({exp} : {ret})"


def build(template: str, *, fn: str, params: list[tuple[str, str]], ret: str, theorem_stmt: str,
          cand: dict[str, str], tests: list[dict[str, str]], entries: list[Entry], with_proof: bool,
          heartbeats: int | None = None, test_heartbeats: int | None = None) -> tuple[str, LineMap]:
    """`heartbeats` overrides every entry's own tier limit when given (tests only)."""
    body = candidate_template(template, cand, with_proof)
    regs = R.parse_regions(body)
    lm = LineMap()
    proof_start_off = regs["proof_aux"].start if "proof_aux" in regs else regs["proof"].start
    # the `-- !benchmark @start proof_aux` line itself belongs to the proof span
    proof_start_line = _line_of(body, proof_start_off) - 1
    lm.code_span = (1, proof_start_line - 1)
    lines = body.rstrip("\n").split("\n")
    lm.template_end = len(lines)
    lm.proof_span = (proof_start_line, lm.template_end)

    out = list(lines)

    def emit(s: str) -> tuple[int, int]:
        start = len(out) + 1
        out.extend(s.split("\n"))
        return start, len(out)

    emit("")
    emit("-- ======================= PRL harness (generated) =======================")
    if with_proof:
        _, ln = emit(f"#print axioms {fn}_spec_satisfied")
        lm.model_axioms_line = ln
    for i, t in enumerate(tests):
        g = guard_line(fn, params, ret, t["input_lean"], t["expected_lean"], pre_arg(template, fn))
        if test_heartbeats:
            g = f"set_option maxHeartbeats {test_heartbeats} in\n{g}"
        lm.tests.append(emit(g))
    for e in entries:
        script = "\n".join("  " + ln for ln in e.script.split("\n"))
        hb = heartbeats if heartbeats is not None else e.heartbeats
        s, en = emit(f"set_option maxHeartbeats {hb} in\ntheorem prl_try_{len(lm.entries)} {theorem_stmt} := by\n{script}")
        _, ax = emit(f"#print axioms prl_try_{len(lm.entries)}")
        lm.entries.append((e.id, s, en, ax))
    return "\n".join(out) + "\n", lm


def build_batch(template: str, *, fn: str, params: list[tuple[str, str]], ret: str,
                cands: list[dict[str, str]], tests: list[dict[str, str]]) -> tuple[str, list[dict]]:
    """Compile + test many code candidates in one file (dataset building only; no proofs).

    Each candidate gets its own copy of the (import-free) template inside `namespace PRLB<k>`, so the
    Mathlib import is paid once. Returns the source and, per candidate, its code span and test spans.
    """
    first = ensure_mathlib(candidate_template(template, {"code_aux": "", "code": "0"}, False))
    imports = [ln for ln in first.split("\n") if ln.startswith("import ")]
    out = list(dict.fromkeys(imports))
    spans = []
    for k, c in enumerate(cands):
        body = candidate_template(template, c, with_proof=False)
        body_lines = [ln for ln in body.split("\n") if not ln.startswith("import ")]
        out.append(f"namespace PRLB{k}")
        s = len(out) + 1
        out.extend(body_lines)
        e = len(out)
        tspans = []
        for t in tests:
            out.append(guard_line(fn, params, ret, t["input_lean"], t["expected_lean"], pre_arg(template, fn)))
            tspans.append((len(out), len(out)))
        out.append(f"end PRLB{k}")
        spans.append({"code": (s, e), "tests": tspans})
    return "\n".join(out) + "\n", spans


EVAL_RE = re.compile(r"<<PRL:(\d+)>>(.*?)<</PRL>>", re.S)


def parse_eval(stdout: str, n: int) -> list[str | None]:
    text = stdout.replace("\r\n", "\n")
    found = {int(m.group(1)): m.group(2).strip() for m in EVAL_RE.finditer(text)}
    return [found.get(i) for i in range(n)]


def build_eval(template: str, *, fn: str, params: list[tuple[str, str]], cand: dict[str, str],
               inputs: list[dict[str, str]]) -> tuple[str, list[int]]:
    """File that `#eval`s the candidate on inputs (used for hint witnesses and the test oracle)."""
    body = candidate_template(template, cand, with_proof=False)
    out = body.rstrip("\n").split("\n")
    out.append("")
    lines = []
    for inp in inputs:
        k = len(lines)
        out.append(f'#eval! IO.println ("<<PRL:{k}>>" ++ reprStr ({call(fn, params, inp, pre_arg(template, fn))}) ++ "<</PRL>>")')
        lines.append(len(out))
    return "\n".join(out) + "\n", lines
