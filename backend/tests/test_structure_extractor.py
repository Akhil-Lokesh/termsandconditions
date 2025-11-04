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
