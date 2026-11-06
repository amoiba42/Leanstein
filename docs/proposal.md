# P.I.G. (Proof-Independent Generation): Automation for Structurally Verified Code Patches

**Course:** Agentic Software Engineering (AutoSE, CS6.403) · **Team:** Agents of Ultron — Inesh Dheer, Poojitha J, Gracy Garg
**Codebase:** Leanstein (`https://github.com/amoiba42/Leanstein`)

This document states the final, agreed design. Each decision is recorded as an architecture decision record in
[`docs/adr/`](adr/README.md); changes after the freeze are logged in `prereg/deviations.md`.

## 1. Summary

Small, locally runnable language models write correct code far more often than valid Lean 4 proofs. We test
whether they obtain **more end-to-end verified repairs when they repair only the implementation, so that a fixed,
pre-registered Lean automation portfolio proves the unchanged specification, than when they write proofs**. We
compare this against budget-matched proof-writing agents, including one that is given the same automation first,
and we measure why it works: whether successes come from re-shaping code for automation or from undoing the bug,
and which code shapes make automation succeed.

## 2. Research gap and claim

Close work repairs the *proof* from compiler feedback (APRIL, APOLLO), plans programs and proofs jointly or studies
proof stability under refactoring with frontier models (P³, RefactorProof), restructures code for SMT-based
verification in Dafny (Dissect-and-Restore, DafnyFix), or trains strong proof models with large search budgets
(Goedel-Code-Prover).

**Claim.** Resource-constrained code models can reach more reliable formally verified repair by shaping the
implementation for a fixed, pre-registered Lean 4 automation pipeline instead of generating proofs. We evaluate
this against budget-matched proof-writing agents on natural model errors and controlled mutants, and we
characterise when the gain comes from re-shaping rather than reverting. We do not claim novelty for compiler
feedback, structured repair messages, automated tactics or code restructuring in isolation.

## 3. Research questions and hypotheses

| RQ | Question | Primary measure | Hypothesis |
|---|---|---|---|
| **RQ1** (confirmatory) | At matched budget, does C beat B and BP in verified-repair rate? | family-level rate, paired | C > B and C > BP |
| RQ2 Mechanism | Shaping vs reverting share; can models re-shape correct but unprovable code (S vs S-plain)? | shaping share; S rate | non-trivial shaping share; S > S-plain |
| RQ3 Feedback | Does the structured hint beat a plain retry? | C vs C-plain | C > C-plain |
| RQ4 Code shapes | Which implementation features predict automation success? | feature tables | a small set explains most successes |
| RQ5 Costs and scale | Tokens, latency, Lean CPU, energy per verified repair; 2B vs 4B; Qwen vs Gemma | cost and energy tables | exploratory |

A clean negative result is a valid, reported outcome. Requirement IDs: [`docs/requirements.md`](requirements.md).

## 4. Method

### 4.1 Benchmark and tasks — [ADR 0003](adr/0003-verina-benchmark-and-splits.md)
VERINA (189 Lean 4 tasks, pinned commit `66b3ce50`); 184 eligible after a recorded exclusion list of 5 known-bad
tasks. Family-level splits: pilot 20, main 114, held-out 50. The task family is the statistical unit. Code:
[`prl/tasks/`](../prl/tasks/).

### 4.2 Bugs — [ADR 0004](adr/0004-bug-sources-and-pool-rule.md)
Natural bugs from Qwen3.5-0.8B and 9B (never repairers) and mutants from operators on the reference
implementation, each kept only if it compiles and fails at least one test. Correct references the portfolio cannot
prove form the shaping set (study S). Pool rule: natural only if at least 60 `main` families carry a natural bug,
otherwise natural ∪ mutant. Code: [`prl/natural/`](../prl/natural/), [`prl/mutate/`](../prl/mutate/).

### 4.3 Tests — [ADR 0005](adr/0005-hidden-tests.md)
Visible VERINA tests (one failing witness may be shown); 30 hidden generated tests per family whose precondition is
proved in Lean, with outputs from the reference; never shown to a model. Code: [`prl/testgen/`](../prl/testgen/).

### 4.4 Conditions — [ADR 0001](adr/0001-code-only-repair-with-frozen-portfolio.md), [ADR 0002](adr/0002-control-conditions.md)

| ID | Model writes | Proof from | Feedback |
|---|---|---|---|
| T | — | portfolio | — |
| A | code + proof | model | none (independent samples) |
| B | code + proof | model | Lean errors, failing witness, proof errors |
| BP | code + proof | portfolio first, else model | as B |
| **C** | code only | portfolio | witness / errors + best unsolved goal + structural hint |
| C-plain | code only | portfolio | generic retry |
| S / S-plain | code only, from a correct reference | portfolio | as C / as C-plain |
| Bhammer (exploratory) | code + proof; prompt lists the portfolio | model | as B |

Derived analyses without extra model calls: `B_noauto` and the B→C cross-evaluation.

### 4.5 Budget — [ADR 0008](adr/0008-run-budget.md)
Per (instance, condition, model, seed): at most 8 generations, 48k tokens and 600 s of inference; the first cap
reached ends the run. C, C-plain, S and S-plain sample two candidates per feedback round.

### 4.6 Models and serving — [ADR 0009](adr/0009-models-and-serving.md)
Repairers Qwen3.5-2B and 4B (primary), Gemma-4-E4B (second family), Goedel-Code-Prover-8B (A and B only);
generators Qwen3.5-0.8B and 9B. 4-bit GGUF served by llama.cpp `162e2bb` on one 48 GB MIG slice of an NVIDIA RTX
PRO 6000 Blackwell; temperature 0.7, top-p 0.95, reasoning off, seeds 11, 23, 37.

### 4.7 Verification — [ADR 0006](adr/0006-two-tier-portfolio.md), [ADR 0010](adr/0010-verification-server.md)
Lean 4.24.0 with the whole of Mathlib, loaded once per worker by the verification server [`lean_env/PrlRepl.lean`](../lean_env/PrlRepl.lean).
Staged check: compile and all tests first, then the proof by the allowed source. The portfolio has two frozen
tiers (L at 50k heartbeats, H at 200k) with early stop. Success = compile ∧ visible ∧ hidden tests ∧ proof by the
allowed source ∧ axioms ⊆ {propext, Classical.choice, Quot.sound} ∧ locked regions unchanged ∧ static integrity.
Infrastructure failures never charge the budget; non-terminating candidate code does.

### 4.8 Integrity — [ADR 0007](adr/0007-integrity-checks.md), [ADR 0015](adr/0015-audit.md)
Static checks reject proof escapes, redefinitions of locked names, proofs in code-only conditions and empty bodies.
Suspicious successes are flagged (spec-copying, constant bodies, hard-coded tests, `choice`) and enter the audit.

### 4.9 Analysis — [ADR 0012](adr/0012-statistical-analysis.md), [ADR 0013](adr/0013-shaping-vs-reverting.md), [ADR 0014](adr/0014-energy-measurement.md)
Family score = mean over seeds of "any instance solved". RQ1: one-sided paired sign-flip test, Holm over four
primary tests, cluster bootstrap CIs. RQ2: shaping / revert / other, S vs S-plain. RQ4: code-feature tables. RQ5:
cost and estimated energy per verified repair. Secondary analyses are never pooled with the primary estimates.

### 4.10 Pre-registration — [ADR 0011](adr/0011-pre-registration.md)
A pilot calibrates the protocol, a power simulation states what the study can detect, and [`prereg/`](../prereg/) is frozen by a
hash that the driver re-checks before every confirmatory run. The held-out split is analysed once.

## 5. Threats to validity

- **Construct:** a proof certifies only its specification; hidden tests, weak-spec flags and the audit guard
  against wrong-but-verified code.
- **Selection:** portfolio coverage is reported on the full eligible pool; T is a screening and stratification
  variable only.
- **Hand-tuning:** tuning happens on the pilot only; the configuration is frozen; held-out is run once.
- **Specification gaming:** static rejection, axiom check, flags and audit.
- **Internal:** equal budgets and first-turn information; BP, `B_noauto`, Bhammer and the cross-evaluation test
  whether B is a fair baseline.
- **External:** small standalone functions, one benchmark, two model families, 4-bit models.
- **Statistical:** family as unit, exact tests, pilot-based power simulation; C vs BP is underpowered by VERINA's
  fixed size.

## 6. Plan of work

Phases (commands in [`README.md`](../README.md), tasks in [`docs/implementation_plan.md`](implementation_plan.md)): 0 environment and feasibility →
1 components → 2 dataset → 3 pilot, power note, gate and freeze → 4 confirmatory runs (`main`, `main-shaping`,
`heldout` once) → 5 cross-evaluation, analysis and audit.

**Gate (end of pilot):** T proves at least 20% of eligible references; compile rate above 10% in C; at least one
repair by C that neither B nor BP finds; zero false successes; the cost fits. Fallback if the decisive criterion
fails: a proof-friendliness benchmark (T over reference, mutated and model-rewritten code, with study S as the
headline).

## 7. Team roles

- **A, Verification Engine:** [`prl/lean`](../prl/lean/), `lean_env`, integrity checks, portfolio, condition T, RQ4 catalogue.
- **B, Tasks and Models:** [`prl/tasks`](../prl/tasks/), [`prl/mutate`](../prl/mutate/), [`prl/natural`](../prl/natural/), [`prl/testgen`](../prl/testgen/), [`prl/models`](../prl/models/), prompts.
- **C, Study Lead:** [`prereg/`](../prereg/), [`prl/conditions`](../prl/conditions/), [`prl/driver`](../prl/driver/), [`prl/analysis`](../prl/analysis/), related work, report.

## 8. Deliverables

Research report; repair harness ([`prl/`](../prl/)); buggy-VERINA dataset with provenance and hidden tests; experiment logs;
pre-registered portfolio, prompts and configuration; code-shape catalogue; replication instructions.

## 9. Repository map

| Path | Content |
|---|---|
| [`README.md`](../README.md) | setup, pipeline commands, tests |
| [`docs/proposal.md`](proposal.md) | this document |
| [`docs/adr/`](adr/) | architecture decision records |
| [`docs/requirements.md`](requirements.md), [`high_level_design.md`](high_level_design.md), [`low_level_design.md`](low_level_design.md), [`implementation_plan.md`](implementation_plan.md) | specification chain |
| [`docs/feasibility.md`](feasibility.md) | Phase-0 evidence; study probes in `results/phase0_*.json` |
| `context/` | original proposal and plan |
| [`prereg/`](../prereg/) | frozen study inputs and the deviation log |
| [`prl/`](../prl/) | harness (tasks, lean, testgen, mutate, natural, models, conditions, driver, analysis, energy, cli) |
| [`lean_env/`](../lean_env/) | pinned Lean project and the verification server |
| [`tests/`](../tests/) | unit tests and real-Lean integration tests |
| [`scripts/irel/`](../scripts/irel/) | setup and job scripts used for the study runs |
| [`data/`](../data/), [`runs/`](../runs/), [`results/`](../results/) | dataset, run logs and analysis outputs |
