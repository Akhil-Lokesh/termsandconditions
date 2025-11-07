"""
Document upload endpoints.

Handles document upload, processing, and analysis orchestration.
"""

import uuid
import tempfile
import os
from pathlib import Path
from typing import Optional
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    UploadFile,
    File,
    status,
    BackgroundTasks,
    Request,
)
from sqlalchemy.orm import Session

from app.api.deps import (
    get_db,
    get_current_active_user,
    get_openai_service,
    get_pinecone_service,
    get_cache_service,
)
from app.core.config import settings
from app.core.document_processor import DocumentProcessor
from app.core.structure_extractor import StructureExtractor
from app.core.legal_chunker import LegalChunker
from app.core.metadata_extractor import MetadataExtractor
from app.core.anomaly_detector import AnomalyDetector
from app.models.user import User
from app.models.document import Document
from app.models.clause import Clause
from app.schemas.document import DocumentResponse, DocumentCreate, DocumentListResponse
from app.services.openai_service import OpenAIService
from app.services.pinecone_service import PineconeService
from app.utils.exceptions import DocumentProcessingError, EmbeddingError, PineconeError
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


# ============================================================================
# BACKGROUND TASK: Anomaly Detection
# ============================================================================


async def run_anomaly_detection_background(
    document_id: str,
    sections: list,
    metadata: dict,
    openai_service: OpenAIService,
    pinecone_service: PineconeService,
    db: Session,
):
    """
    Run anomaly detection in background after document upload completes.

    This task:
    1. Detects anomalies by comparing clauses to baseline corpus
    2. Generates risk assessment report
    3. Saves anomalies to database
    4. Updates document processing status

    Args:
        document_id: Document ID
        sections: Parsed document sections with clauses
        metadata: Document metadata (company name, etc.)
        openai_service: OpenAI service instance
        pinecone_service: Pinecone service instance
        db: Database session
    """
    try:
        logger.info(f"Starting background anomaly detection for {document_id}...")

        # Extract company name from metadata
        company_name = metadata.get("company", "Unknown")

        # Detect anomalies
        detector = AnomalyDetector(openai_service, pinecone_service, db)
        anomalies = await detector.detect_anomalies(
            document_id=document_id,
            sections=sections,
            company_name=company_name,
            service_type="general",  # TODO: Auto-detect service type from metadata
        )

        logger.info(
            f"Anomaly detection completed: {len(anomalies)} anomalies found"
        )

        # Generate risk assessment report
        risk_report = await detector.generate_report(document_id, anomalies)

        # Save anomalies to database
        from app.models.anomaly import Anomaly

        for anomaly_data in anomalies:
            anomaly = Anomaly(
                id=str(uuid.uuid4()),
                document_id=document_id,
                section=anomaly_data["section"],
                clause_number=anomaly_data["clause_number"],
                clause_text=anomaly_data["clause_text"],
                severity=anomaly_data["severity"],
                explanation=anomaly_data["explanation"],
                consumer_impact=anomaly_data.get("consumer_impact", ""),
                recommendation=anomaly_data.get("recommendation", ""),
                risk_category=anomaly_data.get("risk_category", "other"),
                prevalence=anomaly_data["prevalence"],
                detected_indicators=anomaly_data.get("detected_indicators", []),
            )
            db.add(anomaly)

        # Update document with risk assessment
        document = db.query(Document).filter(Document.id == document_id).first()
        if document:
            document.anomaly_count = len(anomalies)
            document.risk_score = risk_report["overall_risk"]["risk_score"]
            document.risk_level = risk_report["overall_risk"]["risk_level"]
            document.processing_status = "completed"
            db.commit()

            logger.info(
                f"Background anomaly detection complete for {document_id}: "
                f"{len(anomalies)} anomalies, "
                f"Risk Score: {risk_report['overall_risk']['risk_score']}/10 "
                f"({risk_report['overall_risk']['risk_level']})"
            )
        else:
            logger.error(f"Document {document_id} not found when updating anomaly results")

    except Exception as e:
        logger.error(f"Background anomaly detection failed for {document_id}: {e}", exc_info=True)

        # Update document status to failed
        try:
            document = db.query(Document).filter(Document.id == document_id).first()
            if document:
                document.processing_status = "anomaly_detection_failed"
                document.anomaly_count = 0
                document.risk_score = 0.0
                document.risk_level = "Unknown"
                db.commit()
        except Exception as db_error:
            logger.error(f"Failed to update document status after error: {db_error}")


@router.post(
    "/",
    response_model=DocumentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload T&C Document",
    description="""
    Upload a Terms & Conditions PDF document for comprehensive analysis.

    **Rate Limit:** 10 uploads per hour per IP address.

    **Processing Pipeline:**
    1. Validate file type and size
    2. Extract text from PDF (pdfplumber primary, PyPDF2 fallback)
    3. Parse document structure (sections, clauses)
    4. Create semantic chunks with metadata
    5. Generate embeddings (OpenAI text-embedding-3-small)
    6. Extract metadata (company, jurisdiction, dates) using GPT-4
    7. Store vectors in Pinecone (user_tcs namespace)
    8. Run anomaly detection (compare to baseline corpus)
    9. Save analysis results to database

    **Returns:** Document metadata with anomaly count and processing status
    """,
)
async def upload_document(
    request: Request,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(..., description="PDF file (max 10MB)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    openai_service: OpenAIService = Depends(get_openai_service),
    pinecone_service: PineconeService = Depends(get_pinecone_service),
):
    """
    Upload and process a T&C document.

    This endpoint orchestrates the full document processing pipeline including
    text extraction, structure parsing, embedding generation, vector storage,
    and anomaly detection.
    """
    # Apply rate limit: 10 uploads per hour per IP
    limiter = request.app.state.limiter
    await limiter.limit("10/hour")(request, endpoint_func=upload_document)

    logger.info(f"Document upload started by user: {current_user.email}")

    # Validate file type (PDF only)
    if not file.filename.endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF files are supported. Please upload a .pdf file.",
        )

    # Read file content
    content = await file.read()
    file_size_mb = len(content) / (1024 * 1024)

    # Validate file size
    if file_size_mb > settings.MAX_UPLOAD_SIZE_MB:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large ({file_size_mb:.1f}MB). Maximum size: {settings.MAX_UPLOAD_SIZE_MB}MB",
        )

    logger.info(f"File validated: {file.filename} ({file_size_mb:.2f}MB)")

    # Generate unique document ID
    doc_id = str(uuid.uuid4())

    # Save file temporarily
    temp_dir = tempfile.mkdtemp()
    temp_path = Path(temp_dir) / f"{doc_id}.pdf"

    try:
        # Write temp file
        with open(temp_path, "wb") as f:
            f.write(content)

        logger.info(f"Temp file created: {temp_path}")

        # ============================================================
        # STEP 1: Extract text from PDF
        # ============================================================
        processor = DocumentProcessor()
        extracted = await processor.extract_text(str(temp_path))

        text = extracted["text"]
        page_count = extracted["page_count"]
        extraction_method = extracted["extraction_method"]

        logger.info(
            f"Text extracted: {len(text)} chars, {page_count} pages, method={extraction_method}"
        )

        if len(text) < 100:
            raise DocumentProcessingError(
                "Document text too short. This may be a scanned PDF or corrupted file."
            )

        # ============================================================
        # STEP 2: Parse structure (sections, clauses)
        # ============================================================
        extractor = StructureExtractor()
        structure = await extractor.extract_structure(text)

        sections = structure["sections"]
        num_clauses = structure["num_clauses"]

        logger.info(
            f"Structure extracted: {num_clauses} clauses found in {len(sections)} sections"
        )

        if num_clauses == 0:
            raise DocumentProcessingError(
                "No structured clauses found in document. Unable to analyze."
            )

        # ============================================================
        # STEP 2.5: Save clauses to database
        # ============================================================
        logger.info(f"Saving {num_clauses} clauses to database...")

        for section in sections:
            section_name = section.get("title", "Unknown Section")
            section_number = section.get("number", "0")

            for clause in section.get("clauses", []):
                clause_record = Clause(
                    id=str(uuid.uuid4()),
                    document_id=doc_id,
                    section=section_name,
                    section_number=section_number,
                    clause_number=clause.get("id", ""),
                    text=clause.get("text", ""),
                )
                db.add(clause_record)

        # Commit clauses
        db.commit()
        logger.info(f"✓ Saved {num_clauses} clauses to database")

        # ============================================================
        # STEP 3: Create semantic chunks
        # ============================================================
        chunker = LegalChunker()
        chunks = await chunker.create_chunks(sections)

        logger.info(f"Created {len(chunks)} chunks for embedding")

        # ============================================================
        # STEP 4: Generate embeddings
        # ============================================================
        texts = [chunk["text"] for chunk in chunks]
        embeddings = await openai_service.batch_create_embeddings(texts)

        logger.info(f"Generated {len(embeddings)} embeddings")

        # Add embeddings to chunks
        for chunk, embedding in zip(chunks, embeddings):
            chunk["embedding"] = embedding

        # ============================================================
        # STEP 5: Extract metadata with GPT-4
        # ============================================================
        metadata_extractor = MetadataExtractor(openai_service)
        metadata = await metadata_extractor.extract_metadata(text)

        logger.info(
            f"Metadata extracted: Company={metadata.get('company_name', 'Unknown')}, "
            f"Jurisdiction={metadata.get('jurisdiction', 'Unknown')}"
        )

        # ============================================================
        # STEP 6: Store in Pinecone
        # ============================================================
        await pinecone_service.upsert_chunks(
            chunks=chunks,
            namespace=settings.PINECONE_USER_NAMESPACE,
            document_id=doc_id,
        )

        logger.info(f"Stored {len(chunks)} vectors in Pinecone")

        # ============================================================
        # STEP 7: Save to database
        # ============================================================
        document = Document(
            id=doc_id,
            user_id=current_user.id,
            filename=file.filename,
            text=text,
            document_metadata=metadata,
            page_count=page_count,
            clause_count=num_clauses,
            processing_status="embedding_completed",
        )

        db.add(document)
        db.commit()
        db.refresh(document)

        logger.info(f"Document saved to database: {doc_id}")

        # ============================================================
        # STEP 8: Schedule anomaly detection in background
        # ============================================================
        logger.info(f"Scheduling background anomaly detection for {doc_id}")

        # Update document status to indicate background processing
        document.processing_status = "analyzing_anomalies"
        db.commit()

        # Schedule background task
        background_tasks.add_task(
            run_anomaly_detection_background,
            document_id=doc_id,
            sections=sections,
            metadata=metadata,
            openai_service=openai_service,
            pinecone_service=pinecone_service,
            db=db,
        )

        logger.info(f"Background anomaly detection scheduled for {doc_id}")

        # ============================================================
        # Success! Upload complete, analysis running in background
        # ============================================================
        logger.info(f"✓ Document upload complete: {doc_id} (anomaly detection in background)")

        return DocumentResponse(
            id=doc_id,
            filename=file.filename,
            metadata=metadata,
            page_count=page_count,
            clause_count=num_clauses,
            anomaly_count=0,  # Will be populated when background task completes
            processing_status="analyzing_anomalies",
            created_at=document.created_at,
        )

    except DocumentProcessingError as e:
        logger.error(f"Document processing error: {e}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        )

    except EmbeddingError as e:
        logger.error(f"Embedding generation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Failed to generate embeddings. OpenAI service may be unavailable.",
        )

    except PineconeError as e:
        logger.error(f"Vector storage failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Failed to store document vectors. Pinecone service may be unavailable.",
        )

    except Exception as e:
        logger.error(f"Unexpected error during processing: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Document processing failed: {str(e)}",
        )

    finally:
        # Cleanup temp file
        if temp_path.exists():
            os.remove(temp_path)
        if Path(temp_dir).exists():
            os.rmdir(temp_dir)
        logger.info("Temp files cleaned up")


@router.get(
    "/{document_id}",
    response_model=DocumentResponse,
    summary="Get Document Details",
    description="Retrieve full details of a specific document by ID.",
)
async def get_document(
    document_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Get document metadata and analysis results by ID.
    """
    document = (
        db.query(Document)
        .filter(
            Document.id == document_id,
            Document.user_id == current_user.id,
        )
        .first()
    )

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document not found: {document_id}",
        )

    return DocumentResponse(
        id=document.id,
        filename=document.filename,
        metadata=document.document_metadata,
        page_count=document.page_count,
        clause_count=document.clause_count,
        anomaly_count=document.anomaly_count,
        processing_status=document.processing_status,
        created_at=document.created_at,
    )


@router.get(
    "/",
    response_model=DocumentListResponse,
    summary="List User Documents",
    description="Get a list of all documents uploaded by the current user.",
)
async def list_documents(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    List all documents for the current user with pagination.
    """
    # Get total count
    total = db.query(Document).filter(Document.user_id == current_user.id).count()

    # Get documents with pagination
    documents = (
        db.query(Document)
        .filter(Document.user_id == current_user.id)
        .order_by(Document.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )

    return DocumentListResponse(
        documents=[
            DocumentResponse(
                id=doc.id,
                filename=doc.filename,
                metadata=doc.document_metadata,
                page_count=doc.page_count,
                clause_count=doc.clause_count,
                anomaly_count=doc.anomaly_count,
                processing_status=doc.processing_status,
                created_at=doc.created_at,
            )
            for doc in documents
        ],
        total=total,
        skip=skip,
        limit=limit,
    )


@router.delete(
    "/{document_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete Document",
    description="Delete a document and all associated data (vectors, clauses, anomalies).",
)
async def delete_document(
    document_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    pinecone_service: PineconeService = Depends(get_pinecone_service),
):
    """
    Delete document and cleanup all associated resources.
    """
    # Find document
    document = (
        db.query(Document)
        .filter(
            Document.id == document_id,
            Document.user_id == current_user.id,
        )
        .first()
    )

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document not found: {document_id}",
        )

    try:
        # Delete from Pinecone
        await pinecone_service.delete_document(
            document_id=document_id,
            namespace=settings.PINECONE_USER_NAMESPACE,
        )
        logger.info(f"Deleted vectors from Pinecone: {document_id}")

        # Delete from database (cascades to clauses and anomalies)
        db.delete(document)
        db.commit()

        logger.info(f"Document deleted: {document_id}")

    except Exception as e:
        logger.error(f"Failed to delete document {document_id}: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete document: {str(e)}",
        )
