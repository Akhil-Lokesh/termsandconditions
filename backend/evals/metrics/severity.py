"""
Evaluation metrics for the T&C anomaly detection pipeline.

Pure stdlib so the harness stays portable and CI-friendly. Predictions and
labels are aligned by `clause_id` upstream in the runner — these functions
expect already-aligned lists of equal length.

Each `prediction` and `label` dict is expected to expose:
    - clause_id: str (used for alignment by the runner)
    - severity: str in {"critical", "high", "medium", "low"}  (predictions only)
    - expected_severity: str (labels only)
    - risk_category: str (predictions only)
    - expected_risk_category: str (labels only)

A prediction with severity == None or missing means "not flagged by the
detector". For severity P/R/F1 we treat that as the prediction belonging to
no severity class (i.e. it cannot count as a TP for any class).

Layer-4 note
------------
This module used to live at ``backend/evals/metrics.py``. Layer 4 turned
``evals.metrics`` into a package (to host ``kappa.py``); the package
``__init__`` re-exports every public symbol from here so all existing
``from evals import metrics`` callers keep working unchanged.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple

SEVERITIES: Tuple[str, ...] = ("critical", "high", "medium", "low")


def _pred_sev(p: Dict) -> Optional[str]:
    sev = p.get("severity")
    if sev is None:
        return None
    sev = str(sev).lower()
    return sev if sev in SEVERITIES else None


def _label_sev(label: Dict) -> Optional[str]:
    sev = label.get("expected_severity")
    if sev is None:
        return None
    sev = str(sev).lower()
    return sev if sev in SEVERITIES else None


def _safe_div(numerator: float, denominator: float) -> float:
    return numerator / denominator if denominator else 0.0


def precision_recall_by_severity(
    predictions: List[Dict], labels: List[Dict]
) -> Dict:
    """Per-severity precision/recall/F1 plus macro and micro aggregates.

    Returns a dict shaped like:
        {
            "per_severity": {
                "critical": {"precision": .., "recall": .., "f1": ..,
                              "tp": int, "fp": int, "fn": int, "support": int},
                ...
            },
            "macro": {"precision": .., "recall": .., "f1": ..},
            "micro": {"precision": .., "recall": .., "f1": ..},
            "n": int,
        }
    """
    if len(predictions) != len(labels):
        raise ValueError(
            f"predictions ({len(predictions)}) and labels ({len(labels)}) "
            "must be aligned and equal length"
        )

    per: Dict[str, Dict[str, float]] = {
        s: {"tp": 0, "fp": 0, "fn": 0, "support": 0} for s in SEVERITIES
    }

    for pred, label in zip(predictions, labels):
        gold = _label_sev(label)
        guess = _pred_sev(pred)
        if gold is not None:
            per[gold]["support"] += 1
        if guess is not None and gold is not None and guess == gold:
            per[guess]["tp"] += 1
        else:
            if guess is not None:
                per[guess]["fp"] += 1
            if gold is not None:
                per[gold]["fn"] += 1

    out_per: Dict[str, Dict[str, float]] = {}
    for s in SEVERITIES:
        tp = per[s]["tp"]
        fp = per[s]["fp"]
        fn = per[s]["fn"]
        precision = _safe_div(tp, tp + fp)
        recall = _safe_div(tp, tp + fn)
        f1 = _safe_div(2 * precision * recall, precision + recall)
        out_per[s] = {
            "precision": precision,
            "recall": recall,
            "f1": f1,
            "tp": tp,
            "fp": fp,
            "fn": fn,
            "support": per[s]["support"],
        }

    macro_p = sum(out_per[s]["precision"] for s in SEVERITIES) / len(SEVERITIES)
    macro_r = sum(out_per[s]["recall"] for s in SEVERITIES) / len(SEVERITIES)
    macro_f1 = _safe_div(2 * macro_p * macro_r, macro_p + macro_r)

    total_tp = sum(out_per[s]["tp"] for s in SEVERITIES)
    total_fp = sum(out_per[s]["fp"] for s in SEVERITIES)
    total_fn = sum(out_per[s]["fn"] for s in SEVERITIES)
    micro_p = _safe_div(total_tp, total_tp + total_fp)
    micro_r = _safe_div(total_tp, total_tp + total_fn)
    micro_f1 = _safe_div(2 * micro_p * micro_r, micro_p + micro_r)

    return {
        "per_severity": out_per,
        "macro": {"precision": macro_p, "recall": macro_r, "f1": macro_f1},
        "micro": {"precision": micro_p, "recall": micro_r, "f1": micro_f1},
        "n": len(labels),
    }


def confusion_matrix(predictions: List[Dict], labels: List[Dict]) -> Dict:
    """4x4 confusion matrix as a nested dict: matrix[gold][predicted] = count.

    A row for "unlabeled" or column for "unpredicted" is included so the
    matrix accounts for predictions/labels outside the 4 severities (e.g.,
    the detector did not flag the clause).
    """
    if len(predictions) != len(labels):
        raise ValueError(
            f"predictions ({len(predictions)}) and labels ({len(labels)}) "
            "must be aligned and equal length"
        )

    rows = list(SEVERITIES) + ["unlabeled"]
    cols = list(SEVERITIES) + ["unpredicted"]
    matrix: Dict[str, Dict[str, int]] = {r: {c: 0 for c in cols} for r in rows}

    for pred, label in zip(predictions, labels):
        gold = _label_sev(label) or "unlabeled"
        guess = _pred_sev(pred) or "unpredicted"
        matrix[gold][guess] += 1

    return matrix


def severity_jaccard(predictions: List[Dict], labels: List[Dict]) -> float:
    """Clause-level Jaccard for exact severity match.

    Treats each clause as a (clause_id, severity) tuple. Intersection counts
    clauses where the predicted severity equals the labeled severity. Union
    counts clauses with either a non-empty prediction or a non-empty label.
    """
    if len(predictions) != len(labels):
        raise ValueError(
            f"predictions ({len(predictions)}) and labels ({len(labels)}) "
            "must be aligned and equal length"
        )

    intersection = 0
    union = 0
    for pred, label in zip(predictions, labels):
        gold = _label_sev(label)
        guess = _pred_sev(pred)
        if gold is None and guess is None:
            continue
        union += 1
        if gold is not None and guess is not None and gold == guess:
            intersection += 1

    return _safe_div(intersection, union)


def category_recall(predictions: List[Dict], labels: List[Dict]) -> Dict:
    """Recall on risk_category prediction.

    Returns:
        {
            "overall_recall": float,
            "per_category": {category: {"tp": int, "support": int,
                                          "recall": float}},
            "n_labeled": int,
        }
    """
    if len(predictions) != len(labels):
        raise ValueError(
            f"predictions ({len(predictions)}) and labels ({len(labels)}) "
            "must be aligned and equal length"
        )

    per: Dict[str, Dict[str, int]] = {}
    total_tp = 0
    total_support = 0

    for pred, label in zip(predictions, labels):
        expected = label.get("expected_risk_category")
        if not expected:
            continue
        expected = str(expected).lower()
        total_support += 1
        bucket = per.setdefault(expected, {"tp": 0, "support": 0})
        bucket["support"] += 1
        predicted = pred.get("risk_category")
        if predicted and str(predicted).lower() == expected:
            bucket["tp"] += 1
            total_tp += 1

    per_out = {
        cat: {
            "tp": vals["tp"],
            "support": vals["support"],
            "recall": _safe_div(vals["tp"], vals["support"]),
        }
        for cat, vals in per.items()
    }

    return {
        "overall_recall": _safe_div(total_tp, total_support),
        "per_category": per_out,
        "n_labeled": total_support,
    }
