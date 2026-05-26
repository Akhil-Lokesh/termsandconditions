"""Tests for ``evals/generate_comparative_report.py``.

The cardinal rule under test: **never invent numbers**. When the source
JSON is missing or incomplete, every numeric field must render as the
``MISSING`` placeholder string. We also check that real data renders into
percentages, kappa values, and a confusion matrix table.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

_BACKEND_DIR = Path(__file__).resolve().parents[2]
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

from evals.generate_comparative_report import (  # noqa: E402
    MISSING,
    render_report,
)


def _full_report_dict() -> dict:
    return {
        "model_claude": "production-detector",
        "model_gemini": "gemini:gemini-2.0-flash",
        "dataset": "all",
        "n_samples": 30,
        "batch_size": 5,
        "seed": 42,
        "gemini_stats": {
            "requests_sent": 6,
            "requests_retried": 0,
            "rate_limit_hits": 0,
            "parse_failures": 0,
            "elapsed_seconds": 14.2,
        },
        "agreement": {
            "n": 30,
            "severity_agreement_rate": 0.7333,
            "category_agreement_rate": 0.6667,
            "joint_agreement_rate": 0.5667,
            "severity_kappa": 0.612,
            "severity_kappa_interpretation": "substantial",
            "macro_severity_kappa": 0.55,
            "per_severity_kappa": {
                "critical": 0.42,
                "high": 0.61,
                "medium": 0.49,
                "low": 0.78,
            },
            "category_kappa": 0.59,
            "severity_confusion_matrix": {
                "critical": {"critical": 3, "high": 1, "medium": 0, "low": 0, "__none__": 0},
                "high": {"critical": 0, "high": 6, "medium": 1, "low": 0, "__none__": 0},
                "medium": {"critical": 0, "high": 2, "medium": 8, "low": 1, "__none__": 0},
                "low": {"critical": 0, "high": 0, "medium": 2, "low": 5, "__none__": 1},
                "__none__": {"critical": 0, "high": 0, "medium": 0, "low": 0, "__none__": 0},
            },
        },
        "n_disagreements": 8,
        "timestamp": "2026-05-24T12:00:00+00:00",
        "git_commit": "abcd1234",
    }


def test_render_with_full_data_includes_real_numbers(tmp_path: Path) -> None:
    # Provide a disagreement log so EVERY section has data — proves no
    # MISSING marker is fabricated when the full data set is present.
    log_path = tmp_path / "dis.jsonl"
    log_path.write_text(json.dumps({
        "clause_id": "gold_x",
        "section": "S",
        "text": "t",
        "claude": {"severity": "critical", "risk_category": "arbitration"},
        "gemini": {"severity": "low", "risk_category": "other"},
        "severity_tier_gap": 3,
    }) + "\n")
    md = render_report(_full_report_dict(), log_path)
    # Has bullets section.
    assert "## Resume-ready bullets" in md
    # Renders real percentages, not placeholders.
    assert "73.3%" in md
    assert "66.7%" in md
    assert "56.7%" in md
    # Kappa with sign + interp.
    assert "+0.612" in md
    assert "substantial" in md
    # Sample size + disagreement count are numeric.
    assert "N = 30" in md
    assert "8" in md
    # No MISSING marker leaks when every data slot is populated.
    assert MISSING not in md


def test_render_with_missing_data_uses_placeholders(tmp_path: Path) -> None:
    md = render_report(None, tmp_path / "no_log.jsonl")
    # Bullets exist but every numeric slot is the placeholder.
    assert "## Resume-ready bullets" in md
    assert MISSING in md
    # And we did NOT hallucinate any percentage / kappa value.
    assert "%" not in md.replace(MISSING, "") or "free-tier" in md.lower()


def test_render_partial_data_only_fills_present_fields(tmp_path: Path) -> None:
    # Only the agreement block is populated; gemini_stats absent.
    partial = {
        "model_gemini": "gemini:test-model",
        "n_samples": 10,
        "agreement": {
            "severity_agreement_rate": 0.5,
            "category_agreement_rate": 0.4,
            "severity_kappa": 0.3,
            "severity_kappa_interpretation": "fair",
        },
    }
    md = render_report(partial, tmp_path / "no_log.jsonl")
    assert "50.0%" in md
    assert "40.0%" in md
    assert "+0.300" in md
    # Missing fields keep the marker — proves we don't fabricate.
    assert MISSING in md


def test_confusion_matrix_table_renders_when_present(tmp_path: Path) -> None:
    md = render_report(_full_report_dict(), tmp_path / "no_log.jsonl")
    assert "Severity confusion matrix" in md
    # Header is a markdown table.
    assert "| critical |" in md
    assert "| --- |" in md


def test_disagreement_log_renders_lines(tmp_path: Path) -> None:
    log_path = tmp_path / "dis.jsonl"
    log_path.write_text(json.dumps({
        "clause_id": "gold_001",
        "section": "Arbitration",
        "text": "you waive your right to a jury trial.",
        "claude": {"severity": "critical", "risk_category": "arbitration"},
        "gemini": {"severity": "low", "risk_category": "other"},
        "severity_tier_gap": 3,
    }) + "\n")
    md = render_report(_full_report_dict(), log_path)
    assert "gold_001" in md
    assert "severity-tier gap: 3" in md
    assert "you waive your right" in md


def test_disagreement_log_missing_renders_placeholder(tmp_path: Path) -> None:
    md = render_report(_full_report_dict(), tmp_path / "does_not_exist.jsonl")
    assert "Top disagreement examples" in md
    assert MISSING in md


def test_safety_section_always_present(tmp_path: Path) -> None:
    """Free-tier safety guidance is operational guidance, not data — always include."""
    md_full = render_report(_full_report_dict(), tmp_path / "x.jsonl")
    md_empty = render_report(None, tmp_path / "x.jsonl")
    for md in (md_full, md_empty):
        assert "Free-tier safety" in md
        assert "15 RPM" in md
        assert "Skip-safe" in md
