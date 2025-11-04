"""
Document processor for extracting text and metadata from PDF files.

Uses pdfplumber as primary method with PyPDF2 as fallback.
"""

from typing import Dict, Any
import logging

import PyPDF2
import pdfplumber

logger = logging.getLogger(__name__)


class DocumentProcessor:
    """Processes T&C PDF documents and extracts text and metadata."""

    def __init__(self):
        """Initialize document processor."""
        self.supported_formats = [".pdf"]

    async def extract_text(self, pdf_path: str) -> Dict[str, Any]:
        """
        Extract text from PDF using fallback strategy.

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
                raise Exception(f"Failed to extract text from PDF: {e2}")

        # Get metadata
        metadata = await self._extract_pdf_metadata(pdf_path)

        return {
            "text": text,
            "page_count": metadata.get("page_count", 0),
            "extraction_method": method,
            "metadata": metadata
        }

    async def _extract_with_pdfplumber(self, pdf_path: str) -> str:
        """
        Extract text using pdfplumber (preserves layout).

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

        if not text_parts:
            raise Exception("No text extracted using pdfplumber")

        return "\n\n".join(text_parts)

    async def _extract_with_pypdf2(self, pdf_path: str) -> str:
        """
        Fallback: Extract text using PyPDF2.

        Args:
            pdf_path: Path to PDF file

        Returns:
            str: Extracted text
        """
        text_parts = []
        with open(pdf_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            for page in pdf_reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)

        if not text_parts:
            raise Exception("No text extracted using PyPDF2")

        return "\n\n".join(text_parts)

    async def _extract_pdf_metadata(self, pdf_path: str) -> Dict[str, Any]:
        """
        Extract PDF metadata (author, creation date, etc.).

        Args:
            pdf_path: Path to PDF file

        Returns:
            dict: PDF metadata
        """
        try:
            with open(pdf_path, 'rb') as file:
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
                    "modification_date": metadata.get("/ModDate", "")
                }
        except Exception as e:
            logger.warning(f"Failed to extract metadata: {e}")
            return {"page_count": 0}

    async def is_tc_document(self, text: str) -> bool:
        """
        Simple heuristic to check if document is a T&C.

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
            "terms & conditions"
        ]

        return any(indicator in text_lower for indicator in tc_indicators)
