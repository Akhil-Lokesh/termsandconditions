"""Vote ablation experiment — Layer 5.3.

Compares the LLMClauseDetector with self-consistency voting OFF vs ON, on the
same dataset, and reports the Cohen's kappa lift and dollar cost delta. The
intent is to decide whether to flip `SELF_CONSISTENCY_CRITICAL` ON in prod.

Usage:
    python -m evals.experiments.vote_ablation \\
        --n 100 --dataset all --out vote_ablation_report.json

Skip-safe: if `ANTHROPIC_API_KEY` is not set, prints a message and exits 0.

Architectural note: this module deliberately avoids importing anything from
`evals/judge/` — the judge is a separate concern (LLM-as-judge over predictions),
whereas this ablation only compares two configurations of the production detector.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Make `backend/` importable when launched from the project root.
_THIS_DIR = Path(__file__).resolve().parent
_BACKEND_DIR = _THIS_DIR.parent.parent
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))


# ── Helpers ──────────────────────────────────────────────────────────────────


def _align_predictions(
    findings: List[Dict[str, Any]],
    eval_clauses: List[Any],
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Build aligned (predictions, labels) by clause_id.

    Same shape as `evals/baseline_runner.py:_align_predictions`. Duplicated
    here to keep this experiment self-contained.
    """
    by_id = {str(f.get("clause_number")): f for f in findings}
    predictions: List[Dict[str, Any]] = []
    labels: List[Dict[str, Any]] = []
    for c in eval_clauses:
        f = by_id.get(str(c.clause_id), {})
        predictions.append(
            {
                "clause_id": c.clause_id,
                "severity": f.get("severity"),
                "risk_category": f.get("risk_category"),
                "was_voted": f.get("was_voted", False),
                "original_severity": f.get("original_severity"),
                "vote_agreement": f.get("vote_agreement"),
            }
        )
        labels.append(
            {
                "clause_id": c.clause_id,
                "expected_severity": c.expected_severity,
                "expected_risk_category": c.expected_risk_category,
            }
        )
    return predictions, labels


async def _run_detector(
    eval_clauses: List[Any],
    self_consistency: bool,
) -> Dict[str, Any]:
    """Run the production detector with `self_consistency` toggled.

    Returns the aggregate dict from `detect_risky_clauses(return_aggregate=True)`.
    Importing the detector module fresh under a patched env var is the cleanest
    way to flip the module-level flag without persisting it across runs.
    """
    os.environ["SELF_CONSISTENCY_CRITICAL"] = "true" if self_consistency else "false"

    # Force-reimport so the module-level SELF_CONSISTENCY_ENABLED constant
    # picks up the env-var change. We must invalidate the existing module cache.
    import importlib

    import app.core.llm_clause_detector as llm_module
    importlib.reload(llm_module)
    from app.services.claude_service import ClaudeService

    detector = llm_module.LLMClauseDetector(ClaudeService())
    detector_input = [
        {"clause_number": c.clause_id, "section": c.section, "text": c.text}
        for c in eval_clauses
    ]
    return await detector.detect_risky_clauses(
        detector_input,
        company_name="VoteAblation",
        service_type="general",
        return_aggregate=True,
    )


def _kappa_for(
    predictions: List[Dict[str, Any]],
    labels: List[Dict[str, Any]],
) -> float:
    """Overall Cohen's kappa over severities, using stdlib metrics."""
    # Lazy import — keeps `python -m` startup quick.
    from evals.metrics import kappa as kappa_mod

    bundle = kappa_mod.confusion_with_kappa(predictions, labels)
    return float(bundle["overall_kappa"])


def _summarize_transitions(predictions: List[Dict[str, Any]]) -> Dict[str, int]:
    """Count {kept_critical, demoted_to_high, demoted_to_medium, demoted_to_low, split}."""
    counts: Counter = Counter()
    for p in predictions:
        if not p.get("was_voted"):
            continue
        orig = p.get("original_severity")
        sev = p.get("severity")
        agreement = p.get("vote_agreement")
        if orig != "critical":
            continue
        if agreement == "split":
            counts["split"] += 1
        elif sev == "critical":
            counts["kept_critical"] += 1
        elif sev == "high":
            counts["demoted_to_high"] += 1
        elif sev == "medium":
            counts["demoted_to_medium"] += 1
        elif sev == "low":
            counts["demoted_to_low"] += 1
    return dict(counts)


def _count_criticals(predictions: List[Dict[str, Any]]) -> int:
    return sum(1 for p in predictions if p.get("severity") == "critical")


def _recommendation(kappa_delta: float) -> str:
    """Per the spec: 'vote ON if kappa lift > 0.02'."""
    return "vote ON if kappa lift > 0.02 (YES)" if kappa_delta > 0.02 else "vote ON if kappa lift > 0.02 (NO)"


# ── Async core ───────────────────────────────────────────────────────────────


async def _run_ablation_async(
    dataset_name: str,
    n: int,
) -> Optional[Dict[str, Any]]:
    """Run both arms (vote off, vote on) and return the comparison report.

    Returns None when the run is skipped (no API key / empty dataset).
    """
    from evals.datasets.loader import load_dataset

    eval_clauses = load_dataset(dataset_name, max_rows=n)
    if not eval_clauses:
        print(f"vote_ablation skipped — dataset '{dataset_name}' is empty")
        return None

    print(
        f"vote_ablation: {len(eval_clauses)} clause(s) from dataset='{dataset_name}'"
    )

    # Arm A — vote OFF
    print("→ running arm A: SELF_CONSISTENCY_CRITICAL=false")
    arm_a = await _run_detector(eval_clauses, self_consistency=False)
    preds_a, labels = _align_predictions(arm_a["findings"], eval_clauses)
    kappa_a = _kappa_for(preds_a, labels)
    critical_a = _count_criticals(preds_a)

    # Arm B — vote ON
    print("→ running arm B: SELF_CONSISTENCY_CRITICAL=true")
    arm_b = await _run_detector(eval_clauses, self_consistency=True)
    preds_b, _ = _align_predictions(arm_b["findings"], eval_clauses)
    kappa_b = _kappa_for(preds_b, labels)
    critical_b = _count_criticals(preds_b)
    transitions = _summarize_transitions(preds_b)

    kappa_delta = kappa_b - kappa_a
    cost_a = float(arm_a.get("cost_usd", 0.0))
    cost_b = float(arm_b.get("cost_usd", 0.0))
    cost_delta = cost_b - cost_a
    cost_pct = (
        f"{(cost_delta / cost_a * 100):+.0f}%" if cost_a > 0 else "n/a"
    )

    report = {
        "dataset": dataset_name,
        "n_clauses_tested": len(eval_clauses),
        "kappa_no_vote": kappa_a,
        "kappa_with_vote": kappa_b,
        "kappa_delta": kappa_delta,
        "critical_no_vote": critical_a,
        "critical_with_vote": critical_b,
        "transitions": transitions,
        "cost_no_vote_usd": round(cost_a, 6),
        "cost_with_vote_usd": round(cost_b, 6),
        "cost_delta_usd": round(cost_delta, 6),
        "cost_delta_pct": cost_pct,
        "votes_run": arm_b.get("votes_run", 0),
        "votes_skipped_by_cost": arm_b.get("votes_skipped_by_cost", 0),
        "cost_capped": arm_b.get("cost_capped", False),
        "recommendation": _recommendation(kappa_delta),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    return report


# ── CLI entrypoint ───────────────────────────────────────────────────────────


def _print_summary(report: Dict[str, Any]) -> None:
    """One-screen human summary matching the spec's example format."""
    t = report["transitions"]
    print(f"Total clauses tested: {report['n_clauses_tested']}")
    print(f"Critical findings (no vote): {report['critical_no_vote']}")
    print(f"Critical findings (with vote): {report['critical_with_vote']}")
    print(f"  - kept critical: {t.get('kept_critical', 0)}")
    print(f"  - demoted to high: {t.get('demoted_to_high', 0)}")
    print(f"  - demoted to medium: {t.get('demoted_to_medium', 0)}")
    print(f"  - demoted to low: {t.get('demoted_to_low', 0)}")
    print(f"  - split / kept original: {t.get('split', 0)}")
    print(f"Cohen's kappa (no vote): {report['kappa_no_vote']:.2f}")
    print(f"Cohen's kappa (with vote): {report['kappa_with_vote']:.2f}")
    print(f"Delta: {report['kappa_delta']:+.2f}")
    print(f"Cost (no vote): ${report['cost_no_vote_usd']:.2f}")
    print(f"Cost (with vote): ${report['cost_with_vote_usd']:.2f}")
    print(
        f"Cost delta: ${report['cost_delta_usd']:+.2f} ({report['cost_delta_pct']})"
    )
    print(f"Recommendation: {report['recommendation']}")


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="evals.experiments.vote_ablation",
        description=(
            "Run the self-consistency vote ablation: kappa & cost with vote off vs on."
        ),
    )
    parser.add_argument(
        "--n",
        type=int,
        default=100,
        help="Max clauses to sample (default 100).",
    )
    parser.add_argument(
        "--dataset",
        default="all",
        choices=("seed", "unfair_tos", "opp115", "all"),
        help="Labeled dataset to draw from (default 'all').",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("vote_ablation_report.json"),
        help="Where to write the JSON report (default vote_ablation_report.json).",
    )
    args = parser.parse_args(argv)

    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("vote_ablation skipped — ANTHROPIC_API_KEY not set")
        return 0

    try:
        report = asyncio.run(_run_ablation_async(args.dataset, args.n))
    except KeyboardInterrupt:
        print("vote_ablation interrupted")
        return 130

    if report is None:
        return 0

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"\nwrote vote ablation report to {args.out}\n")
    _print_summary(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = ["main"]
