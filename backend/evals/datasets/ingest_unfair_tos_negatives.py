"""Ingest a MIXED fair/unfair UNFAIR-ToS (LexGLUE) set → unfair_tos_mixed.jsonl.

The default `ingest_unfair_tos.py` skips all "fair" sentences, leaving a
positives-only set on which false-positive rate is unmeasurable (see
BENCHMARK_IMPROVEMENT_PLAN.md A2). This variant ALSO keeps fair clauses, labeled
`expected_severity = "none"` / `expected_risk_category = "none"`, so the harness
can compute a real precision / false-positive number on public data.

Fair clauses massively outnumber unfair ones in LexGLUE, so they are capped to
``FAIR_RATIO`` × the unfair count (seeded sample) to keep the set balanced enough
that a subsample contains both positives and negatives.

Run from `backend/` (uses the local HuggingFace cache; no network needed if the
dataset was previously downloaded):
    venv/bin/python -m evals.datasets.ingest_unfair_tos_negatives
"""

from __future__ import annotations

import json
import random
import sys
from pathlib import Path
from typing import Dict, List

from evals.datasets.ingest_unfair_tos import (
    _pick_label_for_row,
    _resolve_label_names,
)

_THIS_DIR = Path(__file__).resolve().parent
OUTPUT_PATH = _THIS_DIR / "unfair_tos_mixed.jsonl"

FAIR_RATIO = 2  # keep ~2 fair clauses per unfair clause
SEED = 42


def _active_names(labels, label_names: List[str]) -> List[str]:
    if labels and isinstance(labels[0], int):
        if len(labels) == len(label_names) and set(labels) <= {0, 1}:
            return [label_names[i] for i, v in enumerate(labels) if v == 1]
        return [label_names[i] for i in labels if 0 <= i < len(label_names)]
    return []


def ingest() -> int:
    try:
        from datasets import load_dataset as hf_load_dataset
    except ImportError:
        print("ERROR: `datasets` not installed. pip install 'datasets>=2.14.0'")
        return 0

    print("Loading coastalcph/lex_glue config=unfair_tos (mixed fair+unfair) ...")
    try:
        ds = hf_load_dataset("coastalcph/lex_glue", "unfair_tos")
    except Exception as e:  # noqa: BLE001
        print(f"ERROR: failed to load dataset: {e}")
        return 0

    label_names = _resolve_label_names(ds)

    unfair: List[Dict] = []
    fair: List[Dict] = []
    for split_name in ("train", "validation", "test"):
        if split_name not in ds:
            continue
        for idx, row in enumerate(ds[split_name]):
            text = (row.get("text") or "").strip()
            if not text:
                continue
            names = _active_names(row.get("labels") or [], label_names)
            if names:
                m = _pick_label_for_row(names)
                unfair.append({
                    "clause_id": f"unfair_tos_{split_name}_{idx}",
                    "section": names[0],
                    "text": text,
                    "expected_severity": m["severity"],
                    "expected_risk_category": m["category"],
                    "notes": ", ".join(names),
                    "source": "UNFAIR-ToS (LexGLUE)",
                })
            else:
                fair.append({
                    "clause_id": f"fair_tos_{split_name}_{idx}",
                    "section": "Fair",
                    "text": text,
                    "expected_severity": "none",
                    "expected_risk_category": "none",
                    "notes": "no unfairness label (fair clause)",
                    "source": "UNFAIR-ToS (LexGLUE) — fair",
                })

    # Cap fair clauses to FAIR_RATIO × unfair (seeded) for a balanced-ish set.
    cap = FAIR_RATIO * len(unfair)
    if len(fair) > cap:
        fair = random.Random(SEED).sample(fair, cap)

    rows = unfair + fair
    random.Random(SEED).shuffle(rows)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_PATH.open("w", encoding="utf-8") as f_out:
        for r in rows:
            f_out.write(json.dumps(r, ensure_ascii=False) + "\n")

    print("=" * 60)
    print(f"Mixed ingestion complete: {len(rows)} rows -> {OUTPUT_PATH}")
    print(f"  unfair (positives): {len(unfair)}")
    print(f"  fair   (negatives): {len(fair)}  (capped at {FAIR_RATIO}x unfair)")
    print("=" * 60)
    return len(rows)


if __name__ == "__main__":
    n = ingest()
    sys.exit(0 if n > 0 else 1)
