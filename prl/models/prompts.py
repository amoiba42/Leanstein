"""Prompt construction. `TaskView` is the only object prompts are built from (IR-9)."""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from string import Template

from prl.config import PATHS

CONDITION_TEMPLATE = {"A": "A", "B": "B", "BP": "BP", "C": "C", "Cplain": "Cplain", "S": "S", "Splain": "Splain",
                      "natural": "natural"}
PROOF_CONDITIONS = {"A", "B", "BP"}
HINT_CONDITIONS = {"C", "S"}
PLAIN_CONDITIONS = {"Cplain", "Splain"}


@dataclass(frozen=True)
class TaskView:
    """Narrow, prompt-safe projection of a task instance. Never holds reference code or hidden tests."""
    fn: str
    description: str
    spec: str  # precond_aux + precond def + postcond_aux + postcond def (locked text)
    header: str
    theorem_stmt: str
    start_def: str | None  # complete start definition (helpers + def); None for natural-bug generation
    start_note: str


@lru_cache(maxsize=32)
def _tmpl(name: str) -> Template:
    return Template((PATHS.prompts / f"{name}.txt").read_text(encoding="utf-8"))


def _spec_text(template: str, fn: str) -> str:
    """Locked text from the start of `precond_aux` through the end of the postcond definition,
    excluding the implementation (code_aux/code) — i.e. what the contract says, nothing else."""
    from prl.tasks import regions as R

    regs = R.parse_regions(template)
    # solution_aux holds locked helpers that the postcondition may reference (e.g. verina_advanced_1)
    first = "solution_aux" if "solution_aux" in regs else "precond_aux"
    pre = template[regs[first].start: regs["code_aux"].start] if first in regs else ""
    post_start = regs["code"].end
    post_end = regs["proof_aux"].start if "proof_aux" in regs else regs["proof"].start
    post = template[post_start:post_end]
    # drop the implementation's trailing marker line and the proof_aux start marker
    keep = []
    for ln in (pre + "\n" + post).split("\n"):
        s = ln.strip()
        if s.startswith("-- !benchmark") or s.startswith("def " + fn + " ") or s == "def " + fn:
            continue
        keep.append(ln)
    text = "\n".join(keep)
    # postcond section begins after `-- !benchmark @end code` which we removed; strip blank runs
    out, blank = [], 0
    for ln in text.split("\n"):
        blank = blank + 1 if not ln.strip() else 0
        if blank <= 1:
            out.append(ln)
    return "\n".join(out).strip()


def make_view(fam, start_code_aux: str | None, start_code: str | None, kind: str) -> TaskView:
    """Build the prompt-safe view. Uses the family template only for *locked* text."""
    start_def = None
    if start_code is not None:
        body = "\n".join("  " + ln if ln.strip() else ln for ln in start_code.strip("\n").split("\n"))
        start_def = ((start_code_aux.strip() + "\n\n") if start_code_aux and start_code_aux.strip() else "") \
            + fam.header + "\n" + body
    note = {
        "mutant": " (contains a bug)", "natural": " (contains a bug)",
        "shaping": " (correct, but not provable by automation)",
    }.get(kind, "")
    return TaskView(fam.fn, fam.description, _spec_text(fam.template, fam.fn), fam.header, fam.theorem_stmt,
                    start_def, note)


def task_block(v: TaskView) -> str:
    t = _tmpl("task").safe_substitute(
        description=v.description, spec=v.spec, header=v.header, fn=v.fn, theorem_stmt=v.theorem_stmt,
        start_def=v.start_def or "", start_note=v.start_note,
    )
    if v.start_def is None:
        t = t.split("## Current implementation")[0].rstrip()
    return t


def initial_user(v: TaskView, cond: str, witness_line: str | None) -> str:
    instr = _tmpl(CONDITION_TEMPLATE[cond]).safe_substitute(fn=v.fn)
    parts = [task_block(v)]
    if witness_line and cond not in ("S", "Splain"):
        parts.append("## Failing test\n" + witness_line)
    parts.append("## Instructions\n" + instr)
    return "\n\n".join(parts)


def system() -> str:
    return _tmpl("system").template.strip()


def feedback(cond: str, *, witness_line: str | None, errors: list[str], hint_text: str) -> str:
    if cond in PROOF_CONDITIONS:
        return _tmpl("feedback_proof").safe_substitute(
            witness=witness_line or "", errors=("Lean errors:\n" + "\n".join(errors)) if errors else "",
        ).replace("\n\n\n", "\n").strip()
    if cond in HINT_CONDITIONS:
        return _tmpl("feedback_hint").safe_substitute(hint=hint_text).strip()
    if cond in PLAIN_CONDITIONS:
        return _tmpl("feedback_plain").template.strip()
    raise ValueError(cond)


def messages(v: TaskView, cond: str, witness_line: str | None, history: list[tuple[str, str]],
             history_turns: int) -> list[dict[str, str]]:
    msgs = [{"role": "system", "content": system()},
            {"role": "user", "content": initial_user(v, cond, witness_line)}]
    for out, fb in history[-history_turns:] if history_turns > 0 else []:
        msgs.append({"role": "assistant", "content": out[:4000]})
        msgs.append({"role": "user", "content": fb})
    return msgs
