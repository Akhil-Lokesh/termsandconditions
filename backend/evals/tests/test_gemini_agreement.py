"""Tests for ``evals/run_gemini_agreement.py`` agreement-metric internals.

We bypass the orchestrator (which needs real API keys) and exercise the
pure-function helpers directly:

  * ``compute_agreement_metrics`` shape + correctness on hand-crafted
    aligned inputs (perfect agreement, total disagreement, mixed).
  * ``select_disagreement_examples`` prioritization (largest tier-gap first).
  * ``compute_agreement_metrics`` raises when alignment is broken.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, List

_BACKEND_DIR = Path(__file__).resolve().parents[2]
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

import pytest  # noqa: E402

from evals.run_gemini_agreement import (  # noqa: E402
    compute_agreement_metrics,
    select_disagreement_examples,
)


@dataclass
class _ClauseStub:
    clause_id: str
    section: str
    text: str


def _preds(*triples: tuple) -> List[dict]:
    return [
        {"clause_id": cid, "severity": sev, "risk_category": cat}
        for cid, sev, cat in triples
    ]


# --------------------------------------------------------------------------- #
# compute_agreement_metrics                                                   #
# --------------------------------------------------------------------------- #


def test_perfect_agreement_yields_100_pct_and_kappa_one() -> None:
    claude = _preds(
        ("c1", "critical", "arbitration"),
        ("c2", "high", "liability"),
        ("c3", "low", "other"),
        ("c4", "medium", "termination"),
    )
    gemini = list(claude)  # identical
    m = compute_agreement_metrics(claude, gemini)
    assert m["n"] == 4
    assert m["severity_agreement_rate"] == 1.0
    assert m["category_agreement_rate"] == 1.0
    assert m["joint_agreement_rate"] == 1.0
    assert m["severity_kappa"] == 1.0
    assert m["category_kappa"] == 1.0


def test_total_disagreement_severity_kappa_zero_or_negative() -> None:
    claude = _preds(
        ("c1", "critical", "arbitration"),
        ("c2", "high", "liability"),
        ("c3", "low", "other"),
        ("c4", "medium", "termination"),
    )
    # Every prediction shifted to a different tier.
    gemini = _preds(
        ("c1", "low", "other"),
        ("c2", "medium", "other"),
        ("c3", "critical", "arbitration"),
        ("c4", "high", "liability"),
    )
    m = compute_agreement_metrics(claude, gemini)
    assert m["n"] == 4
    assert m["severity_agreement_rate"] == 0.0
    assert m["category_agreement_rate"] == 0.0
    assert m["severity_kappa"] <= 0.0  # at chance or worse


def test_mixed_agreement_counts_match_manually() -> None:
    # 2 of 4 severity-match, 1 of 4 category-match, joint match only on c1.
    claude = _preds(
        ("c1", "critical", "arbitration"),
        ("c2", "high", "liability"),
        ("c3", "low", "other"),
        ("c4", "medium", "termination"),
    )
    gemini = _preds(
        ("c1", "critical", "arbitration"),   # both match (severity + category)
        ("c2", "high", "privacy"),            # severity match, category mismatch
        ("c3", "medium", "data"),             # neither
        ("c4", "low", "termination"),         # category match, severity mismatch
    )
    m = compute_agreement_metrics(claude, gemini)
    assert m["n"] == 4
    assert m["severity_agreement_rate"] == 0.5   # c1, c2
    assert m["category_agreement_rate"] == 0.5   # c1, c4
    assert m["joint_agreement_rate"] == 0.25     # c1 only


def test_confusion_matrix_rows_are_claude_cols_are_gemini() -> None:
    claude = _preds(
        ("c1", "critical", "arbitration"),
        ("c2", "critical", "arbitration"),
        ("c3", "high", "liability"),
        ("c4", "low", "other"),
    )
    gemini = _preds(
        ("c1", "critical", "arbitration"),  # claude:critical x gemini:critical
        ("c2", "high", "arbitration"),       # claude:critical x gemini:high
        ("c3", "high", "liability"),         # claude:high x gemini:high
        ("c4", "low", "other"),               # claude:low x gemini:low
    )
    m = compute_agreement_metrics(claude, gemini)
    cm = m["severity_confusion_matrix"]
    assert cm["critical"]["critical"] == 1
    assert cm["critical"]["high"] == 1
    assert cm["high"]["high"] == 1
    assert cm["low"]["low"] == 1


def test_none_severity_becomes_none_bucket_in_matrix() -> None:
    claude = _preds(("c1", None, None))
    gemini = _preds(("c1", "low", "other"))
    m = compute_agreement_metrics(claude, gemini)
    cm = m["severity_confusion_matrix"]
    # Claude None vs Gemini low — row should be "__none__"
    assert cm["__none__"]["low"] == 1
    # Disagreement: counts as 0 matches.
    assert m["severity_agreement_rate"] == 0.0


def test_alignment_mismatch_raises() -> None:
    claude = _preds(("c1", "low", "other"))
    gemini = _preds(("c2", "low", "other"))
    with pytest.raises(ValueError, match="misalignment"):
        compute_agreement_metrics(claude, gemini)


def test_length_mismatch_raises() -> None:
    claude = _preds(("c1", "low", "other"), ("c2", "low", "other"))
    gemini = _preds(("c1", "low", "other"))
    with pytest.raises(ValueError, match="alignment broken"):
        compute_agreement_metrics(claude, gemini)


# --------------------------------------------------------------------------- #
# select_disagreement_examples                                                #
# --------------------------------------------------------------------------- #


def test_disagreements_skip_matches() -> None:
    clauses = [_ClauseStub(f"c{i}", "S", "t") for i in range(3)]
    claude = _preds(("c0", "low", "other"), ("c1", "low", "other"), ("c2", "low", "other"))
    gemini = _preds(("c0", "low", "other"), ("c1", "low", "other"), ("c2", "low", "other"))
    out = select_disagreement_examples(clauses, claude, gemini)
    assert out == []


def test_disagreements_largest_gap_first() -> None:
    clauses = [_ClauseStub(f"c{i}", "S", "t") for i in range(3)]
    # gaps:  c0=3 (critical->low), c1=1 (high->medium), c2=2 (high->low)
    claude = _preds(
        ("c0", "critical", "arbitration"),
        ("c1", "high", "liability"),
        ("c2", "high", "liability"),
    )
    gemini = _preds(
        ("c0", "low", "other"),
        ("c1", "medium", "liability"),
        ("c2", "low", "other"),
    )
    out = select_disagreement_examples(clauses, claude, gemini)
    assert [r["clause_id"] for r in out] == ["c0", "c2", "c1"]
    assert out[0]["severity_tier_gap"] == 3
    assert out[1]["severity_tier_gap"] == 2
    assert out[2]["severity_tier_gap"] == 1


def test_disagreements_respect_limit() -> None:
    clauses = [_ClauseStub(f"c{i}", "S", "t") for i in range(5)]
    claude = _preds(*[(f"c{i}", "critical", "arbitration") for i in range(5)])
    gemini = _preds(*[(f"c{i}", "low", "other") for i in range(5)])
    out = select_disagreement_examples(clauses, claude, gemini, limit=3)
    assert len(out) == 3


def test_disagreement_row_shape() -> None:
    clauses = [_ClauseStub("cid", "Section", "Text body")]
    claude = _preds(("cid", "critical", "arbitration"))
    gemini = _preds(("cid", "low", "other"))
    out = select_disagreement_examples(clauses, claude, gemini)
    assert len(out) == 1
    row = out[0]
    assert row["clause_id"] == "cid"
    assert row["section"] == "Section"
    assert row["claude"] == {"severity": "critical", "risk_category": "arbitration"}
    assert row["gemini"] == {"severity": "low", "risk_category": "other"}
    assert row["severity_tier_gap"] == 3
    assert "text" in row
