"""Tests for structure extractor."""

import pytest
from app.core.structure_extractor import StructureExtractor


@pytest.mark.asyncio
async def test_structure_extractor_init():
    """Test structure extractor initialization."""
    extractor = StructureExtractor()
    assert extractor is not None


@pytest.mark.asyncio
async def test_extract_structure_basic():
    """Test basic structure extraction."""
    extractor = StructureExtractor()

    # Sample T&C text with clear structure
    text = """
1. Introduction
This agreement governs your use of our service.

2. User Obligations
2.1 You must be at least 18 years old.
2.2 You must provide accurate information.

3. Payment Terms
3.1 All fees are non-refundable.
    """

    result = await extractor.extract_structure(text)

    assert "sections" in result
    assert "num_sections" in result
    assert "num_clauses" in result
    assert result["num_sections"] >= 1


@pytest.mark.asyncio
async def test_extract_structure_no_clear_structure():
    """Test extraction when no clear structure is found."""
    extractor = StructureExtractor()

    # Text without clear sections
    text = "This is a simple text without any section markers."

    result = await extractor.extract_structure(text)

    assert result["num_sections"] == 1
    assert result["sections"][0]["title"] == "Terms and Conditions"


@pytest.mark.asyncio
async def test_wall_of_text_is_split_into_bounded_clauses():
    """Real-world regression: a ToS delivered as one unbroken line (no
    newlines, section markers glued inline) must NOT collapse into a single
    giant clause. The LLM checklist matches reliably on small clauses but
    misses needles buried in an 8k-word wall of text. Every clause must be
    bounded in size, and distinct buried clauses must land separately.
    """
    extractor = StructureExtractor()

    # ~1,600 words, ZERO newlines, inline "B. / G. / T." section markers —
    # the shape of the Apple Media Services T&C that collapsed to 1 clause.
    filler = "This clause describes routine service usage terms and conditions. "
    doc = (
        "These terms create a contract between you and the Company. "
        + filler * 40
        + "B. PAYMENTS your exclusive and sole remedy is replacement or refund "
        "of the price paid, as determined by the Company. "
        + filler * 40
        + "G. TERMINATION If the Company suspects that you have failed to comply, "
        "the Company may, without notice to you, terminate your account. "
        + filler * 40
        + "T. MISC you agree that the Company may disclose any data to law "
        "enforcement authorities without notifying you. "
        + filler * 40
    )
    assert "\n" not in doc

    result = await extractor.extract_structure(doc)

    clauses = [c for s in result["sections"] for c in s.get("clauses", [])]
    sizes = [len((c.get("text") or "").split()) for c in clauses]
    assert sizes, "expected at least one clause"
    # No clause may be an un-searchable wall of text.
    assert max(sizes) <= StructureExtractor.MAX_CLAUSE_WORDS, (
        f"largest clause is {max(sizes)} words "
        f"(cap {StructureExtractor.MAX_CLAUSE_WORDS})"
    )

    # The three distinct buried clauses must NOT all collapse into one clause.
    def clause_of(needle: str) -> int:
        hits = [i for i, c in enumerate(clauses) if needle in (c.get("text") or "")]
        return hits[0] if hits else -1

    sole = clause_of("sole remedy")
    term = clause_of("suspects that you have failed")
    law = clause_of("law enforcement authorities")
    assert sole != -1 and term != -1 and law != -1
    assert len({sole, term, law}) == 3, (
        f"buried clauses collapsed together: sole={sole} term={term} law={law}"
    )
