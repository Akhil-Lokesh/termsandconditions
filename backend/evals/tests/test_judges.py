"""Tests for the judge harness with the network client fully mocked.

We never make real API calls in this suite — the Anthropic and OpenAI
clients are replaced by lightweight async mocks that return canned
JSON. Goals:

  * Verify ``ClaudeJudge`` and ``OpenAIJudge`` parse a well-formed reply.
  * Verify both judges still return a usable verdict when the model
    returns garbage (parser tolerance).
  * Verify the JudgeRunner aggregates verdicts, samples the cross
    family, and writes disagreements to JSONL.
  * Verify the SQLite verdict cache round-trips.
"""

from __future__ import annotations

import asyncio
import json
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, List

_BACKEND_DIR = Path(__file__).resolve().parents[2]
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

import pytest  # noqa: E402

from evals.judge.claude_judge import ClaudeJudge  # noqa: E402
from evals.judge.openai_judge import OpenAIJudge  # noqa: E402
from evals.judge.runner import JudgeRunner, VerdictCache  # noqa: E402


def test_judge_prompts_in_lockstep():
    """openai_judge documents JUDGE_SYSTEM_PROMPT as a verbatim copy of the
    claude_judge one. Enforce that here (the safeguard the comment refers to):
    the two prompts must be byte-identical so the cross-family judge never drifts
    from the primary rubric."""
    import hashlib
    from evals.judge import claude_judge, openai_judge

    claude_hash = hashlib.sha256(claude_judge.JUDGE_SYSTEM_PROMPT.encode()).hexdigest()
    openai_hash = hashlib.sha256(openai_judge.JUDGE_SYSTEM_PROMPT.encode()).hexdigest()
    assert claude_hash == openai_hash, (
        "claude_judge and openai_judge JUDGE_SYSTEM_PROMPT have diverged — "
        "update BOTH in lockstep."
    )


# --------------------------------------------------------------------------- #
# Anthropic-client stub                                                       #
# --------------------------------------------------------------------------- #


class _AnthropicTextBlock:
    def __init__(self, text: str) -> None:
        self.text = text


class _AnthropicResponse:
    def __init__(self, text: str) -> None:
        self.content = [_AnthropicTextBlock(text)]


class _AnthropicMessages:
    def __init__(self, responder) -> None:
        self._responder = responder

    async def create(self, **kwargs) -> _AnthropicResponse:
        text = self._responder(kwargs)
        return _AnthropicResponse(text)


class _StubAnthropicClient:
    """Minimal stub matching the AsyncAnthropic surface we use."""

    def __init__(self, responder) -> None:
        self.messages = _AnthropicMessages(responder)


# --------------------------------------------------------------------------- #
# OpenAI-client stub                                                          #
# --------------------------------------------------------------------------- #


class _OpenAIChoiceMessage:
    def __init__(self, content: str) -> None:
        self.content = content


class _OpenAIChoice:
    def __init__(self, content: str) -> None:
        self.message = _OpenAIChoiceMessage(content)


class _OpenAIResponse:
    def __init__(self, content: str) -> None:
        self.choices = [_OpenAIChoice(content)]


class _OpenAICompletions:
    def __init__(self, responder) -> None:
        self._responder = responder

    async def create(self, **kwargs) -> _OpenAIResponse:
        text = self._responder(kwargs)
        return _OpenAIResponse(text)


class _OpenAIChat:
    def __init__(self, responder) -> None:
        self.completions = _OpenAICompletions(responder)


class _StubOpenAIClient:
    def __init__(self, responder) -> None:
        self.chat = _OpenAIChat(responder)


# --------------------------------------------------------------------------- #
# Helpers                                                                     #
# --------------------------------------------------------------------------- #


def _make_clauses() -> List[Dict[str, Any]]:
    return [
        {
            "clause_id": "c1",
            "section": "Arbitration",
            "text": "You agree to mandatory arbitration and waive your right to a class action.",
            "expected_severity": "high",
            "expected_risk_category": "arbitration",
        },
        {
            "clause_id": "c2",
            "section": "Privacy",
            "text": "We may use cookies to improve our service.",
            "expected_severity": "low",
            "expected_risk_category": "privacy",
        },
    ]


def _make_predictions() -> List[Dict[str, Any]]:
    return [
        {"severity": "high", "risk_category": "arbitration"},
        {"severity": "critical", "risk_category": "privacy"},  # over-call
    ]


def _good_responder(_kwargs) -> str:
    return json.dumps(
        {
            "severity_verdict": "yes",
            "category_verdict": "yes",
            "rationale": "Looks right to me.",
        }
    )


def _bad_responder(_kwargs) -> str:
    return "I think the answer is yes."  # not JSON


# --------------------------------------------------------------------------- #
# Single-clause judging                                                       #
# --------------------------------------------------------------------------- #


def test_claude_judge_parses_well_formed_response():
    judge = ClaudeJudge(model="stub", api_key="dummy")
    judge._client = _StubAnthropicClient(_good_responder)
    verdict = asyncio.run(
        judge.judge_clause(_make_clauses()[0], _make_predictions()[0])
    )
    assert verdict["severity_verdict"] == "yes"
    assert verdict["category_verdict"] == "yes"
    assert "rationale" in verdict
    assert verdict["_judge"].startswith("claude:")


def test_claude_judge_tolerates_garbage_response():
    judge = ClaudeJudge(model="stub", api_key="dummy")
    judge._client = _StubAnthropicClient(_bad_responder)
    verdict = asyncio.run(
        judge.judge_clause(_make_clauses()[0], _make_predictions()[0])
    )
    # No JSON at all → parser should land on a "no" verdict but still
    # return a properly shaped dict.
    assert verdict["severity_verdict"] in {"yes", "partial", "no"}
    assert verdict["category_verdict"] in {"yes", "no"}
    assert isinstance(verdict["rationale"], str)


def test_openai_judge_parses_well_formed_response():
    judge = OpenAIJudge(model="stub", api_key="dummy")
    judge._client = _StubOpenAIClient(_good_responder)
    verdict = asyncio.run(
        judge.judge_clause(_make_clauses()[0], _make_predictions()[0])
    )
    assert verdict["severity_verdict"] == "yes"
    assert verdict["category_verdict"] == "yes"
    assert verdict["_judge"].startswith("openai:")


# --------------------------------------------------------------------------- #
# Batch judging                                                               #
# --------------------------------------------------------------------------- #


def test_claude_judge_batch_returns_aligned_verdicts():
    judge = ClaudeJudge(model="stub", api_key="dummy")
    judge._client = _StubAnthropicClient(_good_responder)
    verdicts = asyncio.run(
        judge.judge_batch(_make_clauses(), _make_predictions(), concurrency=2)
    )
    assert len(verdicts) == 2
    for v in verdicts:
        assert v["severity_verdict"] == "yes"


def test_judge_batch_rejects_length_mismatch():
    judge = ClaudeJudge(model="stub", api_key="dummy")
    judge._client = _StubAnthropicClient(_good_responder)
    with pytest.raises(ValueError):
        asyncio.run(judge.judge_batch([{}], [{}, {}]))


# --------------------------------------------------------------------------- #
# Cache round-trip                                                            #
# --------------------------------------------------------------------------- #


def test_verdict_cache_roundtrip(tmp_path):
    cache = VerdictCache(tmp_path / "cache.db")
    key = cache.make_key("c1", {"severity": "high"}, "claude:stub")
    assert cache.get(key) is None
    cache.put(
        key,
        "claude:stub",
        {"severity_verdict": "yes", "category_verdict": "yes", "rationale": "..."},
    )
    out = cache.get(key)
    assert out is not None
    assert out["severity_verdict"] == "yes"
    cache.close()


# --------------------------------------------------------------------------- #
# Runner orchestration                                                        #
# --------------------------------------------------------------------------- #


def _make_disagreeing_openai(_kwargs) -> str:
    return json.dumps(
        {
            "severity_verdict": "no",
            "category_verdict": "no",
            "rationale": "OpenAI disagrees with Claude.",
        }
    )


def test_runner_runs_primary_and_cross_with_disagreement_log(tmp_path):
    primary = ClaudeJudge(model="stub-claude", api_key="dummy")
    primary._client = _StubAnthropicClient(_good_responder)
    cross = OpenAIJudge(model="stub-openai", api_key="dummy")
    cross._client = _StubOpenAIClient(_make_disagreeing_openai)

    cache_path = tmp_path / "cache.db"
    log_path = tmp_path / "disagreements.jsonl"
    runner = JudgeRunner(
        primary_judge=primary,
        cross_judge=cross,
        cache_path=cache_path,
        disagreement_log=log_path,
    )
    try:
        # Cross-check sample 1.0 so every pair is cross-checked.
        report = asyncio.run(
            runner.run(
                _make_clauses(),
                _make_predictions(),
                cross_check_sample=1.0,
                concurrency=2,
            )
        )
    finally:
        runner.close()

    assert report["n_judged"] == 2
    assert report["n_cross_checked"] == 2
    # Primary returned "yes", cross returned "no" — every pair disagrees.
    assert report["agreement_rate"] == 0.0
    assert report["n_disagreements"] == 2
    # The disagreement log file should now have two lines.
    lines = [ln for ln in log_path.read_text().splitlines() if ln.strip()]
    assert len(lines) == 2
    row = json.loads(lines[0])
    assert row["primary"]["severity_verdict"] == "yes"
    assert row["cross"]["severity_verdict"] == "no"


def test_runner_skips_cross_when_no_cross_judge(tmp_path):
    primary = ClaudeJudge(model="stub-claude", api_key="dummy")
    primary._client = _StubAnthropicClient(_good_responder)
    runner = JudgeRunner(
        primary_judge=primary,
        cross_judge=None,
        cache_path=tmp_path / "cache.db",
        disagreement_log=tmp_path / "disagreements.jsonl",
    )
    try:
        report = asyncio.run(
            runner.run(_make_clauses(), _make_predictions(), cross_check_sample=0.5)
        )
    finally:
        runner.close()

    assert report["n_judged"] == 2
    assert report["n_cross_checked"] == 0
    assert report["cross_judge"] is None
