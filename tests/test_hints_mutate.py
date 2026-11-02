from prl.lean import hints as H
from prl.lean.verify import VerifyResult
from prl.mutate.operators import generate
from prl.tasks import verina as V

FAM = V.load_family(V.PATHS.verina_tasks / "verina_basic_1")


def _vr(**kw):
    v = VerifyResult("portfolio", True, [], compile_ok=True, visible_pass=True, hidden_pass=True)
    for k, x in kw.items():
        setattr(v, k, x)
    return v


def test_pointer_catalogue():
    p = H.pointers(FAM, "", "Id.run do\n  let mut s := 0\n  for x in [1,2] do\n    s := s + x\n  return s > 0")
    assert "imperative_loop" in p
    assert "partial_def" in H.pointers(FAM, "partial def g (n : Nat) : Nat := g n", "g 1 > 0")
    assert "well_founded" in H.pointers(FAM, "def g (n : Nat) : Nat := n\ntermination_by n", "g 1 > 0")
    assert "array_index" in H.pointers(FAM, "", "#[1][0]! > 0")
    assert "fold_accumulator" in H.pointers(FAM, "", "[a].foldl (· + ·) 0 < b")
    assert H.pointers(FAM, "", "a * b < 0") == []


def test_hint_kinds_by_failure_stage():
    h = H.extract(FAM, {"code": "x", "code_aux": ""}, _vr(compile_ok=False, lean_errors=["line 3: unknown x"]), None)
    assert h.kinds[0] == "compile_error" and "unknown x" in h.text
    h = H.extract(FAM, {"code": "a < b", "code_aux": ""}, _vr(visible_pass=False, n_visible_fail=2),
                  "Failing test: f (a := 1) returned true, expected false.")
    assert h.kinds[0] == "test_failure" and "Failing test" in h.text
    h = H.extract(FAM, {"code": "a * b < 0", "code_aux": ""},
                  _vr(entry_goals={"simp": "a b : ℤ\n⊢ a * b < 0 ↔ x", "grind": "grind failed"}), None)
    assert h.kinds[0] == "proof_stuck" and "(simp)" in h.text


def test_hidden_failures_never_reveal_inputs():
    h = H.extract(FAM, {"code": "a < b", "code_aux": ""}, _vr(hidden_pass=False, n_hidden_fail=3), None)
    assert "3 additional behavioural check(s) failed" in h.text


def test_hint_length_cap_and_determinism():
    big = _vr(entry_goals={"simp": "⊢ " + "x" * 5000})
    a = H.extract(FAM, {"code": "a * b < 0", "code_aux": ""}, big, None)
    b = H.extract(FAM, {"code": "a * b < 0", "code_aux": ""}, big, None)
    assert len(a.text) <= H.catalogue()["max_chars"] and a.text == b.text


def test_mutation_operators():
    ms = generate("if a < b then a + 1 else b - 1")
    ops = {m.op for m in ms}
    assert {"relflip", "arith", "const", "negate_cond", "swap_branches", "drop_succ"} <= ops
    assert all(m.text != "if a < b then a + 1 else b - 1" for m in ms)
    assert len({m.text for m in ms}) == len(ms)


def test_mutation_skips_comments_and_strings():
    ms = generate('"a < b".length -- x + 1\n  + 0')
    assert all("--" in m.text and '"a < b"' in m.text for m in ms)
    assert not any(m.before == "<" for m in ms)


def test_mutation_deterministic():
    assert [m.text for m in generate("a * b < 0")] == [m.text for m in generate("a * b < 0")]
