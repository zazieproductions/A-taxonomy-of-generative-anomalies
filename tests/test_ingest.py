from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from anomaly_archive.ingest import IngestError, ingest_exports


def make_run(
    run_id: str = "run-001",
    *,
    status: str = "completed",
    completion: str = "A small moon in the archive.",
    temperature: float | None = 0.8,
    updated_marker: str | None = None,
) -> dict:
    config = {
        "model": "provider/model-alpha",
        "wrapper_model_id": "alpha",
        "prompt": "Write one sentence.",
        "temperature": temperature,
        "top_p": 0.9,
        "top_k": -1,
        "seed": 11,
        "seed_mode": "random",
        "presence_penalty": 0.0,
        "frequency_penalty": 0.0,
        "repetition_penalty": 1.0,
        "max_tokens": 40,
        "stream": True,
        "logprobs": 2,
    }
    result = {
        "id": run_id,
        "compare_run_id": None,
        "status": status,
        "finalized": True,
        "started_at": "2026-10-30T12:00:00+00:00",
        "ended_at": "2026-10-30T12:00:01+00:00",
        "model": "alpha",
        "prompt_before": "Write one sentence.",
        "completion_text": completion,
        "generation_config": config,
        "logprobs": [
            {"token": "A", "logprob": -0.25, "top": [{"token": "A", "logprob": -0.25}]}
        ],
        "error_message": None,
        "n_prompt_tokens": 4,
        "n_completion_tokens": 6,
        "finish_reason": "length" if status == "completed" else None,
        "stop_reason": None,
        "usage_source": "upstream",
    }
    if updated_marker is not None:
        result["marker"] = updated_marker
    return result


def make_export(
    runs: list[dict],
    *,
    experiment_id: str = "experiment-001",
    updated_at: str = "2026-10-30T12:10:00+00:00",
) -> dict:
    return {
        "schema_version": 2,
        "id": experiment_id,
        "title": "A fixture experiment",
        "last_mode": "single",
        "created_at": "2026-10-30T11:00:00+00:00",
        "updated_at": updated_at,
        "last_generation_config": {},
        "runs": runs,
        "snapshots": [],
        "compare_snapshots": [],
    }


def write_jsonl(path: Path, value: object, *, pretty: bool = False) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2 if pretty else None) + "\n",
        encoding="utf-8",
    )


class IngestTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def ingest_all(self) -> dict:
        return ingest_exports([self.root], root=self.root)

    def test_single_json_object_in_jsonl_and_schema_fields(self) -> None:
        run = make_run()
        source = self.root / "workbench-export.jsonl"
        write_jsonl(source, make_export([run]), pretty=True)

        corpus = self.ingest_all()
        self.assertEqual(corpus["deduplication"]["source_run_rows"], 1)
        self.assertEqual(corpus["deduplication"]["unique_generation_count"], 1)
        generation = corpus["generations"][0]
        self.assertEqual(generation["generation_id"], "run-001")
        self.assertEqual(generation["model_identifier"], "provider/model-alpha")
        self.assertEqual(generation["wrapper_model_id"], "alpha")
        self.assertEqual(generation["prompt"], "Write one sentence.")
        self.assertEqual(generation["completion"], run["completion_text"])
        self.assertEqual(generation["sampling"]["temperature"], 0.8)
        self.assertEqual(generation["sampling"]["top_p"], 0.9)
        self.assertEqual(generation["tokens"]["prompt"], 4)
        self.assertEqual(generation["tokens"]["completion"], 6)
        self.assertEqual(generation["logprobs"][0]["top"][0]["token"], "A")
        self.assertEqual(generation["source_provenance"][0]["source_file"], source.name)
        self.assertEqual(len(corpus["source_exports"][0]["source_sha256"]), 64)

    def test_successive_exports_deduplicate_by_original_run_id(self) -> None:
        shared = make_run("stable-id")
        earlier = self.root / "earlier.jsonl"
        later = self.root / "later.jsonl"
        write_jsonl(earlier, make_export([shared], updated_at="2026-10-30T12:10:00+00:00"))
        write_jsonl(
            later,
            make_export(
                [shared, make_run("new-run")],
                updated_at="2026-10-30T12:20:00+00:00",
            ),
        )

        corpus = self.ingest_all()
        self.assertEqual(corpus["deduplication"]["source_run_rows"], 3)
        self.assertEqual(corpus["deduplication"]["unique_generation_count"], 2)
        self.assertEqual(corpus["deduplication"]["duplicate_rows_removed"], 1)
        stable = next(g for g in corpus["generations"] if g["generation_id"] == "stable-id")
        self.assertEqual(len(stable["source_provenance"]), 2)
        self.assertEqual(
            {p["source_file"] for p in stable["source_provenance"]},
            {"earlier.jsonl", "later.jsonl"},
        )
        self.assertEqual(corpus["deduplication"]["conflicts"], [])

    def test_conflicting_duplicate_keeps_latest_export_and_audits_conflict(self) -> None:
        first = make_run("stable-id", completion="earlier text")
        second = make_run("stable-id", completion="later text", updated_marker="richer")
        write_jsonl(
            self.root / "a.jsonl",
            make_export([first], updated_at="2026-10-30T12:10:00+00:00"),
        )
        write_jsonl(
            self.root / "b.jsonl",
            make_export([second], updated_at="2026-10-30T12:20:00+00:00"),
        )

        corpus = self.ingest_all()
        self.assertEqual(len(corpus["generations"]), 1)
        self.assertEqual(corpus["generations"][0]["completion"], "later text")
        self.assertEqual(len(corpus["deduplication"]["conflicts"]), 1)
        conflict = corpus["deduplication"]["conflicts"][0]
        self.assertIn("completion_text", conflict["differing_source_fields"])
        self.assertEqual(conflict["selected_source_file"], "b.jsonl")
        self.assertEqual(len(corpus["generations"][0]["source_provenance"]), 2)

    def test_cancelled_partial_is_not_relabelled_as_completed(self) -> None:
        cancelled = make_run("partial", status="cancelled", completion="A partial fragment")
        cancelled["n_completion_tokens"] = 3
        cancelled["finish_reason"] = None
        write_jsonl(self.root / "cancelled.jsonl", make_export([cancelled]))

        generation = self.ingest_all()["generations"][0]
        self.assertEqual(generation["status"], "cancelled")
        self.assertEqual(generation["completion"], "A partial fragment")
        self.assertIsNone(generation["finish_reason"])
        self.assertEqual(generation["tokens"]["completion"], 3)

    def test_unrecorded_sampling_fields_are_not_filled_in(self) -> None:
        run = make_run("sparse")
        del run["generation_config"]["top_p"]
        run["generation_config"].pop("temperature")
        write_jsonl(self.root / "sparse.jsonl", make_export([run]))

        generation = self.ingest_all()["generations"][0]
        self.assertNotIn("top_p", generation["sampling"])
        self.assertNotIn("temperature", generation["sampling"])
        self.assertNotIn("top_p", generation["generation_config"])

    def test_absent_source_keys_are_explicitly_distinguished_from_null(self) -> None:
        run = make_run("absent-fields")
        run.pop("generation_config")
        run.pop("logprobs")
        run["completion_text"] = ""
        write_jsonl(self.root / "absent.jsonl", make_export([run]))
        generation = self.ingest_all()["generations"][0]
        self.assertEqual(generation["generation_config"], {})
        self.assertFalse(generation["source_field_presence"]["generation_config"])
        self.assertFalse(generation["source_field_presence"]["logprobs"])
        self.assertTrue(generation["source_field_presence"]["completion_text"])
        self.assertEqual(generation["completion"], "")
        self.assertIsNone(generation["logprobs"])

    def test_conventional_jsonl_lines_are_supported(self) -> None:
        first = make_run("line-1")
        second = make_run("line-2", status="cancelled")
        path = self.root / "lines.jsonl"
        path.write_text(
            json.dumps(make_export([first])) + "\n" + json.dumps(make_export([second])) + "\n",
            encoding="utf-8",
        )
        corpus = self.ingest_all()
        self.assertEqual(len(corpus["generations"]), 2)
        self.assertEqual(
            {g["status"] for g in corpus["generations"]}, {"completed", "cancelled"}
        )
        self.assertEqual(len(corpus["source_exports"]), 2)
        self.assertEqual(
            {p["object_index"] for g in corpus["generations"] for p in g["source_provenance"]},
            {0, 1},
        )

    def test_same_completion_with_distinct_ids_is_not_content_deduplicated(self) -> None:
        run_a = make_run("id-a", completion="same text")
        run_b = make_run("id-b", completion="same text")
        write_jsonl(self.root / "different-ids.jsonl", make_export([run_a, run_b]))
        corpus = self.ingest_all()
        self.assertEqual(len(corpus["generations"]), 2)
        self.assertEqual(corpus["deduplication"]["duplicate_rows_removed"], 0)

    def test_missing_stable_id_fails_loudly(self) -> None:
        run = make_run()
        del run["id"]
        write_jsonl(self.root / "missing-id.jsonl", make_export([run]))
        with self.assertRaisesRegex(IngestError, "no stable string 'id'"):
            self.ingest_all()

    def test_invalid_jsonl_fails_with_location(self) -> None:
        (self.root / "broken.jsonl").write_text('{"runs": [}\n', encoding="utf-8")
        with self.assertRaisesRegex(IngestError, "physical line 1"):
            self.ingest_all()


if __name__ == "__main__":
    unittest.main()
