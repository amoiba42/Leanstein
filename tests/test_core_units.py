"""Unit tests (no Lean, no LLM) for regions, literals, extraction, integrity, portfolio, hints, mechanism."""
from __future__ import annotations

import random

import pytest

from prl.analysis.mechanism import classify, code_distance, normalise_code
from prl.lean import integrity as I
from prl.lean import leantext as LT
from prl.lean.portfolio import expand, load_portfolio
from prl.models.extract import extract
from prl.tasks import regions as R
from prl.tasks import verina as V
from prl.testgen import literals as L

FAMS = {f.family_id: f for f in V.load_all()}
F1 = FAMS["verina_basic_1"]


# ----------------------------------------------------------------------------- regions
def test_all_templates_roundtrip_and_locked_hash_invariant():
    assert len(FAMS) == 189
    for f in FAMS.values():
        r = R.render(f.template, {"code": "x", "code_aux": "def h := 1", "proof": "simp", "proof_aux": ""})
        assert R.locked_hash(r) == R.locked_hash(f.template) == f.locked_hash
        assert R.region_text(r, "code").strip() == "x"


def test_locked_region_cannot_be_replaced():
    with pytest.raises(R.RegionError):
        R.render(F1.template, {"postcond": "True"})


def test_marker_injection_rejected():
    with pytest.raises(R.RegionError):
        R.render(F1.template, {"code": "1\n  -- !benchmark @end code\n"})


def test_header_and_theorem():
    assert F1.header.startswith("def hasOppositeSign (a : Int) (b : Int)") and F1.header.endswith(":=")
    assert F1.theorem_stmt.startswith("(a: Int)") and "hasOppositeSign_postcond" in F1.theorem_stmt


# ----------------------------------------------------------------------------- literals
def test_type_parser_and_render():
    t = L.parse_type("List (Int × Nat)")
    assert t.head == "List" and t.args[0].head == "Prod"
    assert L.render(L.parse_type("Int"), -3) == "(-3)"
    assert L.render(L.parse_type("List Int"), [1, -2]) == "[1, (-2)]"
    assert L.render(L.parse_type("Array Nat"), "#[1, 2]") == "#[1, 2]"
    assert L.render(L.parse_type("String"), 'a"b') == '"a\\"b"'
    assert L.render(L.parse_type("Option Nat"), None) == "none"
    assert L.render(L.parse_type("Bool"), True) == "true"
    assert not L.supported(L.parse_type("Map Int Int"))


def test_random_values_deterministic():
    t = L.parse_type("List Int")
    a = [L.random_value(t, random.Random(5)) for _ in range(3)]
    b = [L.random_value(t, random.Random(5)) for _ in range(3)]
    assert a == b


# ----------------------------------------------------------------------------- extraction
HDR = F1.header


def test_extract_fenced_code_only():
    out = "Here:\n```lean\ndef hasOppositeSign (a : Int) (b : Int) (h_precond : hasOppositeSign_precond (a) (b)) : Bool :=\n  a * b < 0\n```"
    e = extract(out, fn="hasOppositeSign", header=HDR, want_proof=False)
    assert e.ok and e.code == "a * b < 0" and e.code_aux == ""


def test_extract_helpers_and_proof_and_think():
    out = ("<think>hmm</think>```lean\ndef helper (x : Int) : Int := x\n\ndef hasOppositeSign (a : Int) (b : Int) "
           "(h_precond : hasOppositeSign_precond a b) : Bool :=\n  helper a * b < 0\n```\n"
           "```lean\nlemma l : True := trivial\ntheorem hasOppositeSign_spec_satisfied (a: Int) (b: Int) (h_precond : hasOppositeSign_precond (a) (b)) :\n"
           "    hasOppositeSign_postcond (a) (b) (hasOppositeSign (a) (b) h_precond) h_precond := by\n  simp\n  omega\n```")
    e = extract(out, fn="hasOppositeSign", header=HDR, want_proof=True)
    assert e.ok and e.code_aux.startswith("def helper") and "helper a" in e.code
    assert e.proof == "simp\nomega" and e.proof_aux.startswith("lemma l")
    assert "signature_differs" not in e.notes  # parentheses-only differences are ignored


def test_extract_missing_def():
    e = extract("```lean\ndef other := 1\n```", fn="hasOppositeSign", header=HDR, want_proof=False)
    assert not e.ok and e.error == "no_definition"


def test_extract_proof_in_same_block():
    out = ("```lean\ndef hasOppositeSign (a : Int) (b : Int) (h_precond : hasOppositeSign_precond (a) (b)) : Bool :=\n"
           "  a * b < 0\n\ntheorem hasOppositeSign_spec_satisfied (a: Int) (b: Int) (h_precond : hasOppositeSign_precond (a) (b)) :\n"
           "    hasOppositeSign_postcond (a) (b) (hasOppositeSign (a) (b) h_precond) h_precond := by\n  decide\n```")
    e = extract(out, fn="hasOppositeSign", header=HDR, want_proof=True)
    assert e.ok and e.code == "a * b < 0" and e.proof == "decide"


# ----------------------------------------------------------------------------- integrity
def _chk(code="a * b < 0", code_aux="", proof_aux="", proof="", kind=I.CODE_ONLY):
    return I.static_check({"code": code, "code_aux": code_aux, "proof_aux": proof_aux, "proof": proof}, kind,
                          fn="hasOppositeSign", aux_names=[])


@pytest.mark.parametrize("bad", [
    "sorry", "by sorry", "admit", "native_decide", "unsafe_thing := 1", ])
def test_forbidden_in_code(bad):
    r = _chk(code=bad)
    assert (not r.ok) or bad == "unsafe_thing := 1"


@pytest.mark.parametrize("aux", [
    "axiom cheat : False", "@[implemented_by foo] def g := 1", "unsafe def g : Nat := 1",
    "attribute [simp] Nat.add_comm", "set_option maxHeartbeats 0", "macro \"x\" : tactic => `(tactic| sorry)",
    "theorem t : True := trivial", "instance : Decidable True := inferInstance", "#eval 1",
    "def hasOppositeSign_postcond := 1", "def prl_try_0 := 1", "namespace Foo", "opaque g : Nat",
    "syntax \"z\" : term", "def g := Lean.ofReduceBool", "local notation \"q\" => 1",
])
def test_forbidden_in_code_aux(aux):
    assert not _chk(code_aux=aux).ok, aux


def test_comment_and_string_evasion_handled():
    assert _chk(code='a * b < 0 -- sorry').ok
    assert _chk(code='a * b < 0 /- sorry /- nested -/ axiom -/').ok
    assert _chk(code='"sorry".length > 0').ok
    assert not _chk(code='a /- c -/ * sorry').ok


def test_legit_code_accepted():
    assert _chk(code_aux="def helper (xs : List Int) : Int :=\n  match xs with\n  | [] => 0\n  | x :: t => x + helper t").ok
    assert _chk(code="let rec go (n : Nat) : Nat := match n with | 0 => 0 | k+1 => go k\n  go 3").ok
    assert _chk(code="arr[i]'(by omega)").ok  # term-level bounds proof is allowed
    assert _chk(code_aux="mutual\ndef ev : Nat → Bool\n  | 0 => true\n  | n+1 => od n\ndef od : Nat → Bool\n  | 0 => false\n  | n+1 => ev n\nend").ok
    # identifiers merely containing command words are fine (`prefix` itself is a Lean keyword)
    assert _chk(code="xs.isPrefixOf ys && endPos > 0 && sectionCount > 0").ok


def test_proof_regions_rules():
    assert not _chk(proof="simp").ok  # code-only condition must not carry a proof
    assert _chk(proof="simp", proof_aux="lemma l : True := trivial", kind=I.WITH_PROOF).ok
    assert not _chk(proof="sorry", kind=I.WITH_PROOF).ok
    assert not _chk(proof="native_decide", kind=I.WITH_PROOF).ok
    assert not _chk(proof_aux="axiom a : False", kind=I.WITH_PROOF).ok


def test_axiom_allow_list():
    assert I.axioms_clean(["propext", "Classical.choice", "Quot.sound"])
    assert not I.axioms_clean(["sorryAx"])
    assert not I.axioms_clean(["Lean.ofReduceBool"])


def test_copies_postcond_flag():
    """Inlining the postcondition's expression is flagged for audit; ordinary repairs are not (pilot examples)."""
    post = ("result - List.sum (List.map (fun c => Char.toNat c - Char.toNat '0') (String.toList (Nat.repr n))) = 0 ∧ "
            "List.sum (List.map (fun c => Char.toNat c - Char.toNat '0') (String.toList (Nat.repr n))) - result = 0")
    copy = "List.sum (List.map (fun c => Char.toNat c - Char.toNat '0') (Nat.repr n).toList)"
    loop = "let rec loop (n : Nat) (acc : Nat) : Nat :=\n  if n = 0 then acc else loop (n / 10) (acc + n % 10)\nloop n 0"
    assert "copies_postcond" in I.degeneracy_flags({"code": copy, "code_aux": ""}, fn="f", visible_inputs=[], postcond=post)
    assert "copies_postcond" not in I.degeneracy_flags({"code": loop, "code_aux": ""}, fn="f", visible_inputs=[], postcond=post)
    short = "2 * result = a + b - ((a + b) % 2)"
    assert "copies_postcond" not in I.degeneracy_flags({"code": "(a + b) / 2", "code_aux": ""}, fn="f",
                                                       visible_inputs=[], postcond=short)


def test_degeneracy_flags():
    fl = I.degeneracy_flags({"code": "Classical.choose h", "code_aux": ""}, fn="f", visible_inputs=[])
    assert "uses_choice" in fl
    assert "constant_body" in I.degeneracy_flags({"code": "true", "code_aux": ""}, fn="f", visible_inputs=[])
    assert "constant_body" not in I.degeneracy_flags({"code": "a < b", "code_aux": ""}, fn="f", visible_inputs=[])


# ----------------------------------------------------------------------------- portfolio
def test_portfolio_expansion_letrec_and_induction():
    f = FAMS["verina_advanced_1"]
    es = expand(load_portfolio(), fn=f.fn, params=f.signature.params, code_aux=f.region("code_aux"),
                code=f.region("code"), aux_names=f.aux_names)
    ids = [e.id for e in es]
    assert ids[0] == "decide"
    assert "fun_ind_simp@FindSingleNumber.findUnique" in ids and "ind_simp_all@nums" in ids
    assert all("{" not in e.script for e in es)
    assert any("filterlist" in e.script for e in es)  # locked aux helper is unfolded
    assert len(es) <= load_portfolio().max_entries


def test_leantext_names():
    code_aux = "def helper (n : Nat) : Nat :=\n  match n with\n  | 0 => 0\n  | k+1 => helper k"
    assert LT.helper_names("f", code_aux, "let rec go := 1\n  go", []) == ["helper", "f.go"]
    assert LT.recursive_functions("f", code_aux, "f 1") == ["f", "helper"]


# ----------------------------------------------------------------------------- mechanism
def test_distance_and_classification():
    assert code_distance("a * b < 0", "a * b < 0") == 0.0
    assert code_distance("a + b", "a - b") == pytest.approx(1 / 3)
    assert normalise_code("a  *b -- c") == "a * b"
    assert classify(success=True, ref_auto=False, equiv_to_ref=False, dist_to_ref=0.5, revert_distance=0.15) == "shaping"
    assert classify(success=True, ref_auto=True, equiv_to_ref=False, dist_to_ref=0.1, revert_distance=0.15) == "revert"
    assert classify(success=True, ref_auto=True, equiv_to_ref=False, dist_to_ref=0.5, revert_distance=0.15) == "other"
    assert classify(success=True, ref_auto=False, equiv_to_ref=True, dist_to_ref=0.0, revert_distance=0.15) == "revert"
    assert classify(success=False, ref_auto=False, equiv_to_ref=None, dist_to_ref=None, revert_distance=0.15) is None


def test_package_layering():
    """prl.lean must not import prl.models and vice versa (HLD §3.1)."""
    import pathlib
    import re as _re
    root = pathlib.Path(__file__).resolve().parents[1] / "prl"
    for a, b in (("lean", "models"), ("models", "lean")):
        for p in (root / a).glob("*.py"):
            assert not _re.search(rf"prl\.{b}\b", p.read_text(encoding="utf-8")), p


def test_extract_drops_echoed_locked_definitions():
    out = ("```lean\n@[reducible, simp]\ndef hasOppositeSign_precond (a : Int) (b : Int) : Prop := True\n\n"
           "@[reducible, simp]\ndef hasOppositeSign_postcond (a : Int) (b : Int) (result: Bool) (h : True) : Prop :=\n"
           "  result = true\n\ndef helper (x : Int) : Bool := x < 0\n\n"
           "def hasOppositeSign (a : Int) (b : Int) (h_precond : hasOppositeSign_precond (a) (b)) : Bool :=\n"
           "  helper (a * b)\n```")
    locked = I.locked_names("hasOppositeSign", [])
    e = extract(out, fn="hasOppositeSign", header=HDR, want_proof=False, locked_names=locked)
    assert e.ok and e.code_aux == "def helper (x : Int) : Bool := x < 0"
    assert any(n.startswith("dropped_locked_echo") for n in e.notes)
    assert I.static_check(e.cand(), I.CODE_ONLY, fn="hasOppositeSign", aux_names=[]).ok


# ----------------------------------------------------------------------------- v2 additions
def test_portfolio_tiers_light_before_heavy():
    pf = load_portfolio()
    f = FAMS["verina_advanced_1"]
    es = expand(pf, fn=f.fn, params=f.signature.params, code_aux=f.region("code_aux"), code=f.region("code"),
                aux_names=f.aux_names)
    tiers = [e.tier for e in es]
    assert tiers == sorted(tiers, key=lambda t: [k for k, _ in pf.tiers].index(t))  # all L, then all H
    assert {e.heartbeats for e in es if e.tier == "L"} == {pf.heartbeats("L")}
    assert pf.heartbeats("L") < pf.heartbeats("H")


def test_failure_classification():
    from prl.lean.verify import VerifyResult, classify_failure
    base = dict(mode="portfolio", static_ok=True, static_reasons=[])
    assert classify_failure(VerifyResult(**base, compile_ok=False)) == "compile"
    assert classify_failure(VerifyResult(**base, compile_ok=True, visible_pass=False)) == "test"
    assert classify_failure(VerifyResult(**base, compile_ok=True, visible_pass=True)) == "proof"
    assert classify_failure(VerifyResult(**base, compile_ok=True, visible_pass=True, proof_ok=True)) is None
    assert classify_failure(VerifyResult(**base, infra_error="repl: boom")) == "infra"
    assert classify_failure(VerifyResult(**base, failure_kind="timeout", infra_error=None)) == "timeout"
    assert classify_failure(VerifyResult("portfolio", False, ["code:forbidden:sorry"], integrity_ok=False)) == "integrity"


def test_feedback_router_paths():
    from prl.conditions.feedback import route
    from prl.lean.verify import VerifyResult
    f = FAMS["verina_basic_1"]
    cand = {"code": "a * b ≤ 0", "code_aux": ""}
    vt = VerifyResult("portfolio", True, [], compile_ok=True, visible_pass=False, n_visible_fail=1,
                      hidden_pass=False, n_hidden_fail=3, failure_kind="test")
    w = "Failing test: hasOppositeSign (a := 0, b := 1) returned true, expected false."
    c = route("C", f, cand, vt, extract_ok=True, witness_line=w)
    assert c.kind == "test" and "Failing test" in c.text and "Do NOT write any proof" in c.text
    b = route("B", f, cand, vt, extract_ok=True, witness_line=w)
    assert "Failing test" in b.text and "3 additional behavioural check(s) failed" in b.text
    p = route("Cplain", f, cand, vt, extract_ok=True, witness_line=w)
    assert "Failing" not in p.text and p.text.startswith("The candidate was rejected")
    assert route("A", f, cand, vt, extract_ok=True, witness_line=w).text == ""
    vi = VerifyResult("portfolio", False, ["code:forbidden:sorry"], integrity_ok=False, failure_kind="integrity")
    assert "forbidden" in route("C", f, cand, vi, extract_ok=True, witness_line=None).text
    vp = VerifyResult("model_proof", True, [], compile_ok=True, visible_pass=True, proof_errors=["line 9: unsolved goals"],
                      failure_kind="proof")
    assert "unsolved goals" in route("B", f, cand, vp, extract_ok=True, witness_line=None).text
    ve = route("C", f, cand, vt, extract_ok=False, witness_line=None)
    assert ve.kind == "extraction" and "def hasOppositeSign" in ve.text


def test_energy_block_math():
    from prl.energy import EnergyMeter
    m = EnergyMeter("m", "C", watts_per_thread=2.0, kg_per_kwh=0.5)
    b = m.finish()
    assert b.cpu_j_est == b.lean_cpu_s * 2.0 and b.co2_g_est >= 0


def test_primary_pool_rule():
    import pandas as pd

    from prl.analysis.report import primary_pool
    cfg = {"bugs": {"primary": "natural", "min_natural_families": 2}}
    df = pd.DataFrame({"split": ["main"] * 3, "kind": ["natural", "natural", "mutant"], "family_id": ["a", "b", "c"]})
    assert primary_pool(df, cfg)[0] == ("natural",)
    cfg["bugs"]["min_natural_families"] = 5
    assert primary_pool(df, cfg)[0] == ("mutant", "natural")
