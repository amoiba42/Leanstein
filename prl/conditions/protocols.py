"""Condition protocols A, B, BP, C, Cplain, S, Splain and exploratory Bhammer, with exact budget accounting
(FR-COND, FR-BUD). T has no model and lives in `prl.tasks.eligibility`."""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Protocol

from prl.conditions.feedback import route
from prl.config import sha256_text
from prl.lean import leantext as LT
from prl.lean.integrity import locked_names
from prl.lean.portfolio import expand, load_portfolio
from prl.lean.verify import VerifyResult
from prl.models import extract as X
from prl.models import prompts as P
from prl.models.lmstudio import InfraError
from prl.tasks.instances import Instance
from prl.tasks.verina import Family

ALL_CONDITIONS = ("A", "B", "BP", "C", "Cplain", "S", "Splain", "Bhammer")
MODE = {"A": "model_proof", "B": "model_proof", "BP": "portfolio_then_model", "C": "portfolio",
        "Cplain": "portfolio", "S": "portfolio", "Splain": "portfolio", "Bhammer": "model_proof"}
ROUND_CONDITIONS = {"C", "Cplain", "S", "Splain"}
SEQUENTIAL = {"B", "BP", "Bhammer"}


class Generator(Protocol):
    def complete(self, model: str, messages: list[dict[str, str]], *, seed: int, temperature: float,
                 top_p: float, max_tokens: int) -> Any: ...


class JudgeLike(Protocol):
    def verify(self, fam: Family, cand: dict[str, str], mode: str, *, tests: str = "all",
               skip_static: bool = False) -> VerifyResult: ...

    def witness_line(self, fam: Family, cand: dict[str, str], vr: VerifyResult) -> str | None: ...


@dataclass
class Budget:
    n_gen: int
    max_tokens: int
    max_infer_s: float
    used_gen: int = 0
    used_tokens: int = 0
    used_infer_s: float = 0.0

    def charge(self, tokens: int, secs: float) -> None:
        self.used_gen += 1
        self.used_tokens += tokens
        self.used_infer_s += secs

    def exhausted(self) -> str | None:
        if self.used_gen >= self.n_gen:
            return "n_gen"
        if self.used_tokens >= self.max_tokens:
            return "tokens"
        if self.used_infer_s >= self.max_infer_s:
            return "infer_time"
        return None


@dataclass
class AttemptLog:
    fields: dict[str, Any]


@dataclass
class RunResult:
    attempts: list[dict[str, Any]] = field(default_factory=list)
    success: bool = False
    success_idx: int | None = None
    stop_reason: str = ""
    final: dict[str, str] = field(default_factory=dict)
    final_vr: VerifyResult | None = None
    budget: Budget | None = None


def verify_with_infra_retry(judge, fam: Family, cand: dict[str, str], mode: str, retries: int = 2,
                            **kw: Any) -> VerifyResult:
    """Infrastructure failures (verifier crash, spawn failure) never charge the model's budget: the same
    candidate is re-verified; if infrastructure keeps failing, the whole run is abandoned (InfraError) and
    re-executed later by the resumable driver."""
    vr = judge.verify(fam, cand, mode, **kw)
    while vr.failure_kind == "infra" and retries > 0:
        retries -= 1
        time.sleep(5)
        vr = judge.verify(fam, cand, mode, **kw)
    if vr.failure_kind == "infra":
        raise InfraError(f"verifier infrastructure failure: {vr.infra_error}")
    return vr


def derive_seed(seed: int, attempt: int) -> int:
    return seed * 1000 + attempt


def tactic_menu(fam: Family, code_aux: str, code: str) -> str:
    """The frozen portfolio expanded for this task and its start code, one script per line (Bhammer prompt).
    Uses only locked names and the start code the model already sees."""
    entries = expand(load_portfolio(), fn=fam.fn, params=fam.signature.params, code_aux=code_aux, code=code,
                     aux_names=fam.aux_names)
    return "\n".join("- `" + e.script.replace("\n", "; ") + "`" for e in entries)


def proof_log(cand: dict[str, str]) -> dict[str, Any]:
    """`proof_tactic_used` + `automation_only_proof` for a model-written proof (FR-ANA-8; analysis only)."""
    tac = LT.proof_tactics(cand.get("proof", ""), cand.get("proof_aux", ""))
    return {"proof_tactic_used": tac,
            "automation_only_proof": LT.automation_only(tac, cand.get("proof_aux", ""),
                                                        load_portfolio().single_call_automation)}


def _rank(vr: VerifyResult) -> tuple:
    return (bool(vr.compile_ok and vr.tests_pass), bool(vr.compile_ok), -len(vr.static_reasons))


def run_condition(cond: str, inst: Instance, fam: Family, model: str, seed: int, cfg: dict[str, Any],
                  judge: JudgeLike, gen: Generator, raw_sink=None) -> RunResult:
    if cond not in ALL_CONDITIONS:
        raise ValueError(cond)
    b = cfg["budget"]
    budget = Budget(int(b["n_gen"]), int(b["max_total_tokens"]), float(b["max_infer_s"]))
    dec = cfg["decoding"]
    mode = MODE[cond]
    want_proof = cond in P.PROOF_CONDITIONS
    view = P.make_view(fam, inst.start["code_aux"], inst.start["code"], inst.kind)
    wline = inst.witness_line(fam.fn) if inst.kind != "shaping" else None
    tactics = tactic_menu(fam, inst.start["code_aux"], inst.start["code"]) if cond in P.TACTIC_MENU_CONDITIONS else ""
    history: list[tuple[str, str]] = []
    k = int(cfg.get("c_round_k", 2)) if cond in ROUND_CONDITIONS else 1
    hist_turns = int(cfg.get("history_turns", 2))
    rr = RunResult(budget=budget)
    attempt = 0
    round_idx = 0
    best: tuple[tuple, str, dict[str, str], VerifyResult] | None = None
    while True:
        stop = budget.exhausted()
        if stop:
            rr.stop_reason = stop
            break
        # ---- one generation
        hist = [] if cond == "A" else history
        msgs = P.messages(view, cond, wline, hist, hist_turns, tactics)
        prompt_text = "\n".join(m["content"] for m in msgs)
        s = derive_seed(seed, attempt)
        t0 = time.time()
        comp = gen.complete(model, msgs, seed=s, temperature=float(dec["temperature"]), top_p=float(dec["top_p"]),
                            max_tokens=int(b["max_completion_tokens"]))
        budget.charge(comp.tokens_in + comp.tokens_out, comp.elapsed_s)
        ex = X.extract(comp.text, fn=fam.fn, header=fam.header, want_proof=want_proof, locked_names=locked_names(fam.fn, fam.aux_names))
        cand = ex.cand()
        if ex.ok:
            vr = verify_with_infra_retry(judge, fam, cand, mode)
        else:
            vr = VerifyResult(mode, False, [f"extract:{ex.error}"], integrity_ok=True, failure_kind="extraction")
        rec = {
            "attempt_idx": attempt, "round_idx": round_idx, "seed_used": s, "prompt_sha256": sha256_text(prompt_text),
            "prompt_chars": len(prompt_text), "tokens_in": comp.tokens_in, "tokens_out": comp.tokens_out,
            "infer_s": round(comp.elapsed_s, 3), "finish_reason": comp.finish_reason,
            "extract_ok": ex.ok, "extract_error": ex.error, "extract_notes": ex.notes,
            **cand, "verify": vr.to_json(), "success": vr.success, "failure_kind": vr.failure_kind, "ts": t0,
        }
        if want_proof and ex.ok:
            rec.update(proof_log(cand))
        if raw_sink is not None:
            raw_sink(attempt, msgs, comp.text)
        attempt += 1
        if vr.success:
            rr.attempts.append(rec)
            rr.success, rr.success_idx, rr.stop_reason = True, attempt - 1, "success"
            rr.final, rr.final_vr = cand, vr
            break
        # ---- feedback
        r = (_rank(vr), comp.text, cand, vr)
        if best is None or r[0] > best[0]:
            best = r
        fb = ""
        if cond in SEQUENTIAL:
            f = route(cond, fam, cand, vr, extract_ok=ex.ok,
                      witness_line=judge.witness_line(fam, cand, vr) if ex.ok else None)
            fb = f.text
            rec["feedback_kind"] = f.kind
            history.append((comp.text, fb))
        elif cond in ROUND_CONDITIONS and attempt % k == 0:
            _, btext, bcand, bvr = best
            b_ok = not any(r.startswith("extract:") for r in bvr.static_reasons)
            f = route(cond, fam, bcand, bvr, extract_ok=b_ok,
                      witness_line=judge.witness_line(fam, bcand, bvr) if b_ok else None)
            fb = f.text
            rec["feedback_kind"] = f.kind
            rec["hint_kinds"] = list(f.hint_kinds)
            history.append((btext, fb))
            best = None
            round_idx += 1
        rec["feedback_chars"] = len(fb)
        rr.attempts.append(rec)
        rr.final, rr.final_vr = cand, vr
    return rr
