"""Eval datasets package — real labeled corpora ingesters + unified loader.

Layer 3 of the upgrade plan (see /nxt.md). Replaces the 18-clause toy fixture
in `backend/evals/fixtures/labeled_clauses.json` with real, public, labeled
datasets so the eval harness can produce statistically meaningful metrics.

Sub-modules:
    schema     — Pydantic `EvalClause` model + severity/category validators.
    loader     — Unified `load_dataset()` and `dataset_stats()` entrypoints.
    ingest_*   — One-shot dataset ingesters (write JSONL to disk).
"""
