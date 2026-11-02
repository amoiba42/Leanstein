# Tasks and models — harvest, extraction, feedback router

[← index](../ARCHITECTURE.md) · **Member B**

## 1. Phase 1: task preparation from real errors

Goal: buggy programs are the models' own genuine mistakes, not synthetic mutants.

```
for task in verina_tasks:
    for r in range(resample_cap_R):                  # R = 5
        seed = harvest_seed(task, model, r)          # new seed per resample
        text = generate_zero_shot(task, model, seed) # description + spec statement + signature
        code = extract(text)                         # no examples, no hints, no tests, no reference
        if not compiles(code):               continue
        if not spec_theorem_elaborates(code): continue   # signature must match the locked spec
        if passes_all_hidden_tests(code):    continue    # model was right, resample for a wrong one
        write_manifest(task, code, bug_source_model=model, zero_shot_seed=seed, resample_idx=r)
        break
    else:
        log_drop(task, reason="resample_cap_reached")    # never loops forever
```

- **"Buggy"** means it compiles, the spec theorem statement elaborates against it, and it fails at least one hidden test. Whether the theorem is *provable* is not checked here; condition T confirms the pipeline fails on every buggy program.
- The `spec_theorem_elaborates` gate matters: a zero-shot output can change the signature or argument order, and then C's proof obligation never elaborates. Log those rejects separately.
- Non-compiling outputs are not tasks. They consume the resample budget and are logged.
- Every drop is logged with its reason. Report the yield table (tried, kept, dropped) by difficulty. Real errors skew toward tasks the model finds hard — selection bias goes into Threats.
- `bug_type` is assigned afterwards by diffing against the reference (rule-based: wrong bound, wrong operator, missing case, wrong algorithm), hand-checked on pilot tasks.
- **Fallback only:** below 60 harvested tasks, `mutate.py` (operator swap, comparison flip, off-by-one, dropped branch, wrong initial value, swapped arguments) fills the gap. Mutant and real-error results are reported separately, never pooled.
- Variants of one task stay in the same split. 30% is held out and not inspected until the final run.
- `harvest_seed` must not collide with the repair seed space (`seed * 1000 + attempt_idx`), or a repair attempt reproduces the buggy code exactly. Assert disjointness in `common/config.py`.

## 2. Phase 3: candidate extraction

Where model output becomes a candidate.

- `models/extract.py` pulls the code (and, for A and B, the proof) from fenced blocks. Empty, truncated or unparseable output is `format_fail` — a model failure, consumes N, logged.
- **Region rule.** The model may only write the designated implementation region. Contract, theorem statement, proof harness and hidden tests sit outside it. In C and C-plain the candidate is spliced into the region of the locked file; nothing else can change.
- The extractor never drops a failure silently. Output text, extracted code and extraction status are all logged.

## 3. Feedback router

Lives in `generate()` (`models/router.py`). Converts the previous `verify()` result into the next prompt's feedback, using Member A's `failure_type` and hint object. One rule per failure type.

| failure_type | A | B | C | C-plain |
|---|---|---|---|---|
| integrity_fail | none | category message: "forbidden keyword", "edit outside region", "empty or constant body", "spec copied" (no rule internals) | same as B | "failed, retry" |
| format_fail | none | "Return only the implementation in one `lean` code block." | same as B | "failed, retry" |
| compile_fail | none | first Lean error with line, ≤ 400 tokens | same compile error, ≤ 400 tokens | "failed, retry" |
| proof_failed | none | Lean error / unsolved goal from the model's own proof, ≤ 400 tokens | **structural hint** from the goal analyzer: unclosed goal, route taken, tactic trace, rule-based pointer (non-structural recursion, Int and Nat mixed, opaque helper, `partial def`), ≤ 400 tokens | "failed, retry" |
| test_failed | none | generic warning only: "Hidden tests failed. The behaviour does not match the requirement. Re-read the requirement." | same as B | "failed, retry" |
| resource_exhausted | none | "Your implementation ran out of time or memory. Use a cheaper approach." | same as B | "failed, retry" |
| infra_crash / worker_crash | **no feedback, no N consumed, rerun** (all conditions) | | | |

Rules:

1. **Hidden tests stay private.** No test inputs, expected outputs, counts, or which test failed. A unit test checks that no feedback string shares a token 5-gram with any test file. Filter concrete numeric literals out of B's `proof_failed` errors, since `omega` and `decide` can print counterexample values.
2. **C-plain gets the same generic message for every failure type**, so the hint's effect (RQ4) is isolated.
3. **B and C have equal feedback caps (400 tokens).**
4. The previous candidate plus its feedback is the only history (`history_window = 1`).
5. Only `infra_crash` and `worker_crash` trigger a rerun; wrong model solutions are never rerun.
6. **Log truncation.** B's history carries a proof and C's does not, so B overflows the 3,072-token prompt more often. Record `prompt_truncated` and which section was cut; report the rate per condition. The prompt-length table proves the *budget* is equal, not that delivered content is.

Design note: the original flow diagram put B in the generic "failed, retry" branch. The plan defines B as feedback-guided proof-writing with Lean errors, so B keeps them and stays a fair control. The diagram is wrong and must be fixed.
