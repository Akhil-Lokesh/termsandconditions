"""Tests for the gold-holdout import firewall.

The firewall has one job: make sure the gold-standard evaluation holdout
file cannot be read from production code paths (``app/core/``,
``app/services/``, ``app/api/``). This file exercises both halves of the
contract — the happy path (eval / test callers) and the failure path
(simulated production callers).
"""

from __future__ import annotations

import inspect
import os
from typing import List
from unittest import mock

import pytest

from evals.datasets import firewall


def _fake_frame(filename: str) -> inspect.FrameInfo:
    """Build a minimal FrameInfo with the requested filename.

    Only ``filename`` is read by the firewall; the rest of the tuple is
    filled with placeholders that satisfy the NamedTuple contract.
    """
    return inspect.FrameInfo(
        frame=mock.MagicMock(),
        filename=filename,
        lineno=1,
        function="<fake>",
        code_context=None,
        index=None,
    )


def test_load_gold_holdout_from_test_context_returns_list():
    """Calling from this pytest test must succeed (file may be empty)."""
    result = firewall.load_gold_holdout()
    assert isinstance(result, list)
    # The file does not exist yet in this layer; expect empty.
    if not firewall.GOLD_HOLDOUT_PATH.exists():
        assert result == []


def test_firewall_blocks_app_core_caller():
    """A simulated caller under app/core/ must be rejected."""
    forbidden_path = os.path.join(
        "backend", "app", "core", "anomaly_detector.py"
    )
    fake_stack: List[inspect.FrameInfo] = [
        _fake_frame(firewall.__file__),  # frame 0: firewall itself, skipped
        _fake_frame("/repo/" + forbidden_path),  # frame 1: forbidden caller
    ]
    with mock.patch.object(inspect, "stack", return_value=fake_stack):
        with pytest.raises(RuntimeError) as exc_info:
            firewall.assert_caller_in_evals_only()

    # Error must name the offending path and explain the firewall.
    message = str(exc_info.value)
    assert "sealed from production code paths" in message
    assert "evals/" in message


def test_firewall_blocks_app_services_caller():
    """Same rejection rule applies to app/services/."""
    forbidden_path = os.path.join(
        "backend", "app", "services", "claude_service.py"
    )
    fake_stack: List[inspect.FrameInfo] = [
        _fake_frame(firewall.__file__),
        _fake_frame("/repo/" + forbidden_path),
    ]
    with mock.patch.object(inspect, "stack", return_value=fake_stack):
        with pytest.raises(RuntimeError):
            firewall.assert_caller_in_evals_only()


def test_firewall_blocks_app_api_caller():
    """Same rejection rule applies to app/api/."""
    forbidden_path = os.path.join(
        "backend", "app", "api", "v1", "anomalies.py"
    )
    fake_stack: List[inspect.FrameInfo] = [
        _fake_frame(firewall.__file__),
        _fake_frame("/repo/" + forbidden_path),
    ]
    with mock.patch.object(inspect, "stack", return_value=fake_stack):
        with pytest.raises(RuntimeError):
            firewall.assert_caller_in_evals_only()


def test_firewall_allows_evals_caller():
    """A simulated caller under backend/evals/ must succeed."""
    eval_path = os.path.join("backend", "evals", "datasets", "loader.py")
    fake_stack: List[inspect.FrameInfo] = [
        _fake_frame(firewall.__file__),
        _fake_frame("/repo/" + eval_path),
    ]
    with mock.patch.object(inspect, "stack", return_value=fake_stack):
        # Should not raise.
        firewall.assert_caller_in_evals_only()


def test_firewall_allows_eval_tagged_test_caller():
    """test_*evals*.py under backend/tests/ is eval-tagged and allowed."""
    eval_test_path = os.path.join(
        "backend", "tests", "test_pipeline_evals.py"
    )
    fake_stack: List[inspect.FrameInfo] = [
        _fake_frame(firewall.__file__),
        _fake_frame("/repo/" + eval_test_path),
    ]
    with mock.patch.object(inspect, "stack", return_value=fake_stack):
        firewall.assert_caller_in_evals_only()


def test_firewall_error_message_is_helpful():
    """The RuntimeError must point at the exact forbidden file and explain."""
    forbidden_path = os.path.join(
        "backend", "app", "core", "evil_leaker.py"
    )
    fake_stack: List[inspect.FrameInfo] = [
        _fake_frame(firewall.__file__),
        _fake_frame("/repo/" + forbidden_path),
    ]
    with mock.patch.object(inspect, "stack", return_value=fake_stack):
        with pytest.raises(RuntimeError) as exc_info:
            firewall.assert_caller_in_evals_only()

    message = str(exc_info.value)
    # The error mentions: the sealed nature, where callers must live,
    # the offending filename, and a hint about the safe alternative.
    assert "sealed" in message
    assert "evals/" in message
    assert "evil_leaker.py" in message
    assert "loader.py" in message  # mentions the public alternative


def test_load_gold_holdout_runs_assertion_first():
    """load_gold_holdout must reject forbidden callers BEFORE touching disk."""
    forbidden_path = os.path.join(
        "backend", "app", "core", "anomaly_detector.py"
    )
    fake_stack: List[inspect.FrameInfo] = [
        _fake_frame(firewall.__file__),
        _fake_frame("/repo/" + forbidden_path),
    ]
    with mock.patch.object(inspect, "stack", return_value=fake_stack):
        with pytest.raises(RuntimeError):
            firewall.load_gold_holdout()


def test_load_gold_holdout_missing_file_returns_empty(caplog):
    """If gold_holdout.jsonl doesn't exist, return [] and log a warning."""
    if firewall.GOLD_HOLDOUT_PATH.exists():
        pytest.skip("gold_holdout.jsonl exists; missing-file path not exercised")

    import logging
    with caplog.at_level(logging.WARNING, logger=firewall.logger.name):
        result = firewall.load_gold_holdout()

    assert result == []
    assert any(
        "not yet created" in record.message for record in caplog.records
    )
