"""Unified loader for labeled eval datasets.

Exposes two functions:

    load_dataset(name, max_rows=None) -> list[EvalClause]
        name ∈ {"unfair_tos", "opp115", "seed", "all"}
        Reads the corresponding JSONL/JSON file, validates each row through
        the `EvalClause` Pydantic model, and returns the parsed list.

    dataset_stats(name) -> dict
        Counts per severity and per risk category. Useful for sanity
        checks before kicking off an eval run.

The seed dataset is the original hand-labeled fixture
(`evals/fixtures/labeled_clauses.json`); the other two are produced by
the ingesters in this package.

If a dataset file is missing (e.g. ingester hasn't run yet), the loader
returns an empty list and prints a warning — it does not raise. This
keeps CI green when network or licensed data is unavailable.
"""

from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Dict, List, Optional

from .schema import EvalClause, RISK_CATEGORY_VALUES, SEVERITY_VALUES

# Resolve paths relative to this file so the loader works from any cwd.
_THIS_DIR = Path(__file__).resolve().parent
_BACKEND_DIR = _THIS_DIR.parent.parent  # backend/

SEED_PATH = _BACKEND_DIR / "evals" / "fixtures" / "labeled_clauses.json"
UNFAIR_TOS_PATH = _THIS_DIR / "unfair_tos.jsonl"
UNFAIR_TOS_MIXED_PATH = _THIS_DIR / "unfair_tos_mixed.jsonl"
OPP115_PATH = _THIS_DIR / "opp115.jsonl"

_VALID_NAMES = ("unfair_tos", "unfair_tos_mixed", "opp115", "seed", "all")


def _iter_jsonl(path: Path):
    """Yield decoded JSON objects from a JSONL file (one per line)."""
    with path.open("r", encoding="utf-8") as f:
        for lineno, raw in enumerate(f, start=1):
            raw = raw.strip()
            if not raw:
                continue
            try:
                yield json.loads(raw)
            except json.JSONDecodeError as e:
                print(f"  ! {path.name}:{lineno} skipped: invalid JSON ({e})")


def _load_seed() -> List[EvalClause]:
    """Load the original hand-labeled fixture."""
    if not SEED_PATH.exists():
        print(f"  ! seed fixture missing at {SEED_PATH}")
        return []
    with SEED_PATH.open("r", encoding="utf-8") as f:
        data = json.load(f)
    raw_rows = data.get("clauses", []) if isinstance(data, dict) else data
    return _validate_rows(raw_rows, source_label="seed")


def _load_jsonl(path: Path, source_label: str) -> List[EvalClause]:
    if not path.exists():
        print(
            f"  ! {source_label} dataset missing at {path}. "
            f"Run the corresponding ingester to generate it."
        )
        return []
    rows = list(_iter_jsonl(path))
    return _validate_rows(rows, source_label=source_label)


def _validate_rows(rows: List[dict], source_label: str) -> List[EvalClause]:
    """Run each row through EvalClause. Drop invalid rows with a count."""
    out: List[EvalClause] = []
    rejected = 0
    for row in rows:
        try:
            out.append(EvalClause(**row))
        except Exception as e:
            rejected += 1
            if rejected <= 5:
                # Only show the first handful — avoid spamming the log.
                print(f"  ! {source_label} reject: {e}")
    if rejected:
        print(f"  ! {source_label}: rejected {rejected} row(s)")
    return out


def load_dataset(
    name: str,
    max_rows: Optional[int] = None,
) -> List[EvalClause]:
    """Load a named eval dataset, validated through the unified schema.

    Args:
        name: One of {"unfair_tos", "opp115", "seed", "all"}.
        max_rows: If provided, randomly subsample to this size with a
            fixed seed (42) for reproducibility.

    Returns:
        List of validated `EvalClause` instances. Empty if the underlying
        file is missing.

    Raises:
        ValueError: if `name` is not a recognised dataset key.
    """
    if name not in _VALID_NAMES:
        raise ValueError(
            f"Unknown dataset {name!r}. Pick one of {_VALID_NAMES}."
        )

    if name == "seed":
        rows = _load_seed()
    elif name == "unfair_tos":
        rows = _load_jsonl(UNFAIR_TOS_PATH, source_label="unfair_tos")
    elif name == "unfair_tos_mixed":
        rows = _load_jsonl(UNFAIR_TOS_MIXED_PATH, source_label="unfair_tos_mixed")
    elif name == "opp115":
        rows = _load_jsonl(OPP115_PATH, source_label="opp115")
    else:  # "all"
        rows = (
            _load_seed()
            + _load_jsonl(UNFAIR_TOS_PATH, source_label="unfair_tos")
            + _load_jsonl(OPP115_PATH, source_label="opp115")
        )

    if max_rows is not None and len(rows) > max_rows:
        rng = random.Random(42)
        rows = rng.sample(rows, max_rows)

    return rows


def dataset_stats(name: str) -> Dict:
    """Return per-severity and per-category counts for a dataset.

    Always returns the full key set (severities + categories) with zeros
    for absent buckets, so downstream code can rely on the shape.
    """
    rows = load_dataset(name)
    sev_counts = {s: 0 for s in SEVERITY_VALUES}
    cat_counts = {c: 0 for c in RISK_CATEGORY_VALUES}
    for r in rows:
        sev_counts[r.expected_severity] = sev_counts.get(r.expected_severity, 0) + 1
        cat_counts[r.expected_risk_category] = (
            cat_counts.get(r.expected_risk_category, 0) + 1
        )
    return {
        "name": name,
        "total": len(rows),
        "by_severity": sev_counts,
        "by_category": cat_counts,
    }


if __name__ == "__main__":
    # Quick smoke when run directly: print stats for every dataset.
    import sys

    for ds in _VALID_NAMES:
        print(json.dumps(dataset_stats(ds), indent=2))
    sys.exit(0)
