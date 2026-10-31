from __future__ import annotations

import unittest

from anomaly_archive.schema import validate_annotations, validate_corpus
from test_ingest import make_export, make_run
from anomaly_archive.ingest import ingest_exports
from pathlib import Path
import tempfile
import json


class SchemaTests(unittest.TestCase):
    def test_valid_minimal_corpus_passes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "source.jsonl"
            path.write_text(
                json.dumps(make_export([make_run()]), ensure_ascii=False), encoding="utf-8"
            )
            corpus = ingest_exports([directory], root=directory)
        self.assertEqual(validate_corpus(corpus), [])

    def test_invalid_duplicate_ids_and_bad_token_counts_are_reported(self) -> None:
        bad = {
            "schema_version": 1,
            "record_type": "acs-workbench-corpus",
            "source_exports": [],
            "experiments": [],
            "generations": [
                {
                    "generation_id": "duplicate",
                    "experiment_id": None,
                    "experiment_title": None,
                    "model": "m",
                    "model_identifier": None,
                    "wrapper_model_id": None,
                    "prompt": "p",
                    "configured_prompt": None,
                    "completion": "c",
                    "status": "completed",
                    "finalized": True,
                    "timestamps": {"started_at": None, "ended_at": None},
                    "tokens": {"prompt": -1, "completion": None, "source": None},
                    "sampling": {},
                    "generation_config": {},
                    "logprobs": None,
                    "finish_reason": None,
                    "stop_reason": None,
                    "error_message": None,
                    "comparison_run_id": None,
                    "source_provenance": [],
                },
                {
                    "generation_id": "duplicate",
                    "experiment_id": None,
                    "experiment_title": None,
                    "model": "m",
                    "model_identifier": None,
                    "wrapper_model_id": None,
                    "prompt": "p",
                    "configured_prompt": None,
                    "completion": "c",
                    "status": "completed",
                    "finalized": True,
                    "timestamps": {"started_at": None, "ended_at": None},
                    "tokens": {"prompt": None, "completion": None, "source": None},
                    "sampling": {},
                    "generation_config": {},
                    "logprobs": None,
                    "finish_reason": None,
                    "stop_reason": None,
                    "error_message": None,
                    "comparison_run_id": None,
                    "source_provenance": [],
                },
            ],
            "deduplication": {
                "key": "generation_id",
                "source_run_rows": 3,
                "unique_generation_count": 2,
                "duplicate_rows_removed": 0,
                "duplicate_generation_ids": [],
                "conflicts": [],
                "history_policy": "",
            },
        }
        errors = validate_corpus(bad)
        self.assertTrue(any("generation_id is duplicated" in error for error in errors))
        self.assertTrue(any("tokens.prompt" in error for error in errors))
        self.assertTrue(any("source_provenance" in error for error in errors))
        self.assertTrue(any("counts do not balance" in error for error in errors))

    def test_annotation_schema_allows_multiple_labels_and_checks_provenance(self) -> None:
        bundle = {
            "schema_version": 1,
            "taxonomy_version": "1.0.0",
            "annotations": [
                {
                    "annotation_id": "ann-1",
                    "generation_id": "run-1",
                    "labels": ["recursive_degeneration", "lexical_disintegration"],
                    "annotator": "reviewer-01",
                    "rationale": "Repeated forms dominate the recorded continuation.",
                    "evidence": [{"quote": "same same"}],
                    "confidence": 0.8,
                    "provenance": {
                        "method": "manual",
                        "created_at": "2026-10-30T12:00:00Z",
                        "status": "reviewed",
                    },
                }
            ],
        }
        self.assertEqual(
            validate_annotations(
                bundle,
                generation_ids={"run-1"},
                taxonomy_ids={"recursive_degeneration", "lexical_disintegration"},
            ),
            [],
        )

    def test_annotation_unknown_label_and_generation_are_reported(self) -> None:
        bundle = {
            "schema_version": 1,
            "taxonomy_version": "1.0.0",
            "annotations": [
                {
                    "annotation_id": "ann-1",
                    "generation_id": "missing",
                    "labels": ["not-a-label"],
                    "annotator": "reviewer",
                    "rationale": "A reason.",
                    "provenance": {
                        "method": "manual",
                        "created_at": "2026-10-30",
                        "status": "reviewed",
                    },
                }
            ],
        }
        errors = validate_annotations(
            bundle,
            generation_ids={"run-1"},
            taxonomy_ids={"recursive_degeneration"},
        )
        self.assertTrue(any("does not exist" in error for error in errors))
        self.assertTrue(any("unknown taxonomy id" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
