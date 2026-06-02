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
from evals.metrics.severity import SEVERITY_TIER as _TIER  # noqa: E402

logger = logging.getLogger(__name__)


def _ordinal_metrics(
    predictions: List[Dict[str, Any]], labels: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """Recall + ordinal severity stats over RISK-bearing clauses only.

    Recall is computed over gold-risk clauses (excluding fair "none" clauses —
    those are the false-positive denominator, handled separately). Severity
    exact/within-1/under/over are likewise restricted to real-risk gold tiers.
    """
    flagged = 0
    positives = 0
    exact = 0
    within1 = 0
    under = 0  # detector rated LOWER than benchmark
    over = 0   # detector rated HIGHER than benchmark
    for p, l in zip(predictions, labels):
        gold = l.get("expected_severity")
        if gold not in _TIER or gold == "none":
            continue  # skip fair negatives + unlabeled
        positives += 1
        pred = p.get("severity") or "none"
        if pred != "none":
            flagged += 1
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
        "n_positives": positives,
        "recall_flagged": round(flagged / positives, 4) if positives else 0.0,
        "severity_exact": round(exact / positives, 4) if positives else 0.0,
        "severity_within_1": round(within1 / positives, 4) if positives else 0.0,
        "severity_under_rated": round(under / positives, 4) if positives else 0.0,
        "severity_over_rated": round(over / positives, 4) if positives else 0.0,
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

    # Bootstrap 95% CIs on the headline metrics (plan A4) — error bars for a
    # subjective grading task at modest N.
    from evals.metrics import severity as sev_m
    from evals.metrics.bootstrap import bootstrap_ci

    def _recall_positives(preds: List[Dict[str, Any]], labs: List[Dict[str, Any]]) -> float:
        pos = flagged = 0
        for p, l in zip(preds, labs):
            g = l.get("expected_severity")
            if g in _TIER and g != "none":
                pos += 1
                if (p.get("severity") or "none") != "none":
                    flagged += 1
        return flagged / pos if pos else 0.0

    report["confidence_intervals"] = {
        "severity_qwk": bootstrap_ci(sev_m.quadratic_weighted_kappa, predictions, labels),
        "severity_mae": bootstrap_ci(sev_m.severity_mae, predictions, labels),
        "recall_flagged": bootstrap_ci(_recall_positives, predictions, labels),
        "category_recall": bootstrap_ci(
            lambda p, l: sev_m.category_recall(p, l)["overall_recall"], predictions, labels),
        "false_positive_rate": bootstrap_ci(
            lambda p, l: sev_m.false_positive_rate(p, l)["false_positive_rate"], predictions, labels),
    }
    return report


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dataset", default="unfair_tos",
                    choices=("unfair_tos", "unfair_tos_mixed", "opp115", "all"))
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
    fp = report.get("false_positive_rate", {})
    ci = report.get("confidence_intervals", {})

    def _band(key: str, pct: bool = True) -> str:
        c = ci.get(key)
        if not c:
            return ""
        scale = 100 if pct else 1
        unit = "%" if pct else ""
        return f"  [95% CI {c['lo']*scale:.1f}–{c['hi']*scale:.1f}{unit}]"

    print(f"\n=== UNFAIR-ToS benchmark (N={report['n_samples']}, positives={om['n_positives']}) ===")
    print(f"  recall (flagged):       {om['recall_flagged']*100:.1f}%{_band('recall_flagged')}")
    print(f"  category recall:        {report['category_recall'].get('overall_recall', 0)*100:.1f}%{_band('category_recall')}")
    print(f"  category kappa:         {report['category_kappa']:+.3f}  (substantive LexGLUE signal)")
    if fp.get("n_negatives"):
        print(f"  false-positive rate:    {fp['false_positive_rate']*100:.1f}% ({fp['false_positives']}/{fp['n_negatives']} fair){_band('false_positive_rate')}")
    else:
        print("  false-positive rate:    n/a (positives-only — use --dataset unfair_tos_mixed)")
    print("  -- severity (ordinal; primary) --")
    print(f"  severity QWK:           {report['severity_qwk']:+.3f}  (quadratic-weighted){_band('severity_qwk', pct=False)}")
    print(f"  severity MAE:           {report['severity_mae']:.2f} tiers{_band('severity_mae', pct=False)}")
    print(f"  severity within 1 tier: {om['severity_within_1']*100:.1f}%")
    print(f"  under / over-rated:     {om['severity_under_rated']*100:.1f}% / {om['severity_over_rated']*100:.1f}%")
    print(f"  severity kappa:         {report['severity_kappa']:+.3f} (unweighted, base-rate sensitive — NOT the headline)")
    print(f"  micro F1 (severity):    {pr.get('micro', {}).get('f1', 0):.3f}")
    print(f"  wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
