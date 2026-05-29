# Public Benchmark Results — UNFAIR-ToS (LexGLUE)

The detector scored against the public **UNFAIR-ToS** benchmark (the unfair-clause
detection task from **LexGLUE**, derived from the CLAUDETTE corpus). This is an
*external* benchmark — independent of the project's own dashboard — so the
numbers are reproducible and not self-graded.

> Reproduce:
> ```bash
> cd backend
> # mixed fair/unfair set — recall AND false-positive rate, with bootstrap CIs:
> python -m evals.run_unfair_tos_benchmark --dataset unfair_tos_mixed --n 180 --chunk 30 \
>     --out evals/unfair_tos_mixed_benchmark.json
> # (regenerate the mixed set first if missing: python -m evals.datasets.ingest_unfair_tos_negatives)
> ```
> Sequential chunks; `baseline_runner`'s parallel batching times out at large N.

## Headline — mixed fair/unfair set, N = 180 (63 unfair + 117 fair), 95% bootstrap CIs

| Metric | Value (95% CI) | Read |
| --- | --- | --- |
| **Recall** (unfair clause flagged) | **84.1%** (74.6–92.5) | Catches ~5 of 6 unfair clauses |
| **False-positive rate** (fair clause wrongly flagged) | **4.3%** (0.9–8.3) | The precision-first design holds: rarely cries wolf |
| **Risk-category recall** | **54.0%** (41.1–66.2) | Correct category just over half the time |
| Severity QWK (quadratic-weighted) | +0.127 (−0.0–0.3) | Weak **and uncertain — but see caveat 1** |
| Severity MAE | 0.59 tiers (0.4–0.8) | On average ~½ a tier off |
| Severity within 1 tier | 84.1% | Rarely off by more than one |
| Severity under- / over-rated | 34.9% / 4.8% | Leans toward lower tiers |
| Severity Cohen's κ (unweighted) | +0.150 | **Not the headline — base-rate sensitive** |

**The number that matters: 84% recall at a 4.3% false-positive rate.** This is
the precision-first claim made quantitative on a public, licensed set — far more
credible than the old "100% recall" (which was vacuous on a positives-only set).

For reference, the positives-only run (N=120, `unfair_tos`) gave recall 80.8%,
category recall 54.2%, category κ +0.472 — consistent with the above.

## Honest caveats (read before quoting any number)

1. **Severity on this dataset is uninformative — by LABELS, not just metric.**
   The ingester (`datasets/ingest_unfair_tos.py::LABEL_MAPPING`) assigns "gold"
   severity *by category, not by clause wording* — `Limitation of liability` and
   `Arbitration` are hard-coded `high`, **everything else `medium`**. So
   "gold-HIGH" just means "is a liability/arbitration clause."
   We fixed the *metric* (quadratic-weighted kappa replaces unweighted, killing
   the base-rate paradox — see `metrics/severity.py::quadratic_weighted_kappa`),
   but QWK is *still* only +0.127 with a CI spanning 0. That is the honest
   verdict: against category-derived labels, severity agreement is weak **and we
   cannot tell how much is detector miscalibration vs label noise**. The cleaner
   severity signal is the cross-family Gemini study (κ +0.419, graded on *this*
   tool's rubric). Resolving this needs a hand-adjudicated subset
   (`BENCHMARK_IMPROVEMENT_PLAN.md` A3).

2. **Recall must be paired with the FP rate.** "Recall" alone is near-vacuous on
   a positives-only set (a flag-everything detector scores 100%). The mixed set
   fixes this: **84.1% recall AT a 4.3% false-positive rate** is the honest pair.

3. **Isolated-clause grading understates the real product.** The detector is
   built for *whole-document* checklist matching; here it sees single, often
   truncated clauses with no surrounding context, which starves the prompt and
   likely depresses recall and category accuracy versus document-level use
   (`BENCHMARK_IMPROVEMENT_PLAN.md` A5).

4. **N=180, single seed — but now with 95% bootstrap CIs** (A4). The bands above
   are wide (small N for a subjective task); treat point estimates accordingly.
   The earlier N=40 sample read 100% recall / 75% category — that was
   small-sample-optimistic; the CI'd figures here are the ones to trust.

## Honest headline (what is fair to claim)

> On the public UNFAIR-ToS (LexGLUE) benchmark (N=180, mixed fair/unfair), the
> detector flags **84% of unfair clauses at a 4.3% false-positive rate** and
> classifies the risk **category at 54% recall** — on isolated, context-stripped
> clauses, against a tool tuned for whole-document analysis. Severity agreement
> is not meaningfully measurable here (the gold severity is a category proxy).

This is *credibly competitive, not state-of-the-art*. The strongest companion
signal is the cross-family agreement study (`COMPARATIVE_REPORT.md`: vs Gemini
2.5 Flash, same rubric, severity κ +0.419 / category κ +0.531, both moderate).

**The most portfolio-worthy point is the rigor, not any single score:** the
harness diagnosed its own measurement bug (the kappa paradox + category-proxy
labels), corrected the metric (QWK/MAE), and added a real false-positive rate
and confidence intervals rather than quoting the flattering-but-vacuous numbers.

## Status of the improvement plan (`BENCHMARK_IMPROVEMENT_PLAN.md`)

- ✅ **A1** quadratic-weighted kappa + MAE (now the headline severity metric)
- ✅ **A2** fair negatives + false-positive rate (`unfair_tos_mixed`)
- ✅ **A4** bootstrap confidence intervals; reproducible `selected_clause_ids`
- ⏸ **A3** hand-adjudicated severity subset — needs human grading; unblocks any
  detector severity changes (plan section B, intentionally not yet implemented)
- ⏸ **A5** document-level (end-to-end) evaluation — highest effort, deferred
