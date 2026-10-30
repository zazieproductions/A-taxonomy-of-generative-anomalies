"""Dependency-free validators for corpus and annotation interchange files."""

from __future__ import annotations

import re
from typing import Any

_HEX_64 = re.compile(r"^[a-f0-9]{64}$")


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _check_string_or_none(value: Any, path: str, errors: list[str]) -> None:
    if value is not None and not isinstance(value, str):
        errors.append(f"{path} must be a string or null")


def validate_corpus(corpus: Any) -> list[str]:
    """Return all structural/data-integrity errors found in a corpus-v1 object."""
    errors: list[str] = []
    if not isinstance(corpus, dict):
        return ["$ must be a JSON object"]
    for field in ("schema_version", "record_type", "source_exports", "experiments", "generations", "deduplication"):
        if field not in corpus:
            errors.append(f"{field} is required")
    if corpus.get("schema_version") != 1:
        errors.append("schema_version must equal 1")
    if corpus.get("record_type") != "acs-workbench-corpus":
        errors.append("record_type must be 'acs-workbench-corpus'")

    for name in ("source_exports", "experiments", "generations"):
        if not isinstance(corpus.get(name), list):
            errors.append(f"{name} must be an array")
    if not isinstance(corpus.get("deduplication"), dict):
        errors.append("deduplication must be an object")

    exports = corpus.get("source_exports")
    if isinstance(exports, list):
        for index, item in enumerate(exports):
            path = f"source_exports[{index}]"
            if not isinstance(item, dict):
                errors.append(f"{path} must be an object")
                continue
            for field in ("source_file", "source_sha256"):
                if not isinstance(item.get(field), str) or not item[field]:
                    errors.append(f"{path}.{field} must be a non-empty string")
            if isinstance(item.get("source_sha256"), str) and not _HEX_64.fullmatch(
                item["source_sha256"]
            ):
                errors.append(f"{path}.source_sha256 must be a lowercase SHA-256 hex digest")
            for field in ("bytes", "object_index", "run_rows_in_export"):
                value = item.get(field)
                if not isinstance(value, int) or isinstance(value, bool) or value < 0:
                    errors.append(f"{path}.{field} must be a non-negative integer")
            for field in ("experiment_id", "title", "created_at", "updated_at", "last_mode"):
                _check_string_or_none(item.get(field), f"{path}.{field}", errors)
            for field in ("snapshots_in_export", "compare_snapshots_in_export"):
                value = item.get(field)
                if value is not None and (
                    not isinstance(value, int) or isinstance(value, bool) or value < 0
                ):
                    errors.append(f"{path}.{field} must be a non-negative integer or null")

    experiments = corpus.get("experiments")
    experiment_ids: set[str] = set()
    if isinstance(experiments, list):
        for index, item in enumerate(experiments):
            path = f"experiments[{index}]"
            if not isinstance(item, dict):
                errors.append(f"{path} must be an object")
                continue
            for field in ("experiment_id", "title", "source_files", "metadata_versions"):
                if field not in item:
                    errors.append(f"{path}.{field} is required")
            experiment_id = item.get("experiment_id")
            if not isinstance(experiment_id, str) or not experiment_id:
                errors.append(f"{path}.experiment_id must be a non-empty string")
            elif experiment_id in experiment_ids:
                errors.append(f"{path}.experiment_id is duplicated: {experiment_id}")
            else:
                experiment_ids.add(experiment_id)
            _check_string_or_none(item.get("title"), f"{path}.title", errors)
            source_files = item.get("source_files")
            if not isinstance(source_files, list) or any(not isinstance(value, str) for value in source_files):
                errors.append(f"{path}.source_files must be an array of strings")
            versions = item.get("metadata_versions")
            if not isinstance(versions, list):
                errors.append(f"{path}.metadata_versions must be an array")
            else:
                for version_index, version in enumerate(versions):
                    version_path = f"{path}.metadata_versions[{version_index}]"
                    if not isinstance(version, dict):
                        errors.append(f"{version_path} must be an object")
                        continue
                    if not isinstance(version.get("source_file"), str):
                        errors.append(f"{version_path}.source_file must be a string")
                    digest = version.get("source_sha256")
                    if not isinstance(digest, str) or not _HEX_64.fullmatch(digest):
                        errors.append(f"{version_path}.source_sha256 must be a SHA-256 digest")
                    if not isinstance(version.get("metadata"), dict):
                        errors.append(f"{version_path}.metadata must be an object")

    generations = corpus.get("generations")
    generation_ids: set[str] = set()
    if isinstance(generations, list):
        for index, item in enumerate(generations):
            path = f"generations[{index}]"
            if not isinstance(item, dict):
                errors.append(f"{path} must be an object")
                continue
            required_generation_fields = (
                "generation_id", "experiment_id", "experiment_title", "model",
                "model_identifier", "wrapper_model_id", "prompt", "configured_prompt",
                "completion", "status", "finalized", "source_field_presence", "timestamps", "tokens", "sampling",
                "generation_config", "logprobs", "finish_reason", "stop_reason",
                "error_message", "comparison_run_id", "source_provenance",
            )
            for field in required_generation_fields:
                if field not in item:
                    errors.append(f"{path}.{field} is required")
            generation_id = item.get("generation_id")
            if not isinstance(generation_id, str) or not generation_id:
                errors.append(f"{path}.generation_id must be a non-empty string")
            elif generation_id in generation_ids:
                errors.append(f"{path}.generation_id is duplicated: {generation_id}")
            else:
                generation_ids.add(generation_id)

            for field in (
                "model",
                "model_identifier",
                "wrapper_model_id",
                "prompt",
                "configured_prompt",
                "completion",
                "status",
                "finish_reason",
                "stop_reason",
                "error_message",
                "comparison_run_id",
            ):
                _check_string_or_none(item.get(field), f"{path}.{field}", errors)
            if item.get("experiment_id") is not None and not isinstance(
                item.get("experiment_id"), str
            ):
                errors.append(f"{path}.experiment_id must be a string or null")
            if item.get("experiment_title") is not None and not isinstance(
                item.get("experiment_title"), str
            ):
                errors.append(f"{path}.experiment_title must be a string or null")
            if item.get("finalized") is not None and not isinstance(item.get("finalized"), bool):
                errors.append(f"{path}.finalized must be a boolean or null")
            presence = item.get("source_field_presence")
            if not isinstance(presence, dict) or any(not isinstance(value, bool) for value in presence.values()):
                errors.append(f"{path}.source_field_presence must be an object of booleans")

            timestamps = item.get("timestamps")
            if not isinstance(timestamps, dict):
                errors.append(f"{path}.timestamps must be an object")
            else:
                for field in ("started_at", "ended_at"):
                    if field not in timestamps:
                        errors.append(f"{path}.timestamps.{field} is required")
                    _check_string_or_none(timestamps.get(field), f"{path}.timestamps.{field}", errors)

            tokens = item.get("tokens")
            if not isinstance(tokens, dict):
                errors.append(f"{path}.tokens must be an object")
            else:
                for field in ("prompt", "completion", "source"):
                    if field not in tokens:
                        errors.append(f"{path}.tokens.{field} is required")
                for field in ("prompt", "completion"):
                    value = tokens.get(field)
                    if value is not None and (
                        not isinstance(value, int) or isinstance(value, bool) or value < 0
                    ):
                        errors.append(f"{path}.tokens.{field} must be a non-negative integer or null")
                _check_string_or_none(tokens.get("source"), f"{path}.tokens.source", errors)

            for field in ("sampling", "generation_config"):
                if not isinstance(item.get(field), dict):
                    errors.append(f"{path}.{field} must be an object")

            logprobs = item.get("logprobs")
            if logprobs is not None and not isinstance(logprobs, list):
                errors.append(f"{path}.logprobs must be an array or null")
            elif isinstance(logprobs, list):
                for token_index, token_data in enumerate(logprobs):
                    token_path = f"{path}.logprobs[{token_index}]"
                    if not isinstance(token_data, dict):
                        errors.append(f"{token_path} must be an object")
                        continue
                    if not isinstance(token_data.get("token"), str):
                        errors.append(f"{token_path}.token must be a string")
                    if not _is_number(token_data.get("logprob")):
                        errors.append(f"{token_path}.logprob must be a number")
                    if "top" not in token_data:
                        errors.append(f"{token_path}.top is required")
                    top = token_data.get("top")
                    if top is not None and not isinstance(top, list):
                        errors.append(f"{token_path}.top must be an array or null")
                    elif isinstance(top, list):
                        for candidate_index, candidate in enumerate(top):
                            candidate_path = f"{token_path}.top[{candidate_index}]"
                            if not isinstance(candidate, dict):
                                errors.append(f"{candidate_path} must be an object")
                                continue
                            if not isinstance(candidate.get("token"), str):
                                errors.append(f"{candidate_path}.token must be a string")
                            if not _is_number(candidate.get("logprob")):
                                errors.append(f"{candidate_path}.logprob must be a number")

            provenance = item.get("source_provenance")
            if not isinstance(provenance, list) or not provenance:
                errors.append(f"{path}.source_provenance must be a non-empty array")
            else:
                for prov_index, prov in enumerate(provenance):
                    prov_path = f"{path}.source_provenance[{prov_index}]"
                    if not isinstance(prov, dict):
                        errors.append(f"{prov_path} must be an object")
                        continue
                    for field in ("source_file", "source_sha256", "source_record_sha256"):
                        if not isinstance(prov.get(field), str) or not prov[field]:
                            errors.append(f"{prov_path}.{field} must be a non-empty string")
                    for field in ("source_sha256", "source_record_sha256"):
                        value = prov.get(field)
                        if isinstance(value, str) and not _HEX_64.fullmatch(value):
                            errors.append(f"{prov_path}.{field} must be a lowercase SHA-256 digest")
                    for field in ("object_index", "run_index"):
                        value = prov.get(field)
                        if not isinstance(value, int) or isinstance(value, bool) or value < 0:
                            errors.append(f"{prov_path}.{field} must be a non-negative integer")
                    if prov.get("experiment_id") is not None and not isinstance(prov.get("experiment_id"), str):
                        errors.append(f"{prov_path}.experiment_id must be a string or null")
                    _check_string_or_none(prov.get("export_updated_at"), f"{prov_path}.export_updated_at", errors)

    dedup = corpus.get("deduplication")
    if isinstance(dedup, dict):
        for field in ("key", "source_run_rows", "unique_generation_count", "duplicate_rows_removed", "duplicate_generation_ids", "conflicts", "history_policy"):
            if field not in dedup:
                errors.append(f"deduplication.{field} is required")
        if not isinstance(dedup.get("key"), str):
            errors.append("deduplication.key must be a string")
        if not isinstance(dedup.get("history_policy"), str):
            errors.append("deduplication.history_policy must be a string")
        for field in ("source_run_rows", "unique_generation_count", "duplicate_rows_removed"):
            value = dedup.get(field)
            if not isinstance(value, int) or isinstance(value, bool) or value < 0:
                errors.append(f"deduplication.{field} must be a non-negative integer")
        if all(isinstance(dedup.get(key), int) for key in ("source_run_rows", "unique_generation_count", "duplicate_rows_removed")):
            if dedup["source_run_rows"] - dedup["unique_generation_count"] != dedup[
                "duplicate_rows_removed"
            ]:
                errors.append("deduplication counts do not balance")
        if not isinstance(dedup.get("duplicate_generation_ids"), list):
            errors.append("deduplication.duplicate_generation_ids must be an array")
        if not isinstance(dedup.get("conflicts"), list):
            errors.append("deduplication.conflicts must be an array")

    return errors


def validate_annotations(
    bundle: Any,
    *,
    generation_ids: set[str] | None = None,
    taxonomy_ids: set[str] | None = None,
) -> list[str]:
    """Validate annotation bundles, including references and multi-labels."""
    errors: list[str] = []
    if not isinstance(bundle, dict):
        return ["$ must be a JSON object"]
    if bundle.get("schema_version") != 1:
        errors.append("schema_version must equal 1")
    if not isinstance(bundle.get("taxonomy_version"), str) or not bundle["taxonomy_version"]:
        errors.append("taxonomy_version must be a non-empty string")
    annotations = bundle.get("annotations")
    if not isinstance(annotations, list):
        return errors + ["annotations must be an array"]
    annotation_ids: set[str] = set()
    for index, item in enumerate(annotations):
        path = f"annotations[{index}]"
        if not isinstance(item, dict):
            errors.append(f"{path} must be an object")
            continue
        for field in ("annotation_id", "generation_id", "labels", "annotator", "rationale", "provenance"):
            if field not in item:
                errors.append(f"{path}.{field} is required")
        annotation_id = item.get("annotation_id")
        if not isinstance(annotation_id, str) or not annotation_id:
            errors.append(f"{path}.annotation_id must be a non-empty string")
        elif annotation_id in annotation_ids:
            errors.append(f"{path}.annotation_id is duplicated")
        else:
            annotation_ids.add(annotation_id)
        generation_id = item.get("generation_id")
        if not isinstance(generation_id, str) or not generation_id:
            errors.append(f"{path}.generation_id must be a non-empty string")
        elif generation_ids is not None and generation_id not in generation_ids:
            errors.append(f"{path}.generation_id does not exist in the corpus")
        labels = item.get("labels")
        if not isinstance(labels, list) or not labels:
            errors.append(f"{path}.labels must be a non-empty array (multiple labels are allowed)")
        elif any(not isinstance(label, str) or not label for label in labels):
            errors.append(f"{path}.labels must contain non-empty strings")
        elif len(labels) != len(set(labels)):
            errors.append(f"{path}.labels must not contain duplicates")
        elif taxonomy_ids is not None:
            for label in labels:
                if label not in taxonomy_ids:
                    errors.append(f"{path}.labels contains unknown taxonomy id {label!r}")
        for field in ("annotator", "rationale"):
            if not isinstance(item.get(field), str) or not item[field].strip():
                errors.append(f"{path}.{field} must be a non-empty string")
        provenance = item.get("provenance")
        if not isinstance(provenance, dict):
            errors.append(f"{path}.provenance must be an object")
        else:
            for field in ("method", "created_at", "status"):
                if not isinstance(provenance.get(field), str) or not provenance[field]:
                    errors.append(f"{path}.provenance.{field} must be a non-empty string")
        confidence = item.get("confidence")
        if confidence is not None and (
            not _is_number(confidence) or confidence < 0 or confidence > 1
        ):
            errors.append(f"{path}.confidence must be a number from 0 to 1 or null")
        evidence = item.get("evidence", [])
        if not isinstance(evidence, list):
            errors.append(f"{path}.evidence must be an array")
        else:
            for evidence_index, excerpt in enumerate(evidence):
                epath = f"{path}.evidence[{evidence_index}]"
                if not isinstance(excerpt, dict) or not isinstance(excerpt.get("quote"), str):
                    errors.append(f"{epath} must be an object with a string quote")
                elif any(
                    value is not None and (not isinstance(value, int) or isinstance(value, bool) or value < 0)
                    for value in (excerpt.get("start"), excerpt.get("end"))
                ):
                    errors.append(f"{epath}.start/end must be non-negative integers or null")
    return errors
