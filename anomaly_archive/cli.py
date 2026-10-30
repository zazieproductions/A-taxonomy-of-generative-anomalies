"""Command-line interface for the Archive of Generative Deviance."""

from __future__ import annotations

import argparse
import json
import statistics
import sys
from collections import Counter
from pathlib import Path
from typing import Any

from .ingest import IngestError, ingest_exports, write_corpus
from .privacy import build_public_atlas
from .schema import validate_annotations, validate_corpus


def _load_json(path: str | Path) -> Any:
    with Path(path).open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _taxonomy_ids(path: str | Path) -> set[str]:
    taxonomy = _load_json(path)
    terms = taxonomy.get("terms", []) if isinstance(taxonomy, dict) else []
    return {
        term["id"]
        for term in terms
        if isinstance(term, dict) and isinstance(term.get("id"), str)
    }


def _cmd_ingest(args: argparse.Namespace) -> int:
    inputs = args.inputs or [args.source_root]
    corpus = ingest_exports(inputs, root=args.source_root)
    output = write_corpus(corpus, args.output)
    audit = corpus["deduplication"]
    print(f"Wrote {output}")
    print(
        f"{audit['unique_generation_count']} unique generations from "
        f"{audit['source_run_rows']} source run rows; "
        f"{audit['duplicate_rows_removed']} duplicate rows removed; "
        f"{len(audit['conflicts'])} conflicting duplicate IDs"
    )
    return 0


def _cmd_validate(args: argparse.Namespace) -> int:
    corpus = _load_json(args.corpus)
    errors = validate_corpus(corpus)
    if errors:
        print("Corpus validation failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    generation_ids = {item["generation_id"] for item in corpus["generations"]}
    print(f"Corpus valid: {len(generation_ids)} unique generations")

    if args.annotations:
        bundle = _load_json(args.annotations)
        taxonomy_ids = _taxonomy_ids(args.taxonomy) if args.taxonomy else None
        annotation_errors = validate_annotations(
            bundle,
            generation_ids=generation_ids,
            taxonomy_ids=taxonomy_ids,
        )
        if annotation_errors:
            print("Annotation validation failed:", file=sys.stderr)
            for error in annotation_errors:
                print(f"- {error}", file=sys.stderr)
            return 1
        print(f"Annotations valid: {len(bundle['annotations'])} records")
    return 0


def _cmd_publish(args: argparse.Namespace) -> int:
    corpus = _load_json(args.corpus)
    atlas = build_public_atlas(corpus)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    temp = output.with_name(output.name + ".tmp")
    try:
        with temp.open("w", encoding="utf-8", newline="\n") as handle:
            json.dump(atlas, handle, ensure_ascii=False, indent=2, allow_nan=False)
            handle.write("\n")
        temp.replace(output)
    except OSError as exc:
        temp.unlink(missing_ok=True)
        raise IngestError(f"Could not write public Atlas to {output}: {exc}") from exc
    privacy = atlas["privacy_projection"]
    print(f"Wrote public Atlas projection to {output}")
    print(
        f"{len(atlas['generations'])} generations; "
        f"{privacy['masked_field_count']} text fields masked; "
        f"{privacy['logprob_sequences_suppressed']} logprob sequences suppressed"
    )
    print(privacy["notice"])
    return 0


def _cmd_stats(args: argparse.Namespace) -> int:
    corpus = _load_json(args.corpus)
    errors = validate_corpus(corpus)
    if errors:
        print("Corpus validation failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    runs = corpus["generations"]
    status = Counter(record.get("status") or "unrecorded" for record in runs)
    models = Counter(record.get("model") or "unrecorded" for record in runs)
    temperatures = [
        record["sampling"]["temperature"]
        for record in runs
        if isinstance(record.get("sampling", {}).get("temperature"), (int, float))
        and not isinstance(record["sampling"].get("temperature"), bool)
    ]
    logprobs = sum(isinstance(record.get("logprobs"), list) for record in runs)
    print(f"Generations: {len(runs)}")
    print(f"Experiments: {len(corpus['experiments'])}")
    print(f"Statuses: {dict(sorted(status.items()))}")
    print(f"Models: {dict(sorted(models.items()))}")
    print(f"Token-level logprob arrays: {logprobs}/{len(runs)}")
    if temperatures:
        print(
            "Temperature range: "
            f"{min(temperatures):g}–{max(temperatures):g} "
            f"(median {statistics.median(temperatures):g}; n={len(temperatures)})"
        )
    print(
        "Deduplication: "
        f"{corpus['deduplication']['duplicate_rows_removed']} repeated source rows removed"
    )
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="anomaly-archive",
        description="Normalize and validate ACS Research Infrastructure Workbench exports.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    ingest = subparsers.add_parser("ingest", help="ingest .jsonl export files")
    ingest.add_argument(
        "inputs",
        nargs="*",
        help="source .jsonl files, directories, or glob patterns (default: source root)",
    )
    ingest.add_argument("--source-root", default=".", help="base path used for relative provenance")
    ingest.add_argument("--output", default="data/normalized/corpus.json", help="canonical normalized JSON output")
    ingest.set_defaults(func=_cmd_ingest)

    publish = subparsers.add_parser(
        "publish", help="create a best-effort redacted public Atlas projection"
    )
    publish.add_argument("--corpus", default="data/normalized/corpus.json")
    publish.add_argument("--output", default="docs/data/atlas.json")
    publish.set_defaults(func=_cmd_publish)

    validate = subparsers.add_parser("validate", help="validate a normalized corpus and annotations")
    validate.add_argument("corpus", nargs="?", default="data/normalized/corpus.json")
    validate.add_argument("--annotations", help="optional annotation bundle JSON")
    validate.add_argument("--taxonomy", help="taxonomy JSON used to check annotation label IDs")
    validate.set_defaults(func=_cmd_validate)

    stats = subparsers.add_parser("stats", help="summarize a validated corpus")
    stats.add_argument("corpus", nargs="?", default="data/normalized/corpus.json")
    stats.set_defaults(func=_cmd_stats)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except (IngestError, OSError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
