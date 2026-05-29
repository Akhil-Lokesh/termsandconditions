"""Bootstrap confidence intervals for eval metrics (plan A4).

Point estimates at N=30-150 are noisy; a subjective grading task needs error
bars. ``bootstrap_ci`` resamples aligned (prediction, label) pairs with
replacement, recomputes the metric on each resample, and returns the point
estimate plus a percentile confidence interval.

Pure stdlib (no numpy) to keep the harness portable. Deterministic given a seed.
"""

from __future__ import annotations

import random
from typing import Callable, Dict, List, Tuple


def bootstrap_ci(
    metric_fn: Callable[[List[Dict], List[Dict]], float],
    predictions: List[Dict],
    labels: List[Dict],
    n_resamples: int = 2000,
    alpha: float = 0.05,
    seed: int = 42,
) -> Dict[str, float]:
    """Percentile bootstrap CI for a scalar metric.

    Args:
        metric_fn: takes (predictions, labels) -> float. For dict-returning
            metrics (e.g. false_positive_rate), pass a thin lambda that extracts
            the scalar.
        predictions, labels: aligned, equal-length lists.
        n_resamples: number of bootstrap resamples.
        alpha: 1 - confidence (0.05 -> 95% CI).
        seed: RNG seed for reproducibility.

    Returns:
        {"point": p, "lo": lo, "hi": hi, "n": N} — lo/hi are the alpha/2 and
        1-alpha/2 percentiles of the resampled metric. Returns the point
        estimate with lo==hi==point when N == 0.
    """
    if len(predictions) != len(labels):
        raise ValueError("predictions and labels must be aligned and equal length")
    n = len(labels)
    point = round(float(metric_fn(predictions, labels)), 4)
    if n == 0:
        return {"point": point, "lo": point, "hi": point, "n": 0}

    rng = random.Random(seed)
    idx = range(n)
    samples: List[float] = []
    for _ in range(n_resamples):
        pick = [rng.choice(idx) for _ in range(n)]
        rp = [predictions[i] for i in pick]
        rl = [labels[i] for i in pick]
        samples.append(float(metric_fn(rp, rl)))
    samples.sort()
    lo = samples[max(0, int((alpha / 2) * n_resamples))]
    hi = samples[min(n_resamples - 1, int((1 - alpha / 2) * n_resamples))]
    return {"point": point, "lo": round(lo, 4), "hi": round(hi, 4), "n": n}
