"""
Eval harness CLI for the T&C anomaly detection pipeline.

Usage (from the project root, with backend/venv activated):
    python -m evals.runner \\
        --fixtures backend/evals/fixtures/labeled_clauses.json \\
        --out evals_results.json

The runner:
  1. Loads labeled clauses from `--fixtures`.
  2. Sends them through `LLMClauseDetector.detect_risky_clauses()` in a
     single batch — the same code path the production pipeline uses.
  3. Aligns predictions to labels by `clause_id`.
  4. Computes severity P/R/F1, confusion matrix, severity Jaccard, and
     category recall via `evals.metrics`.
  5. Writes a JSON report to `--out` and prints a one-screen summary.

When `ANTHROPIC_API_KEY` is not set the runner prints a "skipped (no API key)"
note and exits with status 0. This lets CI call it unconditionally without
failing on PRs from forks or environments without secrets.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

# Make `backend/` importable when running from project root or backend dir.
_THIS_DIR = Path(__file__).resolve().parent
_BACKEND_DIR = _THIS_DIR.parent
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

# Local imports — keep below sys.path setup.
try:
    from evals import metrics as eval_metrics
except ImportError:  # pragma: no cover - exercised only when run as a script
    import metrics as eval_metrics  # type: ignore[no-redef]


def _load_fixtures(path: Path) -> List[Dict[str, Any]]:
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, list):
        return data
    if isinstance(data, dict) and "clauses" in data:
        return data["clauses"]
    raise ValueError(
        f"Fixtures file {path} must be a list or an object with a 'clauses' key"
    )


def _to_detector_input(labeled: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Translate fixture entries to LLMClauseDetector's expected input shape."""
    return [
        {
            "clause_number": item["clause_id"],
            "section": item.get("section", "Unknown"),
            "text": item["text"],
        }
        for item in labeled
    ]


def _align(
    findings: List[Dict[str, Any]],
    labeled: List[Dict[str, Any]],
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Build per-label prediction list aligned by clause_id.

    A clause that the LLM did not flag becomes a prediction with severity=None.
    """
    finding_by_id = {str(f.get("clause_number")): f for f in findings}
    preds: List[Dict[str, Any]] = []
    labels: List[Dict[str, Any]] = []
    for item in labeled:
        cid = str(item["clause_id"])
        f = finding_by_id.get(cid, {})
        preds.append(
            {
                "clause_id": cid,
                "severity": f.get("severity"),
                "risk_category": f.get("risk_category"),
                "explanation": f.get("explanation"),
            }
        )
        labels.append(
            {
                "clause_id": cid,
                "expected_severity": item.get("expected_severity"),
                "expected_risk_category": item.get("expected_risk_category"),
            }
        )
    return preds, labels


def _compute_report(
    predictions: List[Dict[str, Any]],
    labels: List[Dict[str, Any]],
) -> Dict[str, Any]:
    return {
        "n_examples": len(labels),
        "precision_recall_by_severity": eval_metrics.precision_recall_by_severity(
            predictions, labels
        ),
        "confusion_matrix": eval_metrics.confusion_matrix(predictions, labels),
        "severity_jaccard": eval_metrics.severity_jaccard(predictions, labels),
        "category_recall": eval_metrics.category_recall(predictions, labels),
    }


def _print_summary(report: Dict[str, Any]) -> None:
    pr = report["precision_recall_by_severity"]
    print("=" * 60)
    print(f"T&C eval harness  -  n={report['n_examples']}")
    print("=" * 60)
    print(f"{'severity':<10} {'precision':>10} {'recall':>10} {'f1':>10} {'support':>8}")
    for sev in ("critical", "high", "medium", "low"):
        m = pr["per_severity"][sev]
        print(
            f"{sev:<10} {m['precision']:>10.3f} {m['recall']:>10.3f} "
            f"{m['f1']:>10.3f} {m['support']:>8}"
        )
    print("-" * 60)
    print(
        f"{'macro':<10} {pr['macro']['precision']:>10.3f} "
        f"{pr['macro']['recall']:>10.3f} {pr['macro']['f1']:>10.3f}"
    )
    print(
        f"{'micro':<10} {pr['micro']['precision']:>10.3f} "
        f"{pr['micro']['recall']:>10.3f} {pr['micro']['f1']:>10.3f}"
    )
    print(f"severity jaccard: {report['severity_jaccard']:.3f}")
    print(
        f"category recall:  {report['category_recall']['overall_recall']:.3f} "
        f"(n_labeled={report['category_recall']['n_labeled']})"
    )
    print("=" * 60)


async def _run_detection(
    labeled: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Run a single LLM batch against the labeled clauses."""
    # Imported lazily so `--help` and the no-API-key path don't pull in
    # the full backend dependency graph.
    from app.core.llm_clause_detector import LLMClauseDetector
    from app.services.claude_service import ClaudeService

    claude = ClaudeService()
    detector = LLMClauseDetector(claude)
    detector_input = _to_detector_input(labeled)
    return await detector.detect_risky_clauses(
        detector_input,
        company_name="EvalHarness",
        service_type="general",
    )


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run the T&C anomaly detection eval harness."
    )
    parser.add_argument(
        "--fixtures",
        type=Path,
        default=_THIS_DIR / "fixtures" / "labeled_clauses.json",
        help="Path to the labeled clauses JSON file.",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("evals_results.json"),
        help="Where to write the JSON evaluation report.",
    )
    parser.add_argument(
        "--skip-without-api-key",
        action="store_true",
        default=True,
        help="(default) Exit 0 with a skip note if ANTHROPIC_API_KEY is missing.",
    )
    args = parser.parse_args(argv)

    if not args.fixtures.exists():
        print(f"ERROR: fixtures file not found: {args.fixtures}", file=sys.stderr)
        return 2

    labeled = _load_fixtures(args.fixtures)
    print(f"Loaded {len(labeled)} labeled clauses from {args.fixtures}")

    if not os.environ.get("ANTHROPIC_API_KEY"):
        message = (
            "ANTHROPIC_API_KEY not set - skipped (no API key). "
            "Set the env var to run end-to-end against Claude."
        )
        print(message)
        skip_report = {
            "status": "skipped",
            "reason": "no_api_key",
            "message": message,
            "n_examples": len(labeled),
        }
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(skip_report, indent=2), encoding="utf-8")
        return 0

    try:
        findings = asyncio.run(_run_detection(labeled))
    except Exception as exc:  # noqa: BLE001 - surface any failure to CI
        print(f"ERROR: detection run failed: {exc}", file=sys.stderr)
        return 1

    predictions, labels = _align(findings, labeled)
    report = _compute_report(predictions, labels)
    report["raw_findings_count"] = len(findings)
    report["predictions"] = predictions

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"Wrote report to {args.out}")
    _print_summary(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
