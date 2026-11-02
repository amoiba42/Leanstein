# High-Level Design

**Project:** Prove Less, Repair Better (PRL)
**Status:** v2.0 · 2026-11-02 · derived from `docs/requirements.md` v2.0 and `docs/final_architecture.md` (the diagram there is the authoritative overview)
**Scope:** architecture, components, data flow, condition protocols, trust boundaries, deployment and the experimental pipeline. Byte-level formats and algorithms are in `docs/low_level_design.md`.

---

## 1. Design goals (in priority order)

1. **Trustworthy judging.** A reported success must be a real success: locked contract, Lean-kernel-checked proof, clean axioms, passing withheld tests. Correctness of the judge outranks speed. (IR-*, FR-VER)
2. **Fair comparison.** Conditions differ only in what the design says they differ in: who writes the proof and what feedback is shown. Same instances, models, decoding, budgets and preflight. (FR-COND-8, FR-BUD)
3. **Mechanism visibility.** Every artefact needed to tell *shaping* from *reverting* is logged by construction (reference automation status, patch distances, code features). (SR-MECH)
4. **Reproducibility.** Pinned toolchain, frozen pre-registration with hashes, content-addressed caching, deterministic ordering, one-command regeneration. (SR-PRE, NFR-REP)
5. **Laptop feasibility.** One 8 GB GPU, 24 GB RAM; Lean verification is the bottleneck and is parallelised. (NFR-ENV, NFR-PERF)

---

## 2. System context

```
                         ┌──────────────────────────────────────┐
                         │          VERINA (pinned commit)       │
                         │ 189 tasks: description, Lean template │
                         │ with regions, reference code, tests   │
                         └───────────────┬──────────────────────┘
                                         │ read-only
┌────────────────────┐ OpenAI-compatible ▼
│ LM Studio (CUDA)   │◄──────────────┐  ┌──────────────────────────────────────────────┐
│ repairers: Qwen3.5 │               └──┤                PRL harness (Python)           │
│ 2B/4B, Gemma-4-E4B │                  │ tasks · mutate · natural · testgen · models · │
│ specialist: Goedel │                  │ lean · conditions · driver · energy · analysis│
│ bug gens: 0.8B, 9B │                  └───────┬───────────────────────────┬──────────┘
└────────────────────┘                          │ JSON lines over stdin/out  │ NVML / psutil
                                                ▼                           ▼
                        ┌──────────────────────────────────────────┐  ┌──────────────┐
                        │ Lean verification server pool             │  │ GPU energy    │
                        │ lean_env/PrlRepl.lean: Mathlib loaded once │  │ counter, Lean │
                        │ per worker · Job-Object memory cap 4 GB   │  │ CPU seconds   │
                        └──────────────────────────────────────────┘  └──────────────┘
```

The harness is the only component that talks to the model server and to Lean. The model never touches
the filesystem.

---

## 3. Architecture

### 3.1 Layered view

| Layer | Packages | Responsibility | Owner |
|---|---|---|---|
| **Foundation** | `prl.config`, `prl.util` | Paths, frozen config loading, hashing, JSONL I/O, process control | C |
| **Benchmark** | `prl.tasks` | Parse VERINA, region model, task manifest, splits, eligibility | B |
| **Judge** | `prl.lean` | Lean runner, file renderer, portfolio, test harness, integrity, axioms, hints, cache | A |
| **Bug sources** | `prl.mutate`, `prl.natural` | Mutation operators, natural-bug collection | B |
| **Tests** | `prl.testgen` | Visible-test rendering, hidden differential test generation | A/B |
| **Agent** | `prl.models` | LM Studio client, prompts, extraction, determinism probe | B |
| **Protocols** | `prl.conditions` | T, A, B, B+P, C, C-plain, S, S-plain loops with budget accounting | B/C |
| **Orchestration** | `prl.driver` | Experiment plan expansion, scheduling, resume, records | C |
| **Science** | `prl.analysis` | Outcome labels, statistics, mechanism, code shapes, figures, audit | C |
| **Interface** | `prl.cli` | `prl <command>` entry points | C |

Dependencies point downward only. `prl.lean` has no dependency on `prl.models`; `prl.models` has none on `prl.lean`. They meet only in `prl.conditions` — this is the plan's "two small interfaces" rule, enforced by package structure and by an import-lint unit test.

### 3.2 The two interfaces (frozen)

```python
verify(task: TaskInstance, cand: Candidate, mode: VerifyMode) -> VerifyResult     # Member A
generate(view: TaskView, condition: str, history: list[Turn], seed: int,
         model: ModelSpec) -> Generation                                       # Member B
```

`TaskView` is a deliberately *narrow* projection of a `TaskInstance` (description, signature, pre/postcondition text, faulty code, theorem statement). It is the only object a prompt can be built from, which makes leakage (IR-9) structurally impossible to introduce by accident.

---

## 4. Core domain model

```
TaskFamily (VERINA task)
 ├── regions: imports, solution_aux, precond_aux, precond, code_aux, code,
 │            postcond_aux, postcond, proof_aux, proof
 ├── signature: name, params[(name, type)], return_type
 ├── visible_tests: VERINA test.json
 ├── hidden_tests: generated, precondition-proved, reference-evaluated
 ├── reference status: compiles, tests pass, ref proof ok, T(ref) ∈ {closed by entry k, open}
 └── instances: TaskInstance*
TaskInstance
 ├── kind: mutant | natural | shaping (S: start = reference)
 ├── start_code: (code_aux, code)  ← what the model sees as "faulty"/"to reshape"
 ├── failing_witness (mutant/natural)
 └── provenance, hashes, split
Candidate: (code_aux, code, proof_aux?, proof?) + raw text + extraction status
VerifyResult: compile, tests (visible/hidden), proof (source, closing entry), axioms,
              integrity (ok, reasons), hint, lean errors, timings, cache key
Run: (instance, condition, model, seed) → attempts[≤ N_gen] → outcome label
```

---

## 5. The judge (`prl.lean`)

### 5.1 Verification server pool
`lean_env/PrlRepl.lean` (our own ~60-line Lean program, built with `lake build prlrepl`) imports Mathlib once
and then elaborates one file per request against a fresh copy of the imported environment (environments are
immutable values, so every request starts from the same state). A pool of such workers (count derived from
free RAM, max 6) serves all verifications: ~0.6 s per check instead of 25–40 s with a plain `lean` process.
Each worker runs inside a Windows Job Object with a 4 GB per-process memory cap. The plain `lean` CLI remains
available as a fallback backend (`PRL_LEAN_BACKEND=cli`); verdict parity between the two is tested.

### 5.2 One rendered file per request; staged verification
A request is one self-contained `.lean` file: the locked VERINA template with the candidate's `code_aux` / `code`
(and, in proof modes, `proof_aux` / `proof`) spliced into their regions, followed by a generated harness section.
Line ranges of every part are recorded so messages are attributed exactly.

* **Stage 1** (one request): compile, every visible and hidden test as a `#guard`, and in A/B/BP the model's
  proof followed by `#print axioms`.
* **Stage 2** (only if the mode uses the portfolio and stage 1 compiled and passed all tests): portfolio
  entries one request each, Tier L then Tier H, in frozen order, stopping at the first closing entry
  (condition T on references runs the full vector for RQ4).

### 5.3 Determinism, timeouts and failure taxonomy
Every proof decision uses **heartbeats** (deterministic). Wall-clock guards only protect against hangs.
A timeout or worker death is confirmed once in a fresh worker: if it repeats, the candidate's code is at fault
(`failure_kind` = timeout / resource) and the attempt counts as failed; otherwise the confirmed result is used.
Verifier infrastructure failures (spawn errors, crashes unrelated to the candidate) are retried without
charging the model's budget; persistent ones abandon the run for later re-execution.

### 5.4 Integrity pipeline
```
candidate ─► static pre-filter: REJECT escapes (sorry, axiom, native_decide, implemented_by, macros,
             set_option, attribute, # commands, ...), locked-name redefinitions, empty body;
             FLAG spec-copying, constant body, hard-coded tests, choice  (flags ⇒ mandatory audit)
          ─► render with locked regions ─► locked-region hash check
          ─► Lean (stage 1, stage 2) ─► #print axioms ⊆ {propext, Classical.choice, Quot.sound}
          ─► success = compile ∧ visible ∧ hidden tests ∧ proof by the allowed source ∧ integrity
```
Static rejection happens before Lean runs, so a malicious candidate never executes.

### 5.5 Portfolio (two tiers)
A frozen ordered list of tactic scripts parameterised only by mechanically derived names. Tier L (50k
heartbeats): `decide`, `simp`, `simp_all`, `omega` combinations, `split` combinations. Tier H (200k): `grind`,
`aesop`, `fun_induction` and structural `induction` templates. Identical for T, BP, C, C-plain, S and S-plain.
Stored in `prereg/portfolio.yaml`, hashed in `prereg/FREEZE.json`.

### 5.6 Hint extractor and feedback router
The hint extractor is deterministic and rule-based: the best portfolio entry's first unsolved goal plus
structural pointers from a fixed catalogue (`prereg/hints.yaml`: partial def, well-founded recursion,
imperative loop, Nat/Int mixing, opaque helper, unchecked indexing, fold accumulator, spec/code shape mismatch).
The **feedback router** (`prl.conditions.feedback`) maps failure type × condition to the next-turn message
(see §8). Hidden-test failures are reported only as a count.

### 5.7 Cache
Content-addressed by SHA-256 of (rendered stage-1 file, portfolio scripts and tiers, mode, test split).
Identical candidates across conditions and seeds are verified once.

---

## 6. Benchmark construction

```
VERINA ─► parse regions ─► reference check (compile, tests, ref proof, axioms)
        ─► eligibility (exclude broken/defective) ─► T on reference (coverage)
        ─► hidden test generation (random inputs → precond proved → ref evaluated → round-trip check)
        ─► bug sources:
              natural (PRIMARY): zero-shot samples from Qwen3.5-0.8B and Qwen3.5-9B (never repairers)
                        → compile ∧ fail ≥1 test → ≤1 per family per generator (≤4 samples, resample cap)
              mutants (secondary, controlled): operators on code/code_aux → compile ∧ fail ≥1 test → ≤2 per family
              shaping:  correct reference with T(ref)=open → instance for study S
        ─► T on each buggy instance (record; if portfolio proves a buggy program ⇒ weak spec flag)
        ─► splits (pilot 20 / main / heldout ≈30% of main), family-level, seeded
        ─► manifests + hashes
```

A buggy program that the portfolio *proves* against the spec is direct evidence the spec is too weak for that bug; such instances are kept but flagged and analysed separately (`weak_spec`), since only hidden tests can reject wrong code there.

---

## 7. Agent layer (`prl.models`)

- **Server:** LM Studio with the **CUDA** llama.cpp engine, OpenAI-compatible `POST /v1/chat/completions`,
  models loaded via `lms load` with fixed context length and full GPU offload. One model resident at a time;
  the driver runs (model, condition) blocks sequentially.
- **Models:** repairers Qwen3.5-2B, Qwen3.5-4B (primary), Gemma-4-E4B-it (secondary); proof specialist
  Goedel-Code-Prover-8B (A/B only); natural-bug generators Qwen3.5-0.8B and Qwen3.5-9B (never repairers).
- **Decoding:** `temperature=0.7`, `top_p=0.95`, `max_tokens=1536`, seed from the seed list,
  `reasoning_effort: "none"` (hidden reasoning would otherwise consume the token budget invisibly).
- **Prompts:** one template per condition under `prereg/prompts/`, built only from a narrow `TaskView`
  (description, locked spec incl. `solution_aux` helpers, locked header, theorem statement, start code).
- **Output contract:** the full function definition (helpers allowed before it) in a ```lean block; proof
  conditions add a second block with the theorem. The harness always re-emits the locked header; echoed copies
  of locked definitions are dropped at extraction.

---

## 8. Condition protocols

All runs share the same start code, budgets, decoding and turn-0 information (task + visible failing witness).

| Cond. | Loop | Candidate per generation | Verify mode | Feedback (router) |
|---|---|---|---|---|
| T | none | reference / start code | portfolio (full vector) | — |
| A | N independent samples | code + proof | model_proof | none |
| B | N sequential turns | code + proof | model_proof | Lean errors / visible witness / proof errors |
| BP | N sequential turns | code + proof | portfolio_then_model | as B |
| C | rounds of k=2, ≤N total | code | portfolio | as B's core + structural hint + best unsolved goal |
| C-plain | as C | code | portfolio | fixed "rejected, try again" + format reminder |
| S | as C, start = correct reference T cannot prove | code | portfolio | as C |
| S-plain | as S | code | portfolio | as C-plain |

**Stop rule:** first success, or the first budget cap reached (8 generations, 48k tokens, 240 s inference).
**History:** last 2 turns verbatim for every iterative condition.

---

## 9. Orchestration (`prl.driver`)

```
plan ─► expand (split × condition × model × seed × instance) ─► sort deterministically
     ─► for each (model, condition) block, sequentially:
           lms load model · EnergyMeter.start (NVML counter, Lean CPU seconds)
           thread pool of run-workers: each run = loop{generate → extract → pre-filter → verify → route feedback}
           EnergyMeter.finish → energy.jsonl
     ─► attempts.jsonl / runs.jsonl / energy.jsonl (atomic line writes, fsync)
```
- **Resume:** a run is complete iff its run record exists; incomplete runs restart from scratch.
- **Freeze guard:** `main`/`heldout` refuse to run if `prereg/` differs from `FREEZE.json`.
- **Failure policy:** infrastructure failures are retried and never charged; model behaviour (bad output,
  extraction failure, non-terminating code) is recorded as an attempt and never retried.

---

## 10. Analysis pipeline (`prl.analysis`)

```
runs.jsonl + attempts.jsonl + energy.jsonl + manifests
   ─► outcome labels per run (5 labels)
   ─► family-level scores (mean over seeds)
   ─► RQ1: sign-flip permutation (one-sided), Holm; McNemar exact; cluster bootstrap CI; Cohen's h; discordant counts
   ─► RQ2: mechanism classification (revert / shaping / other), C rate by ref_auto, S vs S-plain
   ─► RQ3: C vs C-plain (same tests as RQ1, exploratory)
   ─► RQ4: code-feature extraction → feature-by-provability tables, L2 logistic regression with family-clustered bootstrap CIs
   ─► primary bug pool chosen by the pre-registered rule (natural if ≥60 confirmatory families, else natural ∪ mutant)
   ─► RQ5: cost tables, energy per verified repair (GPU measured, CPU estimated, per block), model/family gaps,
           sensitivity to N (post-hoc truncation of logs at N∈{2,4,8})
   ─► overlap (Venn) per model; per-stratum tables; closing-tactic distribution
   ─► audit sample CSV (10% of successes, stratified, plus every flagged success) ─► audit results merged
   ─► results/*.csv, results/*.md, results/figures/*.png
```
Everything is a pure function of the log files and manifests, so `prl analyze` is idempotent and regenerates identical outputs.

---

## 11. Trust boundaries and threat model

| Boundary | Threat | Control |
|---|---|---|
| Model → harness | Proof escape (`sorry`, `axiom`, `native_decide`, `implemented_by`, macros, `set_option`) | Static scan (IR-2/IR-4) before Lean; axiom allow-list after |
| Model → harness | Edits outside implementation region / signature change | Region splicing re-emits locked text from reference; signature lock; hash check |
| Model → harness | Spec gaming (weak postcondition) | Hidden tests; `verified_but_wrong` label; weak-spec flag from T on buggy |
| Model → harness | Degenerate code (spec copying, choice, hard-coding) | IR-7 flags, audit |
| Harness → model | Leakage of reference/tests | `TaskView` projection; prompt allow-list; leakage unit test |
| Harness → Lean | Hangs, memory blow-up | Heartbeats, wall guard with process-tree kill, worker cap |
| Researchers → results | Hand-tuning, post-hoc subsets | Pilot-only tuning, FREEZE hashes, held-out run once |

---

## 12. Deployment and environment

| Item | Choice |
|---|---|
| OS / HW | Windows 11, RTX 5060 Laptop 8 GB, 24 GB RAM, i7-14650HX (24 threads); shared with other projects, so model runs happen only on an idle GPU |
| Lean | elan; `leanprover/lean4:v4.24.0`; Mathlib `v4.24.0` (commit `f897ebcf`), prebuilt cache; manifest committed; verification server `PrlRepl` |
| Benchmark | VERINA `66b3ce50` under `third_party/verina` (read-only, not committed) |
| Models | LM Studio 0.4.x, CUDA 12 llama.cpp engine 2.67.0, GGUF 4-bit: Qwen3.5-0.8B/2B/4B/9B, Gemma-4-E4B-it, Goedel-Code-Prover-8B |
| Python | 3.12 via `uv`, lockfile; numpy, scipy, pandas, statsmodels, matplotlib, pyyaml, httpx, nvidia-ml-py, psutil, pytest, ruff |
| Parallelism | Lean workers from free RAM (max 6, 4 GB cap each); concurrent model requests per block |

---

## 13. Experimental pipeline and phases

| Phase | Purpose | Exit |
|---|---|---|
| **0 Feasibility** | T on all references; compile-rate probe of each model on 10 tasks; determinism probe; throughput (idle GPU only) | `docs/feasibility.md`; model set confirmed |
| **1 Build** | All components + unit/integration tests | Test suite green; integrity suite zero false successes |
| **2 Dataset** | Eligibility, hidden tests, natural bugs (0.8B, 9B), mutants, shaping instances, splits | Manifests + provenance tables |
| **3 Pilot** | All conditions on 20 pilot families, 1 seed, primary models; portfolio/prompt tuning *only here* | Go/no-go (requirements §11) |
| **4 Freeze** | Write `prereg/FREEZE.json` | Hash file committed |
| **5 Main** | Confirmatory run on `main`: primary models × {A, B, BP, C, C-plain} × 3 seeds; S/S-plain on shaping instances; Gemma-4-E4B × {B, BP, C} × 1 seed; Goedel-Code-Prover-8B × {A, B} × 1 seed | Logs complete |
| **6 Held-out** | Run `heldout` once | Logs complete |
| **7 Analysis** | `prl analyze`; audit; catalogue | `results/` + report |

---

## 14. Key design decisions (ADR summary)

| # | Decision | Alternatives | Why |
|---|---|---|---|
| D1 | One rendered file per request; staged (tests, then portfolio entries one by one) | everything in one file | early stop at the first closing entry; the import cost is gone with the server (D11) |
| D2 | Heartbeats as the decision limit | Wall clock | Determinism (FR-VER-4) |
| D3 | Model returns whole function definition; harness re-emits locked signature | Ask for body only | Small models follow "write the function" far better than "fill a region"; locked signature keeps integrity |
| D4 | VERINA tests visible, generated tests hidden | Hide VERINA tests | VERINA tests are public; only fresh tests are truly withheld |
| D5 | Hidden-test inputs must have a *Lean-proved* precondition | Python-side filter | Precondition semantics live in Lean; avoids invalid tests |
| D6 | Add B+P and S | Only A/B/C | Pre-empts "strawman B" and "C just reverts" critiques (verdicts) |
| D7 | Family-level mean-over-seeds + sign-flip permutation | Pooled McNemar | Respects the statistical unit; uses all seeds; exact |
| D8 | LM Studio instead of raw llama.cpp | vLLM (no Windows), Ollama | Installed, OpenAI-compatible, GPU-offloaded, seedable |
| D9 | Lean 4.24.0 | latest Lean | VERINA ships a 4.24 migration; grind and fun_induction available |
| D10 | Current Qwen3.5 / Gemma-4 models | Qwen2.5-Coder | User requirement for latest small models; 2B/4B are the direct successors to the planned 1.5B/3B sizes |
| D11 | Own Lean verification server (Mathlib once per worker) | `lean` per file; community REPL | ~40× faster; no third-party code; CLI parity tested |
| D12 | Two heartbeat tiers, early stop, same for all portfolio users | goal-classifier router (Gracy G7) | deterministic; no unregistered degree of freedom; no confound |
| D13 | Natural bugs primary, mutants secondary | mutants only | realism; weakens the "C reverts mutants" objection (Gracy G1, all verdicts) |
| D14 | Energy per (model, condition) block | per attempt | concurrent requests make per-attempt GPU energy ill-defined |
| D15 | Job Object 4 GB cap per Lean worker | 2 GB `setrlimit` (Gracy G3) | Linux-only API; Mathlib alone needs ~2.5 GB |
