"""Extract implementation / proof regions from raw model output (FR-GEN-4)."""
from __future__ import annotations

import re
import textwrap
from dataclasses import dataclass, field

from prl.models.lmstudio import strip_think

_FENCE = re.compile(r"```[ \t]*([A-Za-z0-9_+-]*)[ \t]*\n(.*?)(?:```|\Z)", re.S)


@dataclass
class Extracted:
    ok: bool
    code_aux: str = ""
    code: str = ""
    proof_aux: str = ""
    proof: str = ""
    error: str | None = None
    notes: list[str] = field(default_factory=list)

    def cand(self) -> dict[str, str]:
        return {"code_aux": self.code_aux, "code": self.code, "proof_aux": self.proof_aux, "proof": self.proof}


def blocks(text: str) -> list[str]:
    text = strip_think(text)
    bs = [m.group(2) for m in _FENCE.finditer(text)]
    if not bs:
        bs = [text]
    return [b.replace("\r\n", "\n") for b in bs]


def _norm_ws(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def _split_def(block: str, fn: str) -> tuple[str, str, str] | None:
    """Return (before_def, header_through_assign, body) or None."""
    m = re.search(r"^[ \t]*(?:@\[[^\]]*\]\s*)?(?:(?:noncomputable|partial|private|protected)\s+)*def\s+" + re.escape(fn) + r"(?![\w'.])", block, re.M)
    if not m:
        return None
    before = block[: m.start()]
    rest = block[m.start():]
    depth = 0
    i = 0
    while i < len(rest):
        c = rest[i]
        if c in "([{⟨":
            depth += 1
        elif c in ")]}⟩":
            depth -= 1
        elif c == ":" and rest.startswith(":=", i) and depth == 0:
            return before, rest[: i + 2], rest[i + 2:]
        i += 1
    return None


_PROOF_START = re.compile(r"^[ \t]*(theorem|lemma)\s", re.M)


def _dedent_body(body: str) -> str:
    lines = body.split("\n")
    first = lines[0].strip()
    tail = textwrap.dedent("\n".join(lines[1:]))
    out = (first + "\n" + tail) if first else tail
    return out.strip("\n")


_DECL_START = re.compile(r"^(?:@\[[^\]]*\]\s*)?(?:(?:noncomputable|private|protected)\s+)*(def|abbrev|theorem|lemma)\s+([^\s(:{\[]+)", re.M)


def drop_locked_decls(code_aux: str, locked: set[str]) -> tuple[str, list[str]]:
    """Remove top-level declarations that re-declare locked names (models often echo the given
    precondition/postcondition/theorem). Safe: the harness always re-emits the locked originals, so a
    dropped copy can never influence verification; anything else the model wrote is kept and checked."""
    if not code_aux:
        return code_aux, []
    starts = [m for m in _DECL_START.finditer(code_aux)]
    if not starts:
        return code_aux, []
    # column-0 command boundaries (declarations, attributes, comments at col 0 belong to the next decl)
    bounds = [m.start() for m in re.finditer(r"^(?=\S)", code_aux, re.M)] + [len(code_aux)]
    keep, dropped, pos = [], [], 0
    for m in starts:
        if m.group(2) not in locked:
            continue
        end = next((b for b in bounds if b > m.end() and not code_aux[b:].startswith(("|", "termination_by", "decreasing_by", "where"))), len(code_aux))
        keep.append(code_aux[pos:m.start()])
        pos = end
        dropped.append(m.group(2))
    keep.append(code_aux[pos:])
    out = "".join(keep)
    out = re.sub(r"\n{3,}", "\n\n", out).strip("\n")
    return out, dropped


def extract(text: str, *, fn: str, header: str, want_proof: bool, locked_names: set[str] | None = None) -> Extracted:
    bs = blocks(text)
    code_block_idx = None
    split = None
    for i, b in enumerate(bs):
        s = _split_def(b, fn)
        if s:
            code_block_idx, split = i, s
            break
    if split is None:
        return Extracted(False, error="no_definition")
    before, hdr, body = split
    notes = []
    # a proof written in the same block after the def
    pm = _PROOF_START.search(body)
    same_block_proof = ""
    if pm:
        same_block_proof = body[pm.start():]
        body = body[: pm.start()]
        notes.append("proof_in_code_block")
    if re.sub(r"[\s()]", "", hdr) != re.sub(r"[\s()]", "", header):
        # The harness always re-emits the *locked* header, so a different header cannot change the
        # verified statement; renamed/retyped parameters simply make the body fail to compile.
        notes.append("signature_differs")
    code = _dedent_body(body)
    code_aux = textwrap.dedent(before).strip("\n")
    # drop stray non-Lean lines (e.g. prose before the def inside an unfenced answer)
    if code_aux and not re.search(r"^\s*(def|abbrev|structure|inductive|mutual|@\[|termination_by|decreasing_by|where|\s)", code_aux, re.M):
        code_aux = ""
        notes.append("dropped_prose")
    if locked_names:
        code_aux, dropped = drop_locked_decls(code_aux, locked_names)
        if dropped:
            notes.append("dropped_locked_echo:" + ",".join(dropped))
    ex = Extracted(True, code_aux=code_aux, code=code, notes=notes)
    if want_proof:
        prf_src = same_block_proof
        if not prf_src:
            for j, b in enumerate(bs):
                if j == code_block_idx:
                    continue
                if re.search(r"\btheorem\s+" + re.escape(fn) + r"_spec_satisfied\b", b):
                    prf_src = b
                    break
        m = re.search(r"^[ \t]*theorem\s+" + re.escape(fn) + r"_spec_satisfied\b", prf_src, re.M) if prf_src else None
        if not m:
            ex.notes.append("no_proof")
            return ex
        paux = textwrap.dedent(prf_src[: m.start()]).strip("\n")
        rest = prf_src[m.start():]
        k = rest.find(":= by")
        if k < 0:
            ex.notes.append("proof_without_by")
            return ex
        ex.proof_aux = paux
        ex.proof = _dedent_body(rest[k + len(":= by"):]).strip("\n")
    return ex
