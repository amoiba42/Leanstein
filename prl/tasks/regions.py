"""The VERINA region model: parse `-- !benchmark @start/@end` regions, render replacements,
and compute the hash of the locked (non-replaceable) part of a template.

Invariant (tested): ``locked_hash(render(t, r)) == locked_hash(t)`` for any replacements ``r``
of replaceable regions that do not contain region markers.
"""
from __future__ import annotations

import re
import textwrap
from dataclasses import dataclass

from prl.config import sha256_text

REGION_NAMES = (
    "import", "solution_aux", "precond_aux", "precond", "code_aux", "code",
    "postcond_aux", "postcond", "proof_aux", "proof",
)
REPLACEABLE_CODE = ("code_aux", "code")
REPLACEABLE_PROOF = ("proof_aux", "proof")
REPLACEABLE = REPLACEABLE_CODE + REPLACEABLE_PROOF
INDENTED = ("code", "proof", "precond", "postcond")

_START = re.compile(r"^[ \t]*-- !benchmark @start (\w+)[^\n]*\n", re.M)
MARKER = "!benchmark"


@dataclass(frozen=True)
class Region:
    name: str
    start: int  # offset of first content char (just after the @start line)
    end: int  # offset of the @end line start
    content: str


class RegionError(ValueError):
    pass


def parse_regions(text: str) -> dict[str, Region]:
    regions: dict[str, Region] = {}
    for m in _START.finditer(text):
        name = m.group(1)
        end_re = re.compile(r"^[ \t]*-- !benchmark @end " + re.escape(name) + r"\b", re.M)
        e = end_re.search(text, m.end())
        if not e:
            raise RegionError(f"unterminated region {name}")
        key = name
        if name in regions:
            if name != "import":  # VERINA repeats only `import` regions (type=task / type=solution)
                raise RegionError(f"duplicate region {name}")
            k = 2
            while f"import#{k}" in regions:
                k += 1
            key = f"import#{k}"
        regions[key] = Region(name, m.end(), e.start(), text[m.end():e.start()])
    return regions


def normalise_block(s: str, indent: int) -> str:
    """Dedent, strip blank edges, re-indent by ``indent`` spaces, ensure trailing newline."""
    s = s.replace("\r\n", "\n").replace("\t", "  ")
    lines = s.split("\n")
    while lines and not lines[0].strip():
        lines.pop(0)
    while lines and not lines[-1].strip():
        lines.pop()
    if not lines:
        return ""
    body = textwrap.dedent("\n".join(lines))
    pad = " " * indent
    return "\n".join((pad + ln) if ln.strip() else "" for ln in body.split("\n")) + "\n"


def render(template: str, replacements: dict[str, str]) -> str:
    """Replace the contents of the named regions. Only replaceable regions may be replaced."""
    regions = parse_regions(template)
    for name, val in replacements.items():
        if name not in REPLACEABLE:
            raise RegionError(f"region {name} is locked")
        if name not in regions:
            raise RegionError(f"template has no region {name}")
        if MARKER in val:
            raise RegionError("replacement contains a region marker")
    out = template
    for name in sorted(replacements, key=lambda n: regions[n].start, reverse=True):
        r = regions[name]
        val = normalise_block(replacements[name], 2 if name in INDENTED else 0)
        out = out[: r.start] + val + out[r.end:]
    return out


def locked_view(template: str) -> str:
    regions = parse_regions(template)
    out = template
    for name in sorted((n for n in REPLACEABLE if n in regions), key=lambda n: regions[n].start, reverse=True):
        r = regions[name]
        out = out[: r.start] + out[r.end:]
    return out


def locked_hash(template: str) -> str:
    return sha256_text(locked_view(template))


def region_text(template: str, name: str) -> str:
    regs = parse_regions(template)
    if name == "import":
        return "".join(r.content for k, r in regs.items() if r.name == "import")
    r = regs.get(name)
    return r.content if r else ""


def theorem_statement(template: str, fn: str) -> str:
    """Return the locked theorem statement after its name, e.g. ``(a : Int) ... : P a (f a h) h``.

    The statement ends at the ``:= by`` that precedes the proof region.
    """
    regions = parse_regions(template)
    if "proof" not in regions:
        raise RegionError("no proof region")
    head = template[: regions["proof"].start]
    m = list(re.finditer(r"^theorem\s+" + re.escape(fn) + r"_spec_satisfied\b", head, re.M))
    if not m:
        raise RegionError("theorem not found")
    stmt = head[m[-1].end():]
    k = stmt.rfind(":= by")
    if k < 0:
        raise RegionError("theorem has no ':= by'")
    return stmt[:k].strip()


def def_header(template: str, fn: str) -> str:
    """Locked function header text from ``def fn`` up to and including ``:=``."""
    regions = parse_regions(template)
    head = template[: regions["code"].start]
    m = list(re.finditer(r"^def\s+" + re.escape(fn) + r"\b", head, re.M))
    if not m:
        raise RegionError("def not found")
    hdr = head[m[-1].start():].rstrip("\n")
    # drop the trailing `-- !benchmark @start code` marker line
    hdr = hdr[: hdr.rfind("\n")] if "\n" in hdr else hdr
    return hdr.rstrip()
