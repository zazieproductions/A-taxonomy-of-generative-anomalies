# Working taxonomy and manual annotation protocol

The taxonomy is a coding vocabulary for textual observations, not a model-quality scale. Terms can co-occur. Annotators should prefer a short evidence-based rationale over an explanation of why a sampler or model produced a result.

## Terms

The machine-readable source of truth, including operational cues and exclusion cases, is [`docs/data/taxonomy.json`](./data/taxonomy.json).

| ID | Label | Working distinction |
|---|---|---|
| `conceptual_surrealism` | Conceptual surrealism | A legible impossible world-rule or image is sustained. The sentences can be coherent while time, identity, causality, or scale is rearranged. |
| `semantic_absurdism` | Semantic absurdism | Clauses may be fluent, but their relations, referents, or propositions remain unstable or incompatible. |
| `genre_capture` | Genre capture | A recognizable discourse form (product copy, report, listicle, news digest, etc.) takes over the continuation, possibly against the prompt's frame. |
| `documentary_normalization` | Documentary normalization | Ambiguity or invention is made to sound like ordinary catalog, explainer, policy, news, or institutional prose. The label is about register, not truth. |
| `rhetorical_amplification` | Rhetorical amplification | The completion observably increases the prompt's emotional intensity, certainty, urgency, scale, or repeated emphasis. |
| `recursive_degeneration` | Recursive degeneration | Prompt/output material or a procedural pattern visibly echoes itself while adding little new information. This describes text, not an inferred decoding loop. |
| `lexical_disintegration` | Lexical disintegration | Fused or malformed word-like forms, script/punctuation collisions, or fragments make ordinary lexical parsing difficult. Multilingual text alone is not enough. |

### Boundary questions

- **Surrealism vs. absurdism:** Can a reader state a coherent impossible rule that organizes the passage? If yes, conceptual surrealism may fit. If meaning relations themselves fail to settle, semantic absurdism may also fit.
- **Genre vs. documentary normalization:** Is the principal evidence the adopted form (genre capture), the factual-sounding normalization of an underspecified premise (documentary normalization), or both?
- **Rhetorical amplification vs. recursive degeneration:** Does repetition intensify a stance, or does it mainly repeat material with little change? Both labels are possible when both observations are supported.
- **Lexical disintegration vs. novelty:** A rare, invented, or multilingual word can remain meaningful. Use lexical disintegration only when segmentation/recoverability is visibly impaired.

## Annotation record

Annotation data live separately from generations. Version 1 is a JSON bundle with one or more annotation records:

```json
{
  "annotation_id": "stable-annotation-id",
  "generation_id": "original-workbench-run-id",
  "labels": ["conceptual_surrealism", "semantic_absurdism"],
  "annotator": "name or pseudonymous reviewer ID",
  "rationale": "A concise statement of observable evidence and boundary reasoning.",
  "evidence": [{"quote": "exact short excerpt from the source text"}],
  "provenance": {
    "method": "manual",
    "created_at": "2026-10-30T20:00:00Z",
    "status": "unreviewed",
    "source": "annotation session or project",
    "tool": "optional tool identifier"
  }
}
```

Rules:

1. `generation_id` must refer to a canonical corpus generation.
2. `labels` is a non-empty array; multiple distinct taxonomy IDs are allowed.
3. Every record has an annotator, rationale, method, creation date/time, and review status. Use an ISO 8601 timestamp when the time is known; when only the calendar date was captured, keep date-only precision rather than inventing a time.
4. Evidence excerpts should be exact. Offsets are optional because Unicode normalization and display masking can change how a browser renders text.
5. Do not label a generation as completed because it reads fluently; retain its recorded `status`.
6. Separate observation from interpretation. A setting/value correlation is not a causal explanation unless the experiment controls support it.
7. Do not treat a low type-token ratio or logprob as an anomaly label by itself; name the text evidence and method.

## Atlas annotation workflow

1. Open a specimen and read its recorded prompt, completion, settings, status, and provenance.
2. Select any number of taxonomy terms. Add an annotator ID and rationale; include a short evidence quote if useful.
3. **Save in this browser** writes to local storage only. Nothing is sent to a server, and it does not alter repository files.
4. Choose **Export annotations** to download a bundle containing the checked-in annotations plus this browser's local annotations. Review the content and provenance. Either replace `docs/data/annotations.json` with the reviewed bundle or merge only newly accepted records by `annotation_id`; do not append the entire export to the existing file.
5. Validate against both the corpus and the taxonomy:

   ```sh
   python -m anomaly_archive validate data/normalized/corpus.json \
     --annotations docs/data/annotations.json \
     --taxonomy docs/data/taxonomy.json
   ```

6. Commit the reviewed annotation bundle with any changes. The static site rebuild will show the resulting labels.

The shipped annotations are an initial **AI-assisted, unreviewed editorial pass** over eight curated examples. They demonstrate multi-label records and provenance, but are not human-adjudicated, inter-annotator-tested, or suitable as gold labels without review.
