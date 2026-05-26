"""Tests for ``evals/judge/gemini_judge.py`` with all HTTP fully mocked.

We never hit the real Gemini API. The pluggable ``_HttpTransport`` lets us
inject canned responses (and 429s) per request, so we can verify:

  * The judge parses a well-formed JSON-array reply.
  * The parser is tolerant of garbage / fences / out-of-order items.
  * Severity / category values outside the allowed vocabulary become None.
  * The request body has temperature 0, JSON mime-type, and NO ``tools`` key
    (i.e. search grounding cannot fire).
  * Rate-limit (429) responses trigger retries with backoff that honors
    ``Retry-After``.
  * Batching splits inputs into the configured size.
  * Missing ``GEMINI_API_KEY`` raises ``GeminiNotConfigured``.
"""

from __future__ import annotations

import asyncio
import json
import sys
import types
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

_BACKEND_DIR = Path(__file__).resolve().parents[2]
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

import pytest  # noqa: E402

from evals.judge.gemini_judge import (  # noqa: E402
    GeminiJudge,
    GeminiNotConfigured,
    SEVERITIES,
    RISK_CATEGORIES,
    parse_gemini_response,
)


# --------------------------------------------------------------------------- #
# HTTP transport stub                                                         #
# --------------------------------------------------------------------------- #


class _StubResponse:
    """Mimics the bits of ``httpx.Response`` the judge actually reads."""

    def __init__(self, status_code: int, body: Optional[Dict[str, Any]] = None,
                 text: str = "", headers: Optional[Dict[str, str]] = None) -> None:
        self.status_code = status_code
        self._body = body
        self.text = text or (json.dumps(body) if body is not None else "")
        self.headers = headers or {}

    def json(self) -> Dict[str, Any]:
        if self._body is None:
            raise ValueError("no json body")
        return self._body


class _ScriptedTransport:
    """Returns a pre-scripted sequence of responses; raises after exhaustion."""

    def __init__(self, responses: List[_StubResponse]) -> None:
        self._responses = list(responses)
        self.calls: List[Dict[str, Any]] = []

    async def post(self, url: str, params: Dict[str, Any],
                   json_body: Dict[str, Any]) -> _StubResponse:
        self.calls.append({"url": url, "params": params, "json_body": json_body})
        if not self._responses:
            raise AssertionError("scripted transport exhausted")
        return self._responses.pop(0)


def _make_gemini_json_response(items: List[Dict[str, Any]]) -> _StubResponse:
    """Wrap a list of label objects in Gemini's generateContent reply shape."""
    body = {
        "candidates": [
            {
                "content": {
                    "parts": [{"text": json.dumps(items)}],
                },
                "finishReason": "STOP",
            }
        ]
    }
    return _StubResponse(200, body=body)


def _await(coro):
    return asyncio.get_event_loop().run_until_complete(coro) \
        if False else asyncio.run(coro)  # noqa: E501  (kept for clarity)


# --------------------------------------------------------------------------- #
# Parser tests                                                                #
# --------------------------------------------------------------------------- #


def test_parser_well_formed_array() -> None:
    raw = json.dumps([
        {"clause_id": "a", "severity": "critical", "risk_category": "arbitration"},
        {"clause_id": "b", "severity": "low", "risk_category": "other"},
    ])
    out = parse_gemini_response(raw, ["a", "b"])
    assert [o.clause_id for o in out] == ["a", "b"]
    assert out[0].severity == "critical"
    assert out[0].risk_category == "arbitration"
    assert out[1].severity == "low"


def test_parser_handles_markdown_fences() -> None:
    raw = "```json\n[{\"clause_id\":\"x\",\"severity\":\"high\",\"risk_category\":\"privacy\"}]\n```"
    out = parse_gemini_response(raw, ["x"])
    assert out[0].severity == "high"
    assert out[0].risk_category == "privacy"


def test_parser_handles_trailing_prose() -> None:
    raw = "Sure! Here you go:\n[{\"clause_id\":\"y\",\"severity\":\"medium\",\"risk_category\":\"data\"}]\nLet me know if you need more."
    out = parse_gemini_response(raw, ["y"])
    assert out[0].severity == "medium"
    assert out[0].risk_category == "data"


def test_parser_out_of_order_alignment() -> None:
    raw = json.dumps([
        {"clause_id": "b", "severity": "low", "risk_category": "other"},
        {"clause_id": "a", "severity": "high", "risk_category": "liability"},
    ])
    out = parse_gemini_response(raw, ["a", "b"])
    # Alignment is by clause_id, not position.
    assert out[0].clause_id == "a"
    assert out[0].severity == "high"
    assert out[1].clause_id == "b"
    assert out[1].severity == "low"


def test_parser_rejects_invalid_vocabulary() -> None:
    raw = json.dumps([{"clause_id": "z", "severity": "URGENT", "risk_category": "foo"}])
    out = parse_gemini_response(raw, ["z"])
    assert out[0].severity is None  # "URGENT" not in SEVERITIES
    assert out[0].risk_category is None  # "foo" not in RISK_CATEGORIES


def test_parser_missing_clause_id_yields_nones() -> None:
    raw = json.dumps([{"clause_id": "present", "severity": "low", "risk_category": "other"}])
    out = parse_gemini_response(raw, ["present", "missing"])
    assert out[0].severity == "low"
    assert out[1].clause_id == "missing"
    assert out[1].severity is None
    assert out[1].risk_category is None


def test_parser_handles_total_garbage() -> None:
    raw = "I cannot do that for you, Dave."
    out = parse_gemini_response(raw, ["a", "b"])
    assert all(lbl.severity is None for lbl in out)
    assert all(lbl.risk_category is None for lbl in out)


def test_parser_handles_empty_string() -> None:
    out = parse_gemini_response("", ["a"])
    assert out[0].severity is None


# --------------------------------------------------------------------------- #
# Request body tests                                                          #
# --------------------------------------------------------------------------- #


def test_request_body_has_no_tools_key() -> None:
    """Search grounding cannot fire unless ``tools`` is present in the body."""
    judge = GeminiJudge(api_key="fake")
    body = judge._build_request_body([
        {"clause_id": "c1", "section": "X", "text": "y"},
    ])
    assert "tools" not in body
    # And no top-level reference to grounding-y fields just in case.
    flat = json.dumps(body).lower()
    assert "googlesearchretrieval" not in flat
    assert "google_search_retrieval" not in flat


def test_request_body_temperature_zero_and_json_mime() -> None:
    judge = GeminiJudge(api_key="fake")
    body = judge._build_request_body([{"clause_id": "c", "section": "S", "text": "t"}])
    gen = body["generationConfig"]
    assert gen["temperature"] == 0
    assert gen["responseMimeType"] == "application/json"


def test_request_body_contains_system_prompt_and_user_payload() -> None:
    judge = GeminiJudge(api_key="fake")
    body = judge._build_request_body([
        {"clause_id": "abc", "section": "Arbitration", "text": "Hello world"},
    ])
    assert "systemInstruction" in body
    sys_text = body["systemInstruction"]["parts"][0]["text"]
    assert "Severity rubric" in sys_text
    user_text = body["contents"][0]["parts"][0]["text"]
    assert "abc" in user_text
    assert "Arbitration" in user_text
    assert "Hello world" in user_text


# --------------------------------------------------------------------------- #
# End-to-end batching + happy path                                            #
# --------------------------------------------------------------------------- #


def test_label_batch_single_batch_happy_path() -> None:
    clauses = [
        {"clause_id": "c1", "section": "A", "text": "alpha"},
        {"clause_id": "c2", "section": "B", "text": "beta"},
    ]
    resp = _make_gemini_json_response([
        {"clause_id": "c1", "severity": "critical", "risk_category": "arbitration"},
        {"clause_id": "c2", "severity": "low", "risk_category": "other"},
    ])
    transport = _ScriptedTransport([resp])
    judge = GeminiJudge(api_key="fake", batch_size=5,
                        rpm_pacing_seconds=0, transport=transport)
    labels = asyncio.run(judge.label_batch(clauses))
    assert len(labels) == 2
    assert labels[0].severity == "critical"
    assert labels[1].severity == "low"
    assert judge.stats.requests_sent == 1
    assert judge.stats.parse_failures == 0
    assert len(transport.calls) == 1
    # Endpoint includes the default model name and api_key params.
    from evals.judge.gemini_judge import DEFAULT_MODEL
    assert DEFAULT_MODEL in transport.calls[0]["url"]
    assert transport.calls[0]["params"]["key"] == "fake"


def test_label_batch_splits_into_configured_size() -> None:
    clauses = [{"clause_id": f"c{i}", "section": "S", "text": "t"} for i in range(7)]
    resp1 = _make_gemini_json_response([
        {"clause_id": f"c{i}", "severity": "low", "risk_category": "other"}
        for i in range(5)
    ])
    resp2 = _make_gemini_json_response([
        {"clause_id": f"c{i}", "severity": "high", "risk_category": "liability"}
        for i in range(5, 7)
    ])
    transport = _ScriptedTransport([resp1, resp2])
    judge = GeminiJudge(api_key="fake", batch_size=5,
                        rpm_pacing_seconds=0, transport=transport)
    labels = asyncio.run(judge.label_batch(clauses))
    assert len(labels) == 7
    assert labels[0].severity == "low"
    assert labels[5].severity == "high"
    assert len(transport.calls) == 2  # 5 + 2 split


# --------------------------------------------------------------------------- #
# Retry / backoff                                                             #
# --------------------------------------------------------------------------- #


def test_retries_on_429_then_succeeds() -> None:
    clauses = [{"clause_id": "x", "section": "S", "text": "t"}]
    rate_limited = _StubResponse(429, body=None, text="rate limited",
                                 headers={"Retry-After": "0"})
    ok = _make_gemini_json_response([
        {"clause_id": "x", "severity": "medium", "risk_category": "other"},
    ])
    transport = _ScriptedTransport([rate_limited, ok])
    judge = GeminiJudge(api_key="fake", batch_size=5,
                        rpm_pacing_seconds=0, transport=transport)
    labels = asyncio.run(judge.label_batch(clauses))
    assert labels[0].severity == "medium"
    assert judge.stats.rate_limit_hits == 1
    assert judge.stats.requests_retried == 1
    assert judge.stats.requests_sent == 2


def test_retries_exhausted_yields_empty_labels_without_raising() -> None:
    clauses = [{"clause_id": "x", "section": "S", "text": "t"}]
    # 6 consecutive 429s — max_retries=2 means 3 attempts total, then raise.
    transport = _ScriptedTransport([
        _StubResponse(429, body=None, text="x", headers={"Retry-After": "0"})
        for _ in range(6)
    ])
    judge = GeminiJudge(api_key="fake", batch_size=5,
                        rpm_pacing_seconds=0, max_retries=2, transport=transport)
    labels = asyncio.run(judge.label_batch(clauses))
    # Batch failed, but alignment is preserved with None labels.
    assert len(labels) == 1
    assert labels[0].clause_id == "x"
    assert labels[0].severity is None
    assert judge.stats.parse_failures == 1


# --------------------------------------------------------------------------- #
# Configuration / safety                                                      #
# --------------------------------------------------------------------------- #


def test_missing_api_key_raises_on_use(monkeypatch) -> None:
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    judge = GeminiJudge(batch_size=5, rpm_pacing_seconds=0,
                        transport=_ScriptedTransport([]))
    # Construction is fine; the first request raises so callers can exit 0.
    with pytest.raises(GeminiNotConfigured):
        asyncio.run(judge.label_batch([{"clause_id": "x", "section": "S", "text": "t"}]))


def test_name_property_format() -> None:
    judge = GeminiJudge(model="gemini-something", api_key="fake")
    assert judge.name == "gemini:gemini-something"
