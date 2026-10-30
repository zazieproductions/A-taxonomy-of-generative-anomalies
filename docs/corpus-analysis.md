# Cross-experiment synthesis — what the snapshot supports

**Cut-off:** supplied Workbench exports dated 2026-10-30. This is a reproducible descriptive reading of the archived records, not a preregistered study, significance test, or causal attribution.

## 1. First find the true denominator

| Export file | Workbench experiment ID | Run rows in file | Snapshots | Compare snapshots |
|---|---|---:|---:|---:|
| `2026-10-30_extreme-sampling_genre-capture_batch-06.jsonl` | `9a5c3199-9b2f-4ae0-b4a9-4b504e7399f4` | 17 | 13 | 2 |
| `2026-10-30_identity-meltdown_sampling-experiments.jsonl` | `c638494f-e4a0-4237-8e8c-47e540f1e45c` | 112 | 24 | 20 |
| `2026-10-30_repetition-traps_batch-05.jsonl` | `c638494f-e4a0-4237-8e8c-47e540f1e45c` | 118 | 30 | 20 |

The two identity/repetition exports share the **same Workbench experiment ID**, same title, and the same first 112 run IDs. The later export adds six run IDs. Their overlapping run objects are identical; the pipeline reports zero conflicting duplicate IDs. Counting filenames as separate experiments would inflate the corpus and misrepresent the experiment structure.

**Audit arithmetic:** 17 + 112 + 118 = 247 source run rows; 247 − 112 repeated appearances = **135 unique generations** across two experiments. The 13 ordinary snapshots and 42 comparison snapshots (2 + 20 + 20) are export history, not extra samples. All comparison-lane generation IDs in these files already point to run IDs in `runs`.

## 2. Corpus profile

- **135** generations; **60** exact prompt strings.
- **110 completed / 25 cancelled**. The 25 cancelled runs remain in the data, including 23 with text and two with empty text.
- Run aliases: **73 `llama-8b`**, **62 `trinity-truebase`**. Full upstream model identifiers and wrapper aliases remain separate fields.
- Run start times span about **74 minutes** on one date (18:41:53–19:55:35 UTC).
- The source records `seed_mode: random` for all 135 and contains **135 distinct numeric seed values**. No exact-seed replication is present.
- Every run records `max_tokens: 200` and `repetition_penalty: 1.0`. Those parameters cannot explain between-run variation in this snapshot because they do not vary.
- **70** canonical generations contain token-level logprob arrays. The public Atlas suppresses five of those arrays when a structured or labelled-personal-field pattern is detected; its display count is therefore 65/135.

### Sampling coverage (all supplied generations)

| Field | Observed coverage | What it does *not* establish |
|---|---|---|
| Temperature | 38 distinct values, `1e-11` to `32.200980989887874`; median 1.2 | No balanced temperature grid; several dimensions move with it. |
| Top P | 12 distinct values, `0.10` to `1.0`; `1.0` in 95/135 | Top P is not varied independently in a common prompt/model block. |
| Top K | `-1` in 119, `9` in 10, `1` in 6 | The export does not document backend semantics for `-1` or interactions with other filters. |
| Min P | `0.0` in 123; `0.12218974389217321` in 8; `0.99999999999` in 4 | The nonzero values occur in a small, highly confounded batch. |
| Presence penalty | 10 values, from `-2.0` to `2.0` | No single-factor penalty test. |
| Frequency penalty | 4 values, from `0.0` to `2.0` | No single-factor penalty test. |

All values above are read from recorded configs. The archive does not reinterpret parameter values or fill missing settings with assumed defaults.

## 3. Completion status is part of the evidence

The distinction between rendered text, status, token count, and finish reason matters:

- All **110 completed** runs report `usage_source: upstream`; 92 have `finish_reason: length` and 18 have `finish_reason: stop`.
- Of 25 cancelled runs, 23 report `usage_source: tokenizer` and two have no usage source. All 25 have no finish reason.
- Two completed records have an empty completion string but report one completion token each and `finish_reason: stop`.
- Two cancelled records have empty completion strings and null prompt/completion token counts.
- Prompt and completion token counts are each present in 133/135 records. Completion-count median is 200, but the mean is about 170; the count source differs by status.

These values are not contradictory once the fields are kept separate. They do caution against analyzing only the visible text or comparing token counts across different usage sources.

## 4. Matched model comparisons: useful, still not controlled enough

The archive finds **19 exact-prompt, exact-non-model-config groups** containing exactly two distinct run-level models: 17 in experiment `c638…`, two in `9a5…`. Each pair matches the full recorded generation configuration except `model`, `wrapper_model_id`, and `seed`; each recorded seed differs.

- 18 pairs contain two completed runs.
- One pair contains a completed Llama run and a cancelled Trinity run.
- One short-prompt pair (“Goodbye cruel world”) puts a news-register/keyword-collage continuation beside a more fragmentary word-like continuation. Both report 200 completion tokens and a length finish, but seeds differ.

The pairs are valuable specimens because they hold many recorded fields constant. They do **not** isolate a model effect: model and seed change together, and each pair has one run per model. In addition, the source does not document model build versions beyond the recorded identifiers.

## 5. Three text-level findings worth looking at

### A. Repetition inside a completion is different from duplicate records

No exact completion string is duplicated across the **131 non-empty unique generations**. Yet generation `4e2b509a-6f5b-410e-bbdf-46bea8034860` repeats one complete sentence 18 times in its 200-token completion; the prompt already contains that sentence twice. A simple case-folded Unicode regex split finds 10 types in 182 word tokens (0.055 type-token ratio). The phrase is readable and present in the prompt, so the careful description is **echo/repetition under a length finish**, not “the sampler caused collapse.”

A separate shell-like specimen, `a6f3cf18-d67e-40f5-a281-54899fa32853`, duplicates the same date condition and error message twice before closing its loop. This is a different surface mechanism—procedural self-reproduction—under the same broad recursive-degeneration label.

### B. Coherent impossibility and fractured lexical surface are not the same anomaly

Generation `0efaa96d-dbe8-4195-a391-cbb7b2f640c7` develops a fictional office that administers incompatible accounts of whether “yesterday” is past, future, or replaced. Its impossible premise remains legible across several paragraphs. That supports an initial reading of **conceptual surrealism**, with **semantic absurdism** where incompatible accounts coexist.

By contrast, `43338cd7-f8ff-4160-913e-84c4e3c2ed27` (Llama, temperature 5.0, Top P 1.0; 200 reported completion tokens, length finish) contains fused word-like fragments, script changes, and punctuation collisions. The simple Unicode word split happens to return 118 forms in 118 words. High lexical variety here does not equal high coherence; the label **lexical disintegration** rests on visible recoverability, not on the numeric ratio or temperature.

### C. Plausible document voice can normalize a one-word cue

Generation `0dd744b6-62a7-4286-a6f4-8875b799e949` begins from the one-word prompt “Zazie” and produces two competing product descriptions and a feature list. It is cancelled after 117 completion tokens reported by the tokenizer. The strongest claim is about **register**: an ambiguous name is treated as a product and written as if a catalogue were expected. The completion is partial and its product details are not verified.

## 6. The cancellation/temperature trap

The extreme-sampling experiment has 17 runs, 15 exact prompts, 13 cancelled runs, and four completed runs. All four completed runs record temperature 1.0. The two runs at the highest recorded temperature (about 32.2) are both cancelled and also use Top K 1, nonzero Min P, a nonzero presence penalty, and different prompts. A temperature-only explanation is not supported: settings, model exposure, prompt, and completion status move together.

The appropriate next step is not to fit a curve through these 17 points. It is to freeze one prompt/model, predefine a temperature grid, hold all other settings constant, run replicated seeds in every condition, and annotate completions blind to configuration.

## 7. Measurement and interpretation limits

1. Regex word tokens are not Workbench/model tokens. Type-token ratios depend on text length, Unicode segmentation, and how punctuation is handled.
2. “Completed” and `finish_reason: length` are separate fields. A length finish can be a textually coherent ending to the available window or an abrupt truncation; it is not itself a quality label.
3. Usage sources differ; counts from upstream and tokenizer sources are not presumed equivalent.
4. Top alternatives are incomplete candidate lists, not a normalized distribution. The Atlas displays their reported log probabilities without converting them into percentages.
5. The supplied prompts include sensitive-looking and distressing content. The public projection masks common structured and selected labelled values but is not a privacy guarantee; raw and canonical text remain unchanged.
6. Taxonomy labels and exhibit commentary are initial AI-assisted editorial readings, not adjudicated annotations. Human review and inter-annotator work are needed before treating them as a stable coding scheme.

## Reproduction

```sh
python -m anomaly_archive ingest . --source-root . --output data/normalized/corpus.json
python -m anomaly_archive validate data/normalized/corpus.json \
  --annotations docs/data/annotations.json \
  --taxonomy docs/data/taxonomy.json
python -m anomaly_archive stats data/normalized/corpus.json
```
