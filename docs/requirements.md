# Requirements Specification

**Project:** P.I.G. (Proof-Independent Generation): Automation for Structurally Verified Code Patches (package `prl`)
**Course:** Agentic Software Engineering (AutoSE, CS6.403) · Team *Agents of Ultron*
**Related:** [`docs/proposal.md`](proposal.md) (final design) and [`docs/adr/`](adr/) (design decisions).

---

## 0. How to read this document

Requirements use the IDs `FR-*` (functional), `NFR-*` (non-functional), `SR-*` (scientific / methodological), `IR-*` (integrity), and `DR-*` (data). Every requirement is *testable*: section 9 maps each to the check that proves it. "MUST" is mandatory for the confirmatory study; "SHOULD" is required unless a documented deviation is filed in [`prereg/deviations.md`](../prereg/deviations.md); "MAY" is optional.

Section 2 lists the fixed design parameters; the reasons for each are in [`docs/adr/`](adr/).

---

## 1. Research goal

### 1.1 One-line idea
Do not make small models write Lean proofs. Have them repair the code into a shape that a **fixed, pre-registered Lean 4 automation portfolio** can prove against the **unchanged** specification.

### 1.2 Central hypothesis
**H1.** Under matched model budgets, small local models obtain *more end-to-end verified repairs* when they edit only the implementation and delegate the proof to fixed automation (condition **C**) than when they write proofs (conditions **B** and **B+P**).

**H0.** No difference, or proof-writing is at least as good.

A clean negative result is a valid, reported outcome.

### 1.3 The novelty claim (scoped)
> We investigate whether resource-constrained code models can achieve more reliable formally verified program repair by optimizing implementation structure for a fixed, pre-registered Lean 4 automation pipeline, rather than generating proofs themselves. We evaluate this strategy against budget-matched proof-writing agents — including one that may use the same automation — and characterize, mechanistically, *when the gain comes from re-shaping code rather than from reverting the defect*, and which implementation shapes make automation succeed.

We do **not** claim novelty for compiler feedback, structured repair messages, automated tactics, or code restructuring in isolation (Dissect-and-Restore, DafnyFix, P³, RefactorProof exist). The claim is the combination plus the mechanism evidence.

### 1.4 Research questions (frozen set)

| ID | Question | Primary measure | Hypothesis |
|---|---|---|---|
| **RQ1 Effectiveness** (confirmatory) | At matched budget, does C achieve a higher verified-repair rate than B (model writes proof) and than B+P (model writes proof only when the same portfolio fails)? | Verified-repair rate, paired by task family | C > B and C > B+P |
| **RQ2 Mechanism** | Do C's successes come from *shaping* (a structurally different implementation that automation proves when the reference is not automation-provable) or from *reverting* the defect? Can a small model re-shape an already-correct but automation-resistant implementation (study **S**)? | Shaping share; patch distance to reference; S success rate | A non-empty, non-trivial shaping share exists; S > S-plain |
| **RQ3 Feedback** | Does structured stuck-point feedback (failing witness + unsolved goal + rule-based structural hint) beat a plain retry? | C vs C-plain | C > C-plain |
| **RQ4 Code shapes** | Which implementation features predict automation success? | Feature catalogue + logistic model over all verified candidates | A small set of features explains most successes |
| **RQ5 Trade-offs & scale** | What are the costs (tokens, latency, Lean CPU, patch size, behavioural regressions, integrity flags), and what is the energy per verified repair (GPU measured, CPU estimated), and how does the B–C gap change with model size (2B → 4B) and family (Qwen vs Gemma)? | Cost tables; gap per model | Gap shrinks with scale (exploratory) |

RQ1 is the only confirmatory question. RQ2–RQ5 are pre-registered but exploratory; they are reported with uncertainty and no claim of significance beyond what is computed.

---

## 2. Fixed design parameters

- **Benchmark figures.** VERINA (arXiv 2505.23135, v3, ICLR 2026; pass@1, one trial per task): the best model (OpenAI o3) reaches 72.6% code correctness but 4.9% proof success. Always cite the paper version (v3).
- **Coverage gate.** A screening criterion, not a result: T must prove ≥20% of the eligible pilot references. Portfolio coverage is reported on *all* eligible references.
- **Budget.** N_gen = 8 model generations per (task, condition, model, seed) for every iterative condition, plus caps on total tokens and inference time (FR-BUD). C samples in rounds of k=2 (4 rounds); B/B+P use 8 sequential turns; A uses 8 independent samples (pass@8). Sensitivity at N∈{2,4,8} is computed from the logs. See [`docs/adr/0008-run-budget.md`](adr/0008-run-budget.md).
- **Tactic portfolio.** One frozen, ordered list in [`prereg/portfolio.yaml`](../prereg/portfolio.yaml) (hashed), including `fun_induction` templates available in Lean 4.24. See [`docs/adr/0006-two-tier-portfolio.md`](adr/0006-two-tier-portfolio.md).
- **Conditions.** T, A, B, B+P, C, C-plain, S/S-plain, plus the exploratory Bhammer arm. See [`docs/adr/0002-control-conditions.md`](adr/0002-control-conditions.md).
- **Integrity.** Static rejection of `sorry`, `admit`, new axioms, `native_decide`, `implemented_by`, `unsafe` and the other escapes in IR-*.
- **Tests.** VERINA's own tests are *visible* (one failing witness may be shown); generated differential tests are *hidden* (never shown, never in prompts). See [`docs/adr/0005-hidden-tests.md`](adr/0005-hidden-tests.md).
- **Models.** Primary repairers Qwen3.5-2B and Qwen3.5-4B; secondary repairer Gemma-4-E4B (other family); proof-specialist reference Goedel-Code-Prover-8B (conditions A and B); natural-bug generators Qwen3.5-0.8B and Qwen3.5-9B, never used as repairers. All 4-bit GGUF. See [`docs/adr/0009-models-and-serving.md`](adr/0009-models-and-serving.md).
- **Lean.** Lean `v4.24.0` with Mathlib `v4.24.0`, the version VERINA ships a migration script for (`setup_lean_v424.sh`).
- **Inference server.** An OpenAI-compatible endpoint backed by llama.cpp (LM Studio during development; `llama-server` for the study).

---

## 3. Stakeholders and actors

| Actor | Role |
|---|---|
| Member A (Verification Engine) | Owns everything that runs Lean |
| Member B (Tasks and Models) | Owns task construction, mutation, model serving, prompts, generation |
| Member C (Study Lead) | Owns pre-registration, driver, statistics, paper |
| Small model (agent) | Untrusted producer of candidate code/proofs |
| Lean kernel | Trusted judge of proofs |
| Reviewer / replicator | Must be able to regenerate every number from raw logs |

The model is **untrusted**: all its output is treated as adversarial input to the verifier.

---

## 4. Functional requirements

### 4.1 Task construction (Member B)

- **FR-TASK-1 (MUST)** Load all 189 VERINA tasks from the pinned commit (`66b3ce50…`), parsing the `!benchmark @start/@end` regions: `import`, `solution_aux`, `precond_aux`, `precond`, `code_aux`, `code`, `postcond_aux`, `postcond`, `proof_aux`, `proof`.
- **FR-TASK-2 (MUST)** Check every reference: compile on the pinned toolchain; pass all VERINA tests. Eligibility = compiles ∧ passes tests. Tasks failing either are *excluded with a recorded reason*. The human reference proof is checked **when present** (finding: only 46/189 VERINA tasks ship a proof; 143 have `sorry`), and recorded as `ref_proof ∈ {human_ok, human_broken, absent}` — it is never used by any condition, and its absence is not an exclusion reason. (For `absent` tasks, any portfolio-closed proof is a proof nobody had produced; this is reported as a by-product of T.)
- **FR-TASK-3 (MUST)** Exclude tasks with known specification defects (the published VERINA specification audit) when a machine-readable list is available; otherwise flag tasks where the reference proof is absent or uses `sorry`.
- **FR-TASK-4 (MUST)** A *task family* = one VERINA task. Every derived instance (mutant, natural bug, seed) belongs to its family. Families are the statistical unit.
- **FR-TASK-5 (MUST)** Splits at family level with a fixed seed: `pilot` (20 families, stratified by basic/advanced), `main` (remaining eligible). A held-out portion of `main` (~30%) is locked and run once (`heldout`); it is analysed separately as a replication and never pooled into the confirmatory tests, which use `main`.
- **FR-TASK-6 (MUST)** Emit one JSON task manifest per instance (schema in LLD §3) including SHA-256 hashes of all locked regions and test files.

### 4.2 Bug sources (Member B)

- **FR-MUT-1 (MUST)** Mutation operators on the `code` + `code_aux` regions only: arithmetic operator swap, relational operator flip, boolean connective swap, off-by-one on numeric literals/bounds, wrong initial accumulator value, swapped `if` branches, negated condition, swapped arguments of a binary call, dropped `+1`/`-1` in recursive calls.
- **FR-MUT-2 (MUST)** A mutant is kept only if (a) it compiles, (b) it fails ≥1 visible or hidden test (a *failing witness* exists), and (c) its family's reference passes all tests. Equivalent mutants (pass all tests) are discarded.
- **FR-MUT-3 (MUST)** Choose ≤2 mutants per family by deterministic seeded sampling stratified over operator class; record operator, location, original and mutated text.
- **FR-MUT-4 (MUST)** Mutation is deterministic given a seed.
- **FR-NAT-1 (MUST)** Natural bugs (**primary bug pool**): for each family, sample zero-shot implementations (no faulty code shown) from the generators Qwen3.5-0.8B and Qwen3.5-9B, which are never repairers; at most 4 samples per generator per family (resample cap); keep those that compile and fail at least one test; at most 1 per family per generator. Reported separately from mutants.
- **FR-NAT-2 (MUST)** Primary-pool rule (pre-registered in [`prereg/study.yaml: bugs`](../prereg/study.yaml)): the confirmatory bug pool is *natural* if natural bugs cover at least 60 families of the confirmatory `main` split, otherwise *natural ∪ mutant*. The count is taken from the dataset manifests (not from run results), so the pilot power note, the main analysis and the held-out analysis all use the same pool. Mutants are always reported separately.

### 4.3 Behavioural tests (Member A/B)

- **FR-TEST-1 (MUST)** Visible tests: VERINA `test.json`. Executed in Lean via `#guard` on the compiled candidate.
- **FR-TEST-2 (MUST)** Hidden differential tests: for each family generate up to 30 random inputs per signature type (Int, Nat, Bool, Char, String, List/Array of these, tuples, Option), filter by the precondition (decided in Lean when decidable; otherwise only inputs from VERINA's own tests and their small perturbations that the reference handles without panic are used), compute expected outputs **by evaluating the reference in Lean**. Stored outside any prompt-visible directory.
- **FR-TEST-3 (MUST)** A candidate's test result = pass on all visible ∧ all hidden tests. Execution uses a heartbeat/time limit; timeouts count as fail.

### 4.4 Verification service `verify()` (Member A)

- **FR-VER-1 (MUST)** `verify(task, code_region, proof=None, mode)` where `mode ∈ {portfolio, model_proof, portfolio_then_model}` returns: `compile_ok`, `tests_visible_pass`, `tests_hidden_pass`, `proof_ok`, `proof_source ∈ {portfolio, model, none}`, `closing_tactic`, `integrity_ok` with reason list, `axioms`, `hint` (structured), `lean_errors` (truncated), `lean_secs`.
- **FR-VER-2 (MUST)** The candidate is spliced *only* into `code_aux` and `code` (and, for proof modes, `proof_aux` and `proof`). Every other region is copied verbatim from the locked reference and its hash re-checked.
- **FR-VER-3 (MUST)** Portfolio mode runs every portfolio entry (FR-PORT) and returns the first entry (in frozen order) that closes the theorem.
- **FR-VER-4 (MUST)** Deterministic: identical inputs give identical outputs (resource limits are expressed in Lean heartbeats, not wall clock, for every pass/fail decision; wall-clock caps only guard against hangs, see FR-FAIL-2).
- **FR-VER-7 (MUST)** Staged verification: stage 1 = compile + all tests (+ the model's proof in A/B/BP) in one request; stage 2 = portfolio, only when the code compiles and passes all tests (success is otherwise impossible).
- **FR-VER-5 (MUST)** Results are content-addressed cached (key = hash of rendered Lean file + toolchain + portfolio hash).
- **FR-VER-6 (MUST)** The accepted theorem is checked with `#print axioms`; only `propext`, `Classical.choice`, `Quot.sound` are allowed.

### 4.5 Automation portfolio (Member A)

- **FR-PORT-1 (MUST)** A fixed, ordered list of proof scripts, each a closed tactic block not depending on the task except through *names derived mechanically* from the signature (function name, `_postcond`, `_precond`, parameter names, helper names declared in `code_aux`). Families: `decide`; `simp` / `simp_all` (with function/postcond unfolded); `omega`; `grind`; `aesop`; `unfold … ; split <;> simp_all`; `fun_induction f <;> simp_all` / `<;> grind`; structural `induction` on each List/Array/Nat parameter with `simp_all`/`grind`/`omega` closers.
- **FR-PORT-2 (MUST)** Each entry runs under `set_option maxHeartbeats H` (frozen H > 0; `maxHeartbeats 0` is never allowed in a portfolio entry and the loader rejects it). Heartbeats are the tactic budget; wall-clock guards are hang backstops only: the per-request guard `lean.wall_guard_s` (120 s, must be ≥ 50 s) and, per portfolio entry, max(30 s, guard/4).
- **FR-PORT-3 (MUST)** Frozen in [`prereg/portfolio.yaml`](../prereg/portfolio.yaml) with SHA-256 before the confirmatory run. Tuning allowed only on pilot families. Any change after freeze is a logged deviation; results from different portfolios are never pooled.
- **FR-PORT-4 (MUST)** No per-task customization and no model-chosen tactics in C, C-plain, S.
- **FR-PORT-5 (MUST)** Two tiers: all Tier-L entries (decide, simp, simp_all, omega, split; 50k heartbeats each) before Tier-H entries (grind, aesop, fun_induction, induction; 200k). Limits are heartbeats (deterministic). Entries run in frozen order and stop at the first closing entry (full vector only for T). The same portfolio is used by T, BP, C, C-plain, S and S-plain.

### 4.6 Hint extractor (Member A)

- **FR-HINT-1 (MUST)** Deterministic, rule-based, no LLM (used by the feedback router for C and S). Inputs: the candidate, the Lean output of the best portfolio entry (the one leaving the fewest/smallest unsolved goals).
- **FR-HINT-2 (MUST)** Emits: failing witness (if tests fail: input, expected, actual — visible tests only), first unsolved goal (pretty-printed, truncated to a frozen character cap), and zero or more structural pointers from a fixed catalogue: `partial_def`, `well_founded_recursion` (uses `termination_by`/`decreasing_by`), `loop_imperative` (`for`/`while`/`do`-notation with mutation), `nat_int_mixing` (casts `Int.toNat`, `↑`), `opaque_helper` (helper not unfolded), `array_index_proof` (`arr[i]!`/`get!`), `spec_recursion_mismatch` (postcond is quantified over indices while code recurses over a list, etc.), `fold_accumulator`.
- **FR-HINT-3 (MUST)** Hint length ≤ frozen cap (default 1,200 characters).

### 4.6b Feedback router (Members A/B)

- **FR-FB-1 (MUST)** One router maps (failure type × condition) to the next-turn message. Failure types: extraction, integrity, compile, visible-test, hidden-test, timeout/resource, proof.
- **FR-FB-2 (MUST)** A: no feedback. B/BP/Bhammer: Lean errors, failing visible witness, proof errors. C/S: the same core message plus the structural hint (FR-HINT). C-plain/S-plain: a fixed generic message with the same output-format reminder as C.
- **FR-FB-3 (MUST)** Hidden-test failures are reported only as a count, never inputs or expected outputs.

### 4.6c Resources, failures, energy (Members A/C)

- **FR-RES-1 (MUST)** Each Lean worker runs under a per-process memory cap (Windows Job Object, default 4 GB) and a per-request wall guard; the number of workers is `lean.workers`, or, when it is 0, derived from free RAM at start (max 6); `--lean-workers` or `PRL_LEAN_WORKERS` override it.
- **FR-RES-2 (MUST)** Lean verification uses a persistent verification server ([`lean_env/PrlRepl.lean`](../lean_env/PrlRepl.lean)) that imports the **whole of Mathlib** once per worker and elaborates each file against a fresh copy of that environment; result parity with the plain `lean` CLI is tested. A reduced import set is not allowed (it changes what the portfolio can prove and breaks parity; see [`docs/adr/0010-verification-server.md`](adr/0010-verification-server.md)).
- **FR-FAIL-1 (MUST)** Infrastructure failures (verifier crash, spawn failure, model-server errors) re-verify or re-request the *same* candidate and never charge the model budget; persistent infrastructure failure abandons the run, which the resumable driver re-executes.
- **FR-FAIL-2 (MUST)** A timeout or worker death while evaluating a candidate is confirmed once in a fresh worker; if it repeats, it is the candidate's fault (non-terminating or memory-exhausting code) and counts as a failed attempt (`failure_kind` timeout/resource).
- **FR-FAIL-3 (MUST)** Every attempt record carries `failure_kind` in {None, extraction, integrity, compile, test, timeout, resource, proof}.
- **FR-EN-1 (MUST)** GPU energy is measured with the NVML cumulative energy counter per (model, condition) block; the driver runs blocks sequentially.
- **FR-EN-2 (MUST)** Lean CPU energy is estimated as Lean-worker CPU-seconds × per-thread power (configured; i7-14650HX 55 W / 24 threads) and labelled as an estimate; CO2 = energy × configured grid intensity.
- **FR-EN-3 (MUST)** RQ5 reports energy per verified repair per (model, condition).

### 4.7 Integrity checker (Member A)

See IR-1..IR-9 (§6). Must reject before any proof is attempted when a static violation exists.

### 4.8 Model service `generate()` (Member B)

- **FR-GEN-1 (MUST)** `generate(task_view, condition, history, seed, model)` returns raw text, extracted code region(s), extracted proof (proof conditions only), token counts (prompt, completion), inference seconds.
- **FR-GEN-2 (MUST)** Uses the LM Studio OpenAI-compatible API with fixed decoding (`temperature`, `top_p`, `max_tokens`, `seed`), reasoning/thinking disabled, frozen prompt templates.
- **FR-GEN-3 (MUST)** The prompt-visible `task_view` contains only: NL description, signature, precondition and postcondition text (Lean), the faulty implementation, the condition-specific feedback. It never contains the reference implementation, reference proof, hidden tests, or file paths to them.
- **FR-GEN-4 (MUST)** Robust extraction: fenced code blocks, unfenced output, multiple blocks, truncated output; extraction failures are logged as attempts with `extract_ok=false` (they consume budget).
- **FR-GEN-5 (MUST)** Same `(prompt, seed, decoding, model)` → same text (determinism probe in Phase 0; if the backend is non-deterministic, this is documented and seeds are still logged).

### 4.9 Conditions (Member C defines, B implements prompts, A provides verification)

| ID | Name | Model writes | Feedback per turn | Proof from | Role |
|---|---|---|---|---|---|
| **FR-COND-1 T** | Automation reference | nothing | — | portfolio | Coverage upper bound on reference; must fail on buggy |
| **FR-COND-2 A** | Independent sampling | code + proof | none (N independent samples) | model | Lower bound (pass@N) |
| **FR-COND-3 B** | Feedback-guided proof-writing | code + proof | Lean errors + failing witness | model | Fair proof-writing control |
| **FR-COND-4 B+P** | Proof-writing with automation first | code + proof | Lean errors + failing witness | portfolio if it closes, else model's proof | Isolates "don't write proofs" |
| **FR-COND-5 C** | Automation-friendly repair (proposed) | code only | failing witness + unsolved goal + structural hint | portfolio | The contribution |
| **FR-COND-6 C-plain** | Code-only, plain retry | code only | "The candidate was rejected. Try again." | portfolio | RQ3 ablation |
| **FR-COND-7 S / S-plain** | Proofability shaping study | code only, starting from the *correct reference* that T cannot prove | S: goal + hint; S-plain: plain retry | portfolio | RQ2 mechanism |
| **FR-COND-10 Bhammer** (exploratory) | B told the automation | code + proof; the prompt also lists the frozen portfolio scripts expanded for the task | as B | model | Is C's gain more than knowing which tactics exist? (FR-ANA-9) |

- **FR-COND-8 (MUST)** All conditions use identical task instances, models, decoding, budgets and the same initial preflight (compile + visible tests + portfolio on the faulty code). The preflight output is not charged to the model budget.
- **FR-COND-9 (MUST)** In C, C-plain, S, any candidate that contains proof text, tactic blocks, `theorem`/`lemma` declarations, attributes that change simp sets globally (`@[simp]` on new declarations is allowed only on helper *definitions* inside `code_aux`; `attribute [simp]` commands are rejected), or edits outside the region is rejected (counts as a used attempt).

### 4.10 Budget (Member C)

- **FR-BUD-1 (MUST)** Max model generations N_gen = 8 per (instance, condition, model, seed).
- **FR-BUD-2 (MUST)** Max total tokens (prompt + completion) per (instance, condition, model, seed) = frozen cap (default 48,000); max completion tokens per generation = frozen cap (default 1,536).
- **FR-BUD-3 (MUST)** Max model-inference wall time per (instance, condition, model, seed) = frozen cap (600 s; 240 s before team decision 3, see [`docs/adr/0008-run-budget.md`](adr/0008-run-budget.md)). Whichever of FR-BUD-1..3 binds first ends the run.
- **FR-BUD-4 (MUST)** Lean time per verification is capped (heartbeats + wall guard) and reported separately; it is *not* charged to the model budget but is reported (RQ5), together with energy (FR-EN).

### 4.11 Experiment driver (Member C)

- **FR-DRV-1 (MUST)** Iterates (split, condition, model, seed, instance), calls `generate` then `verify`, appends one attempt record (JSONL) per generation and one run record per (instance, condition, model, seed).
- **FR-DRV-2 (MUST)** Crash-safe and resumable: completed runs are skipped; partial runs restart from scratch (so budgets remain exact).
- **FR-DRV-3 (MUST)** Deterministic order; parallel Lean verification workers; model calls serialized per GPU.
- **FR-DRV-4 (MUST)** One command runs the full study from a config file; one command regenerates all tables and figures from logs.
- **FR-DRV-5 (MUST)** Infrastructure failures (server down, OOM, Lean crash) are retried; model failures are never retried.

### 4.12 Analysis (Member C)

- **FR-ANA-1 (MUST)** Outcome labelling per run: `verified_repair`, `verified_but_behaviourally_wrong` (proof ok, hidden tests fail), `behaviourally_correct_unverified`, `integrity_violation`, `unresolved`.
- **FR-ANA-2 (MUST)** Overlap (Venn) of solved families: only-B, only-C, both, neither — per model.
- **FR-ANA-3 (MUST)** Mechanism classification of every C success (SR-MECH).
- **FR-ANA-4 (MUST)** Code-shape feature extraction on every verified and every unverified-but-test-passing candidate (RQ4).
- **FR-ANA-5 (MUST)** Statistical tests per SR-STAT; tables + figures written to [`results/`](../results/).
- **FR-ANA-6 (MUST)** 10% stratified hand-audit sample exported for manual review with a form (CSV) and the results folded back.
- **FR-ANA-7 (MUST)** Run the B-to-C cross-evaluation (`prl crosseval`, Lean only, no model): for every B attempt whose code compiles but whose model proof fails, take only the implementation regions (`code_aux`, `code`), drop all proof text, and verify that implementation through C's complete pipeline (static integrity, visible + hidden tests, frozen portfolio run even when tests fail, `#print axioms`). Identical code of a family is verified once. Records carry `analysis_kind = "b_to_c_cross_eval"`, live in `runs/<study>/crosseval.jsonl`, and are never merged into the primary B or C estimates. Buckets (mutually exclusive): `c_proves_tests_pass` (a verified repair B's proof missed); `c_proves_tests_fail` (behaviourally wrong yet provable: a finding about a weak contract, never a repair); `c_cannot_prove`; and `c_rejected_integrity` (C's static checks reject the code; expected to be rare, reported separately).
- **FR-ANA-8 (MUST)** Every attempt of a proof-writing condition logs `proof_tactic_used` (sorted tactic names found in the model's proof) and `automation_only_proof`. A proof is a *single-call automation proof* when it declares no helper lemma and every tactic it uses is in the frozen registry `single_call_automation` of [`prereg/portfolio.yaml`](../prereg/portfolio.yaml) (or is glue: `intro`, `intros`, `unfold`, `first`, `try`, `repeat`, `all_goals`, `any_goals`). B is reported twice: overall, and as the derived row `B_noauto` in which such successes count as failures. The exclusion is analysis-only; automation remains legal and the raw records are unchanged.
- **FR-ANA-9 (SHOULD)** If the pilot cost estimate leaves room in the compute budget (decided and logged before the freeze), run the exploratory arm **Bhammer** (FR-COND-10) for the primary models, report its additional compute cost, and never replace or pool it with the primary B arm. Bhammer tests whether C's benefit is code shaping rather than mere awareness of automation.

---

## 5. Scientific / methodological requirements

### 5.1 Pre-registration
- **SR-PRE-1 (MUST)** Before the confirmatory run, [`prereg/`](../prereg/) contains: RQs and hypotheses, definitions, portfolio, hint catalogue, prompt templates, decoding configs, budgets, seeds, split assignment, analysis plan, and a `FREEZE.json` with SHA-256 of each file and the timestamp.
- **SR-PRE-2 (MUST)** The driver refuses to run a `main`/`heldout` split if any [`prereg/`](../prereg/) file hash differs from `FREEZE.json`.
- **SR-PRE-3 (MUST)** Pilot families never enter confirmatory results.

### 5.2 Selection
- **SR-SEL-1 (MUST)** Portfolio coverage (T) is reported on *all* eligible references, with counts screened / included / excluded and reasons.
- **SR-SEL-2 (MUST)** The confirmatory pool is **not** filtered by T outcome. T outcome is used only as a stratification variable (RQ2).

### 5.3 Mechanism (RQ2)
- **SR-MECH-1 (MUST)** For each verified C repair compute: (a) whether T proves the reference (`ref_auto`); (b) normalized token edit distance between repair and reference, and between repair and the faulty program; (c) whether the repair is α-/whitespace-equivalent to the reference.
- **SR-MECH-2 (MUST)** Classify: **revert** = equivalent to reference, or `ref_auto` ∧ distance-to-reference ≤ threshold; **shaping** = ¬`ref_auto` (the reference itself is not automation-provable, so success needed a different shape); **other** = remainder.
- **SR-MECH-3 (MUST)** Report the shaping share with a 95% bootstrap CI, and C's success rate stratified by `ref_auto`.
- **SR-MECH-4 (MUST)** Study S reports the fraction of automation-resistant correct references that the model makes automation-provable without behavioural change (all tests pass), with S vs S-plain paired.

### 5.4 Statistics
- **SR-STAT-1 (MUST)** Unit of analysis: task family. A family is "solved" by a (condition, model, seed) if any of its instances is solved; the family-level score for a (condition, model) is the mean over seeds (∈ {0, 1/3, 2/3, 1}).
- **SR-STAT-2 (MUST)** Primary test (RQ1): one-sided paired sign-flip permutation test on family scores, C vs B and C vs B+P, per primary model, Holm-corrected over the 4 tests (2 comparisons × 2 primary models). α = 0.05.
- **SR-STAT-3 (MUST)** Supporting: exact McNemar on the "solved in majority of seeds" binary; family-cluster bootstrap 95% CI (10,000 resamples, fixed seed) of the rate difference; Cohen's h effect size; number of discordant families.
- **SR-STAT-4 (MUST)** Before freezing, estimate paired power from the pilot (`prl power --study pilot`). For each primary model and primary comparison (C vs B, C vs B+P) compute, at the family level, `p10 = P(C solved, baseline failed)`, `p01 = P(baseline solved, C failed)`, `p_both` and `p_neither` from the majority-solved outcome over the three seeds. Because 20 pilot families give noisy estimates, simulate three scenarios — `point` (add-½ smoothed), `pessimistic` (p10 at the lower and p01 at the upper 80% Jeffreys bound) and `optimistic` (the reverse) — instead of one point estimate. Each simulated family draws its category and then a (score_C, score_baseline) pair from the pilot families of that category, so the simulation uses the same task-clustered unit and the same one-sided sign-flip test as the confirmatory analysis, at α/4 (the smallest per-test level Holm can require over the 4 primary tests); the exact McNemar rate (`statsmodels.stats.contingency_tables.mcnemar`) is reported beside it. Report the smallest number of confirmatory (`main`) families reaching 80% power, its conversion to total eligible families = ⌈n_main / 0.70⌉ + 20 pilot families, and the power at the actual `main` size. The note is written to [`prereg/power_note.json`](../prereg/power_note.json) (frozen) and [`results/power_note.md`](../results/power_note.md); `prl freeze` refuses to run without it. VERINA is fixed, so an underpowered estimate is recorded as a limitation, not fixed by adding tasks.
- **SR-STAT-5 (MUST)** With observed `D = b + c` discordant families, report the minimum detectable split and the observed `b`/`c` counts.
- **SR-STAT-6 (MUST)** No post-hoc subsets in confirmatory claims; any exploratory subset is labelled as such.
- **SR-STAT-7 (SHOULD)** Stratify by tier (basic/advanced), bug operator class, bug source (mutant/natural), `ref_auto`, and input type (scalar / list / array / string).
- **SR-STAT-8 (MUST)** Secondary model-scale and family results are descriptive with CIs.

---

## 6. Integrity requirements (zero false successes)

- **IR-1** Locked regions (imports, precond(+aux), postcond(+aux), theorem statement, test harness) are re-rendered from the reference and their SHA-256 hashes verified on every verification.
- **IR-2** Forbidden tokens in any model-written region (word-boundary match after comment stripping): `sorry`, `admit`, `axiom`, `native_decide`, `implemented_by`, `extern`, `unsafe`, `opaque`, `@[csimp]`, `macro`, `syntax`, `elab`, `run_tac`, `run_cmd`, `#eval`, `#exit`, `set_option`, `import`, `open ... in` targeting `Lean.Elab`, `Decidable.decide` overrides via `instance` on the postcond, `local notation`, `attribute`.
- **IR-3** `#print axioms` of the accepted theorem ⊆ {`propext`, `Classical.choice`, `Quot.sound`}.
- **IR-4** In code-only conditions the candidate may not contain `theorem`, `lemma`, `example` or `instance` declarations, nor redefine names of locked declarations (`f_precond`, `f_postcond`, `f_spec_satisfied`, any `solution_aux` name). `by` blocks *inside code* (termination, `decreasing_by`, array-bound proofs) are allowed: the return type is locked, so a term-level proof inside the implementation cannot discharge the locked theorem. (Refined during design; the original heuristic would reject legitimate `arr[i]'(by omega)` code.)
- **IR-5** The function signature (name, parameter names and types, return type, `h_precond` argument) must be unchanged.
- **IR-6** Verified-but-behaviourally-wrong outcomes are never counted as successes.
- **IR-7** Spec-copying / degenerate code flags (flag, not reject; every flagged success enters the audit): constant body (`true`, `0`, `[]`, ...); implementation mentions `_postcond`; uses `Classical.choose`/`Classical.epsilon`/`Exists.choose`; complexity blow-up (runtime on hidden tests > 20× reference, via heartbeat count); hard-coded outputs (a literal table matching test inputs). Flags are recorded; flagged *successes* go to the mandatory audit.
- **IR-8** An integrity test suite (unit tests) MUST show that each of the following is rejected: `sorry` in code, `axiom` declaration, `native_decide`, weakened postcond, edited test, edited theorem statement, edit outside region, `implemented_by`, `unsafe def`, `attribute [simp]`, a proof block in a code-only condition, a `macro` that redefines a tactic.
- **IR-9** The model never sees tests (hidden), the reference implementation, or the reference proof, and the prompt-render function is unit-tested for this.

---

## 7. Data requirements

- **DR-1** Raw data immutability: VERINA checkout is read-only input; derived artefacts live in [`data/`](../data/).
- **DR-BUG-1** Mutant provenance table: family, operator, location (line/col), before/after snippet, failing witness, seed.
- **DR-BUG-2** Natural-bug provenance: generator model, seed, raw output, failing witness.
- **DR-TEST-1** Visible tests copied from VERINA with hashes.
- **DR-TEST-2** Hidden tests: generator seed, inputs, reference outputs, hash; stored in [`data/hidden/`](../data/hidden/) which the prompt builder cannot read (enforced by an allow-list in the prompt builder).
- **DR-LOG-1** Attempt record (JSONL) fields: see LLD §3.4, including `proof_tactic_used` and `automation_only_proof` for proof-writing conditions.
- **DR-LOG-3** Cross-evaluation records (`runs/<study>/crosseval.jsonl`) and the power note ([`prereg/power_note.json`](../prereg/power_note.json)) are stored next to the logs they derive from.
- **DR-LOG-2** Every prompt, raw output, rendered Lean file hash, and Lean log is stored (Lean logs compressed).
- **DR-REL** Release package: manifests, mutation scripts, provenance tables, prompts, portfolio, logs, analysis scripts, environment description (subject to VERINA licence, Apache-2.0).

---

## 8. Non-functional requirements

| ID | Requirement |
|---|---|
| **NFR-ENV-1** | Runs on one machine with one small GPU, no paid API, no training. Developed on a Windows 11 laptop (RTX 5060, 8 GB); the study ran on one 48 GB MIG slice of an RTX PRO 6000 Blackwell (Linux), deviation R-3. |
| **NFR-ENV-2** | Pinned: Lean `v4.24.0`, Mathlib `v4.24.0` (lake-manifest committed), VERINA commit `66b3ce5014edafb20cb26b87c681e7f31847249f`, Python ≥3.12 with a lockfile ([`uv.lock`](../uv.lock)), model GGUF SHA-256 recorded. |
| **NFR-REP-1** | Every number in the report regenerates from raw logs with one command. |
| **NFR-REP-2** | A fresh clone + `scripts/setup` + one run command reproduces the pipeline (modulo model binaries). |
| **NFR-REL-1** | 1,000 consecutive `verify` calls complete unattended without leaks or hangs. |
| **NFR-REL-2** | A hung Lean process is killed (process tree) within its wall guard. |
| **NFR-PERF-1** | Parallel Lean workers derived from free RAM (max 6; each Mathlib-loaded worker ≈1.8–2.7 GB, capped at 4 GB). Other jobs on the machine are respected: model experiments run only when the GPU is otherwise idle. |
| **NFR-PERF-2** | Model calls: one model resident in VRAM at a time; driver groups runs by model to avoid reload thrash. |
| **NFR-QA-1** | Unit-test coverage for parsing, splicing, integrity, extraction, mutation, hints, statistics; integration tests against real Lean for integrity cases. |
| **NFR-QA-2** | Static checks (ruff) pass; type hints on public APIs. |
| **NFR-FEAS-1** | Phase-0 feasibility evidence (T coverage on references; model compile-rate probe; determinism probe; timing) is collected *before* freezing and recorded in [`docs/feasibility.md`](feasibility.md). |
| **NFR-FEAS-2** | If model compile rate on a 10-task probe is ~0 for a primary model, the primary model set is revised (documented deviation) before the pilot. |
| **NFR-SEC-1** | Model output is never executed outside Lean; Lean runs with no network, in a temp work dir; `#eval`/IO in candidates is banned (IR-2). |

---

## 9. Acceptance criteria and traceability

| Requirement group | Acceptance check |
|---|---|
| FR-TASK | `prl tasks check` prints a table: compile/test/proof status of all 189 references; eligible set written. |
| FR-MUT, FR-NAT | Every kept bug instance has a failing witness re-verified by `verify` (tests fail) and its family reference passes. |
| FR-TEST | Reference passes 100% of visible and hidden tests; each mutant fails ≥1. |
| FR-VER, FR-PORT | Determinism test (same input twice → same output); T coverage table produced; portfolio hash in FREEZE. |
| FR-HINT | Unit tests per pointer; hint length ≤ cap. |
| IR-* | Integrity test suite (IR-8) passes with **zero** false successes on real Lean. |
| FR-GEN | Extraction unit tests; determinism probe recorded. |
| FR-COND | Prompt length table across conditions; leakage test (IR-9). |
| FR-BUD | Run records show which cap ended each run; no run exceeds caps. |
| FR-DRV | Kill-and-resume test produces identical final logs. |
| SR-PRE | Driver refuses a modified prereg file (test). |
| SR-STAT | Statistics unit tests on synthetic data with known answers; power simulation finds a small n for a large effect and none without an effect. |
| FR-ANA-7 | Cross-evaluation unit test: buckets, de-duplication, resumability, only compiling-but-unproved B attempts. |
| FR-ANA-8 | Tactic-extraction unit tests; `B_noauto` derived only inside comparisons (never in costs or audits). |
| FR-COND-10 | Bhammer prompt differs from B's only by the tactic list; feedback identical to B. |
| NFR-REP-1 | `prl analyze` regenerates [`results/`](../results/) byte-identically from logs. |

---

## 10. Go / no-go gate (end of pilot)

Continue to the confirmatory run only if all hold on the 20 pilot families:

1. T proves ≥20% of eligible pilot references (screening; full-pool coverage is reported regardless).
2. Primary models reach a compile rate > 10% in C on pilot instances (floor-effect check).
3. C produces ≥1 hand-verified repair that neither B nor B+P produces on the same instance (decisive).
4. Integrity suite: zero false successes.
5. Estimated full-study cost fits available compute (≤ ~72 h wall time). The same estimate decides whether the exploratory Bhammer arm is run (logged in [`prereg/deviations.md`](../prereg/deviations.md)).
6. The power note (SR-STAT-4) is written. It is not a pass/fail criterion: an underpowered estimate is reported as a limitation before the freeze.

If (3) fails: switch to **Backup 2 — proof-friendliness benchmark** (T over reference, mutated and model-rewritten variants, plus study S as the headline), which reuses the same harness.

---

## 11. Out of scope

- Fine-tuning or reinforcement learning of any model.
- Repository-scale Lean projects.
- Changing or strengthening VERINA specifications (we only exclude defective ones).
- A progressive-hint condition (study S covers re-shaping instead).
- Paid APIs or frontier models as repairers.

---

## 12. Risks (requirements view)

| Risk | Requirement that mitigates it |
|---|---|
| Portfolio proves too little | NFR-FEAS-1, gate 1, backup study |
| Floor effect in Lean fluency | NFR-FEAS-2, 4B model, gate 2 |
| C wins only by reverting the mutation | SR-MECH-*, study S |
| Strawman baseline | B+P, Goedel-Code-Prover-8B reference, Bhammer (exploratory), B-to-C cross-evaluation |
| "B just called `grind`" objection | FR-ANA-8 (`B_noauto`) |
| Mutant unrealism | FR-NAT-1/2 (natural bugs primary), separate reporting |
| Machine shared with other jobs | FR-RES-1 (memory cap, RAM-derived workers); model runs only on an idle GPU |
| Energy claims unsupported | FR-EN-1..3 (measured GPU, labelled CPU estimate) |
| Spec gaming | IR-*, hidden tests, audit |
| Budget unfairness | FR-BUD-1..4 |
| Hand-tuning | SR-PRE-*, pilot-only tuning |
| Low power | all eligible families, 3 seeds, exact tests, pilot-based power simulation before the freeze (SR-STAT-4) |
| Non-deterministic inference | FR-GEN-5, seeds logged, 3 seeds |
