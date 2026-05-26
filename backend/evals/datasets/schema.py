"""Pydantic schema for unified labeled eval clauses.

Every ingester writes JSONL records conforming to `EvalClause`. The loader
parses through this model so downstream code (eval harness, judge runner,
metrics) sees a single, validated shape regardless of upstream dataset.

Severity and category vocabularies are fixed (and pinned to what
`LLMClauseDetector` emits). Records with values outside these sets are
rejected by the validator — surfacing schema drift loudly.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator

# The 4-level severity rubric used by `LLMClauseDetector` and the metrics
# code in `evals/metrics.py`. Keep in sync with both.
SEVERITY_VALUES = ("critical", "high", "medium", "low")

# The 11 risk categories used by the production detector (see
# `app/core/llm_clause_detector.py` and `app/core/constants.py`). Keep
# this tuple in alphabetical-ish but production order — downstream code
# does set-membership checks, not positional comparisons.
RISK_CATEGORY_VALUES = (
    "liability",
    "payment",
    "privacy",
    "arbitration",
    "modification",
    "termination",
    "content",
    "data",
    "rights",
    "surveillance",
    "other",
)


SeverityLiteral = Literal["critical", "high", "medium", "low"]


class EvalClause(BaseModel):
    """One labeled clause for the eval harness.

    Identical shape to the historical seed fixture
    (`evals/fixtures/labeled_clauses.json`) so that JSON file can be loaded
    through the same model without translation.
    """

    clause_id: str = Field(..., description="Stable unique id, e.g. 'unfair_tos_42'.")
    section: str = Field("Unknown", description="Section heading or source label name.")
    text: str = Field(..., description="Raw clause text.")
    expected_severity: SeverityLiteral = Field(
        ..., description="Gold severity in {critical, high, medium, low}."
    )
    expected_risk_category: str = Field(
        ..., description="Gold category in the 11-category vocabulary."
    )
    notes: str = Field("", description="Free-form notes / original upstream labels.")
    source: str = Field(..., description="Origin tag, e.g. 'UNFAIR-ToS (LexGLUE)'.")

    @field_validator("expected_risk_category")
    @classmethod
    def _check_category(cls, v: str) -> str:
        if v not in RISK_CATEGORY_VALUES:
            raise ValueError(
                f"expected_risk_category={v!r} not in {RISK_CATEGORY_VALUES}"
            )
        return v

    @field_validator("text")
    @classmethod
    def _non_empty_text(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("text must be non-empty")
        return v.strip()

    @field_validator("clause_id")
    @classmethod
    def _non_empty_clause_id(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("clause_id must be non-empty")
        return v.strip()
