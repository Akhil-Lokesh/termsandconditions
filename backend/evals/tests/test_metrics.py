"""Tests for evals.metrics. Pure stdlib, no Claude calls."""

from __future__ import annotations

import sys
from pathlib import Path

# Make `backend/` importable so `from evals import metrics` works even when
# pytest is invoked with different rootdirs.
_BACKEND_DIR = Path(__file__).resolve().parents[2]
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

import pytest  # noqa: E402

from evals import metrics  # noqa: E402


def _label(cid: str, sev: str, cat: str = "other") -> dict:
    return {
        "clause_id": cid,
        "expected_severity": sev,
        "expected_risk_category": cat,
    }


def _pred(cid: str, sev, cat=None) -> dict:
    return {"clause_id": cid, "severity": sev, "risk_category": cat}


# --------------------------------------------------------------------------- #
# precision_recall_by_severity                                                #
# --------------------------------------------------------------------------- #


def test_perfect_predictions_yield_unit_metrics():
    labels = [
        _label("a", "critical"),
        _label("b", "high"),
        _label("c", "medium"),
        _label("d", "low"),
    ]
    preds = [
        _pred("a", "critical"),
        _pred("b", "high"),
        _pred("c", "medium"),
        _pred("d", "low"),
    ]
    out = metrics.precision_recall_by_severity(preds, labels)
    for sev in metrics.SEVERITIES:
        assert out["per_severity"][sev]["precision"] == 1.0
        assert out["per_severity"][sev]["recall"] == 1.0
        assert out["per_severity"][sev]["f1"] == 1.0
    assert out["macro"]["f1"] == 1.0
    assert out["micro"]["f1"] == 1.0
    assert out["n"] == 4


def test_all_wrong_predictions_yield_zero_metrics():
    labels = [_label("a", "critical"), _label("b", "high")]
    preds = [_pred("a", "low"), _pred("b", "medium")]
    out = metrics.precision_recall_by_severity(preds, labels)
    for sev in metrics.SEVERITIES:
        assert out["per_severity"][sev]["f1"] == 0.0
    assert out["macro"]["f1"] == 0.0
    assert out["micro"]["f1"] == 0.0


def test_unpredicted_clauses_count_as_false_negatives():
    labels = [_label("a", "high"), _label("b", "medium")]
    preds = [_pred("a", None), _pred("b", None)]
    out = metrics.precision_recall_by_severity(preds, labels)
    assert out["per_severity"]["high"]["fn"] == 1
    assert out["per_severity"]["high"]["tp"] == 0
    assert out["per_severity"]["medium"]["fn"] == 1
    assert out["micro"]["recall"] == 0.0
    # No predictions = no FPs either, so precision is 0/0 -> 0.0 (safe div)
    assert out["micro"]["precision"] == 0.0


def test_invalid_severity_label_treated_as_missing():
    labels = [_label("a", "high"), _label("b", "ULTRA")]
    preds = [_pred("a", "high"), _pred("b", "critical")]
    out = metrics.precision_recall_by_severity(preds, labels)
    assert out["per_severity"]["high"]["tp"] == 1
    # "ULTRA" is invalid - label is treated as missing; critical prediction
    # against missing gold is a false positive for "critical".
    assert out["per_severity"]["critical"]["fp"] == 1


def test_length_mismatch_raises():
    with pytest.raises(ValueError):
        metrics.precision_recall_by_severity([_pred("a", "high")], [])


def test_empty_inputs_are_handled():
    out = metrics.precision_recall_by_severity([], [])
    assert out["n"] == 0
    for sev in metrics.SEVERITIES:
        assert out["per_severity"][sev]["support"] == 0
        assert out["per_severity"][sev]["f1"] == 0.0
    assert out["macro"]["f1"] == 0.0
    assert out["micro"]["f1"] == 0.0


# --------------------------------------------------------------------------- #
# confusion_matrix                                                            #
# --------------------------------------------------------------------------- #


def test_confusion_matrix_diagonal_on_perfect_predictions():
    labels = [_label("a", "critical"), _label("b", "low")]
    preds = [_pred("a", "critical"), _pred("b", "low")]
    cm = metrics.confusion_matrix(preds, labels)
    assert cm["critical"]["critical"] == 1
    assert cm["low"]["low"] == 1
    # Everything else is zero.
    for r in cm:
        for c in cm[r]:
            if not (r == c and r in ("critical", "low")):
                assert cm[r][c] == 0


def test_confusion_matrix_records_unpredicted_clauses():
    labels = [_label("a", "high")]
    preds = [_pred("a", None)]
    cm = metrics.confusion_matrix(preds, labels)
    assert cm["high"]["unpredicted"] == 1


def test_confusion_matrix_records_unlabeled_predictions():
    labels = [{"clause_id": "a", "expected_severity": None}]
    preds = [_pred("a", "high")]
    cm = metrics.confusion_matrix(preds, labels)
    assert cm["unlabeled"]["high"] == 1


# --------------------------------------------------------------------------- #
# severity_jaccard                                                            #
# --------------------------------------------------------------------------- #


def test_severity_jaccard_perfect_is_one():
    labels = [_label("a", "high"), _label("b", "low")]
    preds = [_pred("a", "high"), _pred("b", "low")]
    assert metrics.severity_jaccard(preds, labels) == 1.0


def test_severity_jaccard_all_wrong_is_zero():
    labels = [_label("a", "high"), _label("b", "low")]
    preds = [_pred("a", "low"), _pred("b", "high")]
    assert metrics.severity_jaccard(preds, labels) == 0.0


def test_severity_jaccard_empty_inputs():
    assert metrics.severity_jaccard([], []) == 0.0


def test_severity_jaccard_skips_dual_empty_rows():
    labels = [
        {"clause_id": "a", "expected_severity": None},
        _label("b", "high"),
    ]
    preds = [_pred("a", None), _pred("b", "high")]
    # Only one non-empty pair, and it matches -> Jaccard = 1.0
    assert metrics.severity_jaccard(preds, labels) == 1.0


# --------------------------------------------------------------------------- #
# category_recall                                                             #
# --------------------------------------------------------------------------- #


def test_category_recall_perfect():
    labels = [
        _label("a", "high", "termination"),
        _label("b", "low", "privacy"),
    ]
    preds = [
        _pred("a", "high", "termination"),
        _pred("b", "low", "privacy"),
    ]
    out = metrics.category_recall(preds, labels)
    assert out["overall_recall"] == 1.0
    assert out["per_category"]["termination"]["recall"] == 1.0
    assert out["per_category"]["privacy"]["recall"] == 1.0


def test_category_recall_zero_when_all_wrong():
    labels = [_label("a", "high", "termination")]
    preds = [_pred("a", "high", "privacy")]
    out = metrics.category_recall(preds, labels)
    assert out["overall_recall"] == 0.0
    assert out["per_category"]["termination"]["recall"] == 0.0


def test_category_recall_handles_missing_predicted_category():
    labels = [_label("a", "high", "termination")]
    preds = [_pred("a", "high", None)]
    out = metrics.category_recall(preds, labels)
    assert out["overall_recall"] == 0.0


def test_category_recall_empty_inputs():
    out = metrics.category_recall([], [])
    assert out["overall_recall"] == 0.0
    assert out["n_labeled"] == 0
    assert out["per_category"] == {}


def test_category_recall_length_mismatch_raises():
    with pytest.raises(ValueError):
        metrics.category_recall([_pred("a", "high", "privacy")], [])
