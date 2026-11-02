"""Task instances (mutant / natural / shaping) and their manifests."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from prl.config import PATHS, read_json, write_json


@dataclass
class Instance:
    instance_id: str
    family_id: str
    kind: str  # mutant | natural | shaping
    start: dict[str, str]  # code_aux, code
    split: str = "unassigned"
    provenance: dict[str, Any] = field(default_factory=dict)
    witness: dict[str, Any] | None = None  # {"source","index","input_lean","expected","actual"}
    start_T: dict[str, Any] = field(default_factory=dict)
    hashes: dict[str, str] = field(default_factory=dict)
    flags: list[str] = field(default_factory=list)

    def witness_line(self, fn: str) -> str | None:
        w = self.witness
        if not w or w.get("source") != "visible":
            return None
        return format_witness(fn, w["input_lean"], w["expected"], w.get("actual"))

    def to_json(self) -> dict[str, Any]:
        return asdict(self)

    @staticmethod
    def from_json(d: dict[str, Any]) -> Instance:
        return Instance(**d)


def format_witness(fn: str, inp: dict[str, str], expected: str, actual: str | None) -> str:
    args = ", ".join(f"{k} := {v}" for k, v in inp.items())
    got = f" returned {actual}," if actual else ""
    return f"Failing test: {fn} ({args}){got} expected {expected}."


def save(inst: Instance) -> None:
    write_json(PATHS.instances / f"{inst.instance_id}.json", inst.to_json())


def load(iid: str) -> Instance:
    return Instance.from_json(read_json(PATHS.instances / f"{iid}.json"))


def load_all(kind: str | None = None, split: str | None = None) -> list[Instance]:
    out = []
    for p in sorted(PATHS.instances.glob("*.json")):
        i = Instance.from_json(read_json(p))
        if (kind is None or i.kind == kind) and (split is None or i.split == split):
            out.append(i)
    return out
