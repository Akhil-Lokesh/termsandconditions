"""Score the production detector against the public UNFAIR-ToS (LexGLUE) benchmark.

Unlike ``baseline_runner`` (which sends the whole sample to the detector at once
and fans out parallel batches — that times out on large N with the heavy
checklist prompts), this runner processes clauses in SEQUENTIAL chunks so a big
sample completes reliably. It reuses the exact prediction/label/metric logic
from ``baseline_runner`` and adds two benchmark-honest metrics:

  * recall_flagged       — fraction of (all-unfair) clauses the detector flagged
                           at all. UNFAIR-ToS contains only unfair clauses, so a
                           non-flag is a miss.
  * severity_within_1    — fraction within one ordinal tier. Unweighted Cohen's
                           kappa is depressed by the medium-heavy base rate
                           (kappa paradox); this ordinal view is fairer for a
                           tier scale and exposes the "off by one" pattern.

Usage:
    python -m evals.run_unfair_tos_benchmark --n 120 --chunk 30 \
        --out evals/unfair_tos_benchmark.json
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

_THIS_DIR = Path(__file__).resolve().parent
_BACKEND_DIR = _THIS_DIR.parent
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

from evals.baseline_runner import (  # noqa: E402
    _align_predictions,
    _build_report,
    _detect,
)

logger = logging.getLogger(__name__)

_TIER = {"none": 0, "low": 1, "medium": 2, "high": 3, "critical": 4}


def _ordinal_metrics(
    predictions: List[Dict[str, Any]], labels: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """Recall + ordinal severity metrics that the base-rate-sensitive kappa hides."""
    n = len(labels)
    flagged = sum(1 for p in predictions if p.get("severity"))
    exact = 0
    within1 = 0
    under = 0  # detector rated LOWER than benchmark
    over = 0   # detector rated HIGHER than benchmark
    scored = 0
    for p, l in zip(predictions, labels):
        gold = l.get("expected_severity")
        if gold not in _TIER:
            continue
        scored += 1
        pred = p.get("severity") or "none"
        gi, pi = _TIER[gold], _TIER.get(pred, 0)
        if pi == gi:
            exact += 1
        if abs(pi - gi) <= 1:
            within1 += 1
        if pi < gi:
            under += 1
        elif pi > gi:
            over += 1
    return {
        "n": n,
        "recall_flagged": round(flagged / n, 4) if n else 0.0,
        "severity_exact": round(exact / scored, 4) if scored else 0.0,
        "severity_within_1": round(within1 / scored, 4) if scored else 0.0,
        "severity_under_rated": round(under / scored, 4) if scored else 0.0,
        "severity_over_rated": round(over / scored, 4) if scored else 0.0,
    }


async def _run(dataset: str, n: int, chunk: int, seed: int) -> Dict[str, Any]:
    from evals.datasets.loader import load_dataset

    eval_clauses = load_dataset(dataset, max_rows=n)
    if not eval_clauses:
        raise RuntimeError(f"no clauses for dataset={dataset!r}")

    findings: List[Dict[str, Any]] = []
    total = len(eval_clauses)
    for i in range(0, total, chunk):
        part = eval_clauses[i : i + chunk]
        print(f"  chunk {i // chunk + 1}: clauses {i + 1}-{i + len(part)} of {total}…")
        try:
            findings.extend(await _detect(part))
        except Exception as exc:  # noqa: BLE001
            logger.warning(f"chunk {i // chunk + 1} failed ({exc}); clauses count as missed")

    predictions, labels = _align_predictions(findings, eval_clauses)
    report = _build_report(dataset, eval_clauses, predictions, labels)
    report["ordinal_metrics"] = _ordinal_metrics(predictions, labels)
    report["chunk_size"] = chunk
    return report


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dataset", default="unfair_tos",
                    choices=("unfair_tos", "opp115", "all"))
    ap.add_argument("--n", type=int, default=120)
    ap.add_argument("--chunk", type=int, default=30)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--out", type=Path, default=Path("evals/unfair_tos_benchmark.json"))
    args = ap.parse_args(argv)

    logging.basicConfig(level=logging.WARNING)

    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("skipped — ANTHROPIC_API_KEY not set")
        return 0

    report = asyncio.run(_run(args.dataset, args.n, args.chunk, args.seed))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2), encoding="utf-8")

    om = report["ordinal_metrics"]
    pr = report["precision_recall_by_severity"]
    print(f"\n=== UNFAIR-ToS benchmark (N={report['n_samples']}) ===")
    print(f"  recall (flagged):       {om['recall_flagged'] * 100:.1f}%")
    print(f"  severity exact:         {om['severity_exact'] * 100:.1f}%")
    print(f"  severity within 1 tier: {om['severity_within_1'] * 100:.1f}%")
    print(f"  under-rated / over-rated: {om['severity_under_rated']*100:.1f}% / {om['severity_over_rated']*100:.1f}%")
    print(f"  severity kappa:         {report['severity_kappa']:+.3f} ({report['severity_kappa_interpretation']})")
    print(f"  category kappa:         {report['category_kappa']:+.3f}")
    print(f"  category recall:        {report['category_recall'].get('overall_recall', 0)*100:.1f}%")
    print(f"  micro F1:               {pr.get('micro', {}).get('f1', 0):.3f}")
    print(f"  wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
