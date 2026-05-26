"""Sample diverse clauses from ingested corpora for hand-labeling.

One-shot. Writes ``gold_holdout_queue.jsonl`` — a stub of clauses with the
severity and category fields blank, plus a hint of the upstream label.
Run before ``label_gold_holdout.py``.

Usage:
    cd backend
    python -m evals.datasets.sample_for_labeling
"""

from __future__ import annotations

import json
import random
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).parent
SOURCES = [HERE / "unfair_tos.jsonl", HERE / "opp115.jsonl"]
QUEUE_PATH = HERE / "gold_holdout_queue.jsonl"

TARGET_TOTAL = 160
MIN_LEN, MAX_LEN = 80, 700
SEED = 1234


def main() -> None:
    random.seed(SEED)

    by_cat: dict[str, list[dict]] = defaultdict(list)
    total_read = 0
    for src in SOURCES:
        if not src.exists():
            print(f"warning: {src.name} not found, skipping")
            continue
        with src.open() as f:
            for line in f:
                rec = json.loads(line)
                t = rec.get("text", "").strip()
                if not (MIN_LEN <= len(t) <= MAX_LEN):
                    continue
                cat = rec.get("expected_risk_category", "other")
                rec["text"] = t
                by_cat[cat].append(rec)
                total_read += 1

    if not by_cat:
        raise SystemExit("no clauses available — ingest UNFAIR-ToS or OPP-115 first")

    cats = sorted(by_cat.keys())
    per_cat = TARGET_TOTAL // len(cats)
    leftover = TARGET_TOTAL - per_cat * len(cats)

    sampled: list[dict] = []
    for cat in cats:
        bucket = by_cat[cat]
        random.shuffle(bucket)
        take = per_cat + (1 if leftover > 0 else 0)
        if leftover > 0:
            leftover -= 1
        sampled.extend(bucket[:take])

    random.shuffle(sampled)

    seen: set[str] = set()
    deduped: list[dict] = []
    for r in sampled:
        if r["text"] in seen:
            continue
        seen.add(r["text"])
        deduped.append(r)

    with QUEUE_PATH.open("w") as f:
        for i, r in enumerate(deduped, 1):
            stub = {
                "clause_id": f"gold_{i:03d}",
                "section": r.get("section", "Unknown"),
                "text": r["text"],
                "expected_severity": "",
                "expected_risk_category": "",
                "notes": "",
                "source": "hand-labeled (gold)",
                "_hint_category": r.get("expected_risk_category", ""),
                "_hint_source_dataset": r.get("source", ""),
            }
            f.write(json.dumps(stub) + "\n")

    print(f"sampled {len(deduped)} clauses from {total_read} candidates")
    print(f"wrote {QUEUE_PATH}")
    print("\nnext: python -m evals.datasets.label_gold_holdout")


if __name__ == "__main__":
    main()
