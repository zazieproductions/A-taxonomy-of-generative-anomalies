# A taxonomy of generative anomalies

### An Archive of Generative Deviance

**An experimental literary archive and computational research bench for base-language-model generations from ACS Research Infrastructure Workbench.**

> We keep the strange output, the settings that accompanied it, and the limits of what we can claim. We do not turn a sampling trace into a causal story without controls.

```text
┌──────────────────────────────────────────────────────────┐
│ FIELD ARCHIVE / 01          ACS RESEARCH WORKBENCH        │
│                                                          │
│   OBSERVE  →  PRESERVE  →  COMPARE  →  ANNOTATE           │
│                                                          │
│   No generated folklore. Only what the export records.   │
└──────────────────────────────────────────────────────────┘
```

[Open the Anomaly Atlas](https://zazieproductions.github.io/A-taxonomy-of-generative-anomalies/) · [Cross-experiment analysis](docs/corpus-analysis.md) · [Data model](docs/data-model.md) · [Working taxonomy](docs/taxonomy-and-annotation.md) · [Contributing](CONTRIBUTING.md)

---

## Snapshot / 30 October 2026

| 247 | 135 | 110 / 25 | 70 | 19 |
|---:|---:|---:|---:|---:|
| source run rows | unique generation IDs | completed / cancelled | token-level logprob arrays | prompt/config-matched model pairs* |

*Pairs match the exact prompt and recorded non-model configuration within an experiment, excluding the model identifiers and seed. **Every pair has different recorded seeds**; this is descriptive comparison, not a same-seed benchmark. One pair contains a cancelled run.

Three supplied `.jsonl` exports resolve to **two Workbench experiment IDs**. The identity and repetition filenames are successive exports of the same experiment: 112 run IDs recur unchanged in the later export, which adds six. The pipeline removes those 112 repeated appearances by original run ID, not by completion text. It reports zero conflicting duplicate records in this snapshot.

## Start here

Requires Python 3.10+; the ingestion and validation tools use only the standard library.

```sh
# Run the regression suite
python -m unittest discover -s tests -v

# Build the canonical, provenance-rich corpus from exports anywhere under this repo
python -m anomaly_archive ingest . --source-root . --output data/normalized/corpus.json

# Validate the corpus and annotation references
python -m anomaly_archive validate data/normalized/corpus.json \
  --annotations docs/data/annotations.json \
  --taxonomy docs/data/taxonomy.json

# Build the best-effort redacted Atlas payload
python -m anomaly_archive publish

# Preview the static site locally (then open http://localhost:8000)
python -m http.server 8000 --bind 0.0.0.0 --directory docs
```

You can also run `python -m anomaly_archive --help` or install the package with `pip install -e .` to use the `anomaly-archive` command.

## What is in the archive?

### Research infrastructure

- **Raw exports remain at their supplied paths and byte-for-byte unchanged.** The Workbench filenames end in `.jsonl`, but each supplied file is one large JSON object on one line. The parser supports that actual format, pretty-printed one-object exports, conventional JSONL, and top-level arrays.
- **Stable identity and source provenance.** Every normalized generation is keyed by the original run ID. Repeated sightings are merged into a provenance list with source filename, file hash, source-record digest, export timestamp, and zero-based record indexes. Conflicting versions are surfaced in an audit block.
- **No silent defaults.** Model identifiers, prompt/configured prompt, completion, sampling values, seeds, penalties, token counts, timestamps, finish reasons, completion status, and available logprobs are retained. A missing setting stays missing; source field presence distinguishes absent keys from explicit nulls.
- **Completed and cancelled are distinct.** A cancelled generation can have a partial completion. A completed record can have empty rendered text while the source reports a token. Neither is silently repaired.
- **Unkeyed history is not double-counted.** `snapshots` and `compare_snapshots` counts are recorded in the manifest, but the `runs` array and its stable IDs are the canonical generation unit. The original snapshots remain available in the untouched raw exports.
- **Schemas and tests.** Versioned JSON Schemas live in [`schemas/`](schemas/); dependency-free validators are exercised by `unittest` fixtures for one-object exports, JSONL, deduplication, conflicting snapshots, null/missing settings, cancellation, annotations, and privacy projection.

The canonical normalized dataset is [`data/normalized/corpus.json`](data/normalized/corpus.json). It omits administrative `api_key_id` values; those values remain only in the unchanged source exports. A full field map and deduplication policy live in [`docs/data-model.md`](docs/data-model.md).

### Anomaly Atlas

The static site in [`docs/`](docs/) includes:

- Searchable specimen gallery with filters for model, status, experiment, temperature, Top P, Top K, Min P, taxonomy, and text.
- Prompt-matched side-by-side model comparisons, with seed differences made explicit.
- Interactive UTC run timelines and a descriptive temperature/lexical-variety scatterplot.
- Per-generation logprob traces and top alternatives where data are present in the public payload.
- Curated literary exhibits with commentary, taxonomy labels, and links to the original Workbench export plus stable generation ID.
- A browser-local manual annotation form. Multiple labels, evidence, rationale, annotator, timestamp, and method are exported as JSON; annotations are not sent to a server.

The public site consumes [`docs/data/atlas.json`](docs/data/atlas.json), a separate publication projection. It masks common structured identifiers, selected labelled personal fields, and some inline self-declared names in text; it suppresses an entire token-logprob sequence if a pattern is detected in that generation. This is **best effort, not de-identification**. Unlabelled names, addresses, context-dependent identifiers, and novel formats can remain. The canonical corpus and raw files are not modified by this projection.

### Research notebooks

One notebook is provided per distinct Workbench experiment ID:

1. [Identity, repetition, and continuation drift](docs/research-notebooks/01-identity-and-repetition.md) — 118 unique generations across two successive exports.
2. [Extreme sampling and genre capture](docs/research-notebooks/02-extreme-sampling-genre-capture.md) — 17 runs, mostly cancelled, with sampling dimensions that co-vary.

Each records a proposed post-hoc hypothesis, observed settings, controls or their absence, notable textual observations, limitations, and a future controlled protocol. The hypotheses are marked as proposals because the source exports do not record preregistration or operator-authored hypotheses. A separate [cross-experiment synthesis](docs/corpus-analysis.md) audits the denominators, sampling coverage, model pairs, completion accounting, and representative text patterns.

## A few readings from the data

These are **textual observations**, not causal findings. The curated examples and seed labels are AI-assisted and await human review.

- **The sentence that could not leave.** One 200-reported-token completion repeats a sentence already present twice in its prompt 18 times. A simple case-folded Unicode word split finds 10 forms across 182 word tokens (0.055 type-token ratio). That ratio is a length-sensitive heuristic, not the model tokenizer or a coherence score.
- **The Ministry of yesterday.** A fictional ministry tries to administer whether yesterday is past, future, erased, or still pending. Its impossible chronology remains readable while propositions conflict—a useful boundary case for conceptual surrealism and semantic absurdism.
- **The catalogue from a one-word seed.** A cancelled partial continuation turns “Zazie” into two incompatible product descriptions and a feature list. This is documentary-sounding normalization, not verified information.
- **A prompt-matched divergence.** For one six-token prompt, two model runs share all recorded non-model settings and each report 200 completion tokens. One enters a news register before becoming a keyword collage; the paired continuation fragments differently. The seeds differ, so this is not a same-seed test.
- **Two completed records have empty rendered text but report one completion token each.** Two cancelled records have empty text and null token counts. Those distinctions are preserved instead of guessed away.
- **Temperature is not an explanation by itself.** In the extreme-sampling batch, 13/17 runs are cancelled and all four completed runs record temperature 1.0. Higher temperatures also coincide with different prompts and candidate/penalty settings. This snapshot cannot isolate a temperature effect.

A more complete field-by-field analysis is in the [research notebooks](docs/research-notebooks/).

## Annotation protocol

The working taxonomy covers conceptual surrealism, semantic absurdism, genre capture, documentary normalization, rhetorical amplification, recursive degeneration, and lexical disintegration. Labels are non-exclusive and require textual evidence. The current eight annotations in `docs/data/annotations.json` are explicitly marked **AI-assisted and unreviewed**; they are examples, not gold labels.

Open a specimen in the Atlas, select multiple labels, enter an annotator ID and rationale, then export the bundle. It includes the checked-in annotations plus local records. Review it before use; either replace `docs/data/annotations.json` with the reviewed bundle or merge only new records by `annotation_id`, not the full export. Validate the result with:

```sh
python -m anomaly_archive validate data/normalized/corpus.json \
  --annotations docs/data/annotations.json \
  --taxonomy docs/data/taxonomy.json
```

See [`docs/taxonomy-and-annotation.md`](docs/taxonomy-and-annotation.md) for boundaries and review guidance.

## Research integrity and release warning

- Sampling observations come from recorded configuration objects; no unrecorded parameter is inferred.
- The two model identifiers, their wrapper aliases, and seed values are preserved separately.
- `usage_source` varies between runs; token counts from different sources are not automatically comparable.
- Most prompts/settings are not a balanced experimental design. The observed correlations support questions, not causal conclusions.
- Some supplied prompts contain sensitive-looking personal, financial, medical, or distressing material. The site masks common patterns, but that cannot guarantee privacy. **The raw exports and full canonical corpus are still present in this repository. Review authorization, source-data rights, and sensitive content before making the repository or Pages site public.** No data license or consent statement was supplied, so this project does not assert blanket reuse permission.

## Continuous integration and GitHub Pages

[`.github/workflows/archive.yml`](.github/workflows/archive.yml) runs the automated tests, rebuilds a temporary corpus from the raw exports, validates annotation references, exercises the public projection, and prints corpus statistics. On pushes to `main`, it rebuilds the canonical corpus and redacted site payload, then deploys `docs/` to GitHub Pages.

To publish, enable **Settings → Pages → Build and deployment → GitHub Actions**. After merge to `main`, the workflow publishes the Atlas. Review the release warning above before enabling public access.
