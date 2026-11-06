# 0009. Models and serving

## Status
Accepted

## Context
The study targets small, locally runnable models, with a second model family and a proof-specialist reference.
All runs must use one hardware and software environment.

## Decision
| Role | Models |
|---|---|
| Primary repairers | Qwen3.5-2B, Qwen3.5-4B |
| Second family | Gemma-4-E4B-it |
| Proof specialist (A, B only) | Goedel-Code-Prover-8B |
| Natural-bug generators (never repairers) | Qwen3.5-0.8B, Qwen3.5-9B |

All are 4-bit GGUF files (SHA-256 in `results/ada_model_hashes.txt`) served by llama.cpp commit `162e2bb` through
the `lms` stand-in in `scripts/irel/bin/lms`, on one 48 GB MIG slice of an NVIDIA RTX PRO 6000 Blackwell.
Decoding: temperature 0.7, top-p 0.95, hidden reasoning off, seeds 11, 23, 37. Every step of the study (dataset,
pilot, runs, analysis) ran on this one machine.

## Consequences
- 4-bit was kept for the whole study: full precision did not fit the original hardware, and switching would
  have invalidated everything estimated from the pilot (power, Bhammer cost, time cap).
- Results hold for 4-bit models only (team decision 6 in `prereg/deviations.md`); a full-precision check
  would be a separate study.
- Two jobs ran side by side on the slice, at 12 concurrent requests each.
