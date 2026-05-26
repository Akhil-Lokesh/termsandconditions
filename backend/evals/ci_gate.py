"""CI regression gate — compares a current eval run against the committed baseline.

The gate fails if ANY per-severity kappa (or the overall severity kappa,
or the macro kappa) drops by more than ``max_kappa_regression`` (default
0.03). Improvements never fail; only regressions do.

A "no current data" / "no baseline data" result is treated as a SKIP, not
a regression — we don't want CI to fail when the baseline file simply
hasn't been committed yet or when the run was skipped for missing API
keys. CI scripts can either accept the skip or use ``--strict`` to upgrade
skips to failures.

CLI::

    python -m evals.ci_gate --current results.json --baseline evals/baseline.json
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class _KappaDelta:
    name: str
    baseline: float
    current: float

    @property
    def delta(self) -> float:
        return self.current - self.baseline

    @property
    def is_regression(self) -> bool:
        # Negative delta means current < baseline.
        return self.delta < 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "baseline": self.baseline,
            "current": self.current,
            "delta": self.delta,
        }


def _gather_kappa_axes(report: Dict[str, Any]) -> Dict[str, float]:
    """Return ``{axis_name: kappa_value}`` for all kappa axes in a report.

    Tolerates missing keys (returns the partial set) so this works on
    both full and partial reports.
    """
    out: Dict[str, float] = {}
    if "severity_kappa" in report and isinstance(
        report["severity_kappa"], (int, float)
    ):
        out["severity_kappa"] = float(report["severity_kappa"])
    if "macro_kappa" in report and isinstance(
        report["macro_kappa"], (int, float)
    ):
        out["macro_kappa"] = float(report["macro_kappa"])
    if "category_kappa" in report and isinstance(
        report["category_kappa"], (int, float)
    ):
        out["category_kappa"] = float(report["category_kappa"])
    per = report.get("per_severity_kappa") or {}
    if isinstance(per, dict):
        for sev, val in per.items():
            if isinstance(val, (int, float)):
                out[f"per_severity_kappa.{sev}"] = float(val)
    return out


def check_against_baseline(
    current_results_path: Path,
    baseline_path: Path,
    max_kappa_regression: float = 0.03,
) -> Dict[str, Any]:
    """Compare ``current_results_path`` to ``baseline_path``.

    Args:
        current_results_path: JSON file produced by ``baseline_runner``
            on the CURRENT commit (the PR's would-be merge).
        baseline_path: JSON file committed at HEAD of main (or wherever
            CI looks for the gold baseline).
        max_kappa_regression: Maximum permitted drop on ANY single kappa
            axis. A delta worse than ``-max_kappa_regression`` is a
            regression.

    Returns:
        Result dict with keys::

            {
                "passed": bool,
                "skipped": bool,
                "reason": str,            # "ok" | reason for skip
                "regressions": [ ... ],
                "improvements": [ ... ],
                "summary": "human string",
            }
    """
    current_path = Path(current_results_path)
    base_path = Path(baseline_path)

    if not base_path.exists():
        return {
            "passed": True,
            "skipped": True,
            "reason": f"baseline file missing: {base_path}",
            "regressions": [],
            "improvements": [],
            "summary": (
                f"skipped — baseline file missing at {base_path}. Commit a "
                "baseline run first via `python -m evals.baseline_runner`."
            ),
        }
    if not current_path.exists():
        return {
            "passed": True,
            "skipped": True,
            "reason": f"current results file missing: {current_path}",
            "regressions": [],
            "improvements": [],
            "summary": (
                f"skipped — current results file missing at {current_path}."
            ),
        }

    try:
        baseline = json.loads(base_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return {
            "passed": False,
            "skipped": False,
            "reason": f"baseline JSON malformed: {exc}",
            "regressions": [],
            "improvements": [],
            "summary": f"baseline file unreadable: {exc}",
        }
    try:
        current = json.loads(current_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return {
            "passed": False,
            "skipped": False,
            "reason": f"current JSON malformed: {exc}",
            "regressions": [],
            "improvements": [],
            "summary": f"current file unreadable: {exc}",
        }

    # Skip-aware paths — either side may legitimately be a skip record.
    if baseline.get("status") == "skipped":
        return {
            "passed": True,
            "skipped": True,
            "reason": f"baseline was a skip record: {baseline.get('reason')}",
            "regressions": [],
            "improvements": [],
            "summary": (
                "skipped — baseline file holds a skip record "
                f"({baseline.get('reason')})."
            ),
        }
    if current.get("status") == "skipped":
        return {
            "passed": True,
            "skipped": True,
            "reason": f"current run was skipped: {current.get('reason')}",
            "regressions": [],
            "improvements": [],
            "summary": (
                "skipped — current run is a skip record "
                f"({current.get('reason')})."
            ),
        }

    base_axes = _gather_kappa_axes(baseline)
    cur_axes = _gather_kappa_axes(current)

    if not base_axes or not cur_axes:
        return {
            "passed": True,
            "skipped": True,
            "reason": "no kappa axes present on one or both reports",
            "regressions": [],
            "improvements": [],
            "summary": "skipped — neither report exposes kappa fields.",
        }

    regressions: List[Dict[str, Any]] = []
    improvements: List[Dict[str, Any]] = []

    for axis, baseline_val in base_axes.items():
        if axis not in cur_axes:
            continue
        delta = _KappaDelta(axis, baseline_val, cur_axes[axis])
        if delta.delta < -max_kappa_regression:
            regressions.append(delta.to_dict())
        elif delta.delta > 0.0:
            improvements.append(delta.to_dict())

    passed = len(regressions) == 0
    if passed:
        summary = (
            f"PASS — {len(improvements)} improvements, no kappa regression "
            f"beyond -{max_kappa_regression:.3f}."
        )
    else:
        worst = min(regressions, key=lambda r: r["delta"])
        summary = (
            f"FAIL — {len(regressions)} regression(s); worst on "
            f"{worst['name']}: {worst['baseline']:.4f} → "
            f"{worst['current']:.4f} (delta {worst['delta']:+.4f})."
        )

    return {
        "passed": passed,
        "skipped": False,
        "reason": "ok" if passed else "regression",
        "regressions": regressions,
        "improvements": improvements,
        "summary": summary,
        "max_kappa_regression": max_kappa_regression,
    }


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="CI regression gate for Cohen's kappa baselines."
    )
    parser.add_argument("--current", type=Path, required=True)
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument(
        "--max-regression",
        type=float,
        default=0.03,
        help="Maximum permitted kappa drop on any axis (default 0.03).",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Treat skip cases as failures (default: pass on skip).",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Optional path to write the verdict JSON.",
    )
    args = parser.parse_args(argv)

    verdict = check_against_baseline(
        current_results_path=args.current,
        baseline_path=args.baseline,
        max_kappa_regression=args.max_regression,
    )

    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(verdict, indent=2), encoding="utf-8")
    print(verdict["summary"])
    if verdict["regressions"]:
        print("regressions:")
        for r in verdict["regressions"]:
            print(
                f"  {r['name']}: {r['baseline']:.4f} → "
                f"{r['current']:.4f} (delta {r['delta']:+.4f})"
            )
    if verdict["improvements"]:
        print("improvements:")
        for r in verdict["improvements"]:
            print(
                f"  {r['name']}: {r['baseline']:.4f} → "
                f"{r['current']:.4f} (delta {r['delta']:+.4f})"
            )

    if not verdict["passed"]:
        return 1
    if verdict["skipped"] and args.strict:
        print("--strict: skip treated as failure")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = ["check_against_baseline", "main"]
