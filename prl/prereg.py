"""Pre-registration freeze (SR-PRE-1/2): hash every file under prereg/ except FREEZE.json and deviations.md."""
from __future__ import annotations

import subprocess
import time

from prl.config import PATHS, read_json, sha256_file, sha256_text, write_json

EXCLUDED = {"FREEZE.json", "deviations.md"}


def prereg_files() -> list:
    return sorted(p for p in PATHS.prereg.rglob("*") if p.is_file() and p.name not in EXCLUDED)


def current_hashes() -> dict[str, str]:
    return {p.relative_to(PATHS.prereg).as_posix(): sha256_file(p) for p in prereg_files()}


def _git_commit() -> str:
    try:
        return subprocess.run(["git", "rev-parse", "HEAD"], cwd=PATHS.root, capture_output=True, text=True).stdout.strip()
    except Exception:  # noqa: BLE001
        return ""


def freeze(note: str = "") -> dict:
    h = current_hashes()
    rec = {"files": h, "digest": sha256_text("\n".join(f"{k}:{v}" for k, v in sorted(h.items()))),
           "frozen_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "git_commit": _git_commit(), "note": note}
    write_json(PATHS.prereg / "FREEZE.json", rec)
    return rec


def freeze_status() -> tuple[bool, list[str], str]:
    p = PATHS.prereg / "FREEZE.json"
    if not p.exists():
        return False, ["FREEZE.json missing"], ""
    rec = read_json(p)
    cur = current_hashes()
    diffs = sorted({k for k in set(cur) | set(rec["files"]) if cur.get(k) != rec["files"].get(k)})
    return not diffs, diffs, rec["digest"]
