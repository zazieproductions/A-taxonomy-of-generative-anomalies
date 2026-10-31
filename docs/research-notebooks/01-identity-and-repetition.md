# Experiment notebook 01 — Identity, repetition, and continuation drift

> **Notebook status:** retrospective, post-hoc analysis of archived ACS Workbench exports. The exports do not contain a preregistered hypothesis, randomization plan, or operator-authored controls. The hypothesis below is a proposed next test, not a claim about the original operator's intent.

## Record

| Field | Recorded value |
|---|---|
| Workbench experiment ID | `c638494f-e4a0-4237-8e8c-47e540f1e45c` |
| Workbench title | `Transcript of a psychological interview` |
| Source exports | `2026-10-30_identity-meltdown_sampling-experiments.jsonl`; `2026-10-30_repetition-traps_batch-05.jsonl` |
| Export window | 2026-10-30 18:38:04–19:48:45 UTC (created/updated metadata) |
| Deduplicated generations | 118 |
| Exact prompts | 45 |
| Recorded run models | `llama-8b` (71); `trinity-truebase` (47) |
| Upstream model identifiers | `meta-llama/Llama-3.1-8B`; `arcee-ai/Trinity-Large-TrueBase` |

The two filenames are **successive snapshots of the same Workbench experiment ID**, not evidence of two independent experiments. The earlier export has 112 run rows; the later one has 118. All 112 original run IDs recur unchanged in the later export, which adds six IDs. Across the pair, the pipeline sees 230 source rows and retains 118 generations after removing 112 repeated rows. It found no conflicting duplicate run records.

## Archival question and proposed hypothesis

**Question:** When the exact prompt and recorded non-model settings match, how do the two recorded model identifiers differ in continuation style, genre, repetition, and lexical recoverability?

**H1 — proposed prospectively:** Matched prompt/settings pairs will show model-associated differences in continuation form. The current records can motivate this question but cannot isolate a model effect: every matched pair has different recorded seeds, there is only one run per model in each pair, and the seed mode is recorded as `random`.

A second prospective question is whether repetition or lexical fragmentation changes as temperature changes while prompt, model, Top P, penalties, token budget, and seed protocol are held fixed. The current corpus is not a balanced temperature experiment and does not answer that causal question.

## Design and controls

### What is actually recorded

- 118 unique run IDs, all with start and end timestamps.
- 106 runs marked `completed`; 12 marked `cancelled`. Cancelled records are retained as cancelled, even when they contain partial text.
- 45 exact prompt strings and two run-level model aliases.
- All 118 runs have a numeric seed and the source config value `seed_mode: random`; every numeric seed is distinct in this experiment.
- All runs record `max_tokens: 200`, `repetition_penalty: 1.0`, and `min_p: 0.0`.
- Other recorded settings vary: temperature, Top P, Top K, presence penalty, frequency penalty, and requested logprobs.

### Parameter envelope (values copied from the exports)

| Parameter | Recorded values |
|---|---|
| Temperature | 34 distinct values, `1e-11` through `5.0` |
| Top P | 12 distinct values, `0.10` through `1.0` (`0.10`, `0.22`, `0.222`, `0.2222222222`, `0.33`, `0.50`, `0.51`, `0.80`, `0.88`, `0.90`, `0.95`, `1.0`) |
| Top K | `-1` (108 runs), `9` (10 runs) |
| Min P | `0.0` (all 118 runs) |
| Presence penalty | 8 distinct values, `-2.0` through `2.0` |
| Frequency penalty | 4 distinct values, `0.0` through `2.0` |
| Repetition penalty | `1.0` (all 118 runs) |
| Max tokens | `200` (all 118 runs) |
| Requested logprobs | not recorded in 61; `1` in 7; `5` in 50 |
| Returned logprob arrays | available for 57 generations; null for 61 |

**Observed control status:** no experimental control group is documented. The constants above are shared recorded values, not proof of an intended control design. Prompts and several sampling settings vary together.

## Observations

1. **A prior sentence becomes a loop.** Generation `4e2b509a-6f5b-410e-bbdf-46bea8034860` repeats a sentence already present twice in its prompt **18 times in its completion**. It reports 200 completion tokens and `finish_reason: length`. A case-folded Unicode word split finds 10 distinct forms among 182 word tokens (type-token ratio 0.055). This ratio is a small, length-sensitive text heuristic—not the model tokenizer, a measure of meaning, or evidence that a particular parameter caused the repetition.
2. **An impossible premise can stay coherent.** In `0efaa96d-dbe8-4195-a391-cbb7b2f640c7`, a fictional Ministry administers disagreements about whether yesterday has happened, will happen, or has been replaced. The completion develops the conceit in readable prose while allowing incompatible chronologies to coexist. This is an initial editorial example of conceptual surrealism with semantic absurdism; it is not a validated gold label.
3. **There are 17 exact-prompt, exact-config model pairs** when the model identifiers and recorded integer seeds are excluded from the matching key. All 17 pairs in this experiment are marked completed. The two recorded seed values differ in every pair. One striking pair begins from the short seed “Goodbye cruel world”: the `llama-8b` continuation opens in a news register and sheds into a keyword-like collage, while the `trinity-truebase` continuation becomes a fragmented word-like sequence. Each reports 200 completion tokens and a length finish. This is a descriptive contrast, not a same-seed model test.
4. **Empty rendered text is not the same as zero reported tokens.** Two records are marked completed and have an empty `completion_text`, while each reports one completion token and `finish_reason: stop`. Two cancelled records have empty text and null prompt/completion token counts. The archive preserves those distinctions instead of filling them in.
5. **Usage sources vary.** The 118 records report token usage from `upstream` (106), `tokenizer` (10), or no recorded usage source (2). Counts from different usage sources should not be assumed directly comparable.

## Limitations

- The prompt set is diverse (45 exact prompts); it is not a repeated-measures study on one frozen prompt.
- The 17 model pairs match recorded prompt and non-model config fields, but seeds differ and model is confounded with seed. There is one observation per model in each pair, so no within-cell variance is available.
- Temperature, Top P, penalties, model, and prompt often change together. No causal temperature or penalty effect can be identified from this snapshot.
- `seed_mode: random` and a recorded integer seed are preserved literally; the archive does not infer implementation semantics from those values.
- Completion counts may come from different `usage_source` values. Text can be partial, empty, or tokenized in ways not recoverable from the export.
- Logprobs are absent on many records; missing values are not zeros.
- The raw prompts include sensitive-looking and distressing material. A display mask for common structured identifiers is best-effort only; the canonical dataset and source exports remain unmodified. Review authorization and content before public distribution.
- All eight seed annotations in `docs/data/annotations.json` are AI-assisted and unreviewed. They are prompts for human editorial review, not labels for training or evaluation without adjudication.

## Next controlled run (proposal)

Freeze one prompt per prompt family and one model build. For each target temperature, preserve Top P, Top K, Min P, all penalties, stop settings, token budget, and logprob request. Use the same explicitly fixed seed set across model conditions where the Workbench supports it; otherwise record the limitation and run repeated independent seeds per cell. Randomize condition order, predefine completion/cancellation handling, and collect at least five seeds per cell. Publish the raw export, protocol, and a blinded annotation pass before interpreting trends.
