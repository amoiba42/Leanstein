# 0013. Shaping versus reverting

## Status
Accepted

## Context
For mutants, the original reference is a known fix. If C only restores it, the gain says little about re-shaping
code for automation.

## Decision
Classify every successful run:
- **revert:** the repair equals the reference, or the reference is provable by the portfolio and the repair is
  within normalised distance 0.15 of it;
- **shaping:** the reference itself is not provable by the portfolio, so the verified repair must have a different,
  automation-friendly shape;
- **other:** everything else.

Report C's success rate by reference provability, and test deliberate re-shaping directly with study S (start from
a correct reference the portfolio cannot prove) against S-plain.

## Consequences
- Revert shares are reported separately for natural bugs and mutants.
- Study S measures whether models can re-shape on purpose, independent of bug fixing.
