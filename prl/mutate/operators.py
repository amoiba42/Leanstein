"""Mutation operators over the implementation regions (FR-MUT-1, LLD §6).

Operates on a light token stream; comments and string literals are never mutated.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from prl.lean import leantext as LT


@dataclass(frozen=True)
class Mutant:
    op: str
    region: str  # code | code_aux
    offset: int
    before: str
    after: str
    text: str  # full mutated region text

    @property
    def line_col(self) -> tuple[int, int]:
        pre = self.text[: self.offset]
        return pre.count("\n") + 1, self.offset - (pre.rfind("\n") + 1)


# (op class, pattern, replacement); patterns are applied to code with comments/strings masked
_SIMPLE: list[tuple[str, str, str]] = [
    ("arith", r"(?<=\s)\+(?=\s)", "-"),
    ("arith", r"(?<=\s)-(?=\s)", "+"),
    ("arith", r"(?<=\s)\*(?=\s)", "+"),
    ("arith", r"(?<=\s)/(?=\s)", "*"),
    ("arith", r"(?<=\s)%(?=\s)", "/"),
    ("relflip", r"(?<=\s)<(?=\s)", "≤"),
    ("relflip", r"(?<=\s)≤(?=\s)", "<"),
    ("relflip", r"(?<=\s)<=(?=\s)", "<"),
    ("relflip", r"(?<=\s)>(?=\s)", "≥"),
    ("relflip", r"(?<=\s)≥(?=\s)", ">"),
    ("relflip", r"(?<=\s)>=(?=\s)", ">"),
    ("relflip", r"(?<=\s)==(?=\s)", "!="),
    ("relflip", r"(?<=\s)!=(?=\s)", "=="),
    ("relflip", r"(?<=\s)≠(?=\s)", "="),
    ("boolop", r"(?<=\s)&&(?=\s)", "||"),
    ("boolop", r"(?<=\s)\|\|(?=\s)", "&&"),
    ("boolop", r"(?<=\s)∧(?=\s)", "∨"),
    ("boolop", r"(?<=\s)∨(?=\s)", "∧"),
    ("drop_succ", r"\s\+\s1\b", ""),
    ("drop_succ", r"\s-\s1\b", ""),
]
_NUM = re.compile(r"(?<![\w.'])(\d+)(?![\w.'])")
_IF = re.compile(r"\bif\b(.*?)\bthen\b", re.S)
_EQ_IN_IF = re.compile(r"(?<=\s)=(?=\s)")


def _mask(text: str) -> str:
    """Comments and strings blanked with same-length filler so offsets are preserved."""
    clean = LT.strip_comments_and_strings(text, keep_strings=True)
    # strip_comments drops characters; rebuild an offset-preserving mask instead
    out = list(text)
    i, n, depth = 0, len(text), 0
    while i < n:
        c, nx = text[i], text[i + 1] if i + 1 < n else ""
        if depth:
            if c == "-" and nx == "/":
                out[i] = out[i + 1] = " "
                depth -= 1
                i += 2
                continue
            if c == "/" and nx == "-":
                depth += 1
            if c != "\n":
                out[i] = " "
            i += 1
            continue
        if c == "/" and nx == "-":
            depth = 1
            out[i] = out[i + 1] = " "
            i += 2
            continue
        if c == "-" and nx == "-":
            while i < n and text[i] != "\n":
                out[i] = " "
                i += 1
            continue
        if c == '"':
            j = i + 1
            while j < n and text[j] != '"':
                j += 2 if text[j] == "\\" else 1
            for k in range(i, min(j + 1, n)):
                out[k] = "_"
            i = j + 1
            continue
        i += 1
    del clean
    return "".join(out)


def _swap_branches(text: str, masked: str) -> list[tuple[int, str, str, str]]:
    out = []
    for m in re.finditer(r"\bif\b", masked):
        line_end = masked.find("\n", m.start())
        line_end = len(masked) if line_end < 0 else line_end
        line = masked[m.start():line_end]
        mm = re.match(r"if\s+(.+?)\s+then\s+(.+?)\s+else\s+(.+)$", line)
        if mm and "if" not in mm.group(2) and "if" not in mm.group(3):
            a0 = m.start() + mm.start(2)
            orig = text[m.start():line_end]
            new = f"if {text[m.start() + mm.start(1): m.start() + mm.end(1)]} then " \
                  f"{text[m.start() + mm.start(3): m.start() + mm.end(3)]} else " \
                  f"{text[a0: m.start() + mm.end(2)]}"
            out.append((m.start(), orig, new, text[: m.start()] + new + text[line_end:]))
    return out


def generate(code: str, region: str = "code") -> list[Mutant]:
    if not code.strip():
        return []
    masked = _mask(code)
    muts: list[Mutant] = []
    seen = set()

    def add(op: str, off: int, before: str, after: str, new_text: str) -> None:
        if new_text == code or new_text in seen:
            return
        seen.add(new_text)
        muts.append(Mutant(op, region, off, before, after, new_text))

    for op, pat, rep in _SIMPLE:
        for m in re.finditer(pat, masked):
            new = code[: m.start()] + rep + code[m.end():]
            add(op, m.start(), code[m.start():m.end()], rep, new)
    for m in _NUM.finditer(masked):
        v = int(m.group(1))
        for nv in sorted({v + 1, v - 1 if v > 0 else None, 1 if v == 0 else None, 0 if v == 1 else None} - {None}):
            new = code[: m.start()] + str(nv) + code[m.end():]
            add("const", m.start(), m.group(1), str(nv), new)
    for m in _IF.finditer(masked):
        cond_s, cond_e = m.start(1), m.end(1)
        cond = code[cond_s:cond_e]
        if cond.strip():
            new = code[:cond_s] + f" ¬({cond.strip()}) " + code[cond_e:]
            add("negate_cond", cond_s, cond.strip(), f"¬({cond.strip()})", new)
        for e in _EQ_IN_IF.finditer(masked, cond_s, cond_e):
            new = code[: e.start()] + "≠" + code[e.end():]
            add("relflip", e.start(), "=", "≠", new)
    for off, before, after, new in _swap_branches(code, masked):
        add("swap_branches", off, before, after, new)
    for m in re.finditer(r"\b(min|max)\s+(\(?[\w.]+\)?)\s+(\(?[\w.]+\)?)", masked):
        a, b = code[m.start(2):m.end(2)], code[m.start(3):m.end(3)]
        if a != b:
            other = "max" if m.group(1) == "min" else "min"
            new = code[: m.start()] + f"{other} {a} {b}" + code[m.end():]
            add("swap_args", m.start(), m.group(0), f"{other} {a} {b}", new)
    return muts
