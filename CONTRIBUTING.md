# Contributing research material

## Adding a Workbench export

1. Add the original `.jsonl` file anywhere under the repository. Do not rewrite, reformat, or rename a supplied source export. The ingestion command discovers `.jsonl` files recursively.
2. Rebuild and validate the canonical dataset:

   ```sh
   python -m anomaly_archive ingest . --source-root . --output data/normalized/corpus.json
   python -m anomaly_archive validate data/normalized/corpus.json \
     --annotations docs/data/annotations.json \
     --taxonomy docs/data/taxonomy.json
   ```

3. Review the deduplication report. If an original run ID has conflicting versions, inspect every source appearance and document the resolution. Do not resolve a conflict by completion-text similarity.
4. Rebuild the public projection and review the privacy notice and masked text:

   ```sh
   python -m anomaly_archive publish
   ```

5. Add or update a research notebook for each new Workbench experiment ID. Mark hypotheses as prospective or post-hoc unless the raw protocol actually records them.
6. Run `python -m unittest discover -s tests -v` before submitting.

The ingestion pipeline preserves the source artifacts and excludes administrative `api_key_id` values from normalized generations. Do not add secrets, credentials, private logs, or unsupported claims to generated documentation.

## Adding annotations

Use the Atlas annotation form or edit `docs/data/annotations.json`. An annotation needs a unique `annotation_id`, a stable `generation_id`, one or more taxonomy IDs, annotator identity, rationale, and provenance. Cite exact short excerpts; keep evidence and interpretation separate. Validate references and labels before submitting.

The current seed annotations are AI-assisted and unreviewed. A reviewed annotation should record who reviewed it, how, and when; do not silently change an unreviewed record into a reviewed one.

## Research and privacy review

- Keep completed and cancelled status distinct; do not discard partial generations from the corpus.
- Do not infer defaults for absent sampling parameters or compare token counts without considering `usage_source`.
- The public Atlas projection is not a privacy guarantee. The canonical corpus and raw exports may contain sensitive or distressing text. Confirm rights and review both source and public views before enabling or updating public Pages.
- The repository has no supplied data license or consent statement. Do not add a blanket reuse license without authority.
