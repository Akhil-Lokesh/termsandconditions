"""Baseline runner — computes the official Cohen's kappa baseline for the
LLMClauseDetector on a chosen labeled dataset.

The output JSON is the input to ``evals/ci_gate.py``: a future PR run is
compared against this baseline so we can detect kappa regressions
> ``max_kappa_regression`` (default 0.03) in CI.

The runner is intentionally small. It loads N rows from
``evals.datasets.loader.load_dataset``, runs them through the production
``LLMClauseDetector.detect_risky_clauses``, then plugs the aligned
predictions/labels into ``evals.metrics.kappa.confusion_with_kappa`` and
serialises the result.

Skip-safe: if ``ANTHROPIC_API_KEY`` is not set the runner prints
``baseline skipped — no API key`` and exits 0 without writing a file.
This keeps CI green on PRs from forks / environments without secrets.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

_THIS_DIR = Path(__file__).resolve().parent
_BACKEND_DIR = _THIS_DIR.parent
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))


def _git_commit_short() -> Optional[str]:
    """Best-effort short git SHA. Returns None when not in a repo."""
    try:
        out = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=str(_BACKEND_DIR),
            stderr=subprocess.DEVNULL,
            timeout=2,
        )
        return out.decode("ascii").strip() or None
    except Exception:  # noqa: BLE001
        return None


async def _detect(
    eval_clauses: List[Any],
) -> List[Dict[str, Any]]:
    """Run the production detector over a list of EvalClause rows."""
    from app.core.llm_clause_detector import LLMClauseDetector
    from app.services.claude_service import ClaudeService

    detector = LLMClauseDetector(ClaudeService())
    detector_input = [
        {
            "clause_number": c.clause_id,
            "section": c.section,
            "text": c.text,
        }
        for c in eval_clauses
    ]
    return await detector.detect_risky_clauses(
        detector_input,
        company_name="EvalHarness",
        service_type="general",
    )


def _align_predictions(
    findings: List[Dict[str, Any]],
    eval_clauses: List[Any],
) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Build aligned (predictions, labels) lists keyed by clause_id."""
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


def _build_report(
    dataset_name: str,
    eval_clauses: List[Any],
    predictions: List[Dict[str, Any]],
    labels: List[Dict[str, Any]],
) -> Dict[str, Any]:
    from evals.metrics import kappa as kappa_mod
    from evals.metrics import severity as severity_metrics

    confusion = kappa_mod.confusion_with_kappa(predictions, labels)
    pr = severity_metrics.precision_recall_by_severity(predictions, labels)
    cat_kappa = kappa_mod.category_kappa(predictions, labels)
    cat_recall = severity_metrics.category_recall(predictions, labels)
    return {
        "dataset": dataset_name,
        "n_samples": len(eval_clauses),
        "severity_kappa": confusion["overall_kappa"],
        "severity_kappa_interpretation": confusion[
            "overall_kappa_interpretation"
        ],
        "per_severity_kappa": confusion["per_severity_kappa"],
        "macro_kappa": confusion["macro_kappa"],
        "category_kappa": cat_kappa,
        "confusion_matrix": confusion["confusion_matrix"],
        "precision_recall_by_severity": pr,
        "category_recall": cat_recall,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "git_commit": _git_commit_short(),
    }


def _skip_report(reason: str, dataset_name: str, n_samples: int) -> Dict[str, Any]:
    return {
        "status": "skipped",
        "reason": reason,
        "dataset": dataset_name,
        "n_samples": n_samples,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


async def _run_baseline_async(
    dataset_name: str,
    n_samples: int,
    seed: int,
) -> Dict[str, Any]:
    from evals.datasets.loader import load_dataset

    eval_clauses = load_dataset(dataset_name, max_rows=n_samples)
    if not eval_clauses:
        return _skip_report(
            reason="no_data",
            dataset_name=dataset_name,
            n_samples=0,
        )

    if not os.environ.get("ANTHROPIC_API_KEY"):
        logger.info(
            "baseline skipped — ANTHROPIC_API_KEY not set; dataset=%s n=%d",
            dataset_name,
            len(eval_clauses),
        )
        return _skip_report(
            reason="no_api_key",
            dataset_name=dataset_name,
            n_samples=len(eval_clauses),
        )

    findings = await _detect(eval_clauses)
    predictions, labels = _align_predictions(findings, eval_clauses)
    return _build_report(dataset_name, eval_clauses, predictions, labels)


def run_baseline(
    dataset_name: str = "all",
    n_samples: int = 200,
    seed: int = 42,
) -> Dict[str, Any]:
    """Compute the baseline report synchronously.

    Args:
        dataset_name: One of ``{"seed", "unfair_tos", "opp115", "all"}``.
        n_samples: Cap on the number of clauses run through the detector.
        seed: Deterministic sampling seed (used by ``load_dataset``).

    Returns:
        Baseline report dict. Includes ``status="skipped"`` and reason if
        we couldn't actually run end-to-end.
    """
    # ``seed`` is forwarded by ``load_dataset`` only when ``max_rows`` is
    # set; the parameter is kept in the signature for API symmetry with
    # downstream tools that pass a seed.
    return asyncio.run(_run_baseline_async(dataset_name, n_samples, seed))


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Compute the Cohen's kappa baseline for the LLM detector."
    )
    parser.add_argument(
        "--dataset",
        default="all",
        choices=("seed", "unfair_tos", "opp115", "all"),
    )
    parser.add_argument("--n", type=int, default=200)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("evals/baseline.json"),
        help="Path to write the baseline report (default: evals/baseline.json).",
    )
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    report = run_baseline(
        dataset_name=args.dataset,
        n_samples=args.n,
        seed=args.seed,
    )

    if report.get("status") == "skipped":
        print(f"baseline skipped — {report.get('reason')}")
        # Still write a skip marker if explicitly requested? No — better
        # to leave the baseline file untouched than to overwrite with a
        # skip record. CI uses the file's existence as a signal.
        return 0

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"wrote baseline to {args.out}")
    print(
        f"  dataset={report['dataset']} n={report['n_samples']} "
        f"severity_kappa={report['severity_kappa']:.4f} "
        f"({report['severity_kappa_interpretation']})"
    )
    print(f"  macro_kappa={report['macro_kappa']:.4f}")
    print(f"  category_kappa={report['category_kappa']:.4f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = ["run_baseline", "main"]
