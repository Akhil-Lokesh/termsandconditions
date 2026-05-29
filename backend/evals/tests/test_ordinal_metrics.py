"""Tests for the ordinal severity metrics (A1) and false-positive rate (A2).

These address the kappa base-rate paradox documented in BENCHMARK.md: unweighted
Cohen's kappa collapses when both raters concentrate on one tier, even at high
raw agreement. Quadratic-weighted kappa (QWK) + MAE are the fair ordinal
alternatives. false_positive_rate measures precision against fair negatives.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from evals.metrics import (  # noqa: E402
    false_positive_rate,
    quadratic_weighted_kappa,
    severity_mae,
)
from evals.metrics.kappa import cohens_kappa  # noqa: E402


def _p(sev):
    return {"clause_id": "x", "severity": sev}


def _l(sev):
    return {"clause_id": "x", "expected_severity": sev}


def test_qwk_perfect_agreement_is_one():
    preds = [_p("high"), _p("medium"), _p("medium")]
    labels = [_l("high"), _l("medium"), _l("medium")]
    assert quadratic_weighted_kappa(preds, labels) == 1.0


def test_qwk_exceeds_unweighted_kappa_on_ordinal_near_errors():
    # A VARYING predictor whose errors are all one tier away. Unweighted kappa
    # treats every error as a total miss; QWK rewards the near-misses, so QWK
    # should be strictly higher than unweighted kappa on the same data.
    pred_sevs = ["high", "medium", "medium", "low", "medium", "high"]
    gold_sevs = ["high", "medium", "high", "low", "medium", "medium"]
    preds = [_p(s) for s in pred_sevs]
    labels = [_l(s) for s in gold_sevs]

    qwk = quadratic_weighted_kappa(preds, labels)
    unweighted = cohens_kappa(pred_sevs, gold_sevs)

    assert qwk > unweighted, f"QWK {qwk} should beat unweighted {unweighted}"
    assert 0.0 < qwk < 1.0


def test_qwk_is_zero_for_constant_predictor():
    # A rater that always says "medium" carries no information; kappa (weighted
    # or not) is 0 by definition. Documents this as expected, not a bug.
    preds = [_p("medium")] * 10 + [_p("medium")] * 4
    labels = [_l("medium")] * 10 + [_l("high")] * 4
    assert quadratic_weighted_kappa(preds, labels) == 0.0


def test_qwk_punishes_far_misses_more_than_near():
    near = quadratic_weighted_kappa([_p("medium")] * 3 + [_p("high")],
                                    [_l("medium")] * 3 + [_l("medium")])
    far = quadratic_weighted_kappa([_p("medium")] * 3 + [_p("none")],
                                   [_l("medium")] * 3 + [_l("critical")])
    assert far < near  # a 4-tier miss hurts more than a 1-tier miss


def test_qwk_excludes_gold_none_clauses():
    # gold "none" rows are not risk-bearing -> excluded from QWK population.
    preds = [_p("high"), _p("high")]
    labels = [_l("high"), _l("none")]
    # Only the first pair (high/high) is scored -> perfect.
    assert quadratic_weighted_kappa(preds, labels) == 1.0


def test_mae_counts_missed_clause_as_max_distance():
    # Detector did not flag a gold-HIGH clause (severity None -> "none" tier 0).
    preds = [{"clause_id": "x", "severity": None}]
    labels = [_l("high")]  # high = tier 3 ; none = tier 0 -> distance 3
    assert severity_mae(preds, labels) == 3.0


def test_mae_zero_on_perfect():
    assert severity_mae([_p("medium")], [_l("medium")]) == 0.0


def test_false_positive_rate_on_fair_negatives():
    preds = [_p("high"), _p(None), _p("medium"), _p(None)]
    labels = [_l("none"), _l("none"), _l("none"), _l("high")]
    # 3 fair negatives (gold none); detector flagged 2 of them (high, medium).
    out = false_positive_rate(preds, labels)
    assert out["n_negatives"] == 3
    assert out["false_positives"] == 2
    assert abs(out["false_positive_rate"] - 2 / 3) < 1e-9


def test_false_positive_rate_no_negatives_is_zero():
    # All-positives set (like raw UNFAIR-ToS) -> FP rate undefined, returns 0.
    out = false_positive_rate([_p("high")], [_l("high")])
    assert out["n_negatives"] == 0
    assert out["false_positive_rate"] == 0.0


def test_bootstrap_ci_brackets_point_estimate():
    from evals.metrics.bootstrap import bootstrap_ci
    preds = [_p("high"), _p("medium"), _p("medium"), _p("low")] * 8
    labels = [_l("high"), _l("medium"), _l("high"), _l("low")] * 8
    out = bootstrap_ci(quadratic_weighted_kappa, preds, labels, n_resamples=300, seed=1)
    assert out["n"] == len(labels)
    assert out["lo"] <= out["point"] <= out["hi"]


def test_bootstrap_ci_empty_is_safe():
    from evals.metrics.bootstrap import bootstrap_ci
    out = bootstrap_ci(quadratic_weighted_kappa, [], [], n_resamples=10)
    assert out["n"] == 0 and out["lo"] == out["hi"]
