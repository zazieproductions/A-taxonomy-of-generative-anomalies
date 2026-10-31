"""Build a best-effort redacted projection for the public static Atlas.

The canonical normalized corpus and supplied raw exports are never modified by
this module. Pattern masking is intentionally conservative but is not a privacy
guarantee; a human review is still required before public release.
"""

from __future__ import annotations

import copy
import json
import re
from collections import Counter, defaultdict
from typing import Any

from .schema import validate_corpus

_LABELLED_PERSONAL_FIELD = re.compile(
    r"(?im)(^|\b)((?:your\s+)?(?:full\s+name|name|street\s+address|mailing\s+address|home\s+address|address|current\s+location|location(?:\s+at\s+[^:\n]+)?|coordinates|blood\s+type|blood\s+pressure|body\s+temperature|pupil\s+size|pulse|breathing\s+rate|weight|phone\s+number|email\s+address|UPS\s+tracking\s+number|tracking\s+number|DNA\s+sequence(?:\s+reads)?)\s*:\s*)([^\r\n]+)"
)

_INLINE_SELF_NAME = re.compile(
    r"(?i)\b((?:my|your)\s+(?:full\s+)?name\s+is\s+)([^,.;\r\n]+)"
)

_RULES: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("ssn_like", re.compile(r"\b\d{3}-\d{2}-\d{4}\b")),
    ("payment_card_like", re.compile(r"\b(?:\d[ -]?){13,19}\b")),
    (
        "security_code_like",
        re.compile(r"\b(?:CVV2?|CVC|security\s+code)\s*[:=#]?\s*\d{3,4}\b", re.IGNORECASE),
    ),
    ("ipv4_like", re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")),
    (
        "phone_like",
        re.compile(r"\b(?:\+?1[ .-]?)?(?:\(\d{3}\)|\d{3})[ .-]\d{3}[ .-]\d{4}\b"),
    ),
    (
        "email_like",
        re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE),
    ),
)


REDACTION_NOTICE = (
    "Best-effort public projection: common structured identifiers and selected labelled/self-declared "
    "personal fields are masked in text. Other names, addresses, context-dependent identifiers, "
    "and novel formats may remain. The canonical corpus and source exports are unchanged; review "
    "them and confirm publication rights before release."
)


def redact_sensitive_text(value: str) -> tuple[str, list[str]]:
    """Return display text and the names of pattern families that were masked."""
    result = value
    hits: list[str] = []
    before = result
    result, _ = _INLINE_SELF_NAME.subn(
        lambda match: f"{match.group(1)}[REDACTED STRUCTURED VALUE]",
        result,
    )
    if result != before:
        hits.append("self_declared_name")
    before = result
    result, _ = _LABELLED_PERSONAL_FIELD.subn(
        lambda match: f"{match.group(1)}{match.group(2)}[REDACTED STRUCTURED VALUE]",
        result,
    )
    if result != before:
        hits.append("labelled_personal_field")
    for label, pattern in _RULES:
        before = result
        result, _ = pattern.subn("[REDACTED STRUCTURED VALUE]", result)
        if result != before:
            hits.append(label)
    return result, hits


def build_public_atlas(corpus: dict[str, Any]) -> dict[str, Any]:
    """Create an Atlas payload with common identifiers masked in text fields.

    Generation configuration, token data, logprobs, and provenance are retained
    unless a pattern is detected in a generation's prompt/completion text. In
    that case the public copy suppresses the entire logprob sequence because a
    candidate token can expose a value split across token boundaries.
    """
    errors = validate_corpus(corpus)
    if errors:
        raise ValueError("Cannot publish an invalid corpus:\n- " + "\n- ".join(errors))

    # Pair groups are computed from exact canonical prompt/config values before
    # display masking. IDs expose group membership only, never the prompt hash.
    pair_candidates: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for source in corpus["generations"]:
        config = {
            key: value
            for key, value in source["generation_config"].items()
            if key not in {"model", "wrapper_model_id", "seed"}
        }
        pair_key = json.dumps(
            [source.get("experiment_id"), source.get("prompt"), config],
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        pair_candidates[pair_key].append(source)
    pair_ids: dict[str, str] = {}
    matched_groups = [
        group
        for group in pair_candidates.values()
        if len(group) == 2 and len({item.get("model") for item in group}) == 2
    ]
    matched_groups.sort(
        key=lambda group: min(item["generation_id"] for item in group)
    )
    for index, group in enumerate(matched_groups, start=1):
        pair_id = f"pair-{index:02d}"
        for item in group:
            pair_ids[item["generation_id"]] = pair_id

    counts: Counter[str] = Counter()
    suppressed_logprobs = 0
    public_generations: list[dict[str, Any]] = []
    for source in corpus["generations"]:
        item = copy.deepcopy(source)
        item["comparison_group_id"] = pair_ids.get(item["generation_id"])
        redactions: dict[str, list[str]] = {}
        for field in ("prompt", "configured_prompt", "completion"):
            value = item.get(field)
            if isinstance(value, str):
                masked, families = redact_sensitive_text(value)
                if families:
                    item[field] = masked
                    redactions[field] = families
                    counts.update(families)

        config = item.get("generation_config")
        if isinstance(config, dict) and isinstance(config.get("prompt"), str):
            masked, families = redact_sensitive_text(config["prompt"])
            if families:
                config["prompt"] = masked
                redactions["generation_config.prompt"] = families
                counts.update(families)

        item["privacy_redactions"] = redactions
        item["logprobs_suppressed_for_privacy"] = bool(redactions and isinstance(item.get("logprobs"), list))
        if item["logprobs_suppressed_for_privacy"]:
            item["logprobs"] = None
            suppressed_logprobs += 1
        public_generations.append(item)

    # Only stable identifiers, titles, and provenance paths are needed by the
    # static app. Workbench metadata versions can contain a second unredacted
    # copy of the full prompt, so they remain in the canonical corpus only.
    experiments = [
        {
            "experiment_id": item["experiment_id"],
            "title": item.get("title"),
            "source_files": item.get("source_files", []),
        }
        for item in corpus["experiments"]
    ]
    source_exports = [
        {
            key: item.get(key)
            for key in (
                "source_file",
                "source_sha256",
                "bytes",
                "object_index",
                "experiment_id",
                "title",
                "created_at",
                "updated_at",
                "last_mode",
                "run_rows_in_export",
                "snapshots_in_export",
                "compare_snapshots_in_export",
            )
        }
        for item in corpus["source_exports"]
    ]
    return {
        "schema_version": 1,
        "record_type": "acs-workbench-public-atlas",
        "source_corpus_schema_version": corpus["schema_version"],
        "source_exports": source_exports,
        "experiments": experiments,
        "generations": public_generations,
        "deduplication": copy.deepcopy(corpus["deduplication"]),
        "privacy_projection": {
            "policy": "pattern-and-labelled-context-mask-v2",
            "notice": REDACTION_NOTICE,
            "masked_field_count": sum(len(item["privacy_redactions"]) for item in public_generations),
            "masked_pattern_hits": dict(sorted(counts.items())),
            "logprob_sequences_suppressed": suppressed_logprobs,
            "comparison_group_count": len(matched_groups),
            "comparison_matching_rule": "exact prompt and exact generation_config excluding model, wrapper_model_id, and seed, within one experiment; exactly two records with distinct run-level models",
            "canonical_corpus_is_unmodified": True,
        },
    }
