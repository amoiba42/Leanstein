"""Paths, frozen configuration, hashing and the pinned Lean environment."""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml


def _find_root() -> Path:
    here = Path(__file__).resolve()
    for p in [here, *here.parents]:
        if (p / "pyproject.toml").exists() and (p / "prl").is_dir():
            return p
    raise RuntimeError("cannot locate repository root")


ROOT = _find_root()


@dataclass(frozen=True)
class Paths:
    root: Path = ROOT
    docs: Path = ROOT / "docs"
    prereg: Path = ROOT / "prereg"
    prompts: Path = ROOT / "prereg" / "prompts"
    lean_env: Path = ROOT / "lean_env"
    verina: Path = ROOT / "third_party" / "verina"
    verina_tasks: Path = ROOT / "third_party" / "verina" / "datasets" / "verina"
    data: Path = ROOT / "data"
    families: Path = ROOT / "data" / "families"
    hidden: Path = ROOT / "data" / "hidden"
    instances: Path = ROOT / "data" / "instances"
    provenance: Path = ROOT / "data" / "provenance"
    cache: Path = ROOT / "cache"
    runs: Path = ROOT / "runs"
    results: Path = ROOT / "results"


PATHS = Paths()


def ensure_dir(p: Path) -> Path:
    p.mkdir(parents=True, exist_ok=True)
    return p


def sha256_text(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha256_file(p: Path, chunk: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        while True:
            b = f.read(chunk)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def load_yaml(p: Path) -> Any:
    with open(p, encoding="utf-8") as f:
        return yaml.safe_load(f)


def read_json(p: Path) -> Any:
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def write_json(p: Path, obj: Any) -> None:
    ensure_dir(p.parent)
    tmp = p.with_suffix(p.suffix + ".tmp")
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        json.dump(obj, f, indent=1, ensure_ascii=False, sort_keys=True)
        f.write("\n")
    os.replace(tmp, p)


# --------------------------------------------------------------------------- study config

_STUDY_KEYS = {
    "study_id", "lean", "budget", "decoding", "c_round_k", "history_turns", "seeds", "models",
    "conditions", "shaping_conditions", "splits", "mutants_per_family", "hidden_tests", "analysis",
    "natural", "specialist_conditions", "bugs", "energy",
}


@lru_cache(maxsize=4)
def study_config(path: str | None = None) -> dict[str, Any]:
    p = Path(path) if path else PATHS.prereg / "study.yaml"
    cfg = load_yaml(p)
    unknown = set(cfg) - _STUDY_KEYS
    if unknown:
        raise ValueError(f"unknown keys in {p}: {sorted(unknown)}")
    return cfg


# --------------------------------------------------------------------------- Lean environment


@dataclass(frozen=True)
class LeanEnv:
    lean_exe: str
    lean_path: str
    toolchain_id: str

    def env(self) -> dict[str, str]:
        e = dict(os.environ)
        e["LEAN_PATH"] = self.lean_path
        return e


def _elan_bin() -> Path:
    return Path.home() / ".elan" / "bin"


@lru_cache(maxsize=1)
def lean_env() -> LeanEnv:
    """Resolve the pinned Lean binary and LEAN_PATH once (cached on disk by manifest hash)."""
    manifest = PATHS.lean_env / "lake-manifest.json"
    toolchain = (PATHS.lean_env / "lean-toolchain").read_text().strip()
    key = sha256_text(toolchain + sha256_file(manifest))
    cache_file = PATHS.cache / "lean_env.json"
    if cache_file.exists():
        c = read_json(cache_file)
        if c.get("key") == key and Path(c["lean_exe"]).exists():
            return LeanEnv(c["lean_exe"], c["lean_path"], c["toolchain_id"])
    lake = shutil.which("lake") or str(_elan_bin() / ("lake.exe" if os.name == "nt" else "lake"))
    env = dict(os.environ)
    env["PATH"] = str(_elan_bin()) + os.pathsep + env.get("PATH", "")
    out = subprocess.run(
        [lake, "env", "printenv", "LEAN_PATH"], cwd=PATHS.lean_env, env=env,
        capture_output=True, text=True, timeout=600,
    )
    if out.returncode != 0:
        # `printenv` may be unavailable on Windows; fall back to python inside lake env
        out = subprocess.run(
            [lake, "env", "python", "-c", "import os;print(os.environ['LEAN_PATH'])"],
            cwd=PATHS.lean_env, env=env, capture_output=True, text=True, timeout=600,
        )
    if out.returncode != 0:
        raise RuntimeError(f"cannot resolve LEAN_PATH: {out.stderr}")
    lean_path = out.stdout.strip().splitlines()[-1]
    tc_dir = Path.home() / ".elan" / "toolchains" / toolchain.replace("/", "--").replace(":", "---")
    lean_exe = tc_dir / "bin" / ("lean.exe" if os.name == "nt" else "lean")
    if not lean_exe.exists():
        raise RuntimeError(f"lean binary not found at {lean_exe}")
    mathlib_rev = next(
        p["rev"] for p in read_json(manifest)["packages"] if p["name"] == "mathlib"
    )
    tid = f"{toolchain}+mathlib@{mathlib_rev}"
    write_json(cache_file, {"key": key, "lean_exe": str(lean_exe), "lean_path": lean_path, "toolchain_id": tid})
    return LeanEnv(str(lean_exe), lean_path, tid)
