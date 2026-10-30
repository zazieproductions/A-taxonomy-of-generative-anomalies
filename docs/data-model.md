# Data model and provenance

The canonical corpus is generated from the supplied ACS Research Infrastructure Workbench exports. It is the analytical source for the Atlas; `docs/data/atlas.json` is a privacy-filtered publication view, not a replacement for the canonical data.

## Inputs

The supplied files end in `.jsonl`, but each currently contains one large JSON object on one physical line. The reader accepts:

1. a single JSON object in a `.jsonl` file (including a pretty-printed object);
2. conventional one-object-per-line JSONL;
3. a top-level JSON array of objects.

An ACS experiment export is recognized by its `runs` array. Each member is treated as a generation only when it has a stable string `id`. Missing IDs fail ingestion rather than being deduplicated by text or silently dropped. Direct run objects are also accepted for future input formats.

## Canonical paths and schemas

- Canonical normalized corpus: [`data/normalized/corpus.json`](../data/normalized/corpus.json)
- Corpus JSON Schema: [`schemas/corpus-v1.schema.json`](../schemas/corpus-v1.schema.json)
- Annotation JSON Schema: [`schemas/annotation-v1.schema.json`](../schemas/annotation-v1.schema.json)
- Published Atlas projection: [`docs/data/atlas.json`](./data/atlas.json)
- Taxonomy terms: [`docs/data/taxonomy.json`](./data/taxonomy.json)

Schema version 1 is validated by a dependency-free Python validator in `anomaly_archive/schema.py`. The JSON Schema files are also supplied for editors and downstream tooling.

## Corpus shape

```json
{
  "schema_version": 1,
  "record_type": "acs-workbench-corpus",
  "source_exports": [],
  "experiments": [],
  "generations": [],
  "deduplication": {}
}
```

### `source_exports`

One manifest entry per JSON object read from an input file. It records the relative source filename, source-file SHA-256 and byte size, top-level object index, experiment ID/title, export timestamps and mode, raw run-row count, and counts of the Workbench `snapshots` and `compare_snapshots` history arrays. The file hash is over original bytes; input files are never rewritten.

For the supplied one-object files, `object_index` is `0`. `run_index` in generation provenance is zero-based within the source `runs` array. With conventional multi-object JSONL, `object_index` is zero-based among non-blank records.

### `experiments`

One entry per distinct Workbench experiment ID. `metadata_versions` retains each observed top-level metadata object with its source file and hash, excluding only the raw `runs`, `snapshots`, and `compare_snapshots` arrays. This preserves changing export-level settings and prompt metadata without conflating snapshots with new runs.

### `generations`

One entry per unique original Workbench run ID. The following fields are copied without aliasing or inference:

| Normalized field | Source field |
|---|---|
| `generation_id` | `runs[].id` |
| `experiment_id`, `experiment_title` | top-level export `id`, `title` |
| `model` | `runs[].model` (Workbench run-level identifier) |
| `model_identifier` | `runs[].generation_config.model` |
| `wrapper_model_id` | `runs[].generation_config.wrapper_model_id` |
| `prompt` | `runs[].prompt_before` |
| `configured_prompt` | `runs[].generation_config.prompt` |
| `completion` | `runs[].completion_text` |
| `status`, `finalized` | `runs[].status`, `runs[].finalized` |
| `timestamps.started_at`, `timestamps.ended_at` | `runs[].started_at`, `runs[].ended_at` |
| `tokens.prompt`, `tokens.completion`, `tokens.source` | `n_prompt_tokens`, `n_completion_tokens`, `usage_source` |
| `sampling` | all recorded `generation_config` fields except `prompt`, `model`, and `wrapper_model_id` |
| `generation_config` | full source configuration object, including future/unknown fields |
| `logprobs` | `runs[].logprobs`, including token and candidate values where present |
| `finish_reason`, `stop_reason`, `error_message` | source run fields |
| `comparison_run_id` | `runs[].compare_run_id` |
| `source_provenance` | source file hash, source-record digest, experiment ID, export timestamp and indexes |

`source_field_presence` records whether key operational fields appeared in the source object. This distinguishes a missing key from a key supplied with `null`; empty completion text also remains distinct from an absent completion field. In `sampling`, a setting absent from the source is omitted—it is not filled with a presumed default. Null source values are retained as null where the source field is present.

The normalized record intentionally omits the administrative `api_key_id`. It remains present in the unchanged source export. The `source_record_sha256` is a digest of the canonical JSON serialization of the original run object; `source_sha256` is the byte-level digest of the full export file.

## Status, tokens, and logprobs

- `status` is the raw Workbench value. `completed` and `cancelled` are not collapsed into a generic success/failure flag.
- A cancelled run may contain partial completion text and token counts. It remains cancelled.
- A completed run may have empty rendered text while reporting a token count. Empty text is not replaced with a guessed completion.
- Token counts preserve the source values. `usage_source` may differ (for example, upstream vs. tokenizer); counts from differing sources should not automatically be treated as directly comparable.
- Missing logprobs are null, not zero. When present, the full per-token array and available alternatives are retained in the canonical corpus.

## Deduplication and history

The primary key is the original run `id` (normalized as `generation_id`), not a completion hash. Two distinct runs with identical text remain distinct. Repeated appearances of one ID are collapsed to one analytical generation while every source appearance is retained in `source_provenance`.

If versions of the same ID differ, the selected representation is chosen deterministically by latest source-export `updated_at`, then most non-null raw fields, then stable source ordering. A conflict entry lists differing source fields and the chosen source file. The current supplied data has no conflicting duplicate IDs.

The Workbench also exports `snapshots` and `compare_snapshots`; these are not counted as additional generations because they are not independent stable run records. Their counts remain in the source manifest and their raw contents remain in the untouched source files. In the supplied exports, all comparison-lane `generation_id` values point to IDs already present in `runs`. If a future export contains a comparison-only generation ID, this adapter will not promote it automatically; that source shape should be reviewed and supported explicitly before using it as a specimen.

## Public Atlas projection

`python -m anomaly_archive publish` creates `docs/data/atlas.json` from the canonical corpus. It masks common structured identifier patterns, selected labelled personal fields, and some inline self-declared names in prompt/completion strings. When any such pattern is detected in a generation, that record's entire public logprob sequence is suppressed to avoid exposing identifiers split across token boundaries. The canonical corpus and raw exports are not modified.

This is a **best-effort display projection**, not de-identification or a privacy guarantee. It may miss names, addresses, context-dependent identifiers, or novel formats. The original source links lead back to the repository exports. Review rights, content, and privacy before publishing.

The Atlas's 19 model comparison groups are computed from the canonical text/config before masking. A group requires the exact prompt and all generation-config values to match within one experiment except `model`, `wrapper_model_id`, and `seed`; it must contain exactly two distinct run-level models. Seeds differ in every group. Pair membership is therefore a useful browsing aid, not a same-seed causal comparison.

## Rebuild and validate

```sh
python -m unittest discover -s tests -v
python -m anomaly_archive ingest . --source-root .
python -m anomaly_archive validate data/normalized/corpus.json \
  --annotations docs/data/annotations.json \
  --taxonomy docs/data/taxonomy.json
python -m anomaly_archive publish
python -m anomaly_archive stats data/normalized/corpus.json
```
