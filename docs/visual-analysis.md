# Visual analysis / methods & interpretation

[← Research dashboard](../README.md#visual-research-dashboard) · [Aggregate values](figures/summary.json) · [Corpus synthesis](corpus-analysis.md)

## Scope and provenance

The figures use `data/normalized/corpus.json`, not filenames, raw row counts, public/redacted text, or manually assigned anomaly labels. The unit is the **unique generation ID**. The checked-in snapshot has 135 generations from two experiments and three source exports. New raw exports do not enter these figures until the canonical corpus is explicitly rebuilt. In particular, the later `2026-10-31_the-heavens-were-sponsored.jsonl` is not represented in this snapshot.

No raw prompts, completions, token strings, run IDs, or personal identifiers are embedded in the figures or aggregate JSON. Figures do not change or replace the archive's privacy warning.

## Visual grammar

- **Cyan:** `arcee-ai/Trinity-Large-TrueBase`.
- **Violet:** `meta-llama/Llama-3.1-8B`.
- **Green / amber:** completed / cancelled status only.
- Every chart also uses explicit text labels; color is not the only way to read it.
- Heatmap opacity is linear in count, using one global maximum. Counts, including zeros, are printed in cells.
- Scatterplot axes are linear. Coincident points overlap; use aggregate JSON for exact distribution values.

## Panels and denominators

| Panel | Inclusion | Interpretation |
|:--|:--|:--|
| Model coverage | All 135 generations | Counts of recorded statuses; cancellation is not a quality assessment |
| Sampling matrix | All 135 generations | Counts by model and temperature; missing values get their own column |
| Lexical landscape | Completed texts with ≥3 word tokens: Trinity 42, Llama 66 | One point per generation; 25 cancelled runs and 2 empty completed texts excluded |
| Linguistic fingerprints | Same 108 texts | Per-model distributions, not pooled token-weighted statistics |

Temperature bins are `<0.1`, `[0.1,1)`, exactly `1`, `(1,2]`, and `>2`, plus missing. Very small recorded positive temperatures are not silently replaced with zero.

## Linguistic measurements

All text is case-folded, then split with Python's Unicode `re.findall(r'\b\w+\b', text)`. These are **word-form heuristics**, not the models' tokenizers. Underscores and digits can be part of a word; apostrophes split words. No stemming, stopword removal, or semantic inference is performed.

1. **Type-token ratio (TTR)** = number of distinct completion word forms / completion word count. Strongly length-sensitive; a short fragment can score 1.0 without being meaningful.
2. **Repeated trigram fraction** = `1 − unique contiguous word trigrams / all contiguous word trigrams`. Overlapping trigrams count. This measures reuse, not grammaticality or pathological behavior; fewer than three words yields no value.
3. **Prompt-word overlap** = fraction of completion word positions whose form appears anywhere in the prompt. Repeated completion words each contribute. This measures vocabulary overlap, not copied spans or semantic entailment.

Distribution lines span minimum to maximum. Boxes span nearest-rank Q1 to Q3 (`ceil(p*n)-1`, zero-based), and dots show the ordinary sample median. Collapsed boxes are drawn at least one pixel wide for visibility. Each run has equal weight. These descriptive summaries have no confidence intervals or significance claims.

## What the figures cannot establish

The models were not sampled under balanced controls. Prompts, seeds, completion lengths, sampling filters, penalties and cancellation behavior differ. Aggregate differences cannot be attributed to model identity or temperature. Excluding cancelled runs introduces selection effects; those runs can contain partial text but are deliberately excluded from linguistic comparisons. Repetition can be induced by the prompt. Reported token usage and logprob availability vary, so these figures do not estimate comparable perplexity or full-vocabulary entropy. Taxonomy annotations are sparse and unreviewed, so no anomaly-prevalence chart is inferred from them.

## Reproduce and update

From the repository root, with Python 3.10+ and no third-party packages:

```sh
python -m anomaly_archive.visualize
python -m unittest discover -s tests -v
```

The generator writes four standalone SVGs and `summary.json` to `docs/figures/`. Output is deterministic (no wall-clock timestamps). To inspect another snapshot without overwriting the checked-in figures:

```sh
python -m anomaly_archive.visualize --corpus path/to/corpus.json --output /tmp/archive-figures
```

When updating the canonical corpus, regenerate figures and review README counts and interpretations in the same change. CI checks that checked-in figures match the checked-in corpus; it does not silently substitute a newer raw-data snapshot.
