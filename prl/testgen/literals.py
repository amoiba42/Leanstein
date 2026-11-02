"""Lean type parsing, literal rendering, and random value generation for tests."""
from __future__ import annotations

import json
import random
import re
from dataclasses import dataclass


@dataclass(frozen=True)
class LType:
    head: str  # Int, Nat, Bool, Char, String, UInt8, Float, List, Array, Option, Prod, Unsupported
    args: tuple[LType, ...] = ()

    def __str__(self) -> str:  # pragma: no cover - debug aid
        if not self.args:
            return self.head
        if self.head == "Prod":
            return f"({self.args[0]} × {self.args[1]})"
        return f"{self.head} ({' '.join(map(str, self.args))})"


SCALARS = {"Int", "Nat", "Bool", "Char", "String", "UInt8", "Float"}
UNARY = {"List", "Array", "Option"}


def _tokens(s: str) -> list[str]:
    s = s.replace("×", " × ").replace("(", " ( ").replace(")", " ) ").replace(",", " , ")
    return s.split()


def parse_type(s: str) -> LType:
    toks = _tokens(s)
    pos = 0

    def peek() -> str | None:
        return toks[pos] if pos < len(toks) else None

    def take() -> str:
        nonlocal pos
        t = toks[pos]
        pos += 1
        return t

    def atom() -> LType:
        t = peek()
        if t is None:
            raise ValueError(f"unexpected end in type {s!r}")
        if t == "(":
            take()
            inner = prod()
            if peek() == ",":  # (A, B) style is not Lean, but be lenient
                take()
                inner = LType("Prod", (inner, prod()))
            if take() != ")":
                raise ValueError(f"bad parens in {s!r}")
            return inner
        take()
        if t in SCALARS:
            return LType(t)
        if t in UNARY:
            return LType(t, (atom(),))
        if t == "Prod":
            a = atom()
            b = atom()
            return LType("Prod", (a, b))
        args = [LType(t)]
        while peek() not in (None, ")", "×", ","):
            args.append(atom())
        return LType("Unsupported", tuple(args))

    def prod() -> LType:
        left = atom()
        if peek() == "×":
            take()
            right = prod()
            return LType("Prod", (left, right))
        return left

    t = prod()
    if pos != len(toks):
        raise ValueError(f"trailing tokens in type {s!r}")
    return t


def supported(t: LType) -> bool:
    if t.head == "Unsupported":
        return False
    return all(supported(a) for a in t.args)


def has_float(t: LType) -> bool:
    return t.head == "Float" or any(has_float(a) for a in t.args)


# --------------------------------------------------------------------------- rendering


def _lean_string(s: str) -> str:
    return json.dumps(s, ensure_ascii=False)


def _lean_char(c: str) -> str:
    esc = {"\\": "\\\\", "'": "\\'", "\n": "\\n", "\t": "\\t"}
    return "'" + esc.get(c, c) + "'"


def render(t: LType, v: object) -> str:
    """Render a JSON test value of type ``t`` as a Lean term (parenthesised when needed)."""
    h = t.head
    if isinstance(v, str) and h in {"Array", "List", "Option", "Prod", "Int", "Nat", "Float", "UInt8"}:
        # VERINA stores some values pre-rendered (e.g. "#[1, 2]").
        return "(" + v + ")" if v.strip().startswith("-") else v
    if h == "Bool":
        return "true" if v else "false"
    if h in {"Int", "Nat", "UInt8"}:
        iv = int(v)  # type: ignore[arg-type]
        return f"({iv})" if iv < 0 else str(iv)
    if h == "Float":
        fv = float(v)  # type: ignore[arg-type]
        return f"({fv})" if fv < 0 else repr(fv)
    if h == "String":
        return _lean_string(str(v))
    if h == "Char":
        return _lean_char(str(v))
    if h == "List":
        return "[" + ", ".join(render(t.args[0], x) for x in v) + "]"  # type: ignore[union-attr]
    if h == "Array":
        return "#[" + ", ".join(render(t.args[0], x) for x in v) + "]"  # type: ignore[union-attr]
    if h == "Option":
        return "none" if v is None else f"(some {render(t.args[0], v)})"
    if h == "Prod":
        a, b = v  # type: ignore[misc]
        return f"({render(t.args[0], a)}, {render(t.args[1], b)})"
    raise ValueError(f"cannot render type {t}")


# --------------------------------------------------------------------------- random values

_ALPHA = "abcxyzAB0 "


def random_value(t: LType, rng: random.Random, size: int = 6) -> object:
    h = t.head
    if h == "Int":
        return rng.choice([0, 1, -1, 2, -2, 3, 5, -7, 10, -10, rng.randint(-30, 30), rng.randint(-100, 100)])
    if h == "Nat":
        return rng.choice([0, 1, 2, 3, 4, 5, 7, 10, rng.randint(0, 30), rng.randint(0, 100)])
    if h == "UInt8":
        return rng.choice([0, 1, 2, 9, 10, 48, 57, 65, 97, 127, 255])
    if h == "Bool":
        return rng.random() < 0.5
    if h == "Char":
        return rng.choice("abzAZ09 ")
    if h == "String":
        n = rng.choice([0, 1, 2, 3, 4, size])
        return "".join(rng.choice(_ALPHA) for _ in range(n))
    if h == "Float":
        return round(rng.uniform(-10, 10), 2)
    if h in {"List", "Array"}:
        n = rng.choice([0, 1, 2, 3, size, rng.randint(0, size + 2)])
        xs = [random_value(t.args[0], rng, max(1, size // 2)) for _ in range(n)]
        if n >= 2 and rng.random() < 0.25:  # duplicates are a common edge case
            xs[rng.randrange(n)] = xs[0]
        return xs
    if h == "Option":
        return None if rng.random() < 0.3 else random_value(t.args[0], rng, size)
    if h == "Prod":
        return [random_value(t.args[0], rng, size), random_value(t.args[1], rng, size)]
    raise ValueError(f"cannot generate {t}")


_NEG_NUM = re.compile(r"^-\d")


def is_negative_literal(s: str) -> bool:
    return bool(_NEG_NUM.match(s.strip()))
