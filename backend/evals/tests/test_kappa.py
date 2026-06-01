"""Tests for evals.metrics.kappa.

Cross-checked against ``sklearn.metrics.cohen_kappa_score`` when sklearn
is importable — if not, the tests use the hardcoded values we computed by
hand. The sklearn path is the source of truth; the hardcoded path exists
so this file can still run in stripped-down CI environments.
"""

from __future__ import annotations

import sys
from pathlib import Path

_BACKEND_DIR = Path(__file__).resolve().parents[2]
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

import pytest  # noqa: E402

from evals.metrics import kappa as kappa_mod  # noqa: E402


try:
    from sklearn.metrics import cohen_kappa_score  # type: ignore

    HAS_SKLEARN = True
except ImportError:  # pragma: no cover
    HAS_SKLEARN = False


# --------------------------------------------------------------------------- #
# Edge cases                                                                  #
# --------------------------------------------------------------------------- #


def test_empty_input_returns_zero():
    assert kappa_mod.cohens_kappa([], []) == 0.0


def test_length_mismatch_raises():
    with pytest.raises(ValueError):
        kappa_mod.cohens_kappa(["a"], ["a", "b"])


def test_perfect_agreement_is_one():
    r1 = ["critical", "high", "medium", "low", "high"]
    r2 = ["critical", "high", "medium", "low", "high"]
    assert kappa_mod.cohens_kappa(r1, r2) == pytest.approx(1.0)


def test_perfect_disagreement_is_negative_or_zero():
    # Every pair disagrees; kappa should be <= 0.
    r1 = ["yes", "no", "yes", "no"]
    r2 = ["no", "yes", "no", "yes"]
    k = kappa_mod.cohens_kappa(r1, r2)
    assert k <= 0.0


def test_all_same_label_both_raters_returns_one():
    # Po = 1, Pe = 1 — we treat this as perfect agreement.
    r1 = ["high"] * 10
    r2 = ["high"] * 10
    assert kappa_mod.cohens_kappa(r1, r2) == pytest.approx(1.0)


def test_random_independent_ratings_near_zero():
    # Construct an example where Po == Pe exactly so kappa == 0.
    # r1 has 4 yes / 4 no; r2 ALSO has 4 yes / 4 no.
    # We arrange the agreements so Po = 0.5 and marginals are 0.5/0.5,
    # giving Pe = 0.5 → kappa = 0.
    r1 = ["yes", "yes", "yes", "yes", "no", "no", "no", "no"]
    r2 = ["yes", "yes", "no", "no", "yes", "yes", "no", "no"]
    k = kappa_mod.cohens_kappa(r1, r2)
    assert abs(k) < 0.01


# --------------------------------------------------------------------------- #
# Comparison to sklearn                                                       #
# --------------------------------------------------------------------------- #


@pytest.mark.skipif(not HAS_SKLEARN, reason="sklearn not installed")
def test_matches_sklearn_on_known_case_a():
    r1 = ["critical", "high", "medium", "low", "high", "critical"]
    r2 = ["critical", "medium", "medium", "low", "high", "low"]
    expected = cohen_kappa_score(r1, r2)
    assert kappa_mod.cohens_kappa(r1, r2) == pytest.approx(expected, abs=1e-9)


@pytest.mark.skipif(not HAS_SKLEARN, reason="sklearn not installed")
def test_matches_sklearn_on_known_case_b():
    # Bigger example with all four severities + repetition.
    r1 = ["critical"] * 5 + ["high"] * 5 + ["medium"] * 5 + ["low"] * 5
    r2 = (
        ["critical"] * 4
        + ["high"] * 1
        + ["high"] * 3
        + ["medium"] * 2
        + ["medium"] * 4
        + ["low"] * 1
        + ["low"] * 5
    )
    expected = cohen_kappa_score(r1, r2)
    assert kappa_mod.cohens_kappa(r1, r2) == pytest.approx(expected, abs=1e-9)


def test_matches_hardcoded_when_sklearn_missing():
    """Hardcoded reference value computed by hand (and verified against
    sklearn during development). Lives outside the sklearn-skip branch
    so it always runs."""
    r1 = ["a", "a", "a", "b", "b"]
    r2 = ["a", "a", "b", "b", "b"]
    # N=5, agreements=4 → Po = 0.8
    # marginals r1: a=3/5, b=2/5;  r2: a=2/5, b=3/5
    # Pe = (3/5 * 2/5) + (2/5 * 3/5) = 6/25 + 6/25 = 12/25 = 0.48
    # kappa = (0.8 - 0.48) / (1 - 0.48) = 0.32 / 0.52 ≈ 0.6153846
    expected = (0.8 - 0.48) / (1.0 - 0.48)
    assert kappa_mod.cohens_kappa(r1, r2) == pytest.approx(expected, abs=1e-9)


# --------------------------------------------------------------------------- #
# Per-severity kappa                                                          #
# --------------------------------------------------------------------------- #


def test_kappa_per_severity_shape():
    preds = [{"severity": "critical"}, {"severity": "high"}, {"severity": "low"}]
    labels = [
        {"expected_severity": "critical"},
        {"expected_severity": "high"},
        {"expected_severity": "low"},
    ]
    out = kappa_mod.kappa_per_severity(preds, labels)
    assert set(out.keys()) == {"critical", "high", "medium", "low"}
    # Critical, high, low rows agree perfectly and each has support in both
    # raters → kappa = 1.0 for those classes.
    assert out["critical"] == pytest.approx(1.0)
    assert out["high"] == pytest.approx(1.0)
    assert out["low"] == pytest.approx(1.0)
    # No medium examples in EITHER rater → kappa is UNDEFINED (None), not a
    # fake 1.0 that would later read as a regression once medium appears.
    assert out["medium"] is None


def test_macro_kappa_is_mean():
    d = {"critical": 0.8, "high": 0.6, "medium": 0.4, "low": 0.2}
    assert kappa_mod.macro_kappa(d) == pytest.approx(0.5)


def test_macro_kappa_empty_dict_is_zero():
    assert kappa_mod.macro_kappa({}) == 0.0


# --------------------------------------------------------------------------- #
# Landis-Koch interpretation                                                  #
# --------------------------------------------------------------------------- #


def test_landis_koch_buckets():
    assert kappa_mod.landis_koch(-0.1) == "poor"
    assert kappa_mod.landis_koch(0.10) == "slight"
    assert kappa_mod.landis_koch(0.30) == "fair"
    assert kappa_mod.landis_koch(0.50) == "moderate"
    assert kappa_mod.landis_koch(0.70) == "substantial"
    assert kappa_mod.landis_koch(0.90) == "almost_perfect"
    # Boundary checks against the original Landis-Koch breakpoints.
    assert kappa_mod.landis_koch(0.0) == "slight"
    assert kappa_mod.landis_koch(0.20) == "slight"
    assert kappa_mod.landis_koch(0.40) == "fair"
    assert kappa_mod.landis_koch(0.60) == "moderate"
    assert kappa_mod.landis_koch(0.80) == "substantial"
    assert kappa_mod.landis_koch(1.0) == "almost_perfect"


# --------------------------------------------------------------------------- #
# confusion_with_kappa                                                        #
# --------------------------------------------------------------------------- #


def test_confusion_with_kappa_shape():
    preds = [
        {"severity": "critical", "risk_category": "rights"},
        {"severity": "high", "risk_category": "liability"},
        {"severity": "medium", "risk_category": "modification"},
        {"severity": "low", "risk_category": "content"},
    ]
    labels = [
        {"expected_severity": "critical", "expected_risk_category": "rights"},
        {"expected_severity": "high", "expected_risk_category": "liability"},
        {"expected_severity": "low", "expected_risk_category": "modification"},
        {"expected_severity": "low", "expected_risk_category": "content"},
    ]
    out = kappa_mod.confusion_with_kappa(preds, labels)
    assert out["n"] == 4
    assert "overall_kappa" in out
    assert "overall_kappa_interpretation" in out
    assert "per_severity_kappa" in out
    assert "macro_kappa" in out
    assert "confusion_matrix" in out
    assert isinstance(out["confusion_matrix"], dict)
    # The matrix rows must include the four severities.
    assert {"critical", "high", "medium", "low"}.issubset(
        set(out["confusion_matrix"].keys())
    )


def test_category_kappa_runs():
    preds = [{"risk_category": "liability"}, {"risk_category": "content"}]
    labels = [
        {"expected_risk_category": "liability"},
        {"expected_risk_category": "content"},
    ]
    # Identical pairs → kappa is well-defined and equal to 1.0 (single category each).
    k = kappa_mod.category_kappa(preds, labels)
    assert k == pytest.approx(1.0)


# --------------------------------------------------------------------------- #
# None-handling                                                               #
# --------------------------------------------------------------------------- #


def test_none_severity_treated_as_separate_bucket():
    # Predictor flagged nothing on half the dataset (severity=None);
    # gold has labels. kappa should still be computable.
    preds = [{"severity": None}, {"severity": None}, {"severity": "high"}]
    labels = [
        {"expected_severity": "low"},
        {"expected_severity": "medium"},
        {"expected_severity": "high"},
    ]
    out = kappa_mod.kappa_per_severity(preds, labels)
    # "high" class agrees on 1 of 3, disagrees on 0 — should be positive
    # (because both raters have 1 "yes" on the same row, both have 2 "no"
    # on the others). sklearn would give kappa = 1.0 here.
    assert out["high"] == pytest.approx(1.0)
