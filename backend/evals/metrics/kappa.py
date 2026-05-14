"""Cohen's kappa and related agreement statistics.

Implemented from scratch in stdlib so the eval harness does not have a
hard runtime dependency on scikit-learn (sklearn is in
``requirements.txt`` but the function-level dependency is reserved for
the unit tests, which compare us to ``sklearn.metrics.cohen_kappa_score``
when the library is installed).

Public surface:

    cohens_kappa(rater1, rater2, categories=None) -> float
        Vanilla unweighted Cohen's kappa between two label sequences.

    kappa_per_severity(predictions, labels) -> dict[str, float]
        One-vs-rest kappa for each of {critical, high, medium, low}.

    macro_kappa(per_severity) -> float
        Mean of the per-severity kappas.

    confusion_with_kappa(predictions, labels) -> dict
        Bundle of confusion matrix + overall kappa + per-severity kappas
        + Landis-Koch verbal interpretation.

Severity / category aliases align with ``evals.metrics.severity``.

Interpretation scale (Landis & Koch 1977):
    < 0.00 : poor
    0.00–0.20 : slight
    0.21–0.40 : fair
    0.41–0.60 : moderate
    0.61–0.80 : substantial
    0.81–1.00 : almost_perfect
"""

from __future__ import annotations

from collections import Counter
from typing import Dict, List, Optional, Sequence


SEVERITIES = ("critical", "high", "medium", "low")


# --------------------------------------------------------------------------- #
# Vanilla Cohen's kappa                                                       #
# --------------------------------------------------------------------------- #


def cohens_kappa(
    rater1: Sequence[str],
    rater2: Sequence[str],
    categories: Optional[Sequence[str]] = None,
) -> float:
    """Unweighted Cohen's kappa between two equal-length rater sequences.

    The formula::

        kappa = (Po - Pe) / (1 - Pe)

    where::

        Po = observed agreement = sum_i [rater1_i == rater2_i] / N
        Pe = expected agreement under independence
           = sum_c (count_c_in_r1 / N) * (count_c_in_r2 / N)

    Edge cases:
      * Empty input returns 0.0.
      * Perfect agreement when Pe == 1.0 returns 1.0 (avoids 0/0 NaN).
      * Inputs of unequal length raise ValueError.

    Args:
        rater1: First rater's labels.
        rater2: Second rater's labels.
        categories: Optional explicit category list. When omitted the
            union of observed labels is used; passing this explicitly
            keeps expected-agreement comparable across runs where some
            categories may be absent.

    Returns:
        Kappa coefficient in [-1, 1]. Sklearn's
        ``cohen_kappa_score`` returns the same value (to floating-point
        precision) on the same inputs.
    """
    if len(rater1) != len(rater2):
        raise ValueError(
            f"rater1 ({len(rater1)}) and rater2 ({len(rater2)}) "
            "must have equal length"
        )

    n = len(rater1)
    if n == 0:
        return 0.0

    # Normalize labels — strings to strings, allow None to be "__none__"
    # bucket so it counts as its own category.
    def _norm(label) -> str:
        if label is None:
            return "__none__"
        return str(label)

    r1 = [_norm(x) for x in rater1]
    r2 = [_norm(x) for x in rater2]

    if categories is None:
        cats = sorted(set(r1) | set(r2))
    else:
        cats = [_norm(c) for c in categories]
        # Make sure every observed label is represented; the formula
        # works regardless but missing categories silently drop terms.
        observed = set(r1) | set(r2)
        for o in observed:
            if o not in cats:
                cats.append(o)

    # Observed agreement.
    matches = sum(1 for a, b in zip(r1, r2) if a == b)
    po = matches / n

    # Expected agreement.
    c1 = Counter(r1)
    c2 = Counter(r2)
    pe = 0.0
    for c in cats:
        pe += (c1.get(c, 0) / n) * (c2.get(c, 0) / n)

    if pe >= 1.0:
        # All ratings are identical AND there is only one category — the
        # raters cannot disagree, so kappa is defined as 1.0 if they
        # agree and conventionally 0.0 if they don't. We agree here
        # because pe == 1 ⟹ po == 1 (everyone in the same bucket).
        return 1.0 if po == 1.0 else 0.0

    return (po - pe) / (1.0 - pe)


# --------------------------------------------------------------------------- #
# Per-severity kappa                                                          #
# --------------------------------------------------------------------------- #


def _extract_severities(
    predictions: List[Dict],
    labels: List[Dict],
) -> tuple[List[str], List[str]]:
    """Return aligned (predicted, expected) severity strings.

    Missing / unknown severities collapse to ``"__none__"`` so kappa
    treats them as a fifth bucket instead of silently dropping them.
    """
    if len(predictions) != len(labels):
        raise ValueError(
            f"predictions ({len(predictions)}) and labels ({len(labels)}) "
            "must be aligned and equal length"
        )
    pred_sev: List[str] = []
    gold_sev: List[str] = []
    for p, l in zip(predictions, labels):
        ps = str(p.get("severity") or "__none__").lower()
        gs = str(l.get("expected_severity") or "__none__").lower()
        pred_sev.append(ps)
        gold_sev.append(gs)
    return pred_sev, gold_sev


def kappa_per_severity(
    predictions: List[Dict],
    labels: List[Dict],
) -> Dict[str, float]:
    """One-vs-rest Cohen's kappa for each severity class.

    For each severity ``s`` in ``{critical, high, medium, low}`` we build
    a binary classification problem ("is this clause ``s``?") and compute
    kappa across all aligned predictions/labels. This is the standard way
    to break down a multi-class kappa per class.

    Returns:
        ``{ "critical": float, "high": float, "medium": float, "low": float }``.
        Missing classes (zero support in both raters) get kappa = 0.0.
    """
    pred_sev, gold_sev = _extract_severities(predictions, labels)
    out: Dict[str, float] = {}
    for s in SEVERITIES:
        r1 = ["yes" if x == s else "no" for x in pred_sev]
        r2 = ["yes" if x == s else "no" for x in gold_sev]
        out[s] = cohens_kappa(r1, r2, categories=("yes", "no"))
    return out


def macro_kappa(per_severity: Dict[str, float]) -> float:
    """Mean of per-severity kappas. Returns 0.0 if the dict is empty."""
    if not per_severity:
        return 0.0
    vals = [v for v in per_severity.values()]
    return sum(vals) / len(vals)


# --------------------------------------------------------------------------- #
# Landis-Koch interpretation                                                  #
# --------------------------------------------------------------------------- #


def landis_koch(kappa: float) -> str:
    """Verbal interpretation of a kappa value (Landis & Koch 1977)."""
    if kappa < 0.0:
        return "poor"
    if kappa <= 0.20:
        return "slight"
    if kappa <= 0.40:
        return "fair"
    if kappa <= 0.60:
        return "moderate"
    if kappa <= 0.80:
        return "substantial"
    return "almost_perfect"


# --------------------------------------------------------------------------- #
# Combined report                                                             #
# --------------------------------------------------------------------------- #


def confusion_with_kappa(
    predictions: List[Dict],
    labels: List[Dict],
) -> Dict:
    """Confusion matrix + overall kappa + per-severity kappa + interpretation.

    Returns a dict like::

        {
            "n": int,
            "overall_kappa": float,
            "overall_kappa_interpretation": str,
            "per_severity_kappa": {"critical": .., "high": ..,
                                   "medium": .., "low": ..},
            "macro_kappa": float,
            "confusion_matrix": {...},   # same shape as evals.metrics.severity
        }
    """
    # Lazy import to avoid forcing the package to import its sibling at
    # module load time (keeps package import cheap).
    from . import severity as _severity_metrics

    pred_sev, gold_sev = _extract_severities(predictions, labels)

    overall = cohens_kappa(
        pred_sev,
        gold_sev,
        categories=tuple(SEVERITIES) + ("__none__",),
    )
    per = kappa_per_severity(predictions, labels)
    return {
        "n": len(predictions),
        "overall_kappa": overall,
        "overall_kappa_interpretation": landis_koch(overall),
        "per_severity_kappa": per,
        "macro_kappa": macro_kappa(per),
        "confusion_matrix": _severity_metrics.confusion_matrix(
            predictions, labels
        ),
    }


# --------------------------------------------------------------------------- #
# Category-axis kappa                                                         #
# --------------------------------------------------------------------------- #


def category_kappa(
    predictions: List[Dict],
    labels: List[Dict],
) -> float:
    """Cohen's kappa over the risk_category axis (full multi-class)."""
    if len(predictions) != len(labels):
        raise ValueError(
            f"predictions ({len(predictions)}) and labels ({len(labels)}) "
            "must be aligned and equal length"
        )
    r1: List[str] = []
    r2: List[str] = []
    for p, l in zip(predictions, labels):
        r1.append(str(p.get("risk_category") or "__none__").lower())
        r2.append(str(l.get("expected_risk_category") or "__none__").lower())
    return cohens_kappa(r1, r2)


__all__ = [
    "SEVERITIES",
    "category_kappa",
    "cohens_kappa",
    "confusion_with_kappa",
    "kappa_per_severity",
    "landis_koch",
    "macro_kappa",
]
