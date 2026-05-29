# Public Benchmark Results — UNFAIR-ToS (LexGLUE)

The detector scored against the public **UNFAIR-ToS** benchmark (the unfair-clause
detection task from **LexGLUE**, derived from the CLAUDETTE corpus). This is an
*external* benchmark — independent of the project's own dashboard — so the
numbers are reproducible and not self-graded.

> Reproduce:
> ```bash
> cd backend && python -m evals.run_unfair_tos_benchmark --n 120 --chunk 30 --out evals/unfair_tos_benchmark.json
> ```
> (Sequential chunks; `baseline_runner`'s parallel batching times out at large N.)

## Results — N = 120, current detector

| Metric | Value | Read |
| --- | --- | --- |
| **Recall** (flagged the unfair clause at all) | **80.8%** | Misses ~1 in 5 on isolated-clause grading |
| **Risk-category recall** | **54.2%** | Correct category just over half the time |
| **Risk-category Cohen's κ** | **+0.472** (moderate) | The most meaningful single number here |
| Severity within 1 tier | 80.8% | Ordinal view — rarely off by more than one |
| Severity exact-match | 55.8% | — |
| Severity Cohen's κ | +0.124 (slight) | **Not a valid quality signal — see caveat 1** |
| Severity under-rated / over-rated | 38.3% / 5.8% | Leans toward lower tiers |
| Micro F1 (severity) | 0.618 | — |

Severity confusion (gold → predicted), N=120:

```
gold HIGH   (38):  high 6  | medium 20 | low 0 | missed 12
gold MEDIUM (82):  high 7  | medium 61 | low 3 | missed 11
```

## Honest caveats (read before quoting any number)

1. **The severity metric on this dataset is largely invalid.** The ingester
   (`datasets/ingest_unfair_tos.py::LABEL_MAPPING`) assigns "gold" severity *by
   category, not by clause wording* — `Limitation of liability` and `Arbitration`
   are hard-coded `high`, **everything else is `medium`**. So "gold-HIGH" just
   means "is a liability/arbitration clause," and the gold set is a 2-class,
   medium-heavy distribution. Unweighted Cohen's κ collapses on that base rate
   (the *kappa paradox*), which is why severity κ reads +0.124 despite 55.8%
   raw / 80.8% within-one-tier agreement. **Do not present severity κ as a
   detector weakness — it is measuring a label artifact.**

2. **Positives-only → no precision / false-positive number.** The ingester keeps
   only unfair clauses, so this set tests recall + classification, not precision.
   "Recall 80.8%" should not be read as overall accuracy — there are no fair
   clauses to wrongly flag. A true precision/FP figure needs fair negatives
   (tracked in `BENCHMARK_IMPROVEMENT_PLAN.md`, item A2).

3. **Isolated-clause grading understates the real product.** The detector is
   built for *whole-document* checklist matching; here it sees single, often
   truncated clauses with no surrounding context, which starves the prompt and
   likely depresses both recall and category accuracy versus document-level use.

4. **N=120, single seed, no confidence intervals yet.** Treat as a point
   estimate. (The N=40 sample read 100% recall / 75% category recall — that was
   small-sample-optimistic; N=120 is the figure to trust.)

## Honest headline (what is fair to claim)

> On the public UNFAIR-ToS (LexGLUE) benchmark (N=120), the detector flags
> **80.8%** of unfair clauses and classifies the risk **category** at **κ +0.472
> (moderate)** — on isolated, context-stripped clauses, against a tool tuned for
> whole-document analysis. Severity agreement is not meaningfully measurable on
> this dataset because its gold severity is a category proxy.

This is *credibly competitive, not state-of-the-art*. The cross-family agreement
study (`COMPARATIVE_REPORT.md`: vs Gemini 2.5 Flash, severity κ +0.419, category
κ +0.531, both moderate) is the better-designed companion measure.

## Next steps

See `BENCHMARK_IMPROVEMENT_PLAN.md` for the prioritized plan — top items:
quadratic-weighted kappa + MAE as the headline severity metric (kills the
paradox), a mixed fair/unfair set for a real false-positive rate, and
document-level evaluation.
