# T&C Anomaly Detection Eval Harness

A minimal, labeled-data evaluation harness for the anomaly detection pipeline
orchestrated in `backend/app/core/anomaly_detector.py`. Detection quality is
primarily driven by `LLMClauseDetector` (Claude batch, checklist mode), and
this harness is the first quantitative measurement of that quality.

## Purpose

The `pytest` suite covers the plumbing (upload, parsing, ranking), but none of
it measures whether the LLM-driven detector actually returns the right severity
and risk category on real-world ToS clauses. This harness gives you:

- A small, hand-labeled seed of CUAD- and ContractEval-inspired clauses.
- Per-severity precision / recall / F1, macro and micro aggregates.
- A 4-by-4 severity confusion matrix.
- Clause-level severity Jaccard.
- Risk-category recall, per category and overall.

## How to run

```bash
# from project root, with backend/venv active
export ANTHROPIC_API_KEY=sk-ant-...
python -m evals.runner \
    --fixtures backend/evals/fixtures/labeled_clauses.json \
    --out evals_results.json
```

If `ANTHROPIC_API_KEY` is not set, the runner prints a clear "skipped (no API
key)" note and exits 0. CI can call it unconditionally.

## Metrics produced

Written to `evals_results.json` and summarized to stdout:

- `precision_recall_by_severity`: per-severity P/R/F1 plus macro and micro.
- `confusion_matrix`: nested dict, `matrix[gold][predicted]`.
- `severity_jaccard`: clause-level exact-match Jaccard.
- `category_recall`: per-category and overall recall on risk_category.

## Tests

```bash
backend/venv/bin/python -m pytest backend/evals/tests/ -q
```

These cover `evals/metrics.py` only - no Claude calls.

## Next steps

1. Import a real CUAD subset (Atticus Project) - replace the synthetic seeds
   with vetted clauses.
2. Expand to 200+ labeled clauses across all 11 risk categories defined in
   `llm_clause_detector.DETECTION_SYSTEM_PROMPT`.
3. Add a ContractEval-aligned holdout split so improvements are measured on
   data the model has not been calibrated against.
4. Gate CI: fail the build if per-severity precision regresses more than 3
   percentage points against the last green baseline (`evals_baseline.json`).
5. Track macro F1 over time in a small dashboard (or a checked-in CSV).
6. Optionally extend the runner to evaluate the full 6-stage pipeline, not
   just the LLM stage, so we can attribute regressions to specific stages.
