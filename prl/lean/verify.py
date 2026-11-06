"""`verify()`: the trusted judge (FR-VER-1..6).

modes:
  * ``portfolio``            – code only; the fixed portfolio must close the locked theorem
  * ``model_proof``          – code + model proof; the model's proof must close it
  * ``portfolio_then_model`` – code + model proof; portfolio first, else the model proof
  * ``tests``                – code only; compile + tests, no proof attempt (dataset building)
"""
from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from typing import Any

from prl.config import PATHS, read_json, sha256_text, study_config, write_json
from prl.lean import builder as B
from prl.lean import integrity as I
from prl.lean.portfolio import Entry, expand, load_portfolio
from prl.lean.runner import LeanRun, Msg, run_lean_retry
from prl.tasks import regions as R
from prl.tasks.verina import Family

MODES = ("portfolio", "model_proof", "portfolio_then_model", "tests")
_AX_RE = re.compile(r"depends on axioms: \[([^\]]*)\]", re.S)
VERIFY_VERSION = "v4"


@dataclass
class VerifyResult:
    mode: str
    static_ok: bool
    static_reasons: list[str]
    compile_ok: bool | None = None
    visible_pass: bool | None = None
    hidden_pass: bool | None = None
    n_visible_fail: int = 0
    n_hidden_fail: int = 0
    test_vector: list[bool] = field(default_factory=list)  # visible then hidden
    proof_ok: bool = False
    proof_source: str = "none"
    closing_entry: str | None = None
    entry_vector: dict[str, bool] = field(default_factory=dict)
    entry_goals: dict[str, str] = field(default_factory=dict)
    model_proof_ok: bool | None = None
    axioms_ok: bool = True
    axioms: list[str] = field(default_factory=list)
    locked_ok: bool = True
    integrity_ok: bool = True
    integrity_reasons: list[str] = field(default_factory=list)
    flags: list[str] = field(default_factory=list)
    lean_errors: list[str] = field(default_factory=list)
    proof_errors: list[str] = field(default_factory=list)
    lean_s: float = 0.0
    lean_timeout: bool = False
    infra_error: str | None = None
    failure_kind: str | None = None  # None (success) | integrity | compile | test | proof | timeout | resource | infra
    cache_hit: bool = False
    key: str = ""

    @property
    def tests_pass(self) -> bool:
        return bool(self.visible_pass) and (self.hidden_pass is not False)

    @property
    def success(self) -> bool:
        return bool(self.compile_ok and self.proof_ok and self.integrity_ok and self.tests_pass)

    def to_json(self) -> dict[str, Any]:
        d = asdict(self)
        d["success"] = self.success
        return d

    @staticmethod
    def from_json(d: dict[str, Any]) -> VerifyResult:
        d = {k: v for k, v in d.items() if k != "success"}
        return VerifyResult(**d)


def classify_failure(vr: VerifyResult) -> str | None:
    """Single failure type used by the feedback router and the analysis."""
    if vr.infra_error and vr.failure_kind not in ("timeout", "resource"):
        return "infra"
    if vr.failure_kind in ("timeout", "resource"):
        return vr.failure_kind
    if not vr.static_ok or not vr.integrity_ok:
        return "integrity"
    if not vr.compile_ok:
        return "compile"
    if not vr.tests_pass:
        return "test"
    if not vr.proof_ok:
        return "proof"
    return None


def _in(m: Msg, span: tuple[int, int]) -> bool:
    return span[0] <= m.line <= span[1]


def axioms_of(stdout: str, name: str) -> list[str] | None:
    """Parse `#print axioms <name>` output. Lean prints it without a `file:line` header, so match by
    the (unique) declaration name. Returns None if no output was found for that name."""
    q = re.escape(name)
    out = stdout.replace("\r\n", "\n")
    if re.search(r"'" + q + r"' does not depend on any axioms", out):
        return []
    m = re.search(r"'" + q + r"' depends on axioms: \[([^\]]*)\]", out, re.S)
    if m:
        return [a.strip() for a in m.group(1).replace("\n", " ").split(",") if a.strip()]
    return None


def _goal_text(errs: list[Msg]) -> str:
    for m in errs:
        if "unsolved goals" in m.text:
            return m.text.split("unsolved goals", 1)[1].strip()[:1500]
    return errs[0].text[:1500] if errs else ""


def _tests_for(fam: Family, which: str) -> tuple[list[dict[str, str]], int]:
    vis = fam.visible_tests
    hid: list[dict[str, str]] = []
    if which in ("all", "hidden"):
        p = PATHS.hidden / f"{fam.family_id}.json"
        if p.exists():
            hid = read_json(p)["tests"]
    if which == "hidden":
        return hid, 0
    if which == "none":
        return [], 0
    if which == "visible":
        return vis, len(vis)
    return vis + hid, len(vis)


class Judge:
    """Stateless apart from configuration; thread-safe."""

    def __init__(self, cfg: dict[str, Any] | None = None, use_cache: bool = True):
        self.cfg = cfg or study_config()
        self.pf = load_portfolio()
        self.use_cache = use_cache
        lc = self.cfg["lean"]
        self.wall = float(lc["wall_guard_s"])
        if self.wall < 50:  # must clear worker start-up plus Tier-H tactic work (LLD §5.1)
            raise ValueError(f"lean.wall_guard_s must be >= 50 s, got {self.wall}")
        self.test_hb = int(lc.get("test_heartbeats", 0)) or None
        # test evaluation is not heartbeat-bounded (a mutant can loop forever): short guard, then bisect
        self.batch_wall = float(lc.get("batch_wall_s", 60))

    # ------------------------------------------------------------------ public API
    def entries_for(self, fam: Family, cand: dict[str, str]) -> list[Entry]:
        return expand(self.pf, fn=fam.fn, params=fam.signature.params, code_aux=cand.get("code_aux", ""),
                      code=cand.get("code", ""), aux_names=fam.aux_names)

    def verify(self, fam: Family, cand: dict[str, str], mode: str, *, tests: str = "all",
               skip_static: bool = False, full_vector: bool = False, force_portfolio: bool = False) -> VerifyResult:
        """Staged verification (LLD §5.4, revised in Phase 0 for cost):

        stage 1 — one Lean request: compile + all tests (+ the model's proof in proof modes);
        stage 2 — only if the mode uses the portfolio, the code compiles and passes all tests (otherwise
                  success is impossible): portfolio entries one request each, in the frozen order,
                  stopping at the first closing entry (``full_vector=True`` runs every entry; used for T).
        The closing entry is identical to running all entries and taking the first, by construction.
        """
        if mode not in MODES:
            raise ValueError(mode)
        with_proof = mode in ("model_proof", "portfolio_then_model")
        kind = I.WITH_PROOF if with_proof else I.CODE_ONLY
        cand = {k: (cand.get(k) or "") for k in ("code_aux", "code", "proof_aux", "proof")}
        st = I.StaticResult(True, []) if skip_static else I.static_check(cand, kind, fn=fam.fn, aux_names=fam.aux_names)
        if not st.ok:
            return VerifyResult(mode, False, st.reasons, integrity_ok=False, integrity_reasons=st.reasons,
                                failure_kind="integrity")
        rendered = R.render(fam.template, {"code_aux": cand["code_aux"], "code": cand["code"],
                                           "proof_aux": cand["proof_aux"] if with_proof else "",
                                           "proof": cand["proof"] if with_proof else "sorry"})
        locked_ok = R.locked_hash(rendered) == fam.locked_hash
        test_list, n_vis = _tests_for(fam, tests)
        entries = self.entries_for(fam, cand) if mode in ("portfolio", "portfolio_then_model") else []
        src1, lm1 = B.build(fam.template, fn=fam.fn, params=fam.signature.params, ret=fam.signature.ret,
                            theorem_stmt=fam.theorem_stmt, cand=cand, tests=test_list, entries=[],
                            with_proof=with_proof, test_heartbeats=self.test_hb)
        key = sha256_text("|".join([VERIFY_VERSION, src1, "\n".join(e.script for e in entries), self.pf.sha256,
                                    "tiers=" + repr(self.pf.tiers), mode, str(n_vis), str(full_vector), str(force_portfolio)]))
        cached = self._cache_get(key)
        if cached is not None:
            cached.cache_hit = True
            return cached
        run = run_lean_retry(src1, wall_s=self.wall)
        if run.timeout or (run.extra or {}).get("died"):
            # Failure taxonomy: confirm once in a fresh worker. A repeat means the
            # candidate itself does not terminate / exhausts memory -> failed attempt, not infrastructure.
            again = run_lean_retry(src1, wall_s=self.wall, retries=0)
            if not (again.timeout or (again.extra or {}).get("died")):
                run = again
        if run.timeout or (run.extra or {}).get("died"):
            kind = "timeout" if run.timeout else "resource"
            vr = VerifyResult(mode, True, [], key=key, lean_timeout=run.timeout, lean_s=run.elapsed_s)
            vr.compile_ok = self._compiles(fam, cand)
            vr.visible_pass, vr.hidden_pass = False, (False if len(test_list) > n_vis else None)
            vr.test_vector = [False] * len(test_list)
            vr.n_visible_fail, vr.n_hidden_fail = n_vis, len(test_list) - n_vis
            vr.lean_errors = [f"{kind}: evaluating the tests (or the model proof) did not finish within the limits"]
            vr.failure_kind = kind
        else:
            vr = self._interpret(run, lm1, mode, with_proof, n_vis, [], key, fam.fn)
        if entries and vr.compile_ok and (vr.tests_pass or full_vector or force_portfolio) and vr.infra_error is None:
            self._portfolio(fam, cand, entries, vr, full_vector, mode)
        vr.integrity_ok = vr.axioms_ok and not vr.integrity_reasons
        vr.locked_ok = locked_ok
        if not locked_ok:
            vr.integrity_ok = False
            vr.integrity_reasons.append("locked_hash_mismatch")
        vr.flags = I.degeneracy_flags(cand, fn=fam.fn, visible_inputs=[t["input_lean"] for t in fam.visible_tests],
                                      postcond=R.region_text(fam.template, "postcond"))
        vr.failure_kind = classify_failure(vr)
        if vr.infra_error is None:
            self._cache_put(key, vr)
        return vr

    def _compiles(self, fam: Family, cand: dict[str, str]) -> bool:
        src, lm = B.build(fam.template, fn=fam.fn, params=fam.signature.params, ret=fam.signature.ret,
                          theorem_stmt=fam.theorem_stmt, cand=cand, tests=[], entries=[], with_proof=False,
                          )
        r = run_lean_retry(src, wall_s=self.wall)
        return (not r.timeout) and not [m for m in r.errors() if _in(m, lm.code_span)]

    def _portfolio(self, fam: Family, cand: dict[str, str], entries: list[Entry], vr: VerifyResult,
                   full_vector: bool, mode: str) -> None:
        closing = None
        entry_wall = max(30.0, self.wall / 4)
        for e in entries:
            src, lm = B.build(fam.template, fn=fam.fn, params=fam.signature.params, ret=fam.signature.ret,
                              theorem_stmt=fam.theorem_stmt, cand=cand, tests=[], entries=[e], with_proof=False,
                              )
            r = run_lean_retry(src, wall_s=entry_wall)
            vr.lean_s += r.elapsed_s
            if r.timeout or r.infra_error:
                vr.entry_vector[e.id] = False
                vr.entry_goals[e.id] = "timeout" if r.timeout else "infra_error"
                vr.lean_timeout = vr.lean_timeout or r.timeout
                continue
            (_eid, s, en, _axl) = lm.entries[0]
            eerrs = [m for m in r.errors() if s <= m.line <= en]
            ax = axioms_of(r.stdout, "prl_try_0")
            ok = bool(not eerrs and ax is not None and I.axioms_clean(ax))
            vr.entry_vector[e.id] = ok
            if not ok and eerrs:
                vr.entry_goals[e.id] = _goal_text(eerrs)
            if ok and closing is None:
                closing = e.id
                vr.axioms = ax or []
                if not full_vector:
                    break
        if closing:
            vr.proof_ok, vr.proof_source, vr.closing_entry = True, "portfolio", closing

    def eval_outputs(self, fam: Family, cand: dict[str, str], inputs: list[dict[str, str]]) -> list[str | None]:
        """`#eval` the candidate on inputs; returns the printed value (Repr) or None on error. Cached."""
        src, lines = B.build_eval(fam.template, fn=fam.fn, params=fam.signature.params, cand=cand, inputs=inputs)
        key = sha256_text("eval|" + VERIFY_VERSION + "|" + src)
        p = PATHS.cache / "eval" / key[:2] / f"{key}.json"
        if self.use_cache and p.exists():
            return read_json(p)["out"]
        run = run_lean_retry(src, wall_s=self.wall)
        out = B.parse_eval(run.stdout, len(lines))
        if run.infra_error is None and not run.timeout:
            write_json(p, {"out": out})
        return out

    def batch_tests(self, fam: Family, cands: list[dict[str, str]], tests: str = "all") -> list[dict[str, Any]]:
        """Compile + run tests for many candidates in one Lean process (dataset building only).
        Returns per candidate {compile_ok, test_vector, n_vis}. Falls back to per-candidate runs on timeout."""
        test_list, n_vis = _tests_for(fam, tests)
        return self.batch_tests_with(fam, cands, test_list, n_vis)

    def batch_tests_with(self, fam: Family, cands: list[dict[str, str]], test_list: list[dict[str, str]],
                         n_vis: int | None = None) -> list[dict[str, Any]]:
        if not cands:
            return []
        n_vis = len(test_list) if n_vis is None else n_vis
        src, spans = B.build_batch(fam.template, fn=fam.fn, params=fam.signature.params, ret=fam.signature.ret,
                                   cands=cands, tests=test_list)
        key = sha256_text("batch|" + VERIFY_VERSION + "|" + src)
        p = PATHS.cache / "batch" / key[:2] / f"{key}.json"
        if self.use_cache and p.exists():
            return read_json(p)["out"]
        run = run_lean_retry(src, wall_s=self.batch_wall)
        if run.timeout or run.infra_error:
            if len(cands) == 1:
                return [{"compile_ok": False, "test_vector": [False] * len(test_list), "n_vis": n_vis,
                         "timeout": True}]
            mid = len(cands) // 2
            return (self.batch_tests_with(fam, cands[:mid], test_list, n_vis)
                    + self.batch_tests_with(fam, cands[mid:], test_list, n_vis))
        errs = run.errors()
        out = []
        for sp in spans:
            cs, ce = sp["code"]
            # errors in the locked tail (proof `sorry` is only a warning) count as compile failure
            ok = not any(cs <= m.line <= ce for m in errs)
            tv = [ok and not any(a <= m.line <= b for m in errs) for (a, b) in sp["tests"]]
            out.append({"compile_ok": ok, "test_vector": tv, "n_vis": n_vis})
        if self.use_cache:
            write_json(p, {"out": out})
        return out

    def witness_line(self, fam: Family, cand: dict[str, str], vr: VerifyResult) -> str | None:
        """First failing *visible* test with the candidate's actual output (never hidden tests)."""
        from prl.tasks.instances import format_witness

        if not vr.compile_ok or not vr.test_vector:
            return None
        n_vis = len(fam.visible_tests)
        for i, ok in enumerate(vr.test_vector[:n_vis]):
            if not ok:
                t = fam.visible_tests[i]
                act = self.eval_outputs(fam, cand, [t["input_lean"]])[0]
                return format_witness(fam.fn, t["input_lean"], t["expected_lean"], act)
        return None

    # ------------------------------------------------------------------ interpretation
    def _interpret(self, run: LeanRun, lm: B.LineMap, mode: str, with_proof: bool, n_vis: int,
                   entries: list[Entry], key: str, fam_fn: str = "") -> VerifyResult:
        msgs = run.messages
        errs = [m for m in msgs if m.severity == "error"]
        code_errs = [m for m in errs if _in(m, lm.code_span)]
        vr = VerifyResult(mode, True, [], key=key, lean_s=run.elapsed_s, lean_timeout=run.timeout,
                          infra_error=run.infra_error)
        vr.compile_ok = not code_errs
        vr.lean_errors = [f"line {m.line}: {m.text[:600]}" for m in code_errs[:3]]
        # tests
        tv = [not any(_in(m, span) for m in errs) for span in lm.tests]
        if not vr.compile_ok:
            tv = [False] * len(lm.tests)
        vr.test_vector = tv
        vis, hid = tv[:n_vis], tv[n_vis:]
        vr.visible_pass = all(vis) if vis else None
        vr.hidden_pass = all(hid) if hid else None
        vr.n_visible_fail = sum(not x for x in vis)
        vr.n_hidden_fail = sum(not x for x in hid)
        if vr.visible_pass is None:  # family without visible tests: rely on hidden
            vr.visible_pass = vr.hidden_pass if vr.hidden_pass is not None else vr.compile_ok
        # portfolio entries
        closing = None
        for idx, (eid, s, e, axl) in enumerate(lm.entries):
            eerrs = [m for m in errs if s <= m.line <= e]
            ax = axioms_of(run.stdout, f"prl_try_{idx}")
            ok = vr.compile_ok and not eerrs and ax is not None and I.axioms_clean(ax)
            vr.entry_vector[eid] = bool(ok)
            if not ok and eerrs:
                vr.entry_goals[eid] = _goal_text(eerrs)
            if ok and closing is None:
                closing = eid
                vr.axioms = ax or []
        # model proof
        if with_proof:
            perrs = [m for m in errs if _in(m, lm.proof_span)]
            ax = axioms_of(run.stdout, f"{fam_fn}_spec_satisfied") if lm.model_axioms_line else None
            vr.proof_errors = [f"line {m.line}: {m.text[:600]}" for m in perrs[:3]]
            mok = bool(vr.compile_ok and not perrs and ax is not None and I.axioms_clean(ax))
            vr.model_proof_ok = mok
            if ax is not None and not I.axioms_clean(ax) and not perrs:
                vr.axioms_ok = False
                vr.integrity_reasons.append("model_proof_axioms:" + ",".join(sorted(set(ax) - I.ALLOWED_AXIOMS)))
            if mode == "portfolio_then_model" and closing:
                vr.proof_ok, vr.proof_source, vr.closing_entry = True, "portfolio", closing
            elif mok:
                vr.proof_ok, vr.proof_source = True, "model"
                vr.axioms = ax or []
        elif closing:
            vr.proof_ok, vr.proof_source, vr.closing_entry = True, "portfolio", closing
        vr.integrity_ok = vr.axioms_ok and not vr.integrity_reasons
        return vr

    # ------------------------------------------------------------------ cache
    def _cache_path(self, key: str):
        return PATHS.cache / "verify" / key[:2] / f"{key}.json"

    def _cache_get(self, key: str) -> VerifyResult | None:
        if not self.use_cache:
            return None
        p = self._cache_path(key)
        if p.exists():
            try:
                return VerifyResult.from_json(read_json(p))
            except Exception:  # noqa: BLE001 - corrupted cache entry: recompute
                return None
        return None

    def _cache_put(self, key: str, vr: VerifyResult) -> None:
        if self.use_cache:
            write_json(self._cache_path(key), vr.to_json())
