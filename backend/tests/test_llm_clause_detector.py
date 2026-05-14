"""Tests for LLMClauseDetector."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.core.llm_clause_detector import (
    LLMClauseDetector,
    MAX_INPUT_TOKENS,
    MAX_CRITICAL_VOTES_PER_DOC,
    SELF_CONSISTENCY_VOTES,
    CLAUDE_PRICING,
)
import app.core.llm_clause_detector as llm_module


# ── Fixtures ─��────────────────────────────────────────────────────────────────

@pytest.fixture
def mock_claude():
    """Mock ClaudeService."""
    service = MagicMock()
    service.create_structured_completion = AsyncMock()
    return service


@pytest.fixture
def detector(mock_claude):
    return LLMClauseDetector(mock_claude)


def _make_clauses(n, prefix="Section", text_len=50):
    """Helper to create n test clauses."""
    return [
        {
            "text": f"This is clause number {i} with some legal text. " * (text_len // 50),
            "section": f"{prefix}",
            "clause_number": f"{prefix}.{i}",
        }
        for i in range(n)
    ]


# ── _parse_response tests ────────────────────────────────────────────────────

class TestParseResponse:

    def test_valid_response_all_fields(self, detector):
        """Valid response with all fields parses correctly."""
        clauses = [
            {"text": "You waive all rights.", "section": "Rights", "clause_number": "Rights.0"},
            {"text": "We can modify terms.", "section": "Terms", "clause_number": "Terms.1"},
        ]
        response = {
            "risky_clauses": [
                {
                    "clause_number": "Rights.0",
                    "severity": "high",
                    "risk_category": "rights",
                    "explanation": "Waives fundamental rights.",
                    "consumer_impact": "You lose legal protections.",
                    "recommendation": "Consult a lawyer.",
                },
            ]
        }

        result = detector._parse_response(response, clauses)

        assert len(result) == 1
        assert result[0]["clause_number"] == "Rights.0"
        assert result[0]["severity"] == "high"
        assert result[0]["risk_category"] == "rights"
        assert result[0]["clause_text"] == "You waive all rights."
        assert result[0]["detection_source"] == "llm"

    def test_unknown_clause_number_skipped(self, detector):
        """Finding referencing nonexistent clause is skipped."""
        clauses = [{"text": "Some text.", "section": "A", "clause_number": "A.0"}]
        response = {
            "risky_clauses": [
                {"clause_number": "Z.99", "severity": "high", "risk_category": "other", "explanation": "Bad."}
            ]
        }

        result = detector._parse_response(response, clauses)
        assert len(result) == 0

    def test_invalid_severity_defaults_to_medium(self, detector):
        """Invalid severity string defaults to 'medium'."""
        clauses = [{"text": "Text.", "section": "A", "clause_number": "A.0"}]
        response = {
            "risky_clauses": [
                {"clause_number": "A.0", "severity": "EXTREME", "risk_category": "other", "explanation": "Bad."}
            ]
        }

        result = detector._parse_response(response, clauses)
        assert len(result) == 1
        assert result[0]["severity"] == "medium"

    def test_empty_risky_clauses(self, detector):
        """Empty risky_clauses list returns empty."""
        clauses = [{"text": "Text.", "section": "A", "clause_number": "A.0"}]
        response = {"risky_clauses": []}

        result = detector._parse_response(response, clauses)
        assert result == []

    def test_non_list_risky_clauses_returns_empty(self, detector):
        """Non-list risky_clauses returns empty."""
        clauses = [{"text": "Text.", "section": "A", "clause_number": "A.0"}]
        response = {"risky_clauses": "not a list"}

        result = detector._parse_response(response, clauses)
        assert result == []

    def test_suffix_matching(self, detector):
        """LLM returns '3' but input has 'Section.3' — matches via suffix."""
        clauses = [
            {"text": "Clause three text.", "section": "Section", "clause_number": "Section.3"},
        ]
        response = {
            "risky_clauses": [
                {"clause_number": "3", "severity": "medium", "risk_category": "other", "explanation": "Risky."}
            ]
        }

        result = detector._parse_response(response, clauses)
        assert len(result) == 1
        assert result[0]["clause_number"] == "Section.3"

    def test_numeric_only_matching(self, detector):
        """LLM returns 'Clause 5' and input has '5' — matches via numeric extraction."""
        clauses = [
            {"text": "Some legal text.", "section": "A", "clause_number": "5"},
        ]
        response = {
            "risky_clauses": [
                {"clause_number": "Clause 5", "severity": "low", "risk_category": "other", "explanation": "Minor."}
            ]
        }

        result = detector._parse_response(response, clauses)
        assert len(result) == 1
        assert result[0]["clause_number"] == "5"

    def test_ambiguous_suffix_match_skipped(self, detector):
        """Multiple suffix matches → finding is skipped (ambiguous)."""
        clauses = [
            {"text": "Text A.", "section": "A", "clause_number": "A.3"},
            {"text": "Text B.", "section": "B", "clause_number": "B.3"},
        ]
        response = {
            "risky_clauses": [
                {"clause_number": "3", "severity": "high", "risk_category": "other", "explanation": "Bad."}
            ]
        }

        result = detector._parse_response(response, clauses)
        # Suffix ".3" matches both A.3 and B.3 — ambiguous.
        # Numeric match also yields 2 candidates. Should be skipped.
        assert len(result) == 0


# ── _split_into_batches tests ────────────────────────────────────────────────

class TestSplitIntoBatches:

    def test_small_input_single_batch(self, detector):
        """Small clause list fits in one batch."""
        clauses = _make_clauses(5)
        batches = detector._split_into_batches(clauses)
        assert len(batches) == 1
        assert batches[0] == clauses

    def test_large_input_splits(self, detector):
        """Large clause list splits into multiple batches."""
        # Create clauses with enough text to exceed MAX_INPUT_TOKENS
        # Each clause ~500 words → ~650 tokens + 20 overhead = ~670 tokens
        # 200 clauses * 670 ≈ 134,000 tokens > 80,000 limit
        clauses = [
            {
                "text": "word " * 500,
                "section": "S",
                "clause_number": f"S.{i}",
            }
            for i in range(200)
        ]
        batches = detector._split_into_batches(clauses)
        assert len(batches) >= 2
        # All clauses preserved
        total = sum(len(b) for b in batches)
        assert total == 200

    def test_single_oversized_clause(self, detector):
        """Single clause exceeding limit is returned as-is."""
        clauses = [{"text": "word " * 100000, "section": "S", "clause_number": "S.0"}]
        batches = detector._split_into_batches(clauses)
        assert len(batches) == 1
        assert batches[0] == clauses


# ── detect_risky_clauses tests ───────────────────────────────────────────────

class TestDetectRiskyClauses:

    @pytest.mark.asyncio
    async def test_happy_path(self, detector, mock_claude):
        """End-to-end detection with mocked Claude response."""
        mock_claude.create_structured_completion.return_value = {
            "risky_clauses": [
                {
                    "clause_number": "1",
                    "severity": "high",
                    "risk_category": "rights",
                    "explanation": "Waives rights.",
                    "consumer_impact": "Lose protections.",
                    "recommendation": "Review carefully.",
                }
            ]
        }

        clauses = [{"text": "You waive all legal rights.", "section": "Legal", "clause_number": "1"}]
        result = await detector.detect_risky_clauses(clauses, "TestCo", "general")

        assert len(result) == 1
        assert result[0]["severity"] == "high"
        mock_claude.create_structured_completion.assert_called_once()

    @pytest.mark.asyncio
    async def test_empty_clauses(self, detector, mock_claude):
        """Empty clause list returns empty without calling Claude."""
        result = await detector.detect_risky_clauses([], "TestCo")
        assert result == []
        mock_claude.create_structured_completion.assert_not_called()

    @pytest.mark.asyncio
    async def test_claude_failure_graceful(self, detector, mock_claude):
        """Claude API failure returns empty list (graceful degradation)."""
        mock_claude.create_structured_completion.side_effect = Exception("API timeout")

        clauses = [{"text": "Some clause.", "section": "A", "clause_number": "1"}]
        result = await detector.detect_risky_clauses(clauses, "TestCo")

        assert result == []


# ── _format_clauses tests ────────────────────────────────────────────────────

class TestFormatClauses:

    def test_long_clause_truncated(self, detector):
        """Clauses longer than 2000 chars are truncated."""
        clauses = [{"text": "x" * 3000, "section": "A", "clause_number": "A.0"}]
        formatted = detector._format_clauses(clauses)
        assert "... [truncated]" in formatted
        # Original 3000 chars should be cut to 2000 + truncation marker
        assert len(formatted) < 3000


# ── _majority_vote_critical tests (Layer 5.1) ────────────────────────────────


def _critical_finding(clause_number: str = "1", text: str = "You waive all rights.") -> dict:
    """Helper to build a typical LLM-sourced critical finding."""
    return {
        "clause_number": clause_number,
        "section": "Legal",
        "clause_text": text,
        "severity": "critical",
        "risk_category": "rights",
        "explanation": "Test.",
        "consumer_impact": "Test.",
        "recommendation": "Test.",
        "detection_source": "llm",
    }


def _vote_response(severity: str, category: str = "rights", rationale: str = "r") -> dict:
    return {"severity": severity, "risk_category": category, "rationale": rationale}


class TestMajorityVoteCritical:

    @pytest.mark.asyncio
    async def test_three_of_three_keeps_majority(self, detector, mock_claude):
        """All 3 votes agree → severity preserved with vote_agreement='3/3'."""
        mock_claude.create_structured_completion.side_effect = [
            _vote_response("critical"),
            _vote_response("critical"),
            _vote_response("critical"),
        ]
        finding = _critical_finding()
        result = await detector._majority_vote_critical(finding)
        assert result is not None
        assert result["severity"] == "critical"
        assert result["vote_severity"] == "critical"
        assert result["vote_agreement"] == "3/3"
        assert result["original_severity"] == "critical"
        assert result["was_voted"] is True
        assert result["vote_distribution"]["critical"] == 3
        # Voted severity should be exposed alongside original.
        assert result["vote_distribution"]["high"] == 0

    @pytest.mark.asyncio
    async def test_two_of_three_demotes(self, detector, mock_claude):
        """2/3 vote 'high' → severity demoted from critical → high."""
        mock_claude.create_structured_completion.side_effect = [
            _vote_response("high"),
            _vote_response("high"),
            _vote_response("critical"),
        ]
        finding = _critical_finding()
        result = await detector._majority_vote_critical(finding)
        assert result is not None
        assert result["severity"] == "high"
        assert result["vote_severity"] == "high"
        assert result["vote_agreement"] == "2/3"
        assert result["original_severity"] == "critical"
        assert result["vote_distribution"]["high"] == 2
        assert result["vote_distribution"]["critical"] == 1

    @pytest.mark.asyncio
    async def test_one_one_one_split_keeps_original(self, detector, mock_claude):
        """1-1-1 split → original severity preserved, agreement='split'."""
        mock_claude.create_structured_completion.side_effect = [
            _vote_response("critical"),
            _vote_response("high"),
            _vote_response("medium"),
        ]
        finding = _critical_finding()
        result = await detector._majority_vote_critical(finding)
        assert result is not None
        assert result["severity"] == "critical"  # original preserved
        assert result["vote_agreement"] == "split"
        assert result["original_severity"] == "critical"
        assert result["was_voted"] is True
        # Distribution still recorded.
        assert result["vote_distribution"]["critical"] == 1
        assert result["vote_distribution"]["high"] == 1
        assert result["vote_distribution"]["medium"] == 1

    @pytest.mark.asyncio
    async def test_all_votes_fail_returns_none(self, detector, mock_claude):
        """When all 3 vote calls raise, return None (no update)."""
        mock_claude.create_structured_completion.side_effect = [
            Exception("api down"),
            Exception("api down"),
            Exception("api down"),
        ]
        finding = _critical_finding()
        result = await detector._majority_vote_critical(finding)
        assert result is None

    @pytest.mark.asyncio
    async def test_cost_cap_blocks_vote(self, detector, mock_claude):
        """When projected cost exceeds MAX_LLM_USD_PER_DOC, vote is skipped."""
        # Pre-load the cost tracker close to the cap so projected exceeds it.
        from app.core.config import settings
        detector._cost_tracker_usd = settings.MAX_LLM_USD_PER_DOC + 1.0
        finding = _critical_finding()
        result = await detector._majority_vote_critical(finding)
        # Cost cap means we never call Claude — return None and bump skipped.
        assert result is None
        assert detector._votes_skipped_by_cost == 1
        assert detector._cost_capped is True
        mock_claude.create_structured_completion.assert_not_called()

    @pytest.mark.asyncio
    async def test_vote_demotes_to_medium(self, detector, mock_claude):
        """Three 'medium' votes → demoted to medium."""
        mock_claude.create_structured_completion.side_effect = [
            _vote_response("medium"),
            _vote_response("medium"),
            _vote_response("medium"),
        ]
        finding = _critical_finding()
        result = await detector._majority_vote_critical(finding)
        assert result is not None
        assert result["severity"] == "medium"
        assert result["vote_agreement"] == "3/3"


class TestSelfConsistencyIntegration:

    @pytest.mark.asyncio
    async def test_flag_off_skips_voting(self, detector, mock_claude, monkeypatch):
        """When SELF_CONSISTENCY_ENABLED=False, no extra vote calls happen."""
        # Default flag is off in tests, but be explicit.
        monkeypatch.setattr(llm_module, "SELF_CONSISTENCY_ENABLED", False)
        mock_claude.create_structured_completion.return_value = {
            "risky_clauses": [
                {
                    "clause_number": "1",
                    "severity": "critical",
                    "risk_category": "rights",
                    "explanation": "Bad.",
                    "consumer_impact": "Bad.",
                    "recommendation": "Run.",
                }
            ]
        }
        clauses = [{"text": "You waive everything.", "section": "X", "clause_number": "1"}]
        result = await detector.detect_risky_clauses(clauses, "TestCo")
        assert len(result) == 1
        # Exactly one call — the batch detection. No vote calls.
        assert mock_claude.create_structured_completion.call_count == 1
        assert result[0]["severity"] == "critical"
        # No voting fields added when flag is off.
        assert "was_voted" not in result[0]

    @pytest.mark.asyncio
    async def test_flag_on_runs_vote_on_critical(self, detector, mock_claude, monkeypatch):
        """When flag is ON, criticals get re-voted; non-criticals don't."""
        monkeypatch.setattr(llm_module, "SELF_CONSISTENCY_ENABLED", True)
        # First call = batch detection returns 1 critical and 1 medium.
        # Next 3 calls = vote responses for the critical only.
        mock_claude.create_structured_completion.side_effect = [
            {
                "risky_clauses": [
                    {
                        "clause_number": "1",
                        "severity": "critical",
                        "risk_category": "rights",
                        "explanation": "x",
                        "consumer_impact": "x",
                        "recommendation": "x",
                    },
                    {
                        "clause_number": "2",
                        "severity": "medium",
                        "risk_category": "data",
                        "explanation": "y",
                        "consumer_impact": "y",
                        "recommendation": "y",
                    },
                ]
            },
            _vote_response("high"),
            _vote_response("high"),
            _vote_response("critical"),
        ]
        clauses = [
            {"text": "Waiver.", "section": "X", "clause_number": "1"},
            {"text": "Data collection.", "section": "Y", "clause_number": "2"},
        ]
        result = await detector.detect_risky_clauses(clauses, "TestCo")
        assert len(result) == 2
        # 1 batch + 3 votes = 4 total calls.
        assert mock_claude.create_structured_completion.call_count == 4
        # The critical (clause 1) should have been voted and demoted to high.
        by_id = {r["clause_number"]: r for r in result}
        assert by_id["1"]["severity"] == "high"
        assert by_id["1"]["was_voted"] is True
        assert by_id["1"]["vote_agreement"] == "2/3"
        # The medium should be untouched.
        assert by_id["2"]["severity"] == "medium"
        assert "was_voted" not in by_id["2"]

    @pytest.mark.asyncio
    async def test_cap_enforced_when_too_many_criticals(self, detector, mock_claude, monkeypatch):
        """More than MAX_CRITICAL_VOTES_PER_DOC criticals → only first N voted."""
        monkeypatch.setattr(llm_module, "SELF_CONSISTENCY_ENABLED", True)
        # 6 criticals exceeds the cap of 5.
        risky = [
            {
                "clause_number": str(i),
                "severity": "critical",
                "risk_category": "rights",
                "explanation": f"e{i}",
                "consumer_impact": "x",
                "recommendation": "x",
            }
            for i in range(6)
        ]
        # 1 batch response + (5 cap × 3 vote calls) = 16 total.
        responses = [{"risky_clauses": risky}]
        # All criticals get voted 3/3 critical for simplicity.
        responses += [_vote_response("critical")] * (MAX_CRITICAL_VOTES_PER_DOC * SELF_CONSISTENCY_VOTES)
        mock_claude.create_structured_completion.side_effect = responses
        clauses = [{"text": f"c{i}", "section": "X", "clause_number": str(i)} for i in range(6)]
        result = await detector.detect_risky_clauses(clauses, "TestCo")
        # Exactly 1 batch + 5 × 3 votes consumed from the queue.
        assert mock_claude.create_structured_completion.call_count == 1 + MAX_CRITICAL_VOTES_PER_DOC * SELF_CONSISTENCY_VOTES
        # First 5 criticals should have was_voted=True, 6th should not.
        voted_count = sum(1 for r in result if r.get("was_voted"))
        assert voted_count == MAX_CRITICAL_VOTES_PER_DOC

    @pytest.mark.asyncio
    async def test_return_aggregate_shape(self, detector, mock_claude, monkeypatch):
        """return_aggregate=True returns dict with findings + cost + stats."""
        monkeypatch.setattr(llm_module, "SELF_CONSISTENCY_ENABLED", False)
        mock_claude.create_structured_completion.return_value = {"risky_clauses": []}
        clauses = [{"text": "x", "section": "X", "clause_number": "1"}]
        result = await detector.detect_risky_clauses(clauses, "TestCo", return_aggregate=True)
        assert isinstance(result, dict)
        assert "findings" in result
        assert "cost_usd" in result
        assert "cost_capped" in result
        assert "votes_run" in result
        assert "votes_skipped_by_cost" in result
        assert result["cost_capped"] is False
        assert result["votes_run"] == 0


class TestEstimateCallCost:

    def test_cost_uses_claude_pricing(self):
        """Cost estimation uses Sonnet 4.5 pricing constants."""
        cost = LLMClauseDetector._estimate_call_cost_usd(1_000_000, 0)
        assert cost == pytest.approx(3.0, abs=1e-6)
        cost = LLMClauseDetector._estimate_call_cost_usd(0, 1_000_000)
        assert cost == pytest.approx(15.0, abs=1e-6)

    def test_cost_combined(self):
        """Combined input + output cost."""
        cost = LLMClauseDetector._estimate_call_cost_usd(1000, 1000)
        expected = 1000 * CLAUDE_PRICING["input_per_token"] + 1000 * CLAUDE_PRICING["output_per_token"]
        assert cost == pytest.approx(expected, abs=1e-9)
