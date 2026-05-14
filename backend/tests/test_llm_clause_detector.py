"""Tests for LLMClauseDetector."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.core.llm_clause_detector import LLMClauseDetector, MAX_INPUT_TOKENS


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
