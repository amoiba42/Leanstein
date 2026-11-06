# 0010. Persistent Lean verification server with full Mathlib

## Status
Accepted

## Context
Running `lean` from scratch per candidate costs 25–40 s because Mathlib must be loaded each time; the study needs
hundreds of thousands of checks.

## Decision
Use an own verification server, `lean_env/PrlRepl.lean`, which imports the whole of Mathlib once per worker and
elaborates each candidate against a fresh copy of that environment (about 0.6 s per check). Lean 4.24.0 and
Mathlib v4.24.0 are pinned. The plain `lean` CLI remains as a fallback, with result parity checked. Workers are
sized from free RAM unless configured. A reduced import set (individual tactic modules instead of `import Mathlib`)
is rejected: some of those modules do not exist in Mathlib v4.24, and a smaller environment changes what the
portfolio can prove, breaks specifications that use Mathlib definitions and breaks server/CLI parity.

## Consequences
- Infrastructure failures (worker crash, out of memory) re-verify the same candidate without charging the budget.
- One pinned environment serves every condition.
