# 0006. Two-tier deterministic tactic portfolio

## Status
Accepted

## Context
Light tactics are cheap and close most goals; heavy search is slow. Wall-clock budgets are non-deterministic, and
an adaptive router that skips tactics would add an unregistered degree of freedom.

## Decision
A frozen, ordered portfolio (`prereg/portfolio.yaml`) with two tiers and early stop:
- **Tier L** (50k heartbeats per entry): `decide`, `simp`, `simp_all`, and combinations with `omega` and `split`.
- **Tier H** (200k heartbeats, Lean's default): `grind`, `aesop`, induction templates closed by `simp_all` or `grind`.

Budgets are Lean heartbeats, not seconds; unbounded heartbeats are not allowed. The same portfolio, order and limits
are used by every condition that uses automation (T, BP, C, C-plain, S, S-plain). No per-task customisation and no
model-chosen tactics.

## Consequences
- Results are deterministic and comparable across conditions.
- Wall-clock guards (120 s per request, max(30 s, guard/4) per entry) only stop hangs.
- The portfolio proves 22.3% of eligible references (basic 35.6%, advanced 5.0%); recursion is the main gap.
