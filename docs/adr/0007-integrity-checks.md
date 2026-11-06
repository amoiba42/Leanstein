# 0007. Static integrity checks and locked regions

## Status
Accepted

## Context
A model can "succeed" by escaping the proof obligation, editing the specification, or (in code-only conditions)
smuggling proof text into the code.

## Decision
Before Lean runs, reject: `sorry`, `admit`, `axiom`, `native_decide`, `implemented_by`, `unsafe`, macros,
`set_option`, attributes and `#` commands; redefinition of locked names; proof text in code-only conditions; empty
bodies. After Lean runs, require axioms ⊆ {propext, Classical.choice, Quot.sound} and unchanged hashes of the locked
regions (specification, theorem statement, tests). Flag, without rejecting: spec-copying (`mentions_postcond`,
`copies_postcond` at 35% of postcondition 4-grams), constant bodies, hard-coded tests, `choice`. Flags never change
a result.

## Consequences
- Rejections are frequent for proof-writing conditions (mostly malformed output) and are reported per condition.
- Flagged successes always enter the audit (ADR 0015).
