# 0001. Code-only repair with a frozen tactic portfolio

## Status
Accepted

## Context
Small language models rarely produce valid Lean 4 proofs, yet often produce correct code. Lean ships automation
(`simp`, `omega`, `decide`, `aesop`, `grind`) that closes many goals when the code has a suitable shape. A model
that also writes the proof spends most of its budget on proofs that fail.

## Decision
The method under test is condition **C**: the model edits only the implementation regions (code and helpers), and a
fixed, ordered, pre-registered tactic portfolio (ADR 0006) must prove the unchanged specification. The model never
writes a tactic; any proof text in its output is rejected (ADR 0007). Feedback after a failed attempt is the
failing witness or Lean errors, the best unsolved goal, and a structural hint. C samples two candidates per feedback
round so that its total budget matches the proof-writing conditions (ADR 0008).

## Consequences
- The comparison is about *who writes the proof*: everything else (task, budget, checks) is shared.
- Success is limited by what the portfolio can prove; specifications that need induction are hard (RQ4).
- The model may succeed by reverting a bug or by re-shaping code; both are measured (ADR 0013).
- The portfolio cannot be tuned per task or per condition, which keeps the comparison fair.
