# Prove Less, Repair Better
## Automation-Friendly Program Repair for Small Models in Lean 4 — Final Proposal (living document)

**Course:** Agentic Software Engineering (AutoSE, CS6.403) · **Team:** Agents of Ultron — Inesh Dheer, Poojitha J, Gracy Garg
**Repository:** Leanstein (`https://github.com/amoiba42/Leanstein`) · **Version:** v2.1 · last updated 2026-11-03
**Status (2026-11-06):** complete. The whole study ran from scratch on the IREL server (RTX PRO 6000 Blackwell, one 48 GB MIG slice): dataset, probes, pilot, power note, second freeze, 12,249 study runs and the analysis. The paper is `paper/main.pdf`. Post-freeze deviations: D-1 to D-3. Run record: `context/IREL_RUNS.md`; deviations: `prereg/deviations.md` R-1 to R-10.

This is the single document to follow. It supersedes the original proposal and plan where they differ, and it
records *why* each part exists and *where* it lives in the repository. Update the "Status" lines and §12 as the
study progresses; never edit pre-registered parts after `prl freeze` without a logged deviation.

---

## 1. Summary

Small, locally runnable language models are poor at writing Lean 4 proofs; even strong models produce correct
code far more often than valid proofs on verified-code benchmarks such as VERINA. We test whether small models
obtain **more end-to-end verified repairs when they repair only the implementation — shaping it so that a fixed,
pre-registered Lean automation portfolio proves the unchanged specification — than when they write proofs**.
We compare this against budget-matched proof-writing agents, including one that is given the same automation
first, and we measure *why* it works: whether successes come from re-shaping code for automation or merely from
undoing the bug, and which code shapes make automation succeed.

## 2. Inputs this proposal consolidates (all in `context/`)

| Input | Location | How it is used |
|---|---|---|
| Original proposal | `context/InitialProposal/Prove_Less_Repair_Better_Proposal.pdf` | Research question, H1, B vs C, VERINA, integrity rules, outcome labels — **kept** |
| Original project plan | `context/InitialProposal/AutoSE_Project_Plan.pdf` | Team split, interfaces, conditions T/C-plain, pre-registration, gate, backups — **kept** |
| Claude verdict | `context/InitialVerdicts/ClaudeVerdict` | B+P baseline, shaping-vs-reverting metric, T first, floor check — **adopted (mandatory)** |
| Gemini verdict | `context/InitialVerdicts/GeminiVerdict` | Per-category reporting, spec-copying checks, audit — **adopted** |
| GPT verdict | `context/InitialVerdicts/GPTVerdict` | Consolidated framework, proofability study (S), natural + synthetic bugs, generated hidden tests, fair budgets — **adopted as backbone** |
| Gracy's additions | `context/GracyAdditions/Text.txt`, `context/GracyAdditions/images/Gracy1.jpeg`, `context/GracyAdditions/images/Gracy2.jpeg` | Real errors first, energy, sandbox, infra handling, tiered tactics, feedback router, pre-filter, audit, resample cap — **adopted / adapted** (§10) |
| Gracy's revision 3 | GitHub branches `alternate` (architecture docs) and `working` (commit `48e9147`) | B→C cross-evaluation, B proof-tactic logging, pilot power simulation, B-hammer, RAM-aware workers, wall-guard semantics — **adopted / adapted**; reduced Mathlib imports — **declined** (§10b) |

**Agreed verdict:** the proposal's hypothesis, run under the GPT verdict's framework, with Claude's B+P baseline
and shaping metric as mandatory parts of the main study, Gemini's reporting advice, and Gracy's engineering.
Full deliberation: `docs/final_architecture.md` §1–§2b.

## 3. Research gap and novelty (scoped)

Close work (as identified in the proposal and the verdicts; each item is re-checked in the related-work pass
before any submission):

- **Proof repair from compiler feedback** (APRIL, APOLLO, "Fix, Not Just Resample"): repair the *proof*, not the code.
- **Joint program–proof planning** (P³) and **proof stability under refactoring** (RefactorProof, on VERINA):
  code structure matters for proofs, studied with frontier models and model-written proofs.
- **Verification-aware restructuring / repair in Dafny** (Dissect-and-Restore, DafnyFix): SMT-based, not Lean,
  not small models.
- **Strong proof models for code** (Goedel-Code-Prover): large search budgets, model-written proofs.

**Our claim:** we investigate whether resource-constrained code models achieve more reliable formally verified
program repair by optimising implementation structure for a fixed, pre-registered Lean 4 automation pipeline,
rather than generating proofs; we evaluate this against budget-matched proof-writing agents (including one that
gets the same automation first, an exploratory one that is told the automation, and a proof-specialist model), on natural model errors as well as controlled
mutants, and we characterise mechanistically when the gain comes from re-shaping rather than reverting, and which
implementation shapes make automation succeed. We do not claim novelty for compiler feedback, structured repair
messages, automated tactics or code restructuring in isolation.

**What makes it more than a prompting comparison:** (i) the B+P control isolates "do not write proofs" from
"automation exists"; (ii) the shaping-vs-reverting classification and study S (re-shape *correct* code that
automation cannot prove) test the mechanism directly; (iii) a code-shape catalogue (RQ4) and a released
buggy-VERINA dataset with proved-precondition hidden tests; (iv) energy per verified repair on one GPU slice; (v) a
cross-evaluation that re-checks B's own unproved code through C's pipeline, and B reported without single-call
automation proofs.

## 4. Research questions and hypotheses

| RQ | Question | Primary measure | Hypothesis |
|---|---|---|---|
| **RQ1** (confirmatory) | At matched budget, does C beat B and B+P in verified-repair rate? | family-level rate, paired | C > B and C > B+P |
| RQ2 Mechanism | Shaping vs reverting share; can models re-shape correct-but-unprovable code (S vs S-plain)? | shaping share; S rate | non-trivial shaping share; S > S-plain |
| RQ3 Feedback | Does the structured hint beat plain retry? | C vs C-plain | C > C-plain |
| RQ4 Code shapes | Which implementation features predict automation success? | feature tables | a small set explains most successes |
| RQ5 Costs & scale | Tokens, latency, Lean CPU, **energy per verified repair**, patch size, regressions, integrity flags; 2B vs 4B; Qwen vs Gemma | cost and energy tables | exploratory |

A clean negative result is a valid, reported outcome. Details and requirement IDs: `docs/requirements.md` §1.4.

## 5. Method

### 5.1 Benchmark and tasks
VERINA (189 Lean 4 tasks, pinned commit `66b3ce50`). Eligible = reference compiles and passes its tests (a human
proof is *not* required: only 46/189 ship one). Families are the statistical unit; splits are family-level
(pilot 20, main, held-out 30% of main). Code: `prl/tasks/`.

### 5.2 Bugs
- **Natural (primary):** zero-shot implementations from Qwen3.5-0.8B and Qwen3.5-9B (never repairers), ≤4 samples
  per generator per family, kept if they compile and fail ≥1 test, ≤1 per family per generator.
- **Mutants (secondary, controlled):** operators on the implementation (arith, relational, boolean, constants,
  negated conditions, swapped branches, dropped ±1, swapped arguments), kept if they compile and fail a test,
  ≤2 per family. Condition T on each buggy start flags weak specifications.
- **Shaping instances (study S):** correct references that T cannot prove.
- Pre-registered pool rule: natural if ≥60 families of the `main` split have a natural bug (counted from the dataset,
  not from results), else natural ∪ mutant (`prereg/study.yaml: bugs`).
Code: `prl/natural/`, `prl/mutate/`.

### 5.3 Tests
Visible = VERINA tests (one failing witness may be shown). Hidden = generated inputs whose **precondition is
proved in Lean**, expected outputs from the reference, round-trip checked; never shown, failures reported only as a
count. Code: `prl/testgen/`.

### 5.4 Conditions (`prl/conditions/protocols.py`)
| ID | Model writes | Proof from | Feedback |
|---|---|---|---|
| T | — | portfolio | — |
| A | code + proof | model | none (N independent samples) |
| B | code + proof | model | Lean errors, failing witness, proof errors |
| BP | code + proof | portfolio first, else model | as B |
| **C** | code only | portfolio | witness / errors + best unsolved goal + structural hint |
| C-plain | code only | portfolio | generic retry (same format reminder) |
| S / S-plain | code only, from a correct reference | portfolio | as C / as C-plain |
| Bhammer *(exploratory, optional)* | code + proof; prompt lists the frozen portfolio | model | as B |

Bhammer runs for the primary models only if the pilot cost estimate leaves room (decided before the freeze) and
is never pooled with B.

Budget per (instance, condition, model, seed): ≤8 generations, ≤48k tokens, ≤600 s inference (raised from 240 s before the freeze, ADR-003); first cap wins.

### 5.5 Models (`prereg/study.yaml: models`)
Repairers: Qwen3.5-2B, Qwen3.5-4B (primary), Gemma-4-E4B-it (secondary family); proof specialist
Goedel-Code-Prover-8B (A, B); generators Qwen3.5-0.8B, 9B. GGUF 4-bit (SHA-256 in `results/ada_model_hashes.txt`), served by llama.cpp `162e2bb` on the study GPU, temperature 0.7,
top-p 0.95, `reasoning_effort: none`, seeds 11/23/37.

### 5.6 Verification (`prl/lean/`, `lean_env/PrlRepl.lean`)
Lean 4.24.0 + Mathlib v4.24.0. Own verification server (the whole of Mathlib loaded once per worker, 4 GB memory
cap; worker count from free RAM unless configured). Heartbeats are the tactic budget; wall-clock guards (120 s per
request, max(30 s, 120/4) per portfolio entry) only stop hangs.
Staged: compile + all tests (+ model proof), then the two-tier portfolio (Tier L 50k heartbeats, Tier H 200k;
frozen order; early stop). Success = compile ∧ visible ∧ hidden tests ∧ proof by the allowed source ∧ axioms ⊆
{propext, Classical.choice, Quot.sound} ∧ locked regions unchanged ∧ static integrity. Infrastructure failures
never charge the budget; non-terminating candidate code does.

### 5.7 Integrity (`prl/lean/integrity.py`)
Reject before Lean: proof escapes (sorry, admit, axiom, native_decide, implemented_by, unsafe, macros,
set_option, attribute, # commands), redefinition of locked names, proofs in code-only conditions, empty body.
Flag (then audit): spec-copying, constant bodies, hard-coded tests, choice. 10% stratified audit + all flagged
successes (`prl audit`).

### 5.8 Analysis (`prl/analysis/`)
Family score = mean over seeds of "any instance solved". RQ1: one-sided paired sign-flip permutation test,
Holm over the primary tests, McNemar on majority-solved, 95% family-cluster bootstrap CI, Cohen's h, minimum
detectable effect. RQ2: shaping / revert / other; C by reference provability; S vs S-plain. RQ4: feature tables.
RQ5: costs, energy (GPU measured, CPU estimated, CO2 estimated) per verified repair; sensitivity to N.
Secondary (never pooled with the primary estimates): **B_noauto** — B with successes whose proof is a single-call
automation proof counted as failures (from `proof_tactic_used`); **Bhammer** vs B and C; and the **B→C
cross-evaluation** — every B attempt whose code compiled but whose proof failed, re-verified as code only through
C's pipeline (`prl crosseval`), bucketed into proves + tests pass / proves + tests fail (weak contract) / cannot
prove / rejected by integrity.

### 5.9 Pre-registration
Before the freeze, `prl power` simulates the primary test's power from the pilot (three scenarios, sign-flip at
α/4, families and seeds as in the real analysis) and writes `prereg/power_note.json`; VERINA is fixed, so an
underpowered estimate becomes a stated limitation. `prereg/` (study, portfolio, hints, prompts, power note) is
hashed by `prl freeze`, which refuses to run without the power note; the driver refuses confirmatory splits if
anything changed; changes are logged in `prereg/deviations.md` (which also discloses the one v1 number the team saw).

## 6. Architecture

The authoritative diagram is in `docs/final_architecture.md` §5 (Mermaid; renders on GitHub). Layered package
view and component responsibilities: `docs/high_level_design.md`; module-level specification:
`docs/low_level_design.md`.

## 7. Threats to validity (summary)

Construct (a proof certifies only its spec → hidden tests, verified-but-wrong label, weak-spec flags; known
VERINA test defects excluded); selection (coverage reported on the full eligible pool; T is a screening and
stratification variable only); hand-tuning (pilot-only tuning, freeze, held-out run once, disclosure); spec
gaming (static rejection, axiom check, flags, audit); internal (equal budgets and turn-0 information; B+P; B_noauto,
Bhammer and the cross-evaluation against "B is a strawman");
external (small standalone functions; one benchmark; two model families); statistical (family unit, exact tests,
pilot-based power simulation); shared hardware (memory caps, idle-GPU rule, energy per block). Full list: `docs/requirements.md` §13.

## 8. Plan of work and gate

Phases (commands in `README.md`, statuses in `docs/implementation_plan.md`):
0 environment and feasibility (T, compile probe, determinism) → 1 components (done) → 2 dataset → 3 pilot, power
note, gate and freeze → 4 confirmatory run (`main`, `main-shaping`, `heldout` once) → 5 cross-evaluation, analysis
(held-out analysed separately, never pooled) and audit.
**Gate (end of pilot):** T ≥20% of eligible pilot references; compile rate >10% in C; ≥1 hand-verified repair by
C that neither B nor B+P finds; zero false successes; cost fits (the same estimate decides whether Bhammer runs);
power note written (informative, not pass/fail). If the decisive criterion fails: Backup 2 —
proof-friendliness benchmark (T over reference / mutated / model-rewritten code, with study S as headline).

## 9. Team roles

As in the plan (assignment to people to be confirmed by the team): **A — Verification Engine** (`prl/lean`,
`lean_env`, integrity, portfolio, T, RQ4 catalogue); **B — Tasks & Models** (`prl/tasks`, `prl/mutate`,
`prl/natural`, `prl/testgen`, `prl/models`, prompts); **C — Study Lead** (`prereg/`, `prl/conditions`,
`prl/driver`, `prl/analysis`, related work, paper).

## 10. Gracy's additions — resolution

| # | Suggestion | Resolution |
|---|---|---|
| G1 | Real model errors first | Adopted: natural bugs primary (0.8B, 9B; never repairers) |
| G2 | Energy tracking | Adopted: GPU measured via NVML per block; CPU/CO2 estimated and labelled |
| G3 | 2 GB memory sandbox | Adapted: 4 GB Windows Job Object per Lean worker (Mathlib needs ~2.5 GB); not applied on Linux (study server, 503 GB RAM; deviation R-10) |
| G4 | Infra failures don't burn budget | Adopted; candidate-caused timeouts still count after confirmation |
| G5, G6 | model/Lean seconds; log every attempt | Adopted |
| G7 | Adaptive light→heavy tactics | Adopted as deterministic two-tier portfolio, same for every condition |
| G8, G9 | Feedback router; hidden tests private | Adopted (`prl/conditions/feedback.py`) |
| G10 | C-plain | Adopted |
| G11 | Spec-gaming pre-filter | Adopted: reject vs flag |
| G12 | 10% audit | Adopted (+ all flagged successes) |
| G13 | Resample cap | Adopted (4 samples per generator per family) |
| — | B/A get only "failed, retry" (diagram) | Declined: B keeps Lean errors (no strawman), A has no feedback by definition |

## 10b. Gracy's revision 3 — resolution

| # | Suggestion | Resolution |
|---|---|---|
| R3-1 | Cross-evaluate B's compiling-but-unproved code through C's pipeline | Adopted (`prl crosseval`; secondary; fourth bucket for integrity rejections) |
| R3-2 | Log B's proof tactics; report B without single-call automation proofs | Adopted (`proof_tactic_used`, registry frozen in `portfolio.yaml`, derived row `B_noauto`) |
| R3-3 | Pilot power simulation before the freeze | Adopted, adapted (pilot families added to the eligible-family conversion; Holm bound α/4; `prl freeze` requires it) |
| R3-4 | B-hammer | Adopted as optional exploratory arm `Bhammer` |
| R3-5 | RAM-aware Lean workers with override | Adopted |
| R3-6 | Wall guards as backstops, heartbeats as budget | Adopted; enforced (guard ≥ 50 s, positive tier heartbeats) |
| R3-7 | Five tactic modules instead of `import Mathlib` | Declined: three modules do not exist in Mathlib v4.24; a reduced environment changes T coverage, breaks specs and server/CLI parity |
| — | The `alternate` branch's own parameter set (N = 5, 1,024 tokens, second-based tactic budgets, other repo layout, …) | Ours stays authoritative; item-by-item comparison in `docs/final_architecture.md` §2b; the >5% infra-failure stop rule adopted |

## 11. Repository map

| Path | Content |
|---|---|
| `README.md` | setup, pipeline commands, tests |
| `memory.md` | living project memory (decisions, environment facts, lessons, status) |
| `context/` | original inputs (proposal, plan, verdicts, Gracy's additions) |
| `docs/final_proposal.md` | this document |
| `docs/final_architecture.md` | deliberation and the architecture diagram |
| `docs/requirements.md`, `high_level_design.md`, `low_level_design.md`, `implementation_plan.md` | v2.1 specification chain |
| `docs/feasibility.md` | Phase-0 evidence from development; the study probes are in `results/phase0_*.json` |
| `prereg/` | frozen study inputs and the deviation log |
| `prl/` | harness (tasks, lean, testgen, mutate, natural, models, conditions, driver, analysis, energy, cli) |
| `lean_env/` | pinned Lean project and the verification server |
| `tests/` | 96 unit tests + 24 real-Lean integration tests |
| `scripts/pdownload.py` | parallel downloader for throttled networks |

## 12. Status and next steps

- [x] Design consolidated (v2); docs updated; context folder created.
- [x] Harness implemented: all v2 components; lint clean.
- [x] v2.1 (2026-11-03): Gracy's revision-3 notes reconciled (cross-evaluation, proof-tactic logging, power
  simulation, Bhammer, worker sizing adopted; reduced imports declined) and implemented; 95 unit tests and 24 Lean
  integration tests pass.
- [x] Phase 0, dataset, splits, pilot (492 runs), gate, power note and second freeze (`3f2744e1`), all on IREL,
  2026-11-05.
- [x] Study runs (12,249; 1 infrastructure failure), cross-evaluation, analysis, held-out replication, audit
  (by Claude; human confirmation pending), paper (`paper/main.pdf`), 2026-11-06.
- [ ] Human confirmation of the audit; annotated code-shape examples (catalogue tables are in
  `results/rq4_shapes.md`); venue choice.

## 13. Deliverables

Research report; repair harness (`prl/`); buggy-VERINA dataset with provenance and hidden tests; experiment logs;
pre-registered portfolio, prompts and configuration; code-shape catalogue; replication instructions.
