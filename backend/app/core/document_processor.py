"""
Document processor for extracting text and metadata from PDF files.

Uses pdfplumber as primary method with PyPDF2 as fallback.
Properly handles blocking I/O operations in async context.
"""

import asyncio
from functools import partial
import logging
from pathlib import Path

import PyPDF2
import pdfplumber

from app.core.document_type_detector import DocumentTypeDetector

logger = logging.getLogger(__name__)


class DocumentProcessor:
    """Processes T&C PDF documents and extracts text and metadata."""

    def __init__(self):
        """Initialize document processor."""
        self.supported_formats = [".pdf"]
        self.type_detector = DocumentTypeDetector()

    async def extract_text(self, pdf_path: str) -> dict[str, any]:
        """
        Extract text from PDF using fallback strategy.

        Runs blocking I/O operations in thread pool to avoid blocking event loop.

        Args:
            pdf_path: Path to PDF file

        Returns:
            dict: {
                "text": str,
                "page_count": int,
                "extraction_method": str,
                "metadata": dict
            }

        Raises:
            Exception: If both extraction methods fail
        """
        logger.info(f"Extracting text from: {pdf_path}")

        try:
            # Try pdfplumber first (better formatting)
            text = await self._extract_with_pdfplumber(pdf_path)
            method = "pdfplumber"
            logger.info("Extracted text using pdfplumber")
        except Exception as e:
            logger.warning(f"pdfplumber failed: {e}, falling back to PyPDF2")
            try:
                text = await self._extract_with_pypdf2(pdf_path)
                method = "pypdf2"
                logger.info("Extracted text using PyPDF2")
            except Exception as e2:
                logger.error(f"PyPDF2 also failed: {e2}")
                raise Exception(f"Failed to extract text from PDF: {e2}") from e2

        # Get metadata
        metadata = await self._extract_pdf_metadata(pdf_path)

        # Detect document type
        filename = Path(pdf_path).stem
        type_result = self.type_detector.detect_type(text, title=filename)

        # Add document type info to metadata
        metadata["document_type"] = type_result.document_type
        metadata["document_type_display"] = self.type_detector.get_display_name(type_result.document_type)
        metadata["document_type_confidence"] = type_result.confidence
        metadata["document_type_description"] = self.type_detector.get_description(type_result.document_type)

        logger.info(
            f"Detected document type: {type_result.document_type} "
            f"({type_result.confidence:.0%} confidence)"
        )

        return {
            "text": text,
            "page_count": metadata.get("page_count", 0),
            "extraction_method": method,
            "metadata": metadata,
            "document_type": type_result.document_type,
            "document_type_confidence": type_result.confidence,
        }

    async def _extract_with_pdfplumber(self, pdf_path: str) -> str:
        """
        Extract text using pdfplumber (preserves layout).

        Runs in thread pool to avoid blocking async event loop.

        Args:
            pdf_path: Path to PDF file

        Returns:
            str: Extracted text

        Raises:
            Exception: If extraction fails or no text found
        """
        loop = asyncio.get_event_loop()
        text = await loop.run_in_executor(
            None,  # Use default ThreadPoolExecutor
            partial(self._sync_extract_with_pdfplumber, pdf_path)
        )

        if not text:
            raise Exception("No text extracted using pdfplumber")

        return text

    def _sync_extract_with_pdfplumber(self, pdf_path: str) -> str:
        """
        Synchronous pdfplumber extraction (runs in thread pool).

        Args:
            pdf_path: Path to PDF file

        Returns:
            str: Extracted text
        """
        text_parts = []
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)

        return "\n\n".join(text_parts)

    async def _extract_with_pypdf2(self, pdf_path: str) -> str:
        """
        Fallback: Extract text using PyPDF2.

        Runs in thread pool to avoid blocking async event loop.

        Args:
            pdf_path: Path to PDF file

        Returns:
            str: Extracted text

        Raises:
            Exception: If extraction fails or no text found
        """
        loop = asyncio.get_event_loop()
        text = await loop.run_in_executor(
            None,
            partial(self._sync_extract_with_pypdf2, pdf_path)
        )

        if not text:
            raise Exception("No text extracted using PyPDF2")

        return text

    def _sync_extract_with_pypdf2(self, pdf_path: str) -> str:
        """
        Synchronous PyPDF2 extraction (runs in thread pool).

        Args:
            pdf_path: Path to PDF file

        Returns:
            str: Extracted text
        """
        text_parts = []
        with open(pdf_path, "rb") as file:
            pdf_reader = PyPDF2.PdfReader(file)
            for page in pdf_reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)

        return "\n\n".join(text_parts)

    async def _extract_pdf_metadata(self, pdf_path: str) -> dict[str, any]:
        """
        Extract PDF metadata (author, creation date, etc.).

        Runs in thread pool to avoid blocking async event loop.

        Args:
            pdf_path: Path to PDF file

        Returns:
            dict: PDF metadata
        """
        try:
            loop = asyncio.get_event_loop()
            metadata = await loop.run_in_executor(
                None,
                partial(self._sync_extract_pdf_metadata, pdf_path)
            )
            return metadata
        except Exception as e:
            logger.warning(f"Failed to extract metadata: {e}")
            return {"page_count": 0}

    def _sync_extract_pdf_metadata(self, pdf_path: str) -> dict[str, any]:
        """
        Synchronous metadata extraction (runs in thread pool).

        Args:
            pdf_path: Path to PDF file

        Returns:
            dict: PDF metadata
        """
        with open(pdf_path, "rb") as file:
            pdf_reader = PyPDF2.PdfReader(file)
            metadata = pdf_reader.metadata or {}

            return {
                "page_count": len(pdf_reader.pages),
                "author": metadata.get("/Author", ""),
                "title": metadata.get("/Title", ""),
                "subject": metadata.get("/Subject", ""),
                "creator": metadata.get("/Creator", ""),
                "producer": metadata.get("/Producer", ""),
                "creation_date": metadata.get("/CreationDate", ""),
                "modification_date": metadata.get("/ModDate", ""),
            }

    def is_tc_document(self, text: str) -> bool:
        """
        Simple heuristic to check if document is a T&C.

        This is a synchronous operation (string matching), no need for async.

        Args:
            text: Extracted text from document

        Returns:
            bool: True if likely a T&C document
        """
        text_lower = text.lower()
        tc_indicators = [
            "terms and conditions",
            "terms of service",
            "terms of use",
            "user agreement",
            "service agreement",
            "terms & conditions",
        ]

        return any(indicator in text_lower for indicator in tc_indicators)
