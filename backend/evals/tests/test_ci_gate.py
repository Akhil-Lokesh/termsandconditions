"""Tests for evals.ci_gate. No network, no Claude / OpenAI calls."""

from __future__ import annotations

import json
import sys
from pathlib import Path

_BACKEND_DIR = Path(__file__).resolve().parents[2]
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

from evals.ci_gate import check_against_baseline  # noqa: E402


def _write_json(path: Path, payload: dict) -> Path:
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_skip_when_baseline_missing(tmp_path):
    cur = _write_json(
        tmp_path / "cur.json", {"severity_kappa": 0.8, "macro_kappa": 0.7}
    )
    result = check_against_baseline(cur, tmp_path / "baseline.json")
    assert result["passed"] is True
    assert result["skipped"] is True


def test_skip_when_current_missing(tmp_path):
    base = _write_json(
        tmp_path / "baseline.json", {"severity_kappa": 0.8, "macro_kappa": 0.7}
    )
    result = check_against_baseline(tmp_path / "cur.json", base)
    assert result["passed"] is True
    assert result["skipped"] is True


def test_skip_when_current_is_skip_record(tmp_path):
    base = _write_json(tmp_path / "baseline.json", {"severity_kappa": 0.8})
    cur = _write_json(tmp_path / "cur.json", {"status": "skipped", "reason": "no_api_key"})
    result = check_against_baseline(cur, base)
    assert result["passed"] is True
    assert result["skipped"] is True


def test_pass_when_improvement(tmp_path):
    base = _write_json(
        tmp_path / "baseline.json",
        {"severity_kappa": 0.70, "macro_kappa": 0.65, "category_kappa": 0.6,
         "per_severity_kappa": {"critical": 0.7, "high": 0.6, "medium": 0.5, "low": 0.5}},
    )
    cur = _write_json(
        tmp_path / "cur.json",
        {"severity_kappa": 0.78, "macro_kappa": 0.70, "category_kappa": 0.65,
         "per_severity_kappa": {"critical": 0.8, "high": 0.7, "medium": 0.5, "low": 0.55}},
    )
    result = check_against_baseline(cur, base)
    assert result["passed"] is True
    assert result["skipped"] is False
    assert len(result["regressions"]) == 0
    assert len(result["improvements"]) > 0


def test_fail_when_regression_above_threshold(tmp_path):
    base = _write_json(
        tmp_path / "baseline.json",
        {"severity_kappa": 0.80, "per_severity_kappa": {"critical": 0.75}},
    )
    cur = _write_json(
        tmp_path / "cur.json",
        {"severity_kappa": 0.78, "per_severity_kappa": {"critical": 0.65}},
    )
    # critical drops 0.10 — far worse than the 0.03 default threshold.
    result = check_against_baseline(cur, base, max_kappa_regression=0.03)
    assert result["passed"] is False
    assert any(r["name"] == "per_severity_kappa.critical" for r in result["regressions"])


def test_pass_when_regression_within_threshold(tmp_path):
    base = _write_json(
        tmp_path / "baseline.json",
        {"severity_kappa": 0.80, "per_severity_kappa": {"critical": 0.75}},
    )
    cur = _write_json(
        tmp_path / "cur.json",
        {"severity_kappa": 0.79, "per_severity_kappa": {"critical": 0.73}},
    )
    # Drops are 0.01 / 0.02 — under the 0.03 threshold.
    result = check_against_baseline(cur, base, max_kappa_regression=0.03)
    assert result["passed"] is True


def test_custom_threshold_changes_verdict(tmp_path):
    base = _write_json(
        tmp_path / "baseline.json",
        {"severity_kappa": 0.80},
    )
    cur = _write_json(
        tmp_path / "cur.json",
        {"severity_kappa": 0.74},
    )
    # Drop 0.06. Default 0.03 ⇒ fail; loose 0.10 ⇒ pass.
    strict = check_against_baseline(cur, base, max_kappa_regression=0.03)
    loose = check_against_baseline(cur, base, max_kappa_regression=0.10)
    assert strict["passed"] is False
    assert loose["passed"] is True
