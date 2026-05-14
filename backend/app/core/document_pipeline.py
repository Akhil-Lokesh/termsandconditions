"""
Document Processing Pipeline.

Encapsulates the multi-step document processing flow:
1. Text extraction from PDF
2. Structure parsing (sections, clauses)
3. Semantic chunking
4. Embedding generation
5. Metadata extraction
6. Vector storage

Refactoring: Extract Class pattern to reduce complexity in upload.py
"""

import uuid
import logging
from dataclasses import dataclass
from typing import List, Dict, Any, Optional

from app.core.document_processor import DocumentProcessor
from app.core.structure_extractor import StructureExtractor
from app.core.legal_chunker import LegalChunker
from app.core.metadata_extractor import MetadataExtractor
from app.core.config import settings
from app.services.claude_service import ClaudeService
from app.services.embedding_service import EmbeddingService
from app.services.pinecone_service import PineconeService
from app.utils.exceptions import DocumentProcessingError

# Type hints for optional services
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


@dataclass
class ExtractionResult:
    """Result from PDF text extraction."""
    text: str
    page_count: int
    extraction_method: str
    # Detected document type from DocumentTypeDetector (terms_of_service,
    # privacy_policy, eula, cookie_policy, other). Defaults to terms_of_service
    # when the extraction path doesn't run the detector (e.g., process_text).
    detected_document_type: str = "terms_of_service"
    detected_document_type_confidence: float = 0.0


@dataclass
class StructureResult:
    """Result from document structure parsing."""
    sections: List[Dict[str, Any]]
    num_clauses: int


@dataclass
class ProcessingResult:
    """Complete result from document processing pipeline."""
    doc_id: str
    text: str
    page_count: int
    sections: List[Dict[str, Any]]
    num_clauses: int
    chunks: List[Dict[str, Any]]
    metadata: Dict[str, Any]
    clause_records: List[Any]  # List of Clause model instances


class DocumentProcessingPipeline:
    """
    Orchestrates the document processing workflow.

    Separates concerns by delegating each step to specialized components
    while providing a clean, single-method interface for callers.
    """

    # Minimum text length to consider a document valid
    MIN_TEXT_LENGTH = 100

    def __init__(
        self,
        embedding_service: EmbeddingService,
        pinecone_service: PineconeService,
        claude_service: Optional[ClaudeService] = None,
    ):
        """
        Initialize the processing pipeline.

        Args:
            embedding_service: Embedding service for vector embeddings
            pinecone_service: Pinecone service for vector storage
            claude_service: Claude service for metadata extraction (optional, creates own if not provided)
        """
        self.embedding_service = embedding_service
        self.pinecone_service = pinecone_service
        self.claude_service = claude_service or ClaudeService()

        # Initialize processors
        self.document_processor = DocumentProcessor()
        self.structure_extractor = StructureExtractor()
        self.chunker = LegalChunker()
        self.metadata_extractor = MetadataExtractor(self.claude_service)

    async def process_document(
        self,
        file_path: str,
        doc_id: str,
    ) -> ProcessingResult:
        """
        Process a document through the full pipeline.

        Args:
            file_path: Path to the PDF file
            doc_id: Unique document identifier

        Returns:
            ProcessingResult with all processing outputs

        Raises:
            DocumentProcessingError: If any step fails
        """
        logger.info(f"Starting document processing pipeline for {doc_id}")

        # Step 1: Extract text
        extraction = await self._extract_text(file_path)

        # Step 2: Parse structure
        structure = await self._parse_structure(extraction.text)

        # Step 3: Create chunks
        chunks = await self._create_chunks(structure.sections)

        # Step 4: Generate embeddings
        chunks = await self._generate_embeddings(chunks)

        # Step 5: Extract metadata
        metadata = await self._extract_metadata(extraction.text)

        # Step 5b: Merge DocumentTypeDetector results into metadata.
        # Use distinct keys ('detected_document_type', 'detected_document_type_confidence')
        # to avoid clobbering MetadataExtractor's 'document_type' which holds the
        # human-readable display name (e.g. "Terms of Service").
        metadata["detected_document_type"] = extraction.detected_document_type
        metadata["detected_document_type_confidence"] = extraction.detected_document_type_confidence

        # Step 6: Store vectors
        await self._store_vectors(chunks, doc_id)

        # Step 7: Prepare clause records (for database) with metadata extraction
        clause_records = await self._prepare_clause_records(
            structure.sections, doc_id
        )

        logger.info(f"Document processing pipeline complete for {doc_id}")

        return ProcessingResult(
            doc_id=doc_id,
            text=extraction.text,
            page_count=extraction.page_count,
            sections=structure.sections,
            num_clauses=structure.num_clauses,
            chunks=chunks,
            metadata=metadata,
            clause_records=clause_records,
        )

    async def process_text(
        self,
        text: str,
        doc_id: str,
        filename: str = "Pasted Text",
    ) -> ProcessingResult:
        """
        Process raw text (pasted T&C) through the pipeline.

        Args:
            text: Raw T&C text content
            doc_id: Unique document identifier
            filename: Optional filename for the document

        Returns:
            ProcessingResult with all processing outputs

        Raises:
            DocumentProcessingError: If any step fails
        """
        logger.info(f"Starting text processing pipeline for {doc_id}")

        # Validate text length
        if len(text.strip()) < self.MIN_TEXT_LENGTH:
            raise DocumentProcessingError(
                f"Text too short ({len(text.strip())} chars). Please provide at least {self.MIN_TEXT_LENGTH} characters."
            )

        # Step 0: Detect document type directly on raw text (no PDF available).
        try:
            type_result = self.document_processor.type_detector.detect_type(
                text, title=filename
            )
            detected_doc_type = type_result.document_type
            detected_doc_type_conf = float(type_result.confidence or 0.0)
            logger.info(
                f"Detected document type (text upload): {detected_doc_type} "
                f"(conf={detected_doc_type_conf:.2f})"
            )
        except Exception as e:
            logger.warning(f"Document type detection failed on text upload: {e}")
            detected_doc_type = "terms_of_service"
            detected_doc_type_conf = 0.0

        # Step 1: Parse structure (skip PDF extraction)
        structure = await self._parse_structure(text)

        # Step 2: Create chunks
        chunks = await self._create_chunks(structure.sections)

        # Step 3: Generate embeddings
        chunks = await self._generate_embeddings(chunks)

        # Step 4: Extract metadata
        metadata = await self._extract_metadata(text)

        # Step 4b: Merge DocumentTypeDetector results into metadata (see process_document).
        metadata["detected_document_type"] = detected_doc_type
        metadata["detected_document_type_confidence"] = detected_doc_type_conf

        # Step 5: Store vectors
        await self._store_vectors(chunks, doc_id)

        # Step 6: Prepare clause records (for database) with metadata extraction
        clause_records = await self._prepare_clause_records(
            structure.sections, doc_id
        )

        # Estimate page count from text length (roughly 3000 chars per page)
        estimated_pages = max(1, len(text) // 3000)

        logger.info(f"Text processing pipeline complete for {doc_id}")

        return ProcessingResult(
            doc_id=doc_id,
            text=text,
            page_count=estimated_pages,
            sections=structure.sections,
            num_clauses=structure.num_clauses,
            chunks=chunks,
            metadata=metadata,
            clause_records=clause_records,
        )

    async def _extract_text(self, file_path: str) -> ExtractionResult:
        """
        Extract text from PDF document.

        Args:
            file_path: Path to PDF file

        Returns:
            ExtractionResult with text, page count, and method

        Raises:
            DocumentProcessingError: If extraction fails or text is too short
        """
        logger.info("Step 1: Extracting text from PDF...")

        extracted = await self.document_processor.extract_text(file_path)

        text = extracted["text"]
        page_count = extracted["page_count"]
        extraction_method = extracted["extraction_method"]
        detected_doc_type = extracted.get("document_type", "terms_of_service")
        detected_doc_type_conf = float(extracted.get("document_type_confidence", 0.0) or 0.0)

        logger.info(
            f"Text extracted: {len(text)} chars, {page_count} pages, "
            f"method={extraction_method}, detected_type={detected_doc_type} "
            f"(conf={detected_doc_type_conf:.2f})"
        )

        if len(text) < self.MIN_TEXT_LENGTH:
            raise DocumentProcessingError(
                "Document text too short. This may be a scanned PDF or corrupted file."
            )

        return ExtractionResult(
            text=text,
            page_count=page_count,
            extraction_method=extraction_method,
            detected_document_type=detected_doc_type,
            detected_document_type_confidence=detected_doc_type_conf,
        )

    async def _parse_structure(self, text: str) -> StructureResult:
        """
        Parse document structure into sections and clauses.

        Args:
            text: Full document text

        Returns:
            StructureResult with sections and clause count

        Raises:
            DocumentProcessingError: If no clauses found
        """
        logger.info("Step 2: Parsing document structure...")

        structure = await self.structure_extractor.extract_structure(text)

        sections = structure["sections"]
        num_clauses = structure["num_clauses"]

        logger.info(
            f"Structure extracted: {num_clauses} clauses found in {len(sections)} sections"
        )

        if num_clauses == 0:
            raise DocumentProcessingError(
                "No structured clauses found in document. Unable to analyze."
            )

        return StructureResult(sections=sections, num_clauses=num_clauses)

    async def _create_chunks(
        self, sections: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Create semantic chunks from document sections.

        Args:
            sections: Parsed document sections

        Returns:
            List of chunk dictionaries
        """
        logger.info("Step 3: Creating semantic chunks...")

        chunks = await self.chunker.create_chunks(sections)

        logger.info(f"Created {len(chunks)} chunks for embedding")

        return chunks

    async def _generate_embeddings(
        self, chunks: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Generate embeddings for all chunks.

        Args:
            chunks: List of chunk dictionaries

        Returns:
            Chunks with embeddings added
        """
        logger.info("Step 4: Generating embeddings...")

        texts = [chunk["text"] for chunk in chunks]
        embeddings = await self.embedding_service.batch_create_embeddings(texts)

        logger.info(f"Generated {len(embeddings)} embeddings")

        # Add embeddings to chunks
        for chunk, embedding in zip(chunks, embeddings):
            chunk["embedding"] = embedding

        return chunks

    async def _extract_metadata(self, text: str) -> Dict[str, Any]:
        """
        Extract metadata from document text using Claude.

        Args:
            text: Full document text

        Returns:
            Metadata dictionary
        """
        logger.info("Step 5: Extracting metadata with Claude...")

        metadata = await self.metadata_extractor.extract_metadata(text)

        logger.info(
            f"Metadata extracted: Company={metadata.get('company_name', 'Unknown')}, "
            f"Jurisdiction={metadata.get('jurisdiction', 'Unknown')}"
        )

        return metadata

    async def _store_vectors(
        self, chunks: List[Dict[str, Any]], doc_id: str
    ) -> None:
        """
        Store chunk vectors in Pinecone.

        Args:
            chunks: Chunks with embeddings
            doc_id: Document identifier
        """
        logger.info("Step 6: Storing vectors in Pinecone...")

        await self.pinecone_service.upsert_chunks(
            chunks=chunks,
            namespace=settings.PINECONE_USER_NAMESPACE,
            document_id=doc_id,
        )

        logger.info(f"Stored {len(chunks)} vectors in Pinecone")

    async def _prepare_clause_records(
        self,
        sections: List[Dict[str, Any]],
        doc_id: str,
    ) -> List[Any]:
        """
        Prepare clause records for database storage with enriched metadata.

        Args:
            sections: Parsed document sections
            doc_id: Document identifier

        Returns:
            List of Clause model instances ready for database
        """
        from app.models.clause import Clause
        from app.core.risk_indicators import RiskIndicators

        logger.info("Preparing clause records for database with metadata extraction...")

        # Initialize risk detector once for efficiency
        risk_detector = RiskIndicators()

        clause_records = []

        for section in sections:
            section_name = section.get("title", "Unknown Section")
            section_number = section.get("number", "0")

            for clause in section.get("clauses", []):
                clause_text = clause.get("text", "")

                # Classify clause type locally (no API call) to avoid timeout
                clause_type = self._classify_clause_type_local(clause_text, section_name)

                # Detect risk indicators
                try:
                    detected_risks = risk_detector.detect_indicators(
                        clause_text=clause_text,
                        section_name=section_name
                    )
                    risk_indicators = [r.get("indicator", "") for r in detected_risks]
                    max_severity = self._calculate_max_severity(detected_risks)
                except Exception as e:
                    logger.debug(f"Failed to detect risk indicators: {e}")
                    risk_indicators = []
                    max_severity = "low"

                # Build enriched metadata
                clause_metadata = {
                    "section_number": section_number,
                    "clause_type": clause_type,
                    "risk_indicators": risk_indicators,
                    "pattern_severity": max_severity,
                    "pattern_count": len(risk_indicators),
                }

                clause_record = Clause(
                    id=str(uuid.uuid4()),
                    document_id=doc_id,
                    section=section_name,
                    clause_number=clause.get("id", ""),
                    text=clause_text,
                    clause_metadata=clause_metadata,
                )
                clause_records.append(clause_record)

        logger.info(f"Prepared {len(clause_records)} clause records with metadata")

        return clause_records

    def _classify_clause_type_local(self, clause_text: str, section_name: str) -> str:
        """Classify clause type using keyword matching (no API call)."""
        text_lower = clause_text.lower()
        section_lower = section_name.lower()

        keyword_map = {
            "payment_terms": ["payment", "fee", "charge", "billing", "refund", "subscription", "price"],
            "liability": ["liability", "liable", "indemnif", "damages", "limitation of liability"],
            "termination": ["terminat", "cancel", "suspend", "deactivat"],
            "intellectual_property": ["intellectual property", "copyright", "trademark", "license", "content you"],
            "privacy": ["privacy", "personal data", "data collection", "cookies", "tracking"],
            "dispute_resolution": ["arbitrat", "dispute", "governing law", "jurisdiction", "class action"],
            "user_obligations": ["you agree", "you must", "your responsibility", "prohibited", "not allowed"],
            "service_description": ["service", "platform", "feature", "we provide", "we offer"],
            "modifications": ["modify", "change", "update", "amend", "revise"],
            "warranties": ["warranty", "as-is", "no guarantee", "disclaim"],
        }

        for category, keywords in keyword_map.items():
            for kw in keywords:
                if kw in text_lower or kw in section_lower:
                    return category

        return "general"

    def _calculate_max_severity(self, detected_risks: List[Dict[str, Any]]) -> str:
        """Calculate maximum severity from detected risk indicators."""
        if any(r.get("severity") == "critical" for r in detected_risks):
            return "critical"
        elif any(r.get("severity") == "high" for r in detected_risks):
            return "high"
        elif any(r.get("severity") == "medium" for r in detected_risks):
            return "medium"
        return "low"
