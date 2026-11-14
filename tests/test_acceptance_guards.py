"""Acceptance guards: a modified prereg/ file is refused (SR-PRE-1/2), and a hung Lean process is killed
with its whole process tree within the wall guard (NFR-REL-2)."""
from __future__ import annotations

import dataclasses
import os
import shutil
import sys
import time

import psutil
import pytest

import prl.lean.runner as lean_runner
import prl.prereg as prereg
from prl.cli import main
from prl.config import PATHS
from prl.driver.runner import FreezeError, check_freeze


@pytest.fixture
def prereg_copy(tmp_path, monkeypatch):
    """A private copy of prereg/ so the test can modify a frozen file without touching the real one.
    Line endings are normalised to LF, the form in which the files were frozen."""
    dst = tmp_path / "prereg"
    shutil.copytree(PATHS.prereg, dst)
    for p in dst.rglob("*"):
        if p.is_file():
            p.write_bytes(p.read_bytes().replace(b"\r\n", b"\n"))
    monkeypatch.setattr(prereg, "PATHS", dataclasses.replace(PATHS, prereg=dst))
    return dst


def test_untouched_prereg_matches_freeze(prereg_copy):
    ok, diffs, digest = prereg.freeze_status()
    assert ok and diffs == []
    assert check_freeze() == digest


def test_modified_prereg_file_is_reported_and_refused(prereg_copy):
    with (prereg_copy / "study.yaml").open("ab") as fh:
        fh.write(b"\n# one changed byte\n")
    ok, diffs, _ = prereg.freeze_status()
    assert not ok and diffs == ["study.yaml"]
    with pytest.raises(FreezeError, match="study.yaml"):
        check_freeze()


def test_added_or_removed_prereg_file_is_reported(prereg_copy):
    (prereg_copy / "prompts" / "extra.txt").write_text("x", encoding="utf-8")
    (prereg_copy / "hints.yaml").unlink()
    ok, diffs, _ = prereg.freeze_status()
    assert not ok and diffs == ["hints.yaml", "prompts/extra.txt"]


def test_deviation_log_is_not_frozen(prereg_copy):
    with (prereg_copy / "deviations.md").open("ab") as fh:
        fh.write(b"\nD-99. A later deviation.\n")
    assert prereg.freeze_status()[0]


@pytest.mark.parametrize("split", ["main", "heldout"])
def test_cli_refuses_confirmatory_run_on_modified_prereg(prereg_copy, split, capsys):
    with (prereg_copy / "prompts" / "C.txt").open("ab") as fh:
        fh.write(b" ")
    assert main(["run", "--study", "guard-test", "--split", split]) == 2
    assert "REFUSING TO RUN" in capsys.readouterr().out
    assert not (PATHS.runs / "guard-test").exists()


# --------------------------------------------------------------------------- NFR-REL-2

# Stands in for a hung Lean: the "lean" binary is the Python interpreter and Main.lean is this script.
# It starts a grandchild, records both process ids, and then both sleep far beyond the wall guard.
_HANG = """
import os, subprocess, sys, time
child = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(600)"])
with open({pidfile!r}, "w") as fh:
    fh.write(str(os.getpid()) + " " + str(child.pid))
time.sleep(600)
"""


class _FakeLeanEnv:
    lean_exe = sys.executable

    def env(self) -> dict[str, str]:
        return dict(os.environ)


def _alive(pid: int) -> bool:
    try:
        return psutil.Process(pid).status() != psutil.STATUS_ZOMBIE
    except psutil.NoSuchProcess:
        return False


def test_hung_lean_process_tree_is_killed_within_wall_guard(tmp_path, monkeypatch):
    monkeypatch.setattr(lean_runner, "lean_env", lambda: _FakeLeanEnv())
    monkeypatch.setattr(lean_runner, "PATHS", dataclasses.replace(PATHS, cache=tmp_path / "cache"))
    pidfile = tmp_path / "pids.txt"
    wall_s = 3.0
    t0 = time.perf_counter()
    r = lean_runner.run_lean_cli(_HANG.format(pidfile=str(pidfile)), wall_s=wall_s)
    took = time.perf_counter() - t0
    assert r.timeout and r.infra_error is None
    assert wall_s <= took < wall_s + 10, f"returned after {took:.1f} s"
    parent, child = (int(x) for x in pidfile.read_text().split())
    deadline = time.time() + 5
    while time.time() < deadline and (_alive(parent) or _alive(child)):
        time.sleep(0.1)
    assert not _alive(parent), "the hung process survived the wall guard"
    assert not _alive(child), "a child of the hung process survived the wall guard"
    assert not any((tmp_path / "cache" / "tmp").iterdir()), "the work directory was not removed"
