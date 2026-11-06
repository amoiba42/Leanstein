# 0008. Matched run budget

## Status
Accepted

## Context
Condition C must not win by using more attempts, tokens or time than the proof-writing conditions.

## Decision
Per (instance, condition, model, seed): at most 8 generations, 48,000 total tokens, 1,536 completion tokens per
call, and 600 s of inference; the first cap reached ends the run. C, C-plain, S and S-plain sample two candidates
per feedback round. The last two turns are kept verbatim in the conversation for every condition.

The inference cap was raised from 240 s to 600 s before the freeze (team decision 3 in `prereg/deviations.md`): in the pilot, 240 s stopped 5 of 42 qwen3.5-4b B runs and no C runs, so it was not
condition-neutral. B also slowed as a run went on, because Lean error text accumulated in its prompt, so the cap removed exactly
B's late attempts. Extrapolated demand was 283–395 s; caps of 480 s and above truncate no pilot run and cost the
same, and 600 s is 1.5× the uncensored pilot maximum (394.5 s). The value was chosen from stop reasons, never from
success counts. The token cap never bound in the pilot and stayed at 48,000. A run halts if `infer_time` stops
exceed 1% of runs in any condition.

## Consequences
- No study run hit the 600 s cap.
- The pilot ran under the 240 s cap and is never pooled with or compared to the study; the power note's C vs B
  figures, estimated from it, are mildly optimistic.
- Costs are reported per verified repair, so failed runs count against a condition (ADR 0014).
