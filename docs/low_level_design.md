# Low-Level Design

**Project:** Prove Less, Repair Better (PRL)
**Status:** v2.0 · 2026-11-02 · derived from `docs/high_level_design.md` v2.0 and `docs/final_architecture.md`; every module named here exists under `prl/`
**Scope:** module-by-module specification: data schemas, algorithms, file formats, Lean rendering, integrity rules, prompts, statistics, error handling and tests. Code under `prl/` must conform to this document; deviations are recorded in `prereg/deviations.md`.

---

## 1. Repository layout

```
AutoSEGroupProject/  (GitHub: Leanstein)
├── README.md, memory.md        entry point; living project memory
├── context/                    original inputs (read-only): InitialProposal/ (2 PDFs), InitialVerdicts/, GracyAdditions/
├── docs/                       final_proposal.md (living), final_architecture.md, requirements, HLD, LLD,
│                               implementation_plan, feasibility
├── prereg/                     frozen study inputs (hashed by FREEZE.json)
│   ├── study.yaml              conditions, budgets, decoding, models, seeds, splits, bug pool, energy, analysis
│   ├── portfolio.yaml          two-tier tactic templates (heartbeats per tier)
│   ├── hints.yaml              structural pointer catalogue + caps
│   ├── prompts/*.txt           system, task, per-condition, feedback templates
│   └── deviations.md           logged changes (pre-freeze and post-freeze)
├── prl/                        python package (sections 2–12)
│   ├── config.py, prereg.py, energy.py, cli.py
│   ├── tasks/      regions, verina, eligibility, instances, splits
│   ├── lean/       runner (server pool, Job Object), builder, portfolio, integrity, hints, leantext, verify
│   ├── testgen/    literals, hidden
│   ├── mutate/     operators, select
│   ├── natural/    collect (natural bugs, shaping instances)
│   ├── models/     lmstudio, prompts, extract, registry
│   ├── conditions/ protocols, feedback (router), probes
│   ├── driver/     runner (plan, blocks, resume, records)
│   └── analysis/   stats, mechanism, features, report
├── lean_env/                   pinned Lean project + PrlRepl.lean (verification server)
├── tests/                      unit + `lean`-marked integration tests
├── scripts/pdownload.py        parallel downloader (throttled networks)
└── (generated, git-ignored) data/, cache/, runs/, results/, third_party/verina/
```

---

## 2. Configuration (`prl/config.py`)

- `ROOT` = repo root; `PATHS` = all directories above (generated ones created lazily).
- `load_yaml`, `read_json`, `write_json` (atomic), `sha256_file`, `sha256_text`.
- `lean_env()` → `LeanEnv(lean_exe, lean_path, toolchain_id)`, cached in `cache/lean_env.json` keyed by the
  `lake-manifest.json` hash.
- `study_config()` → parsed `prereg/study.yaml`; unknown keys raise.

`prereg/study.yaml` (v2) keys: `study_id`, `lean{wall_guard_s, workers (0 = from free RAM), mem_limit_gb,
test_heartbeats, batch_wall_s}`, `budget{n_gen, max_total_tokens, max_completion_tokens, max_infer_s}`,
`decoding{temperature, top_p, reasoning_effort}`, `c_round_k`, `history_turns`, `seeds`,
`models{primary, secondary, specialist, natural_generators}`, `conditions`, `specialist_conditions`,
`shaping_conditions`, `splits`, `mutants_per_family`, `hidden_tests`, `natural{samples, per_family_per_generator}`,
`bugs{primary, min_natural_families, fallback}`, `energy{cpu_watts_per_thread, grid_kg_co2_per_kwh}`,
`analysis{bootstrap, permutations, alpha, seed, revert_distance, audit_frac}`. The file itself is the reference.

---

## 3. Data schemas

### 3.1 `Family` (`data/families/<id>.json`)
```json
{
 "family_id": "verina_basic_1", "tier": "basic",
 "signature": {"name": "hasOppositeSign", "params": [["a","Int"],["b","Int"]], "ret": "Bool"},
 "template": "<full task.lean text>",
 "regions": {"import": "...", "solution_aux": "...", "precond_aux": "...", "precond": "...",
             "code_aux": "...", "code": "...", "postcond_aux": "...", "postcond": "...",
             "proof_aux": "...", "proof": "..."},
 "theorem_stmt": "theorem hasOppositeSign_spec_satisfied (a: Int) (b: Int) (h_precond : ...) :\n    ...",
 "description": "...", "visible_tests": [{"input": {...}, "expected": ...}],
 "locked_hash": "<sha256 of template with replaceable regions blanked>",
 "ref": {"compiles": true, "visible_pass": true, "hidden_pass": true,
         "proof": "human_ok|human_broken|absent", "T": {"closed": true, "entry": "simp_all_unfold", "vector": {...}}},
 "eligible": true, "exclusion_reason": null
}
```

### 3.2 `HiddenTests` (`data/hidden/<id>.json`)
`{"family_id", "seed", "tests": [{"input_lean": {"a": "(-3)", ...}, "expected_lean": "true", "pre_proof": "decide"}], "sha256"}`
Values are stored as **Lean source literals** (already rendered), so they are spliced verbatim.

### 3.3 `TaskInstance` (`data/instances/<iid>.json`)
```json
{
 "instance_id": "verina_basic_1__mut__relflip__0", "family_id": "verina_basic_1",
 "kind": "mutant|natural|shaping", "split": "pilot|main|heldout",
 "start": {"code_aux": "", "code": "a * b ≤ 0"},
 "provenance": {"operator": "relflip", "line": 1, "col": 6, "before": "<", "after": "≤", "seed": 5},
 "witness": {"source": "visible", "index": 4, "input_lean": {...}, "expected": "false", "actual": "true"},
 "start_T": {"closed": false, "best_entry": "...", "weak_spec": false},
 "hashes": {"locked": "...", "visible_tests": "...", "hidden_tests": "..."}
}
```

### 3.4 Attempt record (`runs/<study>/attempts.jsonl`, one line per generation)
```
run_id, instance_id, family_id, condition, model, seed, attempt_idx, round_idx,
prompt_sha256, prompt_chars, tokens_in, tokens_out, infer_s, finish_reason,
extract_ok, extract_error, extract_notes[], code_aux, code, proof_aux, proof, failure_kind, feedback_kind,
static_ok, static_reasons[], compile_ok, visible_pass, hidden_pass, n_visible_fail, n_hidden_fail,
proof_ok, proof_source(portfolio|model|none), closing_entry, entry_vector{entry: closed},
axioms_ok, axioms[], integrity_ok, integrity_reasons[], hint_kinds[], feedback_chars,
lean_s, lean_timeout, cache_hit, verify_key, success, ts
```
(`verify` is nested as one object; raw prompts and outputs are stored under `runs/<study>/raw/`.)

### 3.4b Energy record (`runs/<study>/energy.jsonl`, one line per (model, condition) block)
```
study_id, model, condition, t_start, t_end, gpu_j (measured), lean_cpu_s, cpu_j_est, co2_g_est, run_ids[]
```

### 3.5 Run record (`runs/<study>/runs.jsonl`, one line per run)
```
run_id, instance_id, family_id, kind, split, condition, model, seed,
n_attempts, total_tokens, infer_s_total, lean_s_total, stop_reason(success|n_gen|tokens|infer_time),
success, outcome(verified_repair|verified_but_wrong|correct_unverified|integrity_violation|unresolved),
success_attempt_idx, final_code_aux, final_code, proof_source, closing_entry,
dist_to_ref, dist_to_start, equiv_to_ref, ref_auto, features{...}, flags[], prereg_sha, ts
```
`run_id = sha256(study_id|instance_id|condition|model|seed)[:16]`.

---

## 4. `prl.tasks` — VERINA parsing and the region model

### 4.1 Region parsing (`regions.py`)
- Marker regex (multiline): `^[ \t]*-- !benchmark @start (\w+)[^\n]*\n` … `^[ \t]*-- !benchmark @end \1\b`.
- `parse_regions(text) -> dict[name, Region(start_offset, end_offset, content)]`; content is the exact text between the end of the start line and the beginning of the end line.
- `REPLACEABLE_CODE = ("code_aux", "code")`, `REPLACEABLE_PROOF = ("proof_aux", "proof")`.
- `render(template, replacements: dict[name, str]) -> str` replaces region contents only, from the last region backwards (offsets stay valid). Replacement text is normalised: trailing newline ensured; for `code` and `proof` every line is re-indented to 2 spaces after dedent (`textwrap.dedent`).
- `locked_hash(template)`: sha256 of the template with all four replaceable region contents set to `""`. **Invariant (unit-tested):** `locked_hash(render(t, any)) == locked_hash(t)` for any replacement not containing markers; replacement text containing `!benchmark` is rejected statically.

### 4.2 Theorem statement extraction
`theorem_stmt` = text from `theorem <name>_spec_satisfied` up to (excluding) `:= by` that precedes the `proof` region start. Used to restate portfolio attempts: `theorem prl_try_k` + statement-after-name.

### 4.3 Signature
From `task.json`: function name, params, return type. The locked definition line is located by regex `^def <name>\b` in the template and is never produced by the model.

### 4.4 Family loader (`verina.py`)
`load_families(verina_dir) -> list[Family]` reads `task.json`, `task.lean`, `description.txt`, `test.json`. Tier from id prefix. Visible tests: input values rendered to Lean literals via `prl.testgen.literals.render(type, json_value)` (strings already beginning with `#[` are Lean array literals and are passed through).

### 4.5 Eligibility (`eligibility.py`)
Runs `verify_reference(family)` (judge, §5) → fills `ref.*`. `eligible = compiles ∧ visible_pass`. Reasons: `ref_compile_error`, `ref_visible_fail`, `unsupported_type` (hidden test generation impossible is *not* an exclusion: the family keeps visible tests only and is flagged `hidden_unavailable`).

### 4.6 Splits (`splits.py`)
Eligible families sorted by id, shuffled with `random.Random(seed)`. Pilot: first 20 after stratifying basic/advanced proportionally. Remaining = main; `heldout` = first ⌈0.30·|main|⌉ of a second seeded shuffle of main. All instances inherit the family split.

---

## 5. `prl.lean` — the judge

### 5.1 Runner (`runner.py`)
```python
run_lean(source, *, wall_s) -> LeanRun(returncode, messages: list[Msg], stdout, elapsed_s, timeout, infra_error, extra)
```
- **Backend `repl` (default):** a pool of `_ReplWorker`s, each a `prlrepl` process (`lean_env/PrlRepl.lean`)
  that imports Mathlib once and answers one JSON line per request (`{"ok", "messages": [{line, col, severity,
  text}]}`) for the file path it receives. Each worker is placed in a **Windows Job Object** with a
  per-process memory cap (`lean.mem_limit_gb`, default 4 GB). Pool size = `lean.workers` or, if 0,
  `auto_workers()` = ⌊(free RAM − 4 GB) / 3 GB⌋ capped at 6.
- A request that exceeds `wall_s` kills the worker (it restarts lazily); a worker that dies returns
  `infra_error="repl process died"`, `extra.died=True`. CPU seconds of killed workers are accumulated for energy.
- **Backend `cli`:** `lean Main.lean` per request with `LEAN_PATH` (fallback; parity tested).
- Messages from the server carry exact positions; `stdout` is synthesised in CLI format so text parsers
  (`#print axioms`, eval markers) work for both backends.

### 5.2 File builder (`builder.py`)
`build(template, *, fn, params, ret, theorem_stmt, cand, tests, entries, with_proof) -> (source, LineMap)`:
locked template with candidate regions (proof region = candidate proof in proof modes, else `sorry`); then a
generated harness section: in proof modes `#print axioms F_spec_satisfied`; one `#guard` per test; one
`set_option maxHeartbeats <entry tier> in theorem prl_try_k <statement> := by <script>` + `#print axioms
prl_try_k` per entry. `import Mathlib` is ensured. The precondition argument of test calls is
`(by first | decide | trivial | (simp_all; done) | omega | sorry)` — or omitted when the locked header has no
`h_precond` (some VERINA functions). The harness `sorry` never enters an accepted proof (axioms are checked
only on proof declarations). `build_batch` (dataset building) and `build_eval` (`#eval!` with
`<<PRL:k>>…<</PRL>>` markers) use the same rendering.

### 5.3 Result interpretation (in `verify.py`)
- `compile_ok` ⇔ no error in the template lines before `proof_aux`.
- Test i passes ⇔ no error on its line.
- Entry closed ⇔ no error in its range ∧ `#print axioms` (matched by declaration name — Lean prints it without
  a position in CLI mode) ⊆ {propext, Classical.choice, Quot.sound}.
- Model proof ok ⇔ no error in the proof span ∧ clean axioms of `F_spec_satisfied`.

### 5.4 Verify (`verify.py`)
`Judge.verify(fam, cand, mode, *, tests="all", skip_static=False, full_vector=False, force_portfolio=False)`,
modes `portfolio | model_proof | portfolio_then_model | tests`:
1. Static pre-filter (`integrity.static_check`); reject → `failure_kind="integrity"`, no Lean run.
2. Locked-region hash check (defence in depth).
3. **Stage 1** request: compile + all tests (+ model proof). Timeout or worker death → confirmed once in a fresh
   worker; repeat ⇒ `failure_kind` = `timeout` / `resource` (candidate fault).
4. **Stage 2** only if the mode uses the portfolio and compile ∧ tests pass (or `full_vector` / `force_portfolio`):
   entries one request each, Tier L then Tier H, stop at the first closing entry unless `full_vector`.
5. `success = compile_ok ∧ proof_ok ∧ integrity_ok ∧ visible ∧ hidden`; `failure_kind = classify_failure(vr)`
   ∈ {None, integrity, compile, test, proof, timeout, resource, infra}.
6. Cached by content key (stage-1 source, entry scripts, tiers, mode, test split).

Helpers: `eval_outputs` (actual outputs for witnesses), `witness_line` (first failing *visible* test only),
`batch_tests` / `batch_tests_with` (dataset building; one request per candidate with `lean.batch_wall_s`).

### 5.5 Portfolio (`portfolio.py` + `prereg/portfolio.yaml`)
Two tiers: `L` (50k heartbeats): decide, simp, simp_all, unfold_omega, simp_omega, simp_all_omega,
split_simp_all, split_omega; `H` (200k): grind, simp_grind, aesop, fun_ind_simp@R, fun_ind_grind@R,
ind_simp_all@x, ind_grind@x. Template variables `{F}{P}{Q}{H}{R}{U}{x}` are derived mechanically (locked aux
names, `code_aux` defs, `F.<let rec | where>` names, recursive functions, List/Nat parameters). `expand` returns
all L entries then all H entries (YAML order within a tier), capped at 24.

### 5.6 Integrity (`integrity.py`)
`static_check(cand, mode, family) -> StaticResult(ok, reasons)`:
1. **Normalise**: strip `--` line comments and nested `/- … -/` block comments; replace string and char literal contents with placeholders (so tokens inside strings are ignored).
2. **Markers**: any `!benchmark` → `region_marker`.
3. **Forbidden tokens** (regex word boundaries) in all candidate regions: `sorry`, `admit`, `axiom`, `native_decide`, `implemented_by`, `extern`, `unsafe`, `opaque`, `csimp`, `macro`, `macro_rules`, `syntax`, `elab`, `elab_rules`, `run_tac`, `run_cmd`, `run_elab`, `set_option`, `import`, `namespace`, `section`, `export`, `notation`, `infix`, `infixl`, `infixr`, `prefix`, `postfix`, `attribute`, `initialize`, `builtin_initialize`, `Lean.Elab`, `Lean.Meta`, `ofReduceBool`, `Decidable.decide` redefinition, and any `#`-command at line start (`#eval`, `#exit`, `#print`, `#check`, `#guard`, …).
4. **Declarations in code regions**: allowed top-level commands in `code_aux`: `def`, `abbrev`, `@[simp] def`, `@[reducible] def`, `structure`, `inductive`, `mutual … end`, `termination_by`/`decreasing_by` (attached), `where`. Rejected: `theorem`, `lemma`, `example`, `instance`, `class`, `opaque`, `axiom`, `private`/`protected` modifiers on theorems.
5. **Locked names**: candidate must not declare `F`, `F_precond`, `F_postcond`, `F_spec_satisfied`, any name declared in `solution_aux`/`precond_aux`/`postcond_aux`, or names starting with `prl_`.
6. **Code-only modes** (C, C-plain, S, S-plain): `proof_aux` and `proof` must be empty; additionally the `code`/`code_aux` text must not contain `theorem`/`lemma`.
7. **Proof modes**: `proof_aux` may contain `theorem`/`lemma`/`def`; same forbidden tokens apply.
8. **Body sanity**: `code` non-empty; must not contain a top-level `def F` (signature lock — the extractor removes it; re-occurrence means a second definition).

Post-Lean checks: locked hash (§4.1) and axioms (§5.3).

`degeneracy_flags(cand, family)` (IR-7, recorded, not rejecting): `mentions_postcond`, `uses_choice` (`Classical.choose|Classical.epsilon|Exists.choose|Classical.indefiniteDescription`), `hardcoded_tests` (≥3 visible test input literals appear in the code), `uses_decide_on_spec` (`decide` applied to an expression mentioning `_postcond`).

### 5.7 Hints (`hints.py` + `prereg/hints.yaml`) and the feedback router (`prl/conditions/feedback.py`)
`hints.extract(fam, cand, vr, witness_line) -> Hint(kinds, text)`: compile error text, or the failing visible
witness (+ hidden-failure count only), or the closest entry's first unsolved goal (≤600 chars); plus structural
pointers (`partial_def`, `well_founded`, `imperative_loop`, `nat_int_mix`, `opaque_helper`, `array_index`,
`fold_accumulator`, `spec_shape_mismatch`); total ≤1,200 chars; deterministic.

`feedback.route(cond, fam, cand, vr, *, extract_ok, witness_line) -> Feedback(kind, text, hint_kinds)`:

| failure \ cond | A | B / BP | C / S | Cplain / Splain |
|---|---|---|---|---|
| extraction | none | "no `def F` found" | "no `def F` found" | generic |
| integrity | none | rules violated | rules violated | generic |
| compile | none | Lean errors | Lean errors + pointers | generic |
| test | none | visible witness + counts | witness + counts + pointers | generic |
| timeout / resource | none | "did not terminate" | same + pointers | generic |
| proof | none | proof errors | best unsolved goal + pointers | generic |

Hidden-test failures appear only as a count. Infrastructure failures never reach the router.

### 5.8 Test literal rendering and hidden tests (`prl.testgen`)
- `literals.py`: a recursive type parser for `Int, Nat, Bool, Char, String, UInt8, Float, List T, Array T, Option T, T × U, Prod T U, (T)`; `render(type, json_value)` → Lean literal (negative numbers parenthesised; strings escaped; arrays `#[...]`; `Prod` `(a, b)`); `random_value(type, rng, size)` generator with boundary bias (0, ±1, empty collections, singleton, duplicates). `Map`, `HashMap`, `Float` returns → unsupported (family flagged `hidden_unavailable`).
- `hidden.py`: candidates = random values by type (60%: perturbations of a visible input, because restrictive preconditions make purely random inputs rarely admissible), deduplicated against visible inputs, `per_family·candidates_factor` of them. Request 1 (admissibility): `example : Q args := by first | decide | trivial | (simp_all [Q]; done) | omega | grind [Q]` per input; admissible ⇔ no error (the precondition is *proved*). Request 2 (oracle): `#eval! IO.println ("<<PRL:k>>" ++ reprStr (F args …) ++ "<</PRL>>")` on the reference; outputs parsed by marker. Request 3 (round-trip): the reference must pass every rendered guard; failing ones are dropped. At most `per_family` tests, stored with sha256 in `data/hidden/`, never readable by prompt code. Timeouts bisect the batch.

### 5.9 Code features (`prl/analysis/features.py`, shared by hints)
Returns a dict of booleans/ints: `loc`, `n_helpers`, `uses_match`, `uses_if`, `self_recursive`, `let_rec`, `where_helpers`, `partial`, `well_founded`, `imperative_loop`, `fold`, `list_ops` (map/filter/foldl/zip/…), `array_index_bang`, `array_ops`, `nat_int_cast`, `uses_bool_ops`, `max_nesting` (indent levels), `tail_recursive_accumulator`. Pure function of code text.

---

## 6. `prl.mutate` — mutation operators

`mutants(code: str, code_aux: str, rng) -> list[Mutant]` over the *code* region (and `code_aux` if non-empty). Tokenisation with a light Lean lexer (identifiers, numbers, operators, strings, comments skipped). Operators (class → rewrites):

| Class | Rewrites |
|---|---|
| `arith` | `+`↔`-`, `*`→`+`, `/`→`*`, `%`→`/` |
| `relflip` | `<`↔`≤`, `>`↔`≥`, `<=`↔`<`, `>=`↔`>`, `=`→`≠` (only in `if`/`decide` contexts: after `if` and before `then`), `==`↔`!=` |
| `boolop` | `&&`↔`\|\|`, `∧`↔`∨` |
| `const` | integer literal `n` → `n+1`, `n-1` (n>0), `0`↔`1` |
| `negate_cond` | `if c then` → `if ¬(c) then` |
| `swap_branches` | `if c then A else B` → `if c then B else A` (single-line or balanced) |
| `init_value` | first argument literal of `foldl`/`foldr` or initial `let mut x := n` → `n±1` |
| `drop_succ` | `+ 1` / `- 1` removal |
| `swap_args` | `f a b` → `f b a` for `min/max/Nat.sub/List.append/++` |

Each mutant: `(class, line, col, before, after, code_aux', code')`. Filtering pipeline (`select.py`): up to 12 candidates per family sampled across operator classes; compile ∧ visible+hidden tests checked **one request per candidate** with a short wall guard (`lean.batch_wall_s`; mutants may not terminate) → keep failing ones → dedupe by normalised code → stratified pick by class with `Random(seed+hash(family))`, ≤2 per family, preferring distinct classes; condition T is then run on each chosen mutant (`force_portfolio`) — a mutant the portfolio proves is flagged `weak_spec`. Witness = first failing visible test, else first failing hidden test (stored but shown as visible witness only if visible).

---

## 7. `prl.natural` — natural bugs (primary pool) and shaping instances
`natural_for_family(fam, judge, client, [generator], samples, cfg, per_family)`: zero-shot prompt
(`prompts/natural.txt`, no faulty code), seeds 5000+s for s < `natural.samples` (4, resample cap); keep a
candidate iff it passes the static pre-filter, compiles and fails ≥1 test; at most
`natural.per_family_per_generator` (1) per family per generator; instance id
`<family>__nat__<generator>__<s>`; provenance stores generator, seed, raw output (≤6,000 chars).
Generators: `models.natural_generators` = Qwen3.5-0.8B, Qwen3.5-9B (never repairers). The witness is the first
failing visible test (actual output via `eval_outputs`), else a hidden test (not shown to models).
`shaping_instance(fam)`: correct reference with `ref.T.closed = False` → instance `<family>__shape__0`.

---

## 8. `prl.models` — agent layer

### 8.1 Client (`lmstudio.py`)
- `POST {base}/v1/chat/completions` with model, messages, temperature, top_p, max_tokens, seed and
  `reasoning_effort: "none"` (verified: `reasoning_tokens = 0`). Any returned `reasoning_content` is wrapped in
  `<think>` tags and stripped at extraction; its tokens still count against the budget.
- Retries on connection errors / 5xx / 404 / 409 / 429 with exponential backoff → `InfraError` (never charged).
- `ensure_loaded(key, ctx=8192, parallel)`: `lms unload --all`; `lms load <key> --context-length 8192 --gpu max
  -y --identifier <key> --parallel <n>`. Engine: LM Studio's CUDA 12 llama.cpp runtime.

### 8.2 Model registry (`registry.py`)
`ModelSpec(key, lms_path, family, size_b, role, gguf_sha256)`; hashes recorded from the GGUF file on disk at study start.

### 8.3 Prompts (`prompts.py` + `prereg/prompts/`)
- `system.txt` (shared): Lean 4 expert; Lean 4 (not Lean 3) syntax; output format rules.
- `task_block` (shared, generated from `TaskView`): description, Lean signature line, precondition and postcondition definitions (with their aux), the start implementation as a complete `def` (signature line + body).
- Condition instructions:
  - `A.txt`, `B.txt`, `BP.txt`: "Fix the implementation and prove the theorem. Output exactly two ```lean blocks: (1) the full `def` (helpers before it allowed); (2) the theorem `<name>_spec_satisfied` with its proof (lemmas before it allowed). Do not use sorry/admit/axiom/native_decide."
  - `C.txt`, `Cplain.txt`: "Fix the implementation so that it is correct **and simple enough for Lean's automatic tactics (simp, omega, grind, induction) to prove the specification**. Prefer structural recursion over the same structure as the specification, pattern matching, and avoid partial/imperative loops. Output exactly one ```lean block with the full `def` (helpers before it allowed). Do NOT write any proof."
  - `S.txt`, `Splain.txt`: as C but "The implementation below is already behaviourally correct, but Lean's automatic tactics cannot prove it. Rewrite it into an equivalent implementation that the tactics can prove."
- Feedback blocks (`feedback.py`):
  - B/BP: `Your previous attempt failed.\n<failing test line if any>\nLean errors:\n<≤3 errors>`.
  - C/S: `Your previous attempt failed.\n<hint.text>`.
  - Cplain/Splain: `The candidate was rejected. Try again.`
- History: messages = system, user(task + instruction), then for the last `history_turns` turns: assistant(raw output truncated to 4,000 chars), user(feedback). Same rule for all conditions.
- `TaskView` construction is the only prompt input; a unit test asserts that rendered prompts never contain the reference `code`/`proof` text (when it differs from start), hidden test literals, or paths under `data/hidden`.

### 8.4 Extraction (`extract.py`)
1. Strip `<think>…</think>`.
2. Find fenced blocks ```` ```lean ```` / ```` ``` ````; if none, treat whole text as one block.
3. Code block = the first block containing `def F` (word boundary). Within it: `code_aux` = text before the line starting `def F`; definition = from that line on. Split the definition at the first `:=` that ends the signature (scan with bracket depth 0 after the parameter list). Body = remainder (dedented). If the block contains `theorem`/`lemma` after the def (model put the proof in the same block), split it off into the proof part.
4. Proof (proof modes): the first block containing `theorem F_spec_satisfied`; `proof_aux` = text before it; proof = text after its `:= by` (dedented). If missing → `proof=""` (verification will fail on proof, counted).
5. Header check: the harness always re-emits the **locked** header, so a differing model header only adds the note `signature_differs` (renamed or retyped parameters simply fail to compile).
5b. Echoed locked declarations (`F_precond`, `F_postcond`, `F_spec_satisfied`, locked aux names) in `code_aux` are dropped (note `dropped_locked_echo`); they could never influence verification because the locked originals are re-emitted.
6. Truncated output (`finish_reason=length`) is still extracted if a block parses; else `extract_error="truncated"`.

---

## 9. `prl.conditions` — protocols, feedback, probes

`run_condition(cond, inst, fam, model, seed, cfg, judge, gen, raw_sink) -> RunResult`:
- `Budget(n_gen, max_total_tokens, max_infer_s)`; the first exhausted cap is the stop reason.
- Per generation: messages (A: no history; others: last `history_turns` turns) → completion (seed
  `seed·1000 + attempt`) → charge tokens and seconds → extract (dropping echoed locked definitions) →
  `verify_with_infra_retry` (same candidate re-verified up to 2× on infrastructure failure, then `InfraError`
  abandons the run for re-execution) → attempt record (with `failure_kind`, `feedback_kind`, `hint_kinds`).
- B/BP: feedback after every attempt via the router. C/C-plain/S/S-plain: rounds of `c_round_k` samples
  sharing the same history; after each round, feedback for the round's best candidate (compiled ∧ tests pass >
  compiled > other).
- `MODE = {A, B: model_proof; BP: portfolio_then_model; C, Cplain, S, Splain: portfolio}`.
- Turn-0 information is identical for B, BP, C, C-plain (task + visible failing witness).

`probes.compile_probe(models, n_tasks)` and `probes.determinism_probe(models)`: Phase-0 floor-effect and
seed-determinism checks (idle GPU only).

---

## 10. `prl.driver`

- `plan(instances, conditions, models, seeds)` sorted by (model, condition, instance, seed).
- `Runner.run_all`: skips completed run ids; prunes orphan attempts of incomplete runs; executes
  **(model, condition) blocks sequentially**, each inside an `EnergyMeter` (`prl/energy.py`: NVML GPU energy
  counter delta, Lean-worker CPU-seconds × `energy.cpu_watts_per_thread`, CO2 via `grid_kg_co2_per_kwh`),
  written to `energy.jsonl` with the block's run ids; runs inside a block in a thread pool.
- Records: `attempts.jsonl` (one per generation), `runs.jsonl` (one per run, with outcome label, distances,
  `ref_auto`, code features, flags, prereg hash), `energy.jsonl`, raw prompts/outputs under `raw/`.
  Line writes are locked and fsync'd.
- Outcome label (`outcome_label`): verified_repair > verified_but_wrong > integrity_violation >
  correct_unverified > unresolved.
- Freeze guard for `main` / `heldout` (`prl.prereg.freeze_status`).

---

## 11. `prl.analysis`

### 11.1 Outcomes
Computed by `prl.driver.runner.outcome_label` at run time (priority order in §10).

### 11.2 Statistics (`stats.py`)
- `family_scores(runs, cond, model) -> Series[family → mean over seeds of max over instances success]`.
- `signflip_test(x, y, n_perm, seed, alternative="greater")`: d = x − y per family; statistic = mean(d); exact enumeration when ≤ 2^16 non-zero diffs else Monte-Carlo with `n_perm`; p = (count(stat* ≥ stat) + 1)/(n + 1).
- `holm(pvals) -> adjusted`.
- `mcnemar_exact(b, c)`: two-sided binomial test on discordant counts (b = only-x, c = only-y), plus one-sided.
- `cluster_bootstrap_diff(x, y, B, seed)`: resample families with replacement, return mean diff and percentile 95% CI.
- `cohens_h(p1, p2) = 2·asin(√p1) − 2·asin(√p2)`.
- `min_detectable(D, alpha)`: smallest b such that one-sided binomial(b; D, 0.5) p ≤ alpha.
- Unit-tested against scipy/statsmodels and hand-computed cases.

### 11.3 Mechanism (`mechanism.py`)
- Token-level normalised Levenshtein distance between code texts after normalisation (strip comments, collapse whitespace, rename bound variables in `fun x =>`/`match` arms α-consistently is *not* attempted; whitespace/comment normalisation only).
- `equiv_to_ref = normalise(final) == normalise(reference)`.
- Class: `revert` if `equiv_to_ref` or (`ref_auto` ∧ `dist_to_ref ≤ revert_distance`); `shaping` if ¬`ref_auto`; else `other`.
- Outputs: share table per model with bootstrap CI; C success split by `ref_auto`.

### 11.4 Code shapes (in `report.py`, features from `features.py`)
Dataset = T on references + every verified-or-test-passing final candidate of C/C-plain/S/S-plain; label =
portfolio closed. Per binary feature: P(closed | feature) vs P(closed | ¬feature) with bootstrap CIs; closing
entry distribution.

### 11.5 Reports (`report.py`)
`analyze(study_dirs, cfg, out)` writes `results/`: `t_coverage.*`, `comparisons.csv` and `rq1_main.md` (primary
bug pool chosen by `primary_pool` from `study.yaml: bugs`; Holm over the primary tests of the primary models),
`rq2_mechanism.md`, `rq4_shapes*.{md,csv}`, `rq5_costs.md` (+ `rq5_energy.csv`: GPU J measured, CPU J and CO2
estimated, J per verified repair), `outcomes.csv`, `sensitivity_n.csv`, `integrity_flags.csv`,
`figures/rates.png`, `summary.json`. Deterministic and idempotent (tested).
`audit_sample`: stratified `audit_frac` of successes **plus every flagged success**; `prl audit --merge`
summarises the filled-in CSV into `results/audit/summary.md`.

### 11.6 Sensitivity to N
Post-hoc truncation: a run counts as success at budget n if `success_attempt_idx < n`. Reported for n ∈ {2, 4, 8} (exploratory; valid because conditions do not adapt to N except via stopping).

---

## 12. CLI (`prl/cli.py`)

| Command | Action |
|---|---|
| `prl env` | toolchain, backend, Mathlib smoke test, LM Studio models |
| `prl tasks build` | parse 189 VERINA tasks → `data/families/` |
| `prl tasks check [--tests visible] [--ids]` | reference checks + condition T (full vector) |
| `prl hidden [--ids] [--force]` | hidden differential tests |
| `prl bugs natural` | natural bugs from every generator (GPU) |
| `prl bugs mutants` | mutants (CPU) |
| `prl bugs shaping` | study-S instances |
| `prl splits` | family-level splits, stamps instances |
| `prl probe compile|determinism --models …` | Phase-0 probes (GPU) |
| `prl run --study S --split … --kinds … --conditions … --models … [--seeds] [--families] [--limit-families]` | driver |
| `prl freeze [--note]` | write `prereg/FREEZE.json` |
| `prl analyze --study S1,S2` | all tables and figures |
| `prl audit --study S [--merge]` | audit sample / merge filled audit |

Global option `--lean-workers N` (default from `study.yaml`, 0 = from free RAM).

---

## 13. Error handling summary

| Error | Where | Handling |
|---|---|---|
| Stage-1 timeout / worker death | verify | confirm once in a fresh worker; repeat ⇒ candidate fault (`timeout` / `resource`), attempt counts |
| Portfolio entry timeout | verify | entry not closed (`entry_goals[id] = "timeout"`) |
| Verifier infrastructure failure | protocols | same candidate re-verified ≤2×, never charged; then `InfraError` → run abandoned, re-executed on resume |
| LM Studio down / errors | client | backoff ≤7 tries → `InfraError` → run retried by the driver (≤2) then left for resume |
| Extraction failure | extract | attempt recorded (`failure_kind=extraction`), budget consumed |
| Static integrity violation | integrity | attempt recorded, no Lean run |
| Memory exhaustion | runner | Job Object cap kills only that worker; handled as worker death above |
| Corrupted JSONL line | driver | skipped; run re-executed |

---

## 14. Test plan (`tests/`)

| File | Covers | Marker |
|---|---|---|
| `test_core_units.py` | regions round-trip on all 189 templates and locked-hash invariance; literals; extraction (fenced, proof split, echoed locked definitions); static integrity (every rejection, comment/string evasion, legitimate code); portfolio expansion and tier order; failure classification; feedback-router paths; energy arithmetic; primary-pool rule; mechanism; package layering | — |
| `test_hints_mutate.py` | every structural pointer; hint stages; hidden-test privacy; cap; mutation operators, comment/string safety, determinism | — |
| `test_protocols_driver.py` | every condition with a fake model and judge: early stop, budget caps, A without history, C rounds, C-plain feedback, turn-0 parity, prompt leakage; driver kill-and-resume | — |
| `test_stats.py` | sign-flip exactness, Holm, McNemar vs scipy, bootstrap determinism, Cohen's h, minimum detectable effect | — |
| `test_report.py` | analysis idempotence on synthetic logs | — |
| `test_lean_integrity.py` | 18 escape attempts on real Lean (zero false successes), reference vs re-shaped code, determinism | `lean` |

