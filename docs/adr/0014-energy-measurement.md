# 0014. Energy measurement

## Status
Accepted

## Context
RQ5 reports energy per verified repair. The GPU is a MIG slice on a shared physical GPU, and two study jobs ran at
once.

## Decision
The in-run meter (NVML counter per model and condition block) is not used: it read the counter of another physical
GPU, and its CPU figure mixed concurrent jobs, so its figures were withdrawn (D-1 in `prereg/deviations.md`).
Energy is estimated after the study instead (D-4): each model is served again on the same slice with the study's
settings and real study prompts; board power is sampled every 100 ms over three cycles of idle, prompt-only and full
generation; power above idle gives joules per prompt token and per completion token. Every logged model call is
charged by its tokens; Lean CPU energy is logged Lean seconds × 5.47 W per thread; CO₂ uses 0.716 kg/kWh.

## Consequences
- Energy figures are estimates, labelled as such; idle power shared with other tenants is not attributed.
- Absolute values may be up to about 1.6× higher because two jobs shared the slice; the factor applies equally to
  every condition of a model, so comparisons hold.
- Tokens, inference seconds and Lean seconds per verified repair are measured directly and unaffected.
