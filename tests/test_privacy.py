from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from anomaly_archive.ingest import ingest_exports
from anomaly_archive.privacy import build_public_atlas, redact_sensitive_text
from test_ingest import make_export, make_run, write_jsonl


class PrivacyProjectionTests(unittest.TestCase):
    def test_structured_identifier_patterns_are_masked_without_rewriting_source(self) -> None:
        original = "SSN 123-45-6789; card 4242 4242 4242 4242; address 4.3.2.1"
        masked, families = redact_sensitive_text(original)
        self.assertNotIn("123-45-6789", masked)
        self.assertNotIn("4242 4242 4242 4242", masked)
        self.assertNotIn("4.3.2.1", masked)
        self.assertEqual(
            set(families), {"ssn_like", "payment_card_like", "ipv4_like"}
        )
        self.assertEqual(original.count("REDACTED"), 0)

    def test_labelled_and_self_declared_personal_fields_are_masked(self) -> None:
        original = "Your full name: Example Person\nMy name is Another Person, then the story continues."
        masked, families = redact_sensitive_text(original)
        self.assertNotIn("Example Person", masked)
        self.assertNotIn("Another Person", masked)
        self.assertIn("the story continues", masked)
        self.assertIn("labelled_personal_field", families)
        self.assertIn("self_declared_name", families)
        masked_again, repeat_families = redact_sensitive_text(masked)
        self.assertEqual(masked_again, masked)
        self.assertEqual(repeat_families, [])

    def test_public_projection_masks_text_and_suppresses_token_logprobs(self) -> None:
        run = make_run("private-fixture")
        run["prompt_before"] = "A note: 123-45-6789 from 4.3.2.1\nYour full name: Example Person\nAddress: 42 Example Lane"
        run["generation_config"]["prompt"] = run["prompt_before"]
        run["completion_text"] = "Card 4242 4242 4242 4242; the moon is green."
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "source.jsonl"
            write_jsonl(path, make_export([run]))
            canonical = ingest_exports([directory], root=directory)

        public = build_public_atlas(canonical)
        normalized = canonical["generations"][0]
        displayed = public["generations"][0]
        self.assertIn("123-45-6789", normalized["prompt"])
        self.assertIn("4242 4242 4242 4242", normalized["completion"])
        serialized = json.dumps(public, ensure_ascii=False)
        self.assertNotIn("123-45-6789", serialized)
        self.assertNotIn("4242 4242 4242 4242", serialized)
        self.assertNotIn("4.3.2.1", serialized)
        self.assertNotIn("Example Person", serialized)
        self.assertNotIn("42 Example Lane", serialized)
        self.assertIn("REDACTED STRUCTURED VALUE", displayed["prompt"])
        self.assertIsNone(displayed["logprobs"])
        self.assertTrue(displayed["logprobs_suppressed_for_privacy"])
        self.assertTrue(public["privacy_projection"]["canonical_corpus_is_unmodified"])

    def test_unmasked_record_keeps_available_logprobs(self) -> None:
        run = make_run("clean-fixture")
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "source.jsonl"
            write_jsonl(path, make_export([run]))
            canonical = ingest_exports([directory], root=directory)
        public = build_public_atlas(canonical)
        self.assertEqual(public["generations"][0]["logprobs"], run["logprobs"])
        self.assertFalse(public["generations"][0]["logprobs_suppressed_for_privacy"])

    def test_comparison_group_uses_exact_prompt_and_settings_before_masking(self) -> None:
        alpha = make_run("alpha-run")
        beta = make_run("beta-run")
        alpha["generation_config"]["seed"] = 101
        beta["generation_config"]["seed"] = 202
        beta["generation_config"]["model"] = "provider/model-beta"
        beta["generation_config"]["wrapper_model_id"] = "beta"
        beta["model"] = "beta"
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "source.jsonl"
            write_jsonl(path, make_export([alpha, beta]))
            canonical = ingest_exports([directory], root=directory)
        public = build_public_atlas(canonical)
        self.assertEqual(public["privacy_projection"]["comparison_group_count"], 1)
        self.assertEqual(
            {run["comparison_group_id"] for run in public["generations"]}, {"pair-01"}
        )


if __name__ == "__main__":
    unittest.main()
