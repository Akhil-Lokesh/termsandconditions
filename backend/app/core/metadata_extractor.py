"""
Metadata extractor for T&C documents.

Uses GPT-4 to extract structured metadata from Terms & Conditions documents:
- Company name
- Jurisdiction
- Effective date
- Document type
- Governing law
- Version
- Contact information
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime

from app.services.openai_service import OpenAIService
from app.prompts.metadata_prompts import (
    METADATA_EXTRACTION_PROMPT,
    CLAUSE_TYPE_CLASSIFICATION_PROMPT,
)
from app.utils.exceptions import DocumentProcessingError

logger = logging.getLogger(__name__)


class MetadataExtractor:
    """Extracts metadata from T&C documents using GPT-4."""

    def __init__(self, openai_service: OpenAIService):
        """
        Initialize metadata extractor.

        Args:
            openai_service: OpenAI service instance for LLM calls
        """
        self.openai = openai_service

    async def extract_metadata(self, text: str) -> Dict[str, Any]:
        """
        Extract structured metadata from document text.

        Args:
            text: Full document text

        Returns:
            Dict with extracted metadata fields

        Raises:
            DocumentProcessingError: If extraction fails
        """
        try:
            # Use first 2000 characters for metadata extraction
            # (most metadata is in the header/preamble)
            text_preview = text[:2000]

            logger.info("Extracting metadata from document...")

            # Build prompt
            prompt = METADATA_EXTRACTION_PROMPT.format(text_preview=text_preview)

            # Call GPT-4 for structured extraction
            metadata = await self.openai.create_structured_completion(
                prompt=prompt,
                model=self.openai.gpt4_model,
                temperature=0.0,  # Deterministic for consistency
            )

            # Validate and clean metadata
            cleaned_metadata = self._clean_metadata(metadata)

            logger.info(
                f"Metadata extracted: company={cleaned_metadata.get('company_name')}, "
                f"jurisdiction={cleaned_metadata.get('jurisdiction')}"
            )

            return cleaned_metadata

        except Exception as e:
            logger.error(f"Metadata extraction failed: {e}", exc_info=True)
            # Return empty metadata rather than failing completely
            return self._get_default_metadata()

    async def classify_clause_type(self, clause_text: str) -> str:
        """
        Classify a clause into a category.

        Args:
            clause_text: Text of the clause

        Returns:
            Category name (e.g., "payment_terms", "liability")

        Raises:
            DocumentProcessingError: If classification fails
        """
        try:
            # Build prompt
            prompt = CLAUSE_TYPE_CLASSIFICATION_PROMPT.format(clause_text=clause_text)

            # Call GPT-4 for classification
            category = await self.openai.create_completion(
                prompt=prompt,
                model=self.openai.gpt35_model,  # Use GPT-3.5 for simple classification
                temperature=0.0,
                max_tokens=50,
            )

            # Clean response (remove whitespace, newlines)
            category = category.strip().lower()

            # Validate category
            valid_categories = [
                "payment_terms",
                "liability",
                "termination",
                "intellectual_property",
                "privacy",
                "dispute_resolution",
                "user_obligations",
                "service_description",
                "modifications",
                "warranties",
                "general",
            ]

            if category not in valid_categories:
                logger.warning(
                    f"Invalid category '{category}' returned, using 'general'"
                )
                category = "general"

            return category

        except Exception as e:
            logger.error(f"Clause classification failed: {e}", exc_info=True)
            return "general"  # Default fallback

    def _clean_metadata(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Clean and validate extracted metadata.

        Args:
            metadata: Raw metadata from GPT-4

        Returns:
            Cleaned metadata dict
        """
        cleaned = {}

        # String fields
        for field in [
            "company_name",
            "jurisdiction",
            "document_type",
            "governing_law",
            "version",
            "contact_email",
            "website",
        ]:
            value = metadata.get(field)
            if value and value != "null" and value.strip():
                cleaned[field] = value.strip()
            else:
                cleaned[field] = None

        # Date fields
        for date_field in ["effective_date", "last_updated"]:
            value = metadata.get(date_field)
            if value and value != "null":
                # Try to parse date
                try:
                    # If already in ISO format, keep it
                    if isinstance(value, str) and len(value) == 10:
                        datetime.strptime(value, "%Y-%m-%d")
                        cleaned[date_field] = value
                    else:
                        cleaned[date_field] = None
                except ValueError:
                    logger.warning(f"Invalid date format for {date_field}: {value}")
                    cleaned[date_field] = None
            else:
                cleaned[date_field] = None

        # Add extraction timestamp
        cleaned["extracted_at"] = datetime.utcnow().isoformat()

        return cleaned

    def _get_default_metadata(self) -> Dict[str, Any]:
        """
        Get default metadata structure when extraction fails.

        Returns:
            Dict with null values for all fields
        """
        return {
            "company_name": None,
            "jurisdiction": None,
            "effective_date": None,
            "last_updated": None,
            "document_type": "Terms of Service",  # Reasonable default
            "governing_law": None,
            "version": None,
            "contact_email": None,
            "website": None,
            "extracted_at": datetime.utcnow().isoformat(),
            "extraction_failed": True,
        }

    async def enrich_document_metadata(
        self, base_metadata: Dict[str, Any], text: str
    ) -> Dict[str, Any]:
        """
        Enrich basic metadata with extracted information.

        Args:
            base_metadata: Basic metadata (e.g., from PDF)
            text: Full document text

        Returns:
            Enriched metadata dict
        """
        try:
            extracted = await self.extract_metadata(text)

            # Merge with base metadata (extracted takes precedence)
            enriched = {**base_metadata, **extracted}

            return enriched

        except Exception as e:
            logger.error(f"Metadata enrichment failed: {e}", exc_info=True)
            return base_metadata
