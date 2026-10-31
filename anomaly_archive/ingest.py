"""Read ACS Research Infrastructure Workbench exports and normalize runs.

The Workbench's ``.jsonl`` exports are not always line-oriented JSON: the
supplied exports each contain one large JSON object on one physical line. This
module accepts that form as well as conventional one-object-per-line JSONL.
Raw inputs are read-only; the normalizer only writes the requested output.
"""

from __future__ import annotations

import glob
import hashlib
import json
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable

from . import CORPUS_SCHEMA_VERSION
from .schema import validate_corpus


class IngestError(ValueError):
    """Raised when an input cannot be normalized without losing records."""


# Values here describe sampling or request configuration. Model identifiers and
# prompt strings are retained in their own fields and in generation_config.
CONFIG_METADATA_KEYS = {"model", "wrapper_model_id", "prompt"}


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def _safe_source_path(path: Path, root: Path) -> str:
    """Return a stable, non-absolute source locator for provenance."""
    resolved = path.resolve()
    try:
        return resolved.relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.name


def discover_source_files(inputs: Iterable[str | Path], root: str | Path = ".") -> list[Path]:
    """Expand files, directories, and glob patterns into sorted ``.jsonl`` files."""
    root_path = Path(root)
    found: set[Path] = set()
    for item in inputs:
        raw = str(item)
        # Expand globs explicitly so quoted patterns also work on Windows/CI.
        matches = [Path(match) for match in glob.glob(raw, recursive=True)]
        candidates = matches or [Path(raw)]
        for candidate in candidates:
            if candidate.is_dir():
                found.update(p for p in candidate.rglob("*.jsonl") if p.is_file())
            elif candidate.is_file() and candidate.suffix.lower() == ".jsonl":
                found.add(candidate)
    return sorted(found, key=lambda p: _safe_source_path(p, root_path))


def _decode_source(path: Path) -> list[tuple[int, dict[str, Any]]]:
    """Decode one-object exports, JSON arrays, or line-delimited JSON records.

    The returned index is zero-based within a file (for the supplied
    single-object exports it is always 0). Blank lines do not consume an index.
    """
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        payload = None
    except OSError as exc:
        raise IngestError(f"Cannot read {path}: {exc}") from exc

    if isinstance(payload, dict):
        return [(0, payload)]
    if isinstance(payload, list):
        if not all(isinstance(item, dict) for item in payload):
            raise IngestError(f"Top-level JSON array in {path} must contain objects only")
        return list(enumerate(payload))

    records: list[tuple[int, dict[str, Any]]] = []
    try:
        with path.open("r", encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, start=1):
                if not line.strip():
                    continue
                try:
                    value = json.loads(line)
                except json.JSONDecodeError as exc:
                    raise IngestError(
                        f"Invalid JSON in {path} at physical line {line_number}: {exc.msg}"
                    ) from exc
                if not isinstance(value, dict):
                    raise IngestError(
                        f"JSONL record in {path} at physical line {line_number} is not an object"
                    )
                records.append((len(records), value))
    except OSError as exc:
        raise IngestError(f"Cannot read {path}: {exc}") from exc
    if not records:
        raise IngestError(f"No JSON objects found in {path}")
    return records


def _generation_config(run: dict[str, Any]) -> dict[str, Any]:
    config = run.get("generation_config")
    return config if isinstance(config, dict) else {}


def _normalize_run(
    run: dict[str, Any],
    *,
    experiment_id: str | None,
    experiment_title: str | None,
    source_file: str,
    source_sha256: str,
    export_updated_at: str | None,
    object_index: int,
    run_index: int,
) -> dict[str, Any]:
    run_id = run.get("id")
    if not isinstance(run_id, str) or not run_id.strip():
        raise IngestError(
            f"A generation in {source_file} (object {object_index}, run {run_index}) "
            "has no stable string 'id'; it cannot be deduplicated safely"
        )

    config = _generation_config(run)
    source_record_sha256 = _sha256_bytes(_canonical_json(run).encode("utf-8"))
    return {
        "generation_id": run_id,
        "experiment_id": experiment_id,
        "experiment_title": experiment_title,
        # ``model`` is the Workbench run-level identifier. The exact upstream
        # model and wrapper identifier remain separate; no alias is inferred.
        "model": run.get("model"),
        "model_identifier": config.get("model"),
        "wrapper_model_id": config.get("wrapper_model_id"),
        "prompt": run.get("prompt_before"),
        "configured_prompt": config.get("prompt"),
        "completion": run.get("completion_text"),
        "status": run.get("status"),
        "finalized": run.get("finalized"),
        "source_field_presence": {
            field: field in run
            for field in (
                "model", "prompt_before", "completion_text", "status", "finalized",
                "started_at", "ended_at", "generation_config", "logprobs",
                "n_prompt_tokens", "n_completion_tokens", "finish_reason", "stop_reason",
                "usage_source", "error_message", "compare_run_id",
            )
        },
        "timestamps": {
            "started_at": run.get("started_at"),
            "ended_at": run.get("ended_at"),
        },
        "tokens": {
            "prompt": run.get("n_prompt_tokens"),
            "completion": run.get("n_completion_tokens"),
            "source": run.get("usage_source"),
        },
        "sampling": {
            key: value for key, value in config.items() if key not in CONFIG_METADATA_KEYS
        },
        # Retain the complete config object, including fields added by future
        # Workbench versions. The convenience fields above are a stable index.
        "generation_config": config,
        "logprobs": run.get("logprobs"),
        "finish_reason": run.get("finish_reason"),
        "stop_reason": run.get("stop_reason"),
        "error_message": run.get("error_message"),
        "comparison_run_id": run.get("compare_run_id"),
        "source_provenance": [
            {
                "source_file": source_file,
                "source_sha256": source_sha256,
                "experiment_id": experiment_id,
                "object_index": object_index,
                "run_index": run_index,
                "export_updated_at": export_updated_at,
                "source_record_sha256": source_record_sha256,
            }
        ],
    }


def _completeness(record: dict[str, Any]) -> int:
    """Tie-breaker for conflicting duplicate IDs; never changes raw values."""
    return sum(value is not None for value in record.values())


def _candidate_rank(candidate: dict[str, Any]) -> tuple[str, int, str, str]:
    item = candidate["normalized"]
    export_time = candidate.get("export_updated_at") or ""
    raw = candidate["raw"]
    return (
        export_time,
        _completeness(raw),
        candidate["source_file"],
        _canonical_json(raw),
    )


def _merge_provenance(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    values = [entry for item in candidates for entry in item["normalized"]["source_provenance"]]
    return sorted(
        values,
        key=lambda entry: (
            entry["source_file"],
            entry["object_index"],
            entry["run_index"],
        ),
    )


def ingest_exports(
    inputs: Iterable[str | Path],
    *,
    root: str | Path = ".",
) -> dict[str, Any]:
    """Normalize ACS Workbench exports into a stable, deduplicated corpus.

    Deduplication is keyed only by the original run ``id``. Export timestamps
    determine which record representation is canonical if a duplicate ID has
    conflicting content; all appearances remain in ``source_provenance`` and
    conflicting fields are reported in the corpus-level audit block.
    """
    root_path = Path(root).resolve()
    paths = discover_source_files(inputs, root=root_path)
    if not paths:
        raise IngestError("No .jsonl source files found in the supplied input paths")

    source_exports: list[dict[str, Any]] = []
    experiment_versions: dict[str, list[dict[str, Any]]] = defaultdict(list)
    candidates_by_id: dict[str, list[dict[str, Any]]] = defaultdict(list)
    source_run_rows = 0

    for path in paths:
        try:
            raw_bytes = path.read_bytes()
        except OSError as exc:
            raise IngestError(f"Cannot read {path}: {exc}") from exc
        checksum = _sha256_bytes(raw_bytes)
        source_file = _safe_source_path(path, root_path)
        objects = _decode_source(path)

        for object_index, export in objects:
            is_direct_generation = (
                "runs" not in export and isinstance(export.get("completion_text"), str)
            )
            experiment_id_raw = None if is_direct_generation else export.get("id")
            experiment_id = experiment_id_raw if isinstance(experiment_id_raw, str) else None
            title_raw = None if is_direct_generation else export.get("title")
            experiment_title = title_raw if isinstance(title_raw, str) else None
            export_updated_at_raw = export.get("updated_at")
            export_updated_at = (
                export_updated_at_raw if isinstance(export_updated_at_raw, str) else None
            )
            runs = export.get("runs")
            if is_direct_generation:
                runs = [export]
            if runs is None:
                runs = []
            if not isinstance(runs, list):
                raise IngestError(
                    f"'runs' in {source_file} object {object_index} must be a JSON array"
                )

            source_exports.append(
                {
                    "source_file": source_file,
                    "source_sha256": checksum,
                    "bytes": len(raw_bytes),
                    "object_index": object_index,
                    "experiment_id": experiment_id,
                    "title": experiment_title,
                    "created_at": export.get("created_at"),
                    "updated_at": export_updated_at,
                    "last_mode": export.get("last_mode"),
                    "run_rows_in_export": len(runs),
                    # These are Workbench history containers, not independent
                    # generation records; the stable run ID is authoritative.
                    "snapshots_in_export": len(export.get("snapshots", []))
                    if isinstance(export.get("snapshots"), list)
                    else None,
                    "compare_snapshots_in_export": len(export.get("compare_snapshots", []))
                    if isinstance(export.get("compare_snapshots"), list)
                    else None,
                }
            )

            if experiment_id:
                metadata = {
                    key: value
                    for key, value in export.items()
                    if key not in {"runs", "snapshots", "compare_snapshots"}
                }
                experiment_versions[experiment_id].append(
                    {
                        "source_file": source_file,
                        "source_sha256": checksum,
                        "export_updated_at": export_updated_at,
                        "metadata": metadata,
                    }
                )

            for run_index, raw_run in enumerate(runs):
                if not isinstance(raw_run, dict):
                    raise IngestError(
                        f"Generation {run_index} in {source_file} object {object_index} is not an object"
                    )
                normalized = _normalize_run(
                    raw_run,
                    experiment_id=experiment_id,
                    experiment_title=experiment_title,
                    source_file=source_file,
                    source_sha256=checksum,
                    export_updated_at=export_updated_at,
                    object_index=object_index,
                    run_index=run_index,
                )
                source_run_rows += 1
                candidates_by_id[normalized["generation_id"]].append(
                    {
                        "raw": raw_run,
                        "normalized": normalized,
                        "source_file": source_file,
                        "export_updated_at": export_updated_at,
                    }
                )

    generations: list[dict[str, Any]] = []
    conflicts: list[dict[str, Any]] = []
    duplicate_ids: list[str] = []
    for generation_id in sorted(candidates_by_id):
        candidates = candidates_by_id[generation_id]
        selected = max(candidates, key=_candidate_rank)
        normalized = dict(selected["normalized"])
        normalized["source_provenance"] = _merge_provenance(candidates)
        generations.append(normalized)

        if len(candidates) > 1:
            duplicate_ids.append(generation_id)
            raw_versions = [_canonical_json(c["raw"]) for c in candidates]
            if len(set(raw_versions)) > 1:
                keys = set().union(*(set(c["raw"]) for c in candidates))
                differing = sorted(
                    key
                    for key in keys
                    if len({_canonical_json(c["raw"].get(key, "__MISSING__")) for c in candidates})
                    > 1
                )
                conflicts.append(
                    {
                        "generation_id": generation_id,
                        "source_files": sorted({c["source_file"] for c in candidates}),
                        "differing_source_fields": differing,
                        "selected_source_file": selected["source_file"],
                        "selection_rule": "latest export updated_at, then most non-null raw fields, then stable source ordering",
                    }
                )

    experiments: list[dict[str, Any]] = []
    for experiment_id, versions in sorted(experiment_versions.items()):
        ordered_versions = sorted(
            versions,
            key=lambda value: (
                value.get("export_updated_at") or "",
                value["source_file"],
            ),
        )
        latest = ordered_versions[-1]
        experiments.append(
            {
                "experiment_id": experiment_id,
                "title": latest["metadata"].get("title"),
                "source_files": sorted({v["source_file"] for v in versions}),
                "metadata_versions": ordered_versions,
            }
        )

    corpus = {
        "schema_version": CORPUS_SCHEMA_VERSION,
        "record_type": "acs-workbench-corpus",
        "source_exports": sorted(
            source_exports,
            key=lambda item: (item["source_file"], item["object_index"]),
        ),
        "experiments": experiments,
        "generations": generations,
        "deduplication": {
            "key": "generation_id (original Workbench run id)",
            "source_run_rows": source_run_rows,
            "unique_generation_count": len(generations),
            "duplicate_rows_removed": source_run_rows - len(generations),
            "duplicate_generation_ids": sorted(duplicate_ids),
            "conflicts": conflicts,
            "history_policy": (
                "runs are the canonical generation records; export snapshots and comparison lanes "
                "are recorded in the source manifest but are not counted as additional generations"
            ),
        },
    }
    errors = validate_corpus(corpus)
    if errors:
        raise IngestError("Normalized corpus failed validation:\n- " + "\n- ".join(errors))
    return corpus


def write_corpus(corpus: dict[str, Any], output: str | Path) -> Path:
    """Validate and atomically write a UTF-8 JSON corpus."""
    errors = validate_corpus(corpus)
    if errors:
        raise IngestError("Refusing to write invalid corpus:\n- " + "\n- ".join(errors))
    target = Path(output)
    target.parent.mkdir(parents=True, exist_ok=True)
    temp = target.with_name(target.name + ".tmp")
    try:
        with temp.open("w", encoding="utf-8", newline="\n") as handle:
            json.dump(corpus, handle, ensure_ascii=False, indent=2, allow_nan=False)
            handle.write("\n")
        temp.replace(target)
    except OSError as exc:
        temp.unlink(missing_ok=True)
        raise IngestError(f"Could not write corpus to {target}: {exc}") from exc
    return target
