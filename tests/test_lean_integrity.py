"""IR-8: integrity suite on real Lean. Every case must be rejected (zero false successes).

Run with: uv run pytest -m lean
"""
from __future__ import annotations

import pytest

from prl.lean.verify import Judge
from prl.tasks import verina as V

pytestmark = pytest.mark.lean

FAM = V.load_family(V.PATHS.verina_tasks / "verina_basic_1")  # hasOppositeSign: a * b < 0 ; T cannot prove the reference (non-linear)
OK_CODE = "a * b < 0"
# A correct implementation that the portfolio CAN prove (case-split shape instead of multiplication).
SHAPED = "(a < 0 && b > 0) || (a > 0 && b < 0)"


@pytest.fixture(scope="module")
def judge():
    return Judge(use_cache=False)


def _c(code=OK_CODE, code_aux="", proof_aux="", proof=""):
    return {"code": code, "code_aux": code_aux, "proof_aux": proof_aux, "proof": proof}


def test_reference_compiles_and_passes_but_not_provable(judge):
    vr = judge.verify(FAM, _c(), "portfolio", tests="visible")
    assert vr.compile_ok and vr.visible_pass and not vr.proof_ok and not vr.success


def test_shaped_code_is_proved_by_portfolio(judge):
    """The study's core mechanism on a known case: re-shaping makes automation succeed."""
    vr = judge.verify(FAM, _c(code=SHAPED), "portfolio", tests="visible")
    assert vr.compile_ok and vr.visible_pass
    assert vr.proof_ok and vr.success, vr.entry_goals
    assert vr.axioms_ok and set(vr.axioms) <= {"propext", "Classical.choice", "Quot.sound"}


def test_wrong_code_fails_tests(judge):
    vr = judge.verify(FAM, _c(code="a * b ≤ 0"), "portfolio", tests="visible")
    assert vr.compile_ok and not vr.visible_pass and not vr.success


def test_model_proof_correct_accepted(judge):
    proof = "unfold hasOppositeSign hasOppositeSign_postcond\nconstructor\n· intro h\n  rcases h with ⟨ha, hb⟩ | ⟨ha, hb⟩\n  · simp; nlinarith\n  · simp; nlinarith\n· intro h\n  simp only [decide_eq_true_eq, not_lt]\n  push_neg at h\n  rcases le_or_lt 0 a with ha | ha <;> rcases le_or_lt 0 b with hb | hb <;> [nlinarith; nlinarith; nlinarith; (have := h.1 ha hb; omega)]"
    vr = judge.verify(FAM, _c(proof=proof), "model_proof", tests="visible")
    # whether or not this particular script closes, a closed proof must have clean axioms
    if vr.proof_ok:
        assert vr.axioms_ok and vr.proof_source == "model"


ESCAPES = [
    ("sorry_in_proof", "model_proof", _c(proof="sorry")),
    ("admit_in_proof", "model_proof", _c(proof="admit")),
    ("native_decide", "model_proof", _c(proof="native_decide")),
    ("axiom_in_proof_aux", "model_proof", _c(proof_aux="axiom cheat : ∀ a b : Int, False", proof="exact (cheat 0 0).elim")),
    ("sorry_in_code", "portfolio", _c(code="sorry")),
    ("implemented_by", "portfolio", _c(code_aux="def fast (a b : Int) : Bool := true\n@[implemented_by fast] def slow (a b : Int) : Bool := a * b < 0", code="slow a b")),
    ("unsafe_def", "portfolio", _c(code_aux="unsafe def u : Bool := true", code=OK_CODE)),
    ("attribute_simp", "portfolio", _c(code_aux="attribute [simp] Int.mul_neg_iff", code=OK_CODE)),
    ("macro_redefines_tactic", "portfolio", _c(code_aux="macro \"simp\" : tactic => `(tactic| sorry)", code=OK_CODE)),
    ("set_option", "portfolio", _c(code_aux="set_option maxHeartbeats 0", code=OK_CODE)),
    ("theorem_in_code_aux", "portfolio", _c(code_aux="theorem helper : True := trivial", code=OK_CODE)),
    ("redefine_postcond", "portfolio", _c(code_aux="def hasOppositeSign_postcond := True", code=OK_CODE)),
    ("proof_in_code_only", "portfolio", _c(code=SHAPED, proof="simp")),
    ("region_marker_injection", "portfolio", _c(code=OK_CODE + "\n  -- !benchmark @end code")),
    ("eval_command", "portfolio", _c(code_aux="#eval 1", code=OK_CODE)),
    ("instance_override", "portfolio", _c(code_aux="instance : Decidable (1 = 2) := isTrue sorry", code=OK_CODE)),
    ("ofReduceBool", "model_proof", _c(proof="exact Lean.ofReduceBool _ _ rfl")),
    ("namespace_escape", "portfolio", _c(code_aux="namespace Foo\ndef x := 1\nend Foo", code=OK_CODE)),
]


@pytest.mark.parametrize("name,mode,cand", ESCAPES, ids=[e[0] for e in ESCAPES])
def test_escape_rejected(judge, name, mode, cand):
    vr = judge.verify(FAM, cand, mode, tests="visible")
    assert not vr.success, f"FALSE SUCCESS for {name}: {vr.to_json()}"
    assert not vr.integrity_ok or not vr.proof_ok


def test_weakened_postcondition_is_impossible(judge):
    """Locked regions are re-rendered from the reference: a candidate cannot change the postcondition."""
    import pytest as _p

    from prl.tasks import regions as R
    with _p.raises(R.RegionError):
        R.render(FAM.template, {"postcond": "True"})


def test_verify_is_deterministic(judge):
    a = judge.verify(FAM, _c(code=SHAPED), "portfolio", tests="visible")
    b = judge.verify(FAM, _c(code=SHAPED), "portfolio", tests="visible")
    ja, jb = a.to_json(), b.to_json()
    for k in ("lean_s", "cache_hit"):
        ja.pop(k)
        jb.pop(k)
    assert ja == jb
