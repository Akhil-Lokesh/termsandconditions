"""Eval metrics package.

This used to be a single module (``backend/evals/metrics.py``). Layer 4
turned it into a package so we could add ``kappa.py`` alongside the
existing precision/recall / confusion-matrix helpers without piling
everything into one ~600-line file.

To avoid breaking existing call sites — anything that imports
``from evals import metrics`` and then reaches for
``metrics.precision_recall_by_severity`` / ``metrics.SEVERITIES`` etc. —
the package re-exports the legacy public surface from
:mod:`evals.metrics.severity`. New kappa helpers are addressed
explicitly via :mod:`evals.metrics.kappa`.
"""

from __future__ import annotations

# Re-export the legacy public surface so call sites that predate the
# package split keep working unchanged.
from .severity import (  # noqa: F401  (intentional re-export)
    SEVERITIES,
    SEVERITY_TIER,
    category_recall,
    confusion_matrix,
    false_positive_rate,
    precision_recall_by_severity,
    quadratic_weighted_kappa,
    severity_jaccard,
    severity_mae,
)

__all__ = [
    "SEVERITIES",
    "SEVERITY_TIER",
    "category_recall",
    "confusion_matrix",
    "false_positive_rate",
    "precision_recall_by_severity",
    "quadratic_weighted_kappa",
    "severity_jaccard",
    "severity_mae",
]
