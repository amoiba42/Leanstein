"""Load VERINA tasks into `Family` records."""
from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from prl.config import PATHS, read_json, sha256_text, write_json
from prl.tasks import regions as R
from prl.testgen import literals as L

VERINA_COMMIT = "66b3ce5014edafb20cb26b87c681e7f31847249f"


@dataclass
class Signature:
    name: str
    params: list[tuple[str, str]]
    ret: str


@dataclass
class Family:
    family_id: str
    tier: str
    signature: Signature
    template: str
    description: str
    visible_tests: list[dict[str, Any]]  # {"input_lean": {p: lit}, "expected_lean": lit}
    theorem_stmt: str
    header: str
    locked_hash: str
    aux_names: list[str] = field(default_factory=list)  # names declared in locked aux regions
    ref: dict[str, Any] = field(default_factory=dict)
    eligible: bool | None = None
    exclusion_reason: str | None = None
    flags: list[str] = field(default_factory=list)

    # ------------------------------------------------------------------ derived helpers
    @property
    def fn(self) -> str:
        return self.signature.name

    @property
    def precond_name(self) -> str:
        return f"{self.fn}_precond"

    @property
    def postcond_name(self) -> str:
        return f"{self.fn}_postcond"

    def region(self, name: str) -> str:
        return R.region_text(self.template, name)

    @property
    def ref_code(self) -> dict[str, str]:
        return {"code_aux": self.region("code_aux"), "code": self.region("code")}

    def to_json(self) -> dict[str, Any]:
        d = asdict(self)
        d["signature"]["params"] = [list(p) for p in self.signature.params]
        return d

    @staticmethod
    def from_json(d: dict[str, Any]) -> Family:
        d = dict(d)
        s = d.pop("signature")
        sig = Signature(s["name"], [tuple(p) for p in s["params"]], s["ret"])  # type: ignore[misc]
        return Family(signature=sig, **d)


_DECL = re.compile(r"^\s*(?:@\[[^\]]*\]\s*)?(?:noncomputable\s+)?(?:def|abbrev|theorem|lemma|structure|inductive|instance\s+\w*|class)\s+([A-Za-z_][\w.']*)", re.M)


def declared_names(text: str) -> list[str]:
    return [m.group(1) for m in _DECL.finditer(text)]


def _render_tests(sig: Signature, tests: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    for t in tests:
        inp = {}
        for pname, ptype in sig.params:
            inp[pname] = L.render(L.parse_type(ptype), t["input"][pname])
        exp = L.render(L.parse_type(sig.ret), t["expected"])
        out.append({"input_lean": inp, "expected_lean": exp})
    return out


def load_family(task_dir: Path) -> Family:
    meta = json.loads((task_dir / "task.json").read_text(encoding="utf-8"))
    template = (task_dir / "task.lean").read_text(encoding="utf-8").replace("\r\n", "\n")
    desc = (task_dir / "description.txt").read_text(encoding="utf-8").strip()
    s = meta["signature"]
    sig = Signature(s["name"], [(p["param_name"], p["param_type"]) for p in s["parameters"]], s["return_type"])
    fid = meta["id"]
    flags: list[str] = []
    try:
        vis = _render_tests(sig, json.loads((task_dir / "test.json").read_text(encoding="utf-8")))
    except Exception as e:  # noqa: BLE001
        vis = []
        flags.append(f"visible_tests_unrenderable:{type(e).__name__}")
    aux = []
    for rn in ("solution_aux", "precond_aux", "postcond_aux"):
        aux += declared_names(R.region_text(template, rn))
    return Family(
        family_id=fid,
        tier="basic" if "basic" in fid else "advanced",
        signature=sig,
        template=template,
        description=desc,
        visible_tests=vis,
        theorem_stmt=R.theorem_statement(template, sig.name),
        header=R.def_header(template, sig.name),
        locked_hash=R.locked_hash(template),
        aux_names=aux,
        flags=flags,
    )


def load_all(verina_dir: Path = PATHS.verina_tasks) -> list[Family]:
    dirs = sorted(p for p in verina_dir.iterdir() if p.is_dir() and p.name.startswith("verina_"))
    return [load_family(d) for d in dirs]


def family_path(fid: str) -> Path:
    return PATHS.families / f"{fid}.json"


def save_family(f: Family) -> None:
    write_json(family_path(f.family_id), f.to_json())


def get_family(fid: str) -> Family:
    """Saved family (with reference status) if `prl tasks build/check` has run, else parsed from VERINA."""
    p = family_path(fid)
    if p.exists():
        return Family.from_json(read_json(p))
    return load_family(PATHS.verina_tasks / fid)


def all_saved() -> list[Family]:
    return [Family.from_json(read_json(p)) for p in sorted(PATHS.families.glob("*.json"))]


def verina_fingerprint(verina_dir: Path = PATHS.verina_tasks) -> str:
    parts = []
    for p in sorted(verina_dir.rglob("task.lean")):
        parts.append(p.parent.name + ":" + sha256_text(p.read_text(encoding="utf-8")))
    return sha256_text("\n".join(parts))
