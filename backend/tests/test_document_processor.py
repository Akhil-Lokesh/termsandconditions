"""Tests for document processor."""

import pytest
from app.core.document_processor import DocumentProcessor


@pytest.mark.asyncio
async def test_document_processor_init():
    """Test document processor initialization."""
    processor = DocumentProcessor()
    assert processor is not None
    assert processor.supported_formats == [".pdf"]


@pytest.mark.asyncio
async def test_extract_text_success(sample_pdf_path):
    """Test successful text extraction."""
    # TODO: Create a real sample PDF for testing
    pytest.skip("Requires sample PDF file")

    processor = DocumentProcessor()
    result = await processor.extract_text(sample_pdf_path)

    assert "text" in result
    assert "page_count" in result
    assert "extraction_method" in result
    assert "metadata" in result
    assert result["page_count"] > 0


@pytest.mark.asyncio
async def test_extract_text_invalid_file():
    """Test extraction with invalid file."""
    processor = DocumentProcessor()

    with pytest.raises(Exception):
        await processor.extract_text("nonexistent_file.pdf")


@pytest.mark.asyncio
async def test_is_tc_document():
    """Test T&C document detection."""
    processor = DocumentProcessor()

    # Test with T&C text
    tc_text = "These are the Terms and Conditions for using our service."
    assert await processor.is_tc_document(tc_text) is True

    # Test with non-T&C text
    non_tc_text = "This is a random document about cats and dogs."
    assert await processor.is_tc_document(non_tc_text) is False
