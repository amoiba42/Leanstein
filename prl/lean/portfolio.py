"""Expand the pre-registered two-tier tactic portfolio for a given family and candidate."""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from prl.config import PATHS, load_yaml, sha256_file
from prl.lean import leantext as LT
from prl.testgen.literals import parse_type


@dataclass(frozen=True)
class Entry:
    id: str
    script: str
    tier: str = "H"
    heartbeats: int = 200000


@dataclass(frozen=True)
class Portfolio:
    version: int
    max_entries: int
    tiers: tuple[tuple[str, int], ...]  # ordered (tier, heartbeats)
    templates: tuple[dict, ...]
    sha256: str
    single_call_automation: frozenset[str] = frozenset()

    def heartbeats(self, tier: str) -> int:
        return dict(self.tiers)[tier]

    @property
    def max_heartbeats(self) -> int:
        return max(h for _, h in self.tiers)


@lru_cache(maxsize=4)
def load_portfolio(path: str | None = None) -> Portfolio:
    p = Path(path) if path else PATHS.prereg / "portfolio.yaml"
    d = load_yaml(p)
    tiers = tuple((k, int(v["heartbeats"])) for k, v in d["tiers"].items())
    for k, hb in tiers:
        if hb <= 0:  # maxHeartbeats 0 = unbounded: only the explicit test guards may use it
            raise ValueError(f"portfolio tier {k} must have positive heartbeats, got {hb}")
    known = {k for k, _ in tiers}
    for e in d["entries"]:
        if e.get("tier") not in known:
            raise ValueError(f"portfolio entry {e['id']} has unknown tier {e.get('tier')}")
    return Portfolio(int(d["version"]), int(d["max_entries"]), tiers, tuple(d["entries"]), sha256_file(p),
                     frozenset(d.get("single_call_automation", [])))


def inductive_params(params: list[tuple[str, str]]) -> list[str]:
    out = []
    for name, ty in params:
        try:
            t = parse_type(ty)
        except ValueError:
            continue
        if t.head in {"List", "Nat"}:
            out.append(name)
    return out


def expand(pf: Portfolio, *, fn: str, params: list[tuple[str, str]], code_aux: str, code: str,
           aux_names: list[str]) -> list[Entry]:
    """All tier-L entries (in YAML order), then all tier-H entries; capped at `max_entries`."""
    helpers = LT.helper_names(fn, code_aux, code, aux_names)
    H = "".join(", " + h for h in helpers)
    base = {"F": fn, "P": f"{fn}_postcond", "Q": f"{fn}_precond", "H": H}
    rec = LT.recursive_functions(fn, code_aux, code)
    ind = inductive_params(params)
    out: list[Entry] = []
    for tier, hb in pf.tiers:
        for t in (t for t in pf.templates if t["tier"] == tier):
            each = t.get("foreach")
            if each is None:
                out.append(Entry(t["id"], _fmt(t["script"], base), tier, hb))
            elif each == "R":
                for r in rec:
                    u = "" if r == fn else f"unfold {fn} {base['P']}\n"
                    out.append(Entry(f"{t['id']}@{r}", _fmt(t["script"], {**base, "R": r, "U": u}), tier, hb))
            elif each == "x":
                for x in ind:
                    out.append(Entry(f"{t['id']}@{x}", _fmt(t["script"], {**base, "x": x}), tier, hb))
            else:
                raise ValueError(f"unknown foreach {each}")
    return out[: pf.max_entries]


def _fmt(s: str, v: dict[str, str]) -> str:
    out = s
    for k, val in v.items():
        out = out.replace("{" + k + "}", val)
    return out
