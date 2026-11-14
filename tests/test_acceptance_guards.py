"""Acceptance guards: a modified prereg/ file is refused (SR-PRE-1/2)."""
from __future__ import annotations

import dataclasses
import shutil

import pytest

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
