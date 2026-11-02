"""Lightweight Lean 4 source utilities: comment/string stripping and name discovery.

These are deliberately conservative text-level tools (no Lean parser). They are used by the
integrity scanner, the hint extractor and the code-feature extractor.
"""
from __future__ import annotations

import re


def strip_comments_and_strings(src: str, keep_strings: bool = False) -> str:
    """Remove `--` line comments and nested `/- -/` block comments; blank string/char contents.

    Newlines are preserved so line numbers stay meaningful.
    """
    out: list[str] = []
    i, n = 0, len(src)
    depth = 0
    while i < n:
        c = src[i]
        nxt = src[i + 1] if i + 1 < n else ""
        if depth > 0:
            if c == "/" and nxt == "-":
                depth += 1
                i += 2
                continue
            if c == "-" and nxt == "/":
                depth -= 1
                i += 2
                continue
            if c == "\n":
                out.append("\n")
            i += 1
            continue
        if c == "/" and nxt == "-":
            depth = 1
            i += 2
            continue
        if c == "-" and nxt == "-":
            while i < n and src[i] != "\n":
                i += 1
            continue
        if c == '"':
            j = i + 1
            while j < n and src[j] != '"':
                j += 2 if src[j] == "\\" else 1
            out.append(src[i:j + 1] if keep_strings else '""')
            i = j + 1
            continue
        if c == "'" and i + 2 < n and (src[i + 2] == "'" or (src[i + 1] == "\\" and i + 3 < n and src[i + 3] == "'")):
            # char literal 'a' or '\n' (identifiers like x' are not followed by a closing quote soon)
            prev = src[i - 1] if i > 0 else " "
            if not (prev.isalnum() or prev in "_'"):
                j = i + 3 if src[i + 1] == "\\" else i + 2
                out.append(src[i:j + 1] if keep_strings else "' '")
                i = j + 1
                continue
        out.append(c)
        i += 1
    return "".join(out)


_IDENT = r"[A-Za-z_À-ɏͰ-Ͽ][\w.'!?À-ɏͰ-Ͽ]*"
_TOP_DECL = re.compile(
    r"^(?:@\[[^\]]*\]\s*)?(?:(?:private|protected|noncomputable|partial|unsafe|nonrec)\s+)*"
    r"(def|abbrev|theorem|lemma|example|instance|structure|inductive|class|opaque|axiom)\b\s*(" + _IDENT + r")?",
    re.M,
)
_LET_REC = re.compile(r"\blet\s+rec\s+(" + _IDENT + r")")
_WHERE_BLOCK = re.compile(r"^\s*where\s*$|\bwhere\s*\n", re.M)
_WHERE_DEF = re.compile(r"^\s+(" + _IDENT + r")\s*(?:\(|\{|\[|:|:=)", re.M)


def top_level_decls(src: str) -> list[tuple[str, str | None]]:
    """List of (keyword, name) for top-level declarations (column-0 commands)."""
    clean = strip_comments_and_strings(src)
    return [(m.group(1), m.group(2)) for m in _TOP_DECL.finditer(clean)]


def let_rec_names(src: str) -> list[str]:
    return _LET_REC.findall(strip_comments_and_strings(src))


def where_names(src: str) -> list[str]:
    clean = strip_comments_and_strings(src)
    m = _WHERE_BLOCK.search(clean)
    if not m:
        return []
    tail = clean[m.end():]
    names = []
    for mm in _WHERE_DEF.finditer(tail):
        nm = mm.group(1)
        if nm not in {"if", "then", "else", "match", "with", "let", "fun", "do", "return", "termination_by", "decreasing_by"}:
            names.append(nm)
    return names


def helper_names(fn: str, code_aux: str, code: str, aux_names: list[str]) -> list[str]:
    """Names to unfold in the portfolio: locked aux decls, code_aux defs, F.<let rec/where>."""
    names: list[str] = []
    for n in aux_names:
        if n not in names:
            names.append(n)
    for kw, n in top_level_decls(code_aux):
        if n and kw in {"def", "abbrev"} and n not in names:
            names.append(n)
    for n in let_rec_names(code) + where_names(code):
        q = f"{fn}.{n}"
        if q not in names:
            names.append(q)
    for n in let_rec_names(code_aux):
        # let rec inside a helper def: qualified by that helper; we cannot know which without parsing,
        # so only the bare name is skipped (unfolding the helper exposes it).
        pass
    return names


def calls(src: str, name: str) -> bool:
    short = name.split(".")[-1]
    clean = strip_comments_and_strings(src)
    return re.search(r"(?<![\w.])" + re.escape(short) + r"(?![\w'])", clean) is not None


def def_bodies(code_aux: str) -> dict[str, str]:
    """Map helper name -> its text (from its def line to the next column-0 command)."""
    clean = strip_comments_and_strings(code_aux)
    ms = list(_TOP_DECL.finditer(clean))
    out = {}
    for i, m in enumerate(ms):
        end = ms[i + 1].start() if i + 1 < len(ms) else len(clean)
        if m.group(2):
            out[m.group(2)] = clean[m.end():end]
    return out


def recursive_functions(fn: str, code_aux: str, code: str) -> list[str]:
    """F if its body mentions F; helpers whose body mentions themselves; F.<let rec> names."""
    out = []
    if calls(code, fn):
        out.append(fn)
    for n, body in def_bodies(code_aux).items():
        if calls(body, n):
            out.append(n)
    for n in let_rec_names(code) + where_names(code):
        out.append(f"{fn}.{n}")
    seen: list[str] = []
    for n in out:
        if n not in seen:
            seen.append(n)
    return seen
