"""UNFAIR-ToS (LexGLUE / CLAUDETTE) ingester.

Source: Lippi et al. CLAUDETTE corpus, packaged in LexGLUE.
  HuggingFace dataset: `coastalcph/lex_glue` config `unfair_tos`.
  License: CC-BY-4.0.

The dataset has ~9.4K consumer-ToS sentences from real T&C documents,
each annotated with a multi-label vector across 8 unfairness types:

    0  Limitation of liability
    1  Unilateral termination
    2  Unilateral change
    3  Content removal
    4  Contract by using
    5  Choice of law
    6  Jurisdiction
    7  Arbitration

A clause is "unfair" (positive) if any of the 8 labels is 1. "Fair"
sentences (all-zero) are skipped — we want positives for the eval set.

This script:

    1. Loads all three splits (train/val/test) via `datasets.load_dataset`.
    2. Filters to flagged-only rows.
    3. Maps the multi-hot label vector to (risk_category, severity) using
       a deterministic priority order.
    4. Writes one JSONL line per row to `unfair_tos.jsonl` in this dir.
    5. Prints final count + per-category and per-severity distributions.

Run from `backend/`:
    venv/bin/python -m evals.datasets.ingest_unfair_tos
"""

from __future__ import annotations

import json
import sys
import warnings
from pathlib import Path
from typing import Dict, List

# Quiet a noisy urllib3 + LibreSSL warning we can't fix on stock macOS
# Python; it's harmless and clutters CI logs otherwise.
warnings.filterwarnings("ignore", message=".*OpenSSL.*", category=Warning)

_THIS_DIR = Path(__file__).resolve().parent
OUTPUT_PATH = _THIS_DIR / "unfair_tos.jsonl"

# UNFAIR-ToS source labels in their canonical index order. Must match
# LexGLUE's `features` definition; we resolve dynamically below as a
# defensive measure, falling back to this order if the lookup fails.
SOURCE_LABEL_ORDER = (
    "Limitation of liability",
    "Unilateral termination",
    "Unilateral change",
    "Content removal",
    "Contract by using",
    "Choice of law",
    "Jurisdiction",
    "Arbitration",
)

# Map source label -> (risk_category, severity) in our 11/4 vocabulary.
# Severity defaults to "medium" (these are "unfair" clauses by definition,
# but the dataset doesn't grade unfairness intensity, so we pick a safe
# middle bucket). Two well-documented serious categories get bumped to
# "high" per Layer 3.1 spec.
LABEL_MAPPING: Dict[str, Dict[str, str]] = {
    "Limitation of liability": {"category": "liability", "severity": "high"},
    "Unilateral termination": {"category": "termination", "severity": "medium"},
    "Unilateral change": {"category": "modification", "severity": "medium"},
    "Content removal": {"category": "content", "severity": "medium"},
    "Contract by using": {"category": "rights", "severity": "medium"},
    "Choice of law": {"category": "other", "severity": "medium"},
    "Jurisdiction": {"category": "other", "severity": "medium"},
    "Arbitration": {"category": "arbitration", "severity": "high"},
}

# Severity priority — used when a sentence carries multiple unfairness
# labels with conflicting severities. Pick the most severe.
SEVERITY_PRIORITY = {"critical": 0, "high": 1, "medium": 2, "low": 3}

# Category priority — used when a sentence carries multiple labels of
# the same severity. Earlier = preferred. We deliberately demote "other"
# so it only wins when no specific category is present.
CATEGORY_PRIORITY = [
    "liability",
    "arbitration",
    "termination",
    "modification",
    "content",
    "data",
    "privacy",
    "rights",
    "surveillance",
    "payment",
    "other",
]


def _resolve_label_names(dataset) -> List[str]:
    """Pull the human-readable label names from the dataset's features.

    Falls back to `SOURCE_LABEL_ORDER` if the schema layout changes.
    """
    try:
        # LexGLUE exposes labels as a `Sequence(ClassLabel)`.
        features = dataset["train"].features
        seq = features["labels"]
        # Try the most common shape first.
        inner = getattr(seq, "feature", None)
        if inner is not None and hasattr(inner, "names"):
            return list(inner.names)
    except Exception as e:
        print(f"  ! could not resolve label names from features ({e}); using fallback")
    return list(SOURCE_LABEL_ORDER)


def _pick_label_for_row(active_label_names: List[str]) -> Dict[str, str]:
    """Given the set of active unfairness labels for a row, pick one
    (category, severity) tuple using priority rules.
    """
    candidates = []
    for name in active_label_names:
        mapped = LABEL_MAPPING.get(name)
        if mapped is None:
            continue
        candidates.append(
            (
                SEVERITY_PRIORITY[mapped["severity"]],
                CATEGORY_PRIORITY.index(mapped["category"])
                if mapped["category"] in CATEGORY_PRIORITY
                else len(CATEGORY_PRIORITY),
                mapped["category"],
                mapped["severity"],
            )
        )
    if not candidates:
        # Should not happen since we only enter this fn for flagged rows,
        # but be defensive.
        return {"category": "other", "severity": "medium"}
    candidates.sort()
    _, _, category, severity = candidates[0]
    return {"category": category, "severity": severity}


def ingest() -> int:
    """Run the ingestion. Returns the count of rows written."""
    try:
        from datasets import load_dataset as hf_load_dataset
    except ImportError:
        print(
            "ERROR: `datasets` library is not installed. "
            "Run: pip install 'datasets>=2.14.0'"
        )
        return 0

    print("Loading coastalcph/lex_glue config=unfair_tos ...")
    try:
        ds = hf_load_dataset("coastalcph/lex_glue", "unfair_tos")
    except Exception as e:
        print(f"ERROR: failed to load dataset from HuggingFace: {e}")
        print(
            "  Check network connectivity and that the dataset is still "
            "available at coastalcph/lex_glue."
        )
        return 0

    label_names = _resolve_label_names(ds)
    print(f"  resolved {len(label_names)} label names: {label_names}")

    # Pool all three splits — we want the maximum number of labeled
    # examples for evaluation. Splits are an artefact of the original
    # multi-label classification task, not relevant here.
    rows_written = 0
    severity_counts: Dict[str, int] = {}
    category_counts: Dict[str, int] = {}
    label_counts: Dict[str, int] = {}

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    with OUTPUT_PATH.open("w", encoding="utf-8") as f_out:
        for split_name in ("train", "validation", "test"):
            if split_name not in ds:
                continue
            split = ds[split_name]
            print(f"  processing split={split_name} (n={len(split)})")
            for idx, row in enumerate(split):
                labels = row.get("labels") or []
                # Some HF configs return labels as a list of class
                # indices (one per active label); others as a multi-hot
                # vector. Normalise to a list of active label NAMES.
                active_names: List[str] = []
                if labels and isinstance(labels[0], int):
                    # Could be either: index list, or multi-hot.
                    if len(labels) == len(label_names) and set(labels) <= {0, 1}:
                        # Multi-hot.
                        active_names = [
                            label_names[i] for i, v in enumerate(labels) if v == 1
                        ]
                    else:
                        # Index list (the typical LexGLUE shape).
                        active_names = [
                            label_names[i] for i in labels if 0 <= i < len(label_names)
                        ]

                if not active_names:
                    # Skip "fair" rows.
                    continue

                text = (row.get("text") or "").strip()
                if not text:
                    continue

                mapping = _pick_label_for_row(active_names)
                record = {
                    "clause_id": f"unfair_tos_{split_name}_{idx}",
                    "section": active_names[0],
                    "text": text,
                    "expected_severity": mapping["severity"],
                    "expected_risk_category": mapping["category"],
                    "notes": ", ".join(active_names),
                    "source": "UNFAIR-ToS (LexGLUE)",
                }
                f_out.write(json.dumps(record, ensure_ascii=False) + "\n")
                rows_written += 1
                severity_counts[mapping["severity"]] = (
                    severity_counts.get(mapping["severity"], 0) + 1
                )
                category_counts[mapping["category"]] = (
                    category_counts.get(mapping["category"], 0) + 1
                )
                for name in active_names:
                    label_counts[name] = label_counts.get(name, 0) + 1

    print()
    print("=" * 60)
    print(f"UNFAIR-ToS ingestion complete: {rows_written} rows -> {OUTPUT_PATH}")
    print("=" * 60)
    print("by severity:")
    for sev in ("critical", "high", "medium", "low"):
        print(f"  {sev:<10} {severity_counts.get(sev, 0):>6}")
    print("by category (mapped):")
    for cat, count in sorted(category_counts.items(), key=lambda x: -x[1]):
        print(f"  {cat:<14} {count:>6}")
    print("by source label (raw, multi-label counts):")
    for name, count in sorted(label_counts.items(), key=lambda x: -x[1]):
        print(f"  {name:<30} {count:>6}")
    return rows_written


if __name__ == "__main__":
    n = ingest()
    sys.exit(0 if n > 0 else 1)
